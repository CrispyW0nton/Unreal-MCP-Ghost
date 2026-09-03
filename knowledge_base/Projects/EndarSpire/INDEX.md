# ENDAR SPIRE — Project Knowledge Base Index

> Project: Endar Spire | Plugin: Unreal-MCP-Ghost (419 tools) | UE 5.6
> Last updated: 2026-05-03

## Purpose
Project-specific knowledge for the Endar Spire game built with the Unreal-MCP-Ghost plugin. Generic UE5 knowledge lives in the parent knowledge_base/ directory. This folder contains Endar Spire asset paths, proven MCP workflows, Blueprint framework logs, and implementation guides.

## Directory Structure

Projects/EndarSpire/
├── INDEX.md ← You are here
├── Blueprints/
│   ├── BP_SithTrooper_FrameworkLog.md
│   ├── BP_SithHeavyTrooper_FrameworkLog.md
│   ├── BP_RepublicSoldier_FrameworkLog.md
│   ├── BP_DarkJediBoss_FrameworkLog.md
│   ├── BP_DarkJediBoss_NativeDirectorSpec.md
│   └── ObjectiveSystem_FrameworkLog.md
├── Camera/
│   ├── 01_TrueFirstPerson_Camera.md
│   └── 02_FP_Arms_Extraction.md
├── Animation/
│   ├── 03_Animation_Retargeting.md
│   ├── 04_Sequencer_Animation.md
│   └── 11_Rigging_Skinning.md
├── Weapons/
│   ├── 05_Weapon_Rigging.md
│   └── 06_Weapon_Swap.md
├── Combat/
│   ├── 07_Melee_Combat.md
│   ├── 08_Force_Powers_Player.md
│   └── 09_Boss_AI_Patterns.md
├── Audio/
│   └── 10_Voice_Taunts.md
└── Reference/
    ├── 12_MCP_Tool_Reference.md
    └── 19_Project_Organization.md

## Quick Lookup

| I need to... | Read |
|-------------|------|
| Set up first-person camera | Camera/01_TrueFirstPerson_Camera.md |
| Hide player head in FP | Camera/02_FP_Arms_Extraction.md |
| Retarget animations between skeletons | Animation/03_Animation_Retargeting.md |
| Play cutscenes or montages | Animation/04_Sequencer_Animation.md |
| Attach a weapon to a socket | Weapons/05_Weapon_Rigging.md |
| Build weapon swap system | Weapons/06_Weapon_Swap.md |
| Implement melee attacks | Combat/07_Melee_Combat.md |
| Add force powers with cooldowns | Combat/08_Force_Powers_Player.md |
| Design boss AI phases | Combat/09_Boss_AI_Patterns.md |
| Import and play voice/SFX | Audio/10_Voice_Taunts.md |
| Understand skeletons and sockets | Animation/11_Rigging_Skinning.md |
| Quick MCP tool reference + asset paths | Reference/12_MCP_Tool_Reference.md |
| Organize project folders & name assets | Reference/19_Project_Organization.md |
| Understand BP_SithTrooper current state | Blueprints/BP_SithTrooper_FrameworkLog.md |
| Understand BP_SithHeavyTrooper state | Blueprints/BP_SithHeavyTrooper_FrameworkLog.md |
| Understand BP_RepublicSoldier state | Blueprints/BP_RepublicSoldier_FrameworkLog.md |
| Understand BP_DarkJediBoss + native director handoff | Blueprints/BP_DarkJediBoss_FrameworkLog.md |
| Implement Dark Jedi boss native AI (C++) | Blueprints/BP_DarkJediBoss_NativeDirectorSpec.md |
| Understand Phase E objective system scaffold | Blueprints/ObjectiveSystem_FrameworkLog.md |

## Dark Jedi Boss (Phase D)

- [BP_DarkJediBoss Framework Log](Blueprints/BP_DarkJediBoss_FrameworkLog.md)
- [BP_DarkJediBoss Native Director Spec](Blueprints/BP_DarkJediBoss_NativeDirectorSpec.md)

## Objective System (Phase E)

- [Objective System Framework Log](Blueprints/ObjectiveSystem_FrameworkLog.md)

## Critical Rules
1. Timer Bug UE-61800: Timer callbacks must have ZERO parameters
2. Separate TimerHandle variables per cooldown
3. MCP SavePackage crashes with MassEntityEditor — always Ctrl+S manually
4. Always `compile_blueprint` after Blueprint edits
5. Always call `get_blueprint_nodes` before connecting pins
6. Multiply per-frame values by DeltaSeconds
7. Call SpawnDefaultController after runtime spawns
8. Handle cast failures gracefully
9. Follow naming prefixes: BP_, SM_, SK_, M_, T_, ABP_, AM_, BS_, etc.
10. All new assets under /Game/EndarSpire/ in the correct feature folder
11. Never move assets via file explorer — always use Content Browser or exec_python
12. Fix redirectors immediately after any asset move

## Current Scope Corrections
- Player-facing work targets `/Game/FirstPerson/Blueprints/BP_TitanCharacter_P1` unless the user explicitly changes the active class.
- Existing input actions should be reused: `IA_Interact`, `IA_Melee`, `IA_Swap`, `IA_SwapHold`, `IA_Super`, and `IA_Super2`.
- Existing mapping contexts are `/Game/FirstPerson/Input/IMC_Default_Destiny` and `/Game/FirstPerson/Input/IMC_Weapons`; do not create duplicate `IMC_Default`.
- The Sith melee trooper variant is removed from the current development scope.
- The combat droid is removed from the current development scope.
- Focus upcoming enemy work on the Sith Warrior/Dark Jedi boss after confirming SithWarrior mesh and skeleton assets.
