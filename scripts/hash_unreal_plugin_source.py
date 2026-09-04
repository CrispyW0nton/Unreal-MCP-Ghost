"""Emit the reproducible source fingerprint used by qualified UnrealMCP builds."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[1] / "unreal_mcp_server"
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from source_inventory import build_source_inventory  # noqa: E402


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--plugin-root",
        type=Path,
        required=True,
        help="UnrealMCP plugin directory containing UnrealMCP.uplugin and Source.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON manifest path. Parent directories are created.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = _arguments()
    inventory = build_source_inventory(arguments.plugin_root)
    encoded = json.dumps(inventory, indent=2, sort_keys=True) + "\n"
    if arguments.output is not None:
        output = arguments.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
