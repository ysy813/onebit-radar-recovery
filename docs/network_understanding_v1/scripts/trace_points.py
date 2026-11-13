"""Explain a few EXISTING diagnostic pixels. Not a new quality experiment."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import csv, hashlib, json
import numpy as np
HERE=Path(__file__).resolve().parents[1]
ROOT=HERE.parent
MODEL=ROOT/"scalar_restore_v3/pc_candidate_compact"
sys.path.insert(0,str(MODEL))
from restore_power import PowerRestorer
from scalar_guard import apply_guard,local_max
from compact_guard import compact_peak_skip

source=ROOT/"scalar_restore_v3/examples_compact/diagnosed_512_power.npy"
p=np.load(source,allow_pickle=False)
with np.load(source.with_name("diagnosed_512_expected.npz")) as d:
    expected=d["gain_q14"].copy()
    ep=d["power"].copy()
net=PowerRestorer(MODEL)
f=net.features(p)
peak=int(p.max())
mx9=local_max(p,9)
weak=(p>=(peak+9999)//10000)&(p<=peak//16)
keep_candidates=np.flatnonzero((weak&(p==mx9)&(expected==16384)).ravel())
atten=np.flatnonzero(((p>=(peak+9999)//10000)&(expected<12000)).ravel())
if not len(atten): raise ValueError("No illustrative attenuation point")
atten_id=int(atten[np.argmax(p.ravel()[atten])])
peak_id=int(np.argmax(p))
ids=np.unique(np.r_[peak_id,atten_id,keep_candidates[:1024]]).astype("i8")

def rs(x,n):return (x+(1<<(n-1)))>>n
def p5(x):
    v=x.copy()
    for _ in range(4):v=rs(v*x,16)
    return v
z=f[:,ids].T.astype("i8")<<4
a=p5(z[:,[0,4,5,6,7]])
x=np.concatenate([z[:,:8],a,np.clip(3*a[:,:1]-a[:,1:2],-65536,65536),
    np.clip(5*a[:,:1]-a[:,2:3],-65536,65536),a[:,:1]-p5(z[:,2:3]),z[:,8:]],axis=1)
v=x.copy(); stages=[]
for i,(w,b) in enumerate(net.layers):
    acc=v@w.T+b
    before_relu=rs(acc,16)
    v=np.maximum(before_relu,0) if i<2 else before_relu
    stages.append(dict(input=stages[-1]["output"] if i else x.copy(),acc=acc.copy(),
        before_relu=before_relu.copy(),output=v.copy()))
index=np.clip(rs(v[:,0],6)+16384,0,32768)
raw=net.lut[index]
gtemp=np.full(p.shape,16384,dtype="u2")
gtemp.ravel()[ids]=raw
g1=apply_guard(p,gtemp,net.config["power_guard"],f,512)
g2=compact_peak_skip(p,g1,f,512)
protected=[int(i) for i in keep_candidates[:1024]
    if raw[np.flatnonzero(ids==i)[0]]<15000 and g2.ravel()[i]>raw[np.flatnonzero(ids==i)[0]]]
chosen=[("输入最大值锚定",peak_id),("被衰减的谱点，未标定真假",atten_id)]
if protected:chosen.append(("保护起作用的局部峰，未标定真假",protected[0]))
compact_protected=[int(i) for i in keep_candidates[:1024] if g2.ravel()[i]>g1.ravel()[i]]
if compact_protected:chosen.append(("紧凑保护再次提升的峰，未标定真假",compact_protected[0]))
rows=[]
for label,i in chosen:
    j=int(np.flatnonzero(ids==i)[0])
    r,a=divmod(i,512)
    final=int(g2.ravel()[i])
    out=min((1<<64)-1,(int(p.ravel()[i])*final**2+(1<<27))>>28)
    assert final==int(expected.ravel()[i]) and out==int(ep.ravel()[i])
    terms=stages[0]["input"][j]*net.layers[0][0][0]
    assert int(terms.sum()+net.layers[0][1][0])==int(stages[0]["acc"][j,0])
    row=dict(label=label,natural_range_bin=r,natural_doppler_bin=a,power=int(p.ravel()[i]),
        power_relative_peak=float(int(p.ravel()[i])/peak),
        feature_q16=x[j].tolist(),feature_real=(x[j]/65536).tolist(),
        layer0_q16=stages[0]["output"][j].tolist(),
        layer1_q16=stages[1]["output"][j].tolist(),
        raw_score_q16=int(v[j,0]),raw_score_real=float(v[j,0]/65536),
        lut_index=int(index[j]),raw_gain_q14=int(raw[j]),
        first_guard_gain_q14=int(g1.ravel()[i]),final_gain_q14=final,
        final_gain=final/16384,output_power=out,
        first_neuron_input_products_q32=terms.tolist(),
        first_neuron_bias_q32=int(net.layers[0][1][0]),
        first_neuron_accumulator_q32=int(stages[0]["acc"][j,0]),
        first_neuron_activation_q16=int(stages[0]["output"][j,0]),
        matches_existing_expected=True)
    rows.append(row)
report=dict(status="PASS",scope="Teaching trace of existing development example; not new quality evidence",
    source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    source_profile="512 valid chirps; natural FFT order",rows=rows,
    model_modified=False,training_run=False,board_accessed=False)
(HERE/"reports/POINT_TRACE.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
with (HERE/"reports/POINT_FEATURES.csv").open("w",encoding="utf-8-sig",newline="") as s:
    w=csv.writer(s);w.writerow(["feature_index"]+[r["label"] for r in rows])
    for k in range(40):w.writerow([k]+[r["feature_real"][k] for r in rows])
md=["# 一个已有诊断帧里，谱点怎样经过网络","",
    "本页从已发布的diagnosed_512示例抽取谱点，逐层代入冻结参数。它是教学重放，不是新增盲测，也没有新的真实目标标注。",
    "", "| 项目 | "+" | ".join(r["label"] for r in rows)+" |",
    "|---|"+"---|"*len(rows)]
for key,title in [("natural_range_bin","自然距离索引r"),("natural_doppler_bin","自然Doppler索引a"),
    ("power","输入功率"),("power_relative_peak","功率/帧峰值"),("raw_score_real","最后线性层分数s"),
    ("raw_gain_q14","原MLP增益整数Q14"),("first_guard_gain_q14","第一层保护后Q14"),
    ("final_gain_q14","最终增益Q14"),("final_gain","最终幅值增益"),
    ("output_power","输出功率"),("matches_existing_expected","与既有示例输出一致")]:
    md.append("| "+title+" | "+" | ".join(str(r[key]) for r in rows)+" |")
row=rows[-1]
md.extend(["","## 挑一个神经元真正展开","",
    "取最后一列谱点，第一层第0号神经元执行40项乘加。输入和权重都带16位小数，所以乘积与偏置都是Q32：","",
    "$$t=\\sum_{k=0}^{39}W_{0,k}^{Q16} f_k^{Q16}+b_0^{Q32}.$$","",
    f"该点40项乘积加偏置的整数和t={row['first_neuron_accumulator_q32']}；偏置为{row['first_neuron_bias_q32']}。",
    f"然后做(t+32768)>>16并经过ReLU，得到第0号神经元激活整数{row['first_neuron_activation_q16']}，",
    f"对应实数{row['first_neuron_activation_q16']/65536:.8f}。",
    "其它31个神经元同样计算，再经过16神经元层和单输出层，才得到上表s。某个神经元的权重不能直接当成因果归因，特征相关与后续非线性都会影响最终决策。","",
    "完整40维输入、32/16层激活、第一神经元40项乘积以及分数查表下标，均保存在：","",
    "[POINT_TRACE.json](C:/Users/yang/Desktop/SAR_IMAGE/network_understanding_v1/reports/POINT_TRACE.json)。",
    "逐维输入表：[POINT_FEATURES.csv](C:/Users/yang/Desktop/SAR_IMAGE/network_understanding_v1/reports/POINT_FEATURES.csv)。","",
    "## 应怎样解读","",
    "原始增益由神经计算得到；保护根据输入峰形和谐波条件调整它；最后功率乘增益平方。该过程没有从RGB反推幅值。",
    "示例中的“被衰减点”和“受保护峰”只是算法行为分类，没有物理目标标签，不能据此宣布前者一定是伪影、后者一定是真目标。",
    "输入最大值被固定到g=1是明确的锚定规则，不应误认为神经网络自动保证了它。",
    "表中匹配既有示例只说明这个讲解对应当前真实代码，不增加模型质量结论。"])
(HERE/"08_实际谱点逐层计算.md").write_text("\n".join(md)+"\n",encoding="utf-8")
print(json.dumps(dict(status="PASS",rows=[{k:r[k] for k in ["label","natural_range_bin","natural_doppler_bin","raw_score_real","raw_gain_q14","first_guard_gain_q14","final_gain_q14"]} for r in rows]),ensure_ascii=False))
