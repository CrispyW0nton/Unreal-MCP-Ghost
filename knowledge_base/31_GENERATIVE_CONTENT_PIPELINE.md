# Generative Content Pipeline
> Source: project notes, MCP import/tooling roadmap, Unreal asset pipeline practice
> Last Updated: 2026-06-08 | UE 5.6

---

## Overview

Generative content is only useful when it lands in Unreal as controlled,
inspectable, performant game content. Treat generated images, meshes, audio,
animations, and text as inputs to a production pipeline: prompt, generate,
review, import, normalize, materialize, optimize, place, verify, and document.

For Unreal-MCP-Ghost, the agent should never declare generated content complete
at "asset downloaded." Completion means the generated asset is imported or
recorded, named, organized, referenced by gameplay/world assets, audited, and
verified in-editor.

## Key Classes

| Class or Asset | Role |
| --- | --- |
| `UAssetImportTask` | Editor import task for repeatable asset imports. |
| Static Mesh / Skeletal Mesh | Common destinations for generated 3D assets. |
| Texture2D | Destination for generated images, masks, and material inputs. |
| Sound Wave / MetaSound | Destination or wrapper for generated audio. |
| Material / Material Instance | Turns generated textures into consistent PBR assets. |
| Data Asset / Data Table | Stores generated structured design data. |
| Execution journal | Records prompts, source files, imports, audits, and evidence. |

## Common Pitfalls

- Importing generated assets without source prompt/version metadata.
- Accepting broken scale, pivots, collision, UVs, normals, or material slots.
- Using generated textures outside project compression and naming standards.
- Placing large unoptimized meshes directly into a playable map.
- Losing track of license, consent, or provenance for generated content.
- Treating "AI made it" as an excuse to skip art direction and technical review.

## MCP Tool Mapping

| Task | Preferred MCP direction |
| --- | --- |
| Discover provider readiness | `gen_list_providers` |
| Compile IDE companion readiness | `gen_compile_ide_companion_readiness` |
| Compile generated asset lifecycle | `skill_compile_ide_companion_asset_lifecycle_manifest` |
| Inspect provider config/auth | `gen_get_provider_config` |
| Inspect Tripo API wallet credits | `gen_tripo_get_credit_balance` |
| Save provider defaults | `gen_save_provider_config` |
| Guard paid credit spend | `gen_check_credit_budget` |
| Submit Tripo generation tasks | `gen_tripo_text_to_model`, `gen_tripo_image_to_model`, `gen_tripo_multiview_to_model` |
| Refine, texture, or export Tripo results | `gen_tripo_refine_model`, `gen_tripo_texture_model`, `gen_tripo_post_process` |
| Capture Texture/Paint viewport context | `gen_capture_texture_paint_snapshot` |
| Record Texture/Paint brush passes | `gen_record_texture_paint_pass` |
| Compile Texture/Paint proof | `gen_compile_texture_paint_evidence` |
| Plan prompt-only texture sets | `gen_texture_from_prompt` |
| Poll and collect Tripo outputs | `gen_tripo_get_task_status`, `gen_tripo_wait_for_task`, `gen_tripo_download_result` |
| Prepare import handoff | `gen_prepare_import_manifest` |
| Import Tripo outputs into Unreal | `gen_tripo_import_to_project` |
| Import assets | asset import, batch import, texture/audio import tools |
| Normalize materials | `material_create_master`, `material_create_instance_from_master`, texture tools |
| Audit meshes/textures | mesh, texture, technical-art audit tools |
| Place generated content | editor actor and viewport tools |
| Build procedural variants | procedural/world tools and data assets |
| Verify playable result | PIE/log/screenshot tools and execution journal |

## Provider Scaffold

D.1 introduces `tools/generative_tools.py` as the neutral entry point for
generated content. `gen_list_providers` reports the provider scaffold without
requiring network access or credentials. The first planned provider is Tripo,
with task-family coverage landing in later D milestones:

- D.2 adds configuration and authentication.
- D.3 mirrors the Tripo task model for prompt/image/multiview generation,
  refine, texture, post-process, status, wait, and download.
- D.4 imports downloaded results into Unreal assets.
- D.5 adds the provider abstraction used to describe and register future
  providers without changing the public MCP tool contract.
- D.6 adds a texture-only path that reports Tripo's standalone texture
  limitation and returns the Material Instance handoff expected once a texture
  provider lands.
- D.7 adds the `skill_generate_playable_slice` planner and Tripo-gated asset
  submission path.
- D.8 turns this KB into the operational runbook for exact prompts, expected
  tool sequencing, runtime budgets, and known failure modes.
- D.9 adds the MCP Chat dock Generate Asset Workspace for Tripo text, image,
  multiview, and texture-paint planning plus inline progress rendering for
  long-running Tripo waits.
- D.10 adds `gen_compile_ide_companion_readiness`, a no-spend readiness
  compiler that ties Tripo auth, session budget, playable-slice planning,
  import handoff, editor workspace files, and optional live API/editor checks
  into one actionable report.
- D.162 extends that readiness compiler with an optional `mechanic_brief` so
  gameplay plans that need Uthana motion prompts surface animation auth,
  usage-confirmation, and optional account-allowance gates before any provider
  call, download, import, retarget, AnimGraph edit, PIE run, or ledger write.
- D.34 adds `skill_compile_ide_companion_asset_lifecycle_manifest`, a no-spend
  provider-neutral manifest for prompt, credit gate, task submission, status
  wait, download/import, placeholder fallback, replacement mapping,
  material/collision checks, viewport proof, and ledger evidence.
- D.112 adds Uthana as the provider-neutral animation lane for generated
  humanoid motion, retarget/import handoff, AnimGraph reference proof, PIE
  evidence, and ledger recording. Tripo remains the mesh provider; Uthana is
  tracked as motion/animation, not as static mesh generation.
- D.113 extends local provider config so `gen_save_provider_config` can store
  or clear both Tripo and Uthana keys in ignored `Saved/MCPChat/secrets.json`
  without returning the secret values in MCP output.
- D.151 threads Uthana motion prompts into gameplay mechanic plans, so AI,
  composite AI/objective, combat, ability, and animation-explicit briefs can
  feed `generated_animation_prompts` directly into the provider-neutral
  lifecycle manifest with retarget/readback, AnimGraph, PIE, and ledger proof
  still required before gameplay replacement.
