# Phase 3 Manual Control Readiness - 2026-06-07

## Intent

Close the remaining gap between scripted runtime API checks and a player-controllable demo. Previous PIE reports proved the Day 1 loop through direct station calls, but the KB still carried stale manual-checklist risk around WASD movement and mouse look.

## Fix

- Added `Mouse2D` to `IA_Look` in `/Game/Input/IMC_Default`.
- Saved the input mapping context so the mouse-look fix persists across editor restarts.
- Added `insanitii_manual_control_readiness_report` to `unreal_mcp_server/tools/editor_tools.py`.
- Added `scripts/probe_insanitii_manual_control_readiness.py` as a repeatable repo wrapper.

## Report Coverage

The new report launches PIE and verifies:

- `BP_InsanitiiTemplatePlayerController_C` is present.
- `BP_FirstPersonCharacter_C` is possessed.
- The possessed pawn has `CharacterMovementComponent`.
- The player controller is not showing the mouse cursor during gameplay.
- The pawn has Insanitii mental-state and interaction detector components.
- `IA_Move` has W/A/S/D mappings.
- `IA_Look` has `Mouse2D` mapping.
- Insanitii mechanic inputs are mapped: Focus, Breathe, Interact, DebugDecrease, DebugIncrease, ToggleHUD.
- Movement input moves the pawn in PIE.
- Control rotation responds to a look probe.
- PIE stops cleanly.

## Verification

- `probe_insanitii_manual_control_readiness.py` passed:
  - Controller: `BP_InsanitiiTemplatePlayerController_C`
  - Pawn: `BP_FirstPersonCharacter_C`
  - Movement component: `CharacterMovementComponent`
  - Movement response: `155.82 cm`
  - Look response: `32.0 degrees`
  - Mouse cursor hidden
  - WASD/mechanic mappings present
  - Mouse look mapping present
- `insanitii_phase3_pie_runtime_report --wait-seconds 20` passed after the mapping fix.
- `probe_insanitii_tripo_station_readiness.py` passed.
- `report_insanitii_layout_positions.py` passed with `max_deviation: 0.0`.
- `pytest` passed for:
  - `unreal_mcp_server/tests/test_phase9_insanitii_pie_runtime_report.py`
  - `unreal_mcp_server/tests/test_phase13_insanitii_world_reactivity_report.py`
  - `unreal_mcp_server/tests/test_phase8_insanitii_readiness_report.py`

## Remaining Human Feel Check

This report proves control viability, not subjective feel. A human still needs to walk the full Day 1 route with normal input and judge comfort, interaction range, mouse sensitivity, audio mix, and psychosis VFX readability.
