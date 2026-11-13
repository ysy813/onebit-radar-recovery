"""Create a source-checked network-only figure; read weights, never infer/train."""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle, FancyArrowPatch

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
FOLDER = ROOT/'scalar_restore_v3/pc_candidate_compact'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


baseline = read(HERE/'reports/SOURCE_BASELINE.json')
changed = [name for name,info in baseline.items() if sha(ROOT/name)!=info['sha256']]
assert not changed, changed
config = read(FOLDER/'config.json')
assert sha(FOLDER/'weights.npz') == config['sha256']['weights.npz']
assert config['network']==[40,32,16,1] and config['context']==2 and config['feature_policy']=='guarded_child'
assert config['power_guard']['anchor_frame_peak'] and config['compact_peak_policy']['actual_chirps_changed']==[512]
layers = []
with np.load(FOLDER/'weights.npz',allow_pickle=False) as archive:
    for i,(n_in,n_out) in enumerate(zip(config['network'][:-1],config['network'][1:])):
        w,b = archive[f'w{i}'],archive[f'b{i}']
        assert w.shape==(n_out,n_in) and b.size==n_out
        layers.append(dict(inputs=n_in,outputs=n_out,weights=int(w.size),biases=int(b.size),
                           parameters=int(w.size+b.size),activation='ReLU' if i<2 else 'linear'))
assert sum(row['parameters'] for row in layers)==config['parameters']==1857
training_source = ROOT/'scalar_restore_v2/runs/protected_patch5/training_source.py'
training_text = training_source.read_text(encoding='utf-8-sig')
training_config = read(ROOT/'scalar_restore_v2/runs/soft_patch5/config.json')
assert sha(training_source)==training_config['code_sha256']
assert 'pred=x*g' in training_text and 'raw=net(f)' in training_text
assert 'apply_guard(' not in training_text and 'compact_peak_skip(' not in training_text

font_path = Path('C:/Windows/Fonts/msyh.ttc')
assert font_path.is_file()
font_manager.fontManager.addfont(str(font_path))
family = font_manager.FontProperties(fname=str(font_path)).get_name()
plt.rcParams.update({'font.family':family,'font.size':17,'svg.fonttype':'path','axes.unicode_minus':False})
fig,ax = plt.subplots(figsize=(20.5,11.4),dpi=160)
fig.subplots_adjust(left=.008,right=.992,top=.985,bottom=.015)
ax.set_xlim(0,20.5);ax.set_ylim(0,11.4);ax.axis('off')
ink = '#172b3a'; muted = '#536875'; fixed_fill = '#f2f5f7'; fixed_edge = '#90a1ac'
learn_fill = '#e7f1fb'; learn_edge = '#3571a5'; gradient_color = '#3571a5'
texts = []; blocks = {}; graph = []


def text(x,y,value,size=17,container=None,ha='center',color=ink):
    artist = ax.text(x,y,value,fontsize=size,ha=ha,va='center',color=color)
    texts.append((artist,container,value))
    return artist


def block(name,x,y,w,h,learned=False):
    blocks[name]=(x,y,w,h)
    ax.add_patch(Rectangle((x,y),w,h,facecolor=learn_fill if learned else fixed_fill,
                           edgecolor=learn_edge if learned else fixed_edge,linewidth=1.1))


def arrow(start,end,label=None,style='-',color=muted):
    ax.add_patch(FancyArrowPatch(start,end,arrowstyle='-|>',mutation_scale=17,
                                linewidth=1.3,color=color,linestyle=style,shrinkA=0,shrinkB=0))
    graph.append(dict(start=start,end=end,kind='training-gradient' if style=='--' else 'data'))
    if label:
        text((start[0]+end[0])/2,(start[1]+end[1])/2+.25,label,15,color=color)


text(10.25,11.05,'当前 compact 标量网络：结构与训练关系',24)
text(.4,10.67,'推理路径（512 有效 chirp）',18,ha='left')
block('input',.4,7.15,2.3,2.3)
text(1.55,9.0,'输入功率 P1',18,'input')
text(1.55,8.4,'1024 × 512',18,'input')
text(1.55,7.8,r'$X=\sqrt{P_1/G_1}$',18,'input')

