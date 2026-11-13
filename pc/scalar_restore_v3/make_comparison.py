"""Same-frame, shared-scale RD comparison and known-target retention report."""
from pathlib import Path
import sys,json,html
sys.dont_write_bytecode=True
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent

def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def draw(row,folder,out):
    name=row['id']
    with np.load(folder/'arrays'/(name+'.npz')) as d:
        ref=d['reference'];base=d['base'];prior=d['previous_power'];new=d['previous_power'] if row.get('inference_profile')=='frozen_v2_128' else d['enhanced']
    fields=[np.sqrt(ref.astype('f8')/max(float(ref.max()),1))]+[np.sqrt(p.astype('f8')/max(float(base.max()),1)) for p in [base,prior,new]]
    fig,axes=plt.subplots(2,2,figsize=(13,10),layout='constrained')
    for ax,z,label in zip(axes.flat,fields,['Multi-bit reference','1-bit bypass','Previous v2','Corrected v3']):
        im=ax.imshow(np.fft.fftshift(20*np.log10(np.maximum(z,1e-12)),axes=1),origin='lower',extent=(-256,256,0,1024),aspect='auto',vmin=-60,vmax=0,cmap='turbo')
        ax.set_title(label);ax.set_xlabel('Doppler FFT bin');ax.set_ylabel('Natural range index')
        for t in row['targets']:
            if 'weak' in t['kind']:ax.plot(t['doppler_bin'],t['range_bin'],'wo',ms=5,mfc='none',mew=.7)
    fig.colorbar(im,ax=list(axes.flat),label='Normalized amplitude (dB)');fig.suptitle(name+' | full 0-1023 range, shared output scale')
    fig.savefig(out/(name+'.png'),dpi=130);plt.close(fig)
    targets=[t for t in row['targets'] if 'weak' in t['kind']]
    if targets:
        # Show the diagnosed failure, otherwise the worst retained weak target.
        previous_failures=[t for t,old in zip(row['targets'],row['previous_v2']['targets']) if old['newly_below_half']]
        t=previous_failures[0] if previous_failures else min(targets,key=lambda t:t['enhanced_retention']);r,a=t['measured_peak_bin'];aa=np.arange(a-6,a+7)%512
        fig,ax=plt.subplots(figsize=(10,4.5),layout='constrained')
        for z,label in zip(fields,['Multi-bit reference','1-bit bypass','Previous v2','Corrected v3']):ax.plot(np.arange(-6,7),20*np.log10(np.maximum(z[r,aa],1e-12)),marker='.',label=label)
        target_label='diagnosed target' if previous_failures else 'weakest retained target'
        ax.axvline(0,color='k',ls=':',lw=.8);ax.set_xlabel('Doppler offset from reference peak (bins)');ax.set_ylabel('Normalized amplitude (dB)');ax.set_title(f'{name}: {target_label} at range={r}, Doppler={a}');ax.grid(alpha=.25);ax.legend()
        fig.savefig(out/(name+'_target.png'),dpi=140);plt.close(fig)

