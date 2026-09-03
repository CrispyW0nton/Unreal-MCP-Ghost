# Ultimate AI Unreal IDE Audit and Development Plan - 2026-06-14

## Goal

Make Unreal-MCP-Ghost the default solo-developer AI IDE inside Unreal Engine: a tool that can understand a project, generate/import assets, author gameplay systems, operate safely in-editor, verify runtime behavior, and hand back durable evidence instead of vague chat transcripts.

## Audit Snapshot

- Registered MCP tools: 667 across 47 modules.
- Inventory status: 529 live tools, 128 partial tools.
- Startup/profile health: static inventory builds in-process in about 75 ms median; subprocess inventory in about 301 ms median.
- C++ build health: `scripts/run_insanitii_clean_build_and_tripo_verify.ps1` succeeded against the Insanitii UE 5.6 project.
- Bridge route health: 381 C++ routed commands; 371 Python-referenced commands; 0 Python bridge calls missing C++ routes.
- Bridge wrapper gaps: 10 C++ routes are not referenced by Python; 0 are marked as needing Python wrappers and 0 remain in triage.
- Live editor readiness: `scripts/bridge_ping.py` currently fails against `127.0.0.1:55655`, so runtime/editor mutation is unavailable until Unreal Editor is running with the bridge.
- Test health: focused registry/chat/palette tests pass, and full `unittest discover` keeps `last_tool_count.txt` stable before and after the run.
- Worktree health: the repo is heavily dirty with many project artifacts, generated files, untracked tests, and local scripts. This increases release risk until changes are grouped, documented, and staged deliberately.
- Platform-stability update 2026-06-15 D121: `_build_plugin.bat` now defaults to `RunUAT BuildPlugin` for the repo-local UnrealMCP plugin and the no-mutation preflight resolves batch `%~dp0` wrapper defaults for project, plugin, and build-tool references, removing the stale CombatLevel project reference from the main build-wrapper path.
- Provider-neutral generation update 2026-06-15 D122: preflight and cockpit readiness now separate Tripo mesh spend readiness from Uthana paid-animation readiness through a dedicated `paid_animation_generation` policy row.

## Current Strengths

1. Breadth of Unreal coverage is already unusually strong: Blueprint, actor/editor, graph, UMG, AI, animation, data, materials, VFX, audio, save-game, networking, GAS, physics, procedural, source control, diagnostics, repair, project intelligence, and generative tools exist.
2. The bridge command registry is mostly coherent: every discovered Python bridge command has a C++ route.
3. The higher-level companion layer now has a useful spine: readiness, gameplay mechanic planning, session plan, status receipt, work order, evidence ledger, resume, dashboard, blocker resolution, placeholder manifest, and editor queue.
4. Build and static registry performance are healthy enough for iterative development.
5. The knowledge-base rule is clear and aligned with Unreal best practices: inspect before mutation, keep Blueprint graphs readable, prefer vertical-slice validation, and make AI systems observable through Blackboard/BT/EQS patterns.

## Top Risks

1. Registry hygiene must stay protected.
   - Full-suite discovery now keeps `last_tool_count.txt` stable, but future tool additions must update the count deliberately and keep import tests read-only.
   - This remains a release risk because the repo has many generated and experimental artifacts in the same worktree.

2. Live-editor verification is not always available.
   - Bridge ping currently fails when Unreal Editor is not running.
   - The tool can plan and queue work offline, but cannot prove editor mutations or PIE behavior without a running bridge.

3. Partial tool surface is still large.
   - 128 tools are marked partial.
   - Highest visible partial areas: AI, animation, materials, and Niagara.

4. Bridge coverage has shifted from wrapper gaps to maintenance policy.
   - The remaining unreferenced C++ routes are now aliases, legacy helpers, or game-specific recipes.
   - New native routes should be classified immediately as public wrappers, internal helpers, legacy routes, or skill recipes.

5. Large monolithic files increase maintenance risk.
   - `UnrealMCPExtendedCommands.cpp`: about 591 KB.
   - `editor_tools.py`: about 226 KB.
   - `UnrealMCPBlueprintNodeCommands.cpp`: about 214 KB.
   - `MCPChatPanel.cpp`: about 155 KB.
   - These should not block features, but they need boundaries, tests, and gradual extraction.

6. Product surface is still tool-first.
   - The repo has many tools, but the IDE experience should feel like guided workflows: diagnose, propose, preview, execute, verify, repair, and record.

## Definition of Done for "Ultimate AI Unreal IDE"

- A developer can open MCP Chat in Unreal and ask for a gameplay feature, asset, bug fix, or optimization pass.
- The system inspects the project before acting, presents a plan, identifies spend/editor risks, and queues or executes safe steps.
- Generated assets can be requested, tracked, imported, replaced with placeholders when blocked, and mapped back to gameplay use.
- Gameplay mechanics can be authored as Blueprint/C++/AI/HUD/save/input work with readable graph/component evidence.
- Every mutation has compile/readback evidence, rollback or repair guidance, and an evidence ledger.
- Runtime proof is captured through PIE logs, screenshots, actor state, and acceptance criteria.
- CI protects the tool registry, bridge command map, chat UI, docs, and high-order workflows.

## Roadmap

### Phase 0 - Stabilize The Platform

Priority: immediate.

Deliverables:

