# skill_repair_broken_blueprint

**Phase 4 / V6 — Deterministic Repair Skill**

## Purpose

Repair a broken Blueprint by fixing only the deterministic, provably-safe
subset of issues.  The skill never guesses at connections or adds nodes; it
only acts on issues flagged `auto_repairable: true` by the diagnostic tools.

## Workflow

```
1. bp_get_compile_diagnostics   → detect compile errors
2. bp_validate_blueprint        → aggregate health score + issues
3. Build repair plan            → list of auto_repairable issues
4. For each issue (deterministic only):
     ORPHANED_NODE              → bp_remove_orphaned_nodes
     DISCONNECTED_EXEC_PIN      → bp_repair_exec_chain (if both ends known)
     SET_PIN_DEFAULT            → bp_set_pin_default
5. Recompile                    → compile_blueprint
6. bp_run_post_mutation_verify  → re-validate all changed graphs
7. Report before/after JSON
```

## Deterministic issues (auto-repaired)

| Code                  | Action                              |
|-----------------------|-------------------------------------|
| ORPHANED_NODE         | Remove node (no connections at all) |
| DISCONNECTED_EXEC_PIN | Reconnect exec chain if both ends known |
| SET_PIN_DEFAULT       | Set typed default (bool/int/float)  |

## Non-deterministic issues (skipped, reported)

| Code                  | Reason skipped                          |
|-----------------------|-----------------------------------------|
| BP_COMPILE_ERROR      | Requires human inspection               |
| BP_NOT_FOUND          | Path error — agent cannot fix           |
| POSSIBLY_UNUSED_VAR   | May be intentionally exposed on spawn   |
| GRAPH_NOT_FOUND       | Human must create or rename the graph   |

## Output schema

```json
{
  "success": true,
  "outputs": {
    "before": {
      "health_score": 60,
      "error_count": 2,
      "warning_count": 3,
      "compile_clean": false
    },
    "after": {
      "health_score": 85,
      "error_count": 0,
      "warning_count": 2,
      "compile_clean": true
    },
    "repairs_applied": [
      {"action": "remove_orphaned_node", "target": "PrintString_0", ...}
    ],
    "repairs_skipped": [
      {"action": "fix_compile_error", "target": "...", "skip_reason": "not auto-repairable"}
    ],
    "health_delta": 25,
    "safe_to_continue": true,
    "repair_summary": "Applied 1 repair(s); health improved from 60 to 85"
  }
}
```
