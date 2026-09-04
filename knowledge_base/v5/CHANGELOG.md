# Knowledge Base v5 Changelog
> Append-only log for Workstream A knowledge-base changes.
> Agents can read this file at `kb://v5/CHANGELOG.md` to see what changed since a prior session.

---

## 2026-09-03

### D.316 - Repository promotion hardening

- Reconciled the tracked registry baseline and active setup guidance with the verified 713-tool, 51-module inventory; all tool modules now have category metadata.
- Hardened HTTP startup to loopback-only operation, made bridge authentication consistent across standalone clients, isolated automatic chat replies by named session, and moved blocking provider work off the async event loop.
- Restored the plugin descriptor to Unreal Engine 5.6, aligned active bridge guidance on port `55655`, and added regression coverage for the corrected contracts.

## 2026-06-16

### D.315 - Uthana character-target pipeline

- Added guarded Uthana character-target wrappers for the corrected Tripo-to-Uthana flow: upload a Tripo/exported `.fbx`, `.glb`, or `.gltf` with `gen_uthana_create_character`, inspect it with `gen_uthana_get_character`, then generate locomotion with `gen_uthana_create_locomotion`.
- Updated Uthana text/video motion wrappers so `character_id` is sent to Uthana during motion creation rather than merely recorded for download/import bookkeeping.
- Updated the generative pipeline runbook to make the intended order explicit: Tripo character FBX, Uthana auto-rigged character target, Uthana motions on that character, Unreal import/readback/AnimGraph/PIE proof.

### D.314 - HUD Blueprint mutation proof state

- Added compact Blueprint mutation evidence state to the clean cockpit HUD summary: inspect/pre-read, compile-plan, and readback-plan recorded/missing counts, next missing gate, next local receipt handoff, receipt path, safety label, and no-mutation/no-compile/no-save/no-PIE flags.
- Updated the native Unreal MCP Chat panel to parse this bounded proof state and render it as a conditional `BP:` recovery segment, reinforcing that Blueprint work must stop before mutation until inspect/compile/readback evidence is ready.
- Kept the change passive: it does not ping the bridge, mutate Blueprint assets, compile, save, run PIE, call providers, approve usage/spend, stage, commit, branch, merge, clean, or delete files.

### D.313 - HUD handoff safety label

- Added `next_operator_handoff_safety_label` and bounded no-provider/no-spend/no-editor/no-git/no-stage/no-commit flags to the clean cockpit HUD summary.
- Updated the native Unreal MCP Chat panel to include the safety label in the compact `Handoff:` summary while keeping full command text behind drill-down/copy affordances.
- Kept the change passive: it does not execute receipt scripts, mutate Unreal, call the bridge, start PIE, call providers, approve usage/spend, stage, commit, branch, merge, clean, or delete files.

### D.312 - Native next operator handoff summary

- Updated the native Unreal MCP Chat panel to parse the clean HUD packet's next operator handoff label, ID, command kind, and receipt path.
- Added a compact `Handoff:` suffix to the native Next line so local receipt/test actions are visible from the editor without rendering full command strings in the primary HUD.
- Kept the change passive: it does not execute receipt scripts, mutate Unreal, call the bridge, start PIE, call providers, approve usage/spend, stage, commit, branch, merge, clean, or delete files.

### D.311 - Native Uthana HUD render signal

- Updated the native Unreal MCP Chat panel HUD parser to consume the clean HUD packet's generated-animation provider, target animation, next safe action, and next usage handoff ID.
- Added a conditional compact `Anim:` segment to the native HUD line so Uthana lifecycle state is visible only when generated-animation work exists, preserving the clean default HUD density.
- Kept the change passive: it does not call Uthana, check allowance, submit tasks, download/import animations, mutate Unreal, approve usage, spend credits, stage, commit, branch, merge, clean, or delete files.

### D.310 - Uthana lifecycle HUD signal

- Added bounded generated-animation fields to `unreal_mcp_chat_cockpit_hud_summary.v1`, including the Uthana provider, target animation, next animation-safe action, usage receipt path, and next usage handoff ID.
- Updated the compact HUD generation card to show useful animation lifecycle state without exposing raw provider commands in the primary HUD strip.
- Kept the change passive: it does not call Uthana, check allowance, submit tasks, download/import animations, mutate Unreal, approve usage, spend credits, stage, commit, branch, merge, clean, or delete files.

### D.309 - HUD next operator handoff

- Added the readiness repair queue's selected `next_operator_command_handoff` to `unreal_mcp_chat_cockpit_hud_summary.v1` so the native HUD can show the safest local receipt/test action when editor execution is blocked.
- The compact HUD now prefers a non-mutating local handoff over a blocked queued editor action, while keeping the full command in structured drill-down fields for copy/action UI.
- Kept the change passive: it does not run receipt scripts, mutate Unreal, call the bridge, start PIE, call providers, spend credits, stage, commit, branch, merge, clean, or delete files.

### D.308 - Native cockpit HUD summary rendering

- Updated the Unreal MCP Chat panel to parse `unreal_mcp_chat_cockpit_hud_summary.v1` and render a compact HUD strip before the detailed cockpit lines.
- The native panel now prefers bounded readiness, feature, next-step, generation, evidence, and blocker-overflow summaries while leaving detailed cards and workflow actions available through existing drill-down controls.
- Kept the change passive: it does not mutate Unreal assets, call the bridge, start PIE, call providers, spend credits, stage, commit, branch, merge, clean, or delete files.

### D.307 - Clean cockpit HUD summary contract

- Added `unreal_mcp_chat_cockpit_hud_summary.v1` to MCP Chat cockpit overview output as a bounded native-HUD render contract.
- The HUD summary exposes six compact cards for session, readiness, feature work, next safe step, generation, and evidence while keeping detailed cards, workflow actions, and JSON-heavy proof data behind drill-down sources.
- Kept the change passive and clean: it does not mutate Unreal, call providers, spend credits, start PIE, stage, commit, branch, merge, clean, or delete files.

### D.306 - Provider config review command handoff

- Added a structured `write_provider_config_review_receipt` handoff so preflight, platform stability receipts, MCP Chat platform views, provider gate views, and provider-config evidence contexts can surface the masked provider review command directly.
- Marked the handoff as a local receipt action only: no raw keys, no provider call, no wallet check, no credit reservation, no task submission, no download/import, no editor mutation, no spend, and no Git mutation.
- Kept the change passive; it does not configure Tripo or Uthana secrets, call either provider, approve spend or usage, mutate Unreal, stage, commit, branch, merge, clean, or delete files.

### D.305 - Bridge ping live-validation handoff

- Added a structured `verify_unreal_bridge_ping` handoff for the live bridge receipt so preflight, MCP Chat platform views, live-editor gate views, and bridge evidence contexts can render the bridge ping as a clear cockpit action.
- Marked the handoff as live-bridge/editor-required evidence while preserving the hard safety contract: no editor mutation, no PIE, no provider call, no spend, no Git mutation, and no task submission.
- Kept WIP promotion blocked until the existing human approval gate is recorded; this change only improves bridge-gate visibility.

### D.304 - No-mutation test lane command handoff

- Added a passive no-mutation unittest command handoff to preflight and MCP Chat test-lane/platform contexts so the HUD can offer a clean local validation action for `Saved\NoMutationTest\last_run_receipt.json`.
- Threaded the handoff through platform-stability receipt snapshots and parser coverage while keeping the no-mutation lane separate from bridge, provider, Blueprint, and Git approval.
- Kept the change passive: it does not connect to Unreal, call providers, submit tasks, spend credits, mutate assets, stage, commit, branch, merge, clean, or delete files.

### D.303 - Bridge wrapper coverage command handoff

- Added passive operator command handoffs to the high-value bridge wrapper coverage audit so MCP Chat/HUD surfaces can offer one-click local validation for the JSON audit and offline wrapper test lane.
- Threaded those handoffs through preflight, platform stability receipt snapshots, and MCP Chat platform/wrapper contexts while preserving the existing no-bridge/no-editor/no-provider/no-git safety contract.
- Kept the change passive: it does not connect to Unreal, mutate assets, compile or save Blueprints, call providers, spend credits, stage, commit, branch, merge, clean, or delete files.

### D.302 - Uthana animation usage handoff

- Added structured Uthana usage command handoffs to generated-animation lifecycle contexts so MCP Chat/HUD surfaces can present separate local receipt actions for masked allowance evidence and explicit usage approval.
- Threaded the current next Uthana receipt handoff through queue, workflow, and generated-animation evidence contexts so animation generation blockers can be resolved from the cockpit without pasting raw command templates.
- Kept the change passive: it does not call Uthana, submit tasks, download motion files, import animations, mutate Unreal, approve usage, stage, commit, branch, merge, clean, or delete files.

### D.301 - Dirty promotion approval-only gate

- Added approval-only pending metadata for dirty-promotion target review so preflight and MCP Chat can distinguish "all review evidence recorded" from "explicit human approval still required."
- Threaded the single human-approval command handoff through the dirty receipt, preflight repair queue, platform-stability receipt, WIP-promotion context, and evidence-recording contexts while keeping the generic next action focused on that approval gate only when it is the sole missing target item.
- Kept the change passive: it does not record approval, stage, commit, clean, delete, branch, merge, promote to `main`, mutate Unreal, call providers, check wallets, reserve credits, approve spend, or run editor actions.

### D.300 - Dirty promotion focused-test handoff

- Added a structured no-git-mutation focused-test command handoff for the current dirty-promotion target batch, so cockpit UI can present validation commands separately from receipt-recording commands.
- Threaded the handoff through the dirty-promotion receipt, preflight parser, readiness repair queue, platform-stability receipt, MCP Chat WIP-promotion context, dirty evidence context, and platform review context.
- Kept the change passive: it does not stage, commit, clean, delete, branch, merge, promote to `main`, mutate Unreal, call providers, check wallets, reserve credits, approve spend, or run editor actions.

### D.299 - Blueprint evidence operator command handoff

- Added a structured three-command Blueprint mutation evidence handoff for cockpit UI consumers: record target pre-read evidence, record the compile plan, then record the graph/component readback plan.
- Threaded the handoff through the Blueprint evidence receipt, preflight parser, readiness repair queue, platform-stability receipt, MCP Chat platform context, Blueprint mutation context, and platform evidence artifact checklist.
- Kept the change passive: it does not ping the bridge, mutate Blueprint assets, compile, save, run PIE, call providers, spend credits, stage, commit, branch, merge, clean, or delete files.

### D.298 - Platform Blueprint evidence dashboard summary

- Threaded Blueprint mutation evidence receipt state into the platform-stability receipt and MCP Chat platform evidence artifacts, including pre-read, compile-plan, readback-plan, receipt path, required command, and no-mutation flags.
- Kept the bridge gate hard: this only records passive evidence state and does not authorize Blueprint mutation, compile, save, PIE, provider calls, spending, staging, committing, branching, merging, cleaning, or deletion.

### D.297 - Blueprint mutation evidence receipt

- Added an ignored Blueprint mutation evidence receipt for recording pre-read proof, compile-plan proof, and readback-plan proof in separate passive steps before any graph or component write.
- Threaded the receipt state, recorded booleans, path, required command, and command templates through the preflight repair queue and MCP Chat Blueprint mutation gate.
- Kept the hard bridge gate intact and the change passive: it does not ping the bridge, mutate Blueprint assets, compile, save, run PIE, call providers, spend credits, stage, commit, branch, merge, clean, or delete files.

### D.296 - Dirty promotion target evidence merge

- Changed the dirty-promotion receipt writer to preserve target evidence only when the dirty worktree signature and target group still match, so cockpit handoffs can record owner/source, intent, tests, artifact policy, and tracked-diff review in separate steps without losing earlier fields.
- Added `--reset-target-evidence` as the explicit escape hatch for clearing prior target evidence, plus cockpit/preflight/platform-stability metadata that reports the merge policy, whether previous evidence was merged, and whether reset was requested.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, stage, commit, branch, merge, clean, delete files, or promote anything to `main`.

### D.295 - Paid evidence receipt merge handoffs

- Changed the paid-generation evidence receipt writer to preserve existing ignored receipt evidence unless `--reset-evidence` is explicitly passed, so recording Tripo wallet proof and Uthana allowance proof through separate cockpit handoffs no longer overwrites the other provider's state.
- Added named no-spend handoff flags for `--record-masked-tripo-wallet-evidence`, `--record-masked-uthana-allowance-evidence`, and `--record-explicit-spend-and-usage-approval`, plus a summary guard that rejects raw provider-key-like values.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

## 2026-06-15

### D.294 - Platform paid evidence dashboard summary

- Threaded compact paid-generation evidence state into the platform-stability receipt and MCP Chat platform context, including Tripo wallet evidence, Uthana allowance evidence, explicit spend/usage approval, and provider-specific handoff IDs.
- Added the paid evidence summary to platform-stability evidence artifacts so the dashboard can show paid-provider readiness without opening raw preflight JSON.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.293 - Paid evidence artifact checklist split

- Added provider-specific paid evidence command templates and handoff IDs to the MCP Chat evidence-recording artifact checklist.
- Preserved separate Tripo wallet and Uthana allowance proof in workflow action arguments so ledger recording does not collapse animation allowance evidence into an opaque wallet step.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.292 - Provider-specific paid evidence actions

- Split the paid-generation evidence handoff into separate Tripo wallet evidence, Uthana allowance evidence, and explicit spend/usage approval actions so cockpit UI can make animation allowance work first-class.
- Added provider-specific receipt command templates while preserving the combined receipt template and hard no-provider/no-spend/no-Unreal/no-Git safety flags.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.291 - Unified next repair command handoff

- Promoted dirty-review target commands into the generic `next_operator_command_handoff` so cockpit UI can render the next repair action rail without special-casing dirty promotion.
- Threaded the fallback through preflight and MCP Chat readiness-repair contexts while preserving the target-specific dirty review fields.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.290 - Paid evidence operator command handoff

- Added a structured two-command paid-generation evidence handoff for cockpit UI consumers: record masked Tripo/Uthana wallet and allowance evidence first, then record explicit Tripo spend and Uthana usage approval.
- Threaded the handoff through preflight, readiness repair actions, provider spend context, platform preflight context, and record-evidence context.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.289 - Dirty review operator command handoff

- Added a structured two-command dirty-review handoff for cockpit UI consumers: record target evidence first, then record explicit human approval only when approval exists.
- Threaded the handoff through preflight repair queues, dirty review receipts, platform-stability receipts, WIP promotion context, and record-evidence context.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.288 - Dirty review command templates

- Threaded placeholder-safe dirty review command templates through the preflight repair queue, MCP Chat evidence context, and WIP promotion context.
- Split the base evidence command from the human-approval command so `--target-human-approval-recorded` appears only in the explicit approval template.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.287 - Dirty review evidence recording

- Extended `scripts/write_dirty_promotion_review.py` with optional target-batch evidence flags for owner/source, promotion intent, focused test results, artifact policy, tracked diff review, and explicit human approval.
- Threaded recorded target evidence status through preflight, platform-stability receipts, MCP Chat repair context, WIP promotion context, and CI smoke documentation.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.286 - Dirty review decision prompts

- Added owner/source, promotion-intent, focused-test, human-approval, artifact-policy, and tracked-diff decision prompts to dirty-promotion review batches.
- Threaded the target prompt preview through the dirty receipt, repair queue, WIP promotion context, record-evidence context, CLI output, and CI smoke contract.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.285 - Dirty receipt CLI target scope preview

- Extended `scripts/write_dirty_promotion_review.py` output with the current target group's scope, tracked/untracked counts, and sample path preview.
- Updated CI smoke docs and static preflight coverage so the WIP-promotion repair command shows scope, files, evidence, and focused tests in one passive console read.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.284 - Dirty receipt CLI target checklist

- Extended `scripts/write_dirty_promotion_review.py` output with the current target group's missing evidence, required evidence, focused test count, and focused test preview.
- Updated CI smoke docs and static preflight coverage so the next WIP-promotion repair command is self-guiding without opening the receipt JSON.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.283 - Dirty repair required evidence handoff

- Threaded the current dirty-promotion target's required-evidence preview into the readiness repair action and MCP Chat repair-queue context.
- Added chat coverage proving the main repair queue shows the dirty target's required proof beside missing evidence, focused tests, and promotion-after-receipt refusal.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.282 - Platform paid-animation usage guard preview

- Threaded Uthana no-spend checks, explicit usage evidence, placeholder fallback reason, and no-editor/no-ledger flags into the broader platform paid-generation contract.
- Added chat coverage proving the main platform/provider spend surfaces show Uthana account, job, and download allowance review before any paid animation task can be treated as safe.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.281 - Uthana usage contract evidence preview

- Threaded no-spend Uthana allowance checks, explicit usage approval evidence, placeholder fallback, and no-ledger/no-editor safety flags into the paid-generation evidence target context.
- Updated the provider-spend evidence contract so Uthana motion work exposes account, job, and download-allowance checks before any paid text-to-motion task or replacement workflow.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.280 - Runtime proof prerequisite preview

- Threaded runtime proof `required_before` prerequisites through work-order summaries, runtime verification checklists, runtime review contexts, and runtime evidence metadata.
- Added chat coverage proving runtime review can show prerequisite proof such as bridge reachability and editor operation readback before PIE/runtime evidence is attempted.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.279 - Blueprint repair review steps

- Added bounded review-step previews to the existing MCP Chat Blueprint mutation repair sequence so the first safe action explains the read-only inspection path before any graph or component write.
- Threaded the next Blueprint repair action review steps into the Blueprint gate context, keeping pre-read, compile-plan, and readback-plan guidance inside the existing card.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.278 - Blueprint repair sequence cockpit proof

- Threaded the readiness repair queue into the existing MCP Chat Blueprint mutation gate so the card shows the ordered Blueprint repair sequence: pre-read evidence, compile plan, and readback plan.
- Added compact Blueprint repair action previews with gate, action id, recommended tool, bridge/editor requirements, evidence preview, and no-mutation flags, without adding another HUD surface.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.277 - Dirty-promotion required evidence preview

- Threaded the target dirty-promotion required-evidence preview through MCP Chat WIP-promotion context, recordable evidence metadata, and the record-evidence target context.
- Added chat coverage proving the cockpit shows both missing evidence and required evidence for the current dirty-review target while preserving the no-promotion-after-receipt state.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.276 - Dirty-promotion evidence target handoff

- Updated the `record_dirty_promotion_review` evidence item to prefer the top-level dirty-promotion contract target fields for target group, scope, missing evidence, focused tests, sample preview, source, and promotion-allowed state.
- Added chat coverage so ledger handoff metadata stays aligned with the WIP-promotion card and still refuses promotion after writing the passive review receipt.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.275 - Dirty-promotion receipt target contract

- Lifted the current dirty-promotion review target onto the top-level dirty-promotion contract, including target group, scope, missing evidence, focused tests, sample preview, source, and promotion-allowed state.
- Updated MCP Chat WIP-promotion context to prefer the contract target fields so the cockpit can show the current receipt target without parsing nested receipt JSON.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.274 - Readiness repair queue dirty target proof

- Flattened the next dirty-promotion target review group, missing evidence, focused test preview, sample preview, and promotion-allowed flag onto the top-level readiness repair queue summary.
- Added preflight coverage so MCP Chat and CI consumers can show the next WIP-promotion review target without digging through nested action JSON or mutating Git state.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.273 - Readiness card Blueprint proof summary

- Added compact Blueprint mutation proof details to the existing MCP Chat readiness-policy card, including selected template, target phase, editor operation counts, bridge/compile/readback operation counts, queued action count, required pre-read/compile/readback flags, and proof previews.
- Reused the existing readiness card to keep the HUD professional and uncluttered while making Blueprint mutation blockers actionable from the main cockpit.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.272 - Wrapper audit self-describing status proof

- Extended the high-value bridge wrapper coverage audit JSON with direct `state`, `status`, command preview, failing capability preview, audit-tool provenance, bridge-registry provenance, and no-mutation/no-provider safety flags.
- Threaded the self-describing status and safety fields through IDE companion preflight, with offline test coverage so CI, preflight, and MCP Chat can consume wrapper status without inferring those fields from the capability table.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.271 - Generated animation cockpit card proof

- Added compact Uthana generated-animation target and next-safe-action proof to the existing MCP Chat generated-assets card, including target motion metadata, candidate tool, missing stage previews, editor gate previews, and paid-generation receipt guidance.
- Kept the HUD clean by reusing the existing generated-assets surface instead of adding a separate animation card.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.270 - Editor queue card feature-template proof

- Added compact gameplay feature-template next-operation proof to the MCP Chat editor queue card, including template identity, operation id/type, tool candidates, and required proof previews.
- Reused the existing editor queue card so the IDE cockpit can show the actionable gameplay operation without adding another dashboard surface.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.269 - Queued action feature-template evidence context

- Threaded gameplay feature-template operation proof from editor queue receipts into MCP Chat queue summaries and queued-action evidence contexts.
- Extended queued-action evidence to include the template name, next operation id/type, tool candidates, required-before/after proof, and stop-if-missing guidance for ledger recording.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.268 - Gameplay template operation queue proof

- Extended IDE companion editor queue receipts with the selected gameplay feature template, next editor operation, tool candidates, and proof-before/proof-after stop conditions.
- Added a dedicated MCP Chat workflow action for queueing the reviewed gameplay template operation through the existing bridge-gated editor queue compiler, without executing Unreal work.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.267 - Gameplay template next-operation cockpit proof

- Added a compact next-editor-operation summary to gameplay feature work orders, including operation id/type, tool preview, bridge/compile/readback flags, and proof-before/proof-after stop conditions.
- Threaded that summary through MCP Chat gameplay template execution readiness and the feature-work cockpit card so the editor can show one clean next action instead of only aggregate counts.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.266 - Platform receipt repair queue proof

- Extended platform-stability receipts with a compact readiness repair queue summary, including action count, recommended next repair, next gate/tool flags, and a bounded action preview.
- Threaded the repair summary through preflight receipt parsing and MCP Chat platform-stability evidence contexts, including the record-platform-review workflow target.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.265 - Platform receipt blocking gate proof

- Extended platform-stability receipts with `blocking_gate_count` plus the bounded `blocking_gate_preview` already produced from preflight, so a ready platform review can still explain unresolved editor, paid-provider, WIP-promotion, and Blueprint gates.
- Threaded the blocking-gate proof through preflight receipt parsing and MCP Chat platform-stability evidence contexts, including the record-platform-review workflow target.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.264 - Blueprint mutation top-level readiness gates

- Added top-level `ready_for_blueprint_mutation` to `scripts/audit_ide_companion_readiness.py` so Blueprint write readiness is visible beside editor, paid generation, platform, and WIP-promotion readiness.
- Promoted Blueprint pre-read, compile-plan, and readback-plan blockers into top-level `blocking_gates` plus explicit non-mutating repair queue actions, keeping bridge proof ahead of any Blueprint pre-read.
- Threaded the new readiness field into MCP Chat platform context and documented the contract in CI smoke notes.

### D.263 - Platform receipt registry count proof

- Extended `scripts/write_platform_stability_review.py` so platform-stability receipts include `recorded_tool_count` and `partial_tool_count` alongside the existing tool registry proof.
- Threaded the registry count aliases through preflight receipt parsing and MCP Chat platform-stability evidence contexts, including the record-platform-review workflow target.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.262 - Preflight tool-count aliases

- Added top-level `tool_count`, `recorded_tool_count`, `partial_tool_count`, and `tool_registry_reproducible` aliases to `scripts/audit_ide_companion_readiness.py` so cockpit/CI consumers can read registry health without re-deriving it from nested inventory fields.
- Updated preflight coverage and CI smoke docs to keep the flat aliases tied to the canonical `tool_inventory` packet.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.261 - Platform review dirty freshness proof

- Threaded dirty-promotion receipt freshness into `scripts/write_platform_stability_review.py` so platform-stability receipts preserve whether the dirty review matched the current worktree signature.
- Extended preflight parsing and MCP Chat platform-stability evidence contexts with dirty-receipt current/stale/signature-match fields, without adding a new HUD surface.
- Kept the review passive: it does not stage, commit, clean, delete, branch, merge, promote to main, mutate Unreal, call providers, check wallets, reserve credits, approve spend, run PIE, or execute queued editor actions.

### D.260 - Dirty promotion receipt freshness

- Added a stable dirty-worktree signature to the IDE companion preflight and dirty-promotion review receipt so WIP-promotion evidence can prove it matches the current dirty state.
- Preflight now marks legacy or mismatched dirty-promotion receipts as `stale` and exposes receipt-current/signature-match fields through the repair queue plus MCP Chat platform/WIP/evidence contexts.
- Kept the guard passive: it does not stage, commit, clean, delete, branch, merge, promote to main, mutate Unreal, call providers, check wallets, reserve credits, approve spend, run PIE, or execute queued editor actions.

### D.259 - Behavior Tree task graph wrapper audit gate

- Promoted `add_get_random_reachable_point_node`, `add_finish_execute_node`, and `add_clear_blackboard_value_node` into the high-value bridge wrapper coverage audit as the `behavior_tree_task_graph_primitives` capability.
- Updated preflight/test expectations so platform stability now proves 10/10 roadmap wrapper capability families and 14 command signatures before WIP promotion can be considered stable.
- Kept the change passive: it does not call Unreal, mutate editor assets, call providers, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.258 - No-spend Uthana job smoke lane

