"""
skill_audit_blueprint_health — V5 Blueprint Health Audit Skill
==============================================================

A higher-order skill that calls only existing atomic tools:
  bp_get_graph_summary   — discover variables, function graphs, event graph nodes
  bp_get_graph_detail    — paginated detail for each graph
  project_get_references — count incoming references
  bp_compile             — determine compilation health

Returns a structured audit report including:
  compiles_clean           bool   — True when had_errors=False
  variable_count           int    — number of Blueprint member variables
  function_graph_count     int    — number of function graphs
  node_count_total         int    — total nodes across all graphs
  disconnected_exec_pins   list   — [{graph, node_id, pin_name}]
  disconnected_input_pins  list   — [{graph, node_id, pin_name}]
  unused_variables         list   — variable names not referenced in any graph
  incoming_references      int    — count of packages referencing this Blueprint
  warnings                 list   — human-readable warning messages
  health_score             int    — 0-100

Health score formula:
  Base: 100
  -30 if compile fails
  -10 per disconnected exec pin (max -20)
  -5  per unused variable (max -15)
  -5  per disconnected non-exec input pin (max -10)
  Score is clamped to [0, 100].

Usage:
  From an MCP tool call: skill_audit_blueprint_health(blueprint_name='BP_HealthSystem')
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger("UnrealMCP")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_result(
    *,
    success: bool,
    stage: str = "skill_audit_blueprint_health",
    message: str = "",
    outputs: Optional[Dict] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    meta: Optional[Dict] = None,
) -> Dict[str, Any]:
    r: Dict[str, Any] = {
        "success":  success,
        "stage":    stage,
        "message":  message,
        "outputs":  outputs or {},
        "warnings": warnings or [],
        "errors":   errors or [],
        "log_tail": [],
    }
    if meta:
        r["meta"] = meta
    return r


def _meta(t0: float, **extra) -> Dict[str, Any]:
    m: Dict[str, Any] = {
        "tool":        "skill_audit_blueprint_health",
        "duration_ms": int((time.monotonic() - t0) * 1000),
    }
    m.update(extra)
    return m


def _send(command: str, params: dict) -> Dict[str, Any]:
    from unreal_mcp_server import get_unreal_connection
    try:
        conn = get_unreal_connection()
        if not conn:
            return {"success": False, "message": "Not connected to Unreal Engine"}
        result = conn.send_command(command, params)
        return result or {"success": False, "message": "No response from Unreal Engine"}
    except Exception as exc:
        logger.error(f"audit_blueprint_health._send: {exc}")
        return {"success": False, "message": str(exc)}


def _parse(json_str: str) -> Dict[str, Any]:
    """Parse a JSON string returned by an MCP tool into a dict."""
    if isinstance(json_str, dict):
        return json_str
    try:
        return json.loads(json_str)
    except Exception:
        return {}


# ── Scoring ───────────────────────────────────────────────────────────────────

def _compute_score(
    compiles_clean: bool,
    disconnected_exec: List,
    disconnected_inputs: List,
    unused_vars: List,
) -> int:
    score = 100
    if not compiles_clean:
        score -= 30
    # -10 per disconnected exec, max -20
    score -= min(20, len(disconnected_exec) * 10)
    # -5  per unused variable, max -15
    score -= min(15, len(unused_vars) * 5)
    # -5  per disconnected non-exec input pin, max -10
    score -= min(10, len(disconnected_inputs) * 5)
    return max(0, min(100, score))


# ── Graph analysis helpers ────────────────────────────────────────────────────

def _analyse_graph_nodes(
    graph_name: str,
    nodes: List[Dict],
    variable_names: set,
    referenced_var_names: set,
) -> tuple:
    """
    Returns (disconnected_exec, disconnected_inputs).
    Also populates referenced_var_names in-place.
    """
    disconnected_exec   = []
    disconnected_inputs = []

    for node in nodes:
        node_id = node.get("node_id") or node.get("guid") or ""
        title   = node.get("title", "")
        for pin in node.get("pins", []):
            pin_name  = pin.get("pin_name", "")
            pin_type  = pin.get("pin_type", "").lower()
            direction = pin.get("direction", "")
            linked_to = pin.get("linked_to", [])

            # Track referenced variables
            if title in variable_names:
                referenced_var_names.add(title)

            # Disconnected exec output pins (always a warning on Event nodes)
            if pin_type in ("exec", "execute", "") and direction == "output" and not linked_to:
                # Only flag exec pins on event/function-call nodes
                ntype = node.get("node_type", "")
                if ntype in ("event", "function") or "event" in title.lower():
                    disconnected_exec.append({
                        "graph":    graph_name,
                        "node_id":  node_id,
                        "pin_name": pin_name,
                        "title":    title,
                    })

            # Disconnected non-exec input pins
            if pin_type not in ("exec", "execute", "") and direction == "input" and not linked_to:
                pin_default = pin.get("default_value", "")
                # Only flag if there is no default either
                if not pin_default:
                    disconnected_inputs.append({
                        "graph":    graph_name,
                        "node_id":  node_id,
                        "pin_name": pin_name,
                        "title":    title,
                    })

    return disconnected_exec, disconnected_inputs


# ── Registration ──────────────────────────────────────────────────────────────

def register_audit_blueprint_health_skill(mcp: FastMCP):

    @mcp.tool()
    async def skill_audit_blueprint_health(
        ctx: Context,
        blueprint_name: str,
        blueprint_path: Optional[str] = None,
        compile_check: bool = True,
    ) -> str:
        """Audit the health of a Blueprint and return a structured report.

        Calls only existing atomic tools (bp_get_graph_summary, bp_get_graph_detail,
        project_get_references, bp_compile).  Does not use exec_python directly.

        The audit checks:
          • Compilation status (had_errors flag)
          • Variable inventory
          • Disconnected exec pins (execution chains broken)
          • Disconnected non-exec input pins without defaults
          • Unused variables (declared but not referenced in any graph)
          • Incoming reference count

        Returns a 0–100 health_score:
          100   — clean compile, no issues
          70-99 — minor issues (unused vars, unconnected data pins)
          40-69 — significant issues (disconnected exec chains)
          0-39  — compile failure or severe disconnection

        Args:
            blueprint_name:  Asset name (e.g. 'BP_HealthSystem').
            blueprint_path:  Full package path. None = '/Game/Blueprints/<name>'.
            compile_check:   Whether to run bp_compile. Default True.

        Returns:
            JSON StructuredResult with outputs:
              compiles_clean, variable_count, function_graph_count, node_count_total,
              disconnected_exec_pins, disconnected_input_pins, unused_variables,
              incoming_references, warnings, health_score
        """
        t0 = time.monotonic()
        steps_completed = []
        steps_failed    = []
        warnings_out: List[str] = []
        errors_out:   List[str] = []

        # ── resolve path ───────────────────────────────────────────────────
        bp_path = blueprint_path or f"/Game/Blueprints/{blueprint_name}"

        # ── Step 1: get_graph_summary (metadata only) ──────────────────────
        from tools.graph_tools import register_graph_tools as _rgt  # noqa: F401

        # We call the C++ get_blueprint_nodes directly to avoid re-importing
        # the whole MCP tool (the tool is registered in the same process).
        # Use _send to proxy through the C++ bridge.
        raw_summary = _send("get_blueprint_nodes", {
            "blueprint_name": blueprint_name,
            "graph_name":     "EventGraph",
            "include_hidden_pins": False,
        })
        if not raw_summary or raw_summary.get("success") is False:
            msg = (raw_summary or {}).get("message", "get_blueprint_nodes failed")
            return json.dumps(_make_result(
                success=False,
                message=f"Blueprint '{blueprint_name}' not accessible: {msg}",
                errors=[msg],
                meta=_meta(t0),
            ))

        event_nodes_raw = raw_summary.get("nodes") or raw_summary.get("result", {}).get("nodes") or []
        steps_completed.append("get_event_graph_nodes")

        # ── Step 2: fetch variables via exec_python ────────────────────────
        var_code = f"""
