import os, sys
os.environ['PYOPENGL_PLATFORM'] = 'wgl'
os.environ['PYTORCH_JIT'] = '0'

hamer_dir = r'C:\Users\Administrator\Documents\Codex\2026-06-16\files-mentioned-by-the-user-gpu2-3\hamer_code\hamer-main'
os.chdir(hamer_dir)
ckpt = os.path.join(hamer_dir, '_DATA', 'hamer_ckpts', 'checkpoints', 'hamer.ckpt')
sys.path.insert(0, hamer_dir)
sys.path.insert(0, os.path.join(hamer_dir, 'third-party', 'ViTPose'))
sys.path.insert(0, os.path.join(hamer_dir, 'third-party'))

import torch
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')

print('Loading HAMER...')
from hamer.models import load_hamer
m_hamer, cfg_h = load_hamer(ckpt, init_renderer=False)
m_hamer = m_hamer.to("cuda").eval()
print(f'HAMER OK: {sum(p.numel() for p in m_hamer.parameters())/1e6:.1f}M params')
import gc; gc.collect()
print(f'VRAM used: {torch.cuda.memory_allocated()/1e9:.2f} GB')
