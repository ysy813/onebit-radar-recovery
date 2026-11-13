"""Verify teaching algebra by deterministic quadrature, not radar/model tests."""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
import math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent

def quant(z):
    return np.where(z.real >= 0, 1.0, -1.0) + 1j*np.where(z.imag >= 0, 1.0, -1.0)

# Integrate one ideal complex tone over phase; no discrete radar FFT is run.
count = 262144
theta = 2*np.pi*(np.arange(count)+0.173)/count
tone = np.exp(1j*theta)
q = quant(tone)
harmonics = []
for h in [-15, -11, -7, -3, 1, 5, 9, 13]:
    measured = np.mean(q*np.exp(-1j*h*theta))
    predicted = 4/(np.pi*h)
    harmonics.append(dict(order=h, measured_real=float(measured.real),
        measured_imag=float(measured.imag), predicted_real=float(predicted),
        absolute_error=float(abs(measured-predicted))))
absent = []
for h in [-5, -1, 0, 2, 3, 7]:
    measured = np.mean(q*np.exp(-1j*h*theta))
    absent.append(dict(order=h, coefficient_magnitude=float(abs(measured))))
energy = dict(total_power_per_c_squared=2.0,
    fundamental_power_per_c_squared=16/math.pi**2,
    fundamental_fraction=8/math.pi**2,
    other_harmonic_fraction=1-8/math.pi**2,
    fundamental_to_other_db=10*math.log10(8/(math.pi**2-8)),
    third_to_fundamental_power_db=20*math.log10(1/3),
    fifth_to_fundamental_power_db=20*math.log10(1/5),
    scope="Continuous ideal complex tone, phase-averaged; not a radar SNR guarantee")

# A two-tone response has combination frequencies. Double phase quadrature
# avoids pretending the discontinuous sign function has a Taylor series.
mixtures = []
for size in [512, 1024]:
    p1 = 2*np.pi*(np.arange(size)+0.173)/size
    p2 = 2*np.pi*(np.arange(size)+0.397)/size
    u1, u2 = np.exp(1j*p1)[:,None], np.exp(1j*p2)[None,:]
    joined = quant(u1+0.3*u2)
    independent = quant(u1)+quant(0.3*u2)
    rows = []
    for k, l in [(1,0), (0,1), (2,-1), (-2,-1), (1,1)]:
        carrier = np.exp(-1j*(k*p1[:,None]+l*p2[None,:]))
        mixed = np.mean(joined*carrier)
        linear = np.mean(independent*carrier)
        rows.append(dict(k=k, l=l, mixed_real=float(mixed.real),
            mixed_imag=float(mixed.imag), mixed_magnitude=float(abs(mixed)),
            sum_of_separately_quantized_magnitude=float(abs(linear))))
    mixtures.append(dict(phase_grid=size, secondary_to_primary_amplitude=0.3,
        coefficients=rows))

# Real Gaussian case: b is also derived independently from E|x|.
c, sigma = 64.0, 2.0
dx = 24*sigma/count
x = -12*sigma+(np.arange(count)+0.5)*dx
density = np.exp(-0.5*(x/sigma)**2)/(sigma*np.sqrt(2*np.pi))
sgn = np.where(x >= 0, 1.0, -1.0)
q_real = c*sgn
b = c*math.sqrt(2/math.pi)/sigma
eta = q_real-b*x
moments = dict(c=c, sigma=sigma, b_formula=b,
    b_integral=float(np.sum(q_real*x*density)*dx/(sigma*sigma)),
    eta_x_integral=float(np.sum(eta*x*density)*dx),
    eta_power_integral=float(np.sum(eta*eta*density)*dx),
    eta_power_formula=c*c*(1-2/math.pi),
    correlated_power_fraction=2/math.pi,
    residual_power_fraction=1-2/math.pi)

# Isotropic Gaussian angle is uniform. The radial factor cancels in sign.
# This is an angular integral under the stated Gaussian model, not sampling
# the radar data and not claiming the radar observations are Gaussian.
phi = 2*np.pi*(np.arange(count)+0.173)/count
arcsine = []
for rho in [-0.95, -0.75, -0.25, 0.0, 0.25, 0.75, 0.95]:
    alpha = math.acos(rho)
    empirical = np.mean(np.where(np.cos(phi) >= 0,1.0,-1.0)*
        np.where(np.cos(phi-alpha) >= 0,1.0,-1.0))
    predicted = 2/math.pi*math.asin(rho)
    arcsine.append(dict(input_correlation=rho,
        sign_correlation_integral=float(empirical),
        sign_correlation_formula=predicted,
        absolute_error=float(abs(empirical-predicted))))
