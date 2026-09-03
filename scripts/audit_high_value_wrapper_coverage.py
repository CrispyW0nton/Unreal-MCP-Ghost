"""Audit high-value Unreal bridge wrapper coverage.

This offline audit guards the bridge-wrapper priorities from the AI IDE
roadmap. It never connects to Unreal Editor; it checks source, registered tool
signatures, tests, and docs so high-value C++ routes stay reachable from Python
MCP tools with visible evidence.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = REPO_ROOT / "unreal_mcp_server"
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

import bridge_command_audit  # noqa: E402


@dataclass(frozen=True)
class Capability:
    name: str
    description: str
    commands: Sequence[str]
    registry_module: str
    registry_function: str
    expected_parameters: Dict[str, Sequence[str]]
    test_files: Sequence[str]
    doc_files: Sequence[str]


HIGH_VALUE_CAPABILITIES: Sequence[Capability] = (
    Capability(
        name="behavior_tree_blackboard_assignment",
        description="Behavior Tree Blackboard assignment and readback",
        commands=("set_behavior_tree_blackboard", "bt_get_info"),
        registry_module="tools.ai_tools",
        registry_function="register_ai_tools",
        expected_parameters={
            "set_behavior_tree_blackboard": ("behavior_tree_name", "blackboard_name"),
            "bt_get_info": ("behavior_tree_name",),
        },
        test_files=("unreal_mcp_server/tests/test_ai_tools.py",),
        doc_files=("knowledge_base/04_AI_SYSTEMS.md",),
    ),
    Capability(
        name="behavior_tree_task_graph_primitives",
        description="Behavior Tree task graph native node primitives",
        commands=(
            "add_get_random_reachable_point_node",
            "add_finish_execute_node",
            "add_clear_blackboard_value_node",
        ),
        registry_module="tools.ai_tools",
        registry_function="register_ai_tools",
        expected_parameters={
            "add_get_random_reachable_point_node": (
                "blueprint_name",
                "radius",
                "node_position",
            ),
            "add_finish_execute_node": (
                "blueprint_name",
                "success",
                "node_position",
            ),
            "add_clear_blackboard_value_node": (
                "blueprint_name",
                "key_name",
                "node_position",
            ),
        },
        test_files=("unreal_mcp_server/tests/test_ai_tools.py",),
        doc_files=("knowledge_base/04_AI_SYSTEMS.md",),
    ),
    Capability(
        name="blueprint_parent_class_changes",
        description="Blueprint parent-class changes",
        commands=("set_blueprint_parent_class",),
        registry_module="tools.blueprint_tools",
        registry_function="register_blueprint_tools",
        expected_parameters={
            "set_blueprint_parent_class": ("blueprint_name", "new_parent_class"),
        },
        test_files=("unreal_mcp_server/tests/test_b1_gap_tools.py",),
        doc_files=("knowledge_base/01_BLUEPRINT_FUNDAMENTALS.md",),
    ),
    Capability(
        name="construction_script_native_node",
        description="Native Construction Script node route",
        commands=("add_construction_script_node",),
        registry_module="tools.advanced_node_tools",
        registry_function="register_advanced_node_tools",
        expected_parameters={
            "add_construction_script_node": ("blueprint_name", "node_position"),
        },
        test_files=("unreal_mcp_server/tests/test_b1_gap_tools.py",),
        doc_files=("knowledge_base/01_BLUEPRINT_FUNDAMENTALS.md",),
    ),
    Capability(
        name="function_with_pins_creation",
        description="Function-with-pins Blueprint creation",
        commands=("add_blueprint_function_with_pins",),
        registry_module="tools.node_tools",
        registry_function="register_blueprint_node_tools",
        expected_parameters={
            "add_blueprint_function_with_pins": (
                "blueprint_name",
                "function_name",
                "inputs",
                "outputs",
                "is_pure",
            ),
        },
        test_files=("unreal_mcp_server/tests/test_b1_gap_tools.py",),
        doc_files=("knowledge_base/01_BLUEPRINT_FUNDAMENTALS.md",),
    ),
    Capability(
        name="spawnactor_class_assignment",
        description="SpawnActor class assignment",
        commands=("set_spawn_actor_class",),
        registry_module="tools.node_tools",
        registry_function="register_blueprint_node_tools",
        expected_parameters={
            "set_spawn_actor_class": (
                "blueprint_name",
                "node_id",
                "actor_class",
                "graph_name",
            ),
        },
        test_files=("unreal_mcp_server/tests/test_b1_gap_tools.py",),
        doc_files=("knowledge_base/01_BLUEPRINT_FUNDAMENTALS.md",),
    ),
    Capability(
        name="math_relational_native_nodes",
        description="Native arithmetic and relational Blueprint graph primitives",
        commands=("add_arithmetic_operator_node", "add_relational_operator_node"),
        registry_module="tools.advanced_node_tools",
        registry_function="register_advanced_node_tools",
        expected_parameters={
            "add_arithmetic_operator_node": (
                "blueprint_name",
                "operator",
                "operand_type",
                "node_position",
            ),
            "add_relational_operator_node": (
                "blueprint_name",
                "operator",
                "operand_type",
                "node_position",
            ),
        },
        test_files=("unreal_mcp_server/tests/test_b1_gap_tools.py",),
        doc_files=("knowledge_base/01_BLUEPRINT_FUNDAMENTALS.md",),
    ),
    Capability(
        name="sequence_player_nodes",
        description="AnimGraph sequence-player nodes",
        commands=("add_sequence_player_node",),
        registry_module="tools.animation_tools",
        registry_function="register_animation_tools",
        expected_parameters={
            "add_sequence_player_node": (
                "anim_blueprint_name",
                "sequence_asset",
                "graph_name",
                "node_position",
                "wire_to_root",
                "loop",
            ),
        },
        test_files=("unreal_mcp_server/tests/test_animation_tools.py",),
        doc_files=("knowledge_base/05_ANIMATION_SYSTEM.md",),
    ),
    Capability(
        name="animgraph_pose_links",
        description="AnimGraph pose links",
        commands=("connect_anim_graph_nodes",),
        registry_module="tools.animation_tools",
        registry_function="register_animation_tools",
        expected_parameters={
            "connect_anim_graph_nodes": (
                "anim_blueprint_name",
                "source_node_id",
                "target_node_id",
                "graph_name",
            ),
        },
        test_files=("unreal_mcp_server/tests/test_animation_tools.py",),
        doc_files=("knowledge_base/05_ANIMATION_SYSTEM.md",),
    ),
    Capability(
        name="niagara_component_attachment",
        description="Niagara component attachment on generated Blueprints",
        commands=("add_niagara_component",),
        registry_module="tools.niagara_tools",
        registry_function="register_niagara_tools",
        expected_parameters={
            "add_niagara_component": (
                "blueprint_name",
                "component_name",
                "niagara_system_path",
            ),
        },
        test_files=("unreal_mcp_server/tests/test_niagara_tools.py",),
        doc_files=("knowledge_base/09_NIAGARA_VFX.md",),
    ),
)


class _MockMCP:
    def __init__(self) -> None:
        self.tools: Dict[str, Any] = {}

    def tool(self):
        def _decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return _decorator


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_rel(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _registered_tools(module_name: str, register_function: str) -> Dict[str, Any]:
    module = importlib.import_module(module_name)
    mcp = _MockMCP()
    getattr(module, register_function)(mcp)
    return mcp.tools


def _command_registry() -> Dict[str, Any]:
    registry = bridge_command_audit.build_registry()
    return {entry["command"]: entry for entry in registry["commands"]}


def _cpp_review_commands() -> set[str]:
    registry = bridge_command_audit.build_registry()
    return {entry["command"] for entry in registry["cpp_unreferenced_review"]}


def _missing_needles(paths: Iterable[str], needles: Iterable[str]) -> List[str]:
    haystack = "\n".join(_read_rel(path) for path in paths)
    return [needle for needle in needles if needle not in haystack]


def _operator_command_handoff() -> List[Dict[str, Any]]:
    return [
        {
            "id": "run_high_value_wrapper_coverage_audit",
            "label": "Run high-value wrapper coverage audit",
            "command": "python scripts\\audit_high_value_wrapper_coverage.py --json",
            "command_kind": "local_validation",
            "produces_evidence_for": "high_value_bridge_wrapper_coverage",
            "records_evidence_only": False,
            "requires_bridge": False,
            "requires_provider_network": False,
            "requires_spend": False,
            "no_editor_mutation": True,
            "no_provider_call": True,
            "no_git_mutation": True,
            "no_task_submission": True,
        },
        {
            "id": "run_high_value_wrapper_offline_tests",
            "label": "Run high-value wrapper offline tests",
            "command": "python -m unittest unreal_mcp_server.tests.test_phase7_bridge_command_audit unreal_mcp_server.tests.test_phase1_high_value_wrapper_coverage",
            "command_kind": "local_validation",
            "produces_evidence_for": "high_value_bridge_wrapper_tests",
            "records_evidence_only": False,
            "requires_bridge": False,
            "requires_provider_network": False,
            "requires_spend": False,
            "no_editor_mutation": True,
            "no_provider_call": True,
            "no_git_mutation": True,
            "no_task_submission": True,
        },
    ]


def build_report() -> Dict[str, Any]:
    commands = _command_registry()
    cpp_review = _cpp_review_commands()
    capabilities: List[Dict[str, Any]] = []

    for capability in HIGH_VALUE_CAPABILITIES:
        tools = _registered_tools(capability.registry_module, capability.registry_function)
        missing: List[str] = []
        command_rows: List[Dict[str, Any]] = []

        for command in capability.commands:
            entry = commands.get(command)
            if entry is None:
                missing.append(f"{command}: missing from bridge command registry")
                command_rows.append({"command": command, "ok": False})
                continue

            if entry["cpp_routes"] <= 0:
                missing.append(f"{command}: no C++ route discovered")
            if entry["python_references"] <= 0:
                missing.append(f"{command}: no Python bridge reference discovered")
            if command in cpp_review:
                missing.append(f"{command}: still appears in C++-only route review")

            tool = tools.get(command)
            if tool is None:
                missing.append(f"{command}: not registered by {capability.registry_function}")
                parameters: Sequence[str] = ()
                missing_schema_parameters = list(capability.expected_parameters.get(command, ()))
            else:
                parameters = tuple(inspect.signature(tool).parameters)
                missing_schema_parameters = []
                for expected in capability.expected_parameters.get(command, ()):
                    if expected not in parameters:
                        missing.append(f"{command}: missing schema/signature parameter {expected!r}")
                        missing_schema_parameters.append(expected)

            command_rows.append(
                {
                    "command": command,
                    "cpp_routes": entry["cpp_routes"],
                    "python_references": entry["python_references"],
                    "parameters": list(parameters),
                    "expected_schema_parameters": list(capability.expected_parameters.get(command, ())),
                    "missing_schema_parameters": missing_schema_parameters,
                    "schema_ok": tool is not None and not missing_schema_parameters,
                    "ok": command not in cpp_review and entry["cpp_routes"] > 0 and entry["python_references"] > 0,
                }
            )

        missing_tests = _missing_needles(capability.test_files, capability.commands)
        missing_docs = _missing_needles(capability.doc_files, capability.commands)
        for command in missing_tests:
            missing.append(f"{command}: missing offline test evidence")
        for command in missing_docs:
            missing.append(f"{command}: missing documentation evidence")

        capabilities.append(
            {
                "name": capability.name,
                "description": capability.description,
                "commands": command_rows,
                "schema_command_count": len(command_rows),
                "schema_covered_command_count": sum(1 for row in command_rows if row.get("schema_ok")),
                "test_files": list(capability.test_files),
                "doc_files": list(capability.doc_files),
                "ok": not missing,
                "missing": missing,
            }
        )

    failing_capabilities = [entry for entry in capabilities if not entry["ok"]]
    roadmap_priority_names = [capability.name for capability in HIGH_VALUE_CAPABILITIES]
    command_preview = [
        row["command"]
        for capability in capabilities
        for row in capability["commands"]
    ][:20]
    failing_capability_preview = [entry["name"] for entry in failing_capabilities[:8]]
    operator_command_handoff = _operator_command_handoff()
    ok = all(entry["ok"] for entry in capabilities)
    return {
        "schema": "unreal_mcp_high_value_wrapper_coverage.v1",
        "state": "ok" if ok else "blocked",
        "status": "OK" if ok else "FAIL",
        "generated": _utc_now(),
        "source_scope": "offline_source_registry_tests_docs",
        "capability_count": len(capabilities),
        "covered_capability_count": max(0, len(capabilities) - len(failing_capabilities)),
        "failing_capability_count": len(failing_capabilities),
        "command_count": sum(len(entry["commands"]) for entry in capabilities),
        "command_preview": command_preview,
        "schema_command_count": sum(entry["schema_command_count"] for entry in capabilities),
        "schema_covered_command_count": sum(entry["schema_covered_command_count"] for entry in capabilities),
        "roadmap_priority_count": len(roadmap_priority_names),
        "roadmap_priority_covered_count": max(0, len(capabilities) - len(failing_capabilities)),
        "roadmap_priority_missing_count": len(failing_capabilities),
        "roadmap_priority_command_count": sum(len(entry["commands"]) for entry in capabilities),
        "roadmap_priority_preview": roadmap_priority_names[:12],
        "roadmap_priority_missing_preview": failing_capability_preview,
        "failing_capability_preview": failing_capability_preview,
        "operator_command_handoff": operator_command_handoff,
        "operator_command_handoff_ids": [item["id"] for item in operator_command_handoff],
        "operator_command_handoff_count": len(operator_command_handoff),
        "audit_tool": "scripts/audit_high_value_wrapper_coverage.py",
        "bridge_registry_tool": "scripts/bridge_command_audit.py",
        "requires_bridge": False,
        "no_editor_mutation": True,
        "no_provider_call": True,
        "no_git_mutation": True,
        "ok": ok,
        "capabilities": capabilities,
    }


def format_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# High-Value Bridge Wrapper Coverage",
        "",
        f"- Generated: {report['generated']}",
        f"- Schema: `{report['schema']}`",
        f"- Status: {'OK' if report['ok'] else 'FAIL'}",
        f"- Schema coverage: {report['schema_covered_command_count']}/{report['schema_command_count']} command(s)",
        f"- Roadmap priorities: {report['roadmap_priority_covered_count']}/{report['roadmap_priority_count']} covered",
        "",
        "| Capability | Status | Commands |",
        "|---|---|---|",
    ]
    for capability in report["capabilities"]:
        command_names = ", ".join(f"`{row['command']}`" for row in capability["commands"])
        lines.append(
            f"| {capability['description']} | {'OK' if capability['ok'] else 'FAIL'} | {command_names} |"
        )

    failures = [capability for capability in report["capabilities"] if not capability["ok"]]
    if failures:
        lines.extend(["", "## Missing Evidence"])
        for capability in failures:
            lines.append(f"- {capability['name']}:")
            for item in capability["missing"]:
                lines.append(f"  - {item}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown.")
    args = parser.parse_args(argv)

    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(format_markdown(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