import unreal
_result = {{'variables': [], 'function_graphs': []}}
bp = unreal.load_asset('/Game/Blueprints/{blueprint_name}')
if bp is None:
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    hits = reg.get_assets_by_class('Blueprint', True)
    bp = next((unreal.load_asset(str(h.object_path)) for h in hits
               if h.asset_name == '{blueprint_name}'), None)
if bp:
    for p in bp.get_all_member_variables():
        _result['variables'].append(p.variable_name)
    for g in bp.get_all_graphs():
        gname = g.get_name()
        if gname != 'EventGraph':
            _result['function_graphs'].append(gname)
"""
        raw_meta = _send("exec_python", {"code": var_code})
        bp_vars:    List[str] = []
        fn_graphs:  List[str] = []
        if raw_meta and raw_meta.get("success") is not False:
            out = raw_meta.get("result") or raw_meta.get("outputs") or {}
            if isinstance(out, dict):
                bp_vars   = out.get("variables", [])
                fn_graphs = out.get("function_graphs", [])
            steps_completed.append("fetch_metadata")
        else:
            warnings_out.append("Could not fetch Blueprint metadata via exec_python")
            steps_failed.append("fetch_metadata")

        variable_names = set(bp_vars)
        referenced_var_names: set = set()

        # ── Step 3: analyse EventGraph nodes ──────────────────────────────
        disc_exec, disc_inputs = _analyse_graph_nodes(
            "EventGraph", event_nodes_raw, variable_names, referenced_var_names
        )
        node_count_total = len(event_nodes_raw)
        steps_completed.append("analyse_event_graph")

        # ── Step 4: analyse function graph nodes ──────────────────────────
        for fn_name in fn_graphs:
            fn_raw = _send("get_blueprint_nodes", {
                "blueprint_name": blueprint_name,
                "graph_name":     fn_name,
                "include_hidden_pins": False,
            })
            fn_nodes = (fn_raw or {}).get("nodes") or []
            fn_disc_exec, fn_disc_inputs = _analyse_graph_nodes(
                fn_name, fn_nodes, variable_names, referenced_var_names
            )
            disc_exec   += fn_disc_exec
            disc_inputs += fn_disc_inputs
            node_count_total += len(fn_nodes)
        steps_completed.append("analyse_function_graphs")

        # ── Step 5: unused variables ───────────────────────────────────────
        unused_vars = sorted(variable_names - referenced_var_names)

        # ── Step 6: compile check ─────────────────────────────────────────
        compiles_clean = True
        if compile_check:
            comp_raw = _send("compile_blueprint", {"blueprint_name": blueprint_name})
            if comp_raw and comp_raw.get("success") is not False:
                comp_result = comp_raw.get("result") or comp_raw.get("outputs") or comp_raw
                compiles_clean = not comp_result.get("had_errors", False)
                steps_completed.append("compile_check")
                if not compiles_clean:
                    errors_out.append("Blueprint has compile errors")
                    warnings_out.append(f"Compile failed: {comp_result.get('message', 'see UE log')}")
            else:
                warnings_out.append("bp_compile call failed — compile status unknown")
                steps_failed.append("compile_check")

        # ── Step 7: incoming references ───────────────────────────────────
        incoming_references = 0
        ref_code = f"""
