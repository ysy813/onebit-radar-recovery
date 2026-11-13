"""Guard-aware fine tuning; frozen v2 assets and raw captures are read only."""
from pathlib import Path
import sys,json,hashlib,time,argparse,copy
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'scalar_restore_v2'
sys.path.insert(0,str(OLD))
import numpy as np
import torch
from torch.nn import functional as F
from scipy.ndimage import maximum_filter,uniform_filter,binary_dilation
from common_v2 import HardwareNetwork,scene,decode,fft2,power64,prepare,directional_features,amplitudes,apply_power
from model import features_for_policy,IntegerCorrector
from scalar_guard import apply_guard
from evaluate import load_net,original_features,measures,summarize

def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def old_records(name='manifest.json'):
    return [dict(r,pair_path=str(OLD/r['file'])) for r in read(OLD/name)['records']]
def pair(record):
    with np.load(record['pair_path']) as d:return d['reference'],d['base'],d['features']
def save_pair(name,echo,meta,hw):
    p=ROOT/'pairs'/(name+'.npz');p.parent.mkdir(exist_ok=True)
    if p.exists():raise FileExistsError(p)
    n=echo.shape[1];one=np.where(echo.real<0,-64,64)+1j*np.where(echo.imag<0,-64,64)
    if n<512:echo=np.pad(echo,((0,0),(0,512-n)));one=np.pad(one,((0,0),(0,512-n)))
    ref=power64(fft2(echo));base=power64(fft2(one));feat,*_=prepare(base,hw)
    np.savez_compressed(p,reference=ref,base=base,features=directional_features(feat))
    return dict(meta,id=name,pair_path=str(p),file=str(p.relative_to(ROOT)),sha256=sha(p),actual_chirps=n)

def build(split):
    protocol=read(ROOT/'EXPERIMENT_PROTOCOL.json');out=ROOT/(split+'_manifest.json')
    if out.exists():raise FileExistsError(out)
    if split=='fresh_test':
        frozen=read(ROOT/'FROZEN_MODEL.json');assert sha(frozen['path'])==frozen['sha256']
        assert sha(ROOT/'PROFILE_POLICY.json')==frozen['profile_policy_sha256']
        jobs=[('fresh_test',*protocol['fresh_test']['synthetic_seeds'])]
    else:jobs=[('train',*protocol['training']['new_synthetic_seeds']),('development',*protocol['development']['new_synthetic_seeds'])]
    hw=HardwareNetwork();rows=[]
    for group,lo,hi in jobs:
        for i,seed in enumerate(range(lo,hi+1)):
            echo,meta=scene(seed,i);n=128 if i%2==0 else 512
            meta.update(split=group,group='synthetic')
            rows.append(save_pair(f'v3_synth_{seed}_{n}',echo[:,:n],meta,hw));print('PAIR',group,seed,n,flush=True)
    if split=='fresh_test':
        used={r['source_frame_zero_based'] for name in ['manifest.json','followup_test_manifest.json','confirm_test_manifest.json'] for r in old_records(name) if 'source_frame_zero_based' in r}
        for frame in protocol['fresh_test']['raw_frames_zero_based']:
            assert frame not in used
            channels,payload=decode(frame,'rx_blocks_per_chirp')
            for j,rx in enumerate([0,3]):
                meta=dict(split='fresh_test',group='field_temporal',targets=[],layout_assumed='rx_blocks_per_chirp',rx_id=rx,source_frame_zero_based=frame,physical_layout_confirmed=False,raw_frame_sha256=hashlib.sha256(payload).hexdigest())
                rows.append(save_pair(f'v3_field_rx{rx}_{frame:04d}',channels[j],meta,hw));print('PAIR','field',frame,rx,flush=True)
    write(out,dict(records=rows,protocol_sha256=sha(ROOT/'EXPERIMENT_PROTOCOL.json'),code_sha256=sha(__file__)))

