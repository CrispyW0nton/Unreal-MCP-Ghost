# Unreal-MCP-Ghost — API Reference Cheat Sheet

> Quick reference for all UE5 Python APIs needed for Phases 1-4.
> All code runs inside UE5 via `exec_python` or as standalone editor scripts.

---

## 1. ASSET IMPORT APIs

### Core Import Function
```python
import unreal

# The universal import function
task = unreal.AssetImportTask()
task.set_editor_property('filename', r'C:\Assets\model.fbx')       # Source file (OS path)
task.set_editor_property('destination_path', '/Game/Meshes/')        # Content Browser path
task.set_editor_property('destination_name', 'SM_MyModel')           # Optional: override name
task.set_editor_property('automated', True)                          # No dialog popups
task.set_editor_property('save', True)                               # Auto-save after import
task.set_editor_property('replace_existing', True)                   # Overwrite if exists
task.set_editor_property('replace_existing_settings', True)          # Reuse existing settings

# Execute import
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
asset_tools.import_asset_tasks([task])  # Accepts list — batch import!

# Get result
imported_object = task.get_editor_property('imported_object')
# Returns the UObject, or None if failed
```

### FBX Import Options (Static Mesh)
```python
options = unreal.FbxImportUI()
options.set_editor_property('import_mesh', True)
options.set_editor_property('import_textures', True)
options.set_editor_property('import_materials', True)
options.set_editor_property('import_as_skeletal', False)  # Static mesh

# Static mesh specific
options.static_mesh_import_data.set_editor_property('combine_meshes', True)
options.static_mesh_import_data.set_editor_property('generate_lightmap_u_vs', True)
options.static_mesh_import_data.set_editor_property('auto_generate_collision', True)
options.static_mesh_import_data.set_editor_property('one_convex_hull_per_ucx', True)

task.set_editor_property('options', options)
```

### FBX Import Options (Skeletal Mesh)
```python
options = unreal.FbxImportUI()
options.set_editor_property('import_mesh', True)
options.set_editor_property('import_as_skeletal', True)
options.set_editor_property('import_animations', True)

# Reuse existing skeleton
skeleton = unreal.EditorAssetLibrary.load_asset('/Game/Characters/SK_Mannequin_Skeleton')
options.set_editor_property('skeleton', skeleton)

# Skeletal mesh specific
options.skeletal_mesh_import_data.set_editor_property('import_morph_targets', True)
options.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose', False)

# Animation specific (when importing animations)
options.anim_sequence_import_data.set_editor_property('import_bone_tracks', True)
options.anim_sequence_import_data.set_editor_property('remove_redundant_keys', True)

task.set_editor_property('options', options)
```

### Texture Compression Settings
```python
# After importing a texture, set compression based on type
tex = unreal.EditorAssetLibrary.load_asset('/Game/Textures/T_MyTexture')

# Normal map
tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
tex.set_editor_property('srgb', False)

# Roughness / Metallic / AO (masks)
tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
tex.set_editor_property('srgb', False)

# HDR
tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_HDR)

# Default (BaseColor, Emissive)
tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_DEFAULT)
tex.set_editor_property('srgb', True)
```

### Asset Library Utilities
```python
# Check if asset exists
exists = unreal.EditorAssetLibrary.does_asset_exist('/Game/Meshes/SM_MyModel')

# Load asset
asset = unreal.EditorAssetLibrary.load_asset('/Game/Meshes/SM_MyModel')

# List assets in folder
assets = unreal.EditorAssetLibrary.list_assets('/Game/Meshes/', recursive=True)

# Delete asset
unreal.EditorAssetLibrary.delete_asset('/Game/Meshes/SM_OldModel')

# Duplicate asset
unreal.EditorAssetLibrary.duplicate_asset('/Game/Source', '/Game/Dest')

# Rename asset
unreal.EditorAssetLibrary.rename_asset('/Game/OldName', '/Game/NewName')

# Save asset
unreal.EditorAssetLibrary.save_asset('/Game/Meshes/SM_MyModel')

# Save all dirty packages
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
```

---

## 2. MATERIAL CREATION APIs

### Create Material
```python
import unreal
mel = unreal.MaterialEditingLibrary
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

# Create base material
material = asset_tools.create_asset(
    'M_MyMaterial',              # Asset name
    '/Game/Materials/',           # Path
    unreal.Material,              # Class
    unreal.MaterialFactoryNew()   # Factory
)
```