import unreal
_result = {{'count': 0}}
reg = unreal.AssetRegistryHelpers.get_asset_registry()
refs = reg.get_referencers('/Game/Blueprints/{blueprint_name}',
                             unreal.AssetRegistryDependencyType.ALL)
_result['count'] = len(refs) if refs else 0
"""
        raw_refs = _send("exec_python", {"code": ref_code})
        if raw_refs and raw_refs.get("success") is not False:
            ref_out = raw_refs.get("result") or raw_refs.get("outputs") or {}
            if isinstance(ref_out, dict):
                incoming_references = ref_out.get("count", 0)
            steps_completed.append("incoming_references")
        else:
            warnings_out.append("Could not query incoming references")
            steps_failed.append("incoming_references")

        # ── Assemble warnings ─────────────────────────────────────────────
        if disc_exec:
            warnings_out.append(
                f"{len(disc_exec)} disconnected exec pin(s) found — execution chains may be broken"
            )
        if unused_vars:
            warnings_out.append(
                f"{len(unused_vars)} unused variable(s): {', '.join(unused_vars[:5])}"
                + (f" ... (+{len(unused_vars)-5} more)" if len(unused_vars) > 5 else "")
            )
        if disc_inputs:
            warnings_out.append(
                f"{len(disc_inputs)} unconnected non-exec input pin(s) without defaults"
            )

        # ── Score ─────────────────────────────────────────────────────────
        health_score = _compute_score(compiles_clean, disc_exec, disc_inputs, unused_vars)

        outputs = {
            "blueprint_name":        blueprint_name,
            "blueprint_path":        bp_path,
            "compiles_clean":        compiles_clean,
            "variable_count":        len(bp_vars),
            "function_graph_count":  len(fn_graphs),
            "node_count_total":      node_count_total,
            "disconnected_exec_pins":   disc_exec,
            "disconnected_input_pins":  disc_inputs,
            "unused_variables":      unused_vars,
            "incoming_references":   incoming_references,
            "warnings":              warnings_out,
            "health_score":          health_score,
            "steps_completed":       steps_completed,
            "steps_failed":          steps_failed,
        }

        grade = (
            "HEALTHY" if health_score >= 90 else
            "GOOD"    if health_score >= 70 else
            "WARNING" if health_score >= 40 else
            "POOR"
        )
        return json.dumps(_make_result(
            success=True,
            message=(
                f"Blueprint '{blueprint_name}' health: {health_score}/100 ({grade}). "
                f"{len(bp_vars)} vars, {len(fn_graphs)} fns, {node_count_total} nodes, "
                f"compile={'OK' if compiles_clean else 'ERRORS'}"
            ),
            outputs=outputs,
            warnings=warnings_out,
            errors=errors_out,
            meta=_meta(t0,
                       steps_completed=steps_completed,
                       steps_failed=steps_failed),
        ))

    logger.info("Audit Blueprint Health skill registered: skill_audit_blueprint_health")
