# CI Smoke And Profiling

These commands are the repeatable Phase 7 smoke path for validating the MCP
server without a live Unreal Editor session.

## Offline Smoke

Run from the repository root:

```powershell
python scripts\tool_inventory.py --markdown
python scripts\audit_ide_companion_readiness.py
python scripts\audit_test_lanes.py
python scripts\lint_tool_docstrings.py
python scripts\profile_mcp_startup.py --iterations 3 --markdown-out knowledge_base\Reports\mcp_startup_profile.md --json-out knowledge_base\Reports\mcp_startup_profile.json
python scripts\bridge_command_audit.py
python scripts\audit_high_value_wrapper_coverage.py
python scripts\write_platform_stability_review.py
python -m unittest unreal_mcp_server.tests.test_tool_count unreal_mcp_server.tests.test_phase0_ide_companion_preflight unreal_mcp_server.tests.test_tool_docstrings unreal_mcp_server.tests.test_phase7_profile unreal_mcp_server.tests.test_phase7_bridge_command_audit unreal_mcp_server.tests.test_phase1_high_value_wrapper_coverage
python scripts\run_no_mutation_unittest.py
```

Expected results:

- `tool_inventory.py` exits with code `0`, scans Git-tracked tool files by default, and reports no uncategorized modules.
- `audit_ide_companion_readiness.py` exits with code `0`, does not mutate tracked files, and reports top-level `tool_count`, `recorded_tool_count`, `partial_tool_count`, and `tool_registry_reproducible` aliases plus the full `tool_inventory`, current branch and WIP/main branch policy, dirty-state risk with grouped dirty-path evidence plus a no-git-mutation dirty promotion review contract, bridge status, chat status with `/chat/history?limit=1` health, SSE startup diagnostics, a no-process-start chat cockpit repair contract, a passive readiness repair queue for ordered blocker recovery with unified `next_operator_command_handoff` UI actions, mesh and animation provider config presence with no-leak repair templates and ignored secret-path evidence, a no-spend Tripo/Uthana wallet/allowance evidence contract, test-lane separation counts/violations, high-value bridge-wrapper coverage, build-wrapper status, build-wrapper project/plugin/tool reference readiness, platform-stability readiness, WIP-promotion readiness, editor-mutation readiness, `ready_for_blueprint_mutation`, paid mesh/animation generation blockers, Blueprint mutation evidence gates, top-level `blocking_gates` including bridge/chat/provider/wallet/spend blockers, promotion blockers, and Blueprint pre-read/compile/readback blockers, plus a structured `readiness_policy` JSON block for cockpit/CI consumers.
- The root `_build_plugin.bat` defaults to `RunUAT BuildPlugin` for `unreal_plugin\UnrealMCP.uplugin`, writes packages under `Saved\PluginBuildSmoke\Package`, and leaves ignored local proof in `Saved\PluginBuildSmoke\last_build.log` plus `Saved\PluginBuildSmoke\last_build_receipt.json`; pass a plugin path and optional package directory when validating another plugin. Preflight resolves that `%~dp0` default, prefers the local receipt over unrelated machine-global AutomationTool logs, and reports stale wrapper references before anyone runs a compile.
- `scripts\start_chat_cockpit_server.ps1` is the repeatable repair action for `chat_server_reachable`: it starts the SSE MCP server hidden, waits for `/chat/history?limit=1`, and writes ignored local proof to `Saved\ChatCockpit\last_start_receipt.json` without killing ports, mutating Unreal, calling providers, or touching Git. Preflight stays read-only and only points at this script through `chat_cockpit_repair_contract`.
- `scripts\write_dirty_promotion_review.py` writes ignored local proof to `Saved\DirtyPromotionReview\last_review_receipt.json` with dirty groups, review batches, a dirty-worktree signature, promotion-batch policy, generated/local artifact policy, safe next steps, required evidence, structured focused-test command handoffs, approval-only pending state, and no-git-mutation/no-provider/no-editor flags. Target evidence merges with the previous ignored receipt only when the dirty signature and target group still match; use `--reset-target-evidence` to intentionally discard prior target evidence. Preflight marks the receipt stale when its signature no longer matches the current dirty worktree. It does not stage, commit, clean, delete, merge, move branches, mutate Unreal, call providers, or spend credits; it only preserves a reviewable WIP promotion snapshot.
- `scripts\write_provider_config_review.py` writes ignored local proof to `Saved\ProviderConfigReview\last_review_receipt.json` with masked Tripo/Uthana configuration status, secret-path policy, and repair commands. It never writes raw keys, calls providers, checks wallets, reserves credits, records spend approval, mutates Unreal, or touches Git.
- The paid-generation evidence contract exposes `operator_command_handoff`, a three-action UI handoff for recording masked Tripo wallet evidence, masked Uthana allowance evidence, and explicit Tripo spend/Uthana usage approval separately. These handoff commands merge with the existing ignored receipt unless `--reset-evidence` is explicit, so separate Tripo and Uthana proof does not erase earlier evidence. They write only ignored local receipt evidence and are not permission to call providers, reserve credits, submit tasks, download/import assets, mutate Unreal, or touch Git.
- MCP Chat generated-animation lifecycle contexts expose a Uthana-specific usage `operator_command_handoff` for recording masked allowance evidence and explicit usage approval as separate local receipt actions, plus the current next Uthana receipt action for HUD buttons. The clean cockpit HUD generation card also exposes the target animation, provider, next animation-safe action, usage receipt path, and next usage handoff ID as bounded one-line state, while keeping commands in drill-down fields. The native Unreal chat panel parses those bounded animation fields and adds a compact `Anim:` HUD segment only when generated-animation state is present. These actions remain no-provider-call, no-task-submission, no-download, no-import, no-editor-mutation, and no-git-mutation.
- The clean HUD packet exposes a bounded `next_operator_handoff_safety_label` plus no-provider/no-spend/no-editor/no-git/no-stage/no-commit flags for the current local receipt/test handoff. The native Unreal chat panel parses the label, handoff label/ID, command kind, and receipt path so the Next line can show the current handoff without rendering the full command in the visible HUD. The displayed handoff is informational only and does not auto-run receipt scripts, mutate Unreal, touch Git, call providers, or approve spend.
- MCP Chat evidence recording includes the provider-specific paid evidence command templates and handoff IDs as required artifacts, so the ledger checklist can preserve separate Tripo wallet and Uthana allowance proof instead of collapsing them into one opaque wallet step.
- The platform-stability review receipt carries a compact paid-evidence dashboard summary, including Tripo wallet state, Uthana allowance state, spend/usage approval state, and the provider-specific handoff IDs, while remaining no-provider-call and no-spend. It also snapshots the Blueprint mutation evidence handoff IDs so platform dashboards can show the next local receipt commands without treating them as bridge, compile, save, or PIE approval.
- `scripts\write_platform_stability_review.py` writes ignored local proof to `Saved\PlatformStabilityReview\last_review_receipt.json` with platform-stability and WIP-promotion evidence from the local preflight, including test lanes, the static paid-provider smoke contract, no-mutation receipt state, high-value wrapper coverage, build wrapper health, bridge/chat receipt states, provider review state, paid-generation evidence state, Blueprint mutation evidence state, dirty promotion review state/currentness, top-level blocking gate count/preview, the compact readiness repair queue summary, and the compact dirty target-review group for the next WIP-promotion repair. It never writes raw keys, calls providers, checks wallets, reserves credits, records spend approval, mutates Unreal, stages, commits, cleans, or promotes branches.
- `scripts\write_blueprint_mutation_evidence_review.py` writes ignored local proof to `Saved\BlueprintMutationEvidence\last_review_receipt.json` for Blueprint pre-read evidence, compile-plan evidence, and readback-plan evidence. The preflight and MCP Chat Blueprint gate surface the receipt path, state, recorded booleans, command templates, and `operator_command_handoff` IDs for `record_blueprint_pre_read_evidence`, `record_blueprint_compile_plan`, and `record_blueprint_readback_plan`, but the receipt is not permission to ping the bridge, mutate Blueprint graphs/components, compile, save, run PIE, call providers, spend credits, or touch Git.
- The clean MCP Chat HUD summary also exposes compact Blueprint mutation evidence state: recorded/missing inspect-compile-readback proof counts, next missing gate, next local receipt handoff ID/label, receipt path, safety label, and no-mutation/no-compile/no-save/no-PIE flags. The native Unreal chat panel renders that as a conditional `BP:` recovery segment, not as permission to mutate Blueprint assets.
- MCP Chat cockpit exposes `review_provider_config_gate.target_provider_config_context` so Tripo/Uthana credential setup can be reviewed from the workflow rail with masked status, receipt path, repair commands, and no-spend/no-provider-call flags before wallet checks or paid provider task submission.
- `audit_test_lanes.py` exits with code `0` and confirms live-bridge and paid-provider tests are excluded from default `test_*.py` offline discovery by filename.
- `lint_tool_docstrings.py` exits with code `0` and verifies every Git-tracked FastMCP tool docstring has a `KB: see knowledge_base/...#anchor` line plus an `Example:` section.
- `profile_mcp_startup.py` exits with code `0`, prints a Markdown timing table, and writes optional JSON/Markdown artifacts when output paths are provided.
- `bridge_command_audit.py` prints the Python/C++ bridge command metadata summary; `Python missing C++ routes` should remain `0`, and the C++-only route review should keep every unwrapped C++ command classified.
- `audit_high_value_wrapper_coverage.py` exits with code `0` and proves the roadmap's high-value bridge wrappers, including Behavior Tree task graph primitives, have C++ routes, Python references, registered tool signatures, offline test evidence, and documentation evidence. It also emits a passive `operator_command_handoff` for rerunning the JSON audit and the offline wrapper test lane without requiring the bridge, mutating Unreal, calling providers, spending credits, or touching Git.
- The unittest command passes without requiring Unreal Editor or the TCP bridge.
- `run_no_mutation_unittest.py` runs default offline unittest discovery, fails if any Git-tracked file hash changes during the run, and writes ignored local proof to `Saved\NoMutationTest\last_run_receipt.json`; preflight reports this receipt as WIP-promotion evidence and exposes a passive `operator_command_handoff` for rerunning the no-mutation lane, but does not treat it as bridge, provider, or Blueprint mutation approval.

