"""Inference accepts signs only; no target labels or reference spectrum."""
import sys
sys.dont_write_bytecode = True
import time
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from scipy.ndimage import maximum_filter
from threadpoolctl import threadpool_limits

SHAPE=(1024,512)

def roi(r,d,radius=2):
    rr=np.arange(round(float(r))-radius,round(float(r))+radius+1)%1024
    dd=np.arange(round(float(d))-radius,round(float(d))+radius+1)%512
    return (rr[:,None]*512+dd).ravel()

def raw_candidates(q,cfg):
    z=np.fft.fft2(q);amp=abs(z);peak=float(amp.max())
    if peak<=1e-20:return []
    ids=np.flatnonzero((amp==maximum_filter(amp,3,mode='wrap'))&(amp>=cfg['candidate_min_relative']*peak))
    ids=ids[np.lexsort((ids,-amp.ravel()[ids]))]
    used=np.zeros(SHAPE,bool);rows=[]
    for k in ids:
        if used.flat[k]:continue
        r,d=divmod(int(k),512);center=z[r,d];offset=[]
        for left,right,n in [(z[(r-1)%1024,d],z[(r+1)%1024,d],1024),(z[r,(d-1)%512],z[r,(d+1)%512],512)]:
            den=2*center-left-right
            delta=float(np.real((left-right)/den)) if abs(den)>1e-12 else 0.
            offset.append(float(np.clip(delta*np.tan(np.pi/n)/(np.pi/n),-.5,.5)))
        rows.append(dict(index=int(k),integer=[r,d],frequency=[r+offset[0],d+offset[1]],
                         relative_fft_peak=float(amp[r,d]/max(peak,1e-30)),initial_coefficient=[float(center.real/peak*4),float(center.imag/peak*4)]))
        used.flat[roi(r,d,cfg['candidate_nms_radius'])]=True
        if len(rows)>=cfg['candidate_limit']:break
    return rows

def propose(q,cfg):
    pool=raw_candidates(q,{**cfg,'candidate_limit':128})
    head=pool[:cfg['initial_candidates']]
    rng=np.random.default_rng(cfg['sample_seed'])
    ids=rng.choice(q.size,cfg['fit_samples']+cfg['evidence_samples'],replace=False)[:cfg['fit_samples']]
    f=np.array([r['frequency'] for r in head]);integers=np.array([r['integer'] for r in head]);a=np.array([complex(*r['initial_coefficient']) for r in head])
    a,f,log0=fit(ids,q.ravel()[ids],f,a,cfg)
    a,f,log1=fit(ids,q.ravel()[ids],f,a,cfg,True,integers,cfg['frequency_iterations'])
    z=predict(ids,f,a);pred=np.where(z.real>=0,1,-1)+1j*np.where(z.imag>=0,1,-1)
    residual=np.zeros(SHAPE,'c16');residual.ravel()[ids]=q.ravel()[ids]-pred
    candidates=raw_candidates(residual,{**cfg,'candidate_limit':128}) if cfg['strategy']=='residual24' else pool[cfg['initial_candidates']:]
    rows=[];used=np.zeros(SHAPE,bool)
    for j,r in enumerate(head):
        rows.append({**r,'frequency':f[j].tolist(),'initial_coefficient':[float(a[j].real),float(a[j].imag)],'proposal_origin':'原FFT前16'})
        used.flat[roi(*r['integer'])]=True
    additions=[]
    for origin,items in [('符号残差' if cfg['strategy']=='residual24' else '原FFT后续',candidates),('原FFT补足',pool)]:
        for r in items:
            if len(rows)>=cfg['candidate_limit']:break
            if used.flat[r['index']]:continue
            rows.append({**r,'initial_coefficient':[0.,0.],'proposal_origin':origin})
            used.flat[roi(*r['integer'])]=True
            additions.append(dict(index=r['index'],origin=origin,frequency=r['frequency']))
    return rows,dict(strategy=cfg['strategy'],initial_count=len(head),added=additions,initial_fit=log0,initial_refine=log1,
        residual_nonzero_complex_samples=int(np.count_nonzero(residual)),proposal_indices=ids.tolist(),candidate_count=len(rows))

def unpack(v,k,frequencies):
    a=v[:k]+1j*v[k:2*k]
    f=v[2*k:].reshape(2,k).T if len(v)>2*k else frequencies
    return a,f

