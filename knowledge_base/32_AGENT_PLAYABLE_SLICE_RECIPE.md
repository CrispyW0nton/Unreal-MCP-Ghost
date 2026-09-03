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
| Start IDE companion session | `skill_compile_ide_companion_session` |
| Update IDE companion status | `skill_compile_ide_companion_status` |
| Generate IDE companion work order | `skill_compile_ide_companion_work_order` |
| Record IDE companion evidence | `skill_record_ide_companion_evidence` |
| Resume IDE companion session | `skill_resume_ide_companion_session` |
| Show IDE companion dashboard | `skill_compile_ide_companion_dashboard` |
| Resolve IDE companion blockers | `skill_compile_ide_companion_blocker_resolution` |
| Compile placeholder asset manifest | `skill_compile_ide_companion_placeholder_manifest` |
| Compile generated asset lifecycle | `skill_compile_ide_companion_asset_lifecycle_manifest` |
| Plan generated slice | `skill_generate_playable_slice(mode="plan")` |
| Plan one gameplay mechanic | `skill_plan_gameplay_mechanic` |
| Start paid asset generation | `skill_generate_playable_slice(mode="submit_assets", confirm_spend=True)` |
| Plan risk | `risk_evaluate_action` and a short execution journal |
| Build gameplay | Blueprint, gameplay, data, UMG, AI, animation, material, and actor tools |
| Verify editor state | compile/save/diagnostic tools and asset scans |
| Verify runtime | `pie_launch_session`, `pie_capture_log`, `viewport_capture_screenshot` |
| Package evidence | `execution_journal_finish`, `skill_package_vertical_slice_report` |

## D12 IDE Companion Session Orchestrator

`skill_compile_ide_companion_session` is the top-level no-spend planning tool
for the "ultimate companion" workflow. It turns a project brief plus an optional
mechanic brief into one ordered session plan that an in-editor chat agent can
execute incrementally.

The returned `unreal_mcp_ide_companion_session_plan.v1` report includes:

- readiness request parameters for `gen_compile_ide_companion_readiness`;
- generated Smart Mesh asset prompts and estimated Tripo credits;
- an embedded `unreal_mcp_gameplay_mechanic_plan.v1` mechanic plan;
- phases for project orientation, readiness, mechanic design, asset generation,
  editor implementation, runtime verification, and developer handoff;
- gates for API key, API wallet, Unreal bridge, spend approval, Blueprint
  compile, PIE evidence, and final report proof;
- fallback paths for zero wallet credits, offline bridge, Blueprint failures,
  and runtime verification failures.

Use it as the first command when the user asks for broad game-development help
rather than one isolated tool call:

```python
skill_compile_ide_companion_session(
    project_brief="single-developer playable slice with generated assets",
    mechanic_brief="enemy AI patrol that chases the player and updates an objective HUD",
    include_generated_assets=True,
)
```

The plan itself does not call Tripo, mutate Unreal, or spend credits. Execute
the readiness phase first, then stop on `outputs.blocking_gates` if the API
wallet, bridge, or spend-approval gates are not ready.

## D13 IDE Companion Status Receipt

`skill_compile_ide_companion_status` is the companion's progress receipt. Feed it
the latest `unreal_mcp_ide_companion_session_plan.v1` plan plus optional
readiness output, completed phase names, evidence artifacts, and manual blockers.
It does not call the network, mutate Unreal, or spend credits.

The returned `unreal_mcp_ide_companion_status.v1` receipt includes:

- current phase states: completed, available, blocked, or waiting;
- blocking readiness gates and manual blockers;
- readiness flags for paid generation, editor mutation, and runtime
  verification;
- missing evidence for phases claimed complete without artifacts;
- the next safe MCP action for the in-editor companion.

Use it after each meaningful phase so the chat agent can act like an IDE status
bar with memory, rather than a one-shot prompt:

```python
skill_compile_ide_companion_status(
    session_plan=plan,
    readiness_report=readiness,
    completed_phases=["orient_to_project"],
    evidence={"orient_to_project": {"complete": True, "artifacts": ["project context"]}},
)
```

If `blocking_gates` is non-empty, resolve those gates before submitting paid
Tripo work or mutating Unreal assets.

## D14 IDE Companion Work Order

`skill_compile_ide_companion_work_order` turns a session plan plus optional
status/readiness context into the next executable phase order. It is still
offline and safe: it does not call Tripo, mutate Unreal, or spend credits.

The returned `unreal_mcp_ide_companion_work_order.v1` report includes:

- the selected target phase and current phase state;
- prerequisites, readiness blockers, and hard stop conditions;
- concrete MCP tool steps for the phase, including generated-asset task
  arguments when the target is asset generation;
- evidence to collect and acceptance criteria before the phase can be marked
  complete;
- the required `skill_compile_ide_companion_status` refresh after completion or
  early stop.

Use it when the companion has a plan and status but needs a concrete work ticket
for the next IDE action:

```python
skill_compile_ide_companion_work_order(
    session_plan=plan,
    companion_status=status,
)
```

If `safe_to_execute_now` is false, follow the prerequisites and stop conditions
instead of running the listed tool steps.

## D15 IDE Companion Evidence Ledger

`skill_record_ide_companion_evidence` gives the companion durable memory for a
session. It writes phase evidence to
`.mcp_artifacts/ide_companion_sessions/<session>.json`, refreshes the
`unreal_mcp_ide_companion_status.v1` receipt from the recorded evidence, and
returns the ledger path.

The returned `unreal_mcp_ide_companion_evidence_record.v1` receipt includes:

- the ledger path and full ledger payload;
- the recorded phase event, summary, artifacts, and evidence type;
- an updated status receipt with completed phases, blockers, missing evidence,
  and the next safe action;
- no network, editor mutation, or spend requirements.

Use it after every phase completion or early stop:

```python
skill_record_ide_companion_evidence(
    session_plan=plan,
    phase_name="orient_to_project",
    evidence_type="context",
    summary="Project context and required KB guidance loaded.",
    artifacts=["kb://32_AGENT_PLAYABLE_SLICE_RECIPE.md"],
)
```

The ledger is local evidence for the developer and should be treated as a
resume point for the in-editor companion, not as proof by itself. Runtime,
compile, asset, and screenshot evidence still need their own artifacts.

## D16 IDE Companion Session Resume

`skill_resume_ide_companion_session` loads a local companion ledger by session
name or explicit path, rebuilds status from recorded evidence, compiles the next
work order, and returns a compact `unreal_mcp_ide_companion_resume.v1` packet.
It is a no-spend, no-editor-mutation resume point for the in-editor companion.

The resume packet includes:

- the ledger path and event count;
- completed phases derived from ledger evidence;
- refreshed `unreal_mcp_ide_companion_status.v1`;
- next `unreal_mcp_ide_companion_work_order.v1`;
- the next safe action and any blocking gates.

Use it when returning to a prior session:

```python
skill_resume_ide_companion_session(
    session_name="ide-companion",
)
```

If the latest readiness report changed, pass it in so resume output reflects the
current wallet/bridge gates instead of the last recorded state.

## D17 IDE Companion Dashboard

`skill_compile_ide_companion_dashboard` compiles the companion's IDE-facing
state into display-ready cards. It can read an existing ledger or accept a
session plan before any evidence has been recorded. It does not call Tripo,
mutate Unreal, or spend credits.

The returned `unreal_mcp_ide_companion_dashboard.v1` packet includes:

- readiness, progress, next-work, generated-asset, gameplay-mechanic, and
  evidence cards;
- embedded status and work-order payloads;
- primary action, blocking gates, ledger path, generated asset count, and
  mechanic hooks;
- the command-palette actions that form the companion loop.

Use it as the editor/chat summary view:

```python
skill_compile_ide_companion_dashboard(
    session_name="ide-companion",
)
```

When no ledger exists yet, pass `session_plan=plan` so the dashboard can show
the first-run state.

## D18 IDE Companion Blocker Resolution

`skill_compile_ide_companion_blocker_resolution` turns blocking gates into
explicit choices. It is the companion's answer to "what can I do now?" when the
API wallet is empty, spend approval is missing, or the Unreal bridge is offline.
It does not call Tripo, mutate Unreal, or spend credits.

The returned `unreal_mcp_ide_companion_blocker_resolution.v1` packet includes:

- blockers and severity;
- unblock actions with evidence requirements;
- fallback actions such as continuing with placeholders or offline mechanic
  planning;
- placeholder policy for zero-wallet or no-spend work;
- bridge-offline policy for no-editor-mutation work;
- next actions for recording the decision and refreshing the dashboard.

Use it whenever the dashboard or status receipt reports blocking gates:

```python
skill_compile_ide_companion_blocker_resolution(
    session_plan=plan,
    companion_status=status,
    preferred_strategy="continue_with_placeholders",
)
```

For `api_wallet_has_credits`, the recommended safe fallback is to keep generated
asset prompts in the ledger, use placeholder assets for gameplay proof, and
record the decision as evidence. For `unreal_bridge_reachable`, continue with
offline plans only until `scripts/bridge_ping.py` succeeds.

## D19 IDE Companion Placeholder Manifest

`skill_compile_ide_companion_placeholder_manifest` turns planned generated
assets into a no-spend placeholder manifest. It is the concrete follow-up to the
`continue_with_placeholders` blocker strategy: gameplay work can proceed with
readable proxy assets while Tripo generation is blocked by wallet, spend, or
bridge gates.

The returned `unreal_mcp_ide_companion_placeholder_manifest.v1` packet includes:

- placeholder asset names, roles, shapes, labels, and target paths;
- replacement mapping back to future Tripo prompts and import paths;
- tool steps for folder/material/Blueprint/component/compile passes;
- evidence requirements for placeholder proof;
- replacement policy for swapping generated assets in later without losing
  evidence.

Use it after resolving blockers with a placeholder strategy:

```python
skill_compile_ide_companion_placeholder_manifest(
    session_plan=plan,
)
```

This tool does not call Tripo or mutate Unreal. When the bridge is available,
execute its tool steps incrementally, compile every placeholder Blueprint, and
record the placeholder decision in the evidence ledger.

## D34 IDE Companion Generated Asset Lifecycle Manifest

`skill_compile_ide_companion_asset_lifecycle_manifest` turns planned generated
asset prompts into a provider-neutral lifecycle manifest. It is the bridge
between placeholder-first gameplay proof and later generated-asset replacement:
the agent can track prompts, spend gates, provider tasks, imports, quality
checks, viewport proof, and ledger evidence before any paid request is sent.

The returned `unreal_mcp_ide_companion_generated_asset_lifecycle.v1` packet
includes:

- one lifecycle record per planned generated asset;
- provider task contracts for submission, status wait, download, and import;
- explicit `public_mcp_tool_available`, `planned_submit_tool`, and
  `unsupported_reason` fields when a provider-neutral task type is planned but
  no executable MCP submit tool is registered yet;
- explicit credit/wallet and `confirm_spend=True` gates;
- placeholder replacement mapping when a D19 manifest is provided;
- quality gates for import paths, mesh load, material slots, collision
  readability, viewport proof, and ledger evidence;
- a generated-asset quality proof contract naming required after-import mesh
  load/readback, material slot, collision/readability, viewport/thumbnail, and
  ledger evidence;
- a generated-animation quality proof contract naming required after-import
  Animation Sequence readback, target skeleton or retarget evidence,
  AnimGraph/state-machine reference proof, PIE/viewport playback proof, and
  ledger evidence;
- fallback and stop-condition rules for blocked provider or import work.

Use it after a session plan exists, optionally with the placeholder manifest:

```python
skill_compile_ide_companion_asset_lifecycle_manifest(
    session_plan=plan,
    placeholder_manifest=placeholder_manifest,
    preferred_provider="tripo",
    write_manifest=True,
    manifest_name="asset_lifecycle",
)
```

This tool does not call Tripo, mutate Unreal, or spend credits. It only makes
the future generated-asset lifecycle explicit so MCP Chat can show asset status,
replacement readiness, and missing proof without relying on raw provider logs.
When `write_manifest=True`, it writes a local
`.mcp_artifacts/ide_companion_sessions/<session>_asset_lifecycle.json` artifact
that the cockpit overview can read later.

D133 keeps provider-neutral planning honest for Uthana. `text_to_motion` maps
to the registered `gen_uthana_text_to_motion` tool and `video_to_motion` maps
to `gen_uthana_video_to_motion` plus the async `gen_uthana_get_job` poller,
while planned task types such as `retarget_motion` are marked
`unsupported_task_type` until their public MCP submit tools exist. The manifest
and MCP Chat lifecycle summary carry the planned tool name and unsupported
reason, but the workflow should not suggest executing a missing tool.
For video-to-motion, include a local `video_file`, `reference_video_file`, or
`source_video_file` in the animation prompt before attempting upload; the
cockpit blocks as `attach_uthana_video_reference` when that clip evidence is
missing.

D134 surfaces that same signal in the existing MCP Chat Generated Assets card:
generated animation count, pending animation count, unsupported provider task
count, and a bounded preview of planned-but-missing submit tools. Use the card
and warning to decide whether to implement a provider wrapper, switch the
animation prompt back to a supported task type, or continue with placeholder /
marketplace animation proof.

## D35 MCP Chat Generated Asset Lifecycle Visibility

The MCP Chat cockpit reads saved
`unreal_mcp_ide_companion_generated_asset_lifecycle.v1` artifacts from the IDE
companion session directory and summarizes them as generated-asset state.

The read-only `unreal_mcp_chat_cockpit_overview.v1` packet now includes:

- `generated_asset_lifecycles`, a bounded list of matching lifecycle manifests;
- a `generated_assets` card with manifest count, planned asset count, pending
  provider task count, placeholder mapping count, preferred provider, and next
  manifest path;
- preview asset rows with name, role, provider, task status, expected import
  path, and placeholder availability.

This cockpit visibility does not execute queued editor work, call providers, or
spend credits. It is a status surface for deciding whether to continue with
placeholders, request wallet/spend approval, wait for provider tasks, import
results, or record ledger evidence.

## D116 MCP Chat Generated Animation Evidence Routing

The MCP Chat cockpit now treats generated animation evidence as a first-class
workflow target. When a saved lifecycle manifest contains Uthana
`animation_assets`, the overview can surface:

- `compile_generated_animation_evidence`, routed to
  `gen_compile_generated_animation_evidence`;
- `record_generated_animation_evidence`, routed to
  `skill_record_ide_companion_evidence`;
- structured generated-animation evidence context with provider, task status,
  motion id, expected import path, target skeleton, quality proof counts, and
  missing stage preview.

Use the compile action to build a no-spend receipt from captured provider,
download, import, retarget/readback, AnimGraph, PIE, ledger, and approval proof.
Use the record action to append the current generated-animation evidence row to
the companion ledger after the proof is ready or to document why it is not ready
yet. These cockpit routes remain read-only until the chosen tool is invoked; the
overview itself does not call Uthana, download files, import animations, run PIE,
mutate Unreal, or write evidence.

D.117 extends the native MCP Chat panel so those routes are visible from the
existing compact workflow surfaces. The `Actions` launcher includes command
palette prompts for both generated-animation evidence actions, and the native
`Next:` line can summarize the selected motion, provider, target skeleton,
proof counts, missing stages, and artifact count. This keeps Uthana evidence
guidance discoverable in-editor without adding another permanent HUD row.

