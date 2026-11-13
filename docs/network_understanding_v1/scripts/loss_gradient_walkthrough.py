"""Differentiate constructed scalar scores to explain frozen training losses.

No model is instantiated. No optimizer or parameter update is run. Autograd is
used only on ten invented scores and checked against hand-derived expressions.
"""
import sys
sys.dont_write_bytecode = True
import ast
import copy
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import torch
from torch.nn import functional as F

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
SOURCE = ROOT / 'scalar_restore_v2/runs/protected_patch5/training_source.py'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


baseline = read(HERE / 'reports/SOURCE_BASELINE.json')
changed = [p for p, info in baseline.items() if sha(ROOT/p) != info['sha256']]
assert not changed, changed
config_path = ROOT / 'scalar_restore_v2/runs/soft_patch5/config.json'
config = read(config_path)
assert sha(SOURCE) == config['code_sha256']
assert config['protect_strength'] == 20

tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
loop = next(n for n in main.body if isinstance(n, ast.For) and any(
    isinstance(t, ast.Assign) and any(isinstance(v, ast.Name) and v.id == 'goal' for v in t.targets)
    for t in n.body))
start = next(i for i, n in enumerate(loop.body) if isinstance(n, ast.Assign) and any(
    isinstance(v, ast.Name) and v.id == 'g' for v in n.targets))
end = next(i for i, n in enumerate(loop.body) if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
    and isinstance(n.value.func, ast.Attribute) and isinstance(n.value.func.value, ast.Name)
    and n.value.func.value.id == 'opt')
original = loop.body[start:end]


def split_add(node):
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return split_add(node.left) + split_add(node.right)
    return [node]


def capture(expr):
    return ast.Expr(value=ast.Call(func=ast.Attribute(value=ast.Name(id='snapshot_terms', ctx=ast.Load()),
        attr='append', ctx=ast.Load()), args=[copy.deepcopy(expr)], keywords=[]))


def instrument(nodes):
    result = []
    for node in copy.deepcopy(nodes):
        if isinstance(node, ast.If):
            node.body = instrument(node.body)
        result.append(node)
        if isinstance(node, ast.Assign) and any(isinstance(v, ast.Name) and v.id == 'loss' for v in node.targets):
            result.extend(capture(term) for term in split_add(node.value))
        elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and node.target.id == 'loss':
            result.append(capture(node.value))
    return result


code = compile(ast.fix_missing_locations(ast.Module(body=instrument(original), type_ignores=[])), str(SOURCE), 'exec')
examples = [
    dict(name='过估计点', x=.3, y=.01, raw=-1., support=0, known=0, low=0, centers=0, excess=1),
    dict(name='被压低的受支持弱点', x=.018, y=.02, raw=math.log2(.4), support=1, known=1, low=0, centers=1, excess=0),
    dict(name='轻微误压的受支持点', x=.018, y=.02, raw=math.log2(.9), support=1, known=1, low=0, centers=0, excess=0),
    dict(name='低背景被增强', x=.001, y=.0001, raw=math.log2(1.25), support=0, known=0, low=1, centers=0, excess=1),
    dict(name='分数低于下限', x=.08, y=.002, raw=-5., support=0, known=0, low=1, centers=0, excess=1),
    dict(name='分数高于上限', x=.03, y=.03, raw=2., support=1, known=0, low=0, centers=0, excess=0),
    dict(name='输入严格为零', x=0., y=.02, raw=-.4, support=1, known=1, low=0, centers=0, excess=0),
    dict(name='微小输入未进入增益头监督', x=.000001, y=.000001, raw=-.7, support=0, known=0, low=1, centers=0, excess=0),
    dict(name='参考超出增强上限', x=.02, y=.08, raw=.8, support=1, known=1, low=0, centers=1, excess=0),
    dict(name='已达到最强允许衰减', x=.08, y=.002, raw=-3.4, support=0, known=0, low=1, centers=0, excess=1),
]
keys = ['raw', 'x', 'y', 'support', 'known', 'low', 'centers', 'excess']
arrays = {key: np.array([row[key] for row in examples], dtype='f8')[:, None] for key in keys}
names = ['log2_gain_head', 'log_amplitude', 'amplitude_squared', 'support_nonregression',
         'center_relative_nonregression', 'artifact_overestimate', 'low_background_boost', 'explicit_peak_protection']


def execute(raw_values, gradients=False):
    env = dict(torch=torch, F=F, net=SimpleNamespace(boost=True), a=SimpleNamespace(protect_strength=20.), snapshot_terms=[])
    env.update({key: torch.tensor(value, dtype=torch.float64, requires_grad=gradients and key=='raw')
                for key, value in arrays.items()})
    env['raw'] = torch.tensor(raw_values, dtype=torch.float64, requires_grad=gradients)
    exec(code, env)
    assert len(env['snapshot_terms']) == 8
    assert abs(sum(float(term.detach()) for term in env['snapshot_terms']) - float(env['loss'].detach())) < 1e-12
    return env


