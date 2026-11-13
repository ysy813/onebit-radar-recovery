"""Partition error in one already read diagnostic frame; no new evaluation run."""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
import math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
RELEASE = ROOT / "scalar_restore_v3"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def same(a, b):
    return math.isclose(float(a), float(b), rel_tol=1e-11, abs_tol=1e-12)


baseline = read(HERE / "reports/SOURCE_BASELINE.json")
changed = [p for p, v in baseline.items() if sha(ROOT / p) != v["sha256"]]
assert not changed, changed
record_id = "confirm_synth_116013_512"
array_relative = "scalar_restore_v3/compact_development/arrays/" + record_id + ".npz"
array_path = ROOT / array_relative
point_report = read(HERE / "reports/POINT_REFERENCE_WALKTHROUGH.json")
assert sha(array_path) == point_report["source_sha256"][array_relative]
development_path = RELEASE / "compact_development/report.json"
record = next(r for r in read(development_path)["rows"] if r["id"] == record_id)
assert record["group"] == "synthetic" and record["actual_chirps"] == 512
with np.load(array_path, allow_pickle=False) as arrays:
    ref, base, previous, final = [arrays[k] for k in ["reference", "base", "previous_power", "enhanced"]]
y = np.sqrt(ref.astype("f8") / max(float(ref.max()), 1))
input_peak = max(float(base.max()), 1)
amplitudes = {name: np.sqrt(power.astype("f8") / input_peak)
              for name, power in [("bypass", base), ("first_guard", previous), ("compact", final)]}

# Use the same seven-by-seven exclusion geometry as evaluate.measures.
# The background threshold uses float32 y, as common_v2.amplitudes does.
target_neighborhood = np.zeros(y.shape, dtype=bool)
for target in record["targets"]:
    r, a = round(target["range_bin"]), round(target["doppler_bin"])
    target_neighborhood[np.ix_(np.arange(r - 3, r + 4) % 1024,
                                np.arange(a - 3, a + 4) % 512)] = True
y_background = y.astype("f4")
background = (y_background < .003) & ~target_neighborhood
remaining = ~(target_neighborhood | background)
masks = dict(known_target_neighborhoods=target_neighborhood,
             reference_low_background=background, remaining=remaining)
coverage = sum(mask.astype("u1") for mask in masks.values())
reference_energy = float(np.square(y).sum())
full_sse = {name: float(np.square(value - y).sum()) for name, value in amplitudes.items()}
full_nmse = {name: value / reference_energy for name, value in full_sse.items()}
total_reduction = full_sse["bypass"] - full_sse["compact"]
rows = []
for name, mask in masks.items():
    sse = {stage: float(np.square(value[mask] - y[mask]).sum())
           for stage, value in amplitudes.items()}
    reduction = sse["bypass"] - sse["compact"]
    rows.append(dict(region=name, pixels=int(mask.sum()), sse=sse,
                     bypass_to_compact_reduction=reduction,
                     contribution_to_total_reduction=reduction / total_reduction,
                     compact_minus_first_guard=sse["compact"] - sse["first_guard"]))

background_positive = {name: float(np.square(np.maximum(value[background] - y_background[background], 0)).sum())
                       for name, value in amplitudes.items()}
reported = record["metrics"]["all"]
previous_reported = record["previous_v2"]["metrics"]["all"]
bg_v7 = record["original"]["background_positive_error"]
checks = dict(
    same_previously_read_development_array=sha(array_path) == point_report["source_sha256"][array_relative],
    regions_disjoint_and_exhaustive=bool(np.all(coverage == 1)),
    region_pixel_counts_sum_to_full=sum(r["pixels"] for r in rows) == 1024 * 512,
    region_sse_sum_matches_full=all(same(sum(r["sse"][stage] for r in rows), full_sse[stage]) for stage in amplitudes),
    regional_reductions_sum_to_full=same(sum(r["bypass_to_compact_reduction"] for r in rows), total_reduction),
    final_nmse_matches_existing_report=same(full_nmse["bypass"], reported["baseline_nmse"]) and same(full_nmse["compact"], reported["enhanced_nmse"]),
    first_stage_nmse_matches_existing_report=same(full_nmse["first_guard"], previous_reported["enhanced_nmse"]),
    original_background_metrics_reproduced=same(background_positive["compact"], record["background_positive_error"]) and same(background_positive["first_guard"], record["previous_v2"]["background_positive_error"]),
    compact_decreases_target_neighborhood_error=rows[0]["compact_minus_first_guard"] < 0,
    compact_increases_background_error=rows[1]["compact_minus_first_guard"] > 0,
    background_region_explains_most_reduction=rows[1]["contribution_to_total_reduction"] > .9,
    final_background_better_than_bypass_but_worse_than_v7=background_positive["compact"] < background_positive["bypass"] and background_positive["compact"] > bg_v7,
    frozen_sources_unchanged=not changed,
)
sources = [array_relative, "scalar_restore_v3/compact_development/report.json",
           "scalar_restore_v2/evaluate.py", "scalar_restore_v2/common_v2.py",
           "scalar_streak_fix_v1/common.py",
           "network_understanding_v1/reports/POINT_REFERENCE_WALKTHROUGH.json"]
result = dict(status="PASS" if all(checks.values()) else "FAIL", checks=checks,
              scope="Error-accounting explanation for one existing synthetic diagnostic frame; not a new quality test",
              record_id=record_id, original_split=record["split"], regions=rows,
              reference_energy=reference_energy, total_sse=full_sse, total_nmse=full_nmse,
              full_frame_nmse_ratio=full_sse["compact"] / full_sse["bypass"],
              total_sse_reduction=total_reduction,
              background_positive_error=background_positive,
              v7_background_positive_error_from_existing_report=bg_v7,
              final_background_positive_relative_to_v7=background_positive["compact"] / bg_v7,
              qualifications=["All predictions use the input peak; reference uses its own peak",
                              "Region squared errors use float64 reference, with a float32-derived background mask",
                              "Original positive-background metric also uses float32 reference values",
                              "Known-target neighborhoods include other content and are not isolated target amplitudes",
                              "The remaining region is not assumed to be noise or false targets",
                              "Regional contribution percentages are bookkeeping, not causal feature attribution",
                              "This diagnosed frame is not the eight-frame fresh synthetic_512 group",
                              "No detection-rate, physical-target, or statistical-independence conclusion"],
              source_sha256={name: sha(ROOT / name) for name in sources},
              script_sha256=sha(Path(__file__)), frozen_files_checked=len(baseline), changed_sources=changed,
              original_full_quality_status_preserved="FAIL", saved_frame_metric_accounting_run=True,
              model_instantiated=False, neural_inference_run=False, feature_extraction_run=False,
              guard_run=False, radar_fft_run=False, training_run=False, model_parameters_modified=False,
              new_quality_test_run=False, new_holdout_opened=False, new_dataset_generated=False,
              hardware_built=False, board_accessed=False)
(HERE / "reports/SAVED_FRAME_ERROR_PARTITION.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
print(json.dumps(dict(status=result["status"], checks=checks, regions=rows,
                      total_sse=full_sse, full_frame_nmse_ratio=result["full_frame_nmse_ratio"],
                      background_positive_error=background_positive,
                      final_background_relative_to_v7=result["final_background_positive_relative_to_v7"]), ensure_ascii=False))
if result["status"] != "PASS":
    raise SystemExit(1)