- Extended the manual paid-provider smoke with optional `UTHANA_SMOKE_JOB_ID` support so an existing Uthana async job can be polled through `gen_uthana_get_job` as no-spend provider evidence.
- Updated the test-lane audit, preflight no-spend tool summary, and CI smoke docs so job polling remains opt-in, outside default discovery, and separate from Uthana video upload/download/import actions.
- Kept the lane passive: it does not call Tripo or Uthana submit tools, upload files, download files, import animations, mutate Unreal, check wallets outside the opt-in lane, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.257 - Generated animation evidence action arguments

- Expanded the MCP Chat `compile_generated_animation_evidence` workflow action with explicit captured-proof argument slots, including `job_result_json` for Uthana video-to-motion job polling output.
- Pinned chat coverage so the workflow action continues to expose text/job provider result, download, import, PIE, and other proof JSON slots without adding another HUD block.
- Kept the change passive: it does not call Tripo or Uthana, upload files, download files, import animations, mutate Unreal, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.256 - Video job result animation evidence

- Extended `gen_compile_generated_animation_evidence` with optional `job_result_json` so `gen_uthana_get_job` output can provide video-to-motion provider task evidence and finished motion ids.
- Added coverage for finished video jobs and still-running jobs; unfinished jobs now route the evidence next action back to `gen_uthana_get_job` instead of text-to-motion submission.
- Kept the compiler passive: it does not call Tripo or Uthana, upload files, download files, import animations, mutate Unreal, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.255 - Task-aware Uthana video next action

- Made generated-animation next-safe-action guidance task-aware so supported `video_to_motion` routes to `gen_uthana_video_to_motion` and the `gen_uthana_get_job` follow-up instead of text-to-motion defaults.
- Preserved optional `video_file` / `reference_video_file` metadata in lifecycle manifests and cockpit summaries; missing clips now block locally as `attach_uthana_video_reference` before any provider-network or usage-confirmation step.
- Kept the change passive: it does not call Tripo or Uthana, upload files, download files, import animations, mutate Unreal, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.254 - Guarded Uthana video-to-motion tools

- Added guarded public MCP tools for Uthana video-to-motion upload and async job polling, using the documented multipart `create_video_to_motion` flow and `job(job_id)` status query without running provider calls in tests.
- Updated generated animation lifecycle manifests so `video_to_motion` now routes to `gen_uthana_video_to_motion` plus `gen_uthana_get_job` instead of remaining an unsupported planned tool.
- Synced the tracked MCP tool count to 667 for the two intentionally added Uthana public tools.
- Kept the change gated: no upload happens without `confirm_usage=True`; this work did not call Tripo or Uthana, download files, import animations, mutate Unreal, check wallets, reserve credits, approve spend, run PIE, stage, commit, branch, merge, clean, or delete files.

### D.253 - Uthana unsupported task lifecycle blocker

- Threaded unsupported Uthana task metadata into the generated-animation lifecycle gate so planned capabilities without public MCP submit tools block as provider-wrapper gaps instead of looking like ordinary paid usage gates.
- Added next-safe-action coverage for `implement_uthana_submit_tool_wrapper`, including planned submit tool, public-tool availability, unsupported reason, and no-provider/no-download/no-import/no-editor safety flags.
- Kept the change passive: it does not stage, commit, clean, delete, branch, merge, promote to main, mutate Unreal, call Tripo or Uthana, check wallets, reserve credits, confirm spend, run PIE, or execute queued editor actions.

### D.252 - High-value wrapper roadmap proof

- Added explicit roadmap-priority counts, covered/missing counts, command totals, and bounded previews to the high-value wrapper audit so the named Unreal IDE wrapper priorities can be verified without parsing the capability table.
- Threaded the same passive proof fields through readiness preflight and MCP Chat wrapper contexts, preserving the existing clean HUD shape while making wrapper coverage easier to audit.
- Kept the change passive: it does not stage, commit, clean, delete, branch, merge, promote to main, mutate Unreal, call Tripo or Uthana, check wallets, reserve credits, confirm spend, run PIE, or execute queued editor actions.

### D.251 - Native WIP promotion target hint

- Added the compact dirty review target fields to the WIP promotion context and surfaced the target group in the native MCP Chat panel's existing WIP promotion summary line.
- Pinned backend and native static coverage so the HUD can show `target project_knowledge` style guidance without adding a new row or requiring JSON drill-down.
- Kept the change passive: it does not stage, commit, clean, delete, branch, merge, promote to main, mutate Unreal, call Tripo or Uthana, check wallets, reserve credits, confirm spend, run PIE, or execute queued editor actions.

### D.250 - Platform stability chat dirty target context

- Threaded the platform-stability receipt's compact dirty target-review fields into MCP Chat platform context, recordable platform-stability metadata, and the bounded platform-stability workflow target context.
- Pinned chat coverage proving the platform review action can render the next WIP-promotion group, missing evidence, focused tests, samples, and no-promotion-after-receipt state without exposing the separate dirty-promotion evidence block.
- Kept the change passive: it does not stage, commit, clean, delete, branch, merge, promote to main, mutate Unreal, call Tripo or Uthana, check wallets, reserve credits, confirm spend, run PIE, or execute queued editor actions.

### D.249 - Platform stability dirty target snapshot

- Added compact dirty target-review fields to the ignored platform-stability receipt so the platform proof artifact carries the next WIP-promotion repair group, missing evidence, focused tests, samples, and promotion-after-receipt state.
- Threaded the new platform receipt fields through the preflight parser and CI smoke docs, including `PLATFORM_STABILITY_DIRTY_TARGET_REVIEW=...`, so clean HUD panels can render WIP risk from one platform receipt without parsing the full dirty matrix.
- Kept the change passive: it does not stage, commit, clean, delete, branch, merge, promote to main, mutate Unreal, call Tripo or Uthana, check wallets, reserve credits, confirm spend, run PIE, or execute queued editor actions.

### D.248 - Dirty promotion receipt target summary

- Added compact target-review fields to the ignored dirty-promotion receipt so WIP promotion review can show the next dirty group, scope, missing evidence, focused tests, sample paths, and promotion-after-receipt state without parsing the full matrix.
- Threaded the new receipt fields through the preflight parser and CI smoke docs, including `DIRTY_PROMOTION_TARGET_REVIEW=...`, so MCP Chat and platform checks share the same clean review contract.
- Kept the change passive: it does not stage, commit, clean, delete, branch, merge, promote to main, mutate Unreal, call Tripo or Uthana, check wallets, reserve credits, confirm spend, run PIE, or execute queued editor actions.

### D.247 - Generated asset quality evidence safety context

- Added explicit generated-asset quality safety flags to `record_generated_asset_quality_gate` metadata and its bounded target context so MCP Chat can show provider/import/replacement proof requirements without implying the record action can call providers, download/import assets, or mutate Unreal.
- Pinned workflow coverage proving generated-asset quality evidence remains import/quality-pass gated and requires bridge plus quality evidence before replacement, while preserving no-provider-call, no-task-submission, no-download, no-import, no-editor-mutation, and no-git-mutation flags.
- Kept the change passive: it does not call Tripo or Uthana, submit tasks, download files, import assets, mutate Unreal, launch PIE, ping the bridge, check wallets, reserve credits, confirm spend, write ledgers, stage, commit, branch, merge, clean, or delete files.

### D.246 - Feature completion evidence safety context

- Added explicit completion safety flags to `record_feature_completion_contract` metadata and its bounded target context so MCP Chat can show completion proof requirements without implying the feature may be marked done automatically.
- Pinned workflow coverage proving completion remains disallowed until all proof gates and required evidence are reviewed, with no-auto-complete, no-editor-mutation, no-PIE, no-provider-call, and no-git-mutation flags preserved.
- Kept the change passive: it does not mark features complete, launch PIE, mutate Unreal, execute queued editor actions, call Tripo or Uthana, check wallets, reserve credits, confirm spend, write ledgers, stage, commit, branch, merge, clean, or delete files.

### D.245 - Queued action evidence safety context

- Added explicit queued-action safety flags to `record_editor_queue_*` metadata and its bounded `queued_action` target context so MCP Chat can show queued editor proof requirements without implying the action may execute.
- Pinned workflow coverage proving blocked queued-action evidence remains gated on a successful bridge ping before execution and carries no-auto-execute, no-editor-mutation, no-PIE, no-provider-call, and no-git-mutation flags.
- Kept the change passive: it does not execute queued editor actions, ping the bridge, mutate Unreal, launch PIE, call Tripo or Uthana, check wallets, reserve credits, confirm spend, write ledgers, stage, commit, branch, merge, clean, or delete files.

### D.244 - Runtime verification evidence safety context

- Added explicit runtime-proof safety flags to `record_runtime_verification` metadata and its bounded target context so MCP Chat can show that recording runtime evidence does not itself run PIE, mutate the editor, call providers, or touch git.
- Pinned workflow coverage proving blocked runtime evidence remains gated on a successful bridge ping before any runtime probe while still exposing compile, PIE, and proof requirements for the clean HUD.
- Kept the change passive: it does not launch PIE, ping the bridge, execute queued editor actions, mutate Unreal, call Tripo or Uthana, check wallets, reserve credits, confirm spend, write ledgers, stage, commit, branch, merge, clean, or delete files.

### D.243 - Readiness policy target context

- Added a bounded `readiness_policy` target context to recordable evidence actions so MCP Chat can render editor, paid mesh, Uthana animation, Blueprint, and WIP policy blockers/evidence previews without parsing generic metadata.
- Pinned direct target-context coverage proving readiness-policy evidence exposes only readiness-policy context and not repair, dirty, generated, paid, bridge, provider, chat, platform, runtime, queue, or feature-completion blocks.
- Kept the change passive: it does not run review scripts, write ledgers, ping the bridge, call Tripo or Uthana, check wallets, reserve credits, confirm spend, stage, commit, branch, merge, clean, delete files, mutate Unreal, or run PIE.

### D.242 - Platform stability review target context

- Added a bounded `platform_stability_review` target context to recordable evidence actions so MCP Chat can render platform readiness, WIP-promotion pressure, tool registry reproducibility, test-lane state, no-mutation snapshot proof, build status, and wrapper health without parsing generic metadata.
- Pinned cockpit coverage proving platform-stability actions expose only platform proof context, keeping readiness repair, dirty-promotion, generated asset, animation, paid-provider, bridge, provider-config, chat-start, runtime, queued-action, and feature-completion blocks out of the stability proof row.
- Kept the change passive: it does not run review scripts, write ledgers, ping the bridge, start or stop servers, kill ports, call Tripo or Uthana, check wallets, reserve credits, confirm spend, stage, commit, branch, merge, clean, delete files, mutate Unreal, or run PIE.

### D.241 - Chat cockpit startup target context

- Added a bounded `chat_cockpit_start_receipt` target context to recordable evidence actions so MCP Chat can render chat readiness, TCP/HTTP health, startup receipt path, proof command, and no-process-start/no-port-kill safety flags without parsing generic metadata.
- Pinned cockpit coverage proving chat-start actions expose only chat startup context, keeping readiness repair, dirty-promotion, generated asset, animation, paid-provider, bridge, provider-config, runtime, queued-action, and feature-completion blocks out of the chat proof row.
- Kept the change passive: it does not start or stop servers, kill ports, ping the bridge, call Tripo or Uthana, check wallets, reserve credits, confirm spend, run review scripts, write ledgers, stage, commit, branch, merge, clean, delete files, mutate Unreal, or run PIE.

### D.240 - Provider config review target context

- Added a bounded `provider_config_review` target context to recordable evidence actions so MCP Chat can render masked Tripo and Uthana configuration state, source labels, ignored-secret policy, save/proof tools, and no-leak/no-provider-call flags without parsing generic metadata.
- Pinned cockpit coverage proving provider-config actions expose only provider-config context, keeping readiness repair, dirty-promotion, generated asset, animation, paid-provider, bridge, runtime, queued-action, and feature-completion blocks out of the masked provider proof row.
- Kept the change passive: it does not call Tripo or Uthana, check wallets, reserve credits, confirm spend, ping the bridge, run review scripts, write ledgers, stage, commit, branch, merge, clean, delete files, mutate Unreal, or run PIE.

### D.239 - Bridge ping receipt target context

- Added a bounded `bridge_ping_receipt` target context to recordable evidence actions so MCP Chat can render bridge receipt state, endpoint, required proof command, editor-mutation readiness, Blueprint gate pressure, and stop-before-mutation flags without parsing generic metadata.
- Pinned cockpit coverage proving bridge receipt actions expose only bridge context, keeping readiness repair, dirty-promotion, generated asset, animation, paid-provider, runtime, queued-action, and feature-completion blocks out of the bridge proof row.
- Kept the change passive: it does not ping the bridge, run review scripts, write ledgers, stage, commit, branch, merge, clean, delete files, mutate Unreal, run PIE, call Tripo or Uthana, check wallets, reserve credits, or spend.

### D.238 - Readiness repair queue evidence target context

- Added a bounded `readiness_repair_queue` target context to recordable evidence actions so MCP Chat can render the next manual repair action, blocking gate, policy area, recommended contract/tool, proof preview, and safety flags without parsing generic metadata.
- Pinned cockpit coverage proving the generic record-evidence action exposes only repair-queue context when that is the selected evidence target, keeping generated asset, animation, paid-provider, runtime, queued-action, feature-completion, and dirty-promotion blocks out of the first action.
- Kept the cleanup passive: it does not run review scripts, ping the bridge, write ledgers, stage, commit, branch, merge, clean, delete files, mutate Unreal, run PIE, call Tripo or Uthana, check wallets, reserve credits, or spend.

### D.237 - Evidence target context domain gating

- Made optional evidence target context blocks type-aware so dirty-promotion evidence no longer carries generated asset, generated animation, paid-provider, runtime, queued-action, or feature-completion blocks by accident.
- Pinned route coverage proving dirty-promotion actions expose only dirty-promotion context and paid-generation actions expose only paid-generation context.
- Kept the cleanup passive: it does not write ledgers, run review scripts, ping the bridge, stage, commit, branch, merge, clean, delete files, mutate Unreal, run PIE, call Tripo or Uthana, check wallets, reserve credits, or spend.

### D.236 - Preflight next-repair target line

- Added a compact `Next repair target` line to the text preflight summary when the prioritized repair action has a dirty-review target group.
- Included target scope, missing-evidence count, focused-test count, and sample-path count so the CLI summary matches the cockpit repair guidance without dumping long path lists.
- Kept the formatter passive: it does not run review scripts, write receipts, write ledgers, stage, commit, branch, merge, clean, delete files, mutate Unreal, run PIE, call Tripo or Uthana, check wallets, reserve credits, or spend.

### D.235 - Readiness repair queue dirty-target detail

- Added first dirty-review target details to the prioritized readiness repair action: target group, order, scope, tracked/untracked counts, missing evidence preview, focused-test commands, sample paths, and promotion-after-receipt state.
- Threaded those fields into the MCP Chat `review_readiness_repair_queue` context so the editor panel can guide the next WIP-promotion repair directly from the repair queue.
- Kept the repair context passive: it does not run dirty-review scripts, write receipts, write ledgers, stage, commit, branch, merge, clean, delete files, mutate Unreal, run PIE, call Tripo or Uthana, check wallets, reserve credits, or spend.

### D.234 - Evidence selector follows dirty-promotion repair priority

- Updated the generic recordable evidence selector so dirty-promotion review evidence is selected before paid-generation evidence when the readiness-repair queue item is absent.
- Added selector coverage proving readiness-repair evidence remains the first choice while dirty-promotion evidence becomes the next default target ahead of Tripo/Uthana paid-provider evidence.
- Kept the selector passive: it does not write ledgers, run review scripts, ping the bridge, stage, commit, branch, merge, clean, delete files, mutate Unreal, run PIE, call Tripo or Uthana, check wallets, reserve credits, or spend.

### D.233 - Dirty promotion workflow action context

- Added a dedicated `dirty_promotion_review` context block to recordable evidence workflow actions so the editor UI can render the target dirty group, missing evidence, focused tests, receipt command, and safety flags without digging through raw metadata.
- Pinned the workflow action context in route coverage to keep WIP promotion guidance visible at the action layer before any human-approved staging or Main promotion.
- Kept the context passive: it does not run review scripts, write ledgers, stage, commit, branch, merge, clean, delete files, mutate Unreal, run PIE, call Tripo or Uthana, check wallets, reserve credits, or spend.

### D.232 - Dirty promotion target-review metadata

- Added bounded first-target review metadata to the recordable dirty-promotion evidence item so the cockpit can show the next dirty group, missing evidence preview, focused-test commands, sample paths, and promotion-after-receipt state.
- Pinned the metadata in route coverage to keep WIP promotion review actionable before any staging, commit, merge, branch move, clean, or Main promotion.
- Kept the metadata passive: it does not run dirty-review scripts, write ledger rows, stage, commit, branch, merge, clean, delete files, mutate Unreal, run PIE, call Tripo or Uthana, check wallets, reserve credits, or spend.

### D.231 - Readiness policy editor-mutation metadata

- Added editor mutation allowed state, missing-gate count/preview, and evidence-required preview to the recordable readiness-policy evidence metadata.
- Pinned the metadata to preserve the bridge proof requirement (`successful_bridge_ping`) and editor mutation gate state before any queued editor action can be treated as safe.
- Kept the metadata passive: it does not ping the bridge, execute queued editor actions, mutate Unreal, run PIE, write ledgers, call Tripo or Uthana, check wallets, reserve credits, spend, stage, commit, branch, merge, clean, or promote WIP.

### D.230 - Readiness policy paid-provider metadata

- Added paid mesh-generation and paid Uthana-animation allowed states, missing-gate counts/previews, and evidence-required previews to the recordable readiness-policy evidence metadata.
- Preserved separate proof expectations for Tripo mesh provider key/wallet/spend evidence and Uthana animation provider key/allowance/usage evidence before paid provider work.
- Kept the metadata passive: it does not call providers, check wallets, reserve credits, approve spend or usage, submit tasks, download/import assets, write ledgers, mutate Unreal, stage, commit, branch, merge, clean, or promote WIP.

### D.229 - Readiness policy Blueprint proof metadata

- Added Blueprint mutation allowed state, missing-gate count/preview, and evidence-required count/preview to the recordable readiness-policy evidence metadata.
- Pinned the metadata to preserve Blueprint pre-read, compile-check, and graph/component readback requirements before any Blueprint mutation can be treated as safe.
- Kept the metadata passive: it does not execute queued editor actions, ping the bridge, mutate Unreal, run PIE, write ledgers, call Tripo or Uthana, check wallets, reserve credits, spend, stage, commit, branch, merge, clean, or promote WIP.

### D.228 - Readiness policy ledger metadata

- Added compact metadata to the recordable readiness-policy evidence item, including blocked policy count, blocked policy preview, WIP-promotion allowed state, WIP missing-gate count, and WIP evidence-required preview.
- Threaded the no-mutation snapshot proof requirements into that metadata so recorded readiness-policy rows can explain why WIP promotion remains gated without re-reading the full cockpit response.
- Kept the metadata passive: it does not write ledger rows by itself, run tests by itself, mutate Unreal, call Tripo or Uthana, check wallets, reserve credits, spend, stage, commit, branch, merge, clean, or promote WIP.

### D.227 - Readiness policy ledger snapshot proof artifacts

- Extended recordable readiness-policy artifacts to include bounded `evidence_required:` entries from all policy rows, including WIP-promotion no-mutation snapshot receipt requirements.
- Added cockpit regression coverage so recording the readiness policy preserves `no_mutation_receipt_snapshot_digest_match` and `no_mutation_receipt_scope_git_tracked_worktree` expectations.
- Kept the artifact path passive: it does not write ledger rows by itself, run tests by itself, mutate Unreal, call Tripo or Uthana, check wallets, reserve credits, spend, stage, commit, branch, merge, clean, or promote WIP.

### D.226 - WIP promotion policy snapshot proof preview

- Added no-mutation receipt tracked-file count, snapshot digest-match, and `git_tracked_worktree` scope requirements to the MCP Chat WIP-promotion readiness policy.
- Exposed compact readiness-policy evidence previews, including a WIP-promotion evidence preview, so cockpit consumers can see required proof without parsing the full policy row.
- Kept the change passive: it does not run tests by itself, mutate Unreal, call Tripo or Uthana, check wallets, reserve credits, spend, write ledgers, stage, commit, branch, merge, clean, or promote WIP.

### D.225 - No-mutation blocker snapshot proof requirement

- Tightened the MCP Chat blocker resolution for `no_mutation_test_lane_safe` so WIP-promotion guidance now requires tracked-file count, snapshot digest match, and `git_tracked_worktree` scope alongside `TRACKED_FILE_MUTATIONS=0`.
- Added regression coverage that pins the stronger no-mutation evidence requirement in the blocker-resolution summary.
- Kept the resolver passive: it does not run tests, mutate Unreal, call Tripo or Uthana, check wallets, reserve credits, spend, write ledgers, stage, commit, branch, merge, clean, or promote WIP.

### D.224 - Platform evidence no-mutation snapshot trail

- Extended the MCP Chat platform-stability recordable evidence item with no-mutation tracked-file count, snapshot digest match, snapshot scope, and snapshot hash algorithm.
- Increased the compact platform evidence artifact cap only enough to keep wrapper/build proof while adding the snapshot trail, without creating a new HUD row or workflow card.
- Kept the path passive: it does not run tests by itself, mutate Unreal, call Tripo or Uthana, check wallets, reserve credits, spend, write ledgers, stage, commit, branch, merge, clean, or promote WIP.

### D.223 - MCP Chat no-mutation snapshot proof

- Threaded the no-mutation receipt's tracked-file count, snapshot scope, snapshot digest-match flag, and hash algorithm into MCP Chat platform preflight, WIP promotion, and test-lane contexts.
- Kept the native HUD clean by exposing the stronger proof only through existing context payloads instead of adding new rows, cards, or panels.
- Kept the change passive: it does not run Unreal, call Tripo or Uthana, check wallets, reserve credits, spend, mutate the editor, write ledgers, stage, commit, branch, merge, clean, or promote WIP.

### D.222 - No-mutation receipt snapshot proof

- Extended the no-mutation unittest receipt with tracked-file count, snapshot scope, snapshot hash algorithm, and before/after snapshot digests so promotion reviews can prove the guard covered the Git-tracked worktree.
- Threaded the new receipt proof fields through IDE companion preflight parsing while preserving the existing status, exit-code, mutation-count, and mutated-path checks.
- Kept the runner behavior unchanged: it still runs the same offline unittest discovery command, writes only the ignored receipt, and does not call Unreal, providers, wallets, ledgers, staging, commits, branches, or promotion workflows.

### D.221 - Preflight next-repair evidence line

- Added a conditional human-readable preflight line that shows unresolved evidence count and batch count for the next repair when the prioritized repair action exposes a dirty-promotion evidence matrix.
- Kept the JSON contract unchanged except for the D.220 repair action metadata; this change only improves the plain-text cockpit/preflight readout.
- Kept the output passive: it does not run repair scripts, stage, commit, clean, branch, merge, mutate Unreal, call providers, check wallets, reserve credits, spend, write ledgers, or mark WIP promotion ready.

### D.220 - Repair queue dirty evidence summary

- Threaded dirty-promotion evidence matrix counts, unresolved evidence count, and a compact blocked-batch preview into the prioritized readiness repair queue action for `dirty_state_grouped_for_promotion`.
- Exposed the same compact summary through MCP Chat's `review_readiness_repair_queue` target context so the next repair can explain remaining owner/source, intent, focused-test, artifact, tracked-diff, and human-approval work without opening the full preflight JSON.
- Kept the repair queue passive: it does not run the review script, stage, commit, clean, branch, merge, mutate Unreal, call providers, check wallets, reserve credits, spend, write ledgers, or mark WIP promotion ready.

### D.219 - Dirty promotion ledger metadata

- Added dirty-promotion evidence matrix counts and a compact blocked-batch preview to the recordable MCP Chat evidence item for the local dirty-promotion review receipt.
- Kept the recordable evidence artifact list stable and compact while giving future ledger rows durable context about unresolved owner/source, intent, focused-test, artifact, tracked-diff, and human-approval evidence.
- Kept the path passive: it does not write ledger rows by itself, stage, commit, clean, branch, merge, run tests, mutate Unreal, call providers, check wallets, reserve credits, spend, or mark WIP promotion ready.

### D.218 - Native WIP promotion evidence suffix

- Extended the native MCP Chat WIP promotion suggested-action suffix with the dirty-promotion evidence matrix count and unresolved evidence count from the cockpit contract.
- Kept the HUD clean by reusing the existing compact action suffix instead of adding a new row, panel, card, or dashboard element.
- Kept the change passive: it does not stage, commit, clean, branch, merge, run tests, mutate Unreal, call providers, check wallets, reserve credits, spend, or mark WIP promotion ready.

### D.217 - Dirty promotion evidence matrix

