# ViTPose WholeBody - D435i RealSense 部署

基于 ViTPose+-Huge 的人体全身姿态检测 + Intel RealSense D435i 实时推理。

## 文件结构

```
vitpose-deploy/
├── README.md                    # 本文件
├── requirements.txt             # pip 依赖
├── vitpose_model.py             # ViTPose 封装 (MMPose wrapper)
├── scripts/
│   ├── d435i_vitpose.py         # D435i 实时2D骨架显示
│   └── hand_test.py             # 伸手自动录制10秒 + 延迟测试
├── configs/
│   └── ViTPose_huge_wholebody_256x192.py   # MMPose 模型配置
└── weights/
    └── vitpose+_huge/
        └── wholebody.pth        # [Google Drive 下载] 预训练权重 (3.8GB)
```

## 硬件要求

- **GPU**: NVIDIA RTX 3080 / 4080 或更高 (推荐 VRAM ≥ 8GB)
- **摄像头**: Intel RealSense D435i (USB 连接)
- **系统**: Windows 10/11

## 安装步骤

### 1. 创建 Conda 环境

```bash
conda create -n vitpose python=3.10 -y
conda activate vitpose
```

### 2. 安装 PyTorch (CUDA 12.1)

```bash
pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124
```

### 3. 安装基础依赖

```bash
pip install -r requirements.txt
```

### 4. 安装 MMDetection 和 MMPose (源码编译)

MMPose 需要从源码安装，因为它依赖 mmcv 和 mmdet 的特定接口：

```bash
# mmcv 1.4.8 (预编译 wheel)
pip install mmcv==1.4.8 -f https://download.openmmlab.com/mmcv/dist/cu124/torch2.6/index.html

# 如果上面失败, 尝试:
pip install openmim
mim install mmcv-full==1.7.0
# 注意: 如果实际安装了 mmcv-full 1.7+，需修改 vitpose_model.py
# 把 inference_top_down_pose_model 的调用改为新接口

# mmdetection 3.3.0
pip install mmdet==3.3.0

# mmpose 0.24.0 (需从源码安装)
git clone --branch v0.24.0 https://github.com/open-mmlab/mmpose.git
cd mmpose
pip install -r requirements.txt
pip install -v -e .
cd ..

# 或者直接 pip 安装 (可能依赖版本不匹配)
# pip install mmpose==0.24.0
```

### 5. 安装 pyrealsense2 (D435i 驱动)

```bash
pip install pyrealsense2
```

### 6. 下载预训练权重

1. 从 Google Drive 下载: [wholebody.pth (3.8GB)](https://drive.google.com/drive/folders/1B4L5mdKpKWyb84f8Jsem_8AbYIRHSlcn?usp=sharing)
2. 将文件放到 `weights/vitpose+_huge/wholebody.pth`

```
vitpose-deploy/weights/
└── vitpose+_huge/
    └── wholebody.pth    # 3.8GB
```

## 使用方法

### 实时 2D 骨架显示 (D435i)

摄像头实时显示人体 + 手部骨架:

```bash
python scripts/d435i_vitpose.py
```

参数:
- `--max_frames 300`: 采集 300 帧后自动退出
- `--headless`: 无窗口模式 (仅处理+保存)

### 伸手自动录制 + 延迟测试

等待手部出现后自动录制10秒, 输出延迟报告:

```bash
python scripts/hand_test.py
```

- 窗口显示 "等待手部..." 时伸手到摄像头前
- 检测到手后自动开始 10 秒录制 (显示 REC 倒计时)
- 10 秒到自动关窗, 打印延迟报告

## 延迟参考 (RTX 4080, 640×480)

| 阶段 | 延迟 |
|:---|---:|
| D435i 采集 | ~13ms |
| ViTPose 推理 (640×480, 每5帧) | ~110ms |
| 单帧合计 (有手时) | ~140ms |
| 有效 FPS | ~4-9 |

## 技术说明

- ViTPose 模型: ViTPose+-Huge (ViT-H, 32层, 1280维)
- 输入尺寸: 256×192 (heatmap 64×48)
- 输出: 133 个关键点 (17 身体 + 68 面部 + 42 手部)
- 每 5 帧运行一次 ViTPose (显存约 5.5GB)
- 使用 MMPose 0.24.0 的 `inference_top_down_pose_model` API
