"""Compare score gradients at two specified amplitudes; no MLP or training."""
import sys
sys.dont_write_bytecode = True
import ast
import copy
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
SOURCE = ROOT/"scalar_restore_v2/runs/protected_patch5/training_source.py"

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4*1024*1024), b""):
            h.update(block)
    return h.hexdigest()

tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
main = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name == "main")
loop = next(n for n in main.body if isinstance(n,ast.For) and any(
    isinstance(t,ast.Assign) and any(isinstance(v,ast.Name) and v.id == "goal" for v in t.targets)
    for t in n.body))
start = next(i for i,n in enumerate(loop.body) if isinstance(n,ast.Assign) and any(
    isinstance(v,ast.Name) and v.id == "g" for v in n.targets))
end = next(i for i,n in enumerate(loop.body) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
    and isinstance(n.value.func,ast.Attribute) and isinstance(n.value.func.value,ast.Name)
    and n.value.func.value.id == "opt")
nodes = copy.deepcopy(loop.body[start:end])
first_loss = next(n for n in nodes if isinstance(n,ast.Assign) and any(
    isinstance(v,ast.Name) and v.id == "loss" for v in n.targets))

def split_add(node):
    if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Add):
        return split_add(node.left)+split_add(node.right)
    return [node]

expressions = split_add(first_loss.value)
assert len(expressions) == 3
nodes.append(ast.Assign(targets=[ast.Name(id="base_terms",ctx=ast.Store())],
                        value=ast.List(elts=copy.deepcopy(expressions),ctx=ast.Load())))
code = compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(SOURCE),"exec")
env = dict(torch=torch,F=F,net=SimpleNamespace(boost=True),a=SimpleNamespace(protect_strength=20.))
env["raw"] = torch.tensor([[-1.],[-1.]],dtype=torch.float64,requires_grad=True)
env["x"] = torch.tensor([[.1],[.001]],dtype=torch.float64)
env["y"] = torch.tensor([[.12],[.0012]],dtype=torch.float64)
for name in ["support","known","low","centers","excess"]:
    env[name] = torch.zeros((2,1),dtype=torch.float64)
exec(code,env)
names = ["log2_gain_head","log_amplitude","amplitude_squared"]
gradients = {name:torch.autograd.grad(term,env["raw"],retain_graph=True)[0].detach().numpy()[:,0]
             for name,term in zip(names,env["base_terms"])}
x = env["x"].numpy()[:,0]
y = env["y"].numpy()[:,0]
prediction = env["pred"].detach().numpy()[:,0]
goals = env["goal"].numpy()[:,0]
raw = env["raw"].detach().numpy()[:,0]
w = env["w"].numpy()[:,0]
weight = w/w.sum()
analytic = dict(
    log2_gain_head=.35*weight*np.clip(raw-goals,-1,1),
    log_amplitude=.2*weight*np.sign(prediction-y)*prediction*math.log(2)/(.001+prediction),
    amplitude_squared=40*weight*(prediction-y)*prediction*math.log(2))
rows = [dict(input_amplitude=float(x[i]),reference_amplitude=float(y[i]),
             reference_to_input_ratio=float(y[i]/x[i]),specified_score=float(raw[i]),
             specified_gain=.5,predicted_amplitude=float(prediction[i]),
             unclipped_ratio_target=math.log2(y[i]/x[i]),smoothed_clipped_target=float(goals[i]),
             score_derivatives={name:float(gradients[name][i]) for name in names}) for i in range(2)]
ratios = {name:float(abs(gradients[name][1]/gradients[name][0])) for name in names}
baseline = read(HERE/"reports/SOURCE_BASELINE.json")
changed = [p for p,info in baseline.items() if sha(ROOT/p) != info["sha256"]]
config_path = ROOT/"scalar_restore_v2/runs/soft_patch5/config.json"
checks = dict(
    source_matches_selected_snapshot=sha(SOURCE) == read(config_path)["code_sha256"],
    three_source_derivatives_match_independent_formulas=all(np.max(np.abs(gradients[n]-analytic[n])) < 1e-13 for n in names),
    common_relative_error_and_gain=all(abs(row["reference_to_input_ratio"]-1.2)<1e-14 for row in rows),
    amplitude_gradient_scales_quadratically=abs(ratios["amplitude_squared"]-1e-4)<1e-16,
    log_gradient_ratio_matches_offset_formula=abs(ratios["log_amplitude"]-(.0005/.0015)/(.05/.051))<1e-14,
    head_equal_in_this_smooth_l1_linear_regime=abs(ratios["log2_gain_head"]-1)<1e-14,
    epsilon_breaks_exact_ratio_target_invariance=goals[0] != goals[1],
    all_other_loss_terms_zero_for_specified_masks=abs(float(env["loss"].detach())-
        sum(float(t.detach()) for t in env["base_terms"]))<1e-14,
    frozen_sources_unchanged=not changed)
checks = {k:bool(v) for k,v in checks.items()}
sources = ["scalar_restore_v2/runs/protected_patch5/training_source.py",
           "scalar_restore_v2/runs/soft_patch5/config.json"]
result = dict(status="PASS" if all(checks.values()) else "FAIL",checks=checks,
              scope="Specified equal-weight two-score batch; all masks set to zero for algebra, not real training statistics",
              rows=rows,weak_to_strong_absolute_gradient_ratios=ratios,
              qualifications=["These are specified scores, not current MLP predictions",
                              "Masks and equal weights are held fixed; actual selection and normalized denominators may differ",
                              "The comparison concerns partial score derivatives, not MLP parameter updates or Adam steps",
                              "Log loss still gives vanishing score gradients as predicted amplitude tends to zero",
                              "Head gradients are equal here because both residuals are in the same SmoothL1 linear branch",
                              "The epsilon and valid-input cutoff prevent exact scale invariance of all head supervision",
                              "No component ablation benefit or actual weak-target learning rate is measured"],
              source_sha256={p:sha(ROOT/p) for p in sources},script_sha256=sha(Path(__file__)),
              frozen_files_checked=len(baseline),changed_sources=changed,
              constructed_score_autograd_run=True,model_instantiated=False,model_backward_run=False,
              optimizer_run=False,training_run=False,model_parameters_modified=False,
              radar_data_read=False,radar_fft_run=False,feature_extraction_run=False,
              neural_inference_run=False,new_quality_test_run=False,new_holdout_opened=False,
              hardware_built=False,board_accessed=False,original_full_quality_status_preserved="FAIL")
(HERE/"reports/LOSS_SCALE_WALKTHROUGH.json").write_text(
    json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
print(json.dumps({k:result[k] for k in ["status","checks","rows","weak_to_strong_absolute_gradient_ratios"]},ensure_ascii=False))
if result["status"] != "PASS":
    raise SystemExit(1)