## Test Lane Conventions

Keep CI lanes separated by filename and command shape so offline validation never
accidentally mutates an Unreal project or spends provider credits.

| Lane | Filename / command convention | Default CI? | Requirements |
| --- | --- | --- | --- |
| Offline | `unreal_mcp_server\tests\test_*.py` | yes | No Unreal Editor, no TCP bridge, no provider network, no spend, no tracked-file mutation |
| Live bridge | `unreal_mcp_server\tests\live_bridge_*.py` or `scripts\bridge_ping.py` | no | Unreal Editor open, plugin bridge reachable, explicit operator intent |
| Paid provider | `unreal_mcp_server\tests\paid_provider_*.py` | no | Provider API key, wallet/credit evidence, explicit provider-network approval, and explicit spend or no-spend intent confirmation |

Offline tests may mock bridge/provider behavior, validate schemas, check
registration, and inspect local files. They must not require `TRIPO_API_KEY`,
`confirm_spend=True`, an open editor, or a reachable bridge.

Live bridge tests must be excluded from `python -m unittest discover -s
unreal_mcp_server\tests -p "test_*.py"` by filename. Run them only after
`python scripts\bridge_ping.py` succeeds and the target project is safe to
mutate or inspect.

`scripts\bridge_ping.py` writes ignored local proof to
`Saved\BridgePing\last_ping_receipt.json`. A successful receipt uses schema
`unreal_mcp_bridge_ping_receipt.v1`, records `successful_bridge_ping=true`, and
is required before preflight can treat the live editor bridge as ready for
mutation. Failed receipts are still useful blocker evidence and do not authorize
Blueprint, actor, PIE, viewport, or queued editor actions.
Preflight and MCP Chat also expose a live-bridge `operator_command_handoff` for
`python scripts\bridge_ping.py`; the action requires Unreal Editor/bridge
availability but remains no-editor-mutation, no-PIE, no-provider-call,
no-spend, and no-git-mutation.