- D.152 exposes those prompt requirements in MCP Chat gameplay-template review,
  queue review, next-safe-step, and execution-review contexts before any
  lifecycle manifest or provider call exists. The review surface shows prompt
  count, provider/skeleton/tool/proof previews, estimated seconds, and the
  no-bypass policy while remaining read-only.
- D.153 adds a `compile_asset_lifecycle_manifest` cockpit workflow action that
  compiles or refreshes the provider-neutral lifecycle manifest from the current
  companion session plan and work-order generated prompt counts. Its context
  shows planned Tripo mesh prompts, planned Uthana animation prompts, existing
  manifest counts, future provider/spend gates, and no-provider/editor-call
  policy before any pasted lifecycle JSON is requested.
- D.154 surfaces that lifecycle compile target in the native MCP Chat compact
  `Next:` summary, including plan state, mesh/animation prompt counts,
  manifest/pending counts, future gate count, estimated Uthana seconds, and
  write-manifest guidance without adding HUD clutter.
- D.155 makes blocked provider-spend review point at no-spend placeholder
  continuation when available. `target_provider_spend_context` now reports
  `fallback_placeholder_available`, fallback action/tool/queue metadata, and
  now-vs-future network/spend/editor requirements so the cockpit can route from
  blocked wallet/spend gates to placeholder manifest work without provider
  calls.
- D.156 adds `continue_with_placeholder_fallback` as the direct workflow action
  for that route. It reuses the placeholder manifest compiler, carries both
  provider-spend and placeholder target context, and becomes the native compact
  `Next:` route when fallback is available.

Agents should use this provider list as a capability map, not as proof that a
paid generation request has been sent. D.2 can resolve auth/config state, but it
still makes no Tripo API call.

Example:

```python
gen_list_providers(include_import_helpers=True)
```

## IDE Companion Readiness

`gen_compile_ide_companion_readiness` is the preflight for the "single
developer with an Unreal IDE companion" workflow. It does not spend credits and
does not require Unreal Editor by default. The result reports:

- Tripo provider registration and API key source without exposing the secret.
- Uthana animation provider registration and API key source without exposing
  the secret.
- A generated playable-slice plan and its estimated Tripo credits.
- Session budget state and proof that paid submission still requires
  `confirm_spend=True`.
- Import handoff and Tripo Workspace source readiness.
- Optional API wallet and Unreal bridge checks when the caller opts in.
- Optional Uthana account allowance checks when `mechanic_brief` produces
  generated animation prompts and the caller opts in with
  `include_animation_account=True`.

Use it before submitting paid asset tasks or assembling a playable slice:

```python
gen_compile_ide_companion_readiness(
    brief="third-person dungeon-crawler demo with a slime boss",
    mechanic_brief="enemy patrol, chase, attack, and objective HUD feedback",
    include_api_wallet=True,
    include_animation_account=True,
    include_unreal_bridge=True,
)
```

If the report is not ready, follow `outputs.next_actions` instead of guessing
which subsystem is blocking the loop. Read `outputs.blocking_gates` first for
the concise list of unmet gates, then use `outputs.gates` when a full audit
trail is needed.

## Generated Asset Lifecycle Manifest

`skill_compile_ide_companion_asset_lifecycle_manifest` should be compiled after
an IDE companion session plan and before paid task submission. It does not call
providers or mutate Unreal; it creates the neutral contract that later provider
tools must satisfy.

In MCP Chat, prefer
`outputs.workflow_actions.compile_asset_lifecycle_manifest.target_asset_lifecycle_compile_context`
before asking for a pasted session plan or lifecycle manifest. The context
summarizes whether a session plan exists, mesh and Uthana animation prompt
counts, manifest/pending counts, future wallet/spend gates, and whether writing
the manifest is recommended.

The `unreal_mcp_ide_companion_generated_asset_lifecycle.v1` manifest records:

- source prompt, role, provider slot, target content path, and Smart Mesh policy;
- provider task tools for submit, status wait, download, and import;
- required wallet/credit evidence and explicit spend confirmation;
- optional placeholder-to-generated replacement mapping;
- quality gates for imported mesh loading, material slots, collision/readability,
  viewport proof, and ledger evidence;
- a `unreal_mcp_generated_asset_quality_proof_contract.v1` quality proof
  contract that names the required after-import mesh load/readback, material
  slot, collision/readability, viewport/thumbnail, and ledger evidence before
  placeholder replacement;
- a `unreal_mcp_generated_animation_quality_proof_contract.v1` quality proof
  contract that names required after-import Animation Sequence readback, target
  skeleton or retarget evidence, AnimGraph/state-machine references,
  PIE/viewport playback proof, and ledger evidence;
- fallback rules for blocked provider auth, empty wallet, failed import, or
  missing proof.

Use this manifest as the cockpit's generated-asset status model. Tripo remains
the first supported provider, but the manifest should not assume Tripo is the
only backend.

When the caller passes `write_manifest=True`, the manifest is saved under
`.mcp_artifacts/ide_companion_sessions/` and MCP Chat can surface it through the
`generated_asset_lifecycles` field and `generated_assets` cockpit card. This is
the preferred path when the developer wants to resume an asset-generation
session without pasting JSON back into chat.

## Dual Provider Config

`gen_save_provider_config` owns local no-leak settings for both mesh and motion
providers. Use `tripo_api_key` with `store_api_key=True` for Tripo mesh
generation, and `uthana_api_key` with `store_uthana_api_key=True` for Uthana
animation generation. Both are written only to ignored
`Saved/MCPChat/secrets.json`; tool outputs report configured/source/masked
status but never return the raw key.

The same tool can clear Uthana without touching Tripo by passing
`clear_stored_uthana_api_key=True`, or clear Tripo without touching Uthana by
passing `clear_stored_api_key=True`. Environment variables still take
precedence: `TRIPO_API_KEY` for Tripo and `UTHANA_API_KEY` for Uthana.

Native Generate Settings preserves existing Uthana secrets when saving Tripo
settings and shows a compact `Tripo auth | Uthana auth` source summary so the
editor cockpit can report provider readiness without adding UI clutter.
D138 adds a dedicated masked `UTHANA_API_KEY` input to that same native Generate
Settings row, writing the canonical Uthana secret key only to ignored
`Saved/MCPChat/secrets.json` when populated.

D139 updates Resolve Blockers so missing Tripo or Uthana credential gates point
to those native masked Generate Settings fields first, while still accepting env
vars and `gen_save_provider_config` as no-leak fallback paths. Blocker evidence
must stay masked, for example auth source plus configured booleans; raw keys do
not belong in chat, docs, or ledger records.

