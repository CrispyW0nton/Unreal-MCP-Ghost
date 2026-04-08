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

### L-009 — `add_blueprint_function_node` silently drops the `function_target` when the UFunction cannot be found
**Status:** Open · **Severity:** High

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

**Ideal fix:**  
- Echo the original `function_target` in the error response.
- Return a list of candidate functions if the function name matches but the
  target class doesn't (e.g., `MoveToActor` exists on `AAIController` — suggest that).
- Support resolving by module path (`/Script/AIModule.AIController::MoveToActor`).

---

### L-010 — Node IDs return `00000000000000000000000000000000` immediately after creation
**Status:** Open · **Severity:** Medium

**What happened:**  
Several `add_blueprint_*_node` calls returned a node with
`node_id = "00000000000000000000000000000000"`. A subsequent
`find_blueprint_nodes` call was needed to retrieve the real GUID, adding an
extra round-trip.

**Root cause:**  
The GUID is assigned by `FBlueprintEditorUtils::MarkBlueprintAsModified` or
during the next compilation tick. Immediately after `NewObject` + `AddToGraph`,
the node's `NodeGuid` may still be zero.

**Ideal fix:**  
Force GUID assignment immediately after node creation by calling
`Node->CreateNewGuid()` before returning the response, then return that GUID.

---

### L-011 — `set_node_pin_value` returns success but pin value appears empty
**Status:** Open · **Severity:** Medium

**What happened:**  
When trying to set the `ActorClass` pin on a `GetActorOfClass` node to
`"ThePlayerCharacter"`, the command returned `{ node_id, pin_name }` but the
`value` field in the response was empty, and the pin did not update in the editor.

**Root cause:**  
`SetLiteralPinValue` in `UnrealMCPBlueprintNodeCommands.cpp` handles `object`
and `class` pin types differently than scalar types. Class pins require setting
the default object reference, not a string literal.

**Ideal fix:**  
For `class`-type pins, resolve the class by name and call
`Schema->TrySetDefaultObject` instead of `TrySetDefaultText`.

---

### L-012 — No commands for common structural node types
**Status:** Open · **Severity:** High

**Missing node types that require manual editor work or cannot be created at all:**

| Node | Workaround | Effort to Add |
|------|-----------|--------------|
| `ForLoop` / `ForEachLoop` | None via MCP | Low — `UK2Node_MacroInstance` or dedicated |
| `Sequence` | None | Low |
| `DoOnce` | None | Low |
| `Gate` | None | Low |
| `Delay` | `add_blueprint_function_node` with `KismetSystemLibrary` | Already works |
| `Switch on Int` / `Switch on Enum` | None | Medium |
| `Select` | None | Medium |
| `Timeline` | None | High |
| `SpawnActor` | None | Medium |
| `SetTimer by Function Name` | `add_blueprint_function_node` | Already works |
| `GetAllActorsOfClass` | `add_blueprint_function_node` | Already works |
| `LineTraceByChannel` | `add_blueprint_function_node` | Already works |

---

### L-013 — No way to read or write Blueprint variable default values
**Status:** Open · **Severity:** Medium

**What happened:**  
There is no command to read the current default value of a Blueprint variable
(e.g., "what is `PatrolRadius` set to?") or to update it. `set_node_pin_value`
only sets unconnected pin literals, not variable defaults.

**Ideal fix:**  
Add `get_blueprint_variable_defaults` and `set_blueprint_variable_default`
commands that use `FBlueprintEditorUtils::GetBlueprintVariableMetaData` and
`SetBlueprintVariableMetaData` / CDO property access.

---

### L-014 — No NavMesh setup command
**Status:** Open · **Severity:** Medium

**What happened:**  
AI movement requires a `NavMeshBoundsVolume` in the level. There is no MCP
command to place one or resize it. This had to be done manually every time.

**Ideal fix:**  
Add a `setup_navmesh` command under editor commands that:
1. Spawns a `ANavMeshBoundsVolume` at the world origin.
2. Scales it to a user-supplied extent (or auto-detects the level bounds).
3. Calls `FNavigationSystem::Build()` to force a rebuild.

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

### L-017 — `compile_blueprint` error messages are not returned when using the CLI
**Status:** Open · **Severity:** Medium

**What happened:**  
When `compile_blueprint` returned `"compiled with 1 error"`, the error
details were inside a `messages` array but the CLI piping with `python3 -c`
failed to parse them due to mixed stdout/stderr. The actual error message
(e.g., "pin type mismatch on node X") was never surfaced and had to be
investigated by inspecting each node individually.

