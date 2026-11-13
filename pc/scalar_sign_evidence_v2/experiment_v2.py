import sys
sys.dont_write_bytecode=True
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'scalar_multipeak48_v1';V1=ROOT.parent/'scalar_sign_evidence_v1'
sys.path.insert(0,str(OLD));sys.path.insert(0,str(OLD/'source'))
import experiment as previous
from common import np,read,write,sha,echo,power,amplitudes,ENGINE,gain_float,guarded_gain,roi
from model48 import load_model
import solver,solver_v1_snapshot as prior
import argparse,time,json
CFG=read(ROOT/'PROTOCOL.json');MODEL=ROOT.parent/CFG['baseline'];REF=previous.REF

def dataset(split):
    dest=ROOT/'data'/f'{split}_manifest.json'
    if dest.exists():
        data=read(dest);assert data['protocol_sha256']==sha(ROOT/'PROTOCOL.json');return data['records']
    if split=='test':assert (ROOT/'FROZEN.json').exists()
    records=[]
    if split=='development':
        for p in CFG['development_sources']:
            file=ROOT.parent/p;rep=read(V1/'reports/test'/(file.stem+'.json'));meta=dict(rep['metadata']);meta['split']=split
            records.append(meta)
    else:
        folder=ROOT/'data'/split;folder.mkdir(parents=True,exist_ok=True)
        for i,t in enumerate(CFG['splits'][split]['templates']):
            meta=previous.scene(CFG['splits'][split]['seed_base']+i,t,i,0);id=f'{i:03d}_{t}'
            adc=echo(meta);si=np.where(adc.real>=0,1,-1).astype('i1');sq=np.where(adc.imag>=0,1,-1).astype('i1')
            ref=power(adc);base=power(si.astype('f8')*64+1j*sq.astype('f8')*64)
            p=folder/(id+'.npz');np.savez_compressed(p,adc_i=adc.real.astype('i2'),adc_q=adc.imag.astype('i2'),sign_i=si,sign_q=sq,reference=ref,base=base)
            records.append(dict(id=id,split=split,**meta,file=str(p),sha256=sha(p)));print('生成',split,id,flush=True)
    write(dest,dict(records=records,protocol_sha256=sha(ROOT/'PROTOCOL.json'),generation_sources={str(p):sha(p) for p in [Path(__file__),OLD/'experiment.py',OLD/'reference_v2.py',OLD/'source/common.py',OLD/'source/fft_reference/xfft_model.py']}));return records

def support(x,old,sr):
    mask=np.zeros(x.shape,bool);states=[]
    for c in sr['candidates']:
        good=c['h0_solver']['success'] and c['h1_solver']['success'] and c['heldout_loss_delta']-2*c['delta_se']>.001 and c['mismatch_improvement']-2*c['mismatch_se']>0 and c['relative_coefficient']>.01
        if good:mask.flat[roi(*c['fitted_frequency'])]=True
        states.append(dict(index=c['index'],supported=bool(good)))
    out=old.copy();out[mask]=np.maximum(out[mask],x[mask])
    return out,mask,states

def outputs(x,old,model,sr,alphas):
    p,mask,states=support(x,old,sr)
    result={'protect':p}
    for a in alphas:
        v=(1-a)*old+a*model;v[mask]=np.maximum(v[mask],p[mask]);result[f'blend{a}']=v
    return result,dict(states=states,protected_pixels=int(mask.sum()))

def recall(meta,sr):
    return [dict(range_bin=t['range_bin'],doppler_bin=t['doppler_bin'],present=any(max(abs((c['integer'][0]-t['range_bin']+512)%1024-512),abs((c['integer'][1]-t['doppler_bin']+256)%512-256))<=2 for c in sr['candidates'])) for t in meta['targets']]

def source_digests():return {p.name:sha(p) for p in [ROOT/'solver.py',ROOT/'solver_v1_snapshot.py',Path(__file__),ROOT/'PROTOCOL.json']}

