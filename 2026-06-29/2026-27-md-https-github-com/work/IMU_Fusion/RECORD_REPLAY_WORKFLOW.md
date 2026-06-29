# Record-Replay Workflow: Principles, Formulas, and Architecture

## 1. Why Record → Process Once → Replay?

**Problem**: Loading HAMER ViTPose takes ~30s and 2.76GB VRAM. Every run has
this overhead.

**Solution**: Record D435i video + IMU data once. Run HAMER once to extract
visual pose and fuse with IMU. Then replay fused data to Unity any number of
times without reloading the model.

```
  ┌─────────────────┐       ┌────────────────────────┐       ┌─────────────────────────┐
  │   recorder.py   │ ────→ │ offline_fusion_        │ ────→ │ replay_to_unity.py      │
  │                 │       │ processor.py            │       │                         │
  │  D435i (RGB)    │       │                         │       │  Read fused.json        │
  │  IMU (COM122)   │       │  Load HAMER *once*      │       │  UDP → Unity :8080      │
  │                 │       │  ViTPose + HAMER infer   │       │  Play video side-by-side│
  │  rec_.mp4       │       │  IMU interpolation       │       │                         │
  │  rec__imu.csv   │       │  Complementary filter    │       │  Keyboard control:      │
  └─────────────────┘       │                         │       │  SPACE=pause  r=restart  │
                             │  rec__fused.json        │       │  s=0.25x  n=1x  f=2x    │
                             │  rec__processed.mp4     │       └─────────────────────────┘
                             └────────────────────────┘
```

## 2. Pipeline Components

### recorder.py
- Opens D435i at 640x480 30fps RGB
- Opens IMU serial on COM122 460800baud
- Press `r` to toggle recording
- Saves synchronized .mp4 and .csv with monotonic timestamps
- First IMU frame timestamp ≈ first video frame timestamp

### offline_fusion_processor.py
- Loads HAMER model once (slow)
- Reads recorded .mp4 frame by frame
- For every Nth frame: ViTPose → HAMER → wrist rotation matrix
- Interpolates IMU quaternion to each video frame timestamp
- Fuses visual + IMU with complementary filter
- Outputs `_fused.json` (frame-by-frame) and `_processed.mp4` (annotated)

### replay_to_unity.py
- Reads `_fused.json`
- Sends each frame's fused wrist quaternion + finger data to Unity via UDP :8080
- Shows video side-by-side with real-time telemetry
- Playback controls: pause/resume, speed, restart

## 3. Core Algorithms and Formulas

### Quaternion Multiplication
Used to apply calibrated offset to IMU quaternion:
```
Q_imu_calibrated = Q_offset ⊗ Q_imu_raw

where:
  Q_offset = inverse(Q_static_avg)
  Q_static_avg = mean of first N IMU quaternions at rest
```

Implementation:
```
q × p = [ qw*pw - qx*px - qy*py - qz*pz,
          qw*px + qx*pw + qy*pz - qz*py,
          qw*py - qx*pz + qy*pw + qz*px,
          qw*pz + qx*py - qy*px + qz*pw ]
```

### Quaternion Slerp (Spherical Linear Interpolation)
Used for smooth interpolation between IMU and visual poses, and for
IMU temporal interpolation:
```
Slerp(Q_a, Q_b, t) = (sin((1-t)θ) / sinθ) * Q_a + (sin(tθ) / sinθ) * Q_b

where cosθ = Q_a · Q_b (dot product)
      t ∈ [0, 1]
```

Special case (fast path when θ ≈ 0):
```
Slerp(Q_a, Q_b, t) ≈ normalize(Q_a + t * (Q_b - Q_a))
```

### Complementary Filter
Fuses high-frequency IMU (good short-term) with low-frequency visual
(good long-term, no drift):
```
Q_fused = Slerp(Q_visual, Q_imu_calibrated, α)

where α ∈ [0.85, 1.0]:
  α = 0.85 when visual confidence ≥ 0.7 (trust IMU more, high rate)
  α = 1.0 when visual confidence < 0.5 (pure IMU, visual lost)
  α interpolates in between
```

**Why complementary filter over Kalman?**
- Simple, fast, no matrix operations
- Good enough when IMU drift is slow (gyro bias from STM32 Mahony is small)
- α can be dynamically adjusted per frame
- Can be upgraded to ESKF later if needed

### Rotation Matrix → Quaternion
Convert HAMER's MANO `global_orient` (3x3 rotation matrix) to quaternion:
```
R = [[r00, r01, r02],
     [r10, r11, r12],
     [r20, r21, r22]]

trace = r00 + r11 + r22

if trace > 0:
  s = 0.5 / sqrt(trace + 1)
  q = [0.25/s, (r21-r12)*s, (r02-r20)*s, (r10-r01)*s]
elif r00 > r11 and r00 > r22:
  s = 2 * sqrt(1 + r00 - r11 - r22)
  q = [(r21-r12)/s, 0.25*s, (r01+r10)/s, (r02+r20)/s]
elif r11 > r22:
  s = 2 * sqrt(1 + r11 - r00 - r22)
  q = [(r02-r20)/s, (r01+r10)/s, 0.25*s, (r12+r21)/s]
else:
  s = 2 * sqrt(1 + r22 - r00 - r11)
  q = [(r10-r01)/s, (r02+r20)/s, (r12+r21)/s, 0.25*s]
```

### STM32 Mahony Filter (IMU glove firmware)
The IMU glove runs an on-chip Mahony filter:
- Input: raw gyroscope (LSM6DSOW) + accelerometer
- Output: normalized quaternion, transmitted as int16 (×10000 scale)
- 35-byte frame: 0xB5 0xA5 0x55 | ... | qw qx qy qz (int16 ×4) | CRC
- This means Unity receives *already-fused* quaternions, not raw data
- The fusion in Python/Unity corrects *long-term drift* that Mahony alone
  cannot eliminate (no visual reference)

## 4. Delta from Previous Architecture

| Aspect | Before (fusion_pipeline_v2.py) | After (Record-Replay) |
|--------|-------------------------------|----------------------|
| Model loading | Every run (~30s + 2.76GB VRAM) | Once per recording |
| Data source | Live D435i + live IMU | Recorded .mp4 + .csv |
| Iteration speed | Slow (reload model each time) | Fast (instant replay) |
| Debug capability | Real-time only | Frame-by-frame analysis |
| Side-by-side verification | No | Yes, video + Unity |

## 5. Quick Start

```bash
# Step 1: Record data
cd work/IMU_Fusion
D:\ProgramData\anaconda3\envs\hamer\python.exe recorder.py

# Step 2: Process once
D:\ProgramData\anaconda3\envs\hamer\python.exe offline_fusion_processor.py ^
    --video recordings/rec_YYYYMMDD_HHMMSS.mp4 ^
    --imu recordings/rec_YYYYMMDD_HHMMSS_imu.csv

# Step 3: Open Unity project with FusionUDPReceiver on port 8080, then replay
python replay_to_unity.py
```

## 6. File Structure

```
recordings/
  rec_20260629_150000.mp4            -- Raw D435i video
  rec_20260629_150000_imu.csv        -- Raw IMU data
  rec_20260629_150000_fused.json     -- Offline fusion output
  rec_20260629_150000_processed.mp4  -- Annotated output video
```
