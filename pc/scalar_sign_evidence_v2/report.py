import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json,hashlib,warnings,html
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt,font_manager
ROOT=Path(__file__).resolve().parent
font_manager.fontManager.addfont('C:/Windows/Fonts/msyh.ttc')
plt.rcParams.update({'font.family':font_manager.FontProperties(fname='C:/Windows/Fonts/msyh.ttc').get_name(),'axes.unicode_minus':False})
warnings.filterwarnings('error',message='Glyph .* missing.*')
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()
def write(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
FAMILY={'single':'单目标','spread':'分散多目标','near_pairs':'相邻多目标','strong_weak':'强弱混合','collision_minus3':'负三次谐波重合','collision_plus5':'正五次谐波重合','near_collision_plus5':'接近正五次谐波'}

def main():
    summary=read(ROOT/'reports/TEST_SUMMARY.json');frozen=read(ROOT/'FROZEN.json');alpha=frozen['alpha'];primary=summary['primary']
    labels={'bypass':'单比特旁路','old40':'旧40维网络','v1_model':'上一轮独立恢复','v1_gate':'上一轮网络门控','fft24_model':'同预算FFT候选恢复','residual24_model':'残差候选恢复','residual24_protect':'新证据仅保护',primary:f'并行融合（权重{alpha}）','serial':'恢复谱送冻结旧网'}
    table='|方法|半幅以下目标|新增／恢复半幅失败|每帧参考外峰|目标平均误差|最差保留率下降|\n|---|---:|---:|---:|---:|---:|\n'
    for k,lab in labels.items():
        s=summary['summary'][k];table+=f"|{lab}|{s['below_half']}/{s['targets']}|{s['new_half_vs_old']}／{s['recovered_half_vs_old']}|{s['mean_false40']:.2f}|{s['mean_target_error']:.5f}|{s['max_retention_drop']:.4f}|\n"
    rows=[read(ROOT/'reports/test'/(m['id']+'.json')) for m in read(ROOT/'data/test_manifest.json')['records']]
    cards=[];failures=[];candidate_changes=[];harmonics={};perframe=[]
    plotkeys=['reference','bypass','old40','v1_gate','fft24_model','residual24_model',primary]
    for row in rows:
        m=row['metadata'];id=m['id'];title=f"{m['target_count']}个目标｜{FAMILY[m['family']]}｜{'整数频点' if m['grid']=='grid' else '非整数频点'}"
        def panel(ax,arr,key):
            z=arr[key].reshape(256,4,256,2).max(axis=(1,3));im=ax.imshow(np.fft.fftshift(20*np.log10(np.maximum(z,1e-6)),axes=1),origin='lower',aspect='auto',extent=(-256,256,0,1024),vmin=-60,vmax=0,cmap='magma')
            ax.set_title('多比特参考' if key=='reference' else labels[key],fontsize=10);ax.set_xlabel('多普勒频点');ax.set_ylabel('距离频点')
            for t in m['targets']:ax.plot((t['doppler_bin']+256)%512-256,t['range_bin'],'o',ms=5,mfc='none',mec='cyan',mew=.7)
            return im
        with np.load(row['arrays']) as d:
            fig,axs=plt.subplots(2,4,figsize=(18,9),constrained_layout=True)
            for ax,key in zip(axs.ravel(),plotkeys):im=panel(ax,d,key)
            ax=axs.ravel()[-1]
            for k in ['old40','v1_gate','residual24_model',primary]:ax.plot(np.arange(1,m['target_count']+1),[t['retention'] for t in row['metrics'][k]['targets']],'o-',label=labels[k],ms=3)
            ax.axhline(.5,color='red',ls='--');ax.set_title('同位置目标保留率');ax.set_xlabel('目标编号');ax.grid(alpha=.2);ax.legend(fontsize=7)
            fig.colorbar(im,ax=axs.ravel()[:7].tolist(),shrink=.6,label='相对幅值（分贝）；统一色阶')
            fig.suptitle(title+'\n蓝圈为评价真值，不输入推理；模型谱独立归一化，不代表绝对功率')
            fig.savefig(ROOT/'results'/(id+'.png'),dpi=120);plt.close(fig)
            fig,axs=plt.subplots(1,3,figsize=(15,5),constrained_layout=True)
            for ax,k in zip(axs,['residual24_protect',primary,'serial']):im=panel(ax,d,k)
            fig.colorbar(im,ax=axs.tolist(),shrink=.75,label='相对幅值（分贝）');fig.suptitle(title+'：三种接法诊断')
            fig.savefig(ROOT/'results'/(id+'_interfaces.png'),dpi=110);plt.close(fig)
        for j,t in enumerate(m['targets']):
            ret={k:row['metrics'][k]['targets'][j]['retention'] for k in labels}
            if ret[primary]<.5 or ret['residual24_model']<.5 or ret[primary]<ret['old40']-.05:
                failures.append(dict(id=id,target=j+1,retention=ret,metadata=t))
            candidate_changes.append(dict(id=id,target=j+1,**{a:row['recall'][a][j]['present'] for a in row['recall']}))
        perframe.append(dict(id=id,metrics={k:dict(false40=row['metrics'][k]['false40'],below_half=sum(t['retention']<.5 for t in row['metrics'][k]['targets'])) for k in labels}))
        mt='<table><tr><th>方法</th><th>参考外峰</th><th>半幅失败</th></tr>'+''.join(f'<tr><td>{lab}</td><td>{row["metrics"][k]["false40"]}</td><td>{sum(t["retention"]<.5 for t in row["metrics"][k]["targets"])}</td></tr>' for k,lab in labels.items())+'</table>'
        cards.append(f'<section><h2>{title}</h2><p>编号：{id}；种子：{m["seed"]}</p>{mt}<img src="{id}.png"><details><summary>查看三种组合接口</summary><img src="{id}_interfaces.png"></details><p><a href="../reports/test/{id}.json">逐目标和数据来源</a></p></section>')
    for k in labels:
        harmonics[k]={}
        for h in [-3,5,-7,9,-11,13,-15,17,-19,21,-23,25,-27,29]:
            vals=[v['attenuation_db'] for r in rows for v in r['metrics'][k]['harmonics'] if v['order']==h]
            if vals:harmonics[k][str(h)]=dict(count=len(vals),minimum_db=min(vals),median_db=float(np.median(vals)))
    write(ROOT/'reports/DIAGNOSIS.json',dict(failures=failures,candidate_changes=candidate_changes,harmonics=harmonics,perframe=perframe))
    old=summary['summary']['old40'];new=summary['summary'][primary];mod=summary['summary']['residual24_model']
    doc='# 第二轮：先完成候选与保护迭代\n\n'
    doc+=f"主要候选：残差候选恢复＋并行融合，α={alpha}。预声明最终测试质量门槛**{'通过' if summary['quality_pass'] else '未通过'}**。这是PC浮点原型，不是新网络训练或上板资格；本批结果不能抹去开发、验证和历史失败。\n\n"+table+'\n'
    doc+=f"最终12帧{new['targets']}目标。主候选参考外峰相对旧网变化{(new['mean_false40']/old['mean_false40']-1)*100:+.2f}%，单独残差恢复变化{(mod['mean_false40']/old['mean_false40']-1)*100:+.2f}%。固定阈值峰数不是CFAR虚警率。输出均为相对幅值，不代表绝对功率。\n\n"
    doc+='## 开发、验证与最终测试分开看\n\n|划分|原FFT候选召回|残差候选召回|旧网半幅失败|残差恢复半幅失败|冻结比例融合半幅失败|\n|---|---:|---:|---:|---:|---:|\n'
    for split,label in [('development','两帧旧失败开发'),('validation','六帧新验证'),('test','十二帧冻结后测试')]:
        s=read(ROOT/'reports'/f'{split.upper()}_SUMMARY.json');rr=s['recall'];ss=s['summary']
        doc+=f"|{label}|{rr['fft24']['found']}/{rr['fft24']['total']}|{rr['residual24']['found']}/{rr['residual24']['total']}|{ss['old40']['below_half']}|{ss['residual24_model']['below_half']}|{ss[primary]['below_half']}|\n"
    doc+='\n验证按预声明顺序先最少新增半幅失败、再全部失败、再参考外峰、再幅值误差选比例；选出某个比例不表示验证质量已通过。最终测试不改比例、不换主候选。\n\n'
    doc+='## 候选修正是否有效\n\n|候选方法|进入候选的真实目标|PC符号支路均耗时|最初联合拟合正常收敛帧|\n|---|---:|---:|---:|\n'
    for a,lab in [('v1','原v1'),('fft24','同预算原FFT候选'),('residual24','符号残差候选')]:
        r=summary['recall'][a];t=summary['timing'][a];doc+=f"|{lab}|{r['found']}/{r['total']}|{t['mean_seconds']:.2f}秒|{t['initial_joint_converged']}/12|\n"
    doc+='\n两组新方法最终候选均≤24，使用相同拟合与证据样本；残差方法多一次FFT。PC耗时包含候选及反复估计，不是PL预估。全部原始/拟合/证据索引均保存。\n\n'
    gained=sum(not r['fft24'] and r['residual24'] for r in candidate_changes);lost=sum(r['fft24'] and not r['residual24'] for r in candidate_changes)
    doc+=f"相对同预算FFT候选，残差组新增召回{gained}个、漏掉原本召回的{lost}个。不能只比较总召回数。逐目标映射见reports/DIAGNOSIS.json。开发旧失败帧效果与本轮新测试分开报告，不能以修好了两帧开发图就宣布泛化。\n\n"
    doc+='## 主要候选质量判据\n\n|判据|结果|\n|---|---|\n'
    cn={'no_new_half_vs_old':'相对旧网无新增半幅失败','all_targets_half':'全部目标至少参考半幅','artifact':'参考外峰至少减少10%','mae':'目标MAE增加≤0.005','retention_drop':'最差逐目标保留率下降≤0.05'}
    for k,v in summary['gates'].items():doc+=f"|{cn[k]}|{'通过' if v else '未通过'}|\n"
    doc+=f"\n实测值：新增半幅失败{new['new_half_vs_old']}个；全部半幅失败{new['below_half']}个；参考外峰{new['mean_false40']:.3f}，要求≤{.9*old['mean_false40']:.3f}；目标MAE {new['mean_target_error']:.6f}，要求≤{old['mean_target_error']+.005:.6f}；最大逐目标保留率下降{new['max_retention_drop']:.6f}，要求≤0.05。MAE与保留率均基于归一化幅值，不是物理幅值误差。\n"
    doc+='\n这些是预声明研究门槛，不是行业或部署标准。以下失败/退步必须保留：\n\n|帧／目标|旧网保留率|残差恢复|主候选融合|\n|---|---:|---:|---:|\n'
    for r in failures:doc+=f"|{r['id']}／{r['target']}|{r['retention']['old40']:.4f}|{r['retention']['residual24_model']:.4f}|{r['retention'][primary]:.4f}|\n"
    if not failures:doc+='|本批未见上述失败|—|—|—|\n'
    doc+='\n## 如何解读网络与恢复的关系\n\n原门控和本轮并行输出都没有改变旧网输入，因此不能把它们的失败直接叫作网络输入分布不适配。候选补全收益应先看同预算恢复对照；接口收益再比较保护/融合/串接。\n\n仅保护逐点不低于旧网是设计保证，还须看多放过了多少伪峰。并行融合能否合适由新测试逐目标与背景共同决定。串接使用代理功率和冻结权重，仅反映当前直接接法；没有配套重训，不证明所有串接结构一定合适或不合适。不能仅凭单个指标选另一条接法冒充预定主候选通过。\n\n'
    doc+='## 纯谐波区域的逐阶抑制\n\n以下为“中位数／最差值”，单位dB，相对单比特旁路；负值表示该区域反而增强。排除与真目标重合区域，详细口径见方法说明。区域抑制不等于证明其中每个分量的来源。\n\n|阶次|有效区域数|旧40维|原v1门控|残差恢复|主候选融合|\n|---|---:|---:|---:|---:|---:|\n'
    for h in harmonics['old40']:
        cells=[]
        for key in ['old40','v1_gate','residual24_model',primary]:
            z=harmonics[key][h];cells.append(f"{z['median_db']:.2f}／{z['minimum_db']:.2f}")
        doc+=f"|{h}|{harmonics['old40'][h]['count']}|"+'|'.join(cells)+'|\n'
    doc+='\n'
    doc+='## 数据与复现\n\n2帧旧失败开发、6帧新验证、冻结后12帧新测试；无新MLP训练，无实测数据，全部无窗两电平合成。先读[方法与数据说明](方法与数据说明.md)，完整来源在[数据索引](数据索引.md)及DATA_REGISTER.json。图集[results/index.html](results/index.html)展示全部12帧。\n'
    (ROOT/'本轮结果.md').write_text(doc,encoding='utf8')
    (ROOT/'results/index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>符号残差候选与网络组合对照</title><style>body{font-family:Microsoft YaHei;max-width:1700px;margin:25px auto;background:#eef2f6}section{padding:20px;background:white;margin:20px 0}img{width:100%}td,th{padding:5px;border:1px solid #aaa}table{border-collapse:collapse}summary{cursor:pointer}</style><h1>第二轮：符号残差候选与网络组合</h1><p>预声明主候选质量'+('通过，仍需后续验证' if summary['quality_pass'] else '未通过，不能替换部署')+f'；并行融合权重{alpha}仅由验证集确定。无窗、无新网络训练；真值圈只用于评价，预览4×2最大值池化。</p>'+''.join(cards)+'</html>',encoding='utf8')
    records=[];index=['# 数据来源与用途','', '开发复用上一轮两帧已知失败；六帧验证选择融合权重；十二帧冻结后新测试评价。没有本轮MLP权重训练，帧内拟合不是独立训练帧。','', '|用途|编号|种子|数据|报告|','|---|---|---:|---|---|']
    for split in ['development','validation','test']:
        manifest=read(ROOT/'data'/f'{split}_manifest.json')
        for m in manifest['records']:
            rp=ROOT/'reports'/split/(m['id']+'.json');r=read(rp)
            records.append(dict(split=split,metadata=m,report=str(rp),report_sha256=sha(rp),arrays=r['arrays'],arrays_sha256=r['arrays_sha256'],solver_reports=r['solver_reports']))
            index.append(f"|{dict(development='旧开发',validation='新验证',test='新最终测试')[split]}|{m['id']}|{m['seed']}|[NPZ]({Path(m['file']).as_posix()})|[逐帧](reports/{split}/{m['id']}.json)|")
    index+=['','数据NPZ保存adc_i/adc_q整数回波、sign_i/sign_q取值±1、reference/base位精确FFT uint64功率。results中的NPZ保存相对幅值，不是原始回波。生成脚本与源SHA在各data/*_manifest.json；proposal_indices与fit/evidence_indices在逐臂求解报告。没有用图像PNG训练。']
    (ROOT/'数据索引.md').write_text('\n'.join(index)+'\n',encoding='utf8')
    write(ROOT/'DATA_REGISTER.json',dict(records=records,baseline=read(ROOT/'PROTOCOL.json')['baseline'],model_sha256=frozen['model_sha256'],frozen_sha256=sha(ROOT/'FROZEN.json')))
    write(ROOT/'BUILD_STATUS.json',dict(status='PC_STUDY_COMPLETE',quality_pass=summary['quality_pass'],deployment_ready=False,no_new_training=True,no_board_access=True))
    print('全量中文结果报告完成',summary['gates'],flush=True)

if __name__=='__main__':main()
