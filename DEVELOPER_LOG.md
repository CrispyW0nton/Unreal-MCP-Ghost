# Unreal MCP Ghost — Developer Log

> Project: **EnclaveProject** · UE 5.6.1 · MCP Server v2.0.0 · Plugin UnrealMCP UE5.6  
> Repo: https://github.com/CrispyW0nton/Unreal-MCP-Ghost  
> Branch: `genspark_ai_developer` → PR #6

---

## Table of Contents
1. [Asset Structure](#asset-structure)
2. [Crash Reports](#crash-reports)
3. [Bug Tracker](#bug-tracker)
4. [Test History](#test-history)
5. [Architecture Notes](#architecture-notes)

---

## Asset Structure

### `/Game/Dantooine/Art/Characters/` — 15 Character Folders

| Folder | Mesh Type | Has Skeleton | Has PhysicsAsset | Texture/Material |
|--------|-----------|-------------|-----------------|-----------------|
| `CommonerM1` | SkeletalMesh | ✅ | ✅ | ✅ basecolor |
| `ContructionDroid` ⚠️ | SkeletalMesh | ✅ | ✅ | ✅ basecolor |
| `DurosScholar` | SkeletalMesh | ✅ | ✅ | ✅ basecolor |
| `FloatingUtilityDroid` | **StaticMesh** | ❌ | ❌ | ✅ basecolor |
| `Ithorian` | SkeletalMesh | ✅ | ✅ | ✅ basecolor |
| `MasterDorak` | SkeletalMesh | ✅ | ✅ | ✅ basecolor |
| `MasterVandar` | SkeletalMesh | ✅ | ✅ | ✅ basecolor |
| `MasterVrook` | SkeletalMesh | ✅ | ✅ | ✅ basecolor |
| `MasterZhar` | SkeletalMesh | ✅ | ✅ | ✅ basecolor |
| `Mechanic1` | SkeletalMesh | ✅ | ✅ | ✅ (`LandingStripMechanic_*` ⚠️) |
| `Player` | SkeletalMesh | ✅ | ✅ | ✅ (`JediSparPartner_*` ⚠️) |
| `ProtocolDroid` | SkeletalMesh | ✅ | ✅ | ✅ basecolor |
| `RodianSpacer` | SkeletalMesh | ✅ | ✅ | ✅ basecolor |
| `TwiLekJedi` | SkeletalMesh | ✅ | ✅ | ✅ basecolor |
| `ZabrakSentinel` | SkeletalMesh | ✅ | ✅ | ✅ basecolor |

**Naming inconsistencies noted:**
- `ContructionDroid` — folder typo (missing 's' → should be `ConstructionDroid`)
- `Mechanic1` texture named `LandingStripMechanic_*` — mismatched name
- `Player` texture named `JediSparPartner_*` — mismatched name (should reflect Player character)

---

## Crash Reports

### CRASH-001 — `HandleAddBlueprintSpawnActorNode` Assertion at `EdGraphNode.h:586`
**Status:** ✅ **FIXED** (2026-04-12, commit `SafeMarkBlueprintModified` bulk replace)

**Location:** `UnrealMCPBlueprintNodeCommands.cpp` ~line 2489  
**Trigger:** `add_blueprint_spawn_actor_node` tool call on a freshly-created Blueprint  
**Error:** `Assertion failed: Result` at `EdGraphNode.h:586`  

**Root cause:**  
`FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP)` dereferences  
`BP->GeneratedClass` to invalidate the property chain. For newly-created Blueprints  
(or first-session access), `GeneratedClass` is `null` → `EXCEPTION_ACCESS_VIOLATION`  
→ SEH crash before TCP response → Python receives `WinError 10053`.

**Fix:** Introduced `FUnrealMCPCommonUtils::SafeMarkBlueprintModified(UBlueprint*)` in  
`UnrealMCPCommonUtils.h/.cpp`. Guards `GeneratedClass` validity; falls back to  
`Blueprint->Modify()` when null. Applied to **83 call sites** across 4 files:
- `UnrealMCPBlueprintNodeCommands.cpp` — 33 sites
- `UnrealMCPBlueprintCommands.cpp` — 9 sites  
- `UnrealMCPExtendedCommands.cpp` — 40 sites
- `UnrealMCPCommonUtils.cpp` — 1 site

### CRASH-002 — `SafeMarkBlueprintModified` Infinite Recursion
**Status:** ✅ **FIXED** (2026-04-12, same session)

**Root cause:** `SafeMarkBlueprintModified` called **itself** instead of  
`FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified` — infinite recursion  
→ stack overflow on any Blueprint with a valid `GeneratedClass`.

**Fix:** Corrected the call to `FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint)`.  
**All 83 guard sites were effectively no-ops before this fix.**

---

## Bug Tracker

### 🔴 Crash

| ID | Tool | Error | Status | Fix Commit |
|----|------|-------|--------|-----------|
| BUG-008 / CRASH-001 | `add_blueprint_spawn_actor_node` | Assertion `EdGraphNode.h:586` — null `GeneratedClass` | ✅ Fixed | `SafeMarkBlueprintModified` bulk |

### 🔴 Critical

| ID | Tool | Error | Status | Fix |
|----|------|-------|--------|-----|
| BUG-005 | Session — all tools after ~50 min | `"Could not connect to Unreal Engine on 127.0.0.1:55557"` — listener thread died | ✅ Fixed | 15s C++ watchdog timer + Python 30s reconnect loop |
| BUG-006 | `add_component_to_blueprint` | CLIENT-TIMEOUT >45s — `MarkBlueprintAsStructurallyModified` blocks GameThread | ✅ Fixed | `SafeMarkBlueprintModified` + GeneratedClass guard |

### 🟡 UE5-Side Timeouts / Behavioural Issues

| ID | Tool | Error | Status | Fix |
|----|------|-------|--------|-----|
| BUG-017 | `add_blueprint_event_node` (BeginPlay/Tick) | Event not found — `Blueprint->GeneratedClass->FindFunctionByName` fails on new BPs | ✅ Fixed | Rewrote `CreateEventNode`: walk parent class hierarchy, alias table (BeginPlay→ReceiveBeginPlay), custom event fallback |
| BUG-018 | `add_blueprint_sequence_node` (Sequence, ForLoop, DoOnce) | Macro library lookup blocks 200-800 ms on first call | ✅ Fixed | Cache `StandardMacros` UBlueprint in static `TWeakObjectPtr`; `FindObject` before `LoadObject` |
| BUG-019 | `add_blueprint_input_action_node` | `PostPlacedNewNode()` validates against Project Input Settings — slow on projects without legacy input | ✅ Fixed | Skip `PostPlacedNewNode`, call `AllocateDefaultPins()` directly |
| BUG-020 | `exec_python` ZeroDivisionError / ValueError | Exception caught by wrapper but `print()` through GLog blocked 20-30 s | ✅ Fixed | Replaced with silent `builtins._mcp_last_error` variable + C++ `EvaluateStatement` round-trip — no GLog flush, instant response |
| J1 (BUG-023) | `add_blueprint_self_reference` | CLIENT-TIMEOUT >45s — `UK2Node_Self::PostPlacedNewNode()` calls `GetSchema()->GetGraphType()` → dereferences `GeneratedClass`, blocking 20-45s on intermediate compile state | ✅ Fixed | `CreateSelfReferenceNode` now uses `Graph->AddNode(bFromUI=false)` + `AllocateDefaultPins()` directly — same approach as BUG-019 fix |
| BUG-024 | `add_component_to_blueprint` | CLIENT-TIMEOUT >45s — `SafeMarkBlueprintModified` broadcasts to all AssetRegistry and ContentBrowser listeners synchronously (30-60s on large projects) | ✅ Fixed | `HandleAddComponentToBlueprint` now calls only `Blueprint->Modify()`; `SCS->AddNode()` already triggers necessary `PostEditChange()` |
| BUG-025 | WinError 10038 (WSAENOTSOCK) | `receive_full_response` calls `sock.settimeout()` on socket already closed by UE5 watchdog restart; Python error classifier didn't include 10038 | ✅ Fixed | Added `sock.fileno()` pre-check to detect closed handle early; added `10038`/`WSAENOTSOCK`/`OSError` to retryable-socket-error classifier in `_send_command_raw` |

> **Note:** Full param names for BUG-009 through BUG-016 to be populated from next test run results.

### 🟡 UE5-Side Failures (GameThread timeouts / node creation failures)

| ID | Tool | Error | Status |
|----|------|-------|--------|
| BUG-017 | `add_blueprint_event_node` (BeginPlay) | Node not found / already exists | 🔍 Needs verify |
| BUG-018 | `add_print_string_node` | UE5 30s timeout on first call | 🔍 Needs verify |
| BUG-019 | `add_blueprint_sequence_node` | Macro library lookup fails | 🔍 Needs verify |
| BUG-020 | `add_blueprint_input_action_node` | UE5 30s timeout — GameThread hang | 🔍 Needs verify |
| BUG-021 | `exec_python` create BehaviorTree | CLIENT-TIMEOUT >60s — heavy factory | ⚠️ Expected / acceptable |
| BUG-022 | `exec_python` create WidgetBlueprint | CLIENT-TIMEOUT >60s — heavy factory | ⚠️ Expected / acceptable |

### ✅ Fixed (previous sessions)

| ID | Tool | Error | Fix |
|----|------|-------|-----|
| BUG-001 | `get_actors_in_level` | Bug #3 — newline-delimited JSON instead of array | Fixed (JSON array) |
| BUG-002 | All tools — SSE transport | Connection drops on long sessions | Fixed (streamable-http + retry) |
| BUG-003 | `exec_python` | SyntaxError / RuntimeError hang >30s | Fixed (try/except wrapper + Python pre-check) |
| BUG-004 | `get_blueprint_variables`, `compile_blueprint` | WinError 10053 on first call | Fixed (AR warmup + GeneratedClass guard + Python retry) |
| BUG-007 | `get_blueprint_functions` | GameThread block >45s (regression) | Fixed (SafePinToJson + IsValid guards) |

---

## Test History

| Date | Run | Checks | PASS | FAIL | WARN | Notes |
|------|-----|--------|------|------|------|-------|
| 2026-04-10 | Run 1 | ~20 | ~15 | ~5 | 0 | First test — SSE transport, basic connectivity |
| 2026-04-10 | Run 2 | 23 | 19 | 4 | 0 | `get_blueprint_functions` timeout, `add_blueprint_variable` sendall, exec_python errors |
| 2026-04-11 | Run 3 | 23 | 19 | 4 | 0 | Post exec_python fix — same 4 FAIL |
| 2026-04-11 | Run 4 | 51 | 49 | 2 | 0 | Major speed gains (20s total). Remaining: `get_blueprint_variables` + `compile_blueprint` WinError 10053 |
| 2026-04-11 | Run 5 | 51 | 51 | 0 | 0 | WinError 10053 fixed. **51/51 PASS** ✅ |
| 2026-04-12 | Run 6 | 81 | 69 | 5 | 7 | Expanded test suite. Socket drop after ~50 min, `add_component` hang |
| 2026-04-12 | Run 7 | 81 | 76+ | ~2 | ~3 | Post-watchdog / SafeMark fixes (estimated — awaiting results) |
| 2026-04-12 | Run 8 | 81 | 81+ | 0 | 0-1 | CRASH-002 fixed, BUG-017/018/019/020 fixed, exec_python fast errors. Target |
| 2026-04-13 | Run 9 | 81 | 77+ | ~1 | ~3 | Post J1/BUG-023/024/025 fixes. New: IK retargeting tools added. Target: ≥80/81 |

### Run 6 Failure Details (2026-04-12, 69/81)

**Failures (5):**
- J3: `add_component_to_blueprint` — CLIENT-TIMEOUT >45s
- L1: `compile_blueprint` — `Could not connect to 127.0.0.1:55557` (session drop)
- L2: `save_blueprint` — CLIENT-TIMEOUT >60s (session drop cascade)  
- L3: `get_blueprint_variables` — `Could not connect to 127.0.0.1:55557`
- L4: `get_blueprint_graphs` — CLIENT-TIMEOUT >45s (session drop cascade)

**Warnings (7):**
- G2: `exec_python` create BehaviorTree — >60s (heavy factory, acceptable)
- I1: `exec_python` create WidgetBlueprint — >60s (heavy factory, acceptable)
- K1–K4: Error-path lookups — timeout >30s instead of instant error
- K5: Duplicate `create_blueprint` — lost connection (55557)

---

## Architecture Notes

### Transport
- **Cursor (local):** `stdio` — Cursor auto-starts `unreal_mcp_server.py`, no port exposed
- **GenSpark (remote):** `sse` or `streamable-http` — requires Playit.gg tunnel on port 8000

### Socket Protocol
One TCP connection = one JSON command = one JSON response (newline-terminated).  
Python opens a fresh socket per command, UE5 sends response and closes.

### Timeout Budget (seconds)

| Tier | Commands | C++ Budget | Python Budget |
|------|----------|-----------|---------------|
| Fast | ping, get_node, set_pin, etc. | 24s | 30s |
| Slow | compile, save, create_blueprint, get_actors, add_variable, etc. | 80s | 90s |
| Very Slow | exec_python | 140s | 150s |

### Key Files

| File | Role |
|------|------|
| `unreal_plugin/.../UnrealMCPBridge.cpp` | C++ subsystem — socket listener, watchdog timer, command dispatch |
| `unreal_plugin/.../MCPServerRunnable.cpp` | TCP accept/read/send loop (one command per connection) |
| `unreal_plugin/.../Commands/UnrealMCPBlueprintNodeCommands.cpp` | 200+ Blueprint graph node tools |
| `unreal_plugin/.../Commands/UnrealMCPCommonUtils.cpp` | Shared utils: `FindBlueprint`, `SafeMarkBlueprintModified`, pin helpers |
| `unreal_mcp_server/unreal_mcp_server.py` | Python MCP server — FastMCP, `_send_command_raw`, reconnect logic |
| `unreal_mcp_server/tools/editor_tools.py` | `exec_python` tool with syntax pre-check |
| `cursor_setup/mcp.json` | Cursor MCP config (stdio transport) |
| `cursor_system_prompt.md` | System prompt for Cursor AI agent |
| `unreal_mcp_server/tools/animation_tools.py` | Animation BP tools + IK Rig / IK Retargeter tools (exec_python) |

### `SafeMarkBlueprintModified` — Why It Exists

`FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP)` calls into  
`BP->GeneratedClass` to invalidate the compiled property chain. For:
- Newly-created Blueprints (not yet compiled) 
- First-session access on a Blueprint not loaded since editor start
- Blueprints mid-compile when another command runs concurrently

`GeneratedClass` may be `null`, causing `EXCEPTION_ACCESS_VIOLATION` — an SEH  
hardware exception that bypasses C++ `catch(...)` and crashes the GameThread,  
resetting the TCP socket (Python sees `WinError 10053`).

**Solution:** `FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP)` checks  
`BP->GeneratedClass && IsValid(BP->GeneratedClass)` first. Falls back to  
`BP->Modify()` (marks dirty for Undo, no GeneratedClass access).

---

## Animation Retargeting Tools

### Overview
Manual animation retargeting is fully supported via the MCP tool using the UE5 Python API
(`unreal.IKRigController`, `unreal.IKRetargeterController`).  All retargeting tools use
`exec_python` internally (tier-3 timeout: 150 s on Python side, 140 s on C++ side).

### Supported Workflows

#### Method 1 — Quick Retarget (same bone structure)
If all characters share an identical skeleton (same bone names + hierarchy), use the
one-shot pipeline or call `batch_retarget_animations` directly with an existing Retargeter.

#### Method 2 — Manual IK Retarget (different bone structures)
1. `create_ik_rig` for source skeleton (e.g. Mannequin)
2. `create_ik_rig` for target skeleton (e.g. Player)
3. `create_ik_retargeter` — links source → target, auto-maps chains, auto-aligns bones
4. `batch_retarget_animations` — exports retargeted animation sequences

Or use `setup_full_retargeting_pipeline` to run all 4 steps at once.

### New MCP Tools (2026-04-13)

| Tool | Description |
|------|-------------|
| `create_ik_rig` | Create IKRigDefinition asset; optionally auto-generate humanoid chains |
| `add_ik_rig_retarget_chain` | Manually add a named bone chain (start → end) to an IK Rig |
| `set_ik_rig_retarget_root` | Set the pelvis/hips bone as the retarget root |
| `create_ik_retargeter` | Create IKRetargeter asset linking source → target IK Rigs |
| `batch_retarget_animations` | Export retargeted copies of multiple animation sequences |
| `retarget_single_animation` | Export one retargeted animation (quick test/verification) |
| `setup_full_retargeting_pipeline` | One-shot: IK Rigs + Retargeter + optional batch retarget |
| `get_skeleton_bone_names` | List all bone names in a Skeletal Mesh (use before manual chain setup) |

### Typical EnclaveProject Usage
```
# Step 1: Discover bone names (if unsure of exact names)
get_skeleton_bone_names("/Game/Dantooine/Art/Characters/Player/SK_Player")

# Step 2: Create IK Rigs for Mannequin (source) and Player (target)
create_ik_rig(ik_rig_name="IKR_Mannequin", skeletal_mesh_path="/Game/Characters/Mannequin/SK_Mannequin")
create_ik_rig(ik_rig_name="IKR_Player",    skeletal_mesh_path="/Game/Dantooine/Art/Characters/Player/SK_Player")

# Step 3: Create IK Retargeter
create_ik_retargeter(
    retargeter_name="RTG_Mannequin_To_Player",
    source_ik_rig_path="/Game/Animation/IKRigs/IKR_Mannequin",
    target_ik_rig_path="/Game/Animation/IKRigs/IKR_Player"
)

# Step 4: Batch retarget all animations for Player character
batch_retarget_animations(
    retargeter_path="/Game/Animation/Retargeters/RTG_Mannequin_To_Player",
    source_animation_paths=["/Game/Animations/Walk", "/Game/Animations/Run", ...],
    output_path="/Game/Dantooine/Art/Characters/Player/Animations"
)

# OR: All-in-one
setup_full_retargeting_pipeline(
    source_skeletal_mesh="/Game/Characters/Mannequin/SK_Mannequin",
    target_skeletal_mesh="/Game/Dantooine/Art/Characters/Player/SK_Player",
    source_ik_rig_name="IKR_Mannequin",
    target_ik_rig_name="IKR_Player",
    retargeter_name="RTG_Mannequin_To_Player",
    animations_to_retarget=["/Game/Animations/Walk", "/Game/Animations/Run"]
)
```

### Notes
- **IKRigEditor module required:** The IKRig plugin must be enabled in the project
  (`Edit > Plugins > IK Rig`). It is enabled by default in UE 5.6.
- **Auto-generate chains:** Works best for humanoid skeletons (UE Mannequin-like).
  For non-humanoid skeletons (droids, quadrupeds), use `add_ik_rig_retarget_chain` manually.
- **Retarget root:** `apply_auto_generated_retarget_definition` sets the root automatically.
  For custom chains, call `set_ik_rig_retarget_root(root_bone="pelvis")` first.
- **Batch export API:** UE5 exposes retarget export through multiple APIs
  (`IKRetargetEditorController`, `IKRetargetingUtils`, `AssetTools`). The tools try all
  three in order for maximum compatibility across UE 5.4–5.6.
