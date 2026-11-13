"""Write task-scoped conclusions; never replace the full-quality verdict."""
from pathlib import Path
import ast,json,zipfile,shutil
from experiment import ROOT,OLD,read,write,sha

def main():
    dev=read(ROOT/'development_profiled/report.json');fresh=read(ROOT/'fresh_test/report.json');numeric=read(ROOT/'NUMERIC_VERIFICATION.json');frozen=read(ROOT/'FROZEN_MODEL.json');acceptance=read(ROOT/'CORRECTION_ACCEPTANCE.json')
    checks={k:fresh['summary']['checks'][k] for k in acceptance['checks']}
    weak_status='PASS' if all(checks.values()) and read(ROOT/'DEVELOPMENT_CORRECTION_CHECK.json')['status']=='PASS' else 'FAIL'
    diagnosed=next(t for r in dev['rows'] if r['id']=='confirm_synth_116013_512' for t in r['targets'] if t['measured_peak_bin']==[221,205])
    result=dict(weak_correction_status=weak_status,weak_correction_checks=checks,overall_original_quality_status=fresh['status'],overall_original_quality_checks=fresh['summary']['checks'],numeric_status=numeric['status'],diagnosed_target=diagnosed,
        development_known_targets=dev['summary']['known_targets'],development_new_half_losses=dev['summary']['new_targets_below_half'],fresh_known_targets=fresh['summary']['known_targets'],fresh_known_weak_targets=fresh['summary']['known_weak_targets'],fresh_new_half_losses=fresh['summary']['new_targets_below_half'],fresh_weak_mae_ratio_to_bypass=fresh['summary']['weak_mae_ratio'],fresh_v2_nonregression=fresh['summary']['v2_nonregression'],
        architecture=[40,32,16,1],parameters_per_profile=1857,stored_weight_profiles=2,corrected_actual_chirps=512,unchanged_actual_chirps=128,power_guard_changed=False,external_interface_changed=False,quantizer_changed=False,initial_model_preserved=True,selected_model_sha256=frozen['sha256'],model_path='pc_candidate',comparison='results/index.html',ip_built=False,bit_rebuilt=False,board_accessed=False)
    write(ROOT/'RESULTS.json',result)
    failed=[k for k,v in fresh['summary']['checks'].items() if not v]
    write(ROOT/'BUILD_STATUS.json',dict(stage='PC_WEAK_CORRECTION_'+weak_status,weak_correction=weak_status,original_full_quality=fresh['status'],numeric=numeric['status'],ready_for_board_test=False,ready_for_ip_adaptation=fresh['status']=='PASS' and numeric['status']=='PASS',ip_built=False,bit_rebuilt=False,board_tested=False,failed_full_quality_checks=failed,active_model='pc_candidate',active_comparison='results/index.html'))
    table=[]
    for name,rep in [('开发诊断',dev),('新留出',fresh)]:
        for group,v in rep['summary']['v2_nonregression'].items():table.append(f'| {name}/{group} | {v["nmse_relative_to_v2"]:.4f} | {v["background_error_relative_to_v2"]:.4f} |')
    failtext='、'.join(failed) if failed else '无'
    doc=f'''# 弱目标误压修正结果

本轮弱目标修正检查 **{weak_status}**，PC 定点/独立运行检查 **{numeric['status']}**；原整体验收门槛 **{fresh['status']}**。三个结论分别记录，不以单项修正通过替代整体质量通过。本轮没有新 IP/BIT/ELF、没有操作板卡。原工程、冻结 V7、v2 研究包保持不变。

## 修正效果

原失败合成例 `confirm_synth_116013_512` 的参考峰在自然距离索引 221、Doppler 索引 205。旁路保留参考幅值 **59.13%**，v2 为 **46.13%**，本轮为 **{diagnosed['enhanced_retention']*100:.2f}%**。这说明额外误压得到缓解，不表示已经恢复全部多比特幅值，也不是实物目标测量。

开发诊断共 {dev['summary']['known_targets']} 个已知合成目标，本轮新增半幅损失 {dev['summary']['new_targets_below_half']} 个；冻结后新留出有 {fresh['summary']['known_targets']} 个已知目标，其中 {fresh['summary']['known_weak_targets']} 个弱目标，新增半幅损失 **{fresh['summary']['new_targets_below_half']}** 个，弱目标幅值误差/旁路 **{fresh['summary']['weak_mae_ratio']:.4f}**。每个失败（若有）均保留在完整报告与看图页面。

新留出为 seed124000–124031 的 32 组合成数据及实测 BIN 的 0-based463/527/591 帧、RX0/RX3 共 6 例。模型冻结后才生成和读取这些输出，没有依据该批结果重新选模型。实测按 chirp 内 RX 块约定解码；是同一采集的时间划分，不称跨场景验证。

## 改了什么

网络仍为 40→32→16→1、每套权重 1857 个参数，±64 两电平量化、补零顺序、全距离 0–1023、Q14 增益和 g² 功率接口均保持原规则。将最终保护层纳入训练，集中约束已知目标/参考局部峰中心，并用冻结 v2 输出约束背景变化。训练输入为原 train 划分加 24 组新配对合成数据，没有把原失败例或新留出用于训练。

无强保持约束的第一轮虽修复弱峰，但使背景和部分实测帧退化，未采用；其记录在 `development_step15000/`。加强背景保持的微调在 `runs/guardaware_p8_d64/`。最后把该微调与原参数按 alpha=0.75 作保守插值，在开发集选择较小改动，冻结到 `runs/conservative_a0.75/model.pt`。alpha=0.5 未修复原半幅失败，alpha=1 的小规模检查对实测整体误差影响更大。

直接把微调同时用于128/512时，`development_final/report.json` 仍为 FAIL：128chirp 的两个实测参考峰新增半幅损失。因此最终把改动限定到实际 radar1 使用的512chirp；128chirp使用原v2权重逐点原样输出。该决策和原失败均保留，最终开发结果见 `development_profiled/report.json`。仅按已有的有效chirp配置选择权重，不使用参考图、目标坐标或样例ID；没有增加空间后处理。这些选择均在读取新留出之前冻结。

独立PC包存两套权重，每帧只运行一套网络，不串联两次。后续radar1固定512chirp的IP只需修正后的单套1857参数；128兼容权重不要求在该固定配置硬件里双份部署。

## 是否保持了背景效果

下表是本轮/原 v2 的比值，小于 1 表示误差降低；整体误差为逐帧归一化幅值 NMSE 的均值比，背景为正误差平方和之比。

| 范围 | 整体误差/原 v2 | 背景误差/原 v2 |
|---|---:|---:|
{chr(10).join(table)}

原质量门槛未改，未通过项为：{failtext}。详见 `fresh_test/report.json`。背景指标为参考幅值<0.003 区域的代理指标，并非有物体标注的误警率；不能为了改善这一指标而把弱目标一起压掉。当前单项任务与整体验收必须分别判断。

## 文件与工程状态

- 权重与独立定点运行代码：`pc_candidate/`。
- 同帧四路图、全部已知目标和失败表：`results/index.html`。
- 最终开发诊断、数值、新留出报告分别为 `development_profiled/report.json`、`NUMERIC_VERIFICATION.json`、`fresh_test/report.json`。最终开发报告引用 `development_final/arrays`，128项的最终输出使用其中 `previous_power/previous_gain`，512项使用 `enhanced/gain`；网页已按此规则处理，不能把原未分模式的失败输出混作最终输出。
- 网络和保护规则没有新算子，参数存储规模不变；相对最初 V7 IP，仍需适配已有的 40 输入、Q16 计算和 g>1 饱和等差异，不能把权重直接复制进已发布 V7 IP。
- 原保守整体验收 FAIL（若仍存在）保持可查；本轮文件不能当作可下载 FPGA 包。下一步是否进入 IP 适配需按整体质量和工程状态分别决定，不把本轮 PC 数值 PASS 当作上板验证。

所有对照是 FFT 后 RD 标量恢复；没有套用不匹配的 AQ/AR 表冒充新采集数据的物理 SAR 聚焦。
'''
    (ROOT/'弱目标修正结果.md').write_text(doc,encoding='utf8')
    operations='''# 使用本轮修正网络

先双击 `results/index.html` 查看同帧四路对照和目标保留率。四路依次为多比特参考、单比特旁路、原 v2、修正 v3；统一 −60 至 0 dB，网络输出共用旁路峰值、不另拉伸。

`pc_candidate` 只需要 Python、NumPy、SciPy，输入是 FFT 后自然顺序的 1024×512 uint64 功率 `.npy`，不是原始 ADC BIN。两份示例分别为此前失败的合成512chirp例和新留出实测128chirp例。

```powershell
Set-Location 'C:\\Users\\yang\\Desktop\\SAR_IMAGE\\scalar_restore_v3'
$sarPython = 'C:\\Users\\yang\\AppData\\Local\\Programs\\Python\\Python313\\python.exe'
New-Item -ItemType Directory -Force .\\user_checks | Out-Null
& $sarPython .\\pc_candidate\\restore_power.py --input .\\examples\\diagnosed_512_power.npy --output .\\user_checks\\diagnosed_512.npz --actual-chirps 512
& $sarPython .\\pc_candidate\\restore_power.py --input .\\examples\\fresh_rx0_0463_power.npy --output .\\user_checks\\fresh_rx0_0463.npz --actual-chirps 128
```

输出 NPZ 有 `power` 和 `gain_q14`。输出已存在会拒绝覆盖，重跑请换输出名字。chirp 参数为补零前有效数量，radar1 板端正常512chirp用512，新实测BIN128chirp用128；不能因FFT都有512列而混用。

512chirp使用修正权重，128chirp自动使用冻结v2权重；不会因补零后的FFT宽度相同而混用。模型已经训练完成，不需你另行训练。训练/全链数据构建脚本 `experiment.py` 依赖此工作区的原有位精确 FFT 与历史配对资料；运行包不是完整训练数据备份，也不含600MiB原ADC BIN、全套配对缓存或可下载BIT。独立网络推理不依赖旧工程或PyTorch。

本轮没有上板步骤。不要运行旧 `program_onebit_network.tcl` 后认为加载了本轮网络；那仍加载旧IP。工程是否可下载以未来独立部署包自身的构建、数值与验证记录为准。
'''
    (ROOT/'操作说明.md').write_text(operations,encoding='utf8');(ROOT/'pc_candidate/README.md').write_text('独立PC弱目标修正模型。请先阅读包内弱目标修正结果.md及操作说明.md；质量与数值状态见config.json。不是FPGA下载包。\n',encoding='utf8')
    examples=ROOT/'examples';examples.mkdir(exist_ok=False)
    import numpy as np
    for source,name in [(ROOT/'development_final/arrays/confirm_synth_116013_512.npz','diagnosed_512'),(ROOT/'fresh_test/arrays/v3_field_rx0_0463.npz','fresh_rx0_0463')]:
        with np.load(source) as d:np.save(examples/(name+'_power.npy'),d['base']);np.savez_compressed(examples/(name+'_expected.npz'),power=d['enhanced'],gain_q14=d['gain'])
    cfg=read(ROOT/'pc_candidate/config.json');write(ROOT/'pc_candidate/manifest.json',dict(weak_correction_status=weak_status,quality_status=fresh['status'],numeric_status=numeric['status'],ready_for_ip_adaptation=cfg['ready_for_ip_adaptation'],files=[dict(path=p.name,sha256=sha(p)) for p in (ROOT/'pc_candidate').iterdir() if p.is_file() and p.name!='manifest.json']))
    standard=dict(python_sources_parse=all(ast.parse(p.read_text(encoding='utf8')) is not None for p in ROOT.glob('*.py')),frozen_checkpoint_hash_matches=sha(frozen['path'])==frozen['sha256'],same_model_in_fresh_test=fresh['model_sha256']==frozen['sha256'],frozen_profile_policy_hash_matches=sha(ROOT/'PROFILE_POLICY.json')==frozen['profile_policy_sha256'],frozen_128_weights_exactly_preserved=sha(ROOT/'pc_candidate/weights_128.npz')==sha(OLD/'research_candidate/weights.npz'),fresh_after_freeze=(ROOT/'FROZEN_MODEL.json').stat().st_mtime<(ROOT/'fresh_test_manifest.json').stat().st_mtime<(ROOT/'fresh_test/report.json').stat().st_mtime,original_v2_failure_preserved=read(OLD/'independent_test_final/report.json')['status']=='FAIL',numeric_pass=numeric['status']=='PASS',published_model_matches_frozen=sha(ROOT/'pc_candidate/model_float.pt')==frozen['sha256'],no_original_test_in_training=read(ROOT/'TRAINING_INPUTS.json')['no_previous_test_in_training'])
    write(ROOT/'STANDARD_CHECK.json',dict(status='PASS' if all(standard.values()) else 'FAIL',checks=standard,weak_correction_status=weak_status,full_quality_status=fresh['status']))
    assert all(standard.values())
    release=ROOT/'release';release.mkdir(exist_ok=True);archive=release/'scalar_restore_v3_pc_weakfix.zip'
    if archive.exists():raise FileExistsError(archive)
    files=[p for folder in ['pc_candidate','results','examples'] for p in (ROOT/folder).rglob('*') if p.is_file()]
    names=['弱目标修正结果.md','操作说明.md','RESULTS.json','BUILD_STATUS.json','NUMERIC_VERIFICATION.json','STANDARD_CHECK.json','TRAINING_GUARD_CHECK.json','DEVELOPMENT_CORRECTION_CHECK.json','FROZEN_MODEL.json','EXPERIMENT_PROTOCOL.json','CORRECTION_ACCEPTANCE.json','PROFILE_POLICY.json','TRAINING_INPUTS.json','weak_diagnosis.json','experiment.py','runtime_template.py','profile_development.py','export_candidate.py','freeze_model.py','make_comparison.py','finalize.py','verify_training_guard.py','development_profiled/report.json','development_final/report.json','fresh_test/report.json','development_manifest.json','fresh_test_manifest.json','runs/guardaware_p8_d64/config.json','runs/guardaware_p8_d64/training_source.py','runs/conservative_a0.75/model.pt','runs/conservative_a0.75/config.json']
    names+=['CONSERVATIVE_PARAMETER_PROBE.json','probe_d64/report.json','probe_05000/report.json','development_step15000/report.json']
    files+=[ROOT/n for n in names];files=sorted(set(files));expected={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in files}
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(p,str(p.relative_to(ROOT)).replace('\\','/'))
    import hashlib
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert all(hashlib.sha256(z.read(n)).hexdigest()==h for n,h in expected.items())
    write(ROOT/'RUNTIME_PACKAGE.json',dict(status='PASS',file=str(archive.relative_to(ROOT)),sha256=sha(archive),bytes=archive.stat().st_size,file_count=len(files),crc_and_payload_sha_readback_pass=True,scope='PC runtime, weights, code, reports, figures, two FFT-power examples; not full training/raw-data backup or FPGA package',files=expected))
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
