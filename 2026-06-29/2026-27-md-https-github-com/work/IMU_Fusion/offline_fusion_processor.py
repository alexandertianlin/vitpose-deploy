#!/usr/bin/env python3
"""
offline_fusion_processor.py — 加载 HAMER 一次, 处理录制的视频 + IMU CSV,
                              输出融合后的 fused.json 和带标注的处理后视频。

用法:
  Python3 (hamer env) offline_fusion_processor.py ^
      --video recordings/rec_20260629_150000.mp4 ^
      --imu recordings/rec_20260629_150000_imu.csv

输出:
  recordings/rec_20260629_150000_fused.json     — 逐帧融合数据
  recordings/rec_20260629_150000_processed.mp4   — 带标注的视频
"""

import os, sys, json, struct, time, argparse, math
import numpy as np
import cv2

# ====== HAMER 环境配置 (从 fusion_pipeline_v2.py 复用) ======
HAMER_DIR = r"C:\Users\Administrator\Documents\Codex\2026-06-16\files-mentioned-by-the-user-gpu2-3\hamer_code\hamer-main"
CKPT = os.path.join(HAMER_DIR, "_DATA", "hamer_ckpts", "checkpoints", "hamer.ckpt")
os.chdir(HAMER_DIR)
sys.path.insert(0, HAMER_DIR)
sys.path.insert(0, os.path.join(HAMER_DIR, "third-party", "ViTPose"))

os.environ["PYOPENGL_PLATFORM"] = "wgl"
os.environ["PYTORCH_JIT"] = "0"
os.environ["OMP_NUM_THREADS"] = "8"
os.environ["MKL_NUM_THREADS"] = "4"
import torch; torch.set_num_threads(4); torch.set_grad_enabled(False)

# ====== 数学工具 (从 fusion_pipeline_v2.py 复用) ======
def quat_mul(a, b):
    aw,ax,ay,az=a; bw,bx,by,bz=b
    return (aw*bw-ax*bx-ay*by-az*bz, aw*bx+ax*bw+ay*bz-az*by, aw*by-ax*bz+ay*bw+az*bx, aw*bz+ax*by-ay*bx+az*bw)
def quat_norm(q):
    w,x,y,z=q; n=np.sqrt(w*w+x*x+y*y+z*z)
    return (1.0,0.0,0.0,0.0) if n<1e-10 else (w/n,x/n,y/n,z/n)
def quat_inv(q): w,x,y,z=q; return quat_norm((w,-x,-y,-z))
def quat_slerp(a,b,t):
    a=quat_norm(a); b=quat_norm(b); d=a[0]*b[0]+a[1]*b[1]+a[2]*b[2]+a[3]*b[3]
    if d<0: b=(-b[0],-b[1],-b[2],-b[3]); d=-d; d=np.clip(d,-1.0,1.0)
    if d>0.9995: return quat_norm((a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1]),a[2]+t*(b[2]-a[2]),a[3]+t*(b[3]-a[3])))
    th0=np.arccos(d); th=th0*t; s0=np.cos(th)-d*np.sin(th)/np.sin(th0); s1=np.sin(th)/np.sin(th0)
    return quat_norm((s0*a[0]+s1*b[0],s0*a[1]+s1*b[1],s0*a[2]+s1*b[2],s0*a[3]+s1*b[3]))
def rotmat_to_quat(R):
    tr=R[0,0]+R[1,1]+R[2,2]
    if tr>0: s=0.5/np.sqrt(tr+1.0); return (0.25/s,(R[2,1]-R[1,2])*s,(R[0,2]-R[2,0])*s,(R[1,0]-R[0,1])*s)
    elif R[0,0]>R[1,1] and R[0,0]>R[2,2]: s=2.0*np.sqrt(1.0+R[0,0]-R[1,1]-R[2,2]); return ((R[2,1]-R[1,2])/s,0.25*s,(R[0,1]+R[1,0])/s,(R[0,2]+R[2,0])/s)
    elif R[1,1]>R[2,2]: s=2.0*np.sqrt(1.0+R[1,1]-R[0,0]-R[2,2]); return ((R[0,2]-R[2,0])/s,(R[0,1]+R[1,0])/s,0.25*s,(R[1,2]+R[2,1])/s)
    else: s=2.0*np.sqrt(1.0+R[2,2]-R[0,0]-R[1,1]); return ((R[1,0]-R[0,1])/s,(R[0,2]+R[2,0])/s,(R[1,2]+R[2,1])/s,0.25*s)
