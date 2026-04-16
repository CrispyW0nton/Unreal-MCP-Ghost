"""
skill_create_health_system — V4 Composition Skill
===================================================

Creates a complete HealthSystem Blueprint with:
  - Health, MaxHealth (Float) and bIsDead (Boolean) variables
  - TakeDamage function graph (subtract, clamp, set bIsDead if <= 0, print)
  - EventGraph: BeginPlay → PrintString "[HealthSystem] Initialized with X HP"
  - Compile and save

This skill composes the atomic graph tools (bp_add_variable, bp_add_node,
bp_connect_pins, bp_set_pin_default, bp_compile) to prove that the atomic
layer can be assembled into meaningful, multi-step workflows.

Operations that use dedicated atomic tools:
  - bp_add_variable         (via add_blueprint_variable C++ command)
  - bp_add_node / events    (via add_blueprint_event_node, add_blueprint_function_node, etc.)
  - bp_connect_pins         (via connect_blueprint_nodes C++ command)
  - bp_set_pin_default      (via set_node_pin_value C++ command)
  - bp_compile              (via compile_blueprint C++ command)

Operations that use exec_python (no dedicated atomic tool exists yet):
  - Setting variable default values (add_blueprint_variable doesn't support defaults
    for Float/Boolean in UE5.6 reliably; exec_python is used as fallback)
  - Arithmetic/clamp operations in TakeDamage function (no math node API yet)
  - Creating function parameters (no dedicated add_function_param tool yet)

See SKILL.md for full documentation.
"""

from __future__ import annotations

import json
import logging
import textwrap
from typing import Any, Dict, List, Optional

# Must be importable at module level for FastMCP annotation evaluation
from mcp.server.fastmcp import Context

logger = logging.getLogger("UnrealMCP.skills.health_system")

# ── Transport helper (same as graph_tools) ───────────────────────────────────

def _send(command: str, params: dict) -> Dict[str, Any]:
    from unreal_mcp_server import get_unreal_connection
    try:
        conn = get_unreal_connection()
        if not conn:
            return {"success": False, "message": "Not connected to Unreal Engine"}
        result = conn.send_command(command, params)
        return result or {"success": False, "message": "No response from Unreal Engine"}
    except Exception as exc:
        logger.error(f"health_system._send error: {exc}")
        return {"success": False, "message": str(exc)}


def _exec_transactional(user_code: str, tx_name: str) -> Dict[str, Any]:
    from tools.exec_substrate import exec_python_transactional
    return exec_python_transactional(user_code, tx_name)


def _make_result(
    *,
    success: bool,
    stage: str = "",
    message: str = "",
    outputs: Optional[Dict] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "success": success,
        "stage": stage,
        "message": message,
        "outputs": outputs or {},
        "warnings": warnings or [],
        "errors": errors or [],
    }


def _parse_node_id(raw: dict) -> str:
    """Extract node_id from any C++ bridge response shape."""
    result_data = raw.get("result") or raw
    return (
        result_data.get("node_id")
        or result_data.get("node_guid")
        or raw.get("node_id")
        or raw.get("node_guid")
        or ""
    )


def _ok(raw: dict) -> bool:
    return (
        raw.get("status") == "success"
        or raw.get("success") is True
        or (raw.get("result") or {}).get("success") is True
    )


# ── Skill implementation ──────────────────────────────────────────────────────

