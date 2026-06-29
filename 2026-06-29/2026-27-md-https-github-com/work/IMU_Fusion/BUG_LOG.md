# Bug Log — Record-Replay Pipeline

## BUG-001: HAMER requires os.chdir to find MANO mean params
**Status**: Fixed in offline_fusion_processor.py
**Severity**: High

The HAMER model loads MANO joint mean params from a relative path inside
the HAMER source tree. If cwd is not HAMER_DIR, the model loads but
produces incorrect hand_pose (fingers) and may crash on forward pass.

**Fix**: Added os.chdir(HAMER_DIR) at import time and injected
sys.path.insert(0, HAMER_DIR).

---

## BUG-002: ViTPose confidence may be undefined on skip frames
**Status**: Fixed
**Severity**: Medium

When ViTPose skip > 0, the confidence variable is carried over from the
last inferenced frame. If the first frame is skipped, confidence is undefined.

**Fix**: Initialize confidence = 0.0 at the top of each frame loop.

---

## BUG-003: UTF-8 BOM in replay_to_unity.py causes SyntaxError
**Status**: Fixed
**Severity**: Medium

The initial replay_to_unity.py had a UTF-8 BOM at the file start.
Python ast.parse rejects non-printable characters.

**Fix**: Saved without BOM.

---

## BUG-004: Docstring backslash paths trigger SyntaxWarning
**Status**: Fixed
**Severity**: Cosmetic

Paths like D:\ProgramData\... cause invalid escape sequence warnings.

**Fix**: Replaced with plain text in docstrings.

---

## BUG-005: cap.set() per frame is O(n) seek
**Status**: Known issue
**Severity**: Low

cap.set(cv2.CAP_PROP_POS_FRAMES) seeks per frame. Adds ~1-2ms overhead.
Acceptable for offline replay < 1000 frames.
