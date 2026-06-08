# Agent Playable Slice Recipe
> Source: project notes, Unreal-MCP-Ghost roadmap, execution-journal workflow
> Last Updated: 2026-06-08 | UE 5.6

---

## Overview

An agent-playable slice is a small, end-to-end game experience that an AI agent
can discover, build or modify, verify, and explain with evidence. It is not a
loose collection of assets. It has player input, world context, at least one
interactive loop, feedback, failure handling, save/compile discipline, and
runtime proof.

This recipe is the default shape for larger MCP work. Build the narrowest
complete loop first, then expand.

## Key Classes

| Class or Asset | Role |
| --- | --- |
| GameMode / GameState | Defines rules, start state, and replicated match state if needed. |
| PlayerController | Input bridge and player-specific UI ownership. |
| Pawn/Character | The playable body and camera/movement core. |
| Actor Components | Reusable gameplay capabilities such as interaction or inventory. |
| Widget Blueprint | HUD, prompts, result screens, and feedback surfaces. |
| Data Assets/Tables | Tunable content for tasks, items, dialogue, or encounters. |
| Execution journal | Evidence trail for decisions, mutations, and verification. |

## Common Pitfalls

- Building many assets before one input-to-feedback loop works.
- Forgetting compile/save/diagnostic passes after Blueprint edits.
- Treating screenshots as proof without logs, graph readbacks, or asset scans.
- Adding UI text that explains tooling instead of in-world player feedback.
- Leaving debug/test actors in the final map.
- Declaring success without PIE evidence.

## MCP Tool Mapping

| Task | Preferred MCP direction |
| --- | --- |
| Discover current project | `get_project_context`, `scan_project_assets`, `list_available_tools` |
| Plan generated slice | `skill_generate_playable_slice(mode="plan")` |
| Start paid asset generation | `skill_generate_playable_slice(mode="submit_assets", confirm_spend=True)` |
| Package execution runbook | `skill_generate_playable_slice(mode="orchestrate")` |
| Plan risk | `risk_evaluate_action` and a short execution journal |
| Build gameplay | Blueprint, gameplay, data, UMG, AI, animation, material, and actor tools |
| Verify editor state | compile/save/diagnostic tools and asset scans |
| Verify runtime | `pie_launch_session`, `pie_capture_log`, `viewport_capture_screenshot` |
| Package evidence | `execution_journal_finish`, `skill_package_vertical_slice_report` |

## D7 Playable Slice Skill

`skill_generate_playable_slice(brief)` is the D.7 high-order entry point for
the headline generative demo. It converts a one-sentence brief into a validated
`unreal_mcp_playable_slice_plan.v1` plan using
`knowledge_base/v5/PLAYABLE_SLICE_SCHEMA.json`.

All modes also accept optional `asset_roles`, `gameplay_loop`,
`acceptance_criteria`, and `required_evidence`. The Unreal Playable Slice UI
passes these fields through so asset prompts, the level goal, validation, and
the final report match the user's stated intent instead of relying on the brief
alone.

Mode `plan` is offline and safe. It returns:

- one hero asset, two prop assets, and one enemy asset planned for Tripo
  `text_to_model`;
- player, enemy AI, level, HUD, validation, and report targets;
- the ordered tool phases for context, generation, import, Blueprint work, AI,
  level placement, HUD, PIE evidence, and report packaging.

Mode `submit_assets` is the first paid execution gate. It requires:

- `TRIPO_API_KEY` from the environment or `Saved/MCPChat/secrets.json`;
- enough remaining session credit budget;
- `confirm_spend=True` after user approval.

When those gates pass, the skill submits four Tripo `text_to_model` tasks with
`smart_low_poly=True` and returns task IDs plus next steps. It does not pretend
that asynchronous generation, import, Blueprint wiring, PIE, or report
packaging have completed. Agents must continue through
`gen_tripo_wait_for_task`, `gen_tripo_import_to_project`, Blueprint/AI/UMG
tools, PIE evidence, and `skill_package_vertical_slice_report`.

