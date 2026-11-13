import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { Presentation, PresentationFile, FileBlob } from 'file:///C:/Users/yang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';

const SKILL = 'C:/Users/yang/.codex/plugins/cache/openai-primary-runtime/presentations/26.1026.10807/skills/presentations';
const WORK = 'C:/Users/yang/Desktop/SAR_IMAGE/network_understanding_v1/ppt_report_20261105_v1';
const ROOT = 'C:/Users/yang/Desktop/SAR_IMAGE';
const BUILD = path.join(WORK, '.build');
const ASSETS = path.join(BUILD, 'assets');
const OUTPUT = path.join(WORK, '交付');
const FONT = 'Microsoft YaHei';
const { finalizePresentation, applyPresentationChartFont } = await import(pathToFileURL(path.join(SKILL, 'container_tools/artifact_tool_utils.mjs')).href);
await fs.mkdir(OUTPUT, { recursive: true });
await fs.mkdir(path.join(BUILD, 'rendered'), { recursive: true });
const facts = JSON.parse(await fs.readFile(path.join(BUILD, 'facts.json'), 'utf8'));
const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const C = { navy: '#17324D', teal: '#167F83', gray: '#526373', light: '#F0F4F7', border: '#D8E0E7', white: '#FFFFFF', orange: '#B75A29' };
const meta = [];
const owners = { tables: [], charts: [] };

function text(slide, value, x, y, w, h, size = 26, color = C.navy, bold = false, align = 'left') {
  const s = slide.shapes.add({ geometry: 'textbox', position: { left: x, top: y, width: w, height: h }, fill: 'none', line: { fill: 'none', width: 0 } });
  s.text = value;
  s.text.style = { fontSize: size, typeface: FONT, color, bold, alignment: align, verticalAlignment: 'top', autoFit: 'none', wrap: 'square', insets: 0, lineSpacing: 1.15 };
  return s;
}
function base(title, subtitle, notes, sources = [], appendix = false) {
  const s = presentation.slides.add();
  s.background.fill = C.white;
  const n = presentation.slides.items.length;
  text(s, title, 64, 40, 1148, 66, 40, C.navy, true);
  if (subtitle) text(s, subtitle, 66, 111, 1144, 48, 23, C.gray);
  text(s, appendix ? '附录' : '单比特二维频谱标量恢复', 66, 676, 850, 23, 15, C.gray);
  text(s, String(n).padStart(2, '0'), 1144, 674, 70, 25, 17, C.gray, false, 'right');
  s.speakerNotes.text = `${notes}\n\n依据与来源：\n${sources.map(p => p.startsWith('http') ? p : ROOT + '/' + p).join('\n')}\n\n研究对象：scalar_restore_v3/pc_candidate_compact。全部效果数字来自已保存结果，本汇报没有增加训练或测试。`;
  meta.push({ number: n, title, appendix, sources, notes });
  return s;
}
function takeaway(s, value, y = 609, color = C.teal) { text(s, value, 66, y, 1148, 54, 26, color, true); }
function table(s, values, x, y, widths, rowHeights, size = 24) {
  const t = s.tables.add({ rows: values.length, columns: values[0].length, left: x, top: y, width: widths.reduce((a,b) => a+b,0), height: rowHeights.reduce((a,b)=>a+b,0), columnWidths: widths, values });
  t.styleOptions = { headerRow: true, bandedRows: false };
  t.cells.block({ row: 0, column: 0, rowCount: values.length, columnCount: values[0].length }).assign({
    textStyle: { typeface: FONT, fontSize: size, color: C.navy },
    fill: C.white, margins: { left: 12, right: 12, top: 8, bottom: 8 }, anchor: 'middle',
    borders: { top: { fill: C.border, width: 0.7 }, bottom: { fill: C.border, width: 0.7 }, left: { fill: 'none', width: 0 }, right: { fill: 'none', width: 0 } }
  });
  for (let r = 0; r < rowHeights.length; r++) t.rows[r].height = rowHeights[r];
  for (let c = 0; c < values[0].length; c++) {
    const h = t.getCell(0,c); h.fill = C.navy;
    h.text.style = { typeface: FONT, fontSize: size, color: C.white, bold: true };
  }
  owners.tables.push(presentation.slides.items.length);
  return t;
}
async function image(s, filename, x, y, w, h, alt) {
  const b = await fs.readFile(path.join(ASSETS, filename));
  s.images.add({ blob: b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength), contentType: 'image/png', alt, fit: 'contain', position: { left:x, top:y, width:w, height:h } });
}
function chart(s, type, cfg) {
  // Excel literal workbooks retain 15 significant digits. Use 12 for plotted
  // display values only, retaining original source metrics in facts.json.
  for (const series of cfg.series ?? []) {
    for (const key of ['values','xValues']) if (series[key]) series[key] = series[key].map(v => typeof v === 'number' ? Number(v.toPrecision(12)) : v);
  }
  const ch = s.charts.add(type, { chartFill: C.white, plotAreaFill: C.white, chartLine: { fill:'none', width:0 }, plotAreaLine: { fill:'none', width:0 }, ...cfg });
  applyPresentationChartFont(ch, { fontFamily: FONT, availableFonts: [FONT] });
  owners.charts.push(presentation.slides.items.length);
  return ch;
}
const axisText = { fontSize: 20, fill: C.gray };
const grid = { fill: C.border, width: 0.7 };
const N = 'network_understanding_v1/';
const M = 'scalar_restore_v3/pc_candidate_compact/';
const theory = N + '20_理论主讲_单比特失真与恢复依据.md';
const feature = N + '10_第二讲_40维特征与学习增益.md';
const learning = N + '12_第三讲_训练监督与弱峰保护.md';
const evidence = N + 'reports/EVIDENCE_WALKTHROUGH.json';
const comparison = N + '04_原网对照与理论依据.md';

