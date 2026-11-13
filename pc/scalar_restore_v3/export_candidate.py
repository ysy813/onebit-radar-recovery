"""Export frozen weak-target correction and check standalone fixed inference."""
from pathlib import Path
import shutil,importlib.util,subprocess,os
from experiment import ROOT,OLD,read,write,sha,load_net,IntegerCorrector,features_for_policy,apply_guard,apply_power,pair,old_records
import numpy as np
import torch

def bounds(fixed):
    inputs=np.full(40,65536,dtype=object);rows=[]
    for i,(w,b) in enumerate(fixed.layers):
        a=abs(w).astype(object)@inputs+abs(b).astype(object)
        rows.append(dict(layer=i,accumulator_absolute_bound=int(max(a)),signed_bits=int(max(a)).bit_length()+1,coefficient_signed_bits=int(abs(w).max()).bit_length()+1,bias_signed_bits=int(abs(b).max()).bit_length()+1))
        inputs=(a+32768)//65536+1
    return rows

def main():
    torch.set_num_threads(2);frozen=read(ROOT/'FROZEN_MODEL.json');p=Path(frozen['path']);assert sha(p)==frozen['sha256']
    test=read(ROOT/'fresh_test/report.json');assert test['model_sha256']==frozen['sha256']
    folder=ROOT/'pc_candidate';folder.mkdir(exist_ok=False);net,ck=load_net(p);fixed=IntegerCorrector(net)
    payload={'gain_lut':fixed.lut}
    for i,(w,b) in enumerate(fixed.layers):payload[f'w{i}']=w;payload[f'b{i}']=b
    np.savez_compressed(folder/'weights.npz',**payload)
    for source,dest in [(OLD/'research_candidate/root5.npy','root5.npy'),(ROOT/'runtime_template.py','restore_power.py'),(OLD/'research_candidate/weights.npz','weights_128.npz'),(OLD/'runs/soft_patch5/step_30000.pt','model_128_float.pt'),(OLD/'scalar_guard.py','scalar_guard.py'),(p,'model_float.pt'),(OLD/'model.py','model_source.py')]:shutil.copy2(source,folder/dest)
    config=read(OLD/'research_candidate/config.json')
    config.update(version='scalar_restore_v3_guardaware_weakfix',quality_test_status=test['status'],research_only=test['status']!='PASS',approved_for_pl_integration=False,ready_for_ip_adaptation=False,hardware_adapter_implemented=False,
        sha256={name:sha(folder/name) for name in ['weights.npz','weights_128.npz','root5.npy','model_float.pt','model_128_float.pt']},selection_report='../FROZEN_MODEL.json',independent_test_report='../fresh_test/report.json',architecture_changed=False,power_guard_changed=False,weights_finetuned=True,training_guard_included=True,
        profile_weights={'128':'weights_128.npz','512':'weights.npz'},profile_note='128 uses frozen original v2;512 uses corrected weights. Choose by actual-chirps metadata, never by reference or case id.',stored_parameter_sets=2,parameters_per_profile=1857,macs_per_pixel_per_frame=1808,hardware_target_actual_chirps=512)
    write(folder/'config.json',config)
    spec=importlib.util.spec_from_file_location('v3_standalone',folder/'restore_power.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);runtime=module.PowerRestorer(folder)
    records=[r for r in old_records() if r['id'] in ['historical_0024','historical_0036','field_rx_blocks_per_chirp_rx0_0351','field_rx_blocks_per_chirp_rx3_0383']]
    records+=[dict(r,pair_path=str(OLD/r['file'])) for r in read(OLD/'confirm_test_manifest.json')['records'] if r['id']=='confirm_synth_116013_512']
    initial,initial_ck=load_net(OLD/'runs/soft_patch5/step_30000.pt');initial_fixed=IntegerCorrector(initial);rows=[]
    for r in records:
        ref,power,f=pair(r);f=features_for_policy(f,'guarded_child',2);n=r['actual_chirps']
        active=initial if n==128 else net;active_fixed=initial_fixed if n==128 else fixed
        g=apply_guard(power,active_fixed.predict(f),config['power_guard'],f,n);out,gg=runtime.restore(power,True,n)
        floating=[]
        for s in range(0,power.size,32768):
            with torch.no_grad():floating.append(active.gain(torch.from_numpy(f[:,s:s+32768].T.astype('f4')/4096)).numpy().ravel())
        gf=apply_guard(power,np.concatenate(floating).reshape(power.shape)*16384,config['power_guard'],f,n)/16384
        diff=np.abs(gf-gg.astype('f8')/16384)
        rows.append(dict(id=r['id'],features_exact=bool(np.array_equal(f,runtime.features(power))),gain_exact=bool(np.array_equal(g,gg)),power_exact=bool(np.array_equal(out,apply_power(power,g))),float_fixed_gain_mae=float(diff.mean()),float_fixed_gain_max=float(diff.max())))
        print('NUMERIC',r['id'],rows[-1],flush=True)
    zero=np.zeros((1024,512),dtype='u8');zo,zg=runtime.restore(zero,True)
    extreme=np.array([0,1,17,2**32,2**63,2**64-1],dtype='u8');eg=np.array([2048,8192,16384,20000,24576,24576],dtype='u2')
    expected=[min(2**64-1,(int(v)*int(g)**2+2**27)>>28) for v,g in zip(extreme,eg)]
    integer_bounds=bounds(fixed)
    checks=dict(all_standalone_features_gain_power_exact=all(r['features_exact'] and r['gain_exact'] and r['power_exact'] for r in rows),float_fixed_gain_mae_at_most_0p0003=all(r['float_fixed_gain_mae']<=.0003 for r in rows),float_fixed_gain_max_at_most_0p01=all(r['float_fixed_gain_max']<=.01 for r in rows),zero_frame_exact=not zo.any() and bool((zg==16384).all()),u64_saturation_exact=runtime.apply_power(extreme,eg).tolist()==expected,accumulators_fit_signed48=all(r['signed_bits']<=48 for r in integer_bounds),unchanged_training_guard_matches_inference=read(ROOT/'TRAINING_GUARD_CHECK.json')['status']=='PASS')
    # Invoke the CLI from an empty directory without any workspace PYTHONPATH.
    isolated=ROOT/'runtime_smoke';isolated.mkdir(exist_ok=False);cli=[];env=os.environ.copy();env['PYTHONPATH']=''
    import sys
    for name,n in [('v3_synth_124001_512',512),('v3_field_rx0_0463',128)]:
        with np.load(ROOT/'fresh_test/arrays'/(name+'.npz')) as d:power=d['base'];expected_power=d['enhanced'];expected_gain=d['gain']
        ip=isolated/(name+'.npy');op=isolated/(name+'.npz');np.save(ip,power)
        result=subprocess.run([sys.executable,str(folder/'restore_power.py'),'--input',str(ip),'--output',str(op),'--actual-chirps',str(n)],cwd=isolated,env=env,capture_output=True,text=True,timeout=120)
        assert result.returncode==0,result.stdout+result.stderr
        with np.load(op) as d:exact=np.array_equal(d['power'],expected_power) and np.array_equal(d['gain_q14'],expected_gain)
        cli.append(dict(id=name,actual_chirps=n,exact=bool(exact),stdout=result.stdout.strip()))
    checks['isolated_cli_matches_frozen_test']=all(r['exact'] for r in cli)
    preserved={str(OLD/'runs/soft_patch5/step_30000.pt'):'40454b2fcd38275ef8eb75746904afafbafeef582aefcb2755c7ba00f7c22311',str(ROOT.parent/'scalar_enhance_v1/release/scalar_gain_v7_candidate/weights.npz'):'f286163db6c49b06bc33a76317bbdc9c2304f2e22036a00bc7cf5534eb74c479',str(ROOT.parent/'radar1_v7_offline_compare_v1/data/radar_raw.bin'):'b3fb208fcbe335619fee2e32c5e9073548f5502c8c2cd7c823e936bf29cb1015'}
    checks['preserved_input_hashes_match']=all(sha(p)==h for p,h in preserved.items())
    status='PASS' if all(checks.values()) else 'FAIL'
    write(ROOT/'NUMERIC_VERIFICATION.json',dict(status=status,scope='Numerical/interface only, not quality/FPGA verification',checks=checks,rows=rows,isolated_cli=cli,integer_bounds=integer_bounds,preserved_sha256=preserved))
    config['ready_for_ip_adaptation']=test['status']=='PASS' and status=='PASS';write(folder/'config.json',config)
    write(folder/'manifest.json',dict(quality_status=test['status'],numeric_status=status,ready_for_ip_adaptation=config['ready_for_ip_adaptation'],files=[dict(path=p.name,sha256=sha(p)) for p in folder.iterdir() if p.is_file()]))
    print('NUMERIC_COMPLETE',status,checks,flush=True)
    assert all(checks.values())

if __name__=='__main__':main()
