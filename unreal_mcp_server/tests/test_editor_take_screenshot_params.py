"""Coverage for the editor screenshot wrapper's native bridge parameter names."""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))


class _MockMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn
        return decorator


class _ScreenshotConnection:
    def __init__(self):
        self.calls = []

    def send_command(self, command, params):
        self.calls.append((command, params))
        return {"status": "success", "result": {"filepath": params.get("filepath")}}


class _PatchServerModule:
    def __init__(self, connection):
        self.fake = types.ModuleType("unreal_mcp_server")
        self.fake.get_unreal_connection = lambda: connection
        self.previous = None

    def __enter__(self):
        self.previous = sys.modules.get("unreal_mcp_server")
        sys.modules["unreal_mcp_server"] = self.fake

    def __exit__(self, exc_type, exc, tb):
        if self.previous is None:
            sys.modules.pop("unreal_mcp_server", None)
        else:
            sys.modules["unreal_mcp_server"] = self.previous


class TestEditorTakeScreenshotParams(unittest.TestCase):
    def test_screenshot_sends_filepath_for_native_bridge(self):
        from tools.editor_tools import register_editor_tools

        mcp = _MockMCP()
        register_editor_tools(mcp)
        connection = _ScreenshotConnection()

        with _PatchServerModule(connection):
            result = mcp.tools["take_screenshot"](
                ctx=None,
                filename="C:/tmp/shot.png",
                show_ui=False,
                resolution=[800, 450],
            )

        self.assertEqual(result["status"], "success")
        command, params = connection.calls[0]
        self.assertEqual(command, "take_screenshot")
        self.assertEqual(params["filename"], "C:/tmp/shot.png")
        self.assertEqual(params["filepath"], "C:/tmp/shot.png")
        self.assertEqual(params["resolution"], [800, 450])


if __name__ == "__main__":
    unittest.main()