// 01
{
  const s = presentation.slides.add(); s.background.fill = C.navy;
  text(s, '单比特二维频谱的\n轻量标量恢复网络', 78, 140, 1124, 190, 60, C.white, true);
  text(s, '机理特征与共享MLP的幅值增益估计', 82, 370, 1090, 65, 32, '#BFE1E2');
  text(s, '当前 compact 模型的作用、结构、训练与证据', 82, 462, 1100, 55, 25, C.white);
  text(s, '网络原理汇报    2026.11.05', 82, 635, 1100, 35, 21, '#BFE1E2');
  const notes = '本次汇报讨论当前冻结compact标量网络。研究任务是修正单比特I/Q经过二维FFT后的相对幅值失真。重点是信号机理、固定特征、小型MLP、训练监督和保护规则，不涉及部署。完整方法的效果由学习参数与固定保护共同形成。';
  s.speakerNotes.text = notes + '\n来源：' + ROOT + '/' + M + 'config.json';
  meta.push({number:1,title:'单比特二维频谱的轻量标量恢复网络',sources:[M+'config.json'],notes});
}
if (process.argv.includes('--probe')) {
  await fs.writeFile(path.join(BUILD, 'cover.png'), new Uint8Array(await (await presentation.export({ slide: presentation.slides.items[0], format:'png', scale:1 })).arrayBuffer()));
  await (await PresentationFile.exportPptx(presentation)).save(path.join(BUILD,'probe.pptx'));
  console.log('PROBE_PASS'); process.exit(0);
}
// 02
{
 const s=base('研究任务与输入输出','恢复目标是同源多比特参考的相对幅值结构',
 '输入已经是单比特I/Q经过二维FFT后的功率，具有多个强弱等级。数字符号量化发生在FFT之前，每个I/Q分量输出正负64。网络既不输入RGB，也不把每个时域采样的恒定功率直接当作输入。输出保持原频谱坐标，以幅值增益平方修正输入功率。', [M+'restore_power.py',theory]);
 text(s,'1024 × 512',68,186,710,94,65,C.teal,true);
 text(s,'单比特二维FFT功率谱 P₁',70,288,1060,52,33,C.navy,true);
 text(s,'固定特征与共享MLP估计每个谱点的幅值增益',70,380,1120,55,28);
 text(s,'输出功率  P_out = P₁ × g_final²',70,466,1120,66,38,C.teal,true);
 takeaway(s,'推理只读取单比特功率与固定参数，多比特参考仅用于训练和评价');
}
// 03
{
 const s=base('单比特量化的失真来源','理想复单音的方波展开解释有符号谐波',
 'I和Q分别取符号，使正弦分量变为方波。两路联合后的复数傅里叶展开含基波、负三次、正五次、负七次等分量。图是理想单目标数学演示，幅比1/3和1/5不应直接套用于所有多目标实测。多分量先相加再量化，还可能产生互调。', [theory,N+'figures/01_sign_harmonics.png']);
 await image(s,'harmonics.png',64,175,1150,393,'理想正弦量化与有符号谐波数学演示');
 text(s,'多分量先叠加再量化，还会产生互调与频谱重合',68,590,1140,52,28,C.teal,true);
}
// 04
{
 const s=base('有损量化后的恢复空间','正负号排列仍可能保留相对结构信息',
 '正尺度不变性可以直接证明绝对幅度不可唯一恢复。另一方面，多个分量的相对强弱变化可能改变合成波形过零时刻，进而改变符号序列和FFT功率。因此学习估计仍有空间。相同观测也可能对应不同参考，统计估计无法消除这种歧义。当前模型没有输入或恢复复相位。', [theory]);
 text(s,'Q(αx) = Q(x)，α > 0',70,190,1100,68,43,C.teal,true);
 text(s,'整体放大不改变符号，绝对幅度缺少唯一恢复依据',70,277,1120,52,27);
 text(s,'分量相对强弱变化，可能改变过零位置与频谱结构',70,368,1120,60,30,C.navy,true);
 text(s,'配对训练利用这些剩余线索，估计更合适的修正',70,461,1120,60,29);
 takeaway(s,'方法定位：受约束的统计恢复，不承诺逐点精确还原');
}
// 05
{
 const s=base('当前网络的整体结构','固定特征整理线索，共享MLP学习增益，规则减轻部分误压',
 '按图从左向右讲。输入功率一路保留，用于最后的乘法。另一路归一化并提取40维特征，MLP产生分数，有界指数头产生幅值增益，两阶段保护调整部分弱峰，最后功率乘增益平方。图按512有效chirp路径绘制。当前compact沿用冻结v2神经权重，新增紧凑保护，不是新训练出的第二套网络。', [M+'restore_power.py',M+'config.json',N+'figures/08_network_architecture.png']);
 await image(s,'inference.png',60,180,1158,356,'当前compact网络的512有效chirp推理路径');
 text(s,'可训练部分：40 / 32 / 16 / 1 MLP，共1857个参数',70,558,1110,48,29,C.teal,true);
 text(s,'当前 compact 使用冻结v2权重，保护规则不含可训练参数',70,615,1110,40,24,C.gray);
}
// 06
{
 const s=base('归一化与五次根编码','同一相对幅值同时使用压缩表示与解码表示',
 '先按输入帧峰值将功率转换为相对幅值X，再取五次根得到z。编码单调展开弱值，便于小型网络使用较大动态范围。它本身不区分弱目标、弱伪影与弱噪声。派生项取五次方是近似逆编码，与第五谐波不是同一含义。整数近似在此省略。',[M+'restore_power.py',feature]);
 text(s,'X = √(P₁ / max P₁)       z = X^(1/5)',70,184,1140,68,37,C.teal,true);
 table(s,[['相对幅值 X','五次根编码 z','含义'],['1','1','帧峰尺度'],['0.1','0.631','压缩动态范围'],['0.01','0.398','展开较弱数值'],['0.001','0.251','弱目标与弱伪影都会展开']],70,285,[260,320,550],[55,58,58,58,58]);
 takeaway(s,'编码改变数值表示，恢复效果来自后续增益估计与保护');
}
// 07
{
 const s=base('固定40维特征的组成','每个谱点都有一份描述，所有位置使用相同计算规则',
 '前4项依次为中心编码、3×3最大值、3×3均值、9×9均值。父子关联各2项。实现先组织8项自身统计与关联，再增加24个邻居，进入MLP前插入8项派生值。24邻居保留位置排列，统计均值不保留排列。父子查询可以跨越整幅频谱，不能把5×5称为全部信息范围。',[M+'restore_power.py',M+'model_source.py',feature]);
 await image(s,'neighbors.png',64,183,437,450,'5乘5内24邻居与中心的位置示意');
 table(s,[['内容','维数','提供的信息'],['自身与局部统计','4','强度、峰值与底座'],['候选父提示','2','可能的谐波来源'],['门控子提示','2','倍频位置的支持'],['幅值及关系派生','8','比例和局部偏差'],['其余5×5邻居','24','局部形状与排列']],527,190,[238,80,350],[54,65,65,65,65,65],23);
}
// 08
{
 const s=base('三次与五次谐波关联','两维频率同时倍乘，离散频谱按各自长度折叠',
 '图的坐标是FFT自然索引，不是米或角度。对理想二维单音，h阶分量中心位于(hr mod1024,ha mod512)。子提示查询负三倍和正五倍位置，并用局部对比门控降低平滑底座支持。父提示反过来查询可能解释当前点的候选来源。几何相容不能证明真假目标。', [theory,feature,N+'figures/02_alias_coordinates.png']);
 await image(s,'alias.png',62,175,735,447,'理想二维谐波索引折叠示例');
 text(s,'父提示',835,207,350,45,31,C.teal,true);
 text(s,'当前点可能来自哪些\n更强峰的谐波',835,268,365,90,27);
 text(s,'门控子提示',835,388,350,45,31,C.teal,true);
 text(s,'当前点的倍频位置\n是否有局部突出支持',835,449,365,90,27);
 text(s,'关联提供候选线索，MLP结合局部结构决定增益',68,625,1140,36,24,C.gray);
}
// 09
{
 const s=base('8个派生项的作用','提前提供幅值尺度与关系差，降低小MLP表达这些关系的负担',
 '五个五次方来自中心、两个父提示及两个门控子提示。令A=z的五次方，B3、B5为父提示解码值，关系项为限幅的3A−B3与5A−B5。最后一项是A减3×3编码均值的五次方，不是中心减真实幅值均值。扩维没有增加新的雷达观测，也没有消除量化歧义。是否优于不加派生项需要消融，当前没有充分证据断言最优。',[M+'model_source.py',feature]);
 table(s,[['分组','数量','表达式与作用'],['幅值近似解码','5','中心、父提示、子提示分别取五次方'],['谐波关系差','2','clip(3A − B₃) 与 clip(5A − B₅)'],['局部差异','1','A − [3×3编码均值]⁵']],70,190,[250,100,780],[60,105,105,105],26);
 text(s,'A = z⁵，B₃ / B₅为父提示的解码值，clip范围为[−1, 1]',72,588,1120,48,23,C.gray);
}
// 10
{
 const s=base('共享MLP与逐点增益分数','全部谱点共用一套权重，输入特征不同可产生不同输出',
 '第一层40到32，第二层32到16，最后16到1。前两层使用ReLU，最后线性层保留正负分数。参数包含1808个权重与49个偏置。共享指整帧复用同一组参数，并非各神经元使用相同权重。分数是log2增益的回归量，不是目标分类概率。',[M+'model_source.py']);
 table(s,[['层','激活','权重＋偏置','参数'],['40 至 32','ReLU','1280 ＋ 32','1312'],['32 至 16','ReLU','512 ＋ 16','528'],['16 至 1','线性','16 ＋ 1','17'],['合计','整帧共享','1808 ＋ 49','1857']],70,190,[260,240,370,260],[58,68,68,68,68],26);
 takeaway(s,'MLP学习40维线索的组合，输出每个谱点的修正分数 s');
}
// 11
{
 const s=base('有界幅值增益与功率修正','s控制乘法尺度，功率使用幅值增益的平方',
 '先将s限幅到负3与log2的1.5，再取2的幂。s为0时增益1，s为负1时增益0.5。增益范围0.125到1.5，给出受约束的修改。功率等于幅值平方，因此输出功率乘g平方。图是固定公式的数学曲线，不是网络性能测试。',[M+'model_source.py',M+'restore_power.py']);
 const xs=Array.from({length:51},(_,i)=>-4+i*.1);
 chart(s,'scatter',{position:{left:62,top:180,width:690,height:410},series:[{name:'幅值增益',xValues:xs,values:xs.map(x=>2**Math.max(-3,Math.min(Math.log2(1.5),x))),line:{fill:C.teal,width:3},marker:{symbol:'none'}}],hasLegend:false,scatterOptions:{style:'line'},xAxis:{min:-4,max:1,majorUnit:1,crossesAt:-4,title:'MLP分数 s',textStyle:axisText,majorGridlines:null},yAxis:{min:0,max:1.6,majorUnit:.4,title:'幅值增益 g_nn',textStyle:axisText,majorGridlines:grid}});
 text(s,'g_nn = 2^clip(s)',805,211,395,64,35,C.teal,true);
 text(s,'范围  0.125 至 1.5',805,306,395,48,27);
 text(s,'P_out = P₁ × g_final²',805,412,395,83,30,C.navy,true);
 text(s,'输入严格为零时，\n乘法仍输出零',805,522,395,70,25,C.gray);
}
// 12
{
 const s=base('输入驱动的弱峰保护','保护调整增益，减轻部分候选峰的额外衰减',
 '这页讲512有效chirp路径。软弱峰保护考虑相对弱功率、局部峰形、强父谐波解释及原增益。帧峰锚定将输入功率最大位置增益设为1。compact再考虑中心与9×9编码均值之比，从1.4到1.6逐渐增加紧凑度权重，结合第一保护后的增益撤回部分衰减。完整资格还包括相对功率范围、9×9局部最大和无强父解释。规则不读取多比特参考或物理目标标签，可能保留伪峰。',[M+'scalar_guard.py',M+'compact_guard.py']);
 table(s,[['规则','检查的信息','主要作用'],['软弱峰保护','弱功率、局部峰、谐波线索、原增益','减轻部分弱峰误压'],['帧峰锚定','输入帧最大功率位置','最终幅值增益保持1'],['compact紧凑保护','中心 / 9×9编码均值及已有增益','对部分集中弱峰追加保护']],70,185,[270,560,300],[58,95,95,110],24);
 text(s,'紧凑度比值 1.4 至 1.6 连续过渡，比较的是编码值，不能当作SNR',72,575,1120,52,24,C.gray);
}
// 13
{
 const s=base('同源配对训练与监督','同一份回波构造单比特输入和多比特参考',
 '两条支路采用对应的二维FFT数值链，并在同一频谱坐标比较。X来自单比特功率，Y来自多比特参考，各按自己的帧峰值归一化。40维特征只从输入提取。训练预测是X乘神经增益，通过损失反传更新MLP。增益头无参数但参与导数链，最终两阶段推理保护未参与所选训练。当前compact沿用冻结v2权重。',[learning,N+'21_网络主讲_训练参考与证据范围.md',N+'figures/08_network_architecture.png']);
 text(s,'输入：单比特相对幅值 X 与特征 F',72,185,1120,50,30);
 text(s,'参考：同源多比特相对幅值 Y',72,255,1120,50,30);
 text(s,'训练预测  Ŷ = X × g_nn',72,331,1120,62,39,C.teal,true);
 await image(s,'training.png',62,433,1155,158,'配对训练比较预测与参考，仅更新MLP参数');
 text(s,'多比特参考仅用于监督，实际推理不读取参考',72,615,1120,40,25,C.teal,true);
}
// 14
{
 const s=base('八项复合损失的分工','同时约束重建误差、伪影过估计与部分弱峰损伤',
 '按所选训练代码快照说明八项损失，不能仅凭当前工作目录的训练脚本推断历史。头监督目标是带防零小常数的log2(Y/X)，限幅后监督原始分数。幅值和对数损失比较预测与参考。退化惩罚还与旁路误差比较。掩码由参考支持、受控目标及低背景定义，各项的尺度与归一化不同，系数不能简单比较重要性。总损失对参数的导数由反向传播计算，Adam在批次上逐步更新。',[ 'scalar_restore_v2/runs/protected_patch5/training_source.py',learning]);
 table(s,[['损失项','训练时希望减少的现象'],['log₂增益监督','分数偏离参考比例对应的合理增益'],['对数幅值误差','较弱分量的差异未得到足够关注'],['幅值平方误差','预测整体偏离参考幅值结构'],['支持区域退化惩罚','处理后比旁路更伤害参考支持区域'],['峰与目标相对退化惩罚','少量峰的相对损伤被整体均值掩盖'],['过估计惩罚','输出在特定过估计区域仍高于参考'],['低背景放大惩罚','低参考背景的增益大于1'],['重点目标保护','部分目标额外退化或被压至参考约半幅以下']],70,176,[395,735],[47,48,48,48,48,48,48,48,48],22);
 text(s,'训练只更新MLP权重与偏置，两阶段推理保护没有参与所选训练反传',72,636,1120,28,20,C.gray);
}
// 15
{
 const s=base('与原CDQOB-Net的关系','共同研究单比特退化恢复，当前方法重新定义标量增益任务',
 '原交付模型使用RGB输入、多尺度卷积和拼接，输出也是RGB。其修正头为clip(h乘I减h加1)，不能把h直接当作当前幅值增益。当前方法从功率提取机理特征，用共享MLP预测有界幅值增益。原网参数378575，当前1857，但变量与目标不同，不能由参数减少推出效果等价。当前不是从原网直接剪下几层，也没有完成保持其全部效果的完整蒸馏。',[comparison,'cdqob_pc_online_v1/model.py']);
 table(s,[['比较项','原交付RGB网络','当前compact标量方法'],['输入','可视化编码RGB图像','FFT功率与40维数值特征'],['表示方式','多尺度CNN与通道拼接','机理特征与共享MLP'],['输出','三通道RGB图像','一个受限幅值增益，修正功率'],['参数规模','378575','1857'],['恢复方向','向多比特参考图像靠近','向多比特相对幅值结构靠近']],70,185,[210,460,460],[54,65,65,70,60,78],24);
 text(s,'当前方法是独立轻量设计，原网效果不能直接作为本方法的质量证明',72,626,1120,38,24,C.teal,true);
}
// 16
{
 const s=base('实验分组与评价口径','同帧、同坐标、统一增强输出尺度，分开报告目标与背景',
 '已有冻结测试22条，包括16条合成和6条实测派生记录。实测来自同次采集的3源帧、各RX0和RX3两通道，不是6个独立场景。128有效chirp补零至512，不增加有效观测。评价参考和旁路各用自身峰值，增强沿用旁路尺度。已知目标在参考的周期5×5内选峰，所有方法在同一位置读取。NMSE是相对幅值误差，不是检测率。',[evidence,N+'17_已有效果指标的口径核对.md']);
 table(s,[['数据组','记录数','已知目标 / 弱目标','结论适用范围'],['合成128有效chirp','8','56 / 48','受控数值目标'],['合成512有效chirp','8','64 / 48','受控数值目标'],['实测128有效chirp','6','无完整物理标签','同次采集的时段划分']],70,190,[330,130,320,350],[60,90,90,105],24);
 text(s,'目标：同位置幅值与半幅损失    整体：幅值NMSE    背景：正误差平方和',72,576,1120,72,24,C.teal,true);
}
// 17
{
 const s=base('同帧RD功率谱对照','合成512有效chirp样例，比较参考、旁路与当前compact输出',
 '这三个裁剪来自同一份已保存四路对照图，样例compact_synth_128001_512。省略的第四路是先前v2，本页只展示参考、单比特旁路和当前compact。图使用全距离自然索引，横轴为显示移位后的Doppler bin。参考和旁路分别按自身峰值，当前输出共用旁路尺度，统一负60到0dB。圈标受控已知弱目标。视觉上部分散布背景和条纹降低，但仍存在残留。单帧图片不证明跨场景有效或物理SAR聚焦。',[ 'scalar_restore_v3/results_compact/images/compact_synth_128001_512.png',evidence]);
 for (const [i,name] of ['多比特参考','单比特旁路','当前compact'].entries()) text(s,name,68+i*366,178,342,45,28,C.navy,true,'center');
 await image(s,'rd-reference.png',58,230,356,300,'合成512chirp多比特参考RD谱');
 await image(s,'rd-bypass.png',424,230,356,300,'同帧单比特旁路RD谱');
 await image(s,'rd-compact.png',790,230,356,300,'同帧compact增强RD谱');
 await image(s,'rd-colorbar-strip.png',1160,246,18,258,'统一归一化幅值色标负60至0dB');
 for (const [i,label] of ['0','−20','−40','−60'].entries()) text(s,label,1181,236+i*86,45,24,17,C.gray);
 text(s,'dB',1163,516,60,25,17,C.gray);
 text(s,'部分散布背景与量化伪影减弱，仍需数值指标检查目标保留',72,571,1110,53,29,C.teal,true);
 text(s,'样例 compact_synth_128001_512，圆圈标注合成已知弱目标，纵轴为距离索引',72,634,1120,28,19,C.gray);
}
// 18
{
 const group=facts.groups.synthetic_512;
 const s=base('512有效chirp组的弱目标结果','8条受控记录，共64个已知目标，其中48个弱目标',
 '这页只报告512有效chirp组，避免把128组混入。低于参考半幅的已知目标从29降为17，新增向下跨半幅为0。这不表示全部弱目标恢复，也不表示任意参考局部峰都未下降。弱目标绝对误差之和相对旁路为0.798136，下降约20.2%。数据来自受控合成，不应叫外场检测率。',[evidence]);
 chart(s,'bar',{position:{left:66,top:188,width:660,height:390},categories:['单比特旁路','当前compact'],series:[{name:'低于参考半幅的已知目标',values:[group.baseline_below_half,group.enhanced_below_half],fill:C.teal,points:[{idx:0,fill:'#859AA9'},{idx:1,fill:C.teal}]}],barOptions:{direction:'column',grouping:'clustered',gapWidth:100},hasLegend:false,xAxis:{textStyle:axisText},yAxis:{min:0,max:35,majorUnit:5,title:'已知目标数量',textStyle:axisText,majorGridlines:grid},dataLabels:{showValue:true,position:'outEnd',textStyle:{fontSize:27,fill:C.navy,bold:true}}});
 text(s,'约20.2%',790,201,420,90,58,C.teal,true);
 text(s,'弱目标绝对幅值误差\n相对旁路下降',790,302,420,86,28);
 text(s,'0 个',790,425,420,67,43,C.navy,true);
 text(s,'已知目标新增半幅损失',790,505,420,55,25);
 takeaway(s,'17个目标仍低于参考半幅，不能宣称全部恢复');
}
// 19
{
 const group=facts.groups.synthetic_512;
 const s=base('背景抑制与弱峰保留的取舍','512合成组的背景正误差仍高于较早V7标量模型',
 '旧V7指早期标量网络，并非原CDQOB-Net。当前512组合的背景正误差相对V7为1.202078，旧门槛为1.10，因此原整体质量FAIL保持。弱峰专项通过不能覆盖该失败。全体数值参考局部峰另有1处新增下降，不在已知目标所选峰集合内，不能隐去也不能未经标注称为真实漏检。保护依赖输入形态，可能撤回对伪影本来有利的衰减。',[evidence,N+'17_已有效果指标的口径核对.md','scalar_restore_v3/RESULTS_COMPACT.json']);
 chart(s,'bar',{position:{left:66,top:190,width:660,height:384},categories:['V7基准','原背景门槛','当前compact'],series:[{name:'背景正误差 / V7',values:[1,1.1,group.background_error_relative_to_v7],fill:C.teal,points:[{idx:0,fill:'#859AA9'},{idx:1,fill:'#B1BBC4'},{idx:2,fill:C.orange}]}],hasLegend:false,barOptions:{direction:'column',gapWidth:100},xAxis:{textStyle:axisText},yAxis:{min:0,max:1.5,majorUnit:.3,title:'背景正误差 / V7',textStyle:axisText,majorGridlines:grid},dataLabels:{showValue:true,numberFormatCode:'0.000',position:'outEnd',textStyle:{fontSize:25,fill:C.navy,bold:true}}});
 text(s,'原整体门槛未通过',780,206,425,60,34,C.orange,true);
 text(s,'弱峰保护可能同时\n保留部分伪峰',780,309,420,95,29);
 text(s,'全部数值参考局部峰\n仍有1处新增下降',780,446,420,90,27);
 takeaway(s,'目标保留与背景误差需分别报告，图像更暗不能单独证明恢复更好',612,C.orange);
}
// 20
{
 const s=base('方法结论与论证边界','机理特征、学习增益与固定保护共同形成当前效果',
 '结束时把理论、设计和实验分开。理论可解释谐波位置、尺度歧义和增益平方关系。40维、五次根、隐藏宽度及阈值包含经验选择，不是由理论唯一推出。当前实验支持已有数据条件下的幅值改善与弱峰取舍，尚不能证明绝对功率、相位恢复、跨场景普遍有效或原网等价性。整体背景门槛仍未通过，不能据弱峰专项通过宣布全部质量通过。',[theory,comparison,evidence]);
 table(s,[['论证层次','当前可以说明的内容'],['数学机理','符号失真、谐波折叠、相对结构与尺度歧义'],['方法设计','40维固定特征与1857参数MLP估计受限增益'],['已有实验','部分幅值误差与弱峰保留改善，背景存在取舍'],['尚未证明','精确幅相反演、跨场景泛化、结构与阈值最优性']],70,188,[265,865],[60,90,90,90,90],26);
}
// 21 appendix
{
 const s=base('附录：两阶段保护的概念公式','以下为512有效chirp路径，省略整数舍入与饱和',
 '软保护候选需要弱功率、9×9局部最大或near条件、无强父谐波解释。注意负40dB下限只属于第一层near分支，不适用于独立局部最大分支。compact候选必须达到帧峰万分之一、不高于帧峰十六分之一、是9×9最大且无强父解释。t按输入增益从0.25到0.5连续变化。c按中心与9×9编码均值的比从1.4到1.6变化。第二层使用g1而不是原gnn。帧峰锚定单独设1。',[M+'scalar_guard.py',M+'compact_guard.py',learning],true);
 text(s,'t(g) = clip((g − 0.25) / 0.25, 0, 1)',70,187,1120,55,31,C.teal,true);
 text(s,'软保护候选： g₁ = g_nn + max(1 − g_nn, 0) × t(g_nn)',70,274,1120,63,29);
 text(s,'c = clip(5z / max(μ₉(z), 1/32) − 7, 0, 1)',70,365,1120,58,30,C.teal,true);
 text(s,'紧凑候选： g_final = g₁ + max(1 − g₁, 0) × c × t(g₁)',70,454,1120,65,29);
 text(s,'候选外保持对应阶段输入增益，输入帧峰值位置锚定为1',70,565,1120,46,25,C.gray);
}
// 22 appendix
{
 const s=base('附录：训练与结果的追溯依据','全部解释对应当前冻结版本，来源详见各页备注',
 '若被问及原理依据，首先说明符号非线性与傅里叶展开是可推导的机理。若被问及模型参数，定位model_source和weights。若被问及八项损失，定位protected_patch5训练快照，其散列与所选soft_patch5配置一致。若被问及效果，定位22条已保存输出及同口径指标核对。当前训练记录62条，其中32合成30采集派生，并非62个独立场景。本文没有重新训练、推理或测试。',[M+'model_source.py',M+'config.json','scalar_restore_v2/runs/protected_patch5/training_source.py','scalar_restore_v2/runs/soft_patch5/config.json',evidence,comparison],true);
 table(s,[['内容','可核查来源'],['模型与40维特征','pc_candidate_compact / model_source.py、restore_power.py'],['固定保护','scalar_guard.py、compact_guard.py'],['八项损失与训练','protected_patch5 / training_source.py，匹配所选配置散列'],['当前效果','compact_fresh_test / report.json 与 EVIDENCE_WALKTHROUGH'],['原网对照','CDQOB-Net交付代码与《原网对照与理论依据》']],70,187,[265,865],[58,85,70,85,85,85],24);
}

