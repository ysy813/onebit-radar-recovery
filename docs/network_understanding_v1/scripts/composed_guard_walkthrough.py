"""Real-valued sequential gain-map algebra, with saved-point context only."""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
import math
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
changed = [p for p, info in baseline.items() if sha(ROOT / p) != info["sha256"]]
assert not changed, changed
config = read(ROOT / "scalar_restore_v3/pc_candidate_compact/config.json")
assert config["power_guard"]["soft_band_q14"] == [4096, 8192]


def tau(g):
    return max(F(0), min(F(1), 4 * g - 1))


def original_lift(g):
    return g + max(1 - g, 0) * tau(g)


def piecewise_lift(g):
    if g <= F(1, 4) or g >= 1:
        return g
    if g < F(1, 2):
        return -1 + 6 * g - 4 * g * g
    return F(1)


gains = [F(1, 8), F(1, 5), F(1, 4), F(13, 50), F(3, 10), F(5, 16),
         F(8, 25), F(2, 5), F(1, 2), F(7, 10), F(1), F(5, 4), F(3, 2)]
compactness = [F(0), F(1, 4), F(1, 2), F(3, 4), F(1)]
cases = 0
formulas_match = bounds_match = gain_monotonic = True
table = []
for c in compactness:
    previous = F(0)
    for g in gains:
        g1 = original_lift(g)
        g2 = g1 + max(1 - g1, 0) * c * tau(g1)
        alternative = (1 - c) * g1 + c * piecewise_lift(g1)
        formulas_match &= g1 == piecewise_lift(g) and g2 == alternative
        bounds_match &= g <= g1 <= max(F(1), g) and g1 <= g2 <= max(F(1), g)
        gain_monotonic &= g2 >= previous
        previous = g2
        cases += 1
        if c == 1:
            table.append(dict(raw_gain=float(g), first=float(g1), second=float(g2)))

# Full compactness gives q(q(g)). Below the saturation threshold this is a
# quartic; compare it independently to the composed original expression.
quartic_cases = 0
quartic_match = True
for g in [F(1, 4), F(13, 50), F(11, 40), F(3, 10), F(5, 16)]:
    composed = original_lift(original_lift(g))
    polynomial = -11 + 84 * g - 200 * g ** 2 + 192 * g ** 3 - 64 * g ** 4
    quartic_match &= composed == polynomial
    quartic_cases += 1
threshold = (3 - math.sqrt(3)) / 4
bracket_lo, bracket_hi = F(316987, 1000000), F(316988, 1000000)
root_bracket = original_lift(bracket_lo) < F(1, 2) < original_lift(bracket_hi)
root_equation_error = abs(4 * threshold ** 2 - 6 * threshold + 1.5)
single_right_slope = F(6) - 8 * F(1, 4)
double_right_slope = F(84) - 400 * F(1, 4) + 576 * F(1, 4) ** 2 - 256 * F(1, 4) ** 3

trace = read(HERE / "reports/POINT_TRACE.json")
saved = next(r for r in trace["rows"]
             if (r["natural_range_bin"], r["natural_doppler_bin"]) == (200, 148))
g0 = F(saved["raw_gain_q14"], 16384)
g1_ideal = original_lift(g0)
g2_ideal = original_lift(g1_ideal)
z, mean9 = [F(saved["feature_q16"][i], 65536) for i in [0, 3]]
c_saved = max(F(0), min(F(1), 5 * z / max(mean9, F(1, 32)) - 7))
saved_first = F(saved["first_guard_gain_q14"], 16384)
saved_final = F(saved["final_gain_q14"], 16384)
saved_point = dict(position=[200, 148], raw_gain=float(g0),
                   conceptual_first=float(g1_ideal), saved_first=float(saved_first),
                   conceptual_second=float(g2_ideal), saved_second=float(saved_final),
                   compactness_from_saved_features=float(c_saved),
                   full_input_guard_functions_executed=False)
checks = dict(
    piecewise_and_convex_composition_match_exact=formulas_match,
    qualifying_gain_paths_stay_between_raw_and_unity=bounds_match,
    fixed_compactness_maps_monotone_in_gain=gain_monotonic,
    composed_quartic_matches_exact=quartic_match,
    saturation_threshold_root_verified=root_bracket and root_equation_error < 1e-14,
    right_slope_limits_four_and_sixteen=single_right_slope == 4 and double_right_slope == 16,
    second_application_not_generally_redundant=original_lift(original_lift(F(3, 10))) != original_lift(F(3, 10)),
    saved_point_full_compactness_matches=c_saved == 1,
    saved_point_formula_explains_record=g2_ideal == saved_final == 1 and abs(g1_ideal - saved_first) < F(1, 32768),
    original_quality_fail_preserved=config["quality_test_status"] == "FAIL",
    frozen_sources_unchanged=not changed,
)
sources = ["scalar_restore_v3/pc_candidate_compact/config.json",
           "scalar_restore_v3/pc_candidate_compact/scalar_guard.py",
           "scalar_restore_v3/pc_candidate_compact/compact_guard.py",
           "network_understanding_v1/reports/POINT_TRACE.json"]
result = dict(status="PASS" if all(checks.values()) else "FAIL", checks=checks,
              scope="Conditional real-valued gain-map mathematics; not model quality or actual guard-mask inference",
              fixed_mask_and_compactness_cases=cases, quartic_cases=quartic_cases,
              full_compactness_table=table, full_restore_raw_gain_threshold=threshold,
              full_restore_raw_gain_interval=[threshold, 1.0],
              threshold_applies_only_if_both_masks_and_full_compactness_hold=True,
              threshold_is_not_a_target_probability=True,
              one_layer_right_slope_limit=float(single_right_slope),
              two_layer_right_slope_limit=float(double_right_slope),
              saved_point=saved_point,
              qualifications=["512 valid-chirp path; the compact mask is a subset of the first mask",
                              "Full return threshold concerns raw attenuation gains at most one; gains above one are unchanged",
                              "Input masks and compactness are fixed while studying variation of raw gain",
                              "Real-valued threshold is not an asserted exact integer threshold",
                              "Continuity of this gain path does not imply continuity of the full input-dependent algorithm",
                              "Local gain sensitivity is not an SNR or noise-amplification measurement",
                              "No training conclusion or universal target-preservation guarantee"],
              source_sha256={name: sha(ROOT / name) for name in sources},
              script_sha256=sha(Path(__file__)), frozen_files_checked=len(baseline), changed_sources=changed,
              constructed_gain_map_algebra_run=True, model_instantiated=False,
              model_parameters_modified=False, training_run=False, radar_fft_run=False,
              feature_extraction_run=False, neural_inference_run=False,
              full_guard_run=False, new_quality_test_run=False, new_holdout_opened=False,
              hardware_built=False, board_accessed=False)
(HERE / "reports/COMPOSED_GUARD_WALKTHROUGH.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
print(json.dumps(dict(status=result["status"], checks=checks,
                      fixed_cases=cases, full_compactness_table=table,
                      threshold=threshold, saved_point=saved_point), ensure_ascii=False))
if result["status"] != "PASS":
    raise SystemExit(1)
