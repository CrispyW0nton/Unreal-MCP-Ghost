# UnrealMCP — Limitations Log & Development Roadmap

This document is a living record of every limitation, gap, or friction point
encountered while using this plugin to automate Unreal Engine 5 Blueprint work
via AI. Each entry explains what was attempted, what failed or was awkward, and
what the ideal fix looks like. The roadmap at the bottom is derived directly
from this log.

---

## How to Read This File

| Field | Meaning |
|-------|---------|
| **Status** | `Open` – not yet fixed · `Fixed` – resolved in a commit · `Partial` – workaround exists but root cause remains |
| **Severity** | `Critical` blocks real work · `High` causes incorrect results · `Medium` adds friction · `Low` cosmetic/nice-to-have |
| **Commit** | The commit SHA where a fix or workaround landed (if any) |

---

## Limitation Log

---

### L-001 — Non-ASCII characters corrupting C++ source files
**Status:** Fixed · **Severity:** Critical · **Commit:** `6a17554`, `aad26e6`

**What happened:**  
UTF-8 em-dashes (`—`, bytes `0xE2 0x80 0x94`) and other multi-byte characters
were present in C++ comments inside `UnrealMCPBlueprintNodeCommands.cpp` and
`UnrealMCPCommonUtils.cpp`. MSVC on Windows treats source files as single-byte
by default, so the multi-byte sequences broke the tokeniser. This produced a
cascade of misleading errors: unexpected `<<`/`>>` tokens, missing `;`,
`identifier not found: Z_Construct_UClass_USimpleConstructionScript_NoRegister`,
`ResolveGraph is not a member`, illegal local function definitions, and
redefinition of `K2Schema`.

**Root cause:**  
The original plugin source was authored on macOS/Linux with smart quotes or
em-dashes in comments. MSVC does not handle UTF-8 source without an explicit
`/utf-8` compile flag.

**Fix applied:**  
Python script scanned all `.cpp`/`.h`/`.cs` files for non-ASCII bytes and
replaced them with plain ASCII equivalents (`--`, `-`).

**Ideal long-term fix:**  
Add `/utf-8` to `UnrealMCP.Build.cs` additional compiler arguments, or add a
pre-commit hook that rejects non-ASCII in source files.

---

### L-002 — UE 5.6 removed `EMessageSeverity::CriticalError`
**Status:** Fixed · **Severity:** Critical · **Commit:** `6a17554`

**What happened:**  
`HandleCompileBlueprint` in `UnrealMCPBlueprintCommands.cpp` checked for
`EMessageSeverity::CriticalError` when scanning compiler log messages. This
enum value was removed in UE 5.6, causing a compile error.

**Fix applied:**  
Removed all references to `::CriticalError`; severity checks now only cover
`::Error` and `::Warning`.

**Ideal long-term fix:**  
Add a UE version guard macro (`#if ENGINE_MAJOR_VERSION >= 5 && ENGINE_MINOR_VERSION >= 6`) 
so the code degrades gracefully across engine versions rather than failing hard.

---

### L-003 — `FCompilerResultsLog::bAnnotateMentionedNodes` removed in UE 5.6
**Status:** Fixed · **Severity:** High · **Commit:** `6a17554`

**What happened:**  
The compile handler set `ResultsLog.bAnnotateMentionedNodes = false`. This
member was removed in UE 5.6.

**Fix applied:**  
Line removed. The default behaviour (nodes not annotated) is acceptable.

---

### L-004 — No `add_blueprint_branch_node` command
**Status:** Fixed · **Severity:** High · **Commit:** `84bde4b`

**What happened:**  
When building BP_AggroBot1's hunt-mode logic, we needed a Branch (IfThenElse)
node. The only way to create one was through `add_blueprint_function_node` with
various target class guesses — all of which failed because `K2Node_IfThenElse`
is not a `UFunction`; it is a specialised graph node.

**Fix applied:**  
Added `HandleAddBlueprintBranchNode` in C++ and wired it as
`add_blueprint_branch_node`. It directly calls `NewObject<UK2Node_IfThenElse>`.

