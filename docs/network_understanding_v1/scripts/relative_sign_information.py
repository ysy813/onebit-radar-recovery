"""Constructed two-tone sign cells and ideal power ambiguity; no radar or model."""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4*1024*1024), b""):
            h.update(block)
    return h.hexdigest()

nfft = 32
m = np.arange(nfft)
u = np.exp(1j*(2*np.pi*3*m/nfft+.23))
v = np.exp(1j*(2*np.pi*7*m/nfft+.61))
dft = np.exp(-2j*np.pi*np.outer(m,m)/nfft)/nfft

def quantize(signal):
    return 64*(np.where(signal.real>=0,1,-1)+1j*np.where(signal.imag>=0,1,-1))

def changed_components(first,second):
    return int(np.count_nonzero(first.real!=second.real)+np.count_nonzero(first.imag!=second.imag))

ratios = [0.,.1,.2,.4,.8,1.]
signals = {rho:u+rho*v for rho in ratios}
symbols = {rho:quantize(signal) for rho,signal in signals.items()}
spectra = {rho:dft@q for rho,q in symbols.items()}
powers = {rho:np.abs(spectrum)**2 for rho,spectrum in spectra.items()}
rows = []
for rho in ratios:
    reference = dft@signals[rho]
    rows.append(dict(relative_input_tone_amplitude=rho,
                     multibit_bin7_to_bin3=float(abs(reference[7])/abs(reference[3])),
                     sign_component_changes_from_rho0=changed_components(symbols[0.],symbols[rho]),
                     onebit_bin7_to_bin3=float(abs(spectra[rho][7])/abs(spectra[rho][3])),
                     onebit_power_change_max_from_rho0=float(np.max(np.abs(powers[rho]-powers[0.]))),
                     minimum_component_distance_from_zero=float(min(np.min(abs(signals[rho].real)),np.min(abs(signals[rho].imag))))))

# Every real/imag component has form a + rho*b. Its only possible sign
# change along this parameter is at rho=-a/b, when b is nonzero.
a = np.concatenate([u.real,u.imag])
b = np.concatenate([v.real,v.imag])
roots = -a[np.abs(b)>1e-14]/b[np.abs(b)>1e-14]
positive_roots = roots[(roots>0)&(roots<1)]
lo = float(max(positive_roots[positive_roots<.4]))
hi = float(min(positive_roots[positive_roots>.4]))
same_cell_samples = [.2,.4,.8]
cell_constant = all(np.array_equal(symbols[rho],symbols[.4]) for rho in same_cell_samples)

# Integer-valued symbols obey this exact circular shift identity. The ideal
# DFT shift theorem therefore proves equal power without relying on a float
# closeness test alone. This does not assert bit-accurate Xilinx power equality.
shift = 11
shift_identity = np.array_equal(symbols[.1],np.roll(symbols[0.],shift))
phase = np.exp(-2j*np.pi*m*shift/nfft)
shift_error = float(np.max(np.abs(spectra[.1]-phase*spectra[0.])))
peak = float(max(powers[0.]))
relative_power_error = float(np.max(np.abs(powers[.1]-powers[0.]))/peak)
sources = ["scalar_restore_v2/prepare_data.py",
           "scalar_restore_v3/pc_candidate_compact/restore_power.py"]
baseline = json.loads((HERE/"reports/SOURCE_BASELINE.json").read_text(encoding="utf-8-sig"))
changed = [p for p,info in baseline.items() if sha(ROOT/p) != info["sha256"]]
checks = dict(
    all_multibit_relative_tone_amplitudes_match=all(abs(row["multibit_bin7_to_bin3"]-row["relative_input_tone_amplitude"])<1e-13 for row in rows),
    chosen_examples_away_from_sign_boundaries=min(row["minimum_component_distance_from_zero"] for row in rows)>1e-4,
    relative_change_can_change_both_symbols_and_power=changed_components(symbols[0.],symbols[.2])>0
        and float(np.max(np.abs(powers[.2]-powers[0.])))>1,
    positive_global_scale_preserves_symbols=all(np.array_equal(quantize(10*signal),symbols[rho]) for rho,signal in signals.items()),
    different_relative_amplitudes_share_one_sign_cell=cell_constant and lo<.2<.4<.8<hi,
    no_component_sign_root_inside_selected_open_cell=not bool(np.any((roots>lo)&(roots<hi))),
    same_symbol_cell_has_identical_computed_power=all(np.array_equal(powers[rho],powers[.4]) for rho in same_cell_samples),
    power_ambiguity_uses_distinct_symbol_sequences=changed_components(symbols[0.],symbols[.1])==4,
    exact_integer_symbol_circular_shift_identity=bool(shift_identity),
    ideal_dft_shift_theorem_matches_numerical_sums=shift_error<1e-10 and relative_power_error<1e-13,
    frozen_sources_unchanged=not changed)
checks = {k:bool(v) for k,v in checks.items()}
report = dict(status="PASS" if all(checks.values()) else "FAIL",checks=checks,
              scope="Specified 32-sample two-tone family with ideal direct DFT; no current network or radar data evaluated",
              signal="exp(j*(2*pi*3*m/32+0.23)) + rho*exp(j*(2*pi*7*m/32+0.61))",
              quantizer="64*(sgn_plus(real)+j*sgn_plus(imag))",samples=nfft,rows=rows,
              selected_open_sign_cell=dict(lower=lo,upper=hi,checked_ratios=same_cell_samples,
                                           distinct_thresholds_in_0_to_1_rounded=sorted(set(round(float(t),12) for t in positive_roots))),
              power_only_ambiguity=dict(first_rho=0.,second_rho=.1,changed_sign_components=4,
                                        exact_circular_shift_samples=shift,
                                        maximum_complex_shift_identity_residual=shift_error,
                                        maximum_relative_power_residual=relative_power_error),
              interpretation=["A finite sign word can retain some relative-amplitude distinctions while collapsing others",
                              "Fixed-frequency fixed-phase affine sign inequalities create open constant-observation cells",
                              "Distinct sign sequences related by circular shift have equal ideal DFT power",
                              "Current power/features cannot automatically use all information present in complex sign sequences",
                              "Toy signs, thresholds and spectral ratios are not network predictions, physical target labels or generic monotonic calibration",
                              "No equality claim for the current finite-precision Xilinx FFT follows from the ideal shift example"],
              source_sha256={p:sha(ROOT/p) for p in sources},script_sha256=sha(Path(__file__)),
              frozen_files_checked=len(baseline),changed_sources=changed,
              constructed_direct_dft_run=True,radar_data_read=False,radar_fft_run=False,
              model_instantiated=False,neural_inference_run=False,feature_extraction_run=False,
              training_run=False,model_parameters_modified=False,new_quality_test_run=False,
              new_holdout_opened=False,hardware_built=False,board_accessed=False,
              original_full_quality_status_preserved="FAIL")
(HERE/"reports/RELATIVE_SIGN_INFORMATION.json").write_text(
    json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
print(json.dumps({k:report[k] for k in ["status","checks","rows","selected_open_sign_cell","power_only_ambiguity"]},ensure_ascii=False))
if report["status"] != "PASS":
    raise SystemExit(1)
