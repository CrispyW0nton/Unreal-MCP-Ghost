# Unreal-MCP-Ghost — Architecture Blueprint

## Current System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        AI CLIENT LAYER                               │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────────┐ │
│  │Claude Desktop│  │   Cursor    │  │  GenSpark AI Developer       │ │
│  │  (Native)    │  │  (Native)   │  │  (Non-Native / Remote)       │ │
│  └──────┬───────┘  └──────┬──────┘  └───────────────┬──────────────┘ │
│         │ stdio           │ stdio                    │ SSE/HTTP       │
└─────────┼─────────────────┼──────────────────────────┼───────────────┘
          │                 │                          │
┌─────────▼─────────────────▼──────────────────────────▼───────────────┐
│                    MCP TRANSPORT LAYER                                │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │              unreal_mcp_server.py                                ││
│  │                                                                  ││
│  │  Transport Adapters:                                             ││
│  │  ├── StdioTransport  (default, local clients)                   ││
│  │  ├── SSETransport    (remote clients, --transport sse)          ││
│  │  └── StreamableHTTP  (modern clients, --transport streamable-http)│
│  │                                                                  ││
│  │  311 MCP Tools registered via @mcp_server.tool()                ││
│  └──────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   │ TCP JSON (port 55557)
                                   │ (via Playit tunnel if remote)
                                   │
┌──────────────────────────────────▼───────────────────────────────────┐
│                    UE5 C++ PLUGIN LAYER                               │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │  UnrealMCPBridge.cpp — Command Dispatcher + TCP Server          ││
│  │  MCPServerRunnable.cpp — TCP Accept Loop (FRunnable)            ││
│  │                                                                  ││
│  │  119 C++ Commands:                                               ││
│  │  ├── BlueprintCommands      (class create/compile/properties)   ││
│  │  ├── BlueprintNodeCommands  (40 node wiring commands)           ││
│  │  ├── ExtendedCommands       (50 advanced commands)              ││
│  │  ├── EditorCommands         (actor/level manipulation)          ││
│  │  ├── UMGCommands            (widget/UI commands)                ││
│  │  ├── ProjectCommands        (input/project commands)            ││
│  │  └── CommonUtils            (shared helpers)                    ││
│  │                                                                  ││
│  │  exec_python → Runs arbitrary Python on UE5 GameThread          ││
│  └──────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   │ UE5 Editor API (GameThread)
                                   │
┌──────────────────────────────────▼───────────────────────────────────┐
│                      UNREAL ENGINE 5                                 │
│                                                                      │
│  Blueprints │ Actors │ Materials │ Animation │ Niagara │ Sequencer   │
│  UI/UMG │ AI/BehaviorTrees │ DataTables │ Landscape │ MetaSound     │
└──────────────────────────────────────────────────────────────────────┘
```

## Target Architecture (Clean Architecture Refactored)

```
┌──────────────────────────────────────────────────────────────────────┐
│  OUTER RING — Frameworks & Drivers (Transport)                       │
│                                                                      │
│  StdioAdapter │ SSEAdapter │ StreamableHTTPAdapter                   │
│  MCP Resource Provider │ Session Persistence Store                   │
└───────────────────────────────────┬──────────────────────────────────┘
                                    │ implements TransportPort
┌───────────────────────────────────▼──────────────────────────────────┐
│  INTERFACE ADAPTERS                                                   │
│                                                                      │
│  ToolRegistry         — discovers & registers all tools              │
│  ResourceRegistry     — serves knowledge base as MCP resources       │
│  SessionManager       — tracks per-client state & context            │
│  ErrorHandler         — centralized error formatting & retry logic   │
│  MetricsCollector     — tool execution timing & success rates        │
│  CommandQueue         — batches & orders commands for reliability     │
└───────────────────────────────────┬──────────────────────────────────┘
                                    │ depends on UseCasePorts
