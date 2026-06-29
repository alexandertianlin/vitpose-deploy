#!/usr/bin/env python3
"""
recorder.py — 录制 D435i 视频 + IMU 信号，保存为 .mp4 + .csv

用法:
  Python3 (hamer env) recorder.py

操作:
  r    开始/停止录制
  ESC/q  退出

输出文件:
  recordings/rec_YYYYMMDD_HHMMSS.mp4     — D435i RGB 视频 (640x480)
  recordings/rec_YYYYMMDD_HHMMSS_imu.csv  — IMU 数据 (时间戳,四元数)
  两个文件同步: 首个 IMU 帧时间戳 ≈ 首个视频帧时间戳
"""

import os, sys, time, json, struct, csv, threading, queue
from datetime import datetime
import numpy as np
import cv2

# ====== 配置 ======
COM_PORT = "COM122"
COM_BAUD = 460800
CAM_W, CAM_H, CAM_FPS = 640, 480, 30
OUT_DIR = "recordings"

# ====== IMU 解析 ======
from dataclasses import dataclass

@dataclass
class ImuFrame:
    ts: float = 0.0          # 时间戳 (秒, time.monotonic)
    quat_wxyz: tuple = (1.0, 0.0, 0.0, 0.0)
    valid: bool = False

class Stm32Parser:
    """STM32 35字节帧解析器"""
    def __init__(self): self._buf = bytearray()
    def feed(self, data: bytes) -> list:
        self._buf.extend(data); frames = []
        while True:
            idx = self._buf.find(b"\xB5\xA5\x55")
            if idx < 0: self._buf.clear(); break
            if idx > 0: del self._buf[:idx]
            if len(self._buf) < 35: break
            frame = bytes(self._buf[:35]); del self._buf[:35]
            try:
                imu = self._parse(frame)
                if imu: frames.append(imu)
            except: pass
        return frames
    def _parse(self, frame):
        if frame[0]!=0xB5 or frame[1]!=0xA5 or frame[2]!=0x55: return None
        crc=0; [crc:=crc^b for b in frame[:34]]
        if crc!=frame[34]: return None
        qw,qx,qy,qz = [struct.unpack_from("<h",frame,8+i)[0]/10000.0 for i in (0,2,4,6)]
        n=np.sqrt(qw*qw+qx*qx+qy*qy+qz*qz)
        if n>0.001: qw/=n; qx/=n; qy/=n; qz/=n
        return ImuFrame(quat_wxyz=(qw,qx,qy,qz), valid=True)


