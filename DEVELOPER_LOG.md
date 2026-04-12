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

### 🟡 Validation / Schema Mismatches (param name bugs)

| ID | Tool | Wrong Param | Correct Param | Status |
|----|------|-------------|---------------|--------|
| BUG-009 | `add_blueprint_event_node` | TBD from test run | `event_name` | 🔍 Needs verify |
| BUG-010 | `add_print_string_node` | TBD | TBD | 🔍 Needs verify |
| BUG-011 | `add_blueprint_sequence_node` | TBD | TBD | 🔍 Needs verify |
| BUG-012 | `add_blueprint_branch_node` | TBD | TBD | 🔍 Needs verify |
| BUG-013 | `connect_blueprint_nodes` | TBD | TBD | 🔍 Needs verify |
| BUG-014 | `set_node_pin_value` | TBD | TBD | 🔍 Needs verify |
| BUG-015 | `get_blueprint_nodes` | TBD | TBD | 🔍 Needs verify |
| BUG-016 | `find_blueprint_nodes` | TBD | TBD | 🔍 Needs verify |

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
| 2026-04-12 | Run 7 | 81 | 76+ | 2 | 3 | Post-watchdog / SafeMark fixes (estimated — awaiting results) |
| TBD | Run 8 | 81 | 81 | 0 | 0 | Target |

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
