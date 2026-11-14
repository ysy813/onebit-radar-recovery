# 便携后级推理

[返回首页](../README.md) · [版本选择](../docs/GETTING_STARTED.md) · [模型与数据](../docs/METHOD_AND_DATA.md)

## 运行环境

需要 Python、NumPy、SciPy、PyTorch。归档核对环境为 Python 3.13.7、NumPy 2.2.6、SciPy 1.16.2、PyTorch 2.8.0+cpu，详见 [PORTABLE_CHECK.json](../manifests/PORTABLE_CHECK.json)。这些是已核对版本，不代表已测试所有其他版本。

## 输入与命令

在仓库根目录运行：

```powershell
python tools/infer_postrestore.py --input recovered_input.npz --output new_output.npz
```

| 输入字段 | 形状与含义 |
|---|---|
| `recovered_amplitude` | 1024×512，非负、峰归一化后的恢复幅值 |
| `original_onebit_peak` | 原单比特 uint64 功率谱峰标量 |

输出 NPZ 含 `output`（去伪幅值）和 `gain`（幅值增益）。输出文件已存在会拒绝覆盖。

## 用归档数据准备一个输入

先将研究数据 ZIP 解压到仓库根目录。下面的 Python 片段在仓库根目录运行，读取整数单目标测试帧，生成 `demo_input.npz`；这个帧是已有结果，不是新盲测。

```python
from pathlib import Path
import numpy as np

folder = Path("pc/scalar_postrestore_suppress_v1/data/test")
output = Path("demo_input.npz")
if output.exists():
    raise FileExistsError(output)
with np.load(folder / "000_single_grid_a_input.npz") as source:
    peak = int(source["base"].max())
with np.load(folder / "000_single_grid_a_spectra.npz") as spectra:
    amplitude = spectra["model"].copy()
np.savez_compressed(output, recovered_amplitude=amplitude,
                    original_onebit_peak=peak)
```

然后运行 `python tools/infer_postrestore.py --input demo_input.npz --output demo_output.npz`。片段只选取恢复幅值和原单比特功率峰；真值、目标标签和多比特参考不送入推理工具。

## 数值规则与适用范围

此工具只移除原 `infer.py → run.py → 仿真FFT DLL` 的不必要导入依赖，调用归档的原始特征实现和模型实现；仍采用原代理功率取整、原32→40维变换、1/64至1.5幅值增益。权重先核对冻结SHA256。没有新训练、前端替换或算法变化。

需要完整的符号残差恢复时，源码为 [solver.py](../pc/scalar_sign_evidence_v2/solver.py)，参数为该目录 [PROTOCOL.json](../pc/scalar_sign_evidence_v2/PROTOCOL.json) 的 `solver` 字段。它是 CPU 迭代支路，不在此工具内隐式执行；输入恢复谱的含义不要与原单比特功率混淆。

[PORTABLE_CHECK.json](../manifests/PORTABLE_CHECK.json) 记录与两个既有测试帧完整输出的逐点核对和零输入检查；这些是归档接口核对，不是新盲测或新的质量评估。
