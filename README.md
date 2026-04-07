# Unreal Engine MCP Server — Enhanced Blueprint Visual Scripting Edition

> **Built on top of:** [chongdashu/unreal-mcp](https://github.com/chongdashu/unreal-mcp)  
> **Extended with:** Full support for all topics in *Blueprints Visual Scripting for Unreal Engine 5* by Marcos Romero

This MCP server lets you (or any AI assistant) create, modify, and compile full Unreal Engine 5 gameplay Blueprint systems through natural language — directly from Claude, Cursor, or Windsurf.

---

## Architecture

```
Claude / Cursor / Windsurf
        │
        │ MCP Protocol (stdio)
        ▼
  unreal_mcp_server.py          ← Python MCP Server (this repo)
        │
        │ TCP JSON (port 55557)
        ▼
  UnrealMCP C++ Plugin           ← Must be compiled into your UE5 project
        │
        │ UE5 Editor Subsystem
        ▼
  Unreal Engine 5.6+
```

---

## Prerequisites

Before starting, confirm you have all of the following installed:

| Requirement | Version | Notes |
|---|---|---|
| Unreal Engine | 5.6.1+ | Via Epic Games Launcher |
| Visual Studio | 2022 Community | **"Game Development with C++"** workload required |
| Python | 3.10+ | `python --version` to confirm |
| Git | Any | `git --version` to confirm |

### Verify Visual Studio 2022 workload

Open **Visual Studio Installer → Modify → Workloads** and confirm  
**"Game Development with C++"** is checked.  
Without this workload `UnrealBuildTool` cannot compile C++ plugins.

### Verify UE5 engine location

The build tools expect UE5 at:
```
C:\Program Files\Epic Games\UE_5.6\
```
Confirm with PowerShell:
```powershell
Test-Path "C:\Program Files\Epic Games\UE_5.6\Engine\Build\BatchFiles\Build.bat"
```
Expected output: `True`

---

## Full Setup Guide (First Time)

### Step 1 — Clone this repository

Keep dev tools organized in a dedicated folder, **not** on the Desktop:

```powershell
# Create the tools folder if it doesn't exist yet
New-Item -ItemType Directory -Force -Path "C:\Users\NewAdmin\Documents\KotorMods\Tools"

cd "C:\Users\NewAdmin\Documents\KotorMods\Tools"
git clone https://github.com/CrispyW0nton/Unreal-MCP-Ghost.git
cd Unreal-MCP-Ghost
git checkout genspark_ai_developer
```

Verify the clone:
```powershell
dir "C:\Users\NewAdmin\Documents\KotorMods\Tools\Unreal-MCP-Ghost\unreal_plugin\"
```
You should see: `UnrealMCP.uplugin`, `Source\`, `PLUGIN_SETUP.md`

---

### Step 2 — Copy the plugin into your UE5 project

Replace `<YourProject>` with your actual `.uproject` folder, e.g.  
`C:\Users\NewAdmin\Documents\Academy of Art University\2026\Gam115\UnrealProject\Lab3C`

```powershell
$proj = "C:\Users\NewAdmin\Documents\Academy of Art University\2026\Gam115\UnrealProject\Lab3C"
$repo = "C:\Users\NewAdmin\Documents\KotorMods\Tools\Unreal-MCP-Ghost"

# Create the plugin destination folder
New-Item -ItemType Directory -Force -Path "$proj\Plugins\UnrealMCP"

# Copy all plugin source files
Copy-Item -Recurse -Force "$repo\unreal_plugin\*" "$proj\Plugins\UnrealMCP\"
```

Verify the copy:
```powershell
dir "$proj\Plugins\UnrealMCP\"
```
Expected output: `Source\`, `PLUGIN_SETUP.md`, `UnrealMCP.uplugin`  
> **If you see a `Binaries\` folder** from a previous failed build, delete it:
> ```powershell
> Stop-Process -Name "UnrealEditor" -Force -ErrorAction SilentlyContinue
> Start-Sleep 3
> Remove-Item -Recurse -Force "$proj\Plugins\UnrealMCP\Binaries"
> Remove-Item -Recurse -Force "$proj\Plugins\UnrealMCP\Intermediate"
> ```

---

### Step 3 — Generate Visual Studio project files

```powershell
$proj = "C:\Users\NewAdmin\Documents\Academy of Art University\2026\Gam115\UnrealProject\Lab3C"
$uproject = "$proj\Lab3C.uproject"

cmd /c `"`"C:\Program Files\Epic Games\UE_5.6\Engine\Build\BatchFiles\GenerateProjectFiles.bat`" -project=`"$uproject`" -game -rocket`"
```

Alternatively, in **File Explorer**:
1. Navigate to your project folder
2. Right-click `Lab3C.uproject` → **"Generate Visual Studio project files"**
3. Wait for the command window to finish

This creates `Lab3C.sln` in your project folder.

---

### Step 4 — Compile the plugin in Visual Studio 2022

1. Double-click `Lab3C.sln` (or `start "$proj\Lab3C.sln"`) to open in VS 2022
2. Set the build target using the **two toolbar dropdowns**:
   - Configuration: **`Development Editor`**
   - Platform: **`Win64`**
3. Press **`Ctrl+Shift+B`** (Build Solution)
4. Watch the **Output** panel — first compile takes 5–20 minutes

**Successful build output ends with:**
```
========== Build: 1 succeeded, 0 failed, 0 up-to-date, 0 skipped ==========
```

After a successful build, `Plugins\UnrealMCP\Binaries\Win64\UnrealEditor-UnrealMCP.dll`  
will exist in your project folder.

#### Common compile errors and fixes

| Error message | Fix |
|---|---|
| `Cannot open include file: 'UserDefinedStructure/UserDefinedStructEditorUtils.h'` | Already fixed in this branch — re-pull and re-copy the `.cpp` files |
| `'VariableDescriptions': is not a member of 'UUserDefinedStruct'` | Already fixed — re-pull and re-copy |
| `PNGCompressImageArray: cannot convert TArray to TArray64` | Already fixed — re-pull and re-copy |
| `VariantManager` module not found | Already fixed in `Build.cs` — re-pull and re-copy |
| `'Game Development with C++' workload missing` | Open VS Installer → Modify → add the workload |
| Build exits with code 6 | Check the Output panel for the specific `error C` line and paste it here |

---

### Step 5 — Open the project and verify the plugin loads

1. Open UE5 from the `.uproject` file (double-click `Lab3C.uproject` in Explorer)
2. The editor will compile shaders on first launch — wait until 100%
3. Go to **Edit → Plugins**, search for **"UnrealMCP"** — it should show **Enabled** ✓
4. Open **Window → Output Log** and search for:
   ```
   UnrealMCPBridge: Server started on 127.0.0.1:55557
   ```
   If you see this line, the TCP server is running.

**Test the port from PowerShell** (UE5 must be open):
```powershell
python -c "import socket; s=socket.socket(); s.settimeout(2); r=s.connect_ex(('127.0.0.1',55557)); s.close(); print('PORT OPEN - plugin running!' if r==0 else 'PORT CLOSED - plugin not loaded')"
```

---

### Step 6 — Run the Python MCP Server

```powershell
cd "C:\Users\NewAdmin\Documents\KotorMods\Tools\Unreal-MCP-Ghost"
pip install mcp fastmcp
python unreal_mcp_server\unreal_mcp_server.py
```

Expected console output:
```
[MCP] Unreal MCP Server starting...
[MCP] 283 tools registered across 18 modules
[MCP] Server ready — connect your AI client
```

---

### Step 7 — Test the CLI

With UE5 open and the Python server running:
```powershell
cd "C:\Users\NewAdmin\Documents\KotorMods\Tools\Unreal-MCP-Ghost"
python unreal_mcp_server\ue5cli.py get_actors_in_level
```

Expected: a JSON list of every actor in the currently open level (WorldInfo, Brush, lights, meshes, etc.).

---

### Step 8 — Configure your MCP client

**Claude Desktop** — edit `%APPDATA%\Claude\claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "unrealMCP": {
      "command": "python",
      "args": ["C:/Users/NewAdmin/Documents/KotorMods/Tools/Unreal-MCP-Ghost/unreal_mcp_server/unreal_mcp_server.py"]
    }
  }
}
```

**Cursor** — create/edit `%APPDATA%\Cursor\User\mcp.json`:
```json
{
  "mcpServers": {
    "unreal-mcp": {
      "command": "python",
      "args": ["C:/Users/NewAdmin/Documents/KotorMods/Tools/Unreal-MCP-Ghost/unreal_mcp_server/unreal_mcp_server.py"]
    }
  }
}
```

Restart Claude Desktop or Cursor after saving. The AI client will now have all 283 UE5 tools available.

---

## Updating the plugin source

When new fixes are pushed to this repo, update your project in three steps:

```powershell
# 1. Pull latest fixes
cd "C:\Users\NewAdmin\Documents\KotorMods\Tools\Unreal-MCP-Ghost"
git pull origin genspark_ai_developer

