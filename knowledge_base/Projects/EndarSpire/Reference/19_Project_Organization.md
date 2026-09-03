# 19 — UE5 Project Organization & Content Browser Standards

> Project: Endar Spire | Plugin: Unreal-MCP-Ghost (419+ tools) | UE 5.6
> Last updated: 2026-05-02
> Sources: Epic Dev Community (Allar UE5 Style Guide), Lyra Starter Game,
>          Medium article by Hyperdense, SLAY Project structure

## Why This Matters

A UE5 project becomes unmanageable past a few hundred assets if folder
structure and naming are inconsistent. Restructuring later generates
cascading redirectors that can break references across the entire project.
The Endar Spire project currently has assets scattered across multiple
root-level folders with mixed naming conventions. This document establishes
the standard that ALL new assets must follow, and provides a plan to
incrementally clean up existing assets.

## Core Principles

1. ORGANIZE BY FEATURE, NOT BY TYPE.
   Group assets by game domain (Characters/, Weapons/, AI/) not by
   asset type (Meshes/, Textures/, Materials/). Asset type is already
   conveyed by the naming prefix (SM_, SK_, M_, T_, BP_, etc.) and
   Content Browser filters.

2. USE A TOP-LEVEL PROJECT NAMESPACE.
   All project assets live under /Game/EndarSpire/. Nothing should be
   created at /Game/ root except engine/plugin defaults.

3. NAMING CONVENTION: Prefix_BaseName_Variant_Suffix.
   Follow the standard UE5 naming prefixes consistently. Every asset
   the MCP agent creates MUST use the correct prefix.

4. NEVER MOVE ASSETS VIA FILE EXPLORER.
   Always move/rename inside the Content Browser (or via exec_python
   using EditorAssetLibrary). Moving via Windows Explorer creates NO
   redirector and immediately breaks ALL references.

5. FIX REDIRECTORS IMMEDIATELY.
   After moving assets, right-click the source folder → "Update
   Redirector References" (UE 5.4+ name, formerly "Fix Up Redirectors
   in Folder"). Do this before any other work.

6. KEEP FOLDER DEPTH <= 4 LEVELS for solo/small team projects.

## Asset Naming Prefixes (Mandatory)

| Asset Type              | Prefix  | Example                          |
|------------------------|---------|----------------------------------|
| Blueprint              | BP_     | BP_SithTrooper                   |
| Widget Blueprint       | WBP_    | WBP_ObjectiveHUD                 |
| Static Mesh            | SM_     | SM_Carbine                       |
| Skeletal Mesh          | SK_     | SK_SithWarrior                   |
| Material               | M_      | M_LightsaberRed                  |
| Material Instance      | MI_     | MI_LightsaberGreen               |
| Texture                | T_      | T_SithWarrior_D                  |
| Niagara System         | NS_     | NS_ForcePushWave                 |
| Animation Blueprint    | ABP_    | ABP_DarkJediBoss                 |
| Animation Sequence     | AN_     | AN_SithRifleIdle (or A_ legacy)  |
| Animation Montage      | AM_     | AM_LightsaberSlash1              |
| Blend Space            | BS_     | BS_SithWarrior_1D_Locomotion     |
| Sound Wave             | S_      | S_BlasterFire                    |
| Sound Cue              | SC_     | SC_SaberHum                      |
| Particle System        | PS_     | PS_Explosion                     |
| Physics Asset          | PHYS_   | PHYS_SithWarrior                 |
| Input Action           | IA_     | IA_Melee                         |
| Input Mapping Context  | IMC_    | IMC_Default_Destiny              |
| Data Table             | DT_     | DT_WeaponStats                   |
| Behavior Tree          | BT_     | BT_SithPatrol                    |
| Blackboard             | BB_     | BB_SithCombat                    |
| IK Rig                 | IKRig_  | IKRig_SithWarrior                |
| IK Retargeter          | RTG_    | RTG_Sith_to_SithWarrior          |
| Level Sequence         | LS_     | LS_EndarSpire_Intro              |
| Level                  | L_      | L_EndarSpire_Sandbox             |
| Enum                   | E_      | E_WeaponType                     |
| Struct                 | ST_     | ST_WeaponData                    |
| Interface              | BPI_    | BPI_Interactable                 |
| Game Mode              | GM_     | GM_EndarSpire                    |

### Texture Suffixes

| Channel            | Suffix | Example              |
|--------------------|--------|----------------------|
| Base Color/Diffuse | _D     | T_SithWarrior_D      |
| Normal             | _N     | T_SithWarrior_N      |
| Roughness          | _R     | T_SithWarrior_R      |
| Metallic           | _MT    | T_SithWarrior_MT     |
| Emissive           | _E     | T_SithWarrior_E      |
| Ambient Occlusion  | _AO    | T_SithWarrior_AO     |
| ORM packed         | _ORM   | T_SithWarrior_ORM    |
| Alpha/Opacity      | _A     | T_SithWarrior_A      |