### D122 Paid Animation Readiness

The IDE companion preflight keeps Tripo mesh spend and Uthana motion spend as
separate policy rows. `paid_generation` covers mesh/provider tasks, while
`paid_animation_generation` requires `animation_provider_api_key_configured`,
`wallet_evidence_recorded`, and `spend_confirmation_recorded` before Uthana
text-to-motion, status, download, import, retarget, AnimGraph, PIE, or ledger
work may proceed.

## Uthana Motion Task Family

D.114 registers the guarded public Uthana tool family that D.112 lifecycle
manifests and cockpit actions pointed at:

- `gen_uthana_get_account` reads account/org allowance state, including motion
  download seconds remaining, without spending provider quota.
- `gen_uthana_create_character` uploads a Tripo/exported `.fbx`, `.glb`, or
  `.gltf` character file through Uthana `create_character`, requests auto-rigging,
  and returns the Uthana `character_id` that all later motion generation and
  downloads must use.
- `gen_uthana_get_character` reads Uthana character metadata by ID without
  downloading assets or consuming motion quota.
- `gen_uthana_create_locomotion` submits documented GraphQL
  `create_locomotion` calls for direction-controlled locomotion using
  `character_id`, `travel_angle`, `move_speed`, and `strides`.
- `gen_uthana_text_to_motion` submits documented GraphQL
  `create_text_to_motion` calls only after `confirm_usage=True`; the wrapper
  sends `character_id` to Uthana, not merely to the later download step.
- `gen_uthana_video_to_motion` uploads a `.mp4`, `.mov`, or `.avi` reference
  video through the documented GraphQL multipart `create_video_to_motion`
  mutation only after `confirm_usage=True`; the wrapper sends `character_id` and
  returns an async job id, not a finished motion file.
- `gen_uthana_get_job` polls Uthana async jobs such as video-to-motion and
  reports the finished motion id when the job result is available.
- `gen_uthana_get_motion` reads motion metadata by ID.
- `gen_uthana_check_download_allowed` checks download allowance before a file
  download consumes quota.
- `gen_uthana_download_motion` downloads FBX/GLB/BVH motion files with FPS,
  mesh, in-place, torso-only, motion-only GLB, and speed options after explicit
  usage confirmation.
- `gen_uthana_import_animation_to_project` imports a downloaded FBX into
  Unreal only after the bridge ping gate is ready, then reports retarget,
  AnimGraph/state-machine reference, PIE proof, and ledger evidence as
  remaining quality gates.

The intended character pipeline is Tripo mesh first, Uthana rig/animation
second: generate/export the Tripo character FBX, call
`gen_uthana_create_character` to create the Uthana character target, generate
locomotion/text/video motions with that returned `character_id`, download using
the same `character_id`, then import into Unreal. Do not treat a created
character, created motion, or downloaded file as final gameplay proof; generated
animation is complete only after import, skeleton/retarget readback,
AnimGraph/state-machine reference, PIE proof, and ledger evidence.

D.175 extends the manual paid-provider smoke with an optional no-spend Uthana
job-status and download-allowance proof. When `UTHANA_SMOKE_JOB_ID` points at
an existing async job, the lane may call `gen_uthana_get_job` without spending
or downloading. When `UTHANA_SMOKE_MOTION_ID` points at an existing motion, the
lane may call `gen_uthana_check_download_allowed` to record whether the motion
can be downloaded before any file fetch. The default lane still skips these
checks unless IDs are supplied, and it must not call
`gen_uthana_video_to_motion`, `gen_uthana_download_motion`, set
`confirm_usage=True`, upload videos, download files, import animations, reserve
credits, run PIE, mutate Unreal, or write ledger evidence.

## Generated Animation Evidence

D.115 adds `gen_compile_generated_animation_evidence`, a no-network/no-spend
receipt compiler for Uthana motion lifecycles. It accepts JSON outputs from the
Uthana task family plus optional retarget/readback, AnimGraph or state-machine,
PIE/runtime, ledger, and approval evidence. The output schema is
`unreal_mcp_generated_animation_evidence.v1`.

The compiler marks evidence `proven=True` only when all gates are ready:

- source motion prompt;
- Uthana motion ID and character ID;
- download allowance or explicit absence of a quota check requirement;
- downloaded FBX/GLB/BVH path;
- imported Animation Sequence or primary imported asset path;
- retarget/readback evidence against the target skeleton;
- AnimGraph or state-machine reference evidence;
- PIE/runtime proof that the motion plays in gameplay context;
- companion ledger evidence;
- human approval after inspecting the generated motion.

This tool never calls Uthana, downloads files, imports assets, mutates Unreal,
runs PIE, writes the ledger, or approves work on its own. It is the receipt that
lets MCP Chat and companion sessions keep generated animation honest: a motion
ID is provider evidence, a downloaded file is file evidence, an imported asset
is editor evidence, and PIE plus ledger entries are gameplay proof.

D.116 threads that receipt into the MCP Chat cockpit. The workflow rail now
exposes `compile_generated_animation_evidence` for the D.115 compiler and
`record_generated_animation_evidence` for the companion ledger row. The
evidence-recording checklist carries structured generated-animation metadata:
animation id/name, Uthana task status, motion id, expected import path, target
skeleton, quality proof counts, missing stage preview, and the relevant submit,
download, import, and compiler tools. The cockpit still does not call providers,
download files, import animations, run PIE, mutate Unreal, or write ledger
evidence unless the developer explicitly invokes the routed tool.

D.117 adds native MCP Chat summaries and command-palette prompts for those
generated-animation evidence routes. The editor-side `Actions` launcher and
compact `Next:` line can point to the selected Uthana motion, target skeleton,
proof counts, missing stage count, and evidence artifact count without adding a
separate HUD block.

D.127 adds `next_safe_action` to the generated-animation lifecycle context. The
router gives MCP Chat a deterministic next Uthana step: resolve usage gates,
confirm text-to-motion, attach a missing motion id, unblock editor import,
compile quality proof, or record final evidence. This is guidance only; the
overview still does not call Uthana, download motion files, import animations,
mutate Unreal, run PIE, or write ledger evidence.

