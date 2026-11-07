#!/usr/bin/env python3
"""Read-only realtime dashboard. Only the separate loopback port accepts events."""
import base64
import hashlib
import json
import re
import mimetypes
import socket
import struct
import threading
import time
from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from live_chat import LiveChat

ROOT = Path(__file__).resolve().parent
BUFFER = ROOT / "data/cache/live-events.json"
ROLES = ["Risk Manager", "Bubble Map Analyst", "X/Twitter Scout", "Data Scout", "Backtester", "Strategist"]
chat = LiveChat(ROOT / "data/cache/live-chat-state.json")
condition = threading.Condition()
try:
    recent = deque(json.loads(BUFFER.read_text())[-200:], maxlen=200)
except Exception:
    recent = deque(maxlen=200)
if not chat.data["messages"]:
    for event in recent:
        chat.record(event)
sequence = int(recent[-1]["id"]) if recent else 0
heartbeat = None
agent_updates = {}
for item in recent:
    if item.get("kind") == "status":
        agent_updates[item.get("agent")] = item

def read_json(path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}

def snapshot():
    state = read_json(ROOT / "data/research.json")
    ledger = read_json(ROOT / "data/ledger/index.json")
    prior = {a["role"]: a for a in state.get("agents", [])}
    agents = []
    for role in ROLES:
        a = dict(prior.get(role) or {"role": role, "status": "unknown"})
        e = agent_updates.get(role)
        if e and e["time"] >= (a.get("heartbeat") or ""):
            a.update(status=e.get("status", a.get("status")), task=e["text"], heartbeat=e["time"], latest_action=e.get("action") or e["text"])
        agents.append(a)
    state["agents"] = agents
    state["ledger"] = ledger
    return {"chat": chat.data["messages"][-200:], "checklist": chat.data["checklist"], "research": state, "agents": agents, "ledger": ledger, "events": list(recent), "cycle": state.get("cycle_count"), "last_cycle": state.get("last_cycle"), "next_cycle": state.get("next_cycle"), "heartbeat": heartbeat, "server_time": datetime.now(timezone.utc).isoformat(), "sequence": sequence}

def ingest(event):
    global sequence, heartbeat
    with condition:
        if event.get("kind") == "heartbeat":
            heartbeat = event["time"]
        else:
            sequence += 1
            event["id"] = sequence
            recent.append(event)
            for generated in chat.record(event):
                sequence += 1
                generated["id"] = sequence
                recent.append(generated)
            if event.get("agent") in ROLES:
                prior = agent_updates.get(event["agent"], {})
                agent_updates[event["agent"]] = {**prior, **event, "kind": "status", "status": event.get("status", prior.get("status", "working"))}
            BUFFER.parent.mkdir(parents=True, exist_ok=True)
            tmp = BUFFER.with_suffix(".tmp")
            tmp.write_text(json.dumps(list(recent)))
            tmp.replace(BUFFER)
        condition.notify_all()

class Dashboard(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *args):
        pass
    def plain(self, code, body, content="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", content)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)
    def do_POST(self):
        self.close_connection = True
        self.plain(405, b'{"error":"Read only"}')
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/":
            return self.plain(200, (ROOT / "live/index.html").read_bytes(), "text/html; charset=utf-8")
        # Explicit allowlist only; never expose source, credentials or write routes.
        asset = None
        if re.fullmatch(r"/icons/[a-zA-Z0-9_-]+\.png", path):
            asset = ROOT / "live" / path.lstrip("/")
        elif path in ("/BEST_STRATEGY.md", "/LESSONS.md", "/data/research.json", "/data/feed.json", "/data/ledger/index.json") or re.fullmatch(r"/data/ledger/\d{4}-\d{2}-\d{2}\.json", path):
            asset = ROOT / path.lstrip("/")
        if asset:
            if not asset.is_file():
                return self.plain(404, b'{}')
            return self.plain(200, asset.read_bytes(), mimetypes.guess_type(str(asset))[0] or "text/plain")
        if path == "/occupancy.js":
            return self.plain(200, (ROOT / "live/occupancy.js").read_bytes(), "text/javascript")
        if path == "/health":
            return self.plain(200, b'{"ok":true,"mode":"paper/read-only"}')
        if path == "/state":
            with condition:
                body = json.dumps(snapshot()).encode()
            return self.plain(200, body)
        if path not in ("/events", "/ws"):
            return self.plain(404, b'{}')
        ws = path == "/ws"
        if ws:
            key = self.headers.get("Sec-WebSocket-Key", "")
            if self.headers.get("Upgrade", "").lower() != "websocket" or not key:
                return self.plain(400, b'{}')
            accept = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
            self.send_response(101)
            self.send_header("Upgrade", "websocket")
            self.send_header("Connection", "Upgrade")
            self.send_header("Sec-WebSocket-Accept", accept)
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache, no-store")
            self.send_header("X-Accel-Buffering", "no")
            self.send_header("Connection", "close")
        self.end_headers()
        self.connection.settimeout(15)
        self.close_connection = True
        try:
            last = -1
            while True:
                with condition:
                    if last == sequence:
                        condition.wait(timeout=5)
                    payload = snapshot()
                    if last >= 0:
                        payload["delta"] = True
                        payload["events"] = [e for e in payload["events"] if e["id"] > last]
                        payload["chat"] = [e for e in payload["chat"] if e.get("id", 0) > last]
                        if time.monotonic() - last_full < 5:
                            payload.pop("research", None)
                        else:
                            last_full = time.monotonic()
                    else:
                        last_full = time.monotonic()
                    data = json.dumps(payload).encode()
                    last = sequence
                if ws:
                    size = len(data)
                    header = bytes([0x81, size]) if size < 126 else bytes([0x81, 126]) + struct.pack("!H", size) if size < 65536 else bytes([0x81, 127]) + struct.pack("!Q", size)
                    self.wfile.write(header + data)
                else:
                    self.wfile.write(b"id: " + str(last).encode() + b"\ndata: " + data + b"\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, TimeoutError, OSError):
            pass

class Ingest(Dashboard):
    def do_GET(self):
        self.plain(404, b'{}')
    def do_POST(self):
        self.close_connection = True
        # Tunnel targets public port 8796, never this private listener.
        if self.client_address[0] != "127.0.0.1" or self.headers.get("CF-Connecting-IP") or self.headers.get("X-Forwarded-For") or urlsplit(self.path).path != "/event":
            return self.plain(403, b'{}')
        try:
            n = int(self.headers.get("Content-Length", 0))
            if not 0 < n <= 65536:
                return self.plain(413, b'{}')
            self.connection.settimeout(1)
            item = json.loads(self.rfile.read(n))
            if not isinstance(item, dict) or not all(isinstance(item.get(k), str) for k in ("agent", "kind", "text", "time")):
                return self.plain(400, b'{}')
            ingest(item)
            self.plain(200, b'{"ok":true}')
        except (ValueError, OSError):
            self.plain(400, b'{}')

if __name__ == "__main__":
    private = ThreadingHTTPServer(("127.0.0.1", 8797), Ingest)
    threading.Thread(target=private.serve_forever, daemon=True).start()
    print("Read-only dashboard 127.0.0.1:8796; private ingest 127.0.0.1:8797", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8796), Dashboard).serve_forever()
