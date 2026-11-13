# 轻量单比特雷达恢复：硬件实验与 PC 去伪研究

本仓库保存两条不同成熟度的工作：**compact 定点网络的 FPGA 实验部署**，以及**最新的恢复后 40 维去伪网络 PC 研究**。它们不共用可直接替换的权重或数值规则。未收录 CDQOB RGB 整网工程。

| 入口 | 内容 | 当前结论 |
|---|---|---|
| [compact PC 模型](pc/scalar_restore_v3/pc_candidate_compact/) | 冻结 v2 神经权重＋512 chirp 紧凑弱峰保护，Q16 内部计算 | 弱峰专项通过，历史整体背景质量 FAIL 保留 |
| [compact FPGA 工程](hardware/radar1_scalar_compact_exp_v1/README.md) | HLS/RTL/自定义IP/软件/模型、720p60、全自然距离索引 | 已构建的实验部署，硬件签名 0x71 |
| [SD 修复与操作](hardware/radar1_scalar_compact_sd_fix_v1/修复说明与操作步骤.md) | 相同 BIT，修复 FAT 空闲计数缓存导致的短写 | 有后续 60 块读回 PASS 日志，详见下文 |
| [最新 PC 去伪结果](pc/scalar_postrestore_suppress_v1/本轮结果.md) | 固定符号残差恢复＋40→32→16→1 后级网络 | 小规模去伪判据通过；存在明显弱目标损失，未部署 |
| [中文对照图](pc/scalar_postrestore_suppress_v1/results/index.html) | 全部12帧同帧对照 | 下载后用浏览器打开；GitHub 普通文件页不执行 HTML |
| [网络理解材料](docs/network_understanding_v1/00_阅读入口.md) | compact 原理、特征、定点、训练沿革 | 历史教学资料，旧绝对链接可能需按目录寻找 |

## 硬件版实际证据

最新存储运行包在 `radar1_scalar_compact_sd_fix_v1_runtime.zip`；完整 compact 四模式运行包在 `radar1_scalar_compact_exp_v1_runtime.zip`。资产均解压到仓库根目录。两个包 BIT 相同，SD 修复包仅提供网络＋存储模式的新 ELF，不能套用旧 V7 的 0x70 包。

构建状态文件保留发布当时的 `board_tested=false`。后来保存的 [串口日志](hardware/radar1_scalar_compact_sd_fix_v1/board_runs/log.txt) 记录：存储60块、读回PASS、acquisition_error=0；网络done=6、fault=0、image_skip=54、infer_ms=3888。配套 CSV 与 `compact_sd_board_data.zip` 的120 MiB原始RX0数据一同保留。本轮只核对保存的证据，没有连接板卡。日志不证明图像质量、无跳帧或实时吞吐达标。

原整体背景质量FAIL与 `full_system_timing_signoff=false` 不变。HLS/数值/发布检查与实际质量分别记录。

## 最新 PC 研究结果与数据

本轮保留输入适配和加强去伪两组，从同一旧权重继续训练，各8000步，验证集均选4000步。增益下限1/64、上限1.5，主候选无固定保护；不能使用旧 `Model.gain()` 的1/8下限。

44训练＋12验证＋12最终测试，共68帧。训练含32帧已看过历史数据和12新帧；训练池165931行保留源帧/频点映射，不是165931独立帧。输入NPZ是原ADC、符号和FFT功率，恢复谱/最终输出NPZ是相对幅值，图像仅用于展示。完整划分、种子、来源、文件散列与仓库相对路径见 [数据目录](manifests/DATA_CATALOG.json)。

`postrestore_all_68_frames_and_outputs.zip` 保存上述68帧相关输入、恢复谱、训练池和本轮数值输出；它不是所有历史训练与实测数据的全量备份。原报告 JSON 的绝对路径保留为冻结证据，另增相对路径目录，不改变历史 SHA。

最终12帧、40米内46目标：参考外残峰由独立恢复8.9167降到1.1667个/帧；主要目标不足半幅0/32，弱目标12/14。残留强互调伪峰与负七次谐波最差表现仍有问题。该通过仅针对预声明小规模去伪研究判据，不是无损恢复、绝对功率恢复或完整物理SAR聚焦验收。前端CPU平均约13.29秒/帧，整体不称实时PL方案。

## 如何使用归档

源代码按 `pc/` 下原同级目录结构保存。`scalar_multipeak48_v1` 只作为旧40维权重、特征和仿真依赖保留，不代表采用48维主候选。原始 `run.py`、`infer.py` 和数据/训练记录不改；冻结训练流程包含本机绝对路径及源散列约束，换机重训需独立新目录与新协议，不能直接覆盖冻结结果。

本次附加的便携后级推理工具位于 `tools/infer_postrestore.py`；只需恢复幅值和原单比特功率峰，不读取标签。具体命令和核对结果见 `tools/README.md`。如重现原位精确 FFT 生成，需要 Windows 和配套 Xilinx C model；库及原版权随依赖保留，不擅自用 NumPy FFT 替代。

发布包清单：[RELEASE_ASSETS.json](manifests/RELEASE_ASSETS.json)；源文件散列：[SOURCE_MANIFEST.json](manifests/SOURCE_MANIFEST.json)。本仓库先按私有保存，未新增整仓开源许可；以后公开前须核对原始工程、厂商库及第三方文件的许可范围。
