# Generative Content Pipeline
> Source: project notes, MCP import/tooling roadmap, Unreal asset pipeline practice
> Last Updated: 2026-06-07 | UE 5.6

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
| Poll and collect Tripo outputs | `gen_tripo_get_task_status`, `gen_tripo_wait_for_task`, `gen_tripo_download_result` |
| Prepare import handoff | `gen_prepare_import_manifest` |
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

Agents should use this provider list as a capability map, not as proof that a
paid generation request has been sent. D.2 can resolve auth/config state, but it
still makes no Tripo API call.

Example:

```python
gen_list_providers(include_import_helpers=True)
```

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