**Ideal long-term fix:**  
Audit all commonly-needed structural nodes (ForLoop, ForEachLoop, Sequence,
DoOnce, Gate, FlipFlop, Select, Switch on Int/Enum) and add dedicated handlers
for each, or add a generic `add_blueprint_pure_node` that accepts a K2Node
class name.

---

### L-005 — No `add_blueprint_cast_node` command
**Status:** Fixed · **Severity:** High · **Commit:** `84bde4b`

**What happened:**  
Cast nodes (`K2Node_DynamicCast`) cannot be created via `add_blueprint_function_node`
because they are not UFunction calls. There was no way to insert a cast without
a dedicated handler.

**Fix applied:**  
Added `HandleAddBlueprintCastNode` and the `add_blueprint_cast_node` command.
Accepts a short class name or full path and resolves via `FindObject<UClass>`.

---

### L-006 — `set_blueprint_property` does not support `FClassProperty` types
**Status:** Fixed (partial) · **Severity:** High · **Commit:** `cf5beb2`

**What happened:**  
Attempting to set `AIControllerClass` (a `TSubclassOf<AAIController>` property)
via `set_blueprint_property` returned:
`"Unsupported property type: ClassProperty for property AIControllerClass"`.
`SetObjectProperty` in `UnrealMCPCommonUtils.cpp` had no branch for
`FClassProperty` or `FSoftClassProperty`.

**Fix applied (partial):**  
Added `FClassProperty` and `FSoftClassProperty` branches to `SetObjectProperty`
that resolve the class by short name via `TObjectIterator<UClass>`.
Also added a dedicated `set_blueprint_ai_controller` command that sets
`APawn::AIControllerClass` directly on the CDO for reliability.

**Remaining gap:**  
`FObjectProperty`, `FWeakObjectProperty`, `FNameProperty`, `FTextProperty`,
`FStructProperty` (e.g. `FVector`, `FColor`), and array/map/set properties are
all still unsupported in `SetObjectProperty`. Any Blueprint default that uses
these types will return "Unsupported property type".

**Ideal long-term fix:**  
Implement full property serialisation using UE's built-in
`FJsonObjectConverter::JsonObjectToUStruct` / `UStruct::ImportText` pipeline
so all property types are handled uniformly.

---

### L-007 — `MoveToActor` called every Tick breaks AI pathfinding
**Status:** Fixed (design fix) · **Severity:** Critical · **Commit:** (Blueprint-only, no plugin change)

**What happened:**  
The initial hunt-mode logic placed `MoveToActor` in the `EventTick` flow.
`MoveToActor` issues a new pathfinding request every call — calling it 60×/sec
cancels and restarts the path every frame, so the bot never travels anywhere.
The bot appeared frozen despite the logic being structurally correct.

**Fix applied:**  
Replaced the entire Tick chain with `SimpleMoveToActor` called once from the
`OnSeePawn` event (which fires continuously while the bot sees the player),
removing the need for Tick-based polling entirely.

**Lesson for AI tooling:**  
The plugin has no way to warn about this anti-pattern. A future
`validate_blueprint_logic` command that checks for latent/movement calls inside
Tick would catch this automatically.

---

### L-008 — `GetController` (non-pure) used as pure data node causes unreliable results
**Status:** Fixed · **Severity:** High · **Commit:** (Blueprint-only, no plugin change)

**What happened:**  
`GetController` was wired only through its data pins (no exec input/output).
Because it is a non-pure UFunction, its evaluation order relative to the exec
chain is not guaranteed in all UE Blueprint versions. The cast downstream
occasionally received a stale or null result.

**Fix applied:**  
Switched to `SimpleMoveToActor` (from `AIBlueprintHelperLibrary`) which
accepts a base `AController*` and requires no cast, eliminating the issue.

**Ideal long-term fix:**  
`get_node_by_id` should report whether a function node is pure or impure. The
AI could then validate that impure nodes are in the exec chain.

---

### L-009 — `add_blueprint_function_node` error messages lack helpful diagnostics
**Status:** Fixed · **Severity:** High · **Commit:** (this commit)

