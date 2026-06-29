import os
os.environ['PYOPENGL_PLATFORM'] = 'wgl'
os.environ['PYTORCH_JIT'] = '0'
import sys
hamer_dir = r'C:\Users\Administrator\Documents\Codex\2026-06-16\files-mentioned-by-the-user-gpu2-3\hamer_code\hamer-main'
sys.path.insert(0, hamer_dir)
sys.path.insert(0, hamer_dir + '/third-party/ViTPose')

import inspect
from hamer.models.hamer import HAMER

# Look at forward_step to understand output dict keys
source = inspect.getsource(HAMER.forward_step)
print('=== HAMER.forward_step() source ===')
print(source)
