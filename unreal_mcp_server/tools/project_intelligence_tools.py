"""
project_intelligence_tools.py — V5 Project Intelligence (read-only)
====================================================================

Provides 5 tools for discovering and tracing assets in an Unreal Engine 5
project entirely through the Asset Registry Python API.  No tool mutates
state, opens a transaction, or blocks the editor main thread > 500 ms on a
1 k-asset project.

Tools:
  project_find_assets            — filtered asset search with pagination
  project_get_references         — in/out/both dependency edges for a package
  project_trace_reference_chain  — BFS reference chain from a starting package
  project_find_blueprint_by_parent — find Blueprints by parent class name
  project_list_subsystems        — reflect all Subsystem classes by category

Every tool returns a StructuredResult dict that matches the V5 shared contract:
  { success, stage, message, outputs, warnings, errors, log_tail, meta }
where meta = { tool, duration_ms, page?, total_pages? }.

All data is JSON-safe (no raw unreal.* objects).  Lists that may exceed 50 items
are paginated via limit/page parameters.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger("UnrealMCP")

# ── Error codes ───────────────────────────────────────────────────────────────

ERR_NOT_CONNECTED         = "ERR_UNREAL_NOT_CONNECTED"
ERR_AR_NOT_READY          = "ERR_ASSET_REGISTRY_NOT_READY"
ERR_INVALID_PATH          = "ERR_INVALID_PACKAGE_PATH"
ERR_CLASS_NOT_FOUND       = "ERR_CLASS_NOT_FOUND"
ERR_SUBSYSTEM_ENUM_FAILED = "ERR_SUBSYSTEM_ENUM_FAILED"
ERR_INTERNAL              = "ERR_INTERNAL"
ERR_PAGINATION_OOR        = "ERR_PAGINATION_OUT_OF_RANGE"

# ── Internal helpers ──────────────────────────────────────────────────────────

def _send(command: str, params: dict) -> Dict[str, Any]:
    from unreal_mcp_server import get_unreal_connection
    try:
        conn = get_unreal_connection()
        if not conn:
            return {"success": False, "error_code": ERR_NOT_CONNECTED, "message": "Not connected to Unreal Engine"}
        result = conn.send_command(command, params)
        return result or {"success": False, "message": "No response from Unreal Engine"}
    except Exception as exc:
        logger.error(f"project_intelligence._send error: {exc}")
        return {"success": False, "message": str(exc)}


def _exec_python(code: str) -> Dict[str, Any]:
    """Run code via exec_python on UE5 and return the raw response dict.

    Exposed as a module-level function so tests can patch it directly.
    """
    return _send("exec_python", {"code": code})


def _ok(raw: Dict[str, Any]) -> bool:
    return bool(raw and raw.get("success") is not False and raw.get("status") != "error")


def _make_result(
    *,
    success: bool,
    stage: str = "",
    message: str = "",
    outputs: Optional[Dict] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    error_code: Optional[str] = None,
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
    if error_code:
        r["error_code"] = error_code
    if meta:
        r["meta"] = meta
    return r


def _meta(tool: str, t0: float, **extra) -> Dict[str, Any]:
    m: Dict[str, Any] = {"tool": tool, "duration_ms": int((time.monotonic() - t0) * 1000)}
    m.update(extra)
    return m


# ── Subsystem reflection cache ────────────────────────────────────────────────

_SUBSYSTEM_CACHE: Dict[str, Any] = {}
_SUBSYSTEM_CACHE_TS: float = 0.0
_SUBSYSTEM_CACHE_TTL = 10.0  # seconds


def _refresh_subsystem_cache() -> Dict[str, Any]:
    """Reflect subsystem classes from UE5 via exec_python."""
    import textwrap
    code = textwrap.dedent("""
        import unreal, json
        _result = {'engine': [], 'editor': [], 'gameinstance': [], 'localplayer': []}
        _bases = {
            'engine':      unreal.EngineSubsystem,
            'editor':      unreal.EditorSubsystem,
            'gameinstance': unreal.GameInstanceSubsystem,
            'localplayer': unreal.LocalPlayerSubsystem,
        }
        for _cat, _base in _bases.items():
            try:
                for _cls in unreal.get_all_classes_of_type(_base):
                    _name = _cls.get_name() if hasattr(_cls, 'get_name') else str(_cls)
                    _mod  = getattr(_cls, 'get_outer', lambda: None)()
                    _mod_name = _mod.get_name() if _mod and hasattr(_mod, 'get_name') else ''
                    _result[_cat].append({'class': _name, 'module': _mod_name, 'available': True})
            except Exception as _e:
                _result[_cat].append({'class': 'ERROR', 'module': str(_e), 'available': False})
    """)
    raw = _exec_python(code)
    out = (raw or {}).get("result") or (raw or {}).get("outputs") or {}
    if isinstance(out, dict) and any(k in out for k in ("engine", "editor", "gameinstance", "localplayer")):
        return out
    # fallback: return empty categories
    return {"engine": [], "editor": [], "gameinstance": [], "localplayer": []}


# ── Registration ──────────────────────────────────────────────────────────────

def register_project_intelligence_tools(mcp: FastMCP):  # noqa: C901

    # ──────────────────────────────────────────────────────────────────────────
    # project_find_assets
    # ──────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def project_find_assets(
        ctx: Context,
        class_names: List[str] = [],
        package_paths: List[str] = ["/Game"],
        recursive: bool = True,
        tags: Dict[str, str] = {},
        limit: int = 200,
        page: int = 0,
    ) -> str:
        """Find assets in the Unreal project using the Asset Registry.

        Searches by asset class, package path, and optional tag filters.
        Results are paginated — use page / limit to scroll through large sets.

        Returns a list of asset descriptors:
          package_name — full package path (e.g. '/Game/Blueprints/BP_Hero')
          asset_name   — bare asset name (e.g. 'BP_Hero')
          class_path   — asset class full path (e.g. '/Script/Engine.Blueprint')
          tags         — dict of asset registry tags (e.g. {'ParentClass': '...'})

        Args:
            class_names:   Asset class filters (e.g. ['Blueprint', 'StaticMesh']).
                           Empty = all classes.
            package_paths: Root paths to search (e.g. ['/Game/Blueprints']).
            recursive:     Search subdirectories. Default True.
            tags:          Tag=value filters (AND). Empty = no tag filter.
            limit:         Page size. Default 200, max 1000.
            page:          0-based page index. Default 0.

        Returns:
            JSON StructuredResult with outputs.assets list.
        """
        import textwrap
        t0 = time.monotonic()
        limit    = max(1, min(limit, 1000))
        page     = max(0, page)
        offset   = page * limit

        # Build exec_python code to run inside UE5
        code = textwrap.dedent(f"""
            import unreal, json
            _result = {{'assets': [], 'total': 0}}
            reg  = unreal.AssetRegistryHelpers.get_asset_registry()
            flt  = unreal.ARFilter()
            flt.package_paths     = {json.dumps(package_paths)}
            flt.recursive_paths   = {str(recursive).lower()}
            flt.recursive_classes = True
            if {json.dumps(class_names)}:
                flt.class_names = {json.dumps(class_names)}
            assets = reg.get_assets(flt)
            total  = len(assets)
            _result['total'] = total
            offset = {offset}
            limit  = {limit}
            for a in assets[offset:offset+limit]:
                pkg   = str(a.package_name)
                aname = str(a.asset_name)
                cls   = str(a.asset_class_path) if hasattr(a, 'asset_class_path') else str(a.asset_class)
                _tags = {{}}
                try:
                    for k, v in a.tag_and_values.items():
                        _tags[str(k)] = str(v)
                except Exception:
                    pass
                # Apply tag filter
                ok = True
                for tk, tv in {json.dumps(tags)}.items():
                    if _tags.get(tk) != tv:
                        ok = False
                        break
                if ok:
                    _result['assets'].append({{
                        'package_name': pkg,
                        'asset_name':   aname,
                        'class_path':   cls,
                        'tags':         _tags,
                    }})
        """)

        raw = _exec_python(code)
        if not _ok(raw):
            msg = (raw or {}).get("message", "exec_python failed")
            ec  = (raw or {}).get("error_code", ERR_NOT_CONNECTED)
            return json.dumps(_make_result(
                success=False, stage="project_find_assets",
                message=msg, errors=[msg], error_code=ec,
                meta=_meta("project_find_assets", t0),
            ))

        out   = (raw.get("result") or raw.get("outputs") or {})
        if not isinstance(out, dict):
            out = {}
        assets     = out.get("assets", [])
        total      = out.get("total", len(assets))
        total_pages = max(1, -(-total // limit)) if total else 1

        outputs = {
            "total":       total,
            "page":        page,
            "page_size":   limit,
            "total_pages": total_pages,
            "assets":      assets,
        }
        return json.dumps(_make_result(
            success=True,
            stage="project_find_assets",
            message=f"Found {total} assets (page {page+1}/{total_pages}, showing {len(assets)})",
            outputs=outputs,
            meta=_meta("project_find_assets", t0, page=page, total_pages=total_pages),
        ))

    # ──────────────────────────────────────────────────────────────────────────
    # project_get_references
    # ──────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def project_get_references(
        ctx: Context,
        package_name: str,
        direction: str = "both",
        hard_only: bool = False,
    ) -> str:
        """Get asset references (dependencies and/or referencers) for a package.

        Uses the Asset Registry to traverse one level of the reference graph.

        Args:
            package_name: Full package path (e.g. '/Game/Blueprints/BP_HealthSystem').
            direction:    'in' (who uses this), 'out' (what this uses), or 'both'.
            hard_only:    If True, only hard (hard-reference) edges are included.

        Returns:
            JSON StructuredResult. Data keys present depend on direction:
              referencers  — packages that reference this asset   (direction in/both)
              dependencies — packages this asset depends on       (direction out/both)
        """
        import textwrap
        t0 = time.monotonic()

        if direction not in ("in", "out", "both"):
            return json.dumps(_make_result(
                success=False, stage="project_get_references",
                message=f"direction must be 'in', 'out', or 'both'; got '{direction}'",
                errors=[f"Invalid direction: {direction}"],
                error_code=ERR_INVALID_PATH,
                meta=_meta("project_get_references", t0),
            ))

        dep_type = "unreal.AssetRegistryDependencyType.HARD" if hard_only else "unreal.AssetRegistryDependencyType.ALL"

        code = textwrap.dedent(f"""
            import unreal, json
            _result = {{'package': {package_name!r}}}
            reg = unreal.AssetRegistryHelpers.get_asset_registry()
            pkg = {package_name!r}
            if {str(direction in ('in', 'both')).lower()}:
                refs = reg.get_referencers(pkg, {dep_type})
                _result['referencers'] = [str(r) for r in (refs or [])]
            if {str(direction in ('out', 'both')).lower()}:
                deps = reg.get_dependencies(pkg, {dep_type})
                _result['dependencies'] = [str(d) for d in (deps or [])]
        """)

        raw = _exec_python(code)
        if not _ok(raw):
            msg = (raw or {}).get("message", "exec_python failed")
            return json.dumps(_make_result(
                success=False, stage="project_get_references",
                message=msg, errors=[msg], error_code=ERR_NOT_CONNECTED,
                meta=_meta("project_get_references", t0),
            ))

        out = (raw.get("result") or raw.get("outputs") or {})
        if not isinstance(out, dict):
            out = {"package": package_name}

        return json.dumps(_make_result(
            success=True, stage="project_get_references",
            message=f"References for '{package_name}' (direction={direction})",
            outputs=out,
            meta=_meta("project_get_references", t0),
        ))

    # ──────────────────────────────────────────────────────────────────────────
    # project_trace_reference_chain
    # ──────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def project_trace_reference_chain(
        ctx: Context,
        start_package: str,
        direction: str = "in",
        max_depth: int = 3,
        stop_on_class: List[str] = [],
        max_nodes: int = 500,
    ) -> str:
        """BFS trace of the reference chain from a starting package.

        Traverses the asset reference graph and returns all reachable
        packages within max_depth hops.  Deduplicates visited nodes.
        Truncates when max_nodes is hit (sets truncated=true).

        Args:
            start_package:  Starting package (e.g. '/Game/Materials/M_DemoB').
            direction:      'in' (who references start) or 'out' (what start references).
            max_depth:      Maximum BFS depth. Default 3.
            stop_on_class:  Stop expanding a node if its class is in this list.
            max_nodes:      Hard cap on total nodes in result. Default 500.

        Returns:
            JSON StructuredResult with outputs.nodes list:
              [{package, depth, via}] plus depth_reached, truncated.
        """
        import textwrap
        t0 = time.monotonic()

        if direction not in ("in", "out"):
            return json.dumps(_make_result(
                success=False, stage="project_trace_reference_chain",
                message=f"direction must be 'in' or 'out'; got '{direction}'",
                errors=[f"Invalid direction: {direction}"],
                error_code=ERR_INVALID_PATH,
                meta=_meta("project_trace_reference_chain", t0),
            ))

        code = textwrap.dedent(f"""
            import unreal, json
            from collections import deque
            _result = {{'nodes': [], 'depth_reached': 0, 'truncated': False}}
            reg       = unreal.AssetRegistryHelpers.get_asset_registry()
            start     = {start_package!r}
            direction = {direction!r}
            max_depth = {max_depth}
            stop_cls  = set({json.dumps(stop_on_class)})
            max_nodes = {max_nodes}

            visited = {{start}}
            queue   = deque([(start, 0, '')])
            while queue and len(_result['nodes']) < max_nodes:
                pkg, depth, via = queue.popleft()
                if depth > 0:
                    _result['nodes'].append({{'package': pkg, 'depth': depth, 'via': via}})
                if depth >= max_depth:
                    continue
                # Get next hop
                if direction == 'in':
                    neighbours = reg.get_referencers(pkg, unreal.AssetRegistryDependencyType.ALL) or []
                else:
                    neighbours = reg.get_dependencies(pkg, unreal.AssetRegistryDependencyType.ALL) or []
                for nb in neighbours:
                    nb = str(nb)
                    if nb not in visited:
                        visited.add(nb)
                        queue.append((nb, depth + 1, pkg))
                        if depth + 1 > _result['depth_reached']:
                            _result['depth_reached'] = depth + 1

            if len(_result['nodes']) >= max_nodes:
                _result['truncated'] = True
        """)

        raw = _exec_python(code)
        if not _ok(raw):
            msg = (raw or {}).get("message", "exec_python failed")
            return json.dumps(_make_result(
                success=False, stage="project_trace_reference_chain",
                message=msg, errors=[msg], error_code=ERR_NOT_CONNECTED,
                meta=_meta("project_trace_reference_chain", t0),
            ))

        out = (raw.get("result") or raw.get("outputs") or {})
        if not isinstance(out, dict):
            out = {"nodes": [], "depth_reached": 0, "truncated": False}
        out.setdefault("start", start_package)
        out.setdefault("direction", direction)

        return json.dumps(_make_result(
            success=True, stage="project_trace_reference_chain",
            message=(
                f"Traced '{start_package}' {direction}bound: "
                f"{len(out.get('nodes', []))} nodes, depth {out.get('depth_reached', 0)}"
                + (" [truncated]" if out.get("truncated") else "")
            ),
            outputs=out,
            meta=_meta("project_trace_reference_chain", t0),
        ))

    # ──────────────────────────────────────────────────────────────────────────
    # project_find_blueprint_by_parent
    # ──────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def project_find_blueprint_by_parent(
        ctx: Context,
        parent_class: str,
        recursive: bool = True,
        limit: int = 200,
    ) -> str:
        """Find all Blueprints that derive from a given parent class.

        Searches the Asset Registry for Blueprint assets, then filters by the
        'ParentClass' tag.  The tag value typically looks like
        '/Script/Engine.Actor' but the tool also matches on bare class name
        (e.g. 'Actor' matches '/Script/Engine.Actor').

        Args:
            parent_class: Parent class name or full path (e.g. 'Actor', 'Character').
            recursive:    Search all sub-paths under /Game. Default True.
            limit:        Max assets returned. Default 200.

        Returns:
            JSON StructuredResult with outputs.assets (same shape as project_find_assets).
        """
        import textwrap
        t0 = time.monotonic()
        limit = max(1, min(limit, 1000))

        code = textwrap.dedent(f"""
            import unreal, json
            _result = {{'assets': [], 'total': 0}}
            reg = unreal.AssetRegistryHelpers.get_asset_registry()
            flt = unreal.ARFilter()
            flt.class_names      = ['Blueprint']
            flt.package_paths    = ['/Game']
            flt.recursive_paths  = {str(recursive).lower()}
            flt.recursive_classes = True
            assets = reg.get_assets(flt)
            parent_filter = {parent_class!r}.lower()
            matched = []
            for a in assets:
                _tags = {{}}
                try:
                    for k, v in a.tag_and_values.items():
                        _tags[str(k)] = str(v)
                except Exception:
                    pass
                pc = _tags.get('ParentClass', '').lower()
                if parent_filter in pc or pc.endswith('.' + parent_filter):
                    matched.append({{
                        'package_name': str(a.package_name),
                        'asset_name':   str(a.asset_name),
                        'class_path':   str(a.asset_class_path) if hasattr(a, 'asset_class_path') else str(a.asset_class),
                        'tags':         _tags,
                    }})
            _result['total']  = len(matched)
            _result['assets'] = matched[:{limit}]
        """)

        raw = _exec_python(code)
        if not _ok(raw):
            msg = (raw or {}).get("message", "exec_python failed")
            return json.dumps(_make_result(
                success=False, stage="project_find_blueprint_by_parent",
                message=msg, errors=[msg], error_code=ERR_NOT_CONNECTED,
                meta=_meta("project_find_blueprint_by_parent", t0),
            ))

        out = (raw.get("result") or raw.get("outputs") or {})
        if not isinstance(out, dict):
            out = {"assets": [], "total": 0}

        return json.dumps(_make_result(
            success=True, stage="project_find_blueprint_by_parent",
            message=f"Found {out.get('total', 0)} Blueprints with parent '{parent_class}'",
            outputs=out,
            meta=_meta("project_find_blueprint_by_parent", t0),
        ))

    # ──────────────────────────────────────────────────────────────────────────
    # project_list_subsystems
    # ──────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def project_list_subsystems(
        ctx: Context,
        category: str = "all",
        refresh: bool = False,
    ) -> str:
        """Enumerate Unreal Engine Subsystem classes by category.

        Uses unreal.get_all_classes_of_type() reflection — no hand-curated list.
        Results are cached for 10 s; pass refresh=True to force an immediate re-scan.

        Categories: engine | editor | gameinstance | localplayer | all

        Each entry:
          class     — UClass name (e.g. 'UEditorAssetSubsystem')
          module    — Outer package module name
          available — True (all discovered classes are considered available)

        Args:
            category: Which subsystem base class to enumerate. Default 'all'.
            refresh:  Force cache refresh. Default False.

        Returns:
            JSON StructuredResult with outputs matching the category filter.
        """
        global _SUBSYSTEM_CACHE, _SUBSYSTEM_CACHE_TS
        t0 = time.monotonic()

        valid_cats = {"engine", "editor", "gameinstance", "localplayer", "all"}
        if category not in valid_cats:
            return json.dumps(_make_result(
                success=False, stage="project_list_subsystems",
                message=f"category must be one of {sorted(valid_cats)}, got '{category}'",
                errors=[f"Invalid category: {category}"],
                error_code=ERR_SUBSYSTEM_ENUM_FAILED,
                meta=_meta("project_list_subsystems", t0),
            ))

        now = time.monotonic()
        if refresh or not _SUBSYSTEM_CACHE or (now - _SUBSYSTEM_CACHE_TS) > _SUBSYSTEM_CACHE_TTL:
            _SUBSYSTEM_CACHE    = _refresh_subsystem_cache()
            _SUBSYSTEM_CACHE_TS = now

        cache = _SUBSYSTEM_CACHE
        if category == "all":
            outputs = {k: cache.get(k, []) for k in ("engine", "editor", "gameinstance", "localplayer")}
        else:
            outputs = {category: cache.get(category, [])}

        total = sum(len(v) for v in outputs.values())
        return json.dumps(_make_result(
            success=True, stage="project_list_subsystems",
            message=f"Listed {total} subsystem classes (category={category})",
            outputs=outputs,
            meta=_meta("project_list_subsystems", t0),
        ))

    logger.info(
        "Project Intelligence tools registered: "
        "project_find_assets, project_get_references, project_trace_reference_chain, "
        "project_find_blueprint_by_parent, project_list_subsystems"
    )
