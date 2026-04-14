from __future__ import annotations

import json
import logging
import socket
import struct
import time
import uuid
from dataclasses import dataclass
from typing import Any, Optional

log = logging.getLogger("UnrealMCP.NativeRemote")

_MAGIC = "ureremotexec"
_VERSION = 1

_MCAST_GROUP = "239.0.0.1"
_MCAST_PORT = 6766
_MCAST_TTL = 1


class ExecMode:
    EXECUTE_FILE = "ExecuteFile"
    EXECUTE_STATEMENT = "ExecuteStatement"
    EVALUATE_STATEMENT = "EvaluateStatement"


@dataclass
class ExecResult:
    success: bool
    return_value: Any
    output: list[dict[str, Any]]
    error: Optional[str] = None


def _recv_exactly(sock: socket.socket, size: int) -> bytes:
    buffer = bytearray()
    while len(buffer) < size:
        chunk = sock.recv(size - len(buffer))
        if not chunk:
            raise ConnectionError("Remote execution socket closed unexpectedly")
        buffer.extend(chunk)
    return bytes(buffer)


def _read_message(sock: socket.socket) -> dict[str, Any]:
    payload_size = struct.unpack(">I", _recv_exactly(sock, 4))[0]
    payload = _recv_exactly(sock, payload_size)
    return json.loads(payload.decode("utf-8"))


def _encode_message(message: dict[str, Any]) -> bytes:
    payload = json.dumps(message).encode("utf-8")
    return struct.pack(">I", len(payload)) + payload


def _make_message(
    message_type: str,
    data: dict[str, Any],
    source_id: str,
    dest_id: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "version": _VERSION,
        "magic": _MAGIC,
        "source": source_id,
        "dest": dest_id,
        "type": message_type,
        "data": data,
    }


class NativeRemoteExecutionClient:
    """Minimal UE Python Remote Execution client."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        discovery_timeout: float = 5.0,
        command_timeout: float = 60.0,
    ) -> None:
        self.host = host
        self.port = port
        self.discovery_timeout = discovery_timeout
        self.command_timeout = command_timeout
        self.node_id = str(uuid.uuid4())

    def run(
        self,
        code: str,
        exec_mode: str = ExecMode.EXECUTE_STATEMENT,
        unattended: bool = True,
    ) -> ExecResult:
        host, port, ue_node_id = self._resolve_endpoint()
        return self._send_exec(host, port, ue_node_id, code, exec_mode, unattended)

    def _resolve_endpoint(self) -> tuple[str, int, Optional[str]]:
        if self.host is not None and self.port is not None:
            return self.host, self.port, None
        return self._discover_endpoint()

    def _discover_endpoint(self) -> tuple[str, int, str]:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, _MCAST_TTL)
            sock.settimeout(self.discovery_timeout)
            sock.bind(("", _MCAST_PORT))
            membership = struct.pack("4sL", socket.inet_aton(_MCAST_GROUP), socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)

            message = _make_message(
                "open_connection",
                {"command_ip": "0.0.0.0", "command_port": 0},
                source_id=self.node_id,
            )
            sock.sendto(json.dumps(message).encode("utf-8"), (_MCAST_GROUP, _MCAST_PORT))

            deadline = time.monotonic() + self.discovery_timeout
            while time.monotonic() < deadline:
                try:
                    data, addr = sock.recvfrom(65536)
                except socket.timeout:
                    break

                try:
                    reply = json.loads(data.decode("utf-8"))
                except json.JSONDecodeError:
                    continue

                if reply.get("magic") != _MAGIC:
                    continue
                if reply.get("type") not in {"pong", "node", "open_connection"}:
                    continue
                if reply.get("source") == self.node_id:
                    continue

                payload = reply.get("data", {})
                command_port = payload.get("command_port") or payload.get("port")
                command_host = payload.get("command_ip") or addr[0]
                ue_node_id = reply.get("source")
                if command_port and ue_node_id:
                    return command_host, int(command_port), ue_node_id
        finally:
            sock.close()

        raise ConnectionError(
            "No UE5 Python Remote Execution endpoint was discovered. Enable the UE5 "
            "Python Script Plugin and Remote Python Execution in Project Settings, or "
            "pass --unreal-port to connect directly."
        )

    def _send_exec(
        self,
        host: str,
        port: int,
        ue_node_id: Optional[str],
        code: str,
        exec_mode: str,
        unattended: bool,
    ) -> ExecResult:
        try:
            sock = socket.create_connection((host, port), timeout=self.command_timeout)
        except OSError as exc:
            return ExecResult(
                success=False,
                return_value=None,
                output=[],
                error=f"Cannot connect to UE Python Remote Execution at {host}:{port}: {exc}",
            )

        try:
            sock.settimeout(self.command_timeout)
            message = _make_message(
                "exec",
                {
                    "command": code,
                    "exec_mode": exec_mode,
                    "unattended": unattended,
                },
                source_id=self.node_id,
                dest_id=ue_node_id,
            )
            sock.sendall(_encode_message(message))
            reply = _read_message(sock)
            if reply.get("type") != "exec_result":
                return ExecResult(
                    success=False,
                    return_value=None,
                    output=[],
                    error=f"Unexpected UE remote reply type: {reply.get('type')}",
                )

            payload = reply.get("data", {})
            return ExecResult(
                success=bool(payload.get("success", False)),
                return_value=payload.get("result"),
                output=payload.get("output", []),
            )
        except Exception as exc:
            return ExecResult(
                success=False,
                return_value=None,
                output=[],
                error=f"UE Python Remote Execution failed: {exc}",
            )
        finally:
            try:
                sock.close()
            except OSError:
                pass