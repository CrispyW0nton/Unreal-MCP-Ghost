# Unreal MCP — AI-Powered Blueprint Scripting for UE5

Control Unreal Engine 5 with natural language from any AI assistant (Claude, Cursor, Windsurf, or any MCP client). Write Blueprint logic, spawn actors, wire nodes, compile — all without touching the UE5 editor manually.

> **Based on:** [chongdashu/unreal-mcp](https://github.com/chongdashu/unreal-mcp)  
> **Extended with:** 283 tools covering every chapter of *Blueprints Visual Scripting for Unreal Engine 5*

---

## How It Works

```
Your AI Client (Claude / Cursor / Windsurf)
           │
           │  MCP Protocol (stdio)
           ▼
   unreal_mcp_server.py        ← Python server (this repo)
           │
           │  TCP JSON  port 55557
           ▼
   UnrealMCP C++ Plugin         ← compiled into your UE5 project
           │
           │  UE5 Editor API
           ▼
   Unreal Engine 5
```

The Python server translates AI tool calls into JSON commands sent over a local TCP socket. The C++ plugin (an Editor Subsystem) receives them and executes Blueprint graph operations inside the live editor.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Clone the Repository](#2-clone-the-repository)
3. [Copy the Plugin into Your UE5 Project](#3-copy-the-plugin-into-your-ue5-project)
4. [Generate Visual Studio Project Files](#4-generate-visual-studio-project-files)
5. [Compile the Plugin](#5-compile-the-plugin)
6. [Open UE5 and Verify the Plugin](#6-open-ue5-and-verify-the-plugin)
7. [Install Python Dependencies](#7-install-python-dependencies)
8. [Configure Your AI Client](#8-configure-your-ai-client)
9. [Test the Connection](#9-test-the-connection)
10. [Keeping the Plugin Up to Date](#10-keeping-the-plugin-up-to-date)
11. [Remote Access via Playit Tunnel](#11-remote-access-via-playit-tunnel)
12. [Troubleshooting](#12-troubleshooting)
13. [Available Tools Reference](#13-available-tools-reference)

---

## 1. Prerequisites

Install everything in this table before continuing.

| Tool | Minimum Version | How to Check | Download |
|---|---|---|---|
| **Unreal Engine** | 5.4 or later | Epic Games Launcher → Library | [epicgames.com](https://www.unrealengine.com/en-US/download) |
| **Visual Studio** | 2022 (Community or better) | VS Installer | [visualstudio.microsoft.com](https://visualstudio.microsoft.com/downloads/) |
| **Python** | 3.10 or later | `python --version` | [python.org](https://www.python.org/downloads/) |
| **Git** | Any | `git --version` | [git-scm.com](https://git-scm.com/) |

### Visual Studio 2022 — Required Workload

The C++ plugin **will not compile** without this workload.

1. Open **Visual Studio Installer**
2. Click **Modify** next to Visual Studio 2022
3. On the **Workloads** tab, check ✅ **Game development with C++**
4. Click **Modify** / **Install** and wait for it to finish

### Python — Add to PATH

During Python installation, check **"Add Python to PATH"**. Verify afterward:
```
python --version
pip --version
```
Both should print a version number, not an error.

---

## 2. Clone the Repository

Choose a permanent location on your machine. Avoid paths with spaces if possible; if your username has spaces, wrap all paths in quotes in every command.

```powershell
# Example — adjust the destination folder to your preference
git clone https://github.com/CrispyW0nton/Unreal-MCP-Ghost.git "C:\Dev\Unreal-MCP"
cd "C:\Dev\Unreal-MCP"
git checkout genspark_ai_developer
```

> **Why `genspark_ai_developer`?** All active development and bug fixes live on this branch. The `main` branch is the base fork.

Verify the clone succeeded:
```powershell
dir "C:\Dev\Unreal-MCP\unreal_plugin"
```
Expected output includes: `UnrealMCP.uplugin`, `Source\`

---

## 3. Copy the Plugin into Your UE5 Project

The plugin must live inside your project's `Plugins\` folder so UE5 can find and compile it.

### 3a. Locate your UE5 project folder

This is the folder that contains your `.uproject` file. For example:
```
C:\Users\YourName\Documents\UnrealProjects\MyGame\MyGame.uproject
```

### 3b. Copy the plugin

Run these commands in PowerShell. Replace the two path variables with your actual paths.

```powershell
# Set these two paths for your machine
$REPO   = "C:\Dev\Unreal-MCP"
$PROJECT = "C:\Users\YourName\Documents\UnrealProjects\MyGame"

# Create the plugin folder inside your project
New-Item -ItemType Directory -Force -Path "$PROJECT\Plugins\UnrealMCP"

# Copy all plugin files
Copy-Item -Recurse -Force "$REPO\unreal_plugin\*" "$PROJECT\Plugins\UnrealMCP\"
```

Verify:
```powershell
dir "$PROJECT\Plugins\UnrealMCP"
```
Expected output includes: `Source\`, `UnrealMCP.uplugin`

> **If you see a `Binaries\` folder** left over from a previous failed build, delete it before compiling:
> ```powershell
> Stop-Process -Name "UnrealEditor" -Force -ErrorAction SilentlyContinue
> Start-Sleep 2
> Remove-Item -Recurse -Force "$PROJECT\Plugins\UnrealMCP\Binaries"
> Remove-Item -Recurse -Force "$PROJECT\Plugins\UnrealMCP\Intermediate"
> ```

---

## 4. Generate Visual Studio Project Files

UE5 needs to regenerate its `.sln` and `.vcxproj` files to include the new plugin source.

**Option A — Right-click (simplest):**
1. Open **File Explorer** and navigate to your project folder
2. Right-click `YourProject.uproject`
3. Click **"Generate Visual Studio project files"**
4. Wait for the small console window to disappear

**Option B — Command line:**
```powershell
$PROJECT  = "C:\Users\YourName\Documents\UnrealProjects\MyGame"
$UPROJECT = "$PROJECT\MyGame.uproject"
$UE_VER   = "5.6"   # Change to match your installed UE version (5.4, 5.5, 5.6...)

& "C:\Program Files\Epic Games\UE_$UE_VER\Engine\Build\BatchFiles\GenerateProjectFiles.bat" `
    -project="$UPROJECT" -game -rocket
```

After this step, `MyGame.sln` will appear or be updated in your project folder.

---

## 5. Compile the Plugin

Open the solution in Visual Studio 2022 and build it.

1. Double-click `MyGame.sln` in your project folder
2. In the **two toolbar dropdowns**, set:
   - **Configuration:** `Development Editor`
   - **Platform:** `Win64`
3. Press **`Ctrl+Shift+B`** (Build Solution)

The first compile takes **5–20 minutes** depending on your machine. Subsequent builds are incremental (under 30 seconds).

**Success looks like:**
```
========== Build: 1 succeeded, 0 failed, 0 up-to-date, 0 skipped ==========
```

**After a successful build**, this file will exist:
```
MyGame\Plugins\UnrealMCP\Binaries\Win64\UnrealEditor-UnrealMCP.dll
```

### Common Compile Errors

| Error | Fix |
|---|---|
| `'Game development with C++' workload not installed` | Open VS Installer → Modify → add the workload |
| `Cannot open include file: '...'` | Re-pull the repo and re-copy the Source folder |
| `error C2039: 'VariantManager'` | Already fixed in `Build.cs` on this branch — re-pull |
| `PNGCompressImageArray: cannot convert TArray to TArray64` | Already fixed — re-pull and re-copy |
| Build reports exit code 6 with no error shown | Scroll up in the Output panel to find the specific `error C` line |

---

## 6. Open UE5 and Verify the Plugin

1. Double-click your `.uproject` file to open it in UE5
2. If a dialog appears saying **"The following modules are missing or built with a different engine version — would you like to rebuild now?"**, click **Yes** (this is normal on first launch after adding a plugin)
3. Wait for shader compilation to finish (progress bar in the bottom-right corner)

### Confirm the plugin is loaded

**In UE5:** Go to **Edit → Plugins**, search for `UnrealMCP`. It should show a green checkbox ✅ and the description *"Unreal MCP plugin..."*.

**In the Output Log:** Go to **Window → Output Log** and look for:
```
LogTemp: UnrealMCPBridge: Server started on 127.0.0.1:55557
```

**From PowerShell** (with UE5 open):
```powershell
python -c "
import socket
s = socket.socket()
s.settimeout(2)
result = s.connect_ex(('127.0.0.1', 55557))
s.close()
print('PLUGIN RUNNING — port 55557 is open' if result == 0 else 'PLUGIN NOT RUNNING — port 55557 is closed')
"
```

If the port is closed, re-check the Output Log for error messages starting with `UnrealMCP`.

---

## 7. Install Python Dependencies

```powershell
cd "C:\Dev\Unreal-MCP"
pip install mcp fastmcp
```

Verify:
```powershell
python -c "import mcp; import fastmcp; print('OK')"
```

---

## 8. Configure Your AI Client

The MCP server must be registered with your AI client so it can discover and call the tools.

### Claude Desktop

Edit `%APPDATA%\Claude\claude_desktop_config.json` (create the file if it doesn't exist):

```json
{
  "mcpServers": {
    "unrealMCP": {
      "command": "python",
      "args": ["C:/Dev/Unreal-MCP/unreal_mcp_server/unreal_mcp_server.py"]
    }
  }
}
```

> Replace `C:/Dev/Unreal-MCP` with your actual clone path. Use forward slashes.

### Cursor

Edit `%APPDATA%\Cursor\User\mcp.json` (create if it doesn't exist):

```json
{
  "mcpServers": {
    "unreal-mcp": {
      "command": "python",
      "args": ["C:/Dev/Unreal-MCP/unreal_mcp_server/unreal_mcp_server.py"]
    }
  }
}
```

### Windsurf

Edit `%APPDATA%\Windsurf\User\mcp.json`:

```json
{
  "mcpServers": {
    "unreal-mcp": {
      "command": "python",
      "args": ["C:/Dev/Unreal-MCP/unreal_mcp_server/unreal_mcp_server.py"]
    }
  }
}
```

### Any other MCP-compatible client

Point the client to run this command:
```
python "C:\Dev\Unreal-MCP\unreal_mcp_server\unreal_mcp_server.py"
```

The server communicates over **stdio** using the MCP protocol. No additional flags are required.

**Restart your AI client** after saving the config file.

---

## 9. Test the Connection

With UE5 open and the plugin running:

### Quick test via the CLI script

```powershell
cd "C:\Dev\Unreal-MCP"
python sandbox_ue5cli.py get_actors_in_level
```

Expected output: a JSON list of every actor in your currently open level.

### Test via your AI client

Open a new chat in Claude Desktop / Cursor and send:

> "List all the actors in the current Unreal Engine level."

The AI should call `get_actors_in_level` and return a list of actors. If it instead says it cannot connect to Unreal Engine, check that:
1. UE5 is open with your project
2. The plugin is enabled and port 55557 is open (Step 6)
3. Your AI client config points to the correct Python file path (Step 8)
4. You restarted the AI client after editing the config

---

## 10. Keeping the Plugin Up to Date

When fixes or new features are pushed to this repo, update your local copy and rebuild.

```powershell
# Step 1 — Pull latest changes
cd "C:\Dev\Unreal-MCP"
git pull origin genspark_ai_developer

# Step 2 — Copy updated source files into your project
$REPO    = "C:\Dev\Unreal-MCP"
$PROJECT = "C:\Users\YourName\Documents\UnrealProjects\MyGame"

Copy-Item -Recurse -Force "$REPO\unreal_plugin\Source\" "$PROJECT\Plugins\UnrealMCP\Source\"

# Step 3 — Rebuild in Visual Studio 2022
#   Open MyGame.sln → Development Editor | Win64 → Ctrl+Shift+B
```

> **Tip:** You do not need to close UE5 before copying source files. You do need to rebuild before the changes take effect.

---

## 11. Remote Access via Playit Tunnel

By default, the plugin only listens on `127.0.0.1:55557` (localhost). If your AI assistant runs in a cloud environment (such as Claude running in a remote sandbox), you need a TCP tunnel so it can reach your local UE5 instance.

### Setup — Playit.gg (free)

1. Go to [playit.gg](https://playit.gg/) and create a free account
2. Download `playit.exe` for Windows
3. Run `playit.exe` and follow the setup wizard
4. In the Playit dashboard, create a new **TCP tunnel** pointing to `localhost:55557`
5. Playit will assign you a public address like `abc-xyz.with.playit.plus:12345`

### Start the tunnel

```powershell
# Run this whenever you want remote AI access to your UE5 instance
"C:\path\to\playit.exe"
```

Keep this window open. The tunnel is active as long as the process runs.

### Test the tunnel

```powershell
# Replace with your actual Playit address and port
python -c "
import socket, json
host = 'your-address.with.playit.plus'
port = 12345
msg = json.dumps({'command': 'get_actors_in_level', 'params': {}}) + '\n'
s = socket.socket()
s.settimeout(10)
s.connect((host, port))
s.sendall(msg.encode())
print(s.recv(65536).decode()[:500])
s.close()
"
```

Expected: JSON response with actor data.

### Configure the Python server to use the tunnel address

The `unreal_mcp_server.py` connects to `127.0.0.1:55557` by default. For remote access, set environment variables before running it:

```powershell
$env:UNREAL_HOST = "your-address.with.playit.plus"
$env:UNREAL_PORT = "12345"
python "C:\Dev\Unreal-MCP\unreal_mcp_server\unreal_mcp_server.py"
```

---

## 12. Troubleshooting

### Plugin doesn't load

| Symptom | Likely cause | Fix |
|---|---|---|
| "Missing modules" dialog on project open | Plugin not yet compiled | Click Yes to rebuild, or compile manually in VS2022 |
| Plugin shows as disabled in Edit → Plugins | Compilation failed | Check VS2022 Output for `error C` lines |
| Port 55557 is closed after UE5 opens | Plugin loaded but crashed | Check Output Log for `LogTemp: Error` near `UnrealMCP` |
| `UnrealEditor-UnrealMCP.dll` missing | Build not completed | Follow Step 5 again |

### AI client can't connect

| Symptom | Fix |
|---|---|
| AI says "I cannot connect to Unreal Engine" | UE5 not open, or port closed — re-check Step 6 |
| AI doesn't show any Unreal tools | Config file path is wrong, or AI client wasn't restarted — re-check Step 8 |
| `JSONDecodeError` or empty response | UE5 is open but a command timed out — try again; check UE5 didn't freeze |

### Python errors

| Error | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'mcp'` | Run `pip install mcp fastmcp` |
| `python: command not found` | Python not on PATH — reinstall Python with "Add to PATH" checked |
| `pip: command not found` | Same as above |

### Build errors

| Error | Fix |
|---|---|
| `MSB3073` (exit code 6) | Scroll up in VS2022 Output panel to find the actual `error C` line |
| `Cannot open source file '...'` | Missing VS workload — add "Game development with C++" in VS Installer |
| Any error after updating the plugin source | Delete `Binaries\` and `Intermediate\` from `Plugins\UnrealMCP\`, then rebuild |

### Finding the UE5 log file

```powershell
# View last 50 lines of the engine log
Get-Content "$env:LOCALAPPDATA\UnrealEngine\5.6\Saved\Logs\Unreal.log" -Tail 50

# Search for all UnrealMCP messages
Select-String -Path "$env:LOCALAPPDATA\UnrealEngine\5.6\Saved\Logs\Unreal.log" -Pattern "UnrealMCP"
```

### Port 55557 already in use

```powershell
# Find what's using the port
netstat -ano | findstr 55557

# Kill the process (replace 1234 with the actual PID)
taskkill /PID 1234 /F
```

---

## 13. Available Tools Reference

### Blueprint Class Operations

| Tool | What it does |
|---|---|
| `create_blueprint` | Create a new Blueprint asset |
| `add_component_to_blueprint` | Add a component (mesh, collider, etc.) |
| `compile_blueprint` | Compile — returns errors/warnings on failure |
| `set_blueprint_property` | Set a variable or property value |
| `set_component_property` | Set a property on a component |
| `set_physics_properties` | Configure physics simulation |

### Graph Inspection

| Tool | What it does |
|---|---|
| `get_blueprint_nodes` | All nodes in a graph with full pin data. Pass `graph_name="*"` for all graphs at once |
| `find_blueprint_nodes` | Filter nodes by type (`event`, `function`, `variable_get/set`, `input_action`, or any class substring) |
| `get_blueprint_graphs` | List all graphs in a Blueprint (EventGraph, functions, macros) |
| `get_node_by_id` | Fast single-node lookup by GUID or object name |

### Graph Editing

| Tool | What it does |
|---|---|
| `connect_blueprint_nodes` | Connect two pins. Returns `connection_verified` to confirm it took effect |
| `disconnect_blueprint_nodes` | Break a connection (all links on a pin, or a specific link) |
| `delete_blueprint_node` | Remove a node and break its connections |
| `set_node_pin_value` | Set a literal default value on an unconnected pin |

### Node Creation

| Tool | What it does |
|---|---|
| `add_blueprint_event_node` | Add an event (BeginPlay, Tick, custom, etc.) |
| `add_blueprint_function_node` | Add any function call node. Supports short names (`K2_GetActorLocation`) and full UE paths (`/Script/Engine.Actor:K2_GetActorLocation`) |
| `add_blueprint_variable_get_node` | Add a variable read node |
| `add_blueprint_variable_set_node` | Add a variable write node |
| `add_blueprint_variable` | Declare a new member variable (Boolean, Integer, Float, Vector, etc.) |
| `add_blueprint_enhanced_input_action_node` | Add an Enhanced Input event node for a `UInputAction` asset |
| `add_blueprint_input_action_node` | Add a legacy Input Action event node |
| `add_blueprint_self_reference` | Add a "Get a reference to self" node |
| `add_blueprint_get_component_node` | Add a component reference node (validates against SCS) |
| `add_blueprint_get_self_component_reference` | Add a component reference node by name |

### Actor / Level Operations

| Tool | What it does |
|---|---|
| `get_actors_in_level` | List every actor in the open level |
| `find_actors_by_name` | Find actors matching a name pattern |
| `spawn_actor` | Spawn an actor at a location |
| `delete_actor` | Remove an actor from the level |
| `set_actor_transform` | Move/rotate/scale an actor |
| `get_actor_properties` | Read an actor's properties |

### Gameplay Framework

| Tool | What it does |
|---|---|
| `create_character_blueprint` | Character with camera and movement |
| `create_game_mode` | GameMode Blueprint |
| `create_player_controller` | PlayerController Blueprint |
| `create_game_instance` | GameInstance Blueprint |
| `create_ai_controller` | AIController Blueprint |
| `create_behavior_tree` | Behavior Tree asset |
| `create_blackboard` | Blackboard asset |

### UI / UMG

| Tool | What it does |
|---|---|
| `create_umg_widget_blueprint` | Create a Widget Blueprint |
| `add_text_block_to_widget` | Add a text element |
| `add_button_to_widget` | Add a button |
| `bind_widget_event` | Bind a button's OnClicked event |
| `add_widget_to_viewport` | Show the widget at runtime |

### Python / Advanced

| Tool | What it does |
|---|---|
| `exec_python` | Run arbitrary Python inside the UE5 editor (full `unreal` module access) |
| `create_input_mapping` | Create a legacy input action mapping |

> For the complete list of all 283 tools, browse the `unreal_mcp_server/tools/` directory. Each `.py` file contains a module of related tools with docstrings.

---

## Architecture Notes

### How the TCP socket works

- The C++ plugin starts a single-threaded TCP server on `127.0.0.1:55557` when UE5 loads
- Each command is a newline-terminated JSON object: `{"command": "...", "params": {...}}\n`
- The plugin executes the command on UE5's game thread (via `AsyncTask(ENamedThreads::GameThread, ...)`) and returns a JSON response
- One command executes at a time; the Python server queues concurrent requests

### Playit tunnel and health-check probes

TCP proxies (Playit, ngrok, etc.) send zero-byte health-check connections periodically. The plugin handles these by polling for data for up to 5 seconds after accepting a connection — if no data arrives, the connection is classified as a probe and closed without blocking real commands.

---

## File Structure

```
Unreal-MCP/
├── README.md                         ← You are here
├── sandbox_ue5cli.py                 ← Standalone CLI for direct command testing
├── pyproject.toml
│
├── unreal_mcp_server/
│   ├── unreal_mcp_server.py          ← MCP server entry point
│   └── tools/
│       ├── node_tools.py             ← Blueprint graph nodes (connect, create, inspect)
│       ├── blueprint_tools.py        ← Blueprint class operations
│       ├── editor_tools.py           ← Actor management, exec_python
│       ├── gameplay_tools.py         ← GameMode, Character, AI, etc.
│       ├── umg_tools.py              ← Widget Blueprints
│       ├── animation_tools.py        ← AnimBP, State Machines
│       ├── ai_tools.py               ← Behavior Trees, Blackboard
│       ├── advanced_node_tools.py    ← Branch, Delay, Math, Timeline
│       ├── communication_tools.py    ← Dispatchers, Interfaces, Casting
│       ├── data_tools.py             ← Structs, Enums, Arrays, DataTables
│       ├── material_tools.py         ← Materials, dynamic materials
│       ├── savegame_tools.py         ← SaveGame, pause, win/lose menus
│       ├── library_tools.py          ← Function/Macro Libraries, Timers
│       ├── procedural_tools.py       ← Construction Script, Splines, ISM
│       ├── vr_tools.py               ← VR pawn, grab, teleport
│       ├── physics_tools.py          ← Physics simulation
│       ├── project_tools.py          ← Input mappings
│       └── variant_tools.py          ← Variant Manager
│
└── unreal_plugin/
    ├── UnrealMCP.uplugin             ← Plugin descriptor
    └── Source/UnrealMCP/
        ├── UnrealMCP.Build.cs
        ├── Public/Commands/
        │   ├── UnrealMCPBlueprintCommands.h
        │   ├── UnrealMCPBlueprintNodeCommands.h
        │   ├── UnrealMCPCommonUtils.h
        │   └── UnrealMCPEditorCommands.h
        └── Private/
            ├── UnrealMCPBridge.cpp   ← Command dispatcher + TCP server init
            ├── MCPServerRunnable.cpp ← TCP accept loop
            └── Commands/
                ├── UnrealMCPBlueprintCommands.cpp
                ├── UnrealMCPBlueprintNodeCommands.cpp
                ├── UnrealMCPCommonUtils.cpp
                └── UnrealMCPEditorCommands.cpp
```

---

## License

Based on [chongdashu/unreal-mcp](https://github.com/chongdashu/unreal-mcp). Extended under the same MIT license.
