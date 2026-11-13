"""Generate evidence/report only; never select or retrain on final tests."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
from run import ROOT,np,read,write,sha,BIN_M,CFG
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import html, json

FONT=Path('C:/Windows/Fonts/msyh.ttc')
font_manager.fontManager.addfont(str(FONT))
plt.rcParams.update({'font.family':font_manager.FontProperties(fname=str(FONT)).get_name(),'axes.unicode_minus':False,'font.size':11})
NAMES={'reference':'多比特参考','bypass':'单比特旁路','old40':'单比特接旧网络','model':'独立残差恢复','old_serial':'恢复后接冻结旧网络','adapt_raw':'恢复后接输入适配网络','suppress_raw':'恢复后接去伪网络（主候选）','suppress_guard':'去伪网络加旧保护（消融）'}
SCENES=dict(zip(CFG['templates'],['整数频点单目标','非整数频点单目标','四目标分散','四目标近邻','四目标强弱混合','八目标分散','八目标近邻','八目标强弱混合','真目标与负三次谐波重合','真目标与正五次谐波重合','真目标靠近正五次谐波','两目标强弱混合（非整数）']))
KEYS=list(NAMES)[2:]

def table(headers,rows):
    return '| '+' | '.join(headers)+' |\n|'+'|'.join(['---']*len(headers))+'|\n'+''.join('| '+' | '.join(map(str,r))+' |\n' for r in rows)

def htable(headers,rows):
    return '<table><thead><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in r)+'</tr>' for r in rows)+'</tbody></table>'

def main():
    report=read(ROOT/'reports/TEST_SUMMARY.json');summ=report['summary']
    rows=[read(p) for p in sorted((ROOT/'reports/test').glob('*.json'))]
    assert len(rows)==12
    frozen=read(ROOT/'FROZEN.json');out=ROOT/'results';out.mkdir(exist_ok=True)
    summary_headers=['方法','参考外峰/帧（≤40米）','最强参考外幅值','超额能量/帧','主要目标不足半幅','弱目标不足半幅','全频谱参考外峰/帧']
    summary_rows=[[NAMES[k],f"{s['mean_false40']:.2f}",f"{s['worst_false']:.5f}",f"{s['mean_excess']:.6g}",f"{s['main_half_fail']}/{s['main_targets']}",f"{s['weak_half_fail']}/{s['weak_targets']}",f"{s['full_mean_false40']:.2f}"] for k,s in summ.items()]
    cards=[];images=[];details=[];transitions={};harmonics={};distance={};frame_table=[]
    for row in rows:
        m=row['record']['metadata'];ident=row['record']['id'];title=SCENES[m['template']]
        with np.load(row['arrays']) as z:a={k:z[k] for k in z.files}
        for zoom in [False,True] if m['template'] in ['n4_strong_weak','n8_strong_weak','collision_plus5_offgrid'] else [False]:
            keys=list(NAMES) if not zoom else ['reference','model','old_serial','old40','adapt_raw','suppress_raw']
            fig,axes=plt.subplots(2,len(keys)//2,figsize=(24,15) if not zoom else (19,12),layout='constrained')
            extent=[-256.5,255.5,-BIN_M/2,(1023.5)*BIN_M]
            for ax,k in zip(axes.flat,keys):
                # Preserve single-bin peaks when plotting a tall spectrum at screen resolution.
                # This is display-only max aggregation; metrics retain all 1024x512 pixels.
                shifted=np.fft.fftshift(a[k],axes=1)
                shown=shifted.reshape(512,2,256,2).max(axis=(1,3))
                db=20*np.log10(np.maximum(shown,1e-3))
                im=ax.imshow(db,origin='lower',aspect='auto',extent=extent,cmap='turbo',vmin=-60,vmax=0,interpolation='nearest')
                ax.scatter([((t['doppler_bin']+256)%512)-256 for t in m['targets']],[t['range_m'] for t in m['targets']],s=85,facecolors='none',edgecolors='white',linewidths=.8)
                ax.axhline(40,color='white',lw=.5,ls='--');ax.set_xlabel('多普勒频点索引');ax.set_ylabel('等效距离 / 米')
                subtitle=''
                if k in row['metrics']:
                    mm=row['metrics'][k];n=sum(t['within40'] and t['retention']<.5 for t in mm['targets'])
                    subtitle=f"\n40米内残峰 {mm['primary']['false40']}，不足半幅目标 {n}"
                ax.set_title(NAMES[k]+subtitle)
                if zoom:
                    ranges=[t['range_m'] for t in m['targets']];lo=max(0,min(ranges)-1);hi=min(1024*BIN_M,max(ranges)+1)
                    ax.set_ylim(lo,hi)
            fig.colorbar(im,ax=list(axes.flat),label='相对幅值 / 分贝（所有面板共用色标）',shrink=.85)
            fig.suptitle(title+(' · 距离局部放大' if zoom else ' · 全频谱')+'\n白圈：仿真真目标；显示按2×2格取最大值以保留单格峰，评估用原分辨率\n统一色标、不重新归一化；低于−60分贝同色',fontsize=16)
            name=ident+('_zoom' if zoom else '')+'.png';fig.savefig(out/name,dpi=150);plt.close(fig);images.append(name)
        localrows=[]
        for ti,t in enumerate(row['metrics']['suppress_raw']['targets']):
            rr={'frame':ident,'target':ti,'range_m':t['range_m'],'doppler_bin':t['doppler_bin'],'reference':t['reference'],'main':t['main'],'within40':t['within40'],'methods':{k:row['metrics'][k]['targets'][ti] for k in KEYS}}
            details.append(rr)
            localrows.append([ti+1,f"{t['range_m']:.2f}",'主要' if t['main'] else '弱',f"{t['reference']:.4f}"]+[f"{rr['methods'][k]['retention']:.3f}" for k in KEYS])
        frame_table.append([title]+[row['metrics'][k]['primary']['false40'] for k in KEYS])
        cards.append(f'<section id="{ident}"><h2>{title}</h2><p>源帧：{ident}；种子：{m["seed"]}。所有方法使用同一帧，白圈不参与推理。</p><a href="{ident}.png"><img loading="lazy" src="{ident}.png" alt="{title}八路同帧对照"></a>'+(f'<p><a href="{ident}_zoom.png">查看距离局部放大</a></p>' if ident+'_zoom.png' in images else '')+'<details><summary>逐目标输出/参考幅值比（小于0.5记不足半幅）</summary>'+htable(['目标','距离/米','类别','参考幅值']+[NAMES[k] for k in KEYS],localrows)+'</details></section>')
        print('生成中文对照',ident,flush=True)
    for k in KEYS:
        ts=[r['methods'][k] for r in details if r['within40']];new=[r['methods']['suppress_raw'] for r in details if r['within40']]
        transitions[k]={'new_main_half_fail':sum(t['main'] and t['retention']>=.5 and n['retention']<.5 for t,n in zip(ts,new)),
            'new_weak_half_fail':sum(not t['main'] and t['retention']>=.5 and n['retention']<.5 for t,n in zip(ts,new)),
            'recovered_main':sum(t['main'] and t['retention']<.5<=n['retention'] for t,n in zip(ts,new)),
            'recovered_weak':sum(not t['main'] and t['retention']<.5<=n['retention'] for t,n in zip(ts,new))}
        distance[k]={}
        for name,low,hi in [('0–5米',0,5),('5–20米',5,20),('20–40米',20,40),('40米以外',40,1e9)]:
            tt=[r['methods'][k] for r in details if low<r['range_m']<=hi]
            distance[k][name]={cat:{'count':len(sub),'half_fail':sum(t['retention']<.5 for t in sub),'mean_retention':float(np.mean([t['retention'] for t in sub])) if sub else None} for cat,sub in [('main',[t for t in tt if t['main']]),('weak',[t for t in tt if not t['main']])]}
        harmonics[k]={}
        orders=sorted({h['order'] for row in rows for h in row['metrics'][k]['harmonics']},key=abs)
        for order in orders:
            vals=[dict(frame=row['record']['id'],**h) for row in rows for h in row['metrics'][k]['harmonics'] if h['order']==order]
            harmonics[k][str(order)]={'count':len(vals),'median_db':float(np.median([v['attenuation_db'] for v in vals])),'worst':min(vals,key=lambda v:v['attenuation_db'])}
    write(ROOT/'reports/DETAILED_DIAGNOSIS.json',dict(targets=details,transitions_vs_primary=transitions,distance_groups=distance,harmonics=harmonics))
    # Common logarithmic scale; independent frontend peak normalization is explicitly disclosed.
    fig,axes=plt.subplots(1,2,figsize=(13,5),layout='constrained')
    for arm,label in [('adapt','输入适配'),('suppress','加强去伪')]:
        complete=read(ROOT/'runs'/arm/'COMPLETE.json');log=complete['loss_log']
        axes[0].plot([x['step'] for x in log],[x['loss'] for x in log],marker='o',label=label)
        cs=[read(ROOT/'runs'/arm/f'step_{step}.json') for step in CFG['training']['checkpoints']]
        axes[1].plot([x['step'] for x in cs],[x['summary']['mean_false40'] for x in cs],marker='o',label=label)
    axes[0].set(xlabel='训练步数',ylabel='损失数值',title='损失项不同，两组数值不可横向比优劣')
    axes[1].set(xlabel='训练步数',ylabel='40米内参考外峰 / 帧',title='验证集选模；最终测试不参与')
    for ax in axes:ax.legend();ax.grid(alpha=.2)
    fig.savefig(out/'training.png',dpi=150);plt.close(fig);images.append('training.png')
    a=summ['suppress_raw'];b=summ['model'];old=summ['old_serial'];adapt=summ['adapt_raw']
    reduction=lambda x,y:100*(1-x/y) if y else float('nan')
    status='通过本轮预声明的去伪优先判据' if report['quality_pass'] else '未通过本轮预声明的全部判据'
    intro=f"最终12帧新种子测试：主候选{status}。40米内参考外残峰从独立恢复的{b['mean_false40']:.2f}个/帧降到{a['mean_false40']:.2f}，减少{reduction(a['mean_false40'],b['mean_false40']):.2f}%；主要目标不足半幅{a['main_half_fail']}/{a['main_targets']}，弱目标不足半幅{a['weak_half_fail']}/{a['weak_targets']}。这是去伪与弱目标保留的明显取舍，不是无损恢复。"
    gate_names={'main_targets':'40米内主要目标全部≥参考半幅','peaks_vs_model':'残峰较独立恢复减少≥20%','peaks_vs_old_serial':'残峰较恢复接旧网减少≥10%','excess':'超额能量较独立恢复减少≥20%','worst_false':'最强参考外峰不高于独立恢复'}
    gate_rows=[[gate_names[k],'通过' if v else '未通过'] for k,v in report['gates'].items()]
    harmonic_rows=[]
    for order,h in harmonics['suppress_raw'].items():harmonic_rows.append([order,h['count'],f"{harmonics['model'][order]['median_db']:.2f}",f"{h['median_db']:.2f}",f"{h['worst']['attenuation_db']:.2f}",h['worst']['frame']])
    distance_rows=[]
    for name,g in distance['suppress_raw'].items():distance_rows.append([name,f"{g['main']['half_fail']}/{g['main']['count']}",f"{g['weak']['half_fail']}/{g['weak']['count']}"])
    transition_rows=[[NAMES[k],t['new_main_half_fail'],t['new_weak_half_fail'],t['recovered_main'],t['recovered_weak']] for k,t in transitions.items() if k!='suppress_raw']
    seconds=[read(r['record']['solver_report'])['seconds'] for r in rows]
    md=f'''# 恢复后网络去伪：本轮结果

{intro}

看图：[全部12帧中文同帧对照](results/index.html)。权重：[主候选](candidate/suppress/model_float.pt)，运行：[infer.py](infer.py)。本轮没有更新旧工程、IP、BIT或ELF，没有操作板卡。

## 同一组新测试上的结果

{table(summary_headers,summary_rows)}
统计12帧、全范围{len(details)}个已知仿真目标，40米内{a['targets']}个。主要目标按参考峰相对幅值≥0.25划分；不足半幅按同一参考峰位置评价，不等于实际检测漏警。旧40维网络用原单比特频谱，其余后级网络用同一个残差恢复谱。

残峰口径：排除已知目标9×9邻域，输出>参考2倍且超额>0.0001；局部3×3峰、幅值≥0.01（−40分贝），5×5去重。最强参考外幅值采用符合超额条件的背景像素最大值。该诊断不是CFAR虚警率，也不能把所有参考外成分都定为某一阶谐波。

## 改了什么、为何能进一步抑制

1. 固定原残差候选恢复前端，换成以恢复谱为输入继续训练的后级网络。代理功率为round(恢复相对幅值²×原单比特功率峰)，提取32基础量再派生40维；MLP仍为40→32→16→1、1857参数。
2. 两组共同将幅值增益下限1/8改到1/64（约−36.12分贝），上限1.5不变；无固定保护训练。网络给出s，输出为恢复幅值×2^clip(s,−6,log2(1.5))。这只是条件衰减，不能凭空补出前端已删掉的目标。
3. 共同损失：幅值误差×4、原始分数SmoothL1×0.2、主要目标中心幅值误差×12、弱目标中心误差×1。主候选再增加伪影分数SmoothL1×2与伪影正超额幅值误差×12。参考增益分数来自同一回波多比特参考与恢复幅值之比；对限幅前s监督，避免只通过硬限幅后的幅值训练时梯度失效。
4. 批次25%目标区域、50%伪影区域、25%混合池。提高强错误分量的采样和惩罚权重，使网络不容易仅靠压低大量低能背景取得平均损失优势。真实位置标签只用于训练与评估，不送入推理。

两组同初始化、同抽样、各8000步，均由12帧验证集选择第{frozen['selected']['suppress']['step']}步（适配组第{frozen['selected']['adapt']['step']}步）。最终测试没有参与选模。两组都继承旧权重，不能说是完全从零训练或完全没有历史实测影响。

## 对照解释与代价

单纯适配：参考外峰{adapt['mean_false40']:.2f}/帧；加强伪峰约束后{a['mean_false40']:.2f}/帧，额外减少{reduction(a['mean_false40'],adapt['mean_false40']):.2f}%。相对恢复接旧网减少{reduction(a['mean_false40'],old['mean_false40']):.2f}%。原单比特接旧网为{summ['old40']['mean_false40']:.2f}/帧，同样列出，避免只与较差方案比较。

同权重加旧保护后为{summ['suppress_guard']['mean_false40']:.2f}个残峰/帧，弱目标不足半幅{summ['suppress_guard']['weak_half_fail']}/{summ['suppress_guard']['weak_targets']}；它是消融，不用它事后替换预定主候选。共同增益下限与保护改变没有分别做完整因果消融，所以对旧模型的总改善不能全归于新增损失。

以下统计主候选相对其他方法新发生和恢复的半幅失败（逐目标配对、≤40米）：

{table(['比较对象','新增主要目标失败','新增弱目标失败','恢复主要目标','恢复弱目标'],transition_rows)}
不能把被网络压掉的弱目标都解释为“原来就检测不到”。这是当前约束选择的真实代价。主要目标最小保留比{a['main_min_retention']:.4f}；目标平均幅值绝对误差{a['target_mae']:.5f}，不宣称绝对幅值恢复。

{table(['距离组','主要目标不足半幅','弱目标不足半幅'],distance_rows)}
近距离也可能存在弱反射，距离组只用于报告，不保证近目标强。40米以外的折叠重合目标不计入主判据，但完整保留在逐目标报告中。

## 判据与逐阶检查

{table(['预先声明的研究判据','最终结果'],gate_rows)}
这些阈值是本轮助手预声明的实验判据，不是行业标准。通过不等于所有谐波和伪影被清除，也不等于实测或部署验收。

{table(['谐波阶次','样本数','独立恢复中位抑制/分贝','主候选中位抑制/分贝','主候选最差抑制/分贝','最差帧'],harmonic_rows)}
逐阶数值相对原单比特旁路的5×5区域能量；仅统计远离真目标、参考能量足够低的纯谐波候选。接近零的恢复谱会产生很大的数值抑制比，不能当作真实系统动态范围。重合目标、互调和所有错误峰不能靠该表穷尽。

逐帧残峰如下（全部≤40米）；细节见[逐目标与逐阶JSON](reports/DETAILED_DIAGNOSIS.json)：

{table(['场景']+[NAMES[k] for k in KEYS],frame_table)}

## 数据、复现与限制

[数据索引](数据索引.md)给出68帧输入、恢复谱、种子、散列、训练池到源帧/像素映射。44训练帧中32帧是此前已看过的数据，明确转作训练；新增12训练/12验证/12最终测试，各组种子互不重合。训练池165931行不是165931帧，训练中的重复抽样也不增加独立样本数。

新测试覆盖有限的单点、多点、强弱和谐波重合模板，与训练同属一个仿真生成族，是独立种子留出，不是跨场景分布或真实环境泛化证明。没有噪声、杂波或真实车载/近场传播模型，没有新增实测验证。

原回波先叠加后统一I/Q±64量化，FFT用原位精确参考。多比特与单比特各自峰值归一化，恢复谱也按自身峰归一化，故这里只比较相对结构与幅值；后级输出不再单独拉伸。图统一−60至0分贝，白圈仅标注真值。为防缩图漏掉单格峰，所有面板显示时统一按2×2格取最大值；计算、训练、指标和NPZ仍为原1024×512。本轮展示RD谱，不是新增SAR聚焦结果。

冻结前端本次CPU平均{np.mean(seconds):.2f}秒/帧、最慢{max(seconds):.2f}秒/帧；后级是轻量MLP，但组合前端仍是迭代求解器，不能称已满足实时FPGA实现。新下限尚未做定点/RTL适配，本轮不重建BIT。

结论限定：这轮用于判断“恢复之后再训练一个后级，能否进一步去除错误分量”。{status}，同时完整保留弱目标损失与剩余误峰，后续是否接受该工作点应结合图像和新的实测数据判断。
'''
    (ROOT/'本轮结果.md').write_text(md,encoding='utf-8')
    allrecords={'train':read(ROOT/'data/TRAIN_REGISTER.json')['records'],'validation':read(ROOT/'data/VALIDATION_REGISTER.json')['records'],'test':read(ROOT/'data/test_manifest.json')['records']}
    entries=[];indexrows=[]
    for split,records in allrecords.items():
        for r in records:
            m=r['metadata'];entry=dict(split=split,id=r['id'],seed=m['seed'],origin=r['origin'],input=m['file'],input_sha256=m['sha256'],spectra=r['source_arrays'],spectra_sha256=r['source_arrays_sha256'],solver_report=r['solver_report'],solver_sha256=r['solver_report_sha256'])
            entries.append(entry);label={'train':'训练','validation':'验证选模','test':'冻结后最终测试'}[split]
            indexrows.append([label,r['id'],m['seed'],f"[原始输入]({Path(m['file']).as_posix()})",f"[恢复谱]({Path(r['source_arrays']).as_posix()})",r['origin']])
    register=dict(records=entries,counts={k:len(v) for k,v in allrecords.items()},new_generator=str(ROOT/'run.py'),echo_generator=str(ROOT.parent/'scalar_multipeak48_v1/source/common.py'),frozen_sources=frozen['sources'],pool=str(ROOT/'data/train_pool.npz'),pool_sha256=sha(ROOT/'data/train_pool.npz'),test_previously_unseen=True,test_now_viewed=True)
    write(ROOT/'DATA_REGISTER.json',register)
    (ROOT/'数据索引.md').write_text('# 本轮数据来源与划分\n\n44训练／12验证／12最终测试，共68帧。前32训练帧已被此前实验看过，本轮不再称留出。最终测试现已读取，后续不可再作为未见盲测。\n\n新训练种子20261113000–20261113011；验证20261114000–20261114011；测试20261115000–20261115011。生成器run.py的scene函数重映射距离，调用原common.echo叠加回波；参数、频点、相位与目标幅值在各metadata内，量化先于FFT。新数据固定1024×512，无噪声/杂波，无加窗。继承权重有历史实测影响。\n\n输入NPZ保存adc_i/adc_q（int16原始复回波）、sign_i/sign_q（±1符号，对应±64）、reference/base（uint64 FFT功率）。恢复谱NPZ保存相对幅值；训练池保存32基础Q12特征、参考/恢复幅值、标签、frame/pixel源映射。MLP内再派生40维。图片只是显示，不用于训练。\n\n[data/train_pool.npz](data/train_pool.npz)的frame是TRAIN_REGISTER.records索引，pixel是1024×512自然顺序的r×512+d；[POOL_REGISTER](data/POOL_REGISTER.json)列逐帧行数，合计165931行。训练重复抽样不是新增独立帧。\n\n[完整来源与SHA](DATA_REGISTER.json)、[预声明方案](PROTOCOL.json)、[冻结记录](FROZEN.json)。标注只训练/评价使用，infer.py只读恢复幅值与原单比特功率峰。\n\n'+table(['用途','源帧','种子','输入','恢复谱','来源'],indexrows),encoding='utf-8')
    webpage='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>恢复后网络去伪：同帧对照</title><style>body{font:16px/1.6 "Microsoft YaHei",sans-serif;margin:28px auto;max-width:1600px;padding:0 20px;background:#f5f7fa;color:#172333}table{border-collapse:collapse;width:100%;font-size:14px;background:white}th,td{border:1px solid #cbd3dd;padding:7px;text-align:left}section{margin:28px 0;padding:20px;background:white;border-radius:10px}img{width:100%;height:auto}a{color:#095fb0}.note{padding:18px;background:#fff1d6}summary{cursor:pointer}nav a{display:inline-block;margin:6px}</style><h1>恢复后网络去伪：12帧新种子对照</h1>'''
    webpage+='<p class="note">'+html.escape(intro)+'</p><p>所有图统一−60至0分贝，后级输出不重新归一化；白圈只用于评估。主要目标定义为参考相对幅值≥0.25。残峰是参考外误差诊断，不是实际检测虚警率。本轮只有PC仿真，无新BIT或上板。</p><p><a href="../本轮结果.md">完整结论与限制</a> · <a href="../数据索引.md">数据与来源</a></p>'+htable(summary_headers,summary_rows)+'<nav>'+''.join(f'<a href="#{row["record"]["id"]}">{SCENES[row["record"]["metadata"]["template"]]}</a>' for row in rows)+'</nav>'+''.join(cards)+'<section><h2>训练与验证选模</h2><img src="training.png" alt="训练损失与验证残峰曲线"></section></html>'
    (out/'index.html').write_text(webpage,encoding='utf-8')
    write(ROOT/'reports/FIGURE_REGISTER.json',dict(font=str(FONT),images=images,common_scale_db=[-60,0],display_only_max_pool=[2,2],metric_shape=[1024,512],post_output_renormalized=False,visual_inspection_pending=True))
    print(intro,flush=True)

if __name__=='__main__':main()