D.208 adds a compact Uthana usage proof contract directly to that lifecycle
packet. `unreal_mcp_uthana_animation_usage_contract.v1` carries the allowance
tools, paid-generation evidence receipt path, `confirm_usage=True` requirement,
fallback-animation policy, and no-provider/no-download/no-import/no-editor
safety flags. Treat it as cockpit guidance for recording masked allowance and
explicit human usage approval before text-to-motion or download; it does not
call Uthana, submit tasks, fetch files, import animations, mutate Unreal, write
ledger evidence, reserve credits, or spend.

D.128 threads that route into the native MCP Chat summaries and command-palette
prompts. Review Generated Animation Lifecycle can now show the selected
animation plus the next safe Uthana action label/state/tool in the existing
workflow action row, keeping the HUD compact while reducing raw JSON handoff.

D.133 keeps Uthana task contracts executable. Generated lifecycle manifests use
registered public submit paths and surface any planned Uthana capability that
still lacks a public MCP tool as `unsupported_task_type` with
`planned_submit_tool` and `unsupported_reason` metadata. Do not ask MCP Chat or
the command palette to execute those planned tool names until the public MCP
tool exists.

D.134 carries unsupported provider task metadata into the MCP Chat Generated
Assets card. The card now includes generated animation counts, pending
animation counts, unsupported task counts, and a bounded preview, plus a cockpit
warning when a planned provider submit tool is missing. This keeps the HUD
professional and compact while making provider-wrapper gaps visible before any
network, spend, or editor work.

D.253 carries the same unsupported Uthana task proof into the generated
animation lifecycle gate. If a plan asks for a capability before a public MCP
submit tool exists, the next safe action is `implement_uthana_submit_tool_wrapper`,
not a usage-gate or provider-submit step. The packet includes
`planned_submit_tool`, `public_mcp_tool_available`, and `unsupported_reason`,
while preserving no-provider-call, no-download, no-import, and no-editor-mutation
safety flags.

D.254 implements the guarded public Uthana video-to-motion submit and job-poll
surface. Lifecycle manifests now route `video_to_motion` to
`gen_uthana_video_to_motion` and `gen_uthana_get_job`; the upload tool remains
blocked until `confirm_usage=True`, and job polling is no-spend/no-download
status evidence before any motion download or Unreal import.

D.255 makes the MCP Chat generated-animation next-safe-action packet
task-aware for Uthana video-to-motion. A `video_to_motion` lifecycle now carries
optional `video_file` / `reference_video_file` metadata, blocks locally as
`attach_uthana_video_reference` when the reference clip is missing, then routes
confirmed upload to `gen_uthana_video_to_motion` and async status review to
`gen_uthana_get_job`. This is cockpit guidance only; it does not call Uthana,
upload files, download files, import animations, mutate Unreal, write ledgers,
or approve spend.

D.256 lets `gen_compile_generated_animation_evidence` consume
`job_result_json` from `gen_uthana_get_job`, so video-to-motion lifecycles can
carry provider task evidence from upload job polling into the same proof
compiler used by text-to-motion. A finished job can supply the motion id; a
running job routes the next action back to `gen_uthana_get_job`. The compiler
still remains no-network/no-spend and does not mark animation proof complete
until download, import, retarget/readback, AnimGraph or state-machine, PIE,
ledger, and human approval gates are ready.

D.257 exposes those captured-proof slots directly in the MCP Chat
`compile_generated_animation_evidence` workflow action arguments. The action now
names `text_motion_result_json`, `job_result_json`, motion metadata, download,
import, retarget/readback, AnimGraph, PIE, ledger, and approval fields so the
native command palette can guide evidence compilation without asking the
developer to reconstruct the schema from memory.

D.147 carries Uthana/generated-animation lifecycle gates into queue and
execution review. Queue targets, next-safe-step, execution review, and the
execute workflow context can now surface the selected animation, target
skeleton, task status, quality proof contract, missing stages, next safe action,
and no-bypass policy before import, retarget, AnimGraph, state-machine, PIE, or
gameplay replacement work proceeds.

D.148 carries the same generated-content gate shape into editor queue review, so
an already-compiled queue still shows placeholder-to-generated mesh replacement
policy and Uthana animation proof policy before the developer chooses Execute
Next Safe Step.

## Provider Abstraction

D.5 defines the provider layer that future Meshy, Stability, ComfyUI, or local
generator integrations must satisfy before they become public MCP tools.

Python providers live under `unreal_mcp_server/tools/generative/`:

- `__init__.py` defines `GenerativeProvider`, `ProviderOutputPolicy`,
  `ProviderTaskResult`, and `ProviderRegistry`.
- `tripo.py` is the first implementation. It owns Tripo identity, base URL,
  capabilities, final statuses, output-key order, supported model/image
  extensions, model-version normalization, output suffix inference, primary
  model selection, and conservative credit estimates.
- `uthana.py` owns Uthana identity, GraphQL endpoint metadata, motion
  capabilities, FBX/GLB/BVH output policy, animation output selection, and
  generated-motion lifecycle metadata for the guarded `gen_uthana_*` tools.
- `generative_tools.py` uses the registry so provider metadata, credit
  estimates, and output selection are provider-owned instead of hardcoded in
  each MCP tool.

The Unreal plugin has a matching C++ import-side shape in
`unreal_plugin/Source/UnrealMCP/Public/Generative/IGenerativeProvider.h`.
That interface exposes provider name, display name, base URL, capabilities,
output-key policy, supported model extensions, final statuses, and a JSON
description. It is intentionally metadata-focused; Python still owns remote API
transport for Tripo.

To add a provider:

1. Add `tools/generative/<provider>.py` implementing `GenerativeProvider`.
2. Register the provider in `generative_tools.py`'s `ProviderRegistry`.
3. Add provider-specific config/auth fields without exposing secrets in result
   payloads.
4. Map task submission/status/download tools to the provider's task model.
5. Add offline tests for provider description, credit/cost policy, output
   selection, and any public MCP wrapper.
6. Update this KB and the v5 changelog with provider-specific caveats.

## Config And Auth

D.2 adds local Tripo configuration without making any network call. The MCP
resolves credentials in this order:

1. `TRIPO_API_KEY` from the server process environment.
2. `Saved/MCPChat/secrets.json`, using `TRIPO_API_KEY` or `tripo_api_key`.

The API key value is never returned by `gen_get_provider_config`; the tool only
reports whether a key exists and which source won precedence. Defaults live in
`Saved/MCPChat/generative_settings.json`:

