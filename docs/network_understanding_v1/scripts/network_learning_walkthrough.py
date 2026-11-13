"""Explain two EXISTING records and the protection algebra; no new inference."""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
VISUAL = Path('C:/Users/yang/.codex/visualizations/2026/10/31/01a19048-6a4d-7101-874c-4be4ef20d10a/network-gain-walkthrough.html')

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4*1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def w(g):
    return min(1.0,max(0.0,4*g-1))

source_paths = [HERE/'reports'/name for name in [
    'FEATURE_WALKTHROUGH.json','POINT_TRACE.json',
    'TRAINING_GUARD_WALKTHROUGH.json','LEARNED_RULE_WALKTHROUGH.json',
    'POINT_REFERENCE_WALKTHROUGH.json']]
features, trace, guards, learned, references = map(read,source_paths)
points = []
for label,position in [('A',[25,0]),('B',[200,148])]:
    feature = next(row for row in features['actual_point_checks'] if row['position']==position)
    point = next(row for row in trace['rows'] if [row['natural_range_bin'],row['natural_doppler_bin']]==position)
    guard = next(row for row in guards['existing_guard_points'] if row['position']==position)
    network = next(row for row in learned['rows'] if row['position']==position)
    reference = next(row for row in references['point_rows'] if row['position']==position)
    f = [v/65536 for v in point['feature_q16']]
    gain0 = point['raw_gain_q14']/16384
    gain1 = point['first_guard_gain_q14']/16384
    gain2 = point['final_gain_q14']/16384
    assert f == [v/65536 for v in feature['mlp_q16']]
    assert [gain0,gain1,gain2] == [network['raw_gain'],network['first_guard_gain'],network['final_gain']]
    assert guard['first_eligible'] and guard['compact_eligible']
    compactness = guard['compactness_q12']/4096
    lam1 = w(gain0)
    lam2 = compactness*w(gain1)
    lam = 1-(1-lam1)*(1-lam2)
    conceptual_g1 = gain0+(1-gain0)*lam1
    conceptual_g2 = gain1+(1-gain1)*lam2
    assert abs(conceptual_g1-gain1)<0.0002
    assert abs(conceptual_g2-gain2)<0.0002
    assert abs((1-lam)*gain0+lam-gain2)<0.0003
    points.append(dict(id=label,position=position,center=f[0],
        feature_values=f,features_shown=[dict(index=i,label=name,value=f[i]) for i,name in
            [(0,'中心'),(2,'3×3均值'),(3,'9×9均值'),(4,'三次父'),(5,'五次父'),(6,'三次子'),(7,'五次子')]],
        score=point['raw_score_real'],active_neurons=[network['first_layer_active'],network['second_layer_active']],
        gains=[1.0,gain0,gain1,gain2],power_ratios=[1.0,gain0**2,gain1**2,gain2**2],
        guard_eligible=[guard['first_eligible'],guard['compact_eligible']],
        compactness=compactness,first_blend_weight=lam1,second_blend_weight=lam2,
        combined_blend_weight=lam,
        conceptual_real_gains=[conceptual_g1,conceptual_g2],
        source_records_match=True,physical_target_status='Unknown',
        input_relative_amplitude=reference['input_relative_amplitude'],
        reference_relative_amplitude=reference['reference_relative_amplitude'],
        reference_to_input_ratio=reference['reference_to_input_ratio'],
        stage_amplitudes=[reference['stages'][name]['relative_amplitude']
                          for name in ['bypass','mlp','first_guard','compact']],
        stage_absolute_errors=[reference['stages'][name]['absolute_error']
                               for name in ['bypass','mlp','first_guard','compact']]))

# A constructed scalar example explains the risk, not a new test of the MLP.
X,g,c = 0.01,0.4,1.0
g1 = g+(1-g)*w(g)
g2 = g1+(1-g1)*c*w(g1)
examples = []
for name,Y in [('输入幅值恰好正确',0.01),('MLP幅值恰好正确',0.004),('参考位于两者之间',0.006)]:
    predicted = [X*g,X*g1,X*g2]
    errors = [(v-Y)**2 for v in predicted]
    delta = predicted[1]-predicted[0]
    algebra = 2*delta*(predicted[0]-Y)+delta**2
    assert abs(errors[1]-errors[0]-algebra)<1e-18
    lam1 = w(g)
    lam2 = c*w(g1)
    combined = 1-(1-lam1)*(1-lam2)
    blended = (1-combined)*predicted[0]+combined*X
    regularized_derivative = 2*((1-combined)*(blended-predicted[0])+combined*(blended-X))
    assert abs(blended-predicted[2])<1e-15 and abs(regularized_derivative)<1e-15
    examples.append(dict(label=name,input_amplitude=X,reference_amplitude=Y,
        hypothetical_mlp_gain=g,compactness=c,
        gains=[g,g1,g2],output_amplitudes=predicted,squared_errors=errors,
        soft_guard_error_change=errors[1]-errors[0],
        soft_guard_error_change_algebra=algebra,
        soft_guard_improves=errors[1]<errors[0],
        second_guard_improves_over_first=errors[2]<errors[1],
        combined_blend_weight=combined,
        weighted_square_stationarity_residual=regularized_derivative,
        scope='Constructed scalar example, not model inference or radar evidence'))

