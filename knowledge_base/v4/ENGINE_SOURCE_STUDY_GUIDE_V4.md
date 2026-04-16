# Unreal Engine Source Study Guide V4

> **Date**: 2026-04-16 | **Purpose**: Guide developer through the most relevant UE source areas for Unreal-MCP-Ghost

---

## Overview

The Unreal Engine source (`UnrealEngine-release.zip`) is massive. This guide identifies the **8 most important subsystems** to study, in priority order, with specific folders, key files, and what to look for.

**Study method**: Read `.h` files first for API surface, then `.cpp` for behavior. Focus on understanding the *contracts* (what inputs, what guarantees, what side effects) rather than memorizing implementation.

---

## Priority 1: KismetCompiler — Blueprint Compilation

### Why It Matters
Every Blueprint edit Ghost makes must compile cleanly. Understanding the compilation pipeline lets Ghost diagnose errors, predict failure modes, and validate graph edits before committing.

### Where to Look
```
Engine/Source/Editor/KismetCompiler/
├── Public/
│   └── KismetCompiler.h              ← FKismetCompilerContext (the main class)
├── Private/
│   └── KismetCompiler.cpp            ← Compilation implementation
```

### Key Concepts
| Concept | What It Does | Why Ghost Cares |
|---|---|---|
| `CreateFunctionList()` | Builds list of functions to compile | Ghost needs to know what functions exist |
| `MergeUbergraphPagesIn()` | Merges event graph pages into ubergraph | Editing event graphs affects this merge |
| `ExpandTunnelsAndMacros()` | Expands macros/tunnels into actual nodes | Ghost-created macros must expand cleanly |
| `ValidateGeneratedClass()` | Final validation of compiled class | Ghost should call this or its equivalent |
| `CheckConnectionResponse()` | Validates pin connections | Ghost must check before connecting pins |
| `CreateAndProcessUbergraph()` | Creates the unified execution graph | Understanding this prevents ubergraph conflicts |

### Study Questions
1. What causes `CompileBlueprint()` to fail vs warn?
2. How does the compiler handle missing pin connections?
3. What validation runs before vs after compilation?
4. How are wildcard pins resolved?

### Doc Reference
- https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Editor/KismetCompiler/FKismetCompilerContext
- https://ikrima.dev/ue4guide/engine-programming/blueprints/bp-compiler-overview/

---

## Priority 2: BlueprintGraph — Node-Level Authoring

### Why It Matters
This is the module that defines what Blueprint nodes *are* and how they're created, connected, and organized. Ghost's graph-editing API maps directly to these primitives.

### Where to Look
```
Engine/Source/Editor/BlueprintGraph/
├── Public/
│   ├── K2Node.h                      ← Base class for all BP nodes
│   ├── K2Node_Event.h                ← Event nodes
│   ├── K2Node_CallFunction.h         ← Function call nodes
│   ├── K2Node_VariableGet.h          ← Variable getter
│   ├── K2Node_VariableSet.h          ← Variable setter
│   ├── K2Node_IfThenElse.h           ← Branch node
│   ├── EdGraphSchema_K2.h            ← Schema (connection rules, context actions)
│   └── BlueprintActionDatabase.h     ← Action registry
├── Private/
│   ├── K2Node.cpp
│   ├── EdGraphSchema_K2.cpp          ← Pin compatibility, connection validation
│   └── BlueprintActionDatabaseRegistrar.cpp
```

### Key Classes
| Class | Purpose | Ghost Mapping |
|---|---|---|
| `UK2Node` | Base class for all BP nodes | `bp_add_node` target class |
| `UK2Node_Event` | Event nodes (BeginPlay, Tick) | Event graph entry points |
| `UK2Node_CallFunction` | Function call nodes | Most common node type |
| `UK2Node_IfThenElse` | Branch node | Control flow |
| `UEdGraphSchema_K2` | Connection rules, context actions | Pin compatibility checks |
| `FEdGraphSchemaAction_K2NewNode` | Action to add a node to graph | Node creation pattern |

### Study Questions
1. How does `EdGraphSchema_K2` determine if two pins are compatible?
2. What is the lifecycle of creating a node? (Allocate → Initialize → Expand → Compile)
3. How are pin names determined and can they be enumerated at runtime?
4. What is the relationship between `FEdGraphSchemaAction` and actual node creation?

### Doc Reference
- https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Editor/BlueprintGraph

---

## Priority 3: Asset Registry — Project Intelligence

### Why It Matters
Ghost needs to discover, search, and trace dependencies across the entire project without loading every asset. The Asset Registry is the engine-native solution.

### Where to Look
```
Engine/Source/Runtime/AssetRegistry/
├── Public/
│   ├── IAssetRegistry.h              ← Main interface
│   ├── AssetRegistryModule.h         ← Module access
│   ├── AssetData.h                   ← FAssetData structure
│   └── ARFilter.h                    ← FARFilter for queries
├── Private/
│   └── AssetRegistry.cpp             ← Implementation
```

### Key APIs
| Function | Purpose | Ghost Tool |
|---|---|---|
| `GetAssetsByClass()` | Find all assets of a type | `project_find_assets` |
| `GetAssetsByPath()` | Find assets in a directory | `project_find_assets` |
| `GetAssetsByTagValues()` | Search by metadata tags | `project_search_by_tag` |
| `GetAssets()` with `FARFilter` | Multi-criteria search | `project_find_assets` |
| `OnAssetAdded()` delegate | React to new assets | Watch for import results |
| `OnAssetRenamed()` delegate | React to renames | Track asset moves |
| `IsLoadingAssets()` | Check if scan is complete | Wait before querying |

