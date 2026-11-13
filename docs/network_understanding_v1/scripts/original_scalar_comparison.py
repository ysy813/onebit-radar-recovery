"""Compare frozen output-head algebra, without running either neural network."""
import sys
sys.dont_write_bytecode = True
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
WRAPPER = ROOT/'cdqob_pc_online_v1/model.py'
LEGACY = ROOT/'cdqob_pc_online_v1/reference/AoDnet.py'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4*1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


baseline = read(HERE/'reports/SOURCE_BASELINE.json')
changed = [path for path, info in baseline.items() if sha(ROOT/path) != info['sha256']]
assert not changed, changed
wrapper_tree = ast.parse(WRAPPER.read_text(encoding='utf-8'))
wrapper_class = next(n for n in wrapper_tree.body if isinstance(n, ast.ClassDef) and n.name=='CDQOB')
forward = next(n for n in wrapper_class.body if isinstance(n, ast.FunctionDef) and n.name=='forward')
wrapper_return = next(n for n in forward.body if isinstance(n, ast.Return))
wrapper_code = compile(ast.Expression(wrapper_return.value), str(WRAPPER), 'eval')
legacy_tree = ast.parse(LEGACY.read_text(encoding='utf-8'))
legacy_class = next(n for n in legacy_tree.body if isinstance(n, ast.ClassDef) and n.name=='AodModel')
legacy_call = next(n for n in legacy_class.body if isinstance(n, ast.FunctionDef) and n.name=='call')
legacy_jj = next(n for n in legacy_call.body if isinstance(n, ast.Assign) and any(
    isinstance(t, ast.Name) and t.id=='jj' for t in n.targets))
legacy_code = compile(ast.Expression(legacy_jj.value), str(LEGACY), 'eval')
tf_stub = SimpleNamespace(clip_by_value=np.clip, math=SimpleNamespace(multiply=np.multiply))


def source_head(inputs, h):
    env = dict(tf=tf_stub, inputs=np.asarray(inputs), h=np.asarray(h))
    return eval(wrapper_code, {'__builtins__':{}}, env)


inputs = np.linspace(0,1,1001)[:,None]
h = np.array([0.,.5,1.,1.25,2.,4.])[None,:]
wrapper_values = source_head(inputs, h)
legacy_values = np.clip(eval(legacy_code, {'__builtins__':{}}, dict(tf=tf_stub,inputs=inputs,h=h)),0,1)
rewritten = np.clip(1-h*(1-inputs),0,1)
residual_form = np.clip(inputs+(1-h)*(1-inputs),0,1)
examples = []
for value, coefficient in [(0.,.5),(.2,.5),(.2,1.),(.2,1.25),(.8,.5),(1.,4.)]:
    output = float(source_head(value,coefficient))
    examples.append(dict(input_channel=value, coefficient_h=coefficient, output_channel=output,
                         effective_ratio_if_nonzero=output/value if value else None,
                         scope='Constructed output-head arithmetic; h not predicted by the author network'))

gray_input = np.array([.4,.4,.4])
gray_h = np.array([1.,.5,1.5])
gray_output = source_head(gray_input,gray_h)
off_curve = dict(scope='Toy known grayscale encoding C(a)=(a,a,a), not a claim about the author colormap or learned output',
                 scalar_input=.4, rgb_input=gray_input.tolist(), constructed_h=gray_h.tolist(),
                 resulting_rgb=gray_output.tolist(),
                 has_exact_scalar_preimage_on_toy_curve=bool(np.allclose(gray_output,gray_output[0])))

# A known inverse may exist for a chosen continuous encoding, while 8-bit
# rounding alone can make nearby scalar values indistinguishable.
continuous_amplitudes=np.array([.2,.2001])
rgb_uint8=np.rint(255*continuous_amplitudes).astype('u1')
quantization_example=dict(scope='Toy grayscale display rounding only; no author preprocessing inferred',
    two_distinct_relative_amplitudes=continuous_amplitudes.tolist(),
    uint8_gray_values=rgb_uint8.tolist(),
    same_display_value=bool(rgb_uint8[0]==rgb_uint8[1]))

counterexamples = dict(
    nonzero_output_from_zero_color_channel=float(source_head(0.,.5)),
    effective_gain_above_scalar_limit=float(source_head(.2,.5))/.2,
    zero_output_from_positive_color_channel=float(source_head(.2,1.25)),
    scalar_amplitude_from_zero_for_any_finite_gain=0.,
    positive_scalar_input_minimum_for_input_point2=.2*.125,
    warning='These compare algebraic head families, not the quality or actual coefficients of either trained model')
checks = dict(
    wrapper_and_legacy_output_heads_match=bool(np.allclose(wrapper_values,legacy_values,atol=1e-14,rtol=0)),
    complement_and_residual_rewrites_exact=bool(np.allclose(wrapper_values,rewritten,atol=1e-14,rtol=0)
        and np.allclose(wrapper_values,residual_form,atol=1e-14,rtol=0)),
    identity_at_h1=bool(np.allclose(source_head(inputs,1.),inputs,atol=1e-14,rtol=0)),
    h_below_one_never_darkens_a_channel=bool(np.all(source_head(inputs,.5)>=inputs)),
    h_above_one_never_brightens_a_channel=bool(np.all(source_head(inputs,2.)<=inputs)),
    white_channel_anchor=bool(np.all(source_head(1.,h)==1.)),
    bounded_scalar_gain_is_not_same_head_family=counterexamples['nonzero_output_from_zero_color_channel']>0
        and counterexamples['effective_gain_above_scalar_limit']>1.5
        and counterexamples['zero_output_from_positive_color_channel']==0,
    rgb_head_does_not_enforce_even_toy_scalar_color_curve=not off_curve['has_exact_scalar_preimage_on_toy_curve'],
    rounded_rgb_can_lose_scalar_distinctions=quantization_example['same_display_value'],
    frozen_sources_unchanged=not changed)
paths=['cdqob_pc_online_v1/model.py','cdqob_pc_online_v1/reference/AoDnet.py',
       'scalar_restore_v3/pc_candidate_compact/model_source.py',
       'scalar_restore_v3/pc_candidate_compact/restore_power.py']
report=dict(status='PASS' if all(checks.values()) else 'FAIL',
    scope='Output-head expressions with constructed coefficients; no trained CNN or MLP inference',
    checks=checks, algebra_pairs_checked=int(wrapper_values.size), examples=examples,
    toy_off_color_curve=off_curve, toy_display_rounding=quantization_example,
    operator_counterexamples=counterexamples,
    invertible_rgb_conditions=['Known scalar-to-color encoding and normalization',
        'Injectivity on the considered scalar interval',
        'No unresolved rounding, clipping, resizing or image rendering ambiguity',
        'Output lies on the known scalar color curve'],
    source_sha256={path:sha(ROOT/path) for path in paths},
    frozen_files_checked=len(baseline), changed_sources=changed,
    model_instantiated=False, model_parameters_modified=False, training_run=False,
    fft_run=False, feature_extraction_run=False, neural_inference_run=False,
    new_quality_test_run=False, new_holdout_opened=False, hardware_built=False, board_accessed=False)
(HERE/'reports/ORIGINAL_SCALAR_COMPARISON.json').write_text(
    json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
print(json.dumps(dict(status=report['status'],checks=checks,algebra_pairs_checked=report['algebra_pairs_checked'],
    examples=examples,toy_off_color_curve=off_curve,operator_counterexamples=counterexamples),ensure_ascii=False))
if report['status']!='PASS':
    raise SystemExit(1)
