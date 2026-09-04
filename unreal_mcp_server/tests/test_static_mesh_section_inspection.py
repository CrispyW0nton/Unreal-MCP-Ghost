"""Contract coverage for bounded read-only static-mesh section inspection."""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVER_ROOT.parent
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


class _Connection:
    def __init__(self):
        self.calls = []

    def send_command(self, command, params):
        self.calls.append((command, params))
        return {
            "status": "success",
            "result": {
                "success": True,
                "schema": "unreal-mcp/static-mesh-section-snapshot/v1",
                "read_only": True,
                "engine_version": "5.6.1-44394996+++UE5+Release-5.6",
                "asset_path": params["asset_path"],
                "object_path": f'{params["asset_path"]}.SM_Test',
                "lod_index": params["lod_index"],
                "source_model_count": 1,
                "vertex_count": 3,
                "vertex_instance_count": 3,
                "polygon_count": 1,
                "triangle_count": 1,
                "uv_channel_count": 1,
                "lightmap_coordinate_index": 0,
                "render_data_available": False,
                "package_dirty_before": False,
                "package_dirty_after": False,
                "static_materials": [],
                "polygon_groups": [],
                "render_sections": [],
            },
        }


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


class TestStaticMeshSectionInspection(unittest.TestCase):
    def setUp(self):
        from tools.editor_tools import register_editor_tools

        self.mcp = _MockMCP()
        register_editor_tools(self.mcp)
        self.connection = _Connection()

    def test_routes_fixed_read_only_arguments_to_native_bridge(self):
        with _PatchServerModule(self.connection):
            result = self.mcp.tools["inspect_static_mesh_sections"](
                ctx=None,
                asset_path="/Game/LevelPrototyping/KotorModels/m13aa_05a",
                lod_index=0,
                max_sections=64,
            )

        self.assertTrue(result.success)
        self.assertEqual(result.asset_path, "/Game/LevelPrototyping/KotorModels/m13aa_05a")
        self.assertEqual(
            self.connection.calls,
            [
                (
                    "inspect_static_mesh_sections",
                    {
                        "asset_path": "/Game/LevelPrototyping/KotorModels/m13aa_05a",
                        "lod_index": 0,
                        "max_sections": 64,
                    },
                )
            ],
        )

    def test_rejects_non_project_asset_paths_before_bridge_dispatch(self):
        with _PatchServerModule(self.connection):
            result = self.mcp.tools["inspect_static_mesh_sections"](
                ctx=None,
                asset_path="C:/temp/mesh.fbx",
            )

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "ERR_INVALID_ASSET_PATH")
        self.assertEqual(self.connection.calls, [])

    def test_rejects_out_of_range_budgets_before_bridge_dispatch(self):
        with _PatchServerModule(self.connection):
            bad_lod = self.mcp.tools["inspect_static_mesh_sections"](
                ctx=None,
                asset_path="/Game/Meshes/SM_Test",
                lod_index=8,
            )
            bad_limit = self.mcp.tools["inspect_static_mesh_sections"](
                ctx=None,
                asset_path="/Game/Meshes/SM_Test",
                max_sections=0,
            )

        self.assertFalse(bad_lod.success)
        self.assertFalse(bad_limit.success)
        self.assertEqual(self.connection.calls, [])

    def test_cpp_bridge_declares_direct_read_only_mesh_description_route(self):
        editor_cpp = (
            REPO_ROOT
            / "unreal_plugin"
            / "Source"
            / "UnrealMCP"
            / "Private"
            / "Commands"
            / "UnrealMCPEditorCommands.cpp"
        ).read_text(encoding="utf-8")
        bridge_cpp = (
            REPO_ROOT
            / "unreal_plugin"
            / "Source"
            / "UnrealMCP"
            / "Private"
            / "UnrealMCPBridge.cpp"
        ).read_text(encoding="utf-8")
        build_rules = (
            REPO_ROOT
            / "unreal_plugin"
            / "Source"
            / "UnrealMCP"
            / "UnrealMCP.Build.cs"
        ).read_text(encoding="utf-8")

        self.assertIn('CommandType == TEXT("inspect_static_mesh_sections")', editor_cpp)
        self.assertIn("HandleInspectStaticMeshSections", editor_cpp)
        self.assertIn("GetMeshDescription", editor_cpp)
        self.assertIn("GetPolygonGroupMaterialSlotNames", editor_cpp)
        self.assertIn('CommandType == TEXT("inspect_static_mesh_sections")', bridge_cpp)
        self.assertIn("bReadOnlyQualificationCommand", bridge_cpp)
        self.assertIn('CommandType == TEXT("ping")', bridge_cpp)
        self.assertIn('TEXT("approved_source_sha256")', bridge_cpp)
        self.assertIn('TEXT("loaded_plugin_binary_path")', bridge_cpp)
        self.assertIn("MCPSTUDIO_UNREAL_SOURCE_SHA256", build_rules)
        self.assertIn("unqualified", build_rules)


if __name__ == "__main__":
    unittest.main()