- Added a per-batch dirty-promotion evidence matrix to the WIP promotion contract and ignored dirty-promotion receipt, including missing evidence counts for owner/source, promotion intent, artifact policy, tracked diff review, focused tests, and explicit human approval.
- Threaded the matrix preview and unresolved evidence count into MCP Chat platform and WIP-promotion contexts so the cockpit can show what is still missing without cluttering the HUD.
- Kept the matrix passive: it does not stage, commit, clean, delete, branch, merge, run tests, mutate Unreal, call providers, check wallets, reserve credits, spend, or mark any batch promotion-ready by itself.

### D.216 - Split Tripo wallet and Uthana usage evidence

- Split the paid-generation evidence receipt into explicit Tripo mesh wallet evidence, Uthana animation allowance evidence, Tripo spend approval, Uthana usage approval, credit review, and motion-seconds review fields while preserving the older combined wallet/spend booleans for compatibility.
- Threaded the new no-spend evidence fields into IDE companion preflight, MCP Chat platform/provider-spend contexts, and native compact provider/evidence summaries so Uthana animation approval is visible beside Tripo mesh approval.
- Kept the receipt passive: it does not call Tripo or Uthana, check wallets, reserve credits, submit tasks, download files, import assets, mutate Unreal, stage, commit, or write ledger evidence.

### D.215 - Dirty promotion candidate batch test guidance

- Added per-dirty-group candidate batch guidance to the WIP promotion contract and ignored dirty-promotion receipt, including focused test commands, required approval evidence, stage policy, and a hard `promotion_allowed_after_receipt=false` flag.
- Threaded focused-test command counts and candidate-batch policy into MCP Chat platform/WIP contexts and the native WIP promotion suggested-action suffix without adding another HUD row.
- Kept the flow passive: it does not stage, commit, clean, delete, branch, merge, run tests, mutate Unreal, call providers, check wallets, reserve credits, spend, or write ledger evidence.

### D.214 - Native repair queue workflow suffix

- Added a native compact target summary for the `review_readiness_repair_queue` workflow action so the MCP Chat suggested action can show the next repair, gate/tool, action count, blocker count, priority policy, and review-only safety hint.
- Kept the cockpit clean by reusing the existing suggested-action suffix instead of adding another HUD row or card.
- Kept the change passive: it does not run repair scripts, ping the bridge, mutate Unreal, call Tripo or Uthana, check wallets, reserve credits, spend, write ledgers, stage, commit, or promote branches.

### D.213 - Readiness repair queue review action

- Added `review_readiness_repair_queue` to MCP Chat workflow actions so the prioritized blocker repair queue has a direct review target instead of only being nested under platform/WIP contexts or recordable evidence.
- Added `target_readiness_repair_queue_context` with recommended next repair, next gate/tool/command, priority policy, evidence preview, safety flags, and stop-before-running-repair policy.
- Added a native command-palette prompt for reviewing the repair queue without adding another HUD row; it remains review-only and does not execute scripts, ping the bridge, call providers, check wallets, mutate Unreal, stage, commit, clean, merge, or write ledger evidence.

### D.212 - Preflight next-repair text guidance

- Added a compact `Next repair` and `Repair priority` line to the human-readable IDE companion preflight so the current blocker-resolution action is visible without opening JSON.
- Extended the dirty-promotion review receipt command output with review-batch count and a next-step reminder for owner/source assignment, focused tests, and human approval before staging or promotion.
- Kept both surfaces passive: no staging, commits, cleaning, branch movement, bridge ping, Unreal mutation, provider calls, wallet checks, credit reservation, or spend.

### D.211 - Safety-first repair queue priority

- Reordered the IDE companion readiness repair queue so chat health stays first, WIP dirty-state/promotion safety comes before live bridge proof, and bridge proof comes before paid-provider wallet or spend gates.
- Threaded a compact `priority_policy` label through preflight and MCP Chat repair contexts so the cockpit can explain the ordering without adding another HUD row.
- Kept the queue passive: it does not stage, commit, clean, move branches, ping the bridge, mutate Unreal, call providers, check wallets, reserve credits, or spend.

### D.210 - Explicit high-value wrapper families

- Split the high-value bridge-wrapper audit into nine explicit roadmap capability families instead of combining function-with-pins with SpawnActor class assignment and sequence-player nodes with AnimGraph pose links.
- Preserved the same eleven covered bridge commands while making cockpit and preflight evidence report 9/9 capability families with full schema coverage.
- Kept the audit offline and passive: it checks source, Python registration, tests, and docs only; it does not ping Unreal, mutate assets, call providers, spend credits, or touch Git.

### D.209 - Save/load and cooldown runtime proof contracts

- Added domain-specific runtime proof modes for `input_cooldown_ability` and `save_load_state` gameplay templates.
- Cooldown ability proof now requires Enhanced Input mapping readback, cooldown variable/readback, blocked repeat activation, HUD cooldown feedback, PIE input log, screenshot, and ledger evidence.
- Save/load proof now requires SaveGame or slot-helper readback, slot/version readback, before-save captured state, loaded-state comparison, restored HUD/objective proof, PIE save/load log, screenshot, and ledger evidence.

### D.208 - Uthana animation usage proof contract

- Added a compact `unreal_mcp_uthana_animation_usage_contract.v1` to MCP Chat's generated-animation lifecycle gate with allowance tools, receipt path, usage-confirmation field, fallback policy, and no-provider/no-download/no-import/no-editor flags.
- Threaded the contract into queue/execution review context and generated-animation evidence metadata so cockpit actions can guide Uthana allowance and explicit usage approval before text-to-motion, download, import, retarget, AnimGraph, PIE, or ledger proof.
- Kept the contract passive: it does not call Uthana, check accounts, submit tasks, download files, import animations, mutate Unreal, write ledgers, reserve credits, or spend.

### D.207 - Dirty promotion batch review details

- Extended the dirty promotion contract and ignored receipt with promotion-batch policy, generated/local artifact policy, safe next steps, and explicit no-provider/no-editor safety flags.
- Threaded those fields through MCP Chat platform, WIP-promotion, and evidence-recording contexts so the cockpit can guide human review of dirty groups before any staging or main-promotion movement.
- Kept the flow passive: it does not stage, commit, clean, delete, merge, move branches, mutate Unreal, call providers, check wallets, reserve credits, or spend.

### D.206 - Platform receipt paid-provider contract proof

- Extended `scripts/write_platform_stability_review.py` so the ignored platform-stability receipt snapshots the paid-provider smoke contract from the test-lane audit.
- Threaded the saved contract fields through IDE companion preflight parsing and MCP Chat platform-stability evidence metadata, including the manual smoke command, opt-in env vars, no-spend tools, forbidden token preview, and no-task/no-download/no-import safety flags.
- Kept the receipt passive: it does not run the provider smoke, call Tripo or Uthana, check wallets, reserve credits, submit tasks, download/import assets, mutate Unreal, stage, commit, or promote branches.

### D.205 - Paid-provider smoke contract visibility

- Extended `scripts/audit_test_lanes.py` with a structured `unreal_mcp_paid_provider_smoke_contract.v1` report for the manual paid-provider smoke lane.
- Exposed the contract through IDE companion preflight and MCP Chat platform context, including required opt-in env vars, manual command, no-spend tools, forbidden token checks, and no-task/no-download/no-import safety flags.
- Kept the contract static and no-spend: it does not run the paid-provider smoke, call Tripo or Uthana, check wallets, reserve credits, submit tasks, download/import assets, mutate Unreal, or touch Git.

### D.204 - No-spend wallet evidence gate clarity

- Added explicit no-spend wallet/allowance review steps and receipt command templates to the IDE companion paid-generation evidence contract.
- Mirrored those fields into MCP Chat platform preflight, evidence recording, and local repair queue contexts so the cockpit can guide Tripo wallet and Uthana allowance proof without cluttering the HUD or submitting provider tasks.
- Kept paid generation blocked until both wallet/allowance evidence and explicit spend/usage confirmation are recorded; the guidance does not call providers, reserve credits, submit tasks, download/import assets, mutate Unreal, or touch Git.

### D.203 - Provider credential-ready preflight

- Verified the ignored `Saved/MCPChat/secrets.json` provider contract can mark both Tripo and Uthana credentials as configured without returning raw keys.
- Rewrote preflight repair-queue assertions so they pass on both clean machines with missing credentials and configured developer machines where provider-key repair gates are already resolved.
- Kept paid work blocked until wallet/allowance evidence and explicit spend/usage confirmation are recorded; this pass does not call providers, check wallets, reserve credits, submit tasks, mutate Unreal, or touch Git.

### D.202 - Compact preflight receipt paths

- Normalized human-readable IDE companion preflight receipt paths so repo-local proof artifacts display as concise `Saved\...` paths instead of long absolute paths.
- Added coverage proving the text summary shortens local no-mutation and plugin-build receipt paths while leaving the JSON report contract unchanged.
- Kept the change display-only: it does not read new artifacts, write receipts, run tests, build plugins, ping Unreal, call providers, approve spend, mutate Unreal, or touch Git.

### D.201 - Preflight execution-proof receipt summary

- Added parsing for the chat cockpit startup receipt and exposed its state/path in the human-readable IDE companion preflight output.
- Extended the same preflight receipt summary to show no-mutation unittest and local plugin-build receipt states beside the bridge/provider/paid/dirty/platform proof rows.
- Kept the summary read-only: it does not start chat, ping the bridge, run tests, build the plugin, call providers, approve spend, mutate Unreal, or touch Git.

### D.200 - Preflight local receipt summary

- Updated the human-readable IDE companion preflight output to show bridge ping, provider config review, paid generation evidence, dirty promotion review, and platform stability receipt states and paths.
- Added coverage so receipt visibility remains part of the CLI contract alongside readiness and blocking gates.
- Kept the summary passive: it reads existing report fields only and does not ping the bridge, start chat, call providers, check wallets, approve spend, mutate Unreal, or touch Git.

### D.199 - Paid generation evidence review receipt

- Added `scripts/write_paid_generation_evidence_review.py` to write ignored local review proof at `Saved/PaidGenerationEvidence/last_review_receipt.json` for Tripo wallet/Uthana allowance evidence and explicit spend/usage approval.
- Updated IDE companion preflight and MCP Chat paid-generation evidence context to expose the receipt path, state, required command, and no-provider/no-wallet/no-credit-reservation/no-task-submission safety flags.
- Kept the receipt passive by default: it does not call providers, check wallets, reserve credits, submit tasks, download or import assets, mutate Unreal, approve spend by itself, or touch Git.

### D.198 - Chat cockpit startup evidence ledger handoff

- Added a `record_chat_cockpit_start_receipt` evidence checklist item and workflow action to MCP Chat so SSE startup and `/chat/history?limit=1` health proof can be recorded into the IDE companion ledger.
- The action carries startup receipt path, health endpoint, repair state, startup/proof commands, and no-process-start/no-port-kill/no-editor/no-provider/no-git safety flags.
- Kept the handoff passive: it does not start processes, kill ports, mutate Unreal, call providers, spend credits, or touch Git.

### D.197 - Bridge ping evidence ledger handoff

- Added a `record_bridge_ping_receipt` evidence checklist item and workflow action to MCP Chat so successful or failed bridge ping receipts can be recorded into the IDE companion ledger.
- The action carries bridge receipt state/path, host/port, TCP readiness, `successful_bridge_ping`, editor-mutation allowance, Blueprint blocker counts, and no-editor/no-PIE/no-provider/no-git safety flags.
- Kept the handoff passive: it records bridge proof or blocker evidence only and does not ping the bridge, execute queued actions, mutate Unreal, run PIE, call providers, or touch Git.

### D.196 - Provider config evidence ledger handoff

- Added a `record_provider_config_review` evidence checklist item and workflow action to MCP Chat so masked Tripo/Uthana provider configuration review proof can be recorded into the IDE companion ledger.
- The action carries provider review receipt state/path, mesh and animation provider names, configured/source booleans, ignored-secret policy, save/proof tool hints, and no-raw-key/no-provider-call/no-wallet-check/no-credit-reservation/no-spend-confirmation flags.
- Kept the handoff passive and secret-safe: it does not echo keys, call providers, check wallets, reserve credits, record spend approval, mutate Unreal, or touch Git.

### D.195 - Dirty promotion evidence ledger handoff

- Added a `record_dirty_promotion_review` evidence checklist item and workflow action to MCP Chat so dirty-state grouping and WIP-promotion review proof can be recorded into the IDE companion ledger.
- The action carries dirty review receipt state/path, dirty risk, tracked/untracked/group counts, review batch counts, recommended next action, and no-stage/no-commit/no-clean/no-branch-move safety flags.
- Kept the handoff passive: it does not stage, commit, clean, delete, merge, move branches, mutate Unreal, call providers, spend credits, or authorize promotion to main.

### D.194 - Platform stability evidence ledger handoff

- Added a `record_platform_stability_review` evidence checklist item and workflow action to MCP Chat so the local platform-stability receipt can be recorded into the IDE companion ledger.
- The action carries receipt state/path, readiness flags, no-mutation/test-lane/wrapper/build proof, WIP-promotion missing gates, and no-provider/no-editor/no-git safety flags.
- Kept the handoff passive and uncluttered: it does not replace the prioritized repair-queue evidence row, mutate Unreal, call providers, spend credits, stage, commit, clean, or promote branches.

### D.193 - Platform stability review receipt

- Added `scripts/write_platform_stability_review.py` to write ignored local proof at `Saved/PlatformStabilityReview/last_review_receipt.json` with platform-stability and WIP-promotion evidence from the local IDE companion preflight.
- Updated IDE companion preflight and MCP Chat platform/WIP-promotion contexts to expose the platform stability review receipt state, path, required command, and passive safety flags.
- Kept the receipt review-only: no raw keys, provider calls, wallet checks, credit reservation, spend confirmation, editor mutation, Git staging, commits, cleaning, branch movement, or promotion authorization.

### D.192 - Repair execution readiness context

- Added `repair_execution_readiness` to `repair_failed_step.target_repair_review_context` so the cockpit distinguishes safe offline repair planning from live Unreal repair application.
- The packet reports whether a repair work order can be compiled, whether the repair can be applied now, bridge/pre-read requirements, after-apply compile/readback/ledger proof, and the recommended next repair step.
- Kept repair readiness passive: no bridge ping, queued action execution, Blueprint mutation, compile, PIE run, ledger write, provider call, spend, or automatic repair application.

### D.191 - Gameplay template execution-readiness context

- Added `execution_readiness` to `review_gameplay_template_plan.target_gameplay_template_context` so the cockpit summarizes whether the selected gameplay template can queue editor work, whether it can be marked complete, and which compile/readback/runtime/ledger proof gates still block it.
- Included compact before/after proof previews, missing gate previews, queue/evidence tool hints, and stop-before-feature-complete policy without adding another HUD card.
- Kept the context review-only: no bridge ping, queued action execution, Blueprint mutation, PIE run, ledger write, provider call, spend, or completion authorization.

### D.190 - Provider config gate workflow target

- Added `review_provider_config_gate` to MCP Chat `workflow_actions`, backed by `chat_get_cockpit_overview`, so masked Tripo/Uthana credential setup, ignored secret-path policy, provider config receipt state, and repair commands can be reviewed before wallet checks or paid provider work.
- Added `target_provider_config_context` with no-raw-key, no-provider-call, no-wallet-check, no-credit-reservation, no-spend-confirmation, and no-editor-mutation flags.
- Kept the surface clean and passive: it rides the existing workflow action rail and does not add another HUD card, call providers, echo secrets, mutate Unreal, or authorize spend.

### D.189 - Provider config review receipt

- Added `scripts/write_provider_config_review.py` to write ignored local proof at `Saved/ProviderConfigReview/last_review_receipt.json` with masked Tripo/Uthana config status, repair commands, and secret-path policy.
- Updated IDE companion preflight, readiness repair queue, MCP Chat platform context, and provider-spend review context to expose the provider config receipt state and required command.
- Kept the receipt no-leak and no-spend: no raw keys, provider calls, wallet checks, credit reservation, spend confirmation, editor mutation, or Git mutation.

### D.188 - Bridge ping receipt hard gate

- Updated `scripts/bridge_ping.py` to write ignored local proof at `Saved/BridgePing/last_ping_receipt.json` for both successful and failed live bridge checks.
- Updated IDE companion preflight and MCP Chat platform/live-editor contexts to expose bridge TCP reachability separately from the required successful bridge-ping receipt.
- Kept the bridge as a hard editor-mutation gate: no Blueprint, actor, PIE, viewport, or queued editor action should proceed until `successful_bridge_ping` is proven by the receipt and the bridge is reachable.

### D.187 - Dirty promotion review receipt

- Added `scripts/write_dirty_promotion_review.py` to write ignored local proof at `Saved/DirtyPromotionReview/last_review_receipt.json` with dirty groups, review batches, required evidence, and WIP/main branch policy.
- Updated IDE companion preflight, readiness repair queue, and MCP Chat promotion contexts to expose the dirty review receipt state, path, and required command beside `dirty_state_grouped_for_promotion`.
- Kept the receipt as review evidence only: no staging, commits, cleaning, deletion, branch movement, editor mutation, provider call, spend, or promotion authorization.

### D.186 - Chat cockpit startup receipt repair helper

- Added `scripts/start_chat_cockpit_server.ps1` as the explicit repair action for `chat_server_reachable`; it starts the SSE MCP server hidden, waits for `/chat/history?limit=1`, and writes ignored proof at `Saved/ChatCockpit/last_start_receipt.json`.
- Updated IDE companion preflight and MCP Chat platform contexts to expose the helper script, receipt path, and underlying manual SSE command through `chat_cockpit_repair_contract`.
- Kept the audit passive and the helper bounded: preflight does not start processes, and the repair script kills no ports, mutates no Unreal assets, calls no providers, echoes no secrets, spends nothing, and touches no Git state.

### D.185 - No-mutation unittest receipt for promotion proof

- Updated `scripts/run_no_mutation_unittest.py` to write ignored local proof at `Saved/NoMutationTest/last_run_receipt.json` after comparing Git-tracked file hashes.
- Updated IDE companion preflight and MCP Chat platform/test-lane contexts to report the receipt state, mutation count, test exit code, and required command; WIP promotion now treats the clean receipt as part of `no_mutation_test_lane_safe` evidence.
- Kept the receipt passive and local: no Unreal editor bridge command, no provider call, no spend, no secret echo, and no git mutation.

### D.184 - Local plugin build receipt for preflight

- Updated `_build_plugin.bat` to tee BuildPlugin output to `Saved/PluginBuildSmoke/last_build.log` and write `Saved/PluginBuildSmoke/last_build_receipt.json` with status, exit code, plugin path, package directory, and log path.
- Updated IDE companion preflight to prefer the local receipt over machine-global AutomationTool logs, preventing unrelated Unreal builds from satisfying or obscuring the plugin build gate.
- Kept the receipt local/ignored and no-provider: no Unreal editor bridge command, no provider call, no spend, no secret echo, and no git mutation.

### D.183 - Gameplay template paid-animation gate context

- Threaded paid-animation readiness into `review_gameplay_template_plan.target_gameplay_template_context` so Uthana prompts show missing auth/wallet/spend gates, required evidence, safe unblock tools, and stop-before-provider state beside the feature-template packet.
- Updated the native compact `Next:` summary for gameplay-template review to include an animation-gate count without adding another HUD panel.
- Kept the route passive: no Uthana call, no download, no import, no PIE, no ledger write, no editor mutation, no secret echo, and no spend.

### D.182 - Paid generation evidence ledger handoff

- Added a provider-neutral MCP Chat evidence row, `record_paid_generation_evidence`, for Tripo wallet proof, Uthana allowance/download proof, and explicit human spend/usage approval before paid provider work.
- Added a dedicated workflow action and native command-palette prompt so the editor can record the paid-generation proof row without requiring raw JSON lookup.
- Kept the handoff passive: no Tripo or Uthana calls, no downloads, no imports, no credit reservation, no approval creation, no editor mutation, and no git mutation.

### D.181 - Native HUD repair queue summary

- Threaded `readiness_repair_queue` into the native MCP Chat panel parser so the existing Blockers line can show the next repair action, gate, recommended tool, and action count.
- Marked the Evidence line when a `record_readiness_repair_queue` row is present, making the ordered repair path visible as recordable ledger evidence without adding another HUD card.
- Kept the native surface passive and clean: no queue execution, bridge ping, process start, provider call, secret echo, editor mutation, spend, or git mutation.

### D.180 - Readiness repair queue evidence handoff

- Added a MCP Chat evidence checklist row for `readiness_repair_queue` so the ordered blocker repair path can be recorded directly into the IDE companion ledger.
- Made record-evidence target selection prefer the repair queue before the broader readiness policy, giving the chat cockpit a concrete first handoff when readiness is blocked.
- Kept the handoff passive and bounded: it records recommended next actions and proof requirements only, with no queue execution, bridge ping, provider call, secret echo, editor mutation, spend, or git mutation.

### D.179 - Readiness repair queue contract

- Added a top-level `readiness_repair_queue` to IDE companion preflight so bridge, chat, provider, wallet/spend, dirty-state, and promotion blockers become ordered safe next actions.
- Threaded the compact queue into MCP Chat platform preflight and WIP promotion contexts so cockpit consumers can show the next repair step without requiring users to interpret scattered JSON packets.
- Kept the queue passive: no automatic server launch, no port kill, no secret echo, no provider call unless explicitly listed as a future wallet check, no editor mutation, no git mutation, and no HUD clutter.

### D.178 - Chat cockpit startup repair contract

- Added a top-level `chat_cockpit_repair_contract` to IDE companion preflight so chat reachability carries a stable schema, SSE endpoint proof, startup steps, and required evidence.
- Threaded the compact no-process-start contract into MCP Chat platform preflight and WIP promotion contexts so `chat_server_reachable` and `chat_cockpit_reachable` share the same repair packet.
- Kept the repair contract passive: no server launch, no port kill, no provider call, no bridge ping, no editor mutation, no git mutation, no spend, and no new HUD row.

### D.177 - Dirty promotion review contract

- Added a read-only dirty promotion contract to IDE companion preflight with dirty risk, tracked/untracked counts, primary group, bounded review batches, required promotion evidence, and explicit no-git-mutation flags.
- Threaded the compact contract into MCP Chat platform preflight and WIP promotion contexts so `dirty_state_grouped_for_promotion` has a concrete review order instead of only raw dirty counts.
- Kept the contract passive: no staging, commits, cleaning, deletion, branch movement, merge, bridge ping, provider call, or editor mutation.

### D.176 - Preflight high-value wrapper coverage gate

- Added high-value bridge-wrapper coverage to IDE companion preflight so the main readiness report now carries wrapper capability counts, command/schema coverage, failing capability preview, and audit tool evidence.
- Promoted `high_value_bridge_wrappers_covered` into platform-stability and WIP-promotion readiness gates, backed by the existing offline source/registry/test/doc audit.
- Threaded compact wrapper coverage into MCP Chat platform preflight context without adding HUD clutter, bridge pings, editor mutation, provider calls, or git mutation.

### D.175 - Uthana no-spend download allowance smoke

- Extended the manual paid-provider smoke with an optional `UTHANA_SMOKE_MOTION_ID` path that calls `gen_uthana_check_download_allowed` for an existing motion.
- Added offline lane-audit coverage proving the smoke names the download-allowance check but does not call the actual Uthana download tool or require `confirm_usage=True`.
- Kept the lane passive: no motion creation, no file download, no animation import, no credit reservation, no PIE, no editor mutation, and no default CI discovery.

### D.174 - Paid generation wallet/spend evidence contract

- Added a structured paid-generation evidence contract to IDE companion preflight for Tripo wallet evidence and Uthana animation allowance evidence.
- Threaded the compact no-spend contract into MCP Chat platform preflight and provider-spend contexts so blocked paid generation points at wallet/allowance tools, explicit spend/usage approval, and ledger evidence requirements.
- Kept the contract passive: no provider calls, no wallet checks, no credit reservation, no ledger writes, no bridge ping, no editor mutation, and no new HUD row.

### D.173 - Provider configuration no-leak repair contract

- Added a provider repair contract to IDE companion preflight with safe Tripo and Uthana setup templates, proof tools, ignored local secret path evidence, and explicit no-leak policy.
- Threaded the compact provider secret/repair contract into MCP Chat platform preflight context so missing provider credentials are actionable without exposing raw keys.
- Kept provider repair passive: no key writes, no network calls, no wallet checks, no provider spend, no bridge ping, no editor mutation, and no new HUD row.

### D.172 - Chat cockpit reachability repair contract

- Added explicit MCP Chat reachability diagnostics to IDE companion preflight: base URL, `/chat/history?limit=1` health endpoint, TCP probe status, SSE startup command, Cursor watcher command, and bounded troubleshooting hints.
- Threaded the compact chat repair contract into MCP Chat platform preflight and WIP promotion contexts so `chat_server_reachable` and `chat_cockpit_reachable` point at the same evidence path.
- Updated chat blocker resolutions to name the SSE server command and `/chat/history` proof while staying passive: no server launch, no bridge ping, no provider call, no editor mutation, and no new HUD row.

### D.171 - Dirty-state grouping evidence for promotion review

- Added read-only dirty worktree grouping to IDE companion preflight, including group counts, primary dirty group, tracked/untracked split, and bounded samples.
- Threaded the grouped dirty-state summary into MCP Chat platform preflight and WIP promotion contexts so `dirty_state_grouped_for_promotion` is actionable instead of only a raw count.
- Kept the grouping passive: no staging, commits, cleanup, branch movement, provider calls, bridge pings, editor mutation, or new HUD row.