- `default_model_version`
- `default_texture_quality`
- `output_folder` under `/Game/Generated`
- `session_credit_budget`

The chat dock also exposes a Generate Asset Settings drawer for the same
values. Use the environment variable for shared automation and the local
secrets file for per-project editor sessions.

## API Wallet Balance

`gen_tripo_get_credit_balance` reads the Tripo API wallet balance from
`GET /user/balance`. This is a no-spend network check that returns the
available `balance` and `frozen` credits for the API wallet associated with the
configured API key.

The in-editor Generate Asset Settings panel also includes a Refresh API Balance
button and a Tripo API Wallet display. This is intentionally separate from the
local session budget: the API wallet reports provider-side credits, while the
session budget is the Unreal-MCP safety cap for the current editor session.
Tripo documents that webapp credits and API wallet credits are independent.

Balance example:

```python
gen_tripo_get_credit_balance()
```

Config example:

```python
gen_get_provider_config(include_paths=True)

gen_save_provider_config(
    default_model_version="tripo-default",
    default_texture_quality="standard",
    output_folder="/Game/Generated/Enemies",
    session_credit_budget=750,
)
```

## Cost Guard

Before any D.3 or later tool spends Tripo credits, call
`gen_check_credit_budget`. It compares the estimated spend against the current
session budget and requires `confirm_spend=True` before returning approval.
Generation tools should stop when `approved` is false and surface the returned
message to the user. When a tool is about to send the paid provider request, use
`reserve_credits=True` so the approved estimate is recorded against that chat
session before the task is launched.

Example:

```python
gen_check_credit_budget(
    estimated_credits=120,
    session_name="dungeon-demo",
    operation="text_to_model",
    confirm_spend=True,
    reserve_credits=True,
)
```

## Tripo Task Family

D.3 mirrors Tripo's asynchronous OpenAPI task model. All paid task-submission
tools require `confirm_spend=True` before calling Tripo. The tool estimates
credit cost, reserves the estimate against the session budget, submits the task,
and returns the `task_id`. If submission fails before Tripo accepts the task, the
reservation is released.

Use these task creation tools:

- `gen_tripo_text_to_model` for text prompts.
- `gen_tripo_image_to_model` for a local image path, image URL, or uploaded
  `file_token`.
- `gen_tripo_multiview_to_model` for 2-4 ordered views: front, left, back,
  right. Missing rear/side slots are represented as empty file entries.
- `gen_tripo_refine_model` for legacy draft model refinement.
- `gen_tripo_texture_model` for retexturing an existing model task.
- `gen_tripo_post_process` for conversion/export such as `FBX`, `OBJ`, `STL`,
  `USDZ`, or `GLTF`.

Then use `gen_tripo_get_task_status` or `gen_tripo_wait_for_task` until the
task reaches a final status. Successful Tripo task output URLs are short-lived,
so call `gen_tripo_download_result` promptly and pass the local files into
`gen_prepare_import_manifest` before D.4 imports them.

Example:

```python
gen_tripo_text_to_model(
    prompt="stylized slime enemy, game-ready proportions",
    model_version="v3.1-20260211",
    texture=True,
    pbr=True,
    texture_quality="standard",
    face_limit=12000,
    session_name="dungeon-demo",
    confirm_spend=True,
)

gen_tripo_wait_for_task(task_id="<task_id>", timeout_s=900, poll_s=10)

gen_tripo_download_result(
    task_id="<task_id>",
    target_folder="C:/Generated/DungeonDemo/Slime",
)
```

## Import Manifest Helper

`gen_prepare_import_manifest` is the import-side bridge helper for generated
asset handoff. It validates the task id, normalizes the destination to a
`/Game/...` content path, records source files, infers each file's import kind,
and returns expected Unreal asset paths. It does not import or mutate assets;
D.4 will consume this manifest before calling the asset import tools.

Use it after a provider task has a local downloaded result, or as a dry run when
planning a generated content pipeline:

```python
gen_prepare_import_manifest(
    task_id="tripo_task_123",
    local_files=["C:/Generated/slime_enemy.glb"],
    content_path="/Game/Generated/Enemies",
    asset_name="SM_SlimeEnemy",
    create_material_instance=True,
    create_blueprint=True,
)
```

The returned `manifest` includes:

- `source_files`: path, file name, extension, inferred import kind, and whether
  the file currently exists on the Unreal host.
- `expected_assets`: primary asset plus optional material instance and Blueprint
  paths.
- `options`: import flags that later tools should preserve.
- `all_files_present`: false when planning references files that have not been
  downloaded yet.

## Auto-Import Bridge

`gen_tripo_import_to_project` is the D.4 bridge from a successful Tripo task to
Unreal project assets. It queries the task, downloads signed output URLs into
`Saved/MCPChat/tripo_downloads/<task_id>/` when no target folder is supplied,
selects the first supported model output (`pbr_model`, `model`, then
`base_model`), asks `gen_prepare_import_manifest` to normalize the destination,
and imports the mesh as a StaticMesh using the same execution substrate as the
asset import tools.

On success it returns:

- `downloads`: local files collected from the short-lived Tripo URLs.
- `manifest`: normalized `/Game/...` destination and expected asset paths.
- `asset_paths`: primary StaticMesh path plus optional material instance and
  Blueprint shell paths.
- `preview_asset_path`: the preferred `/Game/...` StaticMesh path for the
  dedicated Tripo Workspace preview.
- `preview_asset_reference`: the same path encoded as `@asset:/Game/...` so
  chat cards can route it through the existing asset-reference flow.
- `tripo_workspace_handoff`: the Unreal config section/key used by the chat
  dock to request a one-click preview in the Tripo Workspace.
- `thumbnail`: viewport screenshot evidence when the editor connection can
  capture it.

`create_material_instance=True` creates a material instance only when the import
produces an embedded base material to parent from. If Tripo/Interchange already
embedded textures in a GLB/FBX, this preserves that imported material chain. If
no base material exists, the tool reports a warning instead of inventing a
misleading material. `create_blueprint=True` creates an Actor Blueprint shell;
component wiring belongs to the playable-slice skill or Blueprint tools.

Example:

```python
gen_tripo_import_to_project(
    task_id="tripo_task_123",
    content_path="/Game/Generated/Enemies",
    asset_name="SM_Slime",
    create_material_instance=True,
    create_blueprint=False,
    capture_thumbnail=True,
)
```

## Texture-Only Path

