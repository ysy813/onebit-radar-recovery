from pathlib import Path
import sys,json,hashlib
import numpy as np
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'model/runtime'))
from restore_power import PowerRestorer

def literal(a):
    if a.ndim==0:return str(int(a))
    return '{'+','.join(literal(v) for v in a)+'}'

def main():
    with np.load(R/'model/runtime/weights.npz') as d:
        defs=['#pragma once','#include <ap_int.h>']
        for i in range(3):
            w=d[f'w{i}'];b=d[f'b{i}']
            if i==2:w=w[0];b=b[0]
            for name,a,typ in [(f'W{i}',w,'int'),(f'B{i}',b,'long long')]:
                defs.append(f'static const {typ} {name}'+''.join(f'[{n}]' for n in a.shape)+' = '+literal(a)+';')
        defs.append('static const unsigned short GAIN[32769] = '+literal(d['gain_lut'])+';')
    defs.append('static const unsigned short ROOT5[65536] = '+literal(np.load(R/'model/runtime/root5.npy'))+';')
    (R/'hls/parameters.h').write_text('\n'.join(defs)+'\n')
    cases=[('weak512',np.load(R.parent/'scalar_restore_v3/examples_compact/diagnosed_512_power.npy'))]
    p=np.fromfile(R.parent/'radar1_scalar_v7_fullrange_v3/numeric/test_power.bin',dtype='<u8').reshape(1024,512)
    cases.append(('history512',np.roll(p,-256,1)))
    p=np.zeros((1024,512),dtype='u8');rng=np.random.default_rng(221102)
    for r,a,v in zip(rng.integers(0,1024,180),rng.integers(0,512,180),rng.integers(1,2**63,180,dtype='u8')):p[r,a]=v
    p[0,0]=np.iinfo('u8').max;p[1023,511]=2**64-2;p[1,511]=2**60
    cases.append(('u64_edges',p))
    model=PowerRestorer();records=[]
    for name,p in cases:
        out,g=model.restore(p,True,512);folder=R/'numeric'/name;folder.mkdir(exist_ok=True)
        for fn,arr in [('test_power.bin',p),('expected_power.bin',out)]:np.roll(arr,256,1).astype('<u8').tofile(folder/fn)
        np.roll(g,256,1).astype('<u2').tofile(folder/'expected_gain.bin')
        records.append(dict(name=name,changed=int((g!=16384).sum()),suppressed=int((g<16384).sum()),amplified=int((g>16384).sum()),max_gain=int(g.max()),peak=int(p.max())))
        print('GOLDEN_READY',name,records[-1],flush=True)
    (R/'numeric/cases.txt').write_text('\n'.join(n for n,_ in cases)+'\n')
    (R/'reports/numeric_vectors.json').write_text(json.dumps(dict(status='GENERATED_NOT_CSIM',cases=records,weights_sha256=hashlib.sha256((R/'model/runtime/weights.npz').read_bytes()).hexdigest()),indent=2))

if __name__=='__main__':main()