**What happened:**  
When `function_name=MoveToActor` and `function_target=/Script/AIModule.AIController`
was used, the plugin returned:
`"Could not create function node for 'MoveToActor' (target='')"`.
The error message showed `target=''` even though a target was provided,
making it unclear whether the path was wrong, the module wasn't loaded,
or the function name was misspelled.

**Root cause:**  
The C++ handler tries to resolve the `UFunction` via `FindObject`; if it fails
it falls through to a generic error with an already-cleared string. The original
`function_target` parameter is not echoed back.

**Fix applied:**  
Modified `HandleAddBlueprintFunctionCall` to:
- Echo the original `function_target` in the error response.
- When the function name matches but the class is wrong, return a list of up to
  5 candidate matches showing the correct target class path.
- This allows the AI to auto-correct class paths without user intervention.

---

### L-010 — Node IDs returned as zeros immediately after creation
**Status:** Fixed · **Severity:** Medium · **Commit:** (this commit)

**What happened:**  
Several `add_blueprint_*_node` calls returned a node with
`node_id = "00000000000000000000000000000000"`. A subsequent
`find_blueprint_nodes` call was needed to retrieve the real GUID, adding an
extra round-trip.

**Root cause:**  
`CreateNewGuid()` was called **after** `Graph->AddNode()`. In UE5, when a
node is added to the graph before it has a GUID, the GUID remains at zeros
until explicitly assigned.

**Fix applied:**  
Swapped the order in all node creation handlers so `Node->CreateNewGuid()`
is called **before** `Graph->AddNode()`. The GUID now exists from the moment
the node enters the graph, and is immediately available in the response.
Affects 10 node creation functions.

---

### L-011 — `set_node_pin_value` for class-type pins
**Status:** Fixed (partial) · **Severity:** Medium · **Commit:** (this commit)

**What happened:**  
When trying to set the `ActorClass` pin on a `GetActorOfClass` node to
`"ThePlayerCharacter"`, the command returned `{ node_id, pin_name }` but the
`value` field in the response was empty, and the pin did not update in the editor.

**Root cause:**  
`ApplyPinValue` in `UnrealMCPBlueprintNodeCommands.cpp` handles `object`
and `class` pin types differently than scalar types. Class pins require setting
the default object reference, not a string literal.

**Fix applied:**  
Added explicit handling for `PC_Class`, `PC_SoftClass`, `PC_Object`, and
`PC_SoftObject` pin categories. For class pins, the value string is resolved
via `FindFirstObject<UClass>` + `TObjectIterator` fallback, then set via
`Schema->TrySetDefaultObject()` instead of `TrySetDefaultValue()`.

**Remaining:**  
Struct pins (e.g. setting a `FVector` pin to `"(X=1,Y=2,Z=3)"`) still use
text assignment which may not parse correctly for complex nested structs.

---

### L-012 — Missing common structural node types
**Status:** Fixed · **Severity:** High · **Commit:** (this commit)

**What happened:**  
Many common flow-control nodes could not be created via MCP, requiring
manual editor work or workarounds. ForLoop, Sequence, DoOnce, Gate, and
Switch nodes are fundamental to Blueprint logic.

**Fix applied:**  
Added dedicated handlers and Python tools for:
- `add_blueprint_for_loop_node` (UK2Node_MacroInstance wrapping `ForLoop` macro)
- `add_blueprint_for_each_loop_node` (ForEachLoop macro)
- `add_blueprint_sequence_node` (Sequence macro)
- `add_blueprint_do_once_node` (DoOnce macro)
- `add_blueprint_gate_node` (Gate macro with `start_closed` param)
- `add_blueprint_flip_flop_node` (FlipFlop macro)
- `add_blueprint_switch_on_int_node` (K2Node_SwitchInteger)
- `add_blueprint_spawn_actor_node` (K2Node_SpawnActorFromClass)

All macro nodes load from `/Engine/EditorBlueprintResources/StandardMacros`.

**Still missing:**  
- Select node
- Switch on Enum (requires enum asset reference)
- Timeline node (complex state, requires new approach)

---

### L-013 — No way to read or write Blueprint variable default values
**Status:** Fixed · **Severity:** Medium · **Commit:** (this commit)

