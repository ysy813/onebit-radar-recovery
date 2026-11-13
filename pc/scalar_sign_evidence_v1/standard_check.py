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
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepare-cli',action='store_true');args=parser.parse_args()
    if args.prepare_cli:
        with np.load(ROOT/'data/test/000_single_grid_a.npz') as d:
            np.savez_compressed(ROOT/'reports/CLI_INPUT_ONLY.npz',**{k:d[k] for k in ['sign_i','sign_q','base']})
        print('已生成只含符号和输入功率的独立CLI输入。');return
    frozen=read(ROOT/'FROZEN.json');cfg=read(ROOT/'PROTOCOL.json')
    assert sha(ROOT/'sign_solver.py')==frozen['solver_sha256']
    assert sha(ROOT/'run_experiment.py')==frozen['driver_sha256']
    assert sha(ROOT/'PROTOCOL.json')==frozen['protocol_sha256']
    assert sha(ROOT.parent/cfg['baseline'])==frozen['model_sha256']
    all_seeds=[];frames=0;sign_count=0;dependencies={};reports=[]
    for split in ['development','validation','test']:
        manifest=read(ROOT/'data'/f'{split}_manifest.json')
        assert manifest['protocol_sha256']==frozen['protocol_sha256']
        dependencies.update(manifest['generator_code'])
        for meta in manifest['records']:
            frames+=1;all_seeds.append(meta['seed']);data=Path(meta['file']);assert sha(data)==meta['sha256']
            row=read(ROOT/'reports'/split/(meta['id']+'.json'))
            assert row['source_sha256']==meta['sha256'] and row['solver_sha256']==frozen['solver_sha256']
            assert row['model_sha256']==frozen['model_sha256']
            fit=row['solver']['fit_indices'];ev=row['solver']['evidence_indices']
            assert len(fit)==4096 and len(ev)==4096 and len(set(fit+ev))==8192
            with np.load(data,allow_pickle=False) as d:
                assert d['base'].dtype==np.dtype('u8') and d['reference'].dtype==np.dtype('u8')
                assert all(d[k].shape==(1024,512) for k in d.files)
                for c in ['i','q']:
                    assert np.array_equal(d['sign_'+c],np.where(d['adc_'+c]>=0,1,-1));sign_count+=d['sign_'+c].size
            ar=Path(row['arrays']);assert sha(ar)==row['arrays_sha256']
            with np.load(ar,allow_pickle=False) as d:
                assert all(np.isfinite(d[k]).all() and (d[k]>=0).all() for k in d.files)
            if split=='test':
                img=ROOT/'results'/(meta['id']+'.png');b=img.read_bytes();assert b[:8]==b'\x89PNG\r\n\x1a\n'
                w,h=struct.unpack('>II',b[16:24]);assert w>1000 and h>500
            reports.append(dict(split=split,id=meta['id'],input_sha256=meta['sha256'],output_sha256=row['arrays_sha256']))
    assert len(set(all_seeds))==len(all_seeds)==20
    for path,digest in dependencies.items():assert sha(Path(path))==digest
    for p in ROOT.glob('*.py'):ast.parse(p.read_text(encoding='utf8'))
    for p in ROOT.glob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf8')):
            if not target.startswith('http'):assert (p.parent/target).exists(),target
    for p in ROOT.glob('*.json'):read(p)
    with np.load(ROOT/'reports/CLI_INPUT_ONLY.npz') as inp:assert set(inp.files)=={'sign_i','sign_q','base'}
    with np.load(ROOT/'reports/CLI_OUTPUT.npz') as out,np.load(ROOT/'results/test/000_single_grid_a.npz') as expected:
        errors={k:float(abs(out[k]-expected[k]).max()) for k in out.files};assert all(v<1e-6 for v in errors.values()),errors
    # Source signatures document inference's lack of truth/reference arguments.
    tree=ast.parse((ROOT/'sign_solver.py').read_text(encoding='utf8'))
    solve=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='solve')
    assert [a.arg for a in solve.args.args]==['sign_i','sign_q','cfg']
    write(ROOT/'SOURCE_SNAPSHOT.json',dict(dependencies=dependencies,baseline=dict(path=str(ROOT.parent/cfg['baseline']),sha256=frozen['model_sha256']),
        current_sources={str(p):sha(p) for p in ROOT.glob('*.py')}))
    result=dict(status='PASS',scope='实现与数据完整性，不代表质量、原创性或部署通过',frames=frames,independent_scene_seeds=len(all_seeds),
        exact_sign_components_checked=sign_count,fit_evidence_disjoint=True,frozen_sources_unchanged=True,cli_input_only_max_errors=errors,
        gradient_check=read(ROOT/'reports/PREFLIGHT.json'),chinese_visual_review='另见VISUAL_CHECK.json',artifact_records=reports,
        quality_pass=read(ROOT/'reports/TEST_SUMMARY.json')['quality_pass'],deployment_ready=False)
    write(ROOT/'reports/STANDARD_CHECK.json',result)
    write(ROOT/'FILE_MANIFEST.json',dict(files=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='FILE_MANIFEST.json']))
    print('标准检查通过',dict(frames=frames,cli_errors=errors,quality_pass=result['quality_pass']))

if __name__=='__main__':main()
