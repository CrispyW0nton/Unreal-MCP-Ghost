"""Offline tests for Phase 7 bridge command metadata auditing."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVER_ROOT.parent
UMG_COMMANDS_CPP = (
    REPO_ROOT
    / "unreal_plugin"
    / "Source"
    / "UnrealMCP"
    / "Private"
    / "Commands"
    / "UnrealMCPUMGCommands.cpp"
)
PLUGIN_SOURCE = REPO_ROOT / "unreal_plugin" / "Source"
PLUGIN_DESCRIPTOR = REPO_ROOT / "unreal_plugin" / "UnrealMCP.uplugin"
PLUGIN_BUILD_CS = REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCP" / "UnrealMCP.Build.cs"


def _load_audit_module():
    spec = importlib.util.spec_from_file_location(
        "bridge_command_audit",
        REPO_ROOT / "scripts" / "bridge_command_audit.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TestPhase7BridgeCommandAudit(unittest.TestCase):
    def test_plugin_does_not_enable_deprecated_structutils_plugin(self):
        descriptor = json.loads(PLUGIN_DESCRIPTOR.read_text(encoding="utf-8"))
        enabled_plugins = {entry["Name"] for entry in descriptor.get("Plugins", [])}
        build_rules = PLUGIN_BUILD_CS.read_text(encoding="utf-8")

        self.assertNotIn("StructUtils", enabled_plugins)
        self.assertNotIn('"StructUtils",', build_rules)

    def test_plugin_headers_do_not_use_monolithic_json_include(self):
        offenders = []
        for header in PLUGIN_SOURCE.rglob("*.h"):
            source = header.read_text(encoding="utf-8")
            if '#include "Json.h"' in source or "#include <Json.h>" in source:
                offenders.append(str(header.relative_to(REPO_ROOT)).replace("\\", "/"))

        self.assertEqual([], offenders)

    def test_umg_image_brush_size_uses_current_desired_size_api(self):
        source = UMG_COMMANDS_CPP.read_text(encoding="utf-8")

        self.assertIn("SetDesiredSizeOverride(ParseVector2D(PropertyValue))", source)
        self.assertNotIn("SetBrushSize(", source)

    def test_registry_reports_python_and_cpp_commands(self):
        audit = _load_audit_module()

        registry = audit.build_registry()

        self.assertEqual(registry["schema"], "unreal_mcp_bridge_command_registry.v1")
        self.assertEqual(registry["source_scope"], "git_tracked_worktree")
        self.assertGreaterEqual(registry["counts"]["python_referenced"], 250)
        self.assertGreaterEqual(registry["counts"]["cpp_routed"], 250)
        commands = {entry["command"]: entry for entry in registry["commands"]}
        self.assertIn("create_blueprint", commands)
        self.assertIn("exec_python", commands)
        self.assertGreater(commands["create_blueprint"]["python_references"], 0)
        self.assertGreater(commands["create_blueprint"]["cpp_routes"], 0)
        commands = {entry["command"]: entry for entry in registry["commands"]}
        self.assertGreater(commands["set_behavior_tree_blackboard"]["python_references"], 0)
        self.assertGreater(commands["bt_get_info"]["python_references"], 0)
        self.assertGreater(commands["set_blueprint_parent_class"]["python_references"], 0)
        self.assertGreater(commands["add_construction_script_node"]["python_references"], 0)
        self.assertGreater(commands["add_arithmetic_operator_node"]["python_references"], 0)
        self.assertGreater(commands["add_relational_operator_node"]["python_references"], 0)
        self.assertGreater(commands["add_blueprint_function_with_pins"]["python_references"], 0)
        self.assertGreater(commands["set_spawn_actor_class"]["python_references"], 0)
        self.assertGreater(commands["add_sequence_player_node"]["python_references"], 0)
        self.assertGreater(commands["connect_anim_graph_nodes"]["python_references"], 0)
        self.assertGreater(commands["add_niagara_component"]["python_references"], 0)
        self.assertGreater(commands["add_get_random_reachable_point_node"]["python_references"], 0)
        self.assertGreater(commands["add_finish_execute_node"]["python_references"], 0)
        self.assertGreater(commands["add_clear_blackboard_value_node"]["python_references"], 0)
        self.assertGreater(commands["add_map_variable"]["python_references"], 0)
        self.assertGreater(commands["add_open_level_node"]["python_references"], 0)
        self.assertGreater(commands["reconstruct_blueprint_node"]["python_references"], 0)
        self.assertGreater(commands["add_custom_event"]["python_references"], 0)
        self.assertGreater(commands["call_custom_event"]["python_references"], 0)
        self.assertGreater(commands["add_interface_event_node"]["python_references"], 0)
        self.assertGreater(commands["rename_blueprint_comment_node"]["python_references"], 0)
        self.assertGreater(commands["set_pawn_properties"]["python_references"], 0)
        self.assertGreater(commands["bind_widget_component_event"]["python_references"], 0)
        review = {entry["command"]: entry for entry in registry["cpp_unreferenced_review"]}
        self.assertNotIn("set_behavior_tree_blackboard", review)
        self.assertNotIn("bt_get_info", review)
        self.assertNotIn("set_blueprint_parent_class", review)
        self.assertNotIn("add_construction_script_node", review)
        self.assertNotIn("add_arithmetic_operator_node", review)
        self.assertNotIn("add_relational_operator_node", review)
        self.assertNotIn("add_blueprint_function_with_pins", review)
        self.assertNotIn("set_spawn_actor_class", review)
        self.assertNotIn("add_sequence_player_node", review)
        self.assertNotIn("connect_anim_graph_nodes", review)
        self.assertNotIn("add_niagara_component", review)
        self.assertNotIn("add_get_random_reachable_point_node", review)
        self.assertNotIn("add_finish_execute_node", review)
        self.assertNotIn("add_clear_blackboard_value_node", review)
        self.assertNotIn("add_map_variable", review)
        self.assertNotIn("add_open_level_node", review)
        self.assertNotIn("reconstruct_blueprint_node", review)
        self.assertNotIn("add_custom_event", review)
        self.assertNotIn("call_custom_event", review)
        self.assertNotIn("add_interface_event_node", review)
        self.assertNotIn("rename_blueprint_comment_node", review)
        self.assertNotIn("set_pawn_properties", review)
        self.assertNotIn("bind_widget_component_event", review)

    def test_registry_snapshot_comparison_is_stable_after_write(self):
        audit = _load_audit_module()
        registry = audit.build_registry()

        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            registry_path = Path(tmp) / "bridge_command_registry.json"
            audit.write_registry(registry, registry_path)
            recorded = audit.load_registry(registry_path)
            comparison = audit.compare_registry(registry, recorded)

            self.assertFalse(comparison["signature_changed"])
            self.assertEqual(comparison["new_commands"], [])
            self.assertEqual(comparison["removed_commands"], [])

    def test_markdown_report_names_current_drift_sections(self):
        audit = _load_audit_module()
        registry = audit.build_registry()
        markdown = audit.format_markdown(registry)

        self.assertIn("# Bridge Command Registry", markdown)
        self.assertIn("## Drift Summary", markdown)
        self.assertIn("## C++-Only Route Review", markdown)
        self.assertIn("## Commands By Category", markdown)
        self.assertIn("Python missing C++ routes", markdown)
        self.assertIn("attach_bt_sub_node", markdown)


if __name__ == "__main__":
    unittest.main()
