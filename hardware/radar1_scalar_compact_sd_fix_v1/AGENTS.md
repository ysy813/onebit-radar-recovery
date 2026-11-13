本目录是 radar1_scalar_compact_exp_v1 的独立 PS 存储启动修正版，仅修改软件，不重建 PL。
原工程、旧发布包、SD 卡上的已有文件保持不变。不得自动访问 JTAG 或串口。
BIT 必须与原实验版 SHA256 f884d829c217130fb930f85f78019975b1f5d4263f4dd38a482f73ef0d3d73cb 一致，硬件签名 0x71。
本版仅发布 onebit_network_storage 模式；下载资格以 pkg/BUILD_READY.json 为准。
software/sd_space.c 依赖本目录固定的 FatFs R0.13b，启动时清除 RAM 中的空闲计数缓存，再调用 f_getfree 扫描真实 FAT。
tests/vendor/ff.c 是原 BSP 的原样副本，仅供内存磁盘回归；板端仍链接复制的原 libxilffs.a。
原质量 FAIL、实验性质、full_system_timing_signoff=false 继续保留。软件离线测试不代表 SD 板测通过。