# 2. Copy updated source files to your project
$src = "C:\Users\NewAdmin\Documents\KotorMods\Tools\Unreal-MCP-Ghost\unreal_plugin\Source\UnrealMCP\Private"
$dst = "C:\Users\NewAdmin\Documents\Academy of Art University\2026\Gam115\UnrealProject\Lab3C\Plugins\UnrealMCP\Source\UnrealMCP\Private"
Copy-Item -Recurse -Force "$src\*" "$dst\"

# 3. Rebuild in Visual Studio 2022 (Ctrl+Shift+B)
```

---

## Remote Access via Playit Tunnel

The plugin server listens only on `127.0.0.1:55557` by default.  
To access it from outside the machine (e.g. via an AI assistant running in a cloud sandbox),  
use a [Playit.gg](https://playit.gg/) TCP tunnel.

### Setup

1. Download `playit.exe` from [playit.gg](https://playit.gg/)
2. Create a **TCP tunnel** pointing to `localhost:55557`
3. Note your assigned address (e.g. `lie-instability.with.playit.plus:5462`)

### Keep it running

```powershell
Start-Process "C:\playit\playit.exe"
```

Leave this window open whenever you want remote access.

### Testing the tunnel

With UE5 open, playit running, and Python server running:
```powershell
python -c "
import socket, json
host, port = 'lie-instability.with.playit.plus', 5462
msg = json.dumps({'command':'get_actors_in_level','params':{}}) + '\n'
s = socket.socket()
s.settimeout(10)
s.connect((host, port))
s.sendall(msg.encode())
print(s.recv(65536).decode())
s.close()
"
```

### How the proxy-probe fix works

Playit (and other TCP proxies) periodically open a TCP connection, send zero bytes,  
then close it — these are health-check probes.  
The previous plugin code immediately disconnected on the first zero-byte read,  
which caused real commands arriving through the tunnel to be silently dropped.

**The fix** (in `MCPServerRunnable.cpp`): after accepting a connection the plugin now  
polls for pending data for up to 5 seconds (50 ms intervals).  
If data arrives in that window, it proceeds normally.  
If no data arrives within 5 seconds, the connection is classified as a probe and  
closed gracefully without blocking the next real connection.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `PORT CLOSED` in PowerShell test | Plugin not loaded or UE5 not running | Open UE5, check Output Log for `Server started on 127.0.0.1:55557` |
| Plugin shows as disabled in Edit → Plugins | Binaries not compiled | Follow Steps 3–4 to compile |
| `The following modules are missing` dialog | Expected — plugin needs compilation | Click **Yes** to rebuild (or use VS2022) |
| UE5 says `could not be compiled` | C++ error during build | Open VS2022, build manually, check Output for `error C` lines |
| `VariantManager not found` error | Missing optional module | Fixed in `Build.cs` on `genspark_ai_developer` — re-pull |
| CLI returns `Communication error: Expecting value` | UE5 not open or playit not running | Start UE5 first, verify port, then start playit |
| Tunnel receives zero bytes | Proxy health-check probe | Fixed in `MCPServerRunnable.cpp` — re-pull, re-copy, recompile |
| Port 55557 already in use | Another process | `netstat -ano \| findstr 55557` then `taskkill /PID <id> /F` |

### Finding the engine log

```powershell
Get-Content "C:\Users\NewAdmin\AppData\Local\UnrealEngine\5.6\Saved\Logs\Unreal.log" -Tail 30
```

Search for plugin messages:
```powershell
Select-String -Path "C:\Users\NewAdmin\AppData\Local\UnrealEngine\5.6\Saved\Logs\Unreal.log" -Pattern "UnrealMCP"
```

---

## What You Can Do (Full Feature List)

### Core Blueprint Development
| Feature | Tool |
|---------|------|
| Create any Blueprint class | `create_blueprint` |
| Add components | `add_component_to_blueprint` |
| Set physics | `set_physics_properties` |
| Compile | `compile_blueprint` |
| Set properties | `set_blueprint_property`, `set_component_property` |

### Event Graph Nodes
| Feature | Tool |
|---------|------|
| Event nodes (BeginPlay, Tick, etc.) | `add_blueprint_event_node` |
| Function calls | `add_blueprint_function_node` |
| Input actions | `add_blueprint_input_action_node` |
| Variables (get/set) | `add_blueprint_variable`, `add_get_variable_node`, `add_set_variable_node` |
| Self/component references | `add_blueprint_self_reference`, `add_blueprint_get_self_component_reference` |
| Node connections | `connect_blueprint_nodes` |

### Flow Control (Book Chapter 13)
| Node | Tool |
|------|------|
| Branch (if/else) | `add_branch_node` |
| Sequence | `add_sequence_node` |
| Flip Flop | `add_flipflop_node` |
| Do Once | `add_do_once_node` |
| Do N | `add_do_n_node` |
| Gate | `add_gate_node` |
| While Loop | `add_while_loop_node` |
| For Each Loop | `add_for_each_loop_node` |
| Switch on Int/String/Enum | `add_switch_on_int_node`, `add_switch_on_string_node`, `add_switch_on_enum_node` |
| MultiGate | `add_multigate_node` |

### Data Structures (Book Chapter 13)
| Feature | Tool |
|---------|------|
| Array variable | `add_array_variable` |
| Map variable | `add_map_variable` |
| Set variable | `add_set_variable` |
| Custom Struct | `create_struct` |
| Custom Enum | `create_enum` |
| DataTable | `create_data_table` |

### Blueprint Communication (Book Chapter 4)
| Feature | Tool |
|---------|------|
| Event Dispatchers | `add_event_dispatcher`, `call_event_dispatcher`, `bind_event_to_dispatcher` |
| Direct References | `add_direct_blueprint_reference` |
| Casting | `add_cast_node` |
| Blueprint Interfaces | `create_blueprint_interface`, `implement_blueprint_interface` |
| Custom Functions | `add_custom_function` |
| Custom Macros | `add_custom_macro`, `add_macro_node` |
| Function Libraries | `create_blueprint_function_library` |
| Macro Libraries | `create_blueprint_macro_library` |

### Gameplay Framework (Book Chapter 3)
| Feature | Tool |
|---------|------|
| GameMode | `create_game_mode` |
| PlayerController | `create_player_controller` |
| GameInstance | `create_game_instance` |
| HUD | `create_hud_blueprint` |
| Character (with camera) | `create_character_blueprint` |
| FPS Character | `create_fps_character` |
| Projectile | `create_projectile_blueprint` |
| Pickup | `create_pickup_blueprint` |
| Set level GameMode | `set_game_mode_for_level` |

### Animation Blueprints (Book Chapter 17)
| Feature | Tool |
|---------|------|
| Animation Blueprint | `create_animation_blueprint` |
| State Machine | `add_state_machine` |
| States | `add_animation_state` |
| Transitions | `add_state_transition` |
| Assign animations | `set_animation_for_state` |
| Blend Space | `add_blend_space_node` |
| Full character setup | `create_character_animation_setup` |

### AI Systems (Book AI Chapter)
| Feature | Tool |
|---------|------|
| Behavior Tree | `create_behavior_tree` |
| Blackboard | `create_blackboard` |
| AI Controller | `create_ai_controller` |
| BT Task | `create_bt_task` |
| BT Decorator | `create_bt_decorator` |
| BT Service | `create_bt_service` |
| Move To node | `add_move_to_node` |
| Blackboard value | `set_blackboard_value` |
| Full enemy AI | `create_full_enemy_ai` |

### UI / UMG (Book UI Chapter)
| Feature | Tool |
|---------|------|
| Widget Blueprint | `create_umg_widget_blueprint` |
| Text Block | `add_text_block_to_widget` |
| Button | `add_button_to_widget` |
| Progress Bar | `add_progress_bar_to_widget` |
| Image | `add_image_to_widget` |
| Widget Events | `bind_widget_event` |
| Add to Viewport | `add_widget_to_viewport` |
| Property Binding | `set_text_block_binding` |

### Debug & Utilities
| Feature | Tool |
|---------|------|
| Print String | `add_print_string_node` |
| Delay | `add_delay_node` |
| Timeline | `add_timeline_node` |
| Line Trace | `add_line_trace_node` |
| Math nodes | `add_math_node` |
| Comment Box | `add_comment_box` |
| Spawn Actor | `add_spawn_actor_node` |
| Destroy Actor | `add_destroy_actor_node` |
| Open Level | `add_open_level_node` |
| Apply Damage | `add_apply_damage_node` |
| Play Sound | `add_play_sound_node` |
| Build full graph | `build_complete_blueprint_graph` |

### Input Systems
| Feature | Tool |
|---------|------|
| Legacy input mapping | `create_input_mapping` |
| Enhanced Input Action | `create_enhanced_input_action` |
| Input Mapping Context | `create_input_mapping_context` |

---

## Example: Creating a Complete FPS Game System

Just tell Claude:

> "Create a complete FPS game setup with a character that has a gun, health system, a HUD showing health, an enemy with AI that chases and attacks the player."

The MCP tools will:
1. Create `BP_FPSCharacter` with camera, arms mesh, health variables
2. Create `BP_Projectile` with ProjectileMovement 
3. Create `BP_GameMode` assigning the character
4. Create `WBP_HUD` with health bar
5. Create `BB_Enemy` blackboard with PlayerActor, health keys
6. Create `BT_Enemy` behavior tree
7. Create `BP_Enemy` character with AIController
8. Wire up all Event Dispatchers for damage communication

---

## Book Coverage Summary

**283 tools** covering every chapter of *Blueprints Visual Scripting for Unreal Engine 5*:

| Chapter | Topic | Tools |
|---------|-------|-------|
| Ch. 1-2 | Blueprint Editor, Variables, Events, Macros, Functions | `blueprint_tools`, `node_tools` |
| Ch. 3 | OOP, Gameplay Framework (Actor/Pawn/Character/GameMode/GameInstance) | `gameplay_tools` |
| Ch. 4 | Communication (Dispatchers, Casting, Interfaces, Level BP) | `communication_tools` |
| Ch. 5-6 | Object Interaction, Materials, Hit Detection, Sprint, Zoom, Timeline | `material_tools`, `advanced_node_tools` |
| Ch. 7-8 | HUD/UMG, Health/Stamina Bars, Win/Lose Screens, Ammo Counter | `umg_tools`, `savegame_tools` |
| Ch. 9-10 | AI Enemies, NavMesh, Behavior Trees, Blackboard, Patrol, Chase | `ai_tools`, `procedural_tools` |
| Ch. 11 | Game States, SaveGame, Round System, Pause Menu, Player Death | `savegame_tools` |
| Ch. 12 | Build & Publish (packaging handled by UE Editor natively) | - |
| Ch. 13 | Arrays, Sets, Maps, Enums, Structs, DataTables, Flow Control | `data_tools` |
| Ch. 14 | Math & Trace Nodes (Vectors, Transforms, Line/Shape Traces) | `advanced_node_tools` |
| Ch. 15 | Blueprint Tips (Select, Teleport, Format Text, Math Expression, etc.) | `advanced_node_tools` |
| Ch. 16 | VR Development (VRPawn, Teleport, Grab, Blueprint Interfaces) | `vr_tools` |
| Ch. 17 | Animation Blueprints, State Machines, Blend Spaces | `animation_tools` |
| Ch. 18 | Function/Macro Libraries, Actor/Scene Components, Timers | `library_tools` |
| Ch. 19 | Procedural Generation, Splines, Editor Utilities | `procedural_tools` |
| Ch. 20 | Variant Manager, Product Configurator, Level Variant Sets | `variant_tools` |

---

## File Structure

```
unreal_mcp_server/
├── unreal_mcp_server.py          # Main MCP server
├── pyproject.toml                # Python package config
└── tools/
    ├── __init__.py
    ├── editor_tools.py           # Actor management, viewport
    ├── blueprint_tools.py        # Blueprint class operations
    ├── node_tools.py             # Event graph nodes
    ├── project_tools.py          # Input mappings
    ├── umg_tools.py              # Widget Blueprints
    ├── gameplay_tools.py         # GameMode, Character, etc.
    ├── communication_tools.py    # Dispatchers, Interfaces, Casting
    ├── data_tools.py             # Structs, Enums, Arrays, Maps, Sets, DataTables, Flow Control
    ├── animation_tools.py        # AnimBP, State Machines, Blend Spaces
    ├── ai_tools.py               # BehaviorTree, Blackboard, AI Tasks/Decorators
    ├── advanced_node_tools.py    # Branch, Delay, Timeline, Math, Select, Format Text, etc.
    ├── material_tools.py         # Material creation, dynamic materials, hit swap (Ch. 5-6)
    ├── savegame_tools.py         # SaveGame, LoadGame, pause, lose/win menus (Ch. 8, 11)
    ├── library_tools.py          # Function Libraries, Macro Libraries, Actor/Scene Components (Ch. 18)
    ├── procedural_tools.py       # Construction Script, ISM, Splines, Editor Utilities (Ch. 19)
    ├── vr_tools.py               # VRPawn, Motion Controllers, Grab, Teleport, Interfaces (Ch. 16)
    └── variant_tools.py          # Variant Manager, Level Variant Sets, Product Configurator (Ch. 20)