Paid provider tests must also be excluded from default discovery by filename.
Run them only after recording wallet evidence and an explicit human spend
approval for the current session. Prefer offline provider-contract tests under
`test_*.py` whenever possible.

The current paid-provider smoke is a no-spend auth/quota lane. It checks masked
provider config, Tripo API wallet balance, Uthana account allowance, optionally
Uthana async job status for an existing job ID, and optionally Uthana
pre-download allowance for an existing motion ID; it must not submit Tripo tasks,
create Uthana motions, upload videos, download files, import assets, reserve
credits, run PIE, or mutate Unreal.

```powershell
$env:RUN_UNREAL_MCP_PAID_PROVIDER_SMOKE='1'
$env:UNREAL_MCP_PROVIDER_NETWORK_APPROVED='1'
$env:UNREAL_MCP_CONFIRM_NO_SPEND_PROVIDER_CHECKS='1'
# Optional, only when verifying an already-created Uthana motion:
# $env:UTHANA_SMOKE_JOB_ID='<existing-job-id>'
# $env:UTHANA_SMOKE_MOTION_ID='<existing-motion-id>'
python -m unittest unreal_mcp_server.tests.paid_provider_generative_smoke
```

Run `python scripts\audit_test_lanes.py` in offline CI to fail fast if a live
bridge or paid-provider test is accidentally named for default discovery. The
audit also emits a static `unreal_mcp_paid_provider_smoke_contract.v1` contract
for the manual paid-provider smoke, including the opt-in env vars, no-spend
tools, manual command, and forbidden spend/download/task tokens. The IDE
companion preflight embeds this audit and blocks platform-stability readiness
with `test_lane_separation` when violations are present.

