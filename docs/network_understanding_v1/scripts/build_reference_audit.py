"""Read-only source audit for teaching. No training, inference, or board access."""
import sys
sys.dont_write_bytecode = True
import hashlib, json, re
from collections import Counter
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
def read(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8-sig"))
def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as s:
        for b in iter(lambda: s.read(4*1024*1024), b""):
            h.update(b)
    return h.hexdigest()
def write(p, v):
    p.write_text(json.dumps(v, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

files = [
    "scalar_restore_v3/pc_candidate_compact/"+n for n in
    ["restore_power.py", "model_source.py", "compact_guard.py", "scalar_guard.py",
     "config.json", "weights.npz", "root5.npy", "model_float.pt"]
] + [
    "scalar_restore_v2/runs/soft_patch5/config.json",
    "scalar_restore_v2/runs/protected_patch5/training_source.py",
    "scalar_restore_v2/runs/soft_patch5/step_30000.pt",
    "scalar_restore_v2/prepare_data.py", "scalar_restore_v2/common_v2.py",
    "scalar_restore_v2/evaluate.py", "scalar_streak_fix_v1/common.py",
    "radar1_scalar_compact_exp_v1/hls/scalar_compact.cpp",
    "radar1_scalar_compact_exp_v1/hls/parameters.h",
    "radar1_scalar_compact_exp_v1/rtl/image_preprocess.v",
    "radar1_scalar_compact_exp_v1/rtl/network_frame_control.v",
    "radar1_scalar_compact_exp_v1/pkg/design_1_wrapper.bit",
    "radar1_scalar_compact_sd_fix_v1/pkg/design_1_wrapper.bit",
    "radar1_scalar_compact_sd_fix_v1/pkg/onebit_network_storage.elf",
    "radar1_scalar_compact_sd_fix_v1/board_runs/log.txt",
    "scalar_restore_v3/compact_fresh_test/report.json",
    "scalar_restore_v3/NUMERIC_VERIFICATION_COMPACT.json",
    "cdqob_pc_online_v1/model.py",
]
manifest = {r: dict(bytes=(ROOT/r).stat().st_size, sha256=sha(ROOT/r)) for r in files}
baseline_path = HERE/"reports/SOURCE_BASELINE.json"
if baseline_path.exists():
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
else:
    baseline = manifest
    write(baseline_path, baseline)

cfg = read("scalar_restore_v2/runs/soft_patch5/config.json")
rcfg = read("scalar_restore_v3/pc_candidate_compact/config.json")
q = read("scalar_restore_v3/compact_fresh_test/report.json")
numeric = read("scalar_restore_v3/NUMERIC_VERIFICATION_COMPACT.json")
with np.load(ROOT/"scalar_restore_v3/pc_candidate_compact/weights.npz") as w:
    shapes = {k: list(w[k].shape) for k in ["w0","b0","w1","b1","w2","b2"]}
    parameter_count = sum(w[k].size for k in shapes)
    macs = sum(w[k].size for k in ["w0","w1","w2"])
conv_shapes = [(1,1,3,3),(3,3,3,32),(5,5,35,32),(7,7,64,32),(9,9,96,32),(1,1,128,3)]
conv_macs = [int(np.prod(s)) for s in conv_shapes]
old_params = sum(conv_macs) + sum(s[-1] for s in conv_shapes)
log = (ROOT/"radar1_scalar_compact_sd_fix_v1/board_runs/log.txt").read_text(encoding="utf-8-sig")
last = re.findall(r"NET: enabled=(\d+) busy=(\d+) done=(\d+) image_in=(\d+) image_skip=(\d+) infer_ms=(\d+) fault=(\d+) status=([0-9A-Fa-f]+)", log)[-1]
checks = dict(
    frozen_sources_unchanged=manifest == baseline,
    matching_training_snapshot=cfg["code_sha256"] == manifest["scalar_restore_v2/runs/protected_patch5/training_source.py"]["sha256"],
    deployed_weight_matches_config=rcfg["sha256"]["weights.npz"] == manifest["scalar_restore_v3/pc_candidate_compact/weights.npz"]["sha256"],
    selected_float_checkpoint_matches=manifest["scalar_restore_v2/runs/soft_patch5/step_30000.pt"]["sha256"] == manifest["scalar_restore_v3/pc_candidate_compact/model_float.pt"]["sha256"],
    sd_fix_uses_same_bit=manifest["radar1_scalar_compact_exp_v1/pkg/design_1_wrapper.bit"]["sha256"] == manifest["radar1_scalar_compact_sd_fix_v1/pkg/design_1_wrapper.bit"]["sha256"],
    architecture=shapes == {"w0":[32,40],"b0":[32],"w1":[16,32],"b1":[16],"w2":[1,16],"b2":[1]},
    parameter_count=parameter_count == 1857,
    mac_count=macs == 1808 and old_params == 378575,
    quality_fail_preserved=q["status"] == "FAIL",
    weak_correction_pass=q["correction_status"] == "PASS",
    source_numeric_pass=numeric["status"] == "PASS",
    board_log_scoped_pass="RESULT: PASS, stored=60 blocks" in log and int(last[6]) == 0,
)
summary = dict(
    scope="Documentation/source audit only; not a new model quality or board test",
    status="PASS" if all(checks.values()) else "FAIL", checks=checks,
    shapes=shapes, parameters=int(parameter_count), mac_per_point=int(macs),
    mlp_mac_per_1024x512_frame=int(macs*1024*512),
    original_conv_macs=conv_macs, original_parameters=old_params,
    original_mac_per_frame=sum(conv_macs)*1024*512,
    core_mac_ratio=sum(conv_macs)/macs,
    training=dict(record_count=len(cfg["training_records"]),
        pool_samples=sum(r["samples"] for r in cfg["training_records"]),
        record_prefix_counts=dict(Counter("_".join(r["id"].split("_")[:2]) for r in cfg["training_records"])),
        protect_strength=cfg["protect_strength"], learning_rate=cfg["learning_rate"],
        selected_training_code="scalar_restore_v2/runs/protected_patch5/training_source.py"),
    existing_quality_summary=q["summary"],
    existing_board_final=dict(zip(["enabled","busy","done","image_in","image_skip","infer_ms","fault","status"], last)),
    original_quality_status=q["status"], source_manifest=manifest)
write(HERE/"reports/SOURCE_AUDIT.json", summary)

anchors = [
    ("PL数字符号量化", "radar1_scalar_compact_exp_v1/rtl/image_preprocess.v", "wire [15:0] quant_i"),
    ("幅值编码与基础特征", "scalar_restore_v3/pc_candidate_compact/restore_power.py", "def features("),
    ("候选谐波父位置", "scalar_restore_v3/pc_candidate_compact/restore_power.py", "for h in [-3,5]"),
    ("31×1门控与子位置", "scalar_restore_v3/pc_candidate_compact/restore_power.py", "mean=(convolve(z,np.ones((31,1)"),
    ("40维展开与定点MLP", "scalar_restore_v3/pc_candidate_compact/restore_power.py", "def predict_gain_q14("),
    ("浮点MLP定义", "scalar_restore_v3/pc_candidate_compact/model_source.py", "class ScalarCorrector"),
    ("输入弱峰保护", "scalar_restore_v3/pc_candidate_compact/scalar_guard.py", "def apply_guard("),
    ("紧凑弱峰保护", "scalar_restore_v3/pc_candidate_compact/compact_guard.py", "def compact_peak_skip("),
    ("功率增益平方与饱和", "scalar_restore_v3/pc_candidate_compact/restore_power.py", "def apply_power("),
    ("被选训练原始快照", "scalar_restore_v2/runs/protected_patch5/training_source.py", "def main("),
    ("完整训练损失", "scalar_restore_v2/runs/protected_patch5/training_source.py", "goal=torch.log2"),
    ("训练幅值标签归一化", "scalar_restore_v2/common_v2.py", "def amplitudes("),
    ("数据配对与分组", "scalar_restore_v2/prepare_data.py", "def "),
    ("全帧误差指标", "scalar_streak_fix_v1/common.py", "def error_metrics("),
    ("目标与背景指标", "scalar_restore_v2/evaluate.py", "def measures("),
    ("HLS MLP", "radar1_scalar_compact_exp_v1/hls/scalar_compact.cpp", "static unsigned predict("),
    ("HLS保护函数", "radar1_scalar_compact_exp_v1/hls/scalar_compact.cpp", "static unsigned protect("),
    ("HLS natural/shift列换算", "radar1_scalar_compact_exp_v1/hls/scalar_compact.cpp", "NORMALIZE:"),
    ("HLS最后统一写回", "radar1_scalar_compact_exp_v1/hls/scalar_compact.cpp", "APPLY:"),
    ("成像帧所有权与跳帧", "radar1_scalar_compact_exp_v1/rtl/network_frame_control.v", "module network_frame_control"),
    ("原始RGB网络卷积尺寸", "cdqob_pc_online_v1/model.py", "expected ="),
    ("原始RGB网络输出头", "cdqob_pc_online_v1/model.py", "return tf.clip_by_value"),
]
lines = ["# 源码定位表", "", "由只读审计脚本自动生成。文件散列见 reports/SOURCE_AUDIT.json；下列定位为实际代码行。", "",
         "| 要理解的内容 | 源码入口 |", "|---|---|"]
for label, rel, pat in anchors:
    source = (ROOT/rel).read_text(encoding="utf-8-sig").splitlines()
    n = next((i+1 for i,s in enumerate(source) if pat in s), None)
    if n is None:
        raise ValueError((rel, pat))
    lines.append(f"| {label} | [{Path(rel).name} 第{n}行]({(ROOT/rel).as_posix()}:{n}) |")
(HERE/"06_源码定位表.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
print(json.dumps(dict(status=summary["status"],checks=checks,training=summary["training"],
    parameters=int(parameter_count),macs=int(macs)), ensure_ascii=False))
if not all(checks.values()):
    raise SystemExit(1)
