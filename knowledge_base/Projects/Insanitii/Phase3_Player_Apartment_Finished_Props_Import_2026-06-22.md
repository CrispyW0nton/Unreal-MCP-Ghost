# Phase 3 Player Apartment Finished Props Import - 2026-06-22

## Context

The user provided finished apartment props at:

`C:\Users\NewAdmin\Documents\KaiGenInteractive\Insanitii\Assets\FinishedProps`

The request was to update the project plugin first, import all finished props, create a new apartment starter level, and then set the new meshes to strong prop collision.

## Plugin And Project Setup

- Synced the repo `unreal_plugin` folder into the Insanitii project at:
  - `C:\Users\NewAdmin\Documents\KaiGenInteractive\Insanitii\Insanitii\Plugins\UnrealMCP`
- Enabled `UnrealMCP` explicitly in `Insanitii.uproject` with an editor target allow list.
- Rebuilt the project successfully with `scripts\run_insanitii_clean_build_and_tripo_verify.ps1`.
- Regenerated project files with UnrealBuildTool after the `.uproject` changed, addressing the editor prompt that the project file was out of date / new plugins were available.
- Rebuilt again after regeneration; UnrealBuildTool reported the target was up to date.

## Import Path

The first attempt used a single live `exec_python` import through the Unreal MCP bridge. That hit the native access-violation guard during synchronous bulk asset import and the editor process closed. This matches the existing project rule that heavy asset import work should not be forced through the live socket callback.

The import was moved to command-line Unreal Python:

```powershell
UnrealEditor-Cmd.exe Insanitii.uproject -ExecutePythonScript=scripts\ue_import_insanitii_finished_props_apartment.py -unattended -nop4 -nosplash
```

This completed successfully and wrote:

`Saved\Automation\insanitii_finished_props_apartment_import_receipt.json`

## Imported Assets

- Imported 42 finished prop folders.
- Created 42 StaticMesh assets under:
  - `/Game/Insanitii/Art/FinishedProps`
- Created the starter level:
  - `/Game/Insanitii/Maps/Lvl_PlayerApartment`
- Added starter level actors:
  - `APT_Floor_Square`
  - `APT_Key_DirectionalLight`
  - `APT_SkyLight`
  - `APT_Apartment_PointLight`
  - `APT_PlayerStart`

## Material Repair

Unreal's OBJ importer did not consistently create materials/textures for every folder because many source OBJs did not include usable `mtllib` / `usemtl` references even though their folders contained JPG basecolor images.

A commandlet material repair pass was added:

```powershell
UnrealEditor-Cmd.exe Insanitii.uproject -ExecutePythonScript=scripts\ue_repair_insanitii_finished_prop_materials.py -unattended -nop4 -nosplash
```

It imported each folder's basecolor image, created a simple basecolor material, and assigned it to the matching StaticMesh.

Verification receipt:

`Saved\Automation\insanitii_finished_props_material_repair_receipt.json`

Result:

- 42 props repaired.
- 42 basecolor textures created.
- 42 basecolor materials created.
- 42 meshes assigned a material.
- No missing source textures.
- No missing meshes.

## Collision Pass

The user asked to set the new meshes to simple collision as complex. This was applied as Unreal's `Use Complex Collision As Simple` mesh collision setting:

`CollisionTraceFlag = CTF_USE_COMPLEX_AS_SIMPLE`

Commandlet:

```powershell
UnrealEditor-Cmd.exe Insanitii.uproject -ExecutePythonScript=scripts\ue_set_insanitii_finished_prop_collision_complex_as_simple.py -unattended -nop4 -nosplash
```

Verification receipt:

`Saved\Automation\insanitii_finished_props_collision_receipt.json`

Result:

- 42 StaticMesh assets found under `/Game/Insanitii/Art/FinishedProps`.
- 42 updated.
- 42 verified as `CTF_USE_COMPLEX_AS_SIMPLE`.
- 0 failed meshes.
- Dirty packages saved.

## Final Verification

Apartment import verification command:

```powershell
UnrealEditor-Cmd.exe Insanitii.uproject -ExecutePythonScript=scripts\ue_verify_insanitii_apartment_import.py -unattended -nop4 -nosplash
```

Verification receipt:

`Saved\Automation\insanitii_apartment_import_verification_receipt.json`

Result:

- `success: true`
- `source_prop_count: 42`
- `static_mesh_count: 42`
- `basecolor_texture_count: 42`
- `texture_material_count: 42`
- all five apartment starter actors present
- no unassigned meshes

## Notes

Complex-as-simple collision is appropriate for static apartment set dressing where visible shape fidelity matters. If any of these props later become movable physics objects, they should receive authored simple convex hulls or UCX collision instead, because complex-as-simple is not a good fit for fully simulated dynamic rigid bodies.
