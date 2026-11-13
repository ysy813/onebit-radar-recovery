import sys
sys.dont_write_bytecode=True
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SRC=ROOT.parent/'scalar_sign_evidence_v2'
sys.path.insert(0,str(SRC))
import experiment_v2 as v2
from experiment_v2 import np,read,write,sha,roi
import solver
from scipy.ndimage import maximum_filter
import json,argparse,time
CFG=read(ROOT/'PROTOCOL.json')

def sources():
    paths=[ROOT/'experiment.py',ROOT/'PROTOCOL.json',SRC/'experiment_v2.py',SRC/'solver.py',v2.MODEL]
    paths+=list(v2.OLD.glob('*.py'))+list((v2.OLD/'source').rglob('*.py'))
    return {str(p):sha(p) for p in sorted(set(paths))}

def load_old(split):
    records=[]
    for m in read(SRC/'data'/f'{split}_manifest.json')['records']:
        row=read(SRC/'reports'/split/(m['id']+'.json'))
        assert sha(row['arrays'])==row['arrays_sha256']
        with np.load(row['arrays']) as z:
            a={k:z[k] for k in ['reference','bypass','old40','residual24_model']}
        sr=read(Path(row['solver_reports']['residual24']))
        p,mask,_=v2.support(a['bypass'],a['old40'],sr)
        records.append(dict(meta=m,reference=a['reference'],bypass=a['bypass'],old=a['old40'],model=a['residual24_model'],floor=p,mask=mask,source_report=str(SRC/'reports'/split/(m['id']+'.json')),source_arrays=row['arrays']))
    return records

def prepare(record):
    y,x,old=record['reference'],record['bypass'],record['old']
    met=v2.REF.metrics(record['meta'],y,x,old)
    idx=np.array([t['peak_index'] for t in met['targets']]);yy=y.flat[idx]
    hids=np.array([roi(h['order']*record['meta']['targets'][h['target']]['range_bin'],h['order']*record['meta']['targets'][h['target']]['doppler_bin']) for h in met['harmonics']],dtype='i8').reshape(-1,25)
    record.update(idx=idx,yy=yy,old_ret=old.flat[idx]/np.maximum(yy,1e-12),occupied=v2.REF.occupied(record['meta']),hids=hids,
        hlabels=[dict(target=h['target'],order=h['order']) for h in met['harmonics']],
        old_henergy=np.square(old.ravel()[hids]).sum(axis=1),bypass_henergy=np.square(x.ravel()[hids]).sum(axis=1))
    return record

def fuse(r,alpha,protected):
    z=(1-alpha)*r['old']+alpha*r['model']
    if protected:z[r['mask']]=np.maximum(z[r['mask']],r['floor'][r['mask']])
    return z

def metrics(r,z):
    y=r['reference'];ret=z.flat[r['idx']]/np.maximum(r['yy'],1e-12)
    eligible=(~r['occupied'])&(z>2*y)&(z-y>.0001)
    ids=np.flatnonzero(eligible&(z==maximum_filter(z,3,mode='wrap'))&(z>=.01))
    ids=ids[np.lexsort((ids,-z.ravel()[ids]))];used=np.zeros(z.shape,bool);n=0
    for k in ids:
        if used.flat[k]:continue
        n+=1;rr,dd=divmod(int(k),512);used.flat[roi(rr,dd)]=True
    en=np.square(z.ravel()[r['hids']]).sum(axis=1)
    attenuation=10*np.log10(r['bypass_henergy']/np.maximum(en,1e-30))
    change=10*np.log10(np.maximum(en,1e-30)/np.maximum(r['old_henergy'],1e-30))
    return dict(false40=n,retention=ret.tolist(),target_error=np.abs(z.flat[r['idx']]-r['yy']).tolist(),
        below_half=int(np.sum(ret<.5)),new_half=int(np.sum((r['old_ret']>=.5)&(ret<.5))),
        max_drop=float(np.max(r['old_ret']-ret)),
        harmonic_attenuation_db=attenuation.tolist(),harmonic_worsening_db=change.tolist())

