"""Exact-zero and padding mathematics for the frozen input convention.

Only constructed integer samples, small direct DFTs and a rectangular padding
indicator are evaluated. No radar BIN, model or training pair is processed.
"""
import sys
sys.dont_write_bytecode = True
import ast
import hashlib
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
SOURCE = ROOT/'scalar_restore_v2/prepare_data.py'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4*1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


baseline = read(HERE/'reports/SOURCE_BASELINE.json')
changed = [path for path, info in baseline.items() if sha(ROOT/path) != info['sha256']]
assert not changed, changed
tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
save_pair = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name=='save_pair')
one_node = next(n for n in save_pair.body if isinstance(n, ast.Assign) and any(
    isinstance(target,ast.Name) and target.id=='one' for target in n.targets))
padding_node = next(n for n in save_pair.body if isinstance(n,ast.If) and
    isinstance(n.test,ast.Compare) and isinstance(n.test.left,ast.Name) and n.test.left.id=='n')
one_code = compile(ast.Expression(one_node.value), str(SOURCE), 'eval')


def source_quant(echo):
    return eval(one_code, {'__builtins__':{}}, dict(np=np,echo=echo))


c = 64
values = np.arange(-8,9)
echo = values[:,None]+1j*values[None,:]
q_plus = source_quant(echo)
zero_i,zero_q = echo.real==0, echo.imag==0
q_center = c*np.sign(echo.real)+1j*c*np.sign(echo.imag)
zero_component = c*(zero_i+1j*zero_q)
sample_identity = np.array_equal(q_plus-q_center,zero_component)

distributions = []
for name, samples, counts in [
        ('对称且无零值',[-2,-1,0,1,2],[1,3,0,3,1]),
        ('对称且含零值',[-2,-1,0,1,2],[1,3,2,3,1]),
        ('均值为零但不对称',[-2,1],[1,2]),
        ('全零有效采样',[0],[1])]:
    samples=np.asarray(samples); counts=np.asarray(counts)
    probabilities=counts/counts.sum()
    positive=float(probabilities[samples>0].sum())
    negative=float(probabilities[samples<0].sum())
    zero=float(probabilities[samples==0].sum())
    measured=float((c*np.where(samples>=0,1,-1)*probabilities).sum())
    symmetric=all(abs(float(probabilities[samples==v].sum())-float(probabilities[samples==-v].sum()))<1e-14 for v in samples)
    distributions.append(dict(name=name,input_mean=float((samples*probabilities).sum()),
        p_positive=positive,p_negative=negative,p_zero=zero,symmetric=symmetric,
        quantized_mean=measured,mean_from_general_identity=c*(positive-negative+zero),
        symmetric_zero_only_formula=c*zero if symmetric else None))

# A constructed integer grid; the centered sign is an algebraic decomposition,
# not a proposal to replace the user's two-level rule.
rng=np.random.default_rng(20261104)
small=rng.integers(-4,5,size=(16,16))+1j*rng.integers(-4,5,size=(16,16))
q0=c*np.sign(small.real)+1j*c*np.sign(small.imag)
qp=source_quant(small)
indicator=c*((small.real==0)+1j*(small.imag==0))
index=np.arange(16)
dft=np.exp(-2j*np.pi*index[:,None]*index[None,:]/16)
transform=lambda x:dft@x@dft.T
z0,zp,dz=map(transform,[q0,qp,indicator])
power0,powerp=np.abs(z0)**2,np.abs(zp)**2
cross=2*np.real(z0*np.conj(dz))
zero_decomposition=dict(shape=[16,16],scope='Constructed integer grid with direct unnormalized DFT; not radar data',
    i_zero_count=int((small.real==0).sum()),q_zero_count=int((small.imag==0).sum()),
    sample_identity_exact=bool(np.array_equal(qp-q0,indicator)),
    maximum_frequency_identity_error=float(np.max(np.abs(zp-z0-dz))),
    maximum_power_expansion_error=float(np.max(np.abs(powerp-(power0+np.abs(dz)**2+cross)))),
    non_dc_indicator_bins=int(np.count_nonzero(np.abs(dz[1:])>1e-7)+np.count_nonzero(np.abs(dz[0,1:])>1e-7)),
    bins_power_increased=int(np.count_nonzero(powerp-power0>1e-6)),
    bins_power_decreased=int(np.count_nonzero(powerp-power0 < -1e-6)))

