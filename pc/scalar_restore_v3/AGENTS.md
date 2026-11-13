本轮在保留严格两电平（有效分量x>=0取+64，否则-64）的前提下继续优化网络。补零在量化之后；不把数值0直接当无效采样。RX0/RX3按用户确认处理，主排列为chirp内RX块；另一排列只是稳健性检查。

scalar_restore_v2、冻结V7、radar1及已发布BIT/ELF/备份只读。本轮仅在本目录新增代码、数据缓存、权重与报告；不访问板卡/JTAG/串口，不生成子代理。所有处理保持0–1023自然距离索引，评估重点约1.5m以外，不能靠裁掉失败点提高指标。

用户要求自主定位问题、选择方法并完成迭代，不需要用户提供算法建议。用户指出当前512图像视觉效果已好：先核对背景误差相对/绝对大小、目标可见性和误警，再决定其优先级，不能因单个代理指标否定整网。原v2的质量FAIL记录保持不变，不事后改成PASS；新指标须写清意义并在新留出结果读取前声明。

此前102000/108000/116000种子及已读取实测帧只能当开发诊断，不能再次称独立盲测。新模型先用训练/开发集选择，冻结后才读取新的预声明测试。数据按原始采集帧分组所有通道/排列；同一次采集的时间划分不称跨场景验证。数值/接口PASS与恢复质量分别记录。

## 本轮完成状态

当前入口仅为 `pc_candidate_compact/` 和 `results_compact/index.html`，先读 `README.md`、`弱目标修正结果.md`、`操作说明.md`、`BUILD_STATUS.json`。最终是原v2冻结神经权重加512chirp紧凑弱峰保护，128chirp保持原输出；不要把训练微调、profiled、fresh_test或旧export/finalize脚本混作最终候选。

开发诊断570个、新留出120个已知目标均无新增半幅损失；`NUMERIC_VERIFICATION_COMPACT.json`与`STANDARD_CHECK_COMPACT.json`为PASS。原整体质量仍FAIL，唯一失败项为512合成背景误差约1.202倍V7超过旧1.10门槛，不能把弱目标单项PASS改称整体PASS或上板验证。没有新IP/BIT/ELF或板卡访问。

最终记录是 `compact_development/report.json`、`compact_fresh_test/report.json`、`RESULTS_COMPACT.json`。两例原误压点恢复到旁路幅值，不代表恢复全部多比特幅值或真实物体全保留。seed124000–124031第一次留出FAIL保持不变，改规则后已作为开发诊断；seed128000–128015与实测455/519/583帧已经读取，未来不可再次当新盲测。

运行包 `release/scalar_restore_v3_compact_weakfix.zip`，SHA256为00619e643b093e3d17a99908aa1668e594b2f8575ec01da1a5b5bbfec48cbe86，CRC与逐文件SHA读回通过。该包仅PC运行代码/冻结权重/规则/报告/图像/两份FFT功率示例，不含原ADC或完整训练缓存。最终规则源码为 `compact_guard.py`，未来IP适配必须实现此层，不能只复制权重。
