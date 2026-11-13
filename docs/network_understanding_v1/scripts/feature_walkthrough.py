"""Read-only feature teaching: independent point calculations and toy gate demo."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json,math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle

HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parent
MODEL=ROOT/"scalar_restore_v3/pc_candidate_compact"
sys.path.insert(0,str(MODEL))
from restore_power import PowerRestorer
font=Path("C:/Windows/Fonts/msyh.ttc")
if font.exists():
    font_manager.fontManager.addfont(str(font))
    plt.rcParams["font.family"]=font_manager.FontProperties(fname=str(font)).get_name()
plt.rcParams.update({"axes.unicode_minus":False,"font.size":11,
    "axes.spines.top":False,"axes.spines.right":False})
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def save(fig,name):
    fig.savefig(HERE/"figures"/(name+".png"),dpi=180,bbox_inches="tight")
    fig.savefig(HERE/"figures"/(name+".svg"),bbox_inches="tight")
    plt.close(fig)
def patch(z,r,a,size):
    h=size//2
    return z[np.ix_((np.arange(r-h,r+h+1)%1024),(np.arange(a-h,a+h+1)%512))]
def rs(x,n):return (x+(1<<(n-1)))>>n
def fifth(x):
    v=x.copy()
    for _ in range(4):v=rs(v*x,16)
    return v

net=PowerRestorer(MODEL)
p=np.load(ROOT/"scalar_restore_v3/examples_compact/diagnosed_512_power.npy",allow_pickle=False)
f=net.features(p);z=f[0].reshape(1024,512).astype("i8")
trace=json.loads((HERE/"reports/POINT_TRACE.json").read_text(encoding="utf-8"))
rows=[]
for old in trace["rows"]:
    r,a=old["natural_range_bin"],old["natural_doppler_bin"];i=r*512+a
    pp3=patch(z,r,a,3);pp9=patch(z,r,a,9)
    base=[int(z[r,a]),int(pp3.max()),int((pp3.sum()+4)//9),int((pp9.sum()+40)//81)]
    parents=[]
    for h in [-3,5]:
        cand=[];H=abs(h)
        for kr in range(H):
            rp=int(np.rint(r/h+kr*1024/H))%1024
            for ka in range(H):
                ap=int(np.rint(a/h+ka*512/H))%512
                support=patch(z,rp,ap,3)
                sr,sa=np.unravel_index(np.argmax(support),support.shape)
                cand.append(dict(candidate=[rp,ap],support_q12=int(support.max()),
                    support_source=[(rp+int(sr)-1)%1024,(ap+int(sa)-1)%512]))
        winner=max(cand,key=lambda v:v["support_q12"])
        parents.append(dict(order=h,candidates=cand,winner=winner))
        base.append(winner["support_q12"])
    children=[]
    for h in [-3,5]:
        cr,ca=(h*r)%1024,(h*a)%512
        scores=[]
        for dr in range(-1,2):
            for da in range(-1,2):
                rr,aa=(cr+dr)%1024,(ca+da)%512
                center=int(z[rr,aa])
                mean=int((z[(np.arange(rr-15,rr+16)%1024),aa].sum()+15)//31)
                den=max(mean,128)
                ratio=min(4096,(max(20*center-24*den,0)*4096+(5*den)//2)//(5*den))
                score=(center*ratio+2048)>>12
                scores.append(dict(position=[rr,aa],z_q12=center,mean31_q12=mean,
                    denominator_q12=den,ratio_q12=ratio,score_q12=score))
        winner=max(scores,key=lambda v:v["score_q12"])
        children.append(dict(order=h,child=[cr,ca],winner=winner))
        base.append(winner["score_q12"])
    for dr in range(-2,3):
        for da in range(-2,3):
            if (dr,da)!=(0,0):base.append(int(z[(r+dr)%1024,(a+da)%512]))
    assert np.array_equal(np.asarray(base),f[:,i])
    q=np.asarray(base,dtype="i8")<<4
    v=fifth(q[[0,4,5,6,7]])
    x=np.r_[q[:8],v,np.clip(3*v[:1]-v[1:2],-65536,65536),
        np.clip(5*v[:1]-v[2:3],-65536,65536),v[:1]-fifth(q[2:3]),q[8:]]
    assert x.tolist()==old["feature_q16"]
    rows.append(dict(label=old["label"],position=[r,a],base_q12=base,
        mlp_q16=x.tolist(),parent_details=parents,child_details=children,
        physical_relative_amplitude=math.sqrt(int(p[r,a])/int(p.max())),
        raw_gain=old["raw_gain_q14"]/16384,final_gain=old["final_gain"],
        code_features_exact=True,existing_neural_vector_exact=True))

fig,(ax,bar)=plt.subplots(1,2,figsize=(10.8,4.8),layout="constrained")
indices=np.empty((5,5),dtype=int);j=16
for dr in range(5):
    for da in range(5):
        if dr==2 and da==2:indices[dr,da]=0
        else:indices[dr,da]=j;j+=1
bg=np.zeros((5,5));bg[2,2]=1
ax.imshow(bg,cmap="Blues",vmin=0,vmax=2,interpolation="nearest")
for dr in range(5):
    for da in range(5):ax.text(da,dr,str(indices[dr,da]),ha="center",va="center",fontsize=13)
ax.add_patch(Rectangle((.5,.5),3,3,fill=False,edgecolor="#666666",linewidth=1.2))
ax.set(xticks=range(5),xticklabels=range(-2,3),yticks=range(5),yticklabels=range(-2,3),
    xlabel="Doppler邻居偏移 Δa",ylabel="距离邻居偏移 Δr",title="5×5中24邻居的MLP下标；中心为x0")
ax.set_xticks(np.arange(-.5,5),minor=True);ax.set_yticks(np.arange(-.5,5),minor=True)
ax.grid(which="minor",color="#aaaaaa",linewidth=.5)
labels=["自身与局部统计","候选父关联","门控子关联","五次方与关系项","24个局部邻居"]
counts=[4,2,2,8,24]
bar.barh(range(5),counts,color="#2268a2")
for i,c in enumerate(counts):bar.text(c+.3,i,str(c),va="center")
bar.set(yticks=range(5),yticklabels=labels,xlim=(0,27),xlabel="特征数量",title="40维如何组成：32个基础项 + 8个派生项")
bar.invert_yaxis()
save(fig,"05_feature_layout")

show=[rows[0],rows[1],rows[-1]]
fig,axs=plt.subplots(1,3,figsize=(11.5,4),layout="constrained")
for ax,row in zip(axs,show):
    r,a=row["position"];window=patch(z,r,a,5)/4096
    im=ax.imshow(window,vmin=0,vmax=1,cmap="viridis",interpolation="nearest")
    for rr in range(5):
        for aa in range(5):
            ax.text(aa,rr,f"{window[rr,aa]:.2f}",ha="center",va="center",
                fontsize=9,color="white" if window[rr,aa]<.65 else "black")
    ax.add_patch(Rectangle((1.5,1.5),1,1,fill=False,edgecolor="#ef8a62",linewidth=2))
    short="主峰" if row is show[0] else "被衰减点" if row is show[1] else "受保护点"
    ax.set(title=f"{short} ({r},{a})\n原MLP g={row['raw_gain']:.3f}；最终g={row['final_gain']:.3f}",
        xticks=range(5),xticklabels=(np.arange(a-2,a+3)%512),
        yticks=range(5),yticklabels=(np.arange(r-2,r+3)%1024),
        xlabel="自然Doppler索引",ylabel="自然距离索引")
fig.colorbar(im,ax=axs,shrink=.8,label="五次根幅值编码z，不是原始功率")
save(fig,"06_existing_point_neighborhoods")

# Deliberately constructed power fields: explain only feature behavior.
toy=[]
cr,ca=631,401
for name in ["紧凑孤立峰","沿距离方向平滑脊线"]:
    field=np.zeros((1024,512),dtype="u8");field[131,37]=10**12
    if name=="紧凑孤立峰":field[cr,ca]=10**10
    else:field[(np.arange(cr-50,cr+51)%1024),ca]=10**10
    feat=net.features(field);zz=feat[0].reshape(1024,512).astype("i8")
    mean=(zz[(np.arange(cr-15,cr+16)%1024),ca].sum()+15)//31
    den=max(int(mean),128)
    toy.append(dict(name=name,source=[131,37],third_child=[cr,ca],
        source_center_q12=int(feat[0,131*512+37]),
        child_center_q12=int(zz[cr,ca]),child_mean31_q12=int(mean),denominator_q12=den,
        child_gated_support_q12=int(feat[6,131*512+37]),
        offsets=list(range(-20,21)),profile_q12=zz[(np.arange(cr-20,cr+21)%1024),ca].tolist()))
assert toy[0]["child_center_q12"]==toy[1]["child_center_q12"]
assert toy[0]["source_center_q12"]==toy[1]["source_center_q12"]
assert toy[0]["child_gated_support_q12"]>0 and toy[1]["child_gated_support_q12"]==0
fig,axs=plt.subplots(1,2,figsize=(11,4.2),layout="constrained")
for ax,t in zip(axs,toy):
    ax.plot(t["offsets"],np.asarray(t["profile_q12"])/4096,color="#2268a2",label="子位置附近z")
    ax.axhline(t["denominator_q12"]/4096,color="#c45536",ls="--",label="中心mean31与下限所得d")
    ax.set(xlabel="沿距离方向的索引偏移",ylabel="编码值（Q12解码）",ylim=(-.025,.72),
        title=f"{t['name']}\n同样中心z={t['child_center_q12']/4096:.3f}，门控支持={t['child_gated_support_q12']/4096:.3f}")
    ax.legend(frameon=False,fontsize=9,loc="center left")
save(fig,"07_child_gate_example")
report=dict(status="PASS",scope="Feature/code teaching only; toy fields are not physical scene validation",
    source=trace["source"],source_sha256=trace["source_sha256"],
    actual_point_checks=rows,toy_child_gate=toy,
    feature_layout=indices.tolist(),total_mlp_features=40,
    neural_parameters_modified=False,neural_quality_test_run=False,board_accessed=False)
write(HERE/"reports/FEATURE_WALKTHROUGH.json",report)

md=["# 已有谱点的40维特征核对","",
    "本页由教学脚本生成：逐点重新计算基础统计、候选父查询、子位置门控与24邻居，并与冻结实现及既有逐层记录核对。它不增加真实目标标签或新的质量结论。","",
    "| 特征（解码值） | "+" | ".join(str(t["position"]) for t in show)+" |",
    "|---|"+"---|"*len(show)]
for idx,label in [(0,"x0 中心z"),(2,"x2 3×3均值"),(3,"x3 9×9均值"),(4,"x4 三次父提示"),(5,"x5 五次父提示"),(6,"x6 门控三次子提示"),(7,"x7 门控五次子提示"),(8,"x8 中心幅值近似"),(13,"x13 三次幅值偏差"),(14,"x14 五次幅值偏差"),(15,"x15 中心/底座差")]:
    md.append("| "+label+" | "+" | ".join(f"{t['mlp_q16'][idx]/65536:.6f}" for t in show)+" |")
md.extend(["","## 一个候选父查询的实际落点",""])
atten=rows[1];winner=atten["parent_details"][0]["winner"]
md.extend([f"被衰减点{atten['position']}的三次候选父支持最大值，来自候选{winner['candidate']}，其3×3支持的实际最大值在{winner['support_source']}。",
    f"支持Q12={winner['support_q12']}，解码为{winner['support_q12']/4096:.6f}。",
    "全局主峰(83,0)的−3倍子位置是(775,0)，与该被衰减点相差一个距离格和一个周期Doppler格。这与当前邻域容差设计相符。",
    "这说明算法的衰减与关联线索一致，不等于这个点已经被物理标注为纯谐波。","",
    "## 门控演示","",
    "两个构造功率场的子位置中心完全相同，但紧凑峰保留子提示，平滑脊线的子提示为0。这里只证明特征如何计算，不表示MLP已经对所有脊线/目标正确分类。",
    "", "| 构造输入 | 子中心z | mean31 | d | 门控后子支持 |","|---|---:|---:|---:|---:|"])
for t in toy:
    md.append("| "+t["name"]+" | "+" | ".join(f"{t[k]/4096:.6f}" for k in ["child_center_q12","child_mean31_q12","denominator_q12","child_gated_support_q12"])+" |")
md.extend(["","完整候选坐标和40维整数值：[FEATURE_WALKTHROUGH.json](C:/Users/yang/Desktop/SAR_IMAGE/network_understanding_v1/reports/FEATURE_WALKTHROUGH.json)。",
    "讲解入口：[第二讲](C:/Users/yang/Desktop/SAR_IMAGE/network_understanding_v1/10_第二讲_40维特征与学习增益.md)。"])
(HERE/"11_已有谱点的特征核对.md").write_text("\n".join(md)+"\n",encoding="utf-8")
print(json.dumps(dict(status="PASS",actual_points=len(rows),attenuated_parent_winner=winner,
    toy=[{k:t[k] for k in ["name","child_center_q12","child_mean31_q12","child_gated_support_q12"]} for t in toy]),ensure_ascii=False))
