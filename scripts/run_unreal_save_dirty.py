from __future__ import annotations

import json
import os
import sys
from pathlib import Path


os.environ.setdefault("UNREAL_PORT", "55655")

ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = ROOT / "unreal_mcp_server"
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

import unreal_mcp_server as server  # noqa: E402


SAVE_CODE = r'''
import json
import unreal

result = {"success": True, "saved": False, "errors": []}
try:
    result["saved"] = bool(unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True))
except Exception as exc:
    result["success"] = False
    result["errors"].append(str(exc))
print(json.dumps(result))
'''


def main() -> int:
    connection = server.get_unreal_connection()
    if connection is None:
        print(json.dumps({"success": False, "error": "Not connected to Unreal Engine."}, indent=2))
        return 1
    response = connection.send_command("exec_python", {"code": SAVE_CODE}) or {}
    output = response.get("output", "")
    if "[Info]" in output:
        output = output.rsplit("[Info]", 1)[-1].strip()
    try:
        report = json.loads(output)
    except Exception:
        report = {"success": False, "error": "Could not parse save output.", "raw": response}
    print(json.dumps(report, indent=2))
    return 0 if report.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
