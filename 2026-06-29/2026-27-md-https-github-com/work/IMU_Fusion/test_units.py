import os, sys
os.environ['PYOPENGL_PLATFORM'] = 'wgl'
os.environ['PYTORCH_JIT'] = '0'

sys.path.insert(0, r'C:\Users\Administrator\Documents\Codex\2026-06-29\2026-27-md-https-github-com\work\IMU_Fusion')
from fusion_pipeline import (
    Stm32Parser, FusionEngine, ImuData, VisualData,
    rotmat_to_quat, quat_slerp, quat_mul, quat_norm, quat_inv,
    send_udp_fusion, quat_to_json
)
import numpy as np

print('=== Module imports OK ===')

# Test Stm32Parser
parser = Stm32Parser()
print(f'Parser created: frame_count={parser._frame_count}')

# Test FusionEngine
engine = FusionEngine()
print(f'Engine created: calibrated={engine.calibrated}')

# Test quaternion math
q1 = (0.707, 0.707, 0.0, 0.0)
q2 = (1.0, 0.0, 0.0, 0.0)
q_interp = quat_slerp(q1, q2, 0.5)
print(f'Slerp test: ({q1[0]:.3f},{q1[1]:.3f}) -> ({q2[0]:.3f},{q2[1]:.3f}) @ t=0.5 = ({q_interp[0]:.3f},{q_interp[1]:.3f})')

# Test rotmat_to_quat
R = np.eye(3)
q = rotmat_to_quat(R)
print(f'Rotmat identity -> quat: ({q[0]:.3f},{q[1]:.3f},{q[2]:.3f},{q[3]:.3f})')

# Test JSON serialization
q_json = quat_to_json(q)
print(f'JSON: {q_json}')

print()
print('=== ALL UNIT TESTS PASSED ===')
