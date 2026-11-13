"""Interpret the v2 512-chirp background failure without changing its gates."""
from pathlib import Path
import sys,json
import numpy as np
from scipy.ndimage import maximum_filter
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'scalar_restore_v2'
sys.dont_write_bytecode=True;sys.path.insert(0,str(OLD))
from common_v2 import apply_power,amplitudes

def main():
    report=json.loads((OLD/'independent_test_final/report.json').read_text(encoding='utf8'));rows=[]
    sums={name:dict(bg_error=0.,total_error=0.,bg_power=0.,reference_power=0.,bg_pixels=0,fp003=0,fp01=0,fp03=0) for name in ['bypass','v7','v2']}
    for row in report['rows']:
        if row['group']!='synthetic' or row['actual_chirps']!=512:continue
        with np.load(OLD/'independent_test_final/arrays'/(row['id']+'.npz')) as d:ref=d['reference'];base=d['base'];enh=d['enhanced'];og=d['original_gain']
        y,x=amplitudes(ref,base);v7=apply_power(base,og);bg=y<.003
        for t in row['targets']:
            r=round(t['range_bin']);a=round(t['doppler_bin']);bg[np.ix_(np.arange(r-3,r+4)%1024,np.arange(a-3,a+4)%512)]=False
        rr={}
        for name,p in [('bypass',base),('v7',v7),('v2',enh)]:
            z=np.sqrt(p.astype('f8')/max(float(base.max()),1));positive=np.maximum(z[bg]-y[bg],0)**2
            total=float(((z-y)**2).sum());peaks=(z==maximum_filter(z,3,mode='wrap'))&bg
            metrics=dict(bg_error=float(positive.sum()),total_error=total,bg_power=float((z[bg]**2).sum()),reference_power=float((y**2).sum()),bg_pixels=int(bg.sum()),fp003=int((peaks&(z>=.003)).sum()),fp01=int((peaks&(z>=.01)).sum()),fp03=int((peaks&(z>=.03)).sum()),bg_max_amplitude=float(z[bg].max()),bg_p999_amplitude=float(np.quantile(z[bg],.999)))
            for key in sums[name]:sums[name][key]+=metrics[key]
            rr[name]=metrics
        rows.append(dict(id=row['id'],metrics=rr))
    summary={}
    for name,s in sums.items():
        summary[name]=dict(**s,bg_error_rms=float(np.sqrt(s['bg_error']/s['bg_pixels'])),bg_error_rms_db=float(10*np.log10(max(s['bg_error']/s['bg_pixels'],1e-30))),
            bg_error_fraction_total=s['bg_error']/s['total_error'],nmse=s['total_error']/s['reference_power'],bg_error_relative_to_v7=s['bg_error']/sums['v7']['bg_error'])
    result=dict(status='DIAGNOSTIC_NOT_A_CHANGED_QUALITY_VERDICT',reference_background_definition='reference amplitude<0.003 with known-target neighborhoods excluded',
        reference_threshold_db=float(20*np.log10(.003)),summary=summary,background_extra_relative_to_total_v7_error=(sums['v2']['bg_error']-sums['v7']['bg_error'])/sums['v7']['total_error'],rows=rows)
    (ROOT/'background_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
