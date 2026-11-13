"""Fixed-threshold accounting for an existing diagnostic output; no inference."""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
import math
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
point_reference = read(HERE/"reports/POINT_REFERENCE_WALKTHROUGH.json")
assert sha(ROOT/array_relative) == point_reference["source_sha256"][array_relative]
with np.load(ROOT/array_relative, allow_pickle=False) as data:
    ref, base, final, gain = [data[k] for k in ["reference","base","enhanced","gain"]]
peak = int(base.max())
reference_peak = int(ref.max())
x = np.sqrt(base.astype("f8")/peak)
y = np.sqrt(ref.astype("f8")/reference_peak)
output = np.sqrt(final.astype("f8")/peak)
cap = (1 << 64) - 1
expected = np.fromiter((min(cap, (int(p)*int(g)**2+(1<<27))>>28)
                        for p,g in zip(base.flat,gain.flat)), dtype="u8", count=base.size).reshape(base.shape)
no_saturation = ((peak*int(gain.max())**2+(1<<27))>>28) <= cap

# For this non-saturating saved frame, power rounding changes normalized
# amplitude by at most sqrt(0.5/peak). This is not a neural-error bound.
epsilon = math.sqrt(.5/peak)
rows = []
for threshold in [.003,.01,.03,.1]:
    before = x >= threshold
    after = output >= threshold
    reference_above = y >= threshold
    down, up = before & ~after, ~before & after
    rows.append(dict(threshold=threshold, reference_pixels=int(reference_above.sum()),
        bypass_pixels=int(before.sum()), enhanced_pixels=int(after.sum()),
        downward_crossings=int(down.sum()), upward_crossings=int(up.sum()),
        downward_crossings_reference_above=int((down & reference_above).sum()),
        upward_crossings_reference_below=int((up & ~reference_above).sum()),
        reference_above_but_enhanced_below=int((reference_above & ~after).sum()),
        enhanced_above_but_reference_below=int((after & ~reference_above).sum()),
        lower_inclusion_violations=int(np.count_nonzero((x>=8*(threshold+epsilon)) & ~after)),
        upper_inclusion_violations=int(np.count_nonzero(after & (x<max(0,(threshold-epsilon)/1.5))))))
example = dict(position=[774,511], input_relative_amplitude=float(x[774,511]),
               output_relative_amplitude=float(output[774,511]),
               reference_relative_amplitude=float(y[774,511]),
               final_gain=float(gain[774,511]/16384), output_power=int(final[774,511]),
               threshold=.03, crossed_down=bool(x[774,511]>=.03 and output[774,511]<.03),
               physical_label_inferred=False)
checks = dict(
    same_previously_diagnosed_record=point_reference["record_id"] == record_id,
    all_saved_power_values_match_gain_arithmetic=bool(np.array_equal(expected,final)),
    saved_gains_in_frozen_interval=int(gain.min())>=2048 and int(gain.max())<=24576,
    no_saturation_in_saved_frame=no_saturation,
    normalized_amplitude_rounding_bound=bool(np.all(np.abs(output-x*gain.astype("f8")/16384) <= epsilon)),
    four_threshold_accounts_balance=all(r["bypass_pixels"]-r["enhanced_pixels"] == r["downward_crossings"]-r["upward_crossings"] for r in rows),
    rounding_adjusted_set_inclusions_hold=all(r["lower_inclusion_violations"] == r["upper_inclusion_violations"] == 0 for r in rows),
    all_points_remain_nonzero=int(np.count_nonzero(base)) == int(np.count_nonzero(final)) == 524288,
    existing_point_crosses_threshold_without_zero=example["crossed_down"] and example["output_power"]>0,
    low_threshold_also_has_reference_above_losses=rows[0]["downward_crossings_reference_above"]>0,
    frozen_sources_unchanged=not changed,
)
sources = [array_relative, "network_understanding_v1/reports/POINT_REFERENCE_WALKTHROUGH.json",
           "scalar_restore_v3/pc_candidate_compact/config.json",
           "scalar_restore_v3/pc_candidate_compact/restore_power.py"]
result = dict(status="PASS" if all(checks.values()) else "FAIL", checks=checks,
              scope="Threshold accounting of one old synthetic development frame; not new model quality, display calibration, or detection evaluation",
              record_id=record_id, normalization="Reference uses its own peak; bypass and output share the input peak",
              thresholds=rows, input_nonzero=int(np.count_nonzero(base)), output_nonzero=int(np.count_nonzero(final)),
              amplitude_rounding_tolerance=epsilon, existing_point=example,
              ideal_amplitude_set_inclusions="{X>=8T} subset {Aout>=T} subset {X>=2T/3}; exact real arithmetic only",
              qualifications=["Counts are spectral pixels, not targets or independent detections",
                              "Reference-above-threshold is a numerical set, not physical target labels",
                              "Thresholds are specified amplitude cuts, not an assertion about the monitor transfer function",
                              "The saved record has already been used for development and diagnosis",
                              "No adaptive detection threshold or CFAR performance is evaluated"],
              source_sha256={p:sha(ROOT/p) for p in sources}, script_sha256=sha(Path(__file__)),
              frozen_files_checked=len(baseline), changed_sources=changed,
              original_full_quality_status_preserved="FAIL", saved_frame_threshold_accounting_run=True,
              scalar_power_arithmetic_run=True, model_instantiated=False, neural_inference_run=False,
              feature_extraction_run=False, guard_run=False, radar_fft_run=False, training_run=False,
              model_parameters_modified=False, new_quality_test_run=False, new_holdout_opened=False,
              hardware_built=False, board_accessed=False)
(HERE/"reports/SAVED_THRESHOLD_WALKTHROUGH.json").write_text(
    json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
print(json.dumps(dict(status=result["status"],checks=checks,thresholds=rows,existing_point=example,
                      amplitude_rounding_tolerance=epsilon),ensure_ascii=False))
if result["status"] != "PASS":
    raise SystemExit(1)
