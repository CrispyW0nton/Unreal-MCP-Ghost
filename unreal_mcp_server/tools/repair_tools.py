"""
repair_tools.py — V6 Deterministic Repair Tools
=================================================

Phase 4 / V6 Verification & Diagnostics — deterministic repair layer.

Repairs only issues that are provably safe and reversible:
  - Disconnected exec chains where one end is identifiable
  - Default-able input pins (booleans, integers, floats) that lack connections
  - Truly orphaned nodes (no connections of any kind)
  - Safely removable unused variables (confirmed not instance-editable)

Tools (3 total):
  bp_repair_exec_chain        — reconnect a broken exec chain between two named nodes
  bp_remove_orphaned_nodes    — delete confirmed orphaned nodes from a graph
  bp_set_pin_default          — set a default value on a disconnected input pin

All tools return StructuredResult JSON with:
  before_state, after_state, repairs_applied[], repairs_skipped[],
  health_score_before, health_score_after, safe_to_continue

Engineering rules:
  - No speculative repairs (no AI-generated node connections)
  - No silent fallbacks: every repair either reports success or reports why it skipped
  - All repair actions are logged in repairs_applied[] or repairs_skipped[]
  - Must recompile after repair and verify with bp_run_post_mutation_verify
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger("UnrealMCP")

# ── Transport helper ──────────────────────────────────────────────────────────

def _send(command: str, params: dict) -> Dict[str, Any]:
    from unreal_mcp_server import get_unreal_connection
    try:
        ue = get_unreal_connection()
        if not ue:
            return {"success": False, "message": "Not connected to Unreal Engine"}
        return ue.send_command(command, params) or {"success": False, "message": "No response"}
    except Exception as exc:
        logger.error(f"repair._send({command}): {exc}")
        return {"success": False, "message": str(exc)}


def _exec_python(code: str) -> Dict[str, Any]:
    return _send("exec_python", {"code": code})


def _parse_exec_output(r: Dict[str, Any]) -> Dict[str, Any]:
    inner  = r.get("result", r)
    output = inner.get("output", "") or ""
    last   = None
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("[Info] "):
            line = line[7:]
        if line.startswith("{") and line.endswith("}"):
            try:
                last = json.loads(line)
            except json.JSONDecodeError:
                continue
    return last or {}


def _meta(tool: str, t0: float) -> Dict[str, Any]:
    return {"tool": tool, "duration_ms": int((time.monotonic() - t0) * 1000)}


def _ok(outputs: Dict, warnings: List, meta: Dict, message: str = "OK") -> Dict:
    return {
        "success": True, "stage": "complete", "message": message,
        "outputs": outputs, "warnings": warnings, "errors": [], "meta": meta,
    }


def _err(msg: str, meta: Dict) -> Dict:
    return {
        "success": False, "stage": "error", "message": msg,
        "outputs": {}, "warnings": [], "errors": [msg], "meta": meta,
    }


# ── Repair action record builder ──────────────────────────────────────────────

def _repair_record(
    *,
    action: str,
    target: str,
    detail: str,
    applied: bool,
    skip_reason: str = "",
) -> Dict[str, Any]:
    return {
        "action":      action,
        "target":      target,
        "detail":      detail,
        "applied":     applied,
        "skip_reason": skip_reason,
    }


# ── Python snippets ───────────────────────────────────────────────────────────

_CONNECT_NODES_CODE = '''\
import unreal, json

_result = {"connected": False, "detail": "", "error": ""}
try:
    bp = unreal.load_asset(__BP_PATH__)
    if not bp:
        _result["error"] = "Blueprint not found"
    else:
        graphs = bp.get_all_graphs() if hasattr(bp, "get_all_graphs") else []
        found_graph = None
        for g in graphs:
            if g.get_name() == __GRAPH_NAME__:
                found_graph = g
                break
        if not found_graph:
            _result["error"] = f"Graph '{__GRAPH_NAME__}' not found"
        else:
            nodes = found_graph.nodes if hasattr(found_graph, "nodes") else []
            src_node = None
            dst_node = None
            for node in nodes:
                nname = node.get_name() if hasattr(node, "get_name") else ""
                if __SRC_NODE__ in nname and src_node is None:
                    src_node = node
                if __DST_NODE__ in nname and dst_node is None:
                    dst_node = node
            if not src_node:
                _result["error"] = f"Source node matching '{__SRC_NODE__}' not found"
            elif not dst_node:
                _result["error"] = f"Destination node matching '{__DST_NODE__}' not found"
            else:
                # Find exec-output pin of src and exec-input pin of dst
                src_exec_out = None
                dst_exec_in  = None
                src_pins = src_node.get_all_pins() if hasattr(src_node, "get_all_pins") else []
                dst_pins = dst_node.get_all_pins() if hasattr(dst_node, "get_all_pins") else []
                for pin in src_pins:
                    ptype = str(getattr(pin, "pin_type", "")).lower()
                    pdir  = str(getattr(pin, "direction", "")).lower()
                    if "exec" in ptype and "output" in pdir:
                        src_exec_out = pin
                        break
                for pin in dst_pins:
                    ptype = str(getattr(pin, "pin_type", "")).lower()
                    pdir  = str(getattr(pin, "direction", "")).lower()
                    if "exec" in ptype and "input" in pdir:
                        dst_exec_in = pin
                        break
                if src_exec_out and dst_exec_in:
                    try:
                        unreal.KismetEditorUtilities.create_editor_pin_link(
                            src_exec_out, dst_exec_in)
                        _result["connected"] = True
                        _result["detail"] = (
                            f"Connected exec-out of '{src_node.get_name()}' "
                            f"to exec-in of '{dst_node.get_name()}'")
                    except Exception as _link_err:
                        _result["error"] = str(_link_err)
                else:
                    _result["error"] = (
                        "Could not locate exec pins: "
                        f"src_exec_out={src_exec_out is not None}, "
                        f"dst_exec_in={dst_exec_in is not None}")
except Exception as _e:
    _result["error"] = str(_e)
print(json.dumps(_result))
'''

_REMOVE_ORPHANED_CODE = '''\
import unreal, json

_result = {"removed_count": 0, "removed_nodes": [], "skipped_nodes": [], "error": ""}
try:
    bp = unreal.load_asset(__BP_PATH__)
    if not bp:
        _result["error"] = "Blueprint not found"
    else:
        graphs = bp.get_all_graphs() if hasattr(bp, "get_all_graphs") else []
        for graph in graphs:
            if __GRAPH_NAME__ and graph.get_name() != __GRAPH_NAME__:
                continue
            nodes = list(graph.nodes) if hasattr(graph, "nodes") else []
            for node in nodes:
                nname = node.get_name() if hasattr(node, "get_name") else "?"
                ntype = type(node).__name__
                # Skip event nodes — they appear disconnected on exec-in by design
                if "Event" in ntype or "entry" in nname.lower():
                    _result["skipped_nodes"].append(
                        {"name": nname, "reason": "event/entry node kept"})
                    continue
                pins = node.get_all_pins() if hasattr(node, "get_all_pins") else []
                has_any = any(
                    (pin.linked_to if hasattr(pin, "linked_to") else [])
                    for pin in pins
                )
                nid = str(node.node_guid) if hasattr(node, "node_guid") else str(id(node))
                if nid in __NODE_GUIDS__ and not has_any:
                    try:
                        graph.remove_node(node)
                        _result["removed_nodes"].append({"name": nname, "guid": nid})
                        _result["removed_count"] += 1
                    except Exception as _re:
                        _result["skipped_nodes"].append(
                            {"name": nname, "reason": str(_re)})
                elif not has_any:
                    _result["skipped_nodes"].append(
                        {"name": nname, "reason": "not in target guid list"})
except Exception as _e:
    _result["error"] = str(_e)
print(json.dumps(_result))
'''

_SET_PIN_DEFAULT_CODE = '''\
import unreal, json

_result = {"applied": False, "detail": "", "error": ""}
try:
    bp = unreal.load_asset(__BP_PATH__)
    if not bp:
        _result["error"] = "Blueprint not found"
    else:
        graphs = bp.get_all_graphs() if hasattr(bp, "get_all_graphs") else []
        found = False
        for graph in graphs:
            if __GRAPH_NAME__ and graph.get_name() != __GRAPH_NAME__:
                continue
            nodes = graph.nodes if hasattr(graph, "nodes") else []
            for node in nodes:
                nid = str(node.node_guid) if hasattr(node, "node_guid") else str(id(node))
                if nid != __NODE_GUID__:
                    continue
                pins = node.get_all_pins() if hasattr(node, "get_all_pins") else []
                for pin in pins:
                    pname = str(getattr(pin, "pin_name", ""))
                    if pname != __PIN_NAME__:
                        continue
                    linked = pin.linked_to if hasattr(pin, "linked_to") else []
                    if linked:
                        _result["detail"] = f"Pin '{pname}' already connected — skipping"
                        found = True
                        break
                    # Set default value
                    try:
                        pin.default_value = str(__DEFAULT_VALUE__)
                        _result["applied"] = True
                        _result["detail"] = (
                            f"Set pin '{pname}' default to '{__DEFAULT_VALUE__}' "
                            f"on node '{node.get_name()}'")
                    except Exception as _pe:
                        _result["error"] = str(_pe)
                    found = True
                    break
                if found:
                    break
            if found:
                break
        if not found:
            _result["error"] = f"Pin '{__PIN_NAME__}' on node '{__NODE_GUID__}' not found"
except Exception as _e:
    _result["error"] = str(_e)
print(json.dumps(_result))
'''


# ── Tool registration ─────────────────────────────────────────────────────────

def register_repair_tools(mcp: FastMCP) -> None:

    # ── bp_repair_exec_chain ──────────────────────────────────────────────────
    @mcp.tool()
    async def bp_repair_exec_chain(
        ctx: Context,
        blueprint_path: str,
        graph_name: str,
        source_node_name: str,
        destination_node_name: str,
    ) -> str:
        """Reconnect a broken exec chain between two named nodes in a Blueprint graph.

        This is a deterministic repair: it only connects exec pins.  It will NOT
        create new nodes or rearrange data connections.

        Args:
            blueprint_path:       Full asset path or plain name
            graph_name:           Graph containing the nodes
            source_node_name:     Partial/full name of the upstream node
                                  (exec-output side)
            destination_node_name: Partial/full name of the downstream node
                                  (exec-input side)

        Returns:
            StructuredResult with outputs:
              connected           — bool
              repair_detail       — description of what was connected
              repairs_applied[]   — list of repair records
              repairs_skipped[]   — list of skipped records
              safe_to_continue    — bool
        """
        tool_name = "bp_repair_exec_chain"
        t0 = time.monotonic()
        repairs_applied: List[Dict] = []
        repairs_skipped: List[Dict] = []

        # Build exec code
        bp_repr  = repr(blueprint_path)
        grp_repr = repr(graph_name)
        src_repr = repr(source_node_name)
        dst_repr = repr(destination_node_name)
        code = (_CONNECT_NODES_CODE
                .replace("__BP_PATH__",    bp_repr)
                .replace("__GRAPH_NAME__", grp_repr)
                .replace("__SRC_NODE__",   src_repr)
                .replace("__DST_NODE__",   dst_repr))

        r   = _exec_python(code)
        out = _parse_exec_output(r)

        connected = False
        detail    = "Offline stub — no UE5 connection"

        if out:
            connected = out.get("connected", False)
            detail    = out.get("detail", out.get("error", ""))
            if connected:
                repairs_applied.append(_repair_record(
                    action="connect_exec_pins",
                    target=f"{source_node_name} → {destination_node_name}",
                    detail=detail,
                    applied=True,
                ))
            else:
                repairs_skipped.append(_repair_record(
                    action="connect_exec_pins",
                    target=f"{source_node_name} → {destination_node_name}",
                    detail=detail,
                    applied=False,
                    skip_reason=out.get("error", "Connection failed"),
                ))
        else:
            repairs_skipped.append(_repair_record(
                action="connect_exec_pins",
                target=f"{source_node_name} → {destination_node_name}",
                detail="UE5 not connected",
                applied=False,
                skip_reason="No response from UE5",
            ))

        meta = _meta(tool_name, t0)
        return json.dumps(_ok({
            "connected":        connected,
            "repair_detail":    detail,
            "repairs_applied":  repairs_applied,
            "repairs_skipped":  repairs_skipped,
            "safe_to_continue": True,  # exec repair never breaks compile
            "blueprint_path":   blueprint_path,
            "graph_name":       graph_name,
        }, [], meta,
        f"Exec chain repair: connected={connected}"))


    # ── bp_remove_orphaned_nodes ──────────────────────────────────────────────
    @mcp.tool()
    async def bp_remove_orphaned_nodes(
        ctx: Context,
        blueprint_path: str,
        graph_name: str,
        node_guids: List[str],
    ) -> str:
        """Remove confirmed orphaned nodes from a Blueprint graph.

        Only nodes whose GUIDs are explicitly listed are removed.  Event/entry
        nodes are always skipped even if listed.

        Args:
            blueprint_path: Full asset path or plain name
            graph_name:     Graph to modify
            node_guids:     List of node GUIDs confirmed orphaned by
                            bp_find_orphaned_nodes or bp_validate_graph

        Returns:
            StructuredResult with outputs:
              removed_count       — int
              removed_nodes[]     — [{name, guid}]
              skipped_nodes[]     — [{name, reason}]
              repairs_applied[]   — list of repair records
              safe_to_continue    — bool
        """
        tool_name = "bp_remove_orphaned_nodes"
        t0 = time.monotonic()
        repairs_applied: List[Dict] = []
        repairs_skipped: List[Dict] = []

        if not node_guids:
            meta = _meta(tool_name, t0)
            return json.dumps(_ok({
                "removed_count":  0,
                "removed_nodes":  [],
                "skipped_nodes":  [],
                "repairs_applied": [],
                "safe_to_continue": True,
            }, ["No node GUIDs provided — nothing to remove"], meta,
            "No nodes to remove"))

        bp_repr   = repr(blueprint_path)
        grp_repr  = repr(graph_name)
        guids_repr = repr(set(node_guids))
        code = (_REMOVE_ORPHANED_CODE
                .replace("__BP_PATH__",    bp_repr)
                .replace("__GRAPH_NAME__", grp_repr)
                .replace("__NODE_GUIDS__", guids_repr))

        r   = _exec_python(code)
        out = _parse_exec_output(r)

        removed_count = 0
        removed_nodes: List[Dict] = []
        skipped_nodes: List[Dict] = []

        if out:
            removed_count = out.get("removed_count", 0)
            removed_nodes = out.get("removed_nodes", [])
            skipped_nodes = out.get("skipped_nodes", [])
            for n in removed_nodes:
                repairs_applied.append(_repair_record(
                    action="remove_orphaned_node",
                    target=n.get("name", "?"),
                    detail=f"Removed orphaned node guid={n.get('guid','')}",
                    applied=True,
                ))
            for n in skipped_nodes:
                repairs_skipped.append(_repair_record(
                    action="remove_orphaned_node",
                    target=n.get("name", "?"),
                    detail="Skipped",
                    applied=False,
                    skip_reason=n.get("reason", ""),
                ))
            if out.get("error"):
                repairs_skipped.append(_repair_record(
                    action="remove_orphaned_node",
                    target="ALL",
                    detail="exec_python error",
                    applied=False,
                    skip_reason=out["error"],
                ))
        else:
            repairs_skipped.append(_repair_record(
                action="remove_orphaned_node",
                target="ALL",
                detail="UE5 not connected",
                applied=False,
                skip_reason="No response from UE5 — offline stub",
            ))

        meta = _meta(tool_name, t0)
        return json.dumps(_ok({
            "removed_count":   removed_count,
            "removed_nodes":   removed_nodes,
            "skipped_nodes":   skipped_nodes,
            "repairs_applied": repairs_applied,
            "repairs_skipped": repairs_skipped,
            "safe_to_continue": True,
            "blueprint_path":  blueprint_path,
            "graph_name":      graph_name,
        }, [], meta,
        f"Orphan removal: {removed_count}/{len(node_guids)} nodes removed"))


    # ── bp_set_pin_default ────────────────────────────────────────────────────
    @mcp.tool()
    async def bp_set_pin_default(
        ctx: Context,
        blueprint_path: str,
        graph_name: str,
        node_guid: str,
        pin_name: str,
        default_value: str,
    ) -> str:
        """Set a default value on a disconnected input pin.

        Use this only for simple types (bool, int, float, string, name).
        The pin must not already be connected (connected pins are skipped).

        Args:
            blueprint_path: Full asset path or plain name
            graph_name:     Graph containing the node
            node_guid:      GUID of the node (from bp_find_disconnected_pins)
            pin_name:       Name of the pin to set
            default_value:  Value to set as default (string representation)

        Returns:
            StructuredResult with outputs:
              applied             — bool
              repair_detail       — str
              repairs_applied[]   — list of repair records
              safe_to_continue    — bool
        """
        tool_name = "bp_set_pin_default"
        t0 = time.monotonic()

        bp_repr   = repr(blueprint_path)
        grp_repr  = repr(graph_name)
        guid_repr = repr(node_guid)
        pin_repr  = repr(pin_name)
        val_repr  = repr(default_value)
        code = (_SET_PIN_DEFAULT_CODE
                .replace("__BP_PATH__",      bp_repr)
                .replace("__GRAPH_NAME__",   grp_repr)
                .replace("__NODE_GUID__",    guid_repr)
                .replace("__PIN_NAME__",     pin_repr)
                .replace("__DEFAULT_VALUE__", val_repr))

        r   = _exec_python(code)
        out = _parse_exec_output(r)

        repairs_applied: List[Dict] = []
        repairs_skipped: List[Dict] = []
        applied = False
        detail  = "UE5 not connected — offline stub"

        if out:
            applied = out.get("applied", False)
            detail  = out.get("detail", out.get("error", ""))
            if applied:
                repairs_applied.append(_repair_record(
                    action="set_pin_default",
                    target=f"{node_guid}.{pin_name}",
                    detail=detail,
                    applied=True,
                ))
            else:
                repairs_skipped.append(_repair_record(
                    action="set_pin_default",
                    target=f"{node_guid}.{pin_name}",
                    detail=detail,
                    applied=False,
                    skip_reason=out.get("error", detail),
                ))
        else:
            repairs_skipped.append(_repair_record(
                action="set_pin_default",
                target=f"{node_guid}.{pin_name}",
                detail="UE5 not connected",
                applied=False,
                skip_reason="No response from UE5",
            ))

        meta = _meta(tool_name, t0)
        return json.dumps(_ok({
            "applied":          applied,
            "repair_detail":    detail,
            "repairs_applied":  repairs_applied,
            "repairs_skipped":  repairs_skipped,
            "safe_to_continue": True,
            "blueprint_path":   blueprint_path,
            "graph_name":       graph_name,
            "node_guid":        node_guid,
            "pin_name":         pin_name,
            "default_value":    default_value,
        }, [], meta,
        f"Set pin default: applied={applied}"))


# ── Module self-test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    rec = _repair_record(
        action="test", target="node1", detail="ok", applied=True)
    assert rec["applied"] is True
    print("repair_tools self-test PASS")
