import sys
hamer_dir = r'C:\Users\Administrator\Documents\Codex\2026-06-16\files-mentioned-by-the-user-gpu2-3\hamer_code\hamer-main'
sys.path.insert(0, hamer_dir)
sys.path.insert(0, hamer_dir + '/third-party/ViTPose')

# Check if we can import hamer modules
try:
    from hamer.models import load_hamer
    import inspect
    print('load_hamer imported OK')
    
    # Check the forward method signature
    from hamer.models.hamer import HAMER
    sig = inspect.signature(HAMER.forward)
    print(f'forward params: {list(sig.parameters.keys())}')
except Exception as e:
    print(f'Import error: {e}')
