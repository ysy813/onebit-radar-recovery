"""Delivery integrity checks, separate from quality and deployment claims."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from experiment import np,read,write,sha,CFG,load_model,summarize
from infer import restore
import re,ast,subprocess,platform

def main():
    checks={};details={};ph=sha(ROOT/'PROTOCOL.json');test=read(ROOT/'reports/TEST.json');frozen=read(ROOT/'runs/FROZEN.json')
    manifests={s:read(ROOT/'data'/f'{s}_manifest.json') for s in ['train','validation','test']}
    checks['protocol_unchanged']=all(m['protocol_sha256']==ph for m in manifests.values()) and frozen['protocol_sha256']==ph
    checks['168_frames_correct_splits']=[len(manifests[s]['records']) for s in ['train','validation','test']]==[96,24,48]
    seeds=[r['seed'] for m in manifests.values() for r in m['records']]
    checks['unique_seeds']=len(set(seeds))==len(seeds)
    checks['data_hashes']=all(sha(ROOT/r['file'])==r['sha256'] for m in manifests.values() for r in m['records'])
    checks['no_duplicate_pairs']=len({r['sha256'] for m in manifests.values() for r in m['records']})==len(seeds)
    valid=True
    for m in manifests.values():
        for r in m['records']:
            with np.load(ROOT/r['file']) as d:
                valid &= all(d[k].shape==(1024,512) and d[k].dtype==np.dtype('u8') for k in ['reference','base'])
    checks['pair_format']=bool(valid)
    counts={k:sum(p.numel() for p in load_model(v['path']).parameters()) for k,v in frozen['arms'].items()}
    checks['parameter_counts']=all(v==(2113 if '48' in k else 1857) for k,v in counts.items());details['parameters']=counts
    checks['frozen_weights']=all(sha(v['path'])==v['sha256']==test['models'][k] for k,v in frozen['arms'].items())
    checks['test_after_freeze']=all((ROOT/r['file']).stat().st_mtime>=(ROOT/'runs/FROZEN.json').stat().st_mtime for r in manifests['test']['records'])
    completed=[read(ROOT/'runs'/k/'COMPLETE.json') for k in CFG['arms']]
    checks['training_sources_unchanged']=all(c['code_sha256']==sha(ROOT/'experiment.py') and c['feature_sha256']==sha(ROOT/'features48.py') and c['model_sha256']==sha(ROOT/'model48.py') and c['protocol_sha256']==ph for c in completed)
    checks['same_pool_initialization']=all(c['pool_sha256']==sha(ROOT/'data/train_pool.npy') and c['initial_sha256']==CFG['initial_sha256'] for c in completed)
    checks['summary_recomputed']=summarize(test['rows'])==test['summary']
    checks['array_hashes']=all(sha(r['arrays'])==r['arrays_sha256'] for r in test['rows'])
    checks['finite_arrays']=True
    for row in test['rows']:
        with np.load(row['arrays']) as d:
            checks['finite_arrays'] &= all(bool(np.isfinite(d[k]).all() and (d[k]>=0).all()) for k in d.files)
    with np.load(ROOT/'data/train_sample_origin.npz') as d:origin=d['mapping']
    p=np.load(ROOT/'data/train_pool.npy',mmap_mode='r');pool=read(ROOT/'data/POOL.json')
    checks['pool_mapping']=bool(origin.shape==(96*8192,4) and p.shape==(96*8192,53) and (origin[:,0]<96).all() and (origin[:,1]<524288).all() and (origin[:,2]<7).all() and (origin[:,3]<=1).all())
    checks['pool_mapping_hash']=sha(ROOT/'data/train_sample_origin.npz')==pool['origin_sha256'] and sha(ROOT/'data/train_pool.npy')==pool['sha256']
    audit=read(ROOT/'reports/FEATURE_AUDIT.json')
    checks['feature_implementation_audit']=audit['status']=='PASS' and audit['feature_code_sha256']==sha(ROOT/'features48.py') and audit['guard_max_gain_error']<=.001
    details['geometry_quality_not_integrity_gate']=audit['geometry_summary']
    row=manifests['test']['records'][0];cli=ROOT/'results/cli_example.npz'
    if not cli.exists():
        result=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'infer.py'),'--input',str(ROOT/row['file']),'--output',str(cli)],capture_output=True,text=True,encoding='utf8')
        checks['independent_cli_success']=result.returncode==0;details['cli_stdout']=result.stdout
        if result.returncode:details['cli_stderr']=result.stderr
    else:checks['independent_cli_success']=True
    with np.load(cli) as d,np.load(test['rows'][0]['arrays']) as ref:
        err=float(abs(d['relative_amplitude']-ref['f48_repair_guard']).max())
        details['cli_max_amplitude_error']=err;checks['independent_cli_matches']=err<=2e-7
        checks['gain_bounds']=bool(d['gain_q14'].min()>=2048 and d['gain_q14'].max()<=24576)
    q,power,rel=restore(np.zeros((1024,512),'u8'),ROOT/'candidate/f48_repair/model_float.pt')
    checks['zero_frame']=bool((q==16384).all() and not power.any() and not rel.any())
    page=(ROOT/'results/index.html').read_text(encoding='utf8')
    links=re.findall(r'(?:src|href)="([^"]+)"',page)
    checks['gallery_links']=all((ROOT/'results'/x).exists() for x in links)
    checks['all_test_figures']=all((ROOT/'results'/(r['id']+'.png')).exists() for r in test['rows'])
    for path in ROOT.glob('*.py'):ast.parse(path.read_text(encoding='utf8'))
    checks['python_syntax']=True
    old=ROOT.parent/'scalar_constraints_v2';oldfiles=read(old/'FILE_MANIFEST.json')['files']
    changed=[name for name,value in oldfiles.items() if not (old/name).exists() or sha(old/name)!=value]
    checks['previous_experiment_unchanged']=not changed;details['previous_changed_files']=changed
    oldseeds={r['seed'] for s in ['train','validation','test'] for r in read(old/'data'/f'{s}_manifest.json')['records']}
    checks['seeds_disjoint_from_previous']=not set(seeds)&oldseeds
    snapshot=[]
    for path in (ROOT/'source').rglob('*'):
        if not path.is_file():continue
        source=old/'source'/path.relative_to(ROOT/'source')
        if path.name=='v2_protocol.json':source=old/'PROTOCOL.json'
        snapshot.append(dict(copy=str(path),source=str(source),sha256=sha(path),source_sha256=sha(source)))
    for copy,source in [(ROOT/'reference_v2.py',old/'experiment.py'),(ROOT/'initial/joint40.pt',old/'candidate/joint/model_float.pt'),(ROOT/'initial/clean40.pt',old/'initial/model_float.pt')]:
        snapshot.append(dict(copy=str(copy),source=str(source),sha256=sha(copy),source_sha256=sha(source)))
    checks['source_snapshot_matches']=all(r['sha256']==r['source_sha256'] for r in snapshot)
    write(ROOT/'SOURCE_SNAPSHOT.json',dict(files=snapshot))
    write(ROOT/'reports/STANDARD_CHECK.json',dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,details=details,quality_pass=test['primary_quality_pass'],feature_value=test['feature_value'],deployment_ready=False,python=platform.python_version()))
    write(ROOT/'BUILD_STATUS.json',dict(status='PC_48_FEATURE_ABLATION_COMPLETED',integrity_pass=all(checks.values()),quality_pass=test['primary_quality_pass'],feature_value=test['feature_value'],deployment_ready=False,bit_rebuilt=False,board_accessed=False,primary='candidate/f48_repair/model_float.pt',integer_multitarget_coordinate_regression=True))
    files={p.relative_to(ROOT).as_posix():sha(p) for p in ROOT.rglob('*') if p.is_file() and p.name!='FILE_MANIFEST.json'}
    write(ROOT/'FILE_MANIFEST.json',dict(files=files,description='完整交付文件SHA256，不含本文件自身；质量判据单独记录。'))
    print('标准检查',read(ROOT/'reports/STANDARD_CHECK.json'),flush=True)
    if not all(checks.values()):raise SystemExit(1)

if __name__=='__main__':main()
