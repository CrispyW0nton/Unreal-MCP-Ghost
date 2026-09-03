# 12 — MCP Tool Quick Reference (Endar Spire)

> Project: Endar Spire | Plugin: Unreal-MCP-Ghost (419 tools) | UE 5.6

## Connection
- Plugin: C++ bridge on localhost:55655
- Transport: stdio / SSE / streamable-HTTP
- Verify: `get_actors_in_level` should return actor list

## Most-Used Tools for This Project

### Blueprint Creation & Editing
| Tool | Purpose |
|------|---------|
| create_blueprint | Create a new Blueprint class |
| compile_blueprint | Compile a Blueprint |
| add_component | Add component to Blueprint |
| set_component_property | Set property on a component |
| add_blueprint_variable | Add a variable with type and default |
| get_blueprint_variables | List existing variables |
| get_blueprint_functions | List existing functions |
| get_blueprint_nodes | Get all nodes in a graph |
| create_node | Add a node to a graph |
| connect_pins | Connect two node pins |
| bp_get_graph_summary | Get graph structure overview |
| bp_add_node | Add node (V4 atomic op) |
| bp_connect_pins | Connect pins (V4 atomic op) |
| bp_compile | Compile (V4 atomic op) |
| bp_remove_node | Remove a node |
| bp_disconnect_pin | Break a pin connection |

### Actor & Level
| Tool | Purpose |
|------|---------|
| get_actors_in_level | List all actors |
| spawn_actor | Spawn actor in level |
| set_actor_transform | Move/rotate/scale actor |
| get_actor_properties | Read actor properties |
| delete_actor | Remove actor from level |

### Animation
| Tool | Purpose |
|------|---------|
| create_ik_rig | Create IK Rig with chains |
| create_ik_retargeter | Create retargeter between two IK rigs |
| set_retarget_chain_mapping | Map source to target chains |
| create_animation_blueprint | Create AnimBP on skeleton |
| play_montage | Play animation montage at runtime |

### Assets & Import
| Tool | Purpose |
|------|---------|
| exec_python | Run arbitrary UE Python (escape hatch) |
| import_sound_asset | Import audio files |
| duplicate_asset | Duplicate an existing asset |
| create_folder | Create content browser folder |
| list_assets | List assets in a folder |

### Diagnostics (V6)
| Tool | Purpose |
|------|---------|
| bp_run_post_mutation_verify | Verify Blueprint after edits |
| bp_get_graph_summary | Structural overview of graph |
| get_blueprint_variables | Audit variable state |

## Timer Bug UE-61800
Set Timer by Function Name requires the target function to have ZERO parameters. If it has parameters, the timer silently fails. Use separate TimerHandle variables for each cooldown.

## MCP Save Limitation
`SavePackage` can crash with `MassEntityEditor` in this project. Always manually save in Unreal (Ctrl+S) after MCP edits.

## Key Asset Paths
| Asset | Path |
|-------|------|
| Player BP target | /Game/FirstPerson/Blueprints/BP_TitanCharacter_P1 |
| Alternate player BP | /Game/FirstPerson/Blueprints/BP_WarlockCharacter_P2 |
| Primary IMC | /Game/FirstPerson/Input/IMC_Default_Destiny |
| Weapon IMC | /Game/FirstPerson/Input/IMC_Weapons |
| Interact input | /Game/FirstPerson/Input/Actions/IA_Interact |
| Melee input | /Game/FirstPerson/Input/Actions/IA_Melee |
| Swap input | /Game/FirstPerson/Input/Actions/IA_Swap |
| Force input candidates | /Game/FirstPerson/Input/Actions/IA_Super, /Game/FirstPerson/Input/Actions/IA_Super2 |
| Sith Trooper | /Game/EndarSpire/AI/SithV2/BP_SithTrooper |
| Sith Heavy | /Game/EndarSpire/AI/SithV2/BP_SithHeavyTrooper |
| Republic Soldier | /Game/EndarSpire/AI/RepublicV1/Blueprints/BP_RepublicSoldier |
| AI Controller | /Game/EndarSpire/AI/Sith/BP_SithSoldierController |
| Enemy Projectile | /Game/DestinyContent/Blueprints/Enem_Projectile/BP_EnemyProjectile |
| Slugger Projectile | /Game/DestinyContent/Blueprints/Enem_Projectile/BP_EnemyProjectile_Slugger |
| SithWarrior Mesh | /Game/EndarSpire/Characters/RiggedModels/SithWarrior/ |
| Sith Soldier Mesh | /Game/EndarSpire/Characters/RiggedModels/SithSoldier/SithSoldier |
| Heavy Mesh | /Game/EndarSpire/Characters/RiggedModels/HeavySithTrooper/HeavySithTrooper1 |
| Republic Mesh | /Game/EndarSpire/Characters/RiggedModels/RepublicSoldier/RepublicSoldier |
| Carbine | /Game/EndarSpire/WeaponModels/Carbine |
| Grenade BP | /Game/DestinyContent/Blueprints/BP_Grenade |
| Sith Animations | /Game/EndarSpire/Characters/Sith/Animations/ |
| Heavy Animations | /Game/EndarSpire/Characters/HeavySithTrooper/Animations/ |
| Republic Animations | /Game/EndarSpire/Characters/RepublicSoldier/Animations/ |
| Sith IK Rig | /Game/EndarSpire/Characters/Sith/IKRig_SithSoldier |
| Heavy IK Rig | /Game/EndarSpire/Characters/HeavySithTrooper/IKRig_HeavySithTrooper |