### Retarget Output Prefixes

| Target Skeleton    | Prefix      | Example                    |
|-------------------|-------------|----------------------------|
| SithWarrior       | RT_SW_      | RT_SW_LightsaberSlash1     |
| SithSoldier       | RT_Sith_    | RT_Sith_RunForward         |
| HeavySithTrooper  | RT_Heavy_   | RT_Heavy_FireRifle         |
| RepublicSoldier   | RT_Republic_| RT_Republic_RifleIdle      |
| FP Arms (Player)  | FP_         | FP_LS_Slash1, FP_Pistol_Idle |

## Target Folder Structure

This is the IDEAL structure for /Game/EndarSpire/. New assets MUST be
created in the correct location. Existing assets should be migrated
incrementally (see Migration Plan below).

```
/Game/EndarSpire/
├── AI/
│   ├── Sith/
│   │   └── BP_SithSoldierController
│   ├── SithV2/
│   │   ├── BP_SithTrooper, ABP_SithTrooperElite, BPW_SithTrooperHP
│   │   ├── BP_SithHeavyTrooper, ABP_SithHeavyTrooper, BPW_SithHeavyTrooperHP
│   │   └── BP_DarkJediBoss, ABP_DarkJediBoss, BPW_DarkJediBossHP
│   └── RepublicV1/
│       └── Blueprints/
│           ├── BP_RepublicSoldier, ABP_RepublicSoldier, BPW_RepublicSoldierHP
│           └── (future Republic variants)
│
├── Characters/
│   ├── Player/
│   │   └── Animations/
│   │       ├── Lightsaber/    (FP_LS_* retargeted FP arm anims)
│   │       ├── Pistol/        (FP_Pistol_* retargeted FP arm anims)
│   │       ├── ForcePowers/   (FP_Force_* retargeted FP arm anims)
│   │       └── Rifle/         (FP_Rifle_* if needed)
│   ├── RiggedModels/
│   │   ├── SithSoldier/       (SK, skeleton, physics, textures)
│   │   ├── SithWarrior/       (SK, skeleton, physics, textures)
│   │   ├── HeavySithTrooper/  (SK, skeleton, physics, textures)
│   │   └── RepublicSoldier/   (SK, skeleton, physics, textures)
│   ├── Sith/
│   │   ├── IKRig_SithSoldier
│   │   └── Animations/        (source + retargeted Sith anims, montages)
│   │       └── Locomotion/    (BS_Sith_8Dir, SithRetargeted/)
│   ├── SithWarrior/
│   │   ├── IKRig_SithWarrior
│   │   └── Animations/
│   │       ├── ForcePowers/   (RT_SW_* retargeted force anims)
│   │       ├── Lightsaber/    (RT_SW_* retargeted saber anims)
│   │       ├── Locomotion/    (BS_SithWarrior_1D_Locomotion)
│   │       └── Montages/      (RT_SW_*_Montage combat/force/death)
│   ├── HeavySithTrooper/
│   │   ├── IKRig_HeavySithTrooper
│   │   ├── RTG_Sith_to_HeavySith
│   │   └── Animations/        (RT_Heavy_* anims, locomotion, montages)
│   └── RepublicSoldier/
│       └── Animations/         (RT_Republic_* anims, locomotion, montages)
│
├── IKRetarget/
│   ├── NewAnimations/
│   │   ├── ForcePowers/       (source anims on Withdrawing_Sword_Skeleton)
│   │   ├── Lightsaber/        (source anims on Withdrawing_Sword_Skeleton)
│   │   ├── Pistol/            (source anims on Withdrawing_Sword_Skeleton)
│   │   └── Grenade_Throw_Anim (newly uploaded)
│   └── (source IK rigs: IKRig_Src_MX_GreatSword, etc.)
│
├── WeaponModels/
│   ├── Blasters/
│   │   ├── Pistol/            (w_BlstrPstl_0051)
│   │   └── Carbine/           (Carbine)
│   ├── Sabers/                (lshandle06, blade_out, blade, materials)
│   └── (other weapon meshes)
│
├── Sequences/
│   ├── LS_EndarSpire_Intro
│   └── LS_EndarSpire_Ending
│
├── Audio/
│   └── SFX/                   (imported sounds, organized by type)
│
├── UI/
│   ├── WBP_ObjectiveHUD
│   └── (other widget blueprints)
│
├── Effects/
│   └── (Niagara systems, emitters)
│
├── Maps/
│   └── (level files if moved from root)
│
└── Core/
    ├── BP_ObjectiveManager
    ├── BP_Terminal
    └── (game mode, shared systems)
```

## Current Asset Locations (Known From Recon)

These are the actual current paths discovered during project recon.
DO NOT move these without fixing redirectors. This list helps the MCP
agent know where things ARE versus where they SHOULD be.

