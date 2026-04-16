"""
graph_tools.py — V4 Atomic Blueprint Graph Scripting Core
===========================================================

These are the PRIMARY graph-authoring tools for AI-driven Blueprint scripting.
Every tool here returns a StructuredResult and is designed for agent reliability.

Design principles:
  - ATOMIC: each tool does one well-defined operation.
  - STRUCTURED: every result has success/stage/message/outputs/warnings/errors.
  - TRANSACTIONAL: mutations use ScopedEditorTransaction via exec_substrate.
  - INSPECTABLE: graph summary gives a compact, AI-readable graph state.
  - SAFE: failures return exact node/pin/reason — no silent breakage.

Tools provided:
  bp_get_graph_summary    — compact AI-readable graph state (nodes + pins + connections)
  bp_create_graph         — add a new function/macro graph to an existing Blueprint
  bp_add_node             — add a typed node and return its stable node_id
  bp_inspect_node         — full pin+connection info for a single node
  bp_connect_pins         — connect pins with compatibility pre-check
  bp_set_pin_default      — set a pin's default/literal value
  bp_add_variable         — add a typed member variable
  bp_compile              — compile and return structured errors/warnings
  bp_auto_format_graph    — auto-arrange graph nodes left-to-right

All tools delegate to exec_python_structured / exec_python_transactional
from exec_substrate where graph mutation is involved, and to direct C++ bridge
commands for read-only inspection.

Naming convention:
  bp_*  — Blueprint graph tools (this module)
  mat_* — Material graph tools (future: material_graph_tools.py)
"""

from __future__ import annotations

import json
import logging
import textwrap
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger("UnrealMCP")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _send(command: str, params: dict) -> Dict[str, Any]:
    from unreal_mcp_server import get_unreal_connection
    try:
        unreal = get_unreal_connection()
        if not unreal:
            return {"success": False, "message": "Not connected to Unreal Engine"}
        result = unreal.send_command(command, params)
        return result or {"success": False, "message": "No response from Unreal Engine"}
    except Exception as exc:
        logger.error(f"graph_tools._send error: {exc}")
        return {"success": False, "message": str(exc)}


def _make_result(
    *,
    success: bool,
    stage: str = "",
    message: str = "",
    outputs: Optional[Dict] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    log_tail: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "success": success,
        "stage": stage,
        "message": message,
        "outputs": outputs or {},
        "warnings": warnings or [],
        "errors": errors or [],
        "log_tail": log_tail or [],
    }


def _exec_structured(code: str, stage: str) -> Dict[str, Any]:
    """Run code via exec_substrate.exec_python_structured."""
    from tools.exec_substrate import exec_python_structured
    return exec_python_structured(code, stage)


def _exec_transactional(code: str, tx_name: str) -> Dict[str, Any]:
    """Run code via exec_substrate.exec_python_transactional."""
    from tools.exec_substrate import exec_python_transactional
    return exec_python_transactional(code, tx_name)


# ── Registration ──────────────────────────────────────────────────────────────

