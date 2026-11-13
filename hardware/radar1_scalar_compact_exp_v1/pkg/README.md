# radar1 标量恢复网络实验部署 v1

本工程把 `scalar_restore_v3/pc_candidate_compact` 的完整整数算法接入 radar1 成像链路：严格单比特 I/Q ±64 → 原二维 FFT → 标量功率增强及弱峰保护 → 原 AQ/AR 插值 → HDMI。原始 ADC 数据存储支路独立，保存内容不经过网络。

这是用户授权的实验部署。算法弱目标专项检查和数值检查通过，原整体背景质量门槛仍 FAIL；不据此宣称真实目标全部恢复。以本目录新生成的 `pkg/BUILD_READY.json` 判断构建资格，不能使用来源工程的验收记录替代。本模型尚未上板。

- 工程、模型与限制：`工程与网络说明.md`
- 逐步操作：`上板测试步骤.md`
- 构建与验证证据：`BUILD_STATUS.json`、`reports/`
- 用户原 radar1、已发布 V7 工程、PC 冻结模型保持不变。

板卡固定为正点原子 MPSoC ZU4EV；雷达仍使用原 1024 ADC 点、512 有效 chirp、4RX 配置。新外采 128chirp BIN 的配置不用于本次板测。无需 SD 卡描述符或权重文件。
