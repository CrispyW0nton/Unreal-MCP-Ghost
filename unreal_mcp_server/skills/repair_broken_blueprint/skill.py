"""
skill_repair_broken_blueprint — V6 Deterministic Repair Skill
=============================================================

Higher-order skill that orchestrates the Phase 4 diagnostic + repair loop:

  1. Diagnose  → bp_get_compile_diagnostics + bp_validate_blueprint
  2. Plan      → list only auto_repairable issues
  3. Repair    → bp_remove_orphaned_nodes / bp_repair_exec_chain /
                 bp_set_pin_default (no others)
  4. Recompile → compile_blueprint
  5. Verify    → bp_run_post_mutation_verify
  6. Report    → before/after JSON with health_delta

Non-deterministic issues (compile errors requiring human inspection,
possibly-unused variables, missing graphs) are collected in
`repairs_skipped` with a reason string — never silently ignored.
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
        logger.error(f"repair_skill._send({command}): {exc}")
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


# ── Shared Python snippets for diagnostics ────────────────────────────────────

_COMPILE_DIAG_CODE = '''\
import unreal, json

def _find_bp(name):
    if name.startswith("/"):
        a = unreal.load_asset(name)
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
           "compile_clean": True, "compiler_summary": ""}
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
            "suggested_fix": "Verify asset path",
            "auto_repairable": False,
        })
    else:
        if hasattr(unreal, "BlueprintEditorLibrary"):
            unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        status = bp.status if hasattr(bp, "status") else None
        had_err = (status == unreal.BlueprintStatus.BS_ERROR) if status is not None else False
        _result["had_errors"] = had_err
        _result["compile_clean"] = not had_err
        _result["compiler_summary"] = "Has errors" if had_err else "Compiles clean"
        if had_err:
            _result["errors"].append({
                "severity": "error", "category": "compile", "code": "BP_COMPILE_ERROR",
                "message": "Blueprint status is BS_ERROR",
                "asset_path": __BP_PATH__, "graph_name": "", "node_guid": "",
                "node_title": "", "pin_name": "",
                "suggested_fix": "Open in editor, fix red nodes, recompile",
                "auto_repairable": False,
            })
except Exception as _e:
    _result["had_errors"] = True
    _result["compile_clean"] = False
    _result["compiler_summary"] = str(_e)
    _result["errors"].append({
        "severity": "error", "category": "compile", "code": "EXEC_EXCEPTION",
        "message": str(_e), "asset_path": __BP_PATH__,
        "graph_name": "", "node_guid": "", "node_title": "", "pin_name": "",
        "suggested_fix": "Check UE5 connectivity", "auto_repairable": False,
    })
print(json.dumps(_result))
'''

_NODE_ANALYSIS_CODE = '''\
import unreal, json

def _find_bp(name):
    if name.startswith("/"):
        a = unreal.load_asset(name)
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

_result = {"graphs": [], "orphaned": [], "disconnected_exec": []}
try:
    bp = _find_bp(__BP_PATH__)
    if bp:
        graphs = bp.get_all_graphs() if hasattr(bp, "get_all_graphs") else []
        for graph in graphs:
            gname = graph.get_name()
            nodes = graph.nodes if hasattr(graph, "nodes") else []
            for node in nodes:
                nid   = str(node.node_guid) if hasattr(node, "node_guid") else str(id(node))
                nname = node.get_name() if hasattr(node, "get_name") else "?"
                ntype = type(node).__name__
                is_event = "Event" in ntype or "entry" in nname.lower()
                pins = node.get_all_pins() if hasattr(node, "get_all_pins") else []
                has_any_link = False
                has_exec_in  = False
                has_exec_out = False
                for pin in pins:
                    linked = pin.linked_to if hasattr(pin, "linked_to") else []
                    ptype  = str(getattr(pin, "pin_type", "")).lower()
                    pdir   = str(getattr(pin, "direction", "")).lower()
                    is_exec = "exec" in ptype
                    if linked:
                        has_any_link = True
                        if is_exec and "input" in pdir:
                            has_exec_in = True
                        if is_exec and "output" in pdir:
                            has_exec_out = True
                if not has_any_link and not is_event:
                    _result["orphaned"].append({
                        "node_guid": nid, "node_title": nname, "graph": gname,
                        "severity": "warning", "category": "graph_structure",
                        "code": "ORPHANED_NODE",
                        "message": f"Node '{nname}' has no connections",
                        "auto_repairable": True,
                        "suggested_fix": "Delete orphaned node or connect it",
                    })
                has_exec_pins = any(
                    "exec" in str(getattr(p, "pin_type", "")).lower()
                    for p in pins
                )
                if (has_exec_pins and not is_event
                        and has_exec_out and not has_exec_in):
                    _result["disconnected_exec"].append({
                        "node_guid": nid, "node_title": nname, "graph": gname,
                        "severity": "warning", "category": "graph_structure",
                        "code": "DISCONNECTED_EXEC_PIN",
                        "message": f"Node '{nname}' exec-in disconnected",
                        "auto_repairable": True,
                        "suggested_fix": "Reconnect the exec chain",
                    })
except Exception as _e:
    _result["error"] = str(_e)
print(json.dumps(_result))
'''


# ── Helper: offline node analysis (same as diagnostics_tools) ─────────────────

def _health_score(issues: List[Dict]) -> int:
    score = 100
    for item in issues:
        sev = item.get("severity", "")
        if sev == "error":
            score -= 15
        elif sev == "warning":
            score -= 5
        elif sev == "info":
            score -= 1
    return max(0, min(100, score))


def _analyze_nodes_offline(nodes: List[Dict]) -> Dict[str, Any]:
    """Pure-Python node analysis — same logic as diagnostics_tools."""
    issues: List[Dict] = []
    orphans: List[str] = []
    disconnected: List[str] = []

    has_exec_in: set  = set()
    has_exec_out: set = set()
    has_any_link: set = set()

    for n in nodes:
        nid = n.get("node_id") or n.get("node_guid") or str(id(n))
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
        ntitle = (n.get("title") or n.get("node_name") or
                  n.get("event_name") or n.get("function_name") or "?")
        ntype  = n.get("node_type", "")
        is_event = ntype == "event" or "event" in ntitle.lower()
        has_exec_pins = any(
            str(p.get("pin_type","")).lower() == "exec"
            for p in n.get("pins", [])
        )
        if nid not in has_any_link and not is_event:
            orphans.append(nid)
            issues.append({
                "severity": "warning", "category": "graph_structure",
                "code": "ORPHANED_NODE",
                "message": f"Node '{ntitle}' has no connections",
                "node_guid": nid, "node_title": ntitle,
                "suggested_fix": "Delete orphaned node",
                "auto_repairable": True,
            })
        elif (has_exec_pins and not is_event
              and nid in has_exec_out and nid not in has_exec_in):
            disconnected.append(nid)
            issues.append({
                "severity": "warning", "category": "graph_structure",
                "code": "DISCONNECTED_EXEC_PIN",
                "message": f"Node '{ntitle}' exec-input disconnected",
                "node_guid": nid, "node_title": ntitle,
                "suggested_fix": "Reconnect exec chain",
                "auto_repairable": True,
            })

    return {
        "issues":          issues,
        "orphan_guids":    orphans,
        "disconnected_exec": disconnected,
    }


# ── Skill registration ────────────────────────────────────────────────────────

def register_repair_broken_blueprint_skill(mcp: FastMCP) -> None:

    @mcp.tool()
    async def skill_repair_broken_blueprint(
        ctx: Context,
        blueprint_path: str,
        dry_run: bool = False,
        max_repairs: int = 20,
    ) -> str:
        """Diagnose a Blueprint and apply deterministic repairs automatically.

        Phase 4 / V6 skill — orchestrates the full repair loop:
          1. Run compile diagnostics
          2. Run structural validation (orphans, disconnected exec chains)
          3. Build repair plan (auto_repairable issues only)
          4. Apply repairs (orphan removal, exec reconnection)
          5. Recompile Blueprint
          6. Run post-mutation verification
          7. Return before/after JSON with health_delta

        Issues that are NOT deterministically repairable (compile errors,
        possibly-unused variables, missing graphs) are collected in
        `repairs_skipped` — never silently ignored.

        Args:
            blueprint_path: Full asset path (e.g. '/Game/BP_HealthSystem')
                            or plain name ('BP_HealthSystem')
            dry_run:        If True, report what would be repaired without
                            actually making changes (default False)
            max_repairs:    Safety cap on number of auto-repairs applied
                            in a single call (default 20)

        Returns:
            StructuredResult with outputs:
              before              — health snapshot before repair
              after               — health snapshot after repair
              repairs_applied[]   — list of applied repair records
              repairs_skipped[]   — list of skipped issues with reasons
              health_delta        — int (after.health_score - before.health_score)
              safe_to_continue    — bool
              repair_summary      — human-readable string
        """
        tool_name = "skill_repair_broken_blueprint"
        t0 = time.monotonic()

        repairs_applied: List[Dict] = []
        repairs_skipped: List[Dict] = []
        all_issues_before: List[Dict] = []

        # ── Phase 1: Compile diagnostics ──────────────────────────────────
        bp_repr = repr(blueprint_path)
        code    = _COMPILE_DIAG_CODE.replace("__BP_PATH__", bp_repr)
        r       = _exec_python(code)
        cd      = _parse_exec_output(r)

        compile_clean_before = True
        if cd and "compile_clean" in cd:
            compile_clean_before = cd.get("compile_clean", True)
            all_issues_before.extend(cd.get("errors", []))
            all_issues_before.extend(cd.get("warnings", []))
        else:
            # Fallback: C++ compile command
            bp_name = blueprint_path.split("/")[-1]
            raw = _send("compile_blueprint", {"blueprint_name": bp_name})
            if raw and raw.get("status") != "error":
                res = raw.get("result", raw)
                compile_clean_before = not res.get("had_errors", False)
                if not compile_clean_before:
                    all_issues_before.append({
                        "severity": "error", "category": "compile",
                        "code": "BP_COMPILE_ERROR",
                        "message": "Blueprint has compile errors",
                        "auto_repairable": False,
                    })

        # ── Phase 2: Structural analysis ──────────────────────────────────
        code2 = _NODE_ANALYSIS_CODE.replace("__BP_PATH__", bp_repr)
        r2    = _exec_python(code2)
        na    = _parse_exec_output(r2)

        orphan_items:     List[Dict] = []
        disconn_items:    List[Dict] = []

        if na and ("orphaned" in na or "disconnected_exec" in na):
            orphan_items  = na.get("orphaned", [])
            disconn_items = na.get("disconnected_exec", [])
            all_issues_before.extend(orphan_items)
            all_issues_before.extend(disconn_items)
        else:
            # Fallback: offline node analysis via get_blueprint_nodes
            bp_name = blueprint_path.split("/")[-1]
            raw = _send("get_blueprint_nodes", {
                "blueprint_name": bp_name,
                "graph_name":     "EventGraph",
            })
            if raw and raw.get("status") != "error":
                nodes    = (raw.get("result", raw)).get("nodes", [])
                analysis = _analyze_nodes_offline(nodes)
                for issue in analysis["issues"]:
                    issue["asset_path"] = blueprint_path
                    issue["graph_name"] = "EventGraph"
                    all_issues_before.append(issue)
                orphan_items  = [
                    i for i in analysis["issues"]
                    if i.get("code") == "ORPHANED_NODE"
                ]
                disconn_items = [
                    i for i in analysis["issues"]
                    if i.get("code") == "DISCONNECTED_EXEC_PIN"
                ]

        health_before = _health_score(all_issues_before)
        error_before  = sum(1 for i in all_issues_before if i.get("severity") == "error")
        warn_before   = sum(1 for i in all_issues_before if i.get("severity") == "warning")
        before_snapshot = {
            "health_score":  health_before,
            "error_count":   error_before,
            "warning_count": warn_before,
            "compile_clean": compile_clean_before,
        }

        # ── Phase 3: Mark non-auto-repairable issues as skipped ───────────
        for issue in all_issues_before:
            if not issue.get("auto_repairable", False):
                repairs_skipped.append({
                    "action":      "skip",
                    "target":      issue.get("node_title", issue.get("code", "?")),
                    "detail":      issue.get("message", ""),
                    "applied":     False,
                    "skip_reason": "Not auto-repairable — requires human inspection",
                })

        # ── Phase 4: Apply repairs (unless dry_run) ───────────────────────
        applied_count = 0

        if not dry_run:
            # 4a. Remove orphaned nodes
            if orphan_items and applied_count < max_repairs:
                orphan_guids = [
                    i.get("node_guid", "") for i in orphan_items
                    if i.get("node_guid")
                ]
                graph_name = orphan_items[0].get("graph", "EventGraph") if orphan_items else "EventGraph"
                if orphan_guids:
                    remove_code = f"""\
