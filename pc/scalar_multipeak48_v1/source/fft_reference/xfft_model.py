"""Use installed Xilinx bit-accurate FFT model; no floating FFT substitution."""
import ctypes as c
import os
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
_dll_dir=os.add_dll_directory(str(HERE/'xfft_cmodel'))
dll=c.CDLL(str(HERE/'xfft_cmodel/libIp_xfft_v9_1_bitacc_cmodel.dll'))
class Generics(c.Structure):
    _fields_=[(n,c.c_int) for n in ['nfft','arch','has_nfft','float','width','twiddle','scale','bfp','round']]
class Inputs(c.Structure):
    _fields_=[('nfft',c.c_int),('re',c.POINTER(c.c_double)),('nr',c.c_int),('im',c.POINTER(c.c_double)),('ni',c.c_int),('sch',c.POINTER(c.c_int)),('ns',c.c_int),('direction',c.c_int)]
class Outputs(c.Structure):
    _fields_=[('re',c.POINTER(c.c_double)),('nr',c.c_int),('im',c.POINTER(c.c_double)),('ni',c.c_int),('exp',c.c_int),('overflow',c.c_int)]
create=dll.xilinx_ip_xfft_v9_1_create_state;create.argtypes=[Generics];create.restype=c.c_void_p
destroy=dll.xilinx_ip_xfft_v9_1_destroy_state;destroy.argtypes=[c.c_void_p]
simulate=dll.xilinx_ip_xfft_v9_1_bitacc_simulate;simulate.argtypes=[c.c_void_p,Inputs,c.POINTER(Outputs)];simulate.restype=c.c_int
def ptr(a):return a.ctypes.data_as(c.POINTER(c.c_double))
class FFT:
    def __init__(self,nfft,width):
        self.nfft=nfft;self.n=1<<nfft;self.width=width
        self.state=create(Generics(nfft,1,0,0,width,16,0,0,1))
        if not self.state:raise RuntimeError('Xilinx FFT state creation failed')
    def run(self,x):
        re=np.ascontiguousarray(np.real(x)/2**(self.width-1),dtype='f8')
        im=np.ascontiguousarray(np.imag(x)/2**(self.width-1),dtype='f8')
        rr=np.empty(self.n);ii=np.empty(self.n)
        inp=Inputs(self.nfft,ptr(re),self.n,ptr(im),self.n,None,0,1)
        out=Outputs(ptr(rr),self.n,ptr(ii),self.n,0,0)
        if simulate(self.state,inp,c.byref(out)):raise RuntimeError('Xilinx FFT model failed')
        # Unscaled outputs keep the binary point of the input.
        return np.rint(rr*2**(self.width-1))+1j*np.rint(ii*2**(self.width-1))
    def __del__(self):
        if getattr(self,'state',None):destroy(self.state)
def fft2(x):
    assert x.shape==(1024,512)
    a=FFT(10,16);b=FFT(9,27)
    first=np.stack([a.run(x[:,i]) for i in range(512)],axis=1)
    second=np.stack([b.run(first[i]) for i in range(1024)])
    return second
