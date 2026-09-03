# Phase 3 Ordinary Errand Task Expansion - 2026-06-02

## Goal

Expand the playable Day 1 slice beyond the original five station prototype so the player performs more ordinary-life tasks before the psychosis/stabilization beat.

The intended slice now covers:

1. Make a sandwich.
2. Take medication.
3. Buy groceries.
4. Do laundry.
5. Deliver a package.
6. Drive to work.
7. Complete email triage.
8. Endure overwhelming noise until psychosis triggers.
9. Stabilize and sleep into Day 2.

## Runtime Changes

- Added new `EInsanitiiTaskStationAction` values:
  - `Grocery`
  - `Laundry`
  - `PackageDelivery`
  - `Commute`
- Added a visible `UTextRenderComponent` label to task stations so placeholder stations read clearly in the level.
- Added `MoneyDelta` handling for errand stations:
  - groceries and laundry spend money and stabilize mental state;
  - package delivery earns money but increases pressure;
  - commute increases pressure without changing cash.
- Expanded `AInsanitiiSliceObjectiveDirector` to track and advance through the four new ordinary errands.
- Expanded HUD objective progress from six checks to ten checks and split the long progress summary over two compact lines.
- Updated `insanitii_phase3_objective_report` and `insanitii_phase3_pie_runtime_report` to expect the nine-station level and the nine scripted interactions.

## Level Placement

New actors placed in `/Game/FirstPerson/Lvl_FirstPerson`:

| Actor label | Action | Prompt | Cash effect | Mental-state effect | Location | Scale |
| --- | --- | --- | ---: | ---: | --- | --- |
| `INS_TaskStation_Grocery_Corner` | `GROCERY` | `Buy Groceries` | `-$32` | `+0.07` | `(420, 660, 120)` | `(0.75, 0.75, 0.42)` |
| `INS_TaskStation_Laundry_Washer` | `LAUNDRY` | `Do Laundry` | `-$12` | `+0.05` | `(420, 820, 120)` | `(0.70, 0.70, 0.50)` |
| `INS_TaskStation_Package_Dropoff` | `PACKAGE_DELIVERY` | `Deliver Package` | `+$35` | `-0.08` | `(420, -340, 120)` | `(0.55, 0.55, 0.35)` |
| `INS_TaskStation_Commute_Car` | `COMMUTE` | `Drive to Work` | `$0` | `-0.10` | `(420, -520, 110)` | `(1.45, 0.65, 0.28)` |

The level was saved through `LevelEditorSubsystem.save_current_level()`.

## Verification

- Closed Unreal Editor and rebuilt `InsanitiiEditor` with Unreal Build Tool.
- Result: build succeeded, including UnrealHeaderTool reflection for the new station enum values.
- `python -m py_compile unreal_mcp_server\tools\editor_tools.py`: passed.
- `python -m pytest unreal_mcp_server\tests\test_phase9_insanitii_pie_runtime_report.py`: passed.
- Live `insanitii_phase3_objective_report`:
  - status: `warn`;
  - station count: `9`;
  - warning was the dialog scanner counting the visible Unreal Editor window, not a gameplay failure.
- Live `insanitii_phase3_pie_runtime_report`:
  - status: `pass`;
  - `station_count`: `9`;
  - `exercise_step_count`: `9`;
  - `exercise_error_count`: `0`;
  - objective completion: `1.0`;
  - psychosis event: `HallucinationSurge`;
  - PIE stopped cleanly.

The scripted PIE pass validated the expanded economy beats:

- groceries reduced cash from `$250` to `$218`;
- laundry reduced cash from `$218` to `$206`;
- package delivery increased cash from `$206` to `$241`;
- work increased cash from `$241` to `$293`;
- sleep applied the daily living cost and advanced to `Day 2 07:00`.

## Tooling Note

A single large `exec_python` payload that attempted to load the level, spawn/configure all stations, and save the level hit the bridge's guarded native access-violation path and caused the editor session to exit.

Recovery workflow that succeeded:

1. Restart Unreal Editor.
2. Probe the bridge with a small read-only `exec_python`.
3. Spawn/configure one station per `exec_python` call through `EditorActorSubsystem`.
4. Save the level separately through `LevelEditorSubsystem.save_current_level()`.

Tool improvement added in this pass:

- `insanitii_place_ordinary_errand_stations`: loads `Lvl_FirstPerson`, places/updates the four errand stations through separate small `exec_python` chunks, then saves the level through a separate save chunk.

Keep using this split workflow for future Unreal MCP level-authoring passes.

## Remaining Work

- Replace placeholder cube stations with authored or generated assets.
- Use the signed-in Tripo workspace for stronger grocery/laundry/package/commute set dressing when the ChromeMCP asset pipeline is stable.
- Replace local placeholder audio with ElevenLabs downloadable audio once the signed-in Sound Effects UI exposes working playback/download.
- Run a human movement/manual input pass to judge route readability, station spacing, HUD readability, and moment-to-moment feel.
