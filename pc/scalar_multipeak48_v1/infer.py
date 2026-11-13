"""Research inference. Uses base power only; no reference or scene labels."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'source'))
from common import np,ENGINE,guarded_gain
from model48 import load_model,gain_float
from features48 import extract
import argparse

def restore(base,model):
    if base.shape!=(1024,512) or base.dtype!=np.dtype('u8'):raise ValueError('Expected natural-order1024x512 uint64 power')
    if not base.any():return np.full(base.shape,16384,'u2'),base.copy(),np.zeros(base.shape,'f4')
    f=ENGINE.features(base);extra=extract(f);net=load_model(model)
    g=guarded_gain(base,gain_float(net,f,extra),f);q=np.rint(g*16384).astype('u2');p=ENGINE.apply_power(base,q)
    x=np.sqrt(base.astype('f8'));x/=max(x.max(),1)
    return q,p,(x*g).astype('f4')

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--model',type=Path,default=ROOT/'candidate/f48_repair/model_float.pt');a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    with np.load(a.input,allow_pickle=False) as d:base=d['base']
    q,power,x=restore(base,a.model);np.savez_compressed(a.output,gain_q14=q,power=power,relative_amplitude=x)
    print('48维研究网络推理完成：仅使用输入功率；尚非完整PL定点实现。')

if __name__=='__main__':main()