- Remove tracked-file writes from `test_import_tools.py`; replace the old WS-1g count audit with a read-only assertion or delete it in favor of `test_tool_count.py`.
- Done: add a no-mutation full-suite command documented in `docs/ci-smoke.md`; D31 adds the before/after `last_tool_count.txt` guard and static doc coverage.
- Done: D51 promotes the no-mutation full-suite guard into `scripts/run_no_mutation_unittest.py`, snapshotting every Git-tracked file before and after default offline unittest discovery so CI can catch any tracked-file mutation, not only tool-count baseline drift.
- Done: split offline, live-bridge, and paid-provider tests with clear filename conventions in `docs/ci-smoke.md`; D32 adds static coverage for the lane boundaries.
- Done: D52 adds `scripts/audit_test_lanes.py` so CI can enforce that live-bridge and paid-provider tests stay out of default offline `test_*.py` discovery by filename.
- Done: add a preflight script that reports Python version, tool count, dirty-state summary, bridge ping, SSE/chat status, Tripo config presence without exposing secrets, and last build status. D53 adds a structured `readiness_policy` for editor mutation, paid generation, Blueprint mutation, and chat cockpit gates so CI/editor consumers can see missing evidence without scraping prose.
- Done: D118 extends preflight build health so known build wrappers report missing `.uproject` or `Build.bat` references separately from stale last-build logs.
- Done: D119 promotes build-wrapper reference readiness into the preflight `platform_stability` policy and MCP Chat WIP promotion gate, so unresolved local build paths block stability review instead of hiding behind stale successful build logs.
- Done: D120 threads platform-stability/build-wrapper reference state into the native MCP Chat Platform Preflight and WIP Promotion summaries, keeping the clean HUD while making blocked local build paths visible from the editor workflow rail.
- Done: ignore local logs and generated run artifacts (`*.log`, `.mcp_artifacts/`, and `build_artifacts/`) so evidence/session output does not inflate release diffs.

Acceptance:

- `python -m unittest discover -s unreal_mcp_server/tests -p "test_*.py"` does not modify tracked files.
- Focused CI smoke passes from a clean checkout.
- Tool count remains 667 unless intentionally changed.

### Phase 1 - Close High-Value Bridge Wrapper Gaps

Priority: immediate after Phase 0.

Deliverables:

- Keep high-value route coverage closed and document the remaining non-wrapper routes:
  - internal aliases
  - legacy helpers
  - game-specific recipe routes
- Done: D76 adds `scripts/audit_high_value_wrapper_coverage.py` so the roadmap's named high-value wrappers are continuously checked for C++ routes, Python references, registered tool signatures, offline test evidence, and documentation evidence.
- Update `bridge_command_audit.py` recommendations as wrappers land.

Acceptance:

- Bridge audit shows 0 `needs_python_wrapper` routes and 0 `needs_triage` routes.
- Every new wrapper has an offline registration/schema test and a bridge command mapping assertion.

### Phase 2 - Make MCP Chat The IDE Cockpit

Priority: high.

Deliverables:

- Convert companion outputs into first-class chat panel views:
  - session dashboard cards;
  - blocker resolution cards;
  - queued editor action list;
  - evidence ledger timeline;
  - generated asset status/import map;
  - runtime verification checklist.