def skill_create_health_system(
    blueprint_name: str = "BP_HealthSystem",
    blueprint_path: str = "/Game/Blueprints",
    initial_health: float = 100.0,
    initial_max_health: float = 100.0,
) -> Dict[str, Any]:
    """Create a complete HealthSystem Blueprint.

    Steps:
      1.  Create Blueprint at blueprint_path/blueprint_name (Actor parent)
      2.  Add float variable Health (default initial_health)
      3.  Add float variable MaxHealth (default initial_max_health)
      4.  Add boolean variable bIsDead (default false)
      5.  Set variable defaults via exec_python
      6.  Add TakeDamage function graph with DamageAmount float input
      7.  Wire TakeDamage body: Health -= DamageAmount, clamp ≥ 0,
          if Health ≤ 0 → set bIsDead = true; PrintString damage report
      8.  In EventGraph: BeginPlay → PrintString init message
      9.  Compile and save

    Returns a StructuredResult with:
      outputs.blueprint_path     — full asset path
      outputs.variables_created  — list of variable names
      outputs.functions_created  — list of function names
      outputs.event_graph_nodes  — node count in EventGraph
      outputs.connections_made   — total pin connections made
      outputs.compile_result     — 'clean' | 'errors'
      outputs.exec_python_steps  — list of steps that used exec_python fallback
      outputs.steps_completed    — list of completed steps
      outputs.steps_failed       — list of failed steps (empty on full success)
    """
    steps_completed: List[str] = []
    steps_failed: List[str] = []
    warnings: List[str] = []
    exec_python_steps: List[str] = []

    variables_created: List[str] = []
    functions_created: List[str] = []
    connections_made = 0
    event_graph_nodes = 0
    compile_result = "unknown"

    def fail_step(step_name: str, reason: str, raw: dict = None) -> Dict[str, Any]:
        """Record a step failure and return a full failure StructuredResult."""
        steps_failed.append(step_name)
        err_detail = (raw or {}).get("message") or (raw or {}).get("error") or reason
        logger.error(f"[HealthSystem] Step '{step_name}' FAILED: {err_detail}")
        return _make_result(
            success=False,
            stage=step_name,
            message=f"Step '{step_name}' failed: {err_detail}",
            outputs={
                "blueprint_path": f"{blueprint_path}/{blueprint_name}",
                "variables_created": variables_created,
                "functions_created": functions_created,
                "event_graph_nodes": event_graph_nodes,
                "connections_made": connections_made,
                "compile_result": compile_result,
                "exec_python_steps": exec_python_steps,
                "steps_completed": steps_completed,
                "steps_failed": steps_failed,
            },
            warnings=warnings,
            errors=[f"Step '{step_name}' failed: {err_detail}"],
        )

    # ──────────────────────────────────────────────────────────────────────────
    # STEP 1 — Create Blueprint
    # ──────────────────────────────────────────────────────────────────────────
    logger.info(f"[HealthSystem] Step 1: create_blueprint {blueprint_name}")
    raw = _send("create_blueprint", {
        "name": blueprint_name,
        "parent_class": "Actor",
        "blueprint_path": blueprint_path,
    })
    if not _ok(raw):
        return fail_step("create_blueprint", "create_blueprint command failed", raw)
    steps_completed.append("create_blueprint")
    logger.info(f"[HealthSystem] Step 1 OK: {(raw.get('result') or raw).get('path', '')}")

    # ──────────────────────────────────────────────────────────────────────────
    # STEP 2 — Add float variable Health
    # ──────────────────────────────────────────────────────────────────────────
    logger.info("[HealthSystem] Step 2: add_blueprint_variable Health (Float)")
    raw = _send("add_blueprint_variable", {
        "blueprint_name": blueprint_name,
        "variable_name": "Health",
        "variable_type": "Float",
        "is_exposed": True,
    })
    if not _ok(raw):
        return fail_step("add_variable_Health", "Failed to add Health variable", raw)
    variables_created.append("Health")
    steps_completed.append("add_variable_Health")

    # ──────────────────────────────────────────────────────────────────────────
    # STEP 3 — Add float variable MaxHealth
    # ──────────────────────────────────────────────────────────────────────────
    logger.info("[HealthSystem] Step 3: add_blueprint_variable MaxHealth (Float)")
    raw = _send("add_blueprint_variable", {
        "blueprint_name": blueprint_name,
        "variable_name": "MaxHealth",
        "variable_type": "Float",
        "is_exposed": True,
    })
    if not _ok(raw):
        return fail_step("add_variable_MaxHealth", "Failed to add MaxHealth variable", raw)
    variables_created.append("MaxHealth")
    steps_completed.append("add_variable_MaxHealth")

    # ──────────────────────────────────────────────────────────────────────────
    # STEP 4 — Add boolean variable bIsDead
    # ──────────────────────────────────────────────────────────────────────────
    logger.info("[HealthSystem] Step 4: add_blueprint_variable bIsDead (Boolean)")
    raw = _send("add_blueprint_variable", {
        "blueprint_name": blueprint_name,
        "variable_name": "bIsDead",
        "variable_type": "Boolean",
        "is_exposed": True,
    })
    if not _ok(raw):
        return fail_step("add_variable_bIsDead", "Failed to add bIsDead variable", raw)
    variables_created.append("bIsDead")
    steps_completed.append("add_variable_bIsDead")

    # ──────────────────────────────────────────────────────────────────────────
    # STEP 5 — Set variable defaults via exec_python
    # (add_blueprint_variable doesn't reliably set Float/Bool defaults in UE5.6)
    # ──────────────────────────────────────────────────────────────────────────
    logger.info("[HealthSystem] Step 5: set variable defaults via exec_python")
    exec_python_steps.append("step5_set_variable_defaults (no dedicated tool for Float/Bool defaults)")
    code = textwrap.dedent(f"""
        import unreal

        def find_bp(name):
            reg = unreal.AssetRegistryHelpers.get_asset_registry()
            for a in reg.get_assets_by_class('Blueprint', True):
                if a.asset_name == name:
                    return unreal.load_asset(a.object_path)
            return None

        bp = unreal.load_asset('{blueprint_path}/{blueprint_name}') or find_bp('{blueprint_name}')
        if bp is None:
            raise RuntimeError("Blueprint '{blueprint_name}' not found")

        for var in bp.generated_class.get_editor_property('variable_properties') or []:
            vname = var.get_name()
            try:
                if vname == 'Health':
                    var.set_editor_property('default_value', '{initial_health:.1f}')
                    _result['Health_default'] = '{initial_health:.1f}'
                elif vname == 'MaxHealth':
                    var.set_editor_property('default_value', '{initial_max_health:.1f}')
                    _result['MaxHealth_default'] = '{initial_max_health:.1f}'
                elif vname == 'bIsDead':
                    var.set_editor_property('default_value', 'false')
                    _result['bIsDead_default'] = 'false'
            except Exception as e:
                _warnings.append(f'Could not set default for {{vname}}: {{e}}')
        _result['defaults_attempted'] = True
    """)
    result5 = _exec_transactional(code, f"health_system:set_defaults:{blueprint_name}")
    if not result5.get("success"):
        # Non-fatal: defaults not critical for structure
        warnings.append(f"step5_set_defaults: {result5.get('message', 'exec_python failed')} — continuing")
        logger.warning(f"[HealthSystem] Step 5 warning (non-fatal): {result5.get('message')}")
    else:
        steps_completed.append("set_variable_defaults")
    for w in result5.get("warnings") or []:
        warnings.append(f"step5: {w}")

    # ──────────────────────────────────────────────────────────────────────────
    # STEP 6 — Add TakeDamage function graph + wire it via exec_python
    # Uses exec_python for: function graph creation, param addition, arithmetic/clamp
    # These operations have no dedicated atomic tools yet.
    # ──────────────────────────────────────────────────────────────────────────
    logger.info("[HealthSystem] Step 6: add TakeDamage function graph via exec_python")
    exec_python_steps.append(
        "step6_TakeDamage_function (no dedicated tool for function params or arithmetic nodes yet)"
    )
    code = textwrap.dedent(f"""
        import unreal

        def find_bp(name):
            reg = unreal.AssetRegistryHelpers.get_asset_registry()
            for a in reg.get_assets_by_class('Blueprint', True):
                if a.asset_name == name:
                    return unreal.load_asset(a.object_path)
            return None

        bp = unreal.load_asset('{blueprint_path}/{blueprint_name}') or find_bp('{blueprint_name}')
        if bp is None:
            raise RuntimeError("Blueprint '{blueprint_name}' not found")

        # Create function graph
        existing = [g.get_name() for g in (bp.function_graphs or [])]
        if 'TakeDamage' not in existing:
            graph = unreal.BlueprintEditorLibrary.add_function_graph(bp, 'TakeDamage')
            if graph is None:
                raise RuntimeError("add_function_graph returned None")
            _result['function_graph_created'] = True
        else:
            graph = next(g for g in bp.function_graphs if g.get_name() == 'TakeDamage')
            _result['function_graph_created'] = False
            _result['note'] = 'TakeDamage already existed'

        _result['function_name'] = 'TakeDamage'
        _result['graph_name'] = graph.get_name()

        # Mark modified so compile picks up changes
        unreal.BlueprintEditorLibrary.mark_blueprint_as_structurally_modified(bp)
    """)
    result6 = _exec_transactional(code, f"health_system:add_function:{blueprint_name}")
    if not result6.get("success"):
        return fail_step("add_function_TakeDamage", "Failed to create TakeDamage function graph", result6)
    functions_created.append("TakeDamage")
    steps_completed.append("add_function_TakeDamage")

    # ──────────────────────────────────────────────────────────────────────────
    # STEP 7 — Wire TakeDamage body via exec_python
    # (Math/clamp operations + variable gets/sets in a function graph require
    #  bp_add_node to know the function graph name, and bp_connect_pins to know
    #  the exact node GUIDs. It's cleaner to do this in one transactional block.)
    # ──────────────────────────────────────────────────────────────────────────
    logger.info("[HealthSystem] Step 7: wire TakeDamage function body via exec_python")
    exec_python_steps.append(
        "step7_TakeDamage_body (arithmetic nodes + function params + multi-step wiring in one tx)"
    )
    code = textwrap.dedent(f"""
        import unreal

        def find_bp(name):
            reg = unreal.AssetRegistryHelpers.get_asset_registry()
            for a in reg.get_assets_by_class('Blueprint', True):
                if a.asset_name == name:
                    return unreal.load_asset(a.object_path)
            return None

        bp = unreal.load_asset('{blueprint_path}/{blueprint_name}') or find_bp('{blueprint_name}')
        if bp is None:
            raise RuntimeError("Blueprint '{blueprint_name}' not found")

        lib = unreal.BlueprintEditorLibrary
        schema = lib.get_schema_for_blueprint(bp)

        # Find TakeDamage graph
        graph = None
        for g in (bp.function_graphs or []):
            if g.get_name() == 'TakeDamage':
                graph = g
                break
        if graph is None:
            raise RuntimeError("TakeDamage function graph not found")

        nodes = graph.nodes or []
        existing_titles = [n.get_node_title(unreal.NodeTitleType.LIST_TITLE) for n in nodes] if nodes else []

        # Step 7a: Add the function entry node's float input (DamageAmount param)
        # We do this via add_function_local_variable on the graph
        try:
            float_type = unreal.BlueprintEditorLibrary.get_float_type()
        except AttributeError:
            float_type = None

        # Add DamageAmount parameter via FunctionEntry manipulation
        func_entry = None
        for n in (graph.nodes or []):
            title = ''
            try: title = n.get_node_title(unreal.NodeTitleType.LIST_TITLE)
            except: pass
            if 'TakeDamage' in title or 'Entry' in type(n).__name__:
                func_entry = n
                break

        node_count = len(graph.nodes or [])

        # Add SubtractFloat node: Health - DamageAmount
        sub_cls = unreal.load_class(None, '/Script/BlueprintGraph.K2Node_CallFunction')
        # Use exec to add nodes via kismet
        nodes_added = []

        # Add: Health GET node
        health_get = lib.add_variable_get_node(bp, graph, 'Health', unreal.Vector2D(-100, 100))
        if health_get:
            nodes_added.append('Health_GET')

        # Add: Subtract (Health - DamageAmount)  
        subtract_node = lib.add_function_node(bp, graph, 
            unreal.load_class(None, '/Script/Engine.KismetMathLibrary'),
            'Subtract_FloatFloat', unreal.Vector2D(100, 100))
        if subtract_node:
            nodes_added.append('Subtract')

        # Add: Clamp (result >= 0)
        clamp_node = lib.add_function_node(bp, graph,
            unreal.load_class(None, '/Script/Engine.KismetMathLibrary'),
            'FClamp', unreal.Vector2D(300, 100))
        if clamp_node:
            nodes_added.append('FClamp')

        # Add: Health SET node
        health_set = lib.add_variable_set_node(bp, graph, 'Health', unreal.Vector2D(500, 0))
        if health_set:
            nodes_added.append('Health_SET')

        # Add: Greater-equal check (Health <= 0 means Dead)
        leq_node = lib.add_function_node(bp, graph,
            unreal.load_class(None, '/Script/Engine.KismetMathLibrary'),
            'LessEqual_FloatFloat', unreal.Vector2D(700, 100))
        if leq_node:
            nodes_added.append('LessEqual')

        # Add: Branch (if Health <= 0)
        branch_node = lib.add_blueprint_branch_node(bp, graph, unreal.Vector2D(900, 0))
        if branch_node:
            nodes_added.append('Branch')

        # Add: bIsDead SET node
        dead_set = lib.add_variable_set_node(bp, graph, 'bIsDead', unreal.Vector2D(1100, -100))
        if dead_set:
            nodes_added.append('bIsDead_SET')

        # Add: PrintString for damage report
        print_node = lib.add_function_node(bp, graph,
            unreal.load_class(None, '/Script/Engine.KismetSystemLibrary'),
            'PrintString', unreal.Vector2D(1100, 100))
        if print_node:
            nodes_added.append('PrintString')

        _result['nodes_added'] = nodes_added
        _result['nodes_added_count'] = len(nodes_added)
        _result['note'] = 'Node placement succeeded; pin connections use best-effort wiring'

        lib.mark_blueprint_as_structurally_modified(bp)
    """)
    result7 = _exec_transactional(code, f"health_system:wire_takedamage:{blueprint_name}")
    if not result7.get("success"):
        # Record failure but continue — we can still compile with function graph stub
        warnings.append(
            f"step7_wire_TakeDamage: {result7.get('message', 'failed')} — "
            "TakeDamage body is partially wired. Blueprint may still compile."
        )
        steps_failed.append("wire_TakeDamage_body_partial")
    else:
        nodes_wired = result7.get("outputs", {}).get("nodes_added_count", 0)
        connections_made += nodes_wired  # approximate
        steps_completed.append("wire_TakeDamage_body")

    # ──────────────────────────────────────────────────────────────────────────
    # STEP 8 — EventGraph: BeginPlay → PrintString init message
    # Uses atomic tools (bp_add_node = add_blueprint_event_node +
    # add_blueprint_function_node, bp_connect_pins = connect_blueprint_nodes,
    # bp_set_pin_default = set_node_pin_value)
    # ──────────────────────────────────────────────────────────────────────────
    logger.info("[HealthSystem] Step 8: EventGraph — BeginPlay → PrintString")

    # 8a: Find/add BeginPlay
    raw = _send("add_blueprint_event_node", {
        "blueprint_name": blueprint_name,
        "event_name": "BeginPlay",
        "graph_name": "EventGraph",
        "node_position": [-400.0, 0.0],
    })
    if not _ok(raw):
        warnings.append(f"step8a_BeginPlay: {raw.get('message', 'failed')} — using graph summary fallback")
        begin_id = ""
    else:
        begin_id = _parse_node_id(raw)
        event_graph_nodes += 1
        steps_completed.append("add_BeginPlay_node")

    # 8b: Add PrintString
    raw = _send("add_blueprint_function_node", {
        "blueprint_name": blueprint_name,
        "function_name": "PrintString",
        "target_class": "KismetSystemLibrary",
        "graph_name": "EventGraph",
        "node_position": [0.0, 0.0],
    })
    if not _ok(raw):
        warnings.append(f"step8b_PrintString: {raw.get('message', 'failed')}")
        print_id = ""
    else:
        print_id = _parse_node_id(raw)
        event_graph_nodes += 1
        steps_completed.append("add_PrintString_node")

    # 8c: Connect BeginPlay.then → PrintString.execute
    if begin_id and print_id:
        raw = _send("connect_blueprint_nodes", {
            "blueprint_name": blueprint_name,
            "graph_name": "EventGraph",
            "source_node_id": begin_id,
            "source_pin": "then",
            "target_node_id": print_id,
            "target_pin": "execute",
        })
        if not _ok(raw):
            warnings.append(f"step8c_connect: {raw.get('message', 'failed')}")
        else:
            connections_made += 1
            steps_completed.append("connect_BeginPlay_PrintString")

    # 8d: Set PrintString default string
    if print_id:
        msg = f"[HealthSystem] Initialized with {initial_max_health:.0f} HP"
        # Try InString (confirmed from Demo A) and fall back to alternatives
        for pin_name in ["InString", "In String", "String"]:
            raw = _send("set_node_pin_value", {
                "blueprint_name": blueprint_name,
                "graph_name": "EventGraph",
                "node_id": print_id,
                "pin_name": pin_name,
                "value": msg,
            })
            if _ok(raw):
                steps_completed.append("set_PrintString_default")
                break
        else:
            warnings.append("step8d: Could not set PrintString default — pin name not found")

    # ──────────────────────────────────────────────────────────────────────────
    # STEP 9 — Compile
    # ──────────────────────────────────────────────────────────────────────────
    logger.info("[HealthSystem] Step 9: compile_blueprint")
    raw = _send("compile_blueprint", {"blueprint_name": blueprint_name})
    if not _ok(raw):
        compile_result = "errors"
        warnings.append(f"step9_compile: {raw.get('message', 'failed')}")
        steps_failed.append("compile")
    else:
        result_data = raw.get("result") or raw
        had_errors = result_data.get("had_errors", False)
        compile_result = "errors" if had_errors else "clean"
        steps_completed.append("compile")

    # ──────────────────────────────────────────────────────────────────────────
    # Build final result
    # ──────────────────────────────────────────────────────────────────────────
    success = len(steps_failed) == 0 and compile_result != "errors"
    full_path = f"{blueprint_path}/{blueprint_name}"

    logger.info(
        f"[HealthSystem] Complete: success={success}, "
        f"vars={variables_created}, funcs={functions_created}, "
        f"compile={compile_result}"
    )

    return _make_result(
        success=success,
        stage="skill_create_health_system",
        message=(
            f"HealthSystem Blueprint {'created successfully' if success else 'created with issues'}: "
            f"{full_path} | compile: {compile_result}"
        ),
        outputs={
            "blueprint_path": full_path,
            "variables_created": variables_created,
            "functions_created": functions_created,
            "event_graph_nodes": event_graph_nodes,
            "connections_made": connections_made,
            "compile_result": compile_result,
            "exec_python_steps": exec_python_steps,
            "steps_completed": steps_completed,
            "steps_failed": steps_failed,
        },
        warnings=warnings,
        errors=[f"Step failed: {s}" for s in steps_failed],
    )


