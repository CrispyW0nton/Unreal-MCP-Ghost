# Phase 2B Save/Load Skeleton - 2026-06-02

## Goal

Add a real persistence skeleton for the playable Day 1 slice so the daily-loop state is not only a one-session runtime test.

This pass targets the Phase 2B roadmap requirement:

- save/load day and time;
- save/load cash and economy state;
- save/load current lifestyle, skill, and reputation;
- save/load mental-state baseline and counters;
- expose verification through MCP.

## Runtime Changes

Added native save data object:

- `UInsanitiiSaveGame`

Saved fields:

- save version;
- day and minute of day;
- cash balance;
- daily living cost;
- debt flag;
- economy ledger;
- current lifestyle;
- lifestyle skill;
- reputation;
- mental state;
- focus charges;
- breathe cooldown;
- psychosis cooldown;
- consecutive success/failure counters;
- total task completed/failed counters.

Added native manager actor:

- `AInsanitiiSaveGameManager`

Manager behavior:

- finds `INS_LifestyleManager`;
- finds the player mental-state component;
- saves to slot `Insanitii_Day1_Demo`;
- loads from slot `Insanitii_Day1_Demo`;
- restores time, economy, lifestyle, and mental-state fields;
- exposes `GetDebugSummary()` for HUD/MCP inspection.

Placed level actor:

- `INS_SaveGameManager`

## Player-Facing Debug Controls

Updated native HUD controls:

- `K`: save demo state;
- `L`: load demo state.

The debug HUD now includes the save manager summary line, including slot existence and last save/load status.

## Tooling Updates

Added `insanitii_save_load_report` to `unreal_mcp_server/tools/editor_tools.py`.

The report:

1. launches PIE;
2. calls `SaveDemoState`;
3. mutates day/time, cash, and mental state;
4. calls `LoadDemoState`;
5. verifies day, cash, and mental state match the saved baseline;
6. stops PIE cleanly.

The runtime probe was hardened after the first live attempt returned empty active-PIE output:

- removed `SystemExit` paths;
- added one final JSON print;
- added top-level exception capture;
- added pawn fallback from controller to `GameplayStatics.get_player_pawn`.

## Verification

- Closed Unreal Editor and built `InsanitiiEditor` with Unreal Build Tool.
  - Result: succeeded.
  - UHT generated reflection for save/load classes.
- Placed `INS_SaveGameManager` in `/Game/FirstPerson/Lvl_FirstPerson`.
  - Result: created and level saved.
- Live `insanitii_save_load_report`.
  - Result: `pass`.
  - Save succeeded: `true`.
  - Load succeeded: `true`.
  - Save exists: `true`.
  - Restored day: `true`.
  - Restored cash: `true`.
  - Restored mental state: `true`.
  - PIE stopped cleanly.
- Save file exists:
  - `C:\Users\NewAdmin\Documents\KaiGenInteractive\Insanitii\Insanitii\Saved\SaveGames\Insanitii_Day1_Demo.sav`
- Live `insanitii_phase3_pie_runtime_report`.
  - Result: `pass`.
  - 9 stations, 9 scripted interactions, objective completion `1.0`, world reactivity tracked count `40`, clean PIE stop.
- Live `insanitii_audio_feedback_report`.
  - Result: `pass`.
  - 5 audio assets and 5 assigned slots.
- Regression tests:
  - `test_phase9_insanitii_pie_runtime_report.py`
  - `test_phase10_insanitii_audio_feedback_report.py`
  - `test_phase13_insanitii_world_reactivity_report.py`
  - `test_phase14_insanitii_save_load_report.py`
  - `test_editor_take_screenshot_params.py`
  - Result: `5 passed`.

## Remaining Work

- Add main menu/pause menu save/load buttons for non-debug use.
- Add clear in-world/player-facing save feedback beyond the debug HUD.
- Decide whether objective progress should persist. This pass saves core daily-loop state, but not the objective-director booleans.
- Add content-warning/accessibility menus before demo packaging.
