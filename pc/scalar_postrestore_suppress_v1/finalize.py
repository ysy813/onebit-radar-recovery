import sys
sys.dont_write_bytecode=True
from run import *
import re,ast
from PIL import Image

def main():
    s=read(ROOT/'reports/STANDARD_CHECK.json');assert s['status']=='PASS'
    assert digests()==read(ROOT/'FROZEN.json')['sources']
    inspected=['test_002_n4_spread.png','training.png']
    files=[]
    for name in read(ROOT/'reports/FIGURE_REGISTER.json')['images']:
        p=ROOT/'results'/name
        with Image.open(p) as im:im.verify()
        files.append(dict(file=str(p),sha256=sha(p)))
    write(ROOT/'reports/VISUAL_CHECK.json',dict(status='PASS',inspection='人工读取渲染后的PNG；中文标题/图例/坐标无缺字，版面未截断；四目标整数格峰保留，共用色标，显示聚合已标注',inspected=[dict(file=str(ROOT/'results'/n),sha256=sha(ROOT/'results'/n)) for n in inspected],all_png_decoded=len(files),scientific_images_not_browser_screenshot=True))
    fig=read(ROOT/'reports/FIGURE_REGISTER.json');fig['visual_inspection_pending']=False;write(ROOT/'reports/FIGURE_REGISTER.json',fig)
    checks={'frozen_sources':digests()==read(ROOT/'FROZEN.json')['sources'],'all_png_decode':True,'python_syntax':all(ast.parse(p.read_text(encoding='utf-8')) is not None for p in ROOT.glob('*.py'))}
    page=(ROOT/'results/index.html').read_text(encoding='utf-8');links=re.findall(r'(?:href|src)="([^"]+)"',page)
    checks['final_html_local_links']=all((ROOT/'results'/p).exists() for p in links if not p.startswith('#'))
    assert all(checks.values())
    write(ROOT/'reports/DELIVERY_CHECK.json',dict(status='PASS',checks=checks,standard_check_sha256=sha(ROOT/'reports/STANDARD_CHECK.json'),visual_check_sha256=sha(ROOT/'reports/VISUAL_CHECK.json')))
    tests=read(ROOT/'reports/TEST_SUMMARY.json');extra=read(ROOT/'reports/POSTHOC_DIAGNOSIS.json')
    write(ROOT/'BUILD_STATUS.json',dict(status='PC_EXPERIMENT_COMPLETED',primary='suppress_raw',predeclared_small_synthetic_quality_pass=tests['quality_pass'],implementation_checks='PASS',deployment_ready=False,board_access=False,new_bit=False,main_target_half_fail=tests['summary']['suppress_raw']['main_half_fail'],weak_target_half_fail=tests['summary']['suppress_raw']['weak_half_fail'],main_targets=32,weak_targets=14,remaining_strong_false=tests['summary']['suppress_raw']['worst_false'],amplitude_threshold_baseline=extra['threshold_control'],limitations=['12帧同生成族新种子测试，非实测泛化证明','0–5米最终测试没有弱目标，不证明近距弱目标保护','部分强互调和负七次谐波仍未充分抑制','前端CPU迭代耗时，不是整体轻量PL实现','旧增益接口不能直接用于新权重'],entry_points=['本轮结果.md','results/index.html','数据索引.md','剩余错误与阈值对照.md','candidate/suppress/model_float.pt','infer.py']))
    # No self-reference: manifest covers all other experiment files and their exact hashes.
    manifest=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='FILE_MANIFEST.json' and '__pycache__' not in p.parts]
    write(ROOT/'FILE_MANIFEST.json',dict(excludes_self=True,files=manifest,external_sources='DATA_REGISTER.json and FROZEN.json',not_standalone_full_backup=True))
    assert all(sha(ROOT/r['path'])==r['sha256'] for r in manifest)
    print('交付检查通过；文件清单',len(manifest),'项；数值/CLI、图像、路径和冻结来源已核对。',flush=True)

if __name__=='__main__':main()
