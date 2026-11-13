import sys
sys.dont_write_bytecode=True
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'scalar_multipeak48_v1'
sys.path.insert(0,str(OLD));sys.path.insert(0,str(OLD/'source'))
import experiment as previous
from common import np,read,write,sha,echo,power,amplitudes,ENGINE,gain_float,guarded_gain,roi
from model48 import load_model
import sign_solver as solver
import argparse,time,itertools,json
CFG=read(ROOT/'PROTOCOL.json');MODEL=ROOT.parent/CFG['baseline']
REF=previous.REF

def preflight():
    from scipy.optimize._numdiff import approx_derivative
    rng=np.random.default_rng(8172);ids=rng.choice(1024*512,97,False)
    f=np.array([[44.3,56.2],[137.1,331.4]])
    a=np.array([1+.2j,.13-.26j]);y=np.where(rng.normal(size=97)>0,1,-1)+1j*np.where(rng.normal(size=97)>0,1,-1)
    v=np.r_[a.real,a.imag,f[:,0],f[:,1]]
    val,g=solver.objective(v,ids,y,f,CFG['solver'])
    fd=approx_derivative(lambda w:solver.objective(w,ids,y,f,CFG['solver'])[0],v,method='3-point').ravel()
    error=float(abs(g-fd).max());assert error<2e-6,(g,fd)
    n=np.arange(1024)[:,None];m=np.arange(512)[None,:]
    z=np.exp(2j*np.pi*(44.27*n/1024+58.32*m/512)+.3j)
    q=np.where(z.real>=0,1,-1)+1j*np.where(z.imag>=0,1,-1)
    cs=solver.find_candidates(q,CFG['solver']);est=cs[0]['frequency']
    assert abs(est[0]-44.27)<.03 and abs(est[1]-58.32)<.03,est
    ids=np.array([0,511,512,524287]);x=solver.predict(ids,f,a)
    direct=np.array([sum(aa*np.exp(2j*np.pi*(ff[0]*(int(i)//512)/1024+ff[1]*(int(i)%512)/512)) for aa,ff in zip(a,f)) for i in ids])
    assert abs(x-direct).max()<1e-12
    write(ROOT/'reports/PREFLIGHT.json',dict(status='PASS',gradient_max_error=error,candidate_frequency_probe=est,predict_independent_error=float(abs(x-direct).max()),protocol_sha256=sha(ROOT/'PROTOCOL.json')))
    print('预检查通过',error,est,flush=True)

def dataset(split):
    dest=ROOT/'data'/f'{split}_manifest.json'
    if dest.exists():
        rows=read(dest)['records'];assert read(dest)['protocol_sha256']==sha(ROOT/'PROTOCOL.json')
        return rows
    if split=='test':assert (ROOT/'FROZEN.json').exists()
    folder=ROOT/'data'/split;folder.mkdir(parents=True,exist_ok=True);rows=[]
    for i,template in enumerate(CFG['splits'][split]['templates']):
        seed=CFG['splits'][split]['seed_base']+i
        meta=previous.scene(seed,template,i,0);name=f'{i:03d}_{template}'
        adc=echo(meta);si=np.where(adc.real>=0,1,-1).astype('i1');sq=np.where(adc.imag>=0,1,-1).astype('i1')
        ref=power(adc);base=power(si.astype('f8')*64+1j*sq.astype('f8')*64)
        path=folder/(name+'.npz')
        np.savez_compressed(path,adc_i=adc.real.astype('i2'),adc_q=adc.imag.astype('i2'),sign_i=si,sign_q=sq,reference=ref,base=base)
        rows.append(dict(id=name,split=split,**meta,file=str(path),sha256=sha(path)))
        print('新数据',split,name,flush=True)
    write(dest,dict(records=rows,protocol_sha256=sha(ROOT/'PROTOCOL.json'),generator_code={str(p):sha(p) for p in [Path(__file__),OLD/'experiment.py',OLD/'reference_v2.py',OLD/'source/common.py',OLD/'source/fft_reference/xfft_model.py']}))
    return rows

def run(split):
    if split=='test':
        frozen=read(ROOT/'FROZEN.json')
        assert frozen['solver_sha256']==sha(ROOT/'sign_solver.py')
        assert frozen['driver_sha256']==sha(__file__)
        assert frozen['protocol_sha256']==sha(ROOT/'PROTOCOL.json')
        assert frozen['model_sha256']==sha(MODEL)
    net=load_model(MODEL,40)
    for row in dataset(split):
        folder=ROOT/'reports'/split;folder.mkdir(parents=True,exist_ok=True)
        dest=folder/(row['id']+'.json')
        if dest.exists():
            old=read(dest);assert old['solver_sha256']==sha(ROOT/'sign_solver.py') and old['source_sha256']==row['sha256'];continue
        with np.load(row['file']) as d:
            base=d['base'];ref=d['reference'];si=d['sign_i'];sq=d['sign_q']
        y,x=amplitudes(ref,base);start=time.perf_counter()
        f=ENGINE.features(base);g=guarded_gain(base,gain_float(net,f),f);old=x*g
        old_time=time.perf_counter()-start
        model,sr=solver.solve(si,sq,{**CFG['solver'],'sample_seed':CFG['solver']['sample_seed']})
        rec=[]
        for t in row['targets']:
            near=[c for c in sr['candidates'] if max(abs((c['integer'][0]-t['range_bin']+512)%1024-512),abs((c['integer'][1]-t['doppler_bin']+256)%512-256))<=2]
            rec.append(dict(range_bin=t['range_bin'],doppler_bin=t['doppler_bin'],candidate_present=bool(near),candidate_indices=[c['index'] for c in near]))
        metrics={key:REF.metrics(row,y,x,out) for key,out in [('bypass',x),('old40',old),('model',model)]}
        params=[read(ROOT/'FROZEN.json')['gate']] if split=='test' else [dict(threshold=t,se_multiplier=s) for t,s in itertools.product(CFG['gate_grid']['loss_threshold'],CFG['gate_grid']['se_multiplier'])]
        gate_reports={};outs=dict(reference=y,bypass=x,old40=old,model=model)
        for p in params:
            name='gated' if split=='test' else f"gate_{p['threshold']}_{p['se_multiplier']}"
            result,gr=solver.gate(x,old,sr,**p);metrics[name]=REF.metrics(row,y,x,result)
            gate_reports[name]=dict(parameters=p,**gr);outs[name]=result
        arr=ROOT/'results'/split/(row['id']+'.npz');arr.parent.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(arr,**outs)
        write(dest,dict(metadata=row,metrics=metrics,solver=sr,gates=gate_reports,candidate_recall=rec,
                        arrays=str(arr),arrays_sha256=sha(arr),source_sha256=row['sha256'],model_sha256=sha(MODEL),
                        solver_sha256=sha(ROOT/'sign_solver.py'),driver_sha256=sha(__file__),old40_seconds=old_time))
        print('完成',split,row['id'],'符号恢复秒',round(sr['seconds'],2),'错配',round(sr['evidence_mismatch'],5),'收敛',sr['full_solver']['success'],
              '半幅失败',{k:sum(t['retention']<.5 for t in m['targets']) for k,m in metrics.items()},flush=True)

def aggregate(split):
    rows=[read(ROOT/'reports'/split/(r['id']+'.json')) for r in dataset(split)]
    summary=REF.aggregate(rows)
    for k,s in summary.items():
        s['new_half_vs_old40']=sum(a['retention']>=.5 and b['retention']<.5 for row in rows for a,b in zip(row['metrics']['old40']['targets'],row['metrics'][k]['targets']))
        s['recovered_half_vs_old40']=sum(a['retention']<.5 and b['retention']>=.5 for row in rows for a,b in zip(row['metrics']['old40']['targets'],row['metrics'][k]['targets']))
    report=dict(summary=summary,frames=[r['metadata']['id'] for r in rows],
        candidates=dict(recalled=sum(c['candidate_present'] for r in rows for c in r['candidate_recall']),targets=sum(len(r['candidate_recall']) for r in rows)),
        solver=dict(mean_seconds=float(np.mean([r['solver']['seconds'] for r in rows])),max_seconds=max(r['solver']['seconds'] for r in rows),converged=sum(r['solver']['full_solver']['success'] for r in rows),frames=len(rows),mean_evidence_mismatch=float(np.mean([r['solver']['evidence_mismatch'] for r in rows]))))
    if split=='test':
        old=summary['old40'];s=summary['gated']
        report['gates']=dict(no_new_target_half_vs_old=s['new_half_vs_old40']==0,all_targets_at_least_half=s['below_half']==0,
                             artifact=s['mean_false40']<=.9*old['mean_false40'],target_mae=s['mean_target_error']<=old['mean_target_error']+.005)
        report['quality_pass']=all(report['gates'].values());report['deployment_ready']=False
    write(ROOT/'reports'/f'{split.upper()}_SUMMARY.json',report)
    return report,rows

def freeze():
    if (ROOT/'FROZEN.json').exists():raise FileExistsError('Frozen experiment must not be overwritten')
    report,rows=aggregate('validation');summary=report['summary']
    names=[k for k in summary if k.startswith('gate_')]
    chosen=min(names,key=lambda k:(summary[k]['new_half_vs_old40'],summary[k]['below_half'],summary[k]['mean_false40'],summary[k]['mean_target_error'],k))
    write(ROOT/'FROZEN.json',dict(gate=rows[0]['gates'][chosen]['parameters'],validation_selected_name=chosen,validation_summary=summary[chosen],
                                 protocol_sha256=sha(ROOT/'PROTOCOL.json'),solver_sha256=sha(ROOT/'sign_solver.py'),driver_sha256=sha(__file__),model_sha256=sha(MODEL),before_test_generation=True))
    print('冻结',chosen,summary[chosen],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['preflight','development','validation','freeze','test']);args=p.parse_args()
    if args.stage=='preflight':preflight()
    elif args.stage=='freeze':freeze()
    else:run(args.stage);report,_=aggregate(args.stage);print(json.dumps(report,ensure_ascii=False),flush=True)
