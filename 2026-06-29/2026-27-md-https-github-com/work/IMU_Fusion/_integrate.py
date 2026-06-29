import sys, os
fp = r"C:\Users\Administrator\Documents\Codex\2026-06-29\2026-27-md-https-github-com\work\IMU_Fusion\fusion_pipeline.py"
with open(fp, "r", encoding="utf-8") as f:
    content = f.read()

# Add logger import after cv2
content = content.replace(
    "import numpy as np\nimport cv2",
    "import numpy as np\nimport cv2\nsys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\nfrom pipeline_logger import logger"
)
# Wrap stages
content = content.replace('logger.stage("Loading HAMER")', 'logger.stage("Loading HAMER")\n    print("Loading HAMER...")')
content = content.replace('logger.stage("Loading ViTPose")', 'logger.stage("Loading ViTPose")\n    print("Loading ViTPose...")')
content = content.replace('logger.stage("Opening D435i")', 'logger.stage("Opening D435i")\n    print("Opening D435i...")')
content = content.replace('logger.stage("Fusion running")', 'logger.stage("Fusion running")\n    print("=== Running ===")')

# Add startup diagnostic logging
content = content.replace(
    '    _issues = run_diagnostic()',
    'logger.stage("Startup diagnostic")\n    _issues = run_diagnostic()'
)
content = content.replace(
    '    return True\n\ndef run_diagnostic():',
    'logger.ok("All checks passed")\n    return True\n\ndef run_diagnostic():'
)

# Log shutdown
old = 'print("Cleaning up..."); stop_event.set(); pipe.stop()'
new = 'logger.stage("Shutdown")\n    logger.info("Cleaning up...")\n    stop_event.set(); pipe.stop()'
content = content.replace(old, new)
content = content.replace('logger.ok("Pipeline stopped")\n        logger.summary()', 'logger.ok("Pipeline stopped")\n    logger.summary()')

with open(fp, "w", encoding="utf-8") as f:
    f.write(content)

import py_compile
try:
    py_compile.compile(fp)
    print("SYNTAX OK")
    for m in ["from pipeline_logger", "logger.stage", "logger.ok", "logger.summary"]:
        c = content.count(m)
        print(f"  {m}: {c}")
except py_compile.PyCompileError as e:
    print(f"ERROR: {e}")
