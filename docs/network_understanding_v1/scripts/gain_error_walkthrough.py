"""When a prescribed gain helps: exact scalar error algebra, no inference."""
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
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


baseline = read(HERE/'reports/SOURCE_BASELINE.json')
changed = [name for name,info in baseline.items() if sha(ROOT/name)!=info['sha256']]
assert not changed, changed
lower, upper = F(1,8), F(3,2)
gains = [lower,F(1,4),F(1,2),F(3,4),F(1),F(5,4),upper]
ratios = [F(0),F(1,16),F(1,8),F(1,5),F(1,2),F(9,16),F(3,4),F(77,100),F(4,5),F(1),F(5,4),F(3,2),F(2)]
inputs = [F(1,100),F(1,20),F(1,5),F(1,2)]
grid_count = 0
oracle_count = 0
amplitude_identity = power_identity = conditions_match = oracle_no_worse = regret_identity = True
for x in inputs:
    for r in ratios:
        y = x*r
        optimum = max(lower,min(upper,r))
        oracle_error = (x*optimum-y)**2
        bypass_error = (x-y)**2
        oracle_no_worse &= oracle_error <= bypass_error
        oracle_count += 1
        for g in gains:
            error = (x*g-y)**2
            delta = error-bypass_error
            delta_formula = x*x*(g-1)*(g+1-2*r)
            amplitude_identity &= delta == delta_formula
            if g<1:
                helps = r<(g+1)/2
                power_helps = r*r<(g*g+1)/2
            elif g>1:
                helps = r>(g+1)/2
                power_helps = r*r>(g*g+1)/2
            else:
                helps = power_helps = False
            conditions_match &= (delta<0)==helps
            power_delta = ((x*g)**2-y*y)**2-(x*x-y*y)**2
            power_formula = x**4*(g*g-1)*(g*g+1-2*r*r)
            power_identity &= power_delta == power_formula and (power_delta<0)==power_helps
            if lower<=r<=upper:
                regret_identity &= error-oracle_error == x*x*(g-r)**2
            grid_count += 1

examples = []
for r in [F(1,5),F(4,5),F(77,100)]:
    x,g = F(1,5),F(1,2)
    y = x*r
    amp_before,amp_after = (x-y)**2,(x*g-y)**2
    power_before,power_after = (x*x-y*y)**2,((x*g)**2-y*y)**2
    examples.append(dict(input_relative_amplitude=float(x),reference_relative_amplitude=float(y),
                         prescribed_gain=float(g),reference_to_input_ratio=float(r),
                         output_relative_amplitude=float(x*g),
                         amplitude_squared_error_before=float(amp_before),amplitude_squared_error_after=float(amp_after),
                         power_squared_error_before=float(power_before),power_squared_error_after=float(power_after),
                         amplitude_error_improves=amp_after<amp_before,power_error_improves=power_after<power_before))
boundaries = [dict(gain=float(g),amplitude_error_equal_boundary=float((g+1)/2),
                   power_error_equal_boundary=math.sqrt(float((g*g+1)/2)),
                   improvement_direction='reference/input below boundary' if g<1 else 'reference/input above boundary')
              for g in gains if g!=1]

# Reuse gains from existing traced points. The unknown reference is NOT invented.
trace = read(HERE/'reports/POINT_TRACE.json')
existing = []
for row in trace['rows']:
    g = F(row['final_gain_q14'],16384)
    existing.append(dict(position=[row['natural_range_bin'],row['natural_doppler_bin']],
                         existing_final_gain=float(g),
                         improvement_condition=('same error as bypass for every reference' if g==1 else
                            f"Y/X {'<' if g<1 else '>'} {float((g+1)/2)} for amplitude squared error"),
                         actual_reference_ratio_not_evaluated=True,physical_target_label_inferred=False))

checks = dict(
    amplitude_error_identity_exact=bool(amplitude_identity),
    improvement_conditions_match_exact_grid=bool(conditions_match),
    power_error_identity_and_condition_exact=bool(power_identity),
    known_reference_bounded_optimum_cannot_worsen_bypass=bool(oracle_no_worse),
    attainable_reference_regret_identity_exact=bool(regret_identity),
    same_gain_can_help_or_harm=examples[0]['amplitude_error_improves'] and not examples[1]['amplitude_error_improves'],
    amplitude_and_power_metrics_can_disagree=not examples[2]['amplitude_error_improves'] and examples[2]['power_error_improves'],
    existing_four_gains_interpreted_conditionally=len(existing)==4 and sum(row['existing_final_gain']==1 for row in existing)==3 and sum(row['existing_final_gain']==.125 for row in existing)==1,
    frozen_sources_unchanged=not changed)
paths = ['scalar_streak_fix_v1/common.py', 'scalar_restore_v3/pc_candidate_compact/config.json',
         'network_understanding_v1/reports/POINT_TRACE.json']
report = dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,
              scope='Prescribed scalar gains, exact rational error identities and existing gain records only',
              exact_grid_cases=grid_count,known_reference_optimum_cases=oracle_count,
              examples=examples,equality_boundaries=boundaries,existing_points=existing,
              qualifications=['X and Y use the same relative-amplitude coordinates as the paired task',
                              'Constructed examples are not predictions or claimed physical same-I/Q pairs',
                              'A known-reference optimum is unavailable at inference and is not the trained MLP',
                              'Current training has compound losses, shared parameters and fixed output guards',
                              'Power squared error is a separate hypothetical metric, not a relabeling of current amplitude NMSE',
                              'The exact identities omit integer rounding and saturation',
                              'No new quality, target-label or detection conclusion'],
              source_sha256={name:sha(ROOT/name) for name in paths},
              frozen_files_checked=len(baseline),changed_sources=changed,
              exact_constructed_algebra_run=True,model_instantiated=False,model_parameters_modified=False,
              training_run=False,radar_fft_run=False,feature_extraction_run=False,neural_inference_run=False,
              new_quality_test_run=False,new_holdout_opened=False,hardware_built=False,board_accessed=False)
(HERE/'reports/GAIN_ERROR_WALKTHROUGH.json').write_text(
    json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
print(json.dumps(dict(status=report['status'],checks=checks,exact_grid_cases=grid_count,
                      known_reference_optimum_cases=oracle_count,examples=examples,existing_points=existing),ensure_ascii=False))
if report['status']!='PASS':
    raise SystemExit(1)
