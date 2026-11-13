"""Minimal correction: frozen v2 neural weights + compact weak-peak protection."""
from experiment import *
from compact_guard import compact_peak_skip

POLICY=dict(version='compact_peak_skip_v1',network_weights='frozen_v2',network_weight_sha256=sha(OLD/'research_candidate/weights.npz'),float_sha256=sha(OLD/'runs/soft_patch5/step_30000.pt'),actual_chirps_changed=[512],actual_chirps_unchanged=[128],compact_fifthroot_mean9_ratio_transition=[1.4,1.6],v2_final_gain_transition=[.25,.5],input_power_min_relative_to_peak=.0001,weak_power_max_relative_to_peak=1/16,local_max_window=9,exclude_explained_strong_third_fifth_harmonics=True,range_indices=[0,1023],output_power_formula='sat_u64((Pin*g_q14^2+2^27)>>28)',source_sha256=sha(ROOT/'compact_guard.py'),no_reference_or_literal_coordinates=True)

def diagnostics():
    folder=ROOT/'compact_development';folder.mkdir(exist_ok=False);write(ROOT/'COMPACT_POLICY.json',POLICY)
    lookup={r['id']:r for r in dev_records()}
    lookup.update({r['id']:r for r in read(ROOT/'fresh_test_manifest.json')['records']})
    rows=[];selected={'historical_0024','historical_0036','confirm_synth_116013_512','v3_synth_124017_512','v3_synth_124001_512','v3_field_rx0_0463','v3_synth_124000_128'}
    for source in ['development_final','fresh_test']:
        for original in read(ROOT/source/'report.json')['rows']:
            meta=lookup[original['id']];ref,p,f=pair(meta)
            with np.load(ROOT/source/'arrays'/(meta['id']+'.npz')) as d:g0=d['previous_gain'];oldp=d['previous_power'];og=d['original_gain']
            g,info=compact_peak_skip(p,g0,f,meta['actual_chirps'],True);out=apply_power(p,g)
            nr=measures(ref,p,out,g,meta);row=dict(id=meta['id'],group=original['group'],split='development_including_previously_failed_test',actual_chirps=meta['actual_chirps'],layout_assumed=original.get('layout_assumed'),inference_profile='frozen_v2_128' if meta['actual_chirps']==128 else 'compact_skip_512',**nr,original=original['original'],previous_v2=original['previous_v2'],compact_info=info)
            rows.append(row)
            if meta['id'] in selected or any(t['newly_below_half'] for t in row['targets']):
                a=folder/'arrays';a.mkdir(exist_ok=True);np.savez_compressed(a/(meta['id']+'.npz'),reference=ref,base=p,enhanced=out,gain=g,previous_power=oldp,previous_gain=g0,original_gain=og)
            print('COMPACT_DEV',meta['id'],'changed',info['changed_pixels'],'half_loss',sum(t['newly_below_half'] for t in nr['targets']),flush=True)
    summary=summary_for_rows(rows)
    checks={k:summary['checks'][k] for k in read(ROOT/'CORRECTION_ACCEPTANCE.json')['checks']}
    result=dict(status='PASS' if summary['passed'] else 'FAIL',correction_status='PASS' if all(checks.values()) else 'FAIL',correction_checks=checks,summary=summary,rows=rows,policy=POLICY,prior_test124000_now_development=True,all_previous_failures_retained=True)
    write(folder/'report.json',result);print('COMPACT_DEVELOPMENT',result['correction_status'],summary['checks'],summary['v2_nonregression'],flush=True)

def freeze():
    dev=read(ROOT/'compact_development/report.json')
    if dev['correction_status']!='PASS':raise RuntimeError('Compact correction failed development; do not open another test')
    policy=read(ROOT/'COMPACT_POLICY.json');assert policy==POLICY
    p=ROOT/'COMPACT_FROZEN.json'
    if p.exists():raise FileExistsError(p)
    write(p,dict(status='FROZEN_REQUIRES_FRESH_TEST',policy_sha256=sha(ROOT/'COMPACT_POLICY.json'),guard_sha256=sha(ROOT/'compact_guard.py'),weights_sha256=policy['network_weight_sha256'],original_v2_float_sha256=policy['float_sha256'],no_neural_weights_changed=True,development_correction_status=dev['correction_status'],development_full_quality=dev['status']))
    write(ROOT/'COMPACT_TEST_PROTOCOL.json',dict(seed_range=[128000,128015],raw_frames_zero_based=[455,519,583],primary_layout='rx_blocks_per_chirp',rx_ids=[0,3],no_reselection_on_test=True,old124000_test_status='FAIL and diagnostic only after changed design',quality_gates_unchanged=True,correction_acceptance_sha256=sha(ROOT/'CORRECTION_ACCEPTANCE.json'),original_v7_nmse_max=1.05,original_v7_background_max=1.10,per_128_and512_separate=True))