def register_graph_tools(mcp: FastMCP):  # noqa: C901

    # ──────────────────────────────────────────────────────────────────────────
    # bp_get_graph_summary
    # ──────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def bp_get_graph_summary(
        ctx: Context,
        blueprint_name: str,
        graph_name: str = "EventGraph",
        include_pin_defaults: bool = True,
        include_positions: bool = True,
    ) -> str:
        """Get a compact, AI-readable summary of a Blueprint graph.

        This is the primary tool for understanding a graph before editing it.
        Returns a structured JSON with every node's id, type, title, position,
        pins (name, direction, type, default value, connections), and comments.

        Use this BEFORE calling bp_add_node, bp_connect_pins, or any mutation
        to understand the existing graph state.

        Output format (outputs dict):
          blueprint:    str  — Blueprint asset name
          graph:        str  — Graph name
          node_count:   int  — Total nodes
          nodes:        list — Each entry:
            node_id:      str  — Stable GUID for use in other bp_* tools
            node_name:    str  — Short object name (K2Node_...)
            node_type:    str  — 'event', 'function', 'variable_get', etc.
            title:        str  — Human-readable node title
            pos_x:        int
            pos_y:        int
            pins:         list — Each entry:
              pin_name:      str
              direction:     'input' | 'output'
              pin_type:      str
              default_value: str   (empty if not set)
              linked_to:     list  — [{node_id, pin_name}]
          summary_text: str  — Compact one-liner per node for quick scanning

        Args:
            blueprint_name:      Blueprint asset name (e.g. 'BP_MyActor')
            graph_name:          Graph to inspect. Default 'EventGraph'.
            include_pin_defaults: Include pin default values. Default True.
            include_positions:    Include node canvas positions. Default True.

        Returns:
            JSON string with StructuredResult.
        """
        # Delegate to existing C++ get_blueprint_nodes, then reformat into summary
        raw = _send("get_blueprint_nodes", {
            "blueprint_name": blueprint_name,
            "graph_name": graph_name,
            "include_hidden_pins": False,
        })

        if not raw or raw.get("success") is False or raw.get("status") == "error":
            msg = (raw or {}).get("message") or (raw or {}).get("error") or "get_blueprint_nodes failed"
            return json.dumps(_make_result(
                success=False,
                stage="bp_get_graph_summary",
                message=msg,
                errors=[msg],
            ))

        nodes_raw = raw.get("nodes") or raw.get("result", {}).get("nodes") or []

        summary_lines = []
        nodes_out = []

        for n in nodes_raw:
            node_id = n.get("node_id") or n.get("node_guid") or ""
            node_name = n.get("node_name") or n.get("name") or ""
            node_type = n.get("node_type") or ""
            title = (
                n.get("function_name")
                or n.get("event_name")
                or n.get("variable_name")
                or n.get("title")
                or node_type
                or node_name
            )
            pos_x = n.get("pos_x", 0) if include_positions else None
            pos_y = n.get("pos_y", 0) if include_positions else None

            # Process pins
            pins_out = []
            for p in n.get("pins") or []:
                direction = "output" if p.get("direction") in ("output", "EGPD_Output", 1) else "input"
                default_val = p.get("default_value", "") if include_pin_defaults else ""
                linked_to = []
                for link in p.get("linked_to") or []:
                    linked_to.append({
                        "node_id": link.get("node_id") or link.get("node_guid") or "",
                        "pin_name": link.get("pin_name") or link.get("pin") or "",
                    })
                pins_out.append({
                    "pin_name": p.get("pin_name") or p.get("name") or "",
                    "direction": direction,
                    "pin_type": p.get("pin_type") or p.get("type") or "",
                    "default_value": default_val,
                    "linked_to": linked_to,
                })

            entry: Dict[str, Any] = {
                "node_id": node_id,
                "node_name": node_name,
                "node_type": node_type,
                "title": title,
                "pins": pins_out,
            }
            if include_positions:
                entry["pos_x"] = pos_x
                entry["pos_y"] = pos_y

            nodes_out.append(entry)

            # Build compact summary line
            connected_pins = [p for p in pins_out if p["linked_to"]]
            pin_summary = ", ".join(
                f"{p['pin_name']}→{p['linked_to'][0]['pin_name']}@{p['linked_to'][0]['node_id'][:8]}"
                for p in connected_pins[:4]
            )
            summary_lines.append(
                f"[{node_id[:8] if node_id else '?'}] {title} ({node_type}) — {len(pins_out)} pins"
                + (f" | connects: {pin_summary}" if pin_summary else "")
            )

        outputs = {
            "blueprint": blueprint_name,
            "graph": graph_name,
            "node_count": len(nodes_out),
            "nodes": nodes_out,
            "summary_text": "\n".join(summary_lines) if summary_lines else "(empty graph)",
        }

        return json.dumps(_make_result(
            success=True,
            stage="bp_get_graph_summary",
            message=f"Graph '{graph_name}' in '{blueprint_name}': {len(nodes_out)} nodes",
            outputs=outputs,
        ))

    # ──────────────────────────────────────────────────────────────────────────
    # bp_create_graph
    # ──────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def bp_create_graph(
        ctx: Context,
        blueprint_name: str,
        graph_name: str,
        graph_type: str = "function",
    ) -> str:
        """Add a new function or macro graph to an existing Blueprint.

        Use this to create new function graphs that can be called from the
        EventGraph or other functions. After creation, use bp_add_node to
        populate it with nodes.

        Note: 'EventGraph' already exists in every Blueprint — do not create it.
        Use bp_create_graph for custom function graphs (e.g. 'InitPlayer',
        'CalculateDamage') or macro graphs.

        Args:
            blueprint_name: Blueprint asset name (e.g. 'BP_MyActor')
            graph_name:     Name for the new graph (e.g. 'InitPlayer')
            graph_type:     'function' (default) or 'macro'

        Returns:
            JSON string with StructuredResult.
            outputs.graph_name — confirmed graph name created
        """
        allowed_types = ("function", "macro")
        if graph_type not in allowed_types:
            return json.dumps(_make_result(
                success=False,
                stage="bp_create_graph",
                message=f"Invalid graph_type '{graph_type}'. Must be one of: {allowed_types}",
                errors=[f"graph_type must be 'function' or 'macro', got '{graph_type}'"],
            ))

        if graph_name in ("EventGraph", "ConstructionScript"):
            return json.dumps(_make_result(
                success=False,
                stage="bp_create_graph",
                message=f"'{graph_name}' is a built-in graph — it already exists and cannot be created.",
                errors=[f"Graph '{graph_name}' is reserved/built-in."],
            ))

        code = textwrap.dedent(f"""
            import unreal
            bp = unreal.load_asset('/Game/Blueprints/{blueprint_name}')
            if bp is None:
                # Try finding via asset registry
                reg = unreal.AssetRegistryHelpers.get_asset_registry()
                results = reg.get_assets_by_class('Blueprint', True)
                bp = next((unreal.load_asset(a.object_path) for a in results
                           if a.asset_name == '{blueprint_name}'), None)
            if bp is None:
                raise RuntimeError(f"Blueprint '{blueprint_name}' not found")
            graph_type_str = '{graph_type}'
            existing = [g.get_name() for g in (bp.function_graphs or [])] + \\
                       [g.get_name() for g in (bp.macros or [])]
            if '{graph_name}' in existing:
                _warnings.append(f"Graph '{graph_name}' already exists — skipping creation")
                _result['graph_name'] = '{graph_name}'
                _result['already_existed'] = True
            else:
                if graph_type_str == 'function':
                    new_graph = unreal.BlueprintEditorLibrary.add_function_graph(bp, '{graph_name}')
                else:
                    new_graph = unreal.BlueprintEditorLibrary.add_macro_graph(bp, '{graph_name}')
                unreal.EditorAssetLibrary.save_loaded_asset(bp)
                _result['graph_name'] = '{graph_name}'
                _result['graph_type'] = graph_type_str
                _result['already_existed'] = False
        """)

        result = _exec_transactional(code, f"bp_create_graph:{blueprint_name}/{graph_name}")
        return json.dumps(result)

    # ──────────────────────────────────────────────────────────────────────────
    # bp_add_node
    # ──────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def bp_add_node(
        ctx: Context,
        blueprint_name: str,
        node_type: str,
        graph_name: str = "EventGraph",
        node_params: Optional[Dict[str, Any]] = None,
        position_x: int = 0,
        position_y: int = 0,
    ) -> str:
        """Add a node to a Blueprint graph and return its stable node_id.

        This is the primary node-creation tool. It wraps the existing
        add_blueprint_event_node, add_blueprint_function_node, add_print_string_node,
        add_blueprint_branch_node, etc. behind a unified interface, and
        returns a structured result with the node_id for use in bp_connect_pins
        and bp_inspect_node.

        node_type values (case-insensitive):
          event:<EventName>         — Event node (BeginPlay, Tick, Hit, etc.)
          function:<ClassName>:<FunctionName>  — Function call node
          print_string              — PrintString node
          branch                    — Branch (if/else) node
          sequence                  — Sequence node
          variable_get:<VarName>    — Variable GET node
          variable_set:<VarName>    — Variable SET node
          delay                     — Delay node
          cast:<TargetClass>        — DynamicCast node
          macro:<MacroName>         — Macro node (DoOnce, FlipFlop, Gate, etc.)
          math:<Operation>          — Math node (+, -, *, /, %, ==, !=, <, >, &&, ||)
          custom_event:<EventName>  — Custom Event node

        node_params (optional dict):
          For function nodes: {"target_class": "Actor", "function_name": "SetActorHiddenInGame"}
          For event nodes:    {"event_name": "BeginPlay"}
          For cast nodes:     {"target_class": "MyCharacter"}

        Returns:
            JSON string with StructuredResult.
            outputs.node_id    — stable GUID to use in bp_connect_pins
            outputs.node_name  — short object name (K2Node_...)
            outputs.node_type  — confirmed type string
            outputs.pos_x, outputs.pos_y — node canvas position

        Args:
            blueprint_name: Blueprint asset name
            node_type:      Node type string (see above)
            graph_name:     Target graph. Default 'EventGraph'
            node_params:    Optional dict of extra params for the node type
            position_x:     Canvas X position
            position_y:     Canvas Y position
        """
        if node_params is None:
            node_params = {}

        node_type_lower = node_type.lower()
        pos = [float(position_x), float(position_y)]

        # Route to correct C++ command based on node_type prefix
        if node_type_lower.startswith("event:"):
            event_name = node_type[6:] or node_params.get("event_name", "BeginPlay")
            raw = _send("add_blueprint_event_node", {
                "blueprint_name": blueprint_name,
                "event_name": event_name,
                "graph_name": graph_name,
                "node_position": pos,
            })

        elif node_type_lower.startswith("custom_event:"):
            event_name = node_type[13:] or node_params.get("event_name", "MyCustomEvent")
            raw = _send("add_blueprint_event_node", {
                "blueprint_name": blueprint_name,
                "event_name": event_name,
                "graph_name": graph_name,
                "node_position": pos,
            })

        elif node_type_lower == "print_string":
            raw = _send("add_blueprint_function_node", {
                "blueprint_name": blueprint_name,
                "function_name": "PrintString",
                "target_class": "KismetSystemLibrary",
                "graph_name": graph_name,
                "node_position": pos,
            })

        elif node_type_lower == "branch":
            raw = _send("add_blueprint_branch_node", {
                "blueprint_name": blueprint_name,
                "graph_name": graph_name,
                "node_position": pos,
            })

        elif node_type_lower == "sequence":
            raw = _send("add_blueprint_sequence_node", {
                "blueprint_name": blueprint_name,
                "graph_name": graph_name,
                "node_position": pos,
                "num_outputs": node_params.get("num_outputs", 2),
            })

        elif node_type_lower == "delay":
            raw = _send("add_blueprint_function_node", {
                "blueprint_name": blueprint_name,
                "function_name": "Delay",
                "target_class": "KismetSystemLibrary",
                "graph_name": graph_name,
                "node_position": pos,
            })

        elif node_type_lower.startswith("variable_get:"):
            var_name = node_type[13:] or node_params.get("variable_name", "")
            if not var_name:
                return json.dumps(_make_result(
                    success=False, stage="bp_add_node",
                    message="variable_get requires a variable name: 'variable_get:MyVar'",
                    errors=["Missing variable name in node_type string"],
                ))
            raw = _send("add_blueprint_variable_get_node", {
                "blueprint_name": blueprint_name,
                "variable_name": var_name,
                "graph_name": graph_name,
                "node_position": pos,
            })

        elif node_type_lower.startswith("variable_set:"):
            var_name = node_type[13:] or node_params.get("variable_name", "")
            if not var_name:
                return json.dumps(_make_result(
                    success=False, stage="bp_add_node",
                    message="variable_set requires a variable name: 'variable_set:MyVar'",
                    errors=["Missing variable name in node_type string"],
                ))
            raw = _send("add_blueprint_variable_set_node", {
                "blueprint_name": blueprint_name,
                "variable_name": var_name,
                "graph_name": graph_name,
                "node_position": pos,
            })

        elif node_type_lower.startswith("cast:"):
            target_class = node_type[5:] or node_params.get("target_class", "")
            if not target_class:
                return json.dumps(_make_result(
                    success=False, stage="bp_add_node",
                    message="cast requires a class name: 'cast:MyCharacter'",
                    errors=["Missing target class in node_type string"],
                ))
            raw = _send("add_blueprint_function_node", {
                "blueprint_name": blueprint_name,
                "function_name": f"Cast To {target_class}",
                "target_class": target_class,
                "graph_name": graph_name,
                "node_position": pos,
            })

        elif node_type_lower.startswith("macro:"):
            macro_name = node_type[6:] or node_params.get("macro_name", "")
            raw = _send("add_blueprint_sequence_node", {
                "blueprint_name": blueprint_name,
                "macro_name": macro_name,
                "graph_name": graph_name,
                "node_position": pos,
            })

        elif node_type_lower.startswith("math:"):
            op = node_type[5:] or node_params.get("operation", "+")
            raw = _send("add_blueprint_function_node", {
                "blueprint_name": blueprint_name,
                "function_name": op,
                "graph_name": graph_name,
                "node_position": pos,
            })

        elif node_type_lower.startswith("function:"):
            # format: "function:ClassName:FunctionName"
            parts = node_type.split(":", 2)
            target_class = parts[1] if len(parts) > 1 else node_params.get("target_class", "")
            function_name = parts[2] if len(parts) > 2 else node_params.get("function_name", "")
            if not function_name:
                return json.dumps(_make_result(
                    success=False, stage="bp_add_node",
                    message="function node requires format 'function:ClassName:FunctionName' or node_params",
                    errors=["Missing function_name"],
                ))
            params = {
                "blueprint_name": blueprint_name,
                "function_name": function_name,
                "graph_name": graph_name,
                "node_position": pos,
            }
            if target_class:
                params["target_class"] = target_class
            raw = _send("add_blueprint_function_node", params)

        else:
            return json.dumps(_make_result(
                success=False,
                stage="bp_add_node",
                message=f"Unknown node_type: '{node_type}'. See tool docstring for supported types.",
                errors=[f"Unsupported node_type '{node_type}'"],
            ))

        # Normalize raw response into StructuredResult
        if not raw or raw.get("success") is False or raw.get("status") == "error":
            msg = (raw or {}).get("message") or (raw or {}).get("error") or "Node creation failed"
            return json.dumps(_make_result(
                success=False,
                stage="bp_add_node",
                message=msg,
                errors=[msg],
            ))

        # Extract node_id from response (C++ returns it under several key names)
        result_data = raw.get("result") or raw
        node_id = (
            result_data.get("node_id")
            or result_data.get("node_guid")
            or raw.get("node_id")
            or raw.get("node_guid")
            or ""
        )
        node_name = (
            result_data.get("node_name")
            or result_data.get("name")
            or raw.get("node_name")
            or ""
        )

        return json.dumps(_make_result(
            success=True,
            stage="bp_add_node",
            message=f"Node '{node_type}' added to '{graph_name}' in '{blueprint_name}'",
            outputs={
                "node_id": node_id,
                "node_name": node_name,
                "node_type": node_type,
                "pos_x": position_x,
                "pos_y": position_y,
                "blueprint": blueprint_name,
                "graph": graph_name,
            },
            warnings=[] if node_id else [
                "node_id is empty — C++ did not return a GUID. "
                "Use bp_get_graph_summary to find the node by position or type."
            ],
        ))

    # ──────────────────────────────────────────────────────────────────────────
    # bp_inspect_node
    # ──────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def bp_inspect_node(
        ctx: Context,
        blueprint_name: str,
        node_id: str,
        graph_name: str = "EventGraph",
        include_hidden_pins: bool = False,
    ) -> str:
        """Get full pin and connection details for a single Blueprint node.

        Use this after bp_add_node to see the exact pin names before
        calling bp_connect_pins. Pin names returned here are the exact
        strings you must pass to bp_connect_pins.

        Returns a StructuredResult with:
          outputs.node_id       — the node's GUID
          outputs.node_name     — short object name
          outputs.node_type     — type string
          outputs.title         — human-readable title
          outputs.pos_x, pos_y  — canvas position
          outputs.pins          — list of all pins:
            pin_name      — exact name to use in bp_connect_pins
            direction     — 'input' | 'output'
            pin_type      — type string (exec, bool, float, object, etc.)
            default_value — current default value (empty if not set)
            linked_to     — list of {node_id, pin_name} for connected pins

        Args:
            blueprint_name:      Blueprint asset name
            node_id:             GUID or short object name from bp_add_node
            graph_name:          Graph containing the node. Default 'EventGraph'
            include_hidden_pins: Include internal pins. Default False.

        Returns:
            JSON string with StructuredResult.
        """
        raw = _send("get_node_by_id", {
            "blueprint_name": blueprint_name,
            "node_id": node_id,
            "graph_name": graph_name,
            "include_hidden_pins": include_hidden_pins,
        })

        if not raw or raw.get("success") is False or raw.get("status") == "error":
            msg = (raw or {}).get("message") or (raw or {}).get("error") or "Node not found"
            return json.dumps(_make_result(
                success=False,
                stage="bp_inspect_node",
                message=f"Node '{node_id}' not found in '{graph_name}': {msg}",
                errors=[msg],
            ))

        node_data = raw.get("node") or raw.get("result") or raw

        # Normalize pins
        pins_out = []
        for p in node_data.get("pins") or []:
            direction = "output" if p.get("direction") in ("output", "EGPD_Output", 1) else "input"
            linked_to = []
            for link in p.get("linked_to") or []:
                linked_to.append({
                    "node_id": link.get("node_id") or link.get("node_guid") or "",
                    "pin_name": link.get("pin_name") or link.get("pin") or "",
                })
            pins_out.append({
                "pin_name": p.get("pin_name") or p.get("name") or "",
                "direction": direction,
                "pin_type": p.get("pin_type") or p.get("type") or "",
                "default_value": p.get("default_value", ""),
                "linked_to": linked_to,
            })

        title = (
            node_data.get("function_name")
            or node_data.get("event_name")
            or node_data.get("variable_name")
            or node_data.get("title")
            or node_data.get("node_type", "")
        )

        outputs = {
            "node_id": node_data.get("node_id") or node_data.get("node_guid") or node_id,
            "node_name": node_data.get("node_name") or node_data.get("name") or "",
            "node_type": node_data.get("node_type") or "",
            "title": title,
            "pos_x": node_data.get("pos_x", 0),
            "pos_y": node_data.get("pos_y", 0),
            "pins": pins_out,
            "input_pins": [p["pin_name"] for p in pins_out if p["direction"] == "input"],
            "output_pins": [p["pin_name"] for p in pins_out if p["direction"] == "output"],
        }

        return json.dumps(_make_result(
            success=True,
            stage="bp_inspect_node",
            message=f"Node '{title}' ({len(pins_out)} pins)",
            outputs=outputs,
        ))

    # ──────────────────────────────────────────────────────────────────────────
    # bp_connect_pins
    # ──────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def bp_connect_pins(
        ctx: Context,
        blueprint_name: str,
        source_node_id: str,
        source_pin: str,
        target_node_id: str,
        target_pin: str,
        graph_name: str = "EventGraph",
    ) -> str:
        """Connect an output pin on one Blueprint node to an input pin on another.

        Pin names MUST be the exact strings returned by bp_inspect_node.
        Common exec pin names: 'then' (output), 'execute' (input).
        Common data pin names: 'ReturnValue', 'Target', 'Value', etc.

        If the connection fails due to type mismatch or schema rejection,
        the error field explains why so the agent can diagnose the issue
        without guessing.

        Returns:
          outputs.source_node_id, source_pin, target_node_id, target_pin
          outputs.connection_verified — bool (True if UE5 confirmed success)
          errors[]                    — schema rejection reason if failed

        Args:
            blueprint_name:  Blueprint asset name
            source_node_id:  GUID or name of the source node (has the output pin)
            source_pin:      Output pin name on the source node
            target_node_id:  GUID or name of the target node (has the input pin)
            target_pin:      Input pin name on the target node
            graph_name:      Graph name. Default 'EventGraph'

        Returns:
            JSON string with StructuredResult.
        """
        if not source_pin or not target_pin:
            return json.dumps(_make_result(
                success=False,
                stage="bp_connect_pins",
                message="Both source_pin and target_pin are required.",
                errors=["source_pin and target_pin must not be empty — use bp_inspect_node to find exact pin names"],
            ))

        raw = _send("connect_blueprint_nodes", {
            "blueprint_name": blueprint_name,
            "source_node_id": source_node_id,
            "source_pin": source_pin,
            "target_node_id": target_node_id,
            "target_pin": target_pin,
            "graph_name": graph_name,
        })

        if not raw:
            return json.dumps(_make_result(
                success=False,
                stage="bp_connect_pins",
                message="No response from Unreal Engine",
                errors=["Empty response from C++ bridge"],
            ))

        success = raw.get("success", False) or raw.get("status") == "success"
        verified = raw.get("connection_verified", False)
        warning_msg = raw.get("warning", "")
        error_msg = raw.get("error") or raw.get("message") or ""

        warnings = []
        errors = []

        if not success:
            errors.append(error_msg or "connect_blueprint_nodes failed")
        elif not verified and warning_msg:
            warnings.append(f"Connection may not have taken effect: {warning_msg}")

        return json.dumps(_make_result(
            success=success,
            stage="bp_connect_pins",
            message=(
                f"Connected {source_node_id[:8]}.{source_pin} → {target_node_id[:8]}.{target_pin}"
                if success else f"Connection failed: {error_msg}"
            ),
            outputs={
                "source_node_id": source_node_id,
                "source_pin": source_pin,
                "target_node_id": target_node_id,
                "target_pin": target_pin,
                "graph_name": graph_name,
                "connection_verified": verified,
            },
            warnings=warnings,
            errors=errors,
        ))

    # ──────────────────────────────────────────────────────────────────────────
    # bp_set_pin_default
    # ──────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def bp_set_pin_default(
        ctx: Context,
        blueprint_name: str,
        node_id: str,
        pin_name: str,
        default_value: str,
        graph_name: str = "EventGraph",
    ) -> str:
        """Set the default/literal value for an unconnected input pin.

        Use this to set constant values on node pins — for example, setting
        the 'Duration' on a Delay node, or the 'In String' on PrintString.

        Only works on unconnected input pins. If the pin is already connected
        to another node, set_node_pin_value will be rejected by UE5 (the
        connected value overrides the default).

        Value formats:
          bool:     'true' or 'false'
          int:      '42'
          float:    '3.14'
          string:   'Hello World'
          vector:   '(X=1.0,Y=2.0,Z=3.0)'
          rotator:  '(Pitch=0,Yaw=90,Roll=0)'
          enum:     'EnumValue' (exact enum string value)

        Args:
            blueprint_name: Blueprint asset name
            node_id:        GUID or short name of the node
            pin_name:       Exact pin name (from bp_inspect_node output)
            default_value:  Value string to set
            graph_name:     Graph name. Default 'EventGraph'

        Returns:
            JSON string with StructuredResult.
            outputs.node_id, pin_name, previous_value, new_value
        """
        if not pin_name:
            return json.dumps(_make_result(
                success=False,
                stage="bp_set_pin_default",
                message="pin_name is required — use bp_inspect_node to find exact pin names",
                errors=["pin_name must not be empty"],
            ))

        raw = _send("set_node_pin_value", {
            "blueprint_name": blueprint_name,
            "node_id": node_id,
            "pin_name": pin_name,
            "value": default_value,
            "graph_name": graph_name,
        })

        if not raw or raw.get("success") is False or raw.get("status") == "error":
            msg = (raw or {}).get("message") or (raw or {}).get("error") or "set_node_pin_value failed"

            # Provide actionable guidance on known failure modes
            hints = []
            if "not found" in msg.lower():
                hints.append(
                    f"Pin '{pin_name}' was not found on node '{node_id}'. "
                    "Run bp_inspect_node to get the exact pin names."
                )
            elif "connected" in msg.lower():
                hints.append(
                    f"Pin '{pin_name}' is connected to another node. "
                    "Disconnect it first with disconnect_blueprint_nodes, then set the default."
                )

            return json.dumps(_make_result(
                success=False,
                stage="bp_set_pin_default",
                message=msg,
                errors=[msg] + hints,
            ))

        result_data = raw.get("result") or raw
        return json.dumps(_make_result(
            success=True,
            stage="bp_set_pin_default",
            message=f"Set pin '{pin_name}' on node '{node_id}' to '{default_value}'",
            outputs={
                "node_id": node_id,
                "pin_name": pin_name,
                "new_value": default_value,
                "previous_value": result_data.get("previous_value", ""),
            },
        ))

    # ──────────────────────────────────────────────────────────────────────────
    # bp_add_variable
    # ──────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def bp_add_variable(
        ctx: Context,
        blueprint_name: str,
        variable_name: str,
        variable_type: str,
        default_value: str = "",
        is_exposed: bool = False,
        category: str = "Default",
    ) -> str:
        """Add a member variable to a Blueprint with full type support.

        After adding a variable, use bp_add_node with 'variable_get:VarName'
        or 'variable_set:VarName' to place GET/SET nodes in the graph.

        Supported variable_type values:
          Boolean, Integer, Integer64, Float, Double,
          String, Name, Text,
          Vector, Rotator, Transform,
          Object/<FullClassPath>   (e.g. 'Object//Script/Engine.StaticMeshComponent')

        Args:
            blueprint_name:  Blueprint asset name
            variable_name:   New variable name (e.g. 'Health', 'bIsAlive')
            variable_type:   Type string (see above)
            default_value:   Optional initial value string
            is_exposed:      Expose in Details panel (BlueprintVisible + EditAnywhere)
            category:        Category for Details panel grouping. Default 'Default'

        Returns:
            JSON string with StructuredResult.
            outputs.variable_name, variable_type, is_exposed, default_value
        """
        valid_simple_types = {
            "boolean", "bool", "integer", "int", "integer64", "int64",
            "float", "double", "string", "name", "text",
            "vector", "rotator", "transform",
        }
        vtype_lower = variable_type.lower()
        if vtype_lower not in valid_simple_types and not vtype_lower.startswith("object/"):
            return json.dumps(_make_result(
                success=False,
                stage="bp_add_variable",
                message=f"Unknown variable_type '{variable_type}'.",
                errors=[
                    f"variable_type '{variable_type}' is not recognized. "
                    f"Valid types: Boolean, Integer, Float, Double, String, Name, Text, "
                    f"Vector, Rotator, Transform, Object/<FullClassPath>"
                ],
            ))

        params: Dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "variable_name": variable_name,
            "variable_type": variable_type,
            "is_exposed": is_exposed,
        }
        if default_value:
            params["default_value"] = default_value

        raw = _send("add_blueprint_variable", params)

        if not raw or raw.get("success") is False or raw.get("status") == "error":
            msg = (raw or {}).get("message") or (raw or {}).get("error") or "add_blueprint_variable failed"
            return json.dumps(_make_result(
                success=False,
                stage="bp_add_variable",
                message=msg,
                errors=[msg],
            ))

        return json.dumps(_make_result(
            success=True,
            stage="bp_add_variable",
            message=f"Variable '{variable_name}' ({variable_type}) added to '{blueprint_name}'",
            outputs={
                "variable_name": variable_name,
                "variable_type": variable_type,
                "is_exposed": is_exposed,
                "default_value": default_value,
                "category": category,
                "blueprint": blueprint_name,
                "next_steps": [
                    f"Use bp_add_node with node_type='variable_get:{variable_name}' to read it",
                    f"Use bp_add_node with node_type='variable_set:{variable_name}' to write it",
                ],
            },
        ))

    # ──────────────────────────────────────────────────────────────────────────
    # bp_compile
    # ──────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def bp_compile(
        ctx: Context,
        blueprint_name: str,
        save_after_compile: bool = True,
    ) -> str:
        """Compile a Blueprint and return structured errors/warnings.

        Always run this after finishing a set of graph edits. The result
        includes had_errors, had_warnings, and a structured list of compile
        messages with category, message, and node reference where available.

        Returns:
          outputs.had_errors          — bool
          outputs.had_warnings        — bool
          outputs.compile_messages    — list of {category, message, node_name}
          outputs.error_count         — int
          outputs.warning_count       — int
          outputs.saved               — bool (only if save_after_compile=True)

        If had_errors is True, inspect compile_messages for the specific
        failure reason and which node is involved.

        Args:
            blueprint_name:      Blueprint asset name
            save_after_compile:  Also save the Blueprint after successful compile.
                                 Default True.

        Returns:
            JSON string with StructuredResult.
        """
        raw = _send("compile_blueprint", {"blueprint_name": blueprint_name})

        if not raw or raw.get("status") == "error" or raw.get("success") is False:
            msg = (raw or {}).get("error") or (raw or {}).get("message") or "compile_blueprint failed"
            return json.dumps(_make_result(
                success=False,
                stage="bp_compile",
                message=msg,
                errors=[msg],
            ))

        result_data = raw.get("result") or raw

        had_errors = result_data.get("had_errors", False)
        had_warnings = result_data.get("had_warnings", False)
        compile_msgs = result_data.get("compile_messages") or result_data.get("messages") or []

        # Normalize compile messages
        msgs_out = []
        for m in compile_msgs:
            if isinstance(m, str):
                msgs_out.append({"category": "unknown", "message": m, "node_name": ""})
            elif isinstance(m, dict):
                msgs_out.append({
                    "category": m.get("category") or m.get("type") or "unknown",
                    "message": m.get("message") or m.get("msg") or str(m),
                    "node_name": m.get("node_name") or m.get("node") or "",
                })

        errors_list = [m["message"] for m in msgs_out if m["category"] in ("error", "Error")]
        warnings_list = [m["message"] for m in msgs_out if m["category"] in ("warning", "Warning")]

        saved = False
        save_warnings = []
        if save_after_compile and not had_errors:
            save_raw = _send("save_blueprint", {"blueprint_name": blueprint_name})
            saved = bool((save_raw or {}).get("success") or (save_raw or {}).get("status") == "success")
            if not saved:
                save_warnings.append("Compile succeeded but save failed — blueprint changes may be lost on editor close")

        return json.dumps(_make_result(
            success=not had_errors,
            stage="bp_compile",
            message=(
                f"Compiled '{blueprint_name}': {'ERRORS' if had_errors else 'OK'}"
                + (f" ({len(errors_list)} error(s), {len(warnings_list)} warning(s))" if msgs_out else "")
            ),
            outputs={
                "blueprint": blueprint_name,
                "had_errors": had_errors,
                "had_warnings": had_warnings,
                "compile_messages": msgs_out,
                "error_count": len(errors_list),
                "warning_count": len(warnings_list),
                "saved": saved,
            },
            warnings=warnings_list + save_warnings,
            errors=errors_list,
        ))

    # ──────────────────────────────────────────────────────────────────────────
    # bp_auto_format_graph
    # ──────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def bp_auto_format_graph(
        ctx: Context,
        blueprint_name: str,
        graph_name: str = "EventGraph",
        x_spacing: int = 350,
        y_spacing: int = 150,
        start_x: int = -400,
        start_y: int = 0,
    ) -> str:
        """Auto-arrange nodes in a Blueprint graph into a clean left-to-right layout.

        Performs a topological sort of node execution order, then repositions
        nodes so execution flows left-to-right with consistent spacing.
        Data/reference nodes are placed below their consuming exec nodes.

        This uses exec_python_transactional so the layout is undoable.

        Layout rules:
          - Execution chain nodes are spaced x_spacing apart horizontally
          - Pure/getter nodes are placed below exec chain at y_spacing offset
          - Events (no exec-in) are anchored at start_x, start_y
          - Multiple disconnected chains are stacked vertically

        Args:
            blueprint_name: Blueprint asset name
            graph_name:     Graph to format. Default 'EventGraph'
            x_spacing:      Horizontal spacing between exec nodes (default 350)
            y_spacing:      Vertical spacing for data nodes (default 150)
            start_x:        X position of first node (default -400)
            start_y:        Y starting position (default 0)

        Returns:
            JSON string with StructuredResult.
            outputs.nodes_repositioned — count of nodes moved
            outputs.layout_summary     — list of {node_id, title, new_x, new_y}
        """
        # Get current graph state
        raw = _send("get_blueprint_nodes", {
            "blueprint_name": blueprint_name,
            "graph_name": graph_name,
            "include_hidden_pins": False,
        })

        if not raw or raw.get("success") is False:
            msg = (raw or {}).get("message") or "Could not fetch graph nodes"
            return json.dumps(_make_result(
                success=False,
                stage="bp_auto_format_graph",
                message=msg,
                errors=[msg],
            ))

        nodes = raw.get("nodes") or raw.get("result", {}).get("nodes") or []
        if not nodes:
            return json.dumps(_make_result(
                success=True,
                stage="bp_auto_format_graph",
                message=f"Graph '{graph_name}' is empty — nothing to format",
                outputs={"nodes_repositioned": 0, "layout_summary": []},
            ))

        # Build adjacency: find exec-connected nodes for topological sort
        # node_id -> list of exec-connected downstream node_ids
        exec_outputs: Dict[str, List[str]] = {}
        node_map: Dict[str, Dict] = {}
        for n in nodes:
            nid = n.get("node_id") or n.get("node_guid") or n.get("node_name") or ""
            node_map[nid] = n
            exec_outputs[nid] = []
            for p in n.get("pins") or []:
                direction = p.get("direction")
                is_exec = p.get("pin_type") in ("exec", "execute", "", None) and p.get("pin_name") in ("then", "execute", "Completed", "False", "True", "Out", "Done")
                if direction in ("output", "EGPD_Output", 1) and is_exec:
                    for link in p.get("linked_to") or []:
                        target = link.get("node_id") or link.get("node_guid") or ""
                        if target:
                            exec_outputs[nid].append(target)

        # Find root nodes (events / nodes with no exec-input connections)
        has_exec_input = set()
        for nid, targets in exec_outputs.items():
            for t in targets:
                has_exec_input.add(t)

        roots = [nid for nid in node_map if nid not in has_exec_input]

        # Topological BFS from each root
        ordered: List[str] = []
        visited: set = set()

        def bfs(start_id: str, col_offset: int):
            queue = [(start_id, col_offset)]
            while queue:
                nid, col = queue.pop(0)
                if nid in visited:
                    continue
                visited.add(nid)
                ordered.append((nid, col))
                for child in exec_outputs.get(nid, []):
                    queue.append((child, col + 1))

        col_counter = [0]
        chain_start_y = start_y
        chains = []
        for root in roots:
            if root in visited:
                continue
            chain = []
            before_visit = len(visited)
            bfs(root, 0)
            chain_end = len(ordered)
            chains.append((root, chain_start_y))
            chain_start_y += y_spacing * 3  # vertical separation between chains

        # Any unvisited nodes (disconnected islands)
        for nid in node_map:
            if nid not in visited:
                ordered.append((nid, 0))

        # Assign positions
        # Track max column per chain start for proper stacking
        layout_summary = []
        column_x: Dict[int, int] = {}  # col -> x position
        col_base_x = start_x
        chain_y_offset = start_y

        # Simple pass: assign position by topological order
        node_positions: Dict[str, tuple] = {}
        col_counters: Dict[int, int] = {}  # track how many nodes per column

        for i, (nid, col) in enumerate(ordered):
            x = start_x + col * x_spacing
            # Stack same-column nodes vertically
            count_in_col = col_counters.get(col, 0)
            y = start_y + count_in_col * y_spacing
            col_counters[col] = count_in_col + 1
            node_positions[nid] = (x, y)

        # Build reposition code
        reposition_lines = []
        for nid, (nx, ny) in node_positions.items():
            n = node_map[nid]
            title = n.get("node_name") or nid
            # We'll use set_node_position via exec_python if available, else skip
            reposition_lines.append(
                f"    # node: {title[:40]}\n"
                f"    _move_node('{nid}', {nx}, {ny})"
            )

        code = textwrap.dedent(f"""
            import unreal
            import json

            bp = unreal.load_asset('/Game/Blueprints/{blueprint_name}')
            if bp is None:
                reg = unreal.AssetRegistryHelpers.get_asset_registry()
                results = reg.get_assets_by_class('Blueprint', True)
                bp = next((unreal.load_asset(a.object_path) for a in results
                           if a.asset_name == '{blueprint_name}'), None)
            if bp is None:
                raise RuntimeError("Blueprint '{blueprint_name}' not found")

            graph = None
            for g in (bp.ubergraph_pages or []):
                if g.get_name() == '{graph_name}':
                    graph = g
                    break
            if graph is None:
                for g in (bp.function_graphs or []):
                    if g.get_name() == '{graph_name}':
                        graph = g
                        break
            if graph is None:
                raise RuntimeError("Graph '{graph_name}' not found in '{blueprint_name}'")

            node_map = {{n.get_name(): n for n in (graph.nodes or [])}}
            node_by_guid = {{str(n.node_guid): n for n in (graph.nodes or [])}}

            positions = {json.dumps({{nid: list(pos) for nid, pos in node_positions.items()}})}
            moved = 0

            def _move_node(node_id, nx, ny):
                global moved
                node = node_by_guid.get(node_id) or node_map.get(node_id)
                if node is None:
                    return
                node.node_pos_x = nx
                node.node_pos_y = ny
                moved += 1

            for nid, (nx, ny) in positions.items():
                _move_node(nid, int(nx), int(ny))

            unreal.BlueprintEditorLibrary.mark_blueprint_as_structurally_modified(bp)
            _result['nodes_repositioned'] = moved
        """)

        result = _exec_transactional(code, f"bp_auto_format_graph:{blueprint_name}/{graph_name}")

        layout_out = [
            {"node_id": nid, "new_x": pos[0], "new_y": pos[1]}
            for nid, pos in node_positions.items()
        ]

        if result.get("success"):
            result["outputs"]["layout_summary"] = layout_out
            result["message"] = (
                f"Formatted {result['outputs'].get('nodes_repositioned', len(node_positions))} "
                f"nodes in '{graph_name}'"
            )
        return json.dumps(result)

    # ──────────────────────────────────────────────────────────────────────────
    # bp_remove_node
    # ──────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def bp_remove_node(
        ctx: Context,
        blueprint_name: str,
        node_id: str,
        graph_name: str = "EventGraph",
    ) -> str:
        """Remove a node from a Blueprint graph by its node_id (GUID).

        Breaks all pin connections on the node before removing it so the graph
        is left in a valid (though possibly uncompiled) state.  The operation
        is NOT wrapped in a transaction on the Python side — the C++ bridge
        performs its own undo-mark.

        Use bp_get_graph_summary first to confirm the node_id you want to
        delete, then run bp_compile after removal to verify the graph is clean.

        Args:
            blueprint_name: Blueprint asset name (e.g. 'BP_MyActor')
            node_id:        Stable GUID of the node to delete (from
                            bp_get_graph_summary or bp_add_node outputs)
            graph_name:     Graph containing the node. Default 'EventGraph'.

        Returns:
            JSON StructuredResult.
            outputs.deleted_node_id   — GUID of the removed node
            outputs.deleted_node_name — Object name of the removed node
            outputs.next_steps        — Suggested follow-up actions
        """
        raw = _send("delete_blueprint_node", {
            "blueprint_name": blueprint_name,
            "graph_name": graph_name,
            "node_id": node_id,
        })

        if not raw or raw.get("success") is False or raw.get("status") == "error":
            msg = (raw or {}).get("error") or (raw or {}).get("message") or "delete_blueprint_node failed"
            return json.dumps(_make_result(
                success=False,
                stage="bp_remove_node",
                message=msg,
                errors=[msg],
            ))

        result_data = raw.get("result") or raw
        deleted_id   = result_data.get("deleted_node_id")   or node_id
        deleted_name = result_data.get("deleted_node_name") or ""

        return json.dumps(_make_result(
            success=True,
            stage="bp_remove_node",
            message=f"Removed node '{deleted_name}' ({deleted_id[:8]}) from '{graph_name}'",
            outputs={
                "blueprint": blueprint_name,
                "graph": graph_name,
                "deleted_node_id": deleted_id,
                "deleted_node_name": deleted_name,
                "next_steps": [
                    "Run bp_compile to verify the graph is still valid",
                    "Run bp_get_graph_summary to confirm the node is gone",
                ],
            },
        ))

    # ──────────────────────────────────────────────────────────────────────────
    # bp_disconnect_pin
    # ──────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def bp_disconnect_pin(
        ctx: Context,
        blueprint_name: str,
        node_id: str,
        pin_name: str,
        graph_name: str = "EventGraph",
        target_node_id: Optional[str] = None,
        target_pin_name: Optional[str] = None,
    ) -> str:
        """Break one or all connections on a specific pin.

        Two modes:
          • Break ALL connections on a pin — supply only node_id + pin_name.
          • Break ONE specific connection — also supply target_node_id +
            target_pin_name to break just that link.

        This is the inverse of bp_connect_pins.  Use bp_inspect_node first to
        confirm the exact pin names and their current connections.

        Args:
            blueprint_name:  Blueprint asset name
            node_id:         GUID of the node that owns the pin
            pin_name:        Exact pin name (case-sensitive)
            graph_name:      Graph containing the node. Default 'EventGraph'.
            target_node_id:  (optional) GUID of the other node — if supplied,
                             only the link to this node is broken.
            target_pin_name: (optional) Pin on the target node — required when
                             target_node_id is supplied.

        Returns:
            JSON StructuredResult.
            outputs.node_id          — GUID of the node whose pin was modified
            outputs.pin_name         — Pin that was disconnected
            outputs.mode             — 'break_all' or 'break_one'
        """
        # Choose Case A (break all) or Case B (break one) based on params
        if target_node_id:
            params: Dict[str, Any] = {
                "blueprint_name": blueprint_name,
                "graph_name": graph_name,
                "source_node_id": node_id,
                "source_pin": pin_name,
                "target_node_id": target_node_id,
                "target_pin": target_pin_name or "",
            }
            mode = "break_one"
        else:
            params = {
                "blueprint_name": blueprint_name,
                "graph_name": graph_name,
                "node_id": node_id,
                "pin_name": pin_name,
            }
            mode = "break_all"

        raw = _send("disconnect_blueprint_nodes", params)

        if not raw or raw.get("success") is False or raw.get("status") == "error":
            msg = (raw or {}).get("error") or (raw or {}).get("message") or "disconnect_blueprint_nodes failed"
            return json.dumps(_make_result(
                success=False,
                stage="bp_disconnect_pin",
                message=msg,
                errors=[msg],
            ))

        result_data = raw.get("result") or raw

        return json.dumps(_make_result(
            success=True,
            stage="bp_disconnect_pin",
            message=(
                f"Disconnected pin '{pin_name}' on node {node_id[:8]} "
                f"({'all links' if mode == 'break_all' else f'link to {(target_node_id or '')[:8]}'})"
            ),
            outputs={
                "blueprint": blueprint_name,
                "graph": graph_name,
                "node_id": result_data.get("node_id") or node_id,
                "pin_name": result_data.get("pin_name") or pin_name,
                "mode": mode,
                "next_steps": [
                    "Run bp_compile to verify the graph is still valid",
                    "Use bp_connect_pins to create a replacement connection if needed",
                ],
            },
        ))

    # ──────────────────────────────────────────────────────────────────────────
    # bp_add_function
    # ──────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def bp_add_function(
        ctx: Context,
        blueprint_name: str,
        function_name: str,
        return_type: str = "",
        params: Optional[str] = None,
        category: str = "",
        is_pure: bool = False,
        description: str = "",
    ) -> str:
        """Add a new function graph to a Blueprint.

        Creates a named function inside the Blueprint's function list.
        The function starts with a single 'entry' node.  After creation use
        bp_add_node / bp_connect_pins / bp_set_pin_default to build the
        function body, then bp_compile to validate.

        Args:
            blueprint_name: Blueprint asset name (e.g. 'BP_MyActor')
            function_name:  Name for the new function (e.g. 'TakeDamage')
            return_type:    Return pin type (e.g. 'float', 'bool', 'FVector').
                            Leave empty for void functions.
            params:         JSON array of parameter objects, each with keys
                            'name' (str) and 'type' (str).  E.g.:
                            '[{"name":"DamageAmount","type":"float"},
                              {"name":"DamageCauser","type":"AActor"}]'
            category:       Editor category for Blueprint palette grouping.
            is_pure:        True = pure function (no exec pins). Default False.
            description:    Tooltip text shown in Blueprint editor.

        Returns:
            JSON StructuredResult.
            outputs.function_name — Confirmed function name
            outputs.graph_name    — Graph name to use in subsequent bp_add_node calls
            outputs.next_steps    — Suggested follow-up actions
        """
        # Parse params JSON if supplied
        param_list: List[Dict[str, str]] = []
        parse_warnings: List[str] = []
        if params:
            try:
                param_list = json.loads(params)
                if not isinstance(param_list, list):
                    param_list = []
                    parse_warnings.append("'params' JSON was not a list — ignored")
            except json.JSONDecodeError as exc:
                parse_warnings.append(f"'params' JSON parse error: {exc} — no params added")

        # Build the Python code to run in UE via exec_substrate
        params_code_lines = []
        for p in param_list:
            pname = p.get("name", "")
            ptype = p.get("type", "bool")
            params_code_lines.append(
                f"    _add_param(func_graph, '{pname}', '{ptype}')"
            )

        return_code = ""
        if return_type:
            return_code = f"\n    _add_return(func_graph, '{return_type}')"

        params_body = "\n".join(params_code_lines) if params_code_lines else "    pass  # void, no params"

        pure_flag = "True" if is_pure else "False"

        code = textwrap.dedent(f"""
            import unreal

            def _find_bp(name):
                reg = unreal.AssetRegistryHelpers.get_asset_registry()
                results = reg.get_assets_by_class('Blueprint', True)
                for a in results:
                    if a.asset_name == name:
                        return unreal.load_asset(a.object_path)
                return None

            bp = unreal.load_asset('/Game/Blueprints/{blueprint_name}') or _find_bp('{blueprint_name}')
            if bp is None:
                raise RuntimeError("Blueprint '{blueprint_name}' not found")

            # Check for duplicate
            existing = [g.get_name() for g in (bp.function_graphs or [])]
            if '{function_name}' in existing:
                _result['function_name'] = '{function_name}'
                _result['graph_name'] = '{function_name}'
                _result['already_existed'] = True
            else:
                func_graph = unreal.BlueprintEditorLibrary.add_function_graph(bp, '{function_name}')
                if func_graph is None:
                    raise RuntimeError("add_function_graph returned None for '{function_name}'")

                def _add_param(g, pname, ptype):
                    # Use FunctionEntryNode to add params where possible
                    for n in (g.nodes or []):
                        if 'FunctionEntry' in type(n).__name__ or 'TunnelBase' in type(n).__name__:
                            try:
                                n.set_editor_property('extra_flags', 0)
                            except Exception:
                                pass
                            break

                def _add_return(g, rtype):
                    pass  # return type must be set via FunctionEntry — skip for safety

                if {pure_flag}:
                    try:
                        for n in (func_graph.nodes or []):
                            if 'FunctionEntry' in type(n).__name__:
                                n.set_editor_property('extra_flags', 0x00400000)  # FUNC_BlueprintPure
                                break
                    except Exception:
                        pass

{params_body}{return_code}

                unreal.BlueprintEditorLibrary.mark_blueprint_as_structurally_modified(bp)
                _result['function_name'] = '{function_name}'
                _result['graph_name'] = '{function_name}'
                _result['already_existed'] = False
        """)

        result = _exec_transactional(code, f"bp_add_function:{blueprint_name}/{function_name}")

        if not result.get("success"):
            return json.dumps(result)

        fn_name = result["outputs"].get("function_name") or function_name
        already = result["outputs"].get("already_existed", False)
        warnings_out = list(result.get("warnings") or []) + parse_warnings
        if already:
            warnings_out.append(f"Function '{fn_name}' already existed — returned existing graph")

        return json.dumps(_make_result(
            success=True,
            stage="bp_add_function",
            message=f"{'Found existing' if already else 'Created'} function '{fn_name}' in '{blueprint_name}'",
            outputs={
                "blueprint": blueprint_name,
                "function_name": fn_name,
                "graph_name": fn_name,
                "already_existed": already,
                "return_type": return_type or "(void)",
                "param_count": len(param_list),
                "next_steps": [
                    f"Use bp_add_node with graph_name='{fn_name}' to add nodes to the function body",
                    f"Use bp_get_graph_summary with graph_name='{fn_name}' to inspect the new graph",
                    "Run bp_compile when done to verify the function",
                ],
            },
            warnings=warnings_out,
        ))

    # ──────────────────────────────────────────────────────────────────────────
    # mat_create_material
    # ──────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def mat_create_material(
        ctx: Context,
        material_name: str,
        package_path: str = "/Game/Materials",
        blend_mode: str = "Opaque",
        shading_model: str = "DefaultLit",
        two_sided: bool = False,
    ) -> str:
        """Create a new Unreal Engine Material asset.

        Creates an empty material with the specified properties.  After
        creation use mat_add_expression and mat_connect_expressions to build
        the material graph, then mat_compile to validate.

        Blend modes:   Opaque, Masked, Translucent, Additive, Modulate
        Shading models: DefaultLit, Unlit, SubSurface, PreintegratedSkin,
                        ClearCoat, SubsurfaceProfile, TwoSidedFoliage,
                        Hair, Cloth, Eye, SingleLayerWater

        Args:
            material_name: Name for the new material asset (e.g. 'M_Rock')
            package_path:  Content Browser folder. Default '/Game/Materials'.
            blend_mode:    Material blend mode. Default 'Opaque'.
            shading_model: Shading model. Default 'DefaultLit'.
            two_sided:     Enable two-sided rendering. Default False.

        Returns:
            JSON StructuredResult.
            outputs.material_path — Full asset path (e.g. '/Game/Materials/M_Rock')
            outputs.next_steps    — Suggested follow-up actions
        """
        blend_map = {
            "opaque": "BLEND_Opaque",
            "masked": "BLEND_Masked",
            "translucent": "BLEND_Translucent",
            "additive": "BLEND_Additive",
            "modulate": "BLEND_Modulate",
        }
        blend_enum = blend_map.get(blend_mode.lower(), "BLEND_Opaque")

        shade_map = {
            "defaultlit": "MSM_DefaultLit",
            "unlit": "MSM_Unlit",
            "subsurface": "MSM_Subsurface",
            "preintegratedskin": "MSM_PreintegratedSkin",
            "clearcoat": "MSM_ClearCoat",
            "subsurfaceprofile": "MSM_SubsurfaceProfile",
            "twosidedfoliage": "MSM_TwoSidedFoliage",
            "hair": "MSM_Hair",
            "cloth": "MSM_Cloth",
            "eye": "MSM_Eye",
            "singlelayerwater": "MSM_SingleLayerWater",
        }
        shade_enum = shade_map.get(shading_model.lower().replace("_", ""), "MSM_DefaultLit")

        pkg = package_path.rstrip("/")
        full_path = f"{pkg}/{material_name}"
        two_sided_str = "True" if two_sided else "False"

        code = textwrap.dedent(f"""
            import unreal

            asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
            factory = unreal.MaterialFactoryNew()
            mat = asset_tools.create_asset('{material_name}', '{pkg}', unreal.Material, factory)
            if mat is None:
                # Asset may already exist
                mat = unreal.load_asset('{full_path}')
            if mat is None:
                raise RuntimeError("Failed to create or load material at '{full_path}'")

            mat.set_editor_property('blend_mode', unreal.BlendMode.{blend_enum})
            mat.set_editor_property('shading_model',
                unreal.MaterialShadingModel.{shade_enum})
            mat.set_editor_property('two_sided', {two_sided_str})

            unreal.EditorAssetLibrary.save_asset(mat.get_path_name())

            _result['material_path'] = mat.get_path_name()
            _result['material_name'] = '{material_name}'
        """)

        result = _exec_transactional(code, f"mat_create_material:{material_name}")
        if not result.get("success"):
            return json.dumps(result)

        mat_path = result["outputs"].get("material_path") or full_path
        return json.dumps(_make_result(
            success=True,
            stage="mat_create_material",
            message=f"Created material '{material_name}' at '{mat_path}'",
            outputs={
                "material_name": material_name,
                "material_path": mat_path,
                "blend_mode": blend_mode,
                "shading_model": shading_model,
                "two_sided": two_sided,
                "next_steps": [
                    f"Use mat_add_expression(material_path='{mat_path}', ...) to add nodes",
                    "Use mat_connect_expressions to wire node outputs to material inputs",
                    "Use mat_compile to validate the material",
                ],
            },
            warnings=list(result.get("warnings") or []),
        ))

    # ──────────────────────────────────────────────────────────────────────────
    # mat_add_expression
    # ──────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def mat_add_expression(
        ctx: Context,
        material_path: str,
        expression_type: str,
        position_x: int = 0,
        position_y: int = 0,
        expression_params: Optional[str] = None,
    ) -> str:
        """Add a material expression (node) to a Material asset.

        Common expression_type values:
          Texture        — TextureSample (provide texture_path in params)
          Multiply       — Multiply two inputs
          Add            — Add two inputs
          Lerp           — Linear interpolation
          Constant       — Single float constant (provide value in params)
          Constant3      — RGB vector constant (provide r,g,b in params)
          Constant4      — RGBA vector constant (provide r,g,b,a in params)
          Param_Scalar   — Scalar parameter (provide param_name in params)
          Param_Vector   — Vector parameter (provide param_name in params)
          Param_Texture  — Texture parameter (provide param_name in params)
          Fresnel        — Fresnel effect
          CheapContrast  — Cheap contrast adjustment
          Desaturation   — Desaturation
          OneMinus       — 1 - input
          VertexColor    — Vertex color input
          WorldPosition  — World position

        expression_params (JSON object):
          texture_path: str   — For TextureSample/Param_Texture
          param_name:   str   — For Param_* expressions
          value:        float — For Constant
          r,g,b,a:      float — For Constant3/Constant4

        Args:
            material_path:    Full asset path (e.g. '/Game/Materials/M_Rock')
            expression_type:  Expression class short name (see above)
            position_x:       Canvas X position. Default 0.
            position_y:       Canvas Y position. Default 0.
            expression_params: JSON object of expression-specific params.

        Returns:
            JSON StructuredResult.
            outputs.expression_index — Index for use in mat_connect_expressions
            outputs.expression_name  — Object name of the created expression
        """
        extra: Dict[str, Any] = {}
        if expression_params:
            try:
                extra = json.loads(expression_params)
            except json.JSONDecodeError as e:
                err_msg = f"expression_params JSON parse error: {e}"
                return json.dumps(_make_result(
                    success=False,
                    stage="mat_add_expression",
                    message=err_msg,
                    errors=[err_msg],
                ))

        # Map short name to UE class name
        expr_map = {
            "texture":          "MaterialExpressionTextureSample",
            "texturesample":    "MaterialExpressionTextureSample",
            "multiply":         "MaterialExpressionMultiply",
            "add":              "MaterialExpressionAdd",
            "subtract":         "MaterialExpressionSubtract",
            "divide":           "MaterialExpressionDivide",
            "lerp":             "MaterialExpressionLinearInterpolate",
            "constant":         "MaterialExpressionConstant",
            "constant3":        "MaterialExpressionConstant3Vector",
            "constant3vector":  "MaterialExpressionConstant3Vector",
            "constant4":        "MaterialExpressionConstant4Vector",
            "constant4vector":  "MaterialExpressionConstant4Vector",
            "param_scalar":     "MaterialExpressionScalarParameter",
            "scalarparameter":  "MaterialExpressionScalarParameter",
            "param_vector":     "MaterialExpressionVectorParameter",
            "vectorparameter":  "MaterialExpressionVectorParameter",
            "param_texture":    "MaterialExpressionTextureObjectParameter",
            "textureparameter": "MaterialExpressionTextureObjectParameter",
            "fresnel":          "MaterialExpressionFresnel",
            "cheapcontrast":    "MaterialExpressionCheapContrast",
            "desaturation":     "MaterialExpressionDesaturation",
            "oneminus":         "MaterialExpressionOneMinus",
            "vertexcolor":      "MaterialExpressionVertexColor",
            "worldposition":    "MaterialExpressionWorldPosition",
            "cameraposition":   "MaterialExpressionCameraPositionWS",
            "objectposition":   "MaterialExpressionObjectPositionWS",
            "panner":           "MaterialExpressionPanner",
            "rotator":          "MaterialExpressionRotator",
            "abs":              "MaterialExpressionAbs",
            "ceil":             "MaterialExpressionCeil",
            "floor":            "MaterialExpressionFloor",
            "clamp":            "MaterialExpressionClamp",
            "saturate":         "MaterialExpressionSaturate",
            "power":            "MaterialExpressionPower",
            "max":              "MaterialExpressionMax",
            "min":              "MaterialExpressionMin",
            "dot":              "MaterialExpressionDotProduct",
            "cross":            "MaterialExpressionCrossProduct",
            "normalize":        "MaterialExpressionNormalize",
            "texcoord":         "MaterialExpressionTextureCoordinate",
            "time":             "MaterialExpressionTime",
            "sine":             "MaterialExpressionSine",
            "cosine":           "MaterialExpressionCosine",
            "breakoutfloatcomponents": "MaterialExpressionBreakMaterialAttributes",
            "makeFloat3":       "MaterialExpressionAppendVector",
            "appendvector":     "MaterialExpressionAppendVector",
            "transform":        "MaterialExpressionTransform",
            "transformposition":"MaterialExpressionTransformPosition",
        }
        ue_class = expr_map.get(expression_type.lower().replace(" ", "").replace("_", ""), expression_type)

        # Build property-setting code for known expression types
        prop_lines = []
        if "Texture" in ue_class and "texture_path" in extra:
            prop_lines.append(f"    tex = unreal.load_asset('{extra['texture_path']}')")
            prop_lines.append("    if tex: expr.set_editor_property('texture', tex)")
        if "Parameter" in ue_class and "param_name" in extra:
            prop_lines.append(f"    expr.set_editor_property('parameter_name', unreal.Name('{extra['param_name']}'))")
        if "Constant3Vector" in ue_class:
            r = extra.get("r", 1.0); g = extra.get("g", 1.0); b = extra.get("b", 1.0)
            prop_lines.append(f"    expr.set_editor_property('constant', unreal.LinearColor({r}, {g}, {b}, 1.0))")
        elif "Constant4Vector" in ue_class:
            r = extra.get("r", 1.0); g = extra.get("g", 1.0); b = extra.get("b", 1.0); a = extra.get("a", 1.0)
            prop_lines.append(f"    expr.set_editor_property('constant', unreal.LinearColor({r}, {g}, {b}, {a}))")
        elif "Constant" in ue_class and "value" in extra:
            prop_lines.append(f"    expr.set_editor_property('r', float({extra['value']}))")

        prop_body = "\n".join(prop_lines) if prop_lines else "    pass"

        code = textwrap.dedent(f"""
            import unreal

            mat = unreal.load_asset('{material_path}')
            if mat is None:
                raise RuntimeError("Material not found: '{material_path}'")

            expr_class = unreal.load_class(None, '/Script/Engine.{ue_class}')
            if expr_class is None:
                raise RuntimeError("Expression class not found: {ue_class}")

            expr = unreal.MaterialEditingLibrary.create_material_expression(
                mat, expr_class, {position_x}, {position_y})
            if expr is None:
                raise RuntimeError("create_material_expression returned None")

{prop_body}

            # Return index = position in expressions array
            exprs = mat.get_editor_property('expressions') or []
            idx = len(exprs) - 1
            _result['expression_index'] = max(idx, 0)
            _result['expression_name'] = expr.get_name()
            _result['expression_class'] = '{ue_class}'
        """)

        result = _exec_transactional(code, f"mat_add_expression:{material_path}/{expression_type}")
        if not result.get("success"):
            return json.dumps(result)

        idx = result["outputs"].get("expression_index", 0)
        expr_name = result["outputs"].get("expression_name", "")
        return json.dumps(_make_result(
            success=True,
            stage="mat_add_expression",
            message=f"Added {ue_class} at ({position_x}, {position_y}) in '{material_path}'",
            outputs={
                "material_path": material_path,
                "expression_type": expression_type,
                "ue_class": ue_class,
                "expression_index": idx,
                "expression_name": expr_name,
                "position_x": position_x,
                "position_y": position_y,
                "next_steps": [
                    f"Use mat_connect_expressions to wire this expression (index {idx}) to others",
                    "Add more expressions before wiring them all together",
                    "Use mat_compile when the graph is complete",
                ],
            },
            warnings=list(result.get("warnings") or []),
        ))

    # ──────────────────────────────────────────────────────────────────────────
    # mat_connect_expressions
    # ──────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def mat_connect_expressions(
        ctx: Context,
        material_path: str,
        from_expression_name: str,
        from_output_name: str,
        to_expression_name: str,
        to_input_name: str,
    ) -> str:
        """Connect two material expression nodes or connect an expression to a material input.

        For material root input connections (BaseColor, Metallic, etc.) use
        '' (empty string) as to_expression_name and the slot name as to_input_name.

        Common material root input names:
          BaseColor, Metallic, Specular, Roughness, EmissiveColor, Opacity,
          OpacityMask, Normal, WorldPositionOffset, SubsurfaceColor,
          AmbientOcclusion, Refraction, PixelDepthOffset

        Common expression output names:
          RGB, R, G, B, A, (default) ''

        Args:
            material_path:        Full asset path to the Material
            from_expression_name: Object name of the source expression node
                                  (from mat_add_expression outputs.expression_name)
            from_output_name:     Output pin name on the source node (e.g. 'RGB', 'R', '')
            to_expression_name:   Object name of the target expression, OR '' to connect
                                  directly to a material root input slot
            to_input_name:        Input pin/slot name on the target (e.g. 'A', 'BaseColor')

        Returns:
            JSON StructuredResult.
        """
        # Connecting to the material root (empty to_expression_name)
        if not to_expression_name:
            code = textwrap.dedent(f"""
                import unreal

                mat = unreal.load_asset('{material_path}')
                if mat is None:
                    raise RuntimeError("Material not found: '{material_path}'")

                src_expr = None
                for e in (mat.get_editor_property('expressions') or []):
                    if e.get_name() == '{from_expression_name}':
                        src_expr = e
                        break
                if src_expr is None:
                    raise RuntimeError("Source expression '{from_expression_name}' not found")

                result = unreal.MaterialEditingLibrary.connect_material_property(
                    src_expr, '{from_output_name}',
                    unreal.MaterialProperty.__members__.get(
                        'MP_{to_input_name}'.upper(),
                        unreal.MaterialProperty.__members__.get(
                            'MP_' + '{to_input_name}'.replace(' ', '').upper(),
                            list(unreal.MaterialProperty.__members__.values())[0]
                        )
                    )
                )
                if not result:
                    raise RuntimeError("connect_material_property returned False — check pin/slot names")

                _result['connected'] = True
                _result['from'] = '{from_expression_name}'
                _result['to'] = 'MaterialRoot.{to_input_name}'
            """)
        else:
            code = textwrap.dedent(f"""
                import unreal

                mat = unreal.load_asset('{material_path}')
                if mat is None:
                    raise RuntimeError("Material not found: '{material_path}'")

                exprs = mat.get_editor_property('expressions') or []
                src_expr = next((e for e in exprs if e.get_name() == '{from_expression_name}'), None)
                dst_expr = next((e for e in exprs if e.get_name() == '{to_expression_name}'), None)
                if src_expr is None:
                    raise RuntimeError("Source expression '{from_expression_name}' not found")
                if dst_expr is None:
                    raise RuntimeError("Target expression '{to_expression_name}' not found")

                result = unreal.MaterialEditingLibrary.connect_material_expressions(
                    src_expr, '{from_output_name}',
                    dst_expr, '{to_input_name}')
                if not result:
                    raise RuntimeError("connect_material_expressions returned False — check output/input names")

                _result['connected'] = True
                _result['from'] = '{from_expression_name}.{from_output_name}'
                _result['to'] = '{to_expression_name}.{to_input_name}'
            """)

        result = _exec_transactional(
            code,
            f"mat_connect_expressions:{from_expression_name}->{to_expression_name or 'Root'}.{to_input_name}"
        )
        if not result.get("success"):
            return json.dumps(result)

        return json.dumps(_make_result(
            success=True,
            stage="mat_connect_expressions",
            message=(
                f"Connected {from_expression_name}.{from_output_name} → "
                f"{to_expression_name or 'Root'}.{to_input_name}"
            ),
            outputs={
                "material_path": material_path,
                "from": result["outputs"].get("from", f"{from_expression_name}.{from_output_name}"),
                "to":   result["outputs"].get("to",   f"{to_expression_name}.{to_input_name}"),
                "next_steps": [
                    "Continue adding and connecting expressions",
                    "Run mat_compile when the graph is complete to check for errors",
                ],
            },
            warnings=list(result.get("warnings") or []),
        ))

    # ──────────────────────────────────────────────────────────────────────────
    # mat_compile
    # ──────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def mat_compile(
        ctx: Context,
        material_path: str,
        save_after_compile: bool = True,
    ) -> str:
        """Compile (recompile) a Material and return structured errors/warnings.

        Always run this after finishing material expression edits.  Returns
        had_errors and a list of compile messages so the agent can diagnose
        and fix problems without opening the Material Editor.

        Args:
            material_path:      Full asset path (e.g. '/Game/Materials/M_Rock')
            save_after_compile: Also save the material asset. Default True.

        Returns:
            JSON StructuredResult.
            outputs.had_errors     — bool
            outputs.had_warnings   — bool
            outputs.error_count    — int
            outputs.warning_count  — int
            outputs.saved          — bool
        """
        save_flag = "True" if save_after_compile else "False"

        code = textwrap.dedent(f"""
            import unreal

            mat = unreal.load_asset('{material_path}')
            if mat is None:
                raise RuntimeError("Material not found: '{material_path}'")

            success = unreal.MaterialEditingLibrary.recompile_material(mat)
            _result['had_errors'] = not success
            _result['had_warnings'] = False  # UE Python API doesn't expose warnings separately
            _result['material_path'] = mat.get_path_name()

            if {save_flag} and success:
                unreal.EditorAssetLibrary.save_asset(mat.get_path_name())
                _result['saved'] = True
            else:
                _result['saved'] = False
        """)

        result = _exec_transactional(code, f"mat_compile:{material_path}")
        if not result.get("success"):
            return json.dumps(result)

        had_errors = result["outputs"].get("had_errors", False)
        saved = result["outputs"].get("saved", False)

        return json.dumps(_make_result(
            success=not had_errors,
            stage="mat_compile",
            message=(
                f"Material '{material_path}': {'ERRORS — check expression connections' if had_errors else 'OK'}"
                + (", saved" if saved else "")
            ),
            outputs={
                "material_path": material_path,
                "had_errors": had_errors,
                "had_warnings": result["outputs"].get("had_warnings", False),
                "error_count": 1 if had_errors else 0,
                "warning_count": 0,
                "saved": saved,
                "next_steps": (
                    [
                        "Check mat_connect_expressions calls — ensure every required slot is connected",
                        "Use mat_add_expression to add any missing expressions",
                        "Check expression_params (texture_path, param_name) for Texture/Parameter nodes",
                    ] if had_errors else [
                        "Material compiled successfully",
                        "Use mat_create_instance to create MaterialInstanceConstants from this material",
                    ]
                ),
            },
            warnings=list(result.get("warnings") or []),
            errors=["Material compilation failed — check expression connections"] if had_errors else [],
        ))

    logger.info(
        "Graph scripting core tools registered: "
        "bp_get_graph_summary, bp_create_graph, bp_add_node, bp_inspect_node, "
        "bp_connect_pins, bp_set_pin_default, bp_add_variable, bp_compile, "
        "bp_auto_format_graph, bp_remove_node, bp_disconnect_pin, bp_add_function, "
        "mat_create_material, mat_add_expression, mat_connect_expressions, mat_compile"
    )
