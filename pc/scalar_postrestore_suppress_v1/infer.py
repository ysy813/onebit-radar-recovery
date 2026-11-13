"""Only the post-restoration neural stage; no labels or reference inputs."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run import ROOT,np,read,sha,write,ENGINE,load_model,net_gain
import argparse

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    f=read(ROOT/'FROZEN.json');weight=ROOT/'candidate/suppress/model_float.pt'
    assert sha(weight)==f['selected']['suppress']['checkpoint_sha256']
    with np.load(a.input,allow_pickle=False) as d:
        model=d['recovered_amplitude'];peak=int(d['original_onebit_peak'])
    if model.shape!=(1024,512) or not np.isfinite(model).all() or (model<0).any() or model.max()>1.000001:raise ValueError('Expected nonnegative normalized recovered amplitude')
    if not 0<=peak<2**63:raise ValueError('Invalid source power peak')
    proxy=np.rint(model.astype('f8')**2*peak).astype('u8');features=ENGINE.features(proxy)
    gain=net_gain(load_model(weight,40),features);output=model*gain
    a.output.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(a.output,output=output,gain=gain)
    write(a.output.with_suffix('.json'),dict(input_sha256=sha(a.input),output_sha256=sha(a.output),weights_sha256=sha(weight),no_truth_or_reference=True,frontend_included=False,deployment_ready=False))
    print('后级网络推理完成：未读取真值或多比特参考；不包含前端残差求解。')

if __name__=='__main__':main()
