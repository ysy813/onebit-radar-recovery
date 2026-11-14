# 选择版本与开始使用

[返回首页](../README.md) · [模型与数据](METHOD_AND_DATA.md) · [结果与证据](RESULTS.md)

## 先决定你要做什么

| 目的 | 从这里开始 | 是否需要大附件 |
|---|---|---|
| 了解模型和结果 | [方法](METHOD_AND_DATA.md)、[结果](RESULTS.md) | 不需要 |
| 浏览全部对照图 | [中文结果网页](../pc/scalar_postrestore_suppress_v1/results/index.html)，下载后本地打开 | 不需要研究数据包 |
| 运行最新 PC 后级网络 | [便携推理说明](../tools/README.md) | 自备规定输入时不需要 |
| 复查完整训练/验证/测试数组 | 研究数据 ZIP＋[数据目录](../manifests/DATA_CATALOG.json) | 需要，约 1.29 GiB |
| 复测 FPGA 网络＋SD | compact SD 修复运行包＋对应操作说明 | 需要运行包，不需要研究数据包 |

GitHub 文件页不会直接运行 HTML。图片本身可以直接打开；要查看完整交互页面，请下载源码后在浏览器打开 `results/index.html`。

## 下载与解压

在[归档 Release](https://github.com/ysy813/onebit-radar-recovery/releases/tag/archive-2026-11-13)下载所需附件，全部**解压到仓库根目录**。

| 附件 | 解压后的主要位置 | 作用 |
|---|---|---|
| `radar1_scalar_compact_exp_v1_runtime.zip` | `hardware/radar1_scalar_compact_exp_v1/pkg/` | compact 原四模式 BIT/ELF/XSA |
| `radar1_scalar_compact_sd_fix_v1_runtime.zip` | `hardware/radar1_scalar_compact_sd_fix_v1/pkg/` | 网络＋SD 模式的新 ELF，沿用同一 BIT |
| `compact_sd_board_data.zip` | `hardware/radar1_scalar_compact_sd_fix_v1/board_runs/` | 60 块、120 MiB 原始 RX0 I/Q |
| `postrestore_all_68_frames_and_outputs.zip` | `pc/` 下对应来源目录 | 68 帧相关数组、训练池及输出 |

核对下载文件：

```powershell
Get-FileHash -Algorithm SHA256 .\postrestore_all_68_frames_and_outputs.zip
```

期望值见 [RELEASE_ASSETS.json](../manifests/RELEASE_ASSETS.json)。源码的“Download ZIP”不包含 Release 附件。

## 硬件实验版

当前网络＋存储入口为 **compact SD 修复版**。它沿用 compact 实验版 BIT，只重新编译了存储启动软件。两包硬件签名均为 `0x71`；不能与旧 V7 的 `0x70` 产物混用。

| 需要了解的内容 | 文档 |
|---|---|
| 硬件网络结构、数值规则、DDR 调度 | [工程与网络说明](../hardware/radar1_scalar_compact_exp_v1/工程与网络说明.md) |
| 原四模式操作 | [上板测试步骤](../hardware/radar1_scalar_compact_exp_v1/上板测试步骤.md) |
| 网络＋SD 的当前操作 | **[SD 修复说明与操作步骤](../hardware/radar1_scalar_compact_sd_fix_v1/修复说明与操作步骤.md)** |
| 配套发布资格 | [SD 修复 BUILD_READY](../hardware/radar1_scalar_compact_sd_fix_v1/pkg/BUILD_READY.json) |

操作文档中的本机绝对路径需要替换成自己的仓库路径。下载脚本会实际操作板卡；查阅源码或运行 PC 推理不需要执行它们。首次复测应保存完整串口，并分别检查显示、网络计数和 SD 读回。

硬件目录中的状态文件是构建时记录，后续已有日志见[证据说明](RESULTS.md#硬件实验版的证据)。完整时序签核和真实恢复质量限制仍保留。

## PC 研究版

最新主候选为 `pc/scalar_postrestore_suppress_v1/candidate/suppress/model_float.pt`。日常推理建议从便携工具开始：

```powershell
python tools/infer_postrestore.py --input recovered_input.npz --output new_output.npz
```

输入必须是**前端已经恢复的幅值谱**及原单比特功率峰；不能直接把原 ADC、符号矩阵、PNG 或原始功率矩阵当成这个输入。字段和数据准备示例见 [tools/README.md](../tools/README.md)。工具不读取真值，也不会隐式启动 CPU 前端。

完整前端代码是 [solver.py](../pc/scalar_sign_evidence_v2/solver.py)，参数位于该目录 [PROTOCOL.json](../pc/scalar_sign_evidence_v2/PROTOCOL.json) 的 `solver` 字段。其输入为符号观测，包含迭代优化，不属于已完成的 PL 实时模块。

## 复现与继续研究的边界

- 原 `run.py`、训练协议、冻结文件及源散列按历史原样保留；数据记录中包含原机器绝对路径。归档提供相对路径索引，未把全部训练脚本改造成换机一键流程。
- 数值前处理使用 Xilinx 位精确 FFT 模型。原生成路径依赖 Windows 和随包的 C model，不能以普通浮点 FFT 替换后仍声称逐点复现。
- 最终测试已读取；若继续改模型或阈值，需另建实验目录和新的最终测试划分，不能覆盖本次冻结结果。
- 目录名 `scalar_multipeak48_v1` 是依赖来源；本次加载的是其中的 `candidate/f40_repair`，不是 48 维主候选。

## 冻结文件与新版说明

本仓库首页及 `docs/` 是当前整理入口。历史工程内的 README、状态文件、绝对路径和报告是原始记录，可能包含当时“尚未板测”的措辞；阅读时结合本仓库的[结果与证据页](RESULTS.md)。文档美化没有改写这些记录或 Release 附件。