## No-Mutation Full Suite

Use this before declaring platform changes stable. It records every Git-tracked
file hash before and after discovery so import tests cannot silently mutate
registry baselines, docs, fixtures, or generated tracked artifacts.

```powershell
python scripts\run_no_mutation_unittest.py
```

Expected results:

- The suite exits with code `0`.
- `TRACKED_FILE_MUTATIONS=0` is printed.
- `NO_MUTATION_RECEIPT=Saved\NoMutationTest\last_run_receipt.json` is printed, and the ignored receipt reports schema `unreal_mcp_no_mutation_unittest_receipt.v1`, `status=success`, `test_exit_code=0`, and `mutation_count=0`.
- `chat_get_cockpit_overview` includes `hud_summary` with schema `unreal_mcp_chat_cockpit_hud_summary.v1`; the native MCP Chat panel should render its bounded `compact_cards` first and leave detailed `cards` / `workflow_actions` for drill-down views so the editor surface stays clean.
- When queued editor execution is blocked, `hud_summary.next_operator_handoff_*` should expose the selected safe local receipt/test handoff instead of implying a bridge-gated editor action can run.
- `scripts\start_chat_cockpit_server.ps1` prints `CHAT_COCKPIT_RECEIPT=Saved\ChatCockpit\last_start_receipt.json` when used for cockpit repair; the receipt schema is `unreal_mcp_chat_cockpit_start_receipt.v1` and should report `status=started` or `status=already_running` before `ready_for_chat_cockpit` can become true.
- `python scripts\write_dirty_promotion_review.py` prints `DIRTY_PROMOTION_RECEIPT=Saved\DirtyPromotionReview\last_review_receipt.json`, `DIRTY_PROMOTION_REVIEW_BATCHES=...`, `DIRTY_PROMOTION_TARGET_REVIEW=...`, `DIRTY_PROMOTION_TARGET_SCOPE=...`, `DIRTY_PROMOTION_TARGET_TRACKED=...`, `DIRTY_PROMOTION_TARGET_UNTRACKED=...`, `DIRTY_PROMOTION_TARGET_SAMPLE=...`, `DIRTY_PROMOTION_TARGET_STATUS=...`, `DIRTY_PROMOTION_TARGET_RECORDED_EVIDENCE=...`, `DIRTY_PROMOTION_TARGET_MISSING_EVIDENCE=...`, `DIRTY_PROMOTION_TARGET_REQUIRED_EVIDENCE=...`, `DIRTY_PROMOTION_TARGET_DECISION_PROMPTS=...`, `DIRTY_PROMOTION_TARGET_EVIDENCE_COMMAND_TEMPLATE=...`, `DIRTY_PROMOTION_TARGET_APPROVAL_COMMAND_TEMPLATE=...`, `DIRTY_PROMOTION_TARGET_HUMAN_APPROVAL_RECORDED=...`, `DIRTY_PROMOTION_TARGET_PROMOTION_ALLOWED=...`, `DIRTY_PROMOTION_TARGET_FOCUSED_TEST_PREVIEW=...`, and `DIRTY_PROMOTION_NEXT_STEP=...`; the receipt also includes `target_review_operator_command_handoff`, a two-item UI handoff for recording target evidence and explicit human approval without parsing shell text, `target_review_human_approval_command_handoff`, a single approval command surfaced only as a pending gate, plus `target_review_focused_test_command_handoff`, a no-git-mutation local validation handoff for the target batch's focused checks. Optional flags such as `--target-owner-or-source`, `--target-promotion-intent`, `--target-focused-test-results`, `--target-artifact-policy-decision`, `--target-tracked-diff-review`, and `--target-human-approval-recorded` only record review evidence in an ignored receipt; `--reset-target-evidence` is the explicit escape hatch for discarding same-signature target evidence. The receipt schema is `unreal_mcp_dirty_promotion_review_receipt.v1` and should be treated as review evidence, not permission to stage, commit, merge, or promote to `main`.
- `python scripts\write_provider_config_review.py` prints `PROVIDER_CONFIG_RECEIPT=Saved\ProviderConfigReview\last_review_receipt.json`; the receipt schema is `unreal_mcp_provider_config_review_receipt.v1` and should report only masked/configured status, never raw Tripo or Uthana keys. Preflight and cockpit outputs also expose the same action as `write_provider_config_review_receipt`, a local receipt handoff with no provider call, no wallet check, no credit reservation, no task submission, no spend, no editor mutation, and no Git mutation.
- `python scripts\write_blueprint_mutation_evidence_review.py` prints `BLUEPRINT_MUTATION_EVIDENCE_RECEIPT=Saved\BlueprintMutationEvidence\last_review_receipt.json`, `BLUEPRINT_PRE_READ_EVIDENCE_RECORDED=...`, `BLUEPRINT_COMPILE_PLAN_RECORDED=...`, and `BLUEPRINT_READBACK_PLAN_RECORDED=...`; the receipt schema is `unreal_mcp_blueprint_mutation_evidence_review_receipt.v1` and should be treated as passive readiness evidence, not permission to mutate Blueprint assets or run compile/save/PIE.
- `python scripts\write_platform_stability_review.py` prints `PLATFORM_STABILITY_RECEIPT=Saved\PlatformStabilityReview\last_review_receipt.json` and `PLATFORM_STABILITY_DIRTY_TARGET_REVIEW=...`; the receipt schema is `unreal_mcp_platform_stability_review_receipt.v1` and should be treated as review evidence for platform stability and WIP promotion, not permission to mutate Unreal, call providers, spend credits, stage, commit, clean, or promote branches.
- The command does not require Unreal Editor, a bridge connection, Tripo API
  credentials, provider spend approval, or writable generated assets.
