# Agent Playable Slice Recipe
> Source: project notes, Unreal-MCP-Ghost roadmap, execution-journal workflow
> Last Updated: 2026-06-07 | UE 5.6

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