Mode `orchestrate` is the no-spend backend runbook for the full AI IDE flow. It
returns `unreal_mcp_playable_slice_orchestration.v1` with context discovery,
wait/import, Blueprint/UMG/AI/level assembly, PIE verification, and final report
phases. Pass optional `task_submissions_json` and `imported_assets_json` arrays
when generation or import has already happened so the runbook can bind task ids
and asset paths to the planned roles. Its final report call uses the real
`skill_package_vertical_slice_report` argument shape: `title`, `summary`,
`journal_path`, `report_dir`, `project_name`, `artifacts`, and `verification`.
The orchestration also starts and finishes an execution journal with
`execution_journal_start` and `execution_journal_finish`, so the final report can
include the same evidence trail used during autonomous work.

`orchestrate` also returns an `evidence_readiness` ledger. The ledger provides
evidence readiness as the machine-readable answer to whether the slice is merely
ready to execute or actually proven live. It remains
`live_playable_slice_proven=false` until all proof gates are satisfied: Tripo
task ids, credit record, imported generated asset paths, gameplay asset paths,
clean compile reports, PIE log/duration, viewport screenshot, and packaged
vertical-slice report. After a live run, pass `execution_evidence_json` with
completed artifacts such as `credit_guard`, `gameplay_assets`,
`compile_reports`, `pie_log_path`, `pie_duration_s`,
`viewport_screenshot_path`, and `vertical_slice_report_path` to make the
readiness verdict explicit instead of relying on a loose checklist.

Example:

```python
skill_generate_playable_slice(
    brief="third-person dungeon demo with a slime, a skeleton, and a boss",
    mode="plan",
    asset_roles="hero, key pickup, boss",
    gameplay_loop="collect the key, open the boss gate, win",
)

skill_generate_playable_slice(
    brief="third-person dungeon demo with a slime, a skeleton, and a boss",
    mode="submit_assets",
    session_name="dungeon-demo",
    confirm_spend=True,
)

skill_generate_playable_slice(
    brief="third-person dungeon demo with a slime, a skeleton, and a boss",
    mode="orchestrate",
    session_name="dungeon-demo",
    task_submissions_json="[ ... task records from submit_assets ... ]",
    imported_assets_json="[ ... import records from gen_tripo_import_to_project ... ]",
    execution_evidence_json="{ ... compile, PIE, screenshot, and report evidence ... }",
)
```

## D8 Exact Playable-Slice Runbook

This is the canonical D.8 prompt-and-tool recipe for the headline demo. Use it
as the first pass before adding project-specific flourish.

## Chat Dock Playable Slice Builder

The MCP Chat dock now has a **Playable Slice** quick action for the headline
one-brief-to-game workflow. It sits between Generate Asset and Build Gameplay:
Generate Asset handles single Tripo jobs, Build Gameplay handles mechanic/UI/AI
work, and Playable Slice stitches both into a guided vertical-slice workflow
inside Unreal.

The dialog captures:

- a one-sentence playable game brief;
- generated asset roles for Smart Mesh Tripo assets;
- the intended gameplay loop;
- acceptance criteria and required evidence.

The inserted workflow prompt should:

1. Call `skill_generate_playable_slice(mode="plan")` with the brief, asset
   roles, gameplay loop, acceptance criteria, and required evidence, then use
   the returned `unreal_mcp_playable_slice_plan.v1` as the source of truth.
2. Discover project state with `get_project_context`,
   `scan_project_assets(path="/Game", depth=3)`, `list_available_tools`, and
   onboarding context for Blueprints, world building, and UMG.
3. Map every generated asset role to a concrete `/Game/Generated/PlayableSlice`
   path and avoid destructive overwrites.
4. Use `skill_generate_playable_slice(mode="submit_assets")` after spend
   approval, or `gen_tripo_text_to_model` directly for missing 3D roles with
   textures, PBR, `face_limit=12000`, and `smart_low_poly=true`.
5. Use `skill_generate_playable_slice(mode="orchestrate")` to package the
   wait/import, gameplay assembly, PIE, and report phases, then import with
   `gen_tripo_wait_for_task` and `gen_tripo_import_to_project`. Treat the
   first `evidence_readiness` result as a missing-proof ledger, not a pass.
6. Optionally route hero-art refinements through the Texture/Paint Magic Brush
   path when project/render/image-map data exists and spend is approved.