- Done: D35 adds read-only MCP Chat cockpit visibility for saved generated asset lifecycle manifests, including planned asset count, pending task count, placeholder mapping count, preferred provider, and preview rows.
- Done: D38 exposes latest feature-template work orders in the MCP Chat cockpit with compact counts and previews for graph/component operations, compile/readback checks, PIE validation, repair hints, and evidence requirements.
- Done: D39 adds an explicit MCP Chat workflow action rail for Start Companion Session, Check Readiness, Queue Editor Actions, Execute Next Safe Step, Record Evidence, and Repair Failed Step.
- Done: D40 adds a local MCP Chat session picker backed by `.mcp_artifacts/ide_companion_sessions`, aggregating ledgers, editor queues, and generated asset lifecycle manifests per companion session.
- Done: D41 adds MCP Chat blocker-resolution previews so the cockpit shows blocked gates, severity, recommended tools, fallback actions, and required evidence without opening raw JSON.
- Done: D42 adds a runtime verification checklist to the MCP Chat cockpit, surfacing PIE validation, compile/readback, evidence requirements, bridge-blocked state, and runtime proof previews from the latest feature-template work order.
- Done: D43 adds a repair-loop preview to the MCP Chat cockpit, surfacing bounded repair instructions, stop conditions, runtime state, compile/readback previews, evidence previews, and recommended repair/evidence tools.
- Done: D44 adds an evidence-recording checklist to the MCP Chat cockpit, turning blockers, queued editor evidence, runtime proof, repair hints, generated asset lifecycle manifests, and work-order requirements into recordable rows.
- Done: D45 adds a next-safe-step gate to the MCP Chat cockpit, making the first queued editor action, bridge-blocked state, blocking gates, execution policy, and after-execution evidence visible before any bridge mutation.
- Done: D46 adds failure triage to the MCP Chat cockpit, combining ledger failure events, blocked next-safe-step state, runtime verification blockers, and repair-loop hints into compact recovery items with recommended tools and evidence routing.
- Done: D47 threads next-safe-step and failure-triage summaries into the native Unreal MCP Chat panel's compact IDE Cockpit strip, keeping recovery state visible inside the editor without adding clutter or execution side effects.
- Done: D48 completes the native MCP Chat command-palette loop with guarded Execute Next Safe Step and Repair Failed Step entries that route through cockpit overview state instead of bypassing readiness gates.
- Done: D49 adds a generated-asset quality gate to the MCP Chat cockpit, surfacing provider-pending, import-pending, material/collision/viewport/ledger proof, ready, and placeholder counts from lifecycle manifests.
- Done: D50 threads the generated-asset quality gate into the native Unreal MCP Chat panel's compact recovery strip, keeping asset provider/import/quality blockers visible without adding another HUD block or execution side effects.
- Done: D54 adds a read-only MCP Chat `readiness_policy` packet and compact card so editor-mutation, paid-generation, and Blueprint-mutation gates remain visible in the cockpit with missing evidence requirements.
- Done: D55 threads the cockpit `readiness_policy` packet into the native Unreal MCP Chat recovery strip as a compact `Policy:` summary without adding another HUD block or execution side effects.
- Done: D56 adds a `record_readiness_policy` evidence row to the MCP Chat evidence-recording checklist so editor, paid-generation, and Blueprint policy gaps can be recorded before execution.
- Done: D57 threads the cockpit `evidence_recording` packet into the native Unreal MCP Chat Evidence line as a compact `Record:` summary and points the Record Evidence palette action at pending cockpit rows.
- Done: D58 adds a cockpit-selected `target_evidence_item` to the `record_evidence` workflow action, prioritizing pending readiness-policy evidence before raw checklist fallback.
- Done: D59 threads the selected `target_evidence_item` into the native Unreal MCP Chat `Record:` summary so the editor shows the next evidence type, state, and artifact count without another HUD block.
- Done: D60 makes the native Unreal MCP Chat `Next:` line prefer cockpit `workflow_actions`, prioritizing Record Evidence targets, safe execution, repair, queueing, readiness, and session start without invoking any action.
- Done: D61 adds `resume_companion_session` to cockpit `workflow_actions` and native `Next:` priority so existing ledgers can be resumed from the workflow rail before starting a new session.
- Done: D62 adds `show_companion_dashboard` to cockpit `workflow_actions` and native `Next:` priority so existing ledgers can route back to the dashboard surface without relying on legacy suggested-action text.
- Done: D63 adds `resolve_blockers` to cockpit `workflow_actions` and native `Next:` priority so active blocker gates can route directly into blocker-resolution planning before queueing more editor work.
- Done: D64 makes the native Resolve IDE Companion Blockers palette prompt cockpit-aware, preferring `outputs.workflow_actions.resolve_blockers`, `arguments.current_blockers`, and `outputs.blocker_resolutions` before pasted JSON fallback.
- Done: D65 adds a selected `target_blocker_resolution` plus `target_blocker` and `preferred_strategy` arguments to the `resolve_blockers` workflow action so the cockpit can guide agents to the first blocker to resolve without raw JSON hunting.
- Done: D66 threads `target_blocker_resolution` into the native compact `Next:` line when Resolve Blockers is selected, showing the target blocker, strategy, and recommended tool without adding HUD clutter.
- Done: D67 adds `target_queue_context` plus `target_phase` and `ledger_path` arguments to `queue_editor_actions`, and threads the queue target into the native compact `Next:` line when queue compilation is selected.
- Done: D68 adds `target_repair_context` to `repair_failed_step` and threads the selected repair hint into the native compact `Next:` line so repair planning starts from the current failure without HUD clutter.
- Done: D69 adds `target_execute_context` to `execute_next_safe_step` and threads the first queued action target into the native compact `Next:` line while preserving bridge/readiness gating.
- Done: D70 adds a compact native `Actions` launcher to the IDE Cockpit header, opening the command palette filtered to workflow commands without running tools, mutating Unreal, or adding a cluttered permanent button row.
- Done: D71 hardens the native `Actions` launcher by tagging common companion entries with an explicit `workflow` command-palette kind so Execute Next Safe Step and Repair Failed Step remain visible despite short labels.
- Done: D72 updates the native Queue Editor Actions, Execute Next Safe Step, and Repair Failed Step palette prompts to prefer selected cockpit `workflow_actions` targets before raw overview outputs or pasted JSON.
- Done: D73 makes native command-palette category filters exact for known kinds, keeping the cockpit `Actions` launcher focused on real workflow entries while preserving fuzzy search for ordinary terms.
- Done: D74 adds workflow-action total/enabled counts to the native `Actions` button and tooltip, giving a compact readiness cue without adding another HUD row or execution side effect.
- Done: D75 makes the native `Actions` button show `Actions (0)` when workflow actions exist but all are disabled or gated, keeping blocked workflow state visible without HUD clutter.
- Done: D77 adds a cockpit-selected `target_generated_asset_context` to the `resolve_generated_asset` workflow action and threads it into the native compact `Next:` line so generated-asset blockers route from the quality gate without raw lifecycle JSON.
- Done: D78 adds a dedicated native `Resolve Generated Asset` command-palette workflow entry so the cockpit-selected generated asset target is reachable from the compact `Actions` launcher without adding another HUD row.
- Done: D79 adds a `record_generated_asset_quality_gate` evidence row so generated-asset provider/import/quality blockers can be recorded against the selected asset, including next gate, manifest, import path, and quality proof hints.
- Done: D80 adds structured metadata to generated-asset evidence rows so Record Evidence workflows can use asset id, name, provider, state, paths, placeholder state, and quality proof counts without parsing artifact labels.
- Done: D81 adds `target_evidence_context` to the Record Evidence workflow action and teaches the native MCP Chat panel to prefer that compact context for `Record:` target summaries, including artifact previews and generated-asset metadata.
- Done: D82 adds a read-only `show_evidence_ledger` workflow action plus native command-palette entry so the cockpit can route directly into bounded ledger detail and artifact previews without raw JSON or another permanent HUD row.
- Done: D83 adds a read-only `execution_review` packet and `target_execution_review_context` for Execute Next Safe Step, surfacing blocker counts, after-execution evidence, and stop-after-one-action policy before any bridge mutation.
- Done: D84 adds a read-only `repair_review` packet and `target_repair_review_context` for Repair Failed Step, surfacing selected repair hints, recovery-signal counts, evidence previews, and stop-after-one-repair-attempt policy before any repair work order or editor mutation.
- Done: D85 adds a read-only `runtime_review` packet and `review_runtime_verification` workflow action, surfacing PIE step counts, proof item counts, recorded runtime evidence, and stop-after-runtime-probe policy before any PIE/runtime verification attempt.
- Done: D86 adds structured runtime-verification metadata to evidence rows plus a dedicated `record_runtime_evidence` workflow action, so PIE/log/screenshot/actor-state proof can be recorded or explained without parsing raw checklist JSON.
- Done: D87 adds structured queued-action metadata to editor-queue evidence rows plus a dedicated `record_queued_action_evidence` workflow action, so compile/readback proof after a queued step can be recorded or explained without parsing raw queue JSON.
- Done: D88 adds a dedicated `record_generated_asset_evidence` workflow action plus native command-palette summary, so provider/placeholder/import/quality proof for generated assets can be recorded or explained without submitting provider tasks, importing assets, or parsing raw lifecycle JSON.
- Done: D89 adds a read-only `review_generated_asset_gate` workflow action plus native command-palette summary, so provider/import/quality/placeholder counts and the selected generated asset can be inspected before resolving, importing, submitting, replacing, or recording.
- Done: D90 adds `target_readiness_policy_context` to `check_readiness` plus native command-palette summary, so editor/provider/Blueprint readiness gates can be inspected from the workflow rail before refreshing preflight or attempting mutation/spend.
- Done: D91 adds `target_resume_context` to `resume_companion_session` plus native command-palette summary, so the selected ledger's event count, completed phases, blockers, next phase/tool, and mutation stop policy are visible before resuming.
- Done: D92 adds `target_dashboard_context` to `show_companion_dashboard` plus native command-palette summary, so readiness, blockers, queues, evidence, generated assets, runtime, and repair states are visible before opening the dashboard.
- Done: D93 adds `target_start_context` to `start_companion_session` plus native command-palette summary, so startup can see existing ledger, readiness, queue, generated-asset, and stop-policy state before compiling a plan.
- Done: D94 adds `refresh_companion_status` with `target_status_context` plus native command-palette summary, so status receipts can refresh from ledger/readiness/evidence context without pasted JSON.
- Done: D95 adds `generate_work_order` with `target_work_order_context` plus native command-palette summary, so executable phase work orders can be compiled from session/status/readiness context before queueing editor actions.
- Done: D96 adds `compile_placeholder_manifest` with `target_placeholder_context` plus native command-palette summary, so no-spend placeholder fallback can be planned from generated-asset/blocker context before queueing editor actions.
- Done: D97 adds `review_editor_queue` with `target_queue_review_context` plus native command-palette summary, so queued editor actions, bridge blockers, next action, and evidence requirements can be inspected before queue recompilation or execution.
- Done: D98 adds `review_evidence_requirements` with `target_evidence_review_context` plus native command-palette summary, so pending, blocked, and recorded proof requirements can be inspected before ledger evidence is written.
- Done: D99 adds `review_provider_spend_gate` with `target_provider_spend_context` plus native command-palette summary, so provider credentials, wallet evidence, spend confirmation, fallback placeholders, and the selected provider-pending asset can be inspected before any paid provider task.
- Done: D100 adds `review_bridge_wrapper_coverage` with `target_bridge_wrapper_context` plus native command-palette summary, so high-value native bridge wrapper coverage, Python reachability, tests, docs, and source audit evidence are visible from the MCP Chat workflow rail before planning more wrapper work.
- Done: D101 adds `review_gameplay_template_plan` with `target_gameplay_template_context` plus native command-palette summary, so selected gameplay feature-template assets, graph operations, compile/PIE gates, evidence, ownership domains, and repair instructions can be inspected before queueing editor work.
- Done: D102 adds `review_test_lane_gates` with `target_test_lane_context` plus native command-palette summary, so offline/live-bridge/paid-provider test lane separation, default discovery safety, CI docs, and violation previews can be inspected before running risky checks.
- Done: D103 adds `review_blueprint_mutation_gate` with `target_blueprint_mutation_context` plus native command-palette summary, so bridge, Blueprint pre-read, compile-plan, readback-plan, queued action, and evidence gates can be inspected before any Blueprint graph or component mutation.
- Done: D104 adds `review_platform_preflight_gate` with `target_platform_preflight_context` plus native command-palette summary, so tool-count reproducibility, dirty-state risk, bridge/chat/provider/build status, paid/Blueprint missing gates, and stop-before-risky-work policy can be inspected from the workflow rail.
- Done: D105 adds `review_wip_promotion_gate` with `target_wip_promotion_context` plus native command-palette summary, so WIP-to-main readiness can be reviewed against registry, no-mutation CI, wrapper coverage, build, dirty-state, and cockpit reachability gates without creating branches, staging, committing, or merging.
- Done: D106 adds `review_live_editor_bridge_gate` with `target_live_editor_context` plus native command-palette summary, so bridge reachability, queued editor actions, runtime/PIE readiness, execution evidence, and stop-before-editor-or-PIE policy can be inspected before live Unreal work.
- Done: D107 adds `review_generated_asset_import_gate` with `target_generated_asset_import_context` plus native command-palette summary, so import/quality-pending generated assets, expected/imported `/Game` paths, placeholder state, quality proof counts, and bridge/editor gates can be inspected before import or quality work.
- Done: D108 adds `review_generated_asset_lifecycle_gate` with `target_generated_asset_lifecycle_context` plus native command-palette summary, so prompt/provider/task/placeholder/import/quality/evidence lifecycle completeness, preferred provider, manifest path, and stop conditions can be inspected before provider, import, or ledger work.
- Done: D109 adds `review_generated_asset_replacement_gate` with `target_generated_asset_replacement_context` plus native command-palette summary, so placeholder-to-generated asset paths, quality proof, editor readiness, missing replacement stages, and stop-before-placeholder-replacement policy can be inspected before any swap.
- Done: D110 adds `review_generated_asset_provider_task_gate` with `target_generated_asset_provider_task_context` plus native command-palette summary, so provider task status, task ids, status/download/import tools, missing paid gates, and download/import readiness can be inspected before polling, downloading, importing, or recording provider task evidence.
- Done: D111 adds `review_generated_asset_quality_proof_gate` with `target_generated_asset_quality_proof_context` plus native command-palette summary, so material, collision, viewport, ledger proof, imported asset readiness, and missing editor gates can be inspected before quality work or evidence recording.
- Done: D142 adds generated-asset quality proof contracts so mesh load/readback, material slot, collision/readability, viewport/thumbnail, and ledger evidence are structured before placeholder replacement.
- Done: D112 adds Uthana as the provider-neutral animation/motion lane with generated animation prompts, lifecycle manifest `animation_assets`, cockpit `review_generated_animation_lifecycle_gate`, and native command-palette summary, so text-to-motion, download/import, retarget, AnimGraph, PIE, and ledger proof can be reviewed before Uthana or Unreal work.
- Done: D143 adds generated-animation quality proof contracts so Animation Sequence readback, target skeleton/retarget evidence, AnimGraph/state-machine references, PIE/viewport playback proof, and ledger evidence are structured before animation replacement or gameplay proof.
- Done: D113 adds dual Tripo/Uthana provider config handling and native secret preservation, so the Generate Settings path can save Tripo settings without erasing stored Uthana credentials and the compact auth line reports both provider sources without exposing secrets.
- Done: D114 registers guarded Uthana motion lifecycle tools for account allowance, text-to-motion, motion metadata, download-allowed checks, authenticated FBX/GLB/BVH downloads, and bridge-gated FBX import without cluttering the HUD or bypassing usage/editor gates.
- Done: D115 adds a generated-animation evidence compiler so MCP Chat and companion sessions can distinguish provider/file/editor evidence from final gameplay proof before advancing Uthana motion work.
- Done: D116 threads generated-animation evidence into MCP Chat workflow routing with compile and record actions plus structured Uthana animation metadata, so the cockpit can guide proof capture without raw lifecycle JSON, provider calls, editor mutation, or HUD clutter.
- Done: D117 teaches the native MCP Chat Actions/Next surfaces to summarize and prompt the generated-animation compile/record evidence routes, keeping Uthana proof work discoverable without adding another permanent HUD row.
- Add explicit buttons for common workflows:
  - Start Companion Session;
  - Check Readiness;
  - Queue Editor Actions;
  - Execute Next Safe Step;
  - Record Evidence;
  - Repair Failed Step.