### D.170 - Cockpit WIP promotion readiness alignment

- Added `readiness_policy.wip_promotion` to MCP Chat's derived cockpit readiness summary so `check_readiness` mirrors preflight promotion blockers.
- Mapped lower-level `test_lane_separation` and `chat_server_reachable` blockers to canonical WIP-promotion gates: `no_mutation_test_lane_safe` and `chat_cockpit_reachable`.
- Kept the alignment read-only and compact: no new HUD row, no git mutation, no provider calls, no bridge pings, and no editor mutation.

### D.169 - Preflight WIP promotion readiness

- Added `readiness_policy.wip_promotion` and top-level `ready_for_wip_promotion` to the IDE companion preflight.
- WIP promotion readiness now requires WIP branch policy, reproducible tool count, no-mutation test lane safety, build-wrapper readiness, recent plugin build success, grouped/clean dirty state, and chat cockpit reachability.
- Threaded WIP promotion missing-gate counts into MCP Chat platform preflight context without adding another HUD row.

### D.168 - WIP promotion repair targeting

- Added explicit Resolve Blockers guidance for WIP-promotion-only gates: no-mutation lane safety, high-value wrapper coverage, plugin build success, dirty-state grouping, and chat cockpit reachability.
- Threaded compact promotion repair previews and a selected `target_promotion_blocker_resolution` into MCP Chat's existing WIP promotion context.
- Kept promotion repair guidance read-only: no staging, commits, merges, provider calls, bridge pings, editor mutation, or new HUD row.

### D.167 - Platform-stability blocker resolutions

- Added explicit MCP Chat blocker resolutions for platform gates: tool registry reproducibility, test-lane separation, build wrapper presence, build wrapper references, and WIP branch policy.
- Prioritized hard platform-stability blockers before provider credential, wallet, and spend tasks while keeping bridge, chat, and Blueprint safety gates ahead of platform work.
- Kept the guidance read-only: no git mutation, no provider calls, no bridge pings, no editor mutation, and no new HUD row.

### D.166 - Uthana blocker target priority repair

- Updated MCP Chat blocker targeting so `animation_provider_api_key_configured` uses the current Uthana native Generate Settings strategy before wallet or spend evidence tasks.
- Added regression coverage for Uthana-only blocked states where animation key setup must be the selected next blocker resolution.
- Kept the repair in the existing blocker-resolution surface; no provider calls, secret writes, editor mutation, or new HUD row.

### D.165 - Preflight test-lane separation gate

- Embedded `scripts/audit_test_lanes.py` output into `scripts/audit_ide_companion_readiness.py` so preflight JSON carries offline/live-bridge/paid-provider counts and violation evidence.
- Added `test_lane_separation` to the platform-stability policy gates; accidental live or paid tests in default `test_*.py` discovery now block promotion readiness.
- Threaded compact test-lane counts into MCP Chat platform preflight context without adding another HUD row.

### D.164 - Cockpit runtime proof contract visibility

- Threaded `unreal_mcp_gameplay_feature_runtime_proof.v1` summary fields into MCP Chat work-order, gameplay-template, runtime verification, runtime review, and evidence-recording contexts.
- Runtime verification now emits checklist rows for domain-specific runtime proof items such as BT/Blackboard readback, nav setup, replicated state, screenshots, and ledger evidence.
- Kept the cockpit flow read-only and compact: no provider calls, no editor mutation, and no new permanent HUD row.

### D.163 - Gameplay template runtime proof contracts

- Added `unreal_mcp_gameplay_feature_runtime_proof.v1` to gameplay feature templates so runtime proof is domain-specific instead of only generic PIE/log evidence.
- AI patrol/chase templates now require Blackboard assignment/readback, nav or navmesh setup evidence, capsule/movement readback, PIE AI state/log proof, screenshot proof, and ledger evidence.
- Replicated combat templates now require replication description, server-authority damage policy readback, replicated health/death readback, common-mistake validation, single-player damage proof, and two-player PIE proof or an explicit deferred-networking rationale.

### D.162 - Uthana animation readiness preflight

- Extended `gen_compile_ide_companion_readiness` with optional `mechanic_brief` support so generated-animation demand from gameplay plans is visible before provider calls.
- Added Uthana-specific readiness gates for provider registration, animation key configuration, usage-confirmation enforcement, and optional org motion allowance checks.
- Kept animation preflight no-spend/no-editor-mutation by default; the live Uthana account check only runs when `include_animation_account=True`.

### D.161 - High-value wrapper schema evidence

- Promoted schema/signature coverage to first-class evidence in `scripts/audit_high_value_wrapper_coverage.py`.
- The audit now reports expected schema parameters, missing schema parameters, per-command `schema_ok`, and aggregate schema-covered command counts for the roadmap's high-value bridge wrappers.
- Threaded schema coverage counts into MCP Chat bridge-wrapper context and the native compact wrapper summary without adding a new HUD row.

### D.160 - Build warning preflight classification

- Added read-only AutomationTool warning extraction to the IDE companion preflight so last plugin builds report warning count, warning categories, preview lines, and severity.
- Threaded build warning count/categories/severity into MCP Chat platform preflight and WIP promotion contexts without blocking successful builds or adding a new HUD row.
- Updated native compact platform preflight text to include a concise warning count/severity suffix for build-health review.

### D.159 - Remove deprecated StructUtils plugin dependency

- Removed the deprecated `StructUtils` plugin enablement from `UnrealMCP.uplugin`.
- Removed the stale `StructUtils` module dependency from `UnrealMCP.Build.cs`; `FInstancedStruct` remains available through UE 5.6 `CoreUObject`.
- Added source-level guard coverage so the deprecated plugin dependency is not reintroduced while motion matching and Chooser authoring keep their existing code path.

### D.158 - Explicit JSON plugin headers

- Replaced the remaining public plugin `Json.h` includes with explicit `Dom/JsonObject.h` and `Dom/JsonValue.h` includes.
- Added source-level guard coverage so plugin headers do not reintroduce Unreal's monolithic JSON include warning.
- Verified the plugin build no longer emits `Json.h` monolithic-header warnings.

### D.157 - UMG image size deprecation cleanup

- Replaced the deprecated native `UImage::SetBrushSize` call in the UMG property path with `SetDesiredSizeOverride` while preserving the existing `BrushSize` command-facing property.
- Added source-level guard coverage so future plugin edits do not reintroduce `SetBrushSize`.
- Resolved LIM-0006 after plugin build verification confirmed the `UImage::SetBrushSize` deprecation warning no longer appears.

### D.156 - Placeholder fallback workflow action

- Added `continue_with_placeholder_fallback` to the MCP Chat workflow rail so blocked paid-provider generation can route directly into no-spend placeholder manifest compilation.
- The action reuses `skill_compile_ide_companion_placeholder_manifest`, carries both provider-spend fallback context and placeholder context, and is enabled only when `fallback_placeholder_available` is true.
- Added native command-palette guidance and compact `Next:` priority so the fallback path becomes the selected workflow route without adding another HUD row or calling providers.

### D.155 - Provider spend fallback handoff

- Added explicit placeholder fallback metadata to `review_provider_spend_gate.target_provider_spend_context` when paid generation is blocked but placeholder continuation is available.
- The spend gate now reports `fallback_placeholder_available`, the fallback workflow action id/label, placeholder tool, queue tool, no-spend fallback reason, and now-vs-future network/spend/editor requirements.
- Updated the native provider-spend compact summary and command-palette guidance so blocked Tripo spend can route to placeholder manifest compilation without raw JSON hunting or provider calls.

### D.154 - Native lifecycle compile summary

- Threaded `compile_asset_lifecycle_manifest.target_asset_lifecycle_compile_context` into the native MCP Chat compact `Next:` workflow summary.
- The editor now shows lifecycle compile state, session-plan availability, planned mesh prompt count, planned Uthana animation prompt count, manifest/pending counts, future gate count, estimated motion seconds, and write-manifest guidance without adding another HUD row.
- Added static coverage proving the native panel recognizes the lifecycle compile target fields.

### D.153 - Lifecycle manifest compile action from cockpit

- Added `compile_asset_lifecycle_manifest` to the MCP Chat workflow rail so agents can compile or refresh the provider-neutral generated mesh and Uthana animation lifecycle manifest from the current companion session plan.
- The action context reports planned mesh prompt counts, planned Uthana animation prompt counts, existing manifest counts, pending lifecycle rows, future provider/spend gates, write-manifest guidance, and no-provider/editor-call policy.
- Updated native Compile Generated Asset Lifecycle guidance to inspect the cockpit compile context and work-order generated prompt counts before asking for pasted lifecycle JSON.

### D.152 - Gameplay-template generated-animation cockpit review

- Surfaced mechanic-level Uthana `generated_animation_prompts` through IDE companion work orders, MCP Chat work-order context, gameplay-template review context, Feature Work card details, queue target context, next-safe-step review, and execution review.
- Added compact generated-animation prompt counts, previews, provider/skeleton/tool/proof hints, estimated motion seconds, and no-bypass policy so animation requirements are visible before a lifecycle manifest or editor queue execution.
- Updated native Review Gameplay Template guidance and compact summaries to include generated animation prompt requirements without adding a permanent HUD panel.

### D.151 - Gameplay mechanic Uthana animation prompts

- Added mechanic-level `generated_animation_prompts` so AI, composite AI/objective, combat, ability, and animation-explicit gameplay briefs carry Uthana text-to-motion requirements directly in `unreal_mcp_gameplay_mechanic_plan.v1`.
- Threaded generated animation prompts into feature-template asset lists, animation system hooks, optional generated-content tool sequencing, IDE companion session plans, and provider-neutral lifecycle manifests with retarget/readback, AnimGraph, PIE, and ledger proof expectations.
- Added coverage proving direct mechanic plans, companion sessions, and generated asset lifecycle manifests preserve Uthana motion prompts without calling providers, spending usage, importing assets, or mutating Unreal.

### D.150 - Bug-fix repair feature template

- Added `bug_fix_repair_pass` to gameplay mechanic planning so bug/fix/broken/crash/compile-error/regression briefs route into an evidence-backed repair workflow instead of generic feature authoring.
- The repair template requires failure context, reproduction or documented non-repro evidence, one scoped fix, compile/readback confirmation, PIE/log/viewport proof, regression guard evidence, and ledger recording before the fix can be treated as complete.
- Added planner coverage proving repair briefs avoid generated-asset spend, surface repair hooks, include failure-reproduction tools, and preserve completion-contract evidence gates.

### D.149 - Performance optimization feature template

- Added `performance_optimization_pass` to gameplay mechanic planning so optimization briefs route into an executable, evidence-backed feature template instead of the generic objective-HUD template.
- The template requires baseline project/asset/readback context, a scoped single optimization candidate, compile/readback confirmation, before/after PIE/log/viewport proof, and ledger evidence before the pass can be treated as complete.
- Added focused planner coverage for optimization classification, performance hooks, operation candidates, baseline profile phase, and completion-contract evidence.

### D.148 - Generated-content gates in editor queue review

- Threaded generated-asset replacement and Uthana/generated-animation gate summaries into `review_editor_queue.target_queue_review_context`.
- Kept already-compiled queues proof-aware when developers inspect them before execution: placeholder swap, lifecycle import, animation retarget, AnimGraph, PIE, and ledger gates stay visible without a new HUD panel.
- Added focused cockpit coverage for generated mesh replacement and generated animation queue-review gate continuity.

### D.147 - Generated-animation gates in queue and execution review

- Threaded compact Uthana/generated-animation lifecycle signals into queue targets, next-safe-step, and execution review: target motion, provider, skeleton, missing stages, proof contract, next safe action, and no-bypass policy.
- Kept generated animation import, retarget, AnimGraph, PIE, and ledger proof visible when agents queue or execute animation-related editor work.
- Added focused Uthana coverage proving generated-animation gate policy survives queue compilation and single-action execution review.

### D.146 - Generated-asset swap gates in queue and execution review

- Threaded generated-asset replacement operation counts, previews, tool hints, proof-contract counts, and gate policy into `queue_editor_actions.target_queue_context`.
- Added the same placeholder-to-generated replacement guardrails to `next_safe_step`, `execution_review`, and `execute_next_safe_step.target_execution_review_context`.
- Added focused cockpit coverage so queued/editor execution review keeps lifecycle, quality-proof, and ledger evidence gates visible before any placeholder swap.

### D.145 - Gameplay template generated-asset swap review context

- Added compact generated-asset replacement operation counts, previews, tool hints, and proof-contract counts to MCP Chat work-order template summaries and gameplay-template review contexts.
- Updated the native gameplay-template compact summary to show a swap count when the selected template includes placeholder-to-generated replacement work, without adding HUD clutter.
- Added focused cockpit/static coverage for `generated_asset_replacement_operation_count` and the native `swap` suffix.

### D.144 - AI patrol objective asset-swap vertical-slice template

- Added `ai_patrol_objective_asset_swap_slice` to gameplay mechanic planning as the first composite feature template, covering patrol/chase AI, objective HUD updates, placeholder visual fallback, generated-asset replacement, PIE proof, and ledger evidence in one playable slice contract.
- Added generated-asset replacement operation typing and tool candidates so the template routes agents through lifecycle/placeholder review before any placeholder-to-generated swap work.
- Updated native Review Gameplay Template guidance to inspect placeholder/generated asset swap requirements before queueing editor work.

### D.143 - Generated animation quality proof contracts

- Added `unreal_mcp_generated_animation_quality_proof_contract.v1` to Uthana/generated animation lifecycle records, requiring Animation Sequence readback, target skeleton or retarget evidence, AnimGraph/state-machine reference proof, PIE/viewport playback proof, and ledger evidence after import.
- Surfaced compact animation quality-proof contract schemas and required-after-import previews through MCP Chat generated animation lifecycle review and evidence metadata.
- Updated native Review Generated Animation Lifecycle guidance so agents inspect the proof contract before text-to-motion, download, import, retarget, AnimGraph, PIE, or ledger work.

### D.142 - Generated asset quality proof contracts

- Added `unreal_mcp_generated_asset_quality_proof_contract.v1` to generated mesh lifecycle assets, requiring mesh load/readback, material slot, collision/readability, viewport/thumbnail, and ledger evidence after import.
- Surfaced compact quality-proof contract schemas and required-after-import previews through MCP Chat generated asset lifecycle and quality proof review contexts.
- Updated native Review Generated Asset Quality Proof guidance so agents inspect the contract before material/collision/viewport checks, placeholder replacement, or generated-asset evidence recording.

### D.141 - Feature-template operation proof contracts

- Added `unreal_mcp_gameplay_feature_operation_proof.v1` contracts to every gameplay feature-template editor operation, naming preconditions, required after-operation evidence, and stop-if-missing rules.
- Surfaced compact operation-proof counts and required-after evidence previews through MCP Chat work-order, Blueprint mutation, queue, and gameplay-template review contexts without adding a new HUD panel.
- Updated native Review Gameplay Template guidance so agents inspect operation proof contracts before queueing or executing editor work.

### D.140 - Reviewed queued-action executor contract

- Added a compact `pre_execution_checklist`, `executor_contract`, and `post_execution_evidence_required` to the MCP Chat execution review and `execute_next_safe_step` workflow context.
- Updated the native Execute Next Safe Step command-palette prompt to inspect those fields before any queued editor action, then stop after exactly one action and record evidence before continuing.
- Kept the route guidance-only: it refreshes/readbacks cockpit state and evidence requirements, but does not execute tools, ping the bridge, mutate Unreal, record evidence, call providers, or add HUD clutter.

### D.139 - Native Uthana blocker-resolution guidance

- Updated Resolve Blockers guidance so `animation_provider_api_key_configured` points to the native Generate Settings masked `UTHANA_API_KEY` field, env `UTHANA_API_KEY`, or `gen_save_provider_config(store_uthana_api_key=True)` as no-leak setup paths.
- Matched the Tripo blocker text to the native masked `TRIPO_API_KEY` setup path so paid mesh and paid animation readiness now share the same editor-first credential story.
- Extended static cockpit and command-palette coverage to keep the guidance read-only: it may explain auth setup and masked evidence, but it must not call providers, spend credits, mutate Unreal, or expose raw keys.

### D.138 - Native Uthana key setup field

- Added a dedicated masked `UTHANA_API_KEY` field to the native Generate Settings panel beside the existing Tripo key field.
- The panel now loads `UTHANA_API_KEY` or `uthana_api_key` from ignored `Saved/MCPChat/secrets.json`, reports `env:UTHANA_API_KEY` precedence, and writes the canonical `UTHANA_API_KEY` entry when populated.
- Kept the HUD compact and no-leak: auth status still shows only source labels, and the native panel does not call Uthana, spend usage, download files, import animations, or mutate Unreal.

### D.137 - Native feature completion contract workflow summary

- Added native MCP Chat command-palette guidance for `record_feature_completion_contract`, pointing agents to the cockpit workflow action, completion-contract metadata, work-order template, and evidence checklist row.
- Extended the native compact workflow parser with `FeatureCompletionContractTargetSummary` so the existing `Next:` line can show template, proof-gate, required-evidence, stop-condition, and artifact counts without adding another HUD panel.
- Kept the action evidence-only: the prompt explicitly forbids Unreal mutation, PIE, provider calls, or bypassing missing proof while recording the contract review.

### D.136 - Feature completion contract evidence row

- Added a recordable `record_feature_completion_contract` row to the MCP Chat evidence checklist whenever a gameplay work order carries `unreal_mcp_gameplay_feature_completion_contract.v1`.
- The row surfaces completion required-evidence, proof-gate, and stop-before-complete previews, then offers a dedicated `record_feature_completion_contract` workflow action through `skill_record_ide_companion_evidence`.
- Kept the route read-only and no-editor/no-spend: it records the contract review only after existing compile/readback, PIE, asset, repair, and ledger proof has been gathered elsewhere.

### D.135 - Gameplay feature completion contracts

- Added `unreal_mcp_gameplay_feature_completion_contract.v1` to every gameplay feature template packet.
- The contract defines required evidence, proof gates, and stop-before-complete conditions so a template cannot be treated as playable until assets, editor operations, compile/readback, PIE proof, repairs, and ledger evidence are all accounted for.
- Threaded completion proof counts/previews into MCP Chat work-order summaries and the existing Feature Work card without adding a new HUD panel.

### D.134 - Generated asset card unsupported-provider warnings

- Added generated-animation counts and unsupported provider task counts to the MCP Chat `generated_assets` card details.
- The cockpit overview now warns when a lifecycle contains planned provider tasks without registered public MCP submit tools, keeping the HUD compact while avoiding dead-action suggestions.
- Covered the full overview path so `unsupported_provider_task_preview` reaches the existing Generated Assets surface without adding a new panel.

### D.133 - Honest Uthana lifecycle submit-tool contracts

- Updated generated asset lifecycle manifests so Uthana task types without registered public MCP submit tools are marked `unsupported_task_type` instead of advertising dead tool names.
- Added `planned_submit_tool`, `public_mcp_tool_available`, `unsupported_reason`, and aggregate unsupported-task previews for provider-neutral lifecycle consumers.
- Threaded the unsupported-task metadata into MCP Chat lifecycle summaries so the HUD can warn cleanly without adding another panel or suggesting non-executable Uthana actions.

### D.132 - Paid evidence top-level preflight blockers

- Promoted shared paid-provider evidence gates from the mesh/animation readiness rows into top-level preflight `blocking_gates`.
- `wallet_evidence_recorded` and `spend_confirmation_recorded` now appear alongside Tripo/Uthana provider-key blockers for CLI, CI, and native Resolve Blockers consumers.
- Kept the preflight read-only and no-spend: it reports missing evidence but does not store secrets, call providers, record wallet proof, or confirm spend.

### D.131 - Chat cockpit top-level preflight blocker

- Added `chat_server_reachable` to the IDE companion preflight top-level `blocking_gates` whenever the MCP Chat endpoint is unavailable.
- Kept the existing `readiness_policy.chat_cockpit` row as the detailed evidence source, so top-level blockers and policy rows now agree for native cockpit recovery.
- Updated preflight tests to prove chat reachability appears in both places without mutating tracked files, starting services, or requiring Unreal Editor.

### D.130 - Native blocker evidence/offline summary

- Threaded selected blocker-resolution `evidence_required` and `can_continue_offline` into the native MCP Chat Resolve Blockers compact summary.
- Updated Resolve Blockers command-palette guidance to inspect `unblock_action`, `fallback_action`, `evidence_required`, and `can_continue_offline` before asking for pasted JSON.
- Kept the HUD clean and read-only: this enriches the existing Resolve Blockers action row without starting services, storing keys, pinging the bridge, calling providers, mutating Unreal, or writing ledger evidence.

### D.129 - Current blocker-resolution gate coverage

- Updated MCP Chat blocker-resolution routing for the blocker names emitted by the current preflight and cockpit policies: chat server reachability, Tripo provider credential setup, Uthana animation provider credential setup, wallet evidence, spend confirmation, and Blueprint pre-read/compile/readback gates.
- Added target-priority ordering so Resolve Blockers prefers bridge recovery first, then native chat reachability, Blueprint safety gates, provider secret setup, wallet evidence, and spend approval.
- Kept the resolver read-only and no-spend: it recommends review/config/evidence actions but does not start services, store keys, call providers, ping the bridge, mutate Unreal, or write ledger rows.

### D.128 - Native generated-animation next-step summary

- Threaded generated-animation `next_safe_action` into the native MCP Chat compact workflow summary for Review Generated Animation Lifecycle.
- Updated the generated-animation command-palette guidance to inspect `next_safe_action` before asking for raw lifecycle JSON or provider/editor proof.
- Preserved the clean HUD model: this enriches existing action summaries and prompts without adding a permanent Uthana panel or invoking provider/editor work.

### D.127 - Uthana animation next-safe-action routing

- Added `next_safe_action` to the MCP Chat generated-animation lifecycle context so Uthana motion work reports the next conservative cockpit step without requiring users to parse raw lifecycle JSON.
- The next-step router distinguishes usage-gate review, text-to-motion confirmation, missing motion-id reconciliation, editor import readiness, quality evidence compilation, and final ledger recording.
- Kept the route offline and HUD-clean: the context names candidate tools but does not call Uthana, download files, import animations, mutate Unreal, run PIE, or write ledger evidence.

### D.126 - Guarded paid-provider smoke lane

- Added `unreal_mcp_server/tests/paid_provider_generative_smoke.py` as a non-default manual provider lane for no-spend Tripo/Uthana auth and quota checks.
- The smoke requires explicit environment approvals before it runs and only checks masked provider config, Tripo API wallet balance, and Uthana account allowance; it does not submit tasks, create motions, download files, import assets, reserve credits, run PIE, or mutate Unreal.
- Updated lane-audit and CI smoke coverage so the repo proves paid-provider tests remain excluded from default `test_*.py` discovery while still having a runnable provider-readiness lane.

### D.125 - Branch policy preflight evidence

- Added Git branch policy evidence to the no-mutation IDE companion preflight so reports include the current branch, WIP development branch, main stable branch, branch role, and whether active work is on the expected WIP branch.
- Threaded branch policy into `platform_stability`, `branch_policy`, MCP Chat platform preflight, WIP promotion contexts, and native compact workflow summaries.
- Updated CI smoke docs and offline coverage so wip-to-main promotion stays explicit and review-only instead of hidden in convention text.

### D.124 - Cockpit editor-operation checklist review

- Threaded gameplay feature-template `editor_operation_checklist` metadata into MCP Chat work-order, gameplay-template review, Blueprint mutation, queue target, and feature-work card contexts.
- Added bounded editor-operation counts, type/tool previews, and bridge/compile/readback operation counts while preserving the existing graph/component `operation_count`.
- Updated native MCP Chat workflow summaries so Review Gameplay Template Plan, Generate Work Order, Blueprint Mutation, and Queue Editor Actions can show checklist counts without adding HUD clutter.

### D.123 - Gameplay feature template operation checklist

- Extended `unreal_mcp_gameplay_feature_template.v1` packets with `editor_operation_checklist`, a bounded machine-readable list of editor implementation operations.
- Each operation row carries an id, operation type, candidate MCP tools, bridge requirement, compile/readback requirements, readback evidence target, and ledger evidence type.
- Threaded the checklist into IDE companion feature-template work orders so interactable, pickup, AI patrol/chase/attack, objective HUD, save/load, cooldown ability, and replicated combat templates are easier to queue, verify, and repair from the cockpit.

### D.122 - Uthana paid-animation readiness gate

- Added a separate `paid_animation_generation` readiness-policy row to the no-mutation IDE companion preflight so Uthana motion work requires an animation provider key, wallet evidence, and explicit spend confirmation independently from Tripo mesh generation.
- Threaded paid-animation readiness into MCP Chat platform/preflight and readiness summaries without adding another permanent HUD row.
- Updated generated-animation lifecycle review so Uthana motion prompts inspect `paid_animation_generation` gates before text-to-motion, download, import, retarget, AnimGraph, PIE, or ledger proof work.

### D.121 - Repo-local plugin build wrapper default

