"""Post-training diagnostic on training data only; does not change features."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from experiment import np,read,write,load,ENGINE,extract,roi,round_even,dist

def main():
    rows=[]
    for meta in read(ROOT/'data/train_manifest.json')['records']:
        ref,base=load(meta);f=ENGINE.features(base)
        ids=np.array([int((pos:=roi(t['range_bin'],t['doppler_bin']))[np.argmax(ref.ravel()[pos])]) for t in meta['targets']])
        _,geometry=extract(f,ids,True)
        for ti,(t,k) in enumerate(zip(meta['targets'],ids)):
            rr,aa,r16,a16=[int(v[ti]) for v in geometry['center']]
            for h in [-7,9]:
                actual=(round(h*t['range_bin'])%1024,round(h*t['doppler_bin'])%512)
                original=(h*(k//512)%1024,h*(k%512)%512)
                local=(h*rr%1024,h*aa%512)
                refined=(int(round_even(h*r16,16))%1024,int(round_even(h*a16,16))%512)
                rows.append(dict(id=meta['id'],target=ti+1,grid=meta['grid'],family=meta['family'],order=h,
                    original_error=int(dist(*original,*actual)),local_peak_error=int(dist(*local,*actual)),refined_error=int(dist(*refined,*actual)),
                    local_peak_moved=bool((rr,aa)!=(k//512,k%512)),fractional_offset=[(r16-16*rr)/16,(a16-16*aa)/16]))
    groups={}
    for key in sorted({r['grid']+'/'+r['family'] for r in rows}):
        rs=[r for r in rows if r['grid']+'/'+r['family']==key]
        groups[key]=dict(count=len(rs),original_covered=sum(r['original_error']<=2 for r in rs),local_peak_covered=sum(r['local_peak_error']<=2 for r in rs),refined_covered=sum(r['refined_error']<=2 for r in rs),local_peak_moved=sum(r['local_peak_moved'] for r in rs),covered_to_missed_by_fraction=sum(r['local_peak_error']<=2 and r['refined_error']>2 for r in rs))
    write(ROOT/'reports/GEOMETRY_DIAGNOSIS.json',dict(training_only=True,network_unchanged=True,groups=groups,rows=rows,scope='目标B的−7/+9几何覆盖，不是父候选识别准确率或因果消融'))
    print('训练集几何诊断',groups,flush=True)

if __name__=='__main__':main()
