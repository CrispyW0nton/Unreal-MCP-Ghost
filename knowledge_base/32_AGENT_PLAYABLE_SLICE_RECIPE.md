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

When those gates pass, the skill submits four Tripo `text_to_model` tasks and
returns task IDs plus next steps. It does not pretend that asynchronous
generation, import, Blueprint wiring, PIE, or report packaging have completed.
Agents must continue through `gen_tripo_wait_for_task`,
`gen_tripo_import_to_project`, Blueprint/AI/UMG tools, PIE evidence, and
`skill_package_vertical_slice_report`.

Example:

```python
skill_generate_playable_slice(
    brief="third-person dungeon demo with a slime, a skeleton, and a boss",
    mode="plan",
)

skill_generate_playable_slice(
    brief="third-person dungeon demo with a slime, a skeleton, and a boss",
    mode="submit_assets",
    session_name="dungeon-demo",
    confirm_spend=True,
)
```

## D8 Exact Playable-Slice Runbook

This is the canonical D.8 prompt-and-tool recipe for the headline demo. Use it
as the first pass before adding project-specific flourish.

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
6. For each returned task id, `gen_tripo_wait_for_task(task_id, timeout_s=900,
   poll_s=10)`.
7. For each completed model, `gen_tripo_import_to_project(task_id,
   content_path="/Game/Generated/PlayableSlice/<role>",
   create_material_instance=True, create_blueprint=False)`.
8. Create or reuse a third-person player Blueprint, assign the hero mesh when
   suitable, and keep input/camera defaults readable.
9. Create enemy Blueprint shells, one Behavior Tree, and one Blackboard with
   keys for target actor, patrol point, chase range, and attack range.
10. Place the entrance, encounter space, boss trigger, generated props, enemy,
    player start, lights, nav bounds, and blocking volumes.
11. Add a compact UMG HUD with objective text, player health, and boss-room
    trigger feedback.
12. Compile and save every touched Blueprint/material/map asset, then run
    import validation and changed-asset scans.
13. Launch PIE, run or simulate 60 seconds, capture log output and a viewport
    screenshot.
14. Finish with `skill_package_vertical_slice_report`, including changed assets,
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
