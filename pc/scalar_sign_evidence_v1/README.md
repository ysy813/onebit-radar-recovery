# 有限符号证据PC验证

先看[本轮验证结果](本轮验证结果.md)，再看[十二帧中文对照图](results/index.html)。方法解释见[方法与改动说明](方法与改动说明.md)，问题定位见[失败定位与后续改进](失败定位与后续改进.md)，数据见[数据索引](数据索引.md)和DATA_REGISTER.json。

本轮保持零阈值两电平、不加窗；完成符号恢复原型及其与冻结40维网络的门控组合，没有训练新权重或生成IP/BIT。旧模型、工程与48维实验不变。它不是完整DR-GAMP复现，也未确认算法原创性。

## 文件对应关系

- `sign_solver.py`：仅从原始符号提取候选、拟合复回波、稀疏筛选、比较有/无候选的解释；不接收多比特参考或真值。
- `run_experiment.py`：生成仿真数据，调用冻结旧40维网络和新算法，验证选门槛、冻结、最终测试。
- `infer.py`：独立PC推理入口，只读sign_i、sign_q和base三个输入数组。
- `PROTOCOL.json`、`FROZEN.json`：预声明参数、质量判据、验证集选择值及测试前冻结散列。
- `data/`：原始整数I/Q、符号和位精确FFT功率；`results/`：相对幅值谱和图；`reports/`：逐目标、逐候选和完整抽样位置。
- `pilot_margin_v0/`：开发阶段初始方法及失败结果，不与最终模型混用。
- `reports/STANDARD_CHECK.json`：完整性与独立CLI检查，不代表质量通过。

## 复现现有结果

在`C:\Users\yang\Desktop\SAR_IMAGE`打开PowerShell，使用已有Python环境。代码依赖工作区保留的`scalar_multipeak48_v1`源码、权重和Xilinx FFT模型，不能只复制本文件夹就称可独立重建全部实验。

```powershell
& "C:\Users\yang\AppData\Local\Programs\Python\Python313\python.exe" -X utf8 .\scalar_sign_evidence_v1\run_experiment.py preflight
& "C:\Users\yang\AppData\Local\Programs\Python\Python313\python.exe" -X utf8 .\scalar_sign_evidence_v1\build_report.py
```

独立推理示例，输出文件必须尚不存在：

```powershell
& "C:\Users\yang\AppData\Local\Programs\Python\Python313\python.exe" -X utf8 .\scalar_sign_evidence_v1\infer.py --input .\scalar_sign_evidence_v1\data\test\000_single_grid_a.npz --output .\scalar_sign_evidence_v1\my_inference.npz
```

输入NPZ即使包含reference字段，CLI也不读取它。标准检查另创建只含三个合法输入字段的文件并对照推理。`my_inference.npz`输出old40/model/gated三幅相对幅值，配套JSON包含证据与耗时。不是下载板卡指令。

重新生成全套实验应复制源码及依赖记录到新的实验目录，依次preflight、development、validation、freeze、test、build_report。不要删除已有FROZEN或测试结果来悄悄重选参数；当前目录默认复用已核对缓存。