### Add Material Expressions (Nodes)
```python
# Texture Sample node
tex_sample = mel.create_material_expression(
    material,                                    # Parent material
    unreal.MaterialExpressionTextureSample,      # Node class
    -400, 0                                       # X, Y position in graph
)
# Assign texture to the node
tex_sample.set_editor_property('texture',
    unreal.EditorAssetLibrary.load_asset('/Game/Textures/T_BaseColor'))

# Scalar Parameter
scalar_param = mel.create_material_expression(
    material, unreal.MaterialExpressionScalarParameter, -400, 400)
scalar_param.set_editor_property('parameter_name', 'Roughness')
scalar_param.set_editor_property('default_value', 0.5)

# Vector Parameter (for colors)
vec_param = mel.create_material_expression(
    material, unreal.MaterialExpressionVectorParameter, -400, 200)
vec_param.set_editor_property('parameter_name', 'BaseColor')
vec_param.set_editor_property('default_value', unreal.LinearColor(r=1, g=0, b=0, a=1))

# Multiply node
multiply = mel.create_material_expression(
    material, unreal.MaterialExpressionMultiply, -200, 0)

# Lerp node
lerp = mel.create_material_expression(
    material, unreal.MaterialExpressionLinearInterpolate, -200, 200)

# Texture Coordinate
tex_coord = mel.create_material_expression(
    material, unreal.MaterialExpressionTextureCoordinate, -600, 0)
tex_coord.set_editor_property('u_tiling', 2.0)
tex_coord.set_editor_property('v_tiling', 2.0)
```

### Connect Material Expressions
```python
# Connect texture RGB output to material Base Color input
mel.connect_material_expressions(
    tex_sample,   'RGB',        # From node, output name
    material,     'BaseColor'   # To node (material), input name
)

# Connect normal map to Normal input
normal_sample.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
mel.connect_material_expressions(normal_sample, 'RGB', material, 'Normal')

# Connect scalar to Roughness
mel.connect_material_expressions(scalar_param, '', material, 'Roughness')

# Connect multiply: A * B
mel.connect_material_expressions(tex_sample, 'RGB', multiply, 'A')
mel.connect_material_expressions(vec_param, '', multiply, 'B')
mel.connect_material_expressions(multiply, '', material, 'BaseColor')
```

### Material Properties
```python
# Shading model
material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_DEFAULT_LIT)

# Blend mode
material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_OPAQUE)

# Two-sided
material.set_editor_property('two_sided', True)

# Compile
mel.recompile_material(material)
```

### Material Instance
```python
# Create Material Instance Constant
factory = unreal.MaterialInstanceConstantFactoryNew()
mi = asset_tools.create_asset('MI_MyMaterial', '/Game/Materials/',
    unreal.MaterialInstanceConstant, factory)

# Set parent material
mi.set_editor_property('parent',
    unreal.EditorAssetLibrary.load_asset('/Game/Materials/M_Master'))

# Set parameters
unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
    mi, 'Roughness', 0.3)
unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
    mi, 'BaseColor', unreal.LinearColor(r=0.5, g=0.2, b=0.1, a=1))
unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
    mi, 'DiffuseTexture',
    unreal.EditorAssetLibrary.load_asset('/Game/Textures/T_Wood_D'))
```

---

## 3. IK RETARGETING APIs

### Create IK Rig
```python
import unreal

asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

# Create IK Rig asset
ikr = asset_tools.create_asset(
    'IKR_MyCharacter',
    '/Game/Animation/',
    unreal.IKRigDefinition,
    unreal.IKRigDefinitionFactory()
)

# Get the controller (required for all modifications)
ikr_controller = unreal.IKRigController.get_controller(ikr)

# Set skeletal mesh
skel_mesh = unreal.EditorAssetLibrary.load_asset('/Game/Characters/SK_MyChar')
ikr_controller.set_skeletal_mesh(skel_mesh)
```

### Auto-Setup (Bipedal Characters)
```python
# MAGIC FUNCTIONS — auto-detect bipedal skeleton and set up everything
ikr_controller.apply_auto_generated_retarget_definition()  # Creates retarget chains
ikr_controller.apply_auto_fbik()  # Creates FBIK solver + goals

# That's it! For standard bipedal characters this handles:
# - Spine chain (pelvis → head)
# - Left/Right arm chains
# - Left/Right leg chains
# - Retarget root
# - All IK goals
```

### Manual Chain Setup
```python
# Set retarget root bone
ikr_controller.set_retarget_root('pelvis')

# Add retarget chains
# add_retarget_chain(chain_name, start_bone, end_bone, goal_name)
ikr_controller.add_retarget_chain('Spine', 'spine_01', 'head', '')
ikr_controller.add_retarget_chain('LeftArm', 'clavicle_l', 'hand_l', 'hand_l_goal')
ikr_controller.add_retarget_chain('RightArm', 'clavicle_r', 'hand_r', 'hand_r_goal')
ikr_controller.add_retarget_chain('LeftLeg', 'thigh_l', 'foot_l', 'foot_l_goal')
ikr_controller.add_retarget_chain('RightLeg', 'thigh_r', 'foot_r', 'foot_r_goal')
ikr_controller.add_retarget_chain('LeftHand', 'hand_l', 'middle_03_l', '')
ikr_controller.add_retarget_chain('RightHand', 'hand_r', 'middle_03_r', '')

# Modify chain after creation
ikr_controller.set_retarget_chain_start_bone('Spine', 'spine_01')
ikr_controller.set_retarget_chain_end_bone('Spine', 'head')
ikr_controller.set_retarget_chain_goal('LeftArm', 'hand_l_goal')

# Rename chain
ikr_controller.rename_retarget_chain('LeftArm', 'Left_Arm')

# Remove chain
ikr_controller.remove_retarget_chain('Spine')

# Get all chains
chains = ikr_controller.get_retarget_chains()
```

