"""Source, split, numerical and source-free inference integrity checks."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
from run import *
import ast,subprocess,re

def main():
    checks={};frozen=read(ROOT/'FROZEN.json')
    checks['frozen_sources_unchanged']=frozen['sources']==digests()
    records={'train':read(ROOT/'data/TRAIN_REGISTER.json')['records'],'validation':read(ROOT/'data/VALIDATION_REGISTER.json')['records'],'test':read(ROOT/'data/test_manifest.json')['records']}
    seeds={k:{r['metadata']['seed'] for r in rs} for k,rs in records.items()}
    hashes={k:{r['metadata']['sha256'] for r in rs} for k,rs in records.items()}
    checks['split_counts']=[len(records[k]) for k in ['train','validation','test']]==[44,12,12]
    checks['split_seed_disjoint']=all(not(seeds[a]&seeds[b]) for a,b in [('train','validation'),('train','test'),('validation','test')])
    checks['split_input_disjoint']=all(not(hashes[a]&hashes[b]) for a,b in [('train','validation'),('train','test'),('validation','test')])
    checked=0;source_ok=True;quant_ok=True;shape_ok=True
    for split,rs in records.items():
        for r in rs:
            m=r['metadata'];source_ok &= sha(m['file'])==m['sha256']
            source_ok &= all(sha(r[k])==r[k+'_sha256'] for k in ['source_arrays','solver_report'])
            if 'source_report' in r:source_ok &= sha(r['source_report'])==r['source_report_sha256']
            with np.load(m['file']) as z:
                shape_ok &= all(z[k].shape==(1024,512) for k in ['adc_i','adc_q','sign_i','sign_q','base','reference'])
                quant_ok &= np.array_equal(z['sign_i'],np.where(z['adc_i']>=0,1,-1)) and np.array_equal(z['sign_q'],np.where(z['adc_q']>=0,1,-1))
            checked+=1
    checks['all_source_hashes']=bool(source_ok);checks['all_shapes']=bool(shape_ok);checks['sum_then_sign_stored_consistency']=bool(quant_ok)
    print('数据来源、划分和两电平检查完成',checked,flush=True)
    new=records['test'][0];m=new['metadata'];adc=v2.echo(m)
    with np.load(m['file']) as z:
        checks['echo_regeneration']=np.array_equal(adc.real,z['adc_i']) and np.array_equal(adc.imag,z['adc_q'])
        checks['bit_exact_fft_sample']=np.array_equal(v2.power(adc),z['reference']) and np.array_equal(v2.power(z['sign_i'].astype('f8')*64+1j*z['sign_q'].astype('f8')*64),z['base'])
    weights={};old=load_model(OLD_MODEL,40);oldvec=torch.cat([p.detach().ravel() for p in old.parameters()])
    for arm in ['adapt','suppress']:
        p=ROOT/'candidate'/arm/'model_float.pt';net=load_model(p,40);vec=torch.cat([p.detach().ravel() for p in net.parameters()]);cp=torch.load(p,map_location='cpu',weights_only=False)
        checks[arm+'_checkpoint_hash']=sha(p)==frozen['selected'][arm]['checkpoint_sha256']
        checks[arm+'_finite_1857_changed']=len(vec)==1857 and bool(torch.isfinite(vec).all()) and not torch.equal(vec,oldvec)
        checks[arm+'_gain_metadata']=cp['gain_min']==1/64 and cp['gain_max']==1.5
        run=read(ROOT/'runs'/arm/'COMPLETE.json');checks[arm+'_shared_sources_budget']=run['sources']==frozen['sources'] and run['pool_sha256']==frozen['training_pool_sha256'] and run['loss_log'][-1]['step']==8000
        weights[arm]={'parameter_count':len(vec),'changed_parameters':int((vec!=oldvec).sum()),'max_abs_change':float((vec-oldvec).abs().max()),'sha256':sha(p),'selected_step':cp['step']}
    poolpath=ROOT/'data/train_pool.npz';pr=read(ROOT/'data/POOL_REGISTER.json');checks['pool_hash']=sha(poolpath)==pr['sha256']==frozen['training_pool_sha256']
    with np.load(poolpath) as z:pool={k:z[k] for k in z.files}
    checks['pool_shape_bounds']=pool['f'].shape==(pr['rows'],32) and pool['pixel'].min()>=0 and pool['pixel'].max()<1024*512 and pool['frame'].min()==0 and pool['frame'].max()==43
    rng=np.random.default_rng(720130);map_ok=True
    for fi,r in enumerate(records['train']):
        ids=np.flatnonzero(pool['frame']==fi);idx=rng.choice(ids,min(16,len(ids)),False);pixels=pool['pixel'][idx];z=load_record(r)
        map_ok &= np.array_equal(pool['f'][idx],z['features'][:,pixels].T)
        map_ok &= np.array_equal(pool['x'][idx],z['model'].ravel()[pixels]) and np.array_equal(pool['y'][idx],z['y'].ravel()[pixels])
    checks['pool_provenance_recomputed_16_per_frame']=bool(map_ok)
    print('权重、训练预算与训练点映射检查完成',flush=True)
    metric_ok=True;output_ok=True;gain_ok=True;errs=[]
    rows=[read(p) for p in sorted((ROOT/'reports/test').glob('*.json'))]
    net=load_model(ROOT/'candidate/suppress/model_float.pt',40)
    for row in rows:
        z=load_record(row['record']);ap=row['arrays'];output_ok &= sha(ap)==row['arrays_sha256'];gain=net_gain(net,z['features'])
        gain_ok &= np.isfinite(gain).all() and gain.min()>=1/64-1e-7 and gain.max()<=1.5+1e-7
        with np.load(ap) as outputs:
            output_ok &= all(np.isfinite(outputs[k]).all() and (outputs[k]>=0).all() for k in outputs.files)
            errs.append(float(np.max(np.abs(outputs['suppress_raw']-z['model']*gain))))
            for k in row['metrics']:
                ref=v2.REF.metrics(z['record']['metadata'],z['y'],z['x'],outputs[k]);ours=row['metrics'][k]
                metric_ok &= ref['false40']==ours['full_bg']['false40'] and abs(ref['excess_energy']-ours['full_bg']['excess'])<1e-9
                # Recompute the regional target count independently from metadata.
                for t,mt,tt in zip(ref['targets'],z['record']['metadata']['targets'],ours['targets']):
                    metric_ok &= abs(t['retention']-tt['retention'])<1e-9 and tt['within40']==(mt['range_m']<=40)
    checks['output_hash_finite_nonnegative']=bool(output_ok);checks['gain_range']=bool(gain_ok)
    checks['full_frame_output_recompute']=max(errs)<=1e-7;checks['metrics_independent_reference']=bool(metric_ok)
    rec=records['test'][7];z=load_record(rec);inp=ROOT/'reports/CLI_INPUT.npz';out=ROOT/'reports/CLI_OUTPUT.npz'
    with np.load(rec['metadata']['file']) as d:peak=int(d['base'].max())
    if not inp.exists():np.savez_compressed(inp,recovered_amplitude=z['model'],original_onebit_peak=np.uint64(peak))
    if not out.exists():
        result=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'infer.py'),'--input',str(inp),'--output',str(out)],capture_output=True,text=True,encoding='utf-8',check=True)
        (ROOT/'reports/CLI_LOG.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
    with np.load(inp) as d:checks['cli_input_no_truth']=set(d.files)=={'recovered_amplitude','original_onebit_peak'}
    with np.load(out) as d:clierr=float(np.max(np.abs(d['output']-z['model']*net_gain(net,z['features']))))
    checks['label_free_cli_same_output']=clierr<=1e-7
    checks['python_syntax']=all(ast.parse(p.read_text(encoding='utf-8')) is not None for p in ROOT.glob('*.py'))
    for p in ROOT.rglob('*.json'):read(p)
    checks['json_parse']=True
    page=(ROOT/'results/index.html').read_text(encoding='utf-8')
    links=re.findall(r'(?:href|src)="([^"]+)"',page)
    checks['html_local_links']=all((ROOT/'results'/x).exists() for x in links if not x.startswith('#'))
    checks={k:bool(v) for k,v in checks.items()}
    status='PASS' if all(checks.values()) else 'FAIL'
    write(ROOT/'reports/STANDARD_CHECK.json',dict(status=status,checks=checks,checked_source_frames=checked,weights=weights,max_full_frame_error=max(errs),cli_max_error=clierr,quality_separate=True,visual_review_separate=True,not_rtl_or_board_validation=True))
    print(json.dumps(dict(status=status,failed=[k for k,v in checks.items() if not v],cli_error=clierr),ensure_ascii=False),flush=True)
    if status!='PASS':raise RuntimeError('Integrity check failed')

if __name__=='__main__':main()