block('features',3.25,6.7,4.25,3.2)
text(5.375,9.5,'固定特征 Φ：40维',19,'features')
text(5.375,8.95,'自身 / 局部统计4 + 父提示2',17,'features')
text(5.375,8.4,'门控子提示2 + 派生项8',17,'features')
text(5.375,7.85,'5×5其余邻居24',17,'features')
text(5.375,7.2,'归一化 + 五次根表示',17,'features')

block('mlp',8.0,6.7,4.5,3.2,learned=True)
text(10.25,9.5,'共享 MLP：可训练部分',19,'mlp')
for i,y in enumerate([8.9,8.25,7.6]):
    layer=layers[i]
    activation='ReLU' if layer['activation']=='ReLU' else '线性'
    text(10.25,y,f"{layer['inputs']}→{layer['outputs']}，{activation}：{layer['parameters']}参数",17,'mlp')
text(10.25,7.05,'共1857参数，整帧逐点共享',17,'mlp')

block('head',13.0,7.15,2.7,2.3)
text(14.35,9.0,'固定有界增益头',18,'head')
text(14.35,8.4,r'$g_{nn}=2^{\mathrm{clip}(s)}$',19,'head')
text(14.35,7.8,'范围 [0.125, 1.5]',16,'head')

block('guards',16.2,6.7,3.4,3.2)
text(17.9,9.5,'固定保护规则',19,'guards')
text(17.9,8.95,'软弱峰保护＋帧峰锚定',16,'guards')
text(17.9,8.4,'↓',19,'guards')
text(17.9,7.85,'compact 紧凑弱峰保护',16,'guards')
text(17.9,7.2,r'$g_{nn}\to g_1\to g_{final}$',18,'guards')

for left,right,label in [(2.7,3.25,None),(7.5,8.0,'F'),(12.5,13.0,'s'),(15.7,16.2,None)]:
    arrow((left,8.3),(right,8.3),label)

block('output',16.2,4.6,3.4,1.5)
text(17.9,5.7,'功率输出',18,'output')
text(17.9,5.12,r'$P_{out}=P_1\,g_{final}^{\,2}$',20,'output')
arrow((17.9,6.7),(17.9,6.1))
# Route unchanged input power around the outside; it bypasses feature encoding.
ax.plot([1.55,1.55,20.05,20.05],[9.45,10.35,10.35,5.15],color=muted,linewidth=1.2)
arrow((20.05,5.15),(19.6,5.15))
text(11.0,10.57,'原功率 P1 直接用于最终功率修正',17,color=muted)

text(.4,4.35,'训练关系：参考用于监督，不进入推理路径',18,ha='left')
block('pairs',.4,1.15,5.4,2.5)
text(3.1,3.25,'同源配对数据',19,'pairs')
text(3.1,2.7,'输入：相对幅值 X、40维特征 F',17,'pairs')
text(3.1,2.15,'参考：多比特相对幅值 Y',17,'pairs')
text(3.1,1.6,'两路分别按各自帧峰值归一化',17,'pairs')

block('loss',6.6,1.15,6.2,2.5)
text(9.7,3.25,'预测与监督',19,'loss')
text(9.7,2.7,r'$\widehat{Y}=X\,g_{nn}$',20,'loss')
text(9.7,2.15,'八项复合损失：增益、重建、弱峰等',17,'loss')
text(9.7,1.6,'两层推理保护不参与该次训练反传',17,'loss')

block('update',13.6,1.15,6.0,2.5,learned=True)
text(16.6,3.25,'仅更新 MLP 权重和偏置 θ',19,'update')
text(16.6,2.7,'40→32→16→1 的1857个参数',17,'update')
text(16.6,2.15,'固定特征、增益头、保护无可训练参数',17,'update')
text(16.6,1.6,'最终 compact 沿用冻结 v2 神经权重',17,'update')
arrow((5.8,2.4),(6.6,2.4))
arrow((12.8,2.4),(13.6,2.4))
ax.plot([16.6,16.6,10.25],[3.65,4.0,4.0],color=gradient_color,linewidth=1.3,linestyle='--')
arrow((10.25,4.0),(10.25,6.7),style='--',color=gradient_color)
text(12.8,4.2,'训练梯度：仅更新 θ',15,color=gradient_color)
text(10.25,.6,'恢复目标：同源多比特参考的相对幅值结构；图中固定公式采用概念表达',17,color=muted)