nr,na,valid=1024,512,128
padding=np.arange(na)>=valid
phase=np.exp(-2j*np.pi*np.arange(na)[:,None]*np.arange(na)[None,:]/na)
direct=phase@padding.astype('f8')
k=np.arange(1,na)
closed=np.empty(na,dtype='c16');closed[0]=na-valid
closed[1:]=np.exp(-2j*np.pi*k*valid/na)*(1-np.exp(-2j*np.pi*k*(na-valid)/na))/(1-np.exp(-2j*np.pi*k/na))
frequency_delta=nr*c*(1+1j)*direct
total_error_power=float(np.abs(frequency_delta)**2@np.ones(na))
dc_error_power=float(abs(frequency_delta[0])**2)
padding_examples=[]
for column in [0,1,2,3,4,5,8,128,256,511]:
    padding_examples.append(dict(natural_range_bin=0,natural_doppler_bin=column,
        relative_amplitude_to_padding_dc=float(abs(direct[column])/abs(direct[0]))))
padding_report=dict(scope='Hypothetical quantize-after-padding error; current source quantizes before padding',
    shape=[nr,na],valid_chirps=valid,missing_chirps=na-valid,
    missing_complex_sample_value_if_misquantized=[c,c],
    maximum_closed_form_error=float(np.max(np.abs(direct-closed))),
    ideal_error_support_range_bin=0,
    dc_fraction_of_error_spectral_energy=dc_error_power/total_error_power,
    expected_dc_energy_fraction=(na-valid)/na,
    nonzero_multiple_of_four_doppler_bins_are_zeros=bool(np.all(np.abs(direct[4::4])<1e-8)),
    examples=padding_examples,
    windowing_and_fixed_point_fft_not_modelled=True,
    no_claim_this_error_exists_in_current_runtime=True)

# Explicitly compare both operation orders on invented, nonzero valid samples.
valid_samples=np.full((2,valid),3-2j)
correct=np.pad(source_quant(valid_samples),((0,0),(0,na-valid)))
incorrect=source_quant(np.pad(valid_samples,((0,0),(0,na-valid))))
ordering_difference=incorrect-correct

checks=dict(
    all_289_complex_integer_cases_match_zero_indicator_identity=sample_identity and echo.size==289,
    general_mean_formula_verified=all(abs(row['quantized_mean']-row['mean_from_general_identity'])<1e-12 for row in distributions),
    symmetric_zero_mass_formula_verified=all(abs(row['quantized_mean']-row['symmetric_zero_only_formula'])<1e-12 for row in distributions if row['symmetric']),
    zero_mean_alone_not_sufficient=abs(distributions[2]['input_mean'])<1e-14 and distributions[2]['quantized_mean']>0 and distributions[2]['p_zero']==0,
    zero_indicator_frequency_and_power_identity=zero_decomposition['maximum_frequency_identity_error']<1e-9 and zero_decomposition['maximum_power_expansion_error']<1e-6,
    zero_indicator_is_not_only_dc=zero_decomposition['non_dc_indicator_bins']>0,
    zero_convention_not_monotonic_in_each_bin_power=zero_decomposition['bins_power_increased']>0 and zero_decomposition['bins_power_decreased']>0,
    padding_closed_form_verified=padding_report['maximum_closed_form_error']<1e-8,
    padding_error_dc_energy_fraction_verified=abs(padding_report['dc_fraction_of_error_spectral_energy']-.75)<1e-12,
    padding_error_periodic_zeros_verified=padding_report['nonzero_multiple_of_four_doppler_bins_are_zeros'],
    source_operation_order_verified=save_pair.body.index(one_node)<save_pair.body.index(padding_node),
    two_operation_orders_have_expected_difference=bool(np.all(ordering_difference[:,:valid]==0) and np.all(ordering_difference[:,valid:]==c*(1+1j))),
    frozen_sources_unchanged=not changed)
paths=['scalar_restore_v2/prepare_data.py','scalar_restore_v3/pc_candidate_compact/restore_power.py']
report=dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,
    scope='Input-convention mathematics; no quantizer change or model-quality experiment',
    distributions=distributions,zero_indicator_direct_dft=zero_decomposition,hypothetical_padding_error=padding_report,
    source_sha256={path:sha(ROOT/path) for path in paths},frozen_files_checked=len(baseline),changed_sources=changed,
    constructed_direct_dft_run=True,radar_data_fft_run=False,model_instantiated=False,
    model_parameters_modified=False,quantizer_rule_modified=False,training_run=False,
    feature_extraction_run=False,neural_inference_run=False,new_quality_test_run=False,
    new_holdout_opened=False,hardware_built=False,board_accessed=False)
(HERE/'reports/ZERO_CONVENTION_WALKTHROUGH.json').write_text(
    json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
print(json.dumps(dict(status=report['status'],checks=checks,distributions=distributions,
    zero_indicator_direct_dft=zero_decomposition,hypothetical_padding_error=padding_report),ensure_ascii=False))
if report['status']!='PASS':raise SystemExit(1)
