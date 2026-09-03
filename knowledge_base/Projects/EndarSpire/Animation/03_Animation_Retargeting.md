# 03 — Animation Retargeting Pipeline

> Project: Endar Spire | Plugin: Unreal-MCP-Ghost (419 tools) | UE 5.6

## Overview
Retarget animations from one skeleton to another using UE5 IK Rig → IK Retargeter pipeline. This is how all Sith, Heavy, and Republic soldier animations were created.

## Proven Pipeline (from BP_SithHeavyTrooper retarget)

### 1. Create IK Rig for source skeleton (if not exists)
exec_python code: | import unreal factory = unreal.IKRigDefinitionFactory() task = unreal.AssetImportTask() # Use create_ik_rig MCP tool or exec_python

MCP tool:
create_ik_rig name: "IKRig_SithSoldier" skeletal_mesh: "/Game/EndarSpire/Characters/RiggedModels/SithSoldier/SithSoldier" retarget_root: "pelvis" chains: [ {"name": "Spine", "start_bone": "spine_01", "end_bone": "head"}, {"name": "LeftArm", "start_bone": "clavicle_l", "end_bone": "hand_l"}, {"name": "RightArm", "start_bone": "clavicle_r", "end_bone": "hand_r"}, {"name": "LeftLeg", "start_bone": "thigh_l", "end_bone": "foot_l"}, {"name": "RightLeg", "start_bone": "thigh_r", "end_bone": "foot_r"} ]

### 2. Create IK Rig for target skeleton (match chain layout exactly)
create_ik_rig name: "IKRig_HeavySithTrooper" skeletal_mesh: "/Game/EndarSpire/Characters/RiggedModels/HeavySithTrooper/HeavySithTrooper1" retarget_root: "pelvis" chains: [ {"name": "Spine", "start_bone": "spine_01", "end_bone": "head"}, {"name": "LeftArm", "start_bone": "clavicle_l", "end_bone": "hand_l"}, {"name": "RightArm", "start_bone": "clavicle_r", "end_bone": "hand_r"}, {"name": "LeftLeg", "start_bone": "thigh_l", "end_bone": "foot_l"}, {"name": "RightLeg", "start_bone": "thigh_r", "end_bone": "foot_r"} ]

### 3. Create IK Retargeter
create_ik_retargeter name: "RTG_Sith_to_HeavySith" source_ik_rig: "/Game/EndarSpire/Characters/Sith/IKRig_SithSoldier" target_ik_rig: "/Game/EndarSpire/Characters/HeavySithTrooper/IKRig_HeavySithTrooper" chain_mapping: { "Spine": "Spine", "LeftArm": "LeftArm", "RightArm": "RightArm", "LeftLeg": "LeftLeg", "RightLeg": "RightLeg" }

### 4. Batch retarget animations
exec_python code: | import unreal retargeter = unreal.load_asset('/Game/EndarSpire/Characters/HeavySithTrooper/RTG_Sith_to_HeavySith') controller = unreal.IKRetargeterController.get_controller(retargeter) source_anims = unreal.EditorAssetLibrary.list_assets('/Game/EndarSpire/Characters/Sith/Animations/', recursive=True) for anim_path in source_anims: if 'RT_Sith_' in anim_path or 'A_Sith_' in anim_path: controller.batch_retarget([anim_path], '/Game/EndarSpire/Characters/HeavySithTrooper/Animations/')

## CRITICAL: Chain Layout Must Match
The source and target IK Rigs must have the SAME chain names and the SAME number of chains. Mismatched chains produce warped output. This was the root cause of the initial Heavy retarget failure — the auto-generated Heavy rig had extra root/neck/head/finger/IK-goal chains.

## Existing Retarget Assets
| Retargeter | Source → Target |
|-----------|----------------|
| RTG_Sith_to_HeavySith | SithSoldier → HeavySithTrooper |
| RTG_Sith_to_Republic | SithSoldier → RepublicSoldier |
| RTG_MX_TossGrenade_to_Sith | Toss_Grenade_Skeleton → SithSoldier |