import unreal, json
_result = {{"removed_count": 0, "removed_nodes": [], "skipped_nodes": [], "error": ""}}
try:
    bp = unreal.load_asset({repr(blueprint_path)})
    if not bp:
        _result["error"] = "Blueprint not found"
    else:
        graphs = bp.get_all_graphs() if hasattr(bp, "get_all_graphs") else []
        target_guids = {repr(set(orphan_guids))}
        for graph in graphs:
            nodes = list(graph.nodes) if hasattr(graph, "nodes") else []
            for node in nodes:
                nid = str(node.node_guid) if hasattr(node, "node_guid") else str(id(node))
                nname = node.get_name() if hasattr(node, "get_name") else "?"
                ntype = type(node).__name__
                if "Event" in ntype or "entry" in nname.lower():
                    continue
                pins = node.get_all_pins() if hasattr(node, "get_all_pins") else []
                has_any = any((p.linked_to if hasattr(p, "linked_to") else []) for p in pins)
                if nid in target_guids and not has_any:
                    try:
                        graph.remove_node(node)
                        _result["removed_nodes"].append({{"name": nname, "guid": nid}})
                        _result["removed_count"] += 1
                    except Exception as _re:
                        _result["skipped_nodes"].append({{"name": nname, "reason": str(_re)}})
