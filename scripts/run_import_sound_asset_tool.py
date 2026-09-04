from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path


os.environ.setdefault("UNREAL_PORT", "55655")

ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = ROOT / "unreal_mcp_server"
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from tools.audio_tools import register_audio_tools  # noqa: E402


class ToolRegistry:
    def __init__(self) -> None:
        self.tools = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


async def run() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--cue", action="store_true")
    args = parser.parse_args()

    registry = ToolRegistry()
    register_audio_tools(registry)
    result = await registry.tools["import_sound_asset"](
        ctx=None,
        file_path=str(Path(args.file).resolve()),
        destination_path=args.destination,
        auto_create_cue=bool(args.cue),
    )
    print(result if isinstance(result, str) else json.dumps(result, indent=2))
    try:
        parsed = json.loads(result) if isinstance(result, str) else result
    except Exception:
        parsed = {}
    return 0 if parsed.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
