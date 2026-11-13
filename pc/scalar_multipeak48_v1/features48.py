"""Input-only, Q12 additional features. No target labels or reference arrays."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import numpy as np
from scipy.ndimage import maximum_filter,convolve

def round_even(num,den):
    num=np.asarray(num,dtype='i8');den=np.asarray(den,dtype='i8')
    q,r=np.divmod(abs(num),den)
    return np.sign(num)*(q+((2*r>den)|((2*r==den)&((q&1)!=0))))

def fifth(z):
    x=z.astype('i8')<<4;v=x.copy()
    for _ in range(4):v=(v*x+32768)>>16
    return v

def tables(f):
    z=f[0].reshape(1024,512).astype('i8')
    s=maximum_filter(z,3,mode='wrap')
    mean=(convolve(z,np.ones((31,1),dtype='i8'),mode='wrap')+15)//31;den=np.maximum(mean,128)
    ratio=np.minimum(4096,(np.maximum(20*z-24*den,0)*4096+(5*den)//2)//(5*den))
    gated=maximum_filter((z*ratio+2048)>>12,3,mode='wrap')
    return z,s,gated

def parent(s,r,a,h):
    top=np.full(r.shape,-1,'i8');second=top.copy();br=np.zeros_like(r);ba=np.zeros_like(a)
    n=abs(h)
    for kr in range(n):
        rr=round_even((r if h>0 else -r)+kr*1024,n)%1024
        for ka in range(n):
            aa=round_even((a if h>0 else -a)+ka*512,n)%512;v=s[rr,aa]
            better=v>top;second=np.where(better,top,np.maximum(second,v));top=np.maximum(top,v)
            br=np.where(better,rr,br);ba=np.where(better,aa,ba)
    return br,ba,top,np.maximum(second,0)

def refine(z,r,a):
    val=np.full(r.shape,-1,'i8');rr=r.copy();aa=a.copy()
    for dr in range(-1,2):
        for da in range(-1,2):
            r1=(r+dr)%1024;a1=(a+da)%512;v=z[r1,a1];better=v>val
            rr=np.where(better,r1,rr);aa=np.where(better,a1,aa);val=np.maximum(val,v)
    rm=fifth(z[(rr-1)%1024,aa]);rp=fifth(z[(rr+1)%1024,aa])
    am=fifth(z[rr,(aa-1)%512]);ap=fifth(z[rr,(aa+1)%512])
    dr=np.where(rm+rp>=64,np.clip(round_even(16*(rp-rm),np.maximum(rp+rm,1)),-8,8),0)
    da=np.where(am+ap>=64,np.clip(round_even(16*(ap-am),np.maximum(ap+am,1)),-8,8),0)
    return rr,aa,16*rr+dr,16*aa+da

def dist(r,a,rr,aa):
    return np.maximum(abs((r-rr+512)%1024-512),abs((a-aa+256)%512-256))

def extract(f,indices=None,return_geometry=False):
    z,s,gated=tables(f)
    ids=np.arange(1024*512) if indices is None else np.asarray(indices,dtype='i8')
    r=ids//512;a=ids%512
    r3,a3,t3,s3=parent(s,r,a,-3);r5,a5,t5,s5=parent(s,r,a,5)
    assert np.array_equal(t3,f[4,ids]) and np.array_equal(t5,f[5,ids])
    b=refine(z,r,a);p3=refine(z,r3,a3);p5=refine(z,r5,a5)
    def probe(p,h,exclude):
        rr=round_even(h*p[2],16)%1024;aa=round_even(h*p[3],16)%512
        valid=np.ones(rr.shape,bool)
        for e in exclude:valid&=dist(rr,aa,e[0],e[1])>4
        out=np.zeros(rr.shape,'i8')
        for dr in range(-1,2):
            for da in range(-1,2):out=np.maximum(out,gated[(rr+dr)%1024,(aa+da)%512])
        return np.where(valid,out,0),rr,aa
    c3=probe(p3,5,[p3,b]);c5=probe(p5,-3,[p5,b])
    l3=probe(p3,-7,[p3,b]);u3=probe(p3,9,[p3,b]);l5=probe(p5,-7,[p5,b]);u5=probe(p5,9,[p5,b])
    # B hypotheses exclude candidate parents as well as B itself; the candidates
    # are cues, not true labels. Zero parent support disables that exclusion.
    lb=probe(b,-7,[b]);ub=probe(b,9,[b])
    for child in [lb,ub]:
        child[0][((t3>0)&(dist(child[1],child[2],p3[0],p3[1])<=4))|((t5>0)&(dist(child[1],child[2],p5[0],p5[1])<=4))]=0
    h3=np.where(dist(l3[1],l3[2],u3[1],u3[2])>4,np.minimum(l3[0],u3[0]),0)
    h5=np.where(dist(l5[1],l5[2],u5[1],u5[2])>4,np.minimum(l5[0],u5[0]),0)
    same=dist(lb[1],lb[2],ub[1],ub[2])<=4
    extra=np.stack([t3-s3,t5-s5,np.where(t3>0,c3[0],0),np.where(t5>0,c5[0],0),
                    np.where(t3>0,h3,0),np.where(t5>0,h5,0),np.where(same,0,lb[0]),np.where(same,0,ub[0])]).astype('u2')
    assert extra.max()<=4096
    if return_geometry:return extra,dict(parent3=p3,parent5=p5,center=b)
    return extra

def scalar_features(f,index,precomputed=None):
    """Independent scalar address traversal and rounding, for audit only."""
    z,s,g=precomputed if precomputed is not None else tables(f)
    r,a=divmod(int(index),512)
    def rnd(n,d):
        sign=-1 if n<0 else 1;q,v=divmod(abs(int(n)),int(d))
        return sign*(q+int(2*v>d or (2*v==d and q%2)))
    def pwr(v):
        x=int(v)*16;y=x
        for _ in range(4):y=(y*x+32768)//65536
        return y
    def ref(q):
        rr,aa=q;best=-1;pos=None
        for dr in [-1,0,1]:
            for da in [-1,0,1]:
                ij=((rr+dr)%1024,(aa+da)%512);v=int(z[ij])
                if v>best:best=v;pos=ij
        rr,aa=pos;rm=pwr(z[(rr-1)%1024,aa]);rp=pwr(z[(rr+1)%1024,aa]);am=pwr(z[rr,(aa-1)%512]);ap=pwr(z[rr,(aa+1)%512])
        dr=max(-8,min(8,rnd(16*(rp-rm),rp+rm))) if rp+rm>=64 else 0
        da=max(-8,min(8,rnd(16*(ap-am),ap+am))) if ap+am>=64 else 0
        return(rr,aa,rr*16+dr,aa*16+da)
    def par(h):
        q=[]
        for kr in range(abs(h)):
            for ka in range(abs(h)):
                rr=rnd((r if h>0 else -r)+kr*1024,abs(h))%1024;aa=rnd((a if h>0 else -a)+ka*512,abs(h))%512
                q.append((int(s[rr,aa]),rr,aa))
        ordered=sorted(enumerate(q),key=lambda it:(-it[1][0],it[0]));top=ordered[0][1]
        return ref(top[1:]),top[0],ordered[1][1][0]
    def d(p,q):return max(abs((p[0]-q[0]+512)%1024-512),abs((p[1]-q[1]+256)%512-256))
    def probe(p,h,ex):
        rr=rnd(h*p[2],16)%1024;aa=rnd(h*p[3],16)%512
        v=max(int(g[(rr+dr)%1024,(aa+da)%512]) for dr in [-1,0,1] for da in [-1,0,1])
        if any(d((rr,aa),q)<=4 for q in ex):v=0
        return[v,rr,aa]
    p3,t3,s3=par(-3);p5,t5,s5=par(5);b=ref((r,a))
    c3=probe(p3,5,[p3,b]);c5=probe(p5,-3,[p5,b]);l3=probe(p3,-7,[p3,b]);u3=probe(p3,9,[p3,b]);l5=probe(p5,-7,[p5,b]);u5=probe(p5,9,[p5,b])
    ex=[b]+([p3] if t3 else [])+([p5] if t5 else [])
    lb=probe(b,-7,ex);ub=probe(b,9,ex)
    h3=min(l3[0],u3[0]) if d(l3[1:],u3[1:])>4 else 0
    h5=min(l5[0],u5[0]) if d(l5[1:],u5[1:])>4 else 0
    if d(lb[1:],ub[1:])<=4:lb[0]=ub[0]=0
    return np.asarray([t3-s3,t5-s5,c3[0] if t3 else 0,c5[0] if t5 else 0,h3 if t3 else 0,h5 if t5 else 0,lb[0],ub[0]],'u2')