### Key Data: FAssetData
| Field | Value |
|---|---|
| `ObjectPath` | `Package.GroupNames.AssetName` |
| `PackageName` | Package name |
| `PackagePath` | Directory path |
| `AssetName` | Asset name |
| `AssetClass` | Class name |
| `TagsAndValues` | Searchable metadata map |

### Doc Reference
- https://dev.epicgames.com/documentation/en-us/unreal-engine/asset-registry-in-unreal-engine

---

## Priority 4: Interchange Framework — Asset Import Pipeline

### Why It Matters
Ghost already has import tools, but Interchange is Epic's official framework for extensible, async, format-agnostic import. Adopting it future-proofs the import pipeline.

### Where to Look
```
Engine/Plugins/Interchange/
├── Runtime/
│   ├── Source/Import/                ← Import pipeline
│   └── Source/Pipelines/             ← Customizable pipeline stages
Engine/Source/Editor/UnrealEd/Private/Interchange/
```

### Key Concepts
| Concept | Description |
|---|---|
| Pipeline Stack | Ordered set of customizable stages |
| Translator | Format-specific parser (FBX, glTF, etc.) |
| Factory Node | Intermediate representation before UE asset creation |
| Pipeline | C++/Blueprint/Python customizable import logic |

### Doc Reference
- https://dev.epicgames.com/documentation/unreal-engine/importing-assets-using-interchange-in-unreal-engine
- https://dev.epicgames.com/community/learning/tutorials/raKx/unreal-engine-import-customization-with-interchange

---

## Priority 5: Automation Test Framework

### Where to Look
```
Engine/Source/Runtime/Core/Public/Misc/AutomationTest.h    ← FAutomationTestBase
Engine/Source/Developer/AutomationDriver/                   ← Input simulation
Engine/Source/Developer/FunctionalTesting/                  ← Level-based tests
Engine/Source/Developer/ScreenShotComparison/               ← Visual regression
```

### Key Test Types
| Type | Speed | Use For |
|---|---|---|
| Smoke | < 1 second | Quick validation after Ghost edits |
| Feature | Moderate | System-level verification |
| Content Stress | Slow | Load-all-maps, compile-all-BPs validation |
| Screenshot Comparison | Moderate | Visual regression after material changes |

### Design Guidelines (from Epic)
1. Don't assume state — tests can run out of order
2. Leave disk as found — clean up generated files
3. Assume bad previous state — generate and delete before test starts

### Doc Reference
- https://dev.epicgames.com/documentation/unreal-engine/automation-test-framework-in-unreal-engine

---

## Priority 6: Python Editor Scripting (Safety Contract)

### Where to Look
```
Engine/Plugins/Experimental/PythonScriptPlugin/
├── Source/
│   ├── PythonScriptPlugin/           ← Core Python integration
│   └── PythonScriptPluginPreload/    ← Pre-initialization
Engine/Source/Editor/UnrealEd/Private/EditorPythonScripting/
```

### The Safety Contract
| Rule | Correct | Wrong |
|---|---|---|
| Asset operations | `unreal.EditorAssetLibrary` | `os.rename`, `shutil.move` |
| Property access | `set_editor_property()` | Direct attribute assignment |
| Undo support | `ScopedEditorTransaction` | Raw mutations |
| Progress UI | `ScopedSlowTask` | Silent long-running ops |
| Logging | `unreal.log()` family | `print()` |

### Doc Reference
- https://dev.epicgames.com/documentation/en-us/unreal-engine/scripting-the-unreal-editor-using-python

---

## Priority 7: IK Rig — Animation Retargeting

### Where to Look
```
Engine/Plugins/Animation/IKRig/
├── Source/
│   ├── IKRig/                        ← Core IK Rig
│   └── IKRigEditor/                  ← Editor UI and controllers
```

### Key Python APIs
| API | Purpose |
|---|---|
| `IKRigController.get_controller(rig)` | Get controller for modifications |
| `set_retarget_root(bone)` | Set pelvis/root bone |
| `add_retarget_chain(name, start, end, goal)` | Define limb chain |
| `apply_auto_generated_retarget_definition()` | Auto-create chains for bipeds |
| `apply_auto_fbik()` | Auto-create Full Body IK solver |
| `is_skeletal_mesh_compatible(mesh)` | Check if rig fits a skeleton |

### Doc Reference
- https://dev.epicgames.com/documentation/unreal-engine/using-python-to-create-and-edit-ik-rigs-in-unreal-engine

---

## Priority 8: Source Control Integration

### Where to Look
```
Engine/Source/Editor/UnrealEd/Private/SourceControlHelpers.cpp
Engine/Source/Developer/SourceControl/
├── Public/
│   ├── ISourceControlProvider.h      ← Provider interface
│   ├── SourceControlOperations.h     ← CheckOut, CheckIn, etc.
│   └── ISourceControlModule.h        ← Module access
```

### Key Operations
| Operation | Description |
|---|---|
| `CheckOut` | Lock asset for editing |
| `CheckIn` | Submit changes with description |
| `Revert` | Discard local changes |
| `GetState` | Query checkout/modified/added state |
| `Diff` | Compare against depot version |

### Doc Reference
- https://dev.epicgames.com/documentation/unreal-engine/source-control-in-unreal-engine