env = execute(arrays['raw'], True)
autograd = {name: torch.autograd.grad(term, env['raw'], retain_graph=True)[0].detach().numpy()
            for name, term in zip(names, env['snapshot_terms'])}
source_total = torch.autograd.grad(env['loss'], env['raw'])[0].detach().numpy()

raw, x, y, S, K, L, C, E = [arrays[key] for key in keys]
upper = .5849625
inside = (raw > -3) & (raw < upper)
g = np.exp2(np.clip(raw, -3, upper))
prediction = x*g
dg = np.log(2.)*g*inside
q = x*dg
delta = prediction-y
err0 = np.abs(x-y)
goal = np.clip(np.log2((y+.00001)/(x+.00001)), -3, upper)
w = 1+3*S+5*K+8*C
valid = x>.00001


def normalized(mask):
    return mask/max(float(mask.sum()), 1.)


active_standard = np.abs(delta)-err0-.002 > 0
T = np.clip(C+K, 0, 1)
analytic = dict(
    log2_gain_head=.35*normalized(w*valid)*np.clip(raw-goal, -1, 1),
    log_amplitude=.2*normalized(w)*np.sign(delta)*q/(.001+prediction),
    amplitude_squared=40*normalized(w)*delta*q,
    support_nonregression=4*normalized(S+K)*active_standard*np.sign(delta)*q,
    center_relative_nonregression=2*normalized(C+K)*active_standard*np.sign(delta)*q/(y+.01),
    artifact_overestimate=.6*normalized(E)*np.maximum(delta,0)*q/(y+.01)**2,
    low_background_boost=.1*normalized(L)*(g>1)*dg,
    explicit_peak_protection=20*normalized(T)*q/(y+.005)*(
        (np.abs(delta)-err0-.0005>0)*np.sign(delta)
        -(.52*y-prediction>0)*(x>=.5*y)))
analytic_total = sum(analytic.values())
term_errors = {name: float(np.max(np.abs(analytic[name]-autograd[name]))) for name in names}
finite_difference = np.empty_like(raw)
epsilon = 1e-6
with torch.no_grad():
    for index in range(len(examples)):
        plus, minus = raw.copy(), raw.copy()
        plus[index,0] += epsilon
        minus[index,0] -= epsilon
        finite_difference[index,0] = (float(execute(plus)['loss'])-float(execute(minus)['loss']))/(2*epsilon)

rows = []
for index, example in enumerate(examples):
    rows.append(dict(**example, gain=float(g[index,0]), predicted_amplitude=float(prediction[index,0]),
                     target_score=float(goal[index,0]), head_valid=bool(valid[index,0]),
                     amplitude_branch_score_derivative=float(q[index,0]),
                     term_score_derivatives={name: float(analytic[name][index,0]) for name in names},
                     total_score_derivative=float(source_total[index,0]),
                     finite_difference=float(finite_difference[index,0]),
                     scalar_negative_gradient_direction='decrease_score' if source_total[index,0]>0 else
                         'increase_score' if source_total[index,0]<0 else 'no_direct_score_gradient'))

# One common score for identical observations, two incompatible references.
common_x = .02
targets = np.array([.002,.018])
tradeoffs = []
for weights in [np.array([1.,1.]), np.array([1.,9.])]:
    best_output = float(np.clip(np.sum(weights*targets)/weights.sum(), .125*common_x, 1.5*common_x))
    best_gain = best_output/common_x
    prediction_errors = (best_output-targets)**2
    score_gradient = float(np.sum(weights*2*(best_output-targets)*best_output*np.log(2.))/weights.sum())
    tradeoffs.append(dict(weights=weights.tolist(), common_input=common_x,
                          two_incompatible_references=targets.tolist(), optimal_common_output=best_output,
                          optimal_common_gain=best_gain, squared_errors=prediction_errors.tolist(),
                          weighted_score_gradient_at_optimum=score_gradient,
                          both_references_exactly_recovered=bool(np.all(prediction_errors<1e-20))))

