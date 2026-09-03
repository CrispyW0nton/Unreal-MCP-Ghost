# Phase 3: Tripo Station Mesh Blocker Repair

Date: 2026-06-03

## Problem

The separate Tripo Smart Mesh set-dressing actors were visually useful, but some were blocking the actual `INS_TaskStation_*` interactables. This made the scene look better while making the gameplay worse.

The better structure is for each interactable station to own the appropriate Tripo mesh directly through its existing `AInsanitiiTaskStation::MeshComponent`. That keeps collision, focus outline, prompts, sounds, task use, and objective targeting on the same actor.

## Change

Added helper:

`scripts/apply_insanitii_tripo_station_meshes.py`

The helper maps Tripo StaticMesh assets onto the task-station mesh components:

- `INS_TaskStation_Food_Sandwich` -> home kitchen/medication/bed Tripo mesh
- `INS_TaskStation_Medication` -> home kitchen/medication/bed Tripo mesh
- `INS_TaskStation_Sleep_Bed` -> home kitchen/medication/bed Tripo mesh
- `INS_TaskStation_Grocery_Corner` -> grocery checkout/shelves Tripo mesh
- `INS_TaskStation_Laundry_Washer` -> washer/dryer Tripo mesh
- `INS_TaskStation_Package_Dropoff` -> delivery/dropoff Tripo mesh
- `INS_TaskStation_Commute_Car` -> sedan Tripo mesh
- `INS_TaskStation_Work_EmailTriage` -> work desk Tripo mesh
- `INS_TaskStation_Stress_OverwhelmingNoise` -> stress/noise cluster Tripo mesh
- `INS_TaskStation_Grounding_Card` -> grounding table Tripo mesh
- `INS_TaskStation_Grounding_Snack` -> grounding table Tripo mesh

The helper also disables/removes standalone `INS_Tripo_*` actors so they no longer sit in front of interactables.

## Verification

The successful run assigned all 11 task stations, saved the level, and saved dirty packages.

Independent reports after the pass and after an editor quit/relaunch persistence check:

- `report_insanitii_layout_positions.py`: passed with `max_deviation: 0.0`; the wide Day 1 layout stayed locked.
- `report_insanitii_tripo_assets.py`: passed; all reported Tripo meshes are now on `InsanitiiTaskStation` actors, not separate `INS_Tripo_*` blocker actors.
- `probe_insanitii_station_audio.py`: passed; all 11 task stations still expose station audio fields and fallback generated SoundWaves still exist.
- `probe_insanitii_tripo_station_readiness.py`: passed; all 11 task stations report `interactable: true`, non-empty prompts, `CollisionEnabled.QUERY_AND_PHYSICS`, direct `/Game/TripoModels/` meshes, and no standalone `INS_Tripo_*` actors remain.

The post-relaunch bridge ping reported 124 actors in the level, down from the previous 132 actor count, consistent with the eight standalone Tripo blocker actors being removed. The restarted editor still reported all 11 task stations with Tripo meshes attached directly.

Runtime PIE interaction validation was attempted with `run_insanitii_task_friction_probe.py`, but that PIE probe timed out and left PIE active. A later split-call PIE probe also timed out around the play-state transition and the editor then shut down cleanly through normal `QUIT_EDITOR` handling. The unsafe split-call helper was removed.

Current verified replacement for this specific blocker is the non-PIE station readiness probe:

```powershell
python scripts\bridge_ping.py
python scripts\probe_insanitii_tripo_station_readiness.py
```

This proves the saved editor-level station setup is correct. A full human PIE/manual pass is still useful for player movement feel and line-of-sight ergonomics, but the Tripo actors no longer exist as separate blockers.

## Notes

The first version of the helper hit an Unreal Python enum mismatch on `CollisionResponse.BLOCK`; that call was removed because native `AInsanitiiTaskStation` already configures blocking collision in its constructor.

This repair is aligned with the playable-slice goal: the generated meshes now support interaction instead of obstructing it.

## Revalidation: 2026-06-03

The station mesh assignment was re-run after the user flagged the correct direction again: the Tripo meshes should be the interactables' base meshes, not separate blocking props.

The live editor pass reported:

