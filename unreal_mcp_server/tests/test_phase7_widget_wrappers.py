"""Offline coverage for Phase 7 Slice 5 bridge wrapper exposure."""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVER_ROOT.parent
UMG_COMMANDS = REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCP" / "Private" / "Commands" / "UnrealMCPUMGCommands.cpp"
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


class _MockUnrealConnection:
    def __init__(self):
        self.calls = []

    def send_command(self, command, params):
        self.calls.append((command, params))
        return {"success": True, "command": command, "params": params}


class _FakeServerModule:
    def __init__(self, connection):
        self.connection = connection

    def get_unreal_connection(self):
        return self.connection


class _PatchServerModule:
    def __init__(self, connection):
        self.fake = types.ModuleType("unreal_mcp_server")
        self.fake.get_unreal_connection = _FakeServerModule(connection).get_unreal_connection
        self.previous = None

    def __enter__(self):
        self.previous = sys.modules.get("unreal_mcp_server")
        sys.modules["unreal_mcp_server"] = self.fake

    def __exit__(self, exc_type, exc, tb):
        if self.previous is None:
            sys.modules.pop("unreal_mcp_server", None)
        else:
            sys.modules["unreal_mcp_server"] = self.previous


class TestPhase7WidgetWrappers(unittest.TestCase):
    def test_ping_unreal_wraps_native_ping_route(self):
        from tools.editor_tools import register_editor_tools

        mcp = _MockMCP()
        register_editor_tools(mcp)
        connection = _MockUnrealConnection()

        with _PatchServerModule(connection):
            result = mcp.tools["ping_unreal"](ctx=None)

        self.assertTrue(result["success"])
        self.assertEqual(connection.calls, [("ping", {})])

    def test_widget_tree_tools_wrap_native_widget_routes(self):
        from tools.widget_tools import register_widget_tools

        mcp = _MockMCP()
        register_widget_tools(mcp)
        connection = _MockUnrealConnection()

        with _PatchServerModule(connection):
            mcp.tools["widget_add_child"](
                ctx=None,
                widget_blueprint_path="/Game/UI/WBP_Test",
                child_class="TextBlock",
                child_name="TitleText",
                parent_name="RootCanvas",
            )
            mcp.tools["widget_set_property"](
                ctx=None,
                widget_blueprint_path="/Game/UI/WBP_Test",
                widget_name="TitleText",
                property_name="Text",
                property_value="Hello",
            )
            mcp.tools["widget_set_anchor"](
                ctx=None,
                widget_blueprint_path="/Game/UI/WBP_Test",
                widget_name="TitleText",
                anchor_min_x=0.0,
                anchor_min_y=0.0,
                anchor_max_x=1.0,
                anchor_max_y=0.0,
                position_x=20.0,
                position_y=30.0,
                size_x=320.0,
                size_y=48.0,
            )
            mcp.tools["widget_get_children"](
                ctx=None,
                widget_blueprint_path="/Game/UI/WBP_Test",
                parent_name="RootCanvas",
            )

        commands = [command for command, _params in connection.calls]
        self.assertEqual(
            commands,
            ["widget_add_child", "widget_set_property", "widget_set_anchor", "widget_get_children"],
        )
        self.assertEqual(connection.calls[0][1]["parent_name"], "RootCanvas")
        self.assertEqual(connection.calls[1][1]["property_value"], "Hello")
        self.assertEqual(connection.calls[2][1]["size_x"], 320.0)
        self.assertEqual(connection.calls[3][1]["parent_name"], "RootCanvas")

    def test_image_brush_size_uses_ue56_desired_size_override(self):
        cpp = UMG_COMMANDS.read_text(encoding="utf-8")

        self.assertIn('PropertyName.Equals(TEXT("BrushSize"), ESearchCase::IgnoreCase)', cpp)
        self.assertIn("Image->SetDesiredSizeOverride(ParseVector2D(PropertyValue));", cpp)
        self.assertNotIn("Image->SetBrushSize", cpp)


if __name__ == "__main__":
    unittest.main()
