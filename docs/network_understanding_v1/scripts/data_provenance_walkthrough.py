"""Audit frozen training provenance. Hash/read metadata and tensor constants only."""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
import torch

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
V2 = ROOT/'scalar_restore_v2'
V3 = ROOT/'scalar_restore_v3'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(4*1024*1024),b''):
            h.update(block)
    return h.hexdigest()

def headers(path):
    result = {}
    with zipfile.ZipFile(path) as archive:
        for name in ['reference.npy','base.npy','features.npy']:
            with archive.open(name) as stream:
                version = np.lib.format.read_magic(stream)
                reader = np.lib.format.read_array_header_1_0 if version==(1,0) else np.lib.format.read_array_header_2_0
                shape,fortran,dtype = reader(stream)
                result[name[:-4]] = dict(shape=list(shape),dtype=str(dtype),fortran_order=bool(fortran))
    return result

config_path = V2/'runs/soft_patch5/config.json'
manifest_path = V2/'manifest.json'
compact_manifest_path = V3/'compact_test_manifest.json'
config,manifest,compact = map(read,[config_path,manifest_path,compact_manifest_path])
by_id = {row['id']:row for row in manifest['records']}
assert len(by_id)==len(manifest['records'])
selected = config['training_records']
assert len({row['id'] for row in selected})==len(selected)
training_rows = []
for record in selected:
    row = by_id[record['id']]
    path = V2/row['file']
    meta = headers(path)
    digest = sha(path)
    family = ('prior_controlled' if row['id'].startswith('prior_') else
        'historical_capture' if row['group']=='historical_development' else
        'field_capture' if row['group']=='field_temporal' else 'new_synthetic')
    training_rows.append(dict(id=row['id'],split=row['split'],group=row['group'],family=family,
        actual_chirps=row['actual_chirps'],samples=record['samples'],
        source_frame_zero_based=row.get('source_frame_zero_based'),seed=row.get('seed'),
        rx_id=row.get('rx_id'),layout_assumed=row.get('layout_assumed'),
        raw_frame_sha256=row.get('raw_frame_sha256'),
        pair_path=str(path.relative_to(ROOT)).replace('\\','/'),pair_bytes=path.stat().st_size,
        pair_sha256=digest,pair_hash_matches_manifest=digest==row['sha256'],
        pair_hash_matches_selected_training=digest==record['pair_sha256'],headers=meta))

field = [row for row in manifest['records'] if row['group']=='field_temporal']
field_compact = [row for row in compact['records'] if row['group']=='field_temporal']
raw_split = defaultdict(set)
frame_split = defaultdict(set)
frame_hashes = defaultdict(set)
for row in field:
    raw_split[row['raw_frame_sha256']].add(row['split'])
    frame_split[row['source_frame_zero_based']].add(row['split'])
    frame_hashes[row['source_frame_zero_based']].add(row['raw_frame_sha256'])
split_frames = {split:sorted({row['source_frame_zero_based'] for row in field if row['split']==split})
    for split in ['train','validation','temporal_test']}
split_seeds = {split:sorted({row['seed'] for row in manifest['records'] if row['group']=='synthetic' and row['split']==split})
    for split in ['train','validation']}
compact_seeds = sorted({row['seed'] for row in compact['records'] if row['group']=='synthetic'})
train_field_hashes = {row['raw_frame_sha256'] for row in field if row['split']=='train'}
compact_field_hashes = {row['raw_frame_sha256'] for row in field_compact}

# Recheck recorded source payload hashes without decoding, FFT or analysis.
raw_path = ROOT/'radar1_v7_offline_compare_v1/data/radar_raw.bin'
raw_frame_bytes = 128*1024*2*4
expected_raw = defaultdict(set)
for row in field+field_compact:
    expected_raw[row['source_frame_zero_based']].add(row['raw_frame_sha256'])
raw_checks = []
with raw_path.open('rb') as stream:
    for frame,expected in sorted(expected_raw.items()):
        stream.seek(frame*raw_frame_bytes)
        payload = stream.read(raw_frame_bytes)
        digest = hashlib.sha256(payload).hexdigest()
        raw_checks.append(dict(frame_zero_based=frame,bytes=len(payload),sha256=digest,
            recorded_hashes=sorted(expected),matches=len(payload)==raw_frame_bytes and expected=={digest}))

