# Phase 8 Readiness Workflow Report - 2026-05-17

## Purpose

Use Insanitii as the live project smoke target while Unreal-MCP-Ghost moves into Phase 8 production workflows and game templates.

## MCP Tool Added

- `insanitii_phase1_readiness_report`: high-level smoke workflow for Insanitii Phase 1 readiness.

## What It Checks

- Unreal bridge ping.
- The 7 expected placed `INS_` actors.
- The 5 placed `BP_TestInteractable` actors.
- Native parent-class lookup for `InsanitiiTestInteractable` when the active plugin supports it.
- Generated-class validity for the 8 core Blueprint wrappers.
- Enhanced Input mappings in `/Game/Input/IMC_Default`.
- Visible Unreal/Windows dialogs that could block automation.
- Manual PIE checklist still required for player possession and real input behavior.

## Live Result

Status: `warn`

The workflow passed all static readiness checks:

- Bridge ping returned `pong`.
- Found all 7 placed Insanitii actors.
- Found all 5 placed `BP_TestInteractable` actors.
- Verified 8 Blueprint wrappers have generated classes.
- Found 18 mappings in `/Game/Input/IMC_Default`.
- Confirmed all 6 Insanitii actions are mapped:
  - `IA_Focus`
  - `IA_Breathe`
  - `IA_Interact`
  - `IA_DebugDecreaseState`
  - `IA_DebugIncreaseState`
  - `IA_ToggleHUD`
- Found 0 visible blocking dialogs.

## Warning

The running editor still reports the new Phase 7 native smoke routes as unknown. The readiness workflow used read-only `exec_python` fallbacks for:

- actor identity lookup
- class-based actor lookup
- Blueprint generated-class checks
- Enhanced Input mapping inspection

This is acceptable for continuing read-only validation, but native class-chain matching for `InsanitiiTestInteractable` still needs Live Coding reload or editor restart.

## Prompt Handling

No blocking dialogs were visible during this pass. The approved automation policy remains:

1. Run `editor_list_blocking_dialogs()`.
2. Inspect title, text, and available buttons.
3. Use `editor_dismiss_blocking_dialog(button_text="...")` only when the desired button is explicit for the current operation.

## Remaining Phase 1 Gate

Static readiness is now confirmed. The remaining Phase 1 gate is manual PIE validation:

- WASD movement works.
- Mouse look works.
- F activates Focus and consumes charges.
- Tab triggers Breathe and observes cooldown.
- `-` and `=` adjust Mental State with visible feedback.
- E interacts with focused cubes and mutates Mental State.
- `~` toggles the HUD.
- Post-process feedback responds to Mental State.
- Consecutive failures increment cascade pressure.

After manual PIE validation, Insanitii can safely move into Phase 2 Lifestyle Framework implementation.