def aggregate(rows):
    hs=[v for m in rows for v in m['harmonic_worsening_db']]
    return dict(frames=len(rows),targets=sum(len(m['retention']) for m in rows),below_half=sum(m['below_half'] for m in rows),
        new_half=sum(m['new_half'] for m in rows),max_drop=max(m['max_drop'] for m in rows),
        mean_false40=float(np.mean([m['false40'] for m in rows])),mae=float(np.mean([x for m in rows for x in m['target_error']])),
        worst_harmonic_worsening_db=max(hs,default=0.),harmonic_regions_worse_1db=sum(x>1 for x in hs),
        worst_harmonic_attenuation_db=min((x for m in rows for x in m['harmonic_attenuation_db']),default=0.))

def safe(m,base):return m['new_half']==0 and m['max_drop']<=.05+1e-7 and m['mae']<=base['mae']+.005+1e-7
def quality(m,base):
    gates=dict(target_safety=safe(m,base),all_half=m['below_half']==0,background=m['mean_false40']<=.9*base['mean_false40'],worst_harmonics=m['worst_harmonic_worsening_db']<=1+1e-7)
    return dict(gates=gates,pass_all=all(gates.values()))

def bounds(records):
    out=[]
    for r in records:
        mr=r['model'].flat[r['idx']]/np.maximum(r['yy'],1e-12)
        floor=r['floor'].flat[r['idx']]/np.maximum(r['yy'],1e-12)
        covered=r['mask'].flat[r['idx']]
        for j,(o,m) in enumerate(zip(r['old_ret'],mr)):
            if covered[j] or m>=o:continue
            out.append(dict(frame=r['meta']['id'],target=j+1,source_pixel=int(r['idx'][j]),old_retention=float(o),model_retention=float(m),
                unprotected=True,half_alpha_bound=float(np.clip((o-.5)/(o-m),0,1)) if o>=.5 else None,
                drop005_alpha_bound=float(min(1,.05/(o-m)))))
    return out

def scan():
    if (ROOT/'FROZEN.json').exists():raise FileExistsError('Already frozen; no rescanning')
    rs=[prepare(r) for r in load_old('validation')]
    baserows=[metrics(r,r['old']) for r in rs];base=aggregate(baserows)
    scans={};paths=[]
    for mode in ['protected','linear']:
        dest=ROOT/'reports'/f'scan_{mode}.json'
        if dest.exists():
            obj=read(dest);assert obj['sources']==sources();scans[mode]=obj['rows'];continue
        curves=[]
        for step in range(101):
            alpha=step/100;rows=[metrics(r,fuse(r,alpha,mode=='protected')) for r in rs]
            met=aggregate(rows);curves.append(dict(alpha=alpha,summary=met,target_safe=safe(met,base),quality=quality(met,base),frames=rows))
            if step%10==0:print('扫描',mode,alpha,met['new_half'],round(met['mean_false40'],2),flush=True)
        write(dest,dict(sources=sources(),rows=curves,baseline=base,frame_ids=[r['meta']['id'] for r in rs]));scans[mode]=curves
    feasible=[x for x in scans['protected'] if x['target_safe']]
    if feasible:
        selected=min(feasible,key=lambda x:(x['summary']['mean_false40'],x['summary']['worst_harmonic_worsening_db'],x['summary']['mae'],x['alpha']))
    else:selected=scans['protected'][0]
    write(ROOT/'reports/VALIDATION_BOUNDS.json',dict(records=bounds(rs)))
    write(ROOT/'FROZEN.json',dict(alpha=selected['alpha'],sources=sources(),safe_grid_count=len(feasible),
        validation=selected,baseline=base,quality_pass=selected['quality']['pass_all'],before_new_test_generation=True,
        note='选定网格参数，不等于证明通过。保护端点不等同纯旧网。'))
    print('冻结alpha',selected['alpha'],'安全网格点',len(feasible),'验证质量',selected['quality'],flush=True)
    register=[]
    for r in rs:register.append(dict(role='已看过验证/选参',metadata=r['meta'],source_report=r['source_report'],source_report_sha256=sha(r['source_report']),source_arrays=r['source_arrays'],source_arrays_sha256=sha(r['source_arrays'])))
    write(ROOT/'data/validation_register.json',dict(records=register))

