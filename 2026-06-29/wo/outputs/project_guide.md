 # 项目文件清单与部署指南

 **整理日期**: 2026-06-29
 **用途**: 主机维修归来后快速恢复开发环境

 ---

 ## 一、GitHub 仓库总览

 检查结果：共有 **3 个已推送的 GitHub 仓库**，其余代码仅存于本地。

 | # | 仓库名 | URL | 最新提交 | 内容概要 |
 |---|--------|-----|---------|---------|
 | 1 | `hamer` | https://github.com/alexandertianlin/hamer.git | 4 commits | HAMER 实时手部网格重建 + ViTPose 手部检测 |
 | 2 | `vision-imu-gesture-glove` | https://github.com/alexandertianlin/vision-imu-gesture-glove.git | 4 commits | IMU 数据手套 + MediaPipe 视觉纠正 Unity 项目 |
 | 3 | `agiletact` | https://github.com/alexandertianlin/agiletact.git | 4 commits | IMU + 视觉融合管道（周计划和融合脚本）|

 ---

 ## 二、Unity 安装方法与版本号

 ### 2.1 使用的 Unity 版本

 | 项目 | Unity 版本 | 验证文件 |
 |------|-----------|---------|
 | vision-imu-gesture-glove | **2022.3 LTS** | `unity/ProjectSettings/ProjectVersion.txt` |
 | gesture-glove-ui (onlytip) | 同上（派生项目） | 同源 |

 ### 2.2 安装步骤

 1. 安装 Unity Hub（从 https://unity.com/download 下载）
 2. 在 Unity Hub 中安装 Editor 版本 **2022.3 LTS**
    - Unity Hub → Installs → Install Editor → 选择 2022.3 LTS
    - 安装时勾选 Windows Build Support (IL2CPP) 和 Android Build Support（如需打包）
 3. 打开项目: Unity Hub → Open → 选择 `unity/` 文件夹
 4. 必要的 Package 依赖（在 `manifest.json` 中已定义，Unity 会自动下载）:
    - `com.unity.burst` - 高性能代码
    - `com.unity.collections` - 数据集合
    - `com.unity.mathematics` - 数学库
    - `com.unity.render-pipelines.universal` - URP 渲染管线
    - `com.unity.test-framework` - 测试框架

 ### 2.3 注意事项

 - Unity 2022 LTS 是长期支持版，推荐使用
 - 项目使用 URP 渲染管线，不要切换为 Built-in 或 HDRP
 - 本项目中 **未使用** 虚幻引擎（Unreal Engine）

 ---

 ## 三、需要哪些 Unity 文件

 ### 3.1 核心 Unity 文件清单（已推送到 GitHub）

 `alexandertianlin/vision-imu-gesture-glove` 仓库包含：

 ```
 unity/
 ├── Assets/
 │   ├── Scenes/
 │   │   ├── SampleScene.unity                     # 主场景
 │   │   ├── SerialReceiver.cs                     # 串口接收（IMU 硬件数据）
 │   │   ├── HandMotionManager.cs                  # 手部运动管理
 │   │   ├── FingerSolver.cs                       # 手指弯曲/张开求解器
 │   │   ├── VisionFingerCorrectionReceiver.cs     # MediaPipe UDP 视觉纠正
 │   │   ├── VisionOpenPalmRefreshModule.cs        # 手掌张开 IMU 重新校准
 │   │   ├── CameraController.cs                   # 相机控制
 │   │   ├── HandAntiClipping.cs                   # 手部穿透防止
 │   │   ├── source/hand-only-rig.fbx              # 手部骨骼模型
 │   │   └── textures/                             # 全息材质
 │   ├── ForceGrid.prefab                          # 力反馈网格预制体
 │   ├── ForceGridVisualizer.cs                    # 力反馈可视化
 │   └── hand-only-rig.fbx                         # 手部模型
 ├── Packages/manifest.json                        # 包依赖声明
 └── ProjectSettings/
     ├── ProjectVersion.txt                        # 版本号 2022.3.x
     └── ... 其他标准设置文件
 ```

 ### 3.2 仅存于本地的 Unity 文件（未推送到 GitHub）

 | 文件 | 本地路径 | 说明 |
 |------|---------|------|
 | FusionUDPReceiver.cs | `2026-06-26/.../outputs/` | 融合网关 UDP 接收脚本 |
 | fusion_gateway.py | `2026-06-26/.../outputs/` | Python 融合网关 |
 | gesture-glove-vision-ui | `2026-06-26/.../gesture-glove-vision-ui/` | 改进版 Unity UI 项目 |

 ### 3.3 本地文件位置索引

 | 内容 | 本地路径 |
 |------|---------|
 | vision-imu-gesture-glove Unity 项目（已推送） | `2026-06-17/.../vision-imu-gesture-glove/unity/` |
 | gesture-glove-ui Unity 项目（仅本地） | `2026-06-26/.../gesture-glove-vision-ui/` |
 | 融合网关脚本（仅本地） | `2026-06-26/.../outputs/` |

 ---

 ## 四、ViTPose 和 HaMeR 模型部署方法

 ### 4.1 整体架构

 ```
 Camera (640x480)
   → ViTPose+ Huge (133 keypoints)
     → Hand bbox extraction (21 kps per hand)
       → ViTDetDataset (crop + normalize to 256x256)
         → HaMeR (Transformer Decoder + MANO)
           → 21x3D keypoints + MANO params + 778 vertices mesh
             → Finger curl/spread geometry
               → UDP JSON → Unity (port 5055)
 ```

 ### 4.2 环境要求

 | 组件 | 要求 |
 |------|------|
 | GPU | NVIDIA RTX 4080+（12GB+ VRAM） |
 | CUDA | 12.4 / 12.8 |
 | Python | 3.10.20 |
 | PyTorch | 2.6.0+cu124 |
 | 系统 | Windows 11（已验证） |
 | 摄像头 | Intel RealSense D435i 或 普通 USB 摄像头 |

 ### 4.3 Conda 环境搭建

 ```powershell
 conda create -n hamer python=3.10.20 -c conda-forge -y
 conda activate hamer
 pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124
 pip install numpy==1.26.4 opencv-python==4.9.0.80 opencv-contrib-python==4.13.0.92
 pip install mmcv==1.4.8 mmdet==3.3.0
 pip install smplx==0.1.28 timm==1.0.27 pytorch-lightning==2.6.5 yacs==0.1.8
 pip install einops chumpy pyrender trimesh scikit-image
 pip install gdown hydra-core omegaconf pyrealsense2 mediapipe pillow tqdm
 pip install matplotlib pandas scipy setuptools==60.2.0
 ```

 ### 4.4 HaMeR 部署

 克隆源仓库（含 ViTPose 子模块）：
 ```powershell
 git clone --recursive https://github.com/geopavlakos/hamer.git hamer-main
 cd hamer-main
 ```

 目录结构：
 ```
 hamer-main/
 ├── hamer/
 │   ├── configs/                       # YACS 配置文件
 │   ├── configs_hydra/                 # Hydra 训练配置
 │   ├── datasets/
 │   │   ├── vitdet_dataset.py          # [关键] 推理数据集类
 │   │   └── utils.py                   # 图像裁剪工具
 │   ├── models/
 │   │   ├── hamer.py                   # HaMeR 主模型
 │   │   └── mano_wrapper.py            # MANO 模型封装
 │   └── utils/
 │       ├── renderer.py                # 3D 渲染工具
 │       └── download.py                # 模型下载工具
 ├── third-party/ViTPose/              # ViTPose 子模块（mmpose fork）
 ├── vitpose_model.py                   # [关键] ViTPose 模型封装类
 ├── setup.py
 ├── demo.py
 └── _DATA/                             # 模型权重目录
     ├── hamer_ckpts/checkpoints/hamer.ckpt        # 2.69 GB
     ├── vitpose_ckpts/vitpose+_huge/wholebody.pth # 3.81 GB
     └── data/mano/
         ├── MANO_RIGHT.pkl                         # 1.5 MB
         └── mano_mean_params.npz                   # 2 KB
 ```

 ### 4.5 ViTPose 安装（必须源码安装）

 ```powershell
 cd hamer-main\third-party\ViTPose
 pip install -v -e .
 ```
 验证：`python -c "import mmpose; print(mmpose.__version__)"` 应输出 `0.24.0`

 ### 4.6 模型权重下载

 HaMeR 权重（2.69 GB）：
 ```powershell
 python -c "import gdown; gdown.download('https://drive.google.com/uc?id=1mv7CUAnm73oKsEEG1xE3xH2C_oqcFSzT', '_DATA/hamer_demo_data.tar.gz', quiet=False)"
 ```

 ViTPose 权重（3.81 GB）：从 ViTPose 官方仓库下载 `wholebody.pth`

 MANO 模型：从 https://mano.is.tue.mpg.de 注册下载

 ### 4.7 运行脚本

 | 脚本 | 功能 | 摄像头类型 |
 |------|------|-----------|
 | `run_hamer_camera.py` | 完整管道 | USB 摄像头 |
 | `d435i_hamer_vitpose.py` | 完整管道（推荐，可正确标注 L/R）| D435i |
 | `hamer_unity_bridge.py` | 完整管道 + UDP 到 Unity | USB 摄像头 |
 | `d435i_hamer.py --headless` | 批量保存模式 | D435i |

 ### 4.8 延迟数据

 | 阶段 | 时间 | 占总体 |
 |------|------|--------|
 | ViTPose 推理 | ~198 ms | 主要瓶颈 |
 | HaMeR 推理（4 batch）| ~222 ms | 次瓶颈 |
 | 总 FPS | **~4-5** | - |

 ### 4.9 GitHub 已推送的运行脚本

 位于 `alexandertianlin/hamer` 仓库：
 - `run_hamer_camera.py`, `test_hamer.py`, `test_vitpose.py`
 - `test_accuracy.py`, `measure_latency.py`
 - `download_hamer_data.py`

 **未推送但建议推送**：
 - `hamer_unity_bridge.py`（HaMeR → Unity UDP 桥接）
 - `vitpose_base_runtime.py`（ViTPose 精简运行时）
 - `vitpose_cfg.py`（ViTPose 配置）

 ---

 ## 五、GitHub 仓库详细检查结果

 ### 5.1 `alexandertianlin/hamer`

 URL: https://github.com/alexandertianlin/hamer.git
 本地位置: `2026-06-16/files-mentioned-by-the-user-gpu2-3/`
 提交: 4 commits

 已推送：`.gitignore`, `README.md`, `WORK_LOG.md`, `download_hamer_data.py`, `measure_latency.py`, `measure_latency2.py`, `run_hamer_camera.py`, `test_accuracy.py`, `test_hamer.py`, `test_vitpose.py`, `test_cam.jpg`

 未推送（建议推送）：
 - `hamer_unity_bridge.py` - HaMeR → Unity UDP 桥接
 - `vitpose_base_runtime.py` - ViTPose 精简运行环境
 - `vitpose_cfg.py` - ViTPose 配置
 - `add_timing.py` - 时序记录工具
 - `download_direct.py` - 直接下载脚本

 ### 5.2 `alexandertianlin/vision-imu-gesture-glove`

 URL: https://github.com/alexandertianlin/vision-imu-gesture-glove.git
 状态: Unity 项目完整推送（4 commits），含所有 C# 脚本、场景、材质

 ### 5.3 `alexandertianlin/agiletact`

 URL: https://github.com/alexandertianlin/agiletact.git
 状态: 新仓库（4 commits），含 IMU+视觉融合管道脚本和周计划

 ### 5.4 仅存于本地的项目

 | 项目 | 本地路径 | 建议操作 |
 |------|---------|---------|
 | gesture-glove-ui | `2026-06-26/.../gesture-glove-vision-ui/` | 推送到新仓库 |
 | D435i 集成脚本 | `2026-06-18/hamer-d435i-usb/work/` | 合并到 `hamer` 仓库 |
 | D435i + vitpose-deploy | `2026-06-18/hamer-d435i-usb-13-18-17m/` | 合并到 `hamer` 仓库 |
 | detectron2-vitpose | `2026-06-18/detectron2-vitpose/` | 合并到 `hamer` 仓库 |

 ---

 ## 六、模型权重文件对照表

 以下文件过大，不推送到 GitHub（已在 `.gitignore` 排除）：

 | 文件 | 大小 | 位置 | 下载方式 |
 |------|------|------|---------|
 | `hamer.ckpt` | 2.69 GB | `_DATA/hamer_ckpts/checkpoints/` | Google Drive (gdown) |
 | `wholebody.pth` | 3.81 GB | `_DATA/vitpose_ckpts/vitpose+_huge/` | ViTPose 官方仓库 |
 | `MANO_RIGHT.pkl` | ~1.5 MB | `_DATA/data/mano/` | mano.is.tue.mpg.de |
 | `mano_mean_params.npz` | ~2 KB | `_DATA/data/mano/` | HaMeR 官方资源 |

 ---

 ## 七、主机修好后恢复步骤

 ### 步骤 1：安装基础软件

 - [ ] Unity Hub + Unity 2022.3 LTS
 - [ ] Conda（Miniconda / Anaconda）
 - [ ] Git
 - [ ] NVIDIA 驱动 + CUDA 12.4/12.8

 ### 步骤 2：克隆 GitHub 仓库

 ```powershell
 git clone https://github.com/alexandertianlin/hamer.git
 git clone https://github.com/alexandertianlin/vision-imu-gesture-glove.git
 git clone https://github.com/alexandertianlin/agiletact.git
 ```

 ### 步骤 3：创建 Conda 环境

 ```powershell
 conda create -n hamer python=3.10.20 -c conda-forge -y
 conda activate hamer
 pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124
 pip install numpy==1.26.4 opencv-python==4.9.0.80
 pip install mmcv==1.4.8 mmdet==3.3.0 smplx==0.1.28 timm==1.0.27
 pip install pytorch-lightning==2.6.5 yacs==0.1.8 einops chumpy gdown hydra-core omegaconf
 ```

 ### 步骤 4：安装 ViTPose（源码）

 ```powershell
 cd hamer-main/third-party/ViTPose
 pip install -v -e .
 ```

 ### 步骤 5：下载模型权重

 ```powershell
 python download_hamer_data.py
 :: 额外手动下载 wholebody.pth
 ```

 ### 步骤 6：打开 Unity 项目

 Unity Hub → Open → 选择 `vision-imu-gesture-glove/unity/`

 ### 步骤 7：（可选）推送本地文件到 GitHub

 ```powershell
 :: 更新 hamer 仓库
 cd C:\Users\Administrator\Documents\Codex\2026-06-16\files-mentioned-by-the-user-gpu2-3
 git add hamer_unity_bridge.py vitpose_base_runtime.py vitpose_cfg.py
 git commit -m "Add Unity bridge, ViTPose runtime files"
 git push

 :: 创建 gesture-glove-ui 仓库
 cd C:\Users\Administrator\Documents\Codex\2026-06-26\d-alexandertianlin-agiletact-gesture-glove-ui
 git init
 git add gesture-glove-vision-ui/ outputs/
 git commit -m "Initial commit: onlytip 2.2 Unity UI + fusion gateway"
 gh repo create gesture-glove-ui --public --source=.
 git push origin main
 ```

 ---

 ## 八、关键文件速查索引

 | 文件/内容 | 本地路径 |
 |-----------|---------|
 | HaMeR 权重 | `.../gpu2-3/hamer_code/hamer-main/_DATA/hamer_ckpts/checkpoints/hamer.ckpt` |
 | ViTPose 权重 | `.../gpu2-3/_DATA/vitpose_ckpts/vitpose+_huge/wholebody.pth` |
 | ViTPose 封装类 | `.../gpu2-3/hamer_code/hamer-main/vitpose_model.py` |
 | Unity 主场景 | `.../vision-imu-gesture-glove/unity/Assets/Scenes/SampleScene.unity` |
 | Unity UDP 接收 | `.../gesture-glove-ui/outputs/FusionUDPReceiver.cs` |
 | Python UDP 发送 | `.../gpu2-3/hamer_unity_bridge.py` |
 | 融合网关 | `.../gesture-glove-ui/outputs/fusion_gateway.py` |
 | D435i 完整管道 | `2026-06-18/hamer-d435i-usb/work/d435i_hamer_vitpose.py` |
 | 复现指南（详细） | `2026-06-26/cha/outputs/hamer_vitpose_reproduction_guide.md` |
 | IMU 手套项目 | `.../vision-imu-gesture-glove/` |

 ---

 **文档结束**
