"""Evaluate the frozen gain-head loss at three already saved scores.

This is post-hoc scalar arithmetic, not a replay of a training step. No MLP,
optimizer, feature extraction, FFT, new data selection or model update is run.
"""
import sys
sys.dont_write_bytecode = True
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import math
import torch
from torch.nn import functional as F

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

paths = {
    "source": ROOT/"scalar_restore_v2/runs/protected_patch5/training_source.py",
    "config": ROOT/"scalar_restore_v2/runs/soft_patch5/config.json",
    "trace": HERE/"reports/POINT_TRACE.json",
    "reference": HERE/"reports/POINT_REFERENCE_WALKTHROUGH.json",
}
assert sha(paths["source"]) == read(paths["config"])["code_sha256"]
tree = ast.parse(paths["source"].read_text(encoding="utf-8"))
assignments = {}
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        if node.targets[0].id in {"goal", "head"}:
            assert node.targets[0].id not in assignments
            assignments[node.targets[0].id] = node
code = compile(ast.fix_missing_locations(ast.Module(body=[assignments[k] for k in ["goal", "head"]], type_ignores=[])), str(paths["source"]), "exec")
trace = read(paths["trace"])
reference = read(paths["reference"])
rows = []
for position in [[774,511], [25,0], [200,148]]:
    saved = next(row for row in trace["rows"] if [row["natural_range_bin"],row["natural_doppler_bin"]] == position)
    pair = next(row for row in reference["point_rows"] if row["position"] == position)
    x, y, score = pair["input_relative_amplitude"], pair["reference_relative_amplitude"], saved["raw_score_real"]
    raw = torch.tensor([[score]], dtype=torch.float64, requires_grad=True)
    env = dict(torch=torch, F=F, net=SimpleNamespace(boost=True), raw=raw,
               x=torch.tensor([[x]],dtype=torch.float64), y=torch.tensor([[y]],dtype=torch.float64),
               w=torch.ones((1,1),dtype=torch.float64), valid=torch.tensor([[x>1e-5]]))
    exec(code, env)
    goal = min(.5849625,max(-3., math.log2((y+1e-5)/(x+1e-5))))
    residual = score-goal
    penalty = .35*(.5*residual**2 if abs(residual)<1 else abs(residual)-.5)
    derivative = .35*min(1.,max(-1.,residual))
    source_penalty = .35*env["head"]
    source_derivative = float(torch.autograd.grad(source_penalty,raw)[0].item())
    assert abs(float(env["goal"].item())-goal)<1e-13
    assert abs(float(source_penalty.detach())-penalty)<1e-13
    assert abs(source_derivative-derivative)<1e-13
    rows.append(dict(position=position,input_relative_amplitude=x,reference_relative_amplitude=y,
                     saved_score=score,smoothed_clipped_goal=goal,head_loss_single_point=penalty,
                     head_score_derivative_single_point=derivative,
                     isolated_negative_gradient_direction="increase score" if derivative<0 else "decrease score",
                     saved_mlp_gain=saved["raw_gain_q14"]/16384,
                     training_head_gain=2**min(.5849625,max(-3.,score)),
                     strictly_below_lower_limit=score < -3,
                     source_and_independent_formula_match=True))
baseline = read(HERE/"reports/SOURCE_BASELINE.json")
changed = [rel for rel,info in baseline.items() if sha(ROOT/rel)!=info["sha256"]]
checks = dict(source_matches_selected_training_snapshot=True,
              three_source_losses_and_derivatives_match=all(row["source_and_independent_formula_match"] for row in rows),
              saturated_score_head_direction_is_up=rows[0]["head_score_derivative_single_point"]<0 and rows[0]["strictly_below_lower_limit"],
              opposing_directions_at_same_center=rows[1]["head_score_derivative_single_point"]<0<rows[2]["head_score_derivative_single_point"],
              frozen_sources_unchanged=not changed)
report = dict(status="PASS" if all(checks.values()) else "FAIL",checks=checks,rows=rows,
              scope="Post-hoc head supervision at three saved development scores; not original training logs or a complete loss gradient",
              source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in paths.values()},
              script_sha256=sha(Path(__file__)),frozen_files_checked=len(baseline),changed_sources=changed,
              constructed_single_point_head_autograd_run=True,model_instantiated=False,
              model_backward_run=False,optimizer_run=False,training_run=False,model_parameters_modified=False,
              neural_inference_run=False,radar_fft_run=False,feature_extraction_run=False,
              new_quality_test_run=False,new_holdout_opened=False,hardware_built=False,board_accessed=False,
              original_full_quality_status_preserved="FAIL")
(HERE/"reports/SAVED_SCORE_SUPERVISION.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(dict(status=report["status"],rows=rows),ensure_ascii=False))
assert all(checks.values())
