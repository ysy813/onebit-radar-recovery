"""Small scalar corrector with input-derived harmonic cues and bounded gain."""
import torch
from torch import nn

def features_for_policy(f,policy,context=0):
    import numpy as np
    from scipy.ndimage import convolve,maximum_filter
    z=f[0].reshape(1024,512).astype('i8')
    if policy=='directional':out=f.copy()
    elif policy in ['contrast_child','guarded_child']:
        mean=(convolve(z,np.ones((31,1),dtype='i8'),mode='wrap')+15)//31
        den=np.maximum(mean,128)
        if policy=='contrast_child':score=np.minimum(4096,(np.maximum(z-mean,0)*8192+den//2)//den)
        else:
            # Preserve compact source peaks at their original strength, while
            # rejecting the smooth pedestal. Soft contrast transition is
            # relative z/mean from1.2 to1.45, never fixed Doppler coordinates.
            ratio=np.minimum(4096,(np.maximum(20*z-24*den,0)*4096+(5*den)//2)//(5*den))
            score=(z*ratio+2048)>>12
        support=maximum_filter(score,3,mode='wrap');out=f.copy();r=np.arange(1024);a=np.arange(512)
        out[6]=support[np.ix_((-3*r)%1024,(-3*a)%512)].ravel()
        out[7]=support[np.ix_((5*r)%1024,(5*a)%512)].ravel()
    else:raise ValueError(policy)
    if context:
        neighbors=[np.roll(np.roll(z,-dr,axis=0),-da,axis=1).ravel() for dr in range(-context,context+1) for da in range(-context,context+1) if (dr,da)!=(0,0)]
        out=np.concatenate([out,np.stack(neighbors).astype('u2')])
    return out

class ScalarCorrector(nn.Module):
    def __init__(self,boost=True,context=0,width=32,peak_anchor=False):
        super().__init__();self.boost=boost;self.context=context;self.peak_anchor=peak_anchor;extra=(2*context+1)**2-1
        self.layers=nn.Sequential(nn.Linear(16+extra,width),nn.ReLU(),nn.Linear(width,width//2),nn.ReLU(),nn.Linear(width//2,1))
    def augment(self,z):
        a=z[:,[0,4,5,6,7]]**5
        return torch.cat([z[:,:8],a,(3*a[:,:1]-a[:,1:2]).clamp(-1,1),(5*a[:,:1]-a[:,2:3]).clamp(-1,1),a[:,:1]-z[:,2:3]**5,z[:,8:]],1)
    def forward(self,z):
        raw=self.layers(self.augment(z))
        return torch.where(z[:,:1]>=1,torch.zeros_like(raw),raw) if self.peak_anchor else raw
    def gain(self,z):return torch.exp2(self(z).clamp(-3,.5849625 if self.boost else 0))

class IntegerCorrector:
    def __init__(self,net):
        import numpy as np
        self.layers=[];self.peak_anchor=net.peak_anchor
        for i in [0,2,4]:
            w=np.rint(net.layers[i].weight.detach().numpy().astype('f8')*65536).astype('i8')
            b=np.rint(net.layers[i].bias.detach().numpy().astype('f8')*(1<<32)).astype('i8')
            self.layers.append((w,b))
        x=np.arange(-16384,16385)/1024
        self.lut=np.rint(np.exp2(np.clip(x,-3,.5849625 if net.boost else 0))*16384).astype('u2')
    def predict(self,f):
        import numpy as np
        def rs(a,n):return (a+(1<<(n-1)))>>n
        def p5(x):
            y=x.copy()
            for _ in range(4):y=rs(y*x,16)
            return y
        out=np.empty(f.shape[1],dtype='u2')
        for start in range(0,len(out),32768):
            stop=min(start+32768,len(out));z=f[:,start:stop].T.astype('i8')<<4
            a=p5(z[:,[0,4,5,6,7]])
            z=np.concatenate([z[:,:8],a,np.clip(3*a[:,:1]-a[:,1:2],-65536,65536),np.clip(5*a[:,:1]-a[:,2:3],-65536,65536),a[:,:1]-p5(z[:,2:3]),z[:,8:]],1)
            for i,(w,b) in enumerate(self.layers):
                z=rs(z@w.T+b,16)
                if i<2:z=np.maximum(z,0)
            out[start:stop]=self.lut[np.clip(rs(z[:,0],6)+16384,0,32768)]
        if self.peak_anchor:out[f[0]>=4096]=16384
        return out.reshape(1024,512)