def imu_reader_thread(imu_q, stop_event):
    """后台线程: 持续读取 IMU 串口, 给每个帧打上时间戳"""
    parser = Stm32Parser()
    import serial
    retry = 0
    while not stop_event.is_set():
        try:
            ser = serial.Serial(COM_PORT, COM_BAUD, timeout=0.01)
            ser.reset_input_buffer()
            print(f"[IMU] 串口 {COM_PORT} 打开成功 @ {COM_BAUD} baud")
            retry = 0
            while not stop_event.is_set():
                data = ser.read(256)
                if data:
                    now = time.monotonic()
                    for f in parser.feed(data):
                        if f.valid:
                            f.ts = now
                            imu_q.put(f)
                else:
                    time.sleep(0.001)
        except Exception as e:
            retry += 1
            wait = min(1.0 * (2 ** min(retry, 4)), 10)
            print(f"[IMU] 连接失败 ({e}), {wait:.0f}s 后重试 ({retry})...")
            time.sleep(wait)
        finally:
            if 'ser' in locals() and ser.is_open:
                try: ser.close()
                except: pass


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # ====== 启动 D435i ======
    import pyrealsense2 as rs
    ctx = rs.context()
    devices = ctx.query_devices()
    if not devices:
        print("[ERROR] 未检测到 RealSense 设备!")
        sys.exit(1)
    dev = devices[0]
    sn = dev.get_info(rs.camera_info.serial_number)
    print(f"[D435i] 已连接: S/N {sn}, FW {dev.get_info(rs.camera_info.firmware_version)}")

    pipe = rs.pipeline()
    cfg = rs.config()
    cfg.enable_device(sn)
    cfg.enable_stream(rs.stream.color, CAM_W, CAM_H, rs.format.bgr8, CAM_FPS)
    profile = pipe.start(cfg)
    color_stream = profile.get_stream(rs.stream.color)
    intr = color_stream.as_video_stream_profile().get_intrinsics()
    print(f"[D435i] 分辨率: {CAM_W}x{CAM_H} @ {CAM_FPS}fps, 内参: fx={intr.fx:.1f} fy={intr.fy:.1f}")

    # ====== 启动 IMU 读取线程 ======
    imu_q = queue.Queue()
    stop_event = threading.Event()
    imu_thread = threading.Thread(target=imu_reader_thread, args=(imu_q, stop_event), daemon=True)
    imu_thread.start()
    time.sleep(1.0)  # 等 IMU 连接稳定

    # ====== 录制状态 ======
    recording = False
    record_start_ts = 0.0
    video_writer = None
    csv_file = None
    csv_writer = None
    frame_count = 0
    imu_buffer = []

    cv2.namedWindow("Recorder", cv2.WINDOW_NORMAL)
    print("\n[操作] r=录制开关  q/ESC=退出")

    try:
        while True:
            # ====== 捕获 D435i 帧 ======
            frames = pipe.wait_for_frames(timeout_ms=5000)
            color_frame = frames.get_color_frame()
            if not color_frame:
                continue
            img = np.asanyarray(color_frame.get_data())
            now = time.monotonic()

            # ====== 后台读取 IMU ======
            while not imu_q.empty():
                try:
                    imu_f = imu_q.get_nowait()
                    if recording:
                        imu_buffer.append(imu_f)
                except queue.Empty:
                    break

            # ====== 录制逻辑 ======
            if recording:
                if record_start_ts == 0.0:
                    record_start_ts = now
                    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    video_path = os.path.join(OUT_DIR, f"rec_{ts_str}.mp4")
                    csv_path = os.path.join(OUT_DIR, f"rec_{ts_str}_imu.csv")

                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    video_writer = cv2.VideoWriter(video_path, fourcc, CAM_FPS, (CAM_W, CAM_H))

                    csv_file = open(csv_path, 'w', newline='')
                    csv_writer = csv.writer(csv_file)
                    csv_writer.writerow(["ts_monotonic", "ts_utc_ms", "qw", "qx", "qy", "qz", "frame_idx"])

                    print(f"[REC] 开始录制 -> {video_path}")

                video_writer.write(img)
                frame_count += 1
                elapsed = now - record_start_ts
                cv2.circle(img, (30, 30), 10, (0, 0, 255), -1)
                cv2.putText(img, f"REC {elapsed:.1f}s #{frame_count}",
                            (50, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            # ====== 显示 ======
            status = "REC" if recording else "IDLE"
            cv2.putText(img, f"IMU: {imu_q.qsize()} buffered | {status}",
                        (8, CAM_H-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 0), 1)
            cv2.imshow("Recorder", img)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('r'):
                if not recording:
                    recording = True
                    record_start_ts = 0.0
                    imu_buffer.clear()
                    frame_count = 0
                    print("[REC] 按下录制键")
                else:
                    recording = False
                    if video_writer:
                        video_writer.release()
                        video_writer = None
                    if csv_writer:
                        base_ts = record_start_ts
                        for f in imu_buffer:
                            csv_writer.writerow([
                                f"{f.ts:.6f}",
                                int((f.ts - base_ts + time.time() - time.monotonic()) * 1000),
                                f"{f.quat_wxyz[0]:.6f}", f"{f.quat_wxyz[1]:.6f}",
                                f"{f.quat_wxyz[2]:.6f}", f"{f.quat_wxyz[3]:.6f}",
                                ""
                            ])
                        csv_file.close()
                        csv_file = None
                        csv_writer = None
                    print(f"[REC] 录制完成: {frame_count} 帧, {len(imu_buffer)} IMU 数据点")
                    frame_count = 0

            elif key == ord('q') or key == 27:
                break

    finally:
        stop_event.set()
        pipe.stop()
        if video_writer:
            video_writer.release()
        if csv_file:
            csv_file.close()
        cv2.destroyAllWindows()
        print("[REC] 退出")

if __name__ == "__main__":
    main()