# Generic one-parameter algebra, not a model update or a training experiment.
toy_j = np.array([1., 4.])
toy_targets = np.array([-2., 1.])
toy_theta = 0.
toy_scores = toy_theta * toy_j
toy_d = toy_scores-toy_targets
toy_gradient = float(toy_j@toy_d)
toy_eta = .01
toy_next_theta = toy_theta-toy_eta*toy_gradient
toy_next_scores = toy_next_theta*toy_j
toy_before = .5*(toy_scores-toy_targets)**2
toy_after = .5*(toy_next_scores-toy_targets)**2
shared_parameter_example = dict(scope='Generic scalar quadratic illustration; no current MLP evaluated or changed',
    jacobians=toy_j.tolist(), targets=toy_targets.tolist(), original_scores=toy_scores.tolist(),
    loss_derivatives_with_respect_to_scores=toy_d.tolist(), total_parameter_gradient=toy_gradient,
    hypothetical_learning_rate=toy_eta, hypothetical_scores_after_step=toy_next_scores.tolist(),
    exact_linear_score_change=(-toy_eta*np.outer(toy_j,toy_j)@toy_d).tolist(),
    individual_losses_before=toy_before.tolist(), individual_losses_after=toy_after.tolist(),
    total_loss_decreases=bool(toy_after.sum()<toy_before.sum()),
    first_sample_loss_increases=bool(toy_after[0]>toy_before[0]))

checks = dict(
    selected_training_source_hash_verified=sha(SOURCE)==config['code_sha256'],
    eight_source_terms_captured=len(autograd)==8,
    all_eighty_derivatives_match_source_autograd=all(error<1e-10 for error in term_errors.values()),
    total_derivative_matches_source=float(np.max(np.abs(analytic_total-source_total)))<1e-10,
    ten_total_derivatives_match_finite_difference=float(np.max(np.abs(finite_difference-source_total)))<1e-7,
    background_and_weak_point_have_opposite_directions=rows[0]['total_score_derivative']>0 and rows[1]['total_score_derivative']<0,
    clipping_blocks_amplitude_but_not_valid_head=all(rows[i]['amplitude_branch_score_derivative']==0 and
        abs(rows[i]['term_score_derivatives']['log2_gain_head'])>0 and
        all(value==0 for key,value in rows[i]['term_score_derivatives'].items() if key!='log2_gain_head') for i in [4,5,8,9]),
    exact_zero_input_has_no_direct_score_gradient=rows[6]['total_score_derivative']==0,
    tiny_input_has_amplitude_gradient_without_head=not rows[7]['head_valid'] and rows[7]['total_score_derivative']<0,
    incompatible_references_require_tradeoff=all(not row['both_references_exactly_recovered'] and
        abs(row['weighted_score_gradient_at_optimum'])<1e-18 for row in tradeoffs),
    shared_parameter_coupling_algebra_verified=shared_parameter_example['total_loss_decreases'] and
        shared_parameter_example['first_sample_loss_increases'] and
        np.allclose(toy_next_scores-toy_scores, -toy_eta*np.outer(toy_j,toy_j)@toy_d, atol=1e-15),
    frozen_sources_unchanged=not changed)
source_paths = ['scalar_restore_v2/runs/protected_patch5/training_source.py',
                'scalar_restore_v2/runs/soft_patch5/config.json']
report = dict(status='PASS' if all(checks.values()) else 'FAIL',
              scope='Ten constructed independent scores only; masks are specified for algebra, not extracted from radar data',
              checks=checks, examples=rows, per_term_maximum_derivative_error=term_errors,
              total_maximum_derivative_error=float(np.max(np.abs(analytic_total-source_total))),
              maximum_finite_difference_error=float(np.max(np.abs(finite_difference-source_total))),
              identical_feature_squared_loss_examples=tradeoffs,
              shared_parameter_algebra_example=shared_parameter_example,
              warning='Score-space negative-gradient direction is not a guarantee of the shared MLP or Adam update direction',
              source_sha256={path:sha(ROOT/path) for path in source_paths},
              frozen_files_checked=len(baseline), changed_sources=changed,
              constructed_score_autograd_run=True, model_instantiated=False, model_backward_run=False,
              optimizer_run=False, model_parameters_modified=False, training_run=False, fft_run=False,
              feature_extraction_run=False, neural_inference_run=False, new_quality_test_run=False,
              new_holdout_opened=False, hardware_built=False, board_accessed=False)
(HERE/'reports/LOSS_GRADIENT_WALKTHROUGH.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n',encoding='utf-8')
print(json.dumps(dict(status=report['status'], checks=checks,
    maximum_derivative_error=report['total_maximum_derivative_error'],
    maximum_finite_difference_error=report['maximum_finite_difference_error'],
    examples=[{key:row[key] for key in ['name','predicted_amplitude','total_score_derivative','scalar_negative_gradient_direction']} for row in rows],
    identical_feature_squared_loss_examples=tradeoffs),ensure_ascii=False))
if report['status']!='PASS':
    raise SystemExit(1)
