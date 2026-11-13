"""Chinese all-case figures and traceable research delivery."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from experiment import np,read,write,sha,CFG
import html,warnings
import matplotlib
matplotlib.use('Agg')
from matplotlib import font_manager
import matplotlib.pyplot as plt
FONT=Path('C:/Windows/Fonts/msyh.ttc');font_manager.fontManager.addfont(str(FONT))
plt.rcParams.update({'font.family':font_manager.FontProperties(fname=str(FONT)).get_name(),'axes.unicode_minus':False,'font.size':10})
warnings.filterwarnings('error',message='Glyph .* missing.*')
LABELS={'bypass':'单比特旁路','clean_guard':'较早干净仿真40维','initial_guard':'上一轮联合40维',
 'f40_base_guard':'40维·沿用损失','f48_base_guard':'48维·沿用损失','f40_repair_guard':'40维·修正损失','f48_repair_guard':'48维·修正损失'}
FAMILIES={'single':'单目标','spread':'分散多目标','near_pairs':'相邻多目标','strong_weak':'强弱混合','mixed_motion':'静止与双向运动混合',
 'collision_minus3':'弱目标与负三次精确重合','collision_plus5':'弱目标与正五次精确重合','near_collision_minus3':'弱目标接近负三次位置','near_collision_plus5':'弱目标接近正五次位置'}
GATES={'all_targets_half':'全部目标至少保留参考半幅','no_new_individual_half_vs_initial':'相对上一轮不新增逐目标半幅失败','low_harmonic_min':'单目标三／五次最差抑制≥10分贝',
 'high_harmonic_min':'单目标高阶最差抑制≥3分贝','single_harmonic_regression':'各阶相对较早干净模型退步≤3分贝','artifact':'平均残留峰不超过上一轮1.05倍','target_mae':'目标平均误差增加≤0.005','no_new_individual_half_vs_same_loss40':'相对同损失40维不新增逐目标半幅失败'}

def save(fig,name):
    fig.savefig(ROOT/'results'/name,dpi=135);plt.close(fig)

def summary_table(summary):
    out=['|方法|半幅失败／目标数|相对上一轮新增逐目标失败|每帧−40分贝残留峰|目标幅值平均误差|全图误差／旁路|','|---|---:|---:|---:|---:|---:|']
    for k,label in LABELS.items():
        s=summary[k];out.append(f"|{label}|{s['below_half']}/{s['targets']}|{s['new_half_vs_initial']}|{s['mean_false40']:.2f}|{s['mean_target_error']:.5f}|{s['mean_nmse_ratio']:.4f}|")
    return '\n'.join(out)

def main():
    report=read(ROOT/'reports/TEST.json');summary=report['summary'];frozen=read(ROOT/'runs/FROZEN.json');audit=read(ROOT/'reports/FEATURE_AUDIT.json')
    numeric=read(ROOT/'reports/INTEGER_SMOKE.json');failures=read(ROOT/'reports/FAILURES.json');p=summary['f48_repair_guard'];control=summary['f40_repair_guard']
    raw=summary['f48_repair_raw']
    methods=['initial_guard','f40_base_guard','f48_base_guard','f40_repair_guard','f48_repair_guard']
    fig,axs=plt.subplots(1,3,figsize=(16,5),constrained_layout=True)
    for ax,key,title in zip(axs,['mean_false40','below_half','mean_target_error'],['每帧参考外残留峰（−40分贝）','低于参考半幅的目标数量','目标平均绝对幅值误差']):
        ax.bar(range(5),[summary[k][key] for k in methods],color=['#999','#689','#9bc','#b98','#236db5'])
        ax.set_xticks(range(5),[LABELS[k] for k in methods],rotation=25,ha='right');ax.set_title(title);ax.grid(axis='y',alpha=.2)
    fig.suptitle('48维受控对照：扩维收益与损失修正收益分开判断')
    save(fig,'summary.png')
    fig,axs=plt.subplots(1,2,figsize=(15,5),constrained_layout=True)
    for key in ['clean_guard','initial_guard','f40_repair_guard','f48_repair_guard']:
        hs=summary[key]['single_harmonics']
        for ax,which,title in zip(axs,['minimum_db','median_db'],['各阶最差抑制','各阶抑制中位数']):
            ax.plot(range(len(CFG['harmonic_orders'])),[hs.get(str(h),{}).get(which,np.nan) for h in CFG['harmonic_orders']],'o-',ms=3,label=LABELS[key])
            ax.set_xticks(range(len(CFG['harmonic_orders'])),[str(h) for h in CFG['harmonic_orders']]);ax.set_xlabel('候选谐波阶次');ax.set_ylabel('相对旁路额外抑制（分贝）');ax.set_title(title);ax.grid(alpha=.2);ax.legend(fontsize=8)
    save(fig,'harmonics.png')
    gallery=[]
    for row in report['rows']:
        title=f"{row['target_count']}个目标｜{FAMILIES[row['family']]}｜{'整数频点' if row['grid']=='grid' else '非整数频点'}";png=row['id']+'.png';gallery.append((row['id'],title,png))
        if (ROOT/'results'/png).exists():continue
        with np.load(row['arrays']) as d:
            fig,axs=plt.subplots(2,4,figsize=(18,9),constrained_layout=True)
            keys=['reference','bypass','initial_guard','f40_base_guard','f48_base_guard','f40_repair_guard','f48_repair_guard']
            for ax,key in zip(axs.ravel(),keys):
                z=d[key].reshape(256,4,256,2).max(axis=(1,3));z=np.fft.fftshift(20*np.log10(np.maximum(z,1e-6)),axes=1)
                im=ax.imshow(z,origin='lower',aspect='auto',extent=(-256,256,0,1024),interpolation='nearest',cmap='magma',vmin=-60,vmax=0)
                ax.set_title('多比特参考' if key=='reference' else LABELS[key]);ax.set_xlabel('有符号多普勒频点');ax.set_ylabel('自然距离频点')
            ax=axs.ravel()[-1]
            for key in ['bypass','initial_guard','f40_repair_guard','f48_repair_guard']:
                ts=row['metrics'][key]['targets'];ax.plot(range(1,len(ts)+1),[t['retention'] for t in ts],'o-',ms=3,label=LABELS[key])
            ax.axhline(.5,color='#b33',ls='--',label='参考半幅');ax.axhline(1,color='#555',ls=':');ax.set_xlabel('目标编号');ax.set_ylabel('输出／多比特参考幅值');ax.set_title('每个真实目标保留率');ax.legend(fontsize=8);ax.grid(alpha=.2)
            fig.colorbar(im,ax=axs.ravel()[:7].tolist(),shrink=.65,label='相对幅值（分贝；网络输出共用旁路标尺）')
            fig.suptitle(title+'\n全图预览采用４×２最大值池化；指标为完整频谱，未做SAR插值',fontsize=13)
            save(fig,png)
        print('中文对照',row['id'],flush=True)
    table=summary_table(summary);gate_text='\n'.join(f"- {GATES[k]}：{'通过' if v else '未通过'}。" for k,v in report['gates']['f48_repair_guard'].items())
    fv=report['feature_value'];delta=100*(1-p['mean_false40']/max(control['mean_false40'],1e-12))
    hs=['|阶次|较早干净40维最差／分贝|上一轮40维最差|本轮40维修正最差|本轮48维修正最差|','|---|---:|---:|---:|---:|']
    for h in CFG['harmonic_orders']:
        vals=[summary[k]['single_harmonics'].get(str(h),{}).get('minimum_db',None) for k in ['clean_guard','initial_guard','f40_repair_guard','f48_repair_guard']]
        hs.append('|'+str(h)+'|'+'|'.join('无有效区域' if v is None else f'{v:.2f}' for v in vals)+'|')
    group_lines=['|场景|目标数|40维修正半幅失败|48维修正半幅失败|40维／48维每帧残留峰|','|---|---:|---:|---:|---:|']
    for family,group in report['groups'].items():
        a,b=group['f40_repair_guard'],group['f48_repair_guard'];group_lines.append(f"|{FAMILIES[family]}|{b['targets']}|{a['below_half']}|{b['below_half']}|{a['mean_false40']:.2f}／{b['mean_false40']:.2f}|")
    failure_lines=['|来源帧编号|多比特参考幅值|旁路幅值|输出幅值|保留率|原始分数|','|---|---:|---:|---:|---:|---:|']
    for t in failures['failures']:
        failure_lines.append(f"|{t['frame']}|{t['reference']:.4f}|{t['bypass']:.4f}|{t['prediction']:.4f}|{t['retention']:.1%}|{t['raw_score']:.3f}|")
    text=f'''# 48维网络训练与验证结果

本轮已完成96帧训练、24帧验证、四组冻结后的48帧新测试，共{p['targets']}个目标实例。预定主候选为48维修正损失组，整体研究质量判据**{'通过' if report['primary_quality_pass'] else '未通过'}**；没有新IP、BIT、ELF，也没有上板。

## 扩维实际是否有收益

同损失的48维相对40维，修正组每帧−40分贝残留峰{'减少' if delta>=0 else '增加'}{abs(delta):.2f}%，半幅失败由{control['below_half']}个变为{p['below_half']}个，新增逐目标半幅退步{fv['f48_repair']['new_half_losses']}个。

预声明的额外8维收益检查：沿用损失组**{'通过' if fv['f48_base']['passed'] else '未通过'}**；修正损失组**{'通过' if fv['f48_repair']['passed'] else '未通过'}**。它同时要求不新增逐目标误压、谐波退步不超过1分贝、目标误差不明显增加，并有实际数量改善。不能把更换损失产生的收益归功于扩维。

本轮结论是：**完成了训练和验证，但尚未证明这版48维特征值得替换40维。** 不能因为扩维后可运行，或某个平均指标改善，就进入部署。修正损失组在单目标部分阶次上也退步，而训练单目标坐标审计没有相同覆盖损失，因此几何问题不是全部解释；特征利用、有限训练样本与目标／谐波约束之间的权衡仍需分别检验。本轮没有通过最终测试重新挑选更有利的主候选。

{table}

残留峰只是固定阈值、有参考的量化伪影代理，不是CFAR虚警率；不能用画面更黑代替恢复成功。所有网络输出采用相同旁路标尺。

## 按场景结果

{chr(10).join(group_lines)}

## 单目标各阶最差抑制

只统计不与真实目标9×9区域重合、参考能量≤旁路区域0.0025倍的5×5候选区域。多目标倍频位置不是同源因果证明。

{chr(10).join(hs)}

## 预声明门槛

{gate_text}

这些是助手预先提出的研究门槛，不是行业标准。门槛未通过时，即使个别指标更好，也不称整体目标实现。通过PC研究判据也不等于跨场景实测泛化或硬件部署通过。

## 改了什么及为什么

新增8维包括两组父候选明确度、父候选的伙伴峰和高阶联合支持、当前位置的高阶支持；仅由单比特输入产生。为避免整数峰坐标乘阶次放大偏差，增加1/16格的定点局部坐标细化。原40维、增益范围、保护层、隐藏层大小不变，48维为2113参数。

另外做了独立损失消融：直接在未限幅分数上约束目标，处理硬限幅外幅值损失无直接梯度的问题；将三／五次纯谐波和更高阶分别归一约束。详细公式、几何及资源边界见`特征与训练设计.md`、`PROTOCOL.json`。

训练集坐标覆盖审计为：{json_text(audit['geometry_summary'])}。这是定位覆盖，不是谐波识别率；真值只用于审计。全部训练帧的新增特征都经过独立标量与向量核对。

**坐标细化存在明确退步，不能称整体定位改善。** 整数格覆盖从100%下降到56.7%，主要发生在多目标：相邻组96项仅28项覆盖、分散组96项仅41项、混合运动96项仅47项；单目标16项仍全部覆盖。非整数格从47.1%提高到90.4%。这里审计的是训练目标B的−7/+9查询位置，不代表所有父候选均正确。局部旁瓣比值在多目标量化谱中可能把邻格干扰当作离格泄漏；这是与观察相符的解释，尚未通过独立消融证明完整因果。`FEATURE_AUDIT.json`的PASS只表示实现一致、零输入与初始函数等检查通过，不表示几何质量通过。本轮保留预声明定义完成训练和测试，没有事后替换坐标规则或权重。

进一步对相同训练数据分解步骤：整数场景448项的局部整数峰均未移动、均能覆盖；加入小数偏移后194项移出覆盖窗口。因此本轮几何退步可以定位到小数偏移步骤，而非整数峰搜索。详情见`reports/GEOMETRY_DIAGNOSIS.json`；这仍不能单独证明最终图像退步有多少由它造成，需要下一轮受控消融。后续优先检查坐标估计的适用条件和保守回退，而不是盲目增加维数或扩大查询窗口。

## 数值与剩余问题

主候选四个预定帧的Q16冒烟：系数/已观察累加值位宽{'通过' if numeric['all_fit_width'] else '存在失败'}，相对浮点新增半幅失败{'无' if numeric['no_new_half_vs_float'] else '存在或检查未完成'}。详细误差见`reports/INTEGER_SMOKE.json`。这不是完整任意输入位宽证明，也不是RTL/BRAM/时序验证。

本轮仍有{len(failures['failures'])}个主候选目标低于参考半幅，逐点原始分数、新8维及与初始/同损失40维的退步在`reports/FAILURES.json`。精确重合不能保证仅凭单帧功率谱唯一判别。增益上限不足目标数为{p['upper_gain_cannot_reach_half']}，仍计入失败。

主候选保护前／后的半幅失败为{raw['below_half']}／{p['below_half']}，每帧参考外残留峰为{raw['mean_false40']:.2f}／{p['mean_false40']:.2f}。保护前结果也一并保存，不能把所有未抑制谐波自动归因于保护层。训练中加入约束只是改变优化目标，并不保证所有约束在新场景都满足；本轮最终结果比训练损失下降更能决定是否继续采用该设计。

{chr(10).join(failure_lines)}

数据为干净可分离点频仿真，尚未验证噪声、杂波、真实512chirp新场景或运动SAR聚焦。暖启动权重有历史实测影响，但本轮更新只用新仿真。最终测试已读取，若继续据此调参必须换新测试种子。

## 查看入口

- 全部48帧中文对照：`results/index.html`。
- 主候选权重：`candidate/f48_repair/model_float.pt`，SHA256：`{frozen['arms']['f48_repair']['sha256']}`。
- 同损失40维与另两组权重：`candidate/`；不能把不同组混作同一模型。
- 原始逐帧指标及保护前后结果：`reports/TEST.json`；验证与冻结：`reports/VALIDATION.json`、`runs/FROZEN.json`。
- 来源、种子、样本映射与运行指令：`数据来源与复现.md`、`DATA_REGISTER.json`。
'''
    (ROOT/'本轮训练结果.md').write_text(text,encoding='utf8')
    register=[];split_lines=[]
    for split,zh in [('train','训练'),('validation','验证选模'),('test','冻结后测试')]:
        rs=read(ROOT/'data'/f'{split}_manifest.json')['records'];split_lines.append(f"|{zh}|{len(rs)}|{min(r['seed'] for r in rs)}～{max(r['seed'] for r in rs)}|`data/{split}/`|`data/{split}_manifest.json`|")
        register.extend(dict(**r,absolute_path=str(ROOT/r['file']),usage=zh) for r in rs)
    write(ROOT/'DATA_REGISTER.json',dict(records=register,generator=str(ROOT/'experiment.py'),generator_sha256=sha(ROOT/'experiment.py'),feature_source=str(ROOT/'features48.py'),feature_sha256=sha(ROOT/'features48.py'),protocol_sha256=sha(ROOT/'PROTOCOL.json')))
    pool=read(ROOT/'data/POOL.json');unique=sum(r['unique_pixels'] for r in pool['frames']);fallback=sum(r['fallback_samples'] for r in pool['frames'])
    doc='''# 数据来源、划分与复现

全部本轮数据是本机新生成的无噪声、无杂波二维复点频回波；先叠加所有目标，整数取样后统一I/Q±64量化，再使用Xilinx位精确FFT。不使用作者RGB图或旧BIN作为本轮梯度数据。NPZ保存reference与base两幅uint64功率，不是RGB图；ADC可用参数与种子重建。

|用途|帧数|种子|数据目录|每帧真值与SHA256|
|---|---:|---|---|---|
'''+ '\n'.join(split_lines)+f'''

训练池共{pool['shape'][0]}行，对应{unique}个唯一“帧＋频点”位置。采样有放回，不能把样本行数称作独立目标数。类别没有符合位置时会退回随机抽样，共{fallback}行；退回标志、帧索引、完整频点索引和采样类别保存在`data/train_sample_origin.npz`。列定义在`data/POOL.json`。

发生器为`experiment.py:scene/prepare`，基础回波/FFT源为`source/common.py`、`source/fft_reference/xfft_model.py`。本轮从上一轮复制的指标与损失见`reference_v2.py`，其参数快照为`source/v2_protocol.json`。新特征只读取输入功率及其特征，不读取参考或目标元数据。

初始化来自`scalar_constraints_v2/candidate/joint/model_float.pt`，SHA256 `{CFG['initial_sha256']}`。48维零扩展第一层，40/48起始函数一致。另保留较早干净仿真模型用于逐阶抑制对照，不用它在最终测试重新选模。

首次复现训练流程：`experiment.py prepare`→`train`→`select`→`test`，然后`numerical_check.py`、`build_report.py`、`standard_check.py`。完成记录会保留，修改条件应另建目录并换新的最终测试种子。

独立推理示例：

```powershell
& 'C:\\Users\\yang\\AppData\\Local\\Programs\\Python\\Python313\\python.exe' -X utf8 'C:\\Users\\yang\\Desktop\\SAR_IMAGE\\scalar_multipeak48_v1\\infer.py' --input 'C:\\Users\\yang\\Desktop\\SAR_IMAGE\\scalar_multipeak48_v1\\data\\test\\000_single_grid_a.npz' --output 'C:\\Users\\yang\\Desktop\\SAR_IMAGE\\scalar_multipeak48_v1\\results\\user_inference.npz'
```

只读取输入文件base功率，输出gain_q14、power和relative_amplitude。神经推理浮点、特征Q12与原保护整数化；不是已完成RTL的IP。输出路径存在时拒绝覆盖。

来源复制与初始权重散列见SOURCE_SNAPSHOT.json，完整交付散列见FILE_MANIFEST.json。完整性检查PASS不替代恢复质量或扩维收益判据。
'''
    (ROOT/'数据来源与复现.md').write_text(doc,encoding='utf8')
    cards=''.join(f'<section><h2>{html.escape(title)}</h2><p>来源编号：{name}；全部测试帧保留。</p><a href="{png}"><img loading="lazy" src="{png}" alt="{html.escape(title)}对照"></a></section>' for name,title,png in gallery)
    rows=''.join(f"<tr><td>{LABELS[k]}</td><td>{s['below_half']}/{s['targets']}</td><td>{s['new_half_vs_initial']}</td><td>{s['mean_false40']:.2f}</td><td>{s['mean_target_error']:.5f}</td></tr>" for k,s in summary.items() if k in LABELS)
    page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>48维网络训练与验证</title><style>body{{font-family:"Microsoft YaHei",sans-serif;max-width:1600px;margin:30px auto;padding:0 24px;background:#f5f7fa;color:#172b43}}img{{width:100%}}section{{background:white;padding:16px;margin:24px 0}}td,th{{padding:10px;border:1px solid #ccd}}table{{border-collapse:collapse}}.note{{padding:16px;background:#fff2d8}}</style><h1>48维网络：新增特征与损失修正的受控对照</h1><p class="note">主候选整体质量：{'通过本轮研究判据' if report['primary_quality_pass'] else '未通过'}；新增8维收益：沿用损失组{'通过' if fv['f48_base']['passed'] else '未通过'}，修正组{'通过' if fv['f48_repair']['passed'] else '未通过'}。没有硬件部署，不能用总体均值掩盖逐目标或逐阶退步。</p><p>全部48帧都展示。显示采用４×２最大值池化，指标使用完整1024×512；固定−60～0分贝，网络共用旁路标尺，超过0分贝饱和显示。图是RD频谱，未做SAR插值。</p><img src="summary.png" alt="总体对照"><img src="harmonics.png" alt="逐阶最差和中位抑制"><table><tr><th>方法</th><th>半幅失败／目标数</th><th>相对上一轮新增逐目标失败</th><th>每帧残留峰</th><th>目标幅值误差</th></tr>{rows}</table>{cards}</html>'''
    (ROOT/'results/index.html').write_text(page,encoding='utf8')
    print('中文结果、完整来源与操作说明完成',flush=True)

def json_text(x):
    return '；'.join(f"{'整数格' if k=='grid' else '非整数格'}{v['count']}项，原始{v['original_coverage']:.1%}→细化后{v['refined_coverage']:.1%}" for k,v in x.items())

if __name__=='__main__':main()
