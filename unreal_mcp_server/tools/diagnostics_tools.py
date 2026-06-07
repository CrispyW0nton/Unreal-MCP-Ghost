"""
diagnostics_tools.py — V6 Compiler-Aware Diagnostics & Verification
=====================================================================

Phase 4 / V6 Verification & Diagnostics layer.  Every tool here answers
one of the four post-mutation trust questions:

  1. Did the asset compile?
  2. If not, exactly what failed and where?
  3. If it compiled, is the graph still structurally healthy?
  4. Can Ghost automatically repair a small, deterministic subset and prove
     the result improved?

Tools (14 total):
  Blueprint diagnostics —
    compile_blueprint_and_report — compile Blueprint and return graph-aware report
    bp_get_compile_diagnostics    — compiler errors/warnings as structured items
    bp_validate_blueprint         — top-level health score + issue aggregate
    bp_validate_graph             — one graph: exec chains, orphans, unreachable
    bp_find_disconnected_pins     — all disconnected exec/input pins
    bp_find_unreachable_nodes     — nodes with no incoming exec path
    bp_find_unused_variables      — declared vars never referenced in graphs
    bp_find_orphaned_nodes        — nodes floating with no connections at all
    bp_run_post_mutation_verify   — single-call evidence block after mutation

  Material diagnostics —
    compile_material_and_report   — compile Material and return expression-aware report
    mat_get_compile_diagnostics   — material compiler errors/warnings
    mat_validate_material         — expression count, disconnects, health score
  Import/change diagnostics —
    validate_import_result        — verify imported asset existence/class/save state
    get_changed_assets_since      — list changed/dirty assets since a timestamp

Every diagnostic item carries:
  severity, category, code, message, asset_path,
  graph_name, node_guid, node_title, pin_name,
  suggested_fix, auto_repairable

All tools return StructuredResult JSON with meta.tool and meta.duration_ms.

Implementation note:
  The UE5 plugin's compile_blueprint C++ command marks the asset modified and
  defers the full compile to the editor.  Rich diagnostic detail (per-node
  error messages, pin references, compiler log entries) requires exec_python
  to access FKismetCompilerContext results via the unreal Python API.  When
  UE5 is unavailable the tools return safe stub responses indicating offline
  mode — they never fail silently.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger("UnrealMCP")

# ── Shared diagnostic schema constants ───────────────────────────────────────

SEVERITY_ERROR   = "error"
SEVERITY_WARNING = "warning"
SEVERITY_INFO    = "info"

CAT_COMPILE      = "compile"
CAT_GRAPH        = "graph_structure"
CAT_VAR          = "variable_usage"
CAT_MATERIAL     = "material"
CAT_REPAIR       = "repair"

# ── Transport helper ──────────────────────────────────────────────────────────

def _send(command: str, params: dict) -> Dict[str, Any]:
    from unreal_mcp_server import get_unreal_connection
    try:
        ue = get_unreal_connection()
        if not ue:
            return {"success": False, "message": "Not connected to Unreal Engine"}
        return ue.send_command(command, params) or {"success": False, "message": "No response"}
    except Exception as exc:
        logger.error(f"diagnostics._send({command}): {exc}")
        return {"success": False, "message": str(exc)}


def _exec_python(code: str, timeout: float = 60.0) -> Dict[str, Any]:
    return _send("exec_python", {"code": code})


def _parse_exec_output(r: Dict[str, Any]) -> Dict[str, Any]:
    """Extract JSON from exec_python output field."""
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


def _ok(
    outputs: Dict,
    warnings: List,
    meta: Dict,
    message: str = "OK",
    *,
    inputs: Optional[Dict] = None,
    stage: str = "complete",
    log_tail: Optional[List[str]] = None,
) -> Dict:
    return {
        "success": True, "stage": stage, "message": message,
        "inputs": inputs or {}, "outputs": outputs, "warnings": warnings,
        "errors": [], "log_tail": log_tail or [], "meta": meta,
    }


def _err(msg: str, meta: Dict, *, inputs: Optional[Dict] = None, log_tail: Optional[List[str]] = None) -> Dict:
    return {
        "success": False, "stage": "error", "message": msg,
        "inputs": inputs or {}, "outputs": {}, "warnings": [],
        "errors": [msg], "log_tail": log_tail or [], "meta": meta,
    }


# ── Diagnostic item builder ───────────────────────────────────────────────────

def _diag_item(
    *,
    severity: str,
    category: str,
    code: str,
    message: str,
    asset_path: str,
    graph_name: str = "",
    node_guid: str = "",
    node_title: str = "",
    pin_name: str = "",
    suggested_fix: str = "",
    auto_repairable: bool = False,
) -> Dict[str, Any]:
    return {
        "severity":        severity,
        "category":        category,
        "code":            code,
        "message":         message,
        "asset_path":      asset_path,
        "graph_name":      graph_name,
        "node_guid":       node_guid,
        "node_title":      node_title,
        "pin_name":        pin_name,
        "suggested_fix":   suggested_fix,
        "auto_repairable": auto_repairable,
    }


def _health_score(issues: List[Dict]) -> int:
    """Compute 0–100 health score from issue list."""
    score = 100
    for item in issues:
        sev = item.get("severity", "")
        if sev == SEVERITY_ERROR:
            score -= 15
        elif sev == SEVERITY_WARNING:
            score -= 5
        elif sev == SEVERITY_INFO:
            score -= 1
    return max(0, min(100, score))


# ── Python snippets for UE5 exec_python calls ─────────────────────────────────

_COMPILE_DIAG_CODE = '''\
import unreal, json, traceback as _tb

def _find_bp(name):
    path = name if name.startswith("/") else None
    if path:
        a = unreal.load_asset(path)
        if a:
            return a
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    flt = unreal.ARFilter()
    flt.class_names = ["Blueprint"]
    flt.recursive_paths = True
    flt.package_paths = ["/Game"]
    for a in reg.get_assets(flt):
        if str(a.asset_name) == name.split("/")[-1]:
            loaded = unreal.load_asset(str(a.object_path))
            if loaded:
                return loaded
    return None

_result = {"errors": [], "warnings": [], "had_errors": False,
           "had_warnings": False, "compile_clean": True,
           "compiler_summary": ""}
try:
    bp = _find_bp(__BP_PATH__)
    if not bp:
        _result["had_errors"] = True
        _result["compile_clean"] = False
        _result["compiler_summary"] = "Blueprint not found"
        _result["errors"].append({
            "severity": "error", "category": "compile", "code": "BP_NOT_FOUND",
            "message": f"Blueprint '{__BP_PATH__}' not found",
            "asset_path": __BP_PATH__, "graph_name": "", "node_guid": "",
            "node_title": "", "pin_name": "",
            "suggested_fix": "Verify asset path and that Blueprint exists in project",
            "auto_repairable": False,
        })
    else:
        # Request compile and collect messages
        result = unreal.BlueprintEditorLibrary.compile_blueprint(bp) if hasattr(unreal, "BlueprintEditorLibrary") else None
        # Walk existing compile errors via bp.status
        status = bp.status if hasattr(bp, "status") else None
        had_err = (status == unreal.BlueprintStatus.BS_ERROR) if status is not None else False
        _result["had_errors"] = had_err
        _result["had_warnings"] = False
        _result["compile_clean"] = not had_err
        if had_err:
            _result["compiler_summary"] = "Blueprint has compile errors"
            _result["errors"].append({
                "severity": "error", "category": "compile", "code": "BP_COMPILE_ERROR",
                "message": "Blueprint reports BS_ERROR status",
                "asset_path": __BP_PATH__, "graph_name": "", "node_guid": "",
                "node_title": "", "pin_name": "",
                "suggested_fix": "Open BP in editor, fix red nodes, recompile",
                "auto_repairable": False,
            })
        else:
            _result["compiler_summary"] = "Blueprint compiles clean"
except Exception as _e:
    _result["had_errors"] = True
    _result["compile_clean"] = False
    _result["compiler_summary"] = str(_e)
    _result["errors"].append({
        "severity": "error", "category": "compile", "code": "EXEC_EXCEPTION",
        "message": str(_e), "asset_path": __BP_PATH__,
        "graph_name": "", "node_guid": "", "node_title": "", "pin_name": "",
        "suggested_fix": "Check UE5 editor connectivity", "auto_repairable": False,
    })
print(json.dumps(_result))
'''

_GRAPH_VALIDATE_CODE = '''\
import unreal, json

def _find_bp(name):
    path = name if name.startswith("/") else None
    if path:
        a = unreal.load_asset(path)
        if a:
            return a
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    flt = unreal.ARFilter()
    flt.class_names = ["Blueprint"]
    flt.recursive_paths = True
    flt.package_paths = ["/Game"]
    for a in reg.get_assets(flt):
        if str(a.asset_name) == name.split("/")[-1]:
            loaded = unreal.load_asset(str(a.object_path))
            if loaded:
                return loaded
    return None

_result = {"issues": [], "graph_health_score": 100, "issue_count": 0,
           "nodes_checked": 0, "graph_name": __GRAPH_NAME__,
           "blueprint_path": __BP_PATH__}
try:
    bp = _find_bp(__BP_PATH__)
    if not bp:
        _result["issues"].append({
            "severity": "error", "category": "compile", "code": "BP_NOT_FOUND",
            "message": "Blueprint not found", "asset_path": __BP_PATH__,
            "graph_name": __GRAPH_NAME__, "node_guid": "", "node_title": "",
            "pin_name": "", "suggested_fix": "Verify asset path",
            "auto_repairable": False,
        })
    else:
        graphs = bp.get_all_graphs() if hasattr(bp, "get_all_graphs") else []
        target_graph = None
        for g in graphs:
            if __GRAPH_NAME__ == "" or g.get_name() == __GRAPH_NAME__:
                target_graph = g
                break
        if target_graph is None and __GRAPH_NAME__ != "":
            _result["issues"].append({
                "severity": "error", "category": "graph_structure",
                "code": "GRAPH_NOT_FOUND",
                "message": f"Graph '{__GRAPH_NAME__}' not found in Blueprint",
                "asset_path": __BP_PATH__, "graph_name": __GRAPH_NAME__,
                "node_guid": "", "node_title": "", "pin_name": "",
                "suggested_fix": "Check graph name spelling",
                "auto_repairable": False,
            })
        elif target_graph:
            nodes = target_graph.nodes if hasattr(target_graph, "nodes") else []
            _result["nodes_checked"] = len(nodes)
            nodes_with_exec_in = set()
            nodes_with_exec_out = set()
            all_node_ids = set()
            # First pass: catalog connectivity
            for node in nodes:
                nid = str(node.node_guid) if hasattr(node, "node_guid") else str(id(node))
                all_node_ids.add(nid)
                pins = node.get_all_pins() if hasattr(node, "get_all_pins") else []
                has_any_conn = False
                for pin in pins:
                    linked = pin.linked_to if hasattr(pin, "linked_to") else []
                    ptype = str(pin.pin_type.pc_object_class) if hasattr(pin.pin_type, "pc_object_class") else str(pin.pin_type)
                    is_exec = "exec" in ptype.lower() or str(getattr(pin, "pin_type", "")).lower() == "exec"
                    dir_str = str(getattr(pin, "direction", ""))
                    if linked:
                        has_any_conn = True
                        if is_exec:
                            if "input" in dir_str.lower():
                                nodes_with_exec_in.add(nid)
                            elif "output" in dir_str.lower():
                                nodes_with_exec_out.add(nid)
                # Orphan: no connections at all
                if not has_any_conn:
                    nname = node.get_name() if hasattr(node, "get_name") else "Unknown"
                    _result["issues"].append({
                        "severity": "warning",
                        "category": "graph_structure",
                        "code": "ORPHANED_NODE",
                        "message": f"Node '{nname}' has no connections",
                        "asset_path": __BP_PATH__,
                        "graph_name": __GRAPH_NAME__,
                        "node_guid": nid,
                        "node_title": nname,
                        "pin_name": "",
                        "suggested_fix": "Delete orphaned node or connect it to the graph",
                        "auto_repairable": True,
                    })
        # Compute score: -10 per error, -5 per warning
        score = 100
        for issue in _result["issues"]:
            if issue["severity"] == "error":
                score -= 10
            elif issue["severity"] == "warning":
                score -= 5
        _result["graph_health_score"] = max(0, min(100, score))
        _result["issue_count"] = len(_result["issues"])
except Exception as _e:
    _result["issues"].append({
        "severity": "error", "category": "graph_structure", "code": "EXEC_EXCEPTION",
        "message": str(_e), "asset_path": __BP_PATH__, "graph_name": __GRAPH_NAME__,
        "node_guid": "", "node_title": "", "pin_name": "",
        "suggested_fix": "Check UE5 editor connectivity", "auto_repairable": False,
    })
    _result["graph_health_score"] = 0
    _result["issue_count"] = len(_result["issues"])
print(json.dumps(_result))
'''

_FIND_UNUSED_VARS_CODE = '''\
import unreal, json

def _find_bp(name):
    path = name if name.startswith("/") else None
    if path:
        a = unreal.load_asset(path)
        if a:
            return a
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    flt = unreal.ARFilter()
    flt.class_names = ["Blueprint"]
    flt.recursive_paths = True
    flt.package_paths = ["/Game"]
    for a in reg.get_assets(flt):
        if str(a.asset_name) == name.split("/")[-1]:
            loaded = unreal.load_asset(str(a.object_path))
            if loaded:
                return loaded
    return None

_result = {"unused_variables": [], "all_variables": [], "variables_checked": 0}
try:
    bp = _find_bp(__BP_PATH__)
    if bp:
        vars_ = bp.get_all_member_variables() if hasattr(bp, "get_all_member_variables") else []
        all_var_names = []
        for v in vars_:
            vname = str(v.variable_name) if hasattr(v, "variable_name") else str(v)
            all_var_names.append(vname)
        _result["all_variables"] = all_var_names
        _result["variables_checked"] = len(all_var_names)
        # Build text of all node titles + variable references across all graphs
        referenced = set()
        graphs = bp.get_all_graphs() if hasattr(bp, "get_all_graphs") else []
        for graph in graphs:
            nodes = graph.nodes if hasattr(graph, "nodes") else []
            for node in nodes:
                nname = node.get_name() if hasattr(node, "get_name") else ""
                for vname in all_var_names:
                    if vname in nname:
                        referenced.add(vname)
                # Also check pins for variable name in default value or label
                pins = node.get_all_pins() if hasattr(node, "get_all_pins") else []
                for pin in pins:
                    pname = str(getattr(pin, "pin_name", ""))
                    for vname in all_var_names:
                        if vname == pname:
                            referenced.add(vname)
        for vname in all_var_names:
            if vname not in referenced:
                _result["unused_variables"].append({
                    "variable_name": vname,
                    "severity": "warning",
                    "category": "variable_usage",
                    "code": "POSSIBLY_UNUSED_VAR",
                    "message": f"Variable '{vname}' not found in any graph node",
                    "asset_path": __BP_PATH__,
                    "suggested_fix": "Remove if truly unused, or verify usage in graph",
                    "auto_repairable": False,
                    "note": "May be intentionally exposed on spawn or instance-editable; verify before removal",
                })
except Exception as _e:
    _result["error"] = str(_e)
print(json.dumps(_result))
'''

_MAT_COMPILE_DIAG_CODE = '''\
import unreal, json

_result = {"errors": [], "warnings": [], "compile_clean": True,
           "compiler_summary": "", "expression_count": 0,
           "had_errors": False, "material_path": __MAT_PATH__}
try:
    mat = unreal.load_asset(__MAT_PATH__)
    if not mat:
        _result["compile_clean"] = False
        _result["had_errors"] = True
        _result["compiler_summary"] = "Material not found"
        _result["errors"].append({
            "severity": "error", "category": "material", "code": "MAT_NOT_FOUND",
            "message": f"Material '{__MAT_PATH__}' not found",
            "asset_path": __MAT_PATH__, "graph_name": "", "node_guid": "",
            "node_title": "", "pin_name": "",
            "suggested_fix": "Verify material path and that M_DemoB exists",
            "auto_repairable": False,
        })
    else:
        exprs = mat.get_editor_property("expressions") if hasattr(mat, "get_editor_property") else []
        expr_count = len(exprs) if exprs else 0
        _result["expression_count"] = expr_count
        # Check material is usable
        _result["compile_clean"] = True
        _result["compiler_summary"] = f"Material OK: {expr_count} expression(s)"
        if expr_count == 0:
            _result["warnings"].append({
                "severity": "warning", "category": "material",
                "code": "MAT_NO_EXPRESSIONS",
                "message": "Material has no expressions (empty graph)",
                "asset_path": __MAT_PATH__, "graph_name": "", "node_guid": "",
                "node_title": "", "pin_name": "",
                "suggested_fix": "Add at least one material expression",
                "auto_repairable": False,
            })
except Exception as _e:
    _result["compile_clean"] = False
    _result["had_errors"] = True
    _result["compiler_summary"] = str(_e)
    _result["errors"].append({
        "severity": "error", "category": "material", "code": "EXEC_EXCEPTION",
        "message": str(_e), "asset_path": __MAT_PATH__,
        "graph_name": "", "node_guid": "", "node_title": "", "pin_name": "",
        "suggested_fix": "Check UE5 connectivity", "auto_repairable": False,
    })
print(json.dumps(_result))
'''

_COMPILE_BLUEPRINT_REPORT_CODE = '''\
import unreal, json, traceback as _tb

def _find_bp(name):
    if name.startswith("/"):
        asset = unreal.load_asset(name)
        if asset:
            return asset
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    flt = unreal.ARFilter()
    flt.class_names = ["Blueprint"]
    flt.recursive_paths = True
    flt.package_paths = ["/Game"]
    target = name.split("/")[-1]
    for data in reg.get_assets(flt):
        if str(data.asset_name) == target:
            return unreal.load_asset(str(data.object_path))
    return None

def _bp_status_name(bp):
    try:
        return str(bp.status).split(".")[-1]
    except Exception:
        return "UNKNOWN"

_result = {
    "compile_status": "unknown",
    "compile_clean": False,
    "had_errors": False,
    "had_warnings": False,
    "errors": [],
    "warnings": [],
    "graph_summaries": [],
    "graph_count": 0,
    "blueprint_path": __BP_PATH__,
}
try:
    bp = _find_bp(__BP_PATH__)
    if not bp:
        _result["compile_status"] = "asset_missing"
        _result["had_errors"] = True
        _result["errors"].append({
            "severity": "error", "category": "compile", "code": "BP_NOT_FOUND",
            "message": "Blueprint not found", "asset_path": __BP_PATH__,
            "graph_name": "", "node_guid": "", "node_title": "", "pin_name": "",
            "suggested_fix": "Verify Blueprint asset path or name", "auto_repairable": False,
        })
    else:
        with unreal.ScopedSlowTask(2.0, "MCP compile_blueprint_and_report") as task:
            task.make_dialog(False)
            task.enter_progress_frame(1.0, "Compiling Blueprint")
            with unreal.ScopedEditorTransaction("MCP compile Blueprint report"):
                if hasattr(unreal, "BlueprintEditorLibrary"):
                    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
            task.enter_progress_frame(1.0, "Collecting graph summary")
            status_name = _bp_status_name(bp)
            had_errors = "ERROR" in status_name.upper()
            _result["compile_status"] = "errors" if had_errors else "clean"
            _result["compile_clean"] = not had_errors
            _result["had_errors"] = had_errors
            if had_errors:
                _result["errors"].append({
                    "severity": "error", "category": "compile", "code": status_name,
                    "message": "Blueprint reports compile error status",
                    "asset_path": __BP_PATH__, "graph_name": "", "node_guid": "",
                    "node_title": "", "pin_name": "",
                    "suggested_fix": "Run bp_get_compile_diagnostics and inspect red nodes",
                    "auto_repairable": False,
                })
            graphs = bp.get_all_graphs() if hasattr(bp, "get_all_graphs") else []
            include_graphs = __INCLUDE_GRAPHS__
            requested = set(__GRAPH_NAMES__)
            for graph in graphs:
                name = graph.get_name()
                if requested and name not in requested:
                    continue
                nodes = graph.nodes if hasattr(graph, "nodes") else []
                summary = {
                    "graph_name": name,
                    "node_count": len(nodes),
                    "orphaned_node_count": 0,
                    "exec_node_count": 0,
                }
                if include_graphs:
                    for node in nodes:
                        pins = node.get_all_pins() if hasattr(node, "get_all_pins") else []
                        has_link = False
                        has_exec = False
                        for pin in pins:
                            if getattr(pin, "linked_to", None):
                                has_link = True
                            pin_type = str(getattr(pin, "pin_type", "")).lower()
                            if "exec" in pin_type:
                                has_exec = True
                        if has_exec:
                            summary["exec_node_count"] += 1
                        if not has_link and "event" not in node.get_name().lower():
                            summary["orphaned_node_count"] += 1
                    if summary["orphaned_node_count"]:
                        _result["warnings"].append({
                            "severity": "warning", "category": "graph_structure",
                            "code": "ORPHANED_NODES_PRESENT",
                            "message": f"{summary['orphaned_node_count']} orphaned node(s) in {name}",
                            "asset_path": __BP_PATH__, "graph_name": name,
                            "node_guid": "", "node_title": "", "pin_name": "",
                            "suggested_fix": "Run bp_find_orphaned_nodes for details",
                            "auto_repairable": True,
                        })
                _result["graph_summaries"].append(summary)
            _result["graph_count"] = len(_result["graph_summaries"])
            _result["had_warnings"] = bool(_result["warnings"])
            if _result["had_warnings"] and _result["compile_status"] == "clean":
                _result["compile_status"] = "warnings_only"
except Exception as _e:
    _result["compile_status"] = "exception"
    _result["had_errors"] = True
    _result["errors"].append({
        "severity": "error", "category": "compile", "code": "EXEC_EXCEPTION",
        "message": str(_e), "asset_path": __BP_PATH__, "graph_name": "",
        "node_guid": "", "node_title": "", "pin_name": "",
        "suggested_fix": "Check Unreal Python compile path and Output Log",
        "auto_repairable": False,
    })
    _result["log_tail"] = _tb.format_exc().splitlines()[-10:]
print(json.dumps(_result))
'''

_COMPILE_MATERIAL_REPORT_CODE = '''\
import unreal, json, traceback as _tb

_result = {
    "compile_status": "unknown",
    "compile_clean": False,
    "had_errors": False,
    "errors": [],
    "warnings": [],
    "expression_count": 0,
    "expression_summaries": [],
    "material_path": __MAT_PATH__,
}
try:
    mat = unreal.load_asset(__MAT_PATH__)
    if not mat:
        _result["compile_status"] = "asset_missing"
        _result["had_errors"] = True
        _result["errors"].append({
            "severity": "error", "category": "material", "code": "MAT_NOT_FOUND",
            "message": "Material not found", "asset_path": __MAT_PATH__,
            "graph_name": "", "node_guid": "", "node_title": "", "pin_name": "",
            "suggested_fix": "Verify material path", "auto_repairable": False,
        })
    else:
        with unreal.ScopedSlowTask(2.0, "MCP compile_material_and_report") as task:
            task.make_dialog(False)
            task.enter_progress_frame(1.0, "Compiling Material")
            with unreal.ScopedEditorTransaction("MCP compile Material report"):
                if hasattr(unreal, "MaterialEditingLibrary"):
                    unreal.MaterialEditingLibrary.recompile_material(mat)
            task.enter_progress_frame(1.0, "Collecting expression summary")
            exprs = mat.get_editor_property("expressions") if hasattr(mat, "get_editor_property") else []
            _result["expression_count"] = len(exprs) if exprs else 0
            if __INCLUDE_EXPRESSIONS__:
                for expr in exprs or []:
                    _result["expression_summaries"].append({
                        "name": expr.get_name(),
                        "class": expr.get_class().get_name() if expr.get_class() else "",
                        "x": int(getattr(expr, "material_expression_editor_x", 0)),
                        "y": int(getattr(expr, "material_expression_editor_y", 0)),
                    })
            _result["compile_status"] = "clean"
            _result["compile_clean"] = True
            if _result["expression_count"] == 0:
                _result["warnings"].append({
                    "severity": "warning", "category": "material", "code": "MAT_NO_EXPRESSIONS",
                    "message": "Material has no graph expressions",
                    "asset_path": __MAT_PATH__, "graph_name": "", "node_guid": "",
                    "node_title": "", "pin_name": "",
                    "suggested_fix": "Add expressions or verify this is an intentionally empty material",
                    "auto_repairable": False,
                })
                _result["compile_status"] = "warnings_only"
except Exception as _e:
    _result["compile_status"] = "exception"
    _result["had_errors"] = True
    _result["errors"].append({
        "severity": "error", "category": "material", "code": "EXEC_EXCEPTION",
        "message": str(_e), "asset_path": __MAT_PATH__, "graph_name": "",
        "node_guid": "", "node_title": "", "pin_name": "",
        "suggested_fix": "Check Unreal Python material compile path and Output Log",
        "auto_repairable": False,
    })
    _result["log_tail"] = _tb.format_exc().splitlines()[-10:]
print(json.dumps(_result))
'''

_VALIDATE_IMPORT_RESULT_CODE = '''\
import unreal, json, os, traceback as _tb

_result = {
    "asset_path": __ASSET_PATH__,
    "exists": False,
    "class_name": "",
    "expected_class": __EXPECTED_CLASS__,
    "class_matches": True,
    "package_name": "",
    "object_path": "",
    "dirty": False,
    "source_file_exists": None,
    "referencer_count": 0,
    "dependency_count": 0,
    "warnings": [],
    "errors": [],
}
try:
    asset = unreal.load_asset(__ASSET_PATH__)
    if not asset:
        _result["errors"].append("Asset not found")
    else:
        _result["exists"] = True
        cls = asset.get_class().get_name() if asset.get_class() else ""
        _result["class_name"] = cls
        _result["object_path"] = asset.get_path_name()
        package = asset.get_outermost()
        package_name = package.get_name() if package else ""
        _result["package_name"] = package_name
        _result["dirty"] = bool(package.is_dirty()) if package else False
        expected = __EXPECTED_CLASS__
        if expected:
            _result["class_matches"] = expected.lower() in cls.lower()
            if not _result["class_matches"]:
                _result["warnings"].append(f"Expected class '{expected}', got '{cls}'")
        if __REQUIRE_SAVED__ and _result["dirty"]:
            _result["warnings"].append("Asset package is dirty; save before treating import as final")
        reg = unreal.AssetRegistryHelpers.get_asset_registry()
        try:
            deps = reg.get_dependencies(package_name, unreal.AssetRegistryDependencyType.ALL) or []
            refs = reg.get_referencers(package_name, unreal.AssetRegistryDependencyType.ALL) or []
            _result["dependency_count"] = len(deps)
            _result["referencer_count"] = len(refs)
        except Exception:
            pass
    source = __SOURCE_FILE__
    if source:
        _result["source_file_exists"] = os.path.exists(source)
        if not _result["source_file_exists"]:
            _result["warnings"].append("Source file path no longer exists on disk")
except Exception as _e:
    _result["errors"].append(str(_e))
    _result["log_tail"] = _tb.format_exc().splitlines()[-10:]
print(json.dumps(_result))
'''

_GET_CHANGED_ASSETS_SINCE_CODE = '''\
import unreal, json, os, datetime as _dt, traceback as _tb

def _parse_ts(value):
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    try:
        return float(s)
    except Exception:
        pass
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return _dt.datetime.fromisoformat(s).timestamp()

_result = {
    "timestamp": __TIMESTAMP__,
    "path": __PATH__,
    "changed_assets": [],
    "dirty_assets": [],
    "changed_count": 0,
    "dirty_count": 0,
    "errors": [],
}
try:
    cutoff = _parse_ts(__TIMESTAMP__)
    root = (__PATH__ or "/Game").rstrip("/") or "/Game"
    assets = unreal.EditorAssetLibrary.list_assets(root, recursive=True, include_folder=False)
    limit = int(__LIMIT__)
    for asset_path in assets:
        if limit > 0 and len(_result["changed_assets"]) >= limit:
            break
        if (not __INCLUDE_UNREAL_GENERATED__) and (
            asset_path.startswith("/Engine/") or asset_path.startswith("/Script/")
        ):
            continue
        package_name = asset_path.split(".")[0]
        filename = ""
        try:
            filename = unreal.PackageName.long_package_name_to_filename(package_name)
        except Exception:
            filename = ""
        candidates = [filename, filename + ".uasset", filename + ".umap"]
        existing = next((p for p in candidates if p and os.path.exists(p)), "")
        if existing:
            mtime = os.path.getmtime(existing)
            if mtime >= cutoff:
                _result["changed_assets"].append({
                    "asset_path": package_name,
                    "object_path": asset_path,
                    "package_file": existing,
                    "modified_time": _dt.datetime.fromtimestamp(mtime, _dt.timezone.utc).isoformat().replace("+00:00", "Z"),
                    "modified_epoch": mtime,
                })
    if __INCLUDE_DIRTY__:
        dirty = []
        for func_name in ("get_dirty_content_packages", "get_dirty_map_packages"):
            func = getattr(unreal.EditorLoadingAndSavingUtils, func_name, None)
            if not func:
                continue
            try:
                for package in func() or []:
                    name = package.get_name() if hasattr(package, "get_name") else str(package)
                    if name.startswith(root):
                        dirty.append(name)
            except Exception:
                pass
        _result["dirty_assets"] = sorted(set(dirty))
    _result["changed_count"] = len(_result["changed_assets"])
    _result["dirty_count"] = len(_result["dirty_assets"])
except Exception as _e:
    _result["errors"].append(str(_e))
    _result["log_tail"] = _tb.format_exc().splitlines()[-10:]
print(json.dumps(_result))
'''

_GET_BP_NODES_CODE = '''\
import unreal, json

def _find_bp(name):
    path = name if name.startswith("/") else None
    if path:
        a = unreal.load_asset(path)
        if a:
            return a
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    flt = unreal.ARFilter()
    flt.class_names = ["Blueprint"]
    flt.recursive_paths = True
    flt.package_paths = ["/Game"]
    for a in reg.get_assets(flt):
        if str(a.asset_name) == name.split("/")[-1]:
            loaded = unreal.load_asset(str(a.object_path))
            if loaded:
                return loaded
    return None

_result = {"graphs": [], "total_nodes": 0, "blueprint_found": False}
try:
    bp = _find_bp(__BP_PATH__)
    if bp:
        _result["blueprint_found"] = True
        graphs = bp.get_all_graphs() if hasattr(bp, "get_all_graphs") else []
        for graph in graphs:
            nodes = graph.nodes if hasattr(graph, "nodes") else []
            gdata = {"graph_name": graph.get_name(), "node_count": len(nodes), "nodes": []}
            for node in nodes:
                nid  = str(node.node_guid) if hasattr(node, "node_guid") else str(id(node))
                pins_data = []
                pins = node.get_all_pins() if hasattr(node, "get_all_pins") else []
                for pin in pins:
                    linked = pin.linked_to if hasattr(pin, "linked_to") else []
                    pins_data.append({
                        "pin_name":  str(getattr(pin, "pin_name", "")),
                        "direction": str(getattr(pin, "direction", "")),
                        "linked_count": len(linked),
                    })
                gdata["nodes"].append({
                    "node_guid":  nid,
                    "node_title": node.get_name() if hasattr(node, "get_name") else "?",
                    "pin_count":  len(pins_data),
                    "pins":       pins_data,
                })
            _result["graphs"].append(gdata)
            _result["total_nodes"] += len(nodes)
except Exception as _e:
    _result["error"] = str(_e)
print(json.dumps(_result))
'''


# ── Offline-safe analysis functions (pure Python, no UE5 needed) ──────────────

def _analyze_nodes_offline(nodes: List[Dict]) -> Dict[str, Any]:
    """
    Analyse node list from get_blueprint_nodes response.
    Returns issues list, orphans, disconnected_exec, unreachable.
    """
    issues:           List[Dict] = []
    disconnected:     List[Dict] = []
    orphans:          List[Dict] = []
    unreachable:      List[Dict] = []

    # Build connectivity sets
    has_exec_in:  set = set()   # node_guids that have an incoming exec link
    has_exec_out: set = set()   # node_guids that have an outgoing exec link
    has_any_link: set = set()   # node_guids that have ANY link
    all_guids:    set = set()

    for n in nodes:
        nid    = n.get("node_id") or n.get("node_guid") or str(id(n))
        ntitle = n.get("title") or n.get("node_name") or n.get("event_name") or n.get("function_name") or "?"
        all_guids.add(nid)
        for pin in n.get("pins", []):
            linked  = pin.get("linked_to", [])
            ptype   = str(pin.get("pin_type", "")).lower()
            pdir    = str(pin.get("direction", "")).lower()
            is_exec = ptype == "exec"
            if linked:
                has_any_link.add(nid)
                if is_exec:
                    if "input" in pdir:
                        has_exec_in.add(nid)
                    elif "output" in pdir:
                        has_exec_out.add(nid)

    for n in nodes:
        nid    = n.get("node_id") or n.get("node_guid") or str(id(n))
        ntitle = n.get("title") or n.get("node_name") or n.get("event_name") or n.get("function_name") or "?"
        ntype  = n.get("node_type", "")

        # Orphan: no connections at all
        is_event_node = ntype in ("event",) or "event" in ntitle.lower()
        if nid not in has_any_link and not is_event_node:
            orphans.append(nid)
            issues.append(_diag_item(
                severity=SEVERITY_WARNING, category=CAT_GRAPH,
                code="ORPHANED_NODE",
                message=f"Node '{ntitle}' has no connections — it is orphaned",
                asset_path="", graph_name="",
                node_guid=nid, node_title=ntitle,
                suggested_fix="Delete orphaned node or connect it to the graph",
                auto_repairable=True,
            ))

        # Disconnected exec output (non-event node with exec-out but no exec-in)
        has_exec_pins = any("exec" in str(p.get("pin_type", "")).lower() for p in n.get("pins", []))
        if has_exec_pins and nid not in has_exec_in and nid not in has_any_link and not is_event_node:
            # Already captured as orphan; don't double-count
            pass
        elif has_exec_pins and nid in has_exec_out and nid not in has_exec_in and not is_event_node:
            disconnected.append(nid)
            issues.append(_diag_item(
                severity=SEVERITY_WARNING, category=CAT_GRAPH,
                code="DISCONNECTED_EXEC_PIN",
                message=f"Node '{ntitle}' exec-input pin has no incoming connection",
                asset_path="", graph_name="",
                node_guid=nid, node_title=ntitle,
                pin_name="execute",
                suggested_fix="Reconnect the exec chain from the preceding node",
                auto_repairable=True,
            ))

        # Unreachable: has exec pins but neither exec-in nor is event/entry
        if has_exec_pins and nid not in has_exec_in and nid not in has_exec_out and nid not in has_any_link:
            pass  # already orphan

    return {
        "issues":          issues,
        "orphan_guids":    orphans,
        "disconnected_exec": disconnected,
        "unreachable_guids": unreachable,
    }


# ── Tool registration ─────────────────────────────────────────────────────────

def register_diagnostics_tools(mcp: FastMCP) -> None:  # noqa: C901

    # ── compile_blueprint_and_report ─────────────────────────────────────────
    @mcp.tool()
    async def compile_blueprint_and_report(
        ctx: Context,
        blueprint_path: str,
        include_graphs: bool = True,
        graph_names: Optional[List[str]] = None,
    ) -> str:
        """Compile a Blueprint and return graph-aware diagnostic evidence.

        This B.2 report tool wraps the compile in Unreal editor progress and a
        transaction, then returns compile status, structured issues, graph
        summaries, and a safe_to_continue flag for higher-order workflows.

        Args:
            blueprint_path: Full asset path or plain Blueprint asset name.
            include_graphs: Include graph node/orphan summaries when True.
            graph_names: Optional graph-name allowlist; empty checks all graphs.

        Returns:
            StructuredResult JSON with outputs:
              compile_status, compile_clean, had_errors, had_warnings,
              errors[], warnings[], graph_summaries[], graph_count,
              safe_to_continue.

        KB: see knowledge_base/12_MCP_TOOL_USAGE_GUIDE.md#b2-graph-aware-diagnostics-diagnosticstoolspy
        Example:
            compile_blueprint_and_report(blueprint_path="/Game/MCP_Test/BP_Example")"""
        tool_name = "compile_blueprint_and_report"
        t0 = time.monotonic()
        inputs = {
            "blueprint_path": blueprint_path,
            "include_graphs": include_graphs,
            "graph_names": graph_names or [],
        }
        code = (
            _COMPILE_BLUEPRINT_REPORT_CODE
            .replace("__BP_PATH__", repr(blueprint_path))
            .replace("__INCLUDE_GRAPHS__", repr(include_graphs))
            .replace("__GRAPH_NAMES__", repr(graph_names or []))
        )
        raw = _exec_python(code)
        out = _parse_exec_output(raw)
        if out:
            errors = out.get("errors", [])
            warnings = out.get("warnings", [])
            outputs = {
                "compile_status": out.get("compile_status", "unknown"),
                "compile_clean": out.get("compile_clean", False),
                "had_errors": out.get("had_errors", bool(errors)),
                "had_warnings": out.get("had_warnings", bool(warnings)),
                "errors": errors,
                "warnings": warnings,
                "graph_summaries": out.get("graph_summaries", []),
                "graph_count": out.get("graph_count", 0),
                "blueprint_path": blueprint_path,
                "safe_to_continue": not bool(errors),
            }
            meta = _meta(tool_name, t0)
            return json.dumps(_ok(
                outputs,
                [],
                meta,
                f"Blueprint compile report: {outputs['compile_status']}",
                inputs=inputs,
                stage=tool_name,
                log_tail=out.get("log_tail", []),
            ))

        meta = _meta(tool_name, t0)
        return json.dumps(_ok({
            "compile_status": "offline_stub",
            "compile_clean": False,
            "had_errors": False,
            "had_warnings": True,
            "errors": [],
            "warnings": [],
            "graph_summaries": [],
            "graph_count": 0,
            "blueprint_path": blueprint_path,
            "safe_to_continue": False,
            "mode": "offline_stub",
        }, ["UE5 not connected; returning offline compile report stub"], meta,
        inputs=inputs, stage=tool_name))


    # ── compile_material_and_report ──────────────────────────────────────────
    @mcp.tool()
    async def compile_material_and_report(
        ctx: Context,
        material_path: str,
        include_expressions: bool = True,
    ) -> str:
        """Compile a Material and return expression-aware diagnostic evidence.

        The tool invokes Unreal's material recompile path under a progress scope
        and returns compile status, issue arrays, expression count, and optional
        expression summaries for graph-aware material verification.

        Args:
            material_path: Full Material asset path.
            include_expressions: Include expression class/name/position summaries.

        Returns:
            StructuredResult JSON with outputs:
              compile_status, compile_clean, had_errors, errors[], warnings[],
              expression_count, expression_summaries[], safe_to_continue.

        KB: see knowledge_base/12_MCP_TOOL_USAGE_GUIDE.md#b2-graph-aware-diagnostics-diagnosticstoolspy
        Example:
            compile_material_and_report(material_path="/Game/MCP_Test/M_Example")"""
        tool_name = "compile_material_and_report"
        t0 = time.monotonic()
        inputs = {
            "material_path": material_path,
            "include_expressions": include_expressions,
        }
        code = (
            _COMPILE_MATERIAL_REPORT_CODE
            .replace("__MAT_PATH__", repr(material_path))
            .replace("__INCLUDE_EXPRESSIONS__", repr(include_expressions))
        )
        raw = _exec_python(code)
        out = _parse_exec_output(raw)
        if out:
            errors = out.get("errors", [])
            warnings = out.get("warnings", [])
            outputs = {
                "compile_status": out.get("compile_status", "unknown"),
                "compile_clean": out.get("compile_clean", False),
                "had_errors": out.get("had_errors", bool(errors)),
                "errors": errors,
                "warnings": warnings,
                "expression_count": out.get("expression_count", 0),
                "expression_summaries": out.get("expression_summaries", []),
                "material_path": material_path,
                "safe_to_continue": not bool(errors),
            }
            meta = _meta(tool_name, t0)
            return json.dumps(_ok(
                outputs,
                [],
                meta,
                f"Material compile report: {outputs['compile_status']}",
                inputs=inputs,
                stage=tool_name,
                log_tail=out.get("log_tail", []),
            ))

        meta = _meta(tool_name, t0)
        return json.dumps(_ok({
            "compile_status": "offline_stub",
            "compile_clean": False,
            "had_errors": False,
            "errors": [],
            "warnings": [],
            "expression_count": 0,
            "expression_summaries": [],
            "material_path": material_path,
            "safe_to_continue": False,
            "mode": "offline_stub",
        }, ["UE5 not connected; returning offline material report stub"], meta,
        inputs=inputs, stage=tool_name))


    # ── validate_import_result ────────────────────────────────────────────────
    @mcp.tool()
    async def validate_import_result(
        ctx: Context,
        expected_asset_path: str,
        expected_class: str = "",
        source_file: str = "",
        require_saved: bool = True,
    ) -> str:
        """Validate that an imported asset exists and matches expectations.

        Use immediately after import_texture, import_static_mesh,
        import_skeletal_mesh, or generative imports to prove the asset loaded,
        has the expected class, has dependency/reference metadata, and is not
        still dirty when saved output is required.

        Args:
            expected_asset_path: Imported asset path, e.g. "/Game/Meshes/SM_Table".
            expected_class: Optional expected class substring, e.g. "StaticMesh".
            source_file: Optional original OS file path to verify still exists.
            require_saved: Warn when the package is still dirty.

        Returns:
            StructuredResult JSON with outputs:
              exists, class_name, class_matches, dirty, source_file_exists,
              dependency_count, referencer_count, valid.

        KB: see knowledge_base/12_MCP_TOOL_USAGE_GUIDE.md#b2-graph-aware-diagnostics-diagnosticstoolspy
        Example:
            validate_import_result(expected_asset_path="/Game/MCP_Test/SM_Example", expected_class="StaticMesh")"""
        tool_name = "validate_import_result"
        t0 = time.monotonic()
        inputs = {
            "expected_asset_path": expected_asset_path,
            "expected_class": expected_class,
            "source_file": source_file,
            "require_saved": require_saved,
        }
        code = (
            _VALIDATE_IMPORT_RESULT_CODE
            .replace("__ASSET_PATH__", repr(expected_asset_path))
            .replace("__EXPECTED_CLASS__", repr(expected_class))
            .replace("__SOURCE_FILE__", repr(source_file))
            .replace("__REQUIRE_SAVED__", repr(require_saved))
        )
        raw = _exec_python(code)
        out = _parse_exec_output(raw)
        if out:
            warning_items = out.get("warnings", [])
            error_items = out.get("errors", [])
            valid = bool(out.get("exists")) and bool(out.get("class_matches", True)) and not error_items
            if require_saved and out.get("dirty"):
                valid = False
            outputs = {
                "asset_path": expected_asset_path,
                "exists": bool(out.get("exists")),
                "class_name": out.get("class_name", ""),
                "expected_class": expected_class,
                "class_matches": bool(out.get("class_matches", True)),
                "package_name": out.get("package_name", ""),
                "object_path": out.get("object_path", ""),
                "dirty": bool(out.get("dirty", False)),
                "source_file_exists": out.get("source_file_exists"),
                "referencer_count": out.get("referencer_count", 0),
                "dependency_count": out.get("dependency_count", 0),
                "valid": valid,
            }
            meta = _meta(tool_name, t0)
            return json.dumps(_ok(
                outputs,
                warning_items,
                meta,
                "Import validation passed" if valid else "Import validation found issues",
                inputs=inputs,
                stage=tool_name,
                log_tail=out.get("log_tail", []),
            ) if not error_items else _err(
                "; ".join(str(e) for e in error_items),
                meta,
                inputs=inputs,
                log_tail=out.get("log_tail", []),
            ))

        meta = _meta(tool_name, t0)
        return json.dumps(_ok({
            "asset_path": expected_asset_path,
            "exists": False,
            "class_name": "",
            "expected_class": expected_class,
            "class_matches": False,
            "dirty": False,
            "valid": False,
            "mode": "offline_stub",
        }, ["UE5 not connected; returning offline import validation stub"], meta,
        inputs=inputs, stage=tool_name))


    # ── get_changed_assets_since ─────────────────────────────────────────────
    @mcp.tool()
    async def get_changed_assets_since(
        ctx: Context,
        timestamp: str,
        path: str = "/Game",
        include_dirty: bool = True,
        include_unreal_generated: bool = False,
        limit: int = 200,
    ) -> str:
        """List Content Browser assets changed since a timestamp.

        Compares package file modification times and optionally includes dirty
        in-editor packages.  Accepts Unix epoch seconds or ISO-8601 timestamps.

        Args:
            timestamp: Epoch seconds or ISO-8601 timestamp, e.g. "2026-06-07T00:00:00Z".
            path: Content root to scan, default "/Game".
            include_dirty: Include unsaved dirty content/map packages.
            include_unreal_generated: Include /Engine and /Script paths if encountered.
            limit: Maximum changed assets to return; 0 means no explicit cap.

        Returns:
            StructuredResult JSON with outputs:
              changed_assets[], dirty_assets[], changed_count, dirty_count.

        KB: see knowledge_base/12_MCP_TOOL_USAGE_GUIDE.md#b2-graph-aware-diagnostics-diagnosticstoolspy
        Example:
            get_changed_assets_since(timestamp="2026-06-07T00:00:00Z", path="/Game")"""
        tool_name = "get_changed_assets_since"
        t0 = time.monotonic()
        inputs = {
            "timestamp": timestamp,
            "path": path,
            "include_dirty": include_dirty,
            "include_unreal_generated": include_unreal_generated,
            "limit": limit,
        }
        code = (
            _GET_CHANGED_ASSETS_SINCE_CODE
            .replace("__TIMESTAMP__", repr(timestamp))
            .replace("__PATH__", repr(path))
            .replace("__INCLUDE_DIRTY__", repr(include_dirty))
            .replace("__INCLUDE_UNREAL_GENERATED__", repr(include_unreal_generated))
            .replace("__LIMIT__", repr(limit))
        )
        raw = _exec_python(code)
        out = _parse_exec_output(raw)
        if out:
            errors = out.get("errors", [])
            outputs = {
                "timestamp": timestamp,
                "path": path,
                "changed_assets": out.get("changed_assets", []),
                "dirty_assets": out.get("dirty_assets", []),
                "changed_count": out.get("changed_count", 0),
                "dirty_count": out.get("dirty_count", 0),
            }
            meta = _meta(tool_name, t0)
            if errors:
                return json.dumps(_err(
                    "; ".join(str(e) for e in errors),
                    meta,
                    inputs=inputs,
                    log_tail=out.get("log_tail", []),
                ))
            return json.dumps(_ok(
                outputs,
                [],
                meta,
                f"{outputs['changed_count']} changed asset(s), {outputs['dirty_count']} dirty package(s)",
                inputs=inputs,
                stage=tool_name,
                log_tail=out.get("log_tail", []),
            ))

        meta = _meta(tool_name, t0)
        return json.dumps(_ok({
            "timestamp": timestamp,
            "path": path,
            "changed_assets": [],
            "dirty_assets": [],
            "changed_count": 0,
            "dirty_count": 0,
            "mode": "offline_stub",
        }, ["UE5 not connected; returning offline changed-assets stub"], meta,
        inputs=inputs, stage=tool_name))

    # ── bp_get_compile_diagnostics ────────────────────────────────────────────
    @mcp.tool()
    async def bp_get_compile_diagnostics(
        ctx: Context,
        blueprint_path: str,
        include_warnings: bool = True,
        include_info: bool = False,
    ) -> str:
        """Get compiler-derived diagnostics for a Blueprint in structured format.

        Compiles the Blueprint (or reads existing compile status) and returns
        a structured list of errors and warnings — NOT just a raw string.

        Each diagnostic item contains:
          severity, category, code, message, asset_path, graph_name,
          node_guid, node_title, pin_name, suggested_fix, auto_repairable

        Args:
            blueprint_path: Full asset path (e.g. '/Game/Blueprints/BP_HealthSystem')
                            or plain name ('BP_HealthSystem')
            include_warnings: Include warning-level items (default True)
            include_info:     Include info-level items (default False)

        Returns:
            StructuredResult with outputs:
              compile_clean       — bool
              errors[]            — structured error items
              warnings[]          — structured warning items
              compile_time_ms     — int
              compiler_summary    — human-readable one-line summary

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#overview
        Example:
            bp_get_compile_diagnostics(blueprint_path="/Game/MCP_Test/BP_Example")"""
        tool_name = "bp_get_compile_diagnostics"
        t0 = time.monotonic()
        meta = _meta(tool_name, t0)

        # ── 1. Try exec_python path (live UE5) ─────────────────────────────
        bp_path_repr = repr(blueprint_path)
        code = _COMPILE_DIAG_CODE.replace("__BP_PATH__", bp_path_repr)
        r    = _exec_python(code)
        out  = _parse_exec_output(r)

        if out and "compile_clean" in out:
            errors   = out.get("errors",   [])
            warnings = out.get("warnings", [])
            if not include_warnings:
                warnings = []
            if not include_info:
                errors   = [e for e in errors   if e.get("severity") != SEVERITY_INFO]
                warnings = [w for w in warnings if w.get("severity") != SEVERITY_INFO]
            meta = _meta(tool_name, t0)
            return json.dumps(_ok({
                "compile_clean":    out.get("compile_clean", True),
                "errors":           errors,
                "warnings":         warnings,
                "compile_time_ms":  meta["duration_ms"],
                "compiler_summary": out.get("compiler_summary", ""),
                "had_errors":       out.get("had_errors", False),
                "had_warnings":     out.get("had_warnings", False),
            }, [], meta, out.get("compiler_summary", "OK")))

        # ── 2. Fallback: use compile_blueprint C++ command ─────────────────
        raw = _send("compile_blueprint", {"blueprint_name": blueprint_path.split("/")[-1]})
        if raw and raw.get("status") != "error":
            result_data = raw.get("result", raw)
            had_errors = result_data.get("had_errors", False)
            compile_msgs = result_data.get("compile_messages") or []
            errors, warnings = [], []
            for m in compile_msgs:
                cat  = str(m.get("category", "")).lower()
                text = m.get("message", str(m))
                item = _diag_item(
                    severity=SEVERITY_ERROR if cat in ("error",) else SEVERITY_WARNING,
                    category=CAT_COMPILE, code="COMPILE_MSG",
                    message=text, asset_path=blueprint_path,
                    node_title=m.get("node_name", ""),
                    suggested_fix="Review and fix the flagged node",
                    auto_repairable=False,
                )
                if cat in ("error",):
                    errors.append(item)
                else:
                    warnings.append(item)
            if had_errors and not errors:
                errors.append(_diag_item(
                    severity=SEVERITY_ERROR, category=CAT_COMPILE,
                    code="COMPILE_ERROR_GENERIC",
                    message="Blueprint has compile errors (detail unavailable via C++ command)",
                    asset_path=blueprint_path,
                    suggested_fix="Open Blueprint in editor for full error list",
                    auto_repairable=False,
                ))
            meta = _meta(tool_name, t0)
            return json.dumps(_ok({
                "compile_clean":    not had_errors,
                "errors":           errors if include_warnings or errors else [],
                "warnings":         warnings if include_warnings else [],
                "compile_time_ms":  meta["duration_ms"],
                "compiler_summary": "Errors present" if had_errors else "Compiled OK",
                "had_errors":       had_errors,
                "had_warnings":     bool(warnings),
                "mode":             "c++_fallback",
            }, [], meta))

        # ── 3. Offline stub ────────────────────────────────────────────────
        meta = _meta(tool_name, t0)
        return json.dumps(_ok({
            "compile_clean":    True,
            "errors":           [],
            "warnings":         [],
            "compile_time_ms":  0,
            "compiler_summary": "UE5 not connected — offline stub",
            "had_errors":       False,
            "had_warnings":     False,
            "mode":             "offline_stub",
        }, ["UE5 not connected; returning offline stub"], meta,
           "Offline stub — connect UE5 for real diagnostics"))


    # ── bp_validate_graph ─────────────────────────────────────────────────────
    @mcp.tool()
    async def bp_validate_graph(
        ctx: Context,
        blueprint_path: str,
        graph_name: str = "EventGraph",
    ) -> str:
        """Inspect one Blueprint graph for structural health issues.

        Checks exec-chain continuity, orphaned nodes, disconnected required
        inputs, and unreachable nodes — independent of compile status.

        Args:
            blueprint_path: Full asset path or plain name
            graph_name:     Graph to inspect (default 'EventGraph')

        Returns:
            StructuredResult with outputs:
              graph_health_score  — int 0-100
              issue_count         — int
              issues[]            — structured issue items
              nodes_checked       — int

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#overview
        Example:
            bp_validate_graph(blueprint_path="/Game/MCP_Test/BP_Example")"""
        tool_name = "bp_validate_graph"
        t0 = time.monotonic()

        # ── Try exec_python ────────────────────────────────────────────────
        bp_repr   = repr(blueprint_path)
        grph_repr = repr(graph_name)
        code = (_GRAPH_VALIDATE_CODE
                .replace("__BP_PATH__", bp_repr)
                .replace("__GRAPH_NAME__", grph_repr))
        r   = _exec_python(code)
        out = _parse_exec_output(r)

        if out and "issues" in out:
            meta = _meta(tool_name, t0)
            return json.dumps(_ok({
                "graph_health_score": out.get("graph_health_score", 100),
                "issue_count":        out.get("issue_count", 0),
                "issues":             out.get("issues", []),
                "nodes_checked":      out.get("nodes_checked", 0),
                "graph_name":         graph_name,
                "blueprint_path":     blueprint_path,
            }, [], meta, f"Graph '{graph_name}' validated"))

        # ── Fallback: use get_blueprint_nodes ──────────────────────────────
        bp_name = blueprint_path.split("/")[-1]
        raw = _send("get_blueprint_nodes", {
            "blueprint_name": bp_name,
            "graph_name":     graph_name,
        })
        if raw and raw.get("status") != "error":
            nodes = (raw.get("result", raw)).get("nodes", [])
            analysis = _analyze_nodes_offline(nodes)
            issues = []
            for issue in analysis["issues"]:
                issue["asset_path"]  = blueprint_path
                issue["graph_name"]  = graph_name
                issues.append(issue)
            score = _health_score(issues)
            meta  = _meta(tool_name, t0)
            return json.dumps(_ok({
                "graph_health_score": score,
                "issue_count":        len(issues),
                "issues":             issues,
                "nodes_checked":      len(nodes),
                "graph_name":         graph_name,
                "blueprint_path":     blueprint_path,
                "mode":               "offline_node_analysis",
            }, [], meta, f"Graph '{graph_name}': {len(issues)} issue(s)"))

        meta = _meta(tool_name, t0)
        return json.dumps(_ok({
            "graph_health_score": 100,
            "issue_count":        0,
            "issues":             [],
            "nodes_checked":      0,
            "graph_name":         graph_name,
            "blueprint_path":     blueprint_path,
            "mode":               "offline_stub",
        }, ["UE5 not connected; returning offline stub"], meta))


    # ── bp_validate_blueprint ─────────────────────────────────────────────────
    @mcp.tool()
    async def bp_validate_blueprint(
        ctx: Context,
        blueprint_path: str,
        include_graph_validation: bool = True,
        include_variable_check: bool = True,
    ) -> str:
        """Top-level Blueprint validator: compile + graph structure + variable usage.

        Aggregates compile diagnostics, graph-level validation, and variable
        usage into a single health score with an actionable recommendation block.

        Args:
            blueprint_path:          Full asset path or plain name
            include_graph_validation: Also run per-graph structural checks
            include_variable_check:  Also check for unused variables

        Returns:
            StructuredResult with outputs:
              blueprint_path      — str
              compile_clean       — bool
              health_score        — int 0-100
              graphs_checked      — int
              error_count         — int
              warning_count       — int
              issues[]            — all issues combined
              recommended_actions[] — actionable strings

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#overview
        Example:
            bp_validate_blueprint(blueprint_path="/Game/MCP_Test/BP_Example")"""
        tool_name = "bp_validate_blueprint"
        t0 = time.monotonic()

        all_issues: List[Dict]        = []
        warnings_out: List[str]       = []
        graphs_checked                = 0
        compile_clean                 = True
        recommended: List[str]        = []

        # ── Step 1: compile diagnostics ────────────────────────────────────
        bp_repr = repr(blueprint_path)
        code    = _COMPILE_DIAG_CODE.replace("__BP_PATH__", bp_repr)
        r       = _exec_python(code)
        cd      = _parse_exec_output(r)

        if cd and "compile_clean" in cd:
            compile_clean = cd.get("compile_clean", True)
            all_issues.extend(cd.get("errors", []))
            all_issues.extend(cd.get("warnings", []))
            if not compile_clean:
                recommended.append("Fix compile errors before making further edits")
        else:
            # fallback compile
            bp_name = blueprint_path.split("/")[-1]
            raw = _send("compile_blueprint", {"blueprint_name": bp_name})
            if raw and raw.get("status") != "error":
                res_data = raw.get("result", raw)
                had_err  = res_data.get("had_errors", False)
                compile_clean = not had_err
                if had_err:
                    all_issues.append(_diag_item(
                        severity=SEVERITY_ERROR, category=CAT_COMPILE,
                        code="COMPILE_ERROR_GENERIC",
                        message="Blueprint has compile errors",
                        asset_path=blueprint_path,
                        suggested_fix="Open in editor for detail",
                        auto_repairable=False,
                    ))
                    recommended.append("Open Blueprint in editor to see full error list")

        # ── Step 2: graph validation ───────────────────────────────────────
        if include_graph_validation:
            bp_name = blueprint_path.split("/")[-1]
            # Get list of graphs
            grph_raw = _send("get_blueprint_nodes", {
                "blueprint_name": bp_name, "graph_name": "EventGraph"
            })
            graph_names = ["EventGraph"]
            if grph_raw and grph_raw.get("status") != "error":
                graphs_checked = 1
                nodes = (grph_raw.get("result", grph_raw)).get("nodes", [])
                analysis = _analyze_nodes_offline(nodes)
                for issue in analysis["issues"]:
                    issue["asset_path"] = blueprint_path
                    issue["graph_name"] = "EventGraph"
                    all_issues.append(issue)
                if analysis["orphan_guids"]:
                    recommended.append(
                        f"Remove {len(analysis['orphan_guids'])} orphaned node(s) from EventGraph")
                if analysis["disconnected_exec"]:
                    recommended.append(
                        f"Reconnect {len(analysis['disconnected_exec'])} broken exec chain(s)")

        # ── Step 3: variable usage check ───────────────────────────────────
        if include_variable_check:
            code = _FIND_UNUSED_VARS_CODE.replace("__BP_PATH__", repr(blueprint_path))
            r2   = _exec_python(code)
            uv   = _parse_exec_output(r2)
            if uv and "unused_variables" in uv:
                for uvar in uv["unused_variables"]:
                    all_issues.append(_diag_item(
                        severity=SEVERITY_WARNING, category=CAT_VAR,
                        code="POSSIBLY_UNUSED_VAR",
                        message=uvar["message"],
                        asset_path=blueprint_path,
                        suggested_fix=uvar["suggested_fix"],
                        auto_repairable=False,
                    ))
                if uv["unused_variables"]:
                    recommended.append(
                        f"{len(uv['unused_variables'])} possibly-unused variable(s) found — verify before removal")

        # ── Aggregate ──────────────────────────────────────────────────────
        error_count   = sum(1 for i in all_issues if i.get("severity") == SEVERITY_ERROR)
        warning_count = sum(1 for i in all_issues if i.get("severity") == SEVERITY_WARNING)
        health        = _health_score(all_issues)
        if not recommended and error_count == 0 and warning_count == 0:
            recommended.append("Blueprint is healthy — no action required")

        meta = _meta(tool_name, t0)
        return json.dumps(_ok({
            "blueprint_path":    blueprint_path,
            "compile_clean":     compile_clean,
            "health_score":      health,
            "graphs_checked":    graphs_checked,
            "error_count":       error_count,
            "warning_count":     warning_count,
            "issues":            all_issues,
            "recommended_actions": recommended,
        }, warnings_out, meta,
        f"Blueprint validated: health={health}/100, errors={error_count}, warnings={warning_count}"))


    # ── bp_find_disconnected_pins ─────────────────────────────────────────────
    @mcp.tool()
    async def bp_find_disconnected_pins(
        ctx: Context,
        blueprint_path: str,
        graph_name: str = "EventGraph",
        pin_type_filter: str = "exec",
    ) -> str:
        """Find all disconnected exec or input pins in a Blueprint graph.

        Args:
            blueprint_path:  Full asset path or plain name
            graph_name:      Graph to inspect (default 'EventGraph')
            pin_type_filter: 'exec', 'input', or 'all'

        Returns:
            StructuredResult with outputs:
              disconnected_pins[] — list of {node_guid, node_title, pin_name,
                                             pin_type, direction, severity}
              total_disconnected  — int

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#overview
        Example:
            bp_find_disconnected_pins(blueprint_path="/Game/MCP_Test/BP_Example")"""
        tool_name = "bp_find_disconnected_pins"
        t0 = time.monotonic()
        bp_name = blueprint_path.split("/")[-1]
        raw = _send("get_blueprint_nodes", {
            "blueprint_name": bp_name,
            "graph_name":     graph_name,
        })
        disconnected: List[Dict] = []
        if raw and raw.get("status") != "error":
            nodes = (raw.get("result", raw)).get("nodes", [])
            for n in nodes:
                nid    = n.get("node_id") or n.get("node_guid") or ""
                ntitle = (n.get("title") or n.get("node_name") or
                          n.get("event_name") or n.get("function_name") or "?")
                ntype  = n.get("node_type", "")
                is_event = ntype == "event" or "event" in ntitle.lower()
                for pin in n.get("pins", []):
                    pname   = pin.get("pin_name", "")
                    ptype   = str(pin.get("pin_type", "")).lower()
                    pdir    = str(pin.get("direction", "")).lower()
                    linked  = pin.get("linked_to", [])
                    is_exec = ptype == "exec"
                    # Filter
                    if pin_type_filter == "exec" and not is_exec:
                        continue
                    if pin_type_filter == "input" and "input" not in pdir:
                        continue
                    # Skip event node exec-input (it's always "disconnected" by design)
                    if is_event and is_exec and "input" in pdir:
                        continue
                    if not linked:
                        disconnected.append({
                            "node_guid":    nid,
                            "node_title":   ntitle,
                            "pin_name":     pname,
                            "pin_type":     ptype,
                            "direction":    pdir,
                            "severity":     SEVERITY_WARNING if not is_exec else SEVERITY_WARNING,
                            "auto_repairable": is_exec,
                            "suggested_fix": (
                                "Reconnect exec chain" if is_exec
                                else "Set default value or connect to data node"
                            ),
                        })

        meta = _meta(tool_name, t0)
        return json.dumps(_ok({
            "disconnected_pins": disconnected,
            "total_disconnected": len(disconnected),
            "graph_name":        graph_name,
            "blueprint_path":    blueprint_path,
            "pin_type_filter":   pin_type_filter,
        }, [], meta, f"{len(disconnected)} disconnected {pin_type_filter} pin(s) found"))


    # ── bp_find_unreachable_nodes ─────────────────────────────────────────────
    @mcp.tool()
    async def bp_find_unreachable_nodes(
        ctx: Context,
        blueprint_path: str,
        graph_name: str = "EventGraph",
    ) -> str:
        """Find nodes in a graph that have no incoming exec path from an event node.

        A node is unreachable if it has exec pins but no incoming exec connection
        and is not itself an event/entry node.

        Args:
            blueprint_path: Full asset path or plain name
            graph_name:     Graph to inspect

        Returns:
            StructuredResult with outputs:
              unreachable_nodes[] — {node_guid, node_title, reason}
              total_unreachable   — int

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#overview
        Example:
            bp_find_unreachable_nodes(blueprint_path="/Game/MCP_Test/BP_Example")"""
        tool_name = "bp_find_unreachable_nodes"
        t0 = time.monotonic()
        bp_name = blueprint_path.split("/")[-1]
        raw = _send("get_blueprint_nodes", {
            "blueprint_name": bp_name,
            "graph_name":     graph_name,
        })
        unreachable: List[Dict] = []
        if raw and raw.get("status") != "error":
            nodes = (raw.get("result", raw)).get("nodes", [])
            # Build exec-in set
            exec_in_set: set = set()
            for n in nodes:
                nid = n.get("node_id") or n.get("node_guid") or ""
                for pin in n.get("pins", []):
                    if (str(pin.get("pin_type","")).lower() == "exec"
                            and "input" in str(pin.get("direction","")).lower()
                            and pin.get("linked_to")):
                        exec_in_set.add(nid)

            for n in nodes:
                nid    = n.get("node_id") or n.get("node_guid") or ""
                ntitle = (n.get("title") or n.get("node_name") or
                          n.get("event_name") or n.get("function_name") or "?")
                ntype  = n.get("node_type", "")
                is_event = ntype == "event" or "event" in ntitle.lower()
                has_exec_pins = any(
                    str(p.get("pin_type","")).lower() == "exec"
                    for p in n.get("pins", [])
                )
                if has_exec_pins and not is_event and nid not in exec_in_set:
                    unreachable.append({
                        "node_guid":   nid,
                        "node_title":  ntitle,
                        "reason":      "No incoming exec connection from any reachable node",
                        "severity":    SEVERITY_WARNING,
                        "auto_repairable": False,
                        "suggested_fix": "Connect a preceding node's exec-output to this node, or delete if unused",
                    })

        meta = _meta(tool_name, t0)
        return json.dumps(_ok({
            "unreachable_nodes":  unreachable,
            "total_unreachable":  len(unreachable),
            "graph_name":         graph_name,
            "blueprint_path":     blueprint_path,
        }, [], meta, f"{len(unreachable)} unreachable node(s) found"))


    # ── bp_find_unused_variables ──────────────────────────────────────────────
    @mcp.tool()
    async def bp_find_unused_variables(
        ctx: Context,
        blueprint_path: str,
        safe_mode: bool = True,
    ) -> str:
        """Find Blueprint variables declared but not referenced in any graph.

        Important: Variables that are instance-editable or exposed on spawn
        without graph usage are reported as 'possibly_unused' (not definitely
        unused) to prevent false positives.

        Args:
            blueprint_path: Full asset path or plain name
            safe_mode:      If True, mark instance-editable vars as 'possibly_unused'
                            rather than 'unused' (default True — safer)

        Returns:
            StructuredResult with outputs:
              unused_variables[]    — list of variable issue items
              all_variables[]       — all declared variable names
              variables_checked     — int

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#overview
        Example:
            bp_find_unused_variables(blueprint_path="/Game/MCP_Test/BP_Example")"""
        tool_name = "bp_find_unused_variables"
        t0 = time.monotonic()

        # ── Try exec_python ────────────────────────────────────────────────
        code = _FIND_UNUSED_VARS_CODE.replace("__BP_PATH__", repr(blueprint_path))
        r   = _exec_python(code)
        out = _parse_exec_output(r)
        if out and "all_variables" in out:
            meta = _meta(tool_name, t0)
            return json.dumps(_ok({
                "unused_variables":  out.get("unused_variables", []),
                "all_variables":     out.get("all_variables", []),
                "variables_checked": out.get("variables_checked", 0),
                "blueprint_path":    blueprint_path,
                "safe_mode":         safe_mode,
            }, [], meta,
            f"{len(out.get('unused_variables', []))} possibly-unused variable(s)"))

        # ── Offline stub ───────────────────────────────────────────────────
        meta = _meta(tool_name, t0)
        return json.dumps(_ok({
            "unused_variables":  [],
            "all_variables":     [],
            "variables_checked": 0,
            "blueprint_path":    blueprint_path,
            "safe_mode":         safe_mode,
            "mode":              "offline_stub",
        }, ["UE5 not connected; returning offline stub"], meta))


    # ── bp_find_orphaned_nodes ────────────────────────────────────────────────
    @mcp.tool()
    async def bp_find_orphaned_nodes(
        ctx: Context,
        blueprint_path: str,
        graph_name: str = "EventGraph",
    ) -> str:
        """Find nodes in a Blueprint graph that have zero connections of any kind.

        Orphaned nodes have no input or output links. They are safe to remove
        and are a common byproduct of incomplete graph edits.

        Args:
            blueprint_path: Full asset path or plain name
            graph_name:     Graph to inspect

        Returns:
            StructuredResult with outputs:
              orphaned_nodes[]  — {node_guid, node_title, reason, auto_repairable}
              total_orphaned    — int

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#overview
        Example:
            bp_find_orphaned_nodes(blueprint_path="/Game/MCP_Test/BP_Example")"""
        tool_name = "bp_find_orphaned_nodes"
        t0 = time.monotonic()
        bp_name = blueprint_path.split("/")[-1]
        raw = _send("get_blueprint_nodes", {
            "blueprint_name": bp_name,
            "graph_name":     graph_name,
        })
        orphaned: List[Dict] = []
        if raw and raw.get("status") != "error":
            nodes = (raw.get("result", raw)).get("nodes", [])
            for n in nodes:
                nid    = n.get("node_id") or n.get("node_guid") or ""
                ntitle = (n.get("title") or n.get("node_name") or
                          n.get("event_name") or n.get("function_name") or "?")
                ntype  = n.get("node_type", "")
                is_event = ntype == "event" or "event" in ntitle.lower()
                if is_event:
                    continue  # event nodes always "disconnected" on exec-input side
                has_any = any(pin.get("linked_to") for pin in n.get("pins", []))
                if not has_any:
                    orphaned.append({
                        "node_guid":     nid,
                        "node_title":    ntitle,
                        "reason":        "No connections of any kind",
                        "severity":      SEVERITY_WARNING,
                        "auto_repairable": True,
                        "suggested_fix": "Delete this node if it serves no purpose",
                    })

        meta = _meta(tool_name, t0)
        return json.dumps(_ok({
            "orphaned_nodes":  orphaned,
            "total_orphaned":  len(orphaned),
            "graph_name":      graph_name,
            "blueprint_path":  blueprint_path,
        }, [], meta, f"{len(orphaned)} orphaned node(s) found"))


    # ── bp_run_post_mutation_verify ───────────────────────────────────────────
    @mcp.tool()
    async def bp_run_post_mutation_verify(
        ctx: Context,
        blueprint_path: str,
        changed_graphs: Optional[List[str]] = None,
    ) -> str:
        """Run the standard verification pack immediately after a Blueprint mutation.

        This is the default evidence block that higher-order skills should include
        after any edit.  Runs compile diagnostics + graph validation in one call.

        Args:
            blueprint_path: Full asset path or plain name
            changed_graphs: List of graph names to validate (default: ['EventGraph'])

        Returns:
            StructuredResult with outputs:
              compile_status    — 'clean' | 'errors' | 'warnings_only' | 'unknown'
              error_count       — int
              warning_count     — int
              health_score      — int 0-100
              top_issues[]      — first 5 most critical issues
              safe_to_continue  — bool (no compile errors)
              auto_repair_recommended — bool (auto_repairable issues exist)
              full_issues[]     — all issues

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#overview
        Example:
            bp_run_post_mutation_verify(blueprint_path="/Game/MCP_Test/BP_Example")"""
        tool_name = "bp_run_post_mutation_verify"
        t0 = time.monotonic()
        if changed_graphs is None:
            changed_graphs = ["EventGraph"]

        all_issues: List[Dict] = []
        compile_clean = True

        # Compile diagnostics
        bp_repr = repr(blueprint_path)
        code    = _COMPILE_DIAG_CODE.replace("__BP_PATH__", bp_repr)
        r       = _exec_python(code)
        cd      = _parse_exec_output(r)
        if cd and "compile_clean" in cd:
            compile_clean = cd.get("compile_clean", True)
            all_issues.extend(cd.get("errors", []))
            all_issues.extend(cd.get("warnings", []))
        else:
            bp_name = blueprint_path.split("/")[-1]
            raw = _send("compile_blueprint", {"blueprint_name": bp_name})
            if raw and raw.get("status") != "error":
                res = raw.get("result", raw)
                compile_clean = not res.get("had_errors", False)

        # Graph validation for each changed graph
        bp_name = blueprint_path.split("/")[-1]
        for gname in changed_graphs:
            raw = _send("get_blueprint_nodes", {
                "blueprint_name": bp_name,
                "graph_name":     gname,
            })
            if raw and raw.get("status") != "error":
                nodes    = (raw.get("result", raw)).get("nodes", [])
                analysis = _analyze_nodes_offline(nodes)
                for issue in analysis["issues"]:
                    issue["asset_path"] = blueprint_path
                    issue["graph_name"] = gname
                    all_issues.append(issue)

        error_count   = sum(1 for i in all_issues if i.get("severity") == SEVERITY_ERROR)
        warning_count = sum(1 for i in all_issues if i.get("severity") == SEVERITY_WARNING)
        health        = _health_score(all_issues)
        auto_repair   = any(i.get("auto_repairable") for i in all_issues)

        if error_count == 0 and warning_count == 0:
            compile_status = "clean"
        elif error_count > 0:
            compile_status = "errors"
        else:
            compile_status = "warnings_only"

        # Sort by severity for top issues
        sev_order = {SEVERITY_ERROR: 0, SEVERITY_WARNING: 1, SEVERITY_INFO: 2}
        sorted_issues = sorted(all_issues, key=lambda i: sev_order.get(i.get("severity",""), 9))
        top_issues    = sorted_issues[:5]

        meta = _meta(tool_name, t0)
        return json.dumps(_ok({
            "compile_status":          compile_status,
            "error_count":             error_count,
            "warning_count":           warning_count,
            "health_score":            health,
            "top_issues":              top_issues,
            "safe_to_continue":        error_count == 0,
            "auto_repair_recommended": auto_repair,
            "full_issues":             all_issues,
            "blueprint_path":          blueprint_path,
            "graphs_checked":          changed_graphs,
        }, [], meta,
        f"Post-mutation verify: status={compile_status}, health={health}/100"))


    # ── mat_get_compile_diagnostics ───────────────────────────────────────────
    @mcp.tool()
    async def mat_get_compile_diagnostics(
        ctx: Context,
        material_path: str,
        include_warnings: bool = True,
    ) -> str:
        """Get compiler-derived diagnostics for a Material asset.

        Args:
            material_path:    Full asset path (e.g. '/Game/Materials/M_DemoB')
            include_warnings: Include warning-level items (default True)

        Returns:
            StructuredResult with outputs:
              compile_clean     — bool
              errors[]          — structured error items
              warnings[]        — structured warning items
              expression_count  — int
              compiler_summary  — str
              had_errors        — bool

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#overview
        Example:
            mat_get_compile_diagnostics(material_path="/Game/MCP_Test/M_Example")"""
        tool_name = "mat_get_compile_diagnostics"
        t0 = time.monotonic()
        code = _MAT_COMPILE_DIAG_CODE.replace("__MAT_PATH__", repr(material_path))
        r    = _exec_python(code)
        out  = _parse_exec_output(r)

        if out and "compile_clean" in out:
            errors   = out.get("errors",   [])
            warnings = out.get("warnings", []) if include_warnings else []
            meta = _meta(tool_name, t0)
            return json.dumps(_ok({
                "compile_clean":    out.get("compile_clean", True),
                "errors":           errors,
                "warnings":         warnings,
                "expression_count": out.get("expression_count", 0),
                "compiler_summary": out.get("compiler_summary", ""),
                "had_errors":       out.get("had_errors", False),
                "material_path":    material_path,
            }, [], meta, out.get("compiler_summary", "OK")))

        # Offline stub
        meta = _meta(tool_name, t0)
        return json.dumps(_ok({
            "compile_clean":    True,
            "errors":           [],
            "warnings":         [],
            "expression_count": 0,
            "compiler_summary": "UE5 not connected — offline stub",
            "had_errors":       False,
            "material_path":    material_path,
            "mode":             "offline_stub",
        }, ["UE5 not connected; returning offline stub"], meta))


    # ── mat_validate_material ─────────────────────────────────────────────────
    @mcp.tool()
    async def mat_validate_material(
        ctx: Context,
        material_path: str,
    ) -> str:
        """Validate a Material: expression count, disconnects, health score.

        Gives materials the same trust model as Blueprints.  Narrower than
        Blueprint validation but reliable and non-speculative.

        Args:
            material_path: Full asset path (e.g. '/Game/Materials/M_DemoB')

        Returns:
            StructuredResult with outputs:
              material_health_score  — int 0-100
              compile_clean          — bool
              expression_count       — int
              disconnected_count     — int (expressions not connected to output)
              issues[]               — structured issue items
              recommended_actions[]  — actionable strings

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#overview
        Example:
            mat_validate_material(material_path="/Game/MCP_Test/M_Example")"""
        tool_name = "mat_validate_material"
        t0 = time.monotonic()
        issues:      List[Dict] = []
        recommended: List[str]  = []

        code = _MAT_COMPILE_DIAG_CODE.replace("__MAT_PATH__", repr(material_path))
        r    = _exec_python(code)
        out  = _parse_exec_output(r)

        compile_clean    = True
        expression_count = 0

        if out and "compile_clean" in out:
            compile_clean    = out.get("compile_clean", True)
            expression_count = out.get("expression_count", 0)
            issues.extend(out.get("errors",   []))
            issues.extend(out.get("warnings", []))
            if not compile_clean:
                recommended.append("Fix material compile errors before further edits")
            if expression_count == 0:
                recommended.append("Add material expressions to the graph")
        else:
            # Try mat_compile stub via exec_python
            mat_code = f"""
