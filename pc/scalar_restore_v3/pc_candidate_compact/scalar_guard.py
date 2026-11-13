"""Conservative output safeguard derived only from the input power frame.

This deliberately preserves some spurious peaks too. It is not a second source
of target truth. All quality gates must include the safeguarded output.
"""
import numpy as np

def local_max(power,size):
    """Separable periodic maximum, exact even for values above 2**53."""
    out=power
    for axis in [0,1]:
        source=out;out=source.copy()
        for offset in range(-(size//2),size//2+1):
            if offset:np.maximum(out,np.roll(source,offset,axis=axis),out=out)
    return out

def apply_guard(power,gain_q14,config,features=None,actual_chirps=512):
    if not config:return gain_q14
    version=config.get('version')
    if version not in ['weak_peak_v1','weak_peak_harmonic_v2','weak_peak_soft_v3']:raise ValueError('Unknown scalar guard')
    if actual_chirps not in [128,512]:raise ValueError('Expected 128 or 512 valid chirps before zero padding')
    peak=int(power.max());g=gain_q14.copy()
    if not peak:return g
    mx9=local_max(power,9);mx3=local_max(power,3)
    # The uint64 comparisons avoid overflow and contain no floating arithmetic.
    # Weak <=-12.04dB, detected >=-40dB. The near-peak tolerance is 3.01dB.
    near=(power>=(peak+9999)//10000)&(power>=mx3//2+mx3%2)
    mask=(power>0)&(power<=peak//16)&((power==mx9)|near)
    if version in ['weak_peak_harmonic_v2','weak_peak_soft_v3'] and actual_chirps==512:
        if features is None:raise ValueError('Harmonic guard requires matching Q12 features')
        z=features[[0,4,5]].astype('i8')<<4;a=z.copy()
        for _ in range(4):a=(a*z+32768)>>16
        explained=np.zeros(power.size,dtype=bool)
        for j,h in [(1,3),(2,5)]:explained|=(a[j]>=16384)&(2*np.abs(h*a[0]-a[j])<=a[j])
        # Do not force unity gain at a peak already consistent with a strong
        # third/fifth harmonic. The learned regressor still decides its gain;
        # this rule never directly zeros or subtracts an inferred target.
        mask&=~explained.reshape(power.shape)
    if version=='weak_peak_soft_v3' and actual_chirps==512:
        # Regressor gain is an attenuation decision, not a calibrated class
        # probability. Use a continuous skip connection rather than a hard
        # confidence threshold, so fixed-point rounding cannot flip g to1.
        lo,hi=config['soft_band_q14'];width=hi-lo
        v=g.astype('f8') if g.dtype.kind=='f' else g.astype('i8')
        lift=(np.maximum(16384-v,0)*np.clip(v-lo,0,width)+width//2)//width
        g[mask]=(v+lift)[mask]
    else:g[mask]=np.maximum(g[mask],16384)
    g[power==peak]=16384
    return g
