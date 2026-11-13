"""Prespecified four-frame Q16 smoke and post-freeze failure diagnosis."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from experiment import np,torch,read,write,sha,load,ENGINE,extract,load_model,gain_float,integer_gain,guarded_gain,amplitudes,REF

def main():
    meta=read(ROOT/'data/test_manifest.json')['records'];test=read(ROOT/'reports/TEST.json');net=load_model(ROOT/'candidate/f48_repair/model_float.pt');rows=[]
    for ix in [0,6,17,18]:
        row=meta[ix];ref,base=load(row);y,x=amplitudes(ref,base);f=ENGINE.features(base);extra=extract(f)
        fp=guarded_gain(base,gain_float(net,f,extra),f)
        try:
            q=integer_gain(net,f,extra);ip=guarded_gain(base,q.astype('f4')/16384,f)
            a=REF.metrics(row,y,x,x*fp);b=REF.metrics(row,y,x,x*ip)
            rows.append(dict(id=row['id'],status='CHECKED',max_gain_error=float(abs(fp-ip).max()),mean_gain_error=float(abs(fp-ip).mean()),
                max_relative_amplitude_error=float(abs(x*(fp-ip)).max()),new_half_vs_float=sum(t['retention']>=.5 and u['retention']<.5 for t,u in zip(a['targets'],b['targets'])),float_metrics=a,integer_metrics=b))
        except OverflowError as e:rows.append(dict(id=row['id'],status='FAIL_WIDTH',error=str(e)))
        print('Q16冒烟',row['id'],rows[-1]['status'],flush=True)
    write(ROOT/'reports/INTEGER_SMOKE.json',dict(rows=rows,all_fit_width=all(r['status']=='CHECKED' for r in rows),
        no_new_half_vs_float=all(r.get('new_half_vs_float',1)==0 for r in rows),scope='4个预先指定帧；实际观察累加值检查，不是任意输入位宽证明、完整整帧RTL或IP验证',model_sha256=sha(ROOT/'candidate/f48_repair/model_float.pt')))
    failures=[];regressions=[]
    for row,m in zip(test['rows'],meta):
        ts=row['metrics']['f48_repair_guard']['targets'];bad=[t for t in ts if t['retention']<.5]
        if bad:
            _,base=load(m);f=ENGINE.features(base);ids=np.asarray([t['peak_index'] for t in bad]);extra=extract(f,ids)
            with torch.no_grad():scores=net(torch.from_numpy(np.concatenate([f[:,ids],extra],0).T.astype('f4')/4096)).numpy().ravel()
            for t,s in zip(bad,scores):failures.append(dict(frame=row['id'],family=row['family'],**t,raw_score=float(s),below_clamp=bool(s<-3),extra_q12=extra[:,list(ids).index(t['peak_index'])].tolist()))
        for basekey in ['initial_guard','f40_repair_guard']:
            for ti,(a,b) in enumerate(zip(row['metrics'][basekey]['targets'],ts)):
                if a['retention']>=.5 and b['retention']<.5:regressions.append(dict(frame=row['id'],target=ti+1,comparison=basekey,before_retention=a['retention'],after_retention=b['retention']))
    write(ROOT/'reports/FAILURES.json',dict(failures=failures,individual_regressions=regressions,post_freeze=True,not_used_for_reselection=True))
    print('逐目标诊断完成',len(failures),'个半幅失败',flush=True)

if __name__=='__main__':main()
