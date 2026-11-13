"""Input-derived compact-peak skip; not a target classifier or reference mask.

Applied AFTER the frozen v2 guard. Only the 512-valid-chirp profile is changed.
No literal range/Doppler coordinates, training labels or reference enter it.
"""
import numpy as np
from scalar_guard import local_max

def compact_peak_skip(power,gain_q14,features,actual_chirps=512,return_info=False):
    if actual_chirps not in [128,512]:raise ValueError('Expected128 or512 valid chirps')
    g=gain_q14.copy();peak=int(power.max())
    if actual_chirps==128 or not peak:return (g,dict(changed_pixels=0)) if return_info else g
    if features.shape[1]!=power.size:raise ValueError('Feature/frame shape mismatch')
    z=features[[0,4,5]].astype('i8')<<4;a=z.copy()
    for _ in range(4):a=(a*z+32768)>>16
    explained=np.zeros(power.size,dtype=bool)
    for j,h in [(1,3),(2,5)]:explained|=(a[j]>=16384)&(2*np.abs(h*a[0]-a[j])<=a[j])
    # Shared Q12 features: mean9 is the mean of the fifth-root amplitude
    # representation, NOT raw power or a calibrated SNR estimate.
    center=features[0].astype('i8');mean=np.maximum(features[3].astype('i8'),128)
    compact=np.minimum(4096,(np.maximum(5*center-7*mean,0)*4096+mean//2)//mean).reshape(power.shape)
    mask=(power>=(peak+9999)//10000)&(power<=peak//16)&(power==local_max(power,9))&(~explained.reshape(power.shape))
    v=g.astype('f8') if g.dtype.kind=='f' else g.astype('i8')
    # Continuous confidence over FINAL v2 gain0.25..0.5. It is a regressor
    # decision, not a calibrated probability; don't use a brittle binary gate.
    confidence=np.clip(v-4096,0,4096)
    weight=(compact*confidence+2048)//4096
    lift=(np.maximum(16384-v,0)*weight+2048)//4096
    g[mask]=(v+lift)[mask]
    info=dict(changed_pixels=int(np.count_nonzero(g!=gain_q14)),eligible_pixels=int(mask.sum()),max_gain_increase=float(np.max(g.astype('f8')-gain_q14)/16384))
    return (g,info) if return_info else g
