import os, sys, time, struct, threading
os.environ['PYOPENGL_PLATFORM'] = 'wgl'

print('=== Hardware Connectivity Test ===')
print()

# 1. Test D435i
print('1. D435i Camera...')
try:
    import pyrealsense2 as rs
    ctx = rs.context()
    devs = list(ctx.devices)
    if len(devs) == 0:
        print('   [FAIL] No RealSense device found')
    else:
        for d in devs:
            print(f'   [PASS] {d.get_info(rs.camera_info.name)}')
            print(f'          S/N: {d.get_info(rs.camera_info.serial_number)}')
            print(f'          FW:  {d.get_info(rs.camera_info.firmware_version)}')
            
            # Try to open stream
            pipe = rs.pipeline()
            cfg = rs.config()
            cfg.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
            pipe.start(cfg)
            for _ in range(10):
                pipe.wait_for_frames()
            pipe.stop()
            print('          Stream OK (10 frames)')
except Exception as e:
    print(f'   [ERROR] {e}')

print()

# 2. Test IMU Serial
print('2. IMU Glove (COM122, 460800)...')
try:
    import serial
    ser = serial.Serial('COM122', 460800, timeout=0.5)
    ser.reset_input_buffer()
    time.sleep(0.2)
    data = ser.read(200)
    if len(data) > 0:
        # Try to find frame headers
        headers = 0
        for i in range(len(data) - 2):
            if data[i] == 0xB5 and data[i+1] == 0xA5 and data[i+2] == 0x55:
                headers += 1
        print(f'   [PASS] {len(data)} bytes read, {headers} frame headers found')
        print(f'   First 20 bytes: {data[:20].hex()}')
    else:
        print('   [INFO] No data in 0.5s timeout (may need hand movement)')
    ser.close()
except serial.SerialException as e:
    print(f'   [FAIL] {e}')
except Exception as e:
    print(f'   [ERROR] {e}')

print()
print('=== Done ===')
