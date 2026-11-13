"""Post-hoc diagnostic, not a replacement selection or primary acceptance test."""
import sys
sys.dont_write_bytecode=True
from run import *
from deliver import NAMES,SCENES,table,htable

def main():
    # This control was added after seeing primary results. Tune only on validation.
    vr=read(ROOT/'data/VALIDATION_REGISTER.json')['records'];zs=[load_record(r,False) for r in vr]
    scan=[]
    for threshold in np.arange(0,.50001,.05):
        ms=[measure(z,z['model']*np.where(z['model']<threshold,1/64,1).astype('f4')) for z in zs]
        scan.append(dict(threshold=float(threshold),summary=aggregate(ms)))
    key=lambda r:(r['summary']['main_half_fail'],r['summary']['mean_false40'],r['summary']['worst_false'],r['summary']['mean_excess'],r['summary']['target_mae'],r['threshold'])
    chosen=min(scan,key=key);threshold=chosen['threshold']
    write(ROOT/'reports/THRESHOLD_VALIDATION_SELECTION.json',dict(posthoc=True,description='最终主结果后追加的简单幅值阈值诊断；只用验证选阈值，不改主候选或预声明判据',scan=scan,chosen=chosen))
    rows=[read(p) for p in sorted((ROOT/'reports/test').glob('*.json'))];ms=[];false=[];targetloss=[]
    for row in rows:
        z=load_record(row['record'],False);m=row['record']['metadata'];out=z['model']*np.where(z['model']<threshold,1/64,1).astype('f4');ms.append(measure(z,out))
        with np.load(row['arrays']) as d:a={k:d[k] for k in d.files}
        mask=(~v2.REF.occupied(m))&RANGE_MASK&(a['suppress_raw']>2*z['y'])&(a['suppress_raw']-z['y']>.0001)
        if mask.any():
            p=int(np.argmax(np.where(mask,a['suppress_raw'],-1)));r,d=divmod(p,512)
            close=[]
            def dist(rr,dd):return max(abs((rr-r+512)%1024-512),abs((dd-d+256)%512-256))
            for ti,t in enumerate(m['targets']):
                for h in [-3,5,-7,9,-11,13,-15,17,-19,21,-23,25,-27,29]:
                    close.append(dict(type='pure_harmonic',target=ti,order=h,error_bins=dist(h*t['range_bin'],h*t['doppler_bin'])))
                for tj,u in enumerate(m['targets']):
                    if ti!=tj:close.append(dict(type='intermod_2a_minus_b',a=ti,b=tj,error_bins=dist(2*t['range_bin']-u['range_bin'],2*t['doppler_bin']-u['doppler_bin'])))
            false.append(dict(frame=row['record']['id'],range_bin=r,doppler_bin=d if d<256 else d-512,range_m=r*BIN_M,values={k:float(v[r,d]) for k,v in a.items()},nearest_geometry=min(close,key=lambda c:c['error_bins']),geometry_not_causality=True))
        for ti,t in enumerate(row['metrics']['suppress_raw']['targets']):
            if t['within40'] and t['retention']<.5:
                prev=row['metrics']['model']['targets'][ti];targetloss.append(dict(frame=row['record']['id'],target=ti,range_m=t['range_m'],reference=t['reference'],reconstruction=prev['prediction'],prediction=t['prediction'],new_loss=prev['retention']>=.5,main=t['main']))
    false.sort(key=lambda v:-v['values']['suppress_raw']);s=aggregate(ms)
    write(ROOT/'reports/POSTHOC_DIAGNOSIS.json',dict(threshold_control=s,chosen=chosen,threshold_test_frames=ms,strongest_false_by_frame=false,target_losses=targetloss))
    baseline=read(ROOT/'reports/TEST_SUMMARY.json')['summary'];comp=[]
    for k,ss in [('model',baseline['model']),('threshold',s),('suppress_raw',baseline['suppress_raw'])]:
        comp.append([NAMES.get(k,'验证选参的简单幅值阈值'),f"{ss['mean_false40']:.2f}",f"{ss['worst_false']:.4f}",f"{ss['mean_excess']:.5f}",f"{ss['main_half_fail']}/{ss['main_targets']}",f"{ss['weak_half_fail']}/{ss['weak_targets']}"])
    heads=['方法','参考外峰/帧','最强参考外幅值','超额能量','主要目标不足半幅','弱目标不足半幅']
    false_rows=[]
    for v in false:
        g=v['nearest_geometry'];hyp=(f"目标{g['target']+1}的{g['order']}次谐波" if g['type']=='pure_harmonic' else f"2×目标{g['a']+1}−目标{g['b']+1}互调")
        if g['error_bins']>2:hyp='所查谐波/互调没有2格内匹配'
        else:hyp+='（仅位置接近）'
        false_rows.append([v['frame'],f"{v['range_m']:.2f}",v['doppler_bin'],f"{v['values']['reference']:.5g}",f"{v['values']['model']:.4f}",f"{v['values']['old40']:.4f}",f"{v['values']['suppress_raw']:.4f}",hyp])
    text=f'''# 剩余强伪峰与简单阈值对照

这是主结果完成后的补充诊断，不是预声明主试验，未改动权重或主判据。用于判断去伪是不是仅仅等价于把所有弱分量截掉。

简单基线：恢复谱幅值低于阈值时乘1/64，否则原样通过。阈值在0、0.05、…、0.5中仅由12帧验证集选择，选模排序沿用主要目标保护、残峰数、最强伪峰、超额能量、目标误差。选中阈值{threshold:.2f}。最终测试不调阈值。

{table(heads,comp)}
简单阈值只是一个基线，不是所有阈值/CFAR/稀疏方法的最优代表。网络如有优势，仅在这组对照上成立；新增损失和结构还不能因此宣称原创或充分泛化。

## 每帧最强剩余参考外分量

{table(['帧','距离/米','多普勒格','参考幅值','恢复幅值','原单比特旧网幅值','新网络幅值','几何线索'],false_rows)}
这里按主候选的最大背景像素定位，再比较各方法同一个位置。纯谐波查询−3、5、…、29阶，互调查询2fᵢ−fⱼ，频率均环绕处理；位置接近不证明因果。最强仍有{false[0]['values']['suppress_raw']:.4f}，不能说伪影全部剔除。

## 被压低的弱目标

{table(['帧','目标','距离/米','参考幅值','独立恢复','新网络','新增半幅失败'],[[x['frame'],x['target']+1,f"{x['range_m']:.2f}",f"{x['reference']:.4f}",f"{x['reconstruction']:.4f}",f"{x['prediction']:.4f}",'是' if x['new_loss'] else '前端已不足半幅'] for x in targetloss])}
这些是已知真实仿真目标，不能将其称作成功去除的伪影。完整结果在POSTHOC_DIAGNOSIS.json；图像原始数据仍不做额外阈值后处理。
'''
    (ROOT/'剩余错误与阈值对照.md').write_text(text,encoding='utf-8')
    p=ROOT/'results/index.html';page=p.read_text(encoding='utf-8');marker='<section id="threshold-control">'
    if marker not in page:
        page=page.replace('</html>',marker+'<h2>补充：与简单幅值阈值比较</h2><p>此项为主结果后的诊断，仅用验证集选阈值，不改主候选。<a href="../剩余错误与阈值对照.md">剩余强错误与逐目标损失</a></p>'+htable(heads,comp)+'</section></html>');p.write_text(page,encoding='utf-8')
    p=ROOT/'本轮结果.md';doc=p.read_text(encoding='utf-8')
    if '剩余错误与阈值对照.md' not in doc:p.write_text(doc+'\n\n补充：[剩余强错误、逐目标损失及简单幅值阈值对照](剩余错误与阈值对照.md)。该补充为主结果后的诊断，阈值只按验证集选取，不修改本轮主候选与判据。\n',encoding='utf-8')
    print(json.dumps(dict(threshold=threshold,summary=s,strongest=false[:2]),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