7. Build the playable loop with Blueprint, actor, component, UMG, AI, level,
   lighting, collision, and placement tools.
8. Run `compile_blueprint_and_report`, save/read back touched assets, and verify
   runtime with PIE, `pie_capture_log`, and a viewport screenshot.
9. Finish with `skill_package_vertical_slice_report`, then call
   `skill_generate_playable_slice(mode="orchestrate")` again with
   `task_submissions_json`, `imported_assets_json`, and `execution_evidence_json`
   so `evidence_readiness.live_playable_slice_proven` records whether the live
   run is truly proven. The Chat Dock tool card surfaces this proof status and
   incomplete gates in its inline Evidence area.
10. Report changed assets, Tripo task ids, credit usage, evidence paths,
    incomplete evidence gates, unresolved warnings, and remaining human
    design-review work.

## Chat Dock Gameplay Builder

The MCP Chat dock now has a **Build Gameplay** quick action for development
work that is not primarily asset generation. It turns the chat box into a
guided AI development surface for Mechanic, AI, HUD, and Level Flow requests.
Use it when a non-programmer wants to direct gameplay systems from inside
Unreal without knowing individual tool names.

The inserted workflow prompt should:

1. Discover project state with `get_project_context`,
   `scan_project_assets(path="/Game", depth=2)`, `list_available_tools`, and
   `get_onboarding_context`.
2. Build the smallest playable change using the relevant tool domains:
   Blueprint/gameplay tools for mechanics, `ai_tools` for behavior,
   UMG/widget tools for HUD, and editor/procedural tools for level flow.
3. Run `compile_blueprint_and_report` for touched Blueprints, save changed
   assets, and verify the graph/widget/readback state.
4. Run PIE evidence with `pie_launch_session`, `pie_capture_log`,
   `viewport_capture_screenshot`, and `pie_stop_session` when possible.
5. Report changed asset paths, warnings/errors, evidence paths, and remaining
   human design-review decisions.

### Exact Prompts

Primary user prompt:

```text
Build me a third-person dungeon-crawler demo with three enemy types and a boss
room. The player should be able to move, see a compact objective HUD, encounter
one patrol enemy, and reach a boss-room trigger. Generate only the minimum
assets needed for a playable UE5.6 vertical slice.
```

Smaller smoke prompt:

```text
Build me a third-person dungeon demo with a slime, a skeleton, and a boss. Keep
the map to one entrance room, one encounter room, and one boss alcove.
```

Asset art-direction suffix:

```text
Stylized readable fantasy, clean silhouette, game-ready proportions, centered
pivot, no embedded text, PBR material support, suitable for a compact UE5.6
third-person prototype.
```

### Expected Tool Sequence

1. `get_server_info()` and `get_onboarding_context("generative")` to load the
   current KB/tool map.
2. `get_project_context()` and `scan_project_assets("/Game", depth=2)` to avoid
   overwriting existing project conventions.
3. `skill_generate_playable_slice(brief, mode="plan")` to produce and validate
   the `unreal_mcp_playable_slice_plan.v1` plan.
4. User-facing spend checkpoint: explain planned Tripo asset count, estimated
   credits, output folder, and that paid calls require `TRIPO_API_KEY`.
5. `skill_generate_playable_slice(brief, mode="submit_assets",
   session_name="<slice-name>", confirm_spend=True)` only after approval.
6. `skill_generate_playable_slice(brief, mode="orchestrate",
   task_submissions_json="<returned task records>")` to package the concrete
   import, gameplay, verification, and report phases.
7. For each returned task id, `gen_tripo_wait_for_task(task_id, timeout_s=900,
   poll_s=10)`.
8. For each completed model, `gen_tripo_import_to_project(task_id,
   content_path="/Game/Generated/PlayableSlice/<role>",
   create_material_instance=True, create_blueprint=False)`.
9. Create or reuse a third-person player Blueprint, assign the hero mesh when
   suitable, and keep input/camera defaults readable.
10. Create enemy Blueprint shells, one Behavior Tree, and one Blackboard with
   keys for target actor, patrol point, chase range, and attack range.
