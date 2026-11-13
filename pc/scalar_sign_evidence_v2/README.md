# 符号残差候选与40维网络：第二轮实验

本轮先完成用户授权的两点修正：补足漏检候选、取消证据不足时的额外强压。保留旧网络，比较独立恢复和组合输出。没有训练新MLP权重，没有改动已发布工程或访问板卡。

完成后先看：

先读短版[研究结论](研究结论.md)，了解改进是否有效、失败位置及组合判断。

1. [本轮结果](本轮结果.md)：同一批最终数据的全部方法、门槛、结果与限制。
2. [中文全量图集](results/index.html)：12帧，含强弱、多目标及谐波重合场景。
3. [逐目标失败诊断](逐目标失败诊断.md)：漏检、定位范围、删减和保护证据。
4. [方法与数据说明](方法与数据说明.md)：具体改动、原理、接法与研究边界。
5. [数据索引](数据索引.md)：每帧NPZ、来源、种子和用途；机器清单为DATA_REGISTER.json。

`FROZEN.json`记录验证集选定的融合权重和冻结代码SHA。`reports/STANDARD_CHECK.json`仅检查实现、来源和推理复现；质量结论以`reports/TEST_SUMMARY.json`为准。

## 在PC对已有符号与功率推理

在工作区根目录运行：

```powershell
& "C:\Users\yang\AppData\Local\Programs\Python\Python313\python.exe" -X utf8 .\scalar_sign_evidence_v2\infer.py --input .\scalar_sign_evidence_v2\reports\CLI_INPUT_ONLY.npz --output .\scalar_sign_evidence_v2\results\my_inference.npz
```

输入只需要三个NPZ字段：`sign_i`、`sign_q`为1024×512的±1符号，代表硬件两电平±64的正负；`base`为同帧单比特FFT的1024×512 uint64功率。输出含旧40维网络、残差恢复、仅保护和冻结权重融合的相对幅值。不是SAR聚焦图，也不带绝对功率标定。脚本拒绝覆盖已有输出。

## 复现与依赖

源码依赖`scalar_multipeak48_v1/`内冻结模型、特征、场景生成和Xilinx FFT参考，以及本目录求解器。不是可脱离工作区的完整独立运行包。依赖SHA记录在SOURCE_SNAPSHOT.json及data内清单。

本轮过程顺序是`experiment_v2.py development`、`validation`、`freeze`、`test`。已有结果会做SHA核对后复用，freeze拒绝覆盖。新的研究不要在这里改参数后覆盖结果，应复制到新目录并重新声明数据划分。

报告与检查命令：

```powershell
& "C:\Users\yang\AppData\Local\Programs\Python\Python313\python.exe" -X utf8 .\scalar_sign_evidence_v2\report.py
& "C:\Users\yang\AppData\Local\Programs\Python\Python313\python.exe" -X utf8 .\scalar_sign_evidence_v2\diagnose.py
& "C:\Users\yang\AppData\Local\Programs\Python\Python313\python.exe" -X utf8 .\scalar_sign_evidence_v2\standard_check.py
```

两帧开发复用已知失败数据；6帧新验证选融合比例；冻结后12帧新测试只用于评价。没有本轮训练集；求解器在当前帧估计复系数和频率，不等于重新训练网络。最终测试已被分析，后续不能称未见盲测。