**What happened:**  
There was no command to read the current default value of a Blueprint variable
(e.g., "what is `PatrolRadius` set to?") or to update it. `set_node_pin_value`
only sets unconnected pin literals, not variable defaults.

**Fix applied:**  
Added two new commands:
- `get_blueprint_variable_defaults(blueprint_name, [variable_name])` —
  Returns all variables (or a single named variable) with their default
  values from `FBPVariableDescription.DefaultValue` and the live CDO value
  exported as text via `ExportTextItem_Direct`. Includes variable type,
  tooltip metadata, and both stored and runtime default values.
- `set_blueprint_variable_default(blueprint_name, variable_name, default_value)` —
  Updates the `FBPVariableDescription.DefaultValue` string and also applies
  the change to the CDO via `ImportText_Direct` so it takes effect
  immediately without a full recompile.

Python tools added to `node_tools.py`.

---

### L-014 — No NavMesh setup command
**Status:** Fixed · **Severity:** Medium · **Commit:** (this commit)

**What happened:**  
AI movement requires a `NavMeshBoundsVolume` in the level. There was no MCP
command to place one or resize it. This had to be done manually every time.

**Fix applied:**  
Added `setup_navmesh([extent], [location], [rebuild=true])` command:
- Checks if a `NavMeshBoundsVolume` already exists via `UGameplayStatics::GetAllActorsOfClass`.
- If found, resizes and repositions the existing volume.
- If not found, spawns a new `ANavMeshBoundsVolume` at the specified location
  and scales the brush to the requested half-extents (defaults to 5000×5000×500cm).
- Optionally calls `UNavigationSystemV1::Build()` to trigger an immediate navmesh rebuild.

Dependencies added:
- `#include "Kismet/GameplayStatics.h"`
- `NavigationSystem` module in `UnrealMCP.Build.cs`

Python tool added to `node_tools.py`.

---

### L-015 — No command to set Blueprint Class Defaults (parent class properties like `AutoPossessAI`)
**Status:** Partial · **Severity:** High · **Commit:** `cf5beb2`

**What happened:**  
`AutoPossessAI` (an `EAutoPossessAI` enum) was settable via `set_blueprint_property`
because `FByteProperty`/`FEnumProperty` were already handled.
`AIControllerClass` (a `TSubclassOf<>`) was not. Needed a dedicated command.

**Fix applied:**  
`set_blueprint_ai_controller` added as a dedicated command.
`FClassProperty` support added to `SetObjectProperty`.

**Remaining:**  
Any `TSubclassOf<>` property other than `AIControllerClass` still needs
individual dedicated commands, or a proper `FClassProperty` + `FSoftClassProperty`
implementation in `SetObjectProperty` (which was partially added in L-006).

---

### L-016 — Plugin requires full C++ rebuild for every new command
**Status:** Open · **Severity:** Medium

**What happened:**  
Every time a missing command was discovered (branch node, cast node, AI
controller setter), the fix required:
1. Editing C++ source.
2. User copying files manually to their UE project.
3. User rebuilding in Visual Studio 2022 (~2–5 min build).
4. User restarting UE or hot-reloading.

This broke the AI-iteration loop significantly — multiple back-and-forth
exchanges were needed just to unblock a single Blueprint operation.

**Ideal fix:**  
- **Short term:** Ship a comprehensive set of structural node commands
  (see L-012) so common operations don't require rebuilds.
- **Medium term:** Add a `call_engine_function` escape hatch that executes
  arbitrary `UFunction` calls by reflection, avoiding the need for new C++
  per function.
- **Long term:** Consider a Lua/Python script engine embedded in the plugin
  so logic can be extended without a C++ rebuild.

---

### L-017 — `compile_blueprint` error messages not surfaced in responses
**Status:** Fixed · **Severity:** Medium · **Commit:** (this commit)

**What happened:**  
When `compile_blueprint` returned `"compiled with 1 error"`, the error
details were inside a `messages` array but wrapped in a generic error response
that discarded the array. The Python CLI could not access per-node error text.

**Fix applied:**  
Modified `HandleCompileBlueprint` to return a full result object even on error:
- Sets `success=false` and includes an `error` summary string.
- **Also includes the full `messages` array** with per-message severity and text.
- For warnings-only compiles, adds a `first_warning` field for quick access.

