"""Read-only diagnosis of the previously observed weak-target failure."""
from pathlib import Path
import sys,json
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'scalar_restore_v2'
sys.path.insert(0,str(OLD))
from evaluate import load_net
from model import features_for_policy,IntegerCorrector
from scalar_guard import local_max,apply_guard
from common_v2 import amplitudes

report=json.loads((OLD/'independent_test_final/report.json').read_text(encoding='utf8'))
manifest=json.loads((OLD/'confirm_test_manifest.json').read_text(encoding='utf8'))
row=next(r for r in report['rows'] if r['id']=='confirm_synth_116013_512')
meta=next(r for r in manifest['records'] if r['id']==row['id'])
net,ck=load_net(OLD/'runs/soft_patch5/step_30000.pt')
with np.load(OLD/meta['file']) as d:p=d['base'];ref=d['reference'];f=d['features']
ff=features_for_policy(f,'guarded_child',2);g=IntegerCorrector(net).predict(ff)
outg=apply_guard(p,g,ck['config']['power_guard'],ff,512)
y,x=amplitudes(ref,p);peak=int(p.max());mx9=local_max(p,9);mx3=local_max(p,3)
targets=[]
for t in row['targets']:
    if not t['newly_below_half']:continue
    r,a=t['measured_peak_bin'];i=r*512+a
    z=ff[[0,4,5],i].astype('i8')<<4;v=z.copy()
    for _ in range(4):v=(v*z+32768)>>16
    near=bool(p[r,a]>=(peak+9999)//10000 and p[r,a]>=int(mx3[r,a])//2+int(mx3[r,a])%2)
    mask=bool(0<int(p[r,a])<=peak//16 and (p[r,a]==mx9[r,a] or near))
    explanation=[dict(order=h,parent_amplitude=float(v[j]/65536),relative_residual=float(abs(h*v[0]-v[j])/max(v[j],1)),explained=bool(v[j]>=16384 and 2*abs(h*v[0]-v[j])<=v[j])) for j,h in [(1,3),(2,5)]]
    targets.append(dict(**t,core_gain=float(g[r,a]/16384),guard_gain=float(outg[r,a]/16384),input_features_q12=ff[:,i].tolist(),input_power=int(p[r,a]),frame_peak_power=peak,near_peak=near,weak_mask_before_harmonics=mask,harmonic_explanations=explanation,patch_core_gain=(g[np.ix_(np.arange(r-2,r+3)%1024,np.arange(a-2,a+3)%512)]/16384).tolist()))
result=dict(id=row['id'],targets=targets)
(ROOT/'weak_diagnosis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(result,ensure_ascii=False,indent=2))
