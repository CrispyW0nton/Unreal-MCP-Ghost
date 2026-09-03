# Phase 3 Psychosis Event Coverage Telemetry - 2026-06-07

## Intent

The playable slice needs psychosis events that are not only randomly reachable, but independently verifiable as distinct gameplay beats: being chased, hallucinating presences, and seeing the world reorganize around the player. This pass made those event families easier to force, inspect, and regression-test while preserving the locked wide play-area layout and Tripo station mesh ownership.

The design direction remains aligned with the existing *A Beautiful Mind* experience study: psychosis should feel like misplaced certainty and false salience inside ordinary tasks, not only a generic horror filter. The current event families map cleanly to that:

- **Chase**: an approaching presence that reads as urgent and must be interpreted under pressure.
- **Hallucination Surge**: imagined presences that invite reality testing.
- **World Shift**: ordinary task stations displaced and scaled into a temporarily unreliable world.

## Runtime Changes

- Added transient debug telemetry to `AInsanitiiPsychosisEventDirector`:
  - `LastStartedEventType`
  - `ChaseEventsStarted`
  - `HallucinationSurgeEventsStarted`
  - `WorldShiftEventsStarted`
- Extended `GetDebugSummary()` so reports now include the last event and C/H/W event counts.
- Added `GetEventCoverageDebugSummary()` for compact automation-friendly coverage reporting.
- Added explicit debug helpers:
  - `StartChaseEventForDebug()`
  - `StartHallucinationSurgeForDebug()` already existed and remains covered.
  - `StartWorldShiftForDebug()`
- Marked the new telemetry fields `Transient` so editor probes do not accidentally persist debug counters into the level package.

## Tooling

Added:

- `scripts/probe_insanitii_psychosis_event_variety.py`

The probe forces all three event types and verifies:

- Chase spawns one real, targeted approaching presence with the threat prompt.
- Hallucination Surge spawns five imagined, tagged, reality-testable presences.
- World Shift moves all 11 task stations by a visible amount and restores them exactly afterward.
- Coverage telemetry increases for Chase, Hallucination Surge, and World Shift.
- Cleanup returns the director to no active event, zero hallucinations, and zero shifted actors.

## Verification

Passed:

- `python -m py_compile scripts\probe_insanitii_psychosis_event_variety.py`
- `powershell -ExecutionPolicy Bypass -File scripts\run_insanitii_clean_build_and_tripo_verify.ps1`
- `python scripts\bridge_ping.py`
- `python scripts\probe_insanitii_psychosis_event_variety.py`
- `python scripts\probe_insanitii_tripo_station_readiness.py`
- `python scripts\report_insanitii_layout_positions.py`
- `python scripts\probe_insanitii_hallucinated_presence.py`
- `python scripts\run_insanitii_report.py insanitii_phase3_pie_runtime_report --wait-seconds 20`
- `python -m pytest -q unreal_mcp_server\tests\test_phase9_insanitii_pie_runtime_report.py unreal_mcp_server\tests\test_phase13_insanitii_world_reactivity_report.py`

Results of note:

- Psychosis event variety probe ended with `Chase 1 | HallucinationSurge 1 | WorldShift 1`.
- World Shift reported `shifted=11`, `during_station_max_delta=269.26`, and `after_station_max_delta=0.0`.
- Tripo station readiness still reports all 11 task stations directly own Tripo meshes with no standalone or non-station Tripo mesh actors.
- Layout verification still reports `max_deviation: 0.0`.
- Phase 3 PIE runtime report passes with no warnings or failures.

Known unrelated warning:

- `bridge_ping.py` still reports the existing `BP_BlackHole` introspection warning.