- Updated `_build_plugin.bat` to default to `RunUAT BuildPlugin` for the repo-local `unreal_plugin/UnrealMCP.uplugin` instead of a stale personal `CombatLevel.uproject` path.
- Extended the IDE companion preflight build-wrapper parser to resolve batch `%~dp0` defaults and `set "PROJECT_PATH=..."`, `set "PLUGIN_PATH=..."`, `set "BUILD_BAT=..."`, and `set "RUN_UAT=..."` assignments.
- Added offline coverage so variable-based batch wrappers can prove project/plugin/tool reference readiness without running Unreal BuildTool.

### D.120 - Native platform stability summary

- Updated the native MCP Chat Platform Preflight and WIP Promotion workflow summaries to include platform-stability readiness, build-wrapper status, build health, and missing build-wrapper reference counts.
- Updated the command-palette prompts for those review actions so agents inspect build-wrapper reference readiness before risky work or WIP-to-main movement.
- This keeps the signal inside the existing `Actions`/`Next:` surfaces without adding another permanent HUD row.

### D.119 - Build wrapper readiness policy gate

- Added `platform_stability` to the IDE companion preflight `readiness_policy`, with `build_wrapper_references_ready` as an explicit gate.
- Threaded build-wrapper status, build health, and missing reference counts into MCP Chat platform preflight and WIP promotion contexts.
- The preflight now reports `ready_for_platform_stability` and includes unresolved build-wrapper references in `blocking_gates` without weakening bridge, paid-generation, or Blueprint mutation gates.

### D.118 - Build wrapper reference preflight

- Extended `scripts/audit_ide_companion_readiness.py` to inspect known local build wrappers and report hard-coded `.uproject` and `Build.bat` references.
- Added `build_wrapper_status`, project/tool readiness flags, missing reference lists, and `build_health` so stale successful AutomationTool logs cannot hide a wrapper that no longer resolves locally.
- Updated offline preflight tests and CI smoke docs to keep build-health reporting read-only and reproducible.

### D.117 - Native generated animation evidence workflow summaries

- Extended the native MCP Chat workflow parser with compact summaries for `compile_generated_animation_evidence` and `record_generated_animation_evidence`.
- Added command-palette workflow prompts for compiling the D115 generated-animation evidence receipt and recording generated-animation ledger evidence from cockpit-selected context.
- Kept the clean cockpit HUD model: the existing `Actions` launcher and `Next:` line now carry Uthana animation evidence context without adding a permanent HUD row or invoking providers/editor mutation.

### D.116 - Generated animation evidence cockpit routing

- Added `compile_generated_animation_evidence` and `record_generated_animation_evidence` to the MCP Chat cockpit workflow rail.
- Extended evidence-recording rows with structured generated-animation metadata so Uthana motion, expected import path, target skeleton, missing proof stages, and the D115 compiler tool can be surfaced without parsing lifecycle JSON.
- Kept the route no-spend and no-editor-mutation: the new cockpit actions compile or record evidence context only and do not call Uthana, download files, import animations, run PIE, or bypass ledger/readiness gates.

### D.115 - Generated animation evidence compiler

- Added `gen_compile_generated_animation_evidence`, an offline/no-spend receipt compiler for Uthana-generated animation lifecycles.
- The compiler combines text-to-motion, motion metadata, download allowance, download, import, retarget/readback, AnimGraph or state-machine, PIE/runtime, ledger, and approval evidence into `unreal_mcp_generated_animation_evidence.v1`.
- Generated animation evidence remains `proven=False` until motion, download, import, retarget, AnimGraph, PIE, ledger, and human approval gates are all ready.
- Updated the tool-count baseline to 665 for the intentionally added public MCP evidence tool.

### D.114 - Guarded Uthana motion task tools

- Added public MCP tools for the Uthana motion lifecycle: `gen_uthana_get_account`, `gen_uthana_text_to_motion`, `gen_uthana_get_motion`, `gen_uthana_check_download_allowed`, `gen_uthana_download_motion`, and `gen_uthana_import_animation_to_project`.
- Kept Uthana generation and download behind explicit `confirm_usage=True` gates, with account/org allowance and download-allowed checks available before consuming provider quota.
- Added authenticated Uthana GraphQL and motion download helpers without returning raw API keys in MCP outputs.
- Added a bridge-ping gate before the Uthana Unreal import wrapper mutates the editor, and the import result still reports retarget, AnimGraph, PIE, and ledger proof as remaining quality gates.

### D.113 - Dual provider config and Uthana secret preservation

- Extended `gen_save_provider_config` so it can store, clear, and report Uthana animation provider credentials alongside Tripo mesh credentials without exposing either key in MCP JSON output.
- Added Uthana animation defaults to saved generative settings: `animation_provider`, `animation_output_folder`, and `uthana_default_character_id`.
- Hardened the native Generate Settings save path so saving Tripo settings preserves existing `UTHANA_API_KEY` entries in `Saved/MCPChat/secrets.json` instead of overwriting the secrets file.
- Updated the native compact auth status line to show both Tripo and Uthana credential sources without adding another HUD block.

### D.112 - Uthana animation provider lifecycle contract

- Added Uthana as a provider-neutral animation/motion provider alongside Tripo, with metadata for text/video motion, retargeting, FBX/GLB/BVH outputs, and Unreal animation import handoff.
- Added IDE companion session planning for generated Uthana motion prompts in AI encounter slices, including motion seconds, target skeleton, default character id, and explicit animation retarget/readback gates.
- Extended generated asset lifecycle manifests and MCP Chat lifecycle summaries with `animation_assets`, `preview_animation_assets`, `animation_asset_count`, `animation_pending_count`, and a read-only `review_generated_animation_lifecycle_gate` workflow action.
- Added native compact workflow summary support and a Review Generated Animation Lifecycle Gate palette prompt that prefers `outputs.workflow_actions.review_generated_animation_lifecycle_gate.target_generated_animation_lifecycle_context`.
- This is contract/review-only; it does not call Uthana, download files, import animations, mutate Unreal, run queued actions, spend credits, compile, save assets, write ledger evidence, or bypass readiness gates.

### D.111 - Generated asset quality proof gate review workflow target

- Added `review_generated_asset_quality_proof_gate` to MCP Chat `workflow_actions`, backed by `chat_get_cockpit_overview`, so material, collision, viewport, and ledger proof requirements can be inspected before generated-asset quality work or evidence recording.
- Added `target_generated_asset_quality_proof_context` with selected asset details, quality gate/evidence counts, missing proof count, material/collision/viewport/ledger proof flags, missing editor gates, imported-asset requirement, and quality-proof-ready state.
- Added native compact workflow summary support and a Review Generated Asset Quality Proof Gate palette prompt that prefers `outputs.workflow_actions.review_generated_asset_quality_proof_gate.target_generated_asset_quality_proof_context`.
- This is review-only; it does not capture viewports, mutate Unreal, import assets, replace placeholders, run queued actions, call providers, spend credits, compile, save assets, write ledger evidence, or bypass readiness gates.

### D.110 - Generated asset provider task/download gate review workflow target

- Added `review_generated_asset_provider_task_gate` to MCP Chat `workflow_actions`, backed by `chat_get_cockpit_overview`, so provider task status, task ids, status/download/import tools, downloaded paths, and missing task/download stages can be inspected before provider or import work.
- Added `target_generated_asset_provider_task_context` with selected asset details, provider pending/success counts, task-id missing count, download/import pending counts, paid-generation missing gates, stage preview, and provider-task-ready state.
- Added native compact workflow summary support and a Review Generated Asset Provider Task Gate palette prompt that prefers `outputs.workflow_actions.review_generated_asset_provider_task_gate.target_generated_asset_provider_task_context`.
- This is review-only; it does not call providers, poll status, download files, import assets, mutate Unreal, spend credits, run queued actions, write ledger evidence, or bypass readiness gates.

### D.109 - Generated asset replacement gate review workflow target

- Added `review_generated_asset_replacement_gate` to MCP Chat `workflow_actions`, backed by `chat_get_cockpit_overview`, so placeholder-to-generated asset mapping can be inspected before replacement work.
- Added `target_generated_asset_replacement_context` with selected placeholder asset path, expected/imported generated asset path, quality proof counts, editor readiness gates, missing replacement stages, replacement-ready state, and no-mutation/no-ledger-write policy.
- Added native compact workflow summary support and a Review Generated Asset Replacement Gate palette prompt that prefers `outputs.workflow_actions.review_generated_asset_replacement_gate.target_generated_asset_replacement_context`.
- This is review-only; it does not replace placeholders, mutate Unreal, import assets, run queued actions, call providers, spend credits, compile, save assets, write ledger evidence, or bypass readiness gates.

### D.108 - Generated asset lifecycle gate review workflow target

- Added `review_generated_asset_lifecycle_gate` to MCP Chat `workflow_actions`, backed by `chat_get_cockpit_overview`, so prompt/provider/task/placeholder/import/quality/evidence lifecycle completeness can be inspected before provider, import, or ledger work.
- Added `target_generated_asset_lifecycle_context` with manifest counts, selected asset details, provider/import/quality/placeholder stage counts, preferred provider preview, manifest path preview, stop-condition count, future network/spend flags, and missing-stage preview.
- Added native compact workflow summary support and a Review Generated Asset Lifecycle Gate palette prompt that prefers `outputs.workflow_actions.review_generated_asset_lifecycle_gate.target_generated_asset_lifecycle_context`.
- This is review-only; it does not call providers, spend credits, import assets, mutate Unreal, replace placeholders, run queued actions, write ledger evidence, or bypass readiness gates.

### D.107 - Generated asset import gate review workflow target

- Added `review_generated_asset_import_gate` to MCP Chat `workflow_actions`, backed by `chat_get_cockpit_overview`, so import/quality-pending generated assets can be inspected before editor import, placeholder replacement, material/collision work, viewport proof, or ledger recording.
- Added `target_generated_asset_import_context` with selected import/quality-pending asset details, expected/imported asset paths, placeholder state, quality proof counts, missing editor gates, bridge requirement, and stop-before-import-or-quality-work policy.
- Added native compact workflow summary support and a Review Generated Asset Import Gate palette prompt that prefers `outputs.workflow_actions.review_generated_asset_import_gate.target_generated_asset_import_context`.
- This is review-only; it does not import assets, mutate Unreal, replace placeholders, run queued actions, call providers, spend credits, compile, save assets, write ledger evidence, or bypass readiness gates.

### D.106 - Live editor bridge gate review workflow target

- Added `review_live_editor_bridge_gate` to MCP Chat `workflow_actions`, backed by `chat_get_cockpit_overview`, so bridge reachability, queued editor actions, runtime/PIE readiness, and evidence gates can be inspected before live editor work.
- Added `target_live_editor_context` from platform preflight, readiness policy, editor queues, next-safe-step, execution review, and runtime review, including bridge state, queue counts, next action, runtime proof counts, and stop-before-editor-or-PIE policy.
- Added native compact workflow summary support and a Review Live Editor Bridge Gate palette prompt that prefers `outputs.workflow_actions.review_live_editor_bridge_gate.target_live_editor_context`.
- This is review-only; it does not mutate Unreal, manually ping the bridge, run PIE, execute queued actions, compile, save assets, call providers, spend credits, write ledger evidence, or bypass readiness gates.

### D.105 - WIP promotion gate review workflow target

- Added `review_wip_promotion_gate` to MCP Chat `workflow_actions`, backed by `chat_get_cockpit_overview`, so experimental WIP can be reviewed against main-promotion stability gates before release movement.
- Added `target_wip_promotion_context` from platform preflight, high-value wrapper coverage, test-lane audit, and readiness policy evidence, including registry, build, dirty-state, lane, wrapper, and chat-cockpit gate status.
- Added native compact workflow summary support and a Review WIP Promotion Gate palette prompt that prefers `outputs.workflow_actions.review_wip_promotion_gate.target_wip_promotion_context`.
- This is review-only; it does not create branches, stage files, commit, merge, mutate Unreal, call providers, spend credits, run live lanes, or bypass readiness gates.

### D.104 - Platform preflight gate review workflow target

- Added `review_platform_preflight_gate` to MCP Chat `workflow_actions`, backed by `chat_get_cockpit_overview`, so tool-count reproducibility, dirty-state risk, bridge/chat/provider/build status, and readiness gates can be inspected before risky work.
- Added `target_platform_preflight_context` from `scripts/audit_ide_companion_readiness.py` with registry counts, bridge/chat booleans, provider configuration source, build-wrapper status, paid/Blueprint missing-gate previews, and stop-before-editor-provider-or-blueprint policy.
- Added native compact workflow summary support and a Review Platform Preflight Gate palette prompt that prefers `outputs.workflow_actions.review_platform_preflight_gate.target_platform_preflight_context`.
- This is review-only; it does not mutate Unreal, manually ping the bridge, call providers, spend credits, write ledger evidence, compile, save assets, run test lanes, or expose provider secrets.

### D.103 - Blueprint mutation gate review workflow target

- Added `review_blueprint_mutation_gate` to MCP Chat `workflow_actions`, backed by `chat_get_cockpit_overview`, so bridge, Blueprint pre-read, compile-plan, and readback-plan gates can be inspected before graph or component mutations.
- Added `target_blueprint_mutation_context` with readiness state, missing/required/evidence gate previews, selected work-order template counts, queue counts, bridge-blocked count, explicit pre-read/compile/readback booleans, and stop-before-blueprint-mutation policy.
- Added native compact workflow summary support and a Review Blueprint Mutation Gate palette prompt that prefers `outputs.workflow_actions.review_blueprint_mutation_gate.target_blueprint_mutation_context`.
- This is review-only; it does not mutate Blueprints, compile, save assets, run queued actions, write ledger evidence, ping the bridge, or bypass readiness gates.

### D.102 - Test lane gate review workflow target

- Added `review_test_lane_gates` to MCP Chat `workflow_actions`, backed by `chat_get_cockpit_overview`, so offline, live-bridge, live/manual, paid-provider, and manual test lane separation can be reviewed from the editor workflow rail.
- Added `target_test_lane_context` with default discovery pattern, lane counts, violation count/preview, bounded lane previews, audit script path, CI smoke doc path, default-CI-safe state, and no-editor-mutation policy.
- Added native compact workflow summary support and a Review Test Lane Gates palette prompt that prefers `outputs.workflow_actions.review_test_lane_gates.target_test_lane_context`.
- This is review-only; it does not run live bridge tests, paid-provider tests, mutate Unreal, call providers, spend credits, or bypass readiness gates.

### D.101 - Gameplay template plan review workflow target

- Added `review_gameplay_template_plan` to MCP Chat `workflow_actions`, backed by `chat_get_cockpit_overview`, so the selected `unreal_mcp_gameplay_feature_template.v1` work-order plan can be reviewed from the editor workflow rail before queueing editor work.
- Added `target_gameplay_template_context` with template name, target phase, asset/operation/compile/PIE/evidence/repair counts, ownership domains, bounded preview rows, readiness state, missing editor gates, and stop-before-editor-mutation policy.
- Added native compact workflow summary support and a Review Gameplay Template Plan palette prompt that prefers `outputs.workflow_actions.review_gameplay_template_plan.target_gameplay_template_context`.
- This is review-only; it does not mutate Unreal, queue actions, run PIE, write ledger evidence, call providers, spend credits, or bypass readiness gates.

### D.100 - Bridge wrapper coverage review workflow target

- Added `review_bridge_wrapper_coverage` to MCP Chat `workflow_actions`, backed by `chat_get_cockpit_overview`, so the high-value native bridge wrapper audit is visible from the editor workflow rail.
- Added `target_bridge_wrapper_context` with coverage status, capability counts, command count, failing capability preview, audit script path, bridge registry tool path, and no-editor-mutation policy.
- Added native compact workflow summary support and a Review Bridge Wrapper Coverage palette prompt that prefers `outputs.workflow_actions.review_bridge_wrapper_coverage.target_bridge_wrapper_context`.
- This is review-only; it does not mutate Unreal, ping the bridge, edit Blueprint assets, call providers, spend credits, or bypass readiness gates.

### D.99 - Provider spend gate review workflow target

- Added `review_provider_spend_gate` to MCP Chat `workflow_actions`, backed by `chat_get_cockpit_overview`, so provider credentials, wallet evidence, spend confirmation, and the selected provider-pending asset can be inspected before any paid provider task.
- Added `target_provider_spend_context` with paid-generation readiness state, provider-pending/placeholder counts, missing gate preview, evidence requirements, selected target asset/provider/next gate, fallback tool hints, and stop-before-provider-call policy.
- Added native compact workflow summary support and a Review Provider Spend Gate palette prompt that prefers `outputs.workflow_actions.review_provider_spend_gate.target_provider_spend_context`.
- This is review-only; it does not submit provider tasks, spend credits, call providers, import assets, mutate Unreal, write ledger evidence, or bypass readiness gates.

### D.98 - Evidence requirements review workflow target

- Added `review_evidence_requirements` to MCP Chat `workflow_actions`, backed by `chat_get_cockpit_overview`, so pending, blocked, and recorded proof requirements can be inspected before ledger writes.
- Added `target_evidence_review_context` with evidence item counts, selected target evidence id/type/context, artifact preview, bridge/network/spend requirements, record tool, and stop-before-ledger-write policy.
- Added native compact workflow summary support and a Review Evidence Requirements palette prompt that prefers `outputs.workflow_actions.review_evidence_requirements.target_evidence_review_context`.
- This is review-only; it does not mutate Unreal, write ledger evidence, call providers, spend credits, ping the bridge, or bypass readiness gates.

### D.97 - Editor queue review workflow target

- Added `review_editor_queue` to MCP Chat `workflow_actions`, backed by `chat_get_cockpit_overview`, so queued editor actions can be inspected from the workflow rail before queue recompilation or execution.
- Added `target_queue_review_context` with queue/action counts, executable/blocked/bridge-blocked queue counts, selected queue path/name/phase, next action id/tool, evidence count, blocking gate preview, and stop-before-editor-mutation policy.
- Added native compact workflow summary support and a Review Editor Queue palette prompt that prefers `outputs.workflow_actions.review_editor_queue.target_queue_review_context`.
- This is review-only; it does not mutate Unreal, run queued actions, record evidence, ping the bridge, call providers, spend credits, or bypass readiness gates.

### D.96 - Placeholder manifest workflow target

- Added `compile_placeholder_manifest` to MCP Chat `workflow_actions`, backed by `skill_compile_ide_companion_placeholder_manifest`, so no-spend placeholder fallback is reachable from the workflow rail.
- Added `target_placeholder_context` with session/ledger path, session-plan state, readiness state, blocker count, generated-asset provider/import/quality/ready/placeholder counts, selected target asset, placeholder root, and stop-before-editor-or-provider policy.
- Added native compact workflow summary support and updated the Placeholder Manifest palette prompt to prefer `outputs.workflow_actions.compile_placeholder_manifest.target_placeholder_context`.
- This compiles or guides a placeholder manifest only; it does not queue editor actions, mutate Unreal, call providers, spend credits, import assets, replace placeholders, or bypass readiness gates.

### D.95 - Work order workflow target

- Added `generate_work_order` to MCP Chat `workflow_actions`, backed by `skill_compile_ide_companion_work_order`, so work-order compilation is reachable from the workflow rail.
- Added `target_work_order_context` with session/ledger path, session-plan/status availability, target phase, readiness state, blocker count, status completed phase count, template operation/compile/PIE/evidence counts, and stop-before-editor-mutation policy.
- Added native compact workflow summary support and updated the Work Order palette prompt to prefer `outputs.workflow_actions.generate_work_order.target_work_order_context`.
- This compiles or guides a no-spend work order only; it does not queue editor actions, mutate Unreal, call providers, spend credits, or bypass readiness gates.

### D.94 - Status refresh workflow target

- Added `refresh_companion_status` to MCP Chat `workflow_actions`, backed by `skill_compile_ide_companion_status`, so status refresh is reachable from the workflow rail instead of only the command palette.
- Added `target_status_context` with session/ledger path, session-plan availability, event/completed phase counts, next phase/tool, readiness state, blocker count, queue count, evidence item count, generated asset count, runtime state, and stop-before-editor-or-provider policy.
- Added native compact workflow summary support and updated the Status palette prompt to prefer `outputs.workflow_actions.refresh_companion_status.target_status_context`.
- This compiles or guides a no-spend status receipt only; it does not mutate Unreal, call providers, spend credits, or bypass readiness gates.

### D.93 - Start session workflow target

- Added `target_start_context` to `start_companion_session` so the workflow rail summarizes session startup state before compiling or refreshing a companion plan.
- Context includes session name, existing ledger state, event/completed phase counts, readiness state, blocked policy count, queue count, generated asset count, recommended next path, and stop-before-editor-or-provider policy.
- Added native compact workflow summary support and updated the Start Session palette prompt to prefer `outputs.workflow_actions.start_companion_session.target_start_context`.
- This is planning/orientation-only; it does not mutate Unreal, call providers, spend credits, or bypass readiness gates.

### D.92 - Dashboard workflow target

- Added `target_dashboard_context` to `show_companion_dashboard` so the workflow rail summarizes the selected ledger/dashboard state before opening the dashboard.
- Context includes ledger/event/completed phase counts, readiness state, blocker count, queue counts, evidence item count, generated asset state/count, runtime review state, repair loop state, and stop-before-editor-mutation policy.
- Added native compact workflow summary support and updated the Dashboard palette prompt to prefer `outputs.workflow_actions.show_companion_dashboard.target_dashboard_context`.
- This is inspection/display-only; it does not mutate Unreal, call providers, spend credits, or bypass readiness gates.

### D.91 - Resume session workflow target

- Added `target_resume_context` to the `resume_companion_session` workflow action so agents can inspect the selected ledger before resuming.
- The context summarizes session name, ledger path, event count, completed phase count, latest phase, next phase/tool, work-order phase, blocking gates, preview event count, and a stop-before-editor-mutation policy.
- Added native compact workflow summary support for `Resume Companion Session`, including event count, completed phase count, blocker count, next phase, and next tool.
- Updated the native resume command-palette prompt to prefer `outputs.workflow_actions.resume_companion_session.target_resume_context` before raw ledger/path handling.

### D.90 - Readiness policy workflow target

- Added `target_readiness_policy_context` to the `check_readiness` workflow action so agents can inspect editor, paid-generation, and Blueprint readiness gates before refreshing preflight.
- The context summarizes blocked policy areas, missing gate count/preview, recommended tools, and a stop-before-editor-or-provider policy without requiring raw readiness JSON.
- Added native compact workflow summary support for `Check Readiness`, including policy area count and missing gate preview.
- Updated the native readiness command-palette prompt to prefer `outputs.workflow_actions.check_readiness.target_readiness_policy_context` before pasted readiness JSON.

### D.89 - Generated asset gate review workflow

- Added a read-only `review_generated_asset_gate` workflow action that targets the generated-asset quality gate before any provider submission, import, replacement, resolution, or evidence recording.
- Added `target_generated_asset_review_context` with aggregate provider/import/quality/placeholder counts plus the cockpit-selected target asset and stop-before-provider-or-import policy.
- Added a native `Review Generated Asset Gate` command-palette workflow entry and compact workflow summary for generated-asset gate state, selected asset, and provider/import/quality counts.
- This review layer does not submit provider tasks, import assets, mutate Unreal, record evidence, spend credits, or bypass readiness gates.

### D.88 - Generated asset evidence recording target

- Added a dedicated `record_generated_asset_evidence` workflow action that targets `record_generated_asset_quality_gate` while preserving the generic `record_evidence` selector for readiness and other pending proof.
- Reused structured generated-asset metadata in `target_evidence_context.generated_asset`, including asset id/name/role, provider, lifecycle state, task status, next gate, manifest/import paths, placeholder state, and quality proof counts.
- Added a native `Record Generated Asset Evidence` command-palette workflow entry and compact workflow summary for asset state, provider, quality gates, and artifact count.
- This records or explains existing generated-asset lifecycle proof only: it does not submit provider tasks, import assets, ping the bridge, mutate Unreal, spend credits, or bypass readiness gates.

### D.87 - Queued action evidence recording target

- Added structured queued-action metadata to `record_editor_queue_*` evidence rows, including queue path/name, target phase, selected action id/tool/label, action counts, argument keys, bridge state, execution readiness, and evidence preview.
- Promoted that metadata into `target_evidence_context.queued_action` so evidence workflows can inspect queued editor proof requirements without parsing artifact labels.
- Added a dedicated `record_queued_action_evidence` workflow action that targets `record_editor_queue_1` while preserving the generic `record_evidence` selector for readiness and other pending proof.
- Added a native `Record Queued Action Evidence` command-palette workflow entry and compact workflow summary for queued evidence state, selected tool, artifact count, and argument count.
- This records or explains existing compile/readback proof only: it does not execute queued work, ping the bridge, mutate Unreal, call providers, spend credits, or bypass readiness gates.

### D.86 - Runtime evidence recording target

- Added structured runtime-verification metadata to the `record_runtime_verification` evidence row, including target phase, bridge state, PIE step count, compile-check count, evidence requirement count, runtime evidence count, blocked/pending/recorded row counts, proof preview, and compile-check preview.
- Promoted that metadata into `target_evidence_context.runtime_verification` so Record Evidence workflows can inspect runtime proof requirements without parsing artifact labels.
- Added a dedicated `record_runtime_evidence` workflow action that targets the runtime verification evidence row while preserving the generic `record_evidence` selector for readiness and other pending proof.
- Added a native `Record Runtime Evidence` command-palette workflow entry and compact workflow summary for runtime evidence state, artifact count, PIE step count, and proof item count.
- This records or explains existing runtime proof only: it does not run PIE, ping the bridge, mutate Unreal, call providers, spend credits, or bypass readiness gates.