blend_examples = []
for gain in [0.125,0.25,0.3,0.4,0.49,0.7,0.99]:
    for compactness in [0.0,0.25,0.7,1.0]:
        lam1 = w(gain)
        first = (1-lam1)*gain+lam1
        lam2 = compactness*w(first)
        second = (1-lam2)*first+lam2
        combined = 1-(1-lam1)*(1-lam2)
        blended = (1-combined)*gain+combined
        stationary = 2*((1-combined)*(blended-gain)+combined*(blended-1))
        assert abs(blended-second)<1e-15 and abs(stationary)<1e-15
        blend_examples.append(dict(raw_gain=gain,compactness=compactness,
            combined_blend_weight=combined,final_gain=second,
            combination_residual=blended-second,stationarity_residual=stationary))

baseline = read(HERE/'reports/SOURCE_BASELINE.json')
changed = [rel for rel,entry in baseline.items() if sha(ROOT/rel)!=entry['sha256']]
checks = dict(
    two_existing_records_match=all(p['source_records_match'] for p in points),
    center_exactly_equal=points[0]['center']==points[1]['center'],
    all_other_features_not_equal=points[0]['feature_values']!=points[1]['feature_values'],
    scores_and_raw_gains_differ=points[0]['score']!=points[1]['score'] and points[0]['gains'][1]!=points[1]['gains'][1],
    stronger_parent_hints_not_sufficient_to_order_gains=all(points[0]['feature_values'][i]>points[1]['feature_values'][i] for i in [4,5]) and points[0]['gains'][1]>points[1]['gains'][1],
    both_final_gains_return_to_input=points[0]['gains'][3]==points[1]['gains'][3]==1,
    saved_reference_stage_gains_match=all(abs(p['stage_amplitudes'][i]/p['input_relative_amplitude']-p['gains'][i])<1e-9 for p in points for i in range(4)),
    saved_reference_error_direction_matches=points[0]['stage_absolute_errors'][3]<points[0]['stage_absolute_errors'][1] and points[1]['stage_absolute_errors'][3]>points[1]['stage_absolute_errors'][1],
    saved_reference_used_for_evaluation_only=True,
    blend_weights_are_bounded=all(0<=p[k]<=1 for p in points for k in ['first_blend_weight','second_blend_weight','combined_blend_weight']),
    protecting_input_can_help_or_hurt=examples[0]['soft_guard_improves'] and not examples[1]['soft_guard_improves'],
    second_guard_can_reverse_a_first_guard_improvement=examples[2]['soft_guard_improves'] and not examples[2]['second_guard_improves_over_first'],
    blend_is_weighted_square_minimizer=all(abs(row['stationarity_residual'])<1e-15 for row in blend_examples) and any(0<row['combined_blend_weight']<1 for row in blend_examples),
    frozen_sources_unchanged=not changed)
payload = dict(schema=1,source='Two already traced points; no new model evaluation',
    points=points,feature_count=40,architecture=[40,32,16,1],
    stage_labels=['输入','MLP输出','软保护后','紧凑保护后'])
fragment = VISUAL.read_text(encoding='utf-8')
serialized = json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
fragment,replacements = re.subn(
    r'(<script type="application/json" id="network-gain-data">)[\s\S]*?(</script>)',
    lambda match:match.group(1)+serialized+match.group(2),fragment)
assert replacements==1
assert '\\"' not in fragment and '<html' not in fragment.lower() and len(fragment.encode('utf-8'))<1_000_000
VISUAL.write_text(fragment,encoding='utf-8')
report = dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,
    scope='Read-only explanation of existing records and scalar protection algebra',
    visual_payload=payload,conceptual_scalar_examples=examples,
    blend_algebra_examples=blend_examples,
    source_sha256={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in source_paths},
    visual_path=str(VISUAL),visual_sha256=sha(VISUAL),
    frozen_files_checked=len(baseline),changed_sources=changed,
    model_parameters_modified=False,training_run=False,fft_run=False,
    feature_extraction_run=False,neural_inference_run=False,
    new_quality_test_run=False,new_holdout_opened=False,
    hardware_built=False,board_accessed=False)
(HERE/'reports/NETWORK_LEARNING_WALKTHROUGH.json').write_text(
    json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=report['status'],checks=checks,
    points=[{k:p[k] for k in ['id','position','center','score','gains','first_blend_weight','second_blend_weight','compactness']} for p in points],
    scalar_examples=examples),ensure_ascii=False))
if not all(checks.values()):
    raise SystemExit(1)
