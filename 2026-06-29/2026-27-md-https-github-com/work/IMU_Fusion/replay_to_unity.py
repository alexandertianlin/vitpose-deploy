#!/usr/bin/env python3
"""
replay_to_unity.py — 读取离线融合结果, 通过 UDP 发送到 Unity,
                     同时播放录制视频用于对照验证。

用法:
  Python3 (hamer env) replay_to_unity.py ^
      --fused recordings/rec_20260629_150000_fused.json ^
      --video recordings/rec_20260629_150000.mp4

如果不指定参数, 自动在 recordings/ 目录下查找最新的匹配文件。

操作:
  SPACE    暂停/继续
  r        重新开始
  s        慢速 (0.25x)
  n        常速 (1x)
  f        快速 (2x)
  q/ESC    退出

画面布局 (左右分屏):
  [左] 录制视频          [右] 融合可视化 + 实时参数
"""

import os, sys, json, time, socket, argparse
import numpy as np
import cv2

UDP_IP = "127.0.0.1"
FINGER_NAMES = ["thumb", "index", "middle", "ring", "little"]


def send_fusion_packet(sock, frame_data, seq, fps_video=30):
    """构建并发送融合数据包到 Unity, 格式匹配 FusionUDPReceiver.cs"""
    pkt = {
        "ts": int(time.time() * 1000),
        "seq": seq,
        "fps": round(fps_video, 1),
        "conf": frame_data.get("confidence", 0.0),
        "wrist_pos": [0, 0, 0],
        "wrist_rot": frame_data.get("fused_q", [1, 0, 0, 0]),
        "fingers": []
    }
    fingers = frame_data.get("fingers", {})
    for fn in FINGER_NAMES:
        joints = fingers.get(fn, [])
        joints_list = []
        for j in joints:
            if isinstance(j, list) and len(j) == 4:
                joints_list.append(j)
            else:
                joints_list.append([1.0, 0.0, 0.0, 0.0])
        while len(joints_list) < 3:
            joints_list.append([1.0, 0.0, 0.0, 0.0])
        pkt["fingers"].append({"name": fn, "joints": joints_list[:3]})
    try:
        sock.sendto(json.dumps(pkt).encode(), (UDP_IP, UDP_PORT_FUS))
    except Exception as e:
        print(f"[UDP] 发送错误: {e}")


def find_latest_recordings():
    """自动查找 recordings/ 目录中最新的融合数据和视频"""
    rec_dir = "recordings"
    if not os.path.exists(rec_dir):
        print(f"[ERROR] recordings/ 目录不存在!")
        sys.exit(1)

    fused_files = [f for f in os.listdir(rec_dir) if f.endswith("_fused.json")]
    if not fused_files:
        print(f"[ERROR] recordings/ 中没有找到 _fused.json 文件!")
        sys.exit(1)
    latest_fused = sorted(fused_files)[-1]
    fused_path = os.path.join(rec_dir, latest_fused)

    base = latest_fused.replace("_fused.json", "")
    video_path = os.path.join(rec_dir, f"{base}.mp4")
    if not os.path.exists(video_path):
        mp4_files = [f for f in os.listdir(rec_dir) if f.endswith(".mp4") and not f.endswith("_processed.mp4")]
        if mp4_files:
            video_path = os.path.join(rec_dir, sorted(mp4_files)[-1])

    print(f"[AUTO] 融合数据: {fused_path}")
    print(f"[AUTO] 视频:     {video_path}")
    return fused_path, video_path