### D.85 - Runtime verification review workflow

- Added a read-only `runtime_review` packet to MCP Chat cockpit overview, derived from the existing runtime verification checklist.
- The packet summarizes target phase, bridge state, PIE validation count, compile-check count, evidence requirement count, runtime evidence already recorded, blocked/pending/recorded checklist counts, proof previews, and stop-after-runtime-probe policy.
- Added a `review_runtime_verification` workflow action with compact `target_runtime_review_context` so agents can inspect PIE, screenshot, actor-state, compile, and readback proof gates before attempting runtime verification.
- Added a native `Review Runtime Verification` command-palette workflow entry and compact workflow summary for runtime review state, PIE step count, proof item count, and recorded runtime evidence count.
- This is inspection-only: it does not run PIE, ping the bridge, mutate Unreal, record evidence, call providers, spend credits, or bypass readiness gates.

### D.84 - Repair review context

- Added a read-only `repair_review` packet to MCP Chat cockpit overview, derived from the existing repair loop and failure triage.
- The packet summarizes the selected repair hint, bridge state, failure-signal counts, blocked/needs-repair counts, repair instruction count, stop-condition count, compile/evidence previews, and stop-after-one-repair-attempt policy.
- Threaded a compact `target_repair_review_context` into the `repair_failed_step` workflow action so native prompts and agents inspect the reviewed repair gate before raw repair-loop rows.
- Updated the native Repair Failed Step command-palette prompt and compact workflow summary to surface repair review state, recovery signal count, and evidence preview count.
- This is inspection-only: it does not compile a repair work order, mutate Unreal, run bridge commands, record evidence, call providers, spend credits, or bypass readiness gates.

### D.83 - Queued execution review context

- Added a read-only `execution_review` packet to MCP Chat cockpit overview, derived from the existing next-safe-step gate and evidence checklist.
- The packet summarizes the selected queued action, bridge requirement, missing gates, after-execution evidence count/preview, execution policy, and the rule to stop after one action.
- Threaded a compact `target_execution_review_context` into the `execute_next_safe_step` workflow action so native prompts and agents inspect the reviewed gate before the raw execute target.
- Updated the native Execute Next Safe Step command-palette prompt and compact workflow summary to surface review state, blocker count, and required evidence count.
- This does not execute queued work, ping the bridge, mutate Unreal, record evidence, call providers, spend credits, or bypass readiness gates.

### D.82 - Evidence ledger workflow action

- Added a read-only `show_evidence_ledger` MCP Chat workflow action that routes from the cockpit to `chat_get_cockpit_ledger_detail`.
- The action carries `target_evidence_ledger_context` with ledger path, session name, event counts, artifact counts, latest evidence phase/type, latest artifact preview, and a bounded timeline preview.
- Added a native `Show Evidence Ledger` command-palette workflow entry so the compact `Actions` launcher can open ledger inspection guidance without adding another permanent HUD row.
- The native MCP Chat panel can summarize the selected evidence-ledger target in compact workflow text when that action is the best next action.
- This is inspection-only: it does not record evidence, mutate Unreal, execute queued editor work, call providers, spend credits, or mark missing proof as complete.

### D.81 - Record Evidence target context

- Added a compact `target_evidence_context` to the `record_evidence` MCP Chat workflow action.
- The context promotes the selected evidence row's phase, type, state, artifact count, bounded artifact preview, and suggested summary so native prompts and agents do not need to parse raw checklist rows.
- Generated-asset evidence rows also expose a filtered `generated_asset` context derived from structured metadata, including asset id/name, provider, current state, next gate, manifest/import paths, placeholder state, and quality proof preview.
- The native MCP Chat panel now prefers `target_evidence_context` when summarizing the `Record:` target and falls back to `target_evidence_item` for compatibility.
- Renamed the native command-palette status parameter that shadowed the `StatusText` widget member so standalone UE 5.6 `BuildPlugin` compiles under warning-as-error settings.
- This remains read-only: it does not mutate Unreal, write ledger evidence, submit provider tasks, spend credits, import assets, or replace placeholders.

### D.80 - Generated asset evidence metadata

- Added optional `metadata` to MCP Chat evidence-recording checklist rows and populated it for `record_generated_asset_quality_gate`.
- The generated-asset metadata carries asset id, asset name, role, provider, provider/import/quality state, task status, next gate, manifest path, expected/imported asset paths, placeholder availability, quality-gate count, quality-evidence count, and quality-gate preview.
- This lets Record Evidence workflows and future native summaries use structured asset context instead of parsing `asset:*`, `state:*`, or `manifest:*` artifact labels.
- The metadata is read-only and does not submit provider tasks, spend credits, import assets, replace placeholders, mutate Unreal, or write ledger evidence.

### D.79 - Generated asset quality evidence row

- Extended the MCP Chat evidence-recording checklist with `record_generated_asset_quality_gate`, derived from the selected generated asset quality-gate item.
- The row captures the target asset, current provider/import/quality state, next gate, manifest path, quality-gate preview, and expected import path so ledger evidence can be recorded against the actual asset blocker instead of only the lifecycle manifest.
- Provider-pending rows remain offline-recordable; import-pending and quality-pending rows are marked bridge-dependent because they need import/readback/viewport proof.
- Kept the row read-only: it does not submit provider tasks, spend credits, import assets, replace placeholders, mutate Unreal, or write ledger evidence by itself.

### D.78 - Generated asset workflow palette command

- Added a dedicated native command-palette workflow entry for `Resolve Generated Asset` so the cockpit-selected generated-asset target can be invoked from the compact `Actions` launcher instead of relying on the broader lifecycle command.
- The inserted prompt tells agents to inspect `outputs.workflow_actions.resolve_generated_asset.target_generated_asset_context` before raw quality-gate rows and to use the selected asset id, manifest path, state, next gate, placeholder availability, import path, and quality-gate preview.
- Kept the entry insertion-only and gate-respecting: it does not submit provider tasks, spend credits, import assets, replace placeholders, mutate Unreal, or record evidence by itself.

### D.77 - Generated asset workflow target

- Added a `resolve_generated_asset` cockpit workflow action that selects the first generated asset needing provider, import, quality, placeholder, or evidence work from `generated_asset_quality_gate.items`.
- The action carries `target_generated_asset_context` plus compact arguments such as manifest path, target asset id, current state, and next gate so agents can continue from the exact asset blocker instead of raw lifecycle JSON.
- Threaded the generated-asset target into the native MCP Chat compact `Next:` workflow priority and updated the Generated Asset Lifecycle palette prompt to inspect that target before falling back to quality-gate rows or pasted lifecycle data.
- Kept the flow read-only: it does not submit provider tasks, spend credits, import assets, replace placeholders, mutate Unreal, or record evidence by itself.

### D.76 - High-value wrapper coverage audit

- Added `scripts/audit_high_value_wrapper_coverage.py` as an offline Phase 1 guard for the roadmap's named bridge-wrapper priorities: BT/Blackboard assignment, Blueprint reparenting, Construction Script entry nodes, function-with-pins, math/comparison graph primitives, SpawnActor class assignment, AnimGraph sequence-player links, and Niagara component attachment.
- The audit checks each capability for C++ route coverage, Python bridge references, registered tool signatures, offline test evidence, and documentation evidence without pinging the bridge, mutating Unreal, or calling providers.
- Added `test_phase1_high_value_wrapper_coverage.py` and wired the audit into `docs/ci-smoke.md` so these wrappers stay closed as the tool evolves.

### D.75 - Zero-enabled workflow action cue

- Updated the native `Actions` button to show the enabled workflow-action count whenever cockpit workflow actions exist, including `Actions (0)` when every workflow action is currently gated or disabled.
- This makes a blocked workflow rail visible at a glance without adding another cockpit row or changing the clean HUD layout.
- The cue remains display-only: it does not run tools, ping the bridge, mutate Unreal, record evidence, or call providers.

### D.74 - Workflow action count on native Actions button

- Added parsed workflow-action totals to the native MCP Chat cockpit overview, including total action count and enabled action count from the backend `workflow_actions` array.
- The compact `Actions` button now shows the enabled count when available and its tooltip reports enabled vs total workflow actions, giving the developer a quick readiness cue without adding another HUD row.
- The count remains display-only: it does not run tools, ping the bridge, mutate Unreal, record evidence, or call providers.

### D.73 - Exact workflow category filtering

- Hardened native command-palette matching so known category tokens such as `workflow`, `tool`, `asset`, `prompt`, and `kb` match the entry kind exactly before falling back to fuzzy text search.
- This keeps the IDE Cockpit `Actions` launcher focused on actual workflow entries instead of incidental prompt text that happens to mention workflow.
- Normal search remains fuzzy for non-category terms; the change is display-only and does not execute tools, ping the bridge, mutate Unreal, record evidence, or call providers.

### D.72 - Workflow prompts prefer selected cockpit targets

- Updated the native Queue Editor Actions, Execute Next Safe Step, and Repair Failed Step command-palette prompts to inspect their selected `workflow_actions` target packets before falling back to broader cockpit outputs or pasted JSON.
- Queue prompts now point at `target_queue_context`, `arguments.target_phase`, `arguments.ledger_path`, and ledger detail lookup; Execute prompts prefer `target_execute_context`; Repair prompts prefer `target_repair_context`.
- Kept the palette insertion-only and gate-respecting: the prompts do not run tools, ping the bridge, mutate Unreal, record evidence, or call providers by themselves.

### D.71 - Workflow action launcher uses explicit palette category

- Hardened the native IDE Cockpit `Actions` launcher so it filters the command palette by an explicit `workflow` item kind instead of matching only `IDE Companion` label text.
- Tagged the common companion workflow entries as workflow items, including Execute Next Safe Step and Repair Failed Step, so the launcher reliably surfaces the full guided action rail.
- Kept the behavior insertion-only: selecting an entry still inserts the guarded prompt and does not execute tools, ping the bridge, mutate Unreal, record evidence, or call providers by itself.

### D.70 - Compact native workflow action launcher

- Added a compact `Actions` button to the native IDE Cockpit header that opens the command palette already filtered to workflow entries.
- Reused the existing command-palette insertion path so Start, Readiness, Queue, Execute, Record, Repair, Resume, Dashboard, and Blocker actions become easier to reach without adding a cluttered button row.
- Kept the launcher display-only: opening the filtered palette does not run tools, ping the bridge, mutate Unreal, record evidence, or call providers by itself.

---

## 2026-06-14

### D.69 - Cockpit-selected Execute Next Safe Step target

- Added a selected `target_execute_context` packet to the MCP Chat `execute_next_safe_step` workflow action, derived from the first queued editor action preview.
- The action now carries the target action id, tool, label, queue path, target phase, argument keys, bridge requirement, and current executable state while preserving bridge/readiness gating.
- Threaded the execute target into the native compact `Next:` line when Execute Next Safe Step is selected, keeping the next mutation legible without running queued actions by itself.

### D.68 - Cockpit-selected Repair Failed Step target

- Added a selected `target_repair_context` packet to the MCP Chat `repair_failed_step` workflow action, derived from the current repair-loop item preview.
- The action now carries the target repair id, target phase, recommended work-order tool, and evidence tool so repair planning can start from the specific failure hint instead of a generic phase.
- Threaded the repair target into the native compact `Next:` line when Repair Failed Step is selected, keeping the repair workflow guided without running repair tools, mutating Unreal, or recording evidence by itself.

### D.67 - Cockpit-selected Queue Editor Actions target

- Added a `target_queue_context` packet to the MCP Chat `queue_editor_actions` workflow action so queue compilation carries the selected target phase, work-order template name, operation count, compile-check count, evidence count, and ledger path.
- The action now passes `target_phase` and `ledger_path` in its arguments when available, reducing raw ledger lookup before compiling the next bridge-gated editor queue.
- Threaded the queue target into the native compact `Next:` line when Queue Editor Actions is selected, showing the target work context without adding HUD clutter or executing queued actions.

### D.66 - Native Resolve Blockers target next-step summary

- Threaded `workflow_actions.resolve_blockers.target_blocker_resolution` into the native MCP Chat compact `Next:` line when Resolve Blockers is the selected workflow action.
- The summary shows the targeted blocker, preferred strategy, and recommended tool in the existing action text, keeping blocker resolution specific without adding another HUD row.
- Kept the surface display-only: it does not run blocker resolution, ping the bridge, mutate Unreal, record evidence, or call providers by itself.

### D.65 - Cockpit-selected Resolve Blockers target

- Added a backend-selected `target_blocker_resolution` to the MCP Chat `resolve_blockers` workflow action so the cockpit can point at the highest-priority current blocker before showing the full blocker list.
- The action now also carries `target_blocker` and `preferred_strategy` arguments derived from that selected blocker, while preserving `current_blockers` and `outputs.blocker_resolutions` for full context.
- Updated the native Resolve IDE Companion Blockers command-palette prompt to prefer `target_blocker_resolution` before falling back to current blockers or pasted JSON, without invoking tools or mutating Unreal by itself.

### D.64 - Native Resolve Blockers cockpit-aware palette prompt

- Updated the native Resolve IDE Companion Blockers command-palette prompt to inspect `outputs.workflow_actions.resolve_blockers` before asking the developer for pasted dashboard/status JSON.
- The prompt now uses `arguments.current_blockers` as the gate list and `outputs.blocker_resolutions` as the existing resolution preview, keeping blocker resolution aligned with the cockpit workflow rail.
- Kept the command-palette entry as prompt insertion only: it does not compile a resolution packet, mutate Unreal, record evidence, ping the bridge, or call providers by itself.

### D.63 - Cockpit Resolve Blockers workflow action

- Added a first-class `resolve_blockers` entry to MCP Chat `workflow_actions`, using `skill_compile_ide_companion_blocker_resolution` when cockpit blocking gates exist.
- The action carries the current blocking gates through `current_blockers` and points at `outputs.blocker_resolutions` so the workflow rail can choose unblock, placeholder, fallback, or stop paths without raw JSON hunting.
- Updated the native Unreal MCP Chat `Next:` priority rail so Resolve Blockers appears after repair and before queueing when blockers are present, without invoking tools or mutating Unreal by itself.

### D.62 - Cockpit Show Companion Dashboard workflow action

- Added a first-class `show_companion_dashboard` entry to MCP Chat `workflow_actions`, using `skill_compile_ide_companion_dashboard` with the current ledger path when a companion ledger exists.
- Updated the native Unreal MCP Chat `Next:` priority rail so Show Companion Dashboard can appear after Resume Companion Session and before starting a new session when no higher-priority evidence, execution, repair, queue, or readiness action is selected.
- Kept the action metadata display-only: it does not run the dashboard tool, mutate Unreal, record evidence, ping the bridge, or call providers by itself.

### D.61 - Cockpit Resume Companion Session workflow action

- Added a first-class `resume_companion_session` entry to MCP Chat `workflow_actions`, using `skill_resume_ide_companion_session` with the current ledger path when a companion ledger exists.
- Updated the native Unreal MCP Chat `Next:` priority rail so Resume Companion Session can appear after readiness and before starting a new session when no higher-priority evidence, execution, repair, or queue action is selected.
- Kept the action metadata read-only: it does not load, mutate, execute, record evidence, ping the bridge, or call providers by itself.

### D.60 - Native cockpit workflow-action next step

- Updated the native Unreal MCP Chat panel so the existing `Next:` line prefers the cockpit `workflow_actions` rail over legacy suggested-action text.
- The native priority order favors a selected Record Evidence target, then Execute Next Safe Step, Repair Failed Step, Queue Editor Actions, Check Readiness, and Start Companion Session.
- Kept the action line display-only: it does not invoke tools, mutate Unreal, ping the bridge, call providers, record evidence, or execute queued actions.

### D.59 - Native cockpit Record Evidence target summary

- Extended the native Unreal MCP Chat panel to parse `workflow_actions.record_evidence.target_evidence_item` from cockpit overviews.
- Folded the selected evidence target into the existing `Record:` summary so the editor surface can show the next evidence type, state, and artifact count without adding another HUD row.
- Kept the surface read-only: it does not record evidence, ping the bridge, call providers, mutate Unreal, or execute queued actions.

### D.58 - Cockpit-selected Record Evidence target

- Extended MCP Chat workflow actions so `record_evidence` carries a backend-selected `target_evidence_item` from the `evidence_recording` checklist.
- The selector prioritizes pending `record_readiness_policy` rows, then other pending evidence rows, so wallet, spend, bridge, Blueprint pre-read, compile, and readback proof can be recorded before unsafe execution.
- Updated the native Record Evidence command-palette prompt to inspect `outputs.workflow_actions.record_evidence.target_evidence_item` before falling back to raw checklist rows.

### D.57 - Native cockpit evidence-recording summary

- Extended the native Unreal MCP Chat panel to parse the cockpit `evidence_recording` packet and fold a compact `Record:` summary into the existing Evidence line.
- The summary shows recordable evidence item counts and flags when the readiness-policy evidence row is present, keeping wallet, spend, bridge, Blueprint pre-read, compile, and readback proof visible in the editor workflow.
- Updated the Record Evidence command-palette prompt to inspect `outputs.evidence_recording.items`, including `record_readiness_policy`, before asking the developer to record phase proof.

### D.56 - MCP Chat readiness policy evidence rows

- Extended the MCP Chat evidence-recording checklist with a `record_readiness_policy` row derived from the cockpit `readiness_policy` packet.
- The row collects missing editor, paid-generation, and Blueprint evidence gates such as bridge reachability, wallet evidence, spend confirmation, Blueprint pre-read, compile, and readback requirements.
- Kept the evidence row offline-capable and read-only: it does not ping the bridge, call providers, mutate Unreal, submit paid generation, or write the ledger by itself.

### D.55 - Native cockpit readiness policy summary

- Extended the native Unreal MCP Chat panel cockpit parser to read the backend `readiness_policy` packet.
- Folded a compact `Policy:` summary into the existing recovery strip, showing blocked policy count and a bounded preview of missing editor, paid-generation, or Blueprint gates.
- Kept the HUD clean and read-only: the summary does not ping the bridge, call providers, mutate Unreal, execute queued actions, or record evidence.

### D.54 - MCP Chat readiness policy packet

- Added a read-only `readiness_policy` packet to the MCP Chat cockpit overview, derived from local ledger blocking gates, queued-action bridge state, and feature work-order requirements.
- The packet exposes editor-mutation, paid-generation, and Blueprint-mutation policy rows with allowed state, required gates, missing gates, and evidence requirements.
- Added a compact Readiness Policy cockpit card so bridge, spend, wallet, Blueprint pre-read, compile, and readback blockers are visible without opening CLI preflight JSON.

### D.53 - Preflight structured readiness policy

- Extended `scripts/audit_ide_companion_readiness.py` with a `readiness_policy` block that exposes editor-mutation, paid-generation, Blueprint-mutation, and chat-cockpit gates.
- The policy keeps paid generation blocked until provider key, wallet evidence, and explicit spend confirmation are present, and keeps Blueprint mutation blocked until action-specific pre-read, compile, and readback evidence requirements exist.
- Added compact text output for missing editor, paid-generation, and Blueprint-mutation gates, plus focused JSON/policy tests and CI documentation.

### D.52 - Executable test lane separation audit

- Added `scripts/audit_test_lanes.py`, an offline CI audit that classifies test files into offline, live-bridge, live/manual, paid-provider, and manual lanes.
- The audit fails if live-bridge or paid-provider tests are accidentally named with the default `test_*.py` discovery prefix.
- Added focused unit tests and documented the lane audit in `docs/ci-smoke.md` alongside readiness, inventory, docstring, bridge, and no-mutation gates.

### D.51 - Tracked-file no-mutation suite guard

- Added `scripts/run_no_mutation_unittest.py`, a CI runner that snapshots all Git-tracked file hashes before and after default offline unittest discovery.
- Added unit coverage for the runner's mutation detection helpers so an already-dirty but stable file is allowed, while a file changed during the run is reported.
- Updated the CI smoke guide to use the runner as the canonical no-mutation full-suite guard.

### D.50 - Native cockpit asset-quality recovery strip

- Extended the native Unreal MCP Chat cockpit parser to read `generated_asset_quality_gate` from `/chat/cockpit/overview`.
- Folded generated-asset quality state into the compact recovery strip as `Assets: ...`, showing provider-pending, import-pending, quality-pending, ready, and placeholder counts without adding another HUD block.
- Kept the surface read-only: it does not submit provider work, spend credits, download/import assets, mutate Unreal, or record evidence by itself.

### D.49 - MCP Chat generated asset quality gate

- Added a bounded `generated_asset_quality_gate` packet to the MCP Chat cockpit overview, derived from saved generated asset lifecycle manifests.
- Added an Asset Quality card with provider-pending, import-pending, quality-pending, ready, and placeholder counts plus per-asset gate previews.
- Kept the gate read-only: it does not submit provider tasks, spend credits, download/import assets, replace placeholders, inspect meshes in Unreal, or record evidence.

### D.48 - MCP Chat companion workflow palette completion

- Added `Execute Next Safe Step` and `Repair Failed Step` to the native Unreal MCP Chat command palette.
- The new commands insert guarded cockpit instructions: refresh `/chat/cockpit/overview`, inspect `next_safe_step`, `failure_triage`, and `repair_loop`, then proceed only when readiness/bridge gates allow it.
- Kept the HUD uncluttered and safe: these entries do not execute queued actions, mutate Unreal, call providers, or record evidence by themselves.

### D.47 - MCP Chat native cockpit recovery line

- Extended the native Unreal MCP Chat panel cockpit overview parser to read `next_safe_step` and `failure_triage` packets from `/chat/cockpit/overview`.
- Added a compact recovery line to the IDE Cockpit strip so safe-step state, bridge-blocked hints, failure-triage counts, and recommended recovery tools are visible inside Unreal.
- Kept the HUD clean and read-only: the line does not execute queued actions, rerun failed tools, mutate Unreal, call providers, or record evidence.

### D.46 - MCP Chat failure triage summary

- Added a bounded `failure_triage` packet to the MCP Chat cockpit overview, combining ledger failure/error events with next-safe-step, runtime verification, and repair-loop state.
- Added a Failure Triage card with blocked and needs-repair counts, recommended tools, evidence tool, and compact recovery-item previews.
- Kept the triage surface read-only: it does not rerun failed tools, mutate Unreal, call providers, compile Blueprints, launch PIE, or record evidence by itself.

### D.45 - MCP Chat next safe step gate

- Added a bounded `next_safe_step` packet to the MCP Chat cockpit overview, summarizing the first queued editor action, bridge-blocked state, blocking gates, argument keys, and after-execution evidence rows.
- Added a Next Safe Step card so the editor HUD can show ready, blocked, or empty execution state before any bridge mutation is attempted.
- Kept the gate read-only: it does not execute queued actions, mutate Unreal, call providers, or record evidence by itself.

### D.44 - MCP Chat evidence recording checklist

- Added a bounded `evidence_recording` packet to the MCP Chat cockpit overview, turning blockers, editor queue evidence, runtime proof, repair-loop hints, generated asset lifecycle manifests, and feature work-order evidence requirements into recordable rows.
- Added an Evidence Recording card with pending, blocked, and recorded counts plus the `skill_record_ide_companion_evidence` tool hint.
- Kept the checklist read-only: it does not write the ledger, mutate Unreal, call providers, or claim evidence has been collected.

### D.43 - MCP Chat repair loop preview

- Added a bounded `repair_loop` packet to the MCP Chat cockpit overview, derived from latest feature-template repair instructions.
- Added a compact Repair Loop card with bridge-blocked state, repair instruction count, stop-condition count, runtime verification state, compile/readback previews, evidence previews, and recommended work-order/evidence tools.
- Kept the repair loop read-only: it does not mutate Unreal, launch repair tools, loop automatically, or mark evidence as collected.

### D.42 - MCP Chat runtime verification checklist

- Added a bounded `runtime_verification` packet to the MCP Chat cockpit overview, derived from the latest feature-template work order's PIE validation and evidence requirements.
- Added a compact Runtime Verification card with bridge-blocked state, PIE validation count, compile/readback count, evidence requirement count, runtime evidence event count, and item previews.
- Kept the checklist read-only: it does not launch PIE, capture screenshots, mutate Unreal, call providers, or record evidence by itself.

### D.41 - MCP Chat blocker resolution preview

- Added a bounded `blocker_resolutions` packet to the MCP Chat cockpit overview, summarizing selected ledger and editor-queue blockers with severity, recommended strategy/tool, unblock action, fallback action, evidence requirement, and offline-continuation state.
- Extended the Blockers card with hard-blocker count, recommended tools, and compact resolution previews so the HUD can show both blocked gates and next resolution paths.
- Kept the preview local and read-only: it does not refresh readiness, execute queued actions, mutate Unreal, call providers, or record evidence by itself.

### D.40 - MCP Chat local session picker

