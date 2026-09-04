"""Send a model file to the Tripo UE Bridge WebSocket server.

The Tripo UE bridge listens on ws://127.0.0.1:60620 and expects each binary
file-transfer frame to contain a JSON header immediately followed by chunk
bytes. This helper keeps the transfer repeatable from the repo instead of
depending on the Tripo Studio "Send To" button.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import pathlib
import uuid

import websockets


DEFAULT_URI = "ws://127.0.0.1:60620"
CHUNK_SIZE = 5 * 1024 * 1024


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


async def _recv_json(ws, timeout: float) -> dict | None:
    message = await asyncio.wait_for(ws.recv(), timeout=timeout)
    if isinstance(message, bytes):
        message = message.decode("utf-8", errors="replace")
    try:
        return json.loads(message)
    except json.JSONDecodeError:
        return {"type": "unparseable", "raw": str(message)}


async def send_asset(path: pathlib.Path, uri: str, timeout: float) -> dict:
    data = path.read_bytes()
    file_id = str(uuid.uuid4())
    file_type = path.suffix.lstrip(".").lower()
    chunk_total = max(1, math.ceil(len(data) / CHUNK_SIZE))

    result: dict = {
        "success": False,
        "uri": uri,
        "file": str(path),
        "file_id": file_id,
        "file_name": path.name,
        "file_type": file_type,
        "size_bytes": len(data),
        "chunk_total": chunk_total,
        "responses": [],
        "acks": [],
        "import_complete": None,
    }

    async with websockets.connect(uri, max_size=None) as ws:
        handshake = {
            "type": "handshake",
            "payload": {
                "clientName": "Unreal-MCP-Ghost Tripo Sender",
                "protocolVersion": "1.0.0",
            },
        }
        await ws.send(_json_bytes(handshake).decode("utf-8"))
        response = await _recv_json(ws, timeout)
        result["responses"].append(response)

        for chunk_index in range(chunk_total):
            start = chunk_index * CHUNK_SIZE
            chunk = data[start : start + CHUNK_SIZE]
            header = {
                "type": "file_transfer",
                "payload": {
                    "fileId": file_id,
                    "fileName": path.name,
                    "fileType": file_type,
                    "chunkIndex": chunk_index,
                    "chunkTotal": chunk_total,
                    "chunkSize": len(chunk),
                },
            }
            await ws.send(_json_bytes(header) + chunk)
            ack = await _recv_json(ws, timeout)
            result["acks"].append(ack)

        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            remaining = max(0.1, deadline - asyncio.get_running_loop().time())
            response = await _recv_json(ws, remaining)
            result["responses"].append(response)
            if response and response.get("type") == "import_complete":
                result["import_complete"] = response
                payload = response.get("payload") or {}
                result["success"] = bool(payload.get("success"))
                break

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="Model file to send, e.g. a Tripo GLB")
    parser.add_argument("--uri", default=os.environ.get("TRIPO_BRIDGE_URI", DEFAULT_URI))
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args()

    path = pathlib.Path(args.file)
    if not path.exists():
        print(json.dumps({"success": False, "error": f"File not found: {path}"}))
        return 2

    try:
        result = asyncio.run(send_asset(path, args.uri, args.timeout))
    except Exception as exc:  # pragma: no cover - CLI diagnostic path
        print(json.dumps({"success": False, "error": str(exc), "file": str(path)}))
        return 1

    print(json.dumps(result, indent=2))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
