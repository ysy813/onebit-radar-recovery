"""Exact risk identities for an indistinguishable harmonic example; no model run."""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def value(v):
    return {"fraction": str(v), "decimal": float(v)}


baseline = read(HERE / "reports/SOURCE_BASELINE.json")
changed = [name for name, info in baseline.items()
           if sha(ROOT / name) != info["sha256"]]
assert not changed, changed
config = read(ROOT / "scalar_restore_v3/pc_candidate_compact/config.json")
lower, upper = [F(str(v)) for v in config["gain_range"]]
collision = read(HERE / "reports/HARMONIC_COLLISION_WALKTHROUGH.json")
assert collision["status"] == "PASS"
assert collision["checks"]["same_quantized_input_for_distinct_references"]

# For x_beta=e^(j theta)+beta e^(-j3 theta), both real and imaginary
# components equal their pure-tone component times 1-3 beta+4 beta t,
# where respectively t=cos^2(theta) or sin^2(theta). Positivity preserves
# the signs, including the unchanged exact zeros under sgn_+(0)=+1.
betas = [F(0), F(3, 10)]
factor_certificate = []
for beta in betas:
    endpoints = [1 - 3 * beta, 1 + beta]
    factor_certificate.append(dict(beta=value(beta),
                                   minimum_factor=value(min(endpoints)),
                                   maximum_factor=value(max(endpoints))))
factor_checks = all(row["minimum_factor"]["decimal"] > 0
                    for row in factor_certificate)

# The 1/3 input amplitude uses IDEAL continuous-phase Fourier coefficients,
# not a newly computed finite radar FFT or a prediction of the current MLP.
x, y_present = F(1, 3), F(3, 10)
priors = [F(1, 10), F(1, 4), F(1, 2), F(3, 4), F(9, 10)]
distributions = []
for p in priors:
    distributions.append((f"same_observation_p_{p}",
                          [(1 - p, x, F(0)), (p, x, y_present)]))
distributions.extend([
    ("variable_input", [(F(1, 3), F(1, 5), F(1, 10)),
                        (F(2, 3), F(2, 5), F(3, 10))]),
    ("upper_bound_active", [(F(1, 2), F(1, 10), F(3, 10)),
                            (F(1, 2), F(1, 10), F(1, 2))]),
    ("lower_bound_active", [(F(1, 2), F(1, 2), F(0)),
                            (F(1, 2), F(1, 2), F(1, 50))]),
])
gains = [lower, F(1, 4), F(9, 20), F(1, 2), F(29, 40), F(1), upper]
identities = nonnegative = bounded_optimum = True
cases = 0
rows = []

for name, samples in distributions:
    assert sum(p for p, _, _ in samples) == 1
    a = sum(p * xx * xx for p, xx, yy in samples)
    b = sum(p * xx * yy for p, xx, yy in samples)
    c = sum(p * yy * yy for p, xx, yy in samples)
    g0 = b / a
    gs = max(lower, min(upper, g0))
    residual = c - b * b / a
    bound_cost = a * (gs - g0) ** 2

    def risk(g):
        return sum(p * (xx * g - yy) ** 2 for p, xx, yy in samples)

    optimum = risk(gs)
    identities &= optimum == residual + bound_cost
    nonnegative &= residual >= 0 and bound_cost >= 0
    for g in gains:
        r = risk(g)
        cross = 2 * a * (g - gs) * (gs - g0)
        identities &= r == residual + a * (g - g0) ** 2
        identities &= r - optimum == a * (g - gs) ** 2 + cross
        nonnegative &= cross >= 0
        bounded_optimum &= r >= optimum
        cases += 1
    rows.append(dict(name=name, a=value(a), b=value(b), c=value(c),
                     unconstrained_gain=value(g0), bounded_gain=value(gs),
                     residual_risk=value(residual), bound_cost=value(bound_cost),
                     bounded_risk=value(optimum)))

prior_rows = []
for p in priors:
    mu = p * y_present
    g = max(lower, min(upper, mu / x))
    prior_rows.append(dict(present_probability=value(p),
                           mean_reference=value(mu), ideal_gain=value(g),
                           output_amplitude=value(x * g),
                           ambiguity_variance=value(p * (1 - p) * y_present ** 2)))

