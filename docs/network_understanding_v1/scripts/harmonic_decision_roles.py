"""Explain harmonic protection eligibility using saved points and exact algebra."""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

baseline = read(HERE / "reports/SOURCE_BASELINE.json")
changed = [p for p, v in baseline.items() if sha(ROOT / p) != v["sha256"]]
guards = read(HERE / "reports/TRAINING_GUARD_WALKTHROUGH.json")
references = read(HERE / "reports/POINT_REFERENCE_WALKTHROUGH.json")
trace = read(HERE / "reports/POINT_TRACE.json")
assert guards["status"] == references["status"] == trace["status"] == "PASS"

# Exact rational equivalence of a thresholded amplitude-ratio predicate and
# its interval form. These specified numbers are not model predictions.
cases = []
for h in [3, 5]:
    for parent in [F(0), F(1, 8), F(1, 4), F(1, 2), F(1)]:
        lo, hi = parent / (2 * h), 3 * parent / (2 * h)
        for current in sorted({F(0), F(1), parent / h, lo, hi,
                               max(F(0), lo - F(1, 65536)),
                               lo + F(1, 65536), hi - F(1, 65536),
                               hi + F(1, 65536)}):
            if not 0 <= current <= 1:
                continue
            ratio = parent >= F(1, 4) and 2 * abs(h * current - parent) <= parent
            interval = parent >= F(1, 4) and lo <= current <= hi
            cases.append(dict(order_magnitude=h, parent=str(parent), current=str(current),
                              ratio_predicate=ratio, interval_predicate=interval))

rows = []
for point in guards["existing_guard_points"]:
    current = point["amplitude_q16"]
    flags = []
    for h, key in [(3, "parent3_q16"), (5, "parent5_q16")]:
        parent = point[key]
        flag = parent >= 16384 and 2 * abs(h * current - parent) <= parent
        flags.append(flag)
        assert flag == point[f"explained{h}"]
    saved_trace = next(p for p in trace["rows"]
                       if [p["natural_range_bin"], p["natural_doppler_bin"]] == point["position"])
    saved_reference = next(p for p in references["point_rows"] if p["position"] == point["position"])
    gains = [point[k] / 16384 for k in ["raw_gain_q14", "first_guard_gain_q14", "final_gain_q14"]]
    assert gains == [saved_trace[k] / 16384 for k in ["raw_gain_q14", "first_guard_gain_q14", "final_gain_q14"]]
    rows.append(dict(position=point["position"], decoded_current=current / 65536,
                     decoded_parent3=point["parent3_q16"] / 65536,
                     decoded_parent5=point["parent5_q16"] / 65536,
                     harmonic_explained=any(flags), first_eligible=point["first_eligible"],
                     compact_eligible=point["compact_eligible"], gains=gains,
                     input_relative_amplitude=saved_reference["input_relative_amplitude"],
                     reference_relative_amplitude=saved_reference["reference_relative_amplitude"],
                     final_absolute_error=saved_reference["stages"]["compact"]["absolute_error"],
                     physical_target_label_inferred=False))

checks = dict(
    amplitude_ratio_interval_equivalent=all(c["ratio_predicate"] == c["interval_predicate"] for c in cases),
    existing_flags_and_gain_paths_match=len(rows) == 4,
    explained_existing_point_keeps_neural_attenuation=rows[1]["harmonic_explained"] and rows[1]["gains"] == [.125, .125, .125],
    unexplained_does_not_imply_small_reference_error=not rows[3]["harmonic_explained"] and rows[3]["gains"][-1] == 1 and rows[3]["reference_relative_amplitude"] < .0001,
    frame_peak_has_separate_anchor=rows[0]["gains"][0] > 1 and rows[0]["gains"][-1] == 1 and not rows[0]["first_eligible"],
    frozen_sources_unchanged=not changed,
)
sources = ["scalar_restore_v3/pc_candidate_compact/scalar_guard.py",
           "scalar_restore_v3/pc_candidate_compact/compact_guard.py",
           "scalar_restore_v3/pc_candidate_compact/model_source.py",
           "network_understanding_v1/reports/TRAINING_GUARD_WALKTHROUGH.json",
           "network_understanding_v1/reports/POINT_REFERENCE_WALKTHROUGH.json",
           "network_understanding_v1/reports/POINT_TRACE.json"]
result = dict(status="PASS" if all(checks.values()) else "FAIL", checks=checks,
              scope="Exact algebra and explanation of previously saved point decisions; not a new quality test",
              record_id=references["record_id"], ratio_cases=cases, point_rows=rows,
              interpretation="Harmonic-explained flag disables two protections for 512 valid chirps; it does not set a learned gain or label physical targets",
              source_sha256={p: sha(ROOT / p) for p in sources}, script_sha256=sha(Path(__file__)),
              frozen_files_checked=len(baseline), changed_sources=changed,
              original_full_quality_status_preserved="FAIL", constructed_ratio_algebra_run=True,
              saved_point_explanation_run=True, model_instantiated=False, neural_inference_run=False,
              feature_extraction_run=False, guard_run=False, radar_fft_run=False, training_run=False,
              model_parameters_modified=False, new_quality_test_run=False, new_holdout_opened=False,
              hardware_built=False, board_accessed=False)
(HERE / "reports/HARMONIC_DECISION_ROLES.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
print(json.dumps(dict(status=result["status"], checks=checks, ratio_cases=len(cases), point_rows=rows), ensure_ascii=False))
if result["status"] != "PASS":
    raise SystemExit(1)
