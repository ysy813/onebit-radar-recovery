# 当前交付入口

本目录最终候选为 `pc_candidate_compact/`，同帧对照为 `results_compact/index.html`。先读 `弱目标修正结果.md` 和 `操作说明.md`。

弱目标修正 PASS，PC数值及独立运行 PASS；原整体背景门槛仍 FAIL。最终方案保留 v2 神经权重，只修改512有效chirp模式的紧凑弱峰保护，128有效chirp输出保持原样。没有新IP、BIT、ELF或板卡访问。

运行包：`release/scalar_restore_v3_compact_weakfix.zip`，完整性记录：`RUNTIME_PACKAGE_COMPACT.json`。仅为PC运行/代码/报告/图像/两份FFT功率示例，不是完整原始数据或训练缓存备份。

`runs/`、`development_final/`、`development_profiled/`、`fresh_test/` 和旧的export/finalize脚本均为保留的尝试；不要混作当前候选。最终复现代码为 `compact_guard.py`、`compact_experiment.py`、`compact_release.py`，配置为 `COMPACT_POLICY.json`，最终留出为 `compact_fresh_test/report.json`。