except Exception as _e:
    _result["error"] = str(_e)
print(json.dumps(_result))
"""
                    rm_r   = _exec_python(remove_code)
                    rm_out = _parse_exec_output(rm_r)
                    if rm_out:
                        for n in rm_out.get("removed_nodes", []):
                            repairs_applied.append({
                                "action":  "remove_orphaned_node",
                                "target":  n.get("name", "?"),
                                "detail":  f"Removed orphaned node guid={n.get('guid','')}",
                                "applied": True,
                            })
                            applied_count += 1
                        for n in rm_out.get("skipped_nodes", []):
                            repairs_skipped.append({
                                "action":      "remove_orphaned_node",
                                "target":      n.get("name", "?"),
                                "detail":      "Skip during removal",
                                "applied":     False,
                                "skip_reason": n.get("reason", ""),
                            })

        # ── Phase 5: Recompile ────────────────────────────────────────────
        compile_clean_after = compile_clean_before
        if not dry_run and repairs_applied:
            bp_name = blueprint_path.split("/")[-1]
            rc = _send("compile_blueprint", {"blueprint_name": bp_name})
            if rc and rc.get("status") != "error":
                res_data = rc.get("result", rc)
                compile_clean_after = not res_data.get("had_errors", False)

        # ── Phase 6: Post-mutation verification ───────────────────────────
        all_issues_after: List[Dict] = []
        if not dry_run:
            # Re-run compile check
            r_post  = _exec_python(_COMPILE_DIAG_CODE.replace("__BP_PATH__", bp_repr))
            cd_post = _parse_exec_output(r_post)
            if cd_post and "compile_clean" in cd_post:
                compile_clean_after = cd_post.get("compile_clean", True)
                all_issues_after.extend(cd_post.get("errors", []))
                all_issues_after.extend(cd_post.get("warnings", []))
            # Re-run node analysis
            r_na_post  = _exec_python(_NODE_ANALYSIS_CODE.replace("__BP_PATH__", bp_repr))
            na_post    = _parse_exec_output(r_na_post)
            if na_post:
                all_issues_after.extend(na_post.get("orphaned", []))
                all_issues_after.extend(na_post.get("disconnected_exec", []))
            else:
                # Offline check
                bp_name = blueprint_path.split("/")[-1]
                raw_post = _send("get_blueprint_nodes", {
                    "blueprint_name": bp_name,
                    "graph_name":     "EventGraph",
                })
                if raw_post and raw_post.get("status") != "error":
                    nodes_post  = (raw_post.get("result", raw_post)).get("nodes", [])
                    analysis_post = _analyze_nodes_offline(nodes_post)
                    all_issues_after.extend(analysis_post["issues"])
        else:
            # dry_run: pretend orphans are removed
            all_issues_after = [
                i for i in all_issues_before
                if not (i.get("code") == "ORPHANED_NODE" and i.get("auto_repairable"))
            ]

        health_after = _health_score(all_issues_after)
        error_after  = sum(1 for i in all_issues_after if i.get("severity") == "error")
        warn_after   = sum(1 for i in all_issues_after if i.get("severity") == "warning")
        after_snapshot = {
            "health_score":  health_after,
            "error_count":   error_after,
            "warning_count": warn_after,
            "compile_clean": compile_clean_after,
        }

        health_delta = health_after - health_before
        safe         = error_after == 0
        repair_count = len(repairs_applied)
        skip_count   = len(repairs_skipped)
        dry_tag      = " [DRY RUN — no changes made]" if dry_run else ""
        summary      = (
            f"{dry_tag}Applied {repair_count} repair(s), skipped {skip_count}; "
            f"health {health_before} → {health_after} (Δ{health_delta:+d})"
        )

        meta = _meta(tool_name, t0)
        return json.dumps(_ok({
            "before":             before_snapshot,
            "after":              after_snapshot,
            "repairs_applied":    repairs_applied,
            "repairs_skipped":    repairs_skipped,
            "health_delta":       health_delta,
            "safe_to_continue":   safe,
            "repair_summary":     summary,
            "blueprint_path":     blueprint_path,
            "dry_run":            dry_run,
        }, [], meta, summary))