- Added a read-only `session_picker` packet to the MCP Chat cockpit overview, using local `.mcp_artifacts/ide_companion_sessions` ledgers, editor queues, and generated asset lifecycle manifests.
- Session picker rows now expose selected state, ledger path, phase/event counts, queue/action counts, generated asset and placeholder counts, pending asset counts, blockers, and can-execute state for a clean editor HUD picker.
- Kept the picker local-file-only: it does not execute queued actions, mutate Unreal, call providers, or mark planned work as evidence.

### D.39 - MCP Chat workflow action rail

- Added a stable `workflow_actions` array to the MCP Chat cockpit overview for Start Companion Session, Check Readiness, Queue Editor Actions, Execute Next Safe Step, Record Evidence, and Repair Failed Step controls.
- Each action now exposes id, label, target tool, bounded arguments, enabled state, reason, bridge/ledger/evidence flags, and optional input-source hints so the editor HUD can render clean explicit controls.
- Kept the rail as read-only cockpit state: execution remains gated by durable queues, bridge readiness, and ledger hydration.

### D.38 - MCP Chat feature work-order preview

- Extended the MCP Chat cockpit overview so matching IDE companion ledgers expose a bounded `work_order_template` summary derived from `latest_work_order.feature_template_work`.
- Added a compact `feature_work_order` card for feature template phase, asset, graph/component operation, compile/readback, PIE validation, repair, and evidence counts/previews.
- Kept the surface read-only and bridge-gated: the cockpit shows planned implementation and repair work, but does not mutate Unreal, call providers, or treat planned steps as proof.

### D.37 - Feature-template work orders

- Extended `skill_compile_ide_companion_work_order` so mechanic design, editor implementation, and runtime verification phases include `feature_template_work` derived from the selected D36 gameplay feature template.
- Work orders now surface feature asset lists, ownership split, graph/component operations, compile/readback checks, PIE validation, repair instructions, evidence requirements, and stop conditions in the phase packet.
- Kept the path offline and bridge-gated: work orders describe what to execute later, but do not mutate Unreal or call providers.

### D.36 - Gameplay feature template packets

- Extended `skill_plan_gameplay_mechanic` so every `unreal_mcp_gameplay_mechanic_plan.v1` includes a selected `unreal_mcp_gameplay_feature_template.v1` packet.
- Added template coverage for interactable objectives, pickup/resource loops, enemy patrol/chase/attack, objective HUD updates, save/load state, input cooldown abilities, and replicated combat samples.
- Each template now carries asset lists, Blueprint/C++/data ownership split, graph/component operations, compile/readback checks, PIE validation steps, repair instructions, evidence requirements, and stop conditions.
- Kept the planner offline and no-spend: template operations are instructions for later bridge-gated work, not live Unreal mutations.

### D.35 - MCP Chat generated asset lifecycle visibility

- Extended `skill_compile_ide_companion_asset_lifecycle_manifest` with optional local manifest persistence under `.mcp_artifacts/ide_companion_sessions/`.
- Extended the MCP Chat cockpit overview to read saved `unreal_mcp_ide_companion_generated_asset_lifecycle.v1` artifacts and expose `generated_asset_lifecycles` plus a compact `generated_assets` status card.
- Added offline coverage for manifest persistence and cockpit lifecycle summaries while keeping the path read-only, no-spend, and no-editor-mutation by default.

### D.34 - IDE companion generated asset lifecycle manifest

- Added `skill_compile_ide_companion_asset_lifecycle_manifest` as a no-spend provider-neutral manifest compiler for generated assets planned by IDE companion sessions.
- The manifest tracks prompt metadata, provider task contracts, wallet/spend gates, placeholder replacement mapping, import and quality gates, viewport proof, ledger evidence, fallback policy, and stop conditions.
- Added MCP registration, command-palette reachability, offline coverage, and generated-content/playable-slice documentation while keeping the tool no-network, no-spend, and no-editor-mutation.
- Synced the tracked MCP tool count to 658.

### D.33 - Local artifact ignore hygiene

- Added `.mcp_artifacts/` and `build_artifacts/` to the generated-artifact ignore policy so companion session evidence and build-test output do not inflate release diffs.
- Updated the Ultimate AI Unreal IDE audit plan to mark local log/run-artifact ignore hygiene complete alongside the existing `*.log` protection.
- Kept the change release-hygiene only: no Unreal editor mutation, no provider calls, and no tool registry changes.

### D.32 - CI lane separation conventions

- Updated `docs/ci-smoke.md` with explicit offline, live-bridge, and paid-provider test lane conventions using filename and command-shape boundaries.
- Added static CI-smoke documentation coverage so default `test_*.py` discovery remains documented as offline/no-spend/no-editor, while `live_bridge_*.py` and `paid_provider_*.py` stay opt-in.
- Reinforced spend and bridge gates: live tests require a reachable Unreal bridge and operator intent, while paid-provider tests require API key, wallet evidence, and explicit human spend approval.

### D.31 - No-mutation full-suite smoke docs

- Updated `docs/ci-smoke.md` with the canonical no-mutation full-suite PowerShell guard that records `last_tool_count.txt` before and after `unittest discover`.
- Added static CI-smoke documentation coverage so the focused Phase 0 gates and full-suite before/after count guard remain visible.
- Kept the smoke path offline: it does not require Unreal Editor, a bridge connection, Tripo credentials, provider spend approval, or writable generated assets.

### D.30 - Preflight Python runtime context

- Extended `scripts/audit_ide_companion_readiness.py` so the no-mutation preflight reports Python executable, version, version tuple, implementation, platform, repo root, current working directory, and virtualenv state.
- Updated preflight tests and CLI JSON coverage so runtime context remains present without modifying the tracked tool-count fixture.
- Kept runtime reporting informational only: it does not install packages, change environments, run Unreal, call providers, or spend credits.

### D.29 - Preflight dirty-state risk

- Extended `scripts/audit_ide_companion_readiness.py` so the no-mutation preflight reports dirty worktree risk, tracked/untracked counts, status buckets, generated/local artifact counts, and short risk reasons.
- Updated preflight tests with deterministic porcelain-status parsing coverage for clean, moderate, high, conflict, and generated-artifact cases.
- Kept dirty-state risk informational: it helps agents avoid mixing release and experimental work, but it does not mutate files, run builds, touch Unreal, call providers, or spend credits.

### D.28 - Preflight last build health

- Extended `scripts/audit_ide_companion_readiness.py` so the no-mutation preflight reports the latest AutomationTool plugin build status, exit code, log path, and summary lines.
- Updated preflight tests with synthetic success/failure AutomationTool logs while keeping the tracked tool count read-only.
- Kept the report informational only: it does not run UnrealBuildTool, package the plugin, mutate Unreal, call providers, or spend credits.

### D.27 - Chat cockpit ledger detail packet

- Added `chat_get_cockpit_ledger_detail` and `/chat/cockpit/ledger` as read-only surfaces for bounded IDE companion ledger drilldown.
- Included recent or selected ledger events, phase index data, latest status/work-order snapshots, artifact lists, artifact kind classification, and artifact overflow counts.
- Synced the tracked MCP tool count to 657 and kept the route/tool no-spend, no-editor-mutation, and local-file-only.

### D.26 - Cockpit evidence artifact preview

- Extended each read-only `evidence_timeline` entry with a bounded `artifact_preview` list so the cockpit can show which proof artifacts back a recent ledger event without loading the full ledger.
- Updated the MCP Chat IDE Cockpit strip to include artifact counts and a short first-artifact hint in the compact evidence timeline row.
- Kept the preview informational only: artifact names do not bypass readiness, bridge, compile, runtime, or paid-provider gates.

### D.25 - Cockpit evidence timeline preview

- Extended the read-only cockpit overview packet with a bounded `evidence_timeline` list derived from recent IDE companion ledger events.
- Updated the MCP Chat IDE Cockpit strip to display a compact evidence timeline so developers can see recently recorded proof without opening ledger JSON.
- Kept the timeline informational only: runtime, compile, asset, and screenshot evidence still need to be collected and recorded before a phase is considered proven.

### D.24 - Cockpit queued-action preview

- Extended the read-only cockpit overview packet so each editor queue includes a bounded `preview_actions` list with action id, tool, label, and argument-key names.
- Updated the MCP Chat IDE Cockpit strip to display a compact queued-action preview, letting developers see the next editor work before any bridge mutation is allowed.
- Kept execution disabled: the preview is informational only and still relies on bridge/readiness gates before any editor action can run.

### D.23 - MCP Chat cockpit overview strip

- Added a compact IDE Cockpit strip to the Unreal MCP Chat panel that refreshes `/chat/cockpit/overview` for the selected session and displays session, blockers, editor queue state, evidence state, and the next suggested action.
- Added a header refresh button and command-palette entry for `chat_get_cockpit_overview` so the D22 backend packet is reachable without manual JSON.
- Kept the strip read-only: it never executes queued editor actions, mutates Unreal, calls Tripo, or bypasses readiness gates.

### D.22 - Chat cockpit overview packet

- Added `chat_get_cockpit_overview` as a no-spend, no-editor-mutation MCP tool that combines saved chat sessions, resume context, IDE companion ledger summaries, editor queues, blockers, display cards, and suggested actions.
- Added `/chat/cockpit/overview` so MCP Chat can fetch the same overview packet over HTTP without manual JSON.
- Extended the shared read-only chat cockpit helper to summarize `unreal_mcp_ide_companion_editor_queue.v1` files alongside ledgers.
- Added offline route/tool coverage for blocked editor queues and synced the tracked MCP tool count to 656.

### D.21 - Chat cockpit session picker

- Added `chat_list_sessions` and `chat_get_session_resume_context` as no-spend, no-editor-mutation MCP tools for listing saved MCP Chat sessions and loading resume context with matching IDE companion ledger summaries.
- Added a shared read-only chat cockpit helper and `/chat/session/resume-context` HTTP route so the editor chat surface can fetch the same resume packet without manual JSON.
- Added offline chat-tool coverage with isolated chat sessions and temporary IDE companion ledgers.
- Documented the D21 chat cockpit session picker workflow in `32_AGENT_PLAYABLE_SLICE_RECIPE.md`.
- Synced the tracked MCP tool count to 655.

### Phase 1 - UMG component event route triage closure

- Added `bind_widget_component_event` as a structured Python MCP wrapper for the native component-bound widget event route.
- Documented event-driven Widget Blueprint workflows and when to prefer component-bound event nodes over the older generic widget event helper.
- Updated bridge-audit assertions so the UMG event route stays referenced from Python.
- Updated the Ultimate AI Unreal IDE audit snapshot: bridge command audit now reports 371 Python-referenced routes, 10 C++-only routes, 0 remaining `needs_python_wrapper` routes, and 0 `needs_triage` routes.
- Synced the tracked MCP tool count to 653.

### Phase 1 - Event, interface, pawn, and comment wrapper gap closure

- Added Python MCP wrappers for native `add_custom_event`, `call_custom_event`, `add_interface_event_node`, `rename_blueprint_comment_node`, and `set_pawn_properties` routes.
- Added offline route coverage and bridge-audit assertions for custom/interface event authoring, pawn defaults, and Blueprint comment polish.
- Updated the Ultimate AI Unreal IDE audit snapshot: bridge command audit now reports 370 Python-referenced routes, 11 C++-only routes, and 0 remaining `needs_python_wrapper` routes.
- Synced the tracked MCP tool count to 652.

### Phase 1 - Data, level flow, and node repair wrapper gap closure

- Updated `add_map_variable` and `add_open_level_node` to call their native bridge routes instead of generic fallback commands.
- Added `reconstruct_blueprint_node` as a Python MCP repair wrapper for native node reconstruction after pin/default mutation.
- Added offline route coverage and bridge-audit assertions for the data, level-flow, and repair routes.
- Updated Blueprint and Data Structure documentation with inspect, compile, readback, and evidence flows.
- Bridge command audit now reports 365 Python-referenced routes, 16 C++-only routes, and 5 remaining `needs_python_wrapper` routes.
- Synced the tracked MCP tool count to 647.

### Phase 1 - Behavior Tree task graph wrapper gap closure

- Updated `add_get_random_reachable_point_node`, `add_finish_execute_node`, and `add_clear_blackboard_value_node` to call their native bridge routes instead of generic Blueprint function-node fallbacks.
- Added offline route coverage for the BT task graph helpers and bridge-audit assertions so the native routes stay referenced.
- Updated AI documentation with the inspect, wire, compile, readback, and PIE evidence flow for generated BTTask Blueprints.
- Bridge command audit now reports 362 Python-referenced routes, 19 C++-only routes, and 8 remaining `needs_python_wrapper` routes.

### Phase 1 - AnimGraph and Niagara wrapper gap closure

- Added Python MCP wrappers for native `add_sequence_player_node` and `connect_anim_graph_nodes` AnimGraph routes.
- Added `add_niagara_component` as a Python MCP wrapper for native NiagaraComponent attachment on Blueprints.
- Updated Animation and Niagara documentation with inspect, compile, readback, and evidence flows for the new wrappers.
- Bridge command audit now reports 359 Python-referenced routes, 22 C++-only routes, and 11 remaining `needs_python_wrapper` routes.
- Synced the tracked MCP tool count to 646.

### Phase 1 - Blueprint graph primitive wrapper gap closure

- Added `add_blueprint_function_with_pins` as a Python MCP wrapper for native function graph signature authoring.
- Updated `add_arithmetic_operator_node` and `add_relational_operator_node` to call their native bridge routes instead of generic Kismet function-node fallbacks.
- Added `set_spawn_actor_class` as a Python MCP wrapper for safe SpawnActorFromClass class-pin assignment.
- Updated Blueprint documentation to include function-signature, math/comparison, and SpawnActor class-pin evidence flow.
- Bridge command audit now reports 356 Python-referenced routes, 25 C++-only routes, and 14 remaining `needs_python_wrapper` routes.
- Synced the tracked MCP tool count to 643.

### Phase 1 - Blueprint class setup wrapper gap closure

- Added `set_blueprint_parent_class` as a Python MCP wrapper for the native Blueprint reparenting route, giving generated gameplay classes an explicit class-architecture primitive.
- Updated `add_construction_script_node` to call the native `add_construction_script_node` bridge route instead of the generic event-node route.
- Updated Blueprint documentation to show the inspect, reparent, compile, Construction Script, and readback evidence flow.
- Bridge command audit now reports 352 Python-referenced routes, 29 C++-only routes, and 18 remaining `needs_python_wrapper` routes.
- Synced the tracked MCP tool count to 641.

### Phase 1 - Behavior Tree wrapper gap closure

- Added Python MCP wrappers for the native `set_behavior_tree_blackboard` and `bt_get_info` bridge routes so AI companion workflows can assign Blackboard assets and inspect Behavior Trees without raw bridge calls.
- Updated AI documentation to show the recommended Blackboard assignment plus graph readback evidence flow.
- Bridge command audit now reports 350 Python-referenced routes, 31 C++-only routes, and 20 remaining `needs_python_wrapper` routes.
- Synced the tracked MCP tool count to 640.

## 2026-06-08

### D.20 - IDE companion editor action queue

- Added `skill_compile_ide_companion_editor_queue` as a no-spend queue compiler that turns placeholder manifests or work orders into durable, bridge-gated editor actions.
- Added a `Queue IDE Companion Editor Actions` command-palette action in the MCP Chat panel so editor work can be persisted while the Unreal bridge is offline.
- Documented the queued editor-action workflow in `32_AGENT_PLAYABLE_SLICE_RECIPE.md` and added offline manifest/work-order/registration coverage.
- Synced the tracked MCP tool count to 638.

### D.19 - IDE companion placeholder manifest

- Added `skill_compile_ide_companion_placeholder_manifest` as a no-spend manifest compiler that maps planned generated-asset prompts to placeholder assets, replacement paths, creation tool steps, evidence requirements, and later Tripo replacement policy.
- Added a `Compile Placeholder Asset Manifest` command-palette action in the MCP Chat panel so the in-editor companion can continue gameplay proof while paid generation is blocked.
- Documented the placeholder workflow in `32_AGENT_PLAYABLE_SLICE_RECIPE.md` and added offline manifest/registration coverage.
- Synced the tracked MCP tool count to 637.

### D.18 - IDE companion blocker resolution

- Added `skill_compile_ide_companion_blocker_resolution` as a no-spend resolver for readiness/status blockers, producing unblock actions, placeholder fallback paths, bridge-offline policy, evidence requirements, and next actions.
- Added a `Resolve IDE Companion Blockers` command-palette action in the MCP Chat panel so the in-editor companion can continue safely when wallet, spend, or bridge gates are blocked.
- Documented the blocker-resolution workflow in `32_AGENT_PLAYABLE_SLICE_RECIPE.md` and added offline wallet/bridge/registration coverage.
- Synced the tracked MCP tool count to 636.

### D.17 - IDE companion dashboard

- Added `skill_compile_ide_companion_dashboard` as a no-spend display packet for IDE companion sessions, returning readiness, progress, next-work, generated-asset, gameplay-mechanic, and evidence cards plus embedded status/work-order payloads.
- Added a `Show IDE Companion Dashboard` command-palette action in the MCP Chat panel so the in-editor companion can render the current session state from a ledger or first-run plan.
- Documented the dashboard workflow in `32_AGENT_PLAYABLE_SLICE_RECIPE.md` and added offline ledger/initial-plan registration coverage.
- Synced the tracked MCP tool count to 635.

### D.16 - IDE companion session resume

- Added `skill_resume_ide_companion_session` as a no-spend resume tool that loads a local evidence ledger, rebuilds status, compiles the next work order, and returns a compact `unreal_mcp_ide_companion_resume.v1` packet.
- Added a `Resume IDE Companion Session` command-palette action in the MCP Chat panel so the in-editor companion can continue from durable ledger state.
- Documented the resume workflow in `32_AGENT_PLAYABLE_SLICE_RECIPE.md` and added offline ledger-path/session-name registration coverage.
- Synced the tracked MCP tool count to 634.

### D.15 - IDE companion evidence ledger

- Added `skill_record_ide_companion_evidence` as a no-spend local ledger writer for IDE companion sessions, persisting phase evidence under `.mcp_artifacts/ide_companion_sessions/` and refreshing status from recorded artifacts.
- Added a `Record IDE Companion Evidence` command-palette action in the MCP Chat panel so the in-editor companion can preserve proof after completing or stopping a phase.
- Documented the evidence ledger workflow in `32_AGENT_PLAYABLE_SLICE_RECIPE.md` and added offline persistence/registration/schema coverage.
- Synced the tracked MCP tool count to 633.

### D.14 - IDE companion work order

- Added `skill_compile_ide_companion_work_order` as a no-spend executable work-order compiler for IDE companion sessions, producing the selected phase, prerequisites, blockers, tool steps, evidence requirements, acceptance criteria, stop conditions, and after-completion status refresh.
- Added a `Generate IDE Companion Work Order` command-palette action in the MCP Chat panel so the in-editor companion can turn a plan/status receipt into the next concrete work ticket.
- Documented the work-order workflow in `32_AGENT_PLAYABLE_SLICE_RECIPE.md` and added offline registration/schema coverage.
- Synced the tracked MCP tool count to 632.

### D.13 - IDE companion status receipt

- Added `skill_compile_ide_companion_status` as a no-spend progress receipt for IDE companion sessions, summarizing phase states, readiness blockers, evidence gaps, readiness for paid generation/editor mutation/runtime verification, and the next safe MCP action.
- Added an `Update IDE Companion Status` command-palette action in the MCP Chat panel so the in-editor companion can refresh session progress after each meaningful phase.
- Documented the receipt workflow in `32_AGENT_PLAYABLE_SLICE_RECIPE.md` and added offline registration/schema coverage.
- Synced the tracked MCP tool count to 631.

### D.12 - IDE companion session orchestrator

- Added `skill_compile_ide_companion_session` as the no-spend top-level planner for a solo Unreal developer session, covering readiness, generated assets, gameplay mechanic planning, editor implementation, runtime verification, fallbacks, gates, and next tool calls.
- Added a `Start IDE Companion Session` command-palette action in the MCP Chat panel so the in-editor companion can insert the full session workflow before spending credits or mutating Unreal.
- Documented the session plan in `32_AGENT_PLAYABLE_SLICE_RECIPE.md` and added offline registration/schema coverage.
- Synced the tracked MCP tool count to 630.

### D.11 - Gameplay mechanic planner

- Added `skill_plan_gameplay_mechanic` as an offline planning skill for one Unreal mechanic at a time, covering generated-asset prompts, Blueprint/component structure, input, AI, damage, HUD, save-game, replication, validation gates, and implementation tool sequence.
- Documented the mechanic-planning workflow in `32_AGENT_PLAYABLE_SLICE_RECIPE.md` so agents can guide gameplay development before mutating the editor.
- Added a `Plan Gameplay Mechanic` command-palette action in the MCP Chat panel so the in-editor companion can insert the planner workflow without relying on a user remembering the tool name.
- Synced the tracked MCP tool count to 629.

### D.10 - IDE companion readiness

- Added `gen_compile_ide_companion_readiness` as a no-spend preflight that checks Tripo auth state, playable-slice planning, session budget, spend-confirmation enforcement, import handoff, Tripo Workspace files, and optional API wallet/editor bridge readiness.
- Documented the readiness report in `31_GENERATIVE_CONTENT_PIPELINE.md` so agents can choose the next safe asset-generation or gameplay-assembly step without guessing.
- Added an `IDE Companion Readiness` command-palette action in the MCP Chat panel so the in-editor companion can insert the readiness workflow before asset or gameplay work.
- Added `outputs.blocking_gates` to the readiness report so chat/palette flows can summarize unmet gates without filtering the full audit list.
- Synced the tracked MCP tool count to 628.

### D.9 follow-up - Generative workspace modes

- Expanded the chat dock Generate Asset action into a compact Generate Asset Workspace with mode, reference-image, existing-task, and texture-prompt fields.
- Added inserted workflow support for Tripo text-to-model, image-to-model, multiview-to-model, and texture-paint planning from inside Unreal.
- Made generated mesh requests Smart Mesh-first by inserting `smart_low_poly=true` and documenting Smart Mesh as the default topology policy for Unreal generation.
- Synced the documented MCP tool count to 623 after the current registry grew beyond the previous 620-tool record.

### D.2 follow-up - Tripo API wallet balance

- Added `gen_tripo_get_credit_balance` for no-spend Tripo API wallet balance checks against `/user/balance`.
- Added a Refresh API Balance action and Tripo API Wallet display to the Generate Asset Settings panel so provider-side balance, frozen credits, local session budget, and pending spend are visible in Unreal.
- Documented that Tripo webapp credits and API wallet credits are separate balances, and synced the tracked MCP tool count to 624.

### D.9 follow-up - Texture paint evidence receipt

- Added `gen_compile_texture_paint_evidence` for no-spend Texture/Paint proof receipts using the `unreal_mcp_texture_paint_evidence.v1` schema.
- Updated the texture-paint workspace prompt to compile evidence after Tripo texture generation, wait, import, viewport evidence, and human approval.
- Documented Texture/Paint evidence gates and synced the tracked MCP tool count to 625.

### D.9 follow-up - Texture paint viewport snapshot

- Added `gen_capture_texture_paint_snapshot` to capture the active Unreal viewport for Texture/Paint source/result context and record it on the texture-paint session.
- Added optional Tripo image file-token upload handoff for snapshots without spending generation credits.
- Updated the Texture/Paint workspace prompt, evidence docs, and tracked MCP tool count to 626.

### D.9 follow-up - Texture paint workspace controls

- Added in-editor Texture/Paint controls for viewport label, brush strength, blend amount, brush radius, and optional snapshot upload.
- Threaded those controls through the generated `gen_prepare_texture_paint_session`, `gen_capture_texture_paint_snapshot`, `gen_tripo_texture_model`, and `gen_compile_texture_paint_evidence` workflow.
- Documented that texture generation should use `prepare_result.outputs.tripo_texture_prompt` so the user's paint controls survive into the paid Tripo task.

### D.9 follow-up - Texture paint pass evidence

- Added `gen_record_texture_paint_pass` to record no-spend paint/blend passes with source/result snapshot labels, affected regions, brush settings, imported asset references, and approval notes.
- Updated texture-paint evidence so `proven=true` now requires at least one recorded paint pass in addition to model, texture task, import, viewport evidence, and human approval.
- Updated the Generate Asset Workspace prompt to capture the painted result and record a paint pass before compiling final texture-paint evidence.

### D.9 follow-up - Dedicated Tripo workspace tab

- Added a `Tripo Workspace` editor tab entry point, invokable from both the MCP Chat dock and the Unreal Window menu.
- Started the separate workspace shell with a large generated-asset viewport region and a right-side mode rail for Text to 3D, Multi Image to 3D, and Texture Paint.
- Documented the product direction that Tripo-style generation should feel like an Unreal asset editor window rather than being confined to the chat dock.

### D.9 follow-up - Tripo workspace asset preview

- Replaced the placeholder workspace viewport with an `SEditorViewport` backed by `FAdvancedPreviewScene` and a preview `UStaticMeshComponent`.
- Added a generated Static Mesh asset path field plus Load Preview and Frame controls so imported Tripo assets can be inspected in the dedicated workspace.
- Documented the intended handoff where future import/evidence cards open generated `/Game/...` assets directly in this Unreal-style workspace tab.

### D.9 follow-up - Tripo preview handoff

