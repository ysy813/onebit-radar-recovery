"""Coordinate dependency envelopes and original CNN receptive field; no model."""
import sys
sys.dont_write_bytecode = True
import ast
import hashlib
import json
from fractions import Fraction
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4*1024*1024), b""):
            h.update(block)
    return h.hexdigest()

source_path = ROOT/"scalar_restore_v3/pc_candidate_compact/restore_power.py"
tree = ast.parse(source_path.read_text(encoding="utf-8"))
feature_function = next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name == "features")
index_expressions = {}
for node in ast.walk(feature_function):
    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
        name = node.targets[0].id
        if name in ["ri","ai"]:
            index_expressions[name] = compile(ast.Expression(body=node.value),str(source_path),"eval")
kernel_shapes = {tuple(ast.literal_eval(n.args[0])) for n in ast.walk(feature_function)
                 if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
                 and isinstance(n.func.value,ast.Name) and n.func.value.id == "np"
                 and n.func.attr == "ones"}
config = read(ROOT/"scalar_restore_v3/pc_candidate_compact/config.json")
nr, na = 1024,512

def box(center, half_r, half_a):
    return {((center[0]+dr)%nr,(center[1]+da)%na)
            for dr in range(-half_r,half_r+1) for da in range(-half_a,half_a+1)}

rows = []
all_source_centers_match = True
all_child_minkowski_sums_match = True
selected_groups = None
for point in [(131,37),(83,0),(774,511),(25,0),(200,148),(0,0),(1023,511)]:
    groups = {"local_statistics_and_neighbors":box(point,4,4)}
    centers_by_order = {}
    for h in [-3,5]:
        order = abs(h)
        centers = {(round(Fraction(point[0],h)+Fraction(kr*nr,order))%nr,
                    round(Fraction(point[1],h)+Fraction(ka*na,order))%na)
                   for kr in range(order) for ka in range(order)}
        source_centers = set()
        for kr in range(order):
            for ka in range(order):
                env = dict(np=np,r=np.array([point[0]]),a=np.array([point[1]]),h=h,
                           order=order,kr=kr,ka=ka)
                source_centers.add((int(eval(index_expressions["ri"],env)[0]),
                                    int(eval(index_expressions["ai"],env)[0])))
        all_source_centers_match &= source_centers == centers
        parent = set().union(*(box(c,1,1) for c in centers))
        child_center = (h*point[0]%nr,h*point[1]%na)
        # Max over 3x3 scores; each score reads a 31x1 mean around itself.
        child_explicit = set().union(*(box(c,15,0) for c in box(child_center,1,1)))
        child_rectangle = box(child_center,16,1)
        all_child_minkowski_sums_match &= child_explicit == child_rectangle
        groups[f"parent_{h}"] = parent
        groups[f"child_{h}"] = child_rectangle
        centers_by_order[str(h)] = dict(parent_candidate_centers=[list(c) for c in sorted(centers)],
                                       child_center=list(child_center))
    union = set().union(*groups.values())
    rows.append(dict(position=list(point),encoded_dependency_group_sizes={k:len(v) for k,v in groups.items()},
                     summed_group_sizes=sum(len(v) for v in groups.values()),
                     union_encoded_positions=len(union),overlap_count=sum(len(v) for v in groups.values())-len(union),
                     centers=centers_by_order))
    if point == (131,37):
        selected_groups = groups

# Compute maximum structural CNN receptive fields from the delivered source
# topology, without importing TensorFlow or loading its trained weights.
original = ROOT/"cdqob_pc_online_v1/model.py"
original_tree = ast.parse(original.read_text(encoding="utf-8"))
expected_shapes = next(ast.literal_eval(n.value) for n in ast.walk(original_tree)
                       if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id == "expected" for t in n.targets))
forward = next(n for n in ast.walk(original_tree) if isinstance(n,ast.FunctionDef) and n.name == "forward")
receptive_fields = {"inputs":1}
for n in forward.body:
    if not (isinstance(n,ast.Assign) and isinstance(n.value,ast.Call)
            and isinstance(n.value.func,ast.Name) and n.value.func.id == "conv"):
        continue
    value, index = n.value.args
    if isinstance(value,ast.Name):
        dependencies = [value.id]
    else:
        dependencies = [v.id for v in value.args[0].elts]
    kernel_index = ast.literal_eval(index)
    receptive_fields[n.targets[0].id] = max(receptive_fields[d] for d in dependencies)+expected_shapes[kernel_index][0]-1