- Done: D40 adds a local session picker for `.mcp_artifacts/ide_companion_sessions`.
- Keep the UI dense and editor-native: no marketing hero layout, no decorative cards inside cards, and no hidden critical state.

Acceptance:

- A developer can resume a previous companion session from the editor without pasting JSON manually.
- Queue execution state is visible before any bridge mutation.
- Failed tool cards route naturally into repair and evidence recording.

### Phase 3 - Asset Generation To Gameplay Integration

Priority: high.

Deliverables:

- Formalize the Tripo lifecycle:
  - prompt manifest;
  - credit/readiness gate;
  - task submit;
  - status wait;
  - download/import;
  - placeholder replacement;
  - material/LOD/collision pass;
  - evidence record.
- Add provider-neutral generative interfaces so Tripo is one backend, not the only architecture.
- Done: add `skill_compile_ide_companion_asset_lifecycle_manifest` as a provider-neutral generated asset lifecycle manifest for prompt, wallet/spend gate, task, import, placeholder replacement, quality proof, and ledger evidence tracking.
- Done: D112 adds Uthana as the first provider-neutral generated animation backend contract, keeping motion prompts, auth/quota gates, FBX/GLB/BVH download/import, retarget proof, AnimGraph references, PIE proof, and ledger evidence separate from Tripo mesh generation.
- Done: D113 extends provider config to store, clear, and report Tripo mesh and Uthana animation credentials independently through ignored local secrets or environment variables, keeping raw keys out of MCP responses and docs.
- Done: D114 turns the Uthana lifecycle contract into callable guarded MCP tools while preserving explicit usage confirmation, quota evidence, bridge-ping import gating, and post-import animation proof requirements.
- Done: D115 adds `gen_compile_generated_animation_evidence` as the no-spend receipt for Uthana motion lifecycles, requiring motion/download/import, retarget/readback, AnimGraph or state-machine reference, PIE proof, ledger evidence, and approval before generated animation is considered proven.
- Done: D116 exposes that receipt through MCP Chat `compile_generated_animation_evidence` and `record_generated_animation_evidence` actions with compact generated-animation evidence context, preserving no-spend/no-editor-mutation defaults.
- Done: D117 adds native MCP Chat command-palette prompts and compact Next-line summaries for the generated-animation compile/record routes, so animation evidence can be followed from the editor without raw JSON.
- Add asset quality gates:
  - import path exists;
  - mesh loads;
  - material slot count reported;
  - collision/readability check;
  - thumbnail or viewport screenshot.
