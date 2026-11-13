import sys
sys.dont_write_bytecode=True
from pathlib import Path
import torch
from torch import nn
import numpy as np

class Model(nn.Module):
    def __init__(self,dimensions):
        super().__init__();self.dimensions=dimensions
        self.layers=nn.Sequential(nn.Linear(dimensions,32),nn.ReLU(),nn.Linear(32,16),nn.ReLU(),nn.Linear(16,1))
    def augment(self,z):
        a=z[:,[0,4,5,6,7]]**5
        base=torch.cat([z[:,:8],a,(3*a[:,:1]-a[:,1:2]).clamp(-1,1),(5*a[:,:1]-a[:,2:3]).clamp(-1,1),a[:,:1]-z[:,2:3]**5,z[:,8:32]],1)
        return base if self.dimensions==40 else torch.cat([base,z[:,32:40]],1)
    def forward(self,z):return self.layers(self.augment(z))
    def gain(self,z):return torch.exp2(self(z).clamp(-3,.5849625))

def load_model(path,dimensions=None):
    ckpt=torch.load(path,map_location='cpu',weights_only=False)
    dim=dimensions or ckpt.get('dimensions',ckpt['state']['layers.0.weight'].shape[1])
    m=Model(dim);state=dict(ckpt['state'])
    if dim==48 and state['layers.0.weight'].shape[1]==40:
        old=state['layers.0.weight'];state['layers.0.weight']=torch.cat([old,torch.zeros((32,8),dtype=old.dtype)],1)
    m.load_state_dict(state);return m.eval()

@torch.no_grad()
def gain_float(net,f,extra):
    out=np.empty(f.shape[1],'f4')
    for start in range(0,len(out),32768):
        z=np.concatenate([f[:,start:start+32768],extra[:,start:start+32768]],0).T.astype('f4')/4096
        out[start:start+len(z)]=net.gain(torch.from_numpy(z)).numpy().ravel()
    return out.reshape(1024,512)

def integer_gain(net,f,extra):
    weights=[]
    for i in [0,2,4]:
        w=np.rint(net.layers[i].weight.detach().numpy().astype('f8')*65536).astype('i8')
        b=np.rint(net.layers[i].bias.detach().numpy().astype('f8')*2**32).astype('i8')
        if np.max(abs(w))>=2**19 or np.max(abs(b))>=2**33:raise OverflowError('Cannot fit existing20/34-bit coefficient containers')
        weights.append((w,b))
    lut=np.rint(np.exp2(np.clip(np.arange(-16384,16385)/1024,-3,.5849625))*16384).astype('u2')
    out=np.empty(f.shape[1],'u2')
    def fifth(x):
        v=x.copy()
        for _ in range(4):v=(v*x+32768)>>16
        return v
    for start in range(0,len(out),16384):
        z=f[:,start:start+16384].T.astype('i8')<<4;a=fifth(z[:,[0,4,5,6,7]])
        v=np.concatenate([z[:,:8],a,np.clip(3*a[:,:1]-a[:,1:2],-65536,65536),np.clip(5*a[:,:1]-a[:,2:3],-65536,65536),a[:,:1]-fifth(z[:,2:3]),z[:,8:]],1)
        if net.dimensions==48:v=np.concatenate([v,extra[:,start:start+16384].T.astype('i8')<<4],1)
        for i,(w,b) in enumerate(weights):
            # This checks observed accumulator outputs, not exhaustive intervals.
            acc=v@w.T+b
            if np.max(abs(acc))>=2**47:raise OverflowError('Observed48-bit accumulation overflow')
            v=(acc+32768)>>16
            if i<2:v=np.maximum(v,0)
        idx=np.clip(((v[:,0]+32)>>6)+16384,0,32768)
        out[start:start+len(v)]=lut[idx]
    return out.reshape(1024,512)