D147 also threads generated-animation lifecycle gates into queue and execution
review. `queue_editor_actions.target_queue_context`, `next_safe_step`,
`execution_review`, and `execute_next_safe_step.target_execution_review_context`
can carry the selected Uthana target, target skeleton, task status, proof
contract, missing stages, next safe action, and animation gate policy. Use those
fields before queued animation import, retarget, AnimGraph, state-machine, or
gameplay replacement work so execution does not outrun generated-animation
proof.

## D20 IDE Companion Editor Action Queue

`skill_compile_ide_companion_editor_queue` turns a placeholder manifest or work
order into a durable editor-action queue. It is the bridge-offline companion to
D19: the agent can preserve exactly what should be created in Unreal without
pretending the editor mutation happened.

The returned `unreal_mcp_ide_companion_editor_queue.v1` packet includes:

- queue path under `.mcp_artifacts/ide_companion_sessions/`;
- bridge state, blocking gates, and prerequisites;
- concrete editor actions such as folder/material/Blueprint/component/compile
  steps;
- evidence requirements and stop conditions;
- after-execution tools for ledger recording and dashboard refresh.

Use it when `unreal_bridge_reachable` is blocked or when editor work should be
reviewed before execution:

```python
skill_compile_ide_companion_editor_queue(
    session_plan=plan,
    companion_status=status,
    placeholder_manifest=manifest,
)
```

This tool writes only a local JSON queue. It does not call Tripo and does not
send commands to Unreal. Before executing queued actions, rerun readiness or
`scripts/bridge_ping.py`, refresh `skill_compile_ide_companion_status`, then run
the queued editor actions one at a time and record evidence for the
`editor_implementation` phase.

## D21 Chat Cockpit Session Picker

`chat_list_sessions`, `chat_get_session_resume_context`, and the
`/chat/session/resume-context` HTTP route expose saved MCP Chat sessions and
nearby IDE companion ledgers to agents and the editor chat surface. They are
local read-only surfaces: they do not call Tripo, mutate Unreal, or spend
credits.

Use `chat_list_sessions` to populate a compact session picker:

```python
chat_list_sessions()
```

The result includes saved chat sessions, the last active session, and summaries
for `.mcp_artifacts/ide_companion_sessions/*.json` ledgers when present.

Use `chat_get_session_resume_context` when the developer chooses a session:

```python
chat_get_session_resume_context(session="ide-companion")
```

The result includes recent chat messages, a matching IDE companion ledger
summary, and suggested follow-up tools such as
`skill_resume_ide_companion_session` and
`skill_compile_ide_companion_dashboard`. If no ledger matches the selected chat
session, the tool returns a warning instead of inventing progress.

The editor chat panel can request the same packet over HTTP:

```text
GET /chat/session/resume-context?session=ide-companion&limit=20
```

The response is suitable for a compact resume card: selected chat session,
recent messages, matching ledger summary, suggested actions, and warnings when
no ledger exists.

## D120 Native Platform Stability Workflow Summaries

The native MCP Chat panel keeps platform-stability review inside the existing
workflow surfaces. The Platform Preflight and WIP Promotion actions summarize
build-wrapper status, build health, missing wrapper references, last plugin
build state, dirty-state risk, bridge/chat readiness, test-lane state, and
wrapper coverage without adding another permanent HUD row.

Use `review_platform_preflight_gate` before risky local work when the preflight
reports `build_wrapper_references_ready` as blocked. Use
`review_wip_promotion_gate` before moving WIP toward main so stale build logs
cannot hide unresolved local `.uproject` or `Build.bat` paths.

## D22 Chat Cockpit Overview

`chat_get_cockpit_overview` and the `/chat/cockpit/overview` HTTP route expose a
display-ready overview packet for the MCP Chat cockpit. They combine saved chat
sessions, recent messages, the matching IDE companion ledger, queued editor
actions, blocker gates, cards, and suggested actions. The surface is read-only:
it does not call Tripo, mutate Unreal, or spend credits.

Use the tool when MCP Chat needs a single packet for the session dashboard:

```python
chat_get_cockpit_overview(session="ide-companion")
```

The result includes the `unreal_mcp_chat_cockpit_overview.v1` schema, selected
session, session list, resume context, editor queue summaries, display cards,
blocking gates, and warnings when queued editor actions are blocked by bridge or
readiness gates. Queue actions are presented as disabled until
`can_execute_now` is true.

The editor chat panel can request the same packet over HTTP:

```text
GET /chat/cockpit/overview?session=ide-companion&limit=20
```

Use this packet as the top-level cockpit state before offering execution
buttons. If any queue reports `unreal_bridge_reachable` or another blocking
gate, keep editor mutation disabled and route the developer toward readiness,
blocker resolution, or evidence recording instead.

The MCP Chat panel also renders a compact IDE Cockpit strip backed by this
route. The strip should remain a read-only status surface: session, blockers,
queue state, queued-action preview, evidence summary, and next suggested action.
It is not an execution button for queued editor actions. Use the refresh control
to update state after recording evidence, changing sessions, or restarting the
MCP chat server.

Each queue summary includes at most five `preview_actions` entries with action
id, tool, optional label, and argument-key names. Each matching ledger also
contributes at most five `evidence_timeline` entries with phase, evidence type,
summary, artifact count, bounded `artifact_preview`, and timestamp. Treat these
entries as review surfaces only. Before execution, rerun readiness, confirm
`can_execute_now`, and record evidence after each editor mutation.

## D27 Chat Cockpit Ledger Detail

`chat_get_cockpit_ledger_detail` and the `/chat/cockpit/ledger` HTTP route expose
a bounded, read-only detail packet for the selected IDE companion ledger. Use it
when the cockpit needs artifact drilldown for a ledger event without loading or
displaying raw JSON.

```python
chat_get_cockpit_ledger_detail(session="ide-companion", event_index=2)
```

The returned `unreal_mcp_chat_ledger_detail.v1` packet includes:

- the ledger path, event count, returned event count, latest status, and latest
  work order;
- a phase index with event counts and latest event indexes;
- bounded event details with phase, evidence type, summary, timestamp, artifact
  count, artifact overflow count, and artifact items;
- artifact item kinds such as `knowledge_base`, `unreal_asset`, `uri`, `path`,
  and `note`;
- no network, editor, or spend requirements.

The editor chat panel can request the same detail over HTTP:

```text
GET /chat/cockpit/ledger?session=ide-companion&event_index=2&artifact_limit=12
```

Treat the packet as a review and navigation surface. It helps developers inspect
which artifacts back a phase, but it does not prove a Blueprint compile, PIE run,
viewport screenshot, or asset import by itself. Continue to use readiness gates,
editor readback, runtime checks, and `skill_record_ide_companion_evidence` for
the actual proof loop.

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

Mode `assemble` is the execution bridge after generated assets exist. It
accepts either:

- `task_ids`: four completed Tripo task ids in plan asset order; the skill
  imports those successful task outputs before assembly; or
- `imported_asset_paths`: four already imported `/Game/...` generated assets.

It then creates the player, enemy, AI Controller, Blackboard, Behavior Tree,
HUD widget, nav bounds, level placement, viewport screenshot, PIE smoke, and
vertical-slice report chain. The generated hero and enemy StaticMeshes are
assigned to visible StaticMesh components on the player and enemy Blueprints.
Native Blueprint and Widget routes currently write to their default
`/Game/Blueprints` and `/Game/Widgets` locations, so agents should read the
returned `created_artifacts` paths instead of assuming the requested
`content_path` was used for those asset classes. If any required step fails, the
skill stops at that stage and returns the completed steps plus raw bridge
evidence.

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

