"""Explain the frozen MLP at FOUR ALREADY TRACED points only.

Exact integer replay and an algebraic fixed-gate decomposition, including
rounding residuals. No FFT, feature extraction, full-frame inference, training,
new holdout, model modification, hardware build or board access.
"""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import hashlib
import json
import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
MODEL = ROOT / "scalar_restore_v3/pc_candidate_compact"
Q = 1 << 16
DEN = 1 << 64

def read(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

trace_path = HERE / "reports/POINT_TRACE.json"
trace = read(trace_path)
weights_path = MODEL / "weights.npz"
assert sha(weights_path) == read(MODEL / "config.json")["sha256"]["weights.npz"]
with np.load(weights_path, allow_pickle=False) as data:
    weights = [data[f"w{i}"].astype("i8").tolist() for i in range(3)]
    biases = [data[f"b{i}"].astype("i8").reshape(-1).tolist() for i in range(3)]
    gain_lut = data["gain_lut"].astype("i8").tolist()
assert [len(w) for w in weights] == [32, 16, 1]
assert [len(w[0]) for w in weights] == [40, 32, 16]

GROUPS = {
    "own_and_local_0_3": list(range(4)),
    "parent_4_5": [4, 5],
    "child_6_7": [6, 7],
    "derived_amplitude_8_15": list(range(8, 16)),
    "neighbors_16_39": list(range(16, 40)),
}
rows = []
for old in trace["rows"]:
    x = [int(v) for v in old["feature_q16"]]
    v = x[:]
    stages = []
    for i in range(3):
        acc = [int(b) + sum(int(a)*int(w) for a,w in zip(v,ww))
               for ww,b in zip(weights[i],biases[i])]
        rounded = [(a+32768)>>16 for a in acc]
        residual = [r*Q-a for r,a in zip(rounded,acc)]
        assert all(-32767 <= e <= 32768 for e in residual)
        out = [max(r,0) for r in rounded] if i < 2 else rounded
        expected = old[f"layer{i}_q16"] if i < 2 else [old["raw_score_q16"]]
        assert out == expected
        stages.append(dict(input_q16=v, accumulator_q32=acc,
                           rounded_before_relu_q16=rounded,
                           rounding_residual_q32=residual, output_q16=out))
        v = out
    d0 = [int(h>0) for h in stages[0]["output_q16"]]
    d1 = [int(h>0) for h in stages[1]["output_q16"]]
    w0,w1,w2 = weights[0],weights[1],weights[2][0]
    b0,b1,b2 = biases[0],biases[1],biases[2][0]

    # a = W2 D1 W1 D0 W0: numerator denominator is Q^3 = 2^48.
    upstream = [d0[j]*sum(w2[k]*d1[k]*w1[k][j] for k in range(16))
                for j in range(32)]
    coeff = [sum(upstream[j]*w0[j][m] for j in range(32)) for m in range(40)]
    terms = [a*f for a,f in zip(coeff,x)]  # common denominator 2^64
    bias_num = (sum(u*b for u,b in zip(upstream,b0))
                + Q*sum(w2[k]*d1[k]*b1[k] for k in range(16)) + Q*Q*b2)
    rounding_num = (
        sum(u*e for u,e in zip(upstream,stages[0]["rounding_residual_q32"]))
        + Q*sum(w2[k]*d1[k]*stages[1]["rounding_residual_q32"][k] for k in range(16))
        + Q*Q*stages[2]["rounding_residual_q32"][0])
    total_num = sum(terms)+bias_num+rounding_num
    assert total_num == old["raw_score_q16"]*(1<<48)
    group_nums = {name:sum(terms[m] for m in ids) for name,ids in GROUPS.items()}
    assert sum(group_nums.values()) == sum(terms)

    # Read the same quantized constants in ideal REAL arithmetic. This is
    # explanatory algebra, not a replacement model or a quality evaluation.
    vv = np.asarray(x,dtype="f8")/Q
    ideal_masks = []
    for i in range(3):
        vv = np.asarray(weights[i],dtype="f8")/Q @ vv + np.asarray(biases[i],dtype="f8")/(Q*Q)
        if i < 2:
            ideal_masks.append((vv>0).astype("i8").tolist())
            vv = np.maximum(vv,0)
    ideal_score = float(vv[0])
    masks_same = ideal_masks == [d0,d1]
    if masks_same:
        assert abs(ideal_score-(sum(terms)+bias_num)/DEN) < 1e-12

    output_terms = [int(w)*int(h) for w,h in zip(w2,stages[1]["output_q16"])]
    assert sum(output_terms)+b2 == stages[2]["accumulator_q32"][0]
    score_q10 = (old["raw_score_q16"]+32)>>6
    lut_index = min(32768,max(0,score_q10+16384))
    assert gain_lut[lut_index] == old["raw_gain_q14"]
    rows.append(dict(
        position=[old["natural_range_bin"],old["natural_doppler_bin"]],
        power=old["power"], center_q16=x[0], center_real=x[0]/Q,
        first_layer_active=sum(d0), second_layer_active=sum(d1),
        first_active_indices=[j for j,d in enumerate(d0) if d],
        second_active_indices=[j for j,d in enumerate(d1) if d],
        active_pattern_matches_ideal_real=bool(masks_same),
        ideal_real_score_with_quantized_constants=ideal_score,
        score_q16=old["raw_score_q16"], score_real=old["raw_score_real"],
        output_head_terms_log2=[n/(Q*Q) for n in output_terms],
        output_head_positive_sum=sum(max(n,0) for n in output_terms)/(Q*Q),
        output_head_negative_sum=sum(min(n,0) for n in output_terms)/(Q*Q),
        output_head_bias=b2/(Q*Q),
        output_head_rounding=stages[2]["rounding_residual_q32"][0]/(Q*Q),
        effective_feature_coeff_numerators=coeff,
        effective_feature_coeff_denominator=1<<48,
        feature_term_numerators=terms,
        grouped_feature_contributions={k:v/DEN for k,v in group_nums.items()},
        effective_bias_contribution=bias_num/DEN,
        propagated_rounding_contribution=rounding_num/DEN,
        exact_identity=dict(common_denominator=DEN, feature_sum_numerator=sum(terms),
                            effective_bias_numerator=bias_num,
                            propagated_rounding_numerator=rounding_num,
                            score_numerator=total_num, exact_match=True),
        raw_gain=old["raw_gain_q14"]/16384,
        first_guard_gain=old["first_guard_gain_q14"]/16384,
        final_gain=old["final_gain_q14"]/16384,
        source_trace_exact=True,
    ))

same_center = [r for r in rows if r["position"] in [[25,0],[200,148]]]
assert len(same_center)==2 and same_center[0]["center_q16"]==same_center[1]["center_q16"]
assert same_center[0]["score_q16"] != same_center[1]["score_q16"]
assert same_center[0]["final_gain"] == same_center[1]["final_gain"] == 1
result=dict(
    status="PASS", scope="Exact algebra on four existing point traces; not a performance or causal attribution experiment",
    rows=rows, same_center_different_raw_gain_verified=True,
    exact_integer_decomposition_verified=True,
    groups=GROUPS,
    interpretation="Fixed-gate arithmetic grouping is NOT causal importance, an ablation, or a semantic label for neurons; feature combinations are correlated",
    source_sha256={str(p.relative_to(ROOT)):sha(p) for p in [weights_path,MODEL/"restore_power.py",MODEL/"model_source.py",trace_path]},
    neural_parameters_modified=False, training_run=False, full_frame_inference_run=False,
    new_quality_test_run=False, new_holdout_opened=False, board_accessed=False,
)
report_path=HERE/"reports/LEARNED_RULE_WALKTHROUGH.json"
report_path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(dict(status=result["status"],points=[{
    k:r[k] for k in ["position","center_real","first_layer_active","second_layer_active",
                     "score_real","output_head_positive_sum","output_head_negative_sum",
                     "output_head_bias","grouped_feature_contributions","effective_bias_contribution",
                     "propagated_rounding_contribution","active_pattern_matches_ideal_real"]}
    for r in rows]),ensure_ascii=False))
