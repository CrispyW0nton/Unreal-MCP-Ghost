# Phase 3 Day 1 Set Dressing - 2026-06-02

## Goal

Improve the playable Day 1 slice from a functional row of prototype task cubes into a more readable route with visible place identity for each ordinary-life beat.

This pass keeps the same verified gameplay loop, but adds environmental anchors so a player can visually parse:

- home,
- grocery,
- laundry,
- package delivery,
- commute,
- work,
- overwhelming noise/stress.

## Level Work

Added 40 labeled prototype set-dressing actors to `/Game/FirstPerson/Lvl_FirstPerson`:

- 26 static-mesh props/floors:
  - route floor pads,
  - kitchen counter,
  - medicine shelf,
  - bed backdrop,
  - grocery shelves and checkout,
  - laundry washers,
  - package door frame and boxes,
  - commute road/lane strips,
  - work desk/monitor,
  - stress speakers and pulse orb.
- 7 zone text signs:
  - `HOME`,
  - `GROCERY`,
  - `LAUNDRY`,
  - `DELIVERY`,
  - `COMMUTE`,
  - `WORK`,
  - `NOISE`.
- 7 colored point lights, one per zone, to make the Day 1 route more readable and give each task area a distinct mood.

Screenshot saved for this pass:

![Day 1 set dressing](C:/Users/NewAdmin/Documents/GDeveloper/Workspaces/Unreal-MCP-Ghost/knowledge_base/Projects/Insanitii/Day1_Set_Dressing_2026-06-02.png)

Note: the screenshot is an editor viewport capture, so visible text-actor billboards/icons are editor overlays. A follow-up gameplay-view capture should be taken during manual PIE review.

## Tooling Added

Added `insanitii_place_day1_set_dressing` to `unreal_mcp_server/tools/editor_tools.py`.

The tool follows the safe level-authoring pattern from the errand station pass:

1. Optionally load `/Game/FirstPerson/Lvl_FirstPerson`.
2. Place/update one set-dressing actor per small `exec_python` chunk.
3. Save the level through a separate `LevelEditorSubsystem.save_current_level()` chunk.

Also fixed the `take_screenshot` MCP wrapper so its public `filename` argument is forwarded to the native bridge as `filepath`. The native route expects `filepath`; this mismatch was discovered while saving the set-dressing screenshot.

## Verification

- Live `insanitii_place_day1_set_dressing`:
  - status: `pass`;
  - placement count: `40`;
  - static mesh count: `26`;
  - text count: `7`;
  - light count: `7`;
  - level save: `true`.
- Live `insanitii_phase3_pie_runtime_report` after set dressing:
  - status: `pass`;
  - station count: `9`;
  - exercise steps: `9`;
  - objective completion: `1.0`;
  - no warnings/failures;
  - PIE stopped cleanly.
- `python -m py_compile unreal_mcp_server\tools\editor_tools.py`: passed.
- `python -m pytest unreal_mcp_server\tests\test_phase9_insanitii_pie_runtime_report.py unreal_mcp_server\tests\test_phase10_insanitii_audio_feedback_report.py unreal_mcp_server\tests\test_phase11_insanitii_errand_station_placement.py unreal_mcp_server\tests\test_phase12_insanitii_day1_set_dressing.py unreal_mcp_server\tests\test_editor_take_screenshot_params.py`: passed.

## Remaining Work

- Take a manual possessed-PIE gameplay screenshot/video with editor billboards hidden.
- Tune set-dressing placement for player movement sightlines and collision feel.
- Replace prototype geometry with authored or generated assets once Tripo/ChromeMCP asset export is stable.
- Add material/color pass for the static meshes; this pass intentionally used engine primitives and lights to avoid adding brittle material-asset creation during live editor automation.