- Add automatic fallback from empty wallet or failed generation to placeholder manifest and editor queue.

Acceptance:

- A generated asset can move from prompt to imported `/Game/...` asset with ledger proof.
- A placeholder can be replaced by a generated asset without losing the original evidence trail.

### Phase 4 - Gameplay Feature Authoring Workflows

Priority: high.

Deliverables:

- Promote mechanic planning into executable feature templates:
  - interactable object;
  - pickup/resource loop;
  - enemy patrol/chase/attack;
  - objective HUD update;
  - save/load state;
  - input action and cooldown ability;
  - replicated actor variable/RPC sample.
- Done: D36 adds `unreal_mcp_gameplay_feature_template.v1` packets to the gameplay mechanic planner, covering the common template families with ownership split, graph/component operations, compile/readback checks, PIE validation, repair instructions, evidence requirements, and stop conditions.
- Done: D37 threads those feature-template packets into IDE companion work orders for mechanic design, editor implementation, and runtime verification, making graph/component operations, PIE validation, and repair instructions visible at execution time.
- Done: D123 adds `editor_operation_checklist` rows to gameplay feature templates and work orders so template operations carry ids, operation types, candidate MCP tools, bridge gates, compile/readback requirements, and ledger evidence type for future editor-queue execution.
- Done: D124 exposes `editor_operation_checklist` metadata through MCP Chat work-order, gameplay-template review, Blueprint mutation, queue target, feature-work card, and native summary surfaces so queue-planning operation counts, candidate tools, and bridge/compile/readback gates can be reviewed before editor mutation.
- Done: D144 adds the composite `ai_patrol_objective_asset_swap_slice` gameplay template, combining patrol/chase AI, objective HUD updates, placeholder fallback, generated-asset replacement requirements, PIE proof, and ledger evidence in one vertical-slice contract.
- Done: D145 surfaces generated-asset replacement operation counts, previews, tool hints, and proof-contract counts in gameplay-template review context and the native compact summary without adding HUD clutter.
- Done: D146 threads generated-asset replacement gate counts, previews, tool hints, proof-contract counts, and no-bypass policy into queue and execution review so placeholder-to-generated swaps stay lifecycle/quality/ledger gated at execution time.
- Done: D147 threads Uthana/generated-animation target, skeleton, missing-stage, proof-contract, next-safe-action, and no-bypass policy into queue and execution review so animation import, retarget, AnimGraph, PIE, and ledger proof stay visible at execution time.
- Done: D148 threads generated-content gates into editor queue review so already-compiled queues keep placeholder swap and Uthana animation proof policies visible before Execute Next Safe Step.
- Done: D149 adds a `performance_optimization_pass` gameplay feature template so optimization/FPS/hitch briefs produce baseline profiling, scoped-change, compile/readback, before/after runtime proof, and ledger evidence requirements.
- Done: D150 adds a `bug_fix_repair_pass` gameplay feature template so bug/fix/broken/crash/compile-error/regression briefs produce failure-context capture, reproduction evidence, one scoped fix, compile/readback, PIE/log/viewport proof, and ledgered regression evidence without scheduling generated-asset spend.
- Done: D151 threads Uthana `generated_animation_prompts` into gameplay mechanic plans, feature-template asset lists, animation system hooks, companion sessions, and lifecycle manifests so AI/combat/ability motion work is planned with auth, usage, retarget/readback, AnimGraph, PIE, and ledger gates before provider or editor execution.
- Done: D152 surfaces mechanic-level Uthana generated-animation prompt counts, previews, provider/skeleton/tool/proof hints, estimated seconds, and no-bypass policy through MCP Chat work-order, gameplay-template, queue, next-safe-step, execution-review, Feature Work card, and native compact summary surfaces without adding HUD clutter.
- Done: D153 adds a cockpit `compile_asset_lifecycle_manifest` workflow action and context so agents can compile or refresh the provider-neutral Tripo mesh and Uthana animation lifecycle manifest from current session/work-order generated prompt counts before asking for pasted lifecycle JSON.
- Done: D154 threads that lifecycle compile target into the native MCP Chat compact `Next:` summary so mesh/Uthana prompt counts, manifest counts, pending rows, future gates, estimated motion seconds, and write-manifest guidance are visible without another HUD block.
- Done: D155 adds explicit provider-spend fallback metadata so blocked wallet/spend gates can route to placeholder manifest compilation and editor queue planning without provider calls, pasted JSON, or HUD clutter.
- Done: D156 adds `continue_with_placeholder_fallback` as the direct cockpit workflow action for blocked paid-generation fallback, using the existing placeholder manifest compiler and native compact `Next:` route without provider calls or a new HUD block.
- Done: D157 removes the deprecated `UImage::SetBrushSize` path from native UMG image property handling, preserves the existing `BrushSize` command-facing property, and adds a source guard so UE plugin builds stay clean on current image sizing APIs.
- Done: D158 replaces monolithic `Json.h` usage in public plugin headers with explicit JSON object/value includes and adds a source guard so current UE plugin builds stop repeating the monolithic-header warning.
- Done: D159 removes the deprecated `StructUtils` plugin/module dependency from the UnrealMCP descriptor/build rules while preserving `FInstancedStruct` motion and Chooser authoring through UE 5.6 `CoreUObject`.
- Done: D160 adds read-only AutomationTool warning classification to the platform preflight and MCP Chat platform/WIP contexts so a successful plugin build can still surface toolchain-only versus repo-facing warnings without cluttering the HUD or blocking safe continuation.
- Done: D161 makes schema/signature coverage a first-class high-value wrapper audit result and threads aggregate schema proof into MCP Chat/native wrapper summaries, matching the roadmap requirement that every new wrapper carry route, registration, schema, test, and documentation evidence.
- Done: D125 adds WIP/main branch-policy evidence to the no-mutation preflight, platform-stability policy, MCP Chat platform review, WIP promotion context, native compact summaries, and CI docs so active development stays on `wip` and promotion to `main` remains review-only.
- Done: D126 adds a guarded `paid_provider_generative_smoke.py` lane for no-spend Tripo wallet and Uthana allowance checks, with explicit provider-network/no-spend approval flags and lane-audit/doc coverage proving paid-provider checks stay outside default offline discovery.
- Done: D127 adds generated-animation `next_safe_action` routing to MCP Chat so Uthana motion work can move from usage gates to confirmation, import readiness, evidence compilation, and ledger recording without provider calls, editor mutation, or HUD clutter.
- Done: D128 surfaces generated-animation `next_safe_action` in the native MCP Chat compact action summary and command-palette guidance, so Uthana motion next steps are visible in-editor without a new permanent HUD block.
- Done: D129 updates cockpit blocker-resolution routing for current chat, Tripo, Uthana, wallet/spend, and Blueprint evidence gates, giving Resolve Blockers accurate read-only next steps before bridge/provider/editor work.
- Done: D130 threads selected blocker required-evidence and offline-continuation policy into the native Resolve Blockers summary/prompt, making recovery guidance visible without adding a HUD panel or executing unsafe work.
- Done: D131 adds `chat_server_reachable` to top-level IDE preflight `blocking_gates` when MCP Chat is down, aligning CLI/CI blockers with the existing `readiness_policy.chat_cockpit` row for cockpit recovery.
- Done: D132 promotes `wallet_evidence_recorded` and `spend_confirmation_recorded` into top-level IDE preflight `blocking_gates` when paid Tripo/Uthana evidence is missing, aligning CLI/CI/native blockers with the paid mesh and paid animation readiness rows.
- Done: D133 marks Uthana lifecycle task types without registered public MCP submit tools as `unsupported_task_type`, while carrying planned tool names and unsupported reasons into MCP Chat summaries instead of suggesting dead actions.
- Done: D134 surfaces unsupported provider task counts/previews in the existing MCP Chat Generated Assets card and overview warnings, keeping planned Uthana wrapper gaps visible without adding HUD clutter.
- Done: D135 adds completion contracts to gameplay feature templates and surfaces proof-gate counts/previews in MCP Chat Feature Work summaries, making "playable" depend on asset, compile/readback, PIE, repair, and ledger evidence rather than planning alone.
- Done: D136 adds `record_feature_completion_contract` to MCP Chat evidence recording and workflow actions so gameplay completion contracts can be reviewed and written to the IDE companion ledger after their underlying proof rows are gathered.
- Done: D137 threads `record_feature_completion_contract` into the native MCP Chat command palette and compact `Next:` summary, keeping completion proof visible in-editor without adding HUD clutter or authorizing unsafe work.
- Done: D138 adds a masked native `UTHANA_API_KEY` field to Generate Settings and saves the canonical key only to ignored `Saved/MCPChat/secrets.json`, reducing animation-provider setup friction without exposing secrets or calling Uthana.
- Done: D139 updates Resolve Blockers to route missing Tripo/Uthana credential gates through the native masked Generate Settings fields first, with env/config-tool fallbacks and masked evidence requirements.
- Done: D140 adds a reviewed queued-action executor contract to MCP Chat so Execute Next Safe Step carries pre-execution checks, exactly-one-action policy, and post-execution evidence requirements before any editor mutation.
- Done: D141 adds per-operation proof contracts to gameplay feature templates and surfaces compact proof counts/previews in MCP Chat before queued editor work.
- Done: D38 surfaces those latest feature-template work-order packets in MCP Chat so implementation, verification, and repair instructions are visible without opening raw ledger JSON.
- Each template should produce:
  - asset list;
  - Blueprint/C++ ownership split;
  - graph/component operations;
  - compile/readback checks;
  - PIE validation steps;
  - repair hints.
