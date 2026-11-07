"""Best-effort, nonblocking telemetry. No trading logic depends on this module."""
import json
import os
import queue
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone

_queue = queue.Queue(maxsize=1000)
_lock = threading.Lock()
_started = False

def _send():
    while True:
        payload = _queue.get()
        try:
            req = urllib.request.Request("http://127.0.0.1:8797/event", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=0.5) as res:
                res.read(100)
        except Exception:
            pass
        finally:
            _queue.task_done()

def emit(agent, kind, text, **details):
    global _started
    if os.environ.get("TRENCHFLOOR_EVENTS_DISABLED") == "1" or "unittest" in sys.modules or "pytest" in sys.modules:
        return
    try:
        with _lock:
            if not _started:
                threading.Thread(target=_send, daemon=True, name="live-events").start()
                _started = True
        _queue.put_nowait({"agent": agent, "kind": kind, "text": str(text)[:1500], "time": datetime.now(timezone.utc).isoformat(), "pid": os.getpid(), **details})
    except Exception:
        pass

def start_heartbeat():
    def beat():
        while True:
            emit("System", "heartbeat", "Research process alive; idle does not mean scanning every second.")
            time.sleep(5)
    try:
        threading.Thread(target=beat, daemon=True, name="live-heartbeat").start()
    except Exception:
        pass
