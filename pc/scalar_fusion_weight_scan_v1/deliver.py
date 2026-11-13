import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json,hashlib,ast,re,argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt,font_manager
import warnings
ROOT=Path(__file__).resolve().parent;SRC=ROOT.parent/'scalar_sign_evidence_v2'
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def write(p,x):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()
FONT='C:/Windows/Fonts/msyh.ttc'
font_manager.fontManager.addfont(FONT)
plt.rcParams.update({'font.family':font_manager.FontProperties(fname=FONT).get_name(),'axes.unicode_minus':False})
warnings.filterwarnings('error',message='Glyph .* missing.*')

def report():
    f=read(ROOT/'FROZEN.json');a=f['alpha'];scans={k:read(ROOT/'reports'/f'scan_{k}.json') for k in ['protected','linear']}
    test=read(ROOT/'reports/TEST_SUMMARY.json');diag=read(ROOT/'reports/OLD_TEST_DIAGNOSTIC.json')
    base=f['baseline'];folder=ROOT/'results';folder.mkdir(exist_ok=True)
    plots=[('mean_false40','每帧参考外峰',None),('new_half','相对旧网新增半幅失败',0),('max_drop','最大目标保留率下降',.05),('mae','目标相对幅值平均绝对误差',base['mae']+.005),('worst_harmonic_worsening_db','最差纯谐波区域相对旧网增幅（分贝）',1),('below_half','全部半幅以下目标',0)]
    fig,axs=plt.subplots(2,3,figsize=(16,9),constrained_layout=True)
    for ax,(key,label,threshold) in zip(axs.flat,plots):
        for mode,name in [('protected','原保护规则保持'),('linear','不带保护的纯融合对照')]:
            rs=scans[mode]['rows'];ax.plot([r['alpha'] for r in rs],[r['summary'][key] for r in rs],label=name)
        ax.axhline(base[key],color='gray',ls=':',label='纯旧网络')
        if threshold is not None:ax.axhline(threshold,color='red',ls='--',label='预声明阈值')
        ax.axvline(a,color='green',ls='--',label=f'选定比例α={a:g}')
        ax.set_title(label);ax.set_xlabel('残差恢复权重α');ax.grid(alpha=.2)
    axs.flat[0].legend(fontsize=8)
    fig.suptitle('六帧已看过验证数据：101个全局比例扫描\n两条支路冻结；比例选择不等于通过；保护端点不等于纯旧网络/纯恢复')
    fig.savefig(folder/'validation_scan.png',dpi=130);plt.close(fig)
    labels={'old40':'纯旧40维网络','model':'独立残差恢复','old_alpha075':'原保护融合（α=0.75）','selected_protected':f'选定保护融合（α={a:g}）','selected_linear':f'纯融合对照（α={a:g}）'}
    titles={'single':'单目标','spread':'分散多目标','near_pairs':'相邻多目标','strong_weak':'强弱混合','collision_minus3':'负三次谐波重合','collision_plus5':'正五次谐波重合','near_collision_plus5':'接近正五次谐波'}
    cards=[];data=[]
    for m in read(ROOT/'data/test_manifest.json')['records']:
        rp=ROOT/'reports/test'/(m['id']+'.json');r=read(rp);data.append(dict(role='冻结后新测试',metadata=m,report=str(rp),report_sha256=sha(rp),arrays=r['arrays'],arrays_sha256=r['arrays_sha256']))
        name=f"{m['target_count']}个目标｜{titles[m['family']]}｜{'整数频点' if m['grid']=='grid' else '非整数频点'}"
        with np.load(r['arrays']) as z:
            fig,axs=plt.subplots(2,3,figsize=(15,9),constrained_layout=True)
            for ax,key in zip(axs.flat,['reference','bypass','old40','model','old_alpha075','selected_protected']):
                v=z[key].reshape(256,4,256,2).max(axis=(1,3))
                im=ax.imshow(np.fft.fftshift(20*np.log10(np.maximum(v,1e-6)),axes=1),origin='lower',extent=(-256,256,0,1024),aspect='auto',vmin=-60,vmax=0,cmap='magma')
                ax.set_title({'reference':'多比特参考','bypass':'单比特旁路',**labels}[key]);ax.set_xlabel('多普勒频点');ax.set_ylabel('距离频点')
                for t in m['targets']:ax.plot((t['doppler_bin']+256)%512-256,t['range_bin'],'o',ms=5,mfc='none',mec='cyan')
            fig.colorbar(im,ax=list(axs.flat),label='相对幅值（分贝）',shrink=.7)
            fig.suptitle(name+'\n蓝圈仅用于评价；模型独立归一化，非绝对功率')
            fig.savefig(folder/(m['id']+'.png'),dpi=120);plt.close(fig)
        table='<table><tr><th>方法</th><th>参考外峰</th><th>半幅以下目标</th></tr>'+''.join(f'<tr><td>{labels[k]}</td><td>{v["false40"]}</td><td>{v["below_half"]}</td></tr>' for k,v in r['metrics'].items())+'</table>'
        cards.append(f'<section><h2>{name}</h2><p>来源编号：{m["id"]}；种子：{m["seed"]}</p>{table}<img src="{m["id"]}.png"><a href="../reports/test/{m["id"]}.json">逐目标指标与来源</a></section>')
    # The original 12 test frames remain diagnostics, never selection data.
    data=read(ROOT/'data/validation_register.json')['records']+[
        dict(role='旧测试/已看过诊断',metadata=r['metadata'],source_report=r['source_report'],source_report_sha256=r['source_report_sha256'],source_arrays=r['source_arrays'],source_arrays_sha256=r['source_arrays_sha256']) for r in diag['records']]+data
    write(ROOT/'DATA_REGISTER.json',dict(records=data,frozen_sha256=sha(ROOT/'FROZEN.json'),source_dependencies=f['sources'],training='无新训练'))
    index=['# 数据来源与用途','', '|用途|帧编号|种子|回波/符号/功率NPZ|报告|','|---|---|---:|---|---|']
    for r in data:
        m=r['metadata'];report=r.get('report',r.get('source_report'))
        index.append(f"|{r['role']}|{m['id']}|{m['seed']}|[输入]({Path(m['file']).as_posix()})|[报告]({Path(report).as_posix()})|")
    index+=['', '输入NPZ：adc_i/adc_q整数回波，sign_i/sign_q为±1（代表±64正负），reference/base为Xilinx位精确FFT uint64功率；结果NPZ为相对幅值谱。没有使用PNG训练。场景生成源码与SHA记录在FROZEN.json/data/test_manifest.json。验证只用6个独立帧，101个权重不是606个独立样本；新测试12帧。']
    (ROOT/'数据索引.md').write_text('\n'.join(index)+'\n',encoding='utf8')
    bp=read(ROOT/'reports/VALIDATION_BOUNDS.json')['records']
    borderline=min((r for r in bp if r['half_alpha_bound'] is not None),key=lambda r:r['half_alpha_bound'])
    relaxed=[r for r in scans['protected']['rows'] if r['summary']['max_drop']<=.05+1e-7 and r['summary']['mae']<=base['mae']+.005+1e-7]
    relaxed_best=min(relaxed,key=lambda r:r['summary']['mean_false40'])
    worst=None
    valids=scans['protected']['frame_ids']
    for i,mets in enumerate(scans['protected']['rows'][0]['frames']):
        oldreport=read(SRC/'reports/validation'/(valids[i]+'.json'));hs=oldreport['metrics']['old40']['harmonics']
        for j,db in enumerate(mets['harmonic_worsening_db']):
            if worst is None or db>worst['db']:worst=dict(frame=valids[i],target=hs[j]['target']+1,order=hs[j]['order'],db=db)
    write(ROOT/'reports/SENSITIVITY.json',dict(borderline=borderline,ignoring_half_threshold_but_keep_drop_mae=relaxed_best['summary'],alpha=relaxed_best['alpha'],protection_floor_worst=worst,
        note='事后解释阈值敏感性，不改变冻结alpha或质量规则'))
    doc=['# 全局融合比例扫描结果','',f"**未找到满足全部要求的全局比例。** 扫描α=0～1，步长0.01；原保护接口满足目标安全条件的网格点只有{f['safe_grid_count']}个，选出α={a:g}。它是{('仅保护端点，不是有恢复贡献的成功融合' if a==0 else '本验证集上的候选比例')}。",'',
         '本轮固定40维权重、残差求解器及保护条件，未重新训练、未访问板卡。另扫不带保护的纯融合，作为保护层消融；不事后替换主接口。', '',
         '## 六帧验证扫描','', '|恢复权重α|新增半幅失败|每帧参考外峰|最大目标保留率下降|最差谐波相对旧网增幅/dB|','|---|---:|---:|---:|---:|']
    for r in scans['protected']['rows']:
        if round(r['alpha']*100) not in [0,1,5,10,25,50,75,100]:continue
        m=r['summary'];doc.append(f"|{r['alpha']:.2f}|{m['new_half']}|{m['mean_false40']:.2f}|{m['max_drop']:.6f}|{m['worst_harmonic_worsening_db']:.2f}|")
    doc+=['',f"纯旧网参考外峰{base['mean_false40']:.2f}/帧，已有{base['below_half']}个目标不足参考半幅。α=0的受保护融合仍可能抬高伪峰，不能等同于纯旧网。纯融合对照的α=0才逐点等于旧网、α=1才等于独立恢复。",'',
        '## 不是只被一个阈值卡住','',
        f"确有一个半幅边缘样本：{borderline['frame']}目标{borderline['target']}，旧网保留率{borderline['old_retention']:.9f}，恢复{borderline['model_retention']:.9f}。它没有保护覆盖，保持≥0.5的连续α上界约{borderline['half_alpha_bound']:.8g}。因此0.01已越界；不能把这当成数学上任意正α都不可用，也不能说0.01造成灾难性下降。",
        f"即使事后暂不计半幅门槛，仅保留最大下降≤0.05和MAE约束，最好网格点为α={relaxed_best['alpha']:g}，参考外峰{relaxed_best['summary']['mean_false40']:.2f}/帧，仍未达到≤{.9*base['mean_false40']:.2f}的10%改善要求。该敏感性分析不重新选参。",
        f"此外，保护规则在α=0已把{worst['frame']}目标{worst['target']}的{worst['order']}阶纯谐波区域能量抬高{worst['db']:.2f}dB（相对旧网）；这个下限不能靠调α消掉。这里是按预声明掩膜认定的谐波区域，不是逐分量唯一归因。",'',
        '## 冻结后新场景测试','', '|方法|半幅以下目标|新增半幅失败|每帧参考外峰|目标MAE|','|---|---:|---:|---:|---:|']
    for k,m in test['summary'].items():doc.append(f"|{labels[k]}|{m['below_half']}/{m['targets']}|{m['new_half']}|{m['mean_false40']:.2f}|{m['mae']:.6f}|")
    doc+=['',f"新测试质量：{'通过' if test['quality']['pass_all'] else '未通过'}。具体判据：{json.dumps(test['quality']['gates'],ensure_ascii=False)}。新测试种子为20261112000～20261112011，冻结后生成，不用于重新挑比例。旧12帧同数据诊断另见reports/OLD_TEST_DIAGNOSTIC.json，未混入上表。",'',
        '## 结论与下一步','', '当前固定全局权重无法兼顾目标保留和足够去伪。降低α能减轻恢复支路带来的错误，却也失去大部分去背景收益；增加α则传递恢复遗漏及伪峰。保护层本身还存在误保留，单纯扫权重无法解决。', '',
        '后续应考虑按局部证据决定采用哪条支路及融合强度，并修正“保护支持”的可靠性；保留恢复求解的定位与误删问题。当前只完成扫描和独立测试，没有自动启动局部权重训练，也不能宣称新方法将必然通过。', '',
        '完整图：[中文图集](results/index.html)；方法与门槛：[实验说明](README.md)；数据：[来源索引](数据索引.md)。所有结果是无噪无杂波点频RD仿真，非实测SAR或PL性能。']
    (ROOT/'本轮结果.md').write_text('\n'.join(doc)+'\n',encoding='utf8')
    (folder/'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>全局融合比例扫描与新场景测试</title><style>body{font-family:Microsoft YaHei;max-width:1600px;margin:25px auto;background:#eef2f6}section{background:white;padding:20px;margin:20px 0}img{width:100%}table{border-collapse:collapse}td,th{padding:6px;border:1px solid #aaa}</style><h1>全局融合比例扫描：未找到整体合格比例</h1><p>保护接口仅α=0满足验证目标安全约束；这是仅保护端点。全部质量条件仍未通过。没有重新训练。</p><a href="../本轮结果.md">结论、阈值敏感性与数据来源</a><img src="validation_scan.png">'+''.join(cards)+'</html>',encoding='utf8')
    write(ROOT/'BUILD_STATUS.json',dict(status='PC_SCAN_COMPLETE',selected_alpha=a,quality_pass=test['quality']['pass_all'],validation_quality_pass=f['quality_pass'],deployment_ready=False,weights_retrained=False))
    print('中文结果与全部新测试图已生成。')

