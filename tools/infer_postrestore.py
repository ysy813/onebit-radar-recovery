"""Portable packaging adapter; identical frozen postrestore numerical rules."""
from pathlib import Path
import sys, hashlib, json, math, argparse
sys.dont_write_bytecode=True
REPO=Path(__file__).resolve().parents[1]
LEGACY=REPO/'pc/scalar_multipeak48_v1'
sys.path.insert(0,str(LEGACY));sys.path.insert(0,str(LEGACY/'source/baseline'))
import numpy as np
import torch
from restore_power import PowerRestorer
from model48 import load_model
WEIGHT=REPO/'pc/scalar_postrestore_suppress_v1/candidate/suppress/model_float.pt'

def infer(amplitude,peak):
    a=np.asarray(amplitude)
    if a.shape!=(1024,512) or not np.isfinite(a).all() or (a<0).any() or a.max()>1.000001:
        raise ValueError('恢复幅值必须为1024×512、有限、非负，最大值不超过1')
    if not 0<=int(peak)<2**63:raise ValueError('功率峰超出范围')
    frozen=json.loads((REPO/'pc/scalar_postrestore_suppress_v1/FROZEN.json').read_text(encoding='utf8'))
    if hashlib.sha256(WEIGHT.read_bytes()).hexdigest()!=frozen['selected']['suppress']['checkpoint_sha256']:
        raise ValueError('冻结权重散列不符')
    torch.set_num_threads(2)
    features=PowerRestorer(LEGACY/'source/baseline').features(np.rint(a.astype('f8')**2*int(peak)).astype('u8'))
    net=load_model(WEIGHT,40);gain=np.empty(features.shape[1],'f4')
    with torch.no_grad():
        for start in range(0,len(gain),32768):
            f=torch.from_numpy(features[:,start:start+32768].T.astype('f4')/4096)
            gain[start:start+len(f)]=torch.exp2(net(f).clamp(-6,math.log2(1.5))).numpy().ravel()
    gain=gain.reshape(1024,512)
    return a*gain,gain

def main():
    p=argparse.ArgumentParser(description='冻结后级去伪网络：不含前端求解，不读取真值')
    p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    with np.load(args.input,allow_pickle=False) as z:output,gain=infer(z['recovered_amplitude'],int(z['original_onebit_peak']))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(args.output,output=output,gain=gain)
    print('后级推理完成；未读取真值；不包含符号恢复前端。')
if __name__=='__main__':main()