This allows the AI to read compile errors directly from the response without
needing a second round-trip to inspect nodes.

---

### L-018 — No command to add comment boxes for graph organisation
**Status:** Fixed · **Severity:** Low · **Commit:** (this commit)

**What happened:**  
Nodes were added at raw coordinates with no grouping or comment boxes. The
resulting graph is functional but hard to read in the UE editor. Comment nodes
(`EdGraphNode_Comment`) exist in the graph already (added manually) but could not
be created or positioned via MCP.

**Fix applied:**  
Added `add_blueprint_comment_node(blueprint_name, comment_text, [graph_name],
[node_position], [width], [height], [color])` command:
- Creates an `UEdGraphNode_Comment` with the specified text, position, and dimensions.
- Accepts optional RGBA color as a 4-element array (0..1 range).
- Returns `node_id`, `node_name`, `comment_text`, position, and size.

Python tool added to `node_tools.py`.

---

### L-019 — No command to reposition existing nodes
**Status:** Fixed · **Severity:** Low · **Commit:** (this commit)

**What happened:**  
Nodes added via MCP are positioned at the coordinates provided at creation
time. If the layout needs adjusting after the fact, there was no
`move_blueprint_node` command — the node had to be deleted and recreated.

**Fix applied:**  
Added `move_blueprint_node(blueprint_name, node_id, node_position, [graph_name])`
command:
- Finds the node by GUID or short name via `FindNodeByIdOrName`.
- Sets `Node->NodePosX` and `Node->NodePosY` to the new position.
- Marks the Blueprint as modified.
- Returns `node_id`, `node_name`, `new_pos_x`, `new_pos_y`.

Python tool added to `node_tools.py`.

---

### L-020 — No round-trip read of Blueprint components and level state
**Status:** Fixed (partial) · **Severity:** High · **Commit:** (this commit)

**What happened:**  
There was no reliable way to ask "what components does BP_AggroBot1 have?",
"what Blueprints exist in this level right now?", or "what is the current value of
`IsHunting?` at runtime?". Debugging during playtesting required the user to
manually check the UE editor.

**Fix applied (partial):**  
Added `get_blueprint_components(blueprint_name)` command:
- Lists all components from the Blueprint's `SimpleConstructionScript` (SCS nodes).
- For each SCS component, returns its name, class, source ("SCS"), and any
  properties that differ from the component class CDO defaults (`modified_properties`).
- Also iterates native C++ component properties from the Blueprint's generated
  class and lists those marked "NativeC++".

Python tool added to `node_tools.py`.

**Still missing:**  
- `get_level_actors` — list all actors currently placed in the open level.
- `get_actor_properties` — read CDO and per-instance property overrides.
- Runtime debug: `get_runtime_property` to read live values during PIE.

---

### L-021 — SpawnActorFromClass node crashes on creation
**Status:** Fixed · **Severity:** Critical · **Commit:** `9f9f7b2`

**What happened:**  
When calling `add_blueprint_spawn_actor_node` to create a `UK2Node_SpawnActorFromClass`
node in a Blueprint, Unreal Engine would crash with an assertion failure at
`EdGraphNode.h:586`. The crash occurred after the node was added to the graph and
`PostPlacedNewNode()` was called.

**Root cause:**  
`UK2Node_SpawnActorFromClass` has unique initialization requirements. Unlike most
Blueprint nodes, calling `PostPlacedNewNode()` on this node type triggers internal
logic that expects certain preconditions that aren't met when the node is created
programmatically. The assertion at EdGraphNode.h:586 typically relates to GUID
operations or node graph state validation.

**Initial attempted fix (failed):**  
Removed calls to `AllocateDefaultPins()` and `ReconstructNode()`, letting
`PostPlacedNewNode()` handle everything. This still crashed.

**Fix applied:**  
Changed the initialization sequence to ONLY call `AllocateDefaultPins()` after
adding the node to the graph. Skip `PostPlacedNewNode()` and `ReconstructNode()`
entirely. The Blueprint editor will complete initialization when the graph is
opened or compiled. This minimal initialization prevents the crash while still
creating a functional node.