await fs.writeFile(path.join(BUILD,'SLIDE_MANIFEST.json'),JSON.stringify({slide_count:meta.length,slides:meta,owners},null,2));
const candidate=path.join(BUILD,'candidate.pptx');
await (await PresentationFile.exportPptx(presentation)).save(candidate);
console.log('DRAFT_EXPORTED',meta.length);
await fs.writeFile(path.join(BUILD,'native-montage.webp'),new Uint8Array(await (await presentation.export({format:'webp',montage:true})).arrayBuffer()));
if (process.argv.includes('--draft-only')) {
  for (let i=0;i<presentation.slides.items.length;i++) {
    const png=await presentation.export({slide:presentation.slides.items[i],format:'png',scale:1});
    await fs.writeFile(path.join(BUILD,'rendered',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
    console.log('RENDERED',i+1);
  }
  console.log('DRAFT_READY'); process.exit(0);
}
const finalName=process.env.SAR_REPORT_OUTPUT || 'compact标量网络_作用与原理_汇报版_v1.pptx';
const finalPath=path.join(OUTPUT,finalName);
await finalizePresentation({
 workspaceDir:WORK,candidatePath:candidate,finalPath,
 pythonExecutable:'C:/Users/yang/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
 integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),
 explicitTotalSlideCount:22,
 requiredNativeTableOwnerSlides:[...new Set(owners.tables)],requiredNativeChartOwnerSlides:[...new Set(owners.charts)],
 materializeLiteralChartWorkbooks:true,
 fontPolicy:{basis:'design',families:[FONT]},
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...[...new Set(owners.tables)].flatMap(n=>['--require-native-table-slide',String(n)])],
 verifyArtifactToolImport:true,receiptPath:path.join(BUILD,finalName+'.validation.json')
});
console.log('FINALIZED',finalPath);
const finalized=await PresentationFile.importPptx(await FileBlob.load(finalPath));
for(let i=0;i<finalized.slides.items.length;i++){
 const png=await finalized.export({slide:finalized.slides.items[i],format:'png',scale:1});
 await fs.writeFile(path.join(BUILD,'rendered',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
 console.log('RENDERED',i+1);
}
await fs.writeFile(path.join(BUILD,'DELIVERED.json'),JSON.stringify({status:'FINALIZED',file:finalPath,slides:meta.length,notes:true},null,2));
console.log('REPORT_READY');
