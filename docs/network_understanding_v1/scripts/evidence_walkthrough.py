"""Audit definitions/aggregation of EXISTING results; no FFT or neural inference.

Only saved reference/base/enhanced arrays and reports are read. This is not a
new holdout, model selection, training, or a change to a quality gate.
"""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
from collections import Counter
import hashlib,json,math
import numpy as np
from scipy.ndimage import maximum_filter

HERE=Path(__file__).resolve().parents[1]
ROOT=HERE.parent
R=ROOT/"scalar_restore_v3"
def read(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as s:
        for block in iter(lambda:s.read(4*1024*1024),b""):h.update(block)
    return h.hexdigest()
def same(a,b):return math.isclose(float(a),float(b),rel_tol=1e-11,abs_tol=1e-12)
report=read(R/"compact_fresh_test/report.json")
protocol=read(R/"COMPACT_TEST_PROTOCOL.json")
manifest=read(R/"compact_test_manifest.json")
metadata={r["id"]:r for r in manifest["records"]}
assert {r["id"] for r in report["rows"]}==set(metadata)
rows=[];all_targets=[];array_hashes={}
for row in report["rows"]:
    path=R/"compact_fresh_test/arrays"/(row["id"]+".npz")
    with np.load(path,allow_pickle=False) as d:
        ref,base,out=[d[k] for k in ["reference","base","enhanced"]]
    y=np.sqrt(ref.astype("f8")/max(float(ref.max()),1))
    scale=max(float(base.max()),1)
    x,e=[np.sqrt(v.astype("f8")/scale) for v in [base,out]]
    maxima=y==maximum_filter(y,3,mode="wrap")
    residual_sums={}
    peak_drops=[]
    for label,mask in [("all",np.ones(y.shape,bool)),("original_37_485",np.broadcast_to(((np.arange(1024)>=37)&(np.arange(1024)<=485))[:,None],y.shape))]:
        denom=max(float(np.square(y[mask]).sum()),1e-30)
        baseline_sse=float(np.square(x[mask]-y[mask]).sum())
        enhanced_sse=float(np.square(e[mask]-y[mask]).sum())
        bn,en=baseline_sse/denom,enhanced_sse/denom
        drop=mask&(y>=.03)&maxima&(x>=.5*y)&(e<.5*y)
        values=dict(baseline_nmse=bn,enhanced_nmse=en,nmse_ratio=en/max(bn,1e-30),extra_reference_peak_drops=int(drop.sum()))
        assert all(same(values[k],row["metrics"][label][k]) for k in values),(row["id"],label)
        residual_sums[label]=dict(baseline_sse=baseline_sse,enhanced_sse=enhanced_sse,reference_energy=denom)
        if label=="all":
            for r,a in np.argwhere(drop):
                peak_drops.append(dict(position=[int(r),int(a)],reference=float(y[r,a]),baseline=float(x[r,a]),enhanced=float(e[r,a])))
    # evaluate.measures uses amplitudes(...).astype(float32) for its reference
    # background values; error_metrics/target_metrics use float64 separately.
    y_bg=y.astype("f4")
    bg=y_bg<.003
    targets=[]
    for t in row["targets"]:
        r,a=round(t["range_bin"])%1024,round(t["doppler_bin"])%512
        ri=np.arange(r-2,r+3)%1024;ai=np.arange(a-2,a+3)%512
        ii,jj=np.unravel_index(y[np.ix_(ri,ai)].argmax(),(5,5))
        q=(int(ri[ii]),int(ai[jj]));tr,bb,ee=[float(v[q]) for v in [y,x,e]]
        vals=dict(reference=tr,baseline=bb,enhanced=ee,baseline_retention=bb/max(tr,1e-12),
            enhanced_retention=ee/max(tr,1e-12),baseline_abs_error=abs(bb-tr),enhanced_abs_error=abs(ee-tr))
        assert list(q)==t["measured_peak_bin"] and all(same(v,t[k]) for k,v in vals.items())
        assert bool(bb>=.5*tr and ee<.5*tr)==t["newly_below_half"]
        targets.append(dict(record=row["id"],actual_chirps=row["actual_chirps"],kind=t["kind"],
            measured_peak_bin=list(q),newly_below_half=bool(t["newly_below_half"]),**vals))
        bg[np.ix_(np.arange(r-3,r+4)%1024,np.arange(a-3,a+4)%512)]=False
    positive=float(np.square(np.maximum(e[bg]-y_bg[bg],0)).sum())
    bgpower=float(np.square(e[bg]).sum())
    assert same(positive,row["background_positive_error"]) and same(bgpower,row["background_power"]), (row["id"],positive,row["background_positive_error"],bgpower,row["background_power"])
    selected={tuple(t["measured_peak_bin"]) for t in targets}
    for q in peak_drops:q["is_selected_known_target_peak"]=tuple(q["position"]) in selected
    all_targets.extend(targets)
    rows.append(dict(id=row["id"],group=row["group"],actual_chirps=row["actual_chirps"],
        source_frame_zero_based=metadata[row["id"]].get("source_frame_zero_based"),
        rx_id=metadata[row["id"]].get("rx_id"),saved_arrays_match_report=True,
        metrics=row["metrics"]["all"],residual_sums=residual_sums["all"],
        background_positive_error=positive,v7_background_positive_error=row["original"]["background_positive_error"],
        known_target_count=len(targets),numeric_reference_peak_drops=peak_drops))
    array_hashes[path.name]=sha(path)
    print("EXISTING_METRICS_MATCH",row["id"],flush=True)

def target_summary(tt):
    weak=[t for t in tt if "weak" in t["kind"]]
    return dict(known_targets=len(tt),known_weak_targets=len(weak),new_half_losses=sum(t["newly_below_half"] for t in tt),
        baseline_below_half=sum(t["baseline_retention"]<.5 for t in tt),
        enhanced_below_half=sum(t["enhanced_retention"]<.5 for t in tt),
        recovered_to_at_least_half=sum(t["baseline_retention"]<.5 and t["enhanced_retention"]>=.5 for t in tt),
        weak_error_ratio=sum(t["enhanced_abs_error"] for t in weak)/max(sum(t["baseline_abs_error"] for t in weak),1e-20) if weak else None)

groups={}
for name,rr in [("synthetic_128",[r for r in rows if r["group"]=="synthetic" and r["actual_chirps"]==128]),
                ("synthetic_512",[r for r in rows if r["group"]=="synthetic" and r["actual_chirps"]==512]),
                ("field_temporal_128",[r for r in rows if r["group"]=="field_temporal"])]:
    ids={r["id"] for r in rr};tt=[t for t in all_targets if t["record"] in ids]
    groups[name]=dict(records=len(rr),record_ids=sorted(ids),**target_summary(tt),
        mean_frame_nmse_ratio=float(np.mean([r["metrics"]["nmse_ratio"] for r in rr])),
        ratio_of_mean_nmse=sum(r["metrics"]["enhanced_nmse"] for r in rr)/sum(r["metrics"]["baseline_nmse"] for r in rr),
        pooled_normalized_sse_ratio=sum(r["residual_sums"]["enhanced_sse"] for r in rr)/sum(r["residual_sums"]["baseline_sse"] for r in rr),
        background_error_relative_to_v7=sum(r["background_positive_error"] for r in rr)/sum(r["v7_background_positive_error"] for r in rr),
        numeric_reference_peak_drops=sum(len(r["numeric_reference_peak_drops"]) for r in rr),
        source_frames=sorted({r["source_frame_zero_based"] for r in rr if r["source_frame_zero_based"] is not None}))
summary=target_summary(all_targets)
expected=report["summary"]
assert summary["known_targets"]==expected["known_targets"]==120
assert summary["known_weak_targets"]==expected["known_weak_targets"]==96
assert summary["new_half_losses"]==expected["new_targets_below_half"]==0
assert summary["baseline_below_half"]==expected["baseline_targets_below_half"]==42
assert summary["enhanced_below_half"]==expected["enhanced_targets_below_half"]==17
assert same(summary["weak_error_ratio"],expected["weak_mae_ratio"])
for n in [128,512]:
    key=f"synthetic_{n}"
    assert same(groups[key]["mean_frame_nmse_ratio"],expected["acquisition_subgroups"][key]["mean_nmse_ratio"])
    assert same(groups[key]["background_error_relative_to_v7"],expected["acquisition_subgroups"][key]["background_error_relative_to_v7"])
assert same(groups["field_temporal_128"]["mean_frame_nmse_ratio"],expected["groups"]["field_temporal"]["mean_nmse_ratio"])
assert report["status"]=="FAIL" and report["correction_status"]=="PASS"
assert groups["synthetic_512"]["background_error_relative_to_v7"]>protocol["original_v7_background_max"]
assert groups["field_temporal_128"]["source_frames"]==protocol["raw_frames_zero_based"]

diagnosed=read(R/"RESULTS_COMPACT.json")["diagnosed_targets"]
result=dict(status="PASS",scope="Recalculation of existing saved outputs and metric aggregation; not a new performance test",
    arrays_checked=len(rows),array_hashes=array_hashes,groups=groups,known_target_summary=summary,rows=rows,
    target_measurement="Select reference peak inside periodic5x5 around known position; compare all methods at that SAME bin",
    weak_definition="kind string contains weak; a controlled generator category, not a calibrated real target SNR threshold",
    diagnosed_numbers_are_retention_ratios=diagnosed,quality_status_preserved=report["status"],
    weak_correction_status_preserved=report["correction_status"],
    all_existing_metrics_match=True,aggregation_matches_original_summary=True,
    neural_parameters_modified=False,new_inference_run=False,new_holdout_opened=False,training_run=False,board_accessed=False,
    sources={str(p.relative_to(ROOT)):sha(p) for p in [R/"compact_fresh_test/report.json",R/"COMPACT_TEST_PROTOCOL.json",R/"compact_test_manifest.json",ROOT/"scalar_restore_v2/evaluate.py",ROOT/"scalar_streak_fix_v1/common.py",ROOT/"scalar_streak_fix_v1/controlled.py"]})
(HERE/"reports/EVIDENCE_WALKTHROUGH.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

md=["# 已有效果指标的口径核对", "",
    "本页重算已读取过的compact_fresh_test保存输出，没有执行FFT、网络推理、训练或新留出测试。22条记录的两种距离统计范围、背景值、全部已知目标读数均与原报告一致。", "",
    "## 1. 把128、512与实测分开", "",
    "| 组 | 记录数 | 已知目标/弱目标 | 旁路低于半幅 → 增强低于半幅 | 新增半幅损失 | 弱目标误差/旁路 | 平均逐帧NMSE比 | 背景正误差/V7 |",
    "|---|---:|---:|---|---:|---:|---:|---:|"]
for name,g in groups.items():
    weak="—" if g["weak_error_ratio"] is None else f"{g['weak_error_ratio']:.6f}"
    target_counts=f"{g['known_targets']}/{g['known_weak_targets']}" if g["known_targets"] else "无物理标签"
    half_counts=f"{g['baseline_below_half']} → {g['enhanced_below_half']}" if g["known_targets"] else "不适用"
    new_losses=str(g["new_half_losses"]) if g["known_targets"] else "不适用"
    md.append(f"| {name} | {g['records']} | {target_counts} | {half_counts} | {new_losses} | {weak} | {g['mean_frame_nmse_ratio']:.6f} | {g['background_error_relative_to_v7']:.6f} |")
md += ["", "实测组6条记录来自同一次采集的3个源帧455/519/583，每帧RX0/RX3两通道，均128有效chirp。没有物理目标标签，不能计算已知目标保留率；不表示场景没有目标。它也不是最近板测完成的那6帧。", "",
    "全体受控目标120个、弱目标96个；42个原低于半幅中有25个升到至少半幅，17个仍低于半幅；没有新增跨过半幅向下的目标。弱目标绝对误差之和/旁路为"+f"{summary['weak_error_ratio']:.9f}。", "",
    "## 2. 三种聚合不是同一个指标", "",
    "| 组 | mean(NMSE增强/NMSE旁路)，原口径 | mean(NMSE增强)/mean(NMSE旁路) | 合并归一化幅值SSE之比 |",
    "|---|---:|---:|---:|"]
for name,g in groups.items():
    md.append(f"| {name} | {g['mean_frame_nmse_ratio']:.9f} | {g['ratio_of_mean_nmse']:.9f} | {g['pooled_normalized_sse_ratio']:.9f} |")
md += ["", "新增两列只是同一保存结果的口径示意，不替换原门槛，也不选择数值更好的一列宣布新性能。背景/V7使用背景正误差之和的比，不能偷偷改成逐帧比值的平均。", "",
    "## 3. 已知目标与参考局部峰不同", "",
    "受控目标先在已知位置的周期5×5内找参考最大点，然后在同一个点读取参考、旁路和增强。不是分别给各方法找最有利的峰。", "",
    "另一个指标extra_reference_peak_drops统计参考幅值≥0.03的全部3×3局部最大点，并不只统计目标标签。已有记录中的额外数值参考峰下降如下：", "",
    "| 记录 | 自然索引 | 参考幅值 | 旁路 | 增强 | 是否已知目标所选峰 |", "|---|---|---:|---:|---:|---|"]
for r in rows:
    for q in r["numeric_reference_peak_drops"]:
        md.append(f"| {r['id']} | {tuple(q['position'])} | {q['reference']:.6f} | {q['baseline']:.6f} | {q['enhanced']:.6f} | {q['is_selected_known_target_peak']} |")
md += ["", "因此“已知目标新增半幅损失0”与“全部数值参考峰仍有1处新增下降”可以同时成立；后者不能隐去，也不能未经标注就称为新增真实漏检。", "",
    "## 4. 两个诊断例的数值单位", "",
    "| 旧诊断例 | 旁路保留率 | 修正前保留率 | compact保留率 |", "|---|---:|---:|---:|"]
for d in diagnosed:
    md.append(f"| {d['id']} | {d['baseline']:.6f} | {d['previous']:.6f} | {d['corrected']:.6f} |")
md += ["", "这些是当前幅值/同位置参考幅值的比值，不是直接的归一化幅值。两例已用于开发诊断，不能称作新的盲测成功。", "",
    "## 5. 可核验范围", "",
    "全部22条保存输出均核对，不只挑选截图。原整体质量FAIL与弱峰专项PASS保持。这里没有增加统计独立样本、置信区间、跨场景测试或物理目标标签。", "",
    "完整数值与文件散列：[EVIDENCE_WALKTHROUGH.json](C:/Users/yang/Desktop/SAR_IMAGE/network_understanding_v1/reports/EVIDENCE_WALKTHROUGH.json)。",
    "论文论证讲解见[第五讲](C:/Users/yang/Desktop/SAR_IMAGE/network_understanding_v1/16_第五讲_论文汇报与证据链.md)。"]
(HERE/"17_已有效果指标的口径核对.md").write_text("\n".join(md)+"\n",encoding="utf-8")
print(json.dumps(dict(status="PASS",records=len(rows),groups=groups,targets=summary),ensure_ascii=False))
