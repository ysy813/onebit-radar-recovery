# 修改与验证记录

## 2026-11-02 实验部署

- 用户授权在缺少新增真实512chirp采集的情况下重建实验BIT，原整体背景门槛FAIL保留。
- 独立复制radar1_scalar_v7_fullrange_v3源码、BD/IP、显示修复、原始SD支路；未复制旧BIT/ELF/发布通过记录。
- 新增hls/scalar_compact.cpp：40输入Q16网络、20位权重、34位偏置容器、增益大于1及功率饱和、门控child特征、5×5上下文、软弱峰和紧凑弱峰保护。
- 新增16MiB独立DDR工作区规划，复用支持表URAM，原功率仅在全部推理后写回。
- 模型复制自scalar_restore_v3/pc_candidate_compact，原模型保持不变。
- 软件/硬件签名0x70→0x71，日志标记compact-exp-v1；启动操作和四模式保持。
- 本次不连接板卡。最终验证与剩余问题见BUILD_STATUS.json、reports及pkg/BUILD_READY.json。
- 回滚：停止雷达后下载此前已验证目录中完整匹配的一套BIT/ELF，不混用本版软件。

## 最终构建与发布验证

- 3份整帧共1572864像素及零帧C仿真与冻结PC参考一致；464组MLP、464组保护RTL（208组发生保护变化）及帧CDC通过；全部合法特征区间乘加位宽检查通过。
- 整机综合、布局布线和新BIT/XSA通过。已约束WNS+0.192ns、WHS+0.010ns、WPWS+0.046ns，路由错误0、DRC无Error。原摄像头204个无定义时钟寄存器、插值214个旧锁存器及I/O约束缺口保留，full_system_timing_signoff=false。
- 最终LUT53577/87840、FF60039/175680、BRAM36等价119.5/128、URAM43/48、DSP262/728。
- 新XSA生成匹配BSP和4个ELF；BIT/XSA载荷、PS初始化、AQ/AR内嵌表、活动HLS RTL、冻结模型和原发布文件散列核对PASS。
- 运行ZIP的CRC及逐项SHA256读回PASS，证据reports/PACKAGE_RESULT.json、reports/STANDARD_CHECK.json。
- BIT SHA256：f884d829c217130fb930f85f78019975b1f5d4263f4dd38a482f73ef0d3d73cb。运行ZIP SHA256：1f9807b997d9e6842abbe581b9d91a613dad976d63eeddb79085bc500bc92dce。
- 状态EXPERIMENTAL_READY_FOR_BOARD_TEST，尚未上板，原整体背景质量FAIL保留；网络HLS估计约2.958秒/帧，未计实际DDR等待。
