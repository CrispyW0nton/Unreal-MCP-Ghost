# Skills — V4 Composition Layer

Skills are higher-order, multi-step workflows that compose atomic graph tools
into reliable, end-to-end Blueprint creation sequences.

Each skill is documented here with:
- Description
- Required atomic tools
- Pre/post-conditions
- Failure modes and what the skill does when they occur
- Validation steps
- Example agent prompt

---

## skill_create_health_system

**File:** `skills/health_system.py`
**MCP tool name:** `skill_create_health_system`
**Version:** V4.1 (2026-04-16)

### Description

Creates a complete HealthSystem Blueprint with:

- **3 variables**: `Health` (Float, default 100.0), `MaxHealth` (Float, default 100.0), `bIsDead` (Boolean, default false)
- **1 function graph**: `TakeDamage(DamageAmount: Float)` — subtracts damage from Health, clamps to 0, sets `bIsDead = true` when Health ≤ 0, prints a damage report
- **EventGraph logic**: `BeginPlay → PrintString("[HealthSystem] Initialized with X HP")`
- **Clean compile** after all steps

### Atomic Tools Used

| Step | Tool | Purpose |
|------|------|---------|
| 1 | `create_blueprint` (C++ bridge) | Create the Blueprint asset |
| 2–4 | `add_blueprint_variable` (C++ bridge) | Add Health, MaxHealth, bIsDead |
| 8a | `add_blueprint_event_node` (C++ bridge) | Add BeginPlay event |
| 8b | `add_blueprint_function_node` (C++ bridge) | Add PrintString node |
| 8c | `connect_blueprint_nodes` (C++ bridge) | BeginPlay.then → PrintString.execute |
| 8d | `set_node_pin_value` (C++ bridge) | Set init message string |
| 9 | `compile_blueprint` (C++ bridge) | Compile and save |

### exec_python Fallbacks

These steps use `exec_python` because no dedicated atomic tool exists yet.
Each is a candidate for a future dedicated tool.

| Step | Reason |
|------|--------|
| 5 — Set variable defaults | `add_blueprint_variable` C++ bridge does not set Float/Bool defaults reliably in UE5.6 |
| 6 — Create TakeDamage function graph | No dedicated `bp_add_function_graph` C++ command yet; uses `BlueprintEditorLibrary.add_function_graph` |
| 7 — Wire TakeDamage body | Math nodes (Subtract, FClamp, LessEqual) + variable SET nodes in function graph require multi-step transactional operation; no single atomic API exists yet |

### Pre-conditions

- UE5 is running with the UnrealMCP plugin loaded
- Connection to UE5 is established (ping returns success)
- The target `blueprint_path` folder exists in the Content Browser

### Post-conditions (on success)

- `/blueprint_path/blueprint_name` exists in the Content Browser
- Blueprint has exactly 3 variables: Health, MaxHealth, bIsDead
- Blueprint has a TakeDamage function graph
- EventGraph has ≥ 2 nodes (BeginPlay, PrintString) connected
- Blueprint compiles clean (had_errors = False)

### Failure Modes

The skill uses **stop-on-first-fatal-failure** semantics:

| Failure | Behaviour |
|---------|-----------|
| `create_blueprint` fails | **STOP** immediately — returns failure result with stage='create_blueprint' |
| Any `add_blueprint_variable` fails | **STOP** — partial variable set reported in outputs.variables_created |
| `add_function_TakeDamage` fails | **STOP** — no function graph created |
| `wire_TakeDamage_body` fails | **WARN + CONTINUE** — body wiring failure is non-fatal; Blueprint can still compile as a stub |
| BeginPlay/PrintString node fails | **WARN + CONTINUE** — non-fatal; compile will still run |
| `compile_blueprint` fails | **WARN** — compile_result = 'errors'; skill returns success=False |

The distinction between STOP and WARN+CONTINUE:
- Variables and function graphs are structural — they must succeed for the skill to produce anything meaningful
- Node wiring in EventGraph is additive — partial wiring still produces a valid (if incomplete) Blueprint

