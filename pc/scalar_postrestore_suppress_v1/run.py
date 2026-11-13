import sys
sys.dont_write_bytecode=True
from pathlib import Path
ROOT=Path(__file__).resolve().parent;SRC=ROOT.parent/'scalar_sign_evidence_v2'
sys.path.insert(0,str(SRC))
import experiment_v2 as v2
from experiment_v2 import np,read,write,sha,roi,ENGINE,load_model,gain_float,guarded_gain
import solver
import torch
from torch.nn import functional as F
from scipy.ndimage import maximum_filter
import argparse,time,json,shutil,math
CFG=read(ROOT/'PROTOCOL.json');torch.set_num_threads(2)
BIN_M=299792458.*22500000/(2*80e12*1024)
RANGE_MASK=np.broadcast_to((np.arange(1024)*BIN_M<=40)[:,None],(1024,512))
OLD_MODEL=ROOT.parent/CFG['initial_model']

def digests():
    paths=[Path(__file__),ROOT/'PROTOCOL.json',OLD_MODEL,SRC/'solver.py',SRC/'experiment_v2.py',SRC/'PROTOCOL.json']
    paths+=list(v2.OLD.glob('*.py'))+list((v2.OLD/'source').rglob('*.py'))
    return {str(p):sha(p) for p in sorted(set(paths))}

def scene(seed,template,i):
    m=v2.previous.scene(seed,template,i,0)
    low,high=[(1,5),(5,20),(20,39.5)][i%3]
    for t in m['targets']:
        r=(low+(t['range_bin']-44)/(476-44)*(high-low))/BIN_M
        r=float(np.clip(r,low/BIN_M,high/BIN_M))
        t['range_bin']=float(round(r)) if m['grid']=='grid' else r
    if 'collision' in template:
        h=-3 if 'minus3' in template else 5
        m['targets'][1]['range_bin']=(h*m['targets'][0]['range_bin']+(1.6 if template.startswith('near_') else 0))%1024
    for t in m['targets']:t['range_m']=t['range_bin']*BIN_M
    m.update(range_design_m=[low,high],note='仅距离重映射，点频RD仿真；非完整近场或车载运动模型')
    return m

def old_records():
    records=[]
    for split in ['development','validation','test']:
        for m in read(SRC/'data'/f'{split}_manifest.json')['records']:
            row=read(SRC/'reports'/split/(m['id']+'.json'))
            sr=Path(row['solver_reports']['residual24'])
            assert read(sr)['code_sha256']==sha(SRC/'solver.py')
            records.append(dict(id=f'v2_{split}_{m["id"]}',metadata=m,source_arrays=row['arrays'],model_key='residual24_model',solver_report=str(sr),source_report=str(SRC/'reports'/split/(m['id']+'.json')),origin='已看过v2数据，转为训练'))
    scan=ROOT.parent/'scalar_fusion_weight_scan_v1'
    for m in read(scan/'data/test_manifest.json')['records']:
        r=read(scan/'reports/test'/(m['id']+'.json'))
        records.append(dict(id='scan_'+m['id'],metadata=m,source_arrays=r['arrays'],model_key='model',solver_report=r['solver_report'],source_report=str(scan/'reports/test'/(m['id']+'.json')),origin='已看过权重扫描测试，转为训练'))
    for r in records:
        for key in ['source_arrays','solver_report','source_report']:r[key+'_sha256']=sha(r[key])
    return records

def make_new(split):
    if split=='test':
        f=read(ROOT/'FROZEN.json');assert f['sources']==digests()
    path=ROOT/'data'/f'{split}_manifest.json'
    if path.exists():
        old=read(path);assert old['sources']==digests();return old['records']
    recs=[];net=load_model(OLD_MODEL,40)
    for i,t in enumerate(CFG['templates']):
        ident=f'{i:03d}_{t}';cache=ROOT/'data'/split/(ident+'.json')
        if cache.exists():r=read(cache);assert r['sources']==digests();recs.append(r);continue
        m=scene(CFG['seeds'][split]+i,t,i);adc=v2.echo(m)
        si=np.where(adc.real>=0,1,-1).astype('i1');sq=np.where(adc.imag>=0,1,-1).astype('i1')
        ref=v2.power(adc);base=v2.power(si.astype('f8')*64+sq.astype('f8')*64j)
        inp=ROOT/'data'/split/(ident+'_input.npz');inp.parent.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(inp,adc_i=adc.real.astype('i2'),adc_q=adc.imag.astype('i2'),sign_i=si,sign_q=sq,reference=ref,base=base)
        y,x=v2.amplitudes(ref,base);feat=ENGINE.features(base);old=x*guarded_gain(base,gain_float(net,feat),feat)
        model,sr=solver.solve(si,sq,{**v2.CFG['solver'],'strategy':'residual24'})
        sp=cache.with_name(ident+'_solver.json');write(sp,sr)
        ap=cache.with_name(ident+'_spectra.npz');np.savez_compressed(ap,reference=y,bypass=x,old40=old,model=model)
        m.update(id=ident,file=str(inp),sha256=sha(inp))
        r=dict(id=split+'_'+ident,metadata=m,source_arrays=str(ap),source_arrays_sha256=sha(ap),model_key='model',solver_report=str(sp),solver_report_sha256=sha(sp),origin='新生成'+split,sources=digests())
        write(cache,r);recs.append(r);print('生成/恢复完成',split,ident,round(sr['seconds'],1),'秒',flush=True)
    write(path,dict(records=recs,sources=digests(),frozen_sha256=sha(ROOT/'FROZEN.json') if split=='test' else None));return recs