outside = (900,400)
outside_is_outside = outside not in set().union(*selected_groups.values())
baseline = read(HERE/"reports/SOURCE_BASELINE.json")
changed = [p for p,info in baseline.items() if sha(ROOT/p) != info["sha256"]]
checks = dict(
    frozen_feature_configuration=config["context"] == 2 and config["feature_policy"] == "guarded_child",
    expected_local_kernel_shapes_present={(3,3),(9,9),(31,1)} <= kernel_shapes,
    rational_parent_centers_match_source_index_expressions=all_source_centers_match,
    child_31_by_1_plus_3_by_3_support_is_33_by_3=all_child_minkowski_sums_match,
    group_sizes_match_for_all_seven_positions=all(r["encoded_dependency_group_sizes"] == {
        "local_statistics_and_neighbors":81,"parent_-3":81,"child_-3":99,"parent_5":225,"child_5":99} for r in rows),
    union_upper_bound_holds=all(r["union_encoded_positions"] <= 585 for r in rows),
    selected_illustration_has_disjoint_groups=rows[0]["union_encoded_positions"] == 585,
    remote_scale_example_outside_conditional_support=outside_is_outside,
    delivered_cnn_maximum_receptive_fields_match=receptive_fields == {"inputs":1,"c1":1,"c2":3,"c3":7,"c4":13,"c5":21,"h":21},
    frozen_sources_unchanged=not changed)
checks = {k:bool(v) for k,v in checks.items()}
sources = ["scalar_restore_v3/pc_candidate_compact/restore_power.py",
           "scalar_restore_v3/pc_candidate_compact/config.json","cdqob_pc_online_v1/model.py"]
result = dict(status="PASS" if all(checks.values()) else "FAIL",checks=checks,
              scope="Structural dependency sets of encoded-field features and delivered CNN topology only",
              conditioning="Encoded field z treated as input; global normalization is a separate all-frame dependency",
              rows=rows,delivered_cnn_receptive_field_widths=receptive_fields,
              ideal_global_scale_example=dict(position_outside_selected_support=list(outside),
                  peak_power_multiplier=4,encoded_value_multiplier=4**(-.1),
                  assumption="Fixed point power and all local/associated raw values; only remote maximum rises; ideal continuous encoding"),
              qualifications=["Sets are possible structural reads, not empirical gradients or learned importance",
                              "Overlapping groups are deduplicated; 585 is not valid as a universal exact count",
                              "Actual max selection, gating, rounding, weights and protection may suppress dependence",
                              "Global peak normalization means the full raw-power dependency is not confined to these sets",
                              "A global scalar normalization does not provide an arbitrary learned global interaction",
                              "Local CNN 21x21 and scalar sparse sets do not imply equal information or comparable quality"],
              source_sha256={p:sha(ROOT/p) for p in sources},script_sha256=sha(Path(__file__)),
              frozen_files_checked=len(baseline),changed_sources=changed,
              coordinate_support_enumeration_run=True,source_index_expressions_evaluated=True,
              radar_data_read=False,radar_fft_run=False,full_feature_extraction_run=False,
              model_instantiated=False,neural_layer_run=False,neural_inference_run=False,
              training_run=False,model_parameters_modified=False,new_quality_test_run=False,
              new_holdout_opened=False,hardware_built=False,board_accessed=False,
              original_full_quality_status_preserved="FAIL")
(HERE/"reports/DEPENDENCY_SUPPORT_WALKTHROUGH.json").write_text(
    json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
print(json.dumps(dict(status=result["status"],checks=checks,
                     encoded_unions=[dict(position=r["position"],union=r["union_encoded_positions"],overlap=r["overlap_count"]) for r in rows],
                     original_cnn=receptive_fields),ensure_ascii=False))
if result["status"] != "PASS":
    raise SystemExit(1)