def main():
    compact='--compact' in sys.argv
    output=ROOT/('results_compact' if compact else 'results');output.mkdir(exist_ok=False);images=output/'images';images.mkdir()
    dev=read(ROOT/('compact_development/report.json' if compact else 'development_profiled/report.json'));fresh=read(ROOT/('compact_fresh_test/report.json' if compact else 'fresh_test/report.json'))
    selected={'confirm_synth_116013_512','historical_0024','historical_0036','v3_field_rx0_0463','v3_field_rx3_0591','v3_synth_124001_512','v3_synth_124000_128'}
    if compact:selected={'confirm_synth_116013_512','v3_synth_124017_512','historical_0024','historical_0036','v3_field_rx0_0463','v3_synth_124001_512','v3_synth_124000_128','compact_synth_128001_512','compact_synth_128000_128','compact_field_rx0_0455','compact_field_rx3_0583'}
    for report in [dev,fresh]:selected.update(r['id'] for r in report['rows'] if any(t['newly_below_half'] for t in r['targets']))
    sections=[];index=[]
    for title,report,folder in [('开发与既有失败诊断（非盲测）',dev,ROOT/('compact_development' if compact else 'development_final')),('冻结模型后的新留出',fresh,ROOT/('compact_fresh_test' if compact else 'fresh_test'))]:
        rows=[];targetrows=[]
        for r in report['rows']:
            name=r['id'];plot=name in selected
            if plot:draw(r,folder,images)
            href=f'<a href="images/{name}.png">{html.escape(name)}</a>' if plot else html.escape(name)
            rows.append(f'<tr><td>{href}</td><td>{r["actual_chirps"]}</td><td>{html.escape(r.get("inference_profile",""))}</td><td>{r["metrics"]["all"]["nmse_ratio"]:.4f}</td><td>{r["previous_v2"]["metrics"]["all"]["nmse_ratio"]:.4f}</td><td>{sum(t["newly_below_half"] for t in r["targets"])}</td></tr>')
            for t,old in zip(r['targets'],r['previous_v2']['targets']):
                targetrows.append(f'<tr class="{"bad" if t["newly_below_half"] else ""}"><td>{html.escape(name)}</td><td>{html.escape(t["kind"])}</td><td>{t["baseline_retention"]:.3f}</td><td>{old["enhanced_retention"]:.3f}</td><td>{t["enhanced_retention"]:.3f}</td></tr>')
            if plot:
                extra=f'<img loading="lazy" src="images/{name}_target.png">' if any('weak' in t['kind'] for t in r['targets']) else ''
                index.append(f'<article><h3>{html.escape(name)}</h3><p>{title}</p><img loading="lazy" src="images/{name}.png">{extra}</article>')
        s=report['summary']
        if compact:title+='（本轮弱目标修正：'+report['correction_status']+'；下方PASS/FAIL为原整体验收）'
        sections.append(f'<h2>{title}：{report["status"]}</h2><p>已知目标 {s["known_targets"]}；相对旁路新增半幅损失 {s["new_targets_below_half"]}；弱目标幅值误差/旁路 {s["weak_mae_ratio"]:.4f}。</p><pre>{html.escape(json.dumps(s["checks"],ensure_ascii=False,indent=2))}</pre><table><tr><th>帧/样例</th><th>有效chirp</th><th>权重模式</th><th>v3误差/旁路</th><th>v2误差/旁路</th><th>新增已知目标损失</th></tr>{"".join(rows)}</table><details><summary>全部已知目标幅值保留率（参考=1）</summary><table><tr><th>样例</th><th>类型</th><th>旁路</th><th>v2</th><th>v3</th></tr>{"".join(targetrows)}</table></details>')
    text='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>弱目标误压修正同帧对照</title><style>body{font:16px/1.6 system-ui,sans-serif;max-width:1300px;margin:28px auto;padding:0 20px;background:#fafafa;color:#18212b}table{border-collapse:collapse;width:100%;font-size:14px}td,th{border:1px solid #ccd2db;padding:6px;text-align:left}th{background:#e7ecf2}.bad{background:#ffe0df}img{width:100%;height:auto}article{margin:36px 0;background:white;padding:16px}pre{white-space:pre-wrap}details{margin:20px 0}</style><h1>弱目标误压修正：v2 / v3 同帧对照</h1><p>这里只验证 FFT 后标量恢复；不是新 BIN 的物理 SAR 聚焦。有效 I/Q 保留严格 ±64 两电平，量化后补零；全部自然距离索引 0–1023 都参与统计。多比特与旁路各用自身帧峰归一化，两个网络输出共同使用旁路峰值，统一 −60 至 0 dB，不重新拉伸。</p><p>历史和此前测试用于开发诊断；新留出在模型冻结后读取。实测新 BIN 按 RX0/RX3、chirp 内 RX 块约定解码，是同一次采集的时间划分，不是跨场景或真实目标全保留的证明。图中的圆圈是合成已知弱目标的位置。</p>'''+''.join(sections)+''.join(index)+'</html>'
    if compact:
        text=text.replace('<h1>弱目标误压修正：v2 / v3 同帧对照</h1>','<h1>弱目标误压修正：v2 / v3 同帧对照</h1><p><b>最终候选保留原v2神经网络权重，只修正512chirp的紧凑弱峰保护。128chirp输出保持原样。</b>最终改善来自网络加保护规则，不能全部归因于重新训练；微调失败记录保留。</p>')
    else:text=text.replace('<h1>弱目标误压修正：v2 / v3 同帧对照</h1>','<h1>弱目标误压修正：v2 / v3 同帧对照</h1><p><b>修正限定到 radar1 的 512 有效 chirp 模式；128 有效 chirp 使用原 v2 权重，两个输出相同是预期行为。</b>逐帧按有效chirp配置选权重，每帧只推理一次，不按参考图或目标位置选择。</p>')
    (output/'index.html').write_text(text,encoding='utf8')
    print('COMPARISON_READY',str(output/'index.html'))

if __name__=='__main__':main()
