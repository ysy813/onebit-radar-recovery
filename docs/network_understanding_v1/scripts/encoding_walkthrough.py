"""Ideal feature-encoding algebra; no full features, network or radar run."""
import sys
sys.dont_write_bytecode = True
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
encoding_rows = [dict(relative_amplitude=a,relative_power=a*a,ideal_encoding=a**.2) for a in [1., .1, .01, .001]]
grid = np.r_[0., np.geomspace(1e-12, 1., 1000)]
encoded = grid**.2
inverse_relative_error = float(np.max(np.abs(encoded[1:]**5/grid[1:]-1)))
windows = {
    'constant_nine': np.full(9, .125),
    'single_peak_nine': np.r_[.5,np.zeros(8)],
    'center_below_raw_mean': np.r_[.1,1.,np.zeros(7)],
    'ramp_nine': np.linspace(0,1,9),
    'single_peak_eighty_one': np.r_[.5,np.zeros(80)]}
window_rows = []
for name, values in windows.items():
    z = values**.2
    decoded_mean = float(z.mean()**5)
    mean_amplitude = float(values.mean())
    window_rows.append(dict(name=name,window_size=len(values),center_amplitude=float(values[0]),
                            decoded_encoded_mean=decoded_mean,raw_amplitude_mean=mean_amplitude,
                            jensen_gap=mean_amplitude-decoded_mean,
                            decoded_maximum=float(z.max()**5),raw_amplitude_maximum=float(values.max()),
                            center_minus_decoded_mean=float(values[0]-decoded_mean),
                            center_minus_raw_mean=float(values[0]-mean_amplitude)))
single_peak_rows = []
for size in [9,31,81]:
    # Use peak amplitude one for exact rational accounting of the ideal mean.
    decoded_mean = Fraction(1,size)**5
    raw_mean = Fraction(1,size)
    single_peak_rows.append(dict(size=size,decoded_encoded_mean=float(decoded_mean),
                                 raw_amplitude_mean=float(raw_mean),
                                 decoded_mean_to_raw_mean=float(decoded_mean/raw_mean),
                                 exact_ratio=f'1/{size**4}',
                                 rational_identity_verified=decoded_mean/raw_mean==Fraction(1,size**4)))
gate_rows = []
for rho in [0., .25, .5, .75, 1.]:
    amplitude = .1
    encoded_gated = amplitude**.2*rho
    decoded_gated = encoded_gated**5
    expected = amplitude*rho**5
    gate_rows.append(dict(constructed_amplitude=amplitude,encoded_gate_weight=rho,
                          decoded_amplitude_feature=decoded_gated,expected_amplitude_times_rho5=expected,
                          feature_power_equivalent_ratio=rho**10,
                          identity_absolute_error=abs(decoded_gated-expected)))
max_gate_errors = []
for shift in range(5):
    values = np.array([.001,.01,.1,.5,1.])
    rho = np.roll(np.array([0.,.25,.5,.75,1.]),shift)
    max_gate_errors.append(float(abs(np.max(values**.2*rho)**5-np.max(values*rho**5))))

# Map a fixed encoded ratio to raw contrast only for this specified flat window.
threshold_rows = []
size = 81
for tau in [Fraction(7,5),Fraction(3,2),Fraction(8,5)]:
    encoding_ratio = tau*(size-1)/(size-tau)
    amplitude_ratio = encoding_ratio**5
    power_ratio = encoding_ratio**10
    center_z = .6
    background_z = center_z/float(encoding_ratio)
    mean_z = (center_z+(size-1)*background_z)/size
    ratio = center_z/mean_z
    weight = max(0.,min(1.,5*ratio-7))
    threshold_rows.append(dict(window_size=size,encoded_center_to_mean_ratio=float(tau),
                               encoded_center_to_flat_background_ratio=float(encoding_ratio),
                               raw_amplitude_center_to_flat_background_ratio=float(amplitude_ratio),
                               raw_power_center_to_flat_background_ratio=float(power_ratio),
                               raw_power_contrast_db=10*math.log10(float(power_ratio)),
                               constructed_center_encoding=center_z,constructed_background_encoding=background_z,
                               constructed_mean_encoding=mean_z,denominator_floor_inactive=mean_z>1/32,
                               recovered_center_mean_ratio=ratio,compactness_only_weight=weight))
