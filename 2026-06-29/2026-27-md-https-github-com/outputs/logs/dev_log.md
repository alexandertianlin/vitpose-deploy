# 研发日志 (Development Log)

## 项目：IMU + Visual Fusion — 融合器开发

---

### 2026-06-29

#### 上午：环境勘查与计划复盘

**任务目标**：勘查本地已有代码库，梳理架构，确认 STM32 IMU 四元数处理方式。

**完成情况**：
- [x] 读取了现有 `SerialReceiver.cs`（Unity 端串口接收），确认 STM32 手套在片上运行 Mahony 滤波器
- [x] 确认四元数在 STM32 固件中计算完成（int16/10000 缩放），Unity 端不需要重新实现陀螺仪积分
- [x] 读取了 HAMER 融合架构文档（`fusion_architecture.md`）
- [x] 修正 P0 计划：去除重复的 IMU 积分实现，聚焦视觉 + IMU 互补滤波融合
- [x] 同步计划到 GitHub（含技术原理和公式）

**关键发现**：
- STM32 LSM6DSOW → Mahony 滤波 → 已归一化四元数 → 35字节帧
- HAMER 输出 `pred_mano_params['global_orient']`（3×3 旋转矩阵）可作为视觉位姿观测
- 现有 `run_vitpose_v3.py` 计算手腕旋转用的是 `orient_q_from_landmarks()`（从关键点近似），不是 HAMER 的 `global_orient`

**阻塞项**：
- D435i 未连接（此时）

#### 下午：硬件就绪，开始实施

**任务目标**：D435i + IMU 手套均已连接，进入实质开发阶段

**硬件状态**：
- D435I: S/N 261222075307, FW 5.17.0.10
- IMU 手套: COM122

**完成情况**：
- [ ] 测试 D435i 摄像头帧
- [ ] 测试 IMU 手套串口
- [ ] 编写融合管道脚本（`fusion_pipeline.py`）
- [ ] 实现 HAMER `global_orient` 提取
- [ ] 实现互补滤波
- [ ] 调整 Unity 端接收

---

### 2026-06-29 下午 — 实施阶段

**任务目标**：D435i + IMU 手套都已连接，实施完整融合管道

**完成情况**：
- [x] 确认 D435i 连接正常（S/N 261222075307, FW 5.17.0.10）
- [x] 确认 IMU 手套在 COM122
- [x] HAMER 环境验证通过（672M 参数，~2.76 GB VRAM）
- [x] 确认 HAMER orward_step() 输出结构：
  - output['pred_mano_params']['global_orient'] — 手腕旋转矩阵 (batch, 1, 3, 3)
  - output['pred_mano_params']['hand_pose'] — 手指关节旋转矩阵 (batch, 15, 3, 3)
  - output['pred_keypoints_3d'] — 21个3D关键点
- [x] 编写 usion_pipeline.py（~30KB，约550行）
  - D435i 视频流捕获（复用 run_vitpose_v3.py 模式）
  - ViTPose 手部检测（每3帧）
  - HAMER 推理（含 global_orient 提取）
  - IMU 串口读取后台线程（COM122, 460800, Stm32Parser）
  - 互补滤波融合引擎（FusionEngine）
  - UDP 发送（FusionUDPReceiver.cs 兼容格式，端口 8080）
  - 调试可视化（cv2 overlay）
- [x] 修复了 ViTPose 置信度作用域问题（saved_kps 变量）

**待验证**：
- [ ] 端到端运行测试（需要显卡 + Display 环境）
- [ ] Unity 端接收验证
## 2026-06-29 傍晚 — CPU 优化 + Bug 修复

### [PERF] 性能诊断输出
改前：vit=0ms hamer=0ms → 不知道是跳帧还是卡死
改后：vit=28ms / vit=skip / hamer=35ms / hamer=idle → 一目了然

### 修复清单

#### 1. IMU 串口断线重连
- 改前：COM122 打不开线程直接退出，CPU 空转等待
- 改后：指数退避重连（1s→2s→4s→8s→10s max），不烧 CPU
- 关键代码：imu_reader_thread() 中增加 while not stop_event.is_set() 外层循环

#### 2. ViTPose 加载诊断
- 改前：加载失败无提示，vit=0ms 让人困惑
- 改后：try/except 包裹，失败时打印 [ViTPose] LOAD FAILED + 错误信息
- 降级：vitpose=None 时跳过 predict_pose，只用 HAMER

#### 3. PERF 输出清晰化
- vit=skip：表示 ViTPose 跳帧（每3帧运行一次），正常行为
- hamer=idle：表示无手部检测时 HAMER 未运行
- hamer=68ms：模型推理实际耗时

#### 4. CPU 三档模式
- balanced: OMP=8 MKL=4 Torch=4 (~15% CPU)
- performance: OMP=16 MKL=8 Torch=8 (~25% CPU, 默认)
- max: 无限制 (~70%+ CPU)

### 已知问题
- ViTPose wholebody.pth (3.81GB) 存在但可能有版本兼容问题
- 双路 Xeon E5-2695 v4 (72线程) 的 OpenMP 线程池必须限制，否则 CPU 打满