def diagnostic():
    f=read(ROOT/'FROZEN.json');assert sources()==f['sources']
    records=[];groups={k:[] for k in CFG['frozen_test_methods']}
    for r in [prepare(x) for x in load_old('test')]:
        outs=dict(old40=r['old'],model=r['model'],old_alpha075=fuse(r,.75,True),selected_protected=fuse(r,f['alpha'],True),selected_linear=fuse(r,f['alpha'],False))
        ms={k:metrics(r,z) for k,z in outs.items()}
        for k,m in ms.items():groups[k].append(m)
        records.append(dict(metadata=r['meta'],metrics=ms,source_report=r['source_report'],source_arrays=r['source_arrays'],source_report_sha256=sha(r['source_report']),source_arrays_sha256=sha(r['source_arrays'])))
    summary={k:aggregate(v) for k,v in groups.items()}
    write(ROOT/'reports/OLD_TEST_DIAGNOSTIC.json',dict(records=records,summary=summary,quality=quality(summary['selected_protected'],summary['old40']),note='已看过旧测试，仅诊断，未用于选alpha'))

def newdata():
    frozen=read(ROOT/'FROZEN.json');assert sources()==frozen['sources']
    path=ROOT/'data/test_manifest.json'
    if path.exists():return read(path)['records']
    records=[]
    for i,t in enumerate(CFG['test']['templates']):
        meta=v2.previous.scene(CFG['test']['seed_base']+i,t,i,0);id=f'{i:03d}_{t}'
        adc=v2.echo(meta);si=np.where(adc.real>=0,1,-1).astype('i1');sq=np.where(adc.imag>=0,1,-1).astype('i1')
        ref=v2.power(adc);base=v2.power(64*si.astype('f8')+64j*sq.astype('f8'))
        p=ROOT/'data/test'/(id+'.npz');p.parent.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(p,adc_i=adc.real.astype('i2'),adc_q=adc.imag.astype('i2'),sign_i=si,sign_q=sq,reference=ref,base=base)
        records.append(dict(id=id,split='new_test',**meta,file=str(p),sha256=sha(p)))
        print('生成新测试',id,flush=True)
    write(path,dict(records=records,frozen_sha256=sha(ROOT/'FROZEN.json'),sources=sources()));return records

def test():
    frozen=read(ROOT/'FROZEN.json');assert sources()==frozen['sources']
    net=v2.load_model(v2.MODEL,40)
    for meta in newdata():
        p=ROOT/'reports/test'/(meta['id']+'.json')
        if p.exists():assert read(p)['frozen_sha256']==sha(ROOT/'FROZEN.json');continue
        with np.load(meta['file']) as z:si,sq,base,ref=[z[k] for k in ['sign_i','sign_q','base','reference']]
        y,x=v2.amplitudes(ref,base);feat=v2.ENGINE.features(base);old=x*v2.guarded_gain(base,v2.gain_float(net,feat),feat)
        model,sr=solver.solve(si,sq,{**v2.CFG['solver'],'strategy':'residual24'})
        floor,mask,states=v2.support(x,old,sr)
        r=prepare(dict(meta=meta,reference=y,bypass=x,old=old,model=model,floor=floor,mask=mask))
        outs=dict(reference=y,bypass=x,old40=old,model=model,old_alpha075=fuse(r,.75,True),selected_protected=fuse(r,frozen['alpha'],True),selected_linear=fuse(r,frozen['alpha'],False))
        metrics_={k:metrics(r,outs[k]) for k in CFG['frozen_test_methods']}
        arr=ROOT/'results/arrays'/(meta['id']+'.npz');arr.parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(arr,**outs)
        sp=ROOT/'reports/test'/(meta['id']+'_solver.json');write(sp,sr)
        write(p,dict(metadata=meta,metrics=metrics_,arrays=str(arr),arrays_sha256=sha(arr),solver_report=str(sp),solver_sha256=sha(sp),
            support=states,harmonic_labels=r['hlabels'],target_peak_indices=r['idx'].tolist(),frozen_sha256=sha(ROOT/'FROZEN.json')))
        print('新测试完成',meta['id'],{k:m['below_half'] for k,m in metrics_.items()},flush=True)
    rows=[read(ROOT/'reports/test'/(m['id']+'.json')) for m in newdata()]
    summary={k:aggregate([r['metrics'][k] for r in rows]) for k in CFG['frozen_test_methods']}
    write(ROOT/'reports/TEST_SUMMARY.json',dict(summary=summary,quality=quality(summary['selected_protected'],summary['old40']),alpha=frozen['alpha']))
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['scan','diagnostic','test']);a=p.parse_args()
    dict(scan=scan,diagnostic=diagnostic,test=test)[a.stage]()
