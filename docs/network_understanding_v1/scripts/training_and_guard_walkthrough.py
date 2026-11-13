"""Reproduce frozen loss algebra and existing guard examples for teaching only.

No optimizer, backward pass, model inference, training data selection, or board IO.
The selected source's loss block is executed on a small algebraic batch and
checked against an independent NumPy expression. Existing point traces are
replayed with scalar guard arithmetic, without changing the frozen package.
"""
import sys
sys.dont_write_bytecode = True
import ast
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import torch
from torch.nn import functional as F

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
SOURCE = ROOT / "scalar_restore_v2/runs/protected_patch5/training_source.py"
MODEL = ROOT / "scalar_restore_v3/pc_candidate_compact"

def read(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")

config = read(ROOT / "scalar_restore_v2/runs/soft_patch5/config.json")
assert digest(SOURCE) == config["code_sha256"]
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
loop = next(n for n in main.body if isinstance(n, ast.For) and any(
    isinstance(t, ast.Assign) and any(isinstance(v, ast.Name) and v.id == "goal" for v in t.targets)
    for t in n.body))
start = next(i for i, n in enumerate(loop.body) if isinstance(n, ast.Assign) and any(
    isinstance(v, ast.Name) and v.id == "g" for v in n.targets))
end = next(i for i, n in enumerate(loop.body) if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
    and isinstance(n.value.func, ast.Attribute) and isinstance(n.value.func.value, ast.Name)
    and n.value.func.value.id == "opt")
block = loop.body[start:end]
assert isinstance(block[-1], ast.If)  # protect_strength branch
loss_code = compile(ast.fix_missing_locations(ast.Module(body=block, type_ignores=[])), str(SOURCE), "exec")

# These are intentionally algebraic examples, not new samples or quality data.
examples = [
    dict(name="峰值与参考一致", x=1., y=1., raw=0., support=1, known=0, low=0, centers=1, excess=0),
    dict(name="伪影衰减仍受下限约束", x=.3, y=.01, raw=-3., support=0, known=0, low=0, centers=0, excess=1),
    dict(name="支持弱峰被误压", x=.018, y=.02, raw=math.log2(.4), support=1, known=1, low=0, centers=0, excess=0),
    dict(name="所需增强超出上限", x=.02, y=.08, raw=math.log2(1.5), support=1, known=1, low=0, centers=1, excess=0),
    dict(name="低背景被放大", x=.001, y=.0001, raw=math.log2(1.25), support=0, known=0, low=1, centers=0, excess=1),
    dict(name="输入严格为零", x=0., y=.02, raw=0., support=1, known=1, low=0, centers=0, excess=0),
    dict(name="原始分数超过增益上限", x=.03, y=.03, raw=2., support=1, known=0, low=0, centers=0, excess=0),
    dict(name="原始分数低于增益下限", x=.08, y=.002, raw=-5., support=0, known=0, low=1, centers=0, excess=1),
]
keys = ["raw", "x", "y", "support", "known", "low", "centers", "excess"]
arrays = {k: np.asarray([r[k] for r in examples], dtype="f8")[:, None] for k in keys}
raw, x, y, S, K, L, C, E = [arrays[k] for k in keys]
g = np.exp2(np.clip(raw, -3, .5849625))
pred = x * g
goal = np.clip(np.log2((y + .00001) / (x + .00001)), -3, .5849625)
w = 1 + 3*S + 5*K + 8*C
valid = x > .00001
err, err0 = np.abs(pred-y), np.abs(x-y)
pos = lambda v: np.maximum(v, 0)
weighted = lambda v, mask: float((v*mask).sum() / max(float(mask.sum()), 1.))
d = np.abs(raw-goal)
huber = np.where(d < 1, .5*d*d, d-.5)
rel = pos(err-err0-.0005)/(y+.005)
half = pos(.52*y-pred)/(y+.005)*(x >= .5*y)
terms = dict(
    log2_gain_head=.35*weighted(huber, w*valid),
    log_amplitude=.2*weighted(np.abs(np.log1p(pred/.001)-np.log1p(y/.001)), w),
    amplitude_squared=20*weighted((pred-y)**2, w),
    support_nonregression=4*weighted(pos(err-err0-.002), S+K),
    center_relative_nonregression=2*weighted(pos(err-err0-.002)/(y+.01), C+K),
    artifact_overestimate=.3*weighted((pos(pred-y)/(y+.01))**2, E),
    low_background_boost=.1*weighted(pos(g-1), L),
    explicit_peak_protection=20*weighted(rel+half, np.clip(C+K, 0, 1)),
)
total = sum(terms.values())
source_losses = {}
for dtype, name in [(torch.float64, "float64"), (torch.float32, "float32")]:
    env = dict(torch=torch, F=F, net=SimpleNamespace(boost=True), a=SimpleNamespace(protect_strength=20.))
    env.update({k: torch.tensor(v, dtype=dtype) for k, v in arrays.items()})
    with torch.no_grad():
        exec(loss_code, env)
    source_losses[name] = float(env["loss"])
assert math.isclose(total, source_losses["float64"], rel_tol=1e-12, abs_tol=1e-12)
assert math.isclose(total, source_losses["float32"], rel_tol=2e-6, abs_tol=2e-6)

for i, row in enumerate(examples):
    row.update(gain=float(g[i, 0]), prediction=float(pred[i, 0]), target_log_gain=float(goal[i, 0]),
               absolute_error_before=float(err0[i, 0]), absolute_error_after=float(err[i, 0]),
               relative_protection=float(rel[i, 0]), half_protection=float(half[i, 0]),
               head_valid=bool(valid[i, 0]))

reachable = []
for a0, target in [(.3, .1), (.02, .08), (.08, .002), (0., .02)]:
    lo, hi = .125*a0, 1.5*a0
    best = float(np.clip(target, lo, hi))
    reachable.append(dict(input=a0, reference=target, output_interval=[lo, hi],
                          closest_amplitude=best, unavoidable_absolute_error=abs(best-target)))

trace = read(HERE / "reports/POINT_TRACE.json")
feature_trace = read(HERE / "reports/FEATURE_WALKTHROUGH.json")
feature_rows = {tuple(r["position"]): r for r in feature_trace["actual_point_checks"]}
power = np.load(ROOT / "scalar_restore_v3/examples_compact/diagnosed_512_power.npy", allow_pickle=False)
with np.load(ROOT / "scalar_restore_v3/examples_compact/diagnosed_512_expected.npz", allow_pickle=False) as s:
    existing_gain, existing_power = s["gain_q14"].copy(), s["power"].copy()
peak = int(power.max())

def max_at(r, a0, size):
    d0 = np.arange(-(size//2), size//2+1)
    return int(power[np.ix_((r+d0)%1024, (a0+d0)%512)].max())

def pow5_q16(q12):
    v = int(q12) << 4
    out = v
    for _ in range(4):
        out = (out*v + 32768) >> 16
    return out

def soft_q14(v):
    return v + (max(16384-v, 0)*max(0, min(v-4096, 4096))+2048)//4096

guard_rows = []
for row in trace["rows"]:
    r, a0 = row["natural_range_bin"], row["natural_doppler_bin"]
    f = feature_rows[(r, a0)]["base_q12"]
    p = int(power[r, a0]); mx3, mx9 = max_at(r, a0, 3), max_at(r, a0, 9)
    amp, parent3, parent5 = [pow5_q16(f[k]) for k in [0,4,5]]
    explained3 = parent3 >= 16384 and 2*abs(3*amp-parent3) <= parent3
    explained5 = parent5 >= 16384 and 2*abs(5*amp-parent5) <= parent5
    explained = explained3 or explained5
    near = p >= (peak+9999)//10000 and p >= (mx3+1)//2
    mask1 = p > 0 and p <= peak//16 and (p == mx9 or near) and not explained
    g0 = row["raw_gain_q14"]
    g1 = soft_q14(g0) if mask1 else g0
    if p == peak:
        g1 = 16384
    mean = max(int(f[3]), 128)
    compact = min(4096, (max(5*int(f[0])-7*mean, 0)*4096+mean//2)//mean)
    mask2 = p >= (peak+9999)//10000 and p <= peak//16 and p == mx9 and not explained
    confidence = max(0, min(g1-4096, 4096))
    weight = (compact*confidence+2048)//4096
    g2 = g1 + (max(16384-g1, 0)*weight+2048)//4096 if mask2 else g1
    out = min((1<<64)-1, (p*g2*g2+(1<<27))>>28)
    exact = (g1 == row["first_guard_gain_q14"] and g2 == row["final_gain_q14"]
             and g2 == int(existing_gain[r,a0]) and out == int(existing_power[r,a0]))
    assert exact
    guard_rows.append(dict(position=[r,a0], label=row["label"], power=p, power_relative_peak=p/peak,
        max3=mx3, max9=mx9, is_max9=p==mx9, near=near,
        amplitude_q16=amp, parent3_q16=parent3, parent5_q16=parent5,
        explained3=explained3, explained5=explained5, first_eligible=mask1, compact_eligible=mask2,
        center_z_q12=int(f[0]), mean9_z_q12=int(f[3]), compactness_q12=compact,
        raw_gain_q14=g0, first_guard_gain_q14=g1, compact_weight_q12=weight, final_gain_q14=g2,
        existing_trace_and_output_exact=exact))

curve = []
for q in [2048,4096,5120,6144,7168,8192,16384,18022]:
    g1 = soft_q14(q)
    weight = max(0,min(g1-4096,4096))  # illustrative eligible point with compactness=1
    g2 = g1 + (max(16384-g1,0)*weight+2048)//4096
    curve.append(dict(raw_gain=q/16384, after_soft=g1/16384, after_fully_compact=g2/16384))

baseline_mse = 10000*.001**2/10001
damaged_mse = (.1-.02)**2/10001
report = dict(status="PASS", scope="Teaching algebra and existing point replay; not training or new quality evidence",
    training_source=str(SOURCE), training_source_sha256=digest(SOURCE),
    training_source_matches_selected_config=True, extracted_loss_lines=[block[0].lineno, block[-1].end_lineno],
    numpy_loss_terms=terms, numpy_total=total, executed_source_totals=source_losses,
    source_loss_matches_independent_algebra=True, algebraic_examples=examples,
    bounded_multiplicative_reachability=reachable,
    mean_error_counterexample=dict(background_pixels=10000, reference_target_amplitude=.1,
        baseline_background_error=.001, baseline_target_error=0., damaged_target_amplitude=.02,
        baseline_mse=baseline_mse, damaged_mse=damaged_mse, mse_ratio=damaged_mse/baseline_mse,
        target_amplitude_loss=.8),
    existing_guard_points=guard_rows, eligible_guard_curve=curve,
    selected_loss_history_available=(ROOT / "scalar_restore_v2/runs/soft_patch5/loss.jsonl").exists(),
    neural_parameters_modified=False, training_run=False, new_quality_test_run=False, board_accessed=False)
save(HERE / "reports/TRAINING_GUARD_WALKTHROUGH.json", report)

md = ["# 训练损失与保护：可核对的数值例子", "",
    "本页区分两类证据：构造数值用于解释损失和结构边界；既有4个谱点用于重放当前保护。没有训练、重新推理整帧或新增目标标签。", "",
    "## 1. 损失公式是否对应所选训练代码", "",
    f"所选配置匹配的源快照SHA256：`{digest(SOURCE)}`。", "",
    f"直接提取快照第{block[0].lineno}–{block[-1].end_lineno}行的损失计算，在8个构造谱点上执行；没有调用main、优化器或反向传播。", "",
    "| 损失分量（已含系数） | 构造批次的值 |", "|---|---:|"]
md += [f"| {k} | {v:.9f} |" for k,v in terms.items()]
md += [f"| NumPy独立公式合计 | {total:.9f} |",
       f"| 快照代码float64 | {source_losses['float64']:.9f} |",
       f"| 快照代码float32 | {source_losses['float32']:.9f} |", "",
       "两者在相应浮点容差内一致。这是公式核对，数值不是模型训练损失曲线，也不能当作效果指标。所选soft_patch5目录没有loss.jsonl，不能补造该次逐步收敛曲线。", "",
       "## 2. 构造谱点说明什么", "",
       "| 情况 | 单比特x | 多比特y | 原始分数s | 限幅后g | 预测xg | 特别保护中的relative / half |",
       "|---|---:|---:|---:|---:|---:|---:|"]
for row in examples:
    md.append(f"| {row['name']} | {row['x']:.4f} | {row['y']:.4f} | {row['raw']:.6f} | {row['gain']:.6f} | {row['prediction']:.6f} | {row['relative_protection']:.6f} / {row['half_protection']:.6f} |")
md += ["", "表中relative/half仅是特别保护的未加权逐点表达式；该项还需要训练参考掩码。不能把没有进入掩码的背景点也算作受保护目标。", "",
       "严格零输入不参与log2增益头损失，但仍可参与其它幅值损失；乘法输出对该点永远为零，不能靠增加训练步数改变这一点。", "",
       "## 3. 增益范围造成的不可避免残差", "",
       "| x | y | 允许输出区间 | 区间内最近输出 | 最小绝对误差 |", "|---:|---:|---|---:|---:|"]
for r in reachable:
    md.append(f"| {r['input']:.4f} | {r['reference']:.4f} | [{r['output_interval'][0]:.6f}, {r['output_interval'][1]:.6f}] | {r['closest_amplitude']:.6f} | {r['unavoidable_absolute_error']:.6f} |")
md += ["", "这是理想有界乘法的数学区间；定点舍入还会有微小差别。它不是当前网络在这些构造点上的推理结果。", "",
       "## 4. 平均误差下降不保证弱目标保留", "",
       f"10000个背景点各有0.001误差，一个幅值0.1的目标原本准确，MSE={baseline_mse:.12g}。",
       f"把背景误差降为0，但把目标压到0.02，MSE反而降到{damaged_mse:.12g}，即原来的{damaged_mse/baseline_mse:.2f}倍。",
       "目标幅值却损失了80%。这是构造反例，说明为什么要分开报告总体误差与逐目标指标，不是本次新增质量失败。", "",
       "## 5. 既有谱点的保护重放", "",
       "这些行来自已有512有效chirp诊断帧。父幅值近似均为Q16解码，是否可解释只是保护规则的判据，不是物理真值。", "",
       "| 自然索引 | 9×9最大 | near | 三/五次解释 | 第一保护候选 | 紧凑保护候选 | 紧凑度 | 原g → 第一保护 → 最终g |",
       "|---|---|---|---|---|---|---:|---|"]
for r in guard_rows:
    md.append(f"| {tuple(r['position'])} | {r['is_max9']} | {r['near']} | {r['explained3']}/{r['explained5']} | {r['first_eligible']} | {r['compact_eligible']} | {r['compactness_q12']/4096:.6f} | {r['raw_gain_q14']/16384:.6f} → {r['first_guard_gain_q14']/16384:.6f} → {r['final_gain_q14']/16384:.6f} |")
md += ["", "四个点的两层增益及输出功率与既有记录逐项一致。主峰固定g=1由锚定规则完成；强谐波解释只阻止保护抬升，不直接决定MLP输出。", "",
       "## 6. 连续保护的增益变化", "",
       "下表假设两层候选条件都满足，紧凑度为1；只演示保护算术，不是新网络预测。", "",
       "| 原g | 第一软保护 | 再经完整紧凑保护 |", "|---:|---:|---:|"]
for r in curve:
    md.append(f"| {r['raw_gain']:.6f} | {r['after_soft']:.6f} | {r['after_fully_compact']:.6f} |")
md += ["", "g≤0.25时这两种连续提升都不会救回该点；g≥0.5且小于1时，第一保护可抬到1。增益带是经验设计，不是校准置信度。", "",
       "讲解见[第三讲](C:/Users/yang/Desktop/SAR_IMAGE/network_understanding_v1/12_第三讲_训练监督与弱峰保护.md)。",
       "完整条件、整数和误差：[TRAINING_GUARD_WALKTHROUGH.json](C:/Users/yang/Desktop/SAR_IMAGE/network_understanding_v1/reports/TRAINING_GUARD_WALKTHROUGH.json)。"]
(HERE / "13_训练损失与保护的数值核对.md").write_text("\n".join(md)+"\n", encoding="utf-8")
print(json.dumps(dict(status="PASS", loss_total=total, source_totals=source_losses,
    existing_guard_points=len(guard_rows), all_existing_outputs_exact=all(r["existing_trace_and_output_exact"] for r in guard_rows)), ensure_ascii=False))