- Added Tripo Preview actions to chat messages and tool cards so generated/imported `/Game/...` assets can open in the dedicated Tripo Workspace.
- Added `UnrealMCP.TripoWorkspace/PreviewAssetPath` handoff state; the workspace polls it, loads the requested Static Mesh, and frames the preview.
- Broadened chat asset extraction to recognize raw `/Game/...` paths in structured tool JSON as well as explicit `@asset:` references.

### D.4 follow-up - Tripo import preview handoff fields

- Updated `gen_tripo_import_to_project` to return `preview_asset_path`, `preview_asset_reference`, and `tripo_workspace_handoff` fields derived from the imported primary StaticMesh.
- Documented the one-click Tripo Workspace preview contract so generated asset imports reliably expose the best preview target to chat/tool cards.

### D.9 follow-up - Tripo workspace mode rail

- Made the dedicated Tripo Workspace mode rail stateful for Text to 3D, Multi Image to 3D, and Texture Paint.
- Added mode-specific prompt/reference/task controls plus a Copy MCP Prompt action so the standalone workspace can stage chat-executable generation requests.
- Added a local Generative Credits readout in the workspace from `Saved/MCPChat/generative_settings.json`, including budget, pending spend, confirmation state, output folder, and Smart Mesh policy.

### D.9 follow-up - Standalone Tripo workspace window

- Added an `IUnrealMCPEditorModule::OpenTripoWorkspaceWindow` entry point that creates or focuses a dedicated `SWindow` containing the Tripo Workspace viewport.
- Updated the chat top-bar action, Tripo Preview action, and Window menu entry to use the standalone workspace window path instead of forcing generation into the chat dock.
- Kept the hidden nomad tab spawner available as an editor integration fallback while making the Unreal-style separate window the primary UX.

### D.9 follow-up - Tripo workspace native details object

- Added a transient `UTripoWorkspaceSession` editor object for Tripo mode, preview path, provider/output state, Smart Mesh policy, credit budget, spend state, task ids, and texture-paint brush controls.
- Added a Property Editor `IDetailsView` to the standalone Tripo Workspace so session state is displayed through native Unreal details rows.
- Synced the details object from `Saved/MCPChat/generative_settings.json` and Tripo preview handoff state while keeping API keys out of the details surface.

### D.9 follow-up - Tripo workspace toolbar and status strip

- Added a native-style action toolbar to the standalone Tripo Workspace for mode switching, preview loading/framing, MCP prompt copy, and generative-credit refresh.
- Added a bottom status strip that surfaces active mode, preview status, local session budget, pending spend, spend confirmation, output folder, and Smart Mesh policy while the viewport remains focused.
- Documented the toolbar/status contract as part of the Unreal-native Tripo workspace UX.

### D.9 follow-up - Tripo workspace API key entry

- Added a masked Tripo API key field to the standalone Tripo Workspace so users can enable generative work without leaving the asset-editor-style window.
- Saved workspace keys to the existing `Saved/MCPChat/secrets.json` contract used by the chat dock and Python MCP server, with `TRIPO_API_KEY` environment precedence preserved.
- Added source-only auth status to the native details object so the UI can show `env:TRIPO_API_KEY`, `Saved/MCPChat/secrets.json`, or `missing` without exposing the secret value.

### D.9 follow-up - Standalone texture-paint controls

- Added explicit Texture Paint controls to the standalone Tripo Workspace for view label, brush strength, blend amount, brush radius, and optional viewport snapshot upload.
- Mirrored the paint controls into the transient details object and copied MCP prompt so Tripo texture generation preserves the user's paint/blend intent.
- Captured current mode inputs before rebuilding the workspace mode panel so switching between generation modes preserves entered values.

### D.9 follow-up - Tripo workspace chat handoff

- Added a Send to Chat toolbar action in the standalone Tripo Workspace.
- Posted the current workspace request to the `tripo-workspace` chat session via `/chat/send` with context for source, mode, preview asset, target asset name, auth source, Smart Mesh, and face limit.
- Kept MCP Chat as the execution/progress/evidence surface while the standalone workspace remains the asset-editor-style creation surface.

### D.9 follow-up - Tripo workspace API wallet credits

- Added provider-side Tripo API wallet balance/frozen-credit display to the standalone Tripo Workspace status strip and native details object.
- Reused the no-spend Tripo `/user/balance` refresh path with the same `TRIPO_API_KEY` then `Saved/MCPChat/secrets.json` credential precedence as the chat settings drawer.
- Updated the Refresh Credits action so the workspace refreshes both local Unreal-MCP budget state and provider wallet status.

### D.9 follow-up - Smart Mesh locked topology policy

- Made Smart Mesh a locked read-only policy in the standalone Tripo Workspace details object instead of an editable generation preference.
- Added a status-strip topology readout and chat handoff context that preserve `smart_low_poly=true`, `face_limit=12000`, and the game-ready topology policy.
- Documented that Unreal generation should not allow users to turn off Smart Mesh in this workspace.

### D.7 follow-up - Playable slice assembly mode

- Extended `skill_generate_playable_slice` with `mode="assemble"` so completed Tripo task ids or imported generated assets can drive the Blueprint, enemy AI, HUD, nav/level, screenshot, PIE smoke, and vertical-slice report chain.
- Added generated StaticMesh assignment for the player/enemy Blueprints and aligned the HUD calls with the native UMG route parameters.
- Kept paid generation gated to `mode="submit_assets"`; assembly can run from existing generated assets without requiring a fresh Tripo API call.
- Updated the playable-slice recipe and smoke coverage for the assembly path and failure stages.

### D.9 - Chat dock generative integration

- Added a Generate Asset quick action in the MCP Chat dock that opens a Tripo prompt/settings/preview panel and inserts a `gen_tripo_text_to_model` request into the composer.
- Added inline Tripo progress rendering for `gen_tripo_wait_for_task` tool cards, including SSE refresh behavior when streamed progress JSON arrives.
- Documented the D.9 chat-dock workflow in the generative content pipeline KB and added static smoke coverage for the UI hooks.

### D.8 - Generative knowledge base runbooks

- Expanded `knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md` with canonical prompts, the expected Tripo/import/material/evidence tool sequence, runtime budgets, failure-mode recovery, and the generated-content evidence contract.
- Expanded `knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md` with exact playable-slice prompts, the end-to-end D.8 tool sequence, runtime expectations, known failure modes, and the minimum green vertical-slice report contract.
- Added static smoke coverage so the D.8 runbook sections remain present in future edits.
- Synced the documented tracked MCP tool count to 620 so the CI smoke count guard remains green.

### D.7 - Playable slice skill

- Added `skill_generate_playable_slice` with offline plan mode and a Tripo-gated asset submission mode.
- Added `knowledge_base/v5/PLAYABLE_SLICE_SCHEMA.json` for the generated slice plan contract.
- Documented the D.7 API-key, credit-budget, and `confirm_spend=True` gates plus the remaining async import/Blueprint/PIE/report steps.

### D.6 - Texture-only path

- Added `gen_texture_from_prompt` as the prompt-only texture entry point with channel/resolution validation and a Material Instance handoff plan.
- Marked Tripo standalone prompt-to-texture generation as unsupported because `texture_model` requires an existing model task.
- Documented the D.6 fallback path and the material-tools sequence for wiring future provider Texture2D outputs into a master material instance.

## 2026-06-07

### D.5 - Generative provider abstraction

- Added `tools/generative/` with the `GenerativeProvider` protocol, output policy/result dataclasses, and a small provider registry.
- Added `TripoProvider` as the first implementation and delegated Tripo credit estimates, output suffixes, model-version normalization, and primary-model selection through it.
- Added `IGenerativeProvider.h` as the C++ import-side provider metadata interface and documented how to add future providers in the generative content KB.

### D.4 - Tripo auto-import bridge

- Added `gen_tripo_import_to_project` to download successful Tripo task outputs, prepare an import manifest, import the primary StaticMesh, and capture viewport thumbnail evidence.
- Reused the asset import execution substrate for generated mesh imports, with ScopedSlowTask and ScopedEditorTransaction coverage inside Unreal.
- Updated the generative content KB with the D.4 auto-import sequence, return payload, material-instance behavior, and Blueprint-shell boundary.

### D.3 - Tripo task tools

- Added Tripo task-family tools for text, image, multiview, refine, texture, conversion, status polling, waiting, and downloading signed outputs.
- Added provider-side HTTP helpers, local image upload support, explicit credit confirmation, and reservation rollback on failed submission.
- Updated the generative content KB with D.3 task sequencing and output handoff guidance.

### D.2 - Generative config and auth

- Added Tripo config/auth tools for key-source detection, local settings persistence, and per-session credit budget checks.
- Added a Generate Asset Settings drawer in the MCP Chat panel for API key, model version, texture quality, output folder, and spend confirmation.
- Updated the generative content KB with config/auth and cost-guard guidance.
- Kept D.2 offline: no Tripo API call is made until D.3 task tools land.

### D.1 - Generative module scaffold

- Added `tools/generative_tools.py` with `gen_list_providers` and `gen_prepare_import_manifest`.
- Added a native `gen_prepare_import_manifest` bridge helper for generated asset import handoff validation.
- Updated the generative content KB with provider scaffold and import manifest helper guidance.
- Added inventory metadata, bridge audit categorization, and D.1 offline smoke coverage.

### C.11 - Onboarding

- Added a config-backed first-launch MCP Chat tour with four steps: connect server, ask a question, drag an asset, and run a workflow.
- Added persistent onboarding completion state with Tour and Done controls so users can dismiss or reopen the guided overlay.
- Added a Sample Prompts surface with six curated demos: Health System, Build Slime Enemy, Dungeon Starter, HUD Health Bar, Repair Blueprint, and Asset Import Pass.
- Wired sample prompt clicks to insert real tool-chain requests into the composer without terminal copy-paste.
- Added C.11 static tests guarding first-launch state, tour steps, six sample demos, prompt insertion, and this changelog entry.

### C.10 - Accessibility and polish

- Added config-backed splitter persistence for the MCP Chat session rail, tool palette, conversation, and composer regions.
- Kept the panel on editor style tokens and subdued foreground colors so light/dark theme parity follows Unreal editor styling.
- Added a status footer that reports server latency, loaded tool count, KB doc count, request queue depth, and metrics state.
- Added an opt-in metrics toggle that records local chat panel telemetry snapshots to `Saved/MCPChat/metrics.json`.
- Added C.10 static tests guarding persisted layout, status footer fields, local opt-in telemetry, editor theming tokens, and this changelog entry.

### C.9 - Command palette

- Added a Ctrl+K command palette to `SMCPChatPanel` with a header button and in-panel search surface.
- Populated fuzzy-searchable entries from MCP tools, core KB docs, recent `@asset:` references, recent user prompts, and slash commands.
- Wired palette clicks to insert tool templates, KB prompts, asset references, recent prompts, or slash command text into the composer.
- Routed `/clear` through the existing clear-history action while keeping `/help`, `/undo`, and `/repair` available from the palette.
- Added C.9 static tests guarding command palette declarations, Ctrl+K/button wiring, search sources, fuzzy matching, click behavior, and this changelog entry.

### C.8 - Session management

- Added named chat-session storage under `Saved/MCPChat/<session>.json` with session list, create, rename, pin, delete, and Markdown export helpers.
- Exposed `/chat/sessions` plus `/chat/session/new`, `/chat/session/rename`, `/chat/session/pin`, `/chat/session/delete`, and `/chat/session/export` HTTP routes.
- Threaded `session` through chat send, poll, history, and clear routes so multiple conversations stay isolated.
- Added a left-side `SMCPChatPanel` session sidebar with Continue Last, New, Rename, Pin, Delete, Export, and per-session load actions.
- Added C.8 storage, route, and static editor tests guarding named session persistence and session-scoped chat URLs.

### C.7 - PIE/log/viewport evidence inline

- Added inline evidence extraction to `SMCPChatPanel` tool-call cards for screenshot paths, log snippets, and PIE/play-in-editor results.
- Rendered an inline evidence section in the originating tool card so viewport captures, logs, and runtime checks stay attached to the command that produced them.
- Added screenshot image widgets for existing local image files while still showing the captured path for missing or remote artifacts.
- Extended the tool detail drawer with a full inline-evidence summary alongside args, structured result detail, and log tail.
- Added C.7 static tests guarding evidence extraction, inline card rendering, image-widget setup, detail drawer evidence text, and this changelog entry.

### C.6 - In-panel tool palette

- Added a toggleable left-side `SMCPChatPanel` tool palette with expandable categories and per-tool insert buttons.
- Exposed `/tools/list?domain=all` through the chat HTTP route layer using the same discovery payload as `list_available_tools`.
- Tracked the UE editor chat HTTP/MCP support package, bringing the documented inventory to 603 MCP tools.
- Wired tool clicks to insert prompt templates with `<parameter>` placeholders derived from discovered tool parameters.
- Added C.6 static and route tests guarding palette fetch, category rendering, template insertion, and HTTP tool discovery.

### C.5 - Asset drag-and-drop

- Upgraded `SMCPChatPanel` drops to accept Content Browser assets, Outliner actors, and OS file explorer drops as typed prompt references.
- Added multi-item drop handling that inserts one `@asset`, `@actor`, or `@file` reference per line.
- Normalized external file paths before inserting `@file:` references into the composer.
- Added C.5 static tests guarding supported drag sources, typed reference formatting, OS file normalization, and multi-item joining.

### C.4 - Context chips

- Added live context chips above the `SMCPChatPanel` composer for open level, selected actor, dirty assets, last compile status, and the SSE 8000 server.
- Wired chip clicks to insert `@level`, `@actor`, `@dirty-assets`, `@last-compile`, and `@server` context references into the prompt.
- Added editor-state helpers for current level, selected actor, dirty package count, and structured/text compile-result tracking.
- Added C.4 static tests guarding chip labels, click wiring, inserted references, and editor context probes.

### C.3 - Tool-call visualization

- Added structured tool-call parsing to `SMCPChatPanel` for JSON MCP invocation/result payloads.
- Rendered tool calls as collapsible cards showing tool name, args summary, status, and structured result summary.
- Added a tool detail drawer that shows full args/result JSON and `log_tail` for selected tool cards.
- Added a Repair action for failed tool cards that queues a `repair_tools` chain request through the chat bridge.
- Added C.3 static tests guarding card rendering, detail drawer wiring, structured-result parsing, and repair prompt dispatch.

### C.2 - Core MCP Chat panel UX

- Upgraded `SMCPChatPanel` to a resizable two-pane Slate layout with conversation history above a multiline composer.
- Added Enter-to-send and Shift+Enter newline handling, plus generic drag/drop reference insertion for the composer.
- Added role-tagged user, agent, and tool message bubbles with Copy, Re-run, Open Log, and Reveal Asset actions.
- Added Markdown fenced-code rendering as highlighted monospaced blocks and append-on-delta SSE `data:` handling for streaming message updates.
- Added C.2 static tests that guard the core panel UX wiring and editor module dependencies.

### C.1 - Editor-only chat module split

- Added `UnrealMCPEditor`, a dedicated editor-only module for the dockable MCP Chat panel.
- Moved `SMCPChatPanel` under `unreal_plugin/Source/UnrealMCPEditor/` with a Public/Private module split.
- Moved chat tab registration and `Window > MCP Chat` menu wiring out of the core `UnrealMCP` module startup.
- Added static tests to keep the C.1 module boundary and descriptor entry from regressing.

### B.14 - MetaHuman pipeline tools

- Added `metahuman_import` for assembled MetaHuman package registration, asset-tree scanning, and manifest creation.
- Added `metahuman_inspect_package` for manifest and package-root inspection before follow-on animation or wrapper work.
- Added `metahuman_link_to_skeleton` for body skeletal mesh, skeleton, IK Rig, retargeter, AnimBP, and post-process AnimBP references.
- Added `metahuman_assign_dna` for DNA asset/file, face skeletal mesh, and rig logic metadata.
- Added `metahuman_configure_wrapper` for gameplay wrapper Blueprint metadata and integration references.
- Added native bridge routes, animation inventory coverage notes, usage guide notes, KB cross-links, and B.14 offline smoke tests.

### B.13 - Pixel Streaming and remote access tools

- Added `pixelstream_inspect_config` for Pixel Streaming plugin availability and config inspection.
- Added `pixelstream_configure_plugin` for Pixel Streaming generation enablement and preference flags.
- Added `pixelstream_configure_streamer` for signalling URL, streamer id, port, offscreen render, websocket, and encoder bitrate settings.
- Added `pixelstream_create_launch_profile` for reusable launch profiles with standalone launch arguments.
- Added native bridge routes, inventory metadata, usage guide notes, KB cross-links, and B.13 offline smoke tests.

### B.12 - Online Subsystem and EOS tools

- Added `online_inspect_config` for masked Online Subsystem/EOS config and plugin availability inspection.
- Added `online_configure_default_subsystem` for default/native online service config.
- Added `online_create_eos_artifact_config` for EOS artifact/product/sandbox/deployment/client id setup with secret suppression by default.
- Added `online_configure_eos_sessions` for EOS session, lobby, presence, connect, and stat mirroring flags.
- Added native bridge routes, OnlineSubsystem module/plugin dependencies, inventory metadata, usage guide notes, KB cross-links, and B.12 offline smoke tests.

### B.11 - Movie Render Queue tools

- Added `mrq_create_job` for editor MRQ queue job creation with sequence/map assignment, output folder, filename format, resolution, deferred pass, and image output format setup.
- Added `mrq_add_render_setting` for output, image output, deferred pass, anti-aliasing, and console variable render settings.
- Added `mrq_render_queue` for dry-run queue validation by default and explicit PIE executor render starts.
- Added native bridge routes, Movie Render Pipeline module dependencies, inventory metadata, usage guide notes, KB cross-links, and B.11 offline smoke tests.

### B.10 - Chaos destruction and cloth tools

- Added `chaos_create_solver_actor` and `chaos_configure_solver_actor` for Chaos Solver actor creation and event/runtime budget configuration.
- Added `chaos_inspect_geometry_collection` and `chaos_configure_geometry_collection` for Geometry Collection inspection, thresholds, clustering, event flags, and solver assignment.
- Added `chaos_configure_cloth_component` for SkeletalMeshComponent cloth simulation controls.
- Added native bridge routes, Chaos/GeometryCollection/Clothing module dependencies, inventory metadata, usage guide notes, KB cross-links, and B.10 offline smoke tests.

### B.9 - World Partition and HLOD tools

- Added `wp_load_region`, `wp_unload_region`, and `wp_create_data_layer` for World Partition editor region and Data Layer authoring.
- Added `hlod_generate` and `hlod_assign_layer` for World Partition HLOD builder passes and actor HLOD layer assignment.
- Added native bridge routes, WorldPartitionEditor/DataLayerEditor module dependencies, usage guide notes, KB cross-links, inventory metadata, and B.9 offline smoke tests.

### B.8 - Motion Matching and Chooser tools

- Added `motion_create_pose_search_schema`, `motion_create_pose_search_database`, `motion_add_database_sequence`, and `motion_inspect_pose_search_asset` for Pose Search authoring.
- Added `chooser_create_table`, `chooser_add_asset_row`, and `chooser_inspect_table` for Chooser table asset-result setup and inspection.
- Added native bridge routes, PoseSearch/Chooser plugin and module dependencies, usage guide notes, KB cross-links, and B.8 offline smoke tests.

### B.7 - MassEntity, StateTree, and SmartObject tools

- Added `mass_create_entity_config`, `mass_add_trait`, and `mass_inspect_entity_config` for MassEntity config asset authoring.
- Added `statetree_create`, `statetree_add_state`, and `statetree_inspect` for StateTree schema-backed asset creation and hierarchy inspection.
- Added `smartobject_create_definition`, `smartobject_add_slot`, and `smartobject_inspect_definition` for SmartObject definition and slot authoring.
- Added native bridge routes, MassGameplay/StateTree/GameplayStateTree/SmartObjects dependencies, inventory metadata, usage guide notes, KB cross-links, and B.7 offline smoke tests.

### B.6 - Geometry Script and Modeling Mode tools

- Added `geom_create_dynamic_mesh`, `geom_boolean_op`, `geom_extrude`, `geom_remesh`, `geom_uv_unwrap`, `geom_bake_to_static_mesh`, and `geom_apply_displacement` for DynamicMesh authoring and Static Mesh baking.
- Added native Geometry Script bridge routes, GeometryScripting plugin/module dependencies, usage guide notes, KB cross-links, and B.6 offline smoke tests.

### B.5 - MetaSounds and audio asset authoring tools

- Added `metasound_create_source`, `metasound_create_patch`, `metasound_add_node`, `metasound_connect_pins`, and `metasound_compile` for MetaSound asset and graph authoring.
- Added `audio_create_soundcue`, `audio_create_attenuation`, and `audio_create_concurrency` for cue routing, 3D falloff, and voice-limit policy assets.
- Added native audio bridge routes, MetaSound plugin/module dependencies, usage guide notes, KB cross-links, and B.5 offline smoke tests.

### B.4 - Networking and replication authoring tools

- Added `net_set_property_replicated`, `net_set_function_rpc`, and `net_set_replication_condition` for replicated Blueprint state and RPC authoring.
- Added `net_add_replicated_component`, `net_set_role_override`, and `net_get_replication_graph_state` for component replication, authority flow, and runtime replication inspection.
- Added native network bridge routes, inventory category metadata, usage guide notes, KB cross-links, and B.4 offline smoke tests.

### B.3 - Gameplay Ability System authoring tools

- Added `gas_create_ability`, `gas_create_gameplay_effect`, `gas_create_gameplay_cue`, and `gas_create_attribute_set` for GAS asset creation.
- Added `gas_grant_ability`, `gas_apply_effect`, and `gas_add_tag` for ASC-backed Blueprint authoring metadata.
- Added `gas_create_ability_task_node` for AbilityTask factory nodes in GameplayAbility graphs.
- Added native GAS bridge routes, inventory category metadata, usage guide notes, KB cross-links, and B.3 offline smoke tests.

### B.2 - graph-aware Blueprint/material diagnostics

- Added `compile_blueprint_and_report` for compile status plus graph summaries.
- Added `compile_material_and_report` for material compile and expression summaries.
- Added `validate_import_result` for post-import existence, class, dirty-state, and dependency evidence.
- Added `get_changed_assets_since` for package mtime and dirty-package asset diffs.
- Added the B.2 diagnostics section to the MCP usage guide and offline smoke tests for all four tools.

### B.1 - pre-existing roadmap gap tools

- Added `bp_add_call_interface_function` for Blueprint Interface message-call nodes.
- Added `bp_add_for_loop_with_break_node` plus the native `add_blueprint_for_loop_with_break_node` route.
- Added `bp_copy_component` plus the native `bp_copy_component` SCS route.
- Added `umg_add_widget_binding` plus the native `umg_add_widget_binding` UMG binding route.
- Added subsystem KB notes for the four B.1 tools in Blueprint fundamentals, Blueprint communication, UMG, component, and MCP usage docs.
- Added offline smoke tests for B.1 tool registration, routing, and StructuredResult shape.

### A.9 - v5 changelog resource

- Added `knowledge_base/v5/CHANGELOG.md` as the append-only KB change log for the v5 directive.
- Exposed `knowledge_base/v5/*.md` files as MCP resources using the `kb://v5/<filename>` URI pattern.

### A.8 - tool docstring KB links

- Added `KB: see knowledge_base/...#anchor` and `Example:` sections to all Git-tracked FastMCP tool docstrings.
- Added `scripts/lint_tool_docstrings.py` so CI can reject tools that omit KB links or examples.
- Updated `docs/ci-smoke.md` to include the docstring lint gate.

### A.7 - modern subsystem guide expansion

- Added `19_GAMEPLAY_ABILITY_SYSTEM.md`.
- Added `20_NETWORKING_AND_REPLICATION.md`.
- Added `21_METASOUNDS_AND_AUDIO_DSP.md`.
- Added `22_GEOMETRY_SCRIPT_AND_MODELING.md`.
- Added `23_MASS_ENTITY_AND_STATETREE.md`.
- Added `24_MOTION_MATCHING_AND_CHOOSERS.md`.
- Added `25_WORLD_PARTITION_AND_HLOD.md`.
- Added `26_CHAOS_PHYSICS_AND_DESTRUCTION.md`.
- Added `27_METAHUMAN_PIPELINE.md`.
- Added `28_MOVIE_RENDER_QUEUE_AND_SEQUENCER.md`.
- Added `29_PIXEL_STREAMING_AND_REMOTE.md`.
- Added `30_ONLINE_SUBSYSTEM_AND_EOS.md`.
- Added `31_GENERATIVE_CONTENT_PIPELINE.md`.
- Added `32_AGENT_PLAYABLE_SLICE_RECIPE.md`.
- Updated `INDEX.md` so the new numbered docs are discoverable from the decision tree and file tables.

### A.1-A.6 - native-mode onboarding surface

- Exposed top-level `knowledge_base/*.md` and `knowledge_base/v4/*.md` files as FastMCP resources.
- Added startup and discovery tools: `get_server_info`, `get_project_context`, `get_onboarding_context`, `scan_project_assets`, and `list_available_tools`.
- Added offline tests for resource metadata, server info, project context caching, onboarding packets, asset scanning, and domain-filtered tool discovery.
