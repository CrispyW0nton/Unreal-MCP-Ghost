#!/usr/bin/env python3
"""
proxy.py — Tiny HTTP wrapper around the UnrealMCP TCP plugin.

Run this ON YOUR MACHINE alongside UE5:
    python proxy.py

It listens on HTTP port 8080 (localhost) and forwards requests to the
UnrealMCP TCP plugin on 127.0.0.1:55557.

Then expose port 8080 for free via localhost.run:
    ssh -R 80:localhost:8080 nokey@localhost.run

Endpoints:
    POST /cmd          {"command": "...", "params": {...}}
    GET  /status       check UE5 is reachable
    GET  /             health check
"""

import json
import os
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict

UNREAL_HOST = os.environ.get("UNREAL_HOST", "127.0.0.1")
UNREAL_PORT = int(os.environ.get("UNREAL_PORT", "55557"))
PROXY_PORT  = int(os.environ.get("PROXY_PORT", "8080"))
TIMEOUT     = 20


def _recv(sock: socket.socket) -> bytes:
    chunks = []
    sock.settimeout(TIMEOUT)
    while True:
        try:
            chunk = sock.recv(8192)
        except socket.timeout:
            break
        if not chunk:
            break
        chunks.append(chunk)
        data = b"".join(chunks)
        try:
            json.loads(data.decode("utf-8"))
            return data
        except json.JSONDecodeError:
            continue
    return b"".join(chunks)


def send_ue5(command: str, params: Dict[str, Any] = None) -> Dict:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.connect((UNREAL_HOST, UNREAL_PORT))
    except ConnectionRefusedError:
        return {"status": "error", "error": f"UE5 not reachable at {UNREAL_HOST}:{UNREAL_PORT}"}
    except Exception as e:
        return {"status": "error", "error": f"Connection failed: {e}"}
    try:
        payload = json.dumps({"type": command, "params": params or {}})
        sock.sendall(payload.encode("utf-8"))
        raw = _recv(sock)
        return json.loads(raw.decode("utf-8"))
    except Exception as e:
        return {"status": "error", "error": f"Communication error: {e}"}
    finally:
        try:
            sock.close()
        except Exception:
            pass


class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"[proxy] {fmt % args}", flush=True)

    def _json(self, data: Any, status: int = 200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> Dict:
        n = int(self.headers.get("Content-Length", 0))
        if n == 0:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/health"):
            self._json({"status": "ok", "ue5": f"{UNREAL_HOST}:{UNREAL_PORT}"})
        elif path == "/status":
            try:
                s = socket.socket()
                s.settimeout(3)
                r = s.connect_ex((UNREAL_HOST, UNREAL_PORT))
                s.close()
                self._json({"reachable": r == 0, "host": UNREAL_HOST, "port": UNREAL_PORT})
            except Exception as e:
                self._json({"reachable": False, "error": str(e)})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        path = self.path.split("?")[0]
        body = self._body()
        if path == "/cmd":
            command = body.get("command")
            if not command:
                self._json({"error": "missing 'command'"}, 400)
                return
            result = send_ue5(command, body.get("params", {}))
            self._json(result, 200 if result.get("status") != "error" else 502)
        else:
            self._json({"error": "not found"}, 404)


if __name__ == "__main__":
    print(f"UnrealMCP HTTP proxy starting on port {PROXY_PORT}", flush=True)
    print(f"Forwarding to UE5 at {UNREAL_HOST}:{UNREAL_PORT}", flush=True)
    print(f"", flush=True)
    print(f"Now run this in another terminal to expose it for free:", flush=True)
    print(f"  ssh -R 80:localhost:{PROXY_PORT} nokey@localhost.run", flush=True)
    print(f"", flush=True)
    HTTPServer(("127.0.0.1", PROXY_PORT), Handler).serve_forever()