### IK Solvers
```python
# Add FBIK solver
solver_index = ikr_controller.add_solver(unreal.IKRigFBIKSolver)

# Add goals to solver
ikr_controller.add_goal('hand_l_goal', 'hand_l', solver_index)
ikr_controller.add_goal('hand_r_goal', 'hand_r', solver_index)
ikr_controller.add_goal('foot_l_goal', 'foot_l', solver_index)
ikr_controller.add_goal('foot_r_goal', 'foot_r', solver_index)

# Connect goals to retarget chains
ikr_controller.connect_goal_to_chain('hand_l_goal', 'LeftArm')
```

### Create IK Retargeter
```python
# Create retargeter asset
retargeter = asset_tools.create_asset(
    'RTG_SourceToTarget',
    '/Game/Animation/',
    unreal.IKRetargeter,
    unreal.IKRetargetFactory()
)

# NOTE: Setting source/target IK Rigs on the retargeter may require
# using the IKRetargeterController (check UE version support)
# Fallback: create via Editor Utility Blueprint
```

### Batch Retarget Animations
```python
# NOTE: Batch retarget export may need Editor Utility Blueprint workaround
# The following is the target API pattern (may not be fully exposed):

# Option A: If IKRetargetBatchOperation is exposed
batch_op = unreal.IKRetargetBatchOperation()
batch_op.set_editor_property('retargeter', retargeter)
batch_op.set_editor_property('source_animations', [anim1, anim2, anim3])
batch_op.set_editor_property('export_path', '/Game/Animation/Retargeted/')
batch_op.run()

# Option B: Editor Utility Blueprint workaround
# Create a utility blueprint that calls the retarget UI function
# Execute via exec_python
```

---

## 4. UTILITY APIs (Frequently Used)

### Content Browser Operations
```python
# Create folder
unreal.EditorAssetLibrary.make_directory('/Game/NewFolder')

# Get asset data (metadata without loading)
asset_data = unreal.EditorAssetLibrary.find_asset_data('/Game/Meshes/SM_Model')
asset_class = str(asset_data.asset_class)

# Filter assets by class
registry = unreal.AssetRegistryHelpers.get_asset_registry()
filter = unreal.ARFilter(class_names=['StaticMesh'], package_paths=['/Game/Meshes'])
assets = registry.get_assets(filter)
```

### Actor Operations
```python
# Spawn actor from asset
actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
    unreal.StaticMeshActor, unreal.Vector(0, 0, 0))

# Set mesh on actor
mesh_comp = actor.get_component_by_class(unreal.StaticMeshComponent)
mesh_comp.set_static_mesh(
    unreal.EditorAssetLibrary.load_asset('/Game/Meshes/SM_Model'))

# Set material on actor
mesh_comp.set_material(0,
    unreal.EditorAssetLibrary.load_asset('/Game/Materials/M_MyMaterial'))

# Set transform
actor.set_actor_location(unreal.Vector(100, 200, 0), False, True)
actor.set_actor_rotation(unreal.Rotator(0, 45, 0), False)
actor.set_actor_scale3d(unreal.Vector(2, 2, 2))
```

### Project Introspection
```python
# Get project name
import os
project_name = os.path.basename(unreal.Paths.get_project_file_path()).replace('.uproject', '')

# Get UE version
version = unreal.SystemLibrary.get_engine_version()

# Get current level name
world = unreal.EditorLevelLibrary.get_editor_world()
level_name = world.get_name()

# Get all level actors
actors = unreal.EditorLevelLibrary.get_all_level_actors()

# Get all level actors of class
static_meshes = unreal.EditorLevelLibrary.get_all_level_actors_of_class(unreal.StaticMeshActor)
```

---

## 5. COMMON GOTCHAS

| Issue | Solution |
|-------|----------|
| `exec_python` output not captured | Use `print(str(result))` — the C++ handler captures stdout |
| Asset not found after import | Call `unreal.EditorAssetLibrary.save_asset()` and wait a frame |
| Material won't compile | Check all required inputs connected, call `mel.recompile_material()` |
| IK chains don't appear | Must call `set_skeletal_mesh()` before adding chains |
| FBX import dialog pops up | Set `task.automated = True` AND set `task.options` |
| Texture shows purple | sRGB/compression settings wrong for texture type |
| Path format | UE5 Content: `/Game/Folder/Asset` — OS: `C:\\Path\\File.fbx` |
| Python vs C++ types | `unreal.Vector(x, y, z)` not `(x, y, z)` tuple |
| Multiple imports | Pass list to `import_asset_tasks([task1, task2, ...])` |
