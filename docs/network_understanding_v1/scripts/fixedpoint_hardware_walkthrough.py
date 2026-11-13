"""Read-only teaching audit: frozen HLS constants, integer traces and BD nets.

Does not compile HLS, run full-frame inference, alter a project or access hardware.
"""
import sys
sys.dont_write_bytecode = True
import ast
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import numpy as np
import torch

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
HW = ROOT / "radar1_scalar_compact_exp_v1"
MODEL = ROOT / "scalar_restore_v3/pc_candidate_compact"

def read(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

header = (HW / "hls/parameters.h").read_text(encoding="utf-8")

def constant(name):
    m = re.search(r"\b" + re.escape(name) + r"(?:\[[^\]]*\])*\s*=\s*(.*?);", header, re.S)
    if not m:
        raise ValueError(name)
    return np.asarray(ast.literal_eval(m[1].replace("{", "[").replace("}", "]")), dtype="i8")

params = {k: constant(k) for k in ["W0","B0","W1","B1","W2","B2","GAIN","ROOT5"]}
assert int(params["ROOT5"].min())==0 and int(params["ROOT5"].max())==4096
assert int(params["GAIN"].min())==2048 and int(params["GAIN"].max())==24576
with np.load(MODEL / "weights.npz", allow_pickle=False) as data:
    matches = {}
    for i in range(3):
        matches[f"W{i}"] = np.array_equal(params[f"W{i}"].ravel(), data[f"w{i}"].ravel())
        matches[f"B{i}"] = np.array_equal(params[f"B{i}"].ravel(), data[f"b{i}"].ravel())
    matches["GAIN"] = np.array_equal(params["GAIN"], data["gain_lut"])
matches["ROOT5"] = np.array_equal(params["ROOT5"], np.load(MODEL / "root5.npy", allow_pickle=False))
assert all(matches.values())
ck=torch.load(MODEL/"model_float.pt",map_location="cpu",weights_only=True)
float_export_matches={}
for i,j in enumerate([0,2,4]):
    w=np.rint(ck["state"][f"layers.{j}.weight"].numpy().astype("f8")*65536).astype("i8")
    b=np.rint(ck["state"][f"layers.{j}.bias"].numpy().astype("f8")*(1<<32)).astype("i8")
    float_export_matches[f"W{i}"]=np.array_equal(params[f"W{i}"].ravel(),w.ravel())
    float_export_matches[f"B{i}"]=np.array_equal(params[f"B{i}"].ravel(),b.ravel())
assert all(float_export_matches.values())

trace = read(HERE / "reports/POINT_TRACE.json")
features = read(HERE / "reports/FEATURE_WALKTHROUGH.json")
base_by_point = {tuple(r["position"]): r["base_q12"] for r in features["actual_point_checks"]}
peak = max(r["power"] for r in trace["rows"])
divisor = math.isqrt(peak << 16)
rows = []
round16 = lambda t: (t + 32768) >> 16
for row in trace["rows"]:
    pos = (row["natural_range_bin"], row["natural_doppler_bin"])
    base = base_by_point[pos]
    root = math.isqrt(row["power"] << 16)
    n = (root*65535 + divisor//2)//divisor
    assert int(params["ROOT5"][n]) == base[0]
    v = list(row["feature_q16"])
    layer_audits = []
    for i in range(3):
        w = params[f"W{i}"].reshape([-1, len(v)]).tolist()
        bias = params[f"B{i}"].reshape(-1).tolist()
        acc = [int(b) + sum(int(a)*int(t) for a,t in zip(v, ww)) for ww,b in zip(w,bias)]
        before_relu = [round16(a) for a in acc]
        nxt = [max(t,0) for t in before_relu] if i < 2 else before_relu
        expected = row[f"layer{i}_q16"] if i < 2 else [row["raw_score_q16"]]
        assert nxt == expected
        layer_audits.append(dict(layer=i, accumulator_q32=acc, output_q16=nxt,
                                 max_abs_accumulator=max(abs(t) for t in acc), matches_existing=True))
        v = nxt
    score = v[0]
    score_q10 = (score + 32) >> 6
    lut_index = min(32768, max(0, score_q10+16384))
    g0 = int(params["GAIN"][lut_index])
    g2 = row["final_gain_q14"]
    scaled = row["power"]*g2*g2+(1<<27)
    output = min((1<<64)-1, scaled>>28)
    assert lut_index == row["lut_index"] and g0 == row["raw_gain_q14"] and output == row["output_power"]
    raw_col = pos[1] ^ 256
    address = 0x24000000 + 8*(pos[0]*512+raw_col)
    rows.append(dict(position=list(pos), integer_sqrt_q8=root, normalization_divisor_q8=divisor,
        normalized_index_u16=n, center_feature_q12=base[0], center_feature_q16=base[0]<<4,
        first_neuron_first_input_q16=row["feature_q16"][0], first_neuron_first_weight_q16=int(params["W0"][0,0]),
        first_neuron_first_product_q32=row["feature_q16"][0]*int(params["W0"][0,0]),
        first_neuron_bias_q32=int(params["B0"][0]), first_neuron_accumulator_q32=layer_audits[0]["accumulator_q32"][0],
        first_neuron_activation_q16=layer_audits[0]["output_q16"][0],
        layers=layer_audits, score_q16=score, score_q10=score_q10, gain_lut_index=lut_index,
        raw_gain_q14=g0, final_gain_q14=g2, scaled_integer=scaled, power_after_round_and_saturation=output,
        board_shifted_column=raw_col, board_byte_address=f"0x{address:08X}", existing_trace_exact=True))

# A conservative interval bound encloses all allowed feature combinations.
# Triangle inequality covers any partial sum/reordering, not only a final sum.
lower = [0]*40
upper = [65536]*40
lower[13:16] = [-65536]*3
bounds = []
for i in range(3):
    w = params[f"W{i}"].reshape([-1,len(lower)]).tolist()
    b = params[f"B{i}"].reshape(-1).tolist()
    out_lo, out_hi, partial = [], [], []
    for ww, bb in zip(w,b):
        lo = int(bb)+sum(int(t)*(l if t>=0 else u) for t,l,u in zip(ww,lower,upper))
        hi = int(bb)+sum(int(t)*(u if t>=0 else l) for t,l,u in zip(ww,lower,upper))
        partial.append(abs(int(bb))+sum(abs(int(t))*max(abs(l),abs(u)) for t,l,u in zip(ww,lower,upper)))
        out_lo.append(round16(lo));out_hi.append(round16(hi))
    if i<2:
        out_lo=[max(v,0) for v in out_lo];out_hi=[max(v,0) for v in out_hi]
    entry=dict(layer=i, accumulator_bits_required=max(partial).bit_length()+1,
        max_abs_partial_accumulator=max(partial), activation_lower=min(out_lo), activation_upper=max(out_hi))
    assert max(partial)+32768 < (1<<47)
    assert min(out_lo)>=-(1<<31) and max(out_hi)<(1<<31)
    bounds.append(entry)
    lower,upper=out_lo,out_hi
assert bounds == read(HW / "reports/interval_bounds.json")["layers"]
weight_min = min(int(params[f"W{i}"].min()) for i in range(3))
weight_max = max(int(params[f"W{i}"].max()) for i in range(3))
assert -(1<<19)<=weight_min<=weight_max<(1<<19)

bdpath = HW / "project/imaging_storage.srcs/sources_1/bd/design_1/design_1.bd"
bd = read(bdpath)["design"]

def net_for(port):
    found=[dict(name=k, ports=v["ports"]) for k,v in bd["nets"].items() if port in v.get("ports",[])]
    assert len(found)==1, (port,len(found))
    return found[0]

ports=["scalar_gain_0/ap_clk","network_frame_control_0/clk","network_frame_control_0/fft_done",
       "network_frame_control_0/interp_done","network_frame_control_0/net_start",
       "scalar_gain_0/ap_start","scalar_gain_0/ap_done","network_frame_control_0/net_done",
       "network_frame_control_0/m_axis_tdata","image_preprocess_0/m_axis_tdata"]
connections={p:net_for(p) for p in ports}
expected_peers={
    "network_frame_control_0/fft_done":"fftshift_write_0/w_frame_end",
    "network_frame_control_0/interp_done":"interp_ip_0/capture_start",
    "network_frame_control_0/net_start":"network_cdc_0/start_fast",
    "scalar_gain_0/ap_start":"network_cdc_0/start_slow",
    "scalar_gain_0/ap_done":"network_cdc_0/done_slow",
    "network_frame_control_0/net_done":"network_cdc_0/done_fast",
    "network_frame_control_0/m_axis_tdata":"image_preprocess_0/s_axis_tdata",
    "image_preprocess_0/m_axis_tdata":"xfft_0/s_axis_data_tdata",
}
assert all(peer in connections[port]["ports"] for port,peer in expected_peers.items())
slow=connections["scalar_gain_0/ap_clk"]["ports"]
fast=connections["network_frame_control_0/clk"]["ports"]
assert "clk_wiz_3/clk_100" in slow and "network_cdc_0/slow_clk" in slow
assert "network_cdc_0/fast_clk" in fast
power_base=int(bd["components"]["net_power_base"]["parameters"]["CONST_VAL"]["value"],0)
work_base=int(bd["components"]["net_work_base"]["parameters"]["CONST_VAL"]["value"],0)
assert (power_base,work_base)==(0x24000000,0x31000000)
xmlpath=HW / "hls/project/solution/syn/report/scalar_gain_csynth.xml"
xml=ET.parse(xmlpath)
cycles=int(xml.findtext(".//SummaryOfOverallLatency/Worst-caseLatency"))
target_ns=float(xml.findtext(".//UserAssignments/TargetClockPeriod"))
monitor=ROOT / "radar1_scalar_compact_sd_fix_v1/software/network_monitor.h"
assert "/250000U" in monitor.read_text(encoding="utf-8")
clock_report=(HW / "reports/timing_summary.rpt").read_text(encoding="utf-8")
assert re.search(r"clk_100_design_1_clk_wiz_3_0\s+\{[^}]+\}\s+10\.000\s+100\.000",clock_report)
assert re.search(r"clk_out2_clk_wiz\s+\{[^}]+\}\s+4\.000\s+250\.000",clock_report)
assert "eth_udp_loop_0/axis_clk" in fast
eth_source=HW / "ip_repo/repo13_eth_udp_loop_1.0/src/eth_udp_loop.v"
eth_text=eth_source.read_text(encoding="utf-8",errors="replace")
assert re.search(r"assign\s+axis_clk\s*=\s*clk_250m\s*;",eth_text)
assert re.search(r"\.clk_out2\s*\(clk_250m\s*\)",eth_text)

max_gain=int(params["GAIN"].max())
worst_scaled=((1<<64)-1)*max_gain**2+(1<<27)
assert worst_scaled.bit_length()<=96
aliases=[dict(natural_a=a, board_a=a^256, double_conversion=(a^256)^256) for a in [0,148,255,256,511]]
rounding=[dict(accumulator_integer=t, quotient_before_round=t/65536, activation_integer=round16(t))
          for t in [-98304,-32768,32768,98304]]
report=dict(status="PASS", scope="Teaching audit only; constants/source/4 existing traces, no new HLS or quality run",
    frozen_constants_match_pc=matches, float_weight_rounding_matches_hls=float_export_matches,
    frozen_bd_expected_peers_verified=True, four_point_integer_replay=rows,
    conservative_interval_bounds=bounds, weight_q16_signed20_range=[weight_min,weight_max],
    partial_accumulator_rounding_margin_verified=True, power_scaling=dict(max_gain_q14=max_gain,
        maximum_scaled_bit_length=worst_scaled.bit_length(), hls_temporary_bits=96,
        saturation_limit=(1<<64)-1), rounding_examples=rounding, doppler_address_examples=aliases,
    verified_bd_connections=connections, power_base=f"0x{power_base:08X}", work_base=f"0x{work_base:08X}",
    clocks=dict(hls_schedule_target_ns=target_ns, actual_core_mhz=100, actual_controller_mhz=250,
        log_counter_cycles_per_ms=250000, hls_estimated_cycles=cycles,
        hls_seconds_at_schedule_target=cycles*target_ns*1e-9, hls_seconds_at_actual_core=cycles/1e8,
        board_infer_ms_existing=read(HERE/"reports/SOURCE_AUDIT.json")["existing_board_final"]["infer_ms"]),
    source_sha256={str(p.relative_to(ROOT)):sha(p) for p in [HW/"hls/scalar_compact.cpp",HW/"hls/parameters.h",bdpath,monitor,xmlpath,eth_source]},
    neural_parameters_modified=False, hls_built=False, full_frame_inference_run=False,
    new_quality_test_run=False, board_accessed=False)
(HERE/"reports/FIXEDPOINT_HARDWARE_WALKTHROUGH.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

md=["# 定点与硬件：实际数值核对", "",
    "本页只读核对冻结HLS常量、4个已有谱点、区间界、BD连接和历史时钟/延时依据，没有重新综合、推理整帧或访问板卡。", "",
    "## 1. 权重和查表是否对应同一个网络", "",
    "| HLS常量 | 与冻结PC数组逐项一致 |", "|---|---|"]
md += [f"| {k} | {v} |" for k,v in matches.items()]
md += ["", "同时逐项核对冻结浮点检查点：权重乘2^16、偏置乘2^32并按导出规则舍入后，与HLS常量一致。没有训练或更新参数。", "",
       f"实际权重Q16整数范围为[{weight_min},{weight_max}]，均可放入20位有符号容器；这不意味着总位宽只有16位。", "",
       "## 2. 四个已有点的归一化和地址", "",
       "| 自然索引 | floor(sqrt(P×2^16)) | 归一化查表下标 | z Q12 | z转Q16 | 板端列 | 功率字节地址 |",
       "|---|---:|---:|---:|---:|---:|---|"]
for r in rows:
    md.append(f"| {tuple(r['position'])} | {r['integer_sqrt_q8']} | {r['normalized_index_u16']} | {r['center_feature_q12']} | {r['center_feature_q16']} | {r['board_shifted_column']} | {r['board_byte_address']} |")
md += ["", "所有点使用同一帧峰值开方结果作归一化分母。地址中的列为自然列a XOR 256；物理单元每点8字节。", "",
       "## 3. 第一层第0神经元的展开", "",
       "| 自然索引 | 首个输入Q16 | 首个权重Q16 | 首项乘积Q32 | 40项加偏置总和Q32 | 舍入与ReLU后Q16 |",
       "|---|---:|---:|---:|---:|---:|"]
for r in rows:
    md.append(f"| {tuple(r['position'])} | {r['first_neuron_first_input_q16']} | {r['first_neuron_first_weight_q16']} | {r['first_neuron_first_product_q32']} | {r['first_neuron_accumulator_q32']} | {r['first_neuron_activation_q16']} |")
md += ["", "所有行偏置Q32相同："+str(int(params["B0"][0]))+"。完整32/16/1层整数结果均与已有POINT_TRACE一致。", "",
       "## 4. 最后分数怎样查成增益", "",
       "| 自然索引 | s Q16 | 舍入到Q10 | 加16384后的LUT下标 | 原g Q14 | 最终g Q14 | 输出功率 |",
       "|---|---:|---:|---:|---:|---:|---:|"]
for r in rows:
    md.append(f"| {tuple(r['position'])} | {r['score_q16']} | {r['score_q10']} | {r['gain_lut_index']} | {r['raw_gain_q14']} | {r['final_gain_q14']} | {r['power_after_round_and_saturation']} |")
md += ["", "## 5. 位宽依据", "",
       "| 层 | 所需有符号累加位数（保守界） | 部分和绝对值上界 | 输出Q16最小 | 输出Q16最大 |",
       "|---|---:|---:|---:|---:|"]
for r in bounds:
    md.append(f"| {r['layer']} | {r['accumulator_bits_required']} | {r['max_abs_partial_accumulator']} | {r['activation_lower']} | {r['activation_upper']} |")
md += ["", "以上三角界与已有interval_bounds.json一致，覆盖所有部分和；另检查加入32768舍入常数后仍在48位范围内。当前48位累加器、32位激活满足这些允许输入范围。它不证明恢复质量。", "",
       f"功率乘最大增益24576的平方并加舍入项，最坏需要{worst_scaled.bit_length()}位无符号整数；HLS使用96位，右移后再饱和到uint64。", "",
       "## 6. 三种时间不能混用", "",
       f"HLS目标{target_ns:g}ns，报告{cycles}周期，对应{cycles*target_ns*1e-9:.9f}秒；实际核心100MHz，同周期对应{cycles/1e8:.9f}秒。",
       "控制器250MHz计时，软件除250000得到毫秒；最近既有板测infer_ms=3888，包含该阶段的握手和实际执行/等待，不是完整FFT到显示延时。", "",
       "## 7. 实际连接入口", "",
       "| 端口 | BD网络名 |", "|---|---|"]
md += [f"| {p} | {v['name']} |" for p,v in connections.items()]
md += ["", "完整端点、舍入例子、散列与数值见[FIXEDPOINT_HARDWARE_WALKTHROUGH.json](C:/Users/yang/Desktop/SAR_IMAGE/network_understanding_v1/reports/FIXEDPOINT_HARDWARE_WALKTHROUGH.json)。",
       "教学说明见[第四讲](C:/Users/yang/Desktop/SAR_IMAGE/network_understanding_v1/14_第四讲_定点数值与FPGA数据流.md)。"]
(HERE/"15_定点与硬件的数值核对.md").write_text("\n".join(md)+"\n",encoding="utf-8")
print(json.dumps(dict(status="PASS",constant_arrays=len(matches),existing_points=len(rows),
    interval_bounds_match=True,core_clock_mhz=100,controller_clock_mhz=250,clocks=report['clocks']),ensure_ascii=False))
