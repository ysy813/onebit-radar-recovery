import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json,hashlib
import numpy as np
import solver
from scipy.optimize._numdiff import approx_derivative
ROOT=Path(__file__).resolve().parent
cfg=json.loads((ROOT/'PROTOCOL.json').read_text(encoding='utf8'))['solver']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(ROOT/'solver_v1_snapshot.py')==sha(ROOT.parent/'scalar_sign_evidence_v1/sign_solver.py')
rng=np.random.default_rng(721);ids=rng.choice(524288,97,False);f=np.array([[79.1,12.7],[310.4,450.2]])
a=np.array([1+.3j,.2-.1j]);v=np.r_[a.real,a.imag,f[:,0],f[:,1]];y=np.where(rng.normal(size=97)>0,1,-1)+1j*np.where(rng.normal(size=97)>0,1,-1)
_,g=solver.objective(v,ids,y,f,cfg);fd=approx_derivative(lambda v:solver.objective(v,ids,y,f,cfg)[0],v,method='3-point').ravel()
err=float(abs(g-fd).max());assert err<2e-6
assert solver.raw_candidates(np.zeros((1024,512),'c16'),cfg)==[]
report=dict(status='PASS',gradient_error=err,original_v1_snapshot_exact=True,zero_residual_no_spurious_candidates=True)
(ROOT/'reports').mkdir(exist_ok=True);(ROOT/'reports/PREFLIGHT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(report)