def objective(v,indices,y,frequencies,cfg,gradient=True):
    k=len(frequencies);a,f=unpack(v,k,frequencies)
    nr=(indices//512)/1024.;nd=(indices%512)/512.
    A=np.exp(2j*np.pi*(nr[:,None]*f[None,:,0]+nd[:,None]*f[None,:,1]))
    z=A@a;yr=y.real;yi=y.imag
    loss=float(np.mean(np.logaddexp(0,-yr*z.real)+np.logaddexp(0,-yi*z.imag))/2)
    norm=np.sqrt(abs(a)**2+1e-8)
    loss+=cfg['group_l1']*norm.sum()+cfg['ridge']*np.square(abs(a)).sum()/2
    e=(-yr*expit(-yr*z.real)-1j*yi*expit(-yi*z.imag))/(2*len(y))
    ag=A.conj().T@e+(cfg['group_l1']/norm+cfg['ridge'])*a
    grad=np.r_[ag.real,ag.imag]
    if len(v)>2*k:
        gr=np.real((np.conj(e)*nr)@A*a*2j*np.pi)
        gd=np.real((np.conj(e)*nd)@A*a*2j*np.pi)
        grad=np.r_[grad,gr,gd]
    return loss,grad

def fit(indices,y,f,a,cfg,refine=False,integers=None,maxiter=None):
    if len(a)==0:
        return a,f,dict(success=True,status=0,message='Empty hypothesis',iterations=0,objective=float(np.log(2)),finite=True)
    v=np.r_[a.real,a.imag]
    bounds=None
    if refine:
        v=np.r_[v,f[:,0],f[:,1]]
        b=cfg['frequency_bound_bins']
        bounds=[(None,None)]*(2*len(a))+[(x-b,x+b) for x in integers[:,0]]+[(x-b,x+b) for x in integers[:,1]]
    result=minimize(objective,v,args=(indices,y,f,cfg),jac=True,method='L-BFGS-B',bounds=bounds,
                    options=dict(maxiter=maxiter or cfg['amplitude_iterations'],ftol=1e-10,gtol=2e-6,maxls=30))
    a,f=unpack(result.x,len(a),f)
    return a,f,dict(success=bool(result.success),status=int(result.status),message=str(result.message),iterations=int(result.nit),objective=float(result.fun),finite=bool(np.isfinite(result.x).all() and np.isfinite(result.fun)))

def predict(indices,f,a):
    return np.exp(2j*np.pi*((indices//512)[:,None]/1024*f[None,:,0]+(indices%512)[:,None]/512*f[None,:,1]))@a

def observations(y,z):
    loss=(np.logaddexp(0,-y.real*z.real)+np.logaddexp(0,-y.imag*z.imag))/2
    mismatch=float(np.mean(np.r_[np.where(z.real>=0,1,-1)!=y.real,np.where(z.imag>=0,1,-1)!=y.imag]))
    return loss,mismatch

@threadpool_limits.wrap(limits=2)
def solve(sign_i,sign_q,cfg):
    started=time.perf_counter()
    if sign_i.shape!=SHAPE or sign_q.shape!=SHAPE:raise ValueError('Expected1024x512')
    if not np.isin(sign_i,[-1,1]).all() or not np.isin(sign_q,[-1,1]).all():raise ValueError('Signs must be±1')
    q=sign_i.astype('f8')+1j*sign_q.astype('f8');rows,proposal=propose(q,cfg)
    rng=np.random.default_rng(cfg['sample_seed']);indices=rng.choice(q.size,cfg['fit_samples']+cfg['evidence_samples'],replace=False)
    fitids=indices[:cfg['fit_samples']];evalids=indices[cfg['fit_samples']:]
    f=np.array([r['frequency'] for r in rows]);integers=np.array([r['integer'] for r in rows])
    a=np.array([complex(*r['initial_coefficient']) for r in rows])
    a,f,initlog=fit(fitids,q.ravel()[fitids],f,a,cfg)
    a,f,fulllog=fit(fitids,q.ravel()[fitids],f,a,cfg,True,integers,cfg['frequency_iterations'])
    # Development correction: a logistic margin alone rewards artificial harmonics.
    # Backward sparse selection uses FIT samples only and records every deletion.
    all_f=f.copy();active=list(range(len(a)));pruning=[]
    for stage in range(len(a)-1):
        accepted=False
        for local in np.argsort(abs(a)):
            keep=np.arange(len(a))!=local
            aa,ff,plog=fit(fitids,q.ravel()[fitids],f[keep],a[keep],cfg,True,integers[np.array(active)[keep]],cfg['pruning_iterations'])
            _,error=observations(q.ravel()[fitids],predict(fitids,ff,aa))
            if plog['finite'] and error<=cfg['pruning_mismatch_max']:
                removed=active.pop(int(local));pruning.append(dict(removed=removed,remaining=len(active),fit_mismatch=error,solver=plog))
                a,f=aa,ff;accepted=True;break
        if not accepted:break
    all_f[np.array(active)]=f
    full_loss,full_mismatch=observations(q.ravel()[evalids],predict(evalids,f,a))
    _,train_mismatch=observations(q.ravel()[fitids],predict(fitids,f,a))
    audits=[]
    for j,row in enumerate(rows):
        keep=np.array(active)!=j
        a0,f0,log0=fit(fitids,q.ravel()[fitids],f[keep],a[keep],cfg,maxiter=cfg['ablation_iterations'])
        if j in active:
            a1,f1,log1=fit(fitids,q.ravel()[fitids],f,a,cfg,maxiter=cfg['ablation_iterations'])
            bj=active.index(j)
        else:
            f1=np.vstack([f0,all_f[j]]);a1=np.r_[a0,0j];bj=len(a1)-1
            a1,f1,log1=fit(fitids,q.ravel()[fitids],f1,a1,cfg,maxiter=cfg['ablation_iterations'])
        ytest=q.ravel()[evalids];z0=predict(evalids,f0,a0);z1=predict(evalids,f1,a1)
        loss0,mismatch0=observations(q.ravel()[evalids],predict(evalids,f0,a0))
        loss1,mismatch1=observations(ytest,z1);delta=loss0-loss1
        err0=((np.where(z0.real>=0,1,-1)!=ytest.real).astype(float)+(np.where(z0.imag>=0,1,-1)!=ytest.imag))/2
        err1=((np.where(z1.real>=0,1,-1)!=ytest.real).astype(float)+(np.where(z1.imag>=0,1,-1)!=ytest.imag))/2
        ed=err0-err1
        audits.append(dict(**row,fitted_frequency=all_f[j].tolist(),coefficient=[float(a1[bj].real),float(a1[bj].imag)],
                           selected_source=j in active,relative_coefficient=float(abs(a1[bj])/max(abs(a1).max(),1e-12)),
                           heldout_loss_delta=float(delta.mean()),delta_se=float(delta.std(ddof=1)/np.sqrt(len(delta))),
                           mismatch_improvement=float(ed.mean()),mismatch_se=float(ed.std(ddof=1)/np.sqrt(len(ed))),
                           h0_mismatch=mismatch0,h1_mismatch=mismatch1,h0_mean_loss=float(loss0.mean()),h0_solver=log0,h1_solver=log1))
    # Model-only relative-spectrum diagnostic, not claimed hardware-ready or an MLP output.
    s=np.zeros(SHAPE,'c16');nr=np.arange(1024)/1024.;nd=np.arange(512)/512.
    for aa,ff in zip(a,f):s+=aa*np.exp(2j*np.pi*ff[0]*nr)[:,None]*np.exp(2j*np.pi*ff[1]*nd)[None,:]
    spec=abs(np.fft.fft2(s));spec/=max(float(spec.max()),1e-30)
    report=dict(candidates=audits,fit_indices=fitids.tolist(),evidence_indices=evalids.tolist(),initial_solver=initlog,full_solver=fulllog,
                selected_sources=active,pruning=pruning,proposal=proposal,
                fit_mismatch=train_mismatch,evidence_mismatch=full_mismatch,evidence_mean_loss=float(full_loss.mean()),seconds=time.perf_counter()-started)
    return spec.astype('f4'),report

def gate(base_amplitude,old_output,report,threshold,se_multiplier):
    out=old_output.copy();protected=np.zeros(SHAPE,bool);suppressed=protected.copy();decisions=[]
    for row in report['candidates']:
        delta=row['heldout_loss_delta'];se=row['delta_se'];valid=row['h1_solver']['finite'] and row['h0_solver']['finite']
        # Nonconverged hypotheses are uncertain, never evidence for stronger attenuation.
        converged=row['h1_solver']['success'] and row['h0_solver']['success']
        sign_lower=row['mismatch_improvement']-se_multiplier*row['mismatch_se']
        sign_upper=row['mismatch_improvement']+se_multiplier*row['mismatch_se']
        support=valid and delta-se_multiplier*se>threshold and sign_lower>0 and row['relative_coefficient']>.01
        redundant=valid and converged and not row['selected_source'] and sign_upper<threshold and row['h0_mismatch']<.001
        state='支持' if support else '冗余' if redundant else '不确定'
        ids=roi(*row['fitted_frequency'])
        if support:protected.flat[ids]=True
        elif redundant:suppressed.flat[ids]=True
        decisions.append(dict(index=row['index'],state=state))
    out[suppressed]=np.minimum(out[suppressed],base_amplitude[suppressed]*.125)
    out[protected]=np.maximum(out[protected],base_amplitude[protected])
    k=int(base_amplitude.argmax());out.flat[k]=max(out.flat[k],base_amplitude.flat[k])
    return out,dict(decisions=decisions,supported=sum(r['state']=='支持' for r in decisions),redundant=sum(r['state']=='冗余' for r in decisions),uncertain=sum(r['state']=='不确定' for r in decisions),protected_pixels=int(protected.sum()),suppressed_pixels=int((suppressed&~protected).sum()))