def show_info_panel(info_panel, current_idx, total_frames, frame_data, playing, speed):
    """在信息面板上绘制当前状态"""
    info_panel.fill(20)
    text_y = 30

    calibrated = frame_data.get("calibrated", False)
    visual_valid = frame_data.get("visual_valid", False)
    confidence = frame_data.get("confidence", 0.0)
    alpha = frame_data.get("alpha", 0.0)

    lines = [
        "=== REPLAY TO UNITY ===",
        f"帧: {current_idx} / {total_frames}",
        f"状态: {'PLAYING' if playing else 'PAUSED'}",
        f"速度: {speed:.2f}x",
        "---",
        f"校准: {'OK' if calibrated else 'NO'}",
        f"视觉: {'OK' if visual_valid else 'NO'}",
        f"置信度: {confidence:.3f}",
        f"alpha: {alpha:.3f}",
    ]

    if frame_data.get("fused_q"):
        q = frame_data["fused_q"]
        lines.append("---")
        lines.append("融合四元数:")
        lines.append(f"  w={q[0]:.4f}")
        lines.append(f"  x={q[1]:.4f}")
        lines.append(f"  y={q[2]:.4f}")
        lines.append(f"  z={q[3]:.4f}")

    # IMU vs Fused 角度差 (近似)
    if frame_data.get("imu_q") and frame_data.get("fused_q"):
        qi = frame_data["imu_q"]
        qf = frame_data["fused_q"]
        # 点积近似夹角的余弦
        dot = abs(qi[0]*qf[0] + qi[1]*qf[1] + qi[2]*qf[2] + qi[3]*qf[3])
        dot = min(1.0, max(-1.0, dot))
        angle_diff = 2.0 * np.degrees(np.arccos(dot))
        lines.append(f"IMU-融合差: {angle_diff:.1f} deg")

    lines.append("---")
    lines.append("[SPACE] 暂停  [r] 重播")
    lines.append("[s]0.25x  [n]1x  [f]2x")

    for line in lines:
        cv2.putText(info_panel, line, (15, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 0), 1)
        text_y += 22


def handle_key(key, state):
    """处理按键输入, 返回更新后的状态"""
    if key == ord(' '):
        state["playing"] = not state["playing"]
        state["last_frame_time"] = time.perf_counter()
        print(f"[REPLAY] {'继续' if state['playing'] else '暂停'}")
    elif key == ord('r'):
        state["current_idx"] = 0
        state["seq"] = 0
        state["last_frame_time"] = time.perf_counter()
        state["cap_set"] = False
        print("[REPLAY] 重播")
    elif key == ord('s'):
        state["speed"] = 0.25
        print(f"[REPLAY] 速度: {state['speed']}x")
    elif key == ord('n'):
        state["speed"] = 1.0
        print(f"[REPLAY] 速度: {state['speed']}x")
    elif key == ord('f'):
        state["speed"] = 2.0
        print(f"[REPLAY] 速度: {state['speed']}x")
    elif key == ord('q') or key == 27:
        state["quit"] = True