skill_generate_playable_slice(
    brief="third-person dungeon demo with a slime, a skeleton, and a boss",
    mode="assemble",
    imported_asset_paths=[
        "/Game/Generated/PlayableSlice/Assets/SM_Hero",
        "/Game/Generated/PlayableSlice/Assets/SM_Prop1",
        "/Game/Generated/PlayableSlice/Assets/SM_Prop2",
        "/Game/Generated/PlayableSlice/Assets/SM_Enemy",
    ],
    run_pie_seconds=60,
)
```

## D11 Gameplay Mechanic Planner

`skill_plan_gameplay_mechanic` is the planning companion for a single mechanic,
such as an interaction loop, cooldown ability, AI encounter, combat loop, or
inventory/resource system. It is offline and safe: it does not mutate Unreal,
does not call Tripo, and does not spend credits.

The returned `unreal_mcp_gameplay_mechanic_plan.v1` report includes:

- the detected mechanic kind and design intent;
- a `unreal_mcp_gameplay_feature_template.v1` packet for the selected feature
  workflow;
- optional Tripo-ready generated asset prompts with Smart Mesh policy;
- Blueprint/component assets, variables, and function/event surfaces;
- input, AI, damage, HUD, save-game, and replication hooks;
- an ordered MCP tool sequence for context, assets, Blueprint scaffold, logic,
  feedback, runtime verification, and evidence packaging;
- validation gates that require compile reports, graph readback, PIE/log, and
  viewport evidence before the mechanic is called complete.

Use this before editing gameplay when the user describes a mechanic rather than
a whole vertical slice:

```python
skill_plan_gameplay_mechanic(
    brief="player dash ability with cooldown and HUD feedback",
    include_generated_assets=True,
)
```

If generated assets are needed, first run
`gen_compile_ide_companion_readiness` and only submit Tripo tasks after the
user confirms spend and the API wallet/session budget gates are ready.

## D36 Gameplay Feature Template Packets

`skill_plan_gameplay_mechanic` now embeds a
`unreal_mcp_gameplay_feature_template.v1` packet so the plan can act like an
executable feature template instead of a generic suggestion list.

The template packet covers the common solo-developer loops from the Ultimate AI
Unreal IDE roadmap:

- interactable objective;
- pickup/resource loop;
- enemy patrol/chase/attack;
- objective HUD update;
- save/load state;
- input cooldown ability;
- replicated combat sample;
- AI patrol objective asset-swap vertical slice;
- performance optimization pass;
- bug-fix repair pass.

Each selected template includes:

- asset list covering Blueprint and generated-or-placeholder assets;
- Blueprint/C++/data ownership split;
- graph and component operations to perform after bridge readiness;
- `editor_operation_checklist` rows with operation ids, operation types,
  candidate MCP tools, bridge requirements, compile/readback requirements, and
  ledger evidence type;
- per-operation `unreal_mcp_gameplay_feature_operation_proof.v1` contracts that
  name required preconditions, after-operation evidence, and stop-if-missing
  rules before a queued editor action can be treated as proven;
- compile/readback checks;
- a `unreal_mcp_gameplay_feature_runtime_proof.v1` contract that names the
  runtime evidence required for the selected template, including AI
  Blackboard/BT/nav/capsule proof or replicated combat authority proof when
  those domains apply;
- PIE validation steps;
- repair instructions for compile, component, graph, and runtime-proof failures;
- a `unreal_mcp_gameplay_feature_completion_contract.v1` definition of done
  with required evidence, proof gates, and stop-before-complete conditions;
- evidence requirements and stop conditions.

Use the template as the shape for the next work order. Do not execute its graph
or component operations until `scripts/bridge_ping.py` succeeds, then compile
and read back every structural edit before continuing.

D149 adds `performance_optimization_pass` for briefs about optimization,
profiling, hitches, frame time, or FPS. Treat it as an evidence-backed pass:
capture baseline context/readback, apply exactly one scoped optimization
candidate, compile and read back the changed asset, then capture matching
before/after PIE log, viewport, and timing evidence before recording success.

D150 adds `bug_fix_repair_pass` for briefs about bugs, broken behavior, crashes,
compile/runtime errors, failures, or regressions. Treat it as a repair workflow:
capture the target asset and failure context, reproduce or document non-repro
evidence before mutating, apply exactly one scoped fix, compile and read back
the changed asset, run PIE/log/viewport verification, then record regression
guard evidence in the IDE companion ledger. Repair passes intentionally do not
schedule generated-asset work unless a separate asset-lifecycle request is made.

D151 threads Uthana animation planning into the gameplay mechanic plan itself.
AI, composite AI/objective, combat, ability, and animation-explicit briefs can
now return `generated_animation_prompts`, an `animation` system hook, estimated
motion seconds, and generated-animation placeholder rows in the feature-template
asset list. Treat those prompts as lifecycle manifest inputs, not as proof:
motion generation still requires Uthana auth, allowance/usage confirmation,
download/import, target skeleton or retarget readback, AnimGraph or state
machine reference proof, PIE/viewport playback evidence, and ledger recording.

D152 surfaces those mechanic-level generated-animation prompts in MCP Chat's
existing work-order and gameplay-template review paths. Review Gameplay Template
now carries prompt counts, provider/skeleton previews, Uthana tool hints,
animation proof requirements, estimated motion seconds, and a no-bypass policy
before queueing editor actions. This remains read-only: the cockpit review does
not call Uthana, download files, import animations, retarget, edit AnimGraphs,
run PIE, write ledger evidence, or add a permanent HUD panel.

D163 Runtime proof contracts add domain-specific evidence to gameplay feature templates. AI patrol/chase
templates now require BT Blackboard assignment, Blackboard key readback,
nav-agent or navmesh setup evidence, enemy capsule/movement readback, PIE AI
state or log proof, screenshot proof, and ledger evidence. Replicated combat
templates now require replication description, server-authority damage policy
readback, replicated health/death state readback, common-mistake validation,
single-player damage proof, and either two-player PIE proof or an explicit
deferred-networking rationale. These contracts keep PIE validation tied to the
actual gameplay domain instead of a generic "it ran" signal.

D209 extends domain-specific runtime proof to input cooldown abilities and
save/load state. `input_cooldown_ability_smoke` requires Enhanced Input mapping
readback, cooldown variable readback, proof that repeat activation is blocked
while cooldown is active, HUD cooldown feedback, PIE input log, screenshot, and
ledger evidence. `save_load_state_restore_smoke` requires SaveGame or slot
helper readback, slot/version readback, captured state before save, loaded-state
comparison, restored HUD/objective state, PIE save/load log, screenshot, and
ledger evidence. Use these contracts before marking those templates playable.

D164 surfaces those runtime proof contracts through MCP Chat's existing cockpit
contexts. Review Gameplay Template, Runtime Verification, Runtime Review, and
Record Runtime Verification now carry the contract schema, proof mode, required
evidence preview, candidate proof tools, and stop-if-missing preview. Treat the
runtime-proof checklist rows as the domain-specific acceptance contract before
marking a gameplay feature proven; the cockpit still does not call providers,
mutate Unreal, run PIE, or add a permanent HUD panel.

D153 adds `compile_asset_lifecycle_manifest` to the cockpit workflow rail. Use
`target_asset_lifecycle_compile_context` when a session plan or gameplay
template already contains generated mesh prompts or Uthana animation prompts but
the lifecycle manifest is missing or stale. The action still does not call
Tripo/Uthana, spend credits, import assets, mutate Unreal, or write ledger
evidence; it prepares the provider-neutral lifecycle contract and reports
planned prompt counts, existing manifest counts, future gates, and the
recommended `write_manifest` path.

D154 makes that compile target visible in the native MCP Chat compact `Next:`
line. The editor summary can now show session-plan availability, mesh prompt
count, Uthana animation prompt count, existing manifest count, pending lifecycle
rows, future gate count, estimated motion seconds, and write guidance without
adding a new HUD row.

D155 tightens the blocked paid-generation path. When Review Provider Spend Gate
sees provider tasks blocked by wallet, credential, or spend gates and
placeholder continuation exists, `target_provider_spend_context` now carries
`fallback_placeholder_available`, `fallback_action_id`,
`fallback_tool`, `fallback_queue_tool`, and a no-spend fallback reason. Use that
handoff to compile placeholders and queue safe editor actions instead of asking
for pasted lifecycle JSON or attempting provider work.

D156 makes the handoff directly actionable. The cockpit workflow rail now adds
`continue_with_placeholder_fallback`, enabled only when provider-spend fallback
is available and placeholder context exists. The native compact `Next:` route
prefers this action over another spend-review loop, while still using the
existing placeholder manifest compiler and stop-before-provider/editor policy.

D135 adds the completion contract to every feature template and threads its
proof counts/previews into MCP Chat's existing Feature Work card. A gameplay
feature is not considered playable until the contract has asset/placeholder
proof, editor operation results, Blueprint compile evidence, graph/component
readback, PIE log, viewport or HUD screenshot, repair blockers clear, and an
IDE companion ledger event.

D136 turns that contract into an evidence-recording handoff. When the cockpit
sees a feature work order with `unreal_mcp_gameplay_feature_completion_contract.v1`,
`outputs.evidence_recording.items.record_feature_completion_contract` lists the
required-evidence, proof-gate, and stop-before-complete previews, and
`outputs.workflow_actions.record_feature_completion_contract` prepares the
`skill_record_ide_companion_evidence` ledger write. Use it only after the
underlying compile/readback, PIE, asset, repair, and ledger proof rows have been
reviewed; the action itself does not mutate Unreal or call paid providers.

D137 makes that handoff visible in the native MCP Chat workflow rail. The
command palette includes `Record Feature Completion Contract`, and the compact
`Next:` line can summarize the selected template with proof-gate,
required-evidence, stop-condition, and artifact counts. This keeps completion
proof visible from Unreal without adding a permanent HUD panel.

## D37 Feature-Template Work Orders

`skill_compile_ide_companion_work_order` now carries the selected D36 feature
template into `unreal_mcp_ide_companion_work_order.v1` as
`feature_template_work` for the `mechanic_design`, `editor_implementation`, and
`runtime_verification` phases.

For editor implementation, the work order exposes:

- feature asset list and ownership split;
- graph/component operations;
- machine-readable `editor_operation_checklist` rows for queue planning,
  including operation proof contracts for compile/readback/ledger evidence;
- compile/readback checks;
- repair instructions;
- feature evidence requirements and stop conditions.

For runtime verification, the work order exposes PIE validation steps and repair
instructions. Treat these as bridge-gated instructions: they are not proof that
the work happened. Execute them only after preflight/bridge readiness passes,
then record compile, readback, PIE, screenshot, and ledger evidence before
marking the phase complete.

## D38 MCP Chat Feature Work-Order Preview

The MCP Chat cockpit overview now reads
`latest_work_order.feature_template_work` from a matching IDE companion ledger
and exposes a bounded `work_order_template` summary plus a `feature_work_order`
card.

The preview is intentionally compact:

- target phase, template name, and display name;
- counts for assets, graph/component operations, compile checks, PIE validation,
  repair instructions, evidence requirements, and stop conditions;
- bounded `editor_operation_checklist` counts, operation-type/tool previews, and
  bridge/compile/readback-required operation counts;
- short previews for operations, compile checks, PIE validation, repair hints,
  and evidence requirements.

This is a read-only IDE surface. It makes the next bridge-gated implementation,
verification, and repair work visible in MCP Chat without executing editor
mutation, calling providers, or treating planned steps as proof.

## D39 MCP Chat Workflow Action Rail

The MCP Chat cockpit overview now includes a stable `workflow_actions` array for
the common IDE companion controls called out in the audit plan:

- Start Companion Session;
- Check Readiness;
- Queue Editor Actions;
- Execute Next Safe Step;
- Record Evidence;
- Repair Failed Step.

Each action includes an id, label, target tool, bounded arguments, enabled
state, reason, bridge/ledger/evidence flags, and an optional `input_source`
hint. The action rail is designed for the editor HUD to render explicit buttons
without guessing from raw JSON.

This remains read-only cockpit state. `Execute Next Safe Step` is enabled only
when a durable queue says the next action can run and bridge blockers are clear.
`Queue Editor Actions` advertises its hydration path because the queue compiler
requires the full session plan, status, and work order, not just the bounded
overview.

## D40 MCP Chat Local Session Picker

The MCP Chat cockpit overview now includes `session_picker`, a read-only
`unreal_mcp_chat_ide_companion_session_picker.v1` packet built from local files
under `.mcp_artifacts/ide_companion_sessions`.

The picker aggregates each IDE companion session across:

- matching evidence ledgers;
- saved editor queues;
- generated asset lifecycle manifests.

Each row is bounded and HUD-friendly: selected state, ledger path, latest phase,
next/work-order phase, event and completed-phase counts, queue/action counts,
generated asset and placeholder counts, pending generated-asset count,
can-execute flag, blockers, and a compact state.

Use this packet to render a local session picker in the editor so developers can
resume prior companion work without pasting paths or opening raw JSON. It does
not execute queued actions, mutate Unreal, call providers, or treat planned work
as evidence.

## D41 MCP Chat Blocker Resolution Preview

The MCP Chat cockpit overview now includes `blocker_resolutions`, a bounded
`unreal_mcp_chat_blocker_resolution_summary.v1` packet derived from the selected
ledger and editor queue blocking gates.

The summary mirrors the D18 blocker policies in a HUD-friendly form:

- blocker name and severity;
- recommended strategy and tool;
- one unblock action;
- one fallback action;
- evidence required to prove the blocker is resolved;
- whether offline continuation is still safe.

The existing Blockers card also includes a compact `resolution_preview` and
hard-blocker count so the editor can show both "what is blocked" and "what to
do next" without opening raw JSON. This preview is guidance only: it does not
refresh readiness, execute queued actions, mutate Unreal, call providers, or
record evidence by itself.

D129 updates the cockpit-side resolver for the current preflight gate names.
It now has explicit guidance for `chat_server_reachable`, Tripo provider key
setup, Uthana animation provider key setup, wallet evidence, spend confirmation,
and Blueprint pre-read/compile/readback gates. Target selection prefers bridge
recovery first, then native chat reachability, Blueprint safety gates, provider
secret setup, wallet evidence, and spend approval. The resolver remains
read-only: it names the next review/config/evidence path but does not start
services, store keys, call providers, ping the bridge, mutate Unreal, or write
ledger evidence.

D130 surfaces the selected blocker-resolution evidence/offline policy in the
native MCP Chat action rail. The Resolve Blockers row can now show the selected
blocker, strategy, tool, required evidence, and whether offline continuation is
allowed. Command-palette guidance also points agents at `unblock_action`,
`fallback_action`, `evidence_required`, and `can_continue_offline` before asking
for raw JSON. No new HUD block is added.

D131 aligns top-level preflight blockers with the chat cockpit readiness row.
When MCP Chat is unreachable, `outputs.blocking_gates` now includes
`chat_server_reachable` as well as the detailed
`outputs.readiness_policy.chat_cockpit.missing_gates` entry. Resolve Blockers
can therefore route native cockpit recovery from the same top-level blocker list
used by CLI and CI checks.

D132 aligns top-level preflight blockers with the paid Tripo/Uthana readiness
rows. If wallet or spend evidence is missing, `outputs.blocking_gates` now
includes `wallet_evidence_recorded` and `spend_confirmation_recorded` alongside
provider-key blockers. The preflight still does not store secrets, call
providers, record wallet proof, or authorize spend.

## D42 MCP Chat Runtime Verification Checklist

The MCP Chat cockpit overview now includes `runtime_verification`, a bounded
`unreal_mcp_chat_runtime_verification_checklist.v1` packet derived from the
latest feature-template work order.

The checklist exposes:

- target phase and bridge-blocked state;
- PIE validation count and bounded validation items;
- compile/readback check count and preview;
- evidence requirement count and proof items;
- runtime evidence events already visible in the bounded ledger preview;
- item state, bridge requirement, and evidence required for each checklist row.

The cockpit also adds a compact Runtime Verification card so the editor can show
what PIE, screenshot, log, actor-state, and compile/readback proof remains
before a phase can be treated as green. This remains a read-only plan/proof
surface: it does not launch PIE, capture screenshots, mutate Unreal, call
providers, or record evidence.

## D43 MCP Chat Repair Loop Preview

The MCP Chat cockpit overview now includes `repair_loop`, a bounded
`unreal_mcp_chat_repair_loop_summary.v1` packet derived from the latest feature
template repair instructions.

The summary exposes:

- repair instruction count and bounded repair items;
- bridge-blocked state;
- related runtime verification state and item count;
- stop-condition count;
- compile/readback and evidence previews;
- recommended work-order and evidence-recording tools.

The cockpit also adds a compact Repair Loop card so failed Blueprint, graph,
component, AI, or runtime-proof work can route naturally into a bounded repair
pass. This is still guidance only: it does not mutate Unreal, launch repair
tools, loop automatically, or mark evidence as collected.

## D44 MCP Chat Evidence Recording Checklist

The MCP Chat cockpit overview now includes `evidence_recording`, a bounded
`unreal_mcp_chat_evidence_recording_checklist.v1` packet that turns cockpit
state into "record this next" rows.

The checklist draws from:

- blocker-resolution previews;
- editor queue evidence requirements;
- runtime verification proof items;
- repair-loop evidence previews;
- generated asset lifecycle manifests;
- feature work-order evidence requirements.

Each item includes source, phase, evidence type, label, required artifacts,
state, bridge requirement, and a suggested ledger summary. The cockpit also adds
an Evidence Recording card with pending, blocked, and recorded counts plus the
`skill_record_ide_companion_evidence` tool hint. This checklist does not write
the ledger, mutate Unreal, call providers, or claim evidence exists; it only
helps the editor present the next evidence-recording tasks cleanly.

## D45 MCP Chat Next Safe Step Gate

The MCP Chat cockpit overview exposes a read-only
`unreal_mcp_chat_next_safe_step_gate.v1` packet for the selected IDE companion
session. It summarizes the first queued editor action, queue path, target phase,
argument keys, bridge requirement, bridge-blocked state, blocking gates, and
the evidence rows that should be recorded after execution.

The cockpit also adds a Next Safe Step card so the editor HUD can distinguish
ready, blocked, and empty queue states before any bridge mutation is attempted.
The packet includes a small execution policy: run only the next queued action,
stop if bridge/readiness gates change, and record evidence before continuing.
It does not execute tools, mutate Unreal, call providers, or record evidence by
itself.

## D46 MCP Chat Failure Triage Summary

The MCP Chat cockpit overview exposes a read-only
`unreal_mcp_chat_failure_triage_summary.v1` packet for the selected IDE
companion session. It scans bounded ledger events for failure/error signals,
then combines them with next-safe-step, runtime verification, and repair-loop
state so failed or blocked work has an obvious recovery path in the HUD.

Each triage item includes source, phase, label, state, recommended repair or
readiness tool, evidence tool, and a bounded artifact preview. The cockpit also
adds a Failure Triage card with blocked and needs-repair counts plus recommended
tools. This card helps failed tool states route naturally into repair work
orders and evidence recording without requiring the developer to inspect raw
JSON.

This remains a status surface only. It does not rerun failed tools, mutate
Unreal, call providers, compile Blueprints, launch PIE, or record evidence by
itself.

## D47 MCP Chat Native Cockpit Recovery Line

The native Unreal MCP Chat panel now parses the cockpit `next_safe_step` and
`failure_triage` packets and renders them in the compact IDE Cockpit strip as a
single recovery line. This makes the D45/D46 backend state visible inside Unreal
instead of only in JSON or Python route tests.

The line stays intentionally dense: safe-step state, bridge-blocked hint, and
failure-triage summary with recommended recovery tools. It does not add another
large card stack to the HUD and it does not execute queued actions. Use it as a
developer-facing prompt to refresh readiness, compile a repair work order, or
record evidence after a failed/blocked phase.

## D48 MCP Chat Companion Workflow Palette Completion

The native Unreal MCP Chat command palette now includes the missing workflow
commands for `Execute Next Safe Step` and `Repair Failed Step`, completing the
editor-visible companion loop alongside Start Session, Check Readiness, Queue
Editor Actions, Record Evidence, and related dashboard/resume/blocker tools.

These commands insert guarded instructions for the agent. `Execute Next Safe
Step` refreshes `chat_get_cockpit_overview`, inspects `outputs.next_safe_step`,
and proceeds only when `can_execute_now` is true. `Repair Failed Step` refreshes
the cockpit, inspects `outputs.failure_triage` and `outputs.repair_loop`, then
compiles a bounded repair work order. Neither command bypasses bridge/readiness
gates, runs paid providers, or mutates Unreal by itself.

## D49 MCP Chat Generated Asset Quality Gate

The MCP Chat cockpit overview exposes a read-only
`unreal_mcp_chat_generated_asset_quality_gate.v1` packet derived from saved
generated-asset lifecycle manifests. It keeps prompt/provider/import state
connected to the quality proof required before a generated mesh can replace a
placeholder in gameplay.

The packet summarizes provider-pending assets, import-pending assets, assets
waiting on material/collision/viewport/ledger proof, ready assets, placeholder
coverage, recommended tools, and bounded per-asset gate previews. The cockpit
also adds an Asset Quality card so the editor HUD can show missing import or
quality evidence without opening the raw lifecycle JSON.

This is a status surface only. It does not submit provider tasks, spend credits,
download or import assets, replace placeholders, inspect meshes in Unreal, or
record evidence by itself.

## D50 Native Cockpit Asset Quality Strip

The native Unreal MCP Chat panel now parses the cockpit
`generated_asset_quality_gate` packet and folds it into the compact IDE Cockpit
recovery strip as an `Assets:` summary. Provider-pending, import-pending,
quality-pending, ready, and placeholder counts are visible beside the safe-step
and failure-triage state without adding another HUD block.

This keeps generated asset blockers visible at the moment a developer decides
whether the next editor step is safe, while preserving the clean cockpit shape.
It is read-only: the strip does not call providers, spend credits, import
assets, replace placeholders, mutate Unreal, or record evidence.

## D54 MCP Chat Readiness Policy Packet

The MCP Chat cockpit overview now includes a read-only `readiness_policy` packet
and compact Readiness Policy card. It turns local ledger blockers, queued bridge
state, and feature work-order evidence requirements into explicit editor
mutation, paid generation, and Blueprint mutation policy rows.

Use this packet before any generated-asset or gameplay implementation step. It
keeps bridge, wallet, spend-confirmation, Blueprint pre-read, compile, and
readback blockers visible in the editor cockpit without requiring a separate
CLI preflight JSON read. The packet does not ping the bridge, call providers,
spend credits, mutate Unreal, or record evidence.

## D55 Native Cockpit Readiness Policy Summary

The native Unreal MCP Chat panel now parses `readiness_policy` from the cockpit
overview and folds a bounded `Policy:` summary into the compact recovery strip.
The line shows how many policy areas are blocked and previews missing gates such
as bridge reachability, wallet evidence, spend confirmation, Blueprint pre-read,
compile, or readback requirements.

This preserves the dense editor-native cockpit shape: no new HUD block, no
provider call, no bridge ping, no queued-action execution, no Unreal mutation,
and no evidence recording.

## D56 MCP Chat Readiness Policy Evidence Row

The MCP Chat evidence-recording checklist now includes a
`record_readiness_policy` row whenever the cockpit `readiness_policy` packet has
missing editor, paid-generation, or Blueprint mutation gates. This gives the
Record Evidence workflow a concrete offline row for bridge reachability, wallet
evidence, spend confirmation, Blueprint pre-read, compile, and readback policy
proof instead of leaving those requirements as status-only text.

The row is read-only and offline-capable. It does not ping the bridge, call
providers, submit paid generation, mutate Unreal, or write the ledger by itself;
it only tells the developer which policy evidence must be recorded before
execution.

## D57 Native Cockpit Evidence Recording Summary

The native Unreal MCP Chat panel now parses the cockpit `evidence_recording`
packet and folds a compact `Record:` summary into the existing Evidence line.
This keeps the HUD professional and uncluttered while making recordable evidence
counts visible beside session, queue, and next-action state.

When the backend exposes `record_readiness_policy`, the native summary flags
policy evidence so wallet, spend, bridge, Blueprint pre-read, compile, and
readback proof are visible before the developer uses the Record Evidence
workflow. The command-palette Record Evidence prompt also tells the agent to
inspect `outputs.evidence_recording.items` first and prefer pending rows from
the cockpit checklist.

## D58 Cockpit-Selected Record Evidence Target

The MCP Chat cockpit workflow actions now attach a selected
`target_evidence_item` to the `record_evidence` action. The selector prefers a
pending `record_readiness_policy` row, then other pending evidence rows, so the
agent has a concrete phase, evidence type, summary, and artifact list before it
records proof.

Use `outputs.workflow_actions.record_evidence.target_evidence_item` as the first
source of truth for the Record Evidence workflow. Fall back to
`outputs.evidence_recording.items` only when the selected target is absent. This
keeps the cockpit guided and reduces manual JSON hunting while preserving the
same safety guarantees: no bridge ping, provider call, Unreal mutation, or
ledger write happens until the explicit Record Evidence tool is invoked.

## D59 Native Cockpit Record Evidence Target Summary

The native Unreal MCP Chat panel now reads
`workflow_actions.record_evidence.target_evidence_item` and folds the selected
target into the existing `Record:` text. The Evidence line can now show both the
recording checklist counts and the concrete next evidence row, such as
`readiness_policy pending`, including the required artifact count.

This keeps the in-editor HUD compact while making the Record Evidence workflow
less dependent on raw JSON inspection. It remains a display-only surface: no
evidence is written, no bridge ping runs, no provider call happens, and no Unreal
mutation is performed by the summary itself.

## D60 Native Cockpit Workflow-Action Next Step

The native Unreal MCP Chat panel now uses the cockpit `workflow_actions` rail as
the source of truth for the existing `Next:` text. When the backend selects a
Record Evidence target, the editor shows that workflow first; otherwise it
prioritizes Execute Next Safe Step, Repair Failed Step, Queue Editor Actions,
Check Readiness, and Start Companion Session.

This keeps the cockpit guided without adding buttons or extra HUD rows. It is
still display-only: selecting or showing a workflow action does not execute an
MCP tool, mutate Unreal, record evidence, ping the bridge, or call a paid
provider.

## D61 Resume Companion Session Workflow Action

The MCP Chat cockpit `workflow_actions` array now includes
`resume_companion_session` when a matching IDE companion ledger is available.
The action points at `skill_resume_ide_companion_session` and carries the current
ledger path when known, so the editor workflow rail can guide a developer back
into an existing session without requiring raw JSON hunting.

The native `Next:` line recognizes this action after readiness and before
starting a fresh session. This is still metadata only: the cockpit does not load
the ledger, run tools, mutate Unreal, record evidence, ping the bridge, or call
providers until the developer explicitly invokes the workflow.

## D62 Show Companion Dashboard Workflow Action

The MCP Chat cockpit `workflow_actions` array now includes
`show_companion_dashboard` when a matching IDE companion ledger is available.
The action points at `skill_compile_ide_companion_dashboard` and carries the
current ledger path when known, so the cockpit can guide a developer back to the
dashboard surface without relying on older suggested-action text.

The native `Next:` line recognizes this action after Resume Companion Session
and before Start Companion Session. It remains display-only: the workflow rail
does not compile a dashboard, mutate Unreal, record evidence, ping the bridge, or
call providers until the developer explicitly invokes the tool.

## D63 Resolve Blockers Workflow Action

The MCP Chat cockpit `workflow_actions` array now includes `resolve_blockers`
when a matching ledger exists and cockpit blocker gates are present. The action
points at `skill_compile_ide_companion_blocker_resolution`, carries
`current_blockers`, and uses `outputs.blocker_resolutions` as its input source.

The native `Next:` line recognizes this action after Repair Failed Step and
before Queue Editor Actions. It remains display-only: the workflow rail does not
compile a resolution packet, mutate Unreal, record evidence, ping the bridge, or
call providers until the developer explicitly invokes the tool.

## D64 Native Resolve Blockers Palette Prompt

The native Resolve IDE Companion Blockers command-palette prompt now points the
agent at `outputs.workflow_actions.resolve_blockers` before asking for pasted
dashboard or status JSON. Use the workflow action's
`arguments.current_blockers` as the current gate list and
`outputs.blocker_resolutions` as the existing blocker-resolution preview.

This keeps the editor workflow aligned with the cockpit rail while preserving
the same safety boundary: selecting the palette entry only inserts a prompt. It
does not compile a resolution packet, mutate Unreal, record evidence, ping the
bridge, or call providers by itself.

## D65 Cockpit-Selected Resolve Blockers Target

The MCP Chat `resolve_blockers` workflow action now carries a selected
`target_blocker_resolution` row. The selector prioritizes the Unreal bridge gate
first, then editor-mutation blockers, placeholder-capable provider blockers,
paid-generation blockers, approval blockers, and unknown gates.

The action also exposes `arguments.target_blocker` and
`arguments.preferred_strategy` while preserving `arguments.current_blockers` and
`outputs.blocker_resolutions` for full context. The native Resolve IDE
Companion Blockers command-palette prompt now tells the agent to prefer this
selected row before asking for pasted dashboard or status JSON.

This remains guidance metadata only. It does not compile a blocker-resolution
packet, mutate Unreal, record evidence, ping the bridge, or call providers until
the developer explicitly invokes the relevant MCP tool.

## D66 Native Resolve Blockers Target Summary

The native Unreal MCP Chat panel now folds
`workflow_actions.resolve_blockers.target_blocker_resolution` into the existing
compact `Next:` text when Resolve Blockers is the selected workflow action. The
summary includes the target blocker, recommended strategy, and recommended tool
so the developer can see the first blocker to resolve without opening raw JSON.

This keeps the HUD clean and editor-native: no new row, card, or execution
button is added. The summary does not run blocker resolution, ping the bridge,
mutate Unreal, record evidence, or call providers by itself.

## D67 Cockpit-Selected Queue Editor Actions Target

The MCP Chat `queue_editor_actions` workflow action now carries a
`target_queue_context` packet. It includes the selected target phase, work-order
template name, operation count, compile-check count, evidence requirement count,
and ledger path when available. The action arguments also include `target_phase`
and `ledger_path` so the queue compiler has a concrete starting point before the
agent opens raw ledger detail.

D146 extends this packet for placeholder-to-generated replacement work. If a
feature template includes generated-asset swap operations, inspect
`generated_asset_replacement_operation_count`,
`generated_asset_replacement_operation_preview`,
`generated_asset_replacement_tool_preview`,
`generated_asset_replacement_proof_contract_count`, and
`generated_asset_replacement_gate_policy` before queue compilation. Do not
queue replacement work that would bypass lifecycle import, quality proof, or
ledger evidence.

D147 extends this packet for Uthana/generated-animation work. When the session
has animation lifecycle assets, inspect `generated_animation_asset_count`,
`generated_animation_target_name`, `generated_animation_target_skeleton`,
`generated_animation_quality_evidence_missing_count`,
`generated_animation_missing_stage_preview`,
`generated_animation_next_safe_action_id`, and
`generated_animation_gate_policy` before queueing import, retarget, AnimGraph,
or gameplay wiring. Do not queue generated-animation editor work that would
bypass provider readiness, bridge readiness, retarget/readback, AnimGraph, PIE,
or ledger evidence.

The native compact `Next:` text now uses this context when Queue Editor Actions
is the selected workflow action. It shows the target work context in the existing
line without adding another HUD row. This remains planning metadata only: it
does not compile a queue, ping the bridge, mutate Unreal, record evidence, or
execute queued editor actions by itself.

## D68 Cockpit-Selected Repair Failed Step Target

The MCP Chat `repair_failed_step` workflow action now carries a selected
`target_repair_context` packet derived from the current repair-loop preview. It
includes the repair item id, label, state, target phase, recommended work-order
tool, evidence tool, follow-up text, and bounded compile/evidence previews.

The native compact `Next:` text uses this target when Repair Failed Step is the
selected workflow action, so the editor can show the exact repair hint before
the developer opens raw JSON. This remains guidance metadata only: it does not
compile a repair work order, ping the bridge, mutate Unreal, or record evidence
until the developer explicitly invokes the relevant MCP tool.

## D69 Cockpit-Selected Execute Next Safe Step Target

The MCP Chat `execute_next_safe_step` workflow action now carries a selected
`target_execute_context` packet derived from the first queued editor action
preview. It includes the action id, tool, label, queue path, queue name, target
phase, argument keys, bridge requirement, and current executable state.

The native compact `Next:` text uses this context when Execute Next Safe Step is
the selected workflow action, so the editor can show the exact queued action
before the developer invokes it. This does not bypass gates: the action remains
disabled until bridge/readiness checks pass and does not mutate Unreal, ping the
bridge, record evidence, or execute queued work by itself.

## D8 Exact Playable-Slice Runbook

This is the canonical D.8 prompt-and-tool recipe for the headline demo. Use it
as the first pass before adding project-specific flourish.

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
8. Call `skill_generate_playable_slice(brief, mode="assemble", task_ids=[...])`
   or pass `imported_asset_paths=[...]` if the imports already happened.
9. Confirm the returned `assembled` result includes player, enemy generated-mesh
   assignment, enemy AI, HUD, nav/level placement, screenshot, PIE smoke, and
   report packaging evidence.
10. If assembly stops early, fix the named `stage` first, then rerun assemble
    with the same asset paths.

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
| Assemble has no assets | `asset_inputs_required` | Wait/import Tripo tasks first, or pass four imported `/Game/...` asset paths. |
| Tripo task is not final | `asset_import_pending` | Continue polling with `gen_tripo_wait_for_task`; rerun assemble after task status is `success`. |
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

## D70 Native Workflow Action Launcher

The native IDE Cockpit header now includes a compact `Actions` control beside
`Refresh`. It opens the existing command palette with a workflow filter already
applied, surfacing the common workflow commands without adding a crowded
permanent button row.

Use this when continuing a playable-slice session from the editor:

1. Refresh the cockpit overview.
2. Click `Actions`.
3. Choose the relevant IDE Companion action: start, readiness, resume,
   dashboard, blockers, queue, execute next safe step, record evidence, or
   repair.
4. Treat the inserted prompt as a planning/execution instruction. It does not
   bypass readiness policy, bridge gates, provider spend confirmation, or
   evidence requirements.

## D71 Workflow Palette Category

The cockpit `Actions` filter is backed by an explicit `workflow` command-palette
kind, not by matching display text. This keeps entries such as `Execute Next Safe
Step` and `Repair Failed Step` visible even though their labels are intentionally
short.

## D72 Workflow Prompt Targeting

The native workflow command-palette prompts now prefer cockpit-selected targets
before asking for broad pasted JSON:

- Queue Editor Actions: use
  `outputs.workflow_actions.queue_editor_actions.target_queue_context`, then
  `arguments.target_phase`, `arguments.ledger_path`, and
  `chat_get_cockpit_ledger_detail`.
- Execute Next Safe Step: use
  `outputs.workflow_actions.execute_next_safe_step.target_execute_context`, then
  `outputs.next_safe_step`.
- Repair Failed Step: use
  `outputs.workflow_actions.repair_failed_step.target_repair_context`, then
  `outputs.failure_triage` and `outputs.repair_loop`.

These prompts remain insertion-only. They do not bypass bridge readiness,
provider spend confirmation, Blueprint evidence gates, or the one-safe-step
execution policy.

## D73 Exact Workflow Category Filtering

The native command palette now treats known category searches such as
`workflow`, `tool`, `asset`, `prompt`, and `kb` as exact kind filters before
falling back to fuzzy text search. The cockpit `Actions` button therefore shows
actual workflow entries instead of unrelated prompts that merely contain the word
workflow.

For normal typed search terms, fuzzy matching still applies.

## D74 Workflow Action Count

The native IDE Cockpit now parses workflow-action totals from
`outputs.workflow_actions` and uses them on the compact `Actions` button. When
enabled actions are available, the button displays the enabled count and the
tooltip reports enabled vs total actions.

This gives the developer a quick readiness cue without adding another cockpit
row. It is display-only and does not execute tools or bypass readiness gates.

## D75 Zero-Enabled Workflow Cue

When the cockpit has workflow actions but all of them are disabled or gated, the
native `Actions` button now shows `Actions (0)`. This makes a blocked workflow
rail visible without adding a new HUD row. The tooltip still reports enabled vs
total actions.

## D77 Generated Asset Workflow Target

The cockpit `workflow_actions` array now includes `resolve_generated_asset`
when a generated asset quality gate has a non-ready item. The backend selects
the first provider-pending, import-pending, or quality-pending asset and exposes
it as `outputs.workflow_actions.resolve_generated_asset.target_generated_asset_context`.

Use that target before opening raw lifecycle JSON. It includes the asset id,
name, role, provider, current state, task status, manifest path, expected import
path, placeholder availability, quality-gate counts, quality-gate preview, and
the next gate. The native compact `Next:` line can surface this selected asset
without adding another cockpit row.

The action is only a planning target. It does not submit provider tasks, spend
credits, download or import assets, replace placeholders, mutate Unreal, or
record evidence. Continue to use readiness policy, wallet/spend evidence,
placeholder fallback, import proof, viewport proof, and ledger evidence before
calling any asset complete.

## D78 Generated Asset Workflow Palette Command

The native command palette now includes `Resolve Generated Asset` as a workflow
entry. It is reachable from the compact `Actions` launcher and points agents at
`outputs.workflow_actions.resolve_generated_asset.target_generated_asset_context`
before raw quality-gate rows or pasted lifecycle data.

Use this command when the cockpit shows provider-pending, import-pending, or
quality-pending generated assets. The inserted prompt tells the agent to use the
selected asset id, manifest path, current state, next gate, placeholder
availability, import path, quality-gate preview, and ledger path to choose the
next safe step.

The command is insertion-only. It does not submit provider tasks, spend credits,
download or import assets, replace placeholders, mutate Unreal, or record
evidence by itself.

## D79 Generated Asset Quality Evidence Row

The cockpit evidence checklist now includes
`record_generated_asset_quality_gate` when a generated asset quality gate has a
selected item. The row is sourced from `generated_asset_quality_gate` and records
the actual asset blocker rather than only the lifecycle manifest.

The row carries the asset name/id, current provider/import/quality state, next
gate, manifest path, expected import path, and quality-gate preview. This makes
provider-pending, import-pending, material/collision, viewport proof, and ledger
evidence requirements visible in the same `Record Evidence` workflow used for
readiness, queues, runtime proof, and repair results.

Provider-pending rows are offline-recordable. Import-pending and quality-pending
rows are marked bridge-dependent because they require import/readback/viewport
proof before they can be treated as complete. The checklist remains read-only:
it does not call providers, spend credits, import assets, mutate Unreal, replace
placeholders, or write the ledger by itself.

## D80 Generated Asset Evidence Metadata

Evidence checklist rows can now carry optional structured `metadata`.
`record_generated_asset_quality_gate` uses it to expose asset id, asset name,
role, provider, current state, task status, next gate, manifest path, expected
and imported asset paths, placeholder availability, quality-gate counts, and
quality-gate preview.

Use this metadata before parsing `required_artifacts`. It keeps Record Evidence
workflows tied to the selected generated asset even when the artifact list is
bounded for compact display. The metadata is still read-only: it does not call
providers, spend credits, import assets, replace placeholders, mutate Unreal, or
write ledger evidence.

## D81 Record Evidence Target Context

The cockpit `record_evidence` workflow action now includes
`target_evidence_context` beside the raw selected evidence row. Use this context
first when deciding what to record. It carries the selected row id, source,
phase, evidence type, state, bridge requirement, artifact count, bounded
artifact preview, and suggested summary.

When the selected row is generated-asset evidence, the context also exposes a
filtered `generated_asset` packet derived from metadata: asset id/name, role,
provider, current state, task status, next gate, manifest path, expected or
imported Unreal path, placeholder availability, and quality proof preview. This
keeps Record Evidence tied to the selected asset even when HUD text and
artifact lists are bounded for compact display.

The native MCP Chat panel prefers `target_evidence_context` for its compact
`Record:` target and only falls back to `target_evidence_item` for older
payloads. The same pass also fixes a native command-palette parameter shadow
that blocked standalone UE 5.6 `BuildPlugin` under warning-as-error settings.
The flow is still read-only: it does not call providers, spend credits, import
assets, replace placeholders, mutate Unreal, or write ledger evidence by
itself.

## D82 Evidence Ledger Workflow Action

The cockpit `workflow_actions` array now includes `show_evidence_ledger` when a
matching IDE companion ledger exists. Use this action when the developer needs
to inspect what proof has already been captured before recording new evidence,
executing queued work, or repairing failures.

The action calls `chat_get_cockpit_ledger_detail` and carries
`target_evidence_ledger_context`. That context includes the ledger path, session
name, total event count, bounded preview count, artifact count, latest evidence
phase/type, latest summary, latest artifact preview, and a compact timeline
preview. Prefer it before opening raw ledger JSON.

The native command palette now includes `Show Evidence Ledger` as a workflow
entry reachable from the compact `Actions` launcher. It is inspection-only: it
does not record evidence, mutate Unreal, execute queued editor work, call
providers, spend credits, or mark missing proof as complete.

## D83 Queued Execution Review Context

The cockpit overview now includes `execution_review`, a read-only
`unreal_mcp_chat_execution_review.v1` packet derived from `next_safe_step` and
the evidence checklist. Use it before attempting any queued editor action.

The packet names the selected action, queue path, target phase, bridge
requirement, missing gates, after-execution evidence preview, execution policy,
and the stop-after-one-action rule. The `execute_next_safe_step` workflow action
also carries this as `target_execution_review_context`, so agents can inspect
the reviewed gate before the raw `target_execute_context`.

D140 extends that review with a compact executor contract: refresh the cockpit
immediately before execution, confirm `can_execute_now` and empty blocking
gates, run only the selected queued action/tool from the selected queue path,
then record the listed post-execution evidence before any second queued action.
These checklist fields are carried in `pre_execution_checklist`,
`executor_contract`, and `post_execution_evidence_required` so native prompts
can guide execution without adding another HUD block.

D146 also carries placeholder-to-generated replacement policy into
`next_safe_step`, `execution_review`, and
`execute_next_safe_step.target_execution_review_context`. When
`generated_asset_replacement_operation_count` is greater than zero, inspect the
replacement preview, tool preview, proof-contract count, and
`generated_asset_replacement_gate_policy` before running the queued action. Keep
placeholder assets active until import, quality proof, compile/readback, and
ledger evidence are present.

D147 carries generated-animation policy through the same execution review. When
`generated_animation_asset_count` is greater than zero, inspect the target
provider, motion id, target skeleton, proof-contract schema, missing stages,
next safe action, and `generated_animation_gate_policy` before running the
queued action. Keep fallback animation active until Uthana motion, import,
retarget/readback, AnimGraph or state-machine reference, PIE proof, and ledger
evidence are complete.

If `can_execute_now` is false, do not mutate Unreal. Summarize the blockers and
route through readiness, blocker resolution, evidence recording, or repair.
If it is true, run exactly one queued action, stop, and record the listed
evidence before any second action. This review layer does not ping the bridge,
execute tools, record evidence, call providers, spend credits, or bypass
readiness gates.

## D84 Repair Review Context

The cockpit overview now includes `repair_review`, a read-only
`unreal_mcp_chat_repair_review.v1` packet derived from `repair_loop` and
`failure_triage`. Use it before compiling or applying any repair pass.

The packet names the selected repair hint, target phase, bridge state,
failure-signal count, blocked and needs-repair counts, repair instruction
count, stop-condition count, compile/evidence previews, recommended repair
tool, evidence tool, and the stop-after-one-repair-attempt rule. The
`repair_failed_step` workflow action also carries this as
`target_repair_review_context`, so agents can inspect the reviewed repair gate
before raw `target_repair_context` or repair-loop rows.

If the review state is blocked, do not mutate Unreal. Summarize the blockers
and route through readiness, blocker resolution, or evidence recording. If the
review is ready, compile one scoped repair work order, apply at most one repair
attempt when gates pass, stop, then record compile/readback/runtime evidence.
This review layer does not compile repairs, ping the bridge, execute tools,
record evidence, call providers, spend credits, or bypass readiness gates.

## D85 Runtime Verification Review Workflow

The cockpit overview now includes `runtime_review`, a read-only
`unreal_mcp_chat_runtime_review.v1` packet derived from
`runtime_verification`. Use it before attempting PIE, viewport, screenshot, or
actor-state proof.

The packet names the target phase, bridge state, PIE validation count,
compile-check count, evidence requirement count, runtime evidence already
recorded, blocked/pending/recorded checklist counts, proof previews, evidence
tool, and the stop-after-runtime-probe rule. The
`review_runtime_verification` workflow action carries this as
`target_runtime_review_context`, so agents can inspect the reviewed runtime
gate before raw checklist rows.

If `can_verify_now` is false, do not mutate Unreal or run PIE. Summarize the
missing bridge/readiness/proof gates and route through readiness, blocker
resolution, or evidence recording. If it is true, capture only the scoped
runtime probe required by the current work order, stop, and record PIE log,
viewport screenshot, observed actor state, compile, and readback evidence
before continuing. This review layer does not run PIE, ping the bridge,
execute tools, record evidence, call providers, spend credits, or bypass
readiness gates.

## D86 Runtime Evidence Recording Target

The cockpit workflow rail now includes `record_runtime_evidence`, a dedicated
evidence-recording action for the `record_runtime_verification` checklist row.
Use it after `review_runtime_verification` has identified the scoped runtime
proof to capture.

The runtime evidence row now carries structured metadata promoted into
`target_evidence_context.runtime_verification`: target phase, bridge state, PIE
validation count, compile-check count, evidence requirement count, runtime
evidence already recorded, blocked/pending/recorded checklist counts, proof
preview, and compile-check preview. This lets agents record or explain runtime
proof without parsing artifact strings.

If the target row is blocked, do not run PIE or mutate Unreal from the record
action. Record only existing artifacts or explain that bridge/readiness gates
prevented runtime proof. If proof exists, record the PIE log, viewport
screenshot, observed actor state, compile, and readback artifacts, then refresh
the cockpit before any further queued execution. This action does not run PIE,
ping the bridge, execute tools, call providers, spend credits, or bypass
readiness gates.

## D87 Queued Action Evidence Recording Target

The cockpit workflow rail now includes `record_queued_action_evidence`, a
dedicated evidence-recording action for the first queued editor action evidence
row, `record_editor_queue_1`. Use it after `execute_next_safe_step` has run or
stopped and the compile/readback proof is available or known blocked.

Queued editor evidence rows now carry structured metadata promoted into
`target_evidence_context.queued_action`: queue path/name, target phase,
selected action id/tool/label, queued action counts, argument keys, bridge
state, execution readiness, and evidence preview. This lets agents record or
explain queued-action proof without parsing artifact strings.

If the target row is blocked, do not execute queued work from the record
action. Record only existing compile/readback artifacts or explain that
bridge/readiness gates prevented proof. If proof exists, record the compile
report, Blueprint/asset/component readback, and any action-specific artifact,
then refresh the cockpit before another queued action. This action does not
execute tools, ping the bridge, mutate Unreal, call providers, spend credits,
or bypass readiness gates.

## D88 Generated Asset Evidence Recording Target

The cockpit workflow rail now includes `record_generated_asset_evidence`, a
dedicated evidence-recording action for the generated asset quality-gate row,
`record_generated_asset_quality_gate`. Use it after provider, placeholder,
import-path, or quality-gate proof exists or is known blocked.

Generated asset evidence rows carry structured metadata promoted into
`target_evidence_context.generated_asset`: asset id/name/role, provider,
lifecycle state, task status, next gate, manifest path, expected import path,
imported asset path, placeholder state, quality gate count, quality evidence
count, and proof preview. This lets agents record or explain generated-asset
proof without parsing artifact strings.

If the target row is blocked, do not submit provider tasks, import assets, or
mutate Unreal from the record action. Record only existing lifecycle artifacts
or explain that provider/import/quality gates prevented proof. If proof exists,
record the provider task receipt, placeholder/readback state, import path, and
viewport or quality evidence, then refresh the cockpit before any further asset
work. This action does not ping the bridge, execute tools, call providers,
spend credits, or bypass readiness gates.

## D89 Generated Asset Gate Review Workflow

The cockpit workflow rail now includes `review_generated_asset_gate`, a
read-only action for inspecting the generated asset quality gate before
resolving lifecycle blockers or recording proof. Use it when generated asset
work is visible in the cockpit and the agent needs to decide between
placeholder fallback, provider submission, import, quality proof, or evidence
recording.

The action carries `target_generated_asset_review_context`: gate state, total
asset count, provider/import/quality/ready/placeholder counts, the
cockpit-selected target asset, review/resolve/evidence tools, and
`stop_before_provider_or_import`. This lets agents inspect generated-asset
status without opening lifecycle JSON or guessing which asset should drive the
next step.

This review action is inspection-only. Do not submit provider tasks, spend
credits, import assets, replace placeholders, mutate Unreal, or record evidence
from the review command. If the gate is blocked, summarize the missing
provider/import/quality/evidence requirements and route to blocker resolution,
placeholder work, `resolve_generated_asset`, or
`record_generated_asset_evidence`.

## D90 Readiness Policy Workflow Target

The `check_readiness` workflow action now carries
`target_readiness_policy_context`, a compact review target derived from the
cockpit `readiness_policy` packet. Use it before refreshing preflight or
attempting editor/provider/Blueprint work.

The context summarizes policy state, blocked policy areas, missing gate count,
missing gate preview, recommended tools, and
`stop_before_editor_or_provider`. This lets agents explain why readiness is
blocked from the workflow rail without asking for pasted readiness JSON or
scraping the policy card.

If any gate is missing, do not mutate Unreal, submit provider tasks, spend
credits, or change Blueprints. Refresh readiness with
`gen_compile_ide_companion_readiness`, route specific blockers through
`resolve_blockers`, and record readiness evidence before returning to queued
editor execution.

## D91 Resume Session Workflow Target

The `resume_companion_session` workflow action now carries
`target_resume_context`, a compact ledger-derived target for returning to an
IDE companion session. Use it before calling the resume skill so the agent can
explain what is being resumed instead of asking for a ledger path alone.

The context summarizes session name, ledger path, event count, completed phase
count, latest phase and summary, next phase/tool, work-order phase, blocking
gate preview, preview event count, resume/dashboard tools, and
`stop_before_editor_mutation`. This keeps resuming a session inside the same
guided cockpit loop as readiness, evidence, execution, repair, runtime, and
generated-asset workflows.

When resuming, do not mutate Unreal immediately. Load the ledger, refresh
readiness if gates may have changed, compile the next work context, then route
through queue, blocker, evidence, or repair actions. Treat resume as
orientation and planning until bridge/readiness gates prove mutation is safe.

## D92 Dashboard Workflow Target

The `show_companion_dashboard` workflow action now carries
`target_dashboard_context`, a compact dashboard-derived target for inspecting
the selected companion state before opening the full dashboard.

The context summarizes session name, ledger path, event count, completed phase
count, latest/next/work-order phases, readiness state, blocked policy count,
blocking gate count, queue/action counts, executable queue count, evidence item
count, generated asset state/count, runtime review state, repair loop state,
dashboard/review tools, and `stop_before_editor_mutation`. This keeps dashboard
navigation in the same workflow rail as readiness, resume, evidence, execution,
repair, runtime, and generated-asset review.

Treat dashboard display as inspection only. Do not mutate Unreal, ping the
bridge, submit provider tasks, spend credits, import assets, record evidence,
or bypass readiness gates from the dashboard action. Use it to orient the next
safe action, then route through readiness, blocker, queue, evidence, runtime,
generated-asset, or repair workflows as appropriate.

## D93 Start Session Workflow Target

The `start_companion_session` workflow action now carries
`target_start_context`, a compact startup target for creating or refreshing the
IDE companion session without losing the current cockpit state.

The context summarizes session name, whether an existing ledger is present,
ledger path, event/completed phase counts, latest phase, readiness state,
blocked policy count, queue count, generated asset count, recommended next
path, startup/review tools, and `stop_before_editor_or_provider`. Use this
before compiling a new session plan so agents can decide whether to create a
fresh plan, resume the existing ledger, refresh readiness, or route to blockers
without asking for pasted JSON.

Treat session start as orientation and planning. Do not mutate Unreal, ping the
bridge, submit provider tasks, spend credits, import assets, change Blueprints,
or bypass readiness gates from this action. It may compile a plan; execution
still must flow through readiness, queue, evidence, runtime, generated-asset,
or repair gates.

## D94 Status Refresh Workflow Target

The cockpit workflow rail now includes `refresh_companion_status`, a
no-spend status-refresh action backed by `skill_compile_ide_companion_status`.
Use it when an IDE companion ledger exists and the agent needs to reconcile
phase progress, readiness, blockers, evidence, queues, generated assets, and
runtime state before choosing the next workflow action.

The action carries `target_status_context`: session name, ledger path, whether
a session plan is available, session-plan phase count, event/completed phase
counts, latest/next phase, next tool, readiness state, blocker count, queue
count, evidence item count, generated asset count, runtime review state, status
tool, resume/readiness/review tools, `requires_session_plan`, and
`stop_before_editor_or_provider`.

Do not use status refresh to mutate Unreal, ping the bridge, submit provider
tasks, spend credits, import assets, or bypass readiness gates. If a session
plan is missing, resume or open the dashboard first, then compile the status
receipt from the real plan, readiness report, completed phases, evidence map,
and current blockers.

## D95 Work Order Workflow Target

The cockpit workflow rail now includes `generate_work_order`, a no-spend
work-order compilation action backed by
`skill_compile_ide_companion_work_order`. Use it after session/status context
exists and before queueing editor actions, especially when the next phase,
blockers, or feature-template work needs to be recompiled from current
readiness and evidence.

The action carries `target_work_order_context`: session name, ledger path,
session-plan/status availability, target phase, latest/next phase, next tool,
readiness state, blocker count, completed phase count from status, gameplay
template name/display name, graph operation count, compile-check count, PIE
validation count, evidence requirement count, work-order/status/resume/review
tools, `requires_session_plan`, `prefers_status_receipt`, and
`stop_before_editor_mutation`.

Do not use work-order generation to mutate Unreal, ping the bridge, queue
editor actions, submit provider tasks, spend credits, import assets, or bypass
readiness gates. Generate the work order, inspect blockers and evidence
requirements, then route to queue, blocker, evidence, runtime, generated-asset,
or repair workflows.

## D96 Placeholder Manifest Workflow Target

The cockpit workflow rail now includes `compile_placeholder_manifest`, a
no-spend placeholder fallback action backed by
`skill_compile_ide_companion_placeholder_manifest`. Use it when generated
assets are blocked by provider, spend, bridge, or import gates but gameplay
proof can continue with placeholders.

The action carries `target_placeholder_context`: session name, ledger path,
session-plan availability, readiness state, blocked policy count, blocker
count, generated-asset gate state, provider/import/quality/ready/placeholder
counts, selected target asset, placeholder root, placeholder/blocker/lifecycle
tools, `requires_session_plan`, and `stop_before_editor_or_provider`.

Do not use placeholder manifest compilation to mutate Unreal, ping the bridge,
queue editor actions, submit provider tasks, spend credits, import assets,
replace placeholders, or bypass readiness gates. Compile the manifest, inspect
the replacement map and evidence requirements, then route to queue, evidence,
generated-asset lifecycle, or blocker workflows.

## D97 Editor Queue Review Workflow Target

The cockpit workflow rail now includes `review_editor_queue`, a read-only queue
inspection action backed by `chat_get_cockpit_overview`. Use it before queue
recompilation or execution when the developer needs to understand queued editor
work, bridge blockers, and required after-execution evidence without mutating
Unreal.

The action carries `target_queue_review_context`: queue/action counts,
executable/blocked/bridge-blocked queue counts, selected queue name/path/phase,
next action id/tool, evidence count, blocking gate preview, review/execute tool
hints, and `stop_before_editor_mutation`.

D148 threads generated-content gates into this same read-only queue review
context. When a queued feature involves placeholder-to-generated mesh swaps or
Uthana animation work, inspect generated-asset replacement counts/previews,
generated-animation target/skeleton/missing-stage fields, and their gate policy
before execution. This keeps already-compiled queues proof-aware without adding
another HUD panel.

Do not use queue review to mutate Unreal, run queued actions, record evidence,
ping the bridge, call providers, spend credits, or bypass readiness gates. Use
the review packet to decide whether to execute one safe step, recompile the
queue, resolve blockers, or record evidence.

## D98 Evidence Requirements Review Workflow Target

The cockpit workflow rail now includes `review_evidence_requirements`, a
read-only evidence checklist review action backed by
`chat_get_cockpit_overview`. Use it before writing ledger evidence when the
developer needs to understand pending proof, blocked proof, already-recorded
proof, and the selected next evidence row without mutating the ledger.

The action carries `target_evidence_review_context`: session name, target
phase, evidence item counts, pending/blocked/recorded counts, selected target
evidence id/type/context, target artifact count and preview, record tool,
bridge/network/spend requirements, and `stop_before_ledger_write`.

Do not use evidence review to mutate Unreal, write ledger evidence, ping the
bridge, call providers, spend credits, or bypass readiness gates. Use the
review packet to decide whether to record evidence, resolve blockers, execute
one safe step, or gather missing proof first.

## D99 Provider Spend Gate Review Workflow Target

The cockpit workflow rail now includes `review_provider_spend_gate`, a
read-only paid-generation gate review action backed by
`chat_get_cockpit_overview`. Use it before any Tripo or other provider task
when generated assets are provider-pending and the developer needs to see
credentials, wallet evidence, spend confirmation, target asset, and fallback
options in one packet.

The action carries `target_provider_spend_context`: paid-generation readiness
state, provider-pending asset count, selected target asset/provider/next gate,
missing gate preview, required evidence preview, placeholder count,
readiness/placeholder/lifecycle tool hints, `future_network_required`,
`future_spend_required`, and `stop_before_provider_call`.

Do not use provider spend review to submit provider tasks, call providers,
spend credits, import assets, mutate Unreal, write ledger evidence, or bypass
readiness gates. Use the review packet to decide whether to refresh readiness,
continue with placeholders, resolve blockers, or stop for explicit spend
confirmation.

## D100 Bridge Wrapper Coverage Review Workflow Target

The cockpit workflow rail now includes `review_bridge_wrapper_coverage`, a
read-only source-audit review action backed by `chat_get_cockpit_overview`.
Use it before planning more native bridge wrapper work so a solo developer can
see whether the roadmap's high-value C++ routes are already reachable from
Python MCP tools, covered by tests, and documented.

The action carries `target_bridge_wrapper_context`: wrapper coverage state,
covered/total capability counts, command count, failing capability preview,
the high-value wrapper audit script, the bridge command registry audit, and
`no_editor_mutation`.

Do not use wrapper coverage review to mutate Unreal, ping the bridge, edit
Blueprint assets, call providers, spend credits, or bypass readiness gates.
Use the review packet to decide whether wrapper work is already stable enough
to move on, or whether a focused wrapper/test/doc follow-up is still needed.

## D101 Gameplay Template Plan Review Workflow Target

The cockpit workflow rail now includes `review_gameplay_template_plan`, a
read-only feature-template review action backed by `chat_get_cockpit_overview`.
Use it after an IDE companion work order exists and before queueing editor
actions, especially for common loops such as interactables, pickups,
patrol/chase/attack AI, objective HUD updates, save/load state, input cooldown
abilities, or replicated samples.

The action carries `target_gameplay_template_context`: selected template name,
target phase, asset count, graph/component operation count, compile/readback
checks, PIE validation count, evidence requirements, repair instructions,
ownership domains, placeholder/generated asset swap requirements, bounded
preview rows, editor readiness state, missing editor gate preview, and
`stop_before_editor_mutation`.

For templates that include placeholder-to-generated replacement work, inspect
`generated_asset_replacement_operation_count`,
`generated_asset_replacement_operation_preview`,
`generated_asset_replacement_tool_preview`, and
`generated_asset_replacement_proof_contract_count` before queueing editor
actions. The native compact summary shows the same work as a small swap count
inside the existing Review Gameplay Template line instead of adding another HUD
block.

Do not use gameplay template review to mutate Unreal, queue actions, run PIE,
write ledger evidence, call providers, spend credits, or bypass readiness
gates. Use the review packet to decide whether the current feature template is
ready to queue, needs a different mechanic plan, or should stop on missing
bridge/readback evidence first.

## D124 Cockpit Editor-Operation Checklist Review

MCP Chat now carries feature-template `editor_operation_checklist` metadata into
the same read-only cockpit surfaces that already review gameplay-template work:
`outputs.work_order_template`, `feature_work_order`, Blueprint mutation review,
`review_gameplay_template_plan.target_gameplay_template_context`, and
`queue_editor_actions.target_queue_context`.

When reviewing a feature plan before editor mutation, inspect:

- `editor_operation_count`;
- `editor_operation_type_preview`;
- `editor_operation_tool_preview`;
- `editor_operation_preview`;
- `bridge_required_operation_count`;
- `compile_after_operation_count`;
- `readback_after_operation_count`.

The legacy `operation_count` still means graph/component operation count. Treat
the new editor-operation fields as the queue-planning layer that says which
MCP tools and readback gates are expected before any bridge-gated mutation.

## D102 Test Lane Gate Review Workflow Target

The cockpit workflow rail now includes `review_test_lane_gates`, a read-only
CI lane review action backed by `chat_get_cockpit_overview`. Use it before
running broad test commands when the developer needs to confirm that default
offline discovery remains separated from live-bridge and paid-provider checks.

The action carries `target_test_lane_context`: default discovery pattern,
offline/live-bridge/live-manual/paid-provider/manual counts, violation count
and preview, bounded lane previews, the `scripts/audit_test_lanes.py` path,
the `docs/ci-smoke.md` path, `default_ci_safe`, future bridge/spend flags, and
`no_editor_mutation`.

Do not use test lane review to run live bridge tests, paid-provider tests,
mutate Unreal, call providers, spend credits, or bypass readiness gates. Use
the review packet to decide whether default offline CI is safe, or whether a
live bridge/provider lane requires explicit operator intent and evidence first.

D165 also embeds this lane audit into IDE companion preflight. The
`unreal_mcp_ide_companion_preflight.v1` report now carries compact lane counts,
violation count, previews, and `default_ci_safe`; platform stability includes
`test_lane_separation` as a required gate. If lane separation fails, do not move
WIP work toward `main`, run broad default discovery, or treat offline CI as
no-mutation until the filenames or lane policy are repaired.

D166 tightens Uthana blocker targeting. When the only paid-animation blockers
are missing Uthana auth plus wallet/spend evidence, MCP Chat should select
`animation_provider_api_key_configured` first and route the developer to the
native masked Generate Settings / `gen_save_provider_config` path. Record wallet
or allowance evidence only after the animation provider credential source is
configured and still never expose the raw key in chat, docs, or ledger entries.

D167 makes platform-stability blockers first-class Resolve Blockers targets.
If preflight reports `tool_registry_reproducible`, `test_lane_separation`,
`build_wrapper_present`, `build_wrapper_references_ready`, or
`working_branch_is_wip`, MCP Chat should return a specific no-mutation repair
strategy rather than an unknown blocker. Platform blockers sit behind bridge,
chat, and Blueprint safety gates, but ahead of provider credential, wallet, and
spend tasks because WIP should not be promoted or broadly tested until registry,
lane, build-wrapper, and branch evidence are trustworthy.

D168 extends that same repair pattern to WIP-promotion-only gates. The
`target_wip_promotion_context` now includes `promotion_resolution_preview` and
`target_promotion_blocker_resolution` for gates such as
`dirty_state_grouped_for_promotion`, `plugin_build_successful`,
`no_mutation_test_lane_safe`, `high_value_bridge_wrappers_covered`, and
`chat_cockpit_reachable`. Use the selected promotion blocker to decide the next
source-side repair before staging, committing, merging, running live lanes, or
moving WIP toward `main`.

D169 makes WIP promotion readiness part of the IDE companion preflight itself.
`unreal_mcp_ide_companion_preflight.v1` now returns
`readiness_policy.wip_promotion` and `ready_for_wip_promotion`, requiring WIP
branch policy, reproducible tool count, no-mutation test lane safety,
build-wrapper readiness, recent plugin build success, grouped/clean dirty state,
and chat cockpit reachability. Treat this as a promotion gate only: it does not
authorize editor mutation, provider calls, git staging, commits, merges, or
moving changes to `main`.

D170 mirrors that WIP promotion policy inside MCP Chat's derived
`readiness_policy` and `check_readiness` context. The cockpit maps audit-level
`test_lane_separation` to `no_mutation_test_lane_safe` and
`chat_server_reachable` to `chat_cockpit_reachable` so the action context uses
the same promotion gate names as preflight. Treat this as read-only guidance for
repair order; it still does not authorize git mutation, bridge pings, provider
calls, editor mutation, or release movement.

D171 makes the dirty-state promotion blocker inspectable. Preflight now groups
dirty paths into bounded source areas such as server tests, MCP server tools,
chat cockpit, Unreal plugin, scripts, docs, project knowledge, local artifacts,
and dependency files. MCP Chat carries that grouped summary into platform
preflight and WIP promotion contexts so a developer can decide what belongs in a
human-led promotion plan. The grouping is evidence only; it must not stage,
commit, clean, delete, branch, merge, ping the bridge, mutate Unreal, or call
providers.

D172 makes chat-cockpit reachability repair explicit. Preflight now reports the
chat base URL, `/chat/history?limit=1` health endpoint, TCP reachability, SSE
startup command, Cursor watcher command, and bounded troubleshooting hints. MCP
Chat carries the same compact packet into platform preflight and WIP promotion
contexts so `chat_server_reachable` and `chat_cockpit_reachable` have the same
repair evidence path. This is still passive guidance: it does not start a
server, run the watcher, ping Unreal, mutate editor state, write evidence, or
call providers.

D173 makes provider credential repair explicit without leaking secrets.
Preflight now carries a provider repair contract with `gen_get_provider_config`,
`gen_save_provider_config`, placeholder-only Tripo and Uthana setup templates,
ignored `Saved/MCPChat` secret-path proof, and a no-leak policy. MCP Chat
surfaces that compact packet in platform preflight context so
`provider_api_key_configured` and `animation_provider_api_key_configured` can be
resolved through native Generate Settings, environment variables, or ignored
local secrets. The contract is guidance only; it must not write keys, call
providers, check wallets, spend credits, ping Unreal, mutate assets, or record
ledger evidence by itself.

D174 makes the wallet/spend gate actionable without calling paid providers.
Preflight now carries `paid_generation_evidence`, a Tripo/Uthana evidence
contract that names `gen_tripo_get_credit_balance`, Uthana account/download
allowance checks, explicit spend/usage approval fields, and the required ledger
evidence row before any paid task submission. MCP Chat surfaces the compact
contract in platform preflight and provider-spend contexts. Treat it as a
no-spend repair checklist only: it must not call providers, check balances,
reserve credits, write ledger evidence, ping Unreal, mutate editor state, or
replace placeholders by itself.

D176 makes high-value wrapper coverage part of the main preflight contract.
Preflight now embeds the offline `audit_high_value_wrapper_coverage.py` result
and promotes `high_value_bridge_wrappers_covered` into platform-stability and
WIP-promotion gates. MCP Chat surfaces the compact wrapper count/schema summary
inside platform preflight context while the existing Review Bridge Wrapper
Coverage action remains the detailed drill-down. This is source, registry, test,
and documentation evidence only; it must not ping Unreal, mutate Blueprints,
stage changes, call providers, or bypass bridge/action-specific proof gates.

D177 turns dirty-state grouping into an explicit promotion review contract.
Preflight now carries `dirty_promotion_contract` with dirty risk, tracked and
untracked counts, primary dirty group, bounded review batches, required
evidence, and no-git-mutation flags. MCP Chat threads that same compact contract
into platform preflight and WIP promotion contexts so
`dirty_state_grouped_for_promotion` points at a human review order. Use it to
classify groups before promotion; do not stage, commit, clean, delete, branch,
merge, ping Unreal, call providers, or mutate assets from the review packet.

D178 promotes chat reachability repair into a named startup contract. Preflight
now carries `chat_cockpit_repair_contract` with the SSE startup command,
`/chat/history?limit=1` proof command, startup steps, required evidence, TCP
readiness, and no-process/no-port-kill flags. MCP Chat threads that same compact
contract into platform preflight and WIP promotion contexts so
`chat_server_reachable` and `chat_cockpit_reachable` share one repair path. Use
it to start and verify chat manually; do not launch servers, kill ports, call
providers, ping Unreal, mutate assets, spend credits, or touch git from the
contract packet.

D179 adds a read-only `readiness_repair_queue` to preflight and MCP Chat
contexts. The queue turns scattered readiness blockers into ordered safe next
actions with a gate, policy area, recommended tool, evidence preview, and passive
flags. It points chat to the chat repair contract, provider keys to masked
Generate Settings or ignored secrets, wallet checks to no-spend allowance tools,
dirty state to the dirty promotion contract, and bridge recovery to bridge ping
evidence. Treat it as guidance for the developer/operator; do not auto-execute
the queue, echo secrets, spend credits, kill ports, mutate Unreal, stage, commit,
clean, branch, or merge from it.

D180 makes that repair queue a first-class MCP Chat evidence handoff. The
cockpit evidence checklist now includes `record_readiness_repair_queue`, with
bounded artifacts for the next action id, gate, recommended contract/tool, and
proof preview. The Record Evidence workflow target prefers this row before the
broader readiness policy so a blocked session can preserve "what to fix first"
in the IDE companion ledger. Recording the row is still passive; it must not run
the repair action, ping Unreal, call providers, echo keys, spend credits, mutate
assets, or touch git.

D181 threads the repair queue into the native MCP Chat panel without adding a
new permanent HUD card. The existing Blockers line can include the next repair
action, gate, recommended tool, and action count; the existing Evidence line can
show when a repair-queue ledger row is available. Keep this as a compact summary
and use detail views/workflow actions for the full JSON. The native panel must
not execute the queue, start processes, ping the bridge, call providers, reveal
secrets, mutate Unreal, spend credits, or touch git from this summary.

D182 adds a provider-neutral paid-generation evidence row to MCP Chat. Use
`record_paid_generation_evidence` to preserve Tripo wallet proof, Uthana
allowance/download proof, and explicit human spend or usage approval before
submitting any paid provider task. The workflow action and native command
palette prompt only record existing proof or a blocked explanation; they must
not call Tripo or Uthana, download files, import assets or animations, reserve
credits, create approval, mutate Unreal, or touch git.

D199 adds a local paid-generation evidence review receipt at
`Saved/PaidGenerationEvidence/last_review_receipt.json`. Use
`scripts/write_paid_generation_evidence_review.py` to preserve non-secret review
proof for wallet/allowance evidence, estimated spend or motion seconds, and
explicit human spend/usage approval before paid Tripo or Uthana tasks. The
receipt is ignored local proof and does not call providers, check wallets,
reserve credits, submit tasks, download or import assets, mutate Unreal, approve
spend by itself, or touch git.

D200 makes the CLI preflight receipt picture visible without opening JSON. The
human-readable `scripts/audit_ide_companion_readiness.py` output should show
bridge ping, provider config review, paid generation evidence, dirty promotion
review, and platform stability receipt states and paths beside the readiness
gates. Treat this as display-only status; it must not ping the bridge, start
chat, call providers, check wallets, approve spend, mutate Unreal, or touch git.

D201 completes that human preflight proof picture for execution-adjacent local
receipts. The summary should also show the chat cockpit startup receipt, the
no-mutation unittest receipt, and the local plugin-build receipt so a developer
can see whether chat, test-lane safety, and build proof are current without
opening JSON artifacts. This remains display-only: do not start chat, run tests,
build the plugin, ping Unreal, call providers, approve spend, mutate assets, or
touch git from the summary.

D202 keeps that preflight proof picture compact for the native cockpit. When a
receipt path is inside the Unreal-MCP-Ghost repo, the human-readable summary
should display the repo-relative `Saved\...` path instead of a long absolute
path. This is a display-only normalization for scanability; JSON outputs should
keep their existing machine-readable values, and the formatter must not read new
artifacts, write receipts, run tests, build, ping Unreal, call providers,
approve spend, mutate assets, or touch git.

D203 treats configured provider credentials as a first-class workstation state.
When Tripo and Uthana keys are present through environment variables or ignored
`Saved/MCPChat/secrets.json`, preflight should mark provider configuration ready
and remove the provider-key repair actions while continuing to block paid mesh
or animation generation until wallet/allowance evidence and explicit
spend/usage confirmation are recorded. Tests should cover both missing-secret
and configured-secret states without echoing raw keys, calling providers,
checking wallets, submitting tasks, mutating Unreal, or touching git.

D204 clarifies the no-spend wallet/allowance gate that follows credential setup.
The preflight and cockpit contracts should show the exact safe review path:
confirm provider-network approval and no-spend intent, run masked
`gen_tripo_get_credit_balance(include_raw=False)` and
`gen_uthana_get_account(include_user=False)` checks when approved, then write
`Saved\PaidGenerationEvidence\last_review_receipt.json` with a short non-secret
summary. The spend/usage confirmation receipt command must remain a separate
step, and provider task submission, credit reservation, downloads, imports,
Unreal mutation, and git mutation stay blocked until that evidence is present.

D205 makes the manual paid-provider smoke contract visible to preflight and the
cockpit. `scripts/audit_test_lanes.py` should prove
`paid_provider_generative_smoke.py` is outside default `test_*.py` discovery and
names the opt-in environment variables, no-spend tools, manual command, and
forbidden spend/download/task-submission tokens. Treat this contract as static
CI evidence only; it must not run the provider smoke, call Tripo or Uthana,
check wallets, reserve credits, submit tasks, download/import assets, mutate
Unreal, or touch git.

D206 preserves that contract in the platform-stability receipt. When
`scripts/write_platform_stability_review.py` writes
`Saved\PlatformStabilityReview\last_review_receipt.json`, it should snapshot the
paid-provider smoke command, opt-in env vars, no-spend tools, and no-task /
no-download / no-import flags so promotion review can rely on saved evidence
rather than a transient preflight view. This remains passive receipt generation:
do not run the provider smoke, call providers, reserve credits, submit tasks,
download/import assets, mutate Unreal, stage, commit, or promote branches.

D183 makes gameplay-template review a better handoff for Uthana animation work.
When a work-order template includes generated animation prompts,
`review_gameplay_template_plan.target_gameplay_template_context` must expose the
paid-animation readiness state beside the prompt preview: missing auth,
wallet/allowance, spend/usage gates, required evidence, safe unblock tools, and
`generated_animation_stop_before_provider`. The native compact `Next:` summary
can show the animation gate count, but the HUD should remain clean and passive:
no Uthana calls, downloads, imports, PIE runs, ledger writes, editor mutation,
secret echo, or spend from template review.

D184 makes plugin-build proof local to this repo. `_build_plugin.bat` now writes
`Saved/PluginBuildSmoke/last_build.log` and
`Saved/PluginBuildSmoke/last_build_receipt.json`; both are ignored local
artifacts. `scripts/audit_ide_companion_readiness.py` should prefer that receipt
before machine-global AutomationTool logs so `plugin_build_successful` reflects
the Unreal-MCP-Ghost plugin build, not a different Unreal project. Treat the
receipt as build evidence only: it does not prove bridge readiness, chat
reachability, provider auth, wallet/spend approval, Blueprint readback, or WIP
promotion safety.

D185 adds the matching proof artifact for the no-mutation test lane.
`scripts/run_no_mutation_unittest.py` writes
`Saved/NoMutationTest/last_run_receipt.json` after the tracked-file hash
comparison completes. Preflight and MCP Chat should report the receipt state,
test exit code, and mutation count, and WIP promotion should keep
`no_mutation_test_lane_safe` blocked until lane separation is clean and the last
receipt reports `status=success`, `test_exit_code=0`, and `mutation_count=0`.
This receipt is local proof only; it does not authorize bridge mutation, provider
work, Blueprint edits, staging, commits, branch movement, or promotion to main.

D186 adds an executable repair path for chat cockpit reachability without making
preflight start processes. When `chat_server_reachable` is blocked,
`chat_cockpit_repair_contract` should point at
`scripts/start_chat_cockpit_server.ps1`, which starts the SSE MCP server hidden,
waits for `/chat/history?limit=1`, and writes
`Saved/ChatCockpit/last_start_receipt.json`. Treat the receipt as chat-start
evidence only: it does not authorize editor mutation, provider calls, spend,
port killing, Git staging, commits, branch movement, or promotion to main.

D198 threads the chat startup receipt into the cockpit evidence ledger flow.
When an IDE companion ledger exists, `record_chat_cockpit_start_receipt` records
startup receipt path, `/chat/history?limit=1` health proof, repair state,
startup/proof commands, and no-process-start/no-port-kill/no-editor/no-provider/
no-git flags through `skill_record_ide_companion_evidence`. Treat this as proof
capture only; it should not start processes, kill ports, mutate Unreal, call
providers, spend credits, or touch Git.

D187 adds durable dirty-state review proof for promotion planning.
`scripts/write_dirty_promotion_review.py` writes
`Saved/DirtyPromotionReview/last_review_receipt.json` with grouped dirty paths,
review batches, required evidence, and WIP/main branch policy. Use it when
`dirty_state_grouped_for_promotion` is the remaining blocker so the cockpit can
show a concrete review artifact instead of asking the developer to interpret raw
`git status`. Treat the receipt as review evidence only; it does not stage,
commit, clean, delete, merge, move branches, mutate Unreal, call providers,
spend credits, or authorize promotion to main.

D195 threads dirty-state review into the cockpit evidence ledger flow. When an
IDE companion ledger exists, `record_dirty_promotion_review` records the dirty
review receipt path/state, dirty risk, tracked/untracked/group counts, review
batch count, recommended next action, and no-stage/no-commit/no-clean/no-branch
movement safety flags through `skill_record_ide_companion_evidence`. Treat this
as proof capture only; it should not stage, commit, clean, merge, move branches,
mutate Unreal, call providers, spend credits, or promote WIP to main.

D188 makes live bridge proof durable. `scripts/bridge_ping.py` now writes
`Saved/BridgePing/last_ping_receipt.json` for successful and failed pings.
Preflight should treat raw TCP reachability as insufficient for editor mutation:
the bridge gate is ready only when the bridge is reachable and the receipt proves
`successful_bridge_ping=true`. A failed receipt is blocker evidence, not
permission to execute Blueprint, actor, PIE, viewport, or queued editor actions.

D197 threads bridge ping proof into the cockpit evidence ledger flow. When an
IDE companion ledger exists, `record_bridge_ping_receipt` records the receipt
path/state, endpoint, TCP readiness, `successful_bridge_ping`, editor-mutation
allowance, Blueprint blocker count, and no-editor/no-PIE/no-provider/no-git
safety flags. Treat this as proof capture only; it should not ping the bridge,
execute queued actions, mutate Unreal, run PIE, call providers, or touch Git.

D189 adds masked provider-config review proof. `scripts/write_provider_config_review.py`
writes `Saved/ProviderConfigReview/last_review_receipt.json` with Tripo/Uthana
configured/source state, ignored secret-path policy, and repair commands. Use it
before wallet, allowance, spend, or generated asset submission work so the
cockpit can show whether provider auth has been reviewed without exposing raw
keys. The receipt does not store keys, call providers, check wallets, reserve
credits, record spend approval, mutate Unreal, touch Git, or authorize paid
generation by itself.

D196 threads masked provider-config review into the cockpit evidence ledger
flow. When an IDE companion ledger exists, `record_provider_config_review`
records the receipt path/state, provider names, configured/source booleans,
ignored-secret policy, save/proof tool hints, and no-raw-key/no-provider-call
flags through `skill_record_ide_companion_evidence`. Treat this as proof capture
only; it should not echo keys, call Tripo or Uthana, check wallets, reserve
credits, record spend approval, mutate Unreal, or touch Git.

D193 adds platform-stability review proof. `scripts/write_platform_stability_review.py`
writes `Saved/PlatformStabilityReview/last_review_receipt.json` with the local
preflight's platform-stability and WIP-promotion evidence: tool-count
reproducibility, test-lane separation, no-mutation receipt state, high-value
wrapper coverage, build wrapper health, bridge/chat receipt states, provider
review state, and dirty-promotion review state. Use it before claiming the IDE
companion is stable enough for promotion or release review. The receipt is
review evidence only; it does not write raw keys, call Tripo or Uthana, check
wallets, reserve credits, record spend approval, mutate Unreal, stage, commit,
clean, move branches, or authorize promotion to main.

D194 threads that receipt into the cockpit evidence ledger flow. When an IDE
companion ledger exists, `record_platform_stability_review` records the receipt
path/state, platform and WIP readiness flags, test-lane/no-mutation/wrapper/build
proof, and safety flags through `skill_record_ide_companion_evidence`. Keep this
as proof capture only; it should not replace the repair queue, bypass bridge or
provider gates, mutate Unreal, touch Git, or promote WIP to main.

D207 makes the dirty-promotion receipt more useful for review. The contract and
`Saved/DirtyPromotionReview/last_review_receipt.json` now include
promotion-batch policy, generated/local artifact policy, safe next steps, and
no-provider/no-editor flags. Use those fields to decide which dirty groups can
be reviewed together and which ignored/local artifacts should stay out of a
promotion batch. The receipt remains evidence only; it must not stage, commit,
clean, merge, move branches, mutate Unreal, call providers, check wallets, or
authorize promotion to main.

## D103 Blueprint Mutation Gate Review Workflow Target

The cockpit workflow rail now includes `review_blueprint_mutation_gate`, a
read-only Blueprint safety review action backed by `chat_get_cockpit_overview`.
Use it before any Blueprint graph, component, parent-class, construction
script, AnimGraph, Behavior Tree task, or generated Blueprint mutation.

The action carries `target_blueprint_mutation_context`: Blueprint mutation
readiness, missing and required gate previews, evidence requirements, selected
work-order template operation/compile/PIE/evidence counts, queued editor action
counts, bridge-blocked count, explicit `pre_read_required`,
`compile_plan_required`, `readback_plan_required`, `bridge_required`,
`requires_compile_readback`, and `stop_before_blueprint_mutation`.

Do not use Blueprint mutation review to mutate Blueprints, compile, save
assets, run queued actions, write ledger evidence, ping the bridge, or bypass
readiness gates. Use the review packet to decide whether the next step is
pre-read inspection, work-order repair, queue recompilation, evidence
recording, or waiting for bridge readiness.

## D104 Platform Preflight Gate Review Workflow Target

The cockpit workflow rail now includes `review_platform_preflight_gate`, a
read-only platform stability review action backed by `chat_get_cockpit_overview`.
Use it before risky work when the developer needs one compact view of tool
registry reproducibility, dirty-state risk, bridge reachability, chat cockpit
reachability, provider configuration presence, build-wrapper health, and the
readiness gates that decide whether Unreal/editor/provider work may proceed.

The action carries `target_platform_preflight_context`: preflight state,
editor/paid/chat readiness booleans, blocking gate preview, tool and recorded
tool counts, partial tool count, dirty/tracked/untracked counts, bridge/chat
booleans, provider source without secret values, paid and Blueprint missing
gate previews, compact test-lane separation counts, build-wrapper status, and
`stop_before_editor_provider_or_blueprint`.

Do not use platform preflight review to mutate Unreal, manually ping the
bridge, call providers, spend credits, write ledger evidence, compile, save
assets, run test lanes, or bypass readiness gates. Use the packet to decide
whether the next step is a no-mutation test, a readiness refresh, a bridge
startup, a provider/wallet evidence task, or a build/productization follow-up.

## D105 WIP Promotion Gate Review Workflow Target

The cockpit workflow rail now includes `review_wip_promotion_gate`, a
read-only promotion-readiness review action backed by `chat_get_cockpit_overview`.
Use it when experimental work on `wip` needs to be judged against the evidence
expected before moving toward `main`.

The action carries `target_wip_promotion_context`: source/stable branch policy,
ready and missing gate counts, gate previews, tool and recorded tool counts,
dirty/tracked/untracked counts, latest plugin build status, test-lane
violations, high-value wrapper coverage state, readiness state, and
`stop_before_branch_stage_commit_or_merge`.

Do not use WIP promotion review to create branches, stage files, commit, merge,
mutate Unreal, call providers, spend credits, run live lanes, or bypass
readiness gates. Use the packet to decide whether the next step is cleanup,
evidence grouping, no-mutation CI, BuildPlugin verification, live bridge proof,
or a deliberate human-led promotion plan.

## D106 Live Editor Bridge Gate Review Workflow Target

The cockpit workflow rail now includes `review_live_editor_bridge_gate`, a
read-only live-editor safety review action backed by `chat_get_cockpit_overview`.
Use it immediately before any queued editor action, PIE/runtime probe, viewport
capture, compile/readback pass, or other live Unreal work.

The action carries `target_live_editor_context`: bridge reachability from
platform preflight, editor mutation readiness, missing gate preview, queued and
executable action counts, bridge-blocked queue count, selected next action,
execution review state, after-execution evidence count, runtime review state,
runtime proof count, and `stop_before_editor_or_pie`.

Do not use live editor bridge review to mutate Unreal, manually ping the
bridge, run PIE, execute queued actions, compile, save assets, call providers,
spend credits, write ledger evidence, or bypass readiness gates. Use the
packet to decide whether the next step is bridge startup, queue review,
readiness refresh, runtime evidence planning, or waiting for operator intent.

## D107 Generated Asset Import Gate Review Workflow Target

The cockpit workflow rail now includes `review_generated_asset_import_gate`, a
read-only generated-asset import and quality review action backed by
`chat_get_cockpit_overview`. Use it after provider/placeholder planning and
before any editor import, placeholder replacement, material/collision pass,
viewport proof capture, or generated-asset evidence recording.

The action carries `target_generated_asset_import_context`: selected
import/quality-pending asset id, name, role, provider, current state, expected
and imported Unreal asset paths, placeholder state, quality gate/evidence
counts, missing editor gates, bridge requirement, required lifecycle/queue/
evidence tools, and `stop_before_import_or_quality_work`.

Do not use generated asset import review to import assets, mutate Unreal,
replace placeholders, run queued actions, call providers, spend credits,
compile, save assets, write ledger evidence, or bypass readiness gates. Use the
packet to decide whether the next step is bridge startup, queue compilation,
asset lifecycle repair, placeholder continuation, or quality evidence planning.

## D108 Generated Asset Lifecycle Gate Review Workflow Target

The cockpit workflow rail now includes `review_generated_asset_lifecycle_gate`,
a read-only generated-asset lifecycle completeness review action backed by
`chat_get_cockpit_overview`. Use it after a lifecycle manifest exists and
before provider submission, import planning, placeholder replacement, quality
work, or generated-asset evidence recording.

The action carries `target_generated_asset_lifecycle_context`: manifest count,
asset count, selected target asset, provider/import/quality/placeholder stage
counts, preferred provider preview, manifest path preview, missing lifecycle
stage preview, stop-condition count, future network/spend flags, lifecycle and
placeholder tool hints, and `stop_before_lifecycle_mutation`.

Do not use generated asset lifecycle review to call providers, spend credits,
import assets, mutate Unreal, replace placeholders, run queued actions, write
ledger evidence, or bypass readiness gates. Use the packet to decide whether
the next step is provider spend review, import gate review, placeholder
fallback, lifecycle manifest repair, or evidence planning.

## D153 Generated Asset Lifecycle Compile Workflow Target

The cockpit workflow rail now includes `compile_asset_lifecycle_manifest`, a
no-spend lifecycle compile/refresh action backed by
`skill_compile_ide_companion_asset_lifecycle_manifest`. Use it before raw JSON
handoffs when the current session plan or gameplay template already names
generated mesh or Uthana animation prompt requirements.

The action carries `target_asset_lifecycle_compile_context`: session-plan
presence, work-order template, planned mesh prompt count, planned Uthana
animation prompt count, estimated Uthana motion seconds, existing lifecycle
manifest counts, pending rows, future wallet/spend gates, and
`write_manifest_recommended`.

This target is compile guidance only. It does not call Tripo or Uthana, spend
credits, download files, import assets, mutate Unreal, run queued actions, or
record ledger evidence.

D154 threads the same target through the native compact workflow summary. When
this action is the best next workflow step, `Next:` can show the compile state,
plan state, mesh/animation prompt counts, manifest/pending counts, future gate
count, estimated Uthana seconds, and write-manifest hint without requiring the
developer to open raw lifecycle JSON.

## D155 Provider Spend Fallback Workflow Handoff

The provider spend review target now reports an explicit no-spend fallback path.
If paid generation is blocked and placeholders are available, inspect
`outputs.workflow_actions.review_provider_spend_gate.target_provider_spend_context.fallback_placeholder_available`
and then route to `compile_placeholder_manifest` before provider submission.

The context includes the fallback action id/label, placeholder compiler tool,
editor queue compiler tool, fallback reason, and now-vs-future spend/network/
editor requirements. This keeps paid-provider gates hard while still letting a
solo developer continue playable-slice proof with placeholders.

## D156 Placeholder Fallback Workflow Action

`continue_with_placeholder_fallback` is the direct no-spend action after D155.
It calls `skill_compile_ide_companion_placeholder_manifest` with the current
session plan and placeholder root, and it carries both
`target_provider_spend_context` and `target_placeholder_context`.

Use this action when blocked paid-provider gates should not stop playable-slice
proof. It compiles a placeholder manifest only; it must not submit provider
tasks, spend credits, call providers, import assets, mutate Unreal, queue editor
actions, or write ledger evidence.

## D109 Generated Asset Replacement Gate Review Workflow Target

The cockpit workflow rail now includes `review_generated_asset_replacement_gate`,
a read-only placeholder-to-generated asset replacement review action backed by
`chat_get_cockpit_overview`. Use it after lifecycle/import review and before
any editor action that swaps placeholder references for generated assets.

The action carries `target_generated_asset_replacement_context`: selected
asset id/name/role/provider, placeholder asset path, expected and imported
generated asset paths, replacement policy preview, placeholder count,
replacement-pending count, quality proof counts, missing editor gates, missing
replacement stages, `replacement_ready`, and
`stop_before_placeholder_replacement`.

Do not use generated asset replacement review to replace placeholders, mutate
Unreal, import assets, run queued actions, call providers, spend credits,
compile, save assets, write ledger evidence, or bypass readiness gates. Use
the packet to decide whether the next step is import gate review, quality proof
planning, bridge startup, queue compilation, or replacement evidence planning.

## D110 Generated Asset Provider Task/Download Gate Review Workflow Target

The cockpit workflow rail now includes
`review_generated_asset_provider_task_gate`, a read-only provider task and
download readiness review action backed by `chat_get_cockpit_overview`. Use it
after spend/provider review and before polling provider status, downloading
provider outputs, importing generated assets, or recording provider task
evidence.

The action carries `target_generated_asset_provider_task_context`: selected
asset id/name/role/provider, provider task status, task id, submit/status/
download/import tool names, expected/downloaded/imported asset paths, provider
pending and success counts, task-id missing count, download/import pending
counts, missing paid-provider gates, missing task/download stages,
`provider_task_ready`, and `stop_before_provider_task_or_download`.

Do not use provider task/download review to call providers, poll status,
download files, import assets, mutate Unreal, spend credits, run queued
actions, write ledger evidence, or bypass readiness gates. Use the packet to
decide whether the next step is spend review, status wait, download planning,
import gate review, or provider-task evidence planning.

## D111 Generated Asset Quality Proof Gate Review Workflow Target

The cockpit workflow rail now includes
`review_generated_asset_quality_proof_gate`, a read-only material, collision,
viewport, and ledger proof review action backed by `chat_get_cockpit_overview`.
Use it after import/provider-task review and before quality checks, viewport
capture, placeholder replacement, or generated-asset evidence recording.

The action carries `target_generated_asset_quality_proof_context`: selected
asset id/name/role/provider/state, expected and imported asset paths, quality
proof contract schema, required-after-import proof preview, quality gate
preview, quality gate/evidence counts, missing proof count, material/collision/
viewport/ledger proof booleans, missing editor gates, imported-asset
requirement, `quality_proof_ready`, and `stop_before_quality_proof_work`.

Do not use quality proof review to capture viewports, mutate Unreal, import
assets, replace placeholders, run queued actions, call providers, spend
credits, compile, save assets, write ledger evidence, or bypass readiness
gates. Use the packet to decide whether the next step is import review, bridge
startup, material/collision/viewport proof planning, or evidence planning.

## D112 Uthana Animation Provider Lifecycle Contract

Uthana is now represented as the provider-neutral animation and motion lane for
IDE companion sessions. Tripo remains the first mesh provider; Uthana is treated
as a separate motion provider for generated humanoid animation, retargeting, and
Unreal Animation Sequence handoff.

AI encounter session plans can include `generated_animation_prompts` with
provider `uthana`, task type `text_to_motion`, target skeleton, expected
animation content path, default character id, and estimated motion seconds. The
generated asset lifecycle manifest now carries `animation_assets` beside mesh
`assets`, with Uthana submit/download/import tool names, retarget/readback
requirements, AnimGraph or state-machine reference proof, PIE/viewport proof,
and ledger evidence requirements.

The cockpit workflow rail now includes
`review_generated_animation_lifecycle_gate`, a read-only Uthana motion review
action backed by `chat_get_cockpit_overview`. The action carries
`target_generated_animation_lifecycle_context`: selected animation id/name/role,
motion id, task status, target skeleton, expected import path, animation quality
proof contract schema, required-after-import proof preview, quality gate/evidence
counts, missing paid-provider gates, missing editor gates, missing animation
stages, `unreal_mcp_uthana_animation_usage_contract.v1` allowance/usage receipt
guidance, and `stop_before_animation_generation_or_import`.

Do not use generated animation lifecycle review to call Uthana, download files,
import animations, mutate Unreal, run queued actions, spend credits, compile,
save assets, write ledger evidence, or bypass readiness gates. Use the packet to
decide whether the next step is Uthana auth/quota setup, usage confirmation,
motion generation planning, animation import/retarget queueing, or runtime
evidence planning.

D208 threads the Uthana usage proof contract into generated-animation lifecycle,
queue/execution review, and evidence-recording metadata. The contract points at
`gen_uthana_get_account`, optional `gen_uthana_check_download_allowed`,
`Saved/PaidGenerationEvidence/last_review_receipt.json`, and the
`confirm_usage=True` field required for text-to-motion or download calls. It is
still review guidance only; it must not call Uthana, submit motions, download,
import, mutate Unreal, write ledgers, reserve credits, or spend.

## D113 Dual Provider Config And Secret Preservation

`gen_save_provider_config` can now manage both Tripo mesh-provider credentials
and Uthana animation-provider credentials. Store Uthana with
`uthana_api_key` plus `store_uthana_api_key=True`; clear it with
`clear_stored_uthana_api_key=True`. Store or clear Tripo with the existing
`tripo_api_key`, `store_api_key`, and `clear_stored_api_key` fields.

Both providers use ignored `Saved/MCPChat/secrets.json`. MCP JSON responses
report only configured/source/masked status, never raw secret values. The
native Generate Settings save path preserves existing Uthana secrets when
saving Tripo settings, and the compact auth line reports both provider sources
without adding another permanent HUD block.

## D114 Guarded Uthana Motion Task Tools

The Uthana lifecycle tool names in generated animation manifests now resolve to
public MCP tools. Use `gen_uthana_get_account` and
`gen_uthana_check_download_allowed` for allowance evidence before consuming
quota. Use `gen_uthana_text_to_motion`, `gen_uthana_video_to_motion`, and
`gen_uthana_download_motion` only after explicit `confirm_usage=True` approval.
Use `gen_uthana_get_job` to poll async video-to-motion jobs without downloading
or importing output. Use `gen_uthana_import_animation_to_project` only with a
downloaded FBX and a ready bridge ping; it still reports retarget readback,
AnimGraph or state-machine reference, PIE proof, and ledger evidence as
required follow-up gates.

Generated motion is not complete when the API returns a motion ID. Treat the ID
as provider evidence, the downloaded FBX/GLB/BVH as file evidence, the imported
Animation Sequence as editor evidence, and PIE plus ledger entries as gameplay
proof.

## D115 Generated Animation Evidence Compiler

Use `gen_compile_generated_animation_evidence` when a generated animation needs
to graduate from "provider task happened" to "gameplay-ready proof exists." The
compiler is offline and read-only: it consumes JSON from Uthana generation,
download allowance, download, import, retarget/readback, AnimGraph or
state-machine, PIE/runtime, and ledger steps, then emits a single
`unreal_mcp_generated_animation_evidence.v1` receipt.

Do not mark generated motion complete until the compiler reports
`proven=True`. Missing retarget/readback, AnimGraph reference, PIE proof,
ledger evidence, or human approval should keep the companion session in a
repair/evidence state instead of advancing the slice as playable.

## D116 Provider Config Gate Review Workflow Target

The cockpit workflow rail now includes `review_provider_config_gate`, a
read-only provider setup review action backed by `chat_get_cockpit_overview`.
Use it before wallet checks, allowance checks, spend approval, Tripo task
submission, or Uthana task submission when the developer needs to see whether
mesh and animation provider credentials are configured safely.

The action carries `target_provider_config_context`: Tripo and Uthana configured
booleans, provider source labels, provider config receipt path/state, repair
commands with `<TRIPO_API_KEY>` and `<UTHANA_API_KEY>` placeholders, ignored
secret-path policy, wallet/allowance tool hints, missing gate preview, and the
recommended next setup step.

Do not use provider config review to paste raw keys into chat, call providers,
check wallets, reserve credits, approve spend, mutate Unreal, run queued
actions, or write ledger evidence. Use the packet to decide whether to
configure Tripo, configure Uthana, write the provider config review receipt,
or move on to separate wallet/allowance and spend-confirmation evidence.

## D117 Gameplay Template Execution Readiness

`review_gameplay_template_plan.target_gameplay_template_context` now carries an
`execution_readiness` packet for the selected feature template. Use it to decide
whether the template is only reviewable, ready to queue editor work, or still
blocked by bridge, Blueprint pre-read, compile/readback, runtime proof, or
ledger evidence gates.

The packet reports `can_queue_editor_work`, `can_mark_feature_complete`,
bridge-required operation count, compile/readback counts, operation proof
contract count, runtime proof count, completion evidence count, before/after
proof previews, missing gate preview, queue/evidence tool hints, and
`stop_before_feature_complete`.

Do not use execution readiness to run queued work, mutate Blueprints, compile,
run PIE, write ledger evidence, call providers, spend credits, or mark a
feature complete. It is a cockpit review contract so a developer can see the
next safe step before pressing any execution control.

## D118 Repair Execution Readiness

`repair_failed_step.target_repair_review_context` now carries
`repair_execution_readiness`, a compact repair gate for the selected repair
hint. Use it to distinguish offline repair planning from live editor repair
application.

The packet reports whether a repair work order can be compiled, whether the
repair can be applied now, the selected repair id/phase, bridge and Blueprint
pre-read requirements, after-apply compile/readback/ledger proof, stop-if-missing
conditions, and the recommended next repair step.

Do not use repair execution readiness to ping the bridge, mutate Blueprints,
compile, run PIE, write ledger evidence, call providers, spend credits, or apply
the repair automatically. It is a review contract: compile a scoped repair work
order first, apply at most one repair attempt only after gates pass, then record
evidence before continuing.

## References

- Repo: `13_TOOL_EXPANSION_ROADMAP.md`
- Repo: `12_MCP_TOOL_USAGE_GUIDE.md`
- Repo: `18_PACKAGING_AND_OPTIMIZATION.md`
