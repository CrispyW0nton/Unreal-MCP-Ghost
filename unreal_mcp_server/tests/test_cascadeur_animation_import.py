"""Contract tests for the Cascadeur animation-only FBX handoff."""

import asyncio
import json
from unittest.mock import patch

from mcp.server.fastmcp import FastMCP

from tools.asset_import_tools import register_asset_import_tools


def _registered_tools():
    mcp = FastMCP("cascadeur_animation_import_test")
    register_asset_import_tools(mcp)
    return {tool.name: tool.fn for tool in mcp._tool_manager.list_tools()}


def test_animation_only_import_is_registered():
    assert "import_animation_fbx" in _registered_tools()


def test_animation_only_import_rejects_invalid_length_before_unreal():
    result = asyncio.run(
        _registered_tools()["import_animation_fbx"](
            ctx=None,
            file_path="C:/Proof/animation.fbx",
            skeleton="/Game/Characters/Skeletons/SK_Test_Skeleton",
            animation_length="entire_timeline",
        )
    )
    parsed = json.loads(result)
    assert parsed["success"] is False
    assert parsed["stage"] == "import_animation_fbx"
    assert "exported_time" in parsed["errors"][0]


def test_animation_only_import_rejects_non_game_destination():
    result = asyncio.run(
        _registered_tools()["import_animation_fbx"](
            ctx=None,
            file_path="C:/Proof/animation.fbx",
            skeleton="/Game/Characters/Skeletons/SK_Test_Skeleton",
            destination_path="/Engine/EditorMeshes",
        )
    )
    parsed = json.loads(result)
    assert parsed["success"] is False
    assert parsed["stage"] == "import_animation_fbx"
    assert parsed["errors"] == ["destination_path must be inside /Game"]


def test_animation_only_import_builds_non_destructive_unreal_command():
    captured = {}

    def fake_substrate(code, stage):
        captured["code"] = code
        captured["stage"] = stage
        return {
            "success": True,
            "stage": stage,
            "message": "captured",
            "outputs": {},
            "warnings": [],
            "errors": [],
            "log_tail": [],
        }

    with patch("tools.asset_import_tools._get_substrate", return_value=fake_substrate):
        result = asyncio.run(
            _registered_tools()["import_animation_fbx"](
                ctx=None,
                file_path="C:/Proof/cascadeur-animation.fbx",
                skeleton="/Game/Characters/Skeletons/SK_Test_Skeleton",
                destination_path="/Game/MCPStudio/Validation/Cascadeur",
            )
        )

    assert json.loads(result)["success"] is True
    assert captured["stage"] == "import_animation_fbx"
    assert 'set_editor_property("import_mesh", False)' in captured["code"]
    assert 'set_editor_property("import_animations", True)' in captured["code"]
    assert 'set_editor_property("import_materials", False)' in captured["code"]
    assert 'set_editor_property("import_textures", False)' in captured["code"]
    assert "task.replace_existing = replace_existing" in captured["code"]
    assert 'isinstance(asset, unreal.AnimSequence)' in captured["code"]
