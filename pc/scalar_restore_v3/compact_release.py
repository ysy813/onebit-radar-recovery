"""Export/verify the minimal correction, then write its reviewable delivery."""
from experiment import *
from compact_guard import compact_peak_skip
import shutil,importlib.util,subprocess,os,zipfile,ast,html

def export_verify():
    test=read(ROOT/'compact_fresh_test/report.json');frozen=read(ROOT/'COMPACT_FROZEN.json')
    assert sha(ROOT/'compact_guard.py')==frozen['guard_sha256']
    folder=ROOT/'pc_candidate_compact';folder.mkdir(exist_ok=False)
    for source,dest in [(OLD/'research_candidate/weights.npz','weights.npz'),(OLD/'research_candidate/root5.npy','root5.npy'),(OLD/'runs/soft_patch5/step_30000.pt','model_float.pt'),(OLD/'model.py','model_source.py'),(OLD/'scalar_guard.py','scalar_guard.py'),(ROOT/'compact_guard.py','compact_guard.py'),(ROOT/'compact_runtime_template.py','restore_power.py')]:shutil.copy2(source,folder/dest)
    config=read(OLD/'research_candidate/config.json');config.update(version='scalar_restore_v3_compact_weakfix',quality_test_status=test['status'],weak_correction_status=test['correction_status'],approved_for_pl_integration=False,ready_for_board_test=False,research_only=test['status']!='PASS',neural_weights_changed=False,stored_parameter_sets=1,compact_peak_policy=read(ROOT/'COMPACT_POLICY.json'),sha256={p:sha(folder/p) for p in ['weights.npz','root5.npy','model_float.pt','compact_guard.py','scalar_guard.py']},selection_report='../COMPACT_FROZEN.json',independent_test_report='../compact_fresh_test/report.json')
    write(folder/'config.json',config)
    spec=importlib.util.spec_from_file_location('compact_standalone',folder/'restore_power.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);runtime=module.PowerRestorer(folder)
    net,ck=load_net(OLD/'runs/soft_patch5/step_30000.pt');fixed=IntegerCorrector(net);records=dev_records();records+=[r for r in read(ROOT/'fresh_test_manifest.json')['records'] if r['id']=='v3_synth_124017_512'];rows=[]
    names={'historical_0024','historical_0036','field_rx_blocks_per_chirp_rx0_0351','confirm_synth_116013_512','v3_synth_124017_512'}
    for r in records:
        if r['id'] not in names:continue
        ref,p,f=pair(r);ff=features_for_policy(f,'guarded_child',2);n=r['actual_chirps'];g0=apply_guard(p,fixed.predict(ff),ck['config']['power_guard'],ff,n);expected=compact_peak_skip(p,g0,ff,n);out,g=runtime.restore(p,True,n)
        values=[]
        for s in range(0,p.size,32768):
            with torch.no_grad():values.append(net.gain(torch.from_numpy(ff[:,s:s+32768].T.astype('f4')/4096)).numpy().ravel())
        gf=apply_guard(p,np.concatenate(values).reshape(p.shape)*16384,ck['config']['power_guard'],ff,n);gf=compact_peak_skip(p,gf,ff,n)/16384;diff=np.abs(gf-g.astype('f8')/16384)
        rows.append(dict(id=r['id'],features_exact=bool(np.array_equal(ff,runtime.features(p))),gain_exact=bool(np.array_equal(g,expected)),power_exact=bool(np.array_equal(out,apply_power(p,expected))),float_fixed_gain_mae=float(diff.mean()),float_fixed_gain_max=float(diff.max()),no_power_decrease_relative_v2=bool(np.all(g>=g0))))
        print('COMPACT_NUMERIC',rows[-1],flush=True)
    p=np.zeros((17,13),dtype='u8');p[0,0]=2**64-1;p[8,7]=(2**64-1)//32
    f=np.zeros((8,p.size),dtype='u2');q=8*13+7;f[0,q]=2000;f[3,q]=1000
    arithmetic=True
    for value in [2048,4096,7000,8192,11000,16384,24576]:
        gg=np.full(p.shape,value,dtype='u2');actual=compact_peak_skip(p,gg,f,512);expected=gg.copy()
        conf=min(max(value-4096,0),4096);score=4096;weight=(score*conf+2048)//4096;lift=(max(16384-value,0)*weight+2048)//4096
        expected[8,7]=value+lift
        arithmetic&=np.array_equal(actual,expected) and np.array_equal(compact_peak_skip(p,gg,f,128),gg)
    z=np.zeros((1024,512),dtype='u8');zo,zg=runtime.restore(z,True)
    pv=np.array([0,1,17,2**32,2**63,2**64-1],dtype='u8');gv=np.array([2048,8192,16384,20000,24576,24576],dtype='u2');ex=[min(2**64-1,(int(p)*int(g)**2+2**27)>>28) for p,g in zip(pv,gv)]
    checks=dict(standalone_exact=all(r['features_exact'] and r['gain_exact'] and r['power_exact'] for r in rows),float_fixed_mae_at_most0p0003=all(r['float_fixed_gain_mae']<=.0003 for r in rows),float_fixed_max_at_most0p01=all(r['float_fixed_gain_max']<=.01 for r in rows),new_guard_never_reduces_v2_gain=all(r['no_power_decrease_relative_v2'] for r in rows),u64_guard_arithmetic_exact=bool(arithmetic),u64_saturation_exact=runtime.apply_power(pv,gv).tolist()==ex,zero_frame_exact=not zo.any() and bool((zg==16384).all()),original_neural_weights_exactly_preserved=sha(folder/'weights.npz')==frozen['weights_sha256'],original_q16_integer_bounds_still_apply=read(OLD/'NUMERIC_VERIFICATION_RESEARCH.json')['checks']['accumulators_fit_signed48'])
    smoke=ROOT/'compact_runtime_smoke';smoke.mkdir(exist_ok=False);env=os.environ.copy();env['PYTHONPATH']='';cli=[]
    for name,n in [('compact_synth_128001_512',512),('compact_field_rx0_0455',128)]:
        with np.load(ROOT/'compact_fresh_test/arrays'/(name+'.npz')) as d:power=d['base'];expected_power=d['enhanced'];expected_gain=d['gain']
        ip=smoke/(name+'.npy');op=smoke/(name+'.npz');np.save(ip,power)
        r=subprocess.run([sys.executable,str(folder/'restore_power.py'),'--input',str(ip),'--output',str(op),'--actual-chirps',str(n)],cwd=smoke,env=env,capture_output=True,text=True,timeout=120)
        assert r.returncode==0,r.stdout+r.stderr
        with np.load(op) as d:exact=bool(np.array_equal(d['power'],expected_power) and np.array_equal(d['gain_q14'],expected_gain))
        cli.append(dict(id=name,exact=exact,stdout=r.stdout.strip()))
    checks['isolated_cli_exact']=all(r['exact'] for r in cli)
    checks['original_raw_capture_preserved']=sha(ROOT.parent/'radar1_v7_offline_compare_v1/data/radar_raw.bin')=='b3fb208fcbe335619fee2e32c5e9073548f5502c8c2cd7c823e936bf29cb1015'
    result=dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,rows=rows,isolated_cli=cli,full_quality=test['status'],weak_correction=test['correction_status'],scope='PC numeric only; no IP/BIT/board verification')
    write(ROOT/'NUMERIC_VERIFICATION_COMPACT.json',result)
    assert all(checks.values())
    print('COMPACT_NUMERIC_PASS',checks,flush=True)

