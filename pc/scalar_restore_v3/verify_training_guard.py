"""Check that the differentiable deployment layer matches integer inference."""
import numpy as np
import torch
from experiment import ROOT,OLD,read,write,pair,old_records,features_for_policy,apply_guard,guarded_gain

torch.set_num_threads(2);rng=np.random.default_rng(120905);rows=[]
for rec_id in ['historical_0024','field_rx_blocks_per_chirp_rx0_0351']:
    r=next(r for r in old_records() if r['id']==rec_id)
    _,p,f=pair(r);f=features_for_policy(f,'guarded_child',2)
    config=read(OLD/'research_candidate/config.json')['power_guard']
    g=rng.integers(2048,24577,size=p.shape,dtype='u2')
    for n in [128,512]:
        mask=apply_guard(p,np.full(p.shape,8192,dtype='u2'),config,f,n)!=8192
        anchor=p==p.max()
        with torch.no_grad():
            actual=guarded_gain(torch.from_numpy(g.astype('f8')/16384),torch.from_numpy(mask),torch.from_numpy(anchor),torch.full(p.shape,n)).numpy()*16384
        expected=apply_guard(p,g,config,f,n)
        diff=np.abs(actual-expected.astype('f8'))
        rows.append(dict(id=rec_id,actual_chirps=n,max_q14_lsb_difference=float(diff.max()),mean_difference=float(diff.mean()),pass_rounding_bound=bool(diff.max()<=.5+1e-8)))
checks=dict(integer_guard_matches_training_within_half_lsb=all(r['pass_rounding_bound'] for r in rows))
write(ROOT/'TRAINING_GUARD_CHECK.json',dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,rows=rows))
print(checks,flush=True)
assert all(checks.values())