11. Place the entrance, encounter space, boss trigger, generated props, enemy,
    player start, lights, nav bounds, and blocking volumes.
12. Add a compact UMG HUD with objective text, player health, and boss-room
    trigger feedback.
13. Compile and save every touched Blueprint/material/map asset, then run
    import validation and changed-asset scans.
14. Launch PIE, run or simulate 60 seconds, capture log output and a viewport
    screenshot.
15. Finish with `skill_package_vertical_slice_report`, including changed assets,
    task ids, screenshots, PIE logs, warnings, and follow-ups.

### Expected Runtime

| Slice size | Expected runtime | Practical target |
| --- | ---: | --- |
| Plan-only | < 10 s | No network, no API key, no spend. |
| Asset submission only | 10-60 s | Requires API key and confirmed spend. |
| Four generated assets, parallel wait | 5-20 min | Depends on Tripo queue and output size. |
| Import and material pass | 2-8 min | Depends on mesh complexity and Interchange. |
| Blueprint/AI/HUD assembly | 5-15 min | Faster when project templates already exist. |
| Evidence/report pass | 2-5 min | PIE, logs, screenshot, report packaging. |

The full directive target remains under 30 minutes for a fresh UE5.6 project.
If Tripo queue time exceeds that, record the queue delay separately instead of
calling the Unreal-side automation slow.

### Known Failure Modes

| Failure | What the agent sees | Required response |
| --- | --- | --- |
| No `TRIPO_API_KEY` | `auth_required` from submit mode | Stop paid execution and ask for a key/config update; keep the plan result. |
| User has not approved credits | `spend_confirmation_required` | Explain estimated spend and rerun only after `confirm_spend=True`. |
| Generation task stalls | Wait times out before final status | Keep task ids, report partial state, and continue only with completed assets or a smaller retry. |
| Generated mesh is unsuitable | Bad silhouette, scale, holes, or material slots | Import into a review folder, mark warning, and swap to primitive/blockout stand-ins for PIE. |
| AI cannot navigate | Enemy stands still or BT fails movement | Verify nav bounds, capsule radius, movement component, Blackboard keys, and BT task names. |
| HUD exists but does not update | Widget displays stale objective/health | Check PlayerController ownership and binding source; prefer explicit event updates. |
| Blueprint compile fails | Compile report returns errors | Run repair tools or simplify the graph before PIE; do not package the report as green. |
| PIE logs runtime errors | 60-second run is not clean | Capture log tail, fix blocking issues, rerun, and include residual warnings. |

### Minimum Green Report

The final vertical-slice report is green only when it includes all of these:

- the original brief and validated plan id/schema;
- Tripo task ids, asset prompts, and credit-confirmation state;
- imported `/Game/Generated/PlayableSlice/...` asset paths;
- player, enemy AI, level, HUD, and validation asset paths;
- compile/save result for touched assets;
- PIE log evidence for at least 60 seconds or a clearly marked shorter smoke;
- screenshot evidence from the playable level;
- warnings and follow-ups for generated asset quality, licensing, or polish.

## Working Example

Goal: build a one-room interaction slice.

1. Discover the project: active map, player pawn, input mappings, existing UI,
   dirty packages, and relevant Content folders.
2. Start an execution journal with the task name and risk notes.
3. Create or reuse an interactable Actor with an interaction component.
4. Add one prompt widget and one result widget.
5. Bind input to trace/interact from the player.
6. On interaction, update a small objective state and play visible/audio
   feedback.
7. Compile and save the touched Blueprints/assets.
8. Launch PIE, simulate or manually perform the interaction, capture logs and a
   screenshot.
9. Finish the journal with pass/warn/fail status and follow-ups.

## Validation Checklist

- The slice starts from current project context, not assumptions.
- Every touched Blueprint compiles and is saved.
- Player input reaches gameplay state and visible/audio feedback.
- Runtime proof includes PIE logs and visual evidence.
- The final report lists changed assets, verification evidence, and remaining
  risks.

## References

- Repo: `13_TOOL_EXPANSION_ROADMAP.md`
- Repo: `12_MCP_TOOL_USAGE_GUIDE.md`
- Repo: `18_PACKAGING_AND_OPTIMIZATION.md`