### Structured Result

```json
{
  "success": true,
  "stage": "skill_create_health_system",
  "message": "HealthSystem Blueprint created successfully: /Game/Blueprints/BP_HealthSystem | compile: clean",
  "outputs": {
    "blueprint_path": "/Game/Blueprints/BP_HealthSystem",
    "variables_created": ["Health", "MaxHealth", "bIsDead"],
    "functions_created": ["TakeDamage"],
    "event_graph_nodes": 2,
    "connections_made": 1,
    "compile_result": "clean",
    "exec_python_steps": [
      "step5_set_variable_defaults (no dedicated tool for Float/Bool defaults)",
      "step6_TakeDamage_function (no dedicated tool for function params or arithmetic nodes yet)",
      "step7_TakeDamage_body (arithmetic nodes + function params + multi-step wiring in one tx)"
    ],
    "steps_completed": [
      "create_blueprint",
      "add_variable_Health",
      "add_variable_MaxHealth",
      "add_variable_bIsDead",
      "set_variable_defaults",
      "add_function_TakeDamage",
      "wire_TakeDamage_body",
      "add_BeginPlay_node",
      "add_PrintString_node",
      "connect_BeginPlay_PrintString",
      "set_PrintString_default",
      "compile"
    ],
    "steps_failed": []
  },
  "warnings": [],
  "errors": []
}
```

### Validation Steps

After running the skill, validate with:

```python
# 1. Check the Blueprint exists
r = send("get_blueprint_info", {"blueprint_name": "BP_HealthSystem"})
assert r["success"] or r["status"] == "success"

# 2. Check variables via graph summary
r = send("get_blueprint_variables", {"blueprint_name": "BP_HealthSystem"})
var_names = [v["name"] for v in r.get("result", {}).get("variables", [])]
assert "Health" in var_names
assert "MaxHealth" in var_names
assert "bIsDead" in var_names

# 3. Check EventGraph has nodes
r = send("get_blueprint_nodes", {"blueprint_name": "BP_HealthSystem", "graph_name": "EventGraph"})
assert len(r.get("result", {}).get("nodes", [])) >= 2

# 4. Check compile is clean
r = send("compile_blueprint", {"blueprint_name": "BP_HealthSystem"})
assert not r.get("result", {}).get("had_errors", True)
```

### Example Agent Prompt

```
Use the skill_create_health_system tool to create a health system for my game.
Name it BP_PlayerHealth, put it in /Game/Characters, start with 150 HP.
Report what variables, functions and nodes were created and whether the compile was clean.
```

### Known Limitations (V4.1)

1. **TakeDamage function body wiring**: The skill uses exec_python for arithmetic nodes (Subtract, FClamp, LessEqual) because `bp_add_node` does not yet support adding nodes into non-EventGraph function graphs. This is tracked as a future enhancement.

2. **Function parameters**: The `DamageAmount` float input parameter to TakeDamage is created via `BlueprintEditorLibrary.add_function_graph` but getting it properly wired to the Subtract node requires access to the FunctionEntry node's pin. This requires `bp_inspect_node` on the function graph, which will be added in V4.2.

3. **Variable default values**: UE5.6's `add_blueprint_variable` C++ command does not consistently apply default values for Float and Boolean types when set at creation time. The skill uses an exec_python fallback that sets them via the Blueprint's generated class properties. If this fails (non-fatal warning), the defaults must be set manually in the Blueprint editor.

4. **BlueprintEditorLibrary availability**: `add_function_node`, `add_variable_get_node`, `add_variable_set_node`, `add_blueprint_branch_node` are UE 5.3+ Python APIs. They may not be available in older UE versions.

### Future Enhancements (Deferred)

- Dedicated `bp_add_function_param` tool to add typed input/output pins to function graphs
- `bp_add_node` support for function-graph targets (not just EventGraph)
- Native C++ bridge for `set_blueprint_variable_default` to eliminate exec_python step 5
- `bp_add_local_variable` for function-local variables
