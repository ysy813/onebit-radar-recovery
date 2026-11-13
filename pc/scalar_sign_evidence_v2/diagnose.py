"""Post-freeze diagnosis only: labels never feed inference or parameter selection."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json
from experiment_v2 import echo, np
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf8'))
def dist(a,b,n):return abs((a-b+n/2)%n-n/2)

def main():
    cfg=read(ROOT/'PROTOCOL.json');alpha=read(ROOT/'FROZEN.json')['alpha']
    splits={}
    for split in ['development','validation','test']:
        records=[]
        for meta in read(ROOT/'data'/f'{split}_manifest.json')['records']:
            row=read(ROOT/'reports'/split/(meta['id']+'.json'))
            sr=read(Path(row['solver_reports']['residual24']))
            with np.load(meta['file']) as observed:
                si=observed['sign_i'];sq=observed['sign_q']
            for j,t in enumerate(meta['targets']):
                retention={k:v['targets'][j]['retention'] for k,v in row['metrics'].items()}
                near=[]
                for c in sr['candidates']:
                    di=[dist(c['integer'][0],t['range_bin'],1024),dist(c['integer'][1],t['doppler_bin'],512)]
                    if max(di)>2:continue
                    df=[dist(c['fitted_frequency'][0],t['range_bin'],1024),dist(c['fitted_frequency'][1],t['doppler_bin'],512)]
                    state=next(x['supported'] for x in row['support']['residual24']['states'] if x['index']==c['index'])
                    near.append(dict(integer=c['integer'],fitted=c['fitted_frequency'],origin=c['proposal_origin'],
                        integer_error_bins=di,fit_error_bins=df,
                        target_inside_refinement_box=max(di)<=cfg['solver']['frequency_bound_bins'],
                        retained_in_sparse_explanation=c['selected_source'],protected=state,
                        h0_converged=c['h0_solver']['success'],h1_converged=c['h1_solver']['success'],
                        logistic_improvement_lower=c['heldout_loss_delta']-2*c['delta_se'],
                        sign_error_improvement_lower=c['mismatch_improvement']-2*c['mismatch_se']))
                audit=None
                if retention['residual24_model']<.5 or retention['old40']-retention['residual24_blend'+str(alpha)]>.05:
                    # Diagnostic intervention uses truth AFTER inference, never for prediction.
                    without={**meta,'targets':[v for k,v in enumerate(meta['targets']) if k!=j]}
                    minus=echo(without)
                    di=(np.where(minus.real>=0,1,-1)!=si).astype('i1')
                    dq=(np.where(minus.imag>=0,1,-1)!=sq).astype('i1')
                    changed=di+dq
                    audit=dict(full_changed_sign_components=int(changed.sum()),full_total=2*si.size,
                        fit_changed_sign_components=int(changed.ravel()[sr['fit_indices']].sum()),
                        evidence_changed_sign_components=int(changed.ravel()[sr['evidence_indices']].sum()),
                        note='按相同回波生成/缩放/ADC取整规则移除该目标；事后可辨识性审计，不用于推理。不变化说明至少存在此同符号替代场景；有变化不证明全局唯一可辨识。')
                records.append(dict(id=meta['id'],target=j+1,retention=retention,near_candidates=near,remove_target_audit=audit,
                    residual_model_failure=retention['residual24_model']<.5,
                    primary_new_half=retention['old40']>=.5 and retention['residual24_blend'+str(alpha)]<.5,
                    primary_drop_over_005=retention['old40']-retention['residual24_blend'+str(alpha)]>.05))
        splits[split]=records
    (ROOT/'reports/TARGET_DIAGNOSIS.json').write_text(json.dumps(splits,ensure_ascii=False,indent=2),encoding='utf8')
    lines=['# 失败发生在哪一步','',
        '这是冻结后逐目标诊断，不用于重新选择参数。候选“召回”按整数中心与真值相距不超过2个频点统计；优化频率的可动范围仅±0.55个频点，所以进入5×5候选邻域不代表一定可定位到真实频率。', '',
        '|最终帧／目标|旧网保留率|残差恢复|融合|近邻候选情况|', '|---|---:|---:|---:|---|']
    for r in splits['test']:
        if not (r['residual_model_failure'] or r['primary_drop_over_005']):continue
        n=r['near_candidates'];why='未进入候选邻域' if not n else '；'.join(
            f"{c['origin']}，{'保留' if c['retained_in_sparse_explanation'] else '被稀疏删减'}，"
            f"{'可覆盖真频率' if c['target_inside_refinement_box'] else '定位搜索框不覆盖真频率'}，"
            f"{'有保护证据' if c['protected'] else '未获保护证据'}" for c in n)
        v=r['retention'];lines.append(f"|{r['id']}／{r['target']}|{v['old40']:.4f}|{v['residual24_model']:.4f}|{v['residual24_blend'+str(alpha)]:.4f}|{why}|")
    lines+=['', '“被稀疏删减”意味着该候选未进入最终回波重构，不等于证明该目标不存在。相对幅值还受系数估计、非整数频率偏差、归一化和其它分量影响；本表不把单一条件宣称为全部因果。', '',
        '旧网络与并行融合使用相同网络输入。若单独恢复已经漏掉或误压目标，组合失败首先有恢复支路错误这一直接证据；固定比例融合会把错误传入输出。这不足以证明40维网络与符号信息在原理上不能结合。', '',
        '未拟合样本证据未达到保护条件的情况仍是“不确定”。仅保护接法不会新增衰减，但也无法抑制旧网留下的大部分伪峰；固定比例融合也不是“证据不足就保守旁路”，它只是本轮待测对照。', '',
        '后续若继续，应先区分候选缺失、搜索范围偏差、稀疏误删和系数失真，再决定恢复支路修正还是证据自适应融合。当前没有据最终测试改参数或补做训练。']
    lines+=['', '## 移除目标后，输入符号有没有变化', '',
        '以下仅是事后因果干预审计，使用已知仿真目标重新生成“少一个目标”的回波，保持相同缩放和整数ADC量化规则。统计变化的I/Q符号分量数，拟合和证据各含8192个实符号分量；全帧含1048576个。没有变化说明至少有两种场景给出相同符号观测，不能要求任何仅符号算法可靠区分；有变化也不证明唯一可辨识。', '',
        '|划分／帧／目标|全帧变化|拟合样本变化|证据样本变化|', '|---|---:|---:|---:|']
    for split in ['validation','test']:
        for r in splits[split]:
            a=r['remove_target_audit']
            if a is None:continue
            label='验证' if split=='validation' else '最终测试'
            lines.append(f"|{label}／{r['id']}／{r['target']}|{a['full_changed_sign_components']}|{a['fit_changed_sign_components']}|{a['evidence_changed_sign_components']}|")
    (ROOT/'逐目标失败诊断.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print('逐目标失败位置诊断完成。')

if __name__=='__main__':main()