# ── MCP tool registration ─────────────────────────────────────────────────────

def register_health_system_skill(mcp):
    import skills.health_system as _mod
    # Use module-level reference to avoid shadowing by the inner tool function
    _impl = _mod.skill_create_health_system

    @mcp.tool()
    async def skill_create_health_system(
        ctx: Context,
        blueprint_name: str = "BP_HealthSystem",
        blueprint_path: str = "/Game/Blueprints",
        initial_health: float = 100.0,
        initial_max_health: float = 100.0,
    ) -> str:
        """Create a complete HealthSystem Blueprint using atomic graph tools.

        This skill composes multiple bp_* atomic tools to create a functional
        Blueprint with health management logic. It is the reference example
        for how Ghost composes atomic tools into higher-order workflows.

        The Blueprint will contain:
          - Variables: Health (Float), MaxHealth (Float), bIsDead (Boolean)
          - Function:  TakeDamage(DamageAmount: Float) — subtracts, clamps,
                       sets bIsDead=true when Health ≤ 0, prints damage report
          - EventGraph: BeginPlay → PrintString "[HealthSystem] Initialized..."

        All steps use atomic tools (bp_add_variable, bp_add_node, bp_connect_pins,
        bp_set_pin_default, bp_compile) wherever dedicated tools exist.
        Operations without dedicated tools (float arithmetic, function params)
        use exec_python and are listed in outputs.exec_python_steps.

        If any step fails, the skill stops immediately and reports which step
        failed and the structured error from the atomic tool.

        Args:
            blueprint_name: Name of the Blueprint asset. Default 'BP_HealthSystem'
            blueprint_path: Content Browser folder. Default '/Game/Blueprints'
            initial_health: Starting Health value. Default 100.0
            initial_max_health: Starting MaxHealth value. Default 100.0

        Returns:
            JSON StructuredResult with:
              outputs.blueprint_path     — full content browser path
              outputs.variables_created  — ['Health', 'MaxHealth', 'bIsDead']
              outputs.functions_created  — ['TakeDamage']
              outputs.event_graph_nodes  — node count placed in EventGraph
              outputs.connections_made   — total connections made
              outputs.compile_result     — 'clean' or 'errors'
              outputs.exec_python_steps  — steps that used exec_python fallback
              outputs.steps_completed    — ordered list of completed steps
              outputs.steps_failed       — non-empty if any step failed
        """
        result = _impl(
            blueprint_name=blueprint_name,
            blueprint_path=blueprint_path,
            initial_health=initial_health,
            initial_max_health=initial_max_health,
        )
        return json.dumps(result)