def quat_to_list(q): return [round(float(q[0]),6),round(float(q[1]),6),round(float(q[2]),6),round(float(q[3]),6)]

FINGER_NAMES = ["thumb","index","middle","ring","little"]
MANO_TO_FINGER = {"thumb":[14,12,13],"index":[0,1,2],"middle":[3,4,5],"ring":[6,7,8],"little":[9,10,11]}


def load_imu_csv(csv_path):
    """加载 IMU CSV, 返回 (ts_list, quat_list), 时间戳是单调递增的浮点秒"""
    ts_list = []
    quat_list = []
    with open(csv_path, 'r') as f:
        lines = f.readlines()
    # 跳过 header
    for line in lines[1:]:
        parts = line.strip().split(',')
        if len(parts) < 6:
            continue
        ts = float(parts[0])  # ts_monotonic
        qw, qx, qy, qz = float(parts[2]), float(parts[3]), float(parts[4]), float(parts[5])
        ts_list.append(ts)
        quat_list.append((qw, qx, qy, qz))
    print(f"[IMU] 加载 {len(ts_list)} 个 IMU 数据点")
    return np.array(ts_list), quat_list


def interpolate_imu_to_timestamp(ts_imu, quat_imu, target_ts):
    """在目标时间戳线性插值 IMU 四元数 (用 slerp)"""
    if target_ts <= ts_imu[0]:
        return quat_imu[0]
    if target_ts >= ts_imu[-1]:
        return quat_imu[-1]
    idx = np.searchsorted(ts_imu, target_ts) - 1
    idx = max(0, min(idx, len(ts_imu)-2))
    t0, t1 = ts_imu[idx], ts_imu[idx+1]
    if t1 - t0 < 1e-8:
        return quat_imu[idx]
    alpha = (target_ts - t0) / (t1 - t0)
    return quat_slerp(quat_imu[idx], quat_imu[idx+1], alpha)


