"""Exact sampling/weighting examples for teaching; never builds a training pool."""
import sys
sys.dont_write_bytecode = True
import ast
import hashlib
import json
import math
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
SOURCE = ROOT / "scalar_restore_v2/runs/protected_patch5/training_source.py"

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

baseline = read(HERE / "reports/SOURCE_BASELINE.json")
changed = [p for p, info in baseline.items() if sha(ROOT / p) != info["sha256"]]
config = read(ROOT / "scalar_restore_v2/runs/soft_patch5/config.json")
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
pool_function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "make_pool")
sampling_loop = next(n for n in ast.walk(pool_function) if isinstance(n, ast.For)
                     and isinstance(n.target, ast.Tuple)
                     and [e.id for e in n.target.elts] == ["mask", "count"])
counts = [(ast.unparse(item.elts[0]), ast.literal_eval(item.elts[1])) for item in sampling_loop.iter.elts]
counts[-1] = ("uniform", counts[-1][1])
total = sum(count for _, count in counts)

# Specified masks over 100 labelled positions, not extracted radar pixels.
# They illustrate overlaps and missing labels without running make_pool.
n = 100
masks = dict(known={0}, support=set(range(10)), centers={0, 1},
             artifact_peaks=set(range(10, 15)), excess=set(range(10, 30)),
             low=set(range(30, 90)), uniform=set(range(n)))

def sampling_probability(regions):
    probabilities = [F(0)] * n
    for name, count in counts:
        members = regions[name] or set(range(n))
        for i in members:
            probabilities[i] += F(count, total * len(members))
    return probabilities

prob = sampling_probability(masks)
weights = [1 + 3 * (i in masks["support"]) + 5 * (i in masks["known"]) + 8 * (i in masks["centers"]) for i in range(n)]
weighted_total = sum(p * w for p, w in zip(prob, weights))
without_known = {**masks, "known": set()}
fallback_prob = sampling_probability(without_known)
rows = [dict(position=i, memberships=[name for name, members in masks.items() if i in members],
             expected_pool_entries=float(prob[i] * total), expected_sampling_probability=float(prob[i]),
             loss_weight=weights[i], population_normalized_weight=float(prob[i] * weights[i] / weighted_total))
        for i in [0, 1, 3, 10, 20, 30, 90]]

# A separate two-type example illustrates E[numerator/denominator].
# v=1 for the rare type, v=0 otherwise; all samples are valid, w>=1.
rare_probability = F(1, 10)
batch_rows = []
for size in [1, 2, 8, 32]:
    coefficient = sum(F(math.comb(size, k)) * rare_probability ** k * (1-rare_probability) ** (size-k)
                      * F(9*k, size+8*k) for k in range(size+1))
    batch_rows.append(dict(specified_batch_size=size, expected_weighted_mean=float(coefficient)))
ratio_of_expectations = F(9, 10) / (F(9, 10) + F(9, 10))

checks = dict(
    selected_source_hash_matches=sha(SOURCE) == config["code_sha256"],
    source_sampler_counts_match=counts == [("known",2048),("support",2048),("centers",2048),
                                          ("artifact_peaks",2048),("excess",6144),("low",4096),("uniform",4096)],
    expected_probabilities_sum_to_one=sum(prob) == sum(fallback_prob) == 1,
    overlapping_region_counts_add=prob[0] / prob[90] == 81,
    weighting_is_additional=weights[0] == 17 and (prob[0] * weights[0]) / (prob[90] * weights[90]) == 1377,
    empty_known_falls_back_to_uniform=fallback_prob[90] / prob[90] == F(3, 2),
    finite_batch_normalization_differs_from_population=batch_rows[0]["expected_weighted_mean"] == .1 and all(r["expected_weighted_mean"] < .5 for r in batch_rows),
    large_batch_ratio_of_expectations=float(ratio_of_expectations) == .5,
    frozen_sources_unchanged=not changed,
)
sources = ["scalar_restore_v2/runs/protected_patch5/training_source.py",
           "scalar_restore_v2/runs/soft_patch5/config.json"]
result = dict(status="PASS" if all(checks.values()) else "FAIL", checks=checks,
              scope="Specified masks and exact probability algebra only, not actual training statistics or a quality experiment",
              source_sampler_counts=counts, entries_per_record=total,
              probability_formula_is_expectation_over_pool_generation=True,
              actual_fixed_pool_probabilities_not_reconstructed=True,
              specified_mask_example=dict(positions=n, sizes={k:len(v) for k,v in masks.items()}, rows=rows),
              specified_batch_example=dict(rare_probability=.1, common_weight=1, rare_weight=9,
                  common_value=0, rare_value=1, rows=batch_rows, ratio_of_expectations=float(ratio_of_expectations)),
              qualifications=["Expected multiplicity is not a per-step gradient or actual target frequency",
                              "Current losses have separate masks and normalization denominators",
                              "The constructed batch example does not estimate the actual 3072-sample training batch",
                              "Training sampling does not alter inference inputs or supply inference references"],
              source_sha256={p:sha(ROOT/p) for p in sources}, script_sha256=sha(Path(__file__)),
              frozen_files_checked=len(baseline), changed_sources=changed,
              original_full_quality_status_preserved="FAIL", exact_probability_algebra_run=True,
              radar_data_read=False, sampling_run=False, training_pool_built=False, model_instantiated=False,
              training_run=False, optimizer_run=False, neural_inference_run=False, model_parameters_modified=False,
              new_quality_test_run=False, new_holdout_opened=False, hardware_built=False, board_accessed=False)
(HERE / "reports/TRAINING_SAMPLING_WALKTHROUGH.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
print(json.dumps(dict(status=result["status"],checks=checks,example_rows=rows,batch_example=result["specified_batch_example"]),ensure_ascii=False))
if result["status"] != "PASS":
    raise SystemExit(1)