┌───────────────────────────────────▼──────────────────────────────────┐
│  USE CASES — Application Business Rules (311+ Tools)                 │
│                                                                      │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐ ┌─────────────┐ │
│  │ AssetImport  │ │ Blueprint    │ │ Material     │ │ Animation   │ │
│  │ Pipeline     │ │ Tools        │ │ Tools        │ │ Tools       │ │
│  ├─────────────┤ ├──────────────┤ ├──────────────┤ ├─────────────┤ │
│  │import_sound │ │create_bp     │ │create_mat    │ │create_ik_rig│ │
│  │import_tex   │ │compile_bp    │ │add_expr      │ │auto_retarget│ │
│  │import_mesh  │ │add_node      │ │connect_nodes │ │retarget_anim│ │
│  │import_skel  │ │wire_pins     │ │create_inst   │ │batch_retarg │ │
│  └─────────────┘ └──────────────┘ └──────────────┘ └─────────────┘ │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐ ┌─────────────┐ │
│  │ AI/BT       │ │ VFX/Niagara  │ │ UI/UMG       │ │ World       │ │
│  │ Tools        │ │ Tools        │ │ Tools        │ │ Tools       │ │
│  └─────────────┘ └──────────────┘ └──────────────┘ └─────────────┘ │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐                  │
│  │ 3D Generate │ │ MetaHuman    │ │ Game Systems │                  │
│  │ Pipeline     │ │ Tools        │ │ Templates    │                  │
│  └─────────────┘ └──────────────┘ └──────────────┘                  │
└───────────────────────────────────┬──────────────────────────────────┘
                                    │ depends on BridgePort
┌───────────────────────────────────▼──────────────────────────────────┐
│  ENTITIES — Core Domain (Command Protocol)                           │
│                                                                      │
│  UE5CommandSchema    — JSON command/response format definition       │
│  AssetDefinition     — asset type, path, properties schema          │
│  BlueprintDefinition — blueprint structure, nodes, pins schema      │
│  AnimationDefinition — skeleton, IK rig, retarget chain schema      │
│  MaterialDefinition  — material graph, nodes, connections schema    │
└───────────────────────────────────┬──────────────────────────────────┘
                                    │ implements BridgePort
┌───────────────────────────────────▼──────────────────────────────────┐
│  OUTER RING — Frameworks & Drivers (UE5 Bridge)                      │
│                                                                      │
│  TCPBridgeAdapter    — current: TCP JSON to C++ plugin               │
│  ExecPythonAdapter   — fallback: runs Python directly in UE5         │
│  (Future) InProcessAdapter — if MCP server runs inside UE5 plugin   │
└──────────────────────────────────────────────────────────────────────┘
```

## Dependency Rule Compliance

```
ALLOWED:
  Transport → ToolRegistry → Tools → BridgePort → (abstract)
  TCPBridge implements BridgePort  (outer ring, inward dependency ✓)
  SSEAdapter implements TransportPort  (outer ring, inward dependency ✓)

FORBIDDEN:
  Tools → SSEAdapter  (tool must not know about transport) ✗
  BridgePort → Tools  (bridge must not know about specific tools) ✗
  Entities → anything  (entities are the innermost circle) ✗
