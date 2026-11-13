"""Sign-statistics teaching by analytic integration; no radar or network run."""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from scipy.integrate import quad
from scipy.special import erf

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
scale = 64.
k = math.sqrt(2 / math.pi)
cdf_rows = []
for u in [-4., -2., -1., -.2, 0., .2, 1., 2., 4.]:
    probability = .5 * math.erfc(-u / math.sqrt(2))
    integral, error = quad(lambda z: math.exp(-z * z / 2) / math.sqrt(2 * math.pi), -u, math.inf,
                           epsabs=1e-13, epsrel=1e-13)
    mean = math.erf(u / math.sqrt(2))
    h = 1e-5
    finite_derivative = (math.erf((u+h)/math.sqrt(2))-math.erf((u-h)/math.sqrt(2)))/(2*h)
    derivative = k * math.exp(-u * u / 2)
    cdf_rows.append(dict(signal_to_known_sigma=u, probability_positive=probability,
                         independently_integrated_probability=integral,
                         integral_absolute_error=abs(probability-integral),
                         normalized_mean=mean, actual_level_mean=scale*mean,
                         bernoulli_mean_matches=abs((2*probability-1)-mean)<1e-14,
                         derivative=derivative, finite_difference_derivative=finite_derivative,
                         derivative_absolute_error=abs(derivative-finite_derivative)))

# Integrate the conditional mean over deterministic tone phase, not a radar FFT.
count = 32768
theta = 2*np.pi*(np.arange(count)+.173)/count
rows = []
for a in [.025, .05, .1, .2, .5, 1., 2., 5., 20., 100.]:
    conditional_mean = erf(a*np.cos(theta)/math.sqrt(2)) + 1j*erf(a*np.sin(theta)/math.sqrt(2))
    coefficients = {h:complex(np.mean(conditional_mean*np.exp(-1j*h*theta))) for h in [1, -3, 5]}
    linear_fundamental = k*a
    cubic_fundamental = k*(a-a**3/8)
    cubic_third = -k*a**3/24
    rows.append(dict(amplitude_to_known_per_component_sigma=a,
                     small_signal_expansion_check_applied=a<=.2,
                     coefficients=[dict(order=h,real=v.real,imaginary=v.imag) for h,v in coefficients.items()],
                     linear_fundamental=linear_fundamental, cubic_fundamental=cubic_fundamental,
                     cubic_third=cubic_third,
                     fundamental_relative_linear_error=abs(coefficients[1].real-linear_fundamental)/linear_fundamental,
                     fundamental_absolute_cubic_error=abs(coefficients[1].real-cubic_fundamental),
                     third_relative_cubic_error=abs(coefficients[-3].real-cubic_third)/abs(cubic_third),
                     third_to_fundamental_ratio=coefficients[-3].real/coefficients[1].real))

# Derive the complex cubic expansion independently from the two component polynomials.
polynomial_residuals = []
for a in [.025, .1, .2, .5]:
    component_polynomial = k*(a*np.cos(theta)-a**3*np.cos(theta)**3/6) + 1j*k*(a*np.sin(theta)-a**3*np.sin(theta)**3/6)
    harmonic_polynomial = k*((a-a**3/8)*np.exp(1j*theta)-a**3/24*np.exp(-3j*theta))
    polynomial_residuals.append(float(np.max(np.abs(component_polynomial-harmonic_polynomial))))

u = .2
normalized_mean = math.erf(u/math.sqrt(2))
averages = [dict(independent_identical_repetitions=m, output_mean=scale*normalized_mean,
                 standard_deviation_of_mean=scale*math.sqrt((1-normalized_mean**2)/m)) for m in [1, 100, 10000]]
weak_rows = [row for row in rows if row['amplitude_to_known_per_component_sigma'] <= .2]
strong = rows[-1]
checks = dict(
    sign_probability_matches_independent_gaussian_quadrature=max(row['integral_absolute_error'] for row in cdf_rows)<1e-12,
    sign_mean_and_derivative_verified=all(row['bernoulli_mean_matches'] for row in cdf_rows) and max(row['derivative_absolute_error'] for row in cdf_rows)<1e-9,
    weak_signal_expected_fundamental_nearly_proportional=all(row['fundamental_relative_linear_error']<.005 for row in weak_rows),
    third_order_complex_harmonic_identity_verified=max(polynomial_residuals)<1e-14,
    weak_third_harmonic_expansion_matches=all(row['third_relative_cubic_error']<.008 for row in weak_rows),
    conditional_mean_coefficients_real_by_symmetry=max(abs(c['imaginary']) for row in rows for c in row['coefficients'])<1e-12,
    strong_signal_limit_approaches_noiseless_single_tone=all(abs(c['real']-4/(math.pi*c['order']))<.0005 for c in strong['coefficients']),
    repeated_measurement_mean_variance_has_expected_scaling=abs(averages[0]['standard_deviation_of_mean']/averages[1]['standard_deviation_of_mean']-10)<1e-12 and abs(averages[1]['standard_deviation_of_mean']/averages[2]['standard_deviation_of_mean']-10)<1e-12,
    frozen_sources_unchanged=not changed)
source_files = ['scalar_restore_v2/prepare_data.py', 'scalar_restore_v3/pc_candidate_compact/restore_power.py',
                'scalar_restore_v3/pc_candidate_compact/config.json']
report = dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,
              scope='Known-Gaussian conditional sign information, analytic moments and mathematical phase quadrature only',
              hypotheses=['Real component observation is s+n, with fixed s and n Gaussian(0,sigma^2)',
                          'Complex example has signal A exp(j theta) and Gaussian noise of per-component standard deviation sigma',
                          'Repeated-measurement variance assumes independent identically distributed noise at fixed s',
                          'Known fixed sigma supplies a statistical amplitude reference absent from arbitrary sign observations',
                          'Current network does not estimate sigma, invert erf or reconstruct the conditional complex mean'],
              cdf_cases=cdf_rows,complex_tone_phase_samples=count,complex_tone_cases=rows,
              cubic_identity_maximum_errors=polynomial_residuals,independent_repetition_examples=averages,
              qualifications=['Expected spectrum is not the spectrum of every individual quantized frame',
                              'The cubic polynomial is a weak-amplitude expansion; large-a entries are not valid signal predictions',
                              'Power of conditional mean is not expected power',
                              'Information surviving in signs need not all survive power and 40-dimensional feature compression',
                              'Unknown deterministic harmonic collisions remain nonidentifiable',
                              'No claim that adding noise improves the current radar chain or model',
                              'No new quality, detection-rate or SNR result'],
              source_sha256={name:sha(ROOT/name) for name in source_files},
              frozen_files_checked=len(baseline),changed_sources=changed,
              deterministic_mathematical_quadrature_run=True,random_sampling_run=False,
              model_instantiated=False,model_parameters_modified=False,training_run=False,
              radar_fft_run=False,feature_extraction_run=False,neural_inference_run=False,
              new_quality_test_run=False,new_holdout_opened=False,hardware_built=False,board_accessed=False)
(HERE/'reports/WEAK_INFORMATION_WALKTHROUGH.json').write_text(
    json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
print(json.dumps(dict(status=report['status'],checks=checks,
                      selected_cdf_cases=[row for row in cdf_rows if abs(row['signal_to_known_sigma'])<=.2],
                      selected_tone_cases=[row for row in rows if row['amplitude_to_known_per_component_sigma'] in [.1,.2,100]],
                      independent_repetition_examples=averages),ensure_ascii=False))
if report['status']!='PASS':
    raise SystemExit(1)
