"""Deterministic mathematical illustrations; not a network-performance experiment."""
import sys
sys.dont_write_bytecode = True
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE = Path(__file__).resolve().parents[1]
font = Path("C:/Windows/Fonts/msyh.ttc")
if font.exists():
    font_manager.fontManager.addfont(str(font))
    plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(font)).get_name()
plt.rcParams.update({"axes.unicode_minus":False, "font.size":11,
    "axes.spines.top":False,"axes.spines.right":False, "figure.facecolor":"white",
    "savefig.facecolor":"white"})
BLUE, RED, GREEN = "#2268a2", "#c45536", "#258073"
def save(fig, name):
    fig.savefig(HERE/"figures"/(name+".png"), dpi=180, bbox_inches="tight")
    fig.savefig(HERE/"figures"/(name+".svg"), bbox_inches="tight")
    plt.close(fig)

N=262144
theta=2*np.pi*(np.arange(N)+0.371)/N
x=np.exp(1j*theta)
q=np.where(x.real>=0,1.,-1.)+1j*np.where(x.imag>=0,1.,-1.)
orders=[1,-3,5,-7,9]
coeff={h:np.mean(q*np.exp(-1j*h*theta)) for h in orders}
expected={h:(4/np.pi)*((-1)**i)/abs(h) for i,h in enumerate(orders)}
errors={str(h):abs(coeff[h]-expected[h]) for h in orders}
assert max(errors.values())<5e-5
assert np.array_equal(q, np.where((13*x).real>=0,1.,-1.)+1j*np.where((13*x).imag>=0,1.,-1.))

fig, ax=plt.subplots(1,2,figsize=(12.2,4.1), layout="constrained")
t=np.linspace(0,2*np.pi,1200,endpoint=False)+.001
ax[0].plot(t/(2*np.pi),np.cos(t),color=BLUE,label="原始 I = cos θ")
ax[0].plot(t/(2*np.pi),np.where(np.cos(t)>=0,1,-1),color=RED,label="符号量化 I")
ax[0].set(xlabel="一个周期",ylabel="示意幅值",title="① 正弦变成方波")
ax[0].legend(fontsize=9,loc="lower left")
hs=np.arange(-11,12)
cs=np.array([abs(np.mean(q*np.exp(-1j*int(h)*theta))) for h in hs])
ax[1].stem(hs,cs/(4/np.pi),basefmt=" ",linefmt=RED,markerfmt="o")
for h in orders[:4]:
    ax[1].annotate(f"h={h}\n1/{abs(h)}",(h,abs(coeff[h])/(4/np.pi)),
                   xytext=(0,8),textcoords="offset points",ha="center",fontsize=9)
ax[1].set(xticks=[-7,-3,1,5,9],xlabel="相对于原复正弦的有符号频率倍数 h",
          ylabel="幅值 / 基波幅值",ylim=(0,1.26),title="② I/Q联合量化产生有符号奇次谐波")
fig.suptitle("理想单目标数学演示：解释失真来源，不代表真实场景恢复率",fontsize=13)
save(fig,"01_sign_harmonics")

Nr,Na=1024,512
r,a=131,37
coords={h:((h*r)%Nr,(h*a)%Na) for h in [1,-3,5,-7]}
fig,ax=plt.subplots(figsize=(8.8,5.3), layout="constrained")
colors=[BLUE,RED,GREEN,"#8e62a5"]
for (h,(rr,aa)),color in zip(coords.items(),colors):
    ax.scatter(aa,rr,s=100,c=color,zorder=3)
    ax.annotate(f"h={h}: (r,a)=({rr},{aa})",(aa,rr),xytext=(10,10),
                textcoords="offset points",fontsize=10)
    if h!=1:
        ax.annotate("",(aa,rr),(a,r),arrowprops=dict(arrowstyle="->",color=color,alpha=.45))
ax.set(xlim=(0,512),ylim=(0,1024),xlabel="自然 Doppler 索引 a（不是角度）",
       ylabel="自然距离FFT索引 r（不是米）",title="二维离散折叠：两维索引同时乘 h，再取模")
ax.grid(alpha=.18)
save(fig,"02_alias_coordinates")

fig,ax=plt.subplots(1,2,figsize=(12.2,4.2), layout="constrained")
A=np.linspace(0,1,1000)
ax[0].plot(A,A,color="#999999",ls="--",label="未压缩 A")
ax[0].plot(A,A**.2,color=BLUE,label="网络编码 z = A^0.2")
for v in [.001,.01,.1]:
    ax[0].scatter([v],[v**.2],color=RED,s=25)
ax[0].set(xlabel="归一化幅值 A",ylabel="编码值 z",title="弱幅值更可见；不是恢复丢失信息")
ax[0].legend(fontsize=9)
g=np.linspace(.125,1.5,600)
conf=np.clip((g-.25)/.25,0,1)
lift=g+np.maximum(1-g,0)*conf
ax[1].plot(g,g,color="#999999",ls="--",label="原预测增益")
ax[1].plot(g,lift,color=GREEN,label="满足资格时第一层软保护")
ax[1].axvspan(.25,.5,color=GREEN,alpha=.1)
ax[1].set(xlabel="神经网络原始幅值增益",ylabel="保护后的增益",
          title="仅保护符合输入条件的弱峰；仍可能保留伪峰")
ax[1].legend(fontsize=9)
save(fig,"03_encoding_and_guard")

report=dict(status="PASS",scope="Mathematical demo only; no model-quality claim",
    complex_harmonic_coefficient_max_error=max(errors.values()),
    complex_harmonic_coefficient_errors=errors,
    scale_nonidentifiability_verified=True,
    alias_example={str(h):list(v) for h,v in coords.items()},
    figures=["01_sign_harmonics","02_alias_coordinates","03_encoding_and_guard"],
    network_training_run=False,network_inference_run=False,board_accessed=False)
(HERE/"reports/THEORY_DEMO.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,ensure_ascii=False))
