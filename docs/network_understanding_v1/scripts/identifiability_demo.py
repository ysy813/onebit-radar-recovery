"""Analytic counterexample and toy spectra. No model inference or optimization."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE=Path(__file__).resolve().parents[1]
font=Path("C:/Windows/Fonts/msyh.ttc")
if font.exists():
    font_manager.fontManager.addfont(str(font))
    plt.rcParams["font.family"]=font_manager.FontProperties(fname=str(font)).get_name()
plt.rcParams.update({"axes.unicode_minus":False,"font.size":11,
    "axes.spines.top":False,"axes.spines.right":False})
N=8192;k=37;phase=.137
theta=2*np.pi*k*np.arange(N)/N+phase
def quant(x,c=64):
    return c*(np.where(x.real>=0,1,-1)+1j*np.where(x.imag>=0,1,-1))
betas=[.1,.3,.6]
signals=[np.exp(1j*theta)+b*np.exp(3j*theta) for b in betas]
qs=[quant(x) for x in signals]
Y=[np.fft.fft(x)/N for x in signals]
Q=[np.fft.fft(q)/N for q in qs]
assert np.array_equal(qs[0],qs[1])
assert np.array_equal(np.abs(Q[0])**2,np.abs(Q[1])**2)
assert np.count_nonzero(qs[0]!=qs[2])>0
assert all(abs(abs(y[3*k])/abs(y[k])-b)<1e-12 for y,b in zip(Y,betas))
# The quantizer commutes with integer positive scaling. Ideal normalized
# spectra do not gain information when c changes.
assert np.array_equal(quant(signals[0],64),64*quant(signals[0],1))

fig,axs=plt.subplots(1,2,figsize=(12,4.5),layout="constrained")
orders=np.array([-3,1,3,5]);pos=np.arange(len(orders))
colors=["#2268a2","#c45536"]
for j in range(2):
    amp=np.array([abs(Y[j][int(h*k)%N])/abs(Y[j][k]) for h in orders])
    axs[0].bar(pos+(j-.5)*.30,amp,width=.28,color=colors[j],label=f"β={betas[j]:.1f}")
    for xx,yy in zip(pos+(j-.5)*.30,amp):
        if yy>.001:axs[0].text(xx,yy+.025,f"{yy:.1f}",ha="center")
axs[0].set(xticks=pos,xticklabels=["−3f","f","3f","5f"],ylim=(0,1.18),
    ylabel="幅值 / 基波幅值",title="多比特：两个不同的弱分量幅值")
axs[0].legend(frameon=False,loc="upper left")
amp=np.array([abs(Q[0][int(h*k)%N])/abs(Q[0][k]) for h in orders])
axs[1].bar(pos,amp,width=.45,color="#258073",label="β=0.1与0.3：量化后完全相同")
for xx,yy in zip(pos,amp):
    if yy>.001:axs[1].text(xx,yy+.025,f"{yy:.3f}",ha="center")
axs[1].annotate("输入弱分量3f在此例中消失",xy=(2,0),xytext=(2.65,.57),
    arrowprops=dict(arrowstyle="->",color="#666666"),ha="center",fontsize=10)
axs[1].set(xticks=pos,xticklabels=["−3f","f","3f","5f"],ylim=(0,1.18),
    ylabel="幅值 / 基波幅值",title="单比特：相同输入，无法唯一辨别两种参考")
axs[1].legend(frameon=False,loc="upper left")
for ax in axs:ax.set_xlabel("频率位置；3f是真弱分量，−3f是量化谐波")
fig.suptitle("可辨识性反例：xβ = exp(jθ) + β exp(j3θ)，0 < β < 1/3",fontsize=13)
fig.savefig(HERE/"figures/04_relative_ambiguity.png",dpi=180,bbox_inches="tight")
fig.savefig(HERE/"figures/04_relative_ambiguity.svg",bbox_inches="tight")
plt.close(fig)

# A two-dimensional realization of the same analytic counterexample.
nr,na=1024,512
r,a=np.ogrid[:nr,:na]
t=2*np.pi*(131*r/nr+37*a/na)+phase
q10=quant(np.exp(1j*t)+.1*np.exp(3j*t))
q30=quant(np.exp(1j*t)+.3*np.exp(3j*t))
assert np.array_equal(q10,q30)
values=[]
for b,q,y,z in zip(betas,qs,Y,Q):
    values.append(dict(beta=b,
        multibit_weak_to_main=float(abs(y[3*k])/abs(y[k])),
        onebit_weak_to_main=float(abs(z[3*k])/abs(z[k])),
        iq_component_change_fraction_vs_beta0p1=float((np.count_nonzero(q.real!=qs[0].real)+np.count_nonzero(q.imag!=qs[0].imag))/(2*N)),
        normalized_power_same_as_beta0p1=bool(np.array_equal(np.abs(z)**2,np.abs(Q[0])**2))))
report=dict(status="PASS",scope="Toy analytic counterexample, not a realistic data quality test",
    mathematical_family="exp(j theta)+beta exp(j3 theta), 0<beta<1/3",
    real_factor="1-3 beta+4 beta cos(theta)^2 > 0",
    imag_factor="1+3 beta-4 beta sin(theta)^2 > 0",
    discrete_samples=N,base_bin=k,phase=phase,examples=values,
    two_dimensional_same_quantized_input=True,
    two_dimensional_base=[131,37],two_dimensional_weak=[393,111],
    model_inference_run=False,training_run=False,board_accessed=False)
(HERE/"reports/IDENTIFIABILITY_DEMO.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,ensure_ascii=False))
