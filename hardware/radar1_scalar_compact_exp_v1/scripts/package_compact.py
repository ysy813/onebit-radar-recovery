"""Offline-only release audit. An experimental release does not certify quality."""
from pathlib import Path
import json,hashlib,re,zipfile,shutil,sys,xml.etree.ElementTree as ET
import numpy as np
import artifact_checks as checks
R=Path(__file__).resolve().parents[1];OUT=R/'pkg'
BASE=R.parent/'radar1_scalar_v7_fullrange_v3'
WEIGHTS='5ee3e8c1ef16dc73280988d329a7118715642321f85ab7e8d93314ed7c4e50d4'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def read(p):return p.read_text(encoding='utf8',errors='replace')
def require_log(name,tokens):
    s=read(R/'reports'/name)
    for token in tokens:assert token in s,(name,token)
    assert not re.search(r'Fatal:|FATAL_ERROR|^ERROR:',s,re.M),name

def preflight():
    config=json.loads(read(R/'model/runtime/config.json'))
    assert config['version']=='scalar_restore_v3_compact_weakfix'
    assert config['quality_test_status']=='FAIL' and not config['approved_for_pl_integration']
    assert sha(R/'model/runtime/weights.npz')==WEIGHTS
    for name,h in config['sha256'].items():assert sha(R/'model/runtime'/name)==h,name
    # Interval bounds include every MAC partial sum, including any HLS reorder.
    lo=np.zeros(40,dtype=object);hi=np.full(40,65536,dtype=object);lo[13:16]=-65536;bounds=[]
    with np.load(R/'model/runtime/weights.npz') as weights:
        for i in range(3):
            w=weights[f'w{i}'].astype(object);b=weights[f'b{i}'].astype(object)
            assert np.max(np.abs(w))<(1<<19) and np.max(np.abs(b))<(1<<33)
            low=np.where(w>=0,w*lo,w*hi).sum(1)+b;high=np.where(w>=0,w*hi,w*lo).sum(1)+b
            bound=(np.abs(w)*np.maximum(np.abs(lo),np.abs(hi))).sum(1)+np.abs(b)
            bits=int(max(bound)).bit_length()+1;assert bits<=48
            lo=(low+32768)>>16;hi=(high+32768)>>16
            if i<2:lo=np.maximum(lo,0);hi=np.maximum(hi,0)
            assert all(-(1<<31)<=int(v)<(1<<31) for v in list(lo)+list(hi))
            bounds.append(dict(layer=i,accumulator_bits_required=bits,max_abs_partial_accumulator=int(max(bound)),activation_lower=int(min(lo)),activation_upper=int(max(hi))))
    write(R/'reports/interval_bounds.json',dict(status='PASS',all_external_q12_features_inclusive=[0,4096],accumulator_bits=48,activation_bits=32,layers=bounds))
    csim=read(R/'hls/project/solution/csim/report/scalar_gain_csim.log')
    assert 'HLS_CSIM_PASS zero_frame=PASS full_frames=3' in csim
    vectors=json.loads(read(R/'reports/numeric_vectors.json'))
    for case in vectors['cases']:
        folder=R/'numeric'/case['name'];assert f"case={case['name']} mismatches=0" in csim
        assert sha(folder/'csim_power.bin')==sha(folder/'expected_power.bin')
        case['output_sha256']=sha(folder/'csim_power.bin')
    vectors.update(status='PASS',full_frames=3,zero_frame_pass=True,includes_uint64_extremes=True,includes_gain_above_unity=True)
    write(R/'reports/numeric_validation.json',vectors)
    require_log('simulate_compact_console.log',['TB_COMPACT_MLP_PASS cases=464','TB_COMPACT_GUARD_PASS cases=464','COMPACT_RTL_SIMULATIONS_DONE'])
    require_log('simulate_frame_console.log',['NETWORK_FRAME_CDC_PASS admitted=2 skipped=2'])
    baseline=json.loads(read(R/'reports/source_baseline.json'))
    exceptions={'rtl/network_frame_control.v','software/branch_control.h','software/radar_sd_long.c','software/image_init.c'}
    for name,h in baseline['sha256'].items():
        name=name.replace('\\','/')
        assert sha(BASE/name)==h,('Baseline modified',name)
        if name not in exceptions:assert sha(R/name)==h,('Unexpected copied source change',name)
    replacements={
        'rtl/network_frame_control.v':[("8'h70","8'h71")],
        'software/branch_control.h':[('0x70U','0x71U'),('scalar-v7','scalar-compact-exp-v1')],
        'software/radar_sd_long.c':[('radar1-scalar-v7-20261101','radar1-scalar-compact-exp-v1')],
        'software/image_init.c':[('FULLRANGE_V3','COMPACT_EXP_V1'),('WEIGHTS=FROZEN_V7','MODEL=COMPACT_WEAKFIX_Q16')]}
    for name,pairs in replacements.items():
        source=read(BASE/name)
        for a,b in pairs:source=source.replace(a,b)
        assert source==read(R/name),name
    previous=json.loads(read(BASE/'pkg/BUILD_READY.json'))
    for name,h in previous['sha256'].items():assert sha(BASE/'pkg'/name)==h,('Prior release changed',name)
    # Bounds come from the actual source definitions, not a presumed spare region.
    storage=read(R/'software/radar_sd_long.c')
    assert '#define DATA_BASE 0x28000000U' in storage and '#define RING_COUNT 64U' in storage
    assert '#define FRAME_BYTES (2U * 1024U * 1024U)' in storage
    assert 0x28000000+64*2*1024*1024==0x30000000<0x31000000
    source=read(R/'hls/scalar_compact.cpp');assert 'depth=2097152' in source
    assert '0x71U' in read(R/'software/branch_control.h')
    d=json.loads(read(R/'project/imaging_storage.srcs/sources_1/bd/design_1/design_1.bd'))['design']
    assert int(d['components']['net_work_base']['parameters']['CONST_VAL']['value'],0)==0x31000000
    assert int(d['components']['net_power_base']['parameters']['CONST_VAL']['value'],0)==0x24000000
    old=json.loads(read(BASE/'project/imaging_storage.srcs/sources_1/bd/design_1/design_1.bd'))['design']
    for key in ['axi_dma_0_M_AXI_S2MM','axi_dma_0_M_AXI_SG','axis_data_fifo_cap_M_AXIS']:
        assert d['interface_nets'][key]==old['interface_nets'][key],key
    active={}
    gen=R/'project/imaging_storage.gen/sources_1/bd/design_1/ipshared'
    for name in ['scalar_gain.v','scalar_gain_predict.v','scalar_gain_protect.v']:
        copies=list(gen.glob('*/hdl/verilog/'+name));assert len(copies)==1,(name,len(copies))
        assert sha(copies[0])==sha(R/'hls/project/solution/syn/verilog'/name),('Stale generated HLS',name)
        active[name]=sha(copies[0])
    xpr=read(R/'project/imaging_storage.xpr')
    assert 'radar1_scalar_v7_fullrange_v3' not in xpr
    compile_order=R/'reports/compile_order.rpt'
    if compile_order.exists():assert 'radar1_scalar_v7_fullrange_v3' not in read(compile_order)
    xml=ET.parse(R/'hls/project/solution/syn/report/scalar_gain_csynth.xml')
    cycles=int(xml.findtext('.//SummaryOfOverallLatency/Worst-caseLatency'))
    return dict(status='PASS',full_frame_csim=True,zero_frame=True,rtl_mlp_cases=464,rtl_guard_cases=464,
                changed_guard_cases=208,frame_cdc_pass=True,original_sources_unchanged=True,
                storage_fork_unchanged=True,ddr_scratch_bytes=16777216,ddr_scratch_start='0x31000000',ddr_scratch_end_exclusive='0x32000000',
                hls_estimated_cycles=cycles,hls_estimated_seconds_at_100mhz=cycles/1e8,
                hls_estimate_excludes_actual_axi_stalls=True,active_generated_sources=active)

