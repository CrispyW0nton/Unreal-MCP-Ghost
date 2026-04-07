#!/usr/bin/env python3
"""
Railway server — HTTP API that forwards commands to the UE5 UnrealMCP plugin
via a ngrok TCP tunnel.

Endpoints:
  GET  /              health check
  GET  /status        check if UE5 is reachable
  POST /cmd           run a single command  {"command": "...", "params": {...}}
  POST /run_tests     run the e2e test suite (optionally filter by group)
  GET  /list          list all available CLI commands

Environment variables (set in Railway dashboard):
  UNREAL_HOST   ngrok hostname  e.g.  0.tcp.ngrok.io
  UNREAL_PORT   ngrok port      e.g.  12345
  PORT          HTTP port Railway assigns (default 8080)
"""

import json
import os
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, Optional

# ── connection config ──────────────────────────────────────────────────────────
UNREAL_HOST = os.environ.get("UNREAL_HOST", "127.0.0.1")
UNREAL_PORT = int(os.environ.get("UNREAL_PORT", "55557"))
TIMEOUT = 20
HTTP_PORT = int(os.environ.get("PORT", "8080"))


# ── UE5 TCP helpers ────────────────────────────────────────────────────────────
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


def send_command(command: str, params: Dict[str, Any] = None) -> Dict:
    """Connect to UE5 via ngrok, send command, return response dict."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.connect((UNREAL_HOST, UNREAL_PORT))
    except ConnectionRefusedError:
        return {"status": "error", "error": f"Cannot reach UE5 at {UNREAL_HOST}:{UNREAL_PORT}"}
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


def check_status() -> Dict:
    """Quick ping to see if UE5 is reachable."""
    try:
        s = socket.socket()
        s.settimeout(3)
        r = s.connect_ex((UNREAL_HOST, UNREAL_PORT))
        s.close()
        if r == 0:
            return {"reachable": True, "host": UNREAL_HOST, "port": UNREAL_PORT}
        return {"reachable": False, "host": UNREAL_HOST, "port": UNREAL_PORT, "error": f"connect_ex={r}"}
    except Exception as e:
        return {"reachable": False, "host": UNREAL_HOST, "port": UNREAL_PORT, "error": str(e)}


# ── HTTP handler ───────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"[HTTP] {self.address_string()} {fmt % args}", flush=True)

    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> Optional[Dict]:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return None

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/" or path == "/health":
            self._send_json({
                "status": "ok",
                "service": "UnrealMCP Railway Bridge",
                "target": f"{UNREAL_HOST}:{UNREAL_PORT}"
            })

        elif path == "/status":
            self._send_json(check_status())

        elif path == "/list":
            # Run ue5cli.py --list and capture output
            try:
                result = subprocess.run(
                    [sys.executable, "/app/ue5cli.py",
                     "--host", UNREAL_HOST, "--port", str(UNREAL_PORT), "--list"],
                    capture_output=True, text=True, timeout=10
                )
                self._send_json({"output": result.stdout, "error": result.stderr})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)

        else:
            self._send_json({"error": f"Unknown endpoint: {path}"}, 404)

    def do_POST(self):
        path = self.path.split("?")[0]
        body = self._read_body()

        if body is None:
            self._send_json({"error": "Invalid JSON body"}, 400)
            return

        if path == "/cmd":
            # {"command": "get_actors_in_level", "params": {}}
            command = body.get("command")
            if not command:
                self._send_json({"error": "Missing 'command' field"}, 400)
                return
            params = body.get("params", {})
            result = send_command(command, params)
            status_code = 200 if result.get("status") != "error" else 502
            self._send_json(result, status_code)

        elif path == "/run_tests":
            # {"groups": ["connectivity", "level_query"]}  — omit for all groups
            groups = body.get("groups", [])
            args = [sys.executable, "/app/test_e2e.py"] + groups
            env = os.environ.copy()
            env["UNREAL_HOST"] = UNREAL_HOST
            env["UNREAL_PORT"] = str(UNREAL_PORT)
            try:
                result = subprocess.run(
                    args, capture_output=True, text=True,
                    timeout=300, env=env
                )
                self._send_json({
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "passed": result.returncode == 0
                })
            except subprocess.TimeoutExpired:
                self._send_json({"error": "Test suite timed out after 300s"}, 504)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)

        else:
            self._send_json({"error": f"Unknown endpoint: {path}"}, 404)


# ── main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"UnrealMCP Railway Bridge starting", flush=True)
    print(f"  HTTP port : {HTTP_PORT}", flush=True)
    print(f"  UE5 target: {UNREAL_HOST}:{UNREAL_PORT}", flush=True)
    httpd = HTTPServer(("0.0.0.0", HTTP_PORT), Handler)
    httpd.serve_forever()