- Prefer Blackboard and Behavior Tree state for AI rather than scattered Blueprint booleans.

Acceptance:

- A solo developer can ask for one feature and receive a working vertical slice with compile and runtime evidence.

### Phase 5 - Autonomous Verification And Repair Loop

Priority: high.

Deliverables:

- Extend the evidence system into an execution journal:
  - before snapshot;
  - planned mutation;
  - tool result;
  - compile result;
  - graph/component readback;
  - PIE probe;
  - final status.
- Add "repair until green" bounded loops for common failures:
  - missing pins;
  - broken exec chains;
  - compile errors;
  - missing asset references;
  - invalid widget bindings;
  - AI blackboard/BT mismatch.
- Require stop conditions and maximum attempts for autonomous repair.

Acceptance:

- Failed Blueprint/UMG/AI steps can produce a focused repair work order instead of a generic failure.

### Phase 6 - Refactor For Maintainability

Priority: medium, continuous.

Deliverables:

- Extract large C++ command files by domain when adding related work:
  - Blueprint graph primitives;
  - AI/BT/EQS;
  - animation/AnimGraph;
  - editor asset/level tools;
  - technical art/VFX/materials.
- Extract `MCPChatPanel.cpp` into smaller UI/state/service files:
  - conversation view;
  - command palette;
  - tool card rendering;
  - companion dashboard;
  - transport/client state.