`gen_texture_from_prompt` is the D.6 prompt-to-material entry point. It accepts
a material prompt, texture channels, resolution, destination content path, and a
master material path. The supported channel names are `BaseColor`, `Normal`,
`ORM`, and `Emissive`; aliases such as `albedo` and `diffuse` normalize to
`BaseColor`. Valid resolutions are `512`, `1024`, `2048`, and `4096`.

Tripo does not currently provide standalone prompt-only texture generation for
BaseColor/Normal/ORM texture sets. Its `texture_model` task requires an
existing `original_model_task_id`, so D.6 intentionally returns a structured
unsupported result instead of sending a misleading paid request. The result
includes:

- `provider_support`: why the selected provider cannot satisfy the request.
- `requested_texture_set`: normalized prompt, channels, and resolution.
- `materialization_plan`: expected Texture2D paths, Material Instance path,
  texture parameter names, and the material-tools sequence.
- `tripo_model_task_alternative`: the existing `gen_tripo_texture_model`
  route when a model task already exists.

Use the returned `material_tool_handoff` after a future Stability, ComfyUI, or
local texture provider produces actual Texture2D assets:

```python
gen_texture_from_prompt(
    prompt="wet mossy dungeon stone, hand-painted fantasy style",
    channels=["BaseColor", "Normal", "ORM"],
    resolution=1024,
    content_path="/Game/Generated/Dungeon",
    asset_name="MossyStone",
    master_material_path="/Game/Materials/M_Master_GeneratedTexture",
)

material_create_master(
    material_name="M_Master_GeneratedTexture",
    folder_path="/Game/Materials",
    use_texture_parameters=True,
    save=True,
)

material_create_instance_from_master(
    instance_name="MI_MossyStone",
    parent_material_path="/Game/Materials/M_Master_GeneratedTexture",
    folder_path="/Game/Generated/Dungeon/Materials",
)

material_set_instance_parameters_bulk(
    material_instance_path="/Game/Generated/Dungeon/Materials/MI_MossyStone",
    texture_parameters={
        "BaseColorTexture": "/Game/Generated/Dungeon/Textures/T_MossyStone_BaseColor",
        "NormalTexture": "/Game/Generated/Dungeon/Textures/T_MossyStone_Normal",
        "ORMTexture": "/Game/Generated/Dungeon/Textures/T_MossyStone_ORM",
    },
)
```

## Texture Paint Viewport Snapshots

`gen_capture_texture_paint_snapshot` captures the active Unreal viewport for a
Texture/Paint session and records it on the session as a source or result view.
Use it after `gen_prepare_texture_paint_session` while the model is framed in
the editor viewport, then again after import or manual inspection when useful.

The tool calls the existing native `take_screenshot` bridge, saves a PNG under
`.mcp_artifacts/texture_paint` by default, and updates the matching
`texture_paint_sessions.json` record. It can optionally upload the screenshot
to Tripo as an image file token handoff with `upload_to_tripo=True`; that upload
is a network operation but still does not spend generation credits.

Example:

```python
gen_capture_texture_paint_snapshot(
    session_name="demo",
    model_task_id="model-task-123",
    label="source_view",
    resolution=[1024, 1024],
    upload_to_tripo=False,
)
```

## In-Editor Texture/Paint Controls

The Generate Asset Workspace includes compact Texture/Paint controls so the
Unreal user can steer the Tripo-style edit loop without hiding all control in
prompt prose:

- `view_label` names the current viewport capture, usually `source_view` or a
  direction such as `front_view`.
- `brush_strength` is clamped from `0.0` to `1.0` and passed to
  `gen_prepare_texture_paint_session`.
- `blend` and `brush_radius` are encoded into the `blend_mode` and
  `paint_notes` fields for the texture-paint session.
- `upload_to_tripo` controls whether `gen_capture_texture_paint_snapshot`
  uploads the viewport PNG as a Tripo file token handoff. This may use network
  access but does not spend generation credits by itself.

The generated prompt should use `prepare_result.outputs.tripo_texture_prompt`
for `gen_tripo_texture_model` when available. That composed prompt preserves
the user's paint controls, reference image, view angle, and rotation/blending
notes through the paid texture task.

## Texture Paint Pass Records

`gen_record_texture_paint_pass` records a no-spend paint/blend pass on the
current Texture/Paint session. Use it after the generated texture has been
applied or imported and the user has inspected the model in the Unreal viewport.

Each pass stores:

- source and result snapshot labels;
- texture task id and imported texture/material asset path when available;
- affected model regions;
- brush strength, brush radius, blend amount, and blend mode;
- pass notes and the user's approval note.

This does not call Tripo, mutate Unreal assets, or reserve credits. It gives the
session an auditable record of the user's iterative paint decisions so final
evidence can prove that the workflow included a paint/blend pass, not only a
texture generation task.

Example:

```python
gen_record_texture_paint_pass(
    session_name="demo",
    model_task_id="model-task-123",
    pass_label="front_panel_highlights",
    source_snapshot_label="source_view",
    result_snapshot_label="source_view_painted",
    texture_task_id="texture-task-456",
    texture_asset_path="/Game/Generated/MI_PatinaPass",
    affected_regions="front armor panels and bevel highlights",
    brush_strength=0.7,
    brush_radius=0.3,
    blend_amount=0.55,
    blend_mode="soft blend",
    approval_note="Approved front paint pass after viewport inspection.",
)
```

## Texture Paint Evidence

Texture-paint work should end with a no-spend proof receipt, not just a verbal
summary. After `gen_prepare_texture_paint_session`,
`gen_capture_texture_paint_snapshot`, `gen_tripo_texture_model`,
`gen_tripo_wait_for_task`, `gen_tripo_import_to_project`, a painted-result
snapshot, and `gen_record_texture_paint_pass`, call
`gen_compile_texture_paint_evidence`.

The compiler returns `unreal_mcp_texture_paint_evidence.v1` with:

- the original model task id and texture task id;
- final Tripo status and consumed credit when available;
- the texture prompt, reference image, brush strength, blend mode, view angle,
  and paint notes;
- recorded paint passes and the latest paint pass;
- imported asset paths and viewport/thumbnail/session snapshot evidence;
- human approval note;
- readiness gates and next actions when evidence is still partial.

The compiler does not call Tripo, mutate Unreal, reserve credits, or spend
credits. `proven=true` requires a prepared session, source model task, texture
task id, successful final status, imported assets, viewport evidence, at least
one recorded paint pass, and human approval note.