```cpp
Node->CreateNewGuid();
Graph->AddNode(Node);
Node->AllocateDefaultPins();  // Only this - no PostPlacedNewNode!
```

**Testing note:**  
The node may appear incomplete in the graph until the Blueprint is compiled or
the graph is closed and reopened, but it will function correctly once initialized
by the editor.

---

### L-022 — Cannot add mappings to Input Mapping Context programmatically
**Status:** Fixed · **Severity:** Medium · **Commit:** `[current]`

**What happened:**  
While `create_enhanced_input_action` successfully creates UInputAction assets, there was
no command to add those actions to an existing Input Mapping Context (IMC) or assign
key bindings. After creating an Input Action, developers had to manually open the IMC
asset in the editor and add the mapping.

**Root cause:**  
The `add_input_mapping` command handler was implemented in the C++ backend but:
1. Not declared in the public header file (`UnrealMCPExtendedCommands.h`)
2. Not exposed through the Python tool wrapper

**Fix applied:**  
```cpp
// In UnrealMCPExtendedCommands.h - added declaration:
TSharedPtr<FJsonObject> HandleAddInputMapping(const TSharedPtr<FJsonObject>& Params);
```

```python
# In project_tools.py - added Python wrapper:
@mcp.tool()
def add_input_mapping(imc_name: str, action_name: str, key: str) -> dict:
    """
    Add an input mapping to an existing Input Mapping Context (IMC).
    Args:
        imc_name: Name of the Input Mapping Context (e.g., "IMC_Default")
        action_name: Name of the Input Action (e.g., "IA_Jump")
        key: Key name to bind (e.g., "SpaceBar", "V", "T")
    """
```

**Usage example:**  
```python
# Create the action
create_enhanced_input_action("IA_WormholeTP", "Digital", "/Game/Input")

# Add it to the mapping context
add_input_mapping("IMC_Default", "IA_WormholeTP", "V")
```

**Testing:**  
The command successfully:
- Finds the IMC asset via Asset Registry
- Finds the Input Action asset
- Validates the key name
- Creates an FEnhancedActionKeyMapping
- Adds it to IMC->Mappings array
- Marks the asset as dirty for saving

---

### L-023 — Enhanced Input Action nodes fell back to legacy nodes
**Status:** Fixed · **Severity:** High · **Commit:** `9510f6c`

**What happened:**  
When calling `add_blueprint_enhanced_input_action_node`, the plugin would fail to find
the `UK2Node_EnhancedInputAction` class at runtime and fall back to creating a legacy
`K2Node_InputAction` node instead. This resulted in nodes that didn't support the full
Enhanced Input system features (triggers, modifiers, action values).

**Root cause:**  
Two issues:
1. **Missing module dependency**: The `InputBlueprintNodes` module was not included in
   `UnrealMCP.Build.cs`, so the K2Node_EnhancedInputAction class wasn't available.
2. **Missing include**: The header `K2Node_EnhancedInputAction.h` was not included in
   the source file.
3. **Dynamic class finding**: Code used runtime class lookup (`FindObject<UClass>`)
   instead of direct instantiation, which failed silently.

**Fix applied:**  
1. Added `InputBlueprintNodes` to PrivateDependencyModuleNames in Build.cs
2. Added `#include "K2Node_EnhancedInputAction.h"` to the source file
3. Replaced dynamic class finding with direct `NewObject<UK2Node_EnhancedInputAction>()`
4. Set the `InputAction` property directly instead of using reflection
5. Removed the legacy fallback path entirely

```cpp
// Before (failed):
UClass* EIANodeClass = FindObject<UClass>(nullptr, TEXT("/Script/EnhancedInput.K2Node_EnhancedInputAction"));
UEdGraphNode* RawNode = NewObject<UEdGraphNode>(Graph, EIANodeClass);

// After (works):
UK2Node_EnhancedInputAction* Node = NewObject<UK2Node_EnhancedInputAction>(Graph);
Node->InputAction = InputAction;
```

**Testing:**  
Enhanced Input Action nodes now create properly with all pins (Triggered, Started,
Ongoing, Completed, Canceled) and support for action value types.

---

## Roadmap

Derived from the limitations above, grouped by release priority.