def prepare_pool():
    destination=ROOT/'training_pool.npz'
    if destination.exists():return
    records=[r for r in old_records() if r['split']=='train']+[r for r in read(ROOT/'development_manifest.json')['records'] if r['split']=='train']
    initial,ck=load_net(OLD/'runs/soft_patch5/step_30000.pt');initial.eval();cfg=ck['config']['power_guard']
    rng=np.random.default_rng(120901);pools=[];details=[]
    for r in records:
        ref,p,f=pair(r);y,x=amplitudes(ref,p);f=features_for_policy(f,'guarded_child',2)
        reference_peak=(y==maximum_filter(y,3,mode='wrap'))&(y>.003)
        center=np.zeros(p.shape,bool)
        for t in r.get('targets',[]):
            rr=round(t['range_bin']);aa=round(t['doppler_bin']);ri=np.arange(rr-2,rr+3)%1024;ai=np.arange(aa-2,aa+3)%512
            pos=np.unravel_index(y[np.ix_(ri,ai)].argmax(),(5,5));center[ri[pos[0]],ai[pos[1]]]=True
        support=binary_dilation(reference_peak,iterations=1)|binary_dilation(center,iterations=2)
        background=(y<.003)&~support
        artifacts=(x>1.5*y+.0002)&~support
        weakcenters=reference_peak&(y<.25)&(x>=.5*y)
        artpeaks=artifacts&(x==maximum_filter(x,3,mode='wrap'))&(x>.005)
        ids=[]
        for mask,count in [(center,4096),(weakcenters,4096),(reference_peak,2048),(artpeaks,2048),(artifacts,4096),(background,4096),(np.ones(p.shape,bool),4096)]:
            valid=np.flatnonzero(mask);ids.extend(rng.choice(valid,count,replace=True) if len(valid) else rng.integers(p.size,size=count))
        ids=np.asarray(ids);n=r['actual_chirps'];fp=f[:,ids].T.astype('f4')/4096
        # Reuse full-frame input-derived decisions: no reference enters the guard.
        guard_mask=apply_guard(p,np.full(p.shape,8192,dtype='u2'),cfg,f,n)!=8192
        anchor=p==p.max()
        # Training distillation uses the frozen floating teacher only at sampled
        # pixels; all selection/test comparisons use the exact integer teacher.
        with torch.no_grad():
            raw_teacher=initial.gain(torch.from_numpy(fp))
            teacher=guarded_gain(raw_teacher,torch.from_numpy(guard_mask.ravel()[ids,None]),torch.from_numpy(anchor.ravel()[ids,None]),torch.full((len(ids),1),n)).numpy().ravel()
        extra=np.column_stack([x.ravel()[ids],y.ravel()[ids],center.ravel()[ids],reference_peak.ravel()[ids],background.ravel()[ids],artifacts.ravel()[ids],guard_mask.ravel()[ids],anchor.ravel()[ids],np.full(len(ids),n),teacher])
        pools.append(np.column_stack([fp,extra]).astype('f4'));details.append(dict(id=r['id'],pair_sha256=r['sha256'],samples=len(ids),known_centers=int(center.sum()),actual_chirps=n))
        print('POOL',r['id'],flush=True)
    np.savez_compressed(destination,pool=np.concatenate(pools));write(ROOT/'TRAINING_INPUTS.json',dict(records=details,columns='32 Q12 scaled features; input/reference amplitude; known-center; reference-local-peak; background; artifact; input-guard-mask; anchor; actual-chirps; v2-floating-final-gain',teacher_float_only_for_training=True,quality_comparisons_are_integer=True,no_previous_test_in_training=True))

def guarded_gain(g,mask,anchor,chirps):
    soft=g+F.relu(1-g)*((g-.25)/.25).clamp(0,1)
    corrected=torch.where(chirps==512,soft,torch.maximum(g,torch.ones_like(g)))
    return torch.where(anchor>0,torch.ones_like(g),torch.where(mask>0,corrected,g))

