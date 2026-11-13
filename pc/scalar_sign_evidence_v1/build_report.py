import sys
sys.dont_write_bytecode=True
from pathlib import Path
ROOT=Path(__file__).resolve().parent
import json,hashlib,html,time
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt,font_manager
import warnings
font_manager.fontManager.addfont('C:/Windows/Fonts/msyh.ttc')
plt.rcParams.update({'font.family':font_manager.FontProperties(fname='C:/Windows/Fonts/msyh.ttc').get_name(),'axes.unicode_minus':False})
warnings.filterwarnings('error',message='Glyph .* missing.*')

def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def write(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()

LABELS={'bypass':'单比特旁路','old40':'旧40维网络','model':'符号模型单独重建','gated':'旧网络＋符号门控'}
FAMILIES={'single':'单目标','spread':'分散多目标','near_pairs':'相邻多目标','strong_weak':'强弱混合',
          'collision_minus3':'真实目标与负三次谐波重合','collision_plus5':'真实目标与正五次谐波重合','near_collision_plus5':'接近正五次谐波'}

def sign_diagnosis(row):
    meta=row['metadata'];targets=meta['targets'];n=np.arange(1024)[:,None]/1024;m=np.arange(512)[None,:]/512
    atoms=[t['amplitude']*np.exp(2j*np.pi*(t['range_bin']*n+t['doppler_bin']*m)+1j*t['initial_phase_rad']) for t in targets]
    full=sum(atoms);scale=4000/max(abs(full.real).max(),abs(full.imag).max())
    with np.load(meta['file']) as d:si=d['sign_i'];sq=d['sign_q']
    assert np.array_equal(np.where(np.rint(full.real*scale)>=0,1,-1),si)
    assert np.array_equal(np.where(np.rint(full.imag*scale)>=0,1,-1),sq)
    result=[]
    for j,atom in enumerate(atoms):
        other=full-atom;ei=np.where(np.rint(other.real*scale)>=0,1,-1)!=si;eq=np.where(np.rint(other.imag*scale)>=0,1,-1)!=sq
        detail={}
        for split in ['fit','evidence']:
            ids=np.asarray(row['solver'][split+'_indices']);detail[split+'_symbol_changes']=int(ei.ravel()[ids].sum()+eq.ravel()[ids].sum())
        result.append(dict(target=j,full_symbol_changes=int(ei.sum()+eq.sum()),full_symbol_fraction=float((ei.sum()+eq.sum())/(2*si.size)),**detail))
    return result

def main():
    summary=read(ROOT/'reports/TEST_SUMMARY.json');cfg=read(ROOT/'PROTOCOL.json');frozen=read(ROOT/'FROZEN.json')
    manifest=read(ROOT/'data/test_manifest.json');rows=[read(ROOT/'reports/test'/(r['id']+'.json')) for r in manifest['records']]
    folder=ROOT/'results';cards=[];audits=[];harmonics={};failures=[];stats=[]
    for row in rows:
        meta=row['metadata'];id=meta['id'];diag=sign_diagnosis(row);audits.append(dict(id=id,targets=diag))
        title=f"{meta['target_count']}个目标｜{FAMILIES[meta['family']]}｜{'整数频点' if meta['grid']=='grid' else '非整数频点'}"
        with np.load(row['arrays']) as d:
            fig,axs=plt.subplots(2,3,figsize=(16,9),constrained_layout=True)
            for ax,key,lab in zip(axs.ravel(),['reference','bypass','old40','model','gated'],['多比特参考']+list(LABELS.values())):
                z=d[key].reshape(256,4,256,2).max(axis=(1,3));im=ax.imshow(np.fft.fftshift(20*np.log10(np.maximum(z,1e-6)),axes=1),origin='lower',aspect='auto',extent=(-256,256,0,1024),cmap='magma',vmin=-60,vmax=0)
                ax.set_title(lab);ax.set_xlabel('多普勒频点');ax.set_ylabel('距离频点')
                for t in meta['targets']:ax.plot((t['doppler_bin']+256)%512-256,t['range_bin'],'o',ms=6,mfc='none',mec='cyan',mew=.7)
            ax=axs.ravel()[-1]
            for key,lab in LABELS.items():ax.plot(np.arange(1,meta['target_count']+1),[t['retention'] for t in row['metrics'][key]['targets']],'o-',label=lab,ms=4)
            ax.axhline(.5,color='red',ls='--');ax.set_title('同位置输出幅值／多比特参考');ax.set_xlabel('目标编号');ax.legend(fontsize=8);ax.grid(alpha=.2)
            fig.colorbar(im,ax=axs.ravel()[:5].tolist(),shrink=.65,label='相对幅值（分贝）；统一色阶')
            fig.suptitle(title+'\n蓝圈仅用于真值标注；不提供给推理。单独重建更干净不等于目标保留。')
            fig.savefig(folder/(id+'.png'),dpi=120);plt.close(fig)
        mt='<table><tr><th>方法</th><th>参考外峰数</th><th>半幅以下目标</th></tr>'+''.join(f'<tr><td>{lab}</td><td>{row["metrics"][k]["false40"]}</td><td>{sum(t["retention"]<.5 for t in row["metrics"][k]["targets"])}/{meta["target_count"]}</td></tr>' for k,lab in LABELS.items())+'</table>'
        cards.append(f'<section><h2>{title}</h2><p>来源编号：{id}；种子：{meta["seed"]}；符号模型保留源数：{len(row["solver"]["selected_sources"])}；耗时：{row["solver"]["seconds"]:.2f}秒</p>{mt}<img src="{id}.png"><p><a href="../reports/test/{id}.json">逐候选、逐目标和抽样索引</a></p></section>')
        for j,t in enumerate(row['metrics']['gated']['targets']):
            old=row['metrics']['old40']['targets'][j];model=row['metrics']['model']['targets'][j]
            if t['retention']<.5 or model['retention']<.5 or t['retention']<old['retention']-.05:
                failures.append(dict(id=id,target=j+1,old_retention=old['retention'],gated_retention=t['retention'],model_retention=model['retention'],candidate=row['candidate_recall'][j],sign_changes=diag[j]))
        g=row['gates']['gated'];stats.append(dict(id=id,supported=g['supported'],redundant=g['redundant'],uncertain=g['uncertain']))
    for key in LABELS:
        harmonics[key]={}
        for h in cfg['harmonic_orders'] if 'harmonic_orders' in cfg else [-3,5,-7,9,-11,13,-15,17,-19,21,-23,25,-27,29]:
            vals=[v['attenuation_db'] for r in rows for v in r['metrics'][key]['harmonics'] if v['order']==h]
            singles=[v['attenuation_db'] for r in rows if r['metadata']['family']=='single' for v in r['metrics'][key]['harmonics'] if v['order']==h]
            if vals:harmonics[key][str(h)]=dict(count=len(vals),minimum_db=min(vals),median_db=float(np.median(vals)),single_minimum_db=min(singles) if singles else None)
    write(ROOT/'reports/DIAGNOSIS.json',dict(evaluation_only=True,used_for_inference=False,sign_leave_one_out=audits,failures_and_regressions=failures,harmonics=harmonics,gate_decisions=stats))
    table='|方法|半幅以下目标|相对旧网新增／恢复|每帧参考外峰|目标平均绝对误差|\n|---|---:|---:|---:|---:|\n'
    for k,lab in LABELS.items():
        s=summary['summary'][k];table+=f"|{lab}|{s['below_half']}/{s['targets']}|{s['new_half_vs_old40']}／{s['recovered_half_vs_old40']}|{s['mean_false40']:.2f}|{s['mean_target_error']:.6f}|\n"
    old=summary['summary']['old40'];g=summary['summary']['gated'];model=summary['summary']['model']
    doc='# 有限符号证据：本轮验证结果\n\n'
    doc+=f"结论：预声明整体质量门槛**{'通过' if summary['quality_pass'] else '未通过'}**。本轮完成方法原型和新测试对照，没有训练新MLP、没有可替换的部署权重或BIT。\n\n"
    doc+=table+'\n'
    doc+=f"最终测试12帧，{g['targets']}目标；候选覆盖{summary['candidates']['recalled']}/{summary['candidates']['targets']}。门控相对旧网的参考外峰变化为{(g['mean_false40']/max(old['mean_false40'],1e-12)-1)*100:+.2f}%；单独模型变化为{(model['mean_false40']/max(old['mean_false40'],1e-12)-1)*100:+.2f}%。不能只看更干净的重建谱忽略弱目标损失。\n\n"
    doc+=f"PC符号支路平均{summary['solver']['mean_seconds']:.2f}秒/帧，最慢{summary['solver']['max_seconds']:.2f}秒。包含候选FFT、拟合、稀疏删减、双解释比较与模型谱重建；不含旧网和Xilinx FFT生成。不是PL预测速度。最初全候选优化正常收敛{summary['solver']['converged']}/12帧，其他存在迭代预算耗尽，报告保留此限制。\n\n"
    doc+='## 数据与复现\n\n2帧开发、6帧验证、12帧冻结后测试，全部无窗、无噪合成点目标。开发两帧只修正实现/方法并保留初始尝试；验证选择门槛；最终测试不用于修改。没有本轮权重训练集。详见[数据索引](数据索引.md)与DATA_REGISTER.json，生成参数/源代码SHA/原始I/Q/符号/功率/推理结果均可追溯。\n\n'
    doc+=f"门槛由验证集选择为{frozen['gate']}；六组门控验证均不能满足全部目标半幅要求，仍按预声明顺序冻结一组进行测试，不称验证质量通过。\n\n"
    doc+='## 改了什么及为何改\n\n详见[方法与改动说明](方法与改动说明.md)。初始纯logistic证据保留了用于增大符号分类间隔的谐波；开发阶段加入只用拟合样本的稀疏删减，并同时检验未拟合符号上的错误改善。新支路使用输入符号，未用多比特参考推理。\n\n'
    doc+='## 预声明判据\n\n|判据|结果|\n|---|---|\n'
    names={'no_new_target_half_vs_old':'相对旧网无新增逐目标半幅失败','all_targets_at_least_half':'所有目标至少保留参考半幅','artifact':'参考外峰至少减少10%','target_mae':'目标平均误差增加不超过0.005'}
    for k,v in summary['gates'].items():doc+=f"|{names[k]}|{'通过' if v else '未通过'}|\n"
    doc+='\n这些是研究判据，不是CFAR标准或部署验收。低于半幅目标的数量相同也不能称无退步；下表同时列出已失败目标进一步被压低及单独模型丢失的情形。\n\n'
    doc+='|测试帧／目标编号|旧网保留率|门控保留率|单独模型保留率|完整帧去掉此目标后改变的I/Q符号数|\n|---|---:|---:|---:|---:|\n'
    for f in failures:doc+=f"|{f['id']}／{f['target']}|{f['old_retention']:.4f}|{f['gated_retention']:.4f}|{f['model_retention']:.4f}|{f['sign_changes']['full_symbol_changes']}|\n"
    doc+='\n去目标符号差只用于事后诊断：保持完整帧的ADC缩放，删除该真值回波后重新取整取符号。它没有提供给求解器。差异为零是本次有限观测不可区分的证据；差异非零却恢复失败则不能甩锅为信息完全丢失，须查候选、优化和判据。\n\n'
    doc+='逐阶抑制及最差值在reports/DIAGNOSIS.json；所有十二帧均展示，入口[中文图集](results/index.html)。颜色是相对幅值，单独模型有独立尺度归一化，不能作为绝对功率改善结论。\n'
    (ROOT/'本轮验证结果.md').write_text(doc,encoding='utf8')
    summaryhtml='<table><tr><th>方法</th><th>半幅失败</th><th>每帧参考外峰</th></tr>'+''.join(f'<tr><td>{lab}</td><td>{summary["summary"][k]["below_half"]}/{g["targets"]}</td><td>{summary["summary"][k]["mean_false40"]:.2f}</td></tr>' for k,lab in LABELS.items())+'</table>'
    (folder/'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>有限符号证据与旧网络同帧对照</title><style>body{font-family:Microsoft YaHei;max-width:1600px;margin:24px auto;background:#eef2f6}section{background:white;margin:20px 0;padding:20px}img{width:100%}table{border-collapse:collapse}td,th{border:1px solid #999;padding:6px}.warn{color:#a12626;font-weight:bold}</style><h1>有限符号证据与旧网络同帧对照</h1><p class="warn">研究原型；'+('整体质量门槛通过，尚非部署验证' if summary['quality_pass'] else '整体质量门槛未通过，不能替换已部署网络')+'</p><p>12帧新种子、无窗、无噪仿真。参数在测试前冻结。全帧计算指标，预览为4×2最大值池化。单独符号重建和网络门控是两条不同分支。</p>'+summaryhtml+''.join(cards)+'</html>',encoding='utf8')
    register=[];index=['# 数据与代码来源','', '没有本轮神经权重训练。开发集用于检查与修正，验证集选门槛，最终测试冻结后生成。帧内4096拟合/4096证据复符号是同帧不同位置，不是8192帧。','', '|用途|帧编号|种子|目标数|原始数据|结果/报告|','|---|---|---:|---:|---|---|']
    for split in ['development','validation','test']:
        for meta in read(ROOT/'data'/f'{split}_manifest.json')['records']:
            rp=ROOT/'reports'/split/(meta['id']+'.json');row=read(rp)
            register.append(dict(split=split,metadata=meta,report=str(rp),report_sha256=sha(rp),output=row['arrays'],output_sha256=row['arrays_sha256'],fit_and_evidence_indices='逐帧报告solver.fit_indices/evidence_indices'))
            index.append(f"|{dict(development='开发',validation='验证',test='最终测试')[split]}|{meta['id']}|{meta['seed']}|{meta['target_count']}|[NPZ](data/{split}/{meta['id']}.npz)|[报告](reports/{split}/{meta['id']}.json)|")
    index+=['','数据NPZ内容：adc_i/adc_q是整数原始回波；sign_i/sign_q是±1符号；reference/base是Xilinx位精确FFT uint64功率。results下NPZ是归一化幅值谱。没有把渲染图片作为训练数据。','', '生成入口run_experiment.py dataset()，调用旧仿真生成器，源路径和SHA位于各data/*_manifest.json。算法入口sign_solver.py；独立输入CLI为infer.py。完整来源登记见DATA_REGISTER.json。']
    (ROOT/'数据索引.md').write_text('\n'.join(index)+'\n',encoding='utf8')
    write(ROOT/'DATA_REGISTER.json',dict(records=register,protocol_sha256=sha(ROOT/'PROTOCOL.json'),frozen_sha256=sha(ROOT/'FROZEN.json'),baseline=dict(path=str(ROOT.parent/cfg['baseline']),sha256=frozen['model_sha256']),no_training=True))
    write(ROOT/'BUILD_STATUS.json',dict(status='PC_RESEARCH_COMPLETE',quality_pass=summary['quality_pass'],deployment_ready=False,trained_new_weights=False,board_access=False))
    print('中文报告与十二帧图集完成',summary['gates'],flush=True)

if __name__=='__main__':main()
