"""Finite-observation DFT identities on constructed tones; no radar FFT or model."""
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

def response(length, nfft, offsets):
    """Magnitude / L; the expression is used away from removable N-period poles."""
    d = np.asarray(offsets, dtype="f8")
    return np.abs(np.sinc(length*d/nfft)/np.sinc(d/nfft))

def direct(length, nfft, offsets):
    m = np.arange(length, dtype="f8")
    return np.abs(np.exp(-2j*np.pi*np.asarray(offsets)[:,None]*m/nfft).sum(axis=1))/length

nfft = 512
offsets = np.array([0,.5,1,2,3,4], dtype="f8")
rows = []
maximum_error = 0.0
for length in [128,512]:
    dense_offsets = np.linspace(-12,12,193)
    maximum_error = max(maximum_error, float(np.max(np.abs(
        response(length,nfft,dense_offsets)-direct(length,nfft,dense_offsets)))))
    rows.append(dict(valid_chirps=length, padded_dft_length=nfft,
                     first_zero_offset_bins=nfft/length,
                     relative_amplitudes=[dict(offset_bins=float(d),amplitude=float(v))
                                          for d,v in zip(offsets,response(length,nfft,offsets))]))

# A pure multibit tone between DFT bins has neighboring nonzero samples
# without any quantizer or nonlinear processing.
frequency = 37.25
sample_bins = np.array([36,37,38,39])
off_grid = dict(constructed_tone_frequency_in_512_grid=frequency,
               valid_chirps=512, sampled_bins=sample_bins.tolist(),
               relative_amplitudes=response(512,512,sample_bins-frequency).tolist())

# Rectangular 2D observation is separable. Verify directly with a small
# constructed aperture; neither this sum nor the 1D sums read radar data.
nr, na, lr, la = 32,16,13,7
dr, da = .75,-1.25
phase = np.exp(-2j*np.pi*(dr*np.arange(lr)[:,None]/nr+da*np.arange(la)[None,:]/na))
direct_2d = float(abs(phase.sum())/(lr*la))
separable_2d = float(response(lr,nr,[dr])[0]*response(la,na,[da])[0])
sources = ["scalar_restore_v2/prepare_data.py",
           "radar1_v7_fullrange_compare_v2/xfft_model.py",
           "scalar_restore_v3/pc_candidate_compact/restore_power.py"]
source_text = {p:(ROOT/p).read_text(encoding="utf-8") for p in sources}
baseline = json.loads((HERE/"reports/SOURCE_BASELINE.json").read_text(encoding="utf-8-sig"))
changed = [p for p,info in baseline.items() if sha(ROOT/p) != info["sha256"]]
restore_text = source_text[sources[2]]
checks = dict(
    closed_form_matches_direct_sums=maximum_error < 1e-13,
    first_zeros_match=all(response(l,512,[512/l])[0] < 1e-14 for l in [128,512]),
    shorter_aperture_neighbors_nonzero=response(128,512,[1])[0] > .9,
    full_aperture_integer_neighbor_zero=response(512,512,[1])[0] < 1e-14,
    off_grid_multibit_tone_has_nonzero_neighbors=all(v>.1 for v in off_grid["relative_amplitudes"]),
    two_dimensional_product_matches=abs(direct_2d-separable_2d) < 1e-14,
    paired_source_quantizes_before_padding=source_text[sources[0]].index("one=np.where") < source_text[sources[0]].index("if n!=512:echo=np.pad"),
    chirp_count_passed_to_guards_not_mlp="def predict_gain_q14(self,features_q12):" in restore_text
        and "self.predict_gain_q14(f),self.config.get('power_guard'),f,actual_chirps" in restore_text
        and "compact_peak_skip(p,g,f,actual_chirps)" in restore_text,
    frozen_sources_unchanged=not changed,
)
checks = {k:bool(v) for k,v in checks.items()}
result = dict(status="PASS" if all(checks.values()) else "FAIL",checks=checks,
              scope="Constructed rectangular-observation DFT mathematics and source reading only",
              assumption="No window weighting beyond the finite rectangular observation; ideal linear DFT",
              rows=rows,off_grid_multibit_example=off_grid,
              maximum_closed_form_error=maximum_error,
              separable_2d_example=dict(direct_magnitude=direct_2d,product_magnitude=separable_2d),
              interpretation=["Finite-observation sidelobes exist in multibit references without sign quantization",
                              "Zero padding samples the same finite-observation spectrum more densely; no added observations",
                              "The table is not a current network gain, a physical scene diagnosis, or a quality result",
                              "The current MLP has no separate chirp-count argument; fixed guards receive the count"],
              source_sha256={p:sha(ROOT/p) for p in sources},script_sha256=sha(Path(__file__)),
              frozen_files_checked=len(baseline),changed_sources=changed,
              constructed_direct_dft_run=True,radar_data_read=False,radar_fft_run=False,
              feature_extraction_run=False,model_instantiated=False,neural_inference_run=False,
              guard_run=False,training_run=False,model_parameters_modified=False,
              new_quality_test_run=False,new_holdout_opened=False,hardware_built=False,board_accessed=False,
              original_full_quality_status_preserved="FAIL")
(HERE/"reports/APERTURE_SIDELOBE_WALKTHROUGH.json").write_text(
    json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
print(json.dumps({k:result[k] for k in ["status","checks","rows","off_grid_multibit_example",
                                       "maximum_closed_form_error"]},ensure_ascii=False))
if result["status"] != "PASS":
    raise SystemExit(1)