- Extract oversized Python modules only when there is a test-backed domain boundary.

Acceptance:

- New features land in domain-owned files with focused tests.
- No further growth of the largest files without an explicit reason.

### Phase 7 - Productization And Distribution

Priority: medium.

Deliverables:

- One-command install/sync for the plugin into a target project.
- Versioned compatibility matrix for UE 5.6 and plugin modules.
- Start/stop scripts for SSE server and chat agent.
- In-editor diagnostics page:
  - MCP server reachable;
  - bridge reachable;
  - tool count;
  - provider config;
  - last error;
  - log path.
- Release checklist:
  - clean tool inventory;
  - bridge audit;
  - focused unit tests;
  - C++ build;
  - sample vertical slice proof.

Acceptance:

- A new project can install, connect, run a companion session, and produce evidence in under 30 minutes.

## Initial Tickets

1. Replace the mutating WS-1g test in `test_import_tools.py` with a read-only test or remove it.
2. Done: add `scripts/audit_ide_companion_readiness.py` that prints the repo/build/bridge/provider/chat readiness summary. D28 extends its build section with the latest AutomationTool plugin build status, exit code, and summary lines; D29 adds dirty-state risk, tracked/untracked counts, status buckets, and generated/local artifact counts; D30 adds Python runtime version, executable, platform, and virtualenv context.
3. Done: add wrappers for `set_behavior_tree_blackboard` and `bt_get_info`.
4. Done: add wrappers for `add_construction_script_node` and `set_blueprint_parent_class`.
5. Done: add wrappers/direct native routing for `add_blueprint_function_with_pins`, `add_arithmetic_operator_node`, `add_relational_operator_node`, and `set_spawn_actor_class`.
6. Done: add wrappers for `connect_anim_graph_nodes` and `add_sequence_player_node`.
7. Done: add wrapper for `add_niagara_component` and promote Niagara from partial to closer-to-live coverage.
8. Done: route `add_get_random_reachable_point_node`, `add_finish_execute_node`, and `add_clear_blackboard_value_node` through native AI task graph commands.
9. Done: route `add_map_variable`, `add_open_level_node`, and `reconstruct_blueprint_node` through native data/flow/repair commands.
10. Done: add `scripts/audit_high_value_wrapper_coverage.py` and `test_phase1_high_value_wrapper_coverage.py` to keep the named high-value bridge wrappers covered by route, registry/schema, test, and documentation evidence.
11. In progress: add MCP Chat queue visibility backed by the D20 queue JSON. D23 adds a compact read-only cockpit strip with queue state, and D24 adds a bounded queued-action preview; a fuller reviewed executor is still needed before running queued steps from the editor.
12. In progress: add MCP Chat evidence visibility backed by the IDE companion ledger. D25 adds a compact read-only evidence timeline preview, D26 adds bounded artifact hints for recent evidence events, and D27 adds a read-only ledger detail packet with bounded artifact drilldown; a richer native editor viewer is still needed.
13. Add a provider-neutral generated asset lifecycle manifest.
14. Done: add one complete vertical-slice template: "AI patrol enemy with objective HUD and placeholder/generated asset swap."

## Operating Rules For The Next Phase

- Work on the `wip` branch for experimental development and move changes to `main` only after they are stable and verified.
- Do not create additional branches unless the project owner explicitly asks for one.
- No paid provider call without explicit spend confirmation and wallet evidence.
- No editor mutation without a successful bridge ping.
- No Blueprint mutation without pre-read, compile, and readback.
- No new high-order feature without evidence ledger integration.
- No tracked file should be modified by a test.
- Keep generated project artifacts out of generic repo history unless they are intentional fixtures.
- Keep the MCP Chat/HUD surface professional, clean, and uncluttered; favor dense actionable state over decorative or noisy panels.
