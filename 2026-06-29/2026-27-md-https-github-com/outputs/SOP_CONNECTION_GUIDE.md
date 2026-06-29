# 标准操作流程 (SOP) — IMU+Visual Fusion Pipeline

## 启动步骤

### Step A: 检查硬件
```powershell
D:\ProgramData\anaconda3\envs\hamer\python.exe work/IMU_Fusion/diagnose.py
```
输出应该全是 `[PASS]`。如果有 `[FAIL]`，修复后再继续。

### Step B: 关闭冲突进程
确保以下程序没有占用 COM122：
- Arduino IDE 串口监视器
- Putty / TeraTerm
- 其他串口调试工具
- 如果之前 fusion_pipeline.py 崩溃，等 10 秒让串口释放

### Step C: 启动融合管道
```powershell
cd C:\Users\Administrator\Documents\Codex\2026-06-29\2026-27-md-https-github-com
D:\ProgramData\anaconda3\envs\hamer\python.exe work/IMU_Fusion/fusion_pipeline.py
```

### Step D: 启动 Unity
1. 打开 Unity 项目
2. 确保场景中有 FusionUDPReceiver.cs（端口 8080）或 VisionBridge.cs（端口 5055）
3. **不要同时挂两个监听同端口的脚本**
4. 绑定好手部骨骼
5. 等待校准完成（手掌平放）后 Hit Play

## Unity 连接故障排查清单

### 问题 A: "Vision anchor UDP receiver failed"
原因：VisionBridge.cs 和 VisionFingerCorrectionReceiver.cs 同时绑定 5055
解决：禁用 VisionFingerCorrectionReceiver（Inspector 取消勾选）

### 问题 B: "The referenced script is missing"
原因：Unity 找不到对应的 .cs 文件
解决：把 FusionUDPReceiver.cs 放到 Assets/Scenes/ 目录

### 问题 C: Unity 收不到数据
原因1：fusion_pipeline.py 没有运行
   → 运行 diagnose.py 确认
原因2：端口不匹配
   → fusion_pipeline.py 发 8080 → Unity 需要 FusionUDPReceiver
   → fusion_pipeline.py 发 5055 → Unity 需要 VisionBridge
原因3：防火墙阻止 UDP
   → 检查 Windows 防火墙是否允许本地 127.0.0.1 UDP

### 问题 D: 按空格没反应
原因：旧模式（SerialReceiver + HandMotionManager）需要 COM122
   → 如果 fusion_pipeline.py 正在运行，它已经占用了 COM122
   → 二选一：要么用 fusion_pipeline.py（新路），要么用 SerialReceiver（旧路）

## CPU 性能模式
| 命令 | CPU | 适用场景 |
|------|-----|---------|
| python fusion_pipeline.py | ~25% | 默认，推荐 |
| python fusion_pipeline.py --cpu=max | ~70% | 追求最低延迟 |
| python fusion_pipeline.py --cpu=balanced | ~15% | 省资源 |
