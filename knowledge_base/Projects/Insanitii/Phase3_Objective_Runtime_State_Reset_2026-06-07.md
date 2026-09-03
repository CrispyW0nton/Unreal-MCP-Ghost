# Phase 3 Objective Runtime State Reset - 2026-06-07

## Intent

The Day 1 playable slice should always begin from an honest fresh objective state: food/meds/grocery/laundry/package/commute/work/stress/psychosis/sleep should all start incomplete, and `Psychosis OK` should only appear after the player survives an active psychosis event.

During automation, editor-world probes can force and end psychosis events before the scripted Day 1 station loop. That made later report samples confusing because the loop could appear to start with psychosis already complete. This pass prevents saved/editor probe contamination from leaking into the playable start state and makes the runtime report show a clean Day 1 loop after preflight checks.

## Runtime Changes

Updated `AInsanitiiSliceObjectiveDirector`:

- Marked runtime objective state as `Transient`:
  - `CurrentStep`
  - `bAteFood`
  - `bTookMedication`
  - `bBoughtGroceries`
  - `bDidLaundry`
  - `bDeliveredPackage`
  - `bCommutedToWork`
  - `bCompletedWork`
  - `bFacedStress`
  - `bSurvivedPsychosis`
  - `bSlept`
- Added `bResetProgressOnBeginPlay`, defaulting to `true`.
- Added `ResetSliceProgressForDebug()`.
- `BeginPlay()` now resets runtime objective progress before rebinding actors and advancing the objective.

## Tooling

Added:

- `scripts/probe_insanitii_objective_fresh_start.py`

The probe launches PIE and verifies:

- Fresh progress starts as `Food -- ... Psychosis -- | Sleep --`.
- Fresh objective text is `Make a sandwich before the day starts.`
- Fresh completion is `0.0`.
- A forced survived psychosis event changes only the psychosis flag to `Psychosis OK` and raises completion to `0.1`.

Updated:

- `unreal_mcp_server/tools/editor_tools.py`
- `unreal_mcp_server/tests/test_phase9_insanitii_pie_runtime_report.py`

The Phase 3 PIE runtime report now resets objective progress after preflight anchor/stabilization samples and before the ordered station loop. It records `fresh_start_after_preflight`, which verifies the scripted Day 1 loop begins with `Psychosis --` and completion `0.0`.

## Verification

Passed:

- `python -m py_compile scripts\probe_insanitii_objective_fresh_start.py`
- `powershell -ExecutionPolicy Bypass -File scripts\run_insanitii_clean_build_and_tripo_verify.ps1`
- `python scripts\bridge_ping.py`
- `python scripts\probe_insanitii_objective_fresh_start.py`
- `python scripts\probe_insanitii_psychosis_event_visual_signatures.py`
- `python scripts\probe_insanitii_psychosis_event_variety.py`
- `python scripts\probe_insanitii_tripo_station_readiness.py`
- `python scripts\report_insanitii_layout_positions.py`
- `python -m py_compile unreal_mcp_server\tools\editor_tools.py unreal_mcp_server\tests\test_phase9_insanitii_pie_runtime_report.py scripts\probe_insanitii_objective_fresh_start.py`
- `python -m pytest -q unreal_mcp_server\tests\test_phase9_insanitii_pie_runtime_report.py unreal_mcp_server\tests\test_phase13_insanitii_world_reactivity_report.py`
- `python scripts\run_insanitii_report.py insanitii_phase3_pie_runtime_report --wait-seconds 20`

Results of note:

- Fresh-start probe initial progress: `Food -- | Meds -- | Grocery -- | Laundry -- | Package -- | Commute -- | Work -- | Stress -- | Psychosis -- | Sleep --`.
- Fresh-start probe initial completion: `0.0`.
- After forced survived psychosis: `Psychosis OK`, completion `0.1`.
- The full Phase 3 runtime report now shows the ordered station loop beginning with `Psychosis --` and completion `0.0` after preflight checks.
- The full Day 1 loop still reaches objective completion `1.0`.
- Tripo station readiness still reports no standalone/non-station Tripo blockers.
- Layout verification still reports `max_deviation: 0.0`.

Known unrelated warnings:

- `bridge_ping.py` still reports the existing `BP_BlackHole` introspection warning.
- `pytest` still reports the existing cache-provider warning for `.pytest_cache`.