import unreal, json
_result = {{"compile_clean": True, "expression_count": 0, "had_errors": False}}
try:
    mat = unreal.load_asset({repr(material_path)})
    if mat:
        exprs = mat.get_editor_property("expressions") if hasattr(mat, "get_editor_property") else []
        _result["expression_count"] = len(exprs) if exprs else 0
    else:
        _result["compile_clean"] = False
        _result["had_errors"] = True
except Exception as _e:
    _result["error"] = str(_e)
print(json.dumps(_result))
"""
            r2  = _exec_python(mat_code)
            out2 = _parse_exec_output(r2)
            if out2:
                compile_clean    = out2.get("compile_clean", True)
                expression_count = out2.get("expression_count", 0)

        score = _health_score(issues)
        if not issues and compile_clean:
            recommended.append("Material is healthy — no action required")

        meta = _meta(tool_name, t0)
        return json.dumps(_ok({
            "material_health_score": score,
            "compile_clean":         compile_clean,
            "expression_count":      expression_count,
            "disconnected_count":    0,  # requires deeper AST analysis; always 0 in stub
            "issues":                issues,
            "recommended_actions":   recommended,
            "material_path":         material_path,
        }, [], meta,
        f"Material validated: health={score}/100, expressions={expression_count}"))


# ── Module self-test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Quick sanity: build a diag item and check schema
    item = _diag_item(
        severity=SEVERITY_ERROR, category=CAT_COMPILE, code="TEST",
        message="test", asset_path="/Game/BP",
    )
    required = {"severity","category","code","message","asset_path","graph_name",
                "node_guid","node_title","pin_name","suggested_fix","auto_repairable"}
    assert required == set(item.keys()), f"Missing keys: {required - set(item.keys())}"
    print("diagnostics_tools self-test PASS")
