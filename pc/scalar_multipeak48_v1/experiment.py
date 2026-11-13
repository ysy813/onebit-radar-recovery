"""48-feature controlled experiment: data, audit, train, freeze, fresh test."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'source'))
from common import np,torch,math,read,write,sha,ENGINE,generate_pair,amplitudes,roi,masks,guarded_gain
import reference_v2 as REF
REF.CFG=read(ROOT/'source/v2_protocol.json')
from features48 import extract,scalar_features,tables,round_even,dist
from model48 import load_model,gain_float,integer_gain
from scipy.ndimage import maximum_filter
from torch.nn import functional as F
import argparse,time,json,shutil
CFG=read(ROOT/'PROTOCOL.json')
SHAPE=(1024,512)

def scene(seed,template,ti,rep):
    grid='grid' if (ti+rep)%2==0 else 'offgrid'
    base=template
    if template.endswith('_grid'):grid='grid';base=template[:-5]
    if template.endswith('_offgrid'):grid='offgrid';base=template[:-8]
    if template.startswith('single'):grid=template.split('_')[1];base='single_'+grid
    if template.startswith('near_collision'):base=template.replace('near_','');grid='offgrid'
    row=REF.scene(seed,base,0 if grid=='grid' else 1,0)
    if template.startswith('near_collision'):
        row['targets'][1]['range_bin']=(row['targets'][1]['range_bin']+1.6)%1024
        row['targets'][1]['doppler_bin']=(row['targets'][1]['doppler_bin']-.9+256)%512-256
        row['family']=template
    for t in row['targets']:
        t['range_m']=t['range_bin']*299792458.*22500000/(2*80e12*1024)
        t['radial_velocity_m_s']=t['doppler_bin']*299792458./(2*76e9*.0001*512)
        delta=t['velocity_direction_deg']-t['azimuth_deg']
        t['signed_speed_m_s']=t['radial_velocity_m_s']/math.cos(math.radians(delta))
    row['template']=template
    return row

def prepare(split):
    dest=ROOT/'data'/f'{split}_manifest.json'
    if dest.exists():
        assert read(dest)['protocol_sha256']==sha(ROOT/'PROTOCOL.json');return
    if split=='test':assert (ROOT/'runs/FROZEN.json').exists()
    folder=ROOT/'data'/split;folder.mkdir(exist_ok=True);rows=[]
    for rep in range(CFG['split_repeats'][split]):
        for ti,template in enumerate(CFG['templates']):
            idx=len(rows);meta=scene(CFG['seed_bases'][split]+idx,template,ti,rep);name=f'{idx:03d}_{template}'
            ref,base=generate_pair(meta);path=folder/(name+'.npz');np.savez_compressed(path,reference=ref,base=base)
            rows.append(dict(id=name,split=split,**meta,file=path.relative_to(ROOT).as_posix(),sha256=sha(path)))
            print('生成',split,name,flush=True)
    write(dest,dict(records=rows,protocol_sha256=sha(ROOT/'PROTOCOL.json'),generator=str(ROOT/'experiment.py'),generator_sha256=sha(__file__)))

def load(row):
    with np.load(ROOT/row['file']) as d:return d['reference'],d['base']

def harmonic_masks(meta,y,x):
    occupied=REF.occupied(meta);low=np.zeros(SHAPE,bool);high=low.copy()
    for t in meta['targets']:
        for h in CFG['harmonic_orders']:
            ids=roi(h*t['range_bin'],h*t['doppler_bin']);e0=float(np.square(x.ravel()[ids]).sum());er=float(np.square(y.ravel()[ids]).sum())
            if e0>1e-8 and er<=.0025*e0 and not occupied.ravel()[ids].any():
                (low if h in [-3,5] else high).flat[ids]=True
    artifact=(~occupied)&(x>2*y)&(x-y>.0001)
    return low&artifact,high&artifact,artifact

def pool():
    path=ROOT/'data/train_pool.npy';note=ROOT/'data/POOL.json'
    if note.exists():assert sha(path)==read(note)['sha256'];return torch.from_numpy(np.load(path))
    rng=np.random.default_rng(CFG['training']['sampling_seed']);parts=[];origins=[];counts=[];audit=[];geometry=[];guard_error=0.
    categories=list(CFG['training']['categories'].items())
    for fi,row in enumerate(read(ROOT/'data/train_manifest.json')['records']):
        ref,base=load(row);y,x=amplitudes(ref,base);f=ENGINE.features(base);m=masks(row,y,x);gf=REF.guard_fields(base,f)
        low,high,artifact=harmonic_masks(row,y,x)
        m.update(harmonic_low=low,harmonic_high=high,hard=artifact&(x==maximum_filter(x,3,mode='wrap'))&(x>=.003),excess=artifact)
        ids=[];cats=[];fallback=[]
        for ci,(key,count) in enumerate(categories):
            valid=np.arange(x.size) if key=='random' else np.flatnonzero(m[key])
            choice=rng.choice(valid,count,replace=True) if len(valid) else rng.integers(x.size,size=count)
            ids.extend(choice);cats.extend([ci]*count);fallback.extend([not len(valid)]*count)
        ids=np.asarray(ids);extra=extract(f,ids)
        b=np.column_stack([f[:,ids].T.astype('f4')/4096,x.ravel()[ids],y.ravel()[ids],
            *[m[k].ravel()[ids] for k in ('support','known','low','centers','excess')],artifact.ravel()[ids],gf[:,ids].T,
            extra.T.astype('f4')/4096,low.ravel()[ids],high.ravel()[ids]]).astype('f4')
        assert b.shape==(8192,53)
        # Separate scalar address calculation, including edges and actual targets.
        checkids=np.unique(np.concatenate([np.array([0,511,512,1024*512-1]),ids[:4],np.flatnonzero(m['centers'])]))
        vx=extract(f,checkids);tab=tables(f)
        scalar=np.stack([scalar_features(f,k,tab) for k in checkids],1)
        if not np.array_equal(vx,scalar):raise AssertionError(('feature mismatch',row['id']))
        audit.append(dict(id=row['id'],checked_points=len(checkids),max_q12_error=0))
        centers=np.flatnonzero(m['centers']);_,geom=extract(f,centers,True)
        for t in row['targets']:
            pos=roi(t['range_bin'],t['doppler_bin']);k=int(pos[np.argmax(y.ravel()[pos])]);ix=int(np.flatnonzero(centers==k)[0])
            bgeom=[int(v[ix]) for v in geom['center']]
            for h in [-7,9]:
                actual=(round(h*t['range_bin'])%1024,round(h*t['doppler_bin'])%512)
                original=((h*(k//512))%1024,(h*(k%512))%512)
                refined=(int(round_even(h*bgeom[2],16))%1024,int(round_even(h*bgeom[3],16))%512)
                od=int(dist(original[0],original[1],*actual));nd=int(dist(refined[0],refined[1],*actual))
                geometry.append(dict(id=row['id'],grid=row['grid'],family=row['family'],order=h,original_error_bins=od,refined_error_bins=nd,original_covered=od<=2,refined_covered=nd<=2))
        probe=np.linspace(.125,1.5,x.size,dtype='f4').reshape(SHAPE);probe=np.roll(probe,fi*3571)
        exact=guarded_gain(base,probe,f).ravel()[ids]
        approx=REF.differentiable_guard(torch.from_numpy(probe.ravel()[ids,None]),torch.from_numpy(b)).numpy().ravel()
        guard_error=max(guard_error,float(np.max(abs(exact-approx))))
        parts.append(b);origins.append(np.column_stack([np.full(len(ids),fi),ids,cats,fallback]).astype('u4'))
        counts.append(dict(id=row['id'],samples=len(ids),unique_pixels=len(np.unique(ids)),fallback_samples=int(sum(fallback))))
        print('训练池与新增特征核对',row['id'],flush=True)
    zeros=np.zeros((32,1024*512),'u2');zeroextra=extract(zeros,np.array([0,511,524287]));assert not zeroextra.any()
    assert guard_error<=.001
    init40=load_model(ROOT/'initial/joint40.pt',40);init48=load_model(ROOT/'initial/joint40.pt',48)
    check=torch.from_numpy(np.concatenate([parts[0][:64,:32],parts[0][:64,43:51]],1))
    with torch.no_grad():initerr=float((init40(check)-init48(check)).abs().max())
    assert initerr<1e-5
    ar=np.concatenate(parts);np.save(path,ar);np.savez_compressed(ROOT/'data/train_sample_origin.npz',mapping=np.concatenate(origins))
    write(note,dict(sha256=sha(path),shape=list(ar.shape),frames=counts,origin_columns=['frame_index','flat_pixel_index','sampling_category','fallback_to_random'],categories=[k for k,_ in categories],
                    origin_sha256=sha(ROOT/'data/train_sample_origin.npz'),columns='0..42 same as v2;43..50 extra8/4096;51 pure_low_harmonic;52 pure_high_harmonic'))
    write(ROOT/'reports/FEATURE_AUDIT.json',dict(status='PASS',scalar_checks=audit,guard_max_gain_error=guard_error,zero_pass=True,initial_function_error=initerr,
        feature_code_sha256=sha(ROOT/'features48.py'),geometry=geometry,geometry_summary={grid:dict(count=len(rs),original_coverage=float(np.mean([r['original_covered'] for r in rs])),refined_coverage=float(np.mean([r['refined_covered'] for r in rs]))) for grid in ['grid','offgrid'] if (rs:=[r for r in geometry if r['grid']==grid])},
        coverage_limit='位置覆盖审计不等于真伪识别率；多目标局部峰/旁瓣可能改变细化，真值只在审计中使用'))
    return torch.from_numpy(ar)

def losses(net,b,repair):
    z=torch.cat([b[:,:32],b[:,43:51]],1)
    original=REF.losses(lambda f:net(torch.cat([f,b[:,43:51]],1)),b,'joint')
    raw=net(z);x=b[:,32:33];y=b[:,33:34];center=b[:,37:38]
    goal=torch.log2((y+1e-5)/(x+1e-5)).clamp(-3,.5849625)
    minimum=torch.log2((.8*y+1e-5)/(x+1e-5)).clamp(-3,.5849625)
    target=((2*F.smooth_l1_loss(raw,goal,reduction='none')+4*F.relu(minimum-raw))*center).sum()/center.sum().clamp_min(1)
    new=[target]
    for col,w in [(51,4),(52,2)]:
        mask=b[:,col:col+1];new.append(w*(F.smooth_l1_loss(raw,goal,reduction='none')*mask).sum()/mask.sum().clamp_min(1))
    return torch.cat([original,torch.stack(new) if repair else torch.stack([raw.sum()*0]*3)])

def train():
    p=pool();cfg=CFG['training'];assert sha(ROOT/'initial/joint40.pt')==CFG['initial_sha256']
    for name,arm in CFG['arms'].items():
        folder=ROOT/'runs'/name;folder.mkdir(exist_ok=True)
        if (folder/'COMPLETE.json').exists():continue
        log=folder/'loss.jsonl'
        if log.exists():raise RuntimeError('Interrupted training must be preserved')
        torch.manual_seed(cfg['torch_seed']);rng=np.random.default_rng(cfg['torch_seed']+1)
        net=load_model(ROOT/'initial/joint40.pt',arm['dimensions']).train();opt=torch.optim.Adam(net.parameters(),lr=cfg['learning_rate']);start=time.perf_counter()
        for step in range(1,cfg['steps']+1):
            b=p[torch.from_numpy(rng.integers(len(p),size=cfg['batch']))];terms=losses(net,b,arm['repair']);loss=terms.sum();assert torch.isfinite(loss)
            opt.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(net.parameters(),cfg['gradient_clip']);opt.step()
            if step%500==0:
                item=dict(step=step,total=float(loss.detach()),terms=terms.detach().tolist(),seconds=time.perf_counter()-start)
                with log.open('a',encoding='utf8') as f:f.write(json.dumps(item)+'\n')
                print('训练',name,step,round(item['total'],4),flush=True)
            if step in cfg['checkpoints']:torch.save(dict(state=net.state_dict(),dimensions=arm['dimensions'],step=step,arm=name,protocol_sha256=sha(ROOT/'PROTOCOL.json')),folder/f'step_{step}.pt')
        write(folder/'COMPLETE.json',dict(seconds=time.perf_counter()-start,protocol_sha256=sha(ROOT/'PROTOCOL.json'),pool_sha256=sha(ROOT/'data/train_pool.npy'),initial_sha256=CFG['initial_sha256'],code_sha256=sha(__file__),feature_sha256=sha(ROOT/'features48.py'),model_sha256=sha(ROOT/'model48.py')))

def summarize(rows):
    out=REF.aggregate(rows)
    for name,s in out.items():
        s['new_half_vs_initial']=sum(a['retention']>=.5 and b['retention']<.5 for r in rows for a,b in zip(r['metrics']['initial_guard']['targets'],r['metrics'][name]['targets']))
        s['single_harmonics']={}
        regressions=[]
        for h in CFG['harmonic_orders']:
            vals=[]
            for row in rows:
                if row['family']!='single':continue
                hs=[v for v in row['metrics'][name]['harmonics'] if v['order']==h]
                ref=[v for v in row['metrics']['clean_guard']['harmonics'] if v['order']==h]
                vals.extend(v['attenuation_db'] for v in hs)
                regressions.extend(a['attenuation_db']-b['attenuation_db'] for a,b in zip(ref,hs))
            if vals:s['single_harmonics'][str(h)]=dict(count=len(vals),minimum_db=min(vals),median_db=float(np.median(vals)))
        s['worst_single_harmonic_regression_vs_clean_db']=max(regressions,default=0.)
    return out

def gates(summary,name):
    s=summary[name];i=summary['initial_guard'];hs=s['single_harmonics']
    return dict(all_targets_half=s['below_half']==0,no_new_individual_half_vs_initial=s['new_half_vs_initial']==0,
        low_harmonic_min=all(str(h) in hs and hs[str(h)]['minimum_db']>=10 for h in [-3,5]),
        high_harmonic_min=all(str(h) in hs and hs[str(h)]['minimum_db']>=3 for h in CFG['harmonic_orders'] if h not in [-3,5]),
        single_harmonic_regression=s['worst_single_harmonic_regression_vs_clean_db']<=3,
        artifact=s['mean_false40']<=1.05*i['mean_false40'],target_mae=s['mean_target_error']<=i['mean_target_error']+.005)

def evaluate(split,paths,save_arrays=False):
    nets={k:load_model(v) for k,v in paths.items()};rows=[];folder=ROOT/'results/arrays';folder.mkdir(exist_ok=True)
    for row in read(ROOT/'data'/f'{split}_manifest.json')['records']:
        ref,base=load(row);y,x=amplitudes(ref,base);f=ENGINE.features(base);extra=extract(f)
        outputs={'reference':y,'bypass':x};metrics={'bypass':REF.metrics(row,y,x,x)}
        for name,net in nets.items():
            raw=gain_float(net,f,extra)
            for suffix,g in [('raw',raw),('guard',guarded_gain(base,raw,f))]:
                key=name+'_'+suffix;outputs[key]=x*g;metrics[key]=REF.metrics(row,y,x,outputs[key])
        item={k:row[k] for k in ['id','seed','family','template','target_count','grid']};item['metrics']=metrics
        if save_arrays:
            path=folder/(row['id']+'.npz');np.savez_compressed(path,**outputs);item['arrays']=str(path);item['arrays_sha256']=sha(path)
        rows.append(item);print('评估',split,row['id'],flush=True)
    summary=summarize(rows)
    return dict(rows=rows,summary=summary,models={k:sha(v) for k,v in paths.items()},
        groups={g:summarize([r for r in rows if r['family']==g]) for g in sorted({r['family'] for r in rows})},
        gates={k:gates(summary,k) for k in summary if k.endswith('_guard')})

def select():
    if (ROOT/'runs/FROZEN.json').exists():return
    paths={f'{arm}_{step}':ROOT/'runs'/arm/f'step_{step}.pt' for arm in CFG['arms'] for step in CFG['training']['checkpoints']}
    paths.update(initial=ROOT/'initial/joint40.pt',clean=ROOT/'initial/clean40.pt')
    report=evaluate('validation',paths);write(ROOT/'reports/VALIDATION.json',report);chosen={}
    for arm in CFG['arms']:
        def rank(step):
            key=f'{arm}_{step}_guard';s=report['summary'][key];g=report['gates'][key]
            deficit=sum(max(0,10-s['single_harmonics'].get(str(h),dict(minimum_db=-100))['minimum_db']) for h in [-3,5])
            return(sum(not v for v in g.values()),s['below_half'],s['new_half_vs_initial'],deficit,s['mean_false40'],s['mean_target_error'])
        step=min(CFG['training']['checkpoints'],key=rank);folder=ROOT/'candidate'/arm;folder.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/'runs'/arm/f'step_{step}.pt',folder/'model_float.pt')
        chosen[arm]=dict(step=step,path=str(folder/'model_float.pt'),sha256=sha(folder/'model_float.pt'),validation_gates=report['gates'][f'{arm}_{step}_guard'],validation=report['summary'][f'{arm}_{step}_guard'])
    write(ROOT/'runs/FROZEN.json',dict(primary='f48_repair',arms=chosen,protocol_sha256=sha(ROOT/'PROTOCOL.json'),before_final_test=True))
    print('验证冻结完成',json.dumps({k:dict(step=v['step'],gates=v['validation_gates'],half=v['validation']['below_half'],false40=v['validation']['mean_false40']) for k,v in chosen.items()},ensure_ascii=False),flush=True)

def feature_value(rows,prefix):
    a=prefix.replace('48','40')+'_guard';b=prefix+'_guard';s=summarize(rows);ca,cb=s[a],s[b]
    newloss=sum(x['retention']>=.5 and y['retention']<.5 for r in rows for x,y in zip(r['metrics'][a]['targets'],r['metrics'][b]['targets']))
    reg=max((x['attenuation_db']-y['attenuation_db'] for r in rows if r['family']=='single' for x,y in zip(r['metrics'][a]['harmonics'],r['metrics'][b]['harmonics'])),default=0.)
    conditions=dict(no_new_target_loss=newloss==0,harmonic_no_more_than_1db_regression=reg<=1,
        target_mae=cb['mean_target_error']<=ca['mean_target_error']+.002,
        actual_benefit=cb['mean_false40']<=.95*ca['mean_false40'] or cb['below_half']<ca['below_half'])
    return dict(new_half_losses=newloss,worst_harmonic_regression_db=reg,conditions=conditions,passed=all(conditions.values()))

def test():
    if (ROOT/'reports/TEST.json').exists():return
    frozen=read(ROOT/'runs/FROZEN.json');paths={k:Path(v['path']) for k,v in frozen['arms'].items()}
    assert all(sha(paths[k])==v['sha256'] for k,v in frozen['arms'].items())
    prepare('test');paths.update(initial=ROOT/'initial/joint40.pt',clean=ROOT/'initial/clean40.pt')
    report=evaluate('test',paths,True);s=report['summary'];key='f48_repair_guard'
    new_vs_control=sum(a['retention']>=.5 and b['retention']<.5 for r in report['rows'] for a,b in zip(r['metrics']['f40_repair_guard']['targets'],r['metrics'][key]['targets']))
    report['gates'][key]['no_new_individual_half_vs_same_loss40']=new_vs_control==0
    report['primary_quality_pass']=all(report['gates'][key].values());report['deployment_ready']=False
    report['feature_value']={k:feature_value(report['rows'],k) for k in ['f48_base','f48_repair']}
    write(ROOT/'reports/TEST.json',report)
    print('最终测试完成',json.dumps(dict(primary_gates=report['gates'][key],feature_value=report['feature_value'],summary={k:v for k,v in s.items() if k.endswith('_guard')}),ensure_ascii=False),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','train','select','test']);a=p.parse_args()
    if a.stage=='prepare':prepare('train');prepare('validation')
    else:globals()[a.stage]()
