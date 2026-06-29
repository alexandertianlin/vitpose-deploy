| BUG-001 | 视觉置信度变量作用域问题：p['keypoints'] 在 skip frame 时可能引用上一帧的 ViTPose 结果 | 已修复 | 中 | 2026-06-29 | 引入 saved_kps 变量，在每帧 ViTPose 后独立存储置信度，解决变量跨帧引用问题 |
| BUG-002 | HAMER 需要 os.chdir(HAMER_DIR) 才能找到 MANO 均值参数 | 已验证 | 高 | 2026-06-29 | usion_pipeline.py 在加载 HAMER 前执行 os.chdir(HAMER_DIR)，与 un_vitpose_v3.py 保持一致 |
| BUG-003 | fusion_pipeline.py 端口错位：只发 UDP 8080（FusionUDPReceiver），不发 5055（VisionBridge） | 已修复 | 高 | 2026-06-29 | 添加 `send_udp_vision()` 函数，发送 curl/spread 格式到 5055 端口。同时发 8080（融合数据）和 5055（视觉数据） |
| BUG-004 | fusion_pipeline.py 文件被多次替换操作严重损坏（行号错位、重复函数、混入 PowerShell 代码） | 已修复 | 严重 | 2026-06-29 | 完全重写 fusion_pipeline.py（520行，语法验证通过）。关键要素：send_udp_vision、send_udp_fusion、FC/curl/spread、show_debug |
| BUG-005 | IMU 串口打不开线程直接退出，CPU 空转 | 已修复 | 高 | 2026-06-29 | 添加 while 循环 + 指数退避重连（1s-10s），线程存活后待机等待 |
| BUG-006 | ViTPose vit=0ms 分辨不清是跳帧还是卡死 | 已修复 | 中 | 2026-06-29 | PERF 输出改为 vit=skip / hamer=idle，明确标注状态 |
| BUG-007 | ViTPose 加载失败无提示 | 已修复 | 中 | 2026-06-29 | 添加 try/except 包裹，失败打印 [ViTPose] LOAD FAILED + 降级处理 |
