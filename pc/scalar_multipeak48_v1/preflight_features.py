"""Early training-input check before building the complete sample pool."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from experiment import np,torch,ENGINE,write,sha,load_model,extract,scalar_features,tables

def main():
    path=ROOT/'data/train/000_single_grid_a.npz'
    with np.load(path) as d:base=d['base']
    f=ENGINE.features(base);ids=np.unique(np.r_[np.random.default_rng(2026111199).integers(base.size,size=64),0,511,512,base.size-1,np.argmax(base)])
    e=extract(f,ids);tab=tables(f);other=np.stack([scalar_features(f,i,tab) for i in ids],1)
    assert np.array_equal(e,other)
    z=torch.from_numpy(np.concatenate([f[:,ids],e],0).T.astype('f4')/4096)
    a=load_model(ROOT/'initial/joint40.pt',40);b=load_model(ROOT/'initial/joint40.pt',48)
    with torch.no_grad():err=float((a(z)-b(z)).abs().max())
    assert err<1e-5
    write(ROOT/'reports/EARLY_FEATURE_CHECK.json',dict(status='PASS',source=str(path),source_sha256=sha(path),checked_points=len(ids),q12_max_error=0,initial_function_max_error=err,feature_sha256=sha(ROOT/'features48.py')))
    print('新增特征早期核对PASS',len(ids),'点；初始函数误差',err,flush=True)

if __name__=='__main__':main()
