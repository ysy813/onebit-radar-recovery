"""Independent controlled loss ablation. Frozen protocol; no board access."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'source'))
from common import (np,torch,math,read,write,sha,network,ENGINE,generate_pair,
                    amplitudes,roi,masks,gain_float,guarded_gain,frame_metrics)
from scalar_guard import local_max
from scipy.ndimage import maximum_filter
from torch.nn import functional as F
import argparse,time,shutil,json
CFG=read(ROOT/'PROTOCOL.json')
SHAPE=(1024,512)

def scene(seed,template,ti,rep):
    rng=np.random.default_rng(seed)
    grid='grid' if (ti+rep)%2==0 else 'offgrid'
    if template.startswith('single'):
        count=1;family='single';grid=template.split('_')[1]
    elif template.startswith('collision'):
        count=2;family=template
    else:
        n,family=template.split('_',1);count=int(n[1:])
    targets=[]
    for j in range(count):
        for _ in range(1000):
            r=float(rng.integers(44,476));d=float(rng.integers(-214,215))
            if grid=='offgrid':r+=rng.uniform(-.49,.49);d+=rng.uniform(-.49,.49)
            if family=='near_pairs' and j%2:
                r=targets[-1]['range_bin']+float(rng.integers(3,6))
                d=targets[-1]['doppler_bin']+float(rng.integers(3,6))
            if family=='mixed_motion':d=0. if j%3==0 else abs(d)*(1 if j%3==1 else -1)
            if j and family.startswith('collision'):
                h=-3 if family.endswith('minus3') else 5
                r=(h*targets[0]['range_bin'])%1024
                d=(h*targets[0]['doppler_bin']+256)%512-256
            if all(max(abs((r-t['range_bin']+512)%1024-512),abs((d-t['doppler_bin']+256)%512-256))>=3 for t in targets):break
        else:raise RuntimeError('Unable to separate target positions')
        amp=1. if not j else float(np.exp(rng.uniform(np.log(.05),np.log(.3))) if family in ('strong_weak','collision_minus3','collision_plus5') else rng.uniform(.3,.9))
        az=float(rng.uniform(-60,60));delta=float(rng.uniform(-60,60));c=299792458.
        vr=d*c/(2*76e9*.0001*512)
        targets.append(dict(range_bin=r,doppler_bin=d,amplitude=amp,initial_phase_rad=float(rng.uniform(-np.pi,np.pi)),azimuth_deg=az,
                            velocity_direction_deg=az+delta,signed_speed_m_s=vr/math.cos(math.radians(delta)),radial_velocity_m_s=vr,
                            range_m=r*c*22500000/(2*80e12*1024)))
    return dict(seed=seed,template=template,target_count=count,grid=grid,family=family,targets=targets,
                actual_chirps=512,shape=list(SHAPE),noise=False,clutter=False)

def occupied(meta):
    out=np.zeros(SHAPE,bool)
    for t in meta['targets']:out.flat[roi(t['range_bin'],t['doppler_bin'],4)]=True
    return out

def guard_fields(base,f):
    peak=int(base.max());mx3=local_max(base,3);mx9=local_max(base,9)
    z=f[[0,4,5]].astype('i8')<<4;a=z.copy()
    for _ in range(4):a=(a*z+32768)>>16
    explained=np.zeros(base.size,bool)
    for j,h in [(1,3),(2,5)]:explained|=(a[j]>=16384)&(2*np.abs(h*a[0]-a[j])<=a[j])
    explained=explained.reshape(SHAPE)
    near=(base>=(peak+9999)//10000)&(base>=mx3//2+mx3%2)
    weak=(base>0)&(base<=peak//16)&((base==mx9)|near)&~explained
    compact_mask=(base>=(peak+9999)//10000)&(base<=peak//16)&(base==mx9)&~explained
    center=f[0].astype('i8');mean=np.maximum(f[3].astype('i8'),128)
    compact=np.minimum(4096,(np.maximum(5*center-7*mean,0)*4096+mean//2)//mean).reshape(SHAPE)/4096.
    return np.stack([weak,compact_mask*compact,base==peak]).astype('f4').reshape(3,-1)

def differentiable_guard(g,b):
    weak,compact,anchor=[b[:,j:j+1] for j in range(40,43)]
    a=g+weak*F.relu(1-g)*((g-.25)/.25).clamp(0,1)
    a=torch.where(anchor.bool(),torch.ones_like(a),a)
    return a+compact*F.relu(1-a)*((a-.25)/.25).clamp(0,1)

def prepare(split):
    dest=ROOT/'data'/f'{split}_manifest.json'
    if dest.exists():
        old=read(dest);assert old['protocol_sha256']==sha(ROOT/'PROTOCOL.json')
        assert all(sha(ROOT/r['file'])==r['sha256'] for r in old['records']);return
    if split=='test':assert (ROOT/'runs/FROZEN.json').exists()
    folder=ROOT/'data'/split;folder.mkdir(exist_ok=True);records=[]
    for rep in range(CFG['split_repeats'][split]):
        for ti,template in enumerate(CFG['templates']):
            idx=len(records);meta=scene(CFG['seed_bases'][split]+idx,template,ti,rep)
            name=f'{idx:03d}_{template}';path=folder/(name+'.npz')
            ref,base=generate_pair(meta);np.savez_compressed(path,reference=ref,base=base)
            records.append(dict(id=name,split=split,**meta,file=path.relative_to(ROOT).as_posix(),sha256=sha(path)))
            print('生成',split,name,flush=True)
    write(dest,dict(protocol_sha256=sha(ROOT/'PROTOCOL.json'),records=records,source=str(ROOT/'experiment.py'),
                    source_sha256=sha(__file__)))

def load(row):
    with np.load(ROOT/row['file']) as d:return d['reference'],d['base']

def pool():
    dest=ROOT/'data/train_pool.npy'
    if (ROOT/'data/POOL.json').exists():
        assert read(ROOT/'data/POOL.json')['sha256']==sha(dest);return torch.from_numpy(np.load(dest))
    rng=np.random.default_rng(CFG['sampling']['seed']);parts=[];origins=[];counts=[];guard_err=0.
    categories=[('centers',1024),('known',1024),('support',512),('hard',2048),('harmonics',1024),('excess',1536),('random',1024)]
    for frame,row in enumerate(read(ROOT/'data/train_manifest.json')['records']):
        ref,base=load(row);y,x=amplitudes(ref,base);f=ENGINE.features(base);m=masks(row,y,x);gf=guard_fields(base,f)
        artifact=(~occupied(row))&(x>2*y)&(x-y>.0001)
        m['hard']=artifact&(x==maximum_filter(x,3,mode='wrap'))&(x>=.003)
        harmonic=np.zeros(SHAPE,bool)
        for t in row['targets']:
            for h in CFG['harmonic_orders']:harmonic.flat[roi(h*t['range_bin'],h*t['doppler_bin'])]=True
        m['harmonics']=harmonic&artifact;m['excess']=artifact
        ids=[];cats=[]
        for cat,(key,count) in enumerate(categories):
            valid=np.arange(x.size) if key=='random' else np.flatnonzero(m[key])
            idx=rng.choice(valid,count,replace=True) if len(valid) else rng.integers(x.size,size=count)
            ids.extend(idx);cats.extend([cat]*count)
        ids=np.asarray(ids)
        b=np.column_stack([f[:,ids].T.astype('f4')/4096,x.ravel()[ids],y.ravel()[ids],
                           *[m[k].ravel()[ids] for k in ('support','known','low','centers','excess')],
                           artifact.ravel()[ids],gf[:,ids].T]).astype('f4')
        assert b.shape==(8192,43)
        # Independent pseudo-random gains exercise both protection transitions.
        probe=np.linspace(.125,1.5,x.size,dtype='f4').reshape(SHAPE)
        probe=np.roll(probe,frame*3571)
        exact=guarded_gain(base,probe,f).ravel()[ids]
        approx=differentiable_guard(torch.from_numpy(probe.ravel()[ids,None]),torch.from_numpy(b)).numpy().ravel()
        guard_err=max(guard_err,float(np.max(abs(exact-approx))))
        parts.append(b);origins.append(np.column_stack([np.full(len(ids),frame),ids,np.asarray(cats)]).astype('u4'))
        counts.append(dict(id=row['id'],rows=len(ids),unique_pixels=len(np.unique(ids)),hard_peak_pixels=int(m['hard'].sum())))
        print('样本与保护核对',row['id'],'最大增益差',round(guard_err,7),flush=True)
    assert guard_err<=.001
    arr=np.concatenate(parts);np.save(dest,arr);np.savez_compressed(ROOT/'data/train_sample_origin.npz',mapping=np.concatenate(origins))
    write(ROOT/'data/POOL.json',dict(shape=list(arr.shape),sha256=sha(dest),frames=counts,
        origin_columns=['frame_index_in_train_manifest','flat_pixel_range_times512_plus_natural_doppler','sampling_category'],categories=[x[0] for x in categories],
        origin_sha256=sha(ROOT/'data/train_sample_origin.npz'),guard_max_gain_error=guard_err,
        columns=['Q12_features_div4096[0:32]','x','y','support','known','low','centers','excess','artifact','weak_mask','compact_weight','anchor']))
    return torch.from_numpy(arr)

def losses(net,b,arm):
    f=b[:,:32];x,y,support,known,low,centers,excess=[b[:,j:j+1] for j in range(32,39)]
    raw=net(f);g=torch.exp2(raw.clamp(-3,.5849625));pred=x*g
    goal=torch.log2((y+.00001)/(x+.00001)).clamp(-3,.5849625)
    w=1+3*support+5*known+8*centers;valid=x>.00001;err=(pred-y).abs();err0=(x-y).abs();protected=centers+known
    L=[.35*(F.smooth_l1_loss(raw,goal,reduction='none')*w*valid).sum()/(w*valid).sum().clamp_min(1),
       .2*((torch.log1p(pred/.001)-torch.log1p(y/.001)).abs()*w).sum()/w.sum(),
       20*((pred-y)**2*w).sum()/w.sum(),
       4*(F.relu(err-err0-.002)*(support+known)).sum()/(support+known).sum().clamp_min(1),
       2*(F.relu(err-err0-.002)/(y+.01)*protected).sum()/protected.sum().clamp_min(1),
       .3*((F.relu(pred-y)/(y+.01))**2*excess).sum()/excess.sum().clamp_min(1),
       .1*(F.relu(g-1)*low).sum()/low.sum().clamp_min(1)]
    protected=protected.clamp(0,1)
    L.append(20*((F.relu(err-err0-.0005)/(y+.005)+F.relu(.52*y-pred)/(y+.005)*(x>=.5*y))*protected).sum()/protected.sum().clamp_min(1))
    final=x*differentiable_guard(g,b);zero=raw.sum()*0
    artifact=b[:,39:40].bool().ravel()
    err_art=(F.relu((final-y-.001)/(x+.01))**2).ravel()[artifact]
    hard=(err_art.topk(min(64,max(1,math.ceil(len(err_art)*.25)))).values.mean()+.25*err_art.mean()) if len(err_art) else zero
    all_target=((F.relu(.8*y-final)+.25*F.relu(.8*y-pred)+.25*(final-y).abs())/(y+.005)*centers).sum()/centers.sum().clamp_min(1)
    L.extend([3*hard if CFG['arms'][arm]['artifact'] else zero,12*all_target if CFG['arms'][arm]['target'] else zero])
    return torch.stack(L)

def train():
    p=pool();cfg=CFG['training']
    assert sha(ROOT/'initial/model_float.pt')==CFG['initial_sha256']
    for arm in CFG['arms']:
        folder=ROOT/'runs'/arm;folder.mkdir(exist_ok=True)
        if (folder/'COMPLETE.json').exists():continue
        log=folder/'loss.jsonl'
        if log.exists():raise RuntimeError('Preserve partial run before restarting')
        torch.manual_seed(cfg['torch_seed']);rng=np.random.default_rng(cfg['torch_seed']+1)
        net=network(ROOT/'initial/model_float.pt').train();opt=torch.optim.Adam(net.parameters(),lr=cfg['learning_rate']);start=time.perf_counter()
        for step in range(1,cfg['steps']+1):
            b=p[torch.from_numpy(rng.integers(len(p),size=cfg['batch']))]
            terms=losses(net,b,arm);loss=terms.sum();assert torch.isfinite(loss)
            opt.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(net.parameters(),cfg['gradient_clip']);opt.step()
            if step%400==0:
                item=dict(step=step,loss=float(loss.detach()),terms=terms.detach().tolist(),seconds=time.perf_counter()-start)
                with log.open('a',encoding='utf8') as f:f.write(json.dumps(item)+'\n')
                print('训练',arm,step,round(item['loss'],4),flush=True)
            if step in cfg['checkpoints']:
                torch.save(dict(state=net.state_dict(),step=step,arm=arm,protocol_sha256=sha(ROOT/'PROTOCOL.json')),folder/f'step_{step}.pt')
        write(folder/'COMPLETE.json',dict(seconds=time.perf_counter()-start,protocol_sha256=sha(ROOT/'PROTOCOL.json'),pool_sha256=sha(ROOT/'data/train_pool.npy'),initial_sha256=CFG['initial_sha256'],script_sha256=sha(__file__)))

def metrics(meta,y,x,pred):
    b=frame_metrics(meta,y,x,pred);occupied_mask=occupied(meta)
    for t in b['targets']:
        t['retention']=t['prediction']/max(t['reference'],1e-12)
        t['bypass_retention']=t['bypass']/max(t['reference'],1e-12)
        t['upper_gain_cannot_reach_half']=1.5*t['bypass']<.5*t['reference']
    eligible=(~occupied_mask)&(pred>2*y)&(pred-y>.0001)
    cand=np.flatnonzero(eligible&(pred==maximum_filter(pred,3,mode='wrap'))&(pred>=.01))
    cand=cand[np.lexsort((cand,-pred.ravel()[cand]))];used=np.zeros(SHAPE,bool);selected=[]
    for k in cand:
        if used.flat[k]:continue
        selected.append(k);r,a=divmod(int(k),512);used.flat[roi(r,a,2)]=True
    vals=pred.ravel()[selected]
    hs=[]
    for ti,t in enumerate(meta['targets']):
        for h in CFG['harmonic_orders']:
            ids=roi(h*t['range_bin'],h*t['doppler_bin']);e0=float(np.square(x.ravel()[ids]).sum());er=float(np.square(y.ravel()[ids]).sum())
            if e0>1e-8 and er<=.0025*e0 and not occupied_mask.ravel()[ids].any():
                ee=float(np.square(pred.ravel()[ids]).sum());hs.append(dict(target=ti,order=h,attenuation_db=10*math.log10(e0/max(ee,1e-30))))
    return dict(nmse_ratio=b['nmse_ratio'],targets=b['targets'],false40=len(selected),false30=int(np.count_nonzero(vals>=10**(-30/20))),
                excess_energy=float(np.square(np.maximum(pred-y,0))[~occupied_mask].sum()),harmonics=hs,
                strongest_false_amplitude=float(pred[eligible].max()) if eligible.any() else 0.)

def aggregate(rows):
    result={}
    for name in rows[0]['metrics']:
        ms=[r['metrics'][name] for r in rows];ts=[t for m in ms for t in m['targets']]
        result[name]=dict(frames=len(ms),targets=len(ts),below_half=sum(t['retention']<.5 for t in ts),
            below_0_8=sum(t['retention']<.8 for t in ts),new_half=sum(t['new_half_loss'] for t in ts),
            mean_target_error=float(np.mean([t['absolute_error'] for t in ts])),minimum_retention=min(t['retention'] for t in ts),
            mean_false40=float(np.mean([m['false40'] for m in ms])),mean_false30=float(np.mean([m['false30'] for m in ms])),
            mean_nmse_ratio=float(np.mean([m['nmse_ratio'] for m in ms])),
            upper_gain_cannot_reach_half=sum(t['upper_gain_cannot_reach_half'] for t in ts))
    return result

def evaluate(split,paths,save_arrays=False):
    nets={k:network(v) for k,v in paths.items()};rows=[]
    outdir=ROOT/'results/arrays';outdir.mkdir(exist_ok=True)
    for row in read(ROOT/'data'/f'{split}_manifest.json')['records']:
        ref,base=load(row);y,x=amplitudes(ref,base);f=ENGINE.features(base)
        outputs={'reference':y,'bypass':x};ms={'bypass':metrics(row,y,x,x)}
        for name,net in nets.items():
            g=gain_float(net,f)
            for suffix,gg in [('raw',g),('guard',guarded_gain(base,g,f))]:
                key=name+'_'+suffix;outputs[key]=x*gg;ms[key]=metrics(row,y,x,outputs[key])
        item={k:row[k] for k in ('id','seed','template','target_count','grid','family')};item['metrics']=ms
        if save_arrays:
            file=outdir/(row['id']+'.npz');np.savez_compressed(file,**outputs);item['arrays']=str(file);item['sha256']=sha(file)
        rows.append(item);print('评估',split,row['id'],flush=True)
    return dict(rows=rows,summary=aggregate(rows),models={k:sha(v) for k,v in paths.items()},
                groups={family:aggregate([r for r in rows if r['family']==family]) for family in sorted(set(r['family'] for r in rows))})

def select():
    if (ROOT/'runs/FROZEN.json').exists():return
    paths={f'{arm}_{step}':ROOT/'runs'/arm/f'step_{step}.pt' for arm in CFG['arms'] for step in CFG['training']['checkpoints']}
    paths['initial']=ROOT/'initial/model_float.pt'
    report=evaluate('validation',paths);write(ROOT/'reports/VALIDATION.json',report)
    chosen={}
    for arm in CFG['arms']:
        def rank(step):
            s=report['summary'][f'{arm}_{step}_guard']
            return(s['below_half'],s['new_half'],s['mean_false40'],s['mean_nmse_ratio'])
        step=min(CFG['training']['checkpoints'],key=rank);src=ROOT/'runs'/arm/f'step_{step}.pt'
        dest=ROOT/'candidate'/arm;dest.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest/'model_float.pt')
        chosen[arm]=dict(step=step,path=str(dest/'model_float.pt'),sha256=sha(dest/'model_float.pt'),validation=report['summary'][f'{arm}_{step}_guard'])
    write(ROOT/'runs/FROZEN.json',dict(arms=chosen,primary='joint',protocol_sha256=sha(ROOT/'PROTOCOL.json'),before_test_generation=True))
    print('四组验证选模与冻结完成',chosen,flush=True)

def test():
    if (ROOT/'reports/TEST.json').exists():return
    frozen=read(ROOT/'runs/FROZEN.json')
    paths={k:Path(v['path']) for k,v in frozen['arms'].items()}
    assert all(sha(paths[k])==frozen['arms'][k]['sha256'] for k in paths)
    prepare('test');paths['initial']=ROOT/'initial/model_float.pt'
    report=evaluate('test',paths,True)
    c=report['summary']['control_guard'];j=report['summary']['joint_guard']
    gates=dict(all_half_no_increase=j['below_half']<=c['below_half'],new_half_no_increase=j['new_half']<=c['new_half'],
               target_mae=j['mean_target_error']<=c['mean_target_error']+.005,false40=j['mean_false40']<=.8*c['mean_false40'],
               false30=j['mean_false30']<=.9*c['mean_false30'],nmse=j['mean_nmse_ratio']<=1.05*c['mean_nmse_ratio'])
    report['gates']=gates;report['research_improvement_pass']=all(gates.values());report['strict_all_target_pass']=j['below_half']==0 and j['new_half']==0
    report['deployment_ready']=False;write(ROOT/'reports/TEST.json',report)
    print('最终测试完成',json.dumps(dict(gates=gates,summary=report['summary']),ensure_ascii=False),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','train','select','test']);args=parser.parse_args()
    if args.stage=='prepare':prepare('train');prepare('validation')
    else:globals()[args.stage]()