unreal_plugin/
├── UnrealMCP.uplugin             # Plugin descriptor (UE5.6, Editor module)
├── PLUGIN_SETUP.md               # Quick-reference for plugin-only setup
└── Source/UnrealMCP/
    ├── UnrealMCP.Build.cs        # Module build rules (VariantManager removed for UE5.6 compat)
    ├── Public/
    │   ├── UnrealMCPModule.h
    │   ├── UnrealMCPBridge.h     # UEditorSubsystem — starts TCP server on port 55557
    │   ├── MCPServerRunnable.h
    │   └── Commands/
    │       ├── UnrealMCPBlueprintCommands.h
    │       ├── UnrealMCPBlueprintNodeCommands.h
    │       ├── UnrealMCPCommonUtils.h
    │       ├── UnrealMCPEditorCommands.h
    │       ├── UnrealMCPExtendedCommands.h
    │       ├── UnrealMCPProjectCommands.h
    │       └── UnrealMCPUMGCommands.h
    └── Private/
        ├── UnrealMCPModule.cpp
        ├── UnrealMCPBridge.cpp
        ├── MCPServerRunnable.cpp  # TCP accept loop + Playit probe-fix
        └── Commands/
            ├── UnrealMCPBlueprintCommands.cpp
            ├── UnrealMCPBlueprintNodeCommands.cpp
            ├── UnrealMCPCommonUtils.cpp
            ├── UnrealMCPEditorCommands.cpp
            ├── UnrealMCPExtendedCommands.cpp
            ├── UnrealMCPProjectCommands.cpp
            └── UnrealMCPUMGCommands.cpp
```
