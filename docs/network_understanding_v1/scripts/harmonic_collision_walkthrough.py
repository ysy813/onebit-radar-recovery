"""Analytic target/harmonic ambiguity and existing coordinate evidence only."""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
import math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4*1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def quant(signal):
    return np.where(signal.real >= 0,1,-1)+1j*np.where(signal.imag >= 0,1,-1)

count = 65536
theta = 2*np.pi*(np.arange(count)+0.137)/count
main = np.exp(1j*theta)
q0 = quant(main)
coefficient_main = np.mean(q0*np.exp(-1j*theta))
families = []
for order, betas, outside, interval in [
        (-3,[-0.9,-0.3,0.0,0.1,0.3],[-1.1,0.4],[-1.0,1/3]),
        (5,[-0.15,0.0,0.2,0.7],[-0.25,0.9],[-1/5,4/5])]:
    rows = []
    for beta in betas+outside:
        signal = main+beta*np.exp(1j*order*theta)
        if order == -3:
            real_factor = 1-3*beta+4*beta*np.cos(theta)**2
            imag_factor = 1-3*beta+4*beta*np.sin(theta)**2
            factor_lower_bound = 1-3*beta if beta >= 0 else 1+beta
        else:
            real_factor = 1+beta*(16*np.cos(theta)**4-20*np.cos(theta)**2+5)
            imag_factor = 1+beta*(16*np.sin(theta)**4-20*np.sin(theta)**2+5)
            factor_lower_bound = 1-1.25*beta if beta >= 0 else 1+5*beta
        factor_error = max(float(np.max(np.abs(signal.real-np.cos(theta)*real_factor))),
            float(np.max(np.abs(signal.imag-np.sin(theta)*imag_factor))))
        reference_coefficient = np.mean(signal*np.exp(-1j*order*theta))
        reference_main = np.mean(signal*np.exp(-1j*theta))
        q = quant(signal)
        quantized_coefficient = np.mean(q*np.exp(-1j*order*theta))
        q_main = np.mean(q*np.exp(-1j*theta))
        rows.append(dict(beta=beta,inside_open_interval=bool(beta in betas),
            factor_lower_bound=factor_lower_bound,
            trigonometric_factor_identity_error=factor_error,
            component_sign_changes=int(np.count_nonzero(q.real!=q0.real)+np.count_nonzero(q.imag!=q0.imag)),
            same_full_quantized_sequence=bool(np.array_equal(q,q0)),
            ideal_multibit_relative_amplitude=abs(beta),
            multibit_relative_amplitude_integral=float(abs(reference_coefficient)/abs(reference_main)),
            onebit_relative_amplitude_integral=float(abs(quantized_coefficient)/abs(q_main)),
            ideal_same_input_relative_amplitude=1/abs(order),
            desired_gain_if_reference_were_known=abs(order)*abs(beta),
            best_bounded_gain_if_reference_were_known=min(1.5,max(0.125,abs(order)*abs(beta))),
            desired_gain_is_model_prediction=False))
    families.append(dict(order=order,real_beta_open_interval=interval,
        baseline_onebit_relative_amplitude_integral=float(abs(np.mean(q0*np.exp(-1j*order*theta)))/abs(coefficient_main)),
        rows=rows))

# These identities are pointwise. Instantiate the current 1024 x 512 grid
# without running an FFT, constructing features, or invoking the network.
r, a = np.ogrid[:1024,:512]
base_bin = [211,37]
phase_2d = 2*np.pi*(base_bin[0]*r/1024+base_bin[1]*a/512)+0.137
main_2d = np.exp(1j*phase_2d)
q2d = quant(main_2d)
adc_scale = 10000
adc_main_i = np.rint(adc_scale*main_2d.real).astype(np.int32)
adc_main_q = np.rint(adc_scale*main_2d.imag).astype(np.int32)
adc_main = adc_main_i+1j*adc_main_q
grid_examples = []
for order,beta in [(-3,0.3),(5,0.7)]:
    signal = main_2d+beta*np.exp(1j*order*phase_2d)
    candidate = quant(signal)
    adc_i = np.rint(adc_scale*signal.real).astype(np.int32)
    adc_q = np.rint(adc_scale*signal.imag).astype(np.int32)
    adc_signal = adc_i+1j*adc_q
    grid_examples.append(dict(order=order,beta=beta,base_bin=base_bin,
        component_bin=[order*base_bin[0]%1024,order*base_bin[1]%512],
        grid=[1024,512],same_full_quantized_sequence=bool(np.array_equal(candidate,q2d)),
        constructed_integer_iq=dict(scale=adc_scale,
            max_abs_component=int(max(np.abs(adc_i).max(),np.abs(adc_q).max())),
            original_multibit_components_changed=int(np.count_nonzero(adc_i!=adc_main_i)+np.count_nonzero(adc_q!=adc_main_q)),
            fits_signed_int16=bool(np.min(adc_i)>=-32768 and np.max(adc_i)<=32767 and np.min(adc_q)>=-32768 and np.max(adc_q)<=32767),
            same_quantized_sequence=bool(np.array_equal(quant(adc_signal),quant(adc_main))),
            same_as_ideal_quantized_sequence=bool(np.array_equal(quant(adc_signal),q2d)),
            scope='Constructed rounded integer I/Q; not measured ADC or a radar quality test')))