```

## Tool Module Organization (Current → Target)

### Current: 18 modules in `unreal_mcp_server/tools/`
```
tools/
├── actor_tools.py          # Actor/level manipulation
├── blueprint_tools.py      # Blueprint class operations
├── blueprint_node_tools.py # Node creation & wiring
├── ai_tools.py             # Behavior trees, blackboards
├── animation_tools.py      # Animation, notifies
├── data_tools.py           # Data tables, structs
├── input_tools.py          # Input actions, mappings
├── material_tools.py       # Material instances (limited)
├── niagara_tools.py        # VFX/Niagara
├── sequencer_tools.py      # Sequencer tracks
├── ui_tools.py             # UMG widgets
├── umg_tools.py            # UMG commands
├── world_tools.py          # World building
├── project_tools.py        # Project-level operations
├── editor_tools.py         # Editor utilities
├── debug_tools.py          # Debugging/inspection
├── extended_tools.py       # Extended command wrappers
└── utility_tools.py        # Misc utilities
```

### Target: Add these modules
```
tools/
├── ... (existing 18 modules)
├── asset_import_tools.py   # NEW — Phase 1: Sound, Texture, Mesh import
├── material_graph_tools.py # NEW — Phase 2: Full material graph creation
├── ik_retarget_tools.py    # NEW — Phase 3: IK rig, retargeting automation
├── model_gen_tools.py      # NEW — Phase 4: AI 3D model generation
├── metahuman_tools.py      # NEW — Phase 5: MetaHuman automation
├── landscape_tools.py      # NEW — Phase 5: Landscape generation
├── pcg_tools.py            # NEW — Phase 5: PCG graph building
├── metasound_tools.py      # NEW — Phase 5: MetaSound graph building
└── game_template_tools.py  # NEW — Phase 5: Pre-built game systems
```

## C++ Command Expansion Plan

### Current: 119 commands across 7 source files
### Target additions by phase:

| Phase | New C++ Commands | Source File |
|-------|-----------------|-------------|
| Phase 1 | `import_asset`, `get_content_browser_path`, `list_assets_in_folder` | UnrealMCPAssetCommands.cpp (NEW) |
| Phase 2 | `create_material_graph`, `add_material_node`, `connect_material_pins` | UnrealMCPMaterialCommands.cpp (NEW) |
| Phase 3 | `create_ik_rig_asset`, `setup_retarget`, `batch_retarget` | UnrealMCPAnimationCommands.cpp (NEW) |
| Phase 4 | None (API calls handled in Python) | N/A |
| Phase 5 | `create_landscape`, `create_pcg_graph`, `create_metasound` | Various new files |

**Decision: exec_python vs C++ Command**
- Use **exec_python** for: Rapid prototyping, one-off operations, API calls to external services
- Promote to **C++ command** when: Called frequently, needs GameThread guarantees, performance critical
- Rule of thumb: Start everything as exec_python, promote to C++ after it's stable and used often

## Communication Protocol

### TCP JSON Command Format (Port 55557)
```json
// Request
{
    "command": "exec_python",
    "params": {
        "code": "import unreal\n# ... python code ..."
    }
}

// Response
{
    "status": "success",
    "result": { ... }
}

// Error Response
{
    "status": "error",
    "error": "Description of what went wrong",
    "traceback": "Optional Python traceback"
}
```

### MCP Tool → TCP Command Flow
```
1. AI Client calls MCP tool (e.g., import_sound_asset)
2. Python tool handler builds exec_python code string
3. Tool sends TCP JSON: {"command": "exec_python", "params": {"code": "..."}}
4. C++ plugin receives on port 55557
5. UnrealMCPBridge dispatches to exec_python handler
6. Python code runs on UE5 GameThread via FPythonCommandEx
7. Result printed to stdout, captured by C++ handler
8. JSON response sent back over TCP
9. Python tool parses response, returns to MCP client
10. AI Client receives result
```

## Error Handling Strategy

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ MCP Tool     │────▶│ ErrorHandler │────▶│ Return JSON │
│ try/except   │     │ classify()   │     │ to client   │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │ Error Types: │
                    │ • CONN_ERR   │──▶ Auto-retry (3x with backoff)
                    │ • TIMEOUT    │──▶ Retry once, then fail gracefully
                    │ • UE5_ERR    │──▶ Return error + suggestion
                    │ • PARAM_ERR  │──▶ Return validation error
                    │ • IMPORT_ERR │──▶ Return file-specific error
                    └─────────────┘
```

## Session State (For Native Mode Enhancement)

```json
// Per-client session state (stored in memory or Redis)
{
    "session_id": "uuid",
    "client_type": "claude_desktop | genspark | cursor",
    "transport": "stdio | sse | streamable-http",
    "project_context": {
        "project_name": "MyGame",
        "current_level": "MainLevel",
        "ue_version": "5.6"
    },
    "recent_operations": [
        {"tool": "create_blueprint", "args": {...}, "result": "success", "timestamp": "..."},
        {"tool": "import_sound_asset", "args": {...}, "result": "success", "timestamp": "..."}
    ],
    "active_assets": ["/Game/Blueprints/BP_Player", "/Game/Audio/SFX_Jump"],
    "conversation_context": "Building a 3rd person action game..."
}
```
