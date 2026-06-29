# IMU + Visual Fusion Pipeline

## 文件结构

`
work/IMU_Fusion/
├── fusion_pipeline.py     ← 主融合管道（Step 1-3 核心实现）
├── check_hamer.py         ← HAMER 环境检查（废弃）
├── check_hamer_forward.py ← HAMER forward_step 源码检查（废弃）
├── check_forward_step.py  ← forward_step 输出结构检查（废弃）
└── test_hamer_load.py     ← HAMER 模型加载测试（废弃）
`

## 启动方式

`ash
# 激活 conda 环境
conda activate hamer

# 1. 插好 D435i（USB）
# 2. 插好 IMU 手套（COM122）
# 3. 运行融合管道
python work/IMU_Fusion/fusion_pipeline.py

# 4. 在 Unity 中打开场景，Hit Play
# Unity 通过 FusionUDPReceiver.cs 接收 UDP 8080 的融合数据
`

## 数据流

`
D435i ──[USB]──→ ViTPose → HAMER → global_orient(3×3→4元数)
                                          ↓
IMU 手套 ──[COM122]──→ Stm32Parser → 4元数
                                          ↓
                                   FusionEngine
                                   Complementary Filter
                                   Slerp(Q_imu, Q_visual, α)
                                          ↓
                                   UDP JSON (127.0.0.1:8080)
                                          ↓
                                   Unity FusionUDPReceiver.cs
`

## 关键技术参数

| 参数 | 值 |
|------|------|
| 视觉观测来源 | HAMER pred_mano_params['global_orient'] |
| 融合方式 | Slerp 互补滤波 |
| α 动态范围 | 0.85（视觉可靠）~ 1.0（纯 IMU） |
| 置信度阈值 | 高 0.7 / 低 0.5 |
| UDP 端口 | 8080（融合数据）|
| IMU 采样率 | 100Hz（COM122, 460800） |
| 视觉采样率 | ~20-30 fps（ViTPose 每3帧，HAMER 每帧） |
| 校准样本 | 15 帧（手掌静止平放） |

## 坐标系对齐

- HAMER（相机空间）：Z 向前，Y 向下，X 向右（右手系）
- IMU（传感器空间）：通过校准偏置 Q_offset 对齐
- Unity（目标）：Z 向前，Y 向上，X 向右（左手系）

校准流程：手掌平放朝向相机 → 采集 15 帧 IMU + HAMER → 计算偏置
