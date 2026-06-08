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
| Inspect provider config/auth | `gen_get_provider_config` |
| Save provider defaults | `gen_save_provider_config` |
| Guard paid credit spend | `gen_check_credit_budget` |
| Submit Tripo generation tasks | `gen_tripo_text_to_model`, `gen_tripo_image_to_model`, `gen_tripo_multiview_to_model` |
| Refine, texture, or export Tripo results | `gen_tripo_refine_model`, `gen_tripo_texture_model`, `gen_tripo_post_process` |
| Plan prompt-only texture sets | `gen_texture_from_prompt` |
| Plan Tripo Magic Brush paint sessions | `gen_prepare_texture_paint_session` |
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
- D.9 adds the MCP Chat dock quick action for Tripo asset generation and inline
  progress rendering for long-running Tripo waits.

Agents should use this provider list as a capability map, not as proof that a
paid generation request has been sent. D.2 can resolve auth/config state, but it
still makes no Tripo API call.

Example:

```python
gen_list_providers(include_import_helpers=True)
```

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
secrets file for per-project editor sessions. In-editor users can paste the
Tripo API key into the password-style `TRIPO_API_KEY` field, save it to
`Saved/MCPChat/secrets.json`, or clear it from the same drawer. Generate Asset
insertion is gated until the key is available from either source.

Example:

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

Because Unreal is the target runtime, new model generation defaults to Tripo's
Smart Mesh path through `smart_low_poly=True` for text, image, and multiview
tasks. Keep it enabled unless a specific art-review workflow needs rawer
provider output; imported assets should favor game-ready topology over maximum
sculpt detail.

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
    smart_low_poly=True,
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

## Magic Brush Texture Edit Sessions

`gen_prepare_texture_paint_session` records an offline Tripo Studio Magic Brush
plan in `Saved/MCPChat/texture_paint_sessions.json`. It does not call Tripo,
upload viewport renders, paint pixels, or spend credits. Use it when the Unreal
chat UI needs to mirror Tripo's `Edit` tab before the user commits to a paid
operation.

The inspected Tripo Studio route is:

```text
https://studio.tripo3d.ai/workspace/texture-edit
```

The observed Studio UX is:

1. Select or upload a textured model from the right Assets panel.
2. In **Magic Brush**, use Gen Mode with a prompt and creativity strength to
   generate preview texture images from the current mesh view.
3. Choose a generated image, or switch to Paint Mode color.
4. Open the brush bar and adjust size, strength, and hardness.
5. Paint/blend onto the model, rotate the viewport, repeat as needed, and save.

The observed Studio API flow is now represented by dedicated MCP wrappers:

- `gen_tripo_magic_brush_generate` posts `retexture_generate` with
  `camera_matrix`, `model_version`, `project_id`, `prompt`, `render_image`, and
  `strength`. `render_image` should be the uploaded viewport snapshot object
  observed in Studio, usually `{bucket, key}`.
- `gen_tripo_magic_brush_get_retexture` fetches a completed generated texture
  image by `operator_id`.
- `gen_tripo_magic_brush_list_images` calls `get_retexture_images` for the
  Studio project image history.
- `gen_tripo_magic_brush_apply` saves/applies painted image parts through
  `apply_retexture` with `image_map`, `model_version`, and `project_id`.

The planning step remains useful because Unreal still has to capture/upload the
viewport snapshot and compile painted image parts before the Studio wrappers can
run:

```python
gen_prepare_texture_paint_session(
    model_task_id="model-task-id",
    texture_prompt="weathered copper with bright worn edges",
    texture_reference_image="C:/Refs/copper_style.png",
    viewport_view="front_three_quarter",
    brush_strength=0.25,
    brush_hardness=0.35,
    creativity_strength=0.7,
    blend_mode="soft_overlay",
    paint_notes="blend across shoulder seams",
    save_name="MI_CopperKnight_Edit",
    tripo_project_id="studio-project-id",
)
```

Once the snapshot upload and paint compile outputs are available, use:

