"""Constrain the change to radar1's 512-chirp acquisition; retain original128."""
from experiment import ROOT,OLD,read,write,sha,summary_for_rows
import copy

source=read(ROOT/'development_final/report.json');rows=[]
for old in source['rows']:
    r=copy.deepcopy(old)
    if r['actual_chirps']==128:
        r.update(copy.deepcopy(r['previous_v2']));r['inference_profile']='frozen_v2_128'
    else:r['inference_profile']='corrected_512'
    rows.append(r)
summary=summary_for_rows(rows);report=dict(source,status='PASS' if summary['passed'] else 'FAIL',summary=summary,rows=rows,scope='Profile-specific weak correction; original full quality criteria unchanged',arrays_reference_folder='../development_final/arrays',array_interpretation='For frozen_v2_128 profile use previous_power/previous_gain as enhanced/gain; corrected_512 uses enhanced/gain')
write(ROOT/'development_profiled/report.json',report)
write(ROOT/'PROFILE_POLICY.json',dict(selection_input='actual_chirps metadata already required by the power guard',profiles={'128':dict(model='frozen_v2',float_sha256=sha(OLD/'runs/soft_patch5/step_30000.pt'),runtime_weights_sha256=sha(OLD/'research_candidate/weights.npz'),changed=False),'512':dict(model='guardaware_conservative_alpha0p75',float_sha256=source['model_sha256'],changed=True)},reason='Actual radar1 deployment uses512 valid chirps. Joint fine tuning created two numerical peak losses on128 development frames; retain the proven original128 function instead of accepting that regression.',no_reference_or_case_id_used_for_routing=True,hardware_target_actual_chirps=512,weights_per_profile=1857,macs_per_pixel=1808,one_profile_inference_per_frame=True,declared_before_fresh_test=True))
print('PROFILED_DEVELOPMENT',report['status'],summary['checks'],flush=True)