rel_checkpoints = {
    'v7':'scalar_enhance_v1/release/scalar_gain_v7_candidate/model_float.pt',
    'guarded_initial':'scalar_restore_v2/runs/guarded_patch5/step_00000.pt',
    'guarded_final':'scalar_restore_v2/runs/guarded_patch5/step_50000.pt',
    'protected_initial':'scalar_restore_v2/runs/protected_patch5/step_00000.pt',
    'protected_final':'scalar_restore_v2/runs/protected_patch5/step_30000.pt',
    'selected':'scalar_restore_v2/runs/soft_patch5/step_30000.pt',
    'current':'scalar_restore_v3/pc_candidate_compact/model_float.pt',
}
checkpoints = {key:torch.load(ROOT/rel,map_location='cpu',weights_only=True) for key,rel in rel_checkpoints.items()}
checkpoint_meta = {key:dict(path=rel,sha256=sha(ROOT/rel),step=checkpoints[key].get('step'),
    parameter_count=sum(value.numel() for value in checkpoints[key]['state'].values()),
    shapes={name:list(value.shape) for name,value in checkpoints[key]['state'].items()})
    for key,rel in rel_checkpoints.items()}
def states_equal(first,second):
    a,b = checkpoints[first]['state'],checkpoints[second]['state']
    return set(a)==set(b) and all(torch.equal(a[key],b[key]) for key in a)

guard_config_path = V2/'runs/guarded_patch5/config.json'
guard_config = read(guard_config_path)
protected_source = V2/'runs/protected_patch5/training_source.py'
guarded_source = V2/'runs/guarded_patch5/training_source.py'
g0 = checkpoints['guarded_initial']['state']
v7 = checkpoints['v7']['state']
source_paths = [config_path,manifest_path,compact_manifest_path,guard_config_path,
    protected_source,guarded_source,V2/'prepare_data.py',V2/'common_v2.py',
    V2/'runs/protected_patch5/model_source.py',
    V2/'freeze_soft.py',ROOT/'scalar_streak_fix_v1/common.py',
    ROOT/'scalar_streak_fix_v1/inspect_new_capture.py',
    ROOT/'scalar_streak_fix_v1/controlled.py',
    ROOT/'radar1_v7_fullrange_compare_v2/xfft_model.py',
    ROOT/'radar1_v7_fullrange_compare_v2/adapter.py']+[ROOT/rel for rel in rel_checkpoints.values()]
baseline = read(HERE/'reports/SOURCE_BASELINE.json')
changed = [rel for rel,entry in baseline.items() if sha(ROOT/rel)!=entry['sha256']]

counts = dict(families=dict(Counter(row['family'] for row in training_rows)),
    groups=dict(Counter(row['group'] for row in training_rows)),
    actual_chirps={str(n):sum(row['actual_chirps']==n for row in training_rows) for n in [128,512]},
    pair_records=len(training_rows),pool_entries=sum(row['samples'] for row in training_rows),
    field_unique_source_frames=len(split_frames['train']),
    field_rx_ids=sorted({row['rx_id'] for row in training_rows if row['group']=='field_temporal'}),
    field_layouts=sorted({row['layout_assumed'] for row in training_rows if row['group']=='field_temporal'}),
    historical_unique_source_frames=len({row['source_frame_zero_based'] for row in training_rows if row['group']=='historical_development'}),
    synthetic_unique_seeds=len(split_seeds['train']),
    selected_stage_optimizer_steps=checkpoints['selected']['step'],
    selected_stage_batch_size=3072,
    selected_stage_sample_presentations=checkpoints['selected']['step']*3072)
checks = dict(
    selected_manifest_hash_matches=sha(manifest_path)==config['manifest_sha256'],
    selected_records_exactly_all_train={row['id'] for row in training_rows}=={row['id'] for row in manifest['records'] if row['split']=='train'},
    selected_pair_files_match_all_hashes=all(row['pair_hash_matches_manifest'] and row['pair_hash_matches_selected_training'] for row in training_rows),
    paired_numeric_shapes_and_types=all(row['headers']['reference']['shape']==row['headers']['base']['shape']==[1024,512] and row['headers']['reference']['dtype']==row['headers']['base']['dtype']=='uint64' and row['headers']['features']['shape']==[8,524288] for row in training_rows),
    counts_verified=counts['pair_records']==62 and counts['pool_entries']==1396736 and counts['actual_chirps']=={'128':30,'512':32},
    same_raw_frame_split_consistent=all(len(splits)==1 for splits in raw_split.values()) and all(len(splits)==1 for splits in frame_split.values()),
    same_frame_layouts_use_same_payload=all(len(values)==1 for values in frame_hashes.values()),
    all_recorded_raw_payload_hashes_match=all(row['matches'] for row in raw_checks),
    train_validation_frames_disjoint=not(set(split_frames['train'])&set(split_frames['validation'])),
    train_temporal_test_frames_disjoint=not(set(split_frames['train'])&set(split_frames['temporal_test'])),
    train_compact_frames_disjoint=not(train_field_hashes&compact_field_hashes),
    train_validation_seeds_disjoint=not(set(split_seeds['train'])&set(split_seeds['validation'])),
    train_compact_seeds_disjoint=not(set(split_seeds['train'])&set(compact_seeds)),
    exact_training_snapshots=sha(protected_source)==config['code_sha256'] and sha(guarded_source)==guard_config['code_sha256'],
    v7_is_guarded_initial_source=checkpoint_meta['v7']['sha256']==guard_config['source_initial_sha256'],
    v7_first16_copied_and_new_columns_zero=torch.equal(g0['layers.0.weight'][:,:16],v7['layers.0.weight']) and int(torch.count_nonzero(g0['layers.0.weight'][:,16:]))==0,
    v7_hidden_biases_and_second_layer_copied=all(torch.equal(g0[key],v7[key]) for key in ['layers.0.bias','layers.2.weight','layers.2.bias']),
    guarded_output_head_reset=int(torch.count_nonzero(g0['layers.4.weight']))==0 and abs(float(g0['layers.4.bias'].item())+0.2)<1e-7,
    added_neighbor_columns_learned=int(torch.count_nonzero(checkpoints['current']['state']['layers.0.weight'][:,16:]))>0,
    selected_initial_source_verified=checkpoint_meta['guarded_final']['sha256']==config['source_initial_sha256'] and states_equal('protected_initial','guarded_final'),
    core_source_field_is_checkpoint_hash=checkpoint_meta['protected_final']['sha256']==config['core_source_sha256'],
    selected_neural_state_equals_protected=states_equal('selected','protected_final'),
    current_neural_state_equals_selected=states_equal('current','selected') and checkpoint_meta['current']['sha256']==checkpoint_meta['selected']['sha256'],
    current_network_1857_parameters=checkpoint_meta['current']['parameter_count']==1857,
    frozen_sources_unchanged=not changed)
result = dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,
    scope='Training provenance and source-payload/tensor audit only; not training, inference, or a new generalization result',
    counts=counts,training_records=training_rows,
    manifest_split_group_counts=dict(Counter(row['split']+'|'+row['group'] for row in manifest['records'])),
    field_split_frames=split_frames,synthetic_split_seeds=split_seeds,
    compact_test=dict(records=len(compact['records']),synthetic_seeds=compact_seeds,
        field_source_frames=sorted({row['source_frame_zero_based'] for row in field_compact}),
        field_records=len(field_compact),field_physical_layout_confirmed=all(row.get('physical_layout_confirmed',False) for row in field_compact),
        train_raw_payload_overlap=sorted(train_field_hashes&compact_field_hashes),
        note='Already examined historical test records; temporal separation within one capture is not independent-scene validation'),
    raw_payload_audit=dict(path=str(raw_path),frame_bytes=raw_frame_bytes,frames=raw_checks),
    checkpoints=checkpoint_meta,
    added_neighbor_weight_nonzero_count=int(torch.count_nonzero(checkpoints['current']['state']['layers.0.weight'][:,16:])),
    checkpoint_interpretation=dict(source_initial='guarded_patch5/step_50000.pt',
        core_source_sha256='Hash of protected_patch5/step_30000.pt, NOT a Python source-code hash',
        selected_stage='30,000 further optimizer steps after guarded 50,000-step stage',
        original_rgb_network='Not the teacher or target of the selected 62-record scalar-supervision stage; no full-history claim made here',
        model_float_metadata='soft checkpoint includes rule metadata; neural tensors match protected final exactly'),
    source_chain=['scalar_restore_v2/common_v2.py -> scalar_streak_fix_v1/common.py',
        'fft2 -> radar1_v7_fullrange_compare_v2/xfft_model.py -> Xilinx bit-accurate C model',
        'power64 -> radar1_v7_fullrange_compare_v2/adapter.py -> uint64 squared-magnitude arithmetic'],
    reference_boundary='Paired multibit numeric FFT output, not a clutter-free or physically complete target truth',
    missing_evidence=dict(selected_stage_loss_jsonl_exists=(V2/'runs/soft_patch5/loss.jsonl').exists(),
        all_unknown_real_targets_labeled=False,independent_scene_generalization_proved=False,
        full_earlier_pretraining_history_audited=False),
    source_sha256={str(path.relative_to(ROOT)).replace('\\','/'):sha(path) for path in source_paths},
    frozen_files_checked=len(baseline),changed_sources=changed,
    model_parameters_modified=False,training_run=False,fft_run=False,
    feature_extraction_run=False,neural_inference_run=False,
    new_quality_test_run=False,new_quality_holdout_evaluated=False,
    raw_payload_hashes_recomputed=True,checkpoint_tensors_read_only=True,
    hardware_built=False,board_accessed=False)
(HERE/'reports/DATA_PROVENANCE_WALKTHROUGH.json').write_text(
    json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=result['status'],checks=checks,counts=counts,
    split_frames=split_frames,compact_test=result['compact_test'],
    checkpoint_interpretation=result['checkpoint_interpretation']),ensure_ascii=False))
if not all(checks.values()):
    raise SystemExit(1)
