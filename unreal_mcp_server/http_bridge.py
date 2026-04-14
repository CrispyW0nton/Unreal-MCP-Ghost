from __future__ import annotations

from typing import Any, Dict, Optional

import httpx


class HTTPBridgeConnection:
    """Ghost backend that talks to a UE-side HTTP bridge server."""

    def __init__(self, bridge_url: str, timeout: float = 150.0) -> None:
        self.bridge_url = bridge_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)
        self.connected = False

    def connect(self) -> bool:
        try:
            response = self.client.get(f"{self.bridge_url}/ping")
            response.raise_for_status()
            self.connected = response.json().get("status") == "ok"
            return self.connected
        except Exception:
            self.connected = False
            return False

    def disconnect(self) -> None:
        self.connected = False
        self.client.close()

    def send_command(self, command: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        if command == "ping":
            if self.connect():
                return {"success": True, "status": "success", "result": "pong", "output": "pong"}
            return {
                "success": False,
                "status": "error",
                "error": f"Cannot reach UE bridge at {self.bridge_url}",
                "message": f"Cannot reach UE bridge at {self.bridge_url}",
            }

        if command == "exec_python":
            return self._send_exec_python(params or {})

        return self._send_structured_command(command, params or {})

    def _send_exec_python(self, params: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "command": params.get("code", ""),
            "exec_mode": self._normalize_exec_mode(params.get("mode")),
            "unattended": bool(params.get("unattended", True)),
        }
        try:
            response = self.client.post(f"{self.bridge_url}/execute_python", json=payload)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            return {
                "success": False,
                "status": "error",
                "error": str(exc),
                "message": str(exc),
            }

        output_lines = [entry.get("output", "") for entry in data.get("output", []) if entry.get("output")]
        if data.get("result") not in (None, ""):
            output_lines.append(f"Return: {data['result']}")

        result = {
            "success": bool(data.get("success", False) and not data.get("error")),
            "status": "success" if data.get("success", False) and not data.get("error") else "error",
            "output": "\n".join(output_lines).strip(),
            "result": data.get("result"),
        }
        if data.get("error"):
            result["error"] = data["error"]
            result["message"] = data["error"]
        return result

    def _send_structured_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = self.client.post(
                f"{self.bridge_url}/ghost_command",
                json={"type": command, "params": params},
            )
            response.raise_for_status()
            return self._normalize_structured_response(response.json())
        except Exception as exc:
            return {
                "success": False,
                "status": "error",
                "error": str(exc),
                "message": str(exc),
            }

    def _normalize_structured_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if data.get("status") == "error":
            error_message = data.get("error") or data.get("message") or "Unknown bridge error"
            return {
                "success": False,
                "status": "error",
                "error": error_message,
                "message": error_message,
            }

        if data.get("status") == "success" and "result" in data:
            result = data["result"]
            if isinstance(result, dict):
                return result
            return {"success": True, "result": result}

        if data.get("success") is False:
            error_message = data.get("error") or data.get("message") or "Unknown bridge error"
            return {
                "success": False,
                "status": "error",
                "error": error_message,
                "message": error_message,
            }

        return data

    def _normalize_exec_mode(self, mode: Any) -> str:
        normalized = str(mode or "ExecuteStatement").strip().lower()
        if normalized in {"executefile", "execute_file"}:
            return "ExecuteFile"
        if normalized in {"evaluatestatement", "evaluate_statement", "eval"}:
            return "EvaluateStatement"
        return "ExecuteStatement"