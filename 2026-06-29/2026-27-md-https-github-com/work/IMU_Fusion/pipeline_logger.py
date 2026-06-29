"""pipeline_logger.py — Full-link logging for IMU+Visual fusion pipeline.

Usage:
    from pipeline_logger import logger
    logger.stage("Loading models...")
    logger.ok("HAMER loaded")
    logger.fail("IMU not found")
    logger.summary()  # prints summary at end
"""

import os, time, json, sys, traceback
from datetime import datetime

class PipelineLogger:
    def __init__(self):
        self.log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "outputs", "logs", "runs")
        os.makedirs(self.log_dir, exist_ok=True)
        
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = os.path.join(self.log_dir, f"run_{ts}.log")
        self.entries = []
        self._start_time = time.time()
        self._stage_start = time.time()
        self._current_stage = ""
        self._has_errors = False
        self._error_count = 0
        
        self._write("=" * 60)
        self._write(f"PIPELINE RUN STARTED: {ts}")
        self._write(f"PID: {os.getpid()}")
        self._write("=" * 60)

    def _write(self, text):
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(text + "\n")

    def _ts(self):
        return datetime.now().strftime("%H:%M:%S.%f")[:12]

    def _elapsed(self):
        return time.time() - self._start_time

    def stage(self, name):
        """Mark start of a new stage"""
        self._current_stage = name
        self._stage_start = time.time()
        elapsed = self._elapsed()
        line = f"[{self._ts()} +{elapsed:6.1f}s] >>> {name}"
        self._write(line)
        self.entries.append({"t": elapsed, "stage": name, "status": "START", "msg": ""})
        print(line)

    def ok(self, msg=""):
        """Stage completed OK"""
        elapsed = self._elapsed()
        dur = time.time() - self._stage_start
        line = f"[{self._ts()} +{elapsed:6.1f}s]  OK  ({dur:.1f}s) {msg}"
        self._write(line)
        self.entries.append({"t": elapsed, "stage": self._current_stage, "status": "OK", "msg": msg, "dur": dur})
        print(line)

    def fail(self, msg=""):
        """Stage failed"""
        self._has_errors = True
        self._error_count += 1
        elapsed = self._elapsed()
        dur = time.time() - self._stage_start
        line = f"[{self._ts()} +{elapsed:6.1f}s] FAIL ({dur:.1f}s) {msg}"
        self._write(line)
        self._write(traceback.format_exc())
        self.entries.append({"t": elapsed, "stage": self._current_stage, "status": "FAIL", "msg": msg})
        print(f"  [FAIL] {msg}")

    def info(self, msg):
        """Info message"""
        elapsed = self._elapsed()
        line = f"[{self._ts()} +{elapsed:6.1f}s]  ..  {msg}"
        self._write(line)
        self.entries.append({"t": elapsed, "stage": self._current_stage, "status": "INFO", "msg": msg})

    def perf(self, msg):
        """Performance metric"""
        elapsed = self._elapsed()
        line = f"[{self._ts()} +{elapsed:6.1f}s] PERF {msg}"
        self._write(line)

    def data(self, name, value):
        """Log a data point"""
        elapsed = self._elapsed()
        line = f"[{self._ts()} +{elapsed:6.1f}s] DATA {name}={value}"
        self._write(line)

    def exception(self, e):
        """Log an exception"""
        self._has_errors = True
        self._error_count += 1
        elapsed = self._elapsed()
        tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        line = f"[{self._ts()} +{elapsed:6.1f}s] EXCP {type(e).__name__}: {e}"
        self._write(line)
        for tb_line in tb.split("\n"):
            self._write(f"       {tb_line}")

    def summary(self):
        """Print and save final summary"""
        elapsed = self._elapsed()
        status = "HAS ERRORS" if self._has_errors else "ALL OK"
        
        lines = []
        lines.append("=" * 60)
        lines.append(f"RUN COMPLETE: duration={elapsed:.0f}s errors={self._error_count} status={status}")
        lines.append("-" * 60)
        for e in self.entries:
            icon = {"OK": "  OK", "FAIL": "FAIL", "START": " >>>", "INFO": " ..."}[e["status"]]
            t = f"{e['t']:6.1f}s"
            lines.append(f"  [{t}] {icon} {e['stage']} {e['msg']}")
        lines.append("-" * 60)
        lines.append(f"Log file: {self.log_file}")
        lines.append("=" * 60)
        
        summary = "\n".join(lines)
        self._write("\n" + summary)
        print("\n" + summary)

# Global singleton
logger = PipelineLogger()