### Player Assets (under /Game/FirstPerson/ — legacy Destiny structure)
  /Game/FirstPerson/Blueprints/BP_TitanCharacter_P1
  /Game/FirstPerson/Blueprints/BP_WarlockCharacter_P2
  /Game/FirstPerson/Blueprints/BP_FirstPersonGameMode
  /Game/FirstPerson/Blueprints/Weapons_P1
  /Game/FirstPerson/Input/IMC_Default_Destiny
  /Game/FirstPerson/Input/IMC_Weapons
  /Game/FirstPerson/Input/IA_* (18 input actions)
  /Game/FirstPersonArms/Character/Mesh/SK_Mannequin_Arms
  /Game/FirstPersonArms/Animations/FirstPerson_AnimBP

  STATUS: DO NOT MOVE. These are deeply wired. Work with them in-place.

### Destiny Content (under /Game/DestinyContent/ — legacy)
  /Game/DestinyContent/Blueprints/Enem_Projectile/BP_EnemyProjectile
  /Game/DestinyContent/Blueprints/Enem_Projectile/BP_EnemyProjectile_Slugger
  /Game/DestinyContent/Blueprints/BP_Grenade
  /Game/DestinyContent/Blueprints/Enemies/EnemiesV2/BP_Infantry
  /Game/DestinyContent/Blueprints/Enemies/EnemiesV2/BP_Slugger
  /Game/DestinyContent/Blueprints/Enemies/EnemiesV2/BP_Phalanx
  /Game/DestinyContent/Weapon/HungJury/HungJuryV2
  /Game/DestinyContent/Weapon/Deliverance/Deli_StaticMesh
  /Game/DestinyContent/Weapon/Cataclysmic/Cata_SM

  STATUS: DO NOT MOVE. Legacy enemies and weapons deeply referenced.

### Endar Spire Content (under /Game/EndarSpire/ — our project namespace)
  STATUS: This is our project root. All new assets go here.
  Current structure is mostly correct but needs some cleanup.

### Cleanup / Review Assets
  /Game/_ProjectCleanup/Review/RetargetSourceDump/
  STATUS: Contains source skeleton for retarget anims. Leave in place.

## Rules for MCP Agent Asset Creation

1. ALL new Blueprint assets: place under /Game/EndarSpire/ in the
   appropriate feature folder.

2. ALL new animation assets: place under the character's Animations/
   subfolder with the correct retarget prefix.

3. ALL new montages: place in a Montages/ subfolder within the
   character's Animations/ folder.

4. ALL new weapon meshes: place under /Game/EndarSpire/WeaponModels/
   in the appropriate subfolder.

5. ALL new UI widgets: place under /Game/EndarSpire/UI/.

6. ALL new VFX: place under /Game/EndarSpire/Effects/.

7. ALL new sounds: place under /Game/EndarSpire/Audio/SFX/.

8. ALL new sequences: place under /Game/EndarSpire/Sequences/.

9. NEVER create assets at /Game/ root.

10. NEVER create type-based folders (Meshes/, Textures/, Materials/).
    Use the naming prefix instead.

11. Use exec_python with AssetTools.create_asset() when the MCP tool
    create_blueprint hardcodes /Game/Blueprints/. Always specify the
    correct /Game/EndarSpire/... path.

## Migration Plan (Incremental, Low-Risk)

DO NOT attempt a bulk reorganization. Move assets in small batches,
fix redirectors after each batch, and test before proceeding.

### Phase 1 — No-Move Items (leave in place permanently)
  - /Game/FirstPerson/*        (player BPs, input, FP arms)
  - /Game/FirstPersonArms/*    (FP skeleton, AnimBP)
  - /Game/DestinyContent/*     (legacy enemies, projectiles, weapons)
  - /Game/Characters/*         (Mannequin assets)
  - /Game/_ProjectCleanup/*    (source skeletons)

### Phase 2 — New Assets Only (enforce going forward)
  All new assets created from this point forward MUST follow the
  target structure. No exceptions.

### Phase 3 — Optional Cleanup (only if user requests)
  Move misplaced EndarSpire assets to correct subfolders.
  Fix redirectors after each batch.
  Test compile all affected Blueprints.

## Content Browser Tips

- CTRL+SPACE opens/closes the Content Drawer
- Dock it to layout by clicking the dock button (top-right of drawer)
- Use spacebar to preview a selected asset without opening it
- Right-click folder → "Update Redirector References" after any move
- Windows → Content Browser 2/3/4 for multiple browser panels
- Right-click folder → "Add to Favorites" for quick access
- Use Content Browser filters (top bar) to filter by asset type
  rather than creating type-based folders
- ESCAPE cancels a drag-move operation

## Newly Uploaded Animation Assets

The following were recently uploaded and need to be included in
future retarget batches:

  /Game/EndarSpire/IKRetarget/NewAnimations/Pistol/shooting_Anim
  /Game/EndarSpire/IKRetarget/NewAnimations/Grenade_Throw_Anim

These are on the same source skeleton (Withdrawing_Sword_Skeleton)
as the other NewAnimations assets.
