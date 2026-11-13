"""Reference-informed uniform-gain arithmetic on an old saved frame; no model."""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4*1024*1024), b""):
            h.update(block)
    return h.hexdigest()

record_id = "confirm_synth_116013_512"
array_path = f"scalar_restore_v3/compact_development/arrays/{record_id}.npz"
prior = read(HERE/"reports/BOUNDED_ORACLE_WALKTHROUGH.json")
assert sha(ROOT/array_path) == prior["source_sha256"][array_path]
with np.load(ROOT/array_path,allow_pickle=False) as data:
    reference,base,enhanced,gain = [data[k] for k in ["reference","base","enhanced","gain"]]
x = np.sqrt(base.astype("f8")/int(base.max()))
y = np.sqrt(reference.astype("f8")/int(reference.max()))
current = np.sqrt(enhanced.astype("f8")/int(base.max()))
current_ideal = x*gain.astype("f8")/16384
energy = float(np.sum(x*x))
cross = float(np.sum(x*y))
unconstrained = cross/energy
alpha = float(np.clip(unconstrained,.125,1.5))
uniform = alpha*x

def sse(output):
    return float(np.sum((output-y)**2))

uniform_sse = sse(uniform)
residual = uniform-y
delta = current_ideal-uniform
delta_energy = float(np.sum(delta*delta))
delta_cross = float(2*np.sum(residual*delta))
grid = [.125,.25,.5,.75,.822,1.,1.25,1.5]
point_rows = []
for point in [(83,0),(774,511),(25,0),(200,148)]:
    point_rows.append(dict(position=list(point),reference=float(y[point]),bypass=float(x[point]),
                           uniform=float(uniform[point]),compact=float(current[point]),
                           uniform_squared_error=float((uniform[point]-y[point])**2),
                           compact_squared_error=float((current[point]-y[point])**2)))
baseline = read(HERE/"reports/SOURCE_BASELINE.json")
changed = [p for p,info in baseline.items() if sha(ROOT/p) != info["sha256"]]
checks = dict(
    same_old_diagnostic_record=prior["record_id"] == record_id,
    previous_saved_sse_matches=abs(sse(current)-prior["current_saved_power_sse"])<1e-14,
    optimum_is_interior=.125 < unconstrained < 1.5,
    uniform_normal_equation_holds=abs(float(np.sum(residual*x)))<1e-14,
    scalar_quadratic_identity_holds=all(abs(sse(a*x)-(uniform_sse+energy*(a-alpha)**2))<1e-13 for a in grid),
    oracle_uniform_no_worse_than_bypass=uniform_sse <= sse(x),
    saved_and_ideal_compact_better_than_all_constant_gains=max(sse(current),sse(current_ideal)) < uniform_sse,
    nonuniform_error_identity_holds=abs(uniform_sse+delta_energy+delta_cross-sse(current_ideal))<1e-13,
    frame_peak_kept_but_overestimate_attenuated=current[83,0] == x[83,0] and current[774,511] < uniform[774,511],
    uniform_can_be_better_at_individual_point=point_rows[3]["uniform_squared_error"] < point_rows[3]["compact_squared_error"],
    frozen_sources_unchanged=not changed)
checks = {k:bool(v) for k,v in checks.items()}
sources = [array_path,"network_understanding_v1/reports/BOUNDED_ORACLE_WALKTHROUGH.json"]
report = dict(status="PASS" if all(checks.values()) else "FAIL",checks=checks,record_id=record_id,
              scope="Additional arithmetic explanation of one previously diagnosed synthetic development frame; no new quality gate",
              normalization="Reference uses its own peak; bypass, uniform and compact use the SAME input peak",
              uniform_oracle=dict(gain_interval=[.125,1.5],unconstrained_optimum=unconstrained,
                                  selected_gain=alpha,input_amplitude_energy=energy,input_reference_inner_product=cross,
                                  uses_reference=True,peak_anchor_enforced=False,sse=uniform_sse),
              bypass_sse=sse(x),compact_saved_sse=sse(current),compact_ideal_sse=sse(current_ideal),
              compact_to_optimal_uniform_sse=sse(current)/uniform_sse,
              relative_sse_reduction_from_uniform=1-sse(current)/uniform_sse,
              nonuniform_error_identity=dict(uniform_sse=uniform_sse,squared_departure_from_uniform=delta_energy,
                                              residual_cross_term=delta_cross,compact_ideal_sse=sse(current_ideal)),
              point_rows=point_rows,
              qualifications=["Uniform gain is an analytic reference-informed comparison, not a new trained or deployable model",
                              "The constant-gain class is relaxed to allow changing the input peak; current compact preserves its peak",
                              "No independent rescaling of the uniform or compact output is performed",
                              "This one saved development frame does not establish generalization or all-frame superiority",
                              "The result concerns the full compact combination, not the isolated neural MLP",
                              "No superiority over all simple nonlinear rules, filters, thresholds or retrained baselines is proved",
                              "Total error improvement is not a guarantee of improvement at each target or pixel"],
              source_sha256={p:sha(ROOT/p) for p in sources},script_sha256=sha(Path(__file__)),
              frozen_files_checked=len(baseline),changed_sources=changed,
              saved_frame_uniform_gain_accounting_run=True,model_instantiated=False,
              neural_inference_run=False,feature_extraction_run=False,guard_run=False,
              radar_fft_run=False,training_run=False,model_parameters_modified=False,
              new_quality_test_run=False,new_holdout_opened=False,hardware_built=False,board_accessed=False,
              original_full_quality_status_preserved="FAIL")
(HERE/"reports/UNIFORM_GAIN_WALKTHROUGH.json").write_text(
    json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
print(json.dumps({k:report[k] for k in ["status","checks","uniform_oracle","bypass_sse",
                  "compact_saved_sse","relative_sse_reduction_from_uniform","point_rows"]},ensure_ascii=False))
if report["status"] != "PASS":
    raise SystemExit(1)
