import sys
sys.dont_write_bytecode=True
from pathlib import Path
import hashlib,json,re,ast,struct,argparse
import numpy as np
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')

def main():
    p=argparse.ArgumentParser();p.add_argument('--prepare-cli',action='store_true');a=p.parse_args()
    # Use a nontrivial eight-target scene for the input-only reproducibility check.
    sample='007_n8_strong_weak'
    if a.prepare_cli:
        with np.load(ROOT/'data/test'/(sample+'.npz')) as d:
            np.savez_compressed(ROOT/'reports/CLI_INPUT_ONLY.npz',**{k:d[k] for k in ['sign_i','sign_q','base']})
        print('三字段CLI输入已准备：八目标强弱混合。');return
    frozen=read(ROOT/'FROZEN.json');cfg=read(ROOT/'PROTOCOL.json')
    for name,digest in frozen['sources'].items():assert sha(ROOT/name)==digest,name
    assert sha(ROOT.parent/cfg['baseline'])==frozen['model_sha256']
    assert sha(ROOT/'solver_v1_snapshot.py')==sha(ROOT.parent/'scalar_sign_evidence_v1/sign_solver.py')
    records=[];seeds=[];dependencies={};sign_count=0
    for split in ['development','validation','test']:
        manifest=read(ROOT/'data'/f'{split}_manifest.json')
        assert manifest['protocol_sha256']==frozen['sources']['PROTOCOL.json']
        dependencies.update(manifest['generation_sources'])
        for meta in manifest['records']:
            seeds.append(meta['seed']);file=Path(meta['file']);assert sha(file)==meta['sha256']
            if split=='development':assert file.parent==ROOT.parent/'scalar_sign_evidence_v1/data/test'
            else:assert file.parent==ROOT/'data'/split
            row=read(ROOT/'reports'/split/(meta['id']+'.json'))
            assert row['sources']==frozen['sources'] and row['model_sha256']==frozen['model_sha256']
            arms={}
            for arm,path in row['solver_reports'].items():
                sr=read(Path(path));arms[arm]=sr
                fit=sr['fit_indices'];ev=sr['evidence_indices']
                assert len(fit)==len(ev)==4096 and len(set(fit+ev))==8192
                assert len(sr['candidates'])<=24
                assert sr['source_sha256']==meta['sha256']
                expected='solver_v1_snapshot.py' if arm=='v1' else 'solver.py'
                assert sr['code_sha256']==frozen['sources'][expected]
                if arm!='v1':assert sr['proposal']['proposal_indices']==fit
            n=arms['fft24']['proposal']['initial_count']
            assert n==arms['residual24']['proposal']['initial_count']<=16
            assert [r['integer'] for r in arms['fft24']['candidates'][:n]]==[r['integer'] for r in arms['residual24']['candidates'][:n]]
            with np.load(file,allow_pickle=False) as d:
                assert d['base'].dtype==d['reference'].dtype==np.dtype('u8')
                assert all(d[k].shape==(1024,512) for k in d.files)
                for c in ['i','q']:
                    assert np.array_equal(d['sign_'+c],np.where(d['adc_'+c]>=0,1,-1))
                    sign_count+=d['sign_'+c].size
            out=Path(row['arrays']);assert sha(out)==row['arrays_sha256']
            with np.load(out,allow_pickle=False) as d:
                assert all(np.isfinite(d[k]).all() and (d[k]>=0).all() for k in d.files)
                assert np.all(d['residual24_protect']>=d['old40'])
            if split=='test':
                for suffix in ['', '_interfaces']:
                    b=(ROOT/'results'/(meta['id']+suffix+'.png')).read_bytes()
                    assert b[:8]==b'\x89PNG\r\n\x1a\n'
                    w,h=struct.unpack('>II',b[16:24]);assert w>1000 and h>=500
            records.append(dict(split=split,id=meta['id'],input_sha256=meta['sha256'],output_sha256=row['arrays_sha256']))
    assert len(set(seeds))==len(seeds)==20
    for path,digest in dependencies.items():assert sha(Path(path))==digest,path
    for p in ROOT.glob('*.py'):ast.parse(p.read_text(encoding='utf8'))
    for p in ROOT.rglob('*.json'):read(p)
    for p in ROOT.glob('*.md'):
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf8')):
            if not link.startswith('http'):assert (p.parent/link).exists(),link
    for link in re.findall(r'(?:href|src)="([^"]+)"',(ROOT/'results/index.html').read_text(encoding='utf8')):
        assert (ROOT/'results'/link).exists(),link
    with np.load(ROOT/'reports/CLI_INPUT_ONLY.npz') as d:assert set(d.files)=={'sign_i','sign_q','base'}
    with np.load(ROOT/'reports/CLI_OUTPUT.npz') as actual,np.load(ROOT/'results/test'/(sample+'.npz')) as expected:
        errors={k:float(abs(actual[k]-expected[k]).max()) for k in actual.files}
        assert all(v<1e-6 for v in errors.values()),errors
    tree=ast.parse((ROOT/'solver.py').read_text(encoding='utf8'))
    solve=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='solve')
    assert [a.arg for a in solve.args.args]==['sign_i','sign_q','cfg']
    write(ROOT/'SOURCE_SNAPSHOT.json',dict(dependencies=dependencies,model_path=str(ROOT.parent/cfg['baseline']),
        model_sha256=frozen['model_sha256'],current_sources={str(p):sha(p) for p in ROOT.glob('*.py')}))
    report=dict(status='PASS',scope='实现与数据完整性，不代表质量或部署通过',frames=len(records),
        old_development_frames=2,new_validation_frames=6,new_frozen_test_frames=12,
        exact_sign_components_checked=sign_count,fit_evidence_disjoint=True,
        residual_proposal_uses_fit_only=True,same_initial16=True,max24_candidates=True,
        frozen_sources_unchanged=True,cli_scene=sample,cli_input_only_max_errors=errors,
        preflight=read(ROOT/'reports/PREFLIGHT.json'),visual_review=read(ROOT/'reports/VISUAL_CHECK.json'),
        records=records,quality_pass=read(ROOT/'reports/TEST_SUMMARY.json')['quality_pass'],deployment_ready=False)
    write(ROOT/'reports/STANDARD_CHECK.json',report)
    write(ROOT/'FILE_MANIFEST.json',dict(files=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p))
        for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='FILE_MANIFEST.json']))
    print('标准检查通过',dict(frames=len(records),cli_errors=errors,quality_pass=report['quality_pass']))

if __name__=='__main__':main()
