"""Child-feature coordinates under circular shifts; constructed fields only."""
import sys
sys.dont_write_bytecode = True
import ast
import hashlib
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
SOURCE = ROOT / "scalar_restore_v3/pc_candidate_compact/model_source.py"

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
config = read(ROOT / "scalar_restore_v3/pc_candidate_compact/config.json")
assert config["feature_policy"] == "guarded_child" and config["context"] == 2
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "features_for_policy")
environment = {}
exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])), str(SOURCE), "exec"), environment)
child_features = environment["features_for_policy"]

# This field is specified in Q12 encoding. It is NOT claimed to be an actual
# quantized I/Q FFT or a valid complete eight-channel feature tensor.
shape = (1024, 512)
origin = (131, 37)
z = np.zeros(shape, dtype="u2")
z[origin] = 4096
children = {h: ((h*origin[0]) % shape[0], (h*origin[1]) % shape[1]) for h in [-3, 5]}
z[children[-3]] = 2048
z[children[5]] = 1600

def compute_child_planes(encoded):
    f = np.zeros((8, encoded.size), dtype="u2")
    f[0] = encoded.ravel()
    # Context adds other channels; the two child planes do not depend on it.
    return child_features(f, "guarded_child", context=0)[6:8].reshape(2, *shape)

base = compute_child_planes(z)
shifts = [(0,0), (1,0), (10,0), (0,1), (256,0), (512,0),
          (0,128), (0,256), (256,128), (512,256)]
rows = []
for delta in shifts:
    observed = compute_child_planes(np.roll(z, delta, axis=(0,1)))
    rolled = np.roll(base, delta, axis=(1,2))
    point = tuple((origin[a] + delta[a]) % shape[a] for a in range(2))
    expected_identity = all((4*delta[a]) % shape[a] == 0 for a in range(2))
    differences = [int(np.count_nonzero(observed[j] != rolled[j])) for j in range(2)]
    rows.append(dict(circular_shift=list(delta), shifted_source=list(point),
                     index_identity_for_both_orders=expected_identity,
                     different_pixels_by_order=dict(zip(["minus3","plus5"], differences)),
                     child_values_at_shifted_source=observed[:,point[0],point[1]].tolist(),
                     shifted_original_child_values=rolled[:,point[0],point[1]].tolist()))

axes = []
for length in shape:
    allowed = {h: [d for d in range(length) if ((h-1)*d) % length == 0] for h in [-3,5]}
    axes.append(dict(length=length, shifts_by_order={str(h):v for h,v in allowed.items()},
                     same_allowed_shifts=allowed[-3] == allowed[5],
                     expected_quarter_shifts=allowed[-3] == [0,length//4,length//2,3*length//4]))

shift_example = []
for h in [-3,5]:
    shifted_old = ((children[h][0]+10) % shape[0], children[h][1])
    expected_new = ((h*(origin[0]+10)) % shape[0], (h*origin[1]) % shape[1])
    shift_example.append(dict(order=h, original_child=list(children[h]),
                              original_child_moved_ten=list(shifted_old),
                              child_of_source_moved_ten=list(expected_new)))

checks = dict(
    selected_policy_matches=config["feature_policy"] == "guarded_child",
    specified_original_child_features=base[:,origin[0],origin[1]].tolist() == [2048,1600],
    special_shift_sets_are_quarters=all(a["same_allowed_shifts"] and a["expected_quarter_shifts"] for a in axes),
    constructed_special_shifts_commute=all(not any(r["different_pixels_by_order"].values()) for r in rows if r["index_identity_for_both_orders"]),
    constructed_generic_shifts_have_counterexamples=all(all(v>0 for v in r["different_pixels_by_order"].values()) for r in rows if not r["index_identity_for_both_orders"]),
    ten_bin_shift_breaks_both_child_hints=rows[2]["child_values_at_shifted_source"] == [0,0] and rows[2]["shifted_original_child_values"] == [2048,1600],
    fftshift_case_is_not_generic_failure=rows[-1]["index_identity_for_both_orders"] and not any(rows[-1]["different_pixels_by_order"].values()),
    frozen_sources_unchanged=not changed,
)
sources = ["scalar_restore_v3/pc_candidate_compact/model_source.py",
           "scalar_restore_v3/pc_candidate_compact/config.json"]
result = dict(status="PASS" if all(checks.values()) else "FAIL", checks=checks,
              scope="Source child-feature calculation on a specified encoded field and modular algebra; no end-to-end model equivariance or quality claim",
              original_source=list(origin), axes=axes, examples=rows, ten_bin_coordinate_example=shift_example,
              coordinate_condition="(h-1)*delta == 0 mod axis length, for h=-3 and h=5",
              qualifications=["No claim that an arbitrary encoded field is realizable as a sign-IQ FFT",
                              "Other base features are placeholders unused by the two child outputs",
                              "Feature differences do not prove a particular final gain changes",
                              "Special child-feature symmetries do not certify the full pipeline or change the input convention"],
              source_sha256={p:sha(ROOT/p) for p in sources}, script_sha256=sha(Path(__file__)),
              frozen_files_checked=len(baseline), changed_sources=changed,
              original_full_quality_status_preserved="FAIL", constructed_child_feature_run=True,
              radar_data_read=False, radar_fft_run=False, full_feature_extraction_run=False,
              model_instantiated=False, neural_inference_run=False, guard_run=False, training_run=False,
              model_parameters_modified=False, new_quality_test_run=False, new_holdout_opened=False,
              hardware_built=False, board_accessed=False)
(HERE/"reports/SPECTRAL_SHIFT_WALKTHROUGH.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
print(json.dumps(dict(status=result["status"],checks=checks,examples=rows,coordinates=shift_example),ensure_ascii=False))
if result["status"] != "PASS":
    raise SystemExit(1)
