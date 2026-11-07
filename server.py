#!/usr/bin/env python3
"""Read-only static server for the local floor. No trading endpoints."""
from __future__ import annotations

import http.server
import socketserver
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORT = 8795


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


def main():
    with Server(("127.0.0.1", PORT), Handler) as httpd:
        print(f"Trenchfloor http://127.0.0.1:{PORT}  (paper research only)", flush=True)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
