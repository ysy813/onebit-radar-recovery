"""Check fixed 32-to-40 feature expansion only; no neural layer is executed."""
import sys
sys.dont_write_bytecode = True
import ast
import copy
import hashlib
import json
from fractions import Fraction as F
from pathlib import Path
import numpy as np
import torch

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
MODEL = ROOT / "scalar_restore_v3/pc_candidate_compact"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


baseline = read(HERE / "reports/SOURCE_BASELINE.json")
changed = [name for name, info in baseline.items()
           if sha(ROOT / name) != info["sha256"]]
assert not changed, changed

# Execute ONLY the unmodified augment method on specified numeric vectors.
# No ScalarCorrector instance, Linear module, weights, or optimizer is used.
model_tree = ast.parse((MODEL / "model_source.py").read_text(encoding="utf-8"))
model_class = next(n for n in model_tree.body
                   if isinstance(n, ast.ClassDef) and n.name == "ScalarCorrector")
augment = next(n for n in model_class.body
               if isinstance(n, ast.FunctionDef) and n.name == "augment")
float_ns = {"torch": torch}
exec(compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(augment)],
                                                  type_ignores=[])),
             "<read-only augment extraction>", "exec"), float_ns)

# Extract only the pre-layer expansion from the integer reference. In
# particular, stop before its `for i,(w,b) in enumerate(self.layers)` loop.
runtime_tree = ast.parse((MODEL / "restore_power.py").read_text(encoding="utf-8"))
runtime_class = next(n for n in runtime_tree.body
                     if isinstance(n, ast.ClassDef) and n.name == "PowerRestorer")
predict = next(n for n in runtime_class.body
               if isinstance(n, ast.FunctionDef) and n.name == "predict_gain_q14")
helpers = [copy.deepcopy(n) for n in predict.body
           if isinstance(n, ast.FunctionDef)]
chunk = next(n for n in predict.body if isinstance(n, ast.For))
layer_index = next(i for i, n in enumerate(chunk.body) if isinstance(n, ast.For))
prefix = copy.deepcopy(chunk.body[:layer_index])
assert [ast.unparse(n.targets[0]) for n in prefix if isinstance(n, ast.Assign)] == [
    "stop", "z", "v", "z"]
prefix = prefix[1:]  # stop is supplied below; the other three nodes are intact.
body = helpers + ast.parse("start=0\nstop=f.shape[1]").body + prefix
body += ast.parse("return z").body
fn = ast.FunctionDef(name="expand_runtime_only", args=ast.arguments(
    posonlyargs=[], args=[ast.arg(arg="f")], kwonlyargs=[], kw_defaults=[], defaults=[]),
    body=body, decorator_list=[])
assert not any(isinstance(n, ast.Name) and n.id == "self" for n in ast.walk(fn))
integer_ns = {"np": np}
exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])),
             "<read-only integer expansion extraction>", "exec"), integer_ns)

vectors = [np.zeros(32, dtype="i8"), np.full(32, 4096, dtype="i8"),
           np.arange(32, dtype="i8") * 128, 4096 - np.arange(32, dtype="i8") * 128]
vectors += [np.array([(337 * j + 701 * seed) % 4097 for j in range(32)], dtype="i8")
            for seed in range(8)]