def build_test():
    frozen=read(ROOT/'COMPACT_FROZEN.json');assert sha(ROOT/'COMPACT_POLICY.json')==frozen['policy_sha256'];assert sha(ROOT/'compact_guard.py')==frozen['guard_sha256']
    dest=ROOT/'compact_test_manifest.json'
    if dest.exists():raise FileExistsError(dest)
    hw=HardwareNetwork();protocol=read(ROOT/'COMPACT_TEST_PROTOCOL.json');rows=[]
    lo,hi=protocol['seed_range']
    for i,seed in enumerate(range(lo,hi+1)):
        echo,meta=scene(seed,i);n=128 if i%2==0 else 512;meta.update(split='compact_fresh_test',group='synthetic')
        rows.append(save_pair(f'compact_synth_{seed}_{n}',echo[:,:n],meta,hw));print('COMPACT_TEST_PAIR',seed,n,flush=True)
    used={r['source_frame_zero_based'] for name in ['manifest.json','followup_test_manifest.json','confirm_test_manifest.json'] for r in old_records(name) if 'source_frame_zero_based' in r}
    used.update(r['source_frame_zero_based'] for r in read(ROOT/'fresh_test_manifest.json')['records'] if 'source_frame_zero_based' in r)
    for frame in protocol['raw_frames_zero_based']:
        assert frame not in used
        channels,payload=decode(frame,'rx_blocks_per_chirp')
        for j,rx in enumerate([0,3]):
            meta=dict(split='compact_fresh_test',group='field_temporal',targets=[],layout_assumed='rx_blocks_per_chirp',rx_id=rx,source_frame_zero_based=frame,physical_layout_confirmed=False,raw_frame_sha256=hashlib.sha256(payload).hexdigest())
            rows.append(save_pair(f'compact_field_rx{rx}_{frame:04d}',channels[j],meta,hw));print('COMPACT_TEST_FIELD',frame,rx,flush=True)
    write(dest,dict(records=rows,protocol_sha256=sha(ROOT/'COMPACT_TEST_PROTOCOL.json'),frozen_sha256=sha(ROOT/'COMPACT_FROZEN.json')))

def test():
    frozen=read(ROOT/'COMPACT_FROZEN.json');assert sha(ROOT/'COMPACT_POLICY.json')==frozen['policy_sha256'];assert sha(ROOT/'compact_guard.py')==frozen['guard_sha256'];assert sha(OLD/'research_candidate/weights.npz')==frozen['weights_sha256']
    folder=ROOT/'compact_fresh_test';folder.mkdir(exist_ok=False);net,ck=load_net(OLD/'runs/soft_patch5/step_30000.pt');fixed=IntegerCorrector(net);hw=HardwareNetwork();rows=[]
    for r in read(ROOT/'compact_test_manifest.json')['records']:
        ref,p,f=pair(r);ff=features_for_policy(f,'guarded_child',2);n=r['actual_chirps'];g0=apply_guard(p,fixed.predict(ff),ck['config']['power_guard'],ff,n);g,info=compact_peak_skip(p,g0,f,n,True)
        oldp=apply_power(p,g0);out=apply_power(p,g);og=cached_gain(r,f,hw);nr=measures(ref,p,out,g,r);v7=measures(ref,p,apply_power(p,og),og,r);v2=measures(ref,p,oldp,g0,r)
        rows.append(dict(id=r['id'],group=r['group'],split=r['split'],actual_chirps=n,layout_assumed=r.get('layout_assumed'),inference_profile='frozen_v2_128' if n==128 else 'compact_skip_512',**nr,original=v7,previous_v2=v2,compact_info=info))
        a=folder/'arrays';a.mkdir(exist_ok=True);np.savez_compressed(a/(r['id']+'.npz'),reference=ref,base=p,enhanced=out,gain=g,previous_power=oldp,previous_gain=g0,original_gain=og)
        print('COMPACT_TEST',r['id'],'changed',info['changed_pixels'],'half_loss',sum(t['newly_below_half'] for t in nr['targets']),flush=True)
    summary=summary_for_rows(rows);checks={k:summary['checks'][k] for k in read(ROOT/'CORRECTION_ACCEPTANCE.json')['checks']}
    result=dict(status='PASS' if summary['passed'] else 'FAIL',correction_status='PASS' if all(checks.values()) else 'FAIL',correction_checks=checks,summary=summary,rows=rows,policy=POLICY,used_for_tuning=False,board_accessed=False)
    write(folder/'report.json',result);print('COMPACT_FRESH_TEST',result['correction_status'],summary['checks'],flush=True)

if __name__=='__main__':
    torch.set_num_threads(2);a=argparse.ArgumentParser();a.add_argument('action',choices=['diagnostics','freeze','build','test']);args=a.parse_args()
    {'diagnostics':diagnostics,'freeze':freeze,'build':build_test,'test':test}[args.action]()
