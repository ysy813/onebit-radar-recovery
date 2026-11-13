"""Self-contained NumPy/SciPy integer scalar restorer; no PyTorch at inference.

Input: natural-order 1024x512 uint64 FFT power. Output: same power units.
Amplitude gain is Q14, applied as g squared. This is a PC numeric reference,
not an FPGA bitstream or a physical SAR focusing algorithm.
"""
from pathlib import Path
import argparse,hashlib,json,math
import numpy as np
from scipy.ndimage import convolve,maximum_filter
from scalar_guard import apply_guard

class PowerRestorer:
    def __init__(self,folder=None):
        folder=Path(folder) if folder else Path(__file__).resolve().parent
        self.config=json.loads((folder/'config.json').read_text(encoding='utf8'))
        for name in ['weights.npz','root5.npy','weights_128.npz']:
            if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=self.config['sha256'][name]:
                raise ValueError('Runtime file hash mismatch: '+name)
        with np.load(folder/'weights.npz',allow_pickle=False) as d:
            self.layers=[(d[f'w{i}'].astype('i8'),d[f'b{i}'].astype('i8')) for i in range(3)]
            self.lut=d['gain_lut']
        with np.load(folder/'weights_128.npz',allow_pickle=False) as d:
            self.layers_128=[(d[f'w{i}'].astype('i8'),d[f'b{i}'].astype('i8')) for i in range(3)]
            if not np.array_equal(self.lut,d['gain_lut']):raise ValueError('Profile gain LUT mismatch')
        self.root5=np.load(folder/'root5.npy',allow_pickle=False).astype('i8')
        self.context=self.config['context'];self.policy=self.config['feature_policy']

    def features(self,power):
        p=np.asarray(power)
        if p.shape!=(1024,512) or p.dtype!=np.dtype('u8'):
            raise ValueError('Expected uint64 power, shape (1024,512), natural FFT order')
        root=np.fromiter((math.isqrt(int(v)<<16) for v in p.flat),'u8',count=p.size).reshape(p.shape)
        peak=int(root.max())
        n=((root*65535+peak//2)//max(peak,1)).astype('u2');z=self.root5[n]
        support=maximum_filter(z,3,mode='wrap');r=np.arange(1024);a=np.arange(512)
        fields=[z,support,(convolve(z,np.ones((3,3),dtype='i8'),mode='wrap')+4)//9,
                (convolve(z,np.ones((9,9),dtype='i8'),mode='wrap')+40)//81]
        # Constant alias-root address tables; these are cues, not target labels.
        for h in [-3,5]:
            parent=np.zeros_like(z);order=abs(h)
            for kr in range(order):
                ri=np.rint(r/h+kr*1024/order).astype('i8')%1024
                for ka in range(order):
                    ai=np.rint(a/h+ka*512/order).astype('i8')%512
                    np.maximum(parent,support[np.ix_(ri,ai)],out=parent)
            fields.append(parent)
        if self.policy=='directional':
            fields.extend([(convolve(z,np.ones((9,1),dtype='i8'),mode='wrap')+4)//9,
                           (convolve(z,np.ones((1,9),dtype='i8'),mode='wrap')+4)//9])
        else:
            mean=(convolve(z,np.ones((31,1),dtype='i8'),mode='wrap')+15)//31;den=np.maximum(mean,128)
            if self.policy=='guarded_child':
                ratio=np.minimum(4096,(np.maximum(20*z-24*den,0)*4096+(5*den)//2)//(5*den))
                score=(z*ratio+2048)>>12
            elif self.policy=='contrast_child':
                score=np.minimum(4096,(np.maximum(z-mean,0)*8192+den//2)//den)
            else:raise ValueError(self.policy)
            gated=maximum_filter(score,3,mode='wrap')
            fields.extend([gated[np.ix_((h*r)%1024,(h*a)%512)] for h in [-3,5]])
        if self.context:
            fields.extend(np.roll(np.roll(z,-dr,axis=0),-da,axis=1) for dr in range(-self.context,self.context+1) for da in range(-self.context,self.context+1) if (dr,da)!=(0,0))
        return np.stack(fields).astype('u2').reshape(len(fields),-1)

    def predict_gain_q14(self,features_q12,actual_chirps=512):
        if actual_chirps not in [128,512]:raise ValueError('Expected128 or512 valid chirps')
        layers=self.layers_128 if actual_chirps==128 else self.layers
        f=np.asarray(features_q12)
        expected=8+(2*self.context+1)**2-1
        if f.shape!=(expected,1024*512) or np.any(f>4096):raise ValueError('Invalid Q12 feature array')
        def rs(x,n):return (x+(1<<(n-1)))>>n
        def pow5(x):
            y=x.copy()
            for _ in range(4):y=rs(y*x,16)
            return y
        gain=np.empty(f.shape[1],dtype='u2')
        for start in range(0,len(gain),32768):
            stop=min(start+32768,len(gain));z=f[:,start:stop].T.astype('i8')<<4
            v=pow5(z[:,[0,4,5,6,7]])
            z=np.concatenate([z[:,:8],v,np.clip(3*v[:,:1]-v[:,1:2],-65536,65536),np.clip(5*v[:,:1]-v[:,2:3],-65536,65536),v[:,:1]-pow5(z[:,2:3]),z[:,8:]],axis=1)
            for i,(w,b) in enumerate(layers):
                z=rs(z@w.T+b,16)
                if i<2:z=np.maximum(z,0)
            gain[start:stop]=self.lut[np.clip(rs(z[:,0],6)+16384,0,32768)]
        if self.config.get('peak_anchor',False):gain[f[0]>=4096]=16384
        return gain.reshape(1024,512)

    @staticmethod
    def apply_power(power,gain):
        cap=(1<<64)-1
        return np.fromiter((min(cap,(int(p)*int(g)**2+(1<<27))>>28) for p,g in zip(power.flat,gain.flat)),'u8',count=power.size).reshape(power.shape)

    def restore(self,power,return_gain=False,actual_chirps=512):
        if actual_chirps not in [128,512]:raise ValueError('Expected128 or512 valid chirps')
        p=np.asarray(power)
        if p.shape!=(1024,512) or p.dtype!=np.dtype('u8'):raise ValueError('Expected uint64 power (1024,512)')
        if not p.any():g=np.full(p.shape,16384,dtype='u2');out=p.copy()
        else:
            f=self.features(p);g=apply_guard(p,self.predict_gain_q14(f,actual_chirps),self.config.get('power_guard'),f,actual_chirps);out=self.apply_power(p,g)
        return (out,g) if return_gain else out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--actual-chirps',type=int,choices=[128,512],default=512);a=ap.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    e,g=PowerRestorer().restore(np.load(a.input,allow_pickle=False),True,a.actual_chirps)
    np.savez_compressed(a.output,power=e,gain_q14=g);print('PC_INTEGER_REFERENCE_COMPLETE')

if __name__=='__main__':main()
