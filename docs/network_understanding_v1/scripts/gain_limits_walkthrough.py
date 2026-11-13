"""Frozen gain-range interpretation; scalar algebra and existing traces only."""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
import math
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parents[1]
ROOT=HERE.parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(4*1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


baseline=read(HERE/'reports/SOURCE_BASELINE.json')
changed=[path for path,info in baseline.items() if sha(ROOT/path)!=info['sha256']]
assert not changed,changed
folder=ROOT/'scalar_restore_v3/pc_candidate_compact'
config=read(folder/'config.json')
with np.load(folder/'weights.npz',allow_pickle=False) as archive:
    lut=archive['gain_lut'].copy()
lower,upper=config['gain_range']
rows=[]
for gain in [.125,.25,.5,.75,1.,1.5]:
    rows.append(dict(amplitude_gain=gain,power_multiplier=gain**2,
        amplitude_change_db=20*math.log10(gain),power_change_db=10*math.log10(gain**2)))

grid=np.linspace(lower,upper,257)
ratios=grid[:,None]/grid[None,:]
contrast=dict(scope='Necessary algebraic bounds from two gains; simultaneous attainability by the trained MLP is not proved',
    unanchored_maximum_amplitude_ratio_multiplier=upper/lower,
    unanchored_maximum_power_ratio_multiplier=(upper/lower)**2,
    unanchored_maximum_contrast_improvement_db=20*math.log10(upper/lower),
    unanchored_minimum_contrast_change_db=20*math.log10(lower/upper),
    anchored_numerator_gain=1.,anchored_maximum_amplitude_ratio_multiplier=1/lower,
    anchored_maximum_contrast_improvement_db=20*math.log10(1/lower),
    current_gain_lut_q14_min=int(lut.min()),current_gain_lut_q14_max=int(lut.max()))

harmonics=[]
for order in [-3,5]:
    amplitude=1/abs(order)
    after=amplitude*lower
    harmonics.append(dict(order=order,
        assumptions='Ideal separated single-tone harmonic, main amplitude normalized to one and anchored, no alias collision, leakage, windowing or numerical rounding',
        before_relative_amplitude=amplitude,before_relative_db=20*math.log10(amplitude),
        minimum_allowed_relative_amplitude=after,minimum_allowed_relative_power=after**2,
        minimum_allowed_relative_db=20*math.log10(after),
        scalar_reference_zero_not_exactly_reachable=after>0,
        chosen_gain_is_structural_limit_not_new_model_prediction=True))

same_bin=dict(scope='Fixed common gain applied to a hypothetical separated component-power accounting; no radar SNR estimated',
    signal_power=9.,noise_power=1.,common_gain=.125,
    output_signal_power=9*.125**2,output_noise_power=.125**2,
    component_power_ratio_before=9.,component_power_ratio_after=9.,
    warning='Measured |S+N|^2 also contains a cross term; a data-dependent gain requires separate statistical analysis')

trace_path=HERE/'reports/POINT_TRACE.json'
trace=read(trace_path)
existing=[]
for row in trace['rows']:
    gain=row['final_gain_q14']/16384
    rounded=min((1<<64)-1,(row['power']*row['final_gain_q14']**2+(1<<27))>>28)
    existing.append(dict(position=[row['natural_range_bin'],row['natural_doppler_bin']],
        input_power=row['power'],output_power=row['output_power'],final_gain=gain,
        ideal_same_point_change_db=20*math.log10(gain),
        actual_integer_power_ratio=row['output_power']/row['power'],
        actual_integer_change_db=10*math.log10(row['output_power']/row['power']),
        existing_output_exact=rounded==row['output_power'],physical_truth_available=False))

rounding=dict(input_power=1,gain=.125,ideal_output_power=1/64,
    rounded_output_power=(1*2048**2+(1<<27))>>28,
    explanation='Real-valued lower bound is not a positive lower bound after integer rounding')
uniform=dict(input_amplitudes=[.1,.01],common_gain=.125,
    input_ratio=.1/.01,output_ratio=(.1*.125)/(.01*.125),
    common_change_db=20*math.log10(.125),contrast_change_db=0.)

checks=dict(
    frozen_gain_config_and_lut_match=lower==.125 and upper==1.5 and int(lut.min())==2048 and int(lut.max())==24576,
    amplitude_and_power_db_are_equal=all(abs(row['amplitude_change_db']-row['power_change_db'])<1e-13 for row in rows),
    two_gain_ratio_bounds_match_grid=abs(float(ratios.max())-upper/lower)<1e-13 and abs(float(ratios.min())-lower/upper)<1e-13,
    ideal_harmonic_floors_match=all(abs(row['minimum_allowed_relative_power']-1/(64*abs(row['order'])**2))<1e-15 for row in harmonics),
    fixed_common_gain_preserves_component_ratio=abs(same_bin['output_signal_power']/same_bin['output_noise_power']-same_bin['component_power_ratio_before'])<1e-14,
    uniform_darkening_does_not_improve_ratio=uniform['input_ratio']==uniform['output_ratio'],
    existing_four_point_outputs_preserved=len(existing)==4 and all(row['existing_output_exact'] for row in existing),
    integer_rounding_exception_explicit=rounding['rounded_output_power']==0 and rounding['ideal_output_power']>0,
    frozen_sources_unchanged=not changed)
paths=['scalar_restore_v3/pc_candidate_compact/config.json',
       'scalar_restore_v3/pc_candidate_compact/weights.npz',
       'network_understanding_v1/reports/POINT_TRACE.json']
report=dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,
    scope='Gain arithmetic and previously published four-point traces; not a new quality or detection experiment',
    gain_table=rows,contrast_bounds=contrast,ideal_single_tone_harmonic_limits=harmonics,
    fixed_same_bin_example=same_bin,uniform_darkening_example=uniform,
    existing_points=existing,integer_rounding_exception=rounding,
    source_sha256={path:sha(ROOT/path) for path in paths},frozen_files_checked=len(baseline),changed_sources=changed,
    model_instantiated=False,model_parameters_modified=False,training_run=False,
    fft_run=False,feature_extraction_run=False,neural_inference_run=False,
    new_quality_test_run=False,new_holdout_opened=False,hardware_built=False,board_accessed=False)
(HERE/'reports/GAIN_LIMITS_WALKTHROUGH.json').write_text(
    json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
print(json.dumps(dict(status=report['status'],checks=checks,contrast_bounds=contrast,
    ideal_single_tone_harmonic_limits=harmonics,existing_points=existing),ensure_ascii=False))
if report['status']!='PASS':raise SystemExit(1)