---

### Phase 1 — Stability & Correctness (next rebuild)

These are fixes to things that already exist but produce wrong or confusing results.

| ID | Task | Status | Fixes |
|----|------|--------|-------|
| R-01 | Force `NodeGuid` assignment immediately on node creation | ✅ Fixed | L-010 |
| R-02 | Fix `set_node_pin_value` for `class`-type pins | ✅ Fixed | L-011 |
| R-03 | Echo original `function_target` + suggest candidates in error responses | ✅ Fixed | L-009 |
| R-04 | Return full error details in `compile_blueprint` response | ✅ Fixed | L-017 |
| R-05 | Add `/utf-8` compiler flag or pre-commit hook to prevent non-ASCII regression | Open | L-001 |
| R-06 | UE version guards for removed APIs (`EMessageSeverity`, etc.) | Open | L-002 |

---

### Phase 2 — Missing Node Types (closes the biggest workflow gaps)

| ID | Task | Status | Fixes |
|----|------|--------|-------|
| R-07 | `add_blueprint_for_loop_node` | ✅ Fixed | L-012 |
| R-08 | `add_blueprint_for_each_loop_node` | ✅ Fixed | L-012 |
| R-09 | `add_blueprint_sequence_node` | ✅ Fixed | L-012 |
| R-10 | `add_blueprint_do_once_node` | ✅ Fixed | L-012 |
| R-11 | `add_blueprint_switch_node` (int variant) | ✅ Fixed | L-012 |
| R-12 | `add_blueprint_spawn_actor_node` | ✅ Fixed | L-012 |
| R-13 | `add_blueprint_comment_node` | ✅ Fixed | L-018 |
| R-14 | `move_blueprint_node` | ✅ Fixed | L-019 |
| R-11b | `add_blueprint_gate_node` | ✅ Fixed | L-012 |
| R-11c | `add_blueprint_flip_flop_node` | ✅ Fixed | L-012 |
| R-11d | Switch on Enum (requires enum asset reference) | Open | L-012 |
| R-11e | Select node | Open | L-012 |
| R-11f | Timeline node (complex state, requires new approach) | Open | L-012 |

---

### Phase 3 — Property & Class Default Coverage

| ID | Task | Status | Fixes |
|----|------|--------|-------|
| R-15 | Full `FObjectProperty` support in `SetObjectProperty` | Open | L-006 |
| R-16 | `FStructProperty` support (FVector, FRotator, FColor, FLinearColor) | Open | L-006 |
| R-17 | Array/Map/Set property support | Open | L-006 |
| R-18 | `get_blueprint_variable_defaults` command | ✅ Fixed | L-013 |
| R-19 | `set_blueprint_variable_default` command | ✅ Fixed | L-013 |

---

### Phase 4 — Level & Scene Awareness

| ID | Task | Status | Fixes |
|----|------|--------|-------|
| R-20 | `get_level_actors` — list all actors in open level | Open | L-020 |
| R-21 | `get_blueprint_components` — list all components on a Blueprint | ✅ Fixed | L-020 |
| R-22 | `get_actor_properties` — read CDO/instance property values | Open | L-020 |
| R-23 | `setup_navmesh` — spawn + scale NavMeshBoundsVolume, trigger rebuild | ✅ Fixed | L-014 |

---

### Phase 5 — Developer Experience & Extensibility

| ID | Task | Fixes |
|----|------|-------|
| R-24 | Runtime property read during PIE (`get_runtime_property`) | L-020 |
| R-25 | `validate_blueprint_logic` — warn on anti-patterns (e.g. latent calls in Tick) | L-007 |
| R-26 | Reflection-based `call_engine_function` escape hatch | L-016 |
| R-27 | Embedded scripting engine (Python/Lua) for plugin extension without C++ rebuild | L-016 |

---

## How This File Is Maintained

- Every time a new limitation is hit during AI-assisted work, a new `L-NNN` entry is added.
- Every time a fix is shipped, the entry's **Status** and **Commit** are updated.
- The roadmap is re-prioritised at the start of each new feature push.
- This file lives at the repo root: `LIMITATIONS_AND_ROADMAP.md`.
