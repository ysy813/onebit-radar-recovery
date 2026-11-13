"""Compare saved diagnostic gains to their existing paired reference; no inference."""
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
    return math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-12)


baseline = read(HERE / "reports/SOURCE_BASELINE.json")
changed = [name for name, info in baseline.items()
           if sha(ROOT / name) != info["sha256"]]
assert not changed, changed
trace = read(HERE / "reports/POINT_TRACE.json")
package = read(RELEASE / "RUNTIME_PACKAGE_COMPACT.json")
record_id = "confirm_synth_116013_512"
archive_path = RELEASE / "compact_development/arrays" / (record_id + ".npz")
development_path = RELEASE / "compact_development/report.json"
development = read(development_path)
record = next(row for row in development["rows"] if row["id"] == record_id)
assert record["group"] == "synthetic" and record["actual_chirps"] == 512
package_paths = ["compact_development/report.json", "compact_experiment.py", "compact_release.py",
                 "examples_compact/diagnosed_512_power.npy", "examples_compact/diagnosed_512_expected.npz"]
package_match = all(sha(RELEASE / name) == package["files"][name] for name in package_paths)
with np.load(archive_path, allow_pickle=False) as arrays:
    ref, base, enhanced, gain, previous_power, previous_gain = [arrays[name] for name in [
        "reference", "base", "enhanced", "gain", "previous_power", "previous_gain"]]
example_base = np.load(RELEASE / "examples_compact/diagnosed_512_power.npy", allow_pickle=False)
with np.load(RELEASE / "examples_compact/diagnosed_512_expected.npz", allow_pickle=False) as arrays:
    example_enhanced, example_gain = arrays["power"], arrays["gain_q14"]
paired_match = np.array_equal(base, example_base) and np.array_equal(enhanced, example_enhanced)
paired_match &= np.array_equal(gain, example_gain)
g_base, g_ref = int(base.max()), int(ref.max())
assert g_base > 0 and g_ref > 0


def stage(power, gain_q14, reference):
    # Reconstruct only a scalar power from an ALREADY SAVED scalar gain.
    output = min((1 << 64) - 1, (int(power) * int(gain_q14) ** 2 + (1 << 27)) >> 28)
    x = math.sqrt(int(power) / g_base)
    amplitude = math.sqrt(output / g_base)
    ideal = x * int(gain_q14) / 16384
    return dict(gain_q14=int(gain_q14), gain=int(gain_q14) / 16384,
                reconstructed_power=output, relative_amplitude=amplitude,
                ideal_amplitude_without_output_rounding=ideal,
                absolute_error=abs(amplitude - reference), squared_error=(amplitude - reference) ** 2)


rows = []
trace_match = condition_match = first_gain_match = True
for saved in trace["rows"]:
    q = (saved["natural_range_bin"], saved["natural_doppler_bin"])
    power = int(base[q])
    x, y = math.sqrt(power / g_base), math.sqrt(int(ref[q]) / g_ref)
    stages = dict(bypass=stage(power, 16384, y),
                  mlp=stage(power, saved["raw_gain_q14"], y),
                  first_guard=stage(power, saved["first_guard_gain_q14"], y),
                  compact=stage(power, saved["final_gain_q14"], y))
    trace_match &= power == saved["power"]
    trace_match &= stages["compact"]["reconstructed_power"] == int(enhanced[q]) == saved["output_power"]
    trace_match &= int(gain[q]) == saved["final_gain_q14"]
    first_gain_match &= int(previous_gain[q]) == saved["first_guard_gain_q14"]
    first_gain_match &= int(previous_power[q]) == stages["first_guard"]["reconstructed_power"]
    oracle = y / x
    for label, item in stages.items():
        g = item["gain"]
        expected_improvement = oracle < (g + 1) / 2 if g < 1 else oracle > (g + 1) / 2 if g > 1 else False
        ideal_before = (x - y) ** 2
        ideal_after = (item["ideal_amplitude_without_output_rounding"] - y) ** 2
        condition_match &= (ideal_after < ideal_before) == expected_improvement
        item["ideal_squared_error_improves_bypass"] = ideal_after < ideal_before
    matching_labels = [t["kind"] for t in record["targets"] if t["measured_peak_bin"] == list(q)]
    rows.append(dict(position=list(q), reference_power=int(ref[q]), input_power=power,
                     input_relative_amplitude=x, reference_relative_amplitude=y,
                     reference_to_input_ratio=oracle, known_reference_bounded_gain=max(.125, min(1.5, oracle)),
                     stages=stages, exact_selected_synthetic_target_labels=matching_labels,
                     physical_target_label_inferred=False))