def check():
    f=read(ROOT/'FROZEN.json')
    for p,d in f['sources'].items():assert sha(p)==d,p
    oldf=read(SRC/'FROZEN.json')
    for name,d in oldf['sources'].items():assert sha(SRC/name)==d
    regs=read(ROOT/'DATA_REGISTER.json')['records'];assert len(regs)==30
    newseeds=[];oldseeds=[];components=0
    for r in regs:
        m=r['metadata'];assert sha(m['file'])==m['sha256']
        for pathkey in ['report','source_report','arrays','source_arrays']:
            if pathkey in r:assert sha(r[pathkey])==r[pathkey+'_sha256']
        if r['role']=='冻结后新测试':
            newseeds.append(m['seed']);row=read(r['report']);assert row['frozen_sha256']==sha(ROOT/'FROZEN.json')
            with np.load(m['file']) as z:
                for c in ['i','q']:
                    assert np.array_equal(z['sign_'+c],np.where(z['adc_'+c]>=0,1,-1));components+=z['sign_'+c].size
            with np.load(r['arrays']) as z:
                assert all(np.isfinite(z[k]).all() for k in z.files)
                expected=(1-f['alpha'])*z['old40']+f['alpha']*z['model']
                assert np.max(abs(z['selected_linear']-expected))<1e-7
                assert np.all(z['selected_protected']>=z['selected_linear'])
            sr=read(Path(row['solver_report']));assert len(set(sr['fit_indices']+sr['evidence_indices']))==8192
            assert len(sr['candidates'])<=24 and sr['proposal']['proposal_indices']==sr['fit_indices']
            assert sha(row['solver_report'])==row['solver_sha256']
            assert (ROOT/'results'/(m['id']+'.png')).exists()
        else:oldseeds.append(m['seed'])
    assert len(set(newseeds))==12 and not set(newseeds)&set(oldseeds)
    # Independent metric comparison to prior complete implementation on same observations.
    diag=read(ROOT/'reports/OLD_TEST_DIAGNOSTIC.json');errors=[]
    for r in diag['records']:
        prior=read(r['source_report'])
        for k,pk in [('old40','old40'),('model','residual24_model'),('old_alpha075','residual24_blend0.75')]:
            x,y=r['metrics'][k],prior['metrics'][pk]
            assert x['false40']==y['false40'] and x['below_half']==sum(t['retention']<.5 for t in y['targets'])
            err=max(abs(t-v['retention']) for t,v in zip(x['retention'],y['targets']));assert err<2e-6;errors.append(err)
    for mode in ['protected','linear']:
        s=read(ROOT/'reports'/f'scan_{mode}.json');assert len(s['rows'])==101 and s['sources']==f['sources']
        assert [round(r['alpha']*100) for r in s['rows']]==list(range(101))
    for p in ROOT.glob('*.py'):ast.parse(p.read_text(encoding='utf8'))
    for p in ROOT.rglob('*.json'):read(p)
    for p in ROOT.glob('*.md'):
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf8')):
            if not link.startswith('http'):assert (p.parent/link).exists(),link
    for link in re.findall(r'(?:src|href)="([^"]+)"',(ROOT/'results/index.html').read_text(encoding='utf8')):assert (ROOT/'results'/link).exists()
    visual=read(ROOT/'reports/VISUAL_CHECK.json');assert visual['status']=='PASS'
    write(ROOT/'reports/STANDARD_CHECK.json',dict(status='PASS',scope='冻结代码/模型、数据来源、数值规则和同数据指标复现，不代表质量通过',
        referenced_old_frames=18,new_test_frames=12,alpha_count_per_interface=101,exact_sign_components=components,
        old_metric_max_retention_error=max(errors),new_seeds_disjoint=True,quality_pass=read(ROOT/'reports/TEST_SUMMARY.json')['quality']['pass_all'],visual_check=visual))
    write(ROOT/'FILE_MANIFEST.json',dict(files=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='FILE_MANIFEST.json']))
    print('标准检查通过；质量未通过；原模型与求解器保持冻结。')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['report','check']);args=p.parse_args();dict(report=report,check=check)[args.stage]()
