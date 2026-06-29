#!/usr/bin/env python3
"""Pre-flight diagnostic — run BEFORE fusion_pipeline.py"""
import os, sys, socket, time, json
os.environ["PYOPENGL_PLATFORM"] = "wgl"

PASS, FAIL, SKIP = 0, 0, 0
results = []

def check(name, status, detail=""):
    global PASS, FAIL
    if status: PASS += 1
    else: FAIL += 1
    icon = "PASS" if status else "FAIL"
    results.append({"name": name, "status": icon, "detail": detail})
    print(f"  [{icon}] {name}")

print("=" * 56)
print("  Pre-flight Diagnostic — IMU+Visual Fusion Pipeline")
print("=" * 56)
print()

# 1. Python environment
print("[1] Environment")
check("Python", sys.version_info >= (3, 8), f"{sys.version.split()[0]}")
try:
    import torch
    check("PyTorch", True, f"{torch.__version__}")
    check("CUDA available", torch.cuda.is_available(), 
          f"{torch.cuda.get_device_name(0)}" if torch.cuda.is_available() else "")
    if torch.cuda.is_available():
        free_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        check("GPU memory", free_gb >= 4, f"{free_gb:.1f} GB")
except Exception as e:
    check("PyTorch", False, str(e))

try:
    import cv2; check("OpenCV", True, cv2.__version__)
except: check("OpenCV", False, "not installed")
try:
    import numpy as np; check("NumPy", True, np.__version__)
except: check("NumPy", False)
try:
    import serial; check("pyserial", True, "")
except: check("pyserial", False, "pip install pyserial")
try:
    import pyrealsense2 as rs; check("pyrealsense2", True, rs.__version__)
except: check("pyrealsense2", False)

print()

# 2. Hardware
print("[2] Hardware")
# D435i
try:
    import pyrealsense2 as rs
    ctx = rs.context()
    devs = list(ctx.devices)
    if devs:
        for d in devs:
            check(f"D435i: {d.get_info(rs.camera_info.name)}", True,
                  f"S/N {d.get_info(rs.camera_info.serial_number)}")
    else:
        check("D435i camera", False, "No RealSense device found")
except Exception as e:
    check("D435i camera", False, str(e))

# COM122
try:
    import serial
    ser = serial.Serial("COM122", 460800, timeout=0.2)
    data = ser.read(35)
    check("IMU glove (COM122)", len(data) > 0, f"{len(data)} bytes")
    ser.close()
except serial.SerialException as e:
    check("IMU glove (COM122)", False, str(e).split("(")[0].strip())
except Exception as e:
    check("IMU glove (COM122)", False, str(e))

print()

# 3. Model weights
print("[3] Model weights")
HAMER_DIR = r"C:\Users\Administrator\Documents\Codex\2026-06-16\files-mentioned-by-the-user-gpu2-3\hamer_code\hamer-main"
ckpt = os.path.join(HAMER_DIR, "_DATA", "hamer_ckpts", "checkpoints", "hamer.ckpt")
vitpose_pth = os.path.join(HAMER_DIR, "_DATA", "vitpose_ckpts", "vitpose+_huge", "wholebody.pth")

check("HAMER hamer.ckpt", os.path.exists(ckpt), 
      f"{os.path.getsize(ckpt)/1e9:.1f} GB" if os.path.exists(ckpt) else "MISSING")
check("ViTPose wholebody.pth", os.path.exists(vitpose_pth),
      f"{os.path.getsize(vitpose_pth)/1e9:.1f} GB" if os.path.exists(vitpose_pth) else "MISSING")

print()

# 4. Port availability
print("[4] UDP ports")
for port, name in [(5055, "VisionBridge (VisionBridge.cs)"),
                   (8080, "Fusion (FusionUDPReceiver.cs)")]:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.bind(("127.0.0.1", port))
        check(f"Port {port} ({name})", True, "FREE")
        s.close()
    except OSError as e:
        # Find the process holding the port
        check(f"Port {port} ({name})", False, "IN USE by Unity or another process")

print()

# 5. Unity process check
print("[5] Unity")
if sys.platform == "win32":
    import subprocess
    try:
        out = subprocess.check_output("tasklist /FI \"IMAGENAME eq Unity.exe\" /NH", shell=True, timeout=3).decode()
        check("Unity process", "Unity.exe" in out, "Running" if "Unity.exe" in out else "Not running")
    except: check("Unity process", False, "Cannot query")
else:
    check("Unity process", False, "Non-Windows")

print()
print("=" * 56)
print(f"  Results: {PASS} passed, {FAIL} failed")
print()

if FAIL > 0:
    print("  FAILURES:")
    for r in results:
        if r["status"] == "FAIL":
            print(f"    - {r['name']}: {r['detail']}")
    print()
    print("  Fix the above issues before running fusion_pipeline.py")
else:
    print("  All checks passed. Ready to run fusion_pipeline.py")
print("=" * 56)