fig.canvas.draw()
renderer=fig.canvas.get_renderer()
figure_bounds=fig.bbox
outside=[];container_outside=[];collisions=[]
boxes=[]
for artist,container,label in texts:
    box=artist.get_window_extent(renderer)
    boxes.append((box,label))
    if box.x0<figure_bounds.x0 or box.y0<figure_bounds.y0 or box.x1>figure_bounds.x1 or box.y1>figure_bounds.y1:
        outside.append(label)
    if container:
        x,y,w,h=blocks[container]
        left,bottom=ax.transData.transform((x,y));right,top=ax.transData.transform((x+w,y+h))
        if box.x0<left+4 or box.y0<bottom+4 or box.x1>right-4 or box.y1>top-4:
            container_outside.append(label)
for i,(a,alabel) in enumerate(boxes):
    for b,blabel in boxes[i+1:]:
        if min(a.x1,b.x1)-max(a.x0,b.x0)>0 and min(a.y1,b.y1)-max(a.y0,b.y0)>0:
            collisions.append([alabel,blabel])
assert not outside and not container_outside and not collisions,(outside,container_outside,collisions)
png=HERE/'figures/08_network_architecture.png'
svg=HERE/'figures/08_network_architecture.svg'
fig.savefig(png,dpi=160,facecolor='white')
fig.savefig(svg,facecolor='white',metadata={'Title':'Current compact scalar network and training relationship',
    'Description':'Source checked 40-32-16-1 shared MLP, 1857 parameters, bounded gain, two fixed inference guards, same-source relative-amplitude supervision.'})
plt.close(fig)
source_files=['scalar_restore_v3/pc_candidate_compact/config.json',
              'scalar_restore_v3/pc_candidate_compact/weights.npz',
              'scalar_restore_v3/pc_candidate_compact/restore_power.py',
              'scalar_restore_v3/pc_candidate_compact/scalar_guard.py',
              'scalar_restore_v3/pc_candidate_compact/compact_guard.py',
              'scalar_restore_v2/runs/soft_patch5/config.json',
              'scalar_restore_v2/runs/protected_patch5/training_source.py']
report=dict(status='PASS',scope='Source-checked network architecture figure and layout only',
    layers=layers,parameters=sum(row['parameters'] for row in layers),weights=sum(row['weights'] for row in layers),
    biases=sum(row['biases'] for row in layers),inference_profile_valid_chirps=512,
    feature_groups={'self_and_local':4,'parents':2,'gated_children':2,'derived':8,'other_neighbors':24},
    all_1857_parameters_in_shared_mlp=True,inference_guards_trained_end_to_end=False,
    target_is_relative_amplitude=True,output_is_power=True,reference_used_in_inference=False,
    text_bounds_outside=outside,text_outside_blocks=container_outside,text_collisions=collisions,
    labels=[value for _,_,value in texts],graph=graph,
    output_files={str(file.relative_to(ROOT)):sha(file) for file in [png,svg]},
    source_sha256={name:sha(ROOT/name) for name in source_files},
    frozen_files_checked=len(baseline),changed_sources=changed,
    model_instantiated=False,model_parameters_modified=False,training_run=False,radar_fft_run=False,
    feature_extraction_run=False,neural_inference_run=False,new_quality_test_run=False,
    new_holdout_opened=False,hardware_built=False,board_accessed=False)
(HERE/'reports/NETWORK_ARCHITECTURE_FIGURE.json').write_text(
    json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=report['status'],layers=layers,parameters=report['parameters'],
    text_collisions=collisions,output_files=report['output_files']),ensure_ascii=False))