counter = next(row for row in window_rows if row['name']=='center_below_raw_mean')
checks = dict(
    root_is_monotone_and_invertible_in_ideal_arithmetic=bool(np.all(np.diff(encoded)>0)) and inverse_relative_error<1e-13,
    compression_ratio_matches_fifth_root=abs((.1**.2/.001**.2)-100**.2)<1e-14,
    decoded_means_obey_jensen=all(row['jensen_gap']>=-1e-15 for row in window_rows),
    decoded_maxima_commute=all(abs(row['decoded_maximum']-row['raw_amplitude_maximum'])<1e-14 for row in window_rows),
    contrast_sign_counterexample_verified=counter['center_minus_decoded_mean']>0 and counter['center_minus_raw_mean']<0,
    isolated_peak_mean_gap_exact=all(row['rational_identity_verified'] for row in single_peak_rows),
    gated_decoded_feature_is_rho_to_fifth=all(row['identity_absolute_error']<1e-14 for row in gate_rows) and max(max_gate_errors)<1e-14,
    specified_flat_window_ratio_mapping_verified=all(abs(row['recovered_center_mean_ratio']-row['encoded_center_to_mean_ratio'])<1e-14 and row['denominator_floor_inactive'] for row in threshold_rows),
    compactness_transition_matches_frozen_formula=abs(threshold_rows[0]['compactness_only_weight'])<1e-13 and abs(threshold_rows[1]['compactness_only_weight']-.5)<1e-13 and abs(threshold_rows[2]['compactness_only_weight']-1)<1e-13,
    frozen_sources_unchanged=not changed)
source_files = ['scalar_restore_v3/pc_candidate_compact/restore_power.py',
                'scalar_restore_v3/pc_candidate_compact/compact_guard.py',
                'scalar_restore_v3/pc_candidate_compact/config.json']
report = dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,
              scope='Ideal fifth-root representation, Jensen inequality, gated feature and specified window algebra only',
              encoding_examples=encoding_rows,ideal_inverse_maximum_relative_error=inverse_relative_error,
              ideal_grid_points=len(grid),window_examples=window_rows,isolated_peak_exact_examples=single_peak_rows,
              encoded_gate_examples=gate_rows,gated_maximum_identity_errors=max_gate_errors,
              specified_flat_window_thresholds=threshold_rows,
              qualifications=['These are constructed amplitudes and prescribed gate weights, not neural predictions',
                              'Ideal identities have integer-approximation differences in the frozen implementation',
                              'The rho5 factor affects a feature and is not applied directly to FFT power',
                              'Raw contrast mapping applies only to one center plus eighty identical background values with inactive floor',
                              'Compactness weight alone is not the full protection condition or final gain',
                              'No SNR, physical target label or restored-quality result is inferred'],
              source_sha256={name:sha(ROOT/name) for name in source_files},
              frozen_files_checked=len(baseline),changed_sources=changed,
              constructed_algebra_run=True,model_instantiated=False,model_parameters_modified=False,
              training_run=False,radar_fft_run=False,full_feature_extraction_run=False,
              neural_inference_run=False,new_quality_test_run=False,new_holdout_opened=False,
              hardware_built=False,board_accessed=False)
(HERE/'reports/ENCODING_WALKTHROUGH.json').write_text(
    json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
print(json.dumps(dict(status=report['status'],checks=checks,contrast_counterexample=counter,
                      specified_flat_window_thresholds=threshold_rows),ensure_ascii=False))
if report['status']!='PASS':
    raise SystemExit(1)