def load_record(r,features=True):
    assert sha(r['source_arrays'])==r['source_arrays_sha256']
    with np.load(r['source_arrays']) as z:y=z['reference'];x=z['bypass'];old=z['old40'];model=z[r['model_key']]
    with np.load(r['metadata']['file']) as z:base=z['base']
    proxy=np.rint(model.astype('f8')**2*int(base.max())).astype('u8')
    return dict(record=r,y=y,x=x,old=old,model=model,proxy=proxy,features=ENGINE.features(proxy) if features else None)

def prepare():
    train=old_records()+make_new('train_new');validation=make_new('validation')
    write(ROOT/'data/TRAIN_REGISTER.json',dict(records=train,sources=digests()))
    write(ROOT/'data/VALIDATION_REGISTER.json',dict(records=validation,sources=digests()))
    dest=ROOT/'data/train_pool.npz'
    if dest.exists():return
    rng=np.random.default_rng(CFG['seeds']['sampling']);pools=[];ranges=[]
    for fi,r in enumerate(train):
        z=load_record(r);m=r['metadata'];y=z['y'];x=z['model'];occupied=v2.REF.occupied(m)
        target=np.zeros(y.shape,bool);centers=np.zeros(y.shape,bool)
        for t in m['targets']:
            rr=roi(t['range_bin'],t['doppler_bin']);target.flat[rr]=True;centers.flat[rr[np.argmax(y.flat[rr])]]=True
        art=(~occupied)&(x>2*y)&(x-y>.0001)
        peaks=np.flatnonzero(art&(x==maximum_filter(x,3,mode='wrap')))
        peaks=peaks[np.argsort(-x.ravel()[peaks],kind='stable')[:128]]
        hard=np.zeros(y.shape,bool)
        for k in peaks:hard.flat[roi(*divmod(int(k),512))]=True
        hs=np.zeros(y.shape,bool)
        for t in m['targets']:
            for h in [-3,5,-7,9,-11,13,-15,17,-19,21,-23,25,-27,29]:hs.flat[roi(h*t['range_bin'],h*t['doppler_bin'])]=True
        ids=np.unique(np.r_[np.flatnonzero(target),np.flatnonzero(hard| (hs&art)),np.argpartition(x.ravel(),-512)[-512:],rng.choice(y.size,2048,False)])
        yy=y.ravel()[ids];xx=x.ravel()[ids]
        tag=np.where(target.ravel()[ids],1,np.where(art.ravel()[ids],2,0)).astype('i1')
        main=(centers.ravel()[ids]&(yy>=.25)).astype('i1');weak=(centers.ravel()[ids]&(yy<.25)).astype('i1')
        pools.append(dict(f=z['features'][:,ids].T,y=yy,x=xx,tag=tag,main=main,weak=weak,pixel=ids.astype('i4'),frame=np.full(len(ids),fi,'i2')))
        ranges.append(dict(frame=fi,id=r['id'],rows=len(ids)));print('构建训练池',fi+1,'/',len(train),len(ids),flush=True)
    joined={k:np.concatenate([p[k] for p in pools]) for k in pools[0]};np.savez_compressed(dest,**joined)
    write(ROOT/'data/POOL_REGISTER.json',dict(frames=ranges,rows=len(joined['x']),file=str(dest),sha256=sha(dest),source_sha256=sha(ROOT/'data/TRAIN_REGISTER.json'),fields='f=32基础Q12特征，y/x=参考/恢复相对幅值，tag/main/weak=训练标签，frame/pixel=精确源映射'))