- The platform preflight keeps active development on `wip` and treats `main`
  as the stable promotion target; branch movement still requires explicit
  human review outside the no-mutation suite.
- Any intentional MCP tool addition must update
  `unreal_mcp_server\tests\last_tool_count.txt` deliberately and document the
  new count in the relevant changelog or audit note.

## Optional Full Server Startup Probe

Use this when Python dependencies are installed and you want a colder proxy for
server import and CLI startup:

```powershell
python scripts\profile_mcp_startup.py --iterations 3 --include-server-help --command-timeout 30
```

This still does not connect to Unreal Editor. It only times the server's
`--help` path in a subprocess.

## Optional Live Bridge Smoke

Use this only when Unreal Editor is already open with the plugin running. Most local projects use `127.0.0.1:55655`; project-specific port overrides
should be supplied explicitly through configuration.

```powershell
python scripts\bridge_ping.py
```

If C++ plugin files changed, trigger Live Coding in Unreal Editor with
`Ctrl+Alt+F11`, wait for a successful compile, then rerun the bridge smoke.

## CI Artifact Guidance

Store `knowledge_base\Reports\mcp_startup_profile.json` and
`knowledge_base\Reports\mcp_startup_profile.md` as build artifacts. Compare the
median timings across commits before changing startup-heavy imports, bulk tool
registration, or bridge routing code.

Use `python scripts\tool_inventory.py --include-untracked` only for local
workspace audits. CI should keep the default tracked-file scan so scratch tools
do not change documented tool counts.

To create a machine-readable bridge command snapshot for review:

```powershell
python scripts\bridge_command_audit.py --write-registry --registry knowledge_base\Reports\bridge_command_registry.json
```

Use `--check --registry <path>` against a saved snapshot when you want CI to
fail on unreviewed command routing drift.

The Markdown audit includes a C++-only route review table. Treat new
`needs_triage` rows as blocking review items before exposing, retiring, or
shipping new native bridge routes.
