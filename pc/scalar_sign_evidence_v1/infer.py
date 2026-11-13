"""Independent CLI: only sign arrays and one-bit power, never reference labels."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'scalar_multipeak48_v1'
sys.path.insert(0,str(OLD));sys.path.insert(0,str(OLD/'source'))
from common import np,read,write,sha,ENGINE,gain_float,guarded_gain
from model48 import load_model
from sign_solver import solve,gate
import argparse

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists() or a.output.with_suffix('.json').exists():raise FileExistsError(a.output)
    cfg=read(ROOT/'PROTOCOL.json');frozen=read(ROOT/'FROZEN.json');model=ROOT.parent/cfg['baseline']
    assert sha(ROOT/'sign_solver.py')==frozen['solver_sha256'] and sha(model)==frozen['model_sha256']
    with np.load(a.input,allow_pickle=False) as d:
        si=d['sign_i'];sq=d['sign_q'];base=d['base']
    if base.shape!=(1024,512) or base.dtype!=np.dtype('u8'):raise ValueError('Expected uint64 one-bit power')
    f=ENGINE.features(base);net=load_model(model,40);x=np.sqrt(base.astype('f8'));x=(x/max(x.max(),1)).astype('f4')
    old=x*guarded_gain(base,gain_float(net,f),f)
    reconstruction,sr=solve(si,sq,cfg['solver']);out,gr=gate(x,old,sr,**frozen['gate'])
    a.output.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(a.output,old40=old,model=reconstruction,gated=out)
    write(a.output.with_suffix('.json'),dict(solver=sr,gate=gr,input_sha256=sha(a.input),output_sha256=sha(a.output),frozen_sha256=sha(ROOT/'FROZEN.json'),deployment_ready=False))
    print('PC符号证据推理完成；仅使用符号与单比特功率，未读取多比特参考。')

if __name__=='__main__':main()