**Ideal fix:**  
- `compile_blueprint` should return a human-readable `error_summary` string
  at the top level (not just inside `messages[]`) so it prints cleanly.
- CLI (`sandbox_ue5cli.py`) should pretty-print the `messages` array
  automatically on compile failure.

---

### L-018 — No command to add comments / organise the graph visually
**Status:** Open · **Severity:** Low

**What happened:**  
Nodes were added at raw coordinates with no grouping or comment boxes. The
resulting graph is functional but hard to read in the UE editor. Comment nodes
(`EdGraphNode_Comment`) exist in the graph already (added manually) but cannot
be created or positioned via MCP.

**Ideal fix:**  
Add `add_blueprint_comment_node` that creates an `EdGraphNode_Comment` with a
specified title, colour, position, and size.

---

### L-019 — No command to reposition existing nodes
**Status:** Open · **Severity:** Low

**What happened:**  
Nodes added via MCP are positioned at the coordinates provided at creation
time. If the layout needs adjusting after the fact, there is no
`move_blueprint_node` command — the node must be deleted and recreated.

**Ideal fix:**  
Add `move_blueprint_node` that sets `NodePosX` / `NodePosY` and calls
`MarkBlueprintAsModified`.

---

### L-020 — No round-trip read of UE project/level state (actors in scene, components, properties)
**Status:** Open · **Severity:** High

**What happened:**  
There is no reliable way to ask "what Blueprints exist in this level right now?",
"what components does BP_AggroBot1 have?", or "what is the current value of
`IsHunting?` at runtime?". Debugging during playtesting requires the user to
manually check the UE editor.

**Ideal fix:**  
- `get_level_actors` — list all actors in the open level with class, name, position.
- `get_actor_properties` — read CDO and instance override properties.
- `get_blueprint_components` — list all components (SCS nodes + native) on a Blueprint.
- Runtime debug: `get_runtime_property` using `GWorld` to read live property values during PIE.

---

## Roadmap

Derived from the limitations above, grouped by release priority.

---

### Phase 1 — Stability & Correctness (next rebuild)

These are fixes to things that already exist but produce wrong or confusing results.

| ID | Task | Fixes |
|----|------|-------|
| R-01 | Force `NodeGuid` assignment immediately on node creation | L-010 |
| R-02 | Fix `set_node_pin_value` for `class`-type pins | L-011 |
| R-03 | Echo original `function_target` in error responses from `add_blueprint_function_node` | L-009 |
| R-04 | Add `error_summary` top-level field to `compile_blueprint` response | L-017 |
| R-05 | Add `/utf-8` compiler flag or pre-commit hook to prevent non-ASCII regression | L-001 |
| R-06 | UE version guards for removed APIs (`EMessageSeverity`, etc.) | L-002 |

---

### Phase 2 — Missing Node Types (closes the biggest workflow gaps)

| ID | Task | Fixes |
|----|------|-------|
| R-07 | `add_blueprint_for_loop_node` | L-012 |
| R-08 | `add_blueprint_for_each_loop_node` | L-012 |
| R-09 | `add_blueprint_sequence_node` | L-012 |
| R-10 | `add_blueprint_do_once_node` | L-012 |
| R-11 | `add_blueprint_switch_node` (int + enum variants) | L-012 |
| R-12 | `add_blueprint_spawn_actor_node` | L-012 |
| R-13 | `add_blueprint_comment_node` | L-018 |
| R-14 | `move_blueprint_node` | L-019 |

---

### Phase 3 — Property & Class Default Coverage

| ID | Task | Fixes |
|----|------|-------|
| R-15 | Full `FObjectProperty` support in `SetObjectProperty` | L-006 |
| R-16 | `FStructProperty` support (FVector, FRotator, FColor, FLinearColor) | L-006 |
| R-17 | Array/Map/Set property support | L-006 |
| R-18 | `get_blueprint_variable_defaults` command | L-013 |
| R-19 | `set_blueprint_variable_default` command | L-013 |

---

### Phase 4 — Level & Scene Awareness

| ID | Task | Fixes |
|----|------|-------|
| R-20 | `get_level_actors` — list all actors in open level | L-020 |
| R-21 | `get_blueprint_components` — list all components on a Blueprint | L-020 |
| R-22 | `get_actor_properties` — read CDO/instance property values | L-020 |
| R-23 | `setup_navmesh` — spawn + scale NavMeshBoundsVolume, trigger rebuild | L-014 |

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