def main():
    parser = argparse.ArgumentParser(description="回放融合数据到 Unity")
    parser.add_argument("--fused", help="融合 JSON 路径 (自动查找)")
    parser.add_argument("--video", help="录制视频路径 (自动查找)")
    parser.add_argument("--port", type=int, default=8080, help="Unity UDP 端口 (默认 8080)")
    args = parser.parse_args()

    if args.fused and args.video:
        fused_path = args.fused
        video_path = args.video
    else:
        fused_path, video_path = find_latest_recordings()

    if not os.path.exists(fused_path):
        print(f"[ERROR] 融合文件不存在: {fused_path}")
        sys.exit(1)
    if not os.path.exists(video_path):
        print(f"[ERROR] 视频文件不存在: {video_path}")

    # 加载融合数据
    with open(fused_path, 'r') as f:
        data = json.load(f)
    frames = data["frames"]
    meta = data["meta"]
    fps_video = meta.get("fps_video", 30.0)
    total_frames = len(frames)
    print(f"[DATA] {total_frames} 帧融合数据, 视频 fps={fps_video}")
    print(f"[DATA] 校准: {'OK' if meta.get('calibrated') else 'NO'}")

    # 打开视频
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] 无法打开视频: {video_path}")
        sys.exit(1)

    # UDP 套接字
    global UDP_PORT_FUS
    UDP_PORT_FUS = args.port
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"[UDP] 发送到 {UDP_IP}:{UDP_PORT_FUS}")

    # 初始化
    state = {
        "playing": True,
        "speed": 1.0,
        "current_idx": 0,
        "seq": 0,
        "quit": False,
        "last_frame_time": time.perf_counter(),
        "cap_set": False,
    }

    cv2.namedWindow("Replay to Unity", cv2.WINDOW_NORMAL)
    info_width = 400
    cv2.resizeWindow("Replay to Unity", 640 + info_width, 480)
    info_panel = np.zeros((480, info_width, 3), dtype=np.uint8)
    print("\n[操作] SPACE=暂停  r=重播  s=0.25x  n=1x  f=2x  q=退出")

    try:
        while state["current_idx"] < total_frames and not state["quit"]:
            frame_data = frames[state["current_idx"]]
            fps_actual = meta.get("fps_video", 30.0)
            frame_interval = 1.0 / (fps_actual * state["speed"])

            if state["playing"]:
                # 时间驱动播放
                now = time.perf_counter()
                elapsed = now - state["last_frame_time"]
                if elapsed < frame_interval:
                    # 等待同时处理按键
                    wait_ms = max(1, int((frame_interval - elapsed) * 1000))
                    show_info_panel(info_panel, state["current_idx"], total_frames,
                                    frame_data, state["playing"], state["speed"])
                    cap.set(cv2.CAP_PROP_POS_FRAMES, state["current_idx"])
                    ret, frame_img = cap.read()
                    if ret:
                        cv2.putText(frame_img, f"#{state['current_idx']} t={frame_data.get('ts_video','?'):.1f}s",
                                    (8, frame_img.shape[0]-15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                        if frame_img.shape[0] != info_panel.shape[0]:
                            scale = info_panel.shape[0] / frame_img.shape[0]
                            frame_img = cv2.resize(frame_img, (int(frame_img.shape[1]*scale), info_panel.shape[0]))
                        cv2.imshow("Replay to Unity", np.hstack([frame_img, info_panel]))
                    key = cv2.waitKey(wait_ms) & 0xFF
                    handle_key(key, state)
                    continue

                state["last_frame_time"] = now

                # 发送到 Unity
                send_fusion_packet(sock, frame_data, state["seq"], fps_actual)
                state["seq"] += 1

                # 读取并显示当前帧
                cap.set(cv2.CAP_PROP_POS_FRAMES, state["current_idx"])
                ret, frame_img = cap.read()
                if not ret:
                    print(f"[REPLAY] 视频结束于 {state['current_idx']}")
                    break

                show_info_panel(info_panel, state["current_idx"], total_frames,
                                frame_data, state["playing"], state["speed"])

                # 视频叠加信息
                raw_fps = meta.get("fps_video", 30.0)
                cv2.putText(frame_img, f"#{state['current_idx']} t={frame_data.get('ts_video','?'):.1f}s @{state['speed']:.1f}x",
                            (8, frame_img.shape[0]-15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

                if frame_img.shape[0] != info_panel.shape[0]:
                    scale = info_panel.shape[0] / frame_img.shape[0]
                    frame_img = cv2.resize(frame_img, (int(frame_img.shape[1]*scale), info_panel.shape[0]))

                cv2.imshow("Replay to Unity", np.hstack([frame_img, info_panel]))
                state["current_idx"] += 1

            else:
                # 暂停: 持续显示当前帧, 等待按键
                cap.set(cv2.CAP_PROP_POS_FRAMES, state["current_idx"])
                ret, frame_img = cap.read()
                if ret:
                    show_info_panel(info_panel, state["current_idx"], total_frames,
                                    frame_data, state["playing"], state["speed"])
                    cv2.putText(frame_img, f"PAUSED #{state['current_idx']}",
                                (8, frame_img.shape[0]-15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                    if frame_img.shape[0] != info_panel.shape[0]:
                        scale = info_panel.shape[0] / frame_img.shape[0]
                        frame_img = cv2.resize(frame_img, (int(frame_img.shape[1]*scale), info_panel.shape[0]))
                    cv2.imshow("Replay to Unity", np.hstack([frame_img, info_panel]))
                key = cv2.waitKey(50) & 0xFF
                handle_key(key, state)

        if not state["quit"]:
            print(f"\n[REPLAY] 全部 {total_frames} 帧完成")
            print("[REPLAY] 按任意键退出")
            cv2.waitKey(0)

    finally:
        cap.release()
        sock.close()
        cv2.destroyAllWindows()
        print("[REPLAY] 退出")


if __name__ == "__main__":
    main()