- 11 task stations assigned to direct `/Game/TripoModels/` StaticMesh assets.
- `saved_current_level: true` and `saved_dirty_packages: true`.
- No standalone `INS_Tripo_*` actors left to remove.
- `probe_insanitii_tripo_station_readiness.py`: passed after save; every station is interactable, has a prompt, uses a Tripo mesh, and has `CollisionEnabled.QUERY_AND_PHYSICS`.
- `report_insanitii_layout_positions.py`: passed with `max_deviation: 0.0`.
- `probe_insanitii_station_audio.py`: passed, so the mesh repair did not disturb task-station sound wiring.
- `report_insanitii_tripo_assets.py`: confirmed LOD0 triangle counts remain in the smart-mesh target range, from 735 to 2,284 triangles across the imported Tripo assets.

## Revalidation: 2026-06-04

The station mesh assignment was re-run after the user reported that Tripo meshes were still blocking some interactables.

The live editor pass reported:

- 11 task stations assigned to direct `/Game/TripoModels/` StaticMesh assets.
- `saved_current_level: true` and `saved_dirty_packages: true`.
- No standalone `INS_Tripo_*` actors left to remove or disable.
- `probe_insanitii_tripo_station_readiness.py`: passed; every station is an `InsanitiiTaskStation`, remains interactable, has a non-empty prompt, uses a direct Tripo mesh, and has `CollisionEnabled.QUERY_AND_PHYSICS`.
- `report_insanitii_layout_positions.py`: passed with `max_deviation: 0.0`, preserving the locked wide layout.
- `probe_insanitii_station_audio.py`: passed, so task-station audio fallback wiring was not disturbed.
- `report_insanitii_tripo_assets.py`: confirmed the Tripo meshes are reported only on task-station actors, with LOD0 triangle counts still in the current smart-mesh range of 735 to 2,284 triangles.

## Revalidation: 2026-06-07

The station mesh assignment was re-run after the user again called out that Tripo meshes should be the interactables' base meshes, not separate blocking props.

The live editor pass reported:

- 11 task stations assigned to direct `/Game/TripoModels/` StaticMesh assets through each `AInsanitiiTaskStation::MeshComponent`.
- `saved_current_level: true` and `saved_dirty_packages: true`.
- No standalone `INS_Tripo_*` actors and no non-station actors using `/Game/TripoModels/` meshes remain in the level.
- `probe_insanitii_tripo_station_readiness.py`: passed; every station is an `InsanitiiTaskStation`, remains interactable, has a non-empty prompt, uses a direct Tripo mesh, and has `CollisionEnabled.QUERY_AND_PHYSICS`.
- `report_insanitii_layout_positions.py`: passed with `max_deviation: 0.0`, preserving the locked wide layout.

This keeps the generated Smart Mesh art on the gameplay actor that owns prompt focus, task completion, audio feedback, visual feedback, and objective targeting.

## Player-Facing PIE Interaction Revalidation: 2026-06-07

The saved level now has runtime proof that the Tripo-backed stations are usable from the possessed first-person pawn, not only correctly assigned in editor state.

Additional implementation:

- `AInsanitiiTaskStation` now owns a hidden `StationFocusTrace` box attached to the station mesh. It is visibility-query only, hidden in game, ignores physical collision, and gives imported Tripo meshes a stable interaction target.
- `UInsanitiiInteractionDetectorComponent` now traces from the possessed controller/player viewpoint before falling back to camera or actor-forward traces.
- The detector also has a bounded view-cone fallback for nearby interactables when imported mesh collision or a small non-interactable blocker prevents an exact visibility hit.

Verification:

- `probe_insanitii_player_station_interaction_route.py`: passed.
- `route_count`: 11
- `focus_success_count`: 11
- `prompt_success_count`: 11
- `interaction_success_count`: 11
- `tripo_success_count`: 11
- `probe_insanitii_tripo_station_readiness.py`: passed.
- `report_insanitii_layout_positions.py`: passed with `max_deviation: 0.0`.
- `probe_insanitii_station_audio.py`: passed.
- `probe_insanitii_manual_control_readiness.py`: passed.
- `run_insanitii_report.py insanitii_phase3_pie_runtime_report --wait-seconds 20`: passed.

This confirms the Tripo meshes remain the interactables' base meshes while the player can still focus, see prompts, and complete every ordinary task station in PIE.
