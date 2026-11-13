"""Relative-recovery algebra and constructed normalization/guard calls only."""
import sys
sys.dont_write_bytecode = True
import ast
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


baseline = read(HERE / 'reports/SOURCE_BASELINE.json')
changed = [name for name, info in baseline.items() if sha(ROOT / name) != info['sha256']]
assert not changed, changed
normal_path = ROOT / 'scalar_restore_v2/common_v2.py'
guard_path = ROOT / 'scalar_restore_v3/pc_candidate_compact/scalar_guard.py'
config = read(ROOT / 'scalar_restore_v3/pc_candidate_compact/config.json')


def extract_functions(path, names):
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in functions} == set(names)
    namespace = {'np': np}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace


# Do not import the data module: it imports the radar FFT and model wrappers.
amplitudes = extract_functions(normal_path, ['amplitudes'])['amplitudes']
guard = extract_functions(guard_path, ['local_max', 'apply_guard'])['apply_guard']

# Uniformly positive scaling of each component leaves the actual two-level rule unchanged.
sign_cases = 0
sign_invariant = True
for real in range(-8, 9):
    for imag in range(-8, 9):
        original = [64 if real >= 0 else -64, 64 if imag >= 0 else -64]
        for scale in [Fraction(1, 2), Fraction(2), Fraction(5)]:
            scaled = [64 if real * scale >= 0 else -64, 64 if imag * scale >= 0 else -64]
            sign_invariant &= original == scaled
            sign_cases += 1

# Test the extracted normalization on constructed power arrays, not radar data.
reference = np.arange(1, 64, dtype='u8').reshape(7, 9)
base = np.roll(reference, 1, axis=1)
y0, x0 = amplitudes(reference, base)
normal_checks = []
for ref_scale in [1, 4, 9, 25]:
    for base_scale in [1, 4, 9, 25]:
        y, x = amplitudes(reference * ref_scale, base * base_scale)
        normal_checks.append(dict(reference_power_scale=ref_scale, input_power_scale=base_scale,
                                  source_normalized_arrays_exact=bool(np.array_equal(y, y0) and np.array_equal(x, x0))))

# Exact, constructed nonnegative arrays. No claim that this is a real same-I/Q pair.
base_power = [Fraction(100), Fraction(9), Fraction(1)]
reference_power = [Fraction(400), Fraction(4), Fraction(1)]
prescribed_gain = [Fraction(1), Fraction(1, 3), Fraction(1, 2)]
scale_ratio = max(base_power) / max(reference_power)
example = []
for p, t, g in zip(base_power, reference_power, prescribed_gain):
    result = p * g * g
    assert result == scale_ratio * t
    example.append(dict(input_power=float(p), reference_power=float(t), input_relative_amplitude=math.sqrt(float(p / max(base_power))),
                        reference_relative_amplitude=math.sqrt(float(t / max(reference_power))),
                        hypothetical_exact_gain=float(g), output_power=float(result),
                        output_equals_reference_times_scale=True))

identity_count = 0
identity_ok = True
for input_peak in [1, 4, 25, 100]:
    for reference_peak in [1, 9, 64, 400]:
        for input_fraction in [Fraction(1, 100), Fraction(1, 4), Fraction(1)]:
            for ref_fraction in [Fraction(1, 400), Fraction(1, 9), Fraction(1)]:
                p = input_peak * input_fraction
                target = reference_peak * ref_fraction
                gain_squared = ref_fraction / input_fraction
                identity_ok &= p * gain_squared == Fraction(input_peak, reference_peak) * target
                identity_count += 1