def main():
    parser = argparse.ArgumentParser(description="离线融合处理器")
    parser.add_argument("--video", required=True, help="录制的 .mp4 视频路径")
    parser.add_argument("--imu", required=True, help="录制的 IMU .csv 路径")
    parser.add_argument("--vit-skip", type=int, default=3, help="ViTPose 跳帧 (默认 3)")
    args = parser.parse_args()

    # ====== 解析路径 ======
    base = os.path.splitext(args.video)[0].replace("_imu", "")
    fused_json_path = base + "_fused.json"
    processed_video_path = base + "_processed.mp4"

    # ====== 加载 IMU ======
    ts_imu, quat_imu = load_imu_csv(args.imu)
    ts_imu_ref = ts_imu[0]  # 第一个 IMU 时间戳作为参考零点
    ts_imu_zeroed = ts_imu - ts_imu_ref

    # ====== 加载 HAMER (一次, 慢但只做一次) ======
    print("[HAMER] 加载模型中...")
    t0 = time.time()
    from hamer.configs import CACHE_DIR_TOP
    from hamer.utils import recursive_to
    from hamer.models import HAMER
    from hamer.datasets.vitdet_dataset import ViTDetDataset
    from detectron2.data.transforms import ResizeShortestEdge
    import detectron2.data.transforms as T

    cfg_h = {
        "MODEL":{"BACKBONE":{"TYPE":"vit"}, "HAND_SCORE_THRESHOLD":0.5},
        "DATA":{"MEAN":[0.485,0.456,0.406], "STD":[0.229,0.224,0.225]},
        "IMAGE_SIZE":{"HEIGHT":256,"WIDTH":256},
        "MANO":{"MODEL_PATH": os.path.join(HAMER_DIR, "_DATA", "mano"),
                 "MEAN_PARAMS": os.path.join(HAMER_DIR, "_DATA", "mano_mean_params.npy")},
    }
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    m_hamer = HAMER(cfg_h).to(dev).eval()
    ckpt = torch.load(CKPT, map_location=dev)
    m_hamer.load_state_dict(ckpt["model"], strict=False)
    print(f"[HAMER] 加载完成: {time.time()-t0:.1f}s, device={dev}")

    # ====== 初始化 ViTPose ======
    t0 = time.time()
    from vitpose_model import ViTPoseModel
    vitpose = ViTPoseModel(dev)
    print(f"[ViTPose] 加载完成: {time.time()-t0:.1f}s")

    # ====== 读取视频 ======
    cap = cv2.VideoCapture(args.video)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[VIDEO] {total_frames} 帧, {fps:.1f} fps, {w}x{h}")

    # ====== 准备输出视频 ======
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out_video = cv2.VideoWriter(processed_video_path, fourcc, fps, (w, h))

    # ====== 遍历视频帧, 运行 HAMER + 融合 ======
    fused_frames = []
    last_boxes = None
    last_vit_kp = None
    vit_skip = 0
    frame_idx = 0
    calib_quats = []       # 校准用 IMU 四元数缓存
    q_off = (1.0, 0.0, 0.0, 0.0)
    calibrated = False
    alpha_high = 0.85
    current_alpha = alpha_high
    CALIB_SAMPLES = 15
    CONF_THRESH_HIGH = 0.7
    CONF_THRESH_LOW = 0.5

    print(f"\n[PROCESS] 开始处理 {total_frames} 帧...")
    process_t0 = time.time()

    while True:
        ret, img = cap.read()
        if not ret:
            break
        frame_ts = frame_idx / fps  # 相对时间 (秒)
        # 映射到 IMU 时间轴
        imu_target_ts = ts_imu_ref + frame_ts
        q_imu_interp = interpolate_imu_to_timestamp(ts_imu, quat_imu, imu_target_ts)

        # ====== ViTPose 检测(每隔 N 帧) ======
        ran_vit = False
        vit_skip -= 1
        if vit_skip <= 0:
            ran_vit = True
            det = [np.array([[0, 0, w, h, 0.9]])]
            vitposes = vitpose.predict_pose(img, det)
            vit_skip = args.vit_skip
            # 提取手部候选框
            boxes_list, rights_list = [], []
            for vp in vitposes:
                kps = vp["keypoints"]
                for hk, ir in [(kps[-42:-21], False), (kps[-21:], True)]:
                    v = hk[:, 2] > 0.5
                    if sum(v) < 8:
                        continue
                    boxes_list.append([
                        int(hk[v, 0].min()) - 20, int(hk[v, 1].min()) - 20,
                        int(hk[v, 0].max()) + 20, int(hk[v, 1].max()) + 20
                    ])
                    rights_list.append(1.0 if ir else 0.0)
            if boxes_list:
                last_boxes = np.stack(boxes_list).astype(np.float32)

        # ====== HAMER 推理 ======
        visual_valid = False
        wrist_rotmat = None
        wrist_quat = (1.0, 0.0, 0.0, 0.0)
        hand_pose_rotmats = []
        keypoints_3d = None
        confidence = 0.0

        if last_boxes is not None and ran_vit:
            ds = ViTDetDataset(cfg_h, img, last_boxes,
                               np.stack(rights_list).astype(np.float32) if len(rights_list) > 0 else last_boxes[:, 0]*0,
                               rescale_factor=2.0)
            loader = torch.utils.data.DataLoader(ds, batch_size=4, shuffle=False, num_workers=0)
            for batch in loader:
                batch = recursive_to(batch, dev)
                with torch.no_grad():
                    out = m_hamer(batch)
                for n in range(batch["img"].shape[0]):
                    go = out["pred_mano_params"]["global_orient"][n].cpu().numpy().squeeze().reshape(3, 3)
                    wrist_rotmat = go
                    wrist_quat = rotmat_to_quat(go)
                    hp = out["pred_mano_params"]["hand_pose"][n].cpu().numpy()
                    hand_pose_rotmats = [hp[j] for j in range(15)]
                    keypoints_3d = out["pred_keypoints_3d"][n].cpu().numpy()
                    kp2d = out["pred_keypoints_2d"][n].cpu().numpy() + 0.5
                    ir_val = batch["right"][n].item()
                    if ir_val < 0.5:
                        kp2d[:, 0] = 1.0 - kp2d[:, 0]
                    cx, cy, bs = batch["box_center"][n, 0].item(), batch["box_center"][n, 1].item(), batch["box_size"][n].item()
                    kp2d_img = np.zeros((21, 2), dtype=int)
                    kp2d_img[:, 0] = (cx - bs/2 + kp2d[:, 0]*bs).astype(int)
                    kp2d_img[:, 1] = (cy - bs/2 + kp2d[:, 1]*bs).astype(int)
                    confidence = 0.5
                    visual_valid = True
                    # 画骨架
                    for e in [(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),(0,9),(9,10),(10,11),(11,12),
                              (0,13),(13,14),(14,15),(15,16),(0,17),(17,18),(18,19),(19,20)]:
                        cv2.line(img, tuple(kp2d_img[e[0]]), tuple(kp2d_img[e[1]]), (0, 255, 255), 2)
                    for p in kp2d_img:
                        cv2.circle(img, tuple(p), 4, (0, 255, 0), -1)

        # ====== 校准 ======
        if not calibrated and visual_valid:
            calib_quats.append(q_imu_interp)
            if len(calib_quats) >= CALIB_SAMPLES:
                avg = tuple(np.mean([list(q) for q in calib_quats], axis=0))
                q_off = quat_inv(quat_norm(avg))
                calibrated = True
                print(f"[CALIB] 校准完成: {len(calib_quats)} 样本")

        # ====== 融合 ======
        fused_wrist_quat = (1.0, 0.0, 0.0, 0.0)
        if calibrated:
            if visual_valid and confidence >= CONF_THRESH_HIGH:
                target = alpha_high
            elif visual_valid and confidence >= CONF_THRESH_LOW:
                target = alpha_high + (1.0-alpha_high) * (1.0-(confidence-CONF_THRESH_LOW)/(CONF_THRESH_HIGH-CONF_THRESH_LOW))
            else:
                target = 1.0  # 纯 IMU
            step = 0.1
            if current_alpha < target:
                current_alpha = min(target, current_alpha + step)
            elif current_alpha > target:
                current_alpha = max(target, current_alpha - step)

            q_i = quat_mul(q_off, q_imu_interp)  # 校准后的 IMU 四元数
            q_v = wrist_quat if visual_valid else (1.0, 0.0, 0.0, 0.0)
            fused_wrist_quat = quat_slerp(q_v, q_i, current_alpha)

            # 手指直接用视觉的 (如果有)
            finger_data = {}
            for fn in FINGER_NAMES:
                if visual_valid and hand_pose_rotmats:
                    finger_data[fn] = [rotmat_to_quat(hand_pose_rotmats[j])
                                       for j in MANO_TO_FINGER[fn] if j < len(hand_pose_rotmats)]
                else:
                    finger_data[fn] = []

        # ====== 记录融合结果 ======
        fused_entry = {
            "frame": frame_idx,
            "ts_video": round(frame_ts, 4),
            "calibrated": calibrated,
            "visual_valid": visual_valid,
            "confidence": round(confidence, 4),
            "alpha": round(current_alpha, 4),
            "imu_q": quat_to_list(q_imu_interp) if calibrated else [],
            "visual_q": quat_to_list(wrist_quat) if visual_valid else [],
            "fused_q": quat_to_list(fused_wrist_quat) if calibrated else [],
            "fingers": {}
        }
        if calibrated:
            for fn in FINGER_NAMES:
                fused_entry["fingers"][fn] = [quat_to_list(q) for q in finger_data[fn]]
        fused_frames.append(fused_entry)

        # ====== 叠加信息 ======
        info_lines = []
        if calibrated:
            info_lines.append(f"FUSED | alpha={current_alpha:.2f} conf={confidence:.2f}")
            q = fused_wrist_quat
            info_lines.append(f"W: ({q[0]:.3f},{q[1]:.3f},{q[2]:.3f},{q[3]:.3f})")
        elif visual_valid:
            info_lines.append(f"CALIBRATING... {len(calib_quats)}/{CALIB_SAMPLES}")
        else:
            info_lines.append("Waiting for hand...")
        info_lines.append(f"Frame {frame_idx}/{total_frames}")
        for i, line in enumerate(info_lines):
            cv2.putText(img, line, (8, 20+i*20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 0), 1)

        out_video.write(img)
        frame_idx += 1

        if frame_idx % 30 == 0:
            elapsed = time.time() - process_t0
            eta = elapsed / frame_idx * (total_frames - frame_idx)
            print(f"  [{frame_idx}/{total_frames}] {elapsed:.1f}s  ETA:{eta:.0f}s  vis={visual_valid} cal={calibrated}")

    # ====== 关闭资源 ======
    cap.release()
    out_video.release()
    total_time = time.time() - process_t0
    print(f"\n[DONE] {frame_idx}/{total_frames} 帧, 耗时 {total_time:.1f}s ({frame_idx/total_time:.1f} fps)")

    # ====== 输出融合 JSON ======
    output = {
        "meta": {
            "video": args.video,
            "imu": args.imu,
            "total_frames": frame_idx,
            "fps_video": fps,
            "calibrated": calibrated,
            "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "frames": fused_frames,
    }
    with open(fused_json_path, 'w') as f:
        json.dump(output, f, indent=1)
    print(f"[OUTPUT] 融合数据 -> {fused_json_path}")
    print(f"[OUTPUT] 处理视频 -> {processed_video_path}")


if __name__ == "__main__":
    main()
