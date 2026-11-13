"""Reference-informed range relaxation of one saved diagnostic frame; no inference."""
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

baseline = read(HERE/"reports/SOURCE_BASELINE.json")
changed = [p for p, info in baseline.items() if sha(ROOT/p) != info["sha256"]]
record_id = "confirm_synth_116013_512"
array_relative = f"scalar_restore_v3/compact_development/arrays/{record_id}.npz"
prior = read(HERE/"reports/POINT_REFERENCE_WALKTHROUGH.json")
assert sha(ROOT/array_relative) == prior["source_sha256"][array_relative]
with np.load(ROOT/array_relative, allow_pickle=False) as data:
    reference, base, enhanced, gain = [data[k] for k in ("reference", "base", "enhanced", "gain")]
x = np.sqrt(base.astype("f8")/int(base.max()))
y = np.sqrt(reference.astype("f8")/int(reference.max()))
current = x*gain.astype("f8")/16384
saved = np.sqrt(enhanced.astype("f8")/int(base.max()))
lower, upper = .125*x, 1.5*x
oracle = np.clip(y, lower, upper)

def sse(amplitude, mask=None):
    error = (amplitude-y)**2
    return float(error.sum() if mask is None else error[mask].sum())

masks = {
    "reference_below_minimum": y < lower,
    "reference_above_maximum": y > upper,
    "reference_within_interval": (y >= lower) & (y <= upper),
}
regions = [dict(region=name, pixels=int(mask.sum()), oracle_sse=sse(oracle, mask),
                current_ideal_sse=sse(current, mask)) for name, mask in masks.items()]
reference_energy = float(np.sum(y*y))
current_sse, oracle_sse = sse(current), sse(oracle)
distance = float(np.sum((current-oracle)**2))
cross = float(2*np.sum((current-oracle)*(oracle-y)))
checks = dict(
    same_previously_diagnosed_record=prior["record_id"] == record_id,
    frame_shape_matches=base.shape == reference.shape == enhanced.shape == gain.shape == (1024,512),
    all_values_finite=bool(all(np.all(np.isfinite(a)) for a in (x,y,current,saved,oracle))),
    saved_gains_in_frozen_interval=int(gain.min()) >= 2048 and int(gain.max()) <= 24576,
    regions_are_a_partition=bool(np.all(sum(mask.astype("u1") for mask in masks.values()) == 1)),
    oracle_is_reachable_pointwise=bool(np.all((oracle >= lower) & (oracle <= upper))),
    current_is_reachable_pointwise=bool(np.all((current >= lower) & (current <= upper))),
    oracle_no_worse_than_current_or_bypass=oracle_sse <= min(current_sse,sse(x)),
    oracle_zero_error_within_interval=regions[2]["oracle_sse"] == 0,
    boundary_cross_terms_nonnegative=bool(np.all(2*(current-oracle)*(oracle-y) >= -1e-18)),
    projection_identity_matches=bool(np.isclose(oracle_sse+distance+cross,current_sse,rtol=1e-13,atol=1e-15)),
    partition_totals_match=bool(np.isclose(sum(r["oracle_sse"] for r in regions),oracle_sse,rtol=1e-13)
                              and np.isclose(sum(r["current_ideal_sse"] for r in regions),current_sse,rtol=1e-13)),
    frozen_sources_unchanged=not changed,
)
sources = [array_relative, "network_understanding_v1/reports/POINT_REFERENCE_WALKTHROUGH.json",
           "scalar_restore_v3/pc_candidate_compact/config.json"]
result = dict(
    status="PASS" if all(checks.values()) else "FAIL", checks=checks, record_id=record_id,
    scope="Reference-informed pointwise continuous-gain relaxation of an old synthetic development record, not new network performance",
    normalization="Reference uses its own peak; bypass, saved output, and ideal multiplication share the input peak",
    amplitude_gain_interval=[.125,1.5], reference_energy=reference_energy,
    bypass_sse=sse(x), current_ideal_sse=current_sse, current_saved_power_sse=sse(saved),
    oracle_sse=oracle_sse, oracle_to_current_ideal_sse=oracle_sse/current_sse,
    bypass_nmse=sse(x)/reference_energy, current_ideal_nmse=current_sse/reference_energy,
    oracle_nmse=oracle_sse/reference_energy, regions=regions,
    projection_identity=dict(oracle_floor=oracle_sse, squared_distance_to_oracle=distance,
                             boundary_cross_term=cross, reconstructed_current_sse=oracle_sse+distance+cross),
    qualifications=[
        "Oracle uses the unavailable reference and independently selects every continuous gain",
        "It relaxes shared parameters, feature ambiguity, composite training loss, fixed guards, and discrete gain constraints",
        "The ratio is not a causal attribution or an achievable improvement estimate",
        "It does not estimate the conditional Bayes risk or identify causes of the remaining error",
        "Saved-power error is listed separately from ideal multiplication to avoid calling the relaxation bit-exact",
        "This old synthetic development record does not establish generalization or new quality approval",
    ],
    source_sha256={p:sha(ROOT/p) for p in sources}, script_sha256=sha(Path(__file__)),
    frozen_files_checked=len(baseline), changed_sources=changed,
    original_full_quality_status_preserved="FAIL", saved_frame_reference_relaxation_run=True,
    model_instantiated=False, neural_inference_run=False, feature_extraction_run=False,
    guard_run=False, radar_fft_run=False, training_run=False, model_parameters_modified=False,
    new_quality_test_run=False, new_holdout_opened=False, hardware_built=False, board_accessed=False)
(HERE/"reports/BOUNDED_ORACLE_WALKTHROUGH.json").write_text(
    json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
print(json.dumps({k:result[k] for k in ("status","checks","bypass_sse","current_ideal_sse",
                  "oracle_sse","oracle_to_current_ideal_sse","regions","projection_identity")},ensure_ascii=False))
if result["status"] != "PASS":
    raise SystemExit(1)