# A remote maximum changes normalized center, without changing that center's power.
peak_change = []
for peak in [100, 400]:
    relative_power = 8 / peak
    peak_change.append(dict(unchanged_center_power=8, frame_peak_power=peak,
                            relative_amplitude=math.sqrt(relative_power),
                            ideal_fifthroot_amplitude=relative_power ** .1,
                            satisfies_weak_upper_bound_only=8 <= peak // 16,
                            upper_power_bound=peak // 16))

# The guard's peak anchoring is a rule even when both required gains are in range.
anchor_input = np.array([[100, 64, 0]], dtype='u8')
anchor_reference = np.array([[25, 100, 0]], dtype='u8')
anchor_y, anchor_x = amplitudes(anchor_reference, anchor_input)
required = np.array([[.5, 1.25, 1.]])
required_q14 = np.rint(required * 16384).astype('u2')
constructed_features = np.zeros((6, anchor_input.size), dtype='u2')
guarded = guard(anchor_input, required_q14, config['power_guard'], constructed_features, actual_chirps=512)
after_amplitude = anchor_x * guarded.astype('f8') / 16384
anchor = dict(scope='Constructed powers, features and prescribed gains; no neural predictions',
              input_power=anchor_input.tolist(), reference_power=anchor_reference.tolist(),
              input_normalized_amplitude=anchor_x.tolist(), target_normalized_amplitude=anchor_y.tolist(),
              hypothetical_required_gain=required.tolist(), guarded_gain=(guarded / 16384).tolist(),
              guarded_relative_amplitude=after_amplitude.tolist(),
              every_prescribed_gain_within_allowed_range=bool(np.all((required >= .125) & (required <= 1.5))),
              peak_gain_forced_to_one=bool(guarded[0, 0] == 16384),
              peak_target_not_exactly_matched=bool(after_amplitude[0, 0] != anchor_y[0, 0]),
              statement_is_about_training_coordinate_not_arbitrary_renormalized_display=True)

checks = dict(
    positive_scaling_preserves_two_level_observation=bool(sign_invariant) and sign_cases == 867,
    source_independent_normalization_invariant=all(row['source_normalized_arrays_exact'] for row in normal_checks),
    exact_relative_to_raw_scale_identity=bool(identity_ok) and identity_count == 144,
    specified_example_preserves_relative_not_absolute_power=all(row['output_equals_reference_times_scale'] for row in example) and scale_ratio == Fraction(1, 4),
    remote_maximum_changes_center_representation=peak_change[0]['ideal_fifthroot_amplitude'] != peak_change[1]['ideal_fifthroot_amplitude'],
    remote_maximum_changes_only_tested_upper_eligibility=not peak_change[0]['satisfies_weak_upper_bound_only'] and peak_change[1]['satisfies_weak_upper_bound_only'],
    constructed_guard_anchors_peak_despite_reachable_target=all(anchor[k] for k in ['every_prescribed_gain_within_allowed_range', 'peak_gain_forced_to_one', 'peak_target_not_exactly_matched']),
    frozen_sources_unchanged=not changed)
paths = ['scalar_restore_v2/common_v2.py', 'scalar_restore_v2/prepare_data.py',
         'scalar_restore_v3/pc_candidate_compact/restore_power.py',
         'scalar_restore_v3/pc_candidate_compact/scalar_guard.py',
         'scalar_restore_v3/pc_candidate_compact/config.json']
report = dict(status='PASS' if all(checks.values()) else 'FAIL',
              scope='Relative amplitude coordinates, exact scalar algebra and constructed source-function calls only',
              checks=checks,sign_scale_cases=sign_cases,normalization_cases=normal_checks,
              exact_scale_identity_cases=identity_count,
              prescribed_example=example,output_to_reference_power_scale=float(scale_ratio),
              changed_frame_peak_example=peak_change,constructed_peak_anchor_example=anchor,
              limitations=['No assertion that the constructed pairs come from the same measured I/Q',
                           'Ideal scale cancellation is not a guarantee of bit-exact invariance with rounding or saturation',
                           'A changed upper-threshold eligibility is not the full protection mask or a predicted gain',
                           'No new restoration-quality evidence'],
              source_sha256={name:sha(ROOT/name) for name in paths},
              frozen_files_checked=len(baseline),changed_sources=changed,
              constructed_normalization_run=True,constructed_guard_run=True,
              model_instantiated=False,model_parameters_modified=False,training_run=False,
              fft_run=False,full_feature_extraction_run=False,neural_inference_run=False,
              new_quality_test_run=False,new_holdout_opened=False,hardware_built=False,board_accessed=False)
(HERE / 'reports/NORMALIZATION_WALKTHROUGH.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
print(json.dumps(dict(status=report['status'],checks=checks,exact_scale_identity_cases=identity_count,
                      prescribed_example=example,changed_frame_peak_example=peak_change), ensure_ascii=False))
if report['status'] != 'PASS':
    raise SystemExit(1)
