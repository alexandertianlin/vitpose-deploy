import os
os.environ['PYOPENGL_PLATFORM'] = 'wgl'
os.environ['PYTORCH_JIT'] = '0'
import sys

hamer_dir = r'C:\Users\Administrator\Documents\Codex\2026-06-16\files-mentioned-by-the-user-gpu2-3\hamer_code\hamer-main'
ckpt = hamer_dir + r'\_DATA\hamer_ckpts\checkpoints\hamer.ckpt'
sys.path.insert(0, hamer_dir)
sys.path.insert(0, hamer_dir + '/third-party/ViTPose')

import torch
import numpy as np

# Check HAMER forward output keys without loading the full model
from hamer.models.hamer import HAMER
import inspect
# Look at the forward method source code to understand the output dict
source = inspect.getsource(HAMER.forward)
print('=== HAMER.forward() source (first 1200 chars) ===')
print(source[:1200])