Example:

```python
gen_compile_texture_paint_evidence(
    session_name="demo",
    prepare_result_json="<gen_prepare_texture_paint_session result>",
    texture_task_result_json="<gen_tripo_texture_model result>",
    wait_result_json="<gen_tripo_wait_for_task result>",
    import_result_json="<gen_tripo_import_to_project result>",
    approval_note="Approved after viewport inspection.",
)
```

## D8 Generative Runbook

Use this section when the user asks for generated game content and the agent
needs to choose the next safe tool call without guessing.

### Canonical Prompts

Asset prompt for a single mesh:

```text
Create a game-ready <asset role> for a UE5.6 <genre> playable slice. Style:
<art direction>. Requirements: readable silhouette, centered pivot, real-world
scale, clean UVs, simple collision-friendly proportions, PBR textures, no text
or logos. Use this gameplay purpose: <purpose in the level>.
```

Playable-slice brief:

```text
Build me a third-person dungeon-crawler demo with a slime, a skeleton, and a
boss room. Keep the level compact, readable, and playable in PIE.
```

Texture/material prompt:

```text
Wet mossy dungeon stone, hand-painted fantasy style, usable as a tiling UE5
material with BaseColor, Normal, and ORM channels.
```

### Expected Tool Sequence

1. Discover readiness with `gen_list_providers` and
   `gen_get_provider_config(include_paths=True)`.
2. If the request is only planning, use `skill_generate_playable_slice(mode="plan")`
   or `gen_prepare_import_manifest` dry runs. These paths require no API key.
3. If a paid Tripo request is needed, confirm `TRIPO_API_KEY` exists and run
   `gen_check_credit_budget(..., confirm_spend=True, reserve_credits=True)`.
4. Submit exactly the needed Tripo tasks with `gen_tripo_text_to_model`,
   `gen_tripo_image_to_model`, `gen_tripo_multiview_to_model`,
   `gen_tripo_refine_model`, `gen_tripo_texture_model`, or
   `gen_tripo_post_process`.
5. Poll with `gen_tripo_wait_for_task(timeout_s=900, poll_s=10)` for ordinary
   assets. Use a longer timeout only after telling the user the wait changed.
6. Download promptly with `gen_tripo_download_result`; signed provider URLs are
   short-lived.
7. Convert downloads into Unreal expectations with `gen_prepare_import_manifest`.
8. Import with `gen_tripo_import_to_project`, then assign or repair materials
   with the material tools.
9. Place assets, compile/save touched Blueprints, validate imports, run PIE or
   viewport evidence capture, and finish an execution journal or vertical-slice
   report.

### Expected Runtime

| Stage | Expected local time | Notes |
| --- | ---: | --- |
| Provider/config checks | < 5 s | Offline unless reading local secrets/settings. |
| Budget confirmation | < 5 s | Requires explicit user approval for paid calls. |
| Tripo text/image/multiview task submission | 5-30 s | Network/API dependent after confirmation. |
| Tripo model generation wait | 2-15 min per asset | Poll every 10 s; four slice assets may overlap. |
| Download and manifest prep | 10-90 s | Depends on output size and signed URL validity. |
| Unreal import/material handoff | 1-5 min | Depends on Interchange import and asset complexity. |
| Slice assembly and evidence | 5-15 min | Blueprint, AI, level, HUD, PIE, screenshots, report. |

A complete D.7-style playable slice should target the directive's under-30
minute bar only when Tripo tasks run in parallel and the project already has
usable third-person, AI, UMG, and report tooling available.

### Known Failure Modes

| Failure | Symptom | Recovery |
| --- | --- | --- |
| Missing API key | `auth_required` or provider config shows no key | Set `TRIPO_API_KEY` or `Saved/MCPChat/secrets.json`, then retry the paid step only. |
| Spend not confirmed | `spend_confirmation_required` or unapproved budget | Ask for confirmation and rerun with `confirm_spend=True`. |
| Budget exhausted | Credit guard denies reservation | Lower asset count/quality or increase the session budget after approval. |
| Provider task failed | Wait/status returns a final failed state | Preserve task id, prompt, and provider response in the journal; retry with a simpler prompt. |
| Signed URL expired | Download returns 403/404 or missing output | Re-query task status and download immediately; if no URL remains, rerun post-process. |
| Unsupported texture-only request | `gen_texture_from_prompt` returns unsupported | Use the material handoff plan or texture an existing model with `gen_tripo_texture_model`. |
| Import creates poor scale/pivot/collision | Asset appears huge, tiny, offset, or nonblocking | Normalize import settings, create collision, and document art follow-up. |
| Material instance cannot be created | No imported base material or texture slots | Keep imported material chain, warn, and use material tools once Texture2D assets exist. |
| PIE evidence fails | Logs show BP/runtime errors | Run compile/report tools, repair Blueprints, rerun PIE, then update the report. |

### Evidence Contract

Every generated content run should leave these records in the final result or
execution journal:

- original prompt and any negative constraints;
- provider, model version, task id, credit estimate, and confirmation state;
- downloaded file paths and expected `/Game/...` asset paths;
- import result, warnings, material/collision notes, and touched assets;
- compile/PIE/log/screenshot evidence for playable use;
- known follow-ups for human art, design, licensing, or optimization review.

## D9 Chat Dock Integration

The in-editor MCP Chat dock is the preferred surface for user-facing generated
asset work. Use the top-bar Generate Asset Workspace for Tripo `text_to_model`,
`image_to_model`, `multiview_to_model`, or texture-paint planning without
leaving Unreal.

The Tripo Workspace should open as its own Unreal editor window with a large
generated-asset viewport, similar to the experience of double-clicking an
imported mesh asset. Keep the chat dock available for conversational direction,
tool progress, and evidence receipts, but do not force the full creative
texture/model workflow to live inside the chat column. This keeps generation,
inspection, and texture-paint iteration organized in a familiar Unreal shape.

The workspace viewport uses an editor preview scene, not a raw blank viewport.
The first supported preview flow is to paste a generated `/Game/...` Static
Mesh asset path, load it into the workspace's preview component, and frame it
for inspection. Future Tripo import/evidence cards should hand their imported
asset path directly into this standalone workspace so generated assets open
like native Unreal assets.