# Prescribe a halfway return toward bypass. This does not execute the
# current guard or claim that this analytic example meets its full mask.
p = F(1, 2)
g0 = (p * y_present) / x
lam = F(1, 2)
g_protected = (1 - lam) * g0 + lam
pred, protected = x * g0, x * g_protected
before_absent, after_absent = pred ** 2, protected ** 2
before_present = (pred - y_present) ** 2
after_present = (protected - y_present) ** 2
before = (before_absent + before_present) / 2
after = (after_absent + after_present) / 2
bypass = ((x - F(0)) ** 2 + (x - y_present) ** 2) / 2
protection = dict(prescribed_return_fraction=value(lam),
                  before_gain=value(g0), after_gain=value(g_protected),
                  before_output=value(pred), after_output=value(protected),
                  absent_error_before=value(before_absent), absent_error_after=value(after_absent),
                  present_error_before=value(before_present), present_error_after=value(after_present),
                  mean_error_before=value(before), mean_error_after=value(after),
                  mean_bypass_error=value(bypass),
                  mean_error_increase=value(after - before),
                  exact_increase=value((protected - pred) ** 2),
                  actual_guard_executed=False, actual_guard_mask_inferred=False)

# A gain ideal for one prescribed class frequency need not be ideal after
# that frequency changes, even when the observed input remains identical.
p_test = F(1, 10)
g_test = max(lower, min(upper, p_test * y_present / x))


def test_risk(g):
    return (1 - p_test) * (x * g) ** 2 + p_test * (x * g - y_present) ** 2


prior_shift = dict(training_present_probability=value(F(1, 2)),
                   new_present_probability=value(p_test),
                   inherited_ideal_gain=value(g0), new_ideal_gain=value(g_test),
                   inherited_gain_new_risk=value(test_risk(g0)),
                   new_bounded_optimum_risk=value(test_risk(g_test)),
                   actual_training_distribution_estimated=False)

zero_samples = [(F(1, 2), F(0)), (F(1, 2), F(3, 10))]
zero_risks = [sum(p * (F(0) * g - y) ** 2 for p, y in zero_samples)
              for g in gains]
checks = dict(
    source_gain_bounds_match=lower == F(1, 8) and upper == F(3, 2),
    prior_collision_evidence_pass=collision["status"] == "PASS",
    positive_factor_sign_certificate=factor_checks,
    risk_decomposition_exact=bool(identities),
    residual_bound_and_projection_terms_nonnegative=bool(nonnegative),
    bounded_optimum_matches_all_comparisons=bool(bounded_optimum),
    zero_input_risk_independent_of_gain=len(set(zero_risks)) == 1,
    ambiguous_pair_optimal_average_improves_bypass=before < bypass,
    protection_can_reduce_present_case_error=after_present < before_present,
    protection_can_increase_absent_case_and_average_error=(after_absent > before_absent and after > before),
    protection_risk_increase_exact=after - before == (protected - pred) ** 2,
    prescribed_prior_shift_changes_ideal_gain_and_risk=test_risk(g0) > test_risk(g_test),
    original_quality_fail_preserved=config["quality_test_status"] == "FAIL",
    frozen_sources_unchanged=not changed,
)
sources = ["scalar_restore_v3/pc_candidate_compact/config.json",
           "network_understanding_v1/reports/HARMONIC_COLLISION_WALKTHROUGH.json"]
report = dict(status="PASS" if all(checks.values()) else "FAIL", checks=checks,
              scope="Exact rational teaching example, not current-model inference or a new quality experiment",
              sign_factor_certificate=factor_certificate,
              distributions_checked=len(distributions), risk_comparisons=cases,
              risk_rows=rows, same_observation_prior_examples=prior_rows,
              prescribed_protection_example=protection, prescribed_prior_shift=prior_shift,
              assumptions=["Ideal continuous-phase harmonic amplitudes; no finite radar FFT computed",
                           "Class probabilities are prescribed, not estimated from real data",
                           "Squared-amplitude risk, not the eight-term actual training objective",
                           "A clipped risk optimum is not a claimed output of the frozen MLP",
                           "A halfway return is prescribed; current guard masks were not evaluated",
                           "Risk identities do not estimate the current model's irreducible error"],
              source_sha256={name: sha(ROOT / name) for name in sources},
              script_sha256=sha(Path(__file__)),
              frozen_files_checked=len(baseline), changed_sources=changed,
              exact_constructed_algebra_run=True, model_instantiated=False,
              model_parameters_modified=False, training_run=False, radar_fft_run=False,
              feature_extraction_run=False, neural_inference_run=False,
              actual_guard_run=False, new_quality_test_run=False,
              new_holdout_opened=False, hardware_built=False, board_accessed=False)
(HERE / "reports/AMBIGUITY_RISK_WALKTHROUGH.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
print(json.dumps(dict(status=report["status"], checks=checks,
                      distributions_checked=len(distributions), risk_comparisons=cases,
                      prior_examples=prior_rows, protection=protection, prior_shift=prior_shift),
                 ensure_ascii=False))
if report["status"] != "PASS":
    raise SystemExit(1)