def train(steps,protect,lr,distill=0):
    torch.set_num_threads(2);torch.manual_seed(120902);rng=np.random.default_rng(120903)
    folder=ROOT/'runs'/(f'guardaware_p{protect:g}'+(f'_d{distill:g}' if distill else ''))
    folder.mkdir(parents=True,exist_ok=False)
    net,ck=load_net(OLD/'runs/soft_patch5/step_30000.pt');net.train();config=copy.deepcopy(ck['config'])
    config.update(v3_guard_aware_training=True,protect_strength=protect,background_log_gain_distillation_strength=distill,learning_rate=lr,initial_model_sha256=sha(OLD/'runs/soft_patch5/step_30000.pt'),protocol_sha256=sha(ROOT/'EXPERIMENT_PROTOCOL.json'),training_inputs_sha256=sha(ROOT/'TRAINING_INPUTS.json'),old_v2_test_not_used_for_training=True)
    write(folder/'config.json',config);(folder/'training_source.py').write_bytes(Path(__file__).read_bytes())
    with np.load(ROOT/'training_pool.npz') as d:pool=torch.from_numpy(d['pool'])
    opt=torch.optim.Adam(net.parameters(),lr=lr);start=time.perf_counter()
    for step in range(steps+1):
        if step%1000==0 or step==steps:
            torch.save(dict(state=net.state_dict(),config=config,boost=net.boost,step=step),folder/f'step_{step:05d}.pt');print('TRAIN',protect,step,round(time.perf_counter()-start,2),flush=True)
        if step==steps:break
        if step==steps*2//3:
            for group in opt.param_groups:group['lr']=lr*.25
        b=pool[torch.from_numpy(rng.integers(len(pool),size=3072))];f=b[:,:32]
        x,y,known,peaks,bg,artifact,mask,anchor,chirps,teacher=[b[:,i:i+1] for i in range(32,42)]
        raw=net(f);g=torch.exp2(raw.clamp(-3,.5849625));final=guarded_gain(g,mask,anchor,chirps);pred=x*final;old=x*teacher
        goal=torch.log2((y+1e-5)/(x+1e-5)).clamp(-3,.5849625)
        weight=1+3*peaks+5*known
        loss=.1*(F.smooth_l1_loss(raw,goal,reduction='none')*weight).sum()/weight.sum()
        loss+=.25*((torch.log1p(pred/.001)-torch.log1p(y/.001)).abs()*weight).sum()/weight.sum()
        loss+=20*((pred-y).square()*weight).sum()/weight.sum()
        protect_mask=((known+peaks)>0).float()*(y>.003)
        err=(pred-y).abs();baseerr=(x-y).abs()
        penalty=F.relu(err-baseerr-.0003)/(y+.003)
        penalty+=2*F.relu(.56*y-pred)/(y+.003)*(x>=.5*y)
        loss+=protect*(penalty*protect_mask).sum()/protect_mask.sum().clamp_min(1)
        # Preserve already-good v2 outputs where no extra target evidence exists.
        loss+=.5*((final-teacher).abs()*bg).sum()/bg.sum().clamp_min(1)
        loss+=2*(F.relu(pred-old-.0001)/(y+.005)*bg).sum()/bg.sum().clamp_min(1)
        if distill:
            loss+=distill*(torch.log2(final/teacher).square()*bg).sum()/bg.sum().clamp_min(1)
        loss+=.3*((F.relu(pred-y)/(y+.01)).square()*artifact).sum()/artifact.sum().clamp_min(1)
        opt.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(net.parameters(),5);opt.step()
        if step%1000==0:
            with (folder/'loss.jsonl').open('a',encoding='utf8') as out:out.write(json.dumps(dict(step=step,loss=float(loss.detach()),seconds=time.perf_counter()-start))+'\n')
    write(folder/'summary.json',dict(status='TRAINED_NOT_SELECTED',steps=steps,seconds=time.perf_counter()-start))

def cached_gain(row,f,hw):
    old=OLD/'baseline_cache'/(row['id']+'.npz')
    if old.exists():
        with np.load(old) as d:return d['gain']
    p=ROOT/'baseline_cache'/(row['id']+'.npz');p.parent.mkdir(exist_ok=True)
    if p.exists():
        with np.load(p) as d:return d['gain']
    g=hw.runtime.predict_gain_q14(original_features(f));np.savez_compressed(p,gain=g);return g

def summary_for_rows(rows):
    summary=summarize(rows);ng={}
    for group in sorted(set(r['group']+('_'+str(r['actual_chirps']) if r['group']=='synthetic' else '') for r in rows)):
        rr=[r for r in rows if r['group']+('_'+str(r['actual_chirps']) if r['group']=='synthetic' else '')==group]
        ng[group]=dict(nmse_relative_to_v2=float(np.mean([r['metrics']['all']['nmse_ratio'] for r in rr])/np.mean([r['previous_v2']['metrics']['all']['nmse_ratio'] for r in rr])),background_error_relative_to_v2=sum(r['background_positive_error'] for r in rr)/max(sum(r['previous_v2']['background_positive_error'] for r in rr),1e-30))
    summary['v2_nonregression']=ng;summary['checks']['v2_background_and_nmse_nonregression']=all(max(v.values())<=1.05 for v in ng.values());summary['passed']=all(summary['checks'].values())
    return summary

