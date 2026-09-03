# Insanitii Phase 1 Status

## Pre-Flight Status

Date: 2026-05-12

## 2026-05-14 Knowledge Deep Dive Update

Historical note: Blueprint-only architecture planning was formalized using repo guides and local book deep dives. As of 2026-05-18, this is superseded by the best-fit native C++ plus Blueprint-wrapper architecture decision in `Architecture_Decision_Best_Fit_2026-05-18.md`.

New planning docs:

- `Book_Deep_Dive_Blueprint_Synthesis.md`
- `Blueprint_Logic_Implementation_Plan.md`

These now define the recommended source-of-truth approach for:

- single-path Enhanced Input ownership,
- state-driven mechanics structure,
- interaction contract flow,
- debug verification requirements before advancing phases.

Phase 1 execution was requested for the open Unreal Engine 5.6 First Person Template project. Work resumed after the Unreal plugin was installed; the bridge is reachable on `127.0.0.1:55655`.

## Requested First Step

Connect to the open Unreal project through Unreal-MCP-Ghost and run the Phase 1 pre-flight checks:

1. Ping Unreal through MCP.
2. Confirm template level actors.
3. Locate `BP_FirstPersonCharacter`.
4. Capture `00_template_starting_state.png`.

## Blocker

Cursor currently reports the Unreal MCP server as unavailable:

- MCP descriptor status says the server errored.
- `CallMcpTool` reports that no MCP servers are available.
- The MCP descriptor folder does not currently expose tool schema JSON files, so tool calls cannot be safely issued.

The Unreal plugin bridge itself is reachable through the repository's UnrealMCP bridge CLI. Native runtime compilation now succeeds through Live Coding after C++ compile fixes.

The current blocker is editor reflection: the running editor cannot see the newly added `UCLASS` types until Unreal Editor restarts.

## Relevant Config Observation

The checked workspace MCP config files currently reference older or placeholder paths instead of this workspace's server path:

- `cursor_mcp_config.json` uses `C:\PATH\TO\unreal_mcp_server\unreal_mcp_server.py`.
- `cursor_setup/mcp.json` points at an `Academy of Art University` project path.

The current workspace server script is expected at:

`c:\Users\NewAdmin\Documents\GDeveloper\Workspaces\Unreal-MCP-Ghost\unreal_mcp_server\unreal_mcp_server.py`

## Phase 1 Completion State

```text
═══════════════════════════════════════════════════════════
INSANITII PHASE 1 - CORE MECHANICS FOUNDATION
STATUS REPORT
═══════════════════════════════════════════════════════════

COMPLETED SYSTEMS:
[✅] Project folder structure: 19 `/Game/Insanitii` folders created
[✅] BP_MentalStateComponent: native component and Blueprint wrapper compile
[⚠️] FirstPersonCharacter integration: mechanics input fix applied; retest manual Play mode
[✅] Enhanced/Input key handling (F, Tab, E, -, =, H)
[⚠️] M_PsychosisPostProcess material: placeholder created; native PP settings provide runtime feedback
[✅] BP_PostProcessController + placed in level
[⚠️] NS_VisualStatic Niagara system: placeholder asset created
[⚠️] BP_VFXController: deferred; native post-process controller covers Phase 1 visual feedback
[⚠️] WBP_DebugHUD widget: placeholder created; native HUD is functional
[✅] BPI_Interactable interface: placeholder BPI plus native interface
[✅] BP_InteractionDetector
[✅] BP_TestInteractable (5 placed)
[✅] Audio class structure
[✅] BP_InsanitiiGameMode
[⚠️] Data tables and curves: curve assets created; data table deferred pending struct automation
[⚠️] Playtest successful: PIE simulation validated runtime attachment/HUD; full input playtest pending manual Play mode

BLOCKED/ISSUES:
- Cursor MCP wrapper config files have been repaired, but Cursor must be restarted before the wrapper/tool schemas can be rechecked.
- Unreal bridge CLI works on port `55655`.
- Native C++ Live Coding build succeeds.
- Cursor MCP wrapper config repaired; restart Cursor to reload and verify tool schemas.
- Bridge CLI remains confirmed on port `55655`.
- Automated bridge play mode only exposed simulation PIE, not full possessed input play.
- DataTable and detailed material/Niagara graph generation remain tool-gap items.
- Manual PIE movement/look initially failed because the Insanitii controller replaced the template controller. Fixed by restoring `BP_FirstPersonPlayerController` and moving Insanitii key polling into `BP_RuntimeBootstrap`.
- Manual PIE still spawned the native Insanitii controller, so `BP_InsanitiiTemplatePlayerController` was created as a child of the stock template controller and assigned to `BP_InsanitiiGameMode`.
- Actual PIE now verifies controller `BP_InsanitiiTemplatePlayerController`, pawn `BP_FirstPersonCharacter`, HUD `InsanitiiHUD`.
- Follow-up manual PIE showed mechanics keys did not work. `BP_InsanitiiPlayerController` was updated to add the template input mapping contexts from `/Game/Input` and bind mechanics keys directly. Actual PIE now verifies `BP_InsanitiiPlayerController`, `BP_FirstPersonCharacter`, `InsanitiiHUD`, Mental State component, and Interaction Detector component.
- Manual testing then showed native `BP_InsanitiiPlayerController` still broke movement/look. Current setup uses `BP_InsanitiiTemplatePlayerController` for movement/look.
- Mechanics inputs were moved onto the proper Enhanced Input path: Insanitii `InputAction` assets are mapped in `/Game/Input/IMC_Default`, `BP_FirstPersonCharacter` now owns `InsanitiiMentalState` and `InsanitiiInteractionDetector` components, and `UInsanitiiMentalStateComponent` binds the actions from the pawn-owned `UEnhancedInputComponent`.
- Actual PIE needs manual retest for `H`, `F`, `Tab`, `E`, `-`, and `=` after the pawn-side Enhanced Input binding change. The HUD now reports `Input: Enhanced Bound` when the runtime bind succeeds.
- HUD toggle moved from `~` to `H` because tilde/backtick opens the Unreal console.
- Full audit found overlapping mechanics input systems still active in runtime code (`HUD`, `MechanicsInputComponent`, `RuntimeBootstrap`, native `PlayerController`, and component-level Enhanced Input). This must be collapsed to a single runtime input path.

NEXT PHASE READINESS:
- Partially ready. Core runtime foundation exists and level is staged; manual Play-in-Editor retest and Cursor restart/MCP wrapper verification are the next gates.

SCREENSHOTS CAPTURED:
- `phase1_00_baseline.png`
- `phase1_17_test1_hud.png`
- `phase1_17_final_editor_state.png`

PHASE 1 PARTIAL: CORE RUNTIME STAGED, MANUAL PLAYTEST PENDING.
═══════════════════════════════════════════════════════════
```