```python
gen_tripo_magic_brush_generate(
    project_id="studio-project-id",
    prompt="weathered copper with bright worn edges",
    render_image={"bucket": "uploaded-bucket", "key": "viewport.png"},
    camera_matrix=[...],
    strength=0.7,
    confirm_spend=True,
)

gen_tripo_magic_brush_get_retexture(operator_id="<operator_id>")

gen_tripo_magic_brush_apply(
    project_id="studio-project-id",
    image_map=[
        {"part_name": "Body", "image": {"bucket": "painted-bucket", "key": "body.png"}},
    ],
    confirm_spend=True,
)
```

`gen_tripo_texture_model`, `gen_tripo_wait_for_task`, and
`gen_tripo_import_to_project` remain the public OpenAPI fallback when Studio
project ids, viewport snapshot uploads, or image-map paint data are unavailable.

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
asset work. Use the top-bar Generate Asset action as the Tripo workspace inside
Unreal. Current Tripo workspace modes are:

- Text to 3D: inserts `gen_tripo_text_to_model` with `smart_low_poly: true`.
- Image to 3D: inserts `gen_tripo_image_to_model` with an image path or URL and
  `smart_low_poly: true`.
- Multi-Image to 3D: inserts `gen_tripo_multiview_to_model` with ordered
  front, left, back, and right reference inputs and `smart_low_poly: true`.
- Texture/Paint: inserts `gen_prepare_texture_paint_session` first, then a
  gated Studio Magic Brush sequence when project and render data exist:
  `gen_tripo_magic_brush_generate`, `gen_tripo_magic_brush_get_retexture`,
  optional `gen_tripo_magic_brush_list_images`, and
  `gen_tripo_magic_brush_apply`. The planning call captures texture direction,
  optional reference image, paint/blend notes, viewport angle, render image
  bucket/key or URL, camera matrix JSON, brush size, strength, hardness,
  creativity strength, paint mode/color, blend mode, Tripo project id,
  `image_map` JSON, and save-name intent. If Studio project/snapshot/image-map
  data is unavailable, use the gated `gen_tripo_texture_model` fallback for an
  existing model task.

The Generate Asset panel keeps the active mode focused: Text to 3D shows only
the text prompt, Image to 3D shows the single reference-image field,
Multi-Image to 3D shows the ordered view references, and Texture/Paint shows
the Magic Brush controls. This avoids presenting every Tripo field at once in
the Unreal dock.

The top-bar **Playable Slice** action is the higher-level generative workspace
entry point. It captures a one-sentence game brief, generated asset roles,
gameplay loop, acceptance criteria, and evidence requirements, then inserts a
workflow that creates Smart Mesh Tripo assets, imports them into
`/Game/Generated/PlayableSlice`, builds Blueprint/UMG/level gameplay around
them, and verifies the result with compile, PIE, log, and screenshot evidence.

The Generate Asset workspace and its settings panel include a **Generative
Credits** display. It shows the per-session budget, credits used from
`credit_usage_by_session`, remaining credits, the next pending spend, and whether
that spend is confirmed. The UI preserves the server's
`credit_usage_by_session` map when saving local settings so budget history is not
lost when a user updates the Tripo key, model version, texture quality, or output
folder.

1. Open Generate Asset.
2. Select the workspace mode and fill the active prompt/image/task fields.
3. Confirm the current model version, texture quality, output folder, and spend
   state shown from the existing Generate Asset Settings panel.
4. Insert the generated Tripo request into the composer.
5. For Texture/Paint, run the inserted `gen_prepare_texture_paint_session`
   portion before spend approval; it records the no-spend Magic Brush plan.
6. Send paid task calls only after the user has approved the spend gate. The
   inserted request keeps `confirm_spend=false` until the panel spend
   confirmation is active.
7. Follow with `gen_tripo_wait_for_task`; Tripo progress fields render as an
   inline progress bar in the chat tool card.
8. Import successful outputs with `gen_tripo_import_to_project`.

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