target_rows = []
target_record_match = True
for position in [(221, 205), (416, 1)]:
    target = next(t for t in record["targets"] if t["measured_peak_bin"] == list(position))
    previous_target = next(t for t in record["previous_v2"]["targets"]
                           if t["measured_peak_bin"] == list(position))
    power = int(base[position])
    x = math.sqrt(power / g_base)
    y = math.sqrt(int(ref[position]) / g_ref)
    stages = dict(bypass=stage(power, 16384, y),
                  first_guard=stage(power, int(previous_gain[position]), y),
                  compact=stage(power, int(gain[position]), y))
    target_record_match &= same(x, target["baseline"]) and same(y, target["reference"])
    target_record_match &= same(stages["compact"]["relative_amplitude"], target["enhanced"])
    target_record_match &= same(stages["first_guard"]["relative_amplitude"], previous_target["enhanced"])
    target_record_match &= stages["first_guard"]["reconstructed_power"] == int(previous_power[position])
    target_record_match &= stages["compact"]["reconstructed_power"] == int(enhanced[position])
    target_rows.append(dict(position=list(position), synthetic_kind=target["kind"],
                            input_relative_amplitude=x, reference_relative_amplitude=y,
                            stages=stages,
                            first_retention=stages["first_guard"]["relative_amplitude"] / y,
                            compact_retention=stages["compact"]["relative_amplitude"] / y,
                            raw_mlp_gain_not_evaluated=True, physical_target_label_inferred=False))

checks = dict(
    existing_release_file_hashes_match=package_match,
    trace_example_and_original_paired_archive_match=bool(paired_match),
    same_existing_synthetic_development_record=record["group"] == "synthetic",
    four_saved_point_gains_and_final_powers_match=bool(trace_match),
    saved_previous_stage_matches_first_guard=bool(first_gain_match),
    pointwise_error_conditions_match_known_reference=bool(condition_match),
    two_known_synthetic_target_rows_match_existing_report=bool(target_record_match),
    attenuation_example_reduces_reference_error=rows[1]["stages"]["compact"]["absolute_error"] < rows[1]["stages"]["bypass"]["absolute_error"],
    first_protection_example_reduces_mlp_error=rows[2]["stages"]["first_guard"]["absolute_error"] < rows[2]["stages"]["mlp"]["absolute_error"],
    compact_can_revoke_useful_mlp_attenuation=rows[3]["stages"]["compact"]["absolute_error"] > rows[3]["stages"]["mlp"]["absolute_error"],
    known_weak_peak_returns_to_bypass_but_not_reference=same(target_rows[0]["compact_retention"], .5912711111156014),
    known_collision_target_can_benefit_from_attenuation=target_rows[1]["stages"]["compact"]["absolute_error"] < target_rows[1]["stages"]["bypass"]["absolute_error"],
    frozen_sources_unchanged=not changed,
)
sources = ["network_understanding_v1/reports/POINT_TRACE.json",
           "scalar_restore_v3/compact_development/arrays/confirm_synth_116013_512.npz",
           "scalar_restore_v3/compact_development/report.json", "scalar_restore_v3/compact_experiment.py",
           "scalar_restore_v3/compact_release.py", "scalar_restore_v3/RUNTIME_PACKAGE_COMPACT.json",
           "scalar_restore_v3/examples_compact/diagnosed_512_power.npy",
           "scalar_restore_v3/examples_compact/diagnosed_512_expected.npz"]
result = dict(status="PASS" if all(checks.values()) else "FAIL", checks=checks,
              scope="Reference interpretation of an already diagnosed synthetic development frame, not a new quality experiment",
              record_id=record_id, prior_split=record["split"], input_peak_power=g_base,
              reference_peak_power=g_ref, point_rows=rows, known_synthetic_target_rows=target_rows,
              normalization="Reference uses its own peak; all prediction stages use the SAME input peak",
              original_quality_status_preserved="FAIL",
              source_sha256={name: sha(ROOT / name) for name in sources},
              script_sha256=sha(Path(__file__)), frozen_files_checked=len(baseline), changed_sources=changed,
              existing_saved_point_reference_comparison_run=True, scalar_power_arithmetic_run=True,
              model_instantiated=False, neural_layer_run=False, neural_inference_run=False,
              model_parameters_modified=False, training_run=False, radar_fft_run=False,
              feature_extraction_run=False, guard_run=False, new_quality_test_run=False,
              new_holdout_opened=False, new_dataset_generated=False, hardware_built=False, board_accessed=False)
(HERE / "reports/POINT_REFERENCE_WALKTHROUGH.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
print(json.dumps(dict(status=result["status"], checks=checks,
                      points=[dict(position=r["position"], x=r["input_relative_amplitude"],
                                   y=r["reference_relative_amplitude"],
                                   stage_amplitudes={k: v["relative_amplitude"] for k, v in r["stages"].items()})
                              for r in rows], known_targets=target_rows), ensure_ascii=False))
if result["status"] != "PASS":
    raise SystemExit(1)