Chat messages and tool cards that contain `@asset:/Game/...` or raw `/Game/...`
asset paths can request a Tripo preview directly. The chat panel saves the
target to `UnrealMCP.TripoWorkspace/PreviewAssetPath` in the editor config and
opens or focuses the Tripo Workspace `SWindow`. The workspace polls that value,
updates its asset path field, loads the Static Mesh into the preview scene, and
frames it. This is the current bridge from generated/imported asset evidence
into the Unreal-style workspace window.

The dedicated workspace mode rail is stateful. Text to 3D, Multi Image to 3D,
and Texture Paint switch the right-side controls, preserve the user's prompt
state, and can copy an MCP-ready prompt for the chat execution path. The same
rail reads `Saved/MCPChat/generative_settings.json` and displays the local
session credit budget, pending spend, confirmation state, output folder, and
Smart Mesh policy so the workspace carries the same generative context as the
chat dock.

Texture Paint mode exposes the paint loop controls directly in the standalone
workspace: current view label, brush strength, blend amount, brush radius, and
whether to upload the viewport snapshot to Tripo. These values are mirrored into
the native details object and into the copied MCP prompt so the generated
texture pass preserves the user's paint/blend intent instead of reducing it to
a plain text prompt.

The workspace also owns a transient `UTripoWorkspaceSession` object and displays
it through `FPropertyEditorModule::CreateDetailView`. This mirrors Unreal's
native asset editors, where session/asset settings live in an `IDetailsView`
instead of only in custom Slate rows. The details object tracks active mode,
preview asset path, provider, output folder, Smart Mesh policy, local credit
budget, pending spend, target asset name, reference views, texture task id,
paint view label, brush/blend/radius controls, and snapshot upload intent. API
keys remain in the saved secrets path, not in the details object.

The standalone workspace now includes an Unreal-style action toolbar and status
strip. The toolbar keeps mode switching, preview loading/framing, prompt copy,
and generative-credit refresh in the same top action row as other editor asset
workflows. The status strip mirrors the current mode, preview result, local
credit budget, pending spend, confirmation state, output folder, and Smart Mesh
policy so users can see generation context while inspecting the model viewport.
Refreshing credits also performs the no-spend Tripo API wallet balance check
against `/user/balance` when an API key is available, and the workspace displays
provider-side available/frozen credits beside the local Unreal-MCP budget.

Smart Mesh is a locked topology policy in the standalone workspace, not a user
preference. Mesh generation prompts, chat handoff context, and the native
details object all keep `smart_low_poly=true` and `face_limit=12000` so generated
assets target Unreal/game-ready topology by default.

The toolbar can also send the current workspace request directly to MCP Chat.
This posts the MCP-ready request as a human message to the `tripo-workspace`
chat session with context fields for source, active mode, preview asset path,
target asset name, auth source, Smart Mesh, and face limit. Chat remains the
execution/progress/evidence surface while the standalone workspace remains the
asset-editor-style creative control surface.

The workspace also exposes a masked Tripo API key field. Saving from this field
writes the same `Saved/MCPChat/secrets.json` contract used by the chat dock and
Python MCP server; `TRIPO_API_KEY` in the editor environment still takes
precedence. The details view records only the key source (`env:TRIPO_API_KEY`,
`Saved/MCPChat/secrets.json`, or `missing`), never the secret value.

1. Open Generate Asset.
2. Choose mode: `text_to_model`, `image_to_model`, `multiview_to_model`, or
   `texture_paint`.
3. Enter the prompt, target Unreal asset name, and any reference image paths,
   ordered multiview entries, or existing Tripo model task id.
4. For `texture_paint`, set the view label, brush strength, blend amount,
   brush radius, and whether the viewport snapshot should upload to Tripo.
5. Smart Mesh is locked on. The chat dock and standalone workspace insert
   `smart_low_poly=true` and `face_limit=12000` for mesh generation because
   Unreal needs game-ready topology by default.
6. Confirm the current model version, texture quality, output folder, and spend
   state shown from the existing Generate Asset Settings panel.
7. Insert the generated workspace request into the composer.
8. Send only after the user has approved the spend gate. The inserted request
   keeps `confirm_spend=false` until the panel spend confirmation is active.
9. Follow with `gen_tripo_wait_for_task`; Tripo progress fields render as an
   inline progress bar in the chat tool card.
10. Import successful outputs with `gen_tripo_import_to_project`.

Mode mapping:

| Workspace mode | Tool sequence |
| --- | --- |
| `text_to_model` | `gen_tripo_text_to_model` -> `gen_tripo_wait_for_task` -> `gen_tripo_import_to_project` |
| `image_to_model` | `gen_tripo_image_to_model` -> `gen_tripo_wait_for_task` -> `gen_tripo_import_to_project` |
| `multiview_to_model` | `gen_tripo_multiview_to_model` -> `gen_tripo_wait_for_task` -> `gen_tripo_import_to_project` |
| `texture_paint` | `gen_prepare_texture_paint_session` -> `gen_capture_texture_paint_snapshot` -> `gen_tripo_texture_model` -> `gen_tripo_wait_for_task` -> `gen_tripo_import_to_project` -> result `gen_capture_texture_paint_snapshot` -> `gen_record_texture_paint_pass` -> `gen_compile_texture_paint_evidence` |

Long-running Tripo waits should stream or post structured progress updates that
include the tool name `gen_tripo_wait_for_task` and a numeric `progress` field.
The chat panel accepts either `0.0-1.0` or `0-100` progress values and clamps
them before rendering.

## Working Example

Goal: bring a generated grocery shelf prop into a playable slice.

1. Record the prompt, generator, version, and output files in the journal.
2. Import the mesh into `/Game/Generated/Props/Grocery/`.
3. Normalize scale and pivot; create collision suitable for the prop.
4. Import base color, normal, and ORM textures; compress them appropriately.
5. Create `MI_GroceryShelf_A` from the project master material.
6. Assign materials, save assets, and inspect references/size.
7. Place one prop in the level, capture a screenshot, and log any needed art
   fixes.

## Validation Checklist

- Prompt/provenance and source files are recorded.
- Asset names and folders follow project conventions.
- Mesh scale, pivot, collision, UVs, material slots, and texture compression are
  checked.
- Runtime placement is verified visually and through asset scans.
- Generated content has an owner and follow-up list for human review.

## References

- Epic: Importing Assets Directly -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/importing-assets-directly-into-unreal-engine
- Epic: Working with Assets -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/working-with-assets-in-unreal-engine
- Epic: Interchange Framework -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/importing-assets-using-interchange-in-unreal-engine