feature_path = HERE/'reports/FEATURE_WALKTHROUGH.json'
features = read(feature_path)
point = next(row for row in features['actual_point_checks'] if row['position']==[774,511])
parent = next(row for row in point['parent_details'] if row['order']==-3)
observed = point['position']
strong = parent['winner']['support_source']
mapped = [-3*strong[0]%1024,-3*strong[1]%512]
inverse = [pow(-3,-1,1024),pow(-3,-1,512)]
strict_parent = [inverse[0]*observed[0]%1024,inverse[1]*observed[1]%512]
strict_back = [-3*strict_parent[0]%1024,-3*strict_parent[1]%512]
offset = [(observed[0]-mapped[0]+512)%1024-512,
          (observed[1]-mapped[1]+256)%512-256]
coordinate = dict(source='Existing feature report, no new network evaluation',
    observed_bin=observed,strong_support_bin=strong,
    strong_support_exact_third_bin=mapped,observed_offset_periodic=offset,
    exact_modular_inverse=inverse,
    strict_integer_inverse_of_observed=strict_parent,
    strict_parent_maps_back=strict_back,
    tolerance_query_winner=parent['winner'],
    enumerated_candidate_count=len(parent['candidates']),
    actual_input_relative_amplitude=point['physical_relative_amplitude'],
    existing_mlp_gain=point['raw_gain'],existing_final_gain=point['final_gain'],
    ideal_unrounded_output_relative_amplitude=point['physical_relative_amplitude']*point['final_gain'],
    gain_power_ratio=point['final_gain']**2,
    power_change_db=20*math.log10(point['final_gain']),
    true_target_status='Unknown; an association and a gain do not identify physical truth')

baseline = read(HERE/'reports/SOURCE_BASELINE.json')
changed = [rel for rel,entry in baseline.items() if digest(ROOT/rel)!=entry['sha256']]
inside = [row for family in families for row in family['rows'] if row['inside_open_interval']]
outside = [row for family in families for row in family['rows'] if not row['inside_open_interval']]
checks = dict(
    trigonometric_factorizations=all(row['trigonometric_factor_identity_error']<1e-12 for family in families for row in family['rows']),
    analytic_factor_bounds_positive=all(row['factor_lower_bound']>0 for row in inside),
    same_quantized_input_for_distinct_references=all(row['same_full_quantized_sequence'] for row in inside),
    outside_examples_change_symbols=all(row['component_sign_changes']>0 for row in outside),
    reference_amplitudes_verified=all(abs(row['ideal_multibit_relative_amplitude']-row['multibit_relative_amplitude_integral'])<1e-12 for row in inside),
    expected_onebit_harmonic_ratios=all(abs(row['onebit_relative_amplitude_integral']-row['ideal_same_input_relative_amplitude'])<1e-6 for row in inside),
    current_size_grid_examples_identical=all(row['same_full_quantized_sequence'] for row in grid_examples),
    integer_iq_examples_identical_after_onebit=all(row['constructed_integer_iq']['fits_signed_int16'] and row['constructed_integer_iq']['same_quantized_sequence'] and row['constructed_integer_iq']['same_as_ideal_quantized_sequence'] and row['constructed_integer_iq']['original_multibit_components_changed']>0 for row in grid_examples),
    strict_modular_inverse_verified=strict_back==observed and inverse==[341,341],
    neighbor_tolerance_explains_existing_query=mapped==[775,0] and offset==[-1,-1] and strict_parent==[766,171] and strong==[83,0] and len(parent['candidates'])==9,
    existing_strong_attenuation_reproduced=point['final_gain']==0.125 and coordinate['gain_power_ratio']==1/64,
    source_frozen_files_unchanged=not changed)
report = dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,
    scope='Analytic target/harmonic ambiguity, numerical teaching demonstrations and existing coordinate record only',
    phase_samples=count,quantizer_c=1,analytic_families=families,
    signed_beta_meaning='Real coefficient; negative beta means a pi phase shift, not negative power',
    grid_demonstrations=grid_examples,existing_coordinate_example=coordinate,
    source_sha256={str(feature_path.relative_to(ROOT)).replace('\\','/'):digest(feature_path)},
    frozen_files_checked=len(baseline),changed_sources=changed,
    model_parameters_modified=False,training_run=False,radar_data_fft_run=False,
    feature_extraction_run=False,neural_inference_run=False,
    new_quality_test_run=False,new_holdout_opened=False,hardware_built=False,board_accessed=False)
(HERE/'reports/HARMONIC_COLLISION_WALKTHROUGH.json').write_text(
    json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=report['status'],checks=checks,
    inside_examples=len(inside),outside_examples=len(outside),
    third_interval=families[0]['real_beta_open_interval'],
    fifth_interval=families[1]['real_beta_open_interval'],
    existing_coordinate_example=coordinate),ensure_ascii=False))
if not all(checks.values()):
    raise SystemExit(1)