def net_gain(net,features):
    out=np.empty(features.shape[1],'f4')
    with torch.no_grad():
        for st in range(0,len(out),32768):
            ft=torch.from_numpy(features[:,st:st+32768].T.astype('f4')/4096)
            out[st:st+len(ft)]=torch.exp2(net(ft).clamp(-6,math.log2(1.5))).numpy().ravel()
    return out.reshape(1024,512)

def bg_metrics(y,x,meta,mask):
    occ=v2.REF.occupied(meta);eligible=(~occ)&mask&(x>2*y)&(x-y>.0001)
    ids=np.flatnonzero(eligible&(x==maximum_filter(x,3,mode='wrap'))&(x>=.01));ids=ids[np.lexsort((ids,-x.ravel()[ids]))]
    used=np.zeros(y.shape,bool);count=0
    for k in ids:
        if used.flat[k]:continue
        count+=1;used.flat[roi(*divmod(int(k),512))]=True
    return dict(false40=count,strongest=float(x[eligible].max()) if eligible.any() else 0.,excess=float(np.square(np.maximum(x-y,0))[(~occ)&mask].sum()))

def measure(z,pred):
    m=z['record']['metadata'];full=v2.REF.metrics(m,z['y'],z['x'],pred)
    for t,src in zip(full['targets'],m['targets']):
        t.update(range_m=src['range_m'],main=t['reference']>=.25,within40=src['range_m']<=40)
    return dict(primary=bg_metrics(z['y'],pred,m,RANGE_MASK),full_bg=bg_metrics(z['y'],pred,m,np.ones((1024,512),bool)),targets=full['targets'],harmonics=full['harmonics'])

def aggregate(rows):
    ts=[t for r in rows for t in r['targets'] if t['within40']];main=[t for t in ts if t['main']];weak=[t for t in ts if not t['main']]
    return dict(frames=len(rows),targets=len(ts),main_targets=len(main),weak_targets=len(weak),
        main_half_fail=sum(t['retention']<.5 for t in main),weak_half_fail=sum(t['retention']<.5 for t in weak),
        mean_false40=float(np.mean([r['primary']['false40'] for r in rows])),worst_false=float(max(r['primary']['strongest'] for r in rows)),
        mean_excess=float(np.mean([r['primary']['excess'] for r in rows])),target_mae=float(np.mean([t['absolute_error'] for t in ts])),
        main_min_retention=float(min(t['retention'] for t in main)),weak_min_retention=float(min((t['retention'] for t in weak),default=1)),
        full_mean_false40=float(np.mean([r['full_bg']['false40'] for r in rows])))

def evaluate(net,records,guard=False):
    result=[]
    for z in records:
        gain=net_gain(net,z['features'])
        if guard:gain=guarded_gain(z['proxy'],gain,z['features'])
        result.append(measure(z,z['model']*gain))
    return result,aggregate(result)

