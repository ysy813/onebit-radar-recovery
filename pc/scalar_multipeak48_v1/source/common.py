"""Independent, synthetic-only paired RD experiment. No board access."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import hashlib, json, math
import numpy as np
import torch
from scipy.ndimage import maximum_filter, uniform_filter

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'baseline'))
sys.path.insert(0, str(ROOT / 'fft_reference'))
from restore_power import PowerRestorer
from scalar_guard import apply_guard
from compact_guard import compact_peak_skip
from model_source import ScalarCorrector
from xfft_model import fft2

SHAPE = (1024, 512)
ORDERS = (-3, 5, -7, 9, -11, 13)
GROUPS = ('single_grid', 'single_offgrid', 'multi_grid', 'multi_offgrid')
ENGINE = PowerRestorer(ROOT / 'baseline')
torch.set_num_threads(2)

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(2**20), b''): h.update(b)
    return h.hexdigest()

def write(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf8')

def read(path): return json.loads(Path(path).read_text(encoding='utf8'))
def protocol(): return read(ROOT / 'EXPERIMENT_PROTOCOL.json')

def network(path):
    net = ScalarCorrector(True, 2, 32, False)
    net.load_state_dict(torch.load(path, map_location='cpu', weights_only=False)['state'])
    return net.eval()

def amplitudes(ref, base):
    y = np.sqrt(ref.astype('f8')); x = np.sqrt(base.astype('f8'))
    return (y / max(y.max(), 1)).astype('f4'), (x / max(x.max(), 1)).astype('f4')

def roi(r, a, radius=2):
    rr = np.arange(round(r)-radius, round(r)+radius+1) % SHAPE[0]
    aa = np.arange(round(a)-radius, round(a)+radius+1) % SHAPE[1]
    return (rr[:, None] * SHAPE[1] + aa).ravel()

def distances(x, y, n): return abs((x-y+n/2) % n - n/2)

def scene(seed, group, index, challenge=None):
    """Azimuth is geometry metadata, NOT the Doppler coordinate."""
    rng = np.random.default_rng(seed)
    family = protocol()['scene_families'][index % 4]
    multi = group.startswith('multi') or challenge is not None
    count = (2 + index % 2) if multi else 1
    if challenge is not None: count = 2
    off = group.endswith('offgrid')
    targets = []
    for j in range(count):
        r, d = float(rng.integers(40, 481)), float(rng.integers(-220, 221))
        if off:
            r += rng.uniform(-.49, .49); d += rng.uniform(-.49, .49)
        if j and family == 'shared_range': r = targets[0]['range_bin']
        if j and family == 'shared_velocity': d = targets[0]['doppler_bin']
        if j and min(max(distances(r,t['range_bin'],1024), distances(d,t['doppler_bin'],512)) for t in targets) < 8:
            r = (r + 25) % 440 + 40
        amplitude = 1.0 if j == 0 else float(rng.uniform(.12, .35) if family == 'strong_weak' else rng.uniform(.3, .9))
        if j and challenge:
            first = targets[0]
            if challenge.startswith('true_target_at_'):
                h = -3 if challenge.endswith('minus3') else 5
                r = (h * first['range_bin']) % 1024
                d = ((h * first['doppler_bin'] + 256) % 512) - 256
                amplitude = .25
            elif challenge == 'close_pair': r, d, amplitude = first['range_bin'] + 3.2, first['doppler_bin'] + 2.3, .4
            elif challenge == 'weak_pair': amplitude = .08
        theta = float(rng.uniform(-60, 60))
        delta = float(rng.uniform(-65, 65))
        scale = protocol()['radar_scale']; c = scale['c_m_s']
        vr = d * c / (2 * scale['carrier_hz'] * scale['chirp_interval_s'] * 512)
        # Signed speed along a chosen direction, including approaching targets.
        signed_speed = vr / math.cos(math.radians(delta))
        targets.append(dict(range_bin=r, doppler_bin=d, amplitude=amplitude,
            initial_phase_rad=float(rng.uniform(-math.pi, math.pi)), azimuth_deg=theta,
            velocity_direction_deg=theta+delta, signed_speed_m_s=signed_speed,
            radial_velocity_m_s=vr,
            range_m=r*c*scale['sample_rate_hz']/(2*scale['slope_hz_s']*1024)))
    return dict(seed=seed, group=group, family=family if multi else 'single', targets=targets,
                challenge=challenge, actual_chirps=512, shape=list(SHAPE), noise=False, clutter=False)

def echo(meta):
    n = np.arange(1024)[:,None]; m = np.arange(512)[None,:]
    s = np.zeros(SHAPE, 'c16')
    for t in meta['targets']:
        s += t['amplitude'] * np.exp(2j*np.pi*(t['range_bin']*n/1024+t['doppler_bin']*m/512)+1j*t['initial_phase_rad'])
    # Bound coherent full-frame integer power below signed64 for any phase.
    scale = 4000 / max(abs(s.real).max(), abs(s.imag).max())
    return np.rint(s.real*scale)+1j*np.rint(s.imag*scale)

def power(x):
    z = fft2(x)
    # Check before square/add, then exact integer power in uint64.
    if np.hypot(z.real,z.imag).max() >= math.sqrt(2**63-1): raise OverflowError('Power bound violated')
    re = z.real.astype('i8'); im = z.imag.astype('i8')
    return (re*re+im*im).astype('u8')

def generate_pair(meta):
    adc = echo(meta)
    signed = np.where(adc.real >= 0, 64, -64)+1j*np.where(adc.imag >= 0, 64, -64)
    return power(adc), power(signed)

def load_pair(row):
    with np.load(ROOT / row['file'], allow_pickle=False) as d: return d['reference'], d['base']

def masks(meta, y, x):
    known = np.zeros(SHAPE, bool); centers = known.copy(); harmonics = known.copy()
    for t in meta['targets']:
        ids = roi(t['range_bin'], t['doppler_bin'])
        known.flat[ids] = True
        centers.flat[ids[np.argmax(y.ravel()[ids])]] = True
        for h in ORDERS: harmonics.flat[roi(h*t['range_bin'],h*t['doppler_bin'])] = True
    maxima = y == maximum_filter(y,3,mode='wrap')
    support = maximum_filter((maxima & (y>.03)).astype('u1'), 3, mode='wrap').astype(bool) | known
    excess = (x>1.5*y+.0002) & ~support
    low = (y<.003) & ~support
    return dict(known=known, centers=centers, support=support, excess=excess, low=low, harmonics=harmonics & ~known)

@torch.no_grad()
def gain_float(net, f):
    out = np.empty(f.shape[1], 'f4')
    for start in range(0,len(out),32768):
        z = torch.from_numpy(f[:,start:start+32768].T.astype('f4')/4096)
        out[start:start+len(z)] = net.gain(z).numpy().ravel()
    return out.reshape(SHAPE)

def guarded_gain(base, gain, f):
    g = np.rint(gain*16384).astype('u2')
    g = apply_guard(base, g, ENGINE.config['power_guard'], f, 512)
    return compact_peak_skip(base, g, f, 512).astype('f4')/16384

def frame_metrics(meta, y, x, pred):
    err0 = float(np.square(x-y).sum()); err = float(np.square(pred-y).sum())
    targets = []; occupied = np.zeros(SHAPE,bool)
    for t in meta['targets']: occupied.flat[roi(t['range_bin'],t['doppler_bin'],4)] = True
    for t in meta['targets']:
        ids = roi(t['range_bin'],t['doppler_bin']); idx = ids[np.argmax(y.ravel()[ids])]
        yy,xx,pp = (float(v.ravel()[idx]) for v in (y,x,pred))
        targets.append(dict(range_bin=t['range_bin'],doppler_bin=t['doppler_bin'],peak_index=int(idx),
            reference=yy,bypass=xx,prediction=pp,absolute_error=abs(pp-yy),bypass_error=abs(xx-yy),
            extra_error=abs(pp-yy)-abs(xx-yy),new_half_loss=bool(xx>=.5*yy and pp<.5*yy)))
    harmonic_rows = []
    for tid,t in enumerate(meta['targets']):
        for h in ORDERS:
            ids=roi(h*t['range_bin'],h*t['doppler_bin'])
            en0=float(np.square(x.ravel()[ids]).sum()); en=float(np.square(pred.ravel()[ids]).sum()); ref=float(np.square(y.ravel()[ids]).sum())
            overlap=bool(occupied.ravel()[ids].any())
            pure=(not overlap) and en0>1e-8 and ref<=.0025*en0
            harmonic_rows.append(dict(target=tid,order=h,pure_roi=pure,target_overlap=overlap,
                reference_to_bypass_energy=ref/max(en0,1e-30), attenuation_db=float(10*np.log10(max(en0,1e-30)/max(en,1e-30)))))
    return dict(nmse=err/max(float(np.square(y).sum()),1e-30), nmse_ratio=err/max(err0,1e-30),
                targets=targets,harmonics=harmonic_rows)

def summarize(rows, method):
    groups={}; all_targets=[]; failures=[]
    for group in GROUPS:
        selected=[r[method] for r in rows if r['group']==group and not r.get('challenge')]
        if not selected:continue
        targets=[t for r in selected for t in r['targets']]; all_targets+=targets
        harmonics=[h for r in selected for h in r['harmonics'] if h['pure_roi']]
        hs={str(h):[v['attenuation_db'] for v in harmonics if v['order']==h] for h in ORDERS}
        primary=hs['-3']+hs['5']
        groups[group]=dict(frames=len(selected),mean_nmse_ratio=float(np.mean([r['nmse_ratio'] for r in selected])),
            new_half_losses=sum(t['new_half_loss'] for t in targets),mean_target_extra_error=float(np.mean([t['extra_error'] for t in targets])),
            max_target_extra_error=max(t['extra_error'] for t in targets),
            harmonics={h:dict(count=len(v),median_db=float(np.median(v)),min_db=min(v)) for h,v in hs.items() if v})
        g=groups[group]
        if g['mean_nmse_ratio']>1: failures.append(group+':NMSE')
        if g['new_half_losses']: failures.append(group+':new_half_loss')
        if g['mean_target_extra_error']>.02: failures.append(group+':mean_target_error')
        if g['max_target_extra_error']>.1: failures.append(group+':max_target_error')
        if group=='single_grid' and (not primary or min(primary)<10):failures.append(group+':harmonic_10dB')
        if group=='single_offgrid' and (not primary or np.median(primary)<6):failures.append(group+':harmonic_6dB')
    return dict(groups=groups,failed_gates=failures,failed_gate_count=len(failures),
                mean_nmse_ratio=float(np.mean([g['mean_nmse_ratio'] for g in groups.values()])),
                primary_status='PASS' if not failures else 'FAIL')