def run(split):
    if split=='test':
        frozen=read(ROOT/'FROZEN.json');assert frozen['sources']==source_digests() and frozen['model_sha256']==sha(MODEL)
    net=load_model(MODEL,40);alphas=[read(ROOT/'FROZEN.json')['alpha']] if split=='test' else [.25,.5,.75]
    for meta in dataset(split):
        folder=ROOT/'reports'/split;folder.mkdir(parents=True,exist_ok=True);dest=folder/(meta['id']+'.json')
        if dest.exists():assert read(dest)['sources']==source_digests();continue
        with np.load(meta['file']) as d:si=d['sign_i'];sq=d['sign_q'];base=d['base'];ref=d['reference']
        y,x=amplitudes(ref,base);f=ENGINE.features(base);old=x*guarded_gain(base,gain_float(net,f),f)
        out={'reference':y,'bypass':x,'old40':old};records={};support_logs={};feature_shift={}
        for arm in ['v1','fft24','residual24']:
            cache=folder/(meta['id']+'_'+arm+'.json');arrays=folder/(meta['id']+'_'+arm+'.npz')
            if cache.exists():
                sr=read(cache);assert sr['code_sha256']==sha(ROOT/('solver_v1_snapshot.py' if arm=='v1' else 'solver.py'))
                with np.load(arrays) as d:model=d['model']
            else:
                if arm=='v1' and split=='development':
                    oldr=read(V1/'reports/test'/(meta['id']+'.json'));sr=oldr['solver']
                    with np.load(oldr['arrays']) as d:model=d['model']
                    sr={**sr,'reused_v1_report':str(V1/'reports/test'/(meta['id']+'.json'))}
                else:model,sr=(prior if arm=='v1' else solver).solve(si,sq,{**CFG['solver'],'strategy':arm})
                sr.update(code_sha256=sha(ROOT/('solver_v1_snapshot.py' if arm=='v1' else 'solver.py')),source_sha256=meta['sha256'])
                write(cache,sr);np.savez_compressed(arrays,model=model)
            records[arm]=sr;out[arm+'_model']=model
            if arm=='v1':out['v1_gate'],support_logs[arm]=prior.gate(x,old,sr,threshold=.001,se_multiplier=2)
            else:
                combos,log=outputs(x,old,model,sr,alphas);support_logs[arm]=log
                out.update({arm+'_'+k:v for k,v in combos.items()})
                if arm=='residual24':
                    proxy=np.rint(np.square(model.astype('f8'))*int(base.max())).astype('u8')
                    pf=ENGINE.features(proxy);pg=guarded_gain(proxy,gain_float(net,pf),pf)
                    out['serial']=model*pg
                    feature_shift=dict(mean_abs_q12_change=float(np.abs(pf.astype('i4')-f.astype('i4')).mean()),fraction_changed=float(np.mean(pf!=f)),scale='原单比特功率峰映射，非绝对功率标定')
            print('求解完成',split,meta['id'],arm,round(sr['seconds'],2),'秒',flush=True)
        metrics={k:REF.metrics(meta,y,x,v) for k,v in out.items() if k!='reference'}
        arr=ROOT/'results'/split/(meta['id']+'.npz');arr.parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(arr,**out)
        write(dest,dict(metadata=meta,metrics=metrics,solver_reports={k:str(folder/(meta['id']+'_'+k+'.json')) for k in records},
            recall={k:recall(meta,v) for k,v in records.items()},support=support_logs,feature_shift=feature_shift,arrays=str(arr),arrays_sha256=sha(arr),sources=source_digests(),model_sha256=sha(MODEL)))
        print('帧评估',split,meta['id'],{k:sum(t['retention']<.5 for t in m['targets']) for k,m in metrics.items()},flush=True)

def aggregate(split):
    rows=[read(ROOT/'reports'/split/(m['id']+'.json')) for m in dataset(split)];s=REF.aggregate(rows)
    for key,v in s.items():
        pairs=[(a,b) for r in rows for a,b in zip(r['metrics']['old40']['targets'],r['metrics'][key]['targets'])]
        v['new_half_vs_old']=sum(a['retention']>=.5 and b['retention']<.5 for a,b in pairs)
        v['recovered_half_vs_old']=sum(a['retention']<.5 and b['retention']>=.5 for a,b in pairs)
        v['max_retention_drop']=max(a['retention']-b['retention'] for a,b in pairs)
        v['already_failed_worse']=sum(a['retention']<.5 and b['retention']<a['retention']-.01 for a,b in pairs)
    rc={arm:dict(found=sum(t['present'] for r in rows for t in r['recall'][arm]),total=sum(len(r['recall'][arm]) for r in rows)) for arm in ['v1','fft24','residual24']}
    times={arm:dict(mean_seconds=float(np.mean([read(Path(r['solver_reports'][arm]))['seconds'] for r in rows])),initial_joint_converged=sum(read(Path(r['solver_reports'][arm]))['full_solver']['success'] for r in rows)) for arm in rc}
    report=dict(summary=s,recall=rc,timing=times)
    if split=='test':
        key='residual24_blend'+str(read(ROOT/'FROZEN.json')['alpha']);v=s[key];b=s['old40']
        gates=dict(no_new_half_vs_old=v['new_half_vs_old']==0,all_targets_half=v['below_half']==0,artifact=v['mean_false40']<=.9*b['mean_false40'],mae=v['mean_target_error']<=b['mean_target_error']+.005,retention_drop=v['max_retention_drop']<=.05)
        report.update(primary=key,gates=gates,quality_pass=all(gates.values()),deployment_ready=False)
    write(ROOT/'reports'/f'{split.upper()}_SUMMARY.json',report);return report

def freeze():
    if (ROOT/'FROZEN.json').exists():raise FileExistsError('Frozen')
    report=aggregate('validation');s=report['summary']
    a=min([.25,.5,.75],key=lambda a:(s['residual24_blend'+str(a)]['new_half_vs_old'],s['residual24_blend'+str(a)]['below_half'],s['residual24_blend'+str(a)]['mean_false40'],s['residual24_blend'+str(a)]['mean_target_error'],a))
    write(ROOT/'FROZEN.json',dict(alpha=a,sources=source_digests(),model_sha256=sha(MODEL),before_test_generation=True,validation=report));print('冻结alpha',a,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['development','validation','freeze','test']);a=p.parse_args()
    if a.stage=='freeze':freeze()
    else:run(a.stage);print(json.dumps(aggregate(a.stage),ensure_ascii=False),flush=True)