def assess(path,records,output,save=False,profiles=False):
    output.mkdir(parents=True,exist_ok=False);net,ck=load_net(path);fixed=IntegerCorrector(net);old=HardwareNetwork();initial,c0=load_net(OLD/'runs/soft_patch5/step_30000.pt');prior=IntegerCorrector(initial);rows=[]
    baseline_measures={}
    baseline_report=ROOT/'development_step15000/report.json'
    if baseline_report.exists():baseline_measures={r['id']:(r['original'],r['previous_v2']) for r in read(baseline_report)['rows']}
    for r in records:
        ref,p,f=pair(r);og=cached_gain(r,f,old);ff=features_for_policy(f,'guarded_child',2);n=r['actual_chirps']
        cached=ROOT/'prior_cache'/(r['id']+'.npz');cached.parent.mkdir(exist_ok=True)
        if cached.exists():
            with np.load(cached) as d:g0=d['gain']
        else:
            g0=apply_guard(p,prior.predict(ff),c0['config']['power_guard'],ff,n);np.savez_compressed(cached,gain=g0)
        gg=g0.copy() if profiles and n==128 else apply_guard(p,fixed.predict(ff),ck['config']['power_guard'],ff,n)
        out=apply_power(p,gg)
        nr=measures(ref,p,out,gg,r);prior_power=apply_power(p,g0)
        if r['id'] in baseline_measures:v7,v2=baseline_measures[r['id']]
        else:v7=measures(ref,p,apply_power(p,og),og,r);v2=measures(ref,p,prior_power,g0,r)
        group='field_layout_stress' if r['group']=='field_temporal' and r.get('layout_assumed')=='sample_interleaved' else r['group']
        rows.append(dict(id=r['id'],group=group,split=r['split'],actual_chirps=n,layout_assumed=r.get('layout_assumed'),inference_profile='frozen_v2_128' if profiles and n==128 else 'corrected_512',**nr,original=v7,previous_v2=v2))
        if save:
            a=output/'arrays';a.mkdir(exist_ok=True);np.savez_compressed(a/(r['id']+'.npz'),reference=ref,base=p,enhanced=out,gain=gg,previous_power=prior_power,previous_gain=g0,original_gain=og)
        print('EVAL',path.parent.name,path.name,r['id'],round(nr['metrics']['all']['nmse_ratio'],4),'knownloss',sum(t['newly_below_half'] for t in nr['targets']),flush=True)
    summary=summary_for_rows(rows)
    result=dict(status='PASS' if summary['passed'] else 'FAIL',summary=summary,rows=rows,model_path=str(path),model_sha256=sha(path),scope='Quality only; no IP/BIT or board test',protocol_sha256=sha(ROOT/'EXPERIMENT_PROTOCOL.json'))
    write(output/'report.json',result);print('SUMMARY',output.name,result['status'],summary['checks'],flush=True);return result

def dev_records(short=False):
    old=old_records();records=[r for r in old if r['split']=='validation' or r['group']=='historical_development']
    records+=[r for r in read(ROOT/'development_manifest.json')['records'] if r['split']=='development']
    # Previous failed holdout is explicitly development for this new design.
    records+=old_records('confirm_test_manifest.json')
    if short:records=[r for r in records if r['group']=='synthetic']
    return records

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['build','pool','train','evaluate']);ap.add_argument('--split',default='development');ap.add_argument('--steps',type=int,default=15000);ap.add_argument('--protect',type=float,default=8);ap.add_argument('--lr',type=float,default=.00002);ap.add_argument('--distill',type=float,default=0);ap.add_argument('--checkpoint',type=Path);ap.add_argument('--output',type=Path);ap.add_argument('--short',action='store_true');ap.add_argument('--save',action='store_true');a=ap.parse_args();torch.set_num_threads(2)
    if a.action=='build':build(a.split)
    elif a.action=='pool':prepare_pool()
    elif a.action=='train':train(a.steps,a.protect,a.lr,a.distill)
    else:
        records=read(ROOT/'fresh_test_manifest.json')['records'] if a.split=='fresh_test' else dev_records(a.short)
        if a.split=='fresh_test':
            frozen=read(ROOT/'FROZEN_MODEL.json');assert sha(a.checkpoint)==frozen['sha256'];assert sha(ROOT/'PROFILE_POLICY.json')==frozen['profile_policy_sha256']
        assess(a.checkpoint,records,a.output,a.save,profiles=a.split=='fresh_test')
