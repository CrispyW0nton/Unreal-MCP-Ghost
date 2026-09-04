"""
Manual smoke test for Phase 2A native Blueprint graph tools.

Run with Unreal Editor open and the upgraded UnrealMCP plugin loaded:
    python unreal_mcp_server/tests/smoke_phase2a_graph_tools.py
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict


def _require_success(stage: str, result: Dict[str, Any]) -> Dict[str, Any]:
    if not result or result.get("success") is False or result.get("status") == "error":
        raise RuntimeError(f"{stage} failed: {json.dumps(result, indent=2)}")
    return result


def main() -> int:
    from unreal_mcp_server import get_unreal_connection

    unreal = get_unreal_connection()
    if not unreal:
        raise RuntimeError("Not connected to Unreal Engine")

    bp_name = "BP_MCP_Phase2A_Smoke"
    graph_name = "EventGraph"

    create_result = unreal.send_command("create_blueprint", {
        "name": bp_name,
        "parent_class": "Actor",
    }) or {}
    if create_result.get("success") is False and "already" not in str(create_result).lower():
        _require_success("create_blueprint", create_result)

    branch = _require_success("bp_add_node", unreal.send_command("bp_add_node", {
        "blueprint_name": bp_name,
        "graph_name": graph_name,
        "node_class": "K2Node_IfThenElse",
        "position_x": 0,
        "position_y": 0,
    }) or {})

    print_string = _require_success("bp_add_node", unreal.send_command("bp_add_node", {
        "blueprint_name": bp_name,
        "graph_name": graph_name,
        "node_class": "K2Node_CallFunction",
        "function_name": "PrintString",
        "target_class": "KismetSystemLibrary",
        "position_x": 360,
        "position_y": 0,
    }) or {})

    branch_guid = branch.get("node_id") or branch.get("node_guid")
    print_guid = print_string.get("node_id") or print_string.get("node_guid")

    _require_success("inspect_branch", unreal.send_command("bp_inspect_node", {
        "blueprint_name": bp_name,
        "graph_name": graph_name,
        "node_guid": branch_guid,
        "include_hidden_pins": True,
    }) or {})

    inspected_print = _require_success("inspect_print", unreal.send_command("bp_inspect_node", {
        "blueprint_name": bp_name,
        "graph_name": graph_name,
        "node_guid": print_guid,
        "include_hidden_pins": True,
    }) or {})

    _require_success("connect_exec", unreal.send_command("bp_connect_pins", {
        "blueprint_name": bp_name,
        "graph_name": graph_name,
        "source_node_guid": branch_guid,
        "source_pin_name": "then",
        "target_node_guid": print_guid,
        "target_pin_name": "execute",
    }) or {})

    _require_success("set_string_default", unreal.send_command("set_node_pin_value", {
        "blueprint_name": bp_name,
        "graph_name": graph_name,
        "node_id": print_guid,
        "pin_name": "InString",
        "value": "Phase 2A graph smoke test",
    }) or {})

    compile_result = _require_success("compile_blueprint", unreal.send_command("compile_blueprint", {
        "blueprint_name": bp_name,
    }) or {})

    print(json.dumps({
        "blueprint": bp_name,
        "branch": branch,
        "print_string": print_string,
        "inspected_print_pins": inspected_print.get("pins", []),
        "compile": compile_result,
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