colored = [dict(input_correlation=rho,
    residual_correlation=(2/math.pi)*(math.asin(rho)-rho)/(1-2/math.pi))
    for rho in [0.0, 0.5, 0.75, 0.9]]

# Two indistinguishable references: unrestricted squared-error optimum and
# the stricter zero-input restriction of the deployed multiplicative form.
labels = np.array([0.1,0.3])
ambiguity = dict(labels=labels.tolist(), same_observation=True,
    unrestricted_best_prediction=float(labels.mean()),
    irreducible_mean_squared_error=float(np.mean((labels-labels.mean())**2)),
    zero_input_multiplicative_prediction=0.0,
    zero_input_multiplicative_mean_squared_error=float(np.mean(labels**2)),
    scope="Equal-prior ideal ambiguity example; not an empirical radar bound")

# Even in a Bussgang representation, a finite realization contains a cross
# term. Uncorrelatedness is an ensemble statement, not a per-bin identity.
desired = 1+0j
distortion = -0.5+0j
cross_term = dict(desired_power=abs(desired)**2,
    distortion_power=abs(distortion)**2,
    cross_term=2*float((desired*np.conj(distortion)).real),
    actual_total_power=abs(desired+distortion)**2,
    sum_without_cross_term=abs(desired)**2+abs(distortion)**2,
    scope="Algebra example only; not samples claimed to be uncorrelated")

baseline = json.loads((HERE/'reports/SOURCE_BASELINE.json').read_text(encoding='utf-8'))
changed = []
for rel, entry in baseline.items():
    digest = hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
    if digest != entry['sha256']:
        changed.append(rel)

intermod = [row['coefficients'][2] for row in mixtures]
checks = dict(
    harmonic_coefficients=max(r['absolute_error'] for r in harmonics)<3e-5,
    absent_orders=max(r['coefficient_magnitude'] for r in absent)<1e-10,
    constant_modulus=float(np.max(np.abs(np.abs(q)**2-2)))<1e-12,
    scale_invariance=bool(np.array_equal(quant(tone),quant(10*tone))),
    intermodulation_present=all(r['mixed_magnitude']>0.1 and
        r['sum_of_separately_quantized_magnitude']<1e-10 for r in intermod),
    intermodulation_quadrature_stable=abs(intermod[0]['mixed_real']-intermod[1]['mixed_real'])<0.003,
    gaussian_projection=abs(moments['b_integral']-b)<1e-6 and
        abs(moments['eta_x_integral'])<1e-6,
    gaussian_residual_power=abs(moments['eta_power_integral']-moments['eta_power_formula'])<1e-4,
    arcsine_integral=max(r['absolute_error'] for r in arcsine)<2e-5,
    residual_not_white=colored[2]['residual_correlation']>0.1,
    ambiguity_bound=abs(ambiguity['irreducible_mean_squared_error']-0.01)<1e-14,
    per_bin_cross_term_not_discarded=cross_term['actual_total_power']!=cross_term['sum_without_cross_term'],
    frozen_sources_unchanged=not changed)
report = dict(status='PASS' if all(checks.values()) else 'FAIL', checks=checks,
    scope='Deterministic mathematical teaching checks; not a model quality, data, or hardware test',
    complex_tone_coefficients=harmonics, absent_orders=absent,
    ideal_tone_energy=energy, two_tone_phase_integrals=mixtures,
    gaussian_projection=moments, gaussian_arcsine_integrals=arcsine,
    gaussian_colored_residual_examples=colored,
    nonidentifiability_lower_bound_example=ambiguity,
    per_bin_cross_term_example=cross_term,
    frozen_files_checked=len(baseline), changed_sources=changed,
    model_parameters_modified=False, training_run=False, radar_data_fft_run=False,
    feature_extraction_run=False, neural_inference_run=False,
    new_quality_test_run=False, new_holdout_opened=False,
    hardware_built=False, board_accessed=False)
(HERE/'reports/QUANTIZATION_THEORY_WALKTHROUGH.json').write_text(
    json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
if not all(checks.values()):
    raise SystemExit(1)
