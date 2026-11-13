"""Explain existing parent-coordinate cues; no radar FFT or model inference."""
import sys
sys.dont_write_bytecode = True
import ast
import hashlib
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
SOURCE = ROOT / 'scalar_restore_v3/pc_candidate_compact/restore_power.py'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


baseline = read(HERE / 'reports/SOURCE_BASELINE.json')
changed = [p for p, info in baseline.items() if sha(ROOT / p) != info['sha256']]
assert not changed, changed
source_text = SOURCE.read_text(encoding='utf-8')
tree = ast.parse(source_text)
cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'PowerRestorer')
method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'features')
expressions = {}
for node in ast.walk(method):
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        if node.targets[0].id in ['ri', 'ai']:
            expressions[node.targets[0].id] = compile(ast.Expression(node.value), str(SOURCE), 'eval')
assert set(expressions) == {'ri', 'ai'}
assert "support=maximum_filter(z,3,mode='wrap')" in source_text
assert 'support[np.ix_(ri,ai)]' in source_text
assert 'np.maximum(parent,support[np.ix_(ri,ai)],out=parent)' in source_text


def circular(value, length):
    return (value + length // 2) % length - length // 2


def rational_centers(target, length, order):
    size = abs(order)
    sign = 1 if order > 0 else -1
    # Odd denominator: no half-integer ties. This works for negative numerators.
    return [((2 * (sign * target + k * length) + size) // (2 * size)) % length
            for k in range(size)]


def support_positions(target, length, order):
    return {(p + offset) % length for p in rational_centers(target, length, order)
            for offset in [-1, 0, 1]}


rows = []
for order in [-3, 5]:
    size = abs(order)
    radius = (3 * size - 1) // 2
    for length, name, index_name, branch_name in [(1024, 'range', 'ri', 'kr'), (512, 'doppler', 'ai', 'ka')]:
        indices = np.arange(length)
        env = {'np': np, 'h': order, 'order': size,
               'r': indices, 'a': indices, 'kr': 0, 'ka': 0}
        source_centers = []
        for k in range(size):
            env[branch_name] = k
            source_centers.append(eval(expressions[index_name], {'__builtins__': {}}, env))
        exact = True
        exact_inverse = True
        coverage = True
        cardinality = True
        for target in range(length):
            centers = rational_centers(target, length, order)
            exact &= centers == [int(row[target]) for row in source_centers]
            positions = support_positions(target, length, order)
            inverse = pow(order, -1, length)
            exact_inverse &= inverse * target % length in positions
            forward_offsets = {circular(order * p - target, length) for p in positions}
            equivalent_positions = {inverse * (target + e) % length for e in range(-radius, radius + 1)}
            coverage &= forward_offsets == set(range(-radius, radius + 1)) and positions == equivalent_positions
            cardinality &= len(set(centers)) == size and len(positions) == 3 * size
        rows.append(dict(order=order, dimension=name, length=length, coordinates_checked=length,
                         candidate_centers_per_axis=size, support_positions_per_axis=3 * size,
                         forward_residual_min=-radius, forward_residual_max=radius,
                         source_expression_matches_rational_rounding=bool(exact),
                         exact_modular_inverse_always_included=bool(exact_inverse),
                         full_forward_residual_set_matches=bool(coverage),
                         query_cardinality_constant=bool(cardinality)))

order = -3
parent = [131, 37]
child = [order * parent[0] % 1024, order * parent[1] % 512]
alternate = [pow(order, -1, 1024) * (child[0] + 1) % 1024,
             pow(order, -1, 512) * (child[1] - 1) % 512]
query_r = support_positions(child[0], 1024, order)
query_a = support_positions(child[1], 512, order)
query = {(r, a) for r in query_r for a in query_a}


def sparse_cue(sparse_field):
    return max(sparse_field.get(position, 0) for position in query)


cue_a = sparse_cue({tuple(parent): 4096})
cue_b = sparse_cue({tuple(alternate): 4096})
max_pool_example = dict(
    scope='Constructed encoded-field lookup only; not an IQ scene or neural output',
    child=child, exact_integer_parent=parent, alternative_support=alternate,
    alternative_forward_child=[order * alternate[0] % 1024, order * alternate[1] % 512],
    alternative_forward_residual=[circular(order * alternate[0] - child[0], 1024),
                                  circular(order * alternate[1] - child[1], 512)],
    same_parent_cue_q12=[cue_a, cue_b],
    same_parent_cue_does_not_prove_same_other_features=True,
    winner_coordinates_are_not_in_the_two_parent_scalar_features=True)

features = read(HERE / 'reports/FEATURE_WALKTHROUGH.json')
actual = next(row for row in features['actual_point_checks'] if row['position'] == [774, 511])
actual_parent = next(row for row in actual['parent_details'] if row['order'] == -3)
winner = actual_parent['winner']['support_source']
exact_parent = [pow(-3, -1, length) * target % length for target, length in zip(actual['position'], [1024, 512])]
winner_in_support = all(pos in support_positions(target, length, -3)
                        for pos, target, length in zip(winner, actual['position'], [1024, 512]))
actual_record = dict(observed=actual['position'], existing_winner=winner,
                    exact_integer_inverse=exact_parent, winner_in_enumerated_support=winner_in_support,
                    winner_forward_residual=[circular(-3 * p - t, n) for p, t, n in zip(winner, actual['position'], [1024, 512])],
                    existing_mlp_gain=actual['raw_gain'], existing_final_gain=actual['final_gain'],
                    physical_target_truth_available=False)

source_paths = ['scalar_restore_v3/pc_candidate_compact/restore_power.py',
                'network_understanding_v1/reports/FEATURE_WALKTHROUGH.json']
checks = dict(
    all_3072_axis_coordinates_match_source=sum(row['coordinates_checked'] for row in rows) == 3072
        and all(row['source_expression_matches_rational_rounding'] for row in rows),
    exact_inverse_always_included=all(row['exact_modular_inverse_always_included'] for row in rows),
    forward_tolerance_sets_exhaustively_verified=all(row['full_forward_residual_set_matches'] for row in rows),
    per_axis_cardinality_verified=all(row['query_cardinality_constant'] for row in rows),
    two_dimensional_counts_from_cartesian_product=(3 * 3) ** 2 == 81 and (3 * 5) ** 2 == 225,
    same_maximum_from_different_support_locations=parent != alternate and cue_a == cue_b == 4096,
    existing_winner_and_gain_preserved=winner_in_support and winner == [83, 0] and actual['raw_gain'] == .125,
    frozen_sources_unchanged=not changed)
report = dict(status='PASS' if all(checks.values()) else 'FAIL',
              scope='Coordinate geometry and existing feature-record teaching only', checks=checks,
              axes=rows, parent_query_geometry=[
                  dict(order=h, center_pairs=abs(h)**2, encoded_support_points=(3*abs(h))**2,
                       forward_child_tolerance_per_axis=(3*abs(h)-1)//2) for h in [-3, 5]],
              maximum_information_loss_example=max_pool_example, existing_point=actual_record,
              source_sha256={p: sha(ROOT/p) for p in source_paths},
              frozen_files_checked=len(baseline), changed_sources=changed,
              model_parameters_modified=False, training_run=False, fft_run=False,
              radar_feature_extraction_run=False, neural_inference_run=False,
              new_quality_test_run=False, new_holdout_opened=False, hardware_built=False, board_accessed=False)
(HERE / 'reports/PARENT_QUERY_WALKTHROUGH.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(status=report['status'], checks=checks,
                     parent_query_geometry=report['parent_query_geometry'],
                     maximum_information_loss_example=max_pool_example,
                     existing_point=actual_record), ensure_ascii=False))
if report['status'] != 'PASS':
    raise SystemExit(1)