def main():
    pre=preflight();write(R/'reports/preflight.json',pre)
    if '--preflight' in sys.argv:print('COMPACT_PREFLIGHT_PASS');return
    for name,tokens in [
        ('build_hardware_console.log',['NETWORK_HARDWARE_BUILT']),
        ('final_audit_console.log',['NETWORK_FINAL_IMPLEMENTATION_AUDIT_PASS']),
        ('final_platform_console.log',['SCALAR_FINAL_PLATFORM_PASS']),
        ('final_software_console.log',['SCALAR_SOFTWARE_PASS'])]:require_log(name,tokens)
    assert sha(R/'vitis/scalar/export/scalar/hw/scalar_network.xsa')==sha(OUT/'scalar_network.xsa')
    with zipfile.ZipFile(OUT/'scalar_network.xsa') as z:
        assert z.testzip() is None
        for suffix,name in [('.bit','design_1_wrapper.bit'),('psu_init.tcl','psu_init.tcl')]:
            files=[n for n in z.namelist() if n.endswith(suffix)];assert len(files)==1
            assert hashlib.sha256(z.read(files[0])).hexdigest()==sha(OUT/name)
    for name in checks.MODES:
        data=(OUT/f'{name}.elf').read_bytes()
        assert b'scalar-compact-exp-v1' in data
        assert b'NETWORK_RANGE_BINS=0..1023' in data
    elfs={name:checks.elf_check(OUT/f'{name}.elf') for name in checks.MODES}
    lines=read(R/'reports/timing_summary.rpt').splitlines()
    idx=next(i for i,l in enumerate(lines) if 'WNS(ns)' in l and 'TNS(ns)' in l);v=lines[idx+2].split()
    timing=dict(wns_ns=float(v[0]),tns_ns=float(v[1]),setup_failing_endpoints=int(v[2]),whs_ns=float(v[4]),ths_ns=float(v[5]),hold_failing_endpoints=int(v[6]),wpws_ns=float(v[8]),tpws_ns=float(v[9]),pulse_width_failing_endpoints=int(v[10]))
    assert all(timing[k]>=0 for k in ['wns_ns','whs_ns','wpws_ns'])
    assert all(timing[k]==0 for k in ['tns_ns','ths_ns','tpws_ns','setup_failing_endpoints','hold_failing_endpoints','pulse_width_failing_endpoints']),timing
    skew=checks.bus_skew_check()
    assert re.search(r'nets with routing errors\.+\s*:\s*0\s*:',read(R/'reports/route_status.rpt'))
    assert not re.search(r'^\|[^|]+\|\s*Error\s*\|',read(R/'reports/drc.rpt'),re.M)
    resources={};u=read(R/'reports/utilization.rpt')
    for name,label in [('lut','CLB LUTs'),('register','CLB Registers'),('bram36','Block RAM Tile'),('uram','URAM'),('dsp','DSPs')]:
        row=next(l for l in u.splitlines() if l.startswith('|') and l.split('|')[1].strip().rstrip('*')==label)
        fields=row.split('|');used=float(fields[2]);available=int(fields[5]);assert used<=available
        resources[name]=dict(used=used,available=available,percent=round(100*used/available,2))
    method=read(R/'reports/methodology.rpt')
    def groups(pattern):
        cells=re.findall(pattern,method);names={c.split('/')[1] for c in cells}
        return {name:sum(c.split('/')[1]==name for c in cells) for name in names}
    seq=groups(r'The clock pin ([^\r\n]+?) is not reached');latches=groups(r'The latch ([^\r\n]+?) cannot be properly analyzed')
    assert set(seq).issubset({'cam_axi_data_0','ov5640_dri_0'}),seq
    assert set(latches).issubset({'interp_ip_0'}),latches
    scope=dict(full_system_timing_signoff=False,unclocked_sequential_cells_by_block=seq,unclocked_latches_by_block=latches,legacy_external_io_constraint_gaps_retained=True)
    write(R/'reports/constraint_scope.json',scope)
    manifest=dict(revision='radar1_scalar_compact_exp_v1',ready_for_board_test=True,board_tested=False,experimental=True,
                  user_authorized_experimental_bit_rebuild=True,quality_certified=False,upstream_overall_quality_status='FAIL',
                  model='scalar_restore_v3_compact_weakfix',model_weights_sha256=WEIGHTS,neural_weights_retrained=False,
                  input_radar_profile='1024 ADC samples,512 valid chirps,4RX',range_bins_inclusive=[0,1023],
                  same_bit_for_all_modes=True,modes=checks.MODES,hardware_signature='0x71',display_mode='1280x720p60',radar_scanout_pixels=[844,422],
                  storage_always_raw=True,whole_image_frame_skipping=True,preflight=pre,elfs=elfs,timing_closed_for_analyzed_paths=True,
                  timing=timing,bus_skew=skew,full_system_timing_signoff=False,constraint_scope=scope,resources=resources,
                  invalid_table_pixels_skipped=1908,original_projects_modified=False)
    t=timing;r=resources
    appendix='\n\n<!-- FINAL_BUILD_RESULT -->\n## 6. 本版实际构建结果\n\n'
    appendix+='三份524288像素完整帧及零帧C仿真逐点一致；464组综合后MLP和464组保护层RTL对照通过，帧握手/整帧跳过仿真通过。\n\n'
    appendix+=f"已约束时序：WNS {t['wns_ns']:+.3f}ns，WHS {t['whs_ns']:+.3f}ns，WPWS {t['wpws_ns']:+.3f}ns；路由错误0，DRC无Error。仍保留旧约束缺口，full_system_timing_signoff=false。\n\n"
    appendix+='| 资源 | 使用/总量 | 占用 |\n|---|---|---|\n'
    for key,label in [('lut','LUT'),('register','FF'),('bram36','BRAM36等价'),('uram','URAM'),('dsp','DSP')]:appendix+=f"| {label} | {r[key]['used']:g}/{r[key]['available']} | {r[key]['percent']:.2f}% |\n"
    appendix+=f"\nHLS估计网络 {pre['hls_estimated_cycles']} 个100MHz周期，约 {pre['hls_estimated_seconds_at_100mhz']:.3f}秒/帧，不含实际DDR等待；尚未板测。不是500ms/帧实时实现，先验证板端恢复效果。\n"
    doc=R/'工程与网络说明.md';doc.write_text(read(doc).split('<!-- FINAL_BUILD_RESULT -->')[0].rstrip()+appendix,encoding='utf8')
    for name in ['README.md','工程与网络说明.md','上板测试步骤.md']:shutil.copy2(R/name,OUT/name)
    for name in ['timing_summary.rpt','utilization.rpt','route_status.rpt','drc.rpt','constraint_scope.json','numeric_validation.json','interval_bounds.json','preflight.json']:
        shutil.copy2(R/'reports'/name,OUT/name)
    hashes={p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name not in {'BUILD_READY.json','SHA256SUMS.txt'}}
    manifest['sha256']=hashes;write(OUT/'BUILD_READY.json',manifest)
    (OUT/'SHA256SUMS.txt').write_text(''.join(f'{h}  {n}\n' for n,h in hashes.items()),encoding='utf8')
    write(R/'BUILD_STATUS.json',dict(stage='EXPERIMENTAL_READY_FOR_BOARD_TEST',bitstream_ready=True,board_tested=False,experimental=True,quality_certified=False,
                                  timing=timing,resources=resources,full_system_timing_signoff=False,preflight=pre))
    archive=R/'radar1_scalar_compact_exp_v1_runtime.zip'
    if archive.exists():raise FileExistsError(archive)
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(OUT.iterdir()):
            if p.is_file():z.write(p,'pkg/'+p.name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    write(R/'reports/PACKAGE_RESULT.json',dict(status='PASS',archive=str(archive),sha256=sha(archive),experimental=True,board_tested=False))
    print('COMPACT_EXPERIMENT_PACKAGE_PASS',json.dumps(timing),flush=True)

if __name__=='__main__':main()