constructed_count = len(vectors)
traces = read(HERE / "reports/POINT_TRACE.json")["rows"]
for row in traces:
    full = np.array(row["feature_q16"], dtype="i8")
    preserved = np.concatenate([full[:8], full[16:]])
    assert np.all(preserved % 16 == 0)
    vectors.append(preserved // 16)
base_q12 = np.stack(vectors)
integer_features = integer_ns["expand_runtime_only"](base_q12.T)
with torch.no_grad():
    float_features = float_ns["augment"](None, torch.tensor(
        base_q12 / 4096.0, dtype=torch.float64)).numpy()


def independent_integer_expansion(row):
    z = [int(v) * 16 for v in row]

    def pow5(v):
        out = v
        for _ in range(4):
            out = (out * v + 32768) // 65536
        return out

    a = [pow5(z[i]) for i in [0, 4, 5, 6, 7]]
    extra = a + [max(-65536, min(65536, 3 * a[0] - a[1])),
                 max(-65536, min(65536, 5 * a[0] - a[2])),
                 a[0] - pow5(z[2])]
    return z[:8] + extra + z[8:]


def independent_rational_expansion(row):
    z = [F(int(v), 4096) for v in row]
    a = [z[i] ** 5 for i in [0, 4, 5, 6, 7]]
    extra = a + [max(F(-1), min(F(1), 3 * a[0] - a[1])),
                 max(F(-1), min(F(1), 5 * a[0] - a[2])),
                 a[0] - z[2] ** 5]
    return z[:8] + extra + z[8:]


independent_integer = np.array([independent_integer_expansion(v) for v in vectors], dtype="i8")
independent_float = np.array([[float(v) for v in independent_rational_expansion(row)]
                              for row in vectors])
float_preserved = np.concatenate([float_features[:, :8], float_features[:, 16:]], axis=1)
integer_preserved = np.concatenate([integer_features[:, :8], integer_features[:, 16:]], axis=1)
trace_match = all(np.array_equal(integer_features[constructed_count + i], row["feature_q16"])
                  for i, row in enumerate(traces))

# A single affine map of the raw center encoding cannot exactly provide z^5
# over its interval: these three exact dyadic points have nonzero second difference.
raw_z = [F(0), F(1, 4), F(1, 2)]
derived = [v ** 5 for v in raw_z]
second_difference = derived[0] - 2 * derived[1] + derived[2]
float_error = float(np.max(np.abs(float_features - independent_float)))
checks = dict(
    float_augmented_shape=float_features.shape == (16, 40),
    integer_augmented_shape=integer_features.shape == (16, 40),
    all_base_channels_preserved_float=np.array_equal(float_preserved, base_q12 / 4096.0),
    all_base_channels_recoverable_integer=np.array_equal(integer_preserved // 16, base_q12),
    integer_base_channels_exact_multiples=np.all(integer_preserved % 16 == 0).item(),
    float_expansion_matches_exact_rational_formula=float_error < 2e-15,
    integer_expansion_matches_independent_rounding=np.array_equal(integer_features, independent_integer),
    four_existing_full_vectors_reproduced=trace_match,
    derived_basis_is_not_an_affine_copy=second_difference == F(15, 512),
    original_quality_fail_preserved=read(MODEL / "config.json")["quality_test_status"] == "FAIL",
    frozen_sources_unchanged=not changed,
)
checks = {name: bool(v) for name, v in checks.items()}
sources = ["scalar_restore_v3/pc_candidate_compact/model_source.py",
           "scalar_restore_v3/pc_candidate_compact/restore_power.py",
           "scalar_restore_v3/pc_candidate_compact/config.json",
           "network_understanding_v1/reports/POINT_TRACE.json"]
report = dict(status="PASS" if all(checks.values()) else "FAIL", checks=checks,
              scope="Fixed feature expansion on specified vectors and four existing saved vectors only",
              constructed_vectors=constructed_count, existing_vectors=len(traces),
              expansion_vectors=len(vectors), output_channels=40,
              retained_base_channels=list(range(8)) + list(range(16, 40)),
              derived_channels=list(range(8, 16)),
              maximum_float_formula_error=float_error,
              nonaffine_example=dict(center_encodings=[str(v) for v in raw_z],
                                      fifth_powers=[str(v) for v in derived],
                                      second_difference=str(second_difference)),
              qualifications=["Specified vectors are not newly extracted real-frame features",
                              "Retaining all 32 inputs makes this augmentation lossless relative to its base vector",
                              "Expansion adds nonlinear representation, not new radar observations",
                              "No theorem here proves a gain in final quality or optimal hidden width",
                              "Training float expansion and runtime integer expansion include different rounding semantics"],
              source_sha256={name: sha(ROOT / name) for name in sources},
              script_sha256=sha(Path(__file__)),
              frozen_files_checked=len(baseline), changed_sources=changed,
              constructed_feature_augmentation_run=True, model_instantiated=False,
              neural_layer_run=False, model_backward_run=False, model_parameters_modified=False,
              training_run=False, radar_fft_run=False, full_feature_extraction_run=False,
              neural_inference_run=False, new_quality_test_run=False, new_holdout_opened=False,
              hardware_built=False, board_accessed=False)
(HERE / "reports/FEATURE_EXPANSION_WALKTHROUGH.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
print(json.dumps(dict(status=report["status"], checks=checks,
                      constructed_vectors=constructed_count, existing_vectors=len(traces),
                      maximum_float_formula_error=float_error,
                      nonaffine_example=report["nonaffine_example"]), ensure_ascii=False))
if report["status"] != "PASS":
    raise SystemExit(1)