def finalize():
    dev=read(ROOT/'compact_development/report.json');test=read(ROOT/'compact_fresh_test/report.json');numeric=read(ROOT/'NUMERIC_VERIFICATION_COMPACT.json');frozen=read(ROOT/'COMPACT_FROZEN.json')
    diagnosed=[]
    for name in ['confirm_synth_116013_512','v3_synth_124017_512']:
        row=next(r for r in dev['rows'] if r['id']==name);t=next(t for t in row['targets'] if t['measured_peak_bin']==[221,205]);old=next(t for t in row['previous_v2']['targets'] if t['measured_peak_bin']==[221,205]);diagnosed.append(dict(id=name,baseline=t['baseline_retention'],previous=old['enhanced_retention'],corrected=t['enhanced_retention']))
    result=dict(weak_correction_status=test['correction_status'],full_original_quality_status=test['status'],numeric_status=numeric['status'],diagnosed_targets=diagnosed,development_known_targets=dev['summary']['known_targets'],development_new_half_losses=dev['summary']['new_targets_below_half'],fresh_known_targets=test['summary']['known_targets'],fresh_known_weak_targets=test['summary']['known_weak_targets'],fresh_new_half_losses=test['summary']['new_targets_below_half'],fresh_weak_mae_ratio_to_bypass=test['summary']['weak_mae_ratio'],fresh_v2_nonregression=test['summary']['v2_nonregression'],failed_original_quality_checks=[k for k,v in test['summary']['checks'].items() if not v],neural_weights_changed=False,parameters=1857,active_model='pc_candidate_compact',active_comparison='results_compact/index.html',ip_built=False,bit_rebuilt=False,board_accessed=False)
    write(ROOT/'RESULTS_COMPACT.json',result);write(ROOT/'BUILD_STATUS.json',dict(stage='PC_COMPACT_WEAKFIX_'+test['correction_status'],weak_correction=test['correction_status'],full_original_quality=test['status'],numeric=numeric['status'],active_model='pc_candidate_compact',active_comparison='results_compact/index.html',ready_for_board_test=False,ip_built=False,bit_rebuilt=False,board_tested=False,failed_original_quality_checks=result['failed_original_quality_checks']))
    lines=[]
    for label,rep in [('开发诊断',dev),('新留出',test)]:
        for group,v in rep['summary']['v2_nonregression'].items():lines.append(f'| {label}/{group} | {v["nmse_relative_to_v2"]:.4f} | {v["background_error_relative_to_v2"]:.4f} |')
    peaks='\n'.join(f'| {d["id"]} | {d["baseline"]*100:.2f}% | {d["previous"]*100:.2f}% | {d["corrected"]*100:.2f}% |' for d in diagnosed)
    failed='、'.join(result['failed_original_quality_checks']) or '无'
    doc=f'''# 弱目标误压修正结果

本轮最终候选的弱目标修正检查 **{test['correction_status']}**，数值及独立运行检查 **{numeric['status']}**；原整体验收门槛 **{test['status']}**。原质量FAIL记录和所有本轮失败保留，单项PASS不替代整体PASS。本轮未设计新IP、未重建BIT/ELF、未操作板卡。

最终网络是 **原v2冻结神经权重 + 新的紧凑弱峰保护层**，不是重新训练成功的一套新权重。运行入口 `pc_candidate_compact/`，看图为 `results_compact/index.html`。其它训练、profiled和fresh_test目录是过程记录。

## 原误压点修正

两个已知合成弱目标的参考峰都落在自然距离索引221、Doppler索引205，回波相位与背景不同；程序没有硬编码这些坐标。

| 诊断例 | 旁路保留率 | 原v2保留率 | 最终候选保留率 |
|---|---:|---:|---:|
{peaks}

保留率以同源多比特参考幅值为1。最终候选在这些峰处恢复到旁路幅值，消除了这两例的额外衰减；旁路本来已丢失的幅值没有全部补回来。这不是实物目标测量。

开发诊断有 {dev['summary']['known_targets']} 个已知目标，新增半幅损失 {dev['summary']['new_targets_below_half']} 个。冻结规则后新留出共 {test['summary']['known_targets']} 个已知目标、其中 {test['summary']['known_weak_targets']} 个弱目标，新增半幅损失 **{test['summary']['new_targets_below_half']}** 个；弱目标平均幅值误差/旁路 **{test['summary']['weak_mae_ratio']:.4f}**。旁路低于参考半幅的目标有 {test['summary']['baseline_targets_below_half']} 个，最终候选仍有 {test['summary']['enhanced_targets_below_half']} 个，不能宣称全部目标恢复。失败（若有）全部保留。

新的最终留出是seed128000–128015、0-based455/519/583帧的RX0/RX3。上一次seed124000–124031测试仍有1例误压，原报告 `fresh_test/report.json` 保持FAIL；改规则后它只作为开发诊断，不再称新盲测。最终测试只读一次，未据结果再挑模型。实测采用chirp内RX块约定，是同一采集的时段划分，不称跨场景真实目标验收。

## 修正方法与代价

原网络的回归增益会在少数集中的弱峰处形成孤立凹陷，软保护仍保留部分衰减。新层仅在512有效chirp模式下，对输入9×9局部极大、幅值不低于帧峰约−40dB、功率不高于帧峰1/16、且不符合强三/五次谐波关系的点检查紧凑性。紧凑性使用现有Q12第五根幅值特征与9×9均值之比，从1.4至1.6连续变化；这不是标定后的SNR或目标分类概率。

对该紧凑峰，再按原最终幅值增益0.25–0.5作连续置信过渡，最多抬到unity，不额外放大。区域外逐点维持原v2输出。128有效chirp路径完全维持原v2。规则不读取参考图、目标标签、固定距离或Doppler列；也不无条件保留所有局部峰。它仍可能保留部分伪峰，因此背景和总恢复误差同时评估。

只有一套40→32→16→1网络、1857参数、1808 MAC/像素；神经权重和Q16数值原样保留。新增层复用已有均值特征、局部最大值与谐波判别，仅增加比较和有界整数乘加；无第二次神经推理。当前只是PC数值实现，没有据此给出PL周期或资源保证。部署时需实现这层规则，不能只复制权重。

## 背景与整体误差

下表本轮/原v2之比，越低越好；整体误差是逐帧归一化幅值NMSE均值比，背景是参考幅值<0.003区域内的正误差平方和之比。

| 范围 | 整体误差/原v2 | 背景误差/原v2 |
|---|---:|---:|
{chr(10).join(lines)}

原整体验收未通过项：{failed}。原V7背景1.10门槛没有改动；即使本轮针对性修正通过，也不能把该FAIL隐去或改成PASS。参考/旁路各按自己的帧峰归一化，网络输出沿用旁路标尺，结果不代表绝对功率恢复。

## 未采用的微调

本轮确实训练了两轮，并把最终保护层纳入损失。无强保持约束的一轮改善弱峰却使背景退步；加入背景蒸馏并做alpha=0.75参数插值后，开发集通过，但seed124000新留出仍有1例只保留48.80%。跨128/512使用微调还新增两个实测数值峰损失。结果保留于 `development_step15000/`、`development_final/`、`development_profiled/`、`fresh_test/`；这些不是最终交付。最后采用更小的保护层修正，保留原网络主体。

## 工程状态

算法对照只验证FFT后RD标量恢复，不负责量化前采集或SAR插值。严格I/Q±64、零值取+64、量化后补零、0–1023全距离、uint64功率和Q14增益/g²接口均保持原约定。相对已经发布的最初V7 IP，仍须适配v2已有的40输入、Q16、g>1等差异并加入本层；现在没有可下载的新BIT。模型代码、标准检查和运行包说明见 `操作说明.md`、`STANDARD_CHECK_COMPACT.json`、`RUNTIME_PACKAGE_COMPACT.json`。
'''
    (ROOT/'弱目标修正结果.md').write_text(doc,encoding='utf8')
    operations='''# 操作说明

先双击 `results_compact/index.html` 查看四路对照：多比特参考、单比特旁路、原v2、最终修正候选。统一−60至0dB；输出不独立拉伸。页面有原误压例、最终留出示例与所有已知目标数值。

当前模型在 `pc_candidate_compact/`，只需Python、NumPy、SciPy；无需重新训练，推理不依赖PyTorch或旧工程。输入是FFT后自然顺序1024×512的uint64功率.npy，不是原始ADC BIN。

```powershell
Set-Location 'C:\\Users\\yang\\Desktop\\SAR_IMAGE\\scalar_restore_v3'
$sarPython = 'C:\\Users\\yang\\AppData\\Local\\Programs\\Python\\Python313\\python.exe'
New-Item -ItemType Directory -Force .\\user_checks | Out-Null
& $sarPython .\\pc_candidate_compact\\restore_power.py --input .\\examples_compact\\diagnosed_512_power.npy --output .\\user_checks\\diagnosed_512.npz --actual-chirps 512
& $sarPython .\\pc_candidate_compact\\restore_power.py --input .\\examples_compact\\fresh128_power.npy --output .\\user_checks\\fresh128.npz --actual-chirps 128
```

输出NPZ有power和gain_q14，已存在的输出会拒绝覆盖，重跑请换名字。512是补零前有效chirp数；新实测BIN只有128有效chirp，此时参数用128，最终保护层保持原输出。相同512列FFT不代表相同有效chirp数。

不能把原program_onebit_network.tcl当成本轮下载脚本：它仍加载旧IP。本轮只交付PC修正模型及验证，没有新的BIT/ELF，也没有操作板卡。训练试验和完整FFT数据重建代码依赖本工作区，运行ZIP不含600MiB原始BIN或全部训练缓存，不是完整数据备份。
'''
    (ROOT/'操作说明.md').write_text(operations,encoding='utf8')
    (ROOT/'pc_candidate_compact/README.md').write_text('原v2标量网络+512chirp紧凑弱峰保护。神经权重未改，128chirp保持原样。先读上级弱目标修正结果.md和操作说明.md。不是FPGA下载包。\n',encoding='utf8')
    ex=ROOT/'examples_compact';ex.mkdir(exist_ok=False)
    for source,name in [(ROOT/'compact_development/arrays/confirm_synth_116013_512.npz','diagnosed_512'),(ROOT/'compact_fresh_test/arrays/compact_field_rx0_0455.npz','fresh128')]:
        with np.load(source) as d:np.save(ex/(name+'_power.npy'),d['base']);np.savez_compressed(ex/(name+'_expected.npz'),power=d['enhanced'],gain_q14=d['gain'])
    std=dict(local_python_syntax=all(ast.parse(p.read_text(encoding='utf8')) is not None for p in ROOT.glob('*.py')),frozen_guard_hash_matches=sha(ROOT/'compact_guard.py')==frozen['guard_sha256'],original_neural_weights_exact=sha(ROOT/'pc_candidate_compact/weights.npz')==frozen['weights_sha256'],numeric_pass=numeric['status']=='PASS',final_test_generated_after_freeze=(ROOT/'COMPACT_FROZEN.json').stat().st_mtime<(ROOT/'compact_test_manifest.json').stat().st_mtime<(ROOT/'compact_fresh_test/report.json').stat().st_mtime,first_fresh_failure_preserved=read(ROOT/'fresh_test/report.json')['status']=='FAIL',old_v2_failure_preserved=read(OLD/'independent_test_final/report.json')['status']=='FAIL',reports_written=(ROOT/'results_compact/index.html').exists())
    write(ROOT/'STANDARD_CHECK_COMPACT.json',dict(status='PASS' if all(std.values()) else 'FAIL',checks=std,weak_correction=test['correction_status'],original_full_quality=test['status']));assert all(std.values())
    model=ROOT/'pc_candidate_compact';write(model/'manifest.json',dict(weak_correction=test['correction_status'],full_quality=test['status'],numeric=numeric['status'],files=[dict(path=p.name,sha256=sha(p)) for p in model.iterdir() if p.is_file() and p.name!='manifest.json']))
    files=[p for d in ['pc_candidate_compact','results_compact','examples_compact'] for p in (ROOT/d).rglob('*') if p.is_file()]
    names=['弱目标修正结果.md','操作说明.md','RESULTS_COMPACT.json','BUILD_STATUS.json','STANDARD_CHECK_COMPACT.json','NUMERIC_VERIFICATION_COMPACT.json','COMPACT_POLICY.json','COMPACT_FROZEN.json','COMPACT_TEST_PROTOCOL.json','compact_test_manifest.json','compact_development/report.json','compact_fresh_test/report.json','fresh_test/report.json','development_final/report.json','development_step15000/report.json','compact_guard.py','compact_runtime_template.py','compact_experiment.py','compact_release.py','experiment.py','make_comparison.py','EXPERIMENT_PROTOCOL.json','CORRECTION_ACCEPTANCE.json','TRAINING_INPUTS.json','weak_diagnosis.json']
    files += [ROOT/n for n in names];files=sorted(set(files));hashes={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in files}
    release=ROOT/'release';release.mkdir(exist_ok=True);archive=release/'scalar_restore_v3_compact_weakfix.zip'
    if archive.exists():raise FileExistsError(archive)
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(p,str(p.relative_to(ROOT)).replace('\\','/'))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None;assert all(hashlib.sha256(z.read(n)).hexdigest()==h for n,h in hashes.items())
    write(ROOT/'RUNTIME_PACKAGE_COMPACT.json',dict(status='PASS',file=str(archive.relative_to(ROOT)),bytes=archive.stat().st_size,sha256=sha(archive),files=hashes,file_count=len(files),crc_and_sha_readback=True,scope='PC runtime, frozen weights, guard correction, code, reports, pictures, two FFT-power examples; no raw ADC/training-cache/FPGA package'))
    print('COMPACT_DELIVERY',json.dumps(result,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':
    torch.set_num_threads(2);ap=argparse.ArgumentParser();ap.add_argument('action',choices=['verify','finalize']);a=ap.parse_args();{'verify':export_verify,'finalize':finalize}[a.action]()