def train():
    assert (ROOT/'data/train_pool.npz').exists()
    if (ROOT/'FROZEN.json').exists():raise FileExistsError('Already frozen')
    validation=[load_record(r) for r in read(ROOT/'data/VALIDATION_REGISTER.json')['records']]
    with np.load(ROOT/'data/train_pool.npz') as p:pool={k:p[k] for k in p.files}
    pos=np.flatnonzero(pool['tag']==1);neg=np.flatnonzero(pool['tag']==2)
    selection={}
    for arm in ['adapt','suppress']:
        done=ROOT/'runs'/arm/'COMPLETE.json'
        if done.exists():
            old=read(done);assert old['sources']==digests();selection[arm]=old['best'];continue
        torch.manual_seed(CFG['seeds']['training']);rng=np.random.default_rng(CFG['seeds']['training'])
        net=load_model(OLD_MODEL,40);net.train();opt=torch.optim.Adam(net.parameters(),lr=CFG['training']['learning_rate'])
        candidates=[];losslog=[];start=time.perf_counter()
        for step in range(1,8001):
            ids=np.r_[rng.choice(pos,128),rng.choice(neg,256),rng.integers(len(pool['x']),size=128)]
            ft=torch.from_numpy(pool['f'][ids].astype('f4')/4096);x=torch.from_numpy(pool['x'][ids]);y=torch.from_numpy(pool['y'][ids])
            main=torch.from_numpy(pool['main'][ids].astype(bool));weak=torch.from_numpy(pool['weak'][ids].astype(bool));art=torch.from_numpy((pool['tag'][ids]==2))
            s=net(ft).ravel();pred=x*torch.exp2(s.clamp(-6,math.log2(1.5)));goal=torch.log2((y+1e-6)/(x+1e-6)).clamp(-6,math.log2(1.5))
            zero=s.sum()*0
            mse=lambda mask:torch.square(pred[mask]-y[mask]).mean() if mask.any() else zero
            loss=4*torch.square(pred-y).mean()+.2*F.smooth_l1_loss(s,goal)+12*mse(main)+mse(weak)
            if arm=='suppress':loss=loss+2*F.smooth_l1_loss(s[art],goal[art])+12*torch.square(F.relu(pred[art]-y[art])).mean()
            opt.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(net.parameters(),5);opt.step()
            if step%1000==0:
                losslog.append(dict(step=step,loss=float(loss.detach())));print('训练',arm,step,round(float(loss.detach()),5),flush=True)
            if step in CFG['training']['checkpoints']:
                net.eval();rows,summary=evaluate(net,validation);net.train()
                cp=ROOT/'runs'/arm/f'step_{step}.pt';cp.parent.mkdir(parents=True,exist_ok=True)
                torch.save(dict(state=net.state_dict(),dimensions=40,step=step,arm=arm,gain_min=1/64,gain_max=1.5),cp)
                log=dict(step=step,checkpoint=str(cp),checkpoint_sha256=sha(cp),summary=summary,frames=rows)
                write(cp.with_suffix('.json'),log);candidates.append(log);print('验证',arm,step,summary,flush=True)
        best=min(candidates,key=lambda r:(r['summary']['main_half_fail'],r['summary']['mean_false40'],r['summary']['worst_false'],r['summary']['mean_excess'],r['summary']['target_mae'],r['step']))
        selection[arm]=best
        write(done,dict(best=best,candidates=[c['step'] for c in candidates],loss_log=losslog,seconds=time.perf_counter()-start,sources=digests(),pool_sha256=sha(ROOT/'data/train_pool.npz')))
    write(ROOT/'FROZEN.json',dict(selected=selection,sources=digests(),primary='suppress_raw',before_test_generation=True,training_pool_sha256=sha(ROOT/'data/train_pool.npz')))
    for arm,info in selection.items():
        dest=ROOT/'candidate'/arm/'model_float.pt';dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(info['checkpoint'],dest)
    print('选模冻结完成', {k:v['step'] for k,v in selection.items()},flush=True)

def test():
    f=read(ROOT/'FROZEN.json');assert f['sources']==digests()
    recs=make_new('test');oldnet=load_model(OLD_MODEL,40);nets={a:load_model(ROOT/'candidate'/a/'model_float.pt',40) for a in ['adapt','suppress']}
    allrows=[]
    for r in recs:
        p=ROOT/'reports/test'/(r['id']+'.json')
        if p.exists():row=read(p);assert row['frozen_sha256']==sha(ROOT/'FROZEN.json');allrows.append(row);continue
        z=load_record(r);s=net_gain(nets['suppress'],z['features'])
        outs=dict(reference=z['y'],bypass=z['x'],old40=z['old'],model=z['model'],old_serial=z['model']*guarded_gain(z['proxy'],gain_float(oldnet,z['features']),z['features']),
            adapt_raw=z['model']*net_gain(nets['adapt'],z['features']),suppress_raw=z['model']*s,suppress_guard=z['model']*guarded_gain(z['proxy'],s,z['features']))
        ms={k:measure(z,v) for k,v in outs.items() if k not in ['reference','bypass']}
        ap=ROOT/'results/arrays'/(r['id']+'.npz');ap.parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(ap,**outs)
        row=dict(record=r,metrics=ms,arrays=str(ap),arrays_sha256=sha(ap),frozen_sha256=sha(ROOT/'FROZEN.json'));write(p,row);allrows.append(row)
        print('最终评估',r['id'],{k:(m['primary']['false40'],sum(t['main'] and t['within40'] and t['retention']<.5 for t in m['targets'])) for k,m in ms.items()},flush=True)
    summary={k:aggregate([r['metrics'][k] for r in allrows]) for k in allrows[0]['metrics']};a=summary['suppress_raw'];b=summary['model'];o=summary['old_serial']
    gates=dict(main_targets=a['main_half_fail']==0,peaks_vs_model=a['mean_false40']<=.8*b['mean_false40'],peaks_vs_old_serial=a['mean_false40']<=.9*o['mean_false40'],excess=a['mean_excess']<=.8*b['mean_excess'],worst_false=a['worst_false']<=b['worst_false']+1e-7)
    write(ROOT/'reports/TEST_SUMMARY.json',dict(summary=summary,gates=gates,quality_pass=all(gates.values()),deployment_ready=False))
    print(json.dumps(dict(summary=summary,gates=gates),ensure_ascii=False),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','train','test']);a=p.parse_args();dict(prepare=prepare,train=train,test=test)[a.stage]()
