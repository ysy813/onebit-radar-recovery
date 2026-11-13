# 便携后级推理

在仓库根目录运行：

```powershell
python tools/infer_postrestore.py --input recovered_input.npz --output new_output.npz
```

依赖 Python、NumPy、SciPy、PyTorch（本次核对环境版本见 `manifests/PORTABLE_CHECK.json`）。输入 NPZ 仅含 `recovered_amplitude`（1024×512，非负、峰归一化后的恢复幅值）和 `original_onebit_peak`（原单比特 uint64 功率谱峰标量）。输出 `output` 和 `gain`。输出文件已存在会拒绝覆盖。

此工具只移除原 `infer.py → run.py → 仿真FFT DLL` 的不必要导入依赖，调用归档的原始特征实现和模型实现；仍采用原代理功率取整、原32→40维变换、1/64至1.5幅值增益。权重先核对冻结SHA256。没有新训练、前端替换或算法变化。

需要完整的符号残差恢复时，源码为 `pc/scalar_sign_evidence_v2/solver.py`，参数为该目录 `PROTOCOL.json` 的solver字段。它是CPU迭代支路，不在此工具内隐式执行；输入恢复谱的含义不要与原单比特功率混淆。

`manifests/PORTABLE_CHECK.json` 记录与两个既有测试帧完整输出的逐点核对和零输入检查；这些是归档接口核对，不是新盲测或新的质量评估。
