# Skill: `skill_audit_blueprint_health`

**Version:** V5.0  
**File:** `skills/audit_blueprint_health/skill.py`  
**Category:** Blueprint Quality Assurance  
**Phase:** Phase 3 — Project Intelligence

---

## Purpose

Audits a Blueprint asset and produces a structured health report with a 0–100 score.
Calls only existing atomic tools; never uses exec_python for graph analysis.

---

## Signature

```python
skill_audit_blueprint_health(
    blueprint_name: str,          # Asset name e.g. 'BP_HealthSystem'
    blueprint_path: str | None = None,   # Full path; None → /Game/Blueprints/<name>
    compile_check: bool = True,   # Whether to run bp_compile
) -> StructuredResult
```

---

## Atomic Tools Used

| Tool | Purpose |
|------|---------|
| `get_blueprint_nodes` (C++ bridge) | Fetch EventGraph and function graph nodes |
| `exec_python` | Fetch variable list and function graph names |
| `compile_blueprint` (C++ bridge) | Run compile; read had_errors |
| Asset Registry exec_python | Count incoming references |

---

## Output Shape

```json
{
  "success": true,
  "stage": "skill_audit_blueprint_health",
  "message": "Blueprint 'BP_HealthSystem' health: 95/100 (HEALTHY). 3 vars, 1 fn, 11 nodes, compile=OK",
  "outputs": {
    "blueprint_name": "BP_HealthSystem",
    "blueprint_path": "/Game/Blueprints/BP_HealthSystem",
    "compiles_clean": true,
    "variable_count": 3,
    "function_graph_count": 1,
    "node_count_total": 11,
    "disconnected_exec_pins": [],
    "disconnected_input_pins": [],
    "unused_variables": [],
    "incoming_references": 0,
    "warnings": [],
    "health_score": 100,
    "steps_completed": [
      "get_event_graph_nodes",
      "fetch_metadata",
      "analyse_event_graph",
      "analyse_function_graphs",
      "compile_check",
      "incoming_references"
    ],
    "steps_failed": []
  },
  "warnings": [],
  "errors": [],
  "meta": {
    "tool": "skill_audit_blueprint_health",
    "duration_ms": 312
  }
}
```

---

## Health Score Formula

| Condition | Penalty |
|-----------|---------|
| Compile fails | -30 |
| Each disconnected exec pin | -10 (max -20) |
| Each unused variable | -5 (max -15) |
| Each unconnected input pin (no default) | -5 (max -10) |

Score is clamped to [0, 100].

| Range | Grade |
|-------|-------|
| 90–100 | HEALTHY |
| 70–89  | GOOD |
| 40–69  | WARNING |
| 0–39   | POOR |

---

## Pre-conditions

- UE5 editor running with UnrealMCP plugin (port 55557)
- Blueprint exists at the given path
- Ping succeeds

## Post-conditions (on success)

- `compiles_clean` accurately reflects `had_errors` from bp_compile
- `variable_count` == number of Blueprint member variables
- `function_graph_count` == number of function graphs (not EventGraph)
- `node_count_total` == sum of nodes across all graphs
- `health_score` in [0, 100]

## Failure modes

- Blueprint not found → success=False, explicit error message
- UE5 not connected → success=False, ERR_UNREAL_NOT_CONNECTED
- Compile step fails (tool error, not compile error) → warning added, compile status unknown
- Metadata fetch failure → warning added, variable analysis degraded gracefully

---

## Example Agent Prompt

> "Audit the health of BP_HealthSystem and tell me its health score, any disconnected
> execution chains, and whether it compiles clean."

---

## Known Limitations (V5.0)

- Variable usage detection is heuristic (title matching); renames will miss references
- `include_inherited=True` for cpp_analyze_class is not yet implemented
- Function graph node analysis requires the function graph to already exist in UE5

## Tests

See `tests/test_audit_blueprint_health_skill.py`.

## Future Enhancements

- Detect unreachable nodes (islands not connected to any BeginPlay)
- Cross-Blueprint dependency analysis (are referenced Blueprints also healthy?)
- Incremental rescan (only re-audit changed graphs)
