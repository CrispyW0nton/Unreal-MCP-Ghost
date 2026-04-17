# Unreal-MCP-Ghost — AI Blueprint Scripting for UE5

Control Unreal Engine 5 programmatically from any AI agent. Write Blueprint logic, create assets, wire nodes, spawn actors, set up AI, animation, UI, and VFX — all without touching the UE5 editor manually. Every AI agent — local or remote — uses the **406 MCP tools** via the Model Context Protocol.

> **Forked from:** [chongdashu/unreal-mcp](https://github.com/chongdashu/unreal-mcp)  
> **Active branch:** `genspark_ai_developer` — all new features and bug fixes live here  
> **MCP tools:** 406 Python tools (local stdio) + 119 C++ plugin commands (all accessible via MCP)  
> **Knowledge base:** 19 markdown files documenting every tool, pattern, and UE5 system  

---

## How It Works

```
  Local AI Clients                         Remote / Cloud AI Agents
  (Claude Desktop, Cursor, Windsurf)       (GenSpark AI Developer, any cloud MCP client)
           │                                            │
           │  MCP stdio transport                       │  MCP SSE transport
           │  (configured in client JSON)               │  (HTTP POST to /sse endpoint)
           ▼                                            ▼
                        unreal_mcp_server.py
                   (MCP server, 406 tools registered)
                                │
                                │  TCP JSON  port 55557
                                │  (via Playit tunnel if UE5 is remote)
                                ▼
                    UnrealMCP C++ Plugin
                    (Editor Subsystem, compiled into your UE5 project)
                                │
                                │  UE5 Editor API (GameThread)
                                ▼
                        Unreal Engine 5
```

**Every AI agent uses the same 406 MCP tools.** The transport layer differs by agent type:

| Agent Type | Transport | How to Configure |
|---|---|---|
| Claude Desktop, Cursor, Windsurf | **stdio** (local) | Add server to client's MCP config JSON (Section 8) |
| GenSpark AI Developer, cloud agents | **SSE** (HTTP) | Run server with `--transport sse`, connect via `/sse` URL (Section 9) |

- **`unreal_mcp_server.py`** — The MCP server. Runs on the developer's machine. All 406 tools are registered here. Supports `stdio`, `sse`, and `streamable-http` transports.
- **`sandbox_ue5cli.py`** — Low-level debug CLI for directly testing the C++ plugin's 119 raw commands. Not intended for normal AI agent use — agents should use MCP tools instead.
- **C++ Plugin** — Receives JSON commands on `localhost:55557`, executes them on UE5's game thread, returns JSON results.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Clone the Repository](#2-clone-the-repository)
3. [Copy the Plugin into Your UE5 Project](#3-copy-the-plugin-into-your-ue5-project)
4. [Generate Visual Studio Project Files](#4-generate-visual-studio-project-files)
5. [Compile the Plugin](#5-compile-the-plugin)
6. [Open UE5 and Verify the Plugin](#6-open-ue5-and-verify-the-plugin)
7. [Install Python Dependencies](#7-install-python-dependencies)
8. [Configure Your AI Client — Local (stdio)](#8-configure-your-ai-client--local-stdio)
9. [Configure for Remote Agents — GenSpark / Cloud (SSE)](#9-configure-for-remote-agents--genspark--cloud-sse)
10. [Test the Connection](#10-test-the-connection)
11. [Keeping the Plugin Up to Date](#11-keeping-the-plugin-up-to-date)
12. [Troubleshooting](#12-troubleshooting)
13. [Available MCP Tools Reference](#13-available-mcp-tools-reference)
14. [AI Agent Onboarding Prompt](#14-ai-agent-onboarding-prompt)

---

## 1. Prerequisites

| Tool | Minimum Version | How to Check | Download |
|---|---|---|---|
| **Unreal Engine** | 5.4 or later (5.6 recommended) | Epic Games Launcher → Library | [epicgames.com](https://www.unrealengine.com/en-US/download) |
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

---

## 2. Clone the Repository

```powershell
git clone https://github.com/CrispyW0nton/Unreal-MCP-Ghost.git "C:\Dev\Unreal-MCP"
cd "C:\Dev\Unreal-MCP"
git checkout genspark_ai_developer
```

> **Use the `genspark_ai_developer` branch.** All bug fixes, new commands, and the knowledge base live here. The `main` branch is the base fork and is not kept up to date.

Verify the clone:
```powershell
dir "C:\Dev\Unreal-MCP\unreal_plugin"
```
Expected: `UnrealMCP.uplugin`, `Source\`

---

## 3. Copy the Plugin into Your UE5 Project

The plugin must live inside your project's `Plugins\` folder.

```powershell
$REPO    = "C:\Dev\Unreal-MCP"
$PROJECT = "C:\Users\YourName\Documents\UnrealProjects\MyGame"

New-Item -ItemType Directory -Force -Path "$PROJECT\Plugins\UnrealMCP"
Copy-Item -Recurse -Force "$REPO\unreal_plugin\*" "$PROJECT\Plugins\UnrealMCP\"
```

Verify:
```powershell
dir "$PROJECT\Plugins\UnrealMCP"
```
Expected: `Source\`, `UnrealMCP.uplugin`

> **Stale build artifacts?** If you see a leftover `Binaries\` folder from a previous failed build, delete it before compiling:
> ```powershell
> Stop-Process -Name "UnrealEditor" -Force -ErrorAction SilentlyContinue
> Start-Sleep 2
> Remove-Item -Recurse -Force "$PROJECT\Plugins\UnrealMCP\Binaries"
> Remove-Item -Recurse -Force "$PROJECT\Plugins\UnrealMCP\Intermediate"
> ```

---

## 4. Generate Visual Studio Project Files

**Option A — Right-click (simplest):**
1. Open File Explorer and navigate to your project folder
2. Right-click `YourProject.uproject`
3. Click **"Generate Visual Studio project files"**
4. Wait for the small console window to close

**Option B — Command line:**
```powershell
$PROJECT  = "C:\Users\YourName\Documents\UnrealProjects\MyGame"
$UPROJECT = "$PROJECT\MyGame.uproject"
$UE_VER   = "5.6"   # Change to match your installed version

& "C:\Program Files\Epic Games\UE_$UE_VER\Engine\Build\BatchFiles\GenerateProjectFiles.bat" `
    -project="$UPROJECT" -game -rocket
```

---

## 5. Compile the Plugin

1. Double-click `MyGame.sln`
2. Set **Configuration:** `Development Editor` and **Platform:** `Win64`
3. Press **`Ctrl+Shift+B`** (Build Solution)

First compile: **5–20 minutes**. Incremental rebuilds: under 30 seconds.

**Success:**
```
========== Build: 1 succeeded, 0 failed, 0 up-to-date, 0 skipped ==========
```

**Verify the DLL exists:**
```
MyGame\Plugins\UnrealMCP\Binaries\Win64\UnrealEditor-UnrealMCP.dll
```

### Common Compile Errors

| Error | Fix |
|---|---|
| `'Game development with C++' workload not installed` | VS Installer → Modify → add the workload |
| `Cannot open include file: '...'` | Re-pull and re-copy the `Source\` folder |
| `MSB3073` exit code 6 with no error shown | Scroll up in the VS Output panel for the actual `error C` line |
| Any error after updating the plugin | Delete `Binaries\` and `Intermediate\` from `Plugins\UnrealMCP\`, then rebuild |

---

## 6. Open UE5 and Verify the Plugin

1. Double-click your `.uproject`
2. If a **"Missing modules — rebuild now?"** dialog appears, click **Yes**
3. Wait for shader compilation (progress bar, bottom-right)

### Confirm the plugin is running

**In UE5:** Edit → Plugins → search `UnrealMCP` → should show ✅ enabled.

**In Output Log** (Window → Output Log):
```
LogTemp: UnrealMCPBridge: Server started on 127.0.0.1:55557
```

**From PowerShell:**
```powershell
python -c "
import socket
s = socket.socket()
s.settimeout(2)
result = s.connect_ex(('127.0.0.1', 55557))
s.close()
print('PLUGIN RUNNING' if result == 0 else 'PLUGIN NOT RUNNING — port 55557 is closed')
"
```

---

## 7. Install Python Dependencies

```powershell
cd "C:\Dev\Unreal-MCP"
pip install mcp fastmcp uvicorn
```

`uvicorn` is required for SSE/HTTP transport (remote agents). `mcp` and `fastmcp` are required for all transports.

Verify:
```powershell
python -c "import mcp; import fastmcp; import uvicorn; print('OK')"
```

---

## 8. Configure Your AI Client — Local (stdio)

For **local** AI clients (Claude Desktop, Cursor, Windsurf), the server uses the **stdio** transport. No extra setup is needed beyond registering the server in your client's config.

### Claude Desktop

Edit `%APPDATA%\Claude\claude_desktop_config.json`:

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

### Cursor

Edit `%APPDATA%\Cursor\User\mcp.json`:

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

### Any other local MCP client

Point it to: `python "C:\Dev\Unreal-MCP\unreal_mcp_server\unreal_mcp_server.py"`

**Restart your AI client** after saving the config.

---

## 9. Configure for Remote Agents — GenSpark / Cloud (SSE)

Remote AI agents (GenSpark AI Developer and any cloud-based MCP client) cannot use stdio. Instead, run the MCP server in **SSE mode** — it becomes an HTTP server that remote agents connect to over a public URL.

### Step 1 — Set up Playit tunnels

You need **two Playit tunnels** running simultaneously:

| Tunnel | Points to | Purpose |
|---|---|---|
| **Tunnel 1** | `localhost:55557` | UE5 C++ plugin — lets the MCP server reach UE5 |
| **Tunnel 2** | `localhost:8000` | MCP HTTP server — lets GenSpark reach the MCP server |

In the [Playit dashboard](https://playit.gg/), create a second **TCP tunnel** pointing to `localhost:8000`. Note the new public address it gives you (e.g. `your-mcp.with.playit.plus:54321`).

### Step 2 — Start the MCP server in SSE mode

```powershell
cd "C:\Dev\Unreal-MCP"
python unreal_mcp_server\unreal_mcp_server.py `
    --transport sse `
    --mcp-host 0.0.0.0 `
    --mcp-port 8000 `
    --unreal-host YOUR-TUNNEL-1-HOST.with.playit.plus `
    --unreal-port YOUR-TUNNEL-1-PORT
```

You should see:
```
[UnrealMCP] SSE server listening on http://0.0.0.0:8000/sse
[UnrealMCP] UE5 plugin target: YOUR-TUNNEL-1-HOST.with.playit.plus:PORT
```

The MCP server is now reachable at:
```
http://your-mcp.with.playit.plus:54321/sse
```

### Step 3 — Connect GenSpark to the MCP server

In the GenSpark AI Developer interface, configure the MCP server URL to:
```
http://your-mcp.with.playit.plus:54321/sse
```

GenSpark will connect via MCP SSE and automatically discover all 406 tools. See [Section 14](#14-ai-agent-onboarding-prompt) for the onboarding prompt to paste into your first GenSpark session.

### Environment variable alternative

```powershell
$env:UNREAL_HOST    = "YOUR-TUNNEL-1-HOST.with.playit.plus"
$env:UNREAL_PORT    = "YOUR-TUNNEL-1-PORT"
$env:MCP_SERVER_HOST = "0.0.0.0"
$env:MCP_SERVER_PORT = "8000"
python unreal_mcp_server\unreal_mcp_server.py --transport sse
```

### Streamable-HTTP (modern clients)

For clients supporting the MCP 2025-03-26 spec, use `--transport streamable-http`. The endpoint will be at `/mcp` instead of `/sse`.

---

## 10. Test the Connection

### Local agents — via AI client

Open a new chat and send:
> "List all the actors in the current Unreal Engine level."

The AI calls `get_actors_in_level` and returns actor data.

### Remote agents — verify SSE endpoint

```powershell
# Check the SSE endpoint is reachable
curl -N http://your-mcp.with.playit.plus:54321/sse
```

Expected: an SSE stream starting with `event: endpoint`.

### Low-level plugin test (debug only — agents should use MCP tools)

```powershell
# Test the raw C++ plugin commands directly — for developer debugging only
# AI agents should NOT use this; use MCP tool calls instead
cd "C:\Dev\Unreal-MCP"
python sandbox_ue5cli.py get_actors_in_level '{}'
```

---

## 11. Keeping the Plugin Up to Date

```powershell
# Pull the latest changes (conflict-proof)
cd "C:\Dev\Unreal-MCP"
git fetch origin
git reset --hard origin/genspark_ai_developer

# Copy updated source into your project
$REPO    = "C:\Dev\Unreal-MCP"
$PROJECT = "C:\Users\YourName\Documents\UnrealProjects\MyGame"
Copy-Item -Recurse -Force "$REPO\unreal_plugin\Source\" "$PROJECT\Plugins\UnrealMCP\Source\"

# Rebuild in Visual Studio 2022
# Open MyGame.sln → Development Editor | Win64 → Ctrl+Shift+B
```

> Use `git reset --hard` instead of `git pull` — it is always conflict-free and gives you a clean copy of the latest remote state.

---

## 12. Troubleshooting

### Plugin doesn't load

| Symptom | Fix |
|---|---|
| "Missing modules" dialog on project open | Click Yes to rebuild, or compile manually in VS2022 |
| Plugin shows as disabled in Edit → Plugins | Compilation failed — check VS2022 Output for `error C` lines |
| Port 55557 closed after UE5 opens | Plugin loaded but crashed — check Output Log for `LogTemp: Error` near `UnrealMCP` |
| `UnrealEditor-UnrealMCP.dll` missing | Build not completed — follow Step 5 again |

### AI client can't connect

| Symptom | Fix |
|---|---|
| AI says "I cannot connect to Unreal Engine" | UE5 not open, or port 55557 closed — re-check Step 6 |
| AI doesn't show any Unreal tools | Config file path wrong, or AI client not restarted — re-check Step 8 |
| `JSONDecodeError` or empty response | Command timed out — try again; check UE5 didn't freeze |

### Python errors

| Error | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'mcp'` | Run `pip install mcp fastmcp` |
| `python: command not found` | Python not on PATH — reinstall Python with "Add to PATH" checked |

### Finding the UE5 log

```powershell
# Last 50 lines
Get-Content "$env:LOCALAPPDATA\UnrealEngine\5.6\Saved\Logs\Unreal.log" -Tail 50

# All UnrealMCP messages
Select-String -Path "$env:LOCALAPPDATA\UnrealEngine\5.6\Saved\Logs\Unreal.log" -Pattern "UnrealMCP"
```

### Port 55557 already in use

```powershell
netstat -ano | findstr 55557
# Kill the process (replace 1234 with the actual PID shown)
taskkill /PID 1234 /F
```

---

## 13. Available MCP Tools Reference

The MCP server exposes **406 Python tools** across 33 modules (31 tool modules including diagnostics_tools + repair_tools + 2 skill modules). All tools are called by the AI agent via its MCP connection — local agents call them directly, remote agents call them via SSE. The 406 Python tools cover all 20 chapters of "Blueprints Visual Scripting for Unreal Engine 5" and internally translate to 119 C++ plugin commands.

**Phase 4 / V6 additions (Verification & Diagnostics):**
- `tools/diagnostics_tools.py` — 10 tools: bp_get_compile_diagnostics, bp_validate_blueprint, bp_validate_graph, bp_find_disconnected_pins, bp_find_unreachable_nodes, bp_find_unused_variables, bp_find_orphaned_nodes, bp_run_post_mutation_verify, mat_get_compile_diagnostics, mat_validate_material
- `tools/repair_tools.py` — 3 tools: bp_repair_exec_chain, bp_remove_orphaned_nodes, bp_set_pin_default
- `skills/repair_broken_blueprint/` — skill_repair_broken_blueprint (deterministic repair loop)
- All diagnostics return structured JSON with severity/category/code/auto_repairable fields

> **For AI agents:** Call tools by name through your MCP interface. See Section 14 for the onboarding prompt.
>
> **For low-level debugging only:** The raw C++ plugin commands can be tested directly via `python3 sandbox_ue5cli.py <command_name> '<json_params>'`

### Actor / Level Commands
| Command | Key Parameters |
|---|---|
| `get_actors_in_level` | `{}` |
| `find_actors_by_name` | `name` |
| `create_actor` / `spawn_actor` | `type`, `name`, `location`, `rotation` |
| `spawn_blueprint_actor` | `blueprint_path`, `name`, `location` |
| `delete_actor` | `name` |
| `set_actor_transform` | `name`, `location`, `rotation`, `scale` |
| `get_actor_properties` | `name` |
| `set_actor_property` | `name`, `property`, `value` |
| `focus_viewport` | `location` |
| `take_screenshot` | `filename` |
| `exec_python` | `code` — runs arbitrary Python inside UE5 with full `unreal` module access |

### Blueprint Class Commands
| Command | Key Parameters |
|---|---|
| `create_blueprint` | `name`, `parent_class`, `[path]` — defaults to `/Game/Blueprints/`; use `exec_python` for custom paths |
| `compile_blueprint` | `blueprint_name` |
| `set_blueprint_property` | `blueprint_name`, `property_name`, `value` |
| `set_blueprint_variable_default` | `blueprint_name`, `variable_name`, `default_value` |
| `set_pawn_properties` | `blueprint_name`, `[auto_possess_ai]` |
| `set_blueprint_ai_controller` | `blueprint_name`, `ai_controller_class`, `auto_possess_ai` |
| `set_blueprint_parent_class` | `blueprint_name`, `new_parent_class` |
| `add_component_to_blueprint` | `blueprint_name`, `component_type`, `component_name` |
| `set_component_property` | `blueprint_name`, `component_name`, `property_name`, `value` |
| `set_physics_properties` | `blueprint_name`, `component_name`, `simulate_physics`, `[gravity]` |
| `set_static_mesh_properties` | `blueprint_name`, `component_name`, `static_mesh_path` |
| `spawn_blueprint_actor` | `blueprint_path`, `name`, `location` |

### Blueprint Introspection
| Command | Key Parameters |
|---|---|
| `get_blueprint_nodes` | `blueprint_name`, `graph_name` — use `"*"` for all graphs |
| `find_blueprint_nodes` | `blueprint_name`, `graph_name`, `[node_type]`, `[node_name]` |
| `get_blueprint_graphs` | `blueprint_name` |
| `get_node_by_id` | `blueprint_name`, `graph_name`, `node_id` |
| `get_blueprint_variable_defaults` | `blueprint_name`, `[variable_name]` |
| `get_blueprint_variables` | `blueprint_name`, `[category]` — lists all variables with type, default, exposure |
| `get_blueprint_functions` | `blueprint_name` — lists all user-defined functions with typed I/O |
| `get_blueprint_components` | `blueprint_name` |

### Blueprint Variable Commands
| Command | Key Parameters |
|---|---|
| `add_blueprint_variable` | `blueprint_name`, `variable_name`, `variable_type`, `[default_value]`, `[is_exposed]` |
| `add_blueprint_variable_get_node` | `blueprint_name`, `graph_name`, `variable_name`, `node_position` |
| `add_blueprint_variable_set_node` | `blueprint_name`, `graph_name`, `variable_name`, `node_position` |

**Supported `variable_type` values:** `Boolean`, `Integer`, `Integer64`, `Float`, `Double`, `String`, `Name`, `Text`, `Vector`, `Rotator`, `Transform`, `Object/<ClassName>`

### Node Creation Commands
| Command | Key Parameters |
|---|---|
| `add_blueprint_event_node` | `blueprint_name`, `graph_name`, `event_name`, `node_position` |
| `add_blueprint_custom_event_node` | `blueprint_name`, `graph_name`, `event_name`, `node_position` |
| `add_blueprint_function_node` | `blueprint_name`, `graph_name`, `function_name`, `node_position`, `[target_class]` |
| `add_blueprint_function_with_pins` | `blueprint_name`, `function_name`, `[inputs:[{name,type}]]`, `[outputs:[{name,type}]]` |
| `add_blueprint_cast_node` | `blueprint_name`, `graph_name`, `cast_target_class`, `node_position` |
| `add_blueprint_branch_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_blueprint_sequence_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_blueprint_for_loop_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_blueprint_for_each_loop_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_blueprint_do_once_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_blueprint_gate_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_blueprint_flip_flop_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_blueprint_switch_on_int_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_blueprint_spawn_actor_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_blueprint_self_reference` | `blueprint_name`, `graph_name`, `node_position` |
| `add_blueprint_get_component_node` | `blueprint_name`, `graph_name`, `component_name`, `node_position` |
| `add_blueprint_get_self_component_reference` | `blueprint_name`, `graph_name`, `component_name`, `node_position` |
| `add_blueprint_enhanced_input_action_node` | `blueprint_name`, `graph_name`, `action_asset` (full path), `node_position` |
| `add_blueprint_input_action_node` | `blueprint_name`, `graph_name`, `action_name`, `node_position` |
| `add_blueprint_comment_node` | `blueprint_name`, `graph_name`, `comment_text`, `node_position`, `[size]` |
| `add_event_dispatcher` | `blueprint_name`, `dispatcher_name` |
| `add_custom_function` | `blueprint_name`, `function_name` |
| `add_blueprint_set_component_property` | `blueprint_name`, `graph_name`, `component_name`, `property_name`, `node_position` |

### Node Editing Commands
| Command | Key Parameters |
|---|---|
| `connect_blueprint_nodes` | `blueprint_name`, `graph_name`, `source_node_id`, `target_node_id`, `source_pin`, `target_pin` |
| `disconnect_blueprint_nodes` | `blueprint_name`, `graph_name`, `source_node_id`, `target_node_id`, `source_pin`, `target_pin` |
| `delete_blueprint_node` | `blueprint_name`, `graph_name`, `node_id` |
| `set_node_pin_value` | `blueprint_name`, `graph_name`, `node_id`, `pin_name`, `value` |
| `set_spawn_actor_class` | `blueprint_name`, `graph_name`, `node_id`, `class_path` |
| `move_blueprint_node` | `blueprint_name`, `graph_name`, `node_id`, `node_position` |

### Extended Flow Control / Event Nodes (via Extended Commands)
| Command | Key Parameters |
|---|---|
| `add_branch_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_sequence_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_do_once_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_do_n_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_gate_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_flipflop_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_while_loop_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_for_each_loop_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_switch_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_multigate_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_timeline_node` | `blueprint_name`, `graph_name`, `timeline_name`, `node_position` |
| `add_cast_node` | `blueprint_name`, `graph_name`, `cast_target_class`, `node_position` |
| `add_variable_get_node` | `blueprint_name`, `graph_name`, `variable_name`, `node_position` |
| `add_variable_set_node` | `blueprint_name`, `graph_name`, `variable_name`, `node_position` |
| `add_custom_event` | `blueprint_name`, `graph_name`, `event_name`, `node_position` |
| `add_blend_space_node` | `blueprint_name`, `graph_name`, `blend_space_path`, `node_position` |
| `add_macro_node` | `blueprint_name`, `graph_name`, `macro_name`, `node_position` |
| `add_interface_function_node` | `blueprint_name`, `graph_name`, `interface_name`, `function_name`, `node_position` |
| `add_custom_macro` | `blueprint_name`, `macro_name` |
| `bind_event_to_dispatcher` | `blueprint_name`, `graph_name`, `dispatcher_name`, `handler_name`, `node_position` |
| `unbind_event_from_dispatcher` | `blueprint_name`, `graph_name`, `dispatcher_name`, `node_position` |
| `call_event_dispatcher` | `blueprint_name`, `graph_name`, `dispatcher_name`, `node_position` |
| `call_custom_event` | `blueprint_name`, `graph_name`, `event_name`, `node_position` |

### AI / Behavior Tree Commands
| Command | Key Parameters |
|---|---|
| `create_behavior_tree` | `name`, `path` |
| `create_blackboard` | `name`, `path`, `[keys:[{name,type}]]` — add all keys at creation time |
| `set_behavior_tree_blackboard` | `behavior_tree_name`, `blackboard_name` ⚠️ asset names only, not paths |
| `setup_navmesh` | `[extent:{x,y,z}]`, `[location:{x,y,z}]`, `[rebuild:true]` |

**Blackboard key types:** `Vector`, `Bool`, `Float`, `Int`, `String`, `Object`

### Animation Commands
| Command | Key Parameters |
|---|---|
| `create_animation_blueprint` | `name`, `path`, `[skeleton_path]` |
| `add_state_machine` | `blueprint_name`, `name` |
| `add_animation_state` | `blueprint_name`, `state_machine_name`, `state_name` |
| `add_state_transition` | `blueprint_name`, `state_machine_name`, `from_state`, `to_state` |
| `set_animation_for_state` | `blueprint_name`, `state_machine_name`, `state_name`, `animation_path` |
| `add_anim_notify` | `animation_path`, `notify_name`, `time`, `[notify_type]`, `[notify_state_duration]` |

### Data Asset Commands
| Command | Key Parameters |
|---|---|
| `create_struct` | `name`, `path` |
| `create_enum` | `name`, `path` |
| `create_data_table` | `name`, `path`, `row_struct` ⚠️ use `row_struct` not `row_struct_path` |
| `create_blueprint_interface` | `name`, `path` |
| `create_blueprint_macro_library` | `name`, `path` |
| `implement_blueprint_interface` | `blueprint_name`, `interface_name` ⚠️ asset name only |
| `set_blueprint_parent_class` | `blueprint_name`, `new_parent_class` |

### Input Commands
| Command | Key Parameters |
|---|---|
| `create_enhanced_input_action` | `name`, `path` |
| `create_input_mapping_context` | `name`, `path` |
| `add_input_mapping` | `context_name`, `action_name`, `key` |
| `create_input_mapping` | `name`, `path` (legacy) |

### UMG / Widget Commands
| Command | Key Parameters |
|---|---|
| `create_umg_widget_blueprint` | `name`, `path` |
| `add_text_block_to_widget` | `widget_name`, `text_block_name`, `text`, `position` |
| `add_button_to_widget` | `widget_name`, `button_name`, `position` |
| `bind_widget_event` | `widget_name`, `widget_element_name`, `event_name`, `function_name` |
| `set_text_block_binding` | `widget_name`, `text_block_name`, `binding_function` |
| `add_widget_to_viewport` | `widget_name` |

### VFX / Material / Sequencer Commands
| Command | Key Parameters |
|---|---|
| `add_niagara_component` | `blueprint_name`, `component_name`, `[niagara_system_path]` |
| `add_spawn_niagara_at_location_node` | `blueprint_name`, `graph_name`, `niagara_system_path`, `node_position` |
| `set_material_instance_parameter` | `material_instance_path`, `parameter_name`, `parameter_type`, `value` |
| `set_sequencer_track` | `sequence_path`, `actor_name`, `track_type`, `[keyframes:[{time,location,rotation,scale}]]` |

### Level / World Commands
| Command | Key Parameters |
|---|---|
| `set_game_mode_for_level` | `game_mode_name` ⚠️ asset name only, NOT the full content path |

---

### ⚠️ Critical Parameter Gotchas

| Command | Common Mistake | Correct |
|---|---|---|
| `set_game_mode_for_level` | `"game_mode_path": "/Game/.../BP_X"` | `"game_mode_name": "BP_X"` |
| `implement_blueprint_interface` | `"interface_path": "/Game/.../BPI_X"` | `"interface_name": "BPI_X"` |
| `set_behavior_tree_blackboard` | `"blackboard_path": "/Game/.../BB_X"` | `"blackboard_name": "BB_X"` |
| `create_data_table` | `"row_struct_path": "..."` | `"row_struct": "..."` |
| `add_blueprint_enhanced_input_action_node` | Short name `"IA_Jump"` | Full path `"/Game/.../IA_Jump"` |
| `connect_blueprint_nodes` | Hardcoding pin names | Always call `get_blueprint_nodes` first to read exact pin names |

---

### Blueprint Parent Class Quick Reference

When calling `create_blueprint`, use these exact C++ class names:

| Blueprint Purpose | `parent_class` |
|---|---|
| Static props, triggers, managers | `Actor` |
| Simple controllable pawn | `Pawn` |
| Walking character (player or NPC) | `Character` |
| Player input + camera | `PlayerController` |
| AI decision making | `AIController` |
| Game rules (server authority) | `GameModeBase` |
| Persistent data across levels | `GameInstance` |
| Replicated match state | `GameStateBase` |
| Per-player persistent state | `PlayerState` |
| Disk save file | `SaveGame` |
| Reusable logic (no transform) | `ActorComponent` |
| Reusable with transform | `SceneComponent` |
| Global static utilities | `BlueprintFunctionLibrary` |
| Custom BT action | `BTTask_BlueprintBase` |
| Custom BT condition | `BTDecorator_BlueprintBase` |
| Custom BT periodic logic | `BTService_BlueprintBase` |

> For Widget Blueprints, Behavior Trees, Blackboards, and Animation Blueprints — use `exec_python` with the appropriate factory. See the [knowledge base](knowledge_base/12_MCP_TOOL_USAGE_GUIDE.md) for examples.

---

## 14. AI Agent Onboarding Prompt

**Use this prompt when starting any new AI developer session** (GenSpark, Claude, Cursor, or any MCP-connected agent) for any UE5 project using this plugin.

Every AI agent — local or remote — uses the same 406 MCP tools. There is **no separate "cloud mode"** or special CLI interface; the MCP connection (stdio for local, SSE for remote) is the one and only interface.

The full prompt is also saved at [`knowledge_base/AI_DEVELOPER_ONBOARDING_PROMPT.md`](knowledge_base/AI_DEVELOPER_ONBOARDING_PROMPT.md). Copy the block below and paste it as your first message. Replace the `[BRACKETED]` placeholders in Section 9 with your project's specifics.

---

```
You are an AI developer working on an Unreal Engine 5 project using the Unreal-MCP-Ghost plugin.
Read this entire prompt carefully before taking any action.

═══════════════════════════════════════════════
0. HOW YOU ARE CONNECTED (READ THIS FIRST)
═══════════════════════════════════════════════

You interact with Unreal Engine EXCLUSIVELY THROUGH MCP TOOL CALLS — the same tool-call
interface you use for everything else. There is no shell, no CLI script to run, no raw TCP
socket to manage. The MCP server handles all communication with UE5 on your behalf.

You have 406 MCP tools available. Call them directly by name, e.g.:
  get_actors_in_level()
  create_blueprint(name="BP_MyActor", parent_class="Actor")
  compile_blueprint(blueprint_name="BP_MyActor")

Connection architecture:
  You (AI agent)
    │  MCP tool calls  ← this is how YOU interact with everything
    ▼
  unreal_mcp_server.py          ← MCP server on the developer's machine
    │                              Running in SSE mode for remote agents:
    │                              python unreal_mcp_server.py --transport sse
    │                                --mcp-host 0.0.0.0 --mcp-port 8000
    │                                --unreal-host <playit-address>
    │                                --unreal-port <playit-port>
    │  TCP JSON  port 55557  (via Playit tunnel if UE5 is on a remote machine)
    ▼
  UnrealMCP C++ Plugin          ← compiled into UE5, listening on localhost:55557
    │  UE5 Editor API (GameThread)
    ▼
  Unreal Engine 5

The MCP server AND UE5 must both be running before any tool calls will work.

═══════════════════════════════════════════════
1. VERIFY THE CONNECTION — ALWAYS DO THIS FIRST
═══════════════════════════════════════════════

Before doing anything else, call:
  get_actors_in_level()

  ✅ Returns a list of actors → connected, proceed.
  ❌ Returns a connection error → STOP. Tell the user:
     "The MCP server cannot reach the UnrealMCP plugin. Please confirm:
      1. UE5 is open with the UnrealMCP plugin enabled
         (Output Log should show 'Server started on 127.0.0.1:55557')
      2. The MCP server is running:
         python unreal_mcp_server.py --transport sse --unreal-host <addr> --unreal-port <port>
      3. The Playit tunnel for UE5 (port 55557) is active"

Check engine version:
  exec_python(code="import unreal; print(unreal.SystemLibrary.get_engine_version())")

Count existing assets:
  exec_python(code="import unreal\nassets=unreal.EditorAssetLibrary.list_assets('/Game',recursive=True,include_folder=False)\nprint(len(assets),'assets found')")

═══════════════════════════════════════════════
2. MANDATORY RULES — READ BEFORE EVERY ACTION
═══════════════════════════════════════════════

1. CALL MCP TOOLS ONLY. You interact with UE5 exclusively through MCP tool calls.
   Do not attempt to run shell commands. All 406 tools are available directly.

2. NEVER invent a tool name. If unsure whether a tool exists, check Section 4.
   Use exec_python as a fallback for anything not covered by a dedicated tool.

3. NEVER guess a parameter name. Wrong parameter names silently fail with no error.

4. ALWAYS get node IDs before connecting nodes. After adding nodes, call get_blueprint_nodes
   to retrieve actual GUIDs, then use those in connect_blueprint_nodes. Never hardcode GUIDs.

5. ALWAYS compile after node changes. After any add_*_node + connect_blueprint_nodes session,
   call compile_blueprint. An uncompiled Blueprint is silently broken at runtime.

6. USE exec_python for assets in custom project folders. The create_blueprint tool
   hardcodes /Game/Blueprints/. For all project-specific paths, use exec_python with
   AssetToolsHelpers.get_asset_tools().

7. MULTIPLY per-frame values by Delta Seconds. Any value applied on Event Tick MUST be
   multiplied by DeltaSeconds. Skipping this breaks the game at non-60fps framerates.

8. ALWAYS call SpawnDefaultController for runtime-spawned AI. Any AI Pawn/Character
   spawned via Spawn Actor from Class at runtime needs:
   → Return Value → SpawnDefaultController

9. ALWAYS check validity before using references. After any Cast or Get, wire the
   Cast Failed / invalid path to a stop node. Never silently continue on null.

10. STOP and report missing assets. If an asset that should exist doesn't, stop and
    tell the user exactly which asset is missing. Do NOT invent substitute paths.

11. USE asset names, NOT full paths, for name-based commands.
    implement_blueprint_interface → interface_name="BPI_X"  (not the full path)
    set_game_mode_for_level       → game_mode_name="BP_X"   (not the full path)
    set_behavior_tree_blackboard  → blackboard_name="BB_X"  (not the full path)
    create_data_table             → row_struct="ST_X"       (not row_struct_path)

12. ALWAYS query the knowledge base before implementing any system. The knowledge base
    contains authoritative parameter names, patterns, and gotchas sourced from 4 UE5
    textbooks (1,626 pages). Never implement from memory alone.
    - Before AI/BT work    → get_knowledge_base("ai")
    - Before animation     → get_knowledge_base("animation")
    - Before UI/HUD        → get_knowledge_base("ui")
    - Before gameplay      → get_knowledge_base("gameplay")
    - Before materials     → get_knowledge_base("materials")
    - Before input system  → get_knowledge_base("input")
    - Before data/structs  → get_knowledge_base("data")
    - Before communication → get_knowledge_base("communication")
    - Unknown topic?       → list_knowledge_base_topics() then search_knowledge_base("your term")

═══════════════════════════════════════════════
3. KNOWN PARAMETER GOTCHAS
═══════════════════════════════════════════════

  set_game_mode_for_level         → game_mode_name="BP_X"         NOT game_mode_path
  implement_blueprint_interface   → interface_name="BPI_X"         NOT interface_path
  set_behavior_tree_blackboard    → blackboard_name="BB_X"         NOT blackboard_path
  create_data_table               → row_struct="ST_X"              NOT row_struct_path
  add_blueprint_enhanced_input_action_node → action_asset="/Game/.../IA_X"  FULL path required
  connect_blueprint_nodes         → always call get_blueprint_nodes first for exact pin names

═══════════════════════════════════════════════
4. COMPLETE TOOL REFERENCE (406 TOOLS)
═══════════════════════════════════════════════

ACTOR / LEVEL
  get_actors_in_level()
  find_actors_by_name(name="BP_MyActor")
  spawn_actor(name="MyActor", type="Actor", location={"x":0,"y":0,"z":0})
  spawn_blueprint_actor(blueprint_name="BP_X", actor_name="MyX", location={"x":0,"y":0,"z":0})
  delete_actor(name="MyActor")
  set_actor_transform(name="MyActor", location={"x":0,"y":0,"z":0}, rotation={"pitch":0,"yaw":0,"roll":0}, scale={"x":1,"y":1,"z":1})
  get_actor_properties(name="MyActor")
  set_actor_property(name="MyActor", property="bHidden", value="false")
  focus_viewport(location={"x":0,"y":0,"z":0})
  take_screenshot(filename="screenshot_01")
  exec_python(code="import unreal\nprint('hello')")

BLUEPRINT CLASS
  create_blueprint(name="BP_MyActor", parent_class="Actor", path="/Game/Blueprints")
  compile_blueprint(blueprint_name="BP_MyActor")
  set_blueprint_property(blueprint_name="BP_X", property_name="bReplicates", value="true")
  set_blueprint_variable_default(blueprint_name="BP_X", variable_name="Health", default_value="100.0")
  set_pawn_properties(blueprint_name="BP_X", auto_possess_ai="Placed in World")
  set_blueprint_ai_controller(blueprint_name="BP_X", ai_controller_class="BP_AIController", auto_possess_ai="Placed in World")
  set_blueprint_parent_class(blueprint_name="BP_X", new_parent_class="Character")
  add_component_to_blueprint(blueprint_name="BP_X", component_type="StaticMeshComponent", component_name="Mesh")
  set_component_property(blueprint_name="BP_X", component_name="Mesh", property_name="CastShadow", value="true")
  set_physics_properties(blueprint_name="BP_X", component_name="Mesh", simulate_physics=True)
  set_static_mesh_properties(blueprint_name="BP_X", component_name="Mesh", static_mesh_path="/Game/.../SM_X")
  set_collision_settings(blueprint_name="BP_X", component_name="Mesh", collision_preset="BlockAll")
  add_niagara_component(blueprint_name="BP_X", component_name="FX", niagara_system_path="/Game/.../NS_X")

BLUEPRINT INTROSPECTION
  get_blueprint_nodes(blueprint_name="BP_X", graph_name="EventGraph")
  get_blueprint_nodes(blueprint_name="BP_X", graph_name="*")   ← all graphs at once
  find_blueprint_nodes(blueprint_name="BP_X", graph_name="EventGraph", node_type="event")
  get_blueprint_graphs(blueprint_name="BP_X")
  get_node_by_id(blueprint_name="BP_X", graph_name="EventGraph", node_id="GUID-HERE")
  get_blueprint_variables(blueprint_name="BP_X")
  get_blueprint_variables(blueprint_name="BP_X", category="Combat")
  get_blueprint_functions(blueprint_name="BP_X")
  get_blueprint_variable_defaults(blueprint_name="BP_X")
  get_blueprint_components(blueprint_name="BP_X")

VARIABLES
  add_blueprint_variable(blueprint_name="BP_X", variable_name="Health", variable_type="Float", default_value="100.0", is_exposed=True)
  add_blueprint_variable_get_node(blueprint_name="BP_X", graph_name="EventGraph", variable_name="Health", node_position={"x":200,"y":0})
  add_blueprint_variable_set_node(blueprint_name="BP_X", graph_name="EventGraph", variable_name="Health", node_position={"x":400,"y":0})
  add_array_variable(blueprint_name="BP_X", variable_name="Inventory", element_type="Object/BP_Item")
  add_map_variable(blueprint_name="BP_X", variable_name="Stats", key_type="String", value_type="Float")
  add_set_variable(blueprint_name="BP_X", variable_name="VisitedRooms", element_type="Integer")

  Supported variable_type values:
    Boolean, Integer, Integer64, Float, Double, String, Name, Text,
    Vector, Rotator, Transform, Object/<ClassName>

NODE CREATION
  add_blueprint_event_node(blueprint_name="BP_X", graph_name="EventGraph", event_name="ReceiveBeginPlay", node_position={"x":0,"y":0})
  add_blueprint_custom_event_node(blueprint_name="BP_X", graph_name="EventGraph", event_name="OnHealthChanged", node_position={"x":0,"y":200})
  add_blueprint_function_node(blueprint_name="BP_X", graph_name="EventGraph", function_name="K2_GetActorLocation", node_position={"x":200,"y":0})
  add_blueprint_function_with_pins(blueprint_name="BP_X", function_name="TakeDamage", inputs=[{"name":"DamageAmount","type":"Float"}], outputs=[{"name":"NewHealth","type":"Float"}])
  add_blueprint_cast_node(blueprint_name="BP_X", graph_name="EventGraph", cast_target_class="BP_MyCharacter", node_position={"x":400,"y":0})
  add_blueprint_branch_node(blueprint_name="BP_X", graph_name="EventGraph", node_position={"x":600,"y":0})
  add_blueprint_sequence_node(blueprint_name="BP_X", graph_name="EventGraph", node_position={"x":200,"y":0})
  add_blueprint_for_loop_node(blueprint_name="BP_X", graph_name="EventGraph", node_position={"x":200,"y":0})
  add_blueprint_for_each_loop_node(blueprint_name="BP_X", graph_name="EventGraph", node_position={"x":200,"y":0})
  add_blueprint_do_once_node(blueprint_name="BP_X", graph_name="EventGraph", node_position={"x":200,"y":0})
  add_blueprint_gate_node(blueprint_name="BP_X", graph_name="EventGraph", node_position={"x":200,"y":0})
  add_blueprint_flip_flop_node(blueprint_name="BP_X", graph_name="EventGraph", node_position={"x":200,"y":0})
  add_blueprint_switch_on_int_node(blueprint_name="BP_X", graph_name="EventGraph", node_position={"x":200,"y":0})
  add_blueprint_spawn_actor_node(blueprint_name="BP_X", graph_name="EventGraph", node_position={"x":200,"y":0})
  add_blueprint_self_reference(blueprint_name="BP_X", graph_name="EventGraph", node_position={"x":0,"y":200})
  add_blueprint_get_component_node(blueprint_name="BP_X", graph_name="EventGraph", component_name="Mesh", node_position={"x":200,"y":0})
  add_blueprint_enhanced_input_action_node(blueprint_name="BP_X", graph_name="EventGraph", action_asset="/Game/.../IA_Move", node_position={"x":0,"y":400})
  add_blueprint_comment_node(blueprint_name="BP_X", graph_name="EventGraph", comment_text="Movement Logic", node_position={"x":-100,"y":-100}, size={"x":400,"y":200})
  add_event_dispatcher(blueprint_name="BP_X", dispatcher_name="OnQuestComplete")
  add_custom_function(blueprint_name="BP_X", function_name="CalculateDamage")
  add_timeline_node(blueprint_name="BP_X", graph_name="EventGraph", timeline_name="FadeTimeline", node_position={"x":200,"y":0})
  add_delay_node(blueprint_name="BP_X", duration=2.0, node_position={"x":200,"y":0})
  add_print_string_node(blueprint_name="BP_X", message="Debug", node_position={"x":200,"y":0})
  add_math_node(blueprint_name="BP_X", operator="Add", node_position={"x":200,"y":0})

NODE EDITING
  connect_blueprint_nodes(blueprint_name="BP_X", graph_name="EventGraph", source_node_id="GUID1", target_node_id="GUID2", source_pin="then", target_pin="execute")
  disconnect_blueprint_nodes(blueprint_name="BP_X", graph_name="EventGraph", source_node_id="GUID1", target_node_id="GUID2", source_pin="then", target_pin="execute")
  delete_blueprint_node(blueprint_name="BP_X", graph_name="EventGraph", node_id="GUID")
  set_node_pin_value(blueprint_name="BP_X", graph_name="EventGraph", node_id="GUID", pin_name="Value", value="42.0")
  move_blueprint_node(blueprint_name="BP_X", graph_name="EventGraph", node_id="GUID", node_position={"x":400,"y":200})

AI / BEHAVIOR TREE
  create_behavior_tree(name="BT_Enemy", path="/Game/MyProject/AI/BehaviorTrees")
  create_blackboard(name="BB_Enemy", path="/Game/MyProject/AI/Blackboard", keys=[{"name":"TargetActor","type":"Object"},{"name":"PatrolLocation","type":"Vector"},{"name":"IsAlert","type":"Bool"}])
  set_behavior_tree_blackboard(behavior_tree_name="BT_Enemy", blackboard_name="BB_Enemy")
  create_ai_controller(name="BP_EnemyAI", behavior_tree="BT_Enemy")
  create_bt_task(blueprint_name="BTT_Attack", task_name="AttackPlayer")
  create_bt_decorator(blueprint_name="BTD_IsPlayerNear", decorator_name="IsPlayerNear")
  create_bt_service(blueprint_name="BTS_UpdateTarget", service_name="UpdateTarget")
  create_full_enemy_ai(enemy_name="BP_Enemy", has_attack=True, has_hearing=True, has_wandering=True)
  create_full_upgraded_enemy_ai(enemy_name="BP_Enemy")
  setup_navmesh(extent={"x":5000,"y":5000,"z":500}, location={"x":0,"y":0,"z":0}, rebuild=True)
  add_move_to_node(blueprint_name="BTT_X", node_position={"x":200,"y":0})
  add_get_random_reachable_point_node(blueprint_name="BP_X", radius=1000.0)
  add_pawn_sensing_component(blueprint_name="BP_X", hearing_threshold=2800.0, sight_radius=3000.0)
  add_get_blackboard_value_node(blueprint_name="BTT_X", key_name="TargetActor", value_type="Object")
  add_clear_blackboard_value_node(blueprint_name="BTT_X", key_name="TargetActor")
  add_finish_execute_node(blueprint_name="BTT_X", success=True)

  Blackboard key types: Vector, Bool, Float, Int, String, Object

ANIMATION
  create_animation_blueprint(name="ABP_Player", path="/Game/MyProject/Animation", skeleton_path="/Game/MyProject/Art/SK_Player")
  add_state_machine(anim_blueprint_name="ABP_Player", state_machine_name="LocomotionSM")
  add_animation_state(anim_blueprint_name="ABP_Player", state_machine_name="LocomotionSM", state_name="Idle")
  add_state_transition(anim_blueprint_name="ABP_Player", state_machine_name="LocomotionSM", from_state="Idle", to_state="Walk")
  set_animation_for_state(anim_blueprint_name="ABP_Player", state_machine_name="LocomotionSM", state_name="Idle", animation_asset="/Game/.../AN_Idle")
  add_blend_space_node(anim_blueprint_name="ABP_Player", blend_space_asset="/Game/.../BS_Walk", node_position={"x":200,"y":0})
  add_anim_notify(animation_path="/Game/.../AN_Attack", notify_name="FootstepNotify", time=0.5)
  create_character_animation_setup(character_name="BP_Player", skeleton="SK_Player")

DATA ASSETS
  create_struct(name="ST_ItemData", path="/Game/MyProject/Data/Structs")
  create_enum(name="E_ItemType", path="/Game/MyProject/Data/Enums")
  create_data_table(name="DT_Items", row_struct="ST_ItemData")
  create_blueprint_interface(name="BPI_Interactable", path="/Game/MyProject/Interfaces")
  implement_blueprint_interface(blueprint_name="BP_Chest", interface_name="BPI_Interactable")
  create_blueprint_macro_library(name="BML_Utilities")
  create_blueprint_function_library(name="BFL_MathHelpers")
  add_get_data_table_row_node(blueprint_name="BP_X", data_table_variable="DT_Items", row_name="Sword")
  add_make_struct_node(blueprint_name="BP_X", struct_type="ST_ItemData")
  add_break_struct_node(blueprint_name="BP_X", struct_type="ST_ItemData")

ENHANCED INPUT
  create_enhanced_input_action(name="IA_Jump", path="/Game/MyProject/Data/Input")
  create_input_mapping_context(name="IMC_Default", path="/Game/MyProject/Data/Input")
  add_input_mapping(context_name="IMC_Default", action_name="IA_Jump", key="SpaceBar")

UMG / WIDGETS
  create_umg_widget_blueprint(name="WBP_HUD", path="/Game/MyProject/Widgets")
  create_hud_widget(widget_name="WBP_HUD", health_bar=True, stamina_bar=True, ammo_counter=True)
  add_text_block_to_widget(widget_name="WBP_HUD", text_block_name="HealthText", text="100", position={"x":10,"y":10})
  add_button_to_widget(widget_name="WBP_HUD", button_name="RestartButton", position={"x":100,"y":100})
  bind_widget_event(widget_name="WBP_HUD", widget_element_name="RestartButton", event_name="OnClicked", function_name="HandleRestartClicked")
  set_text_block_binding(widget_name="WBP_HUD", text_block_name="HealthText", binding_function="GetHealthText")
  add_widget_to_viewport(widget_name="WBP_HUD")
  add_create_widget_node(blueprint_name="BP_PC", widget_class="WBP_HUD")
  create_pause_menu_widget(widget_name="WBP_PauseMenu")
  create_win_menu_widget(widget_name="WBP_WinScreen", title_text="You Win!")
  create_lose_screen_widget(widget_name="WBP_LoseScreen", message_text="Game Over")

GAMEPLAY FRAMEWORK
  create_game_mode(name="BP_MyGameMode", default_pawn_class="BP_Player", player_controller_class="BP_PC")
  create_player_controller(name="BP_PC", parent_class="PlayerController")
  create_game_instance(name="BP_GameInstance")
  create_character_blueprint(name="BP_Player", parent_class="Character")
  create_fps_character(name="BP_FPSCharacter")
  set_game_mode_for_level(game_mode_name="BP_MyGameMode")
  add_overlap_event(blueprint_name="BP_Trigger", component_name="CollisionBox")
  add_hit_event(blueprint_name="BP_Projectile", component_name="Mesh")
  add_player_death_event(blueprint_name="BP_Player", lose_widget_name="WBP_LoseScreen")

VFX / MATERIALS / SEQUENCER
  create_material(name="M_Rock", base_color={"r":0.5,"g":0.3,"b":0.1}, metallic=0.0, roughness=0.8)
  create_dynamic_material_instance(blueprint_name="BP_X", component_name="Mesh", source_material_path="/Game/.../M_Rock")
  set_material_on_actor(actor_name="SM_Cube", material_path="/Game/.../M_Rock")
  set_material_instance_parameter(material_instance_path="/Game/.../MI_X", parameter_name="BaseColor", parameter_type="Vector", value="1.0,0.0,0.0,1.0")
  add_niagara_component(blueprint_name="BP_X", component_name="FX", niagara_system_path="/Game/.../NS_X")
  add_spawn_niagara_at_location_node(blueprint_name="BP_X", graph_name="EventGraph", niagara_system_path="/Game/.../NS_X", node_position={"x":400,"y":0})
  add_spawn_emitter_at_location_node(blueprint_name="BP_X", particle_system_path="/Game/.../PS_X")
  set_sequencer_track(sequence_path="/Game/.../LS_X", actor_name="MyActor", track_type="Transform", keyframes=[{"time":0.0,"location":{"x":0,"y":0,"z":0}},{"time":2.0,"location":{"x":500,"y":0,"z":0}}])
  add_play_sound_at_location_node(blueprint_name="BP_X", sound_asset_path="/Game/.../SC_X")
  setup_hit_material_swap(blueprint_name="BP_X", mesh_component="Mesh", default_material="/Game/.../M_Default", hit_material="/Game/.../M_Hit")

PHYSICS / MATH / TRACE
  add_line_trace_by_channel_node(blueprint_name="BP_X", trace_channel="Visibility", draw_debug=True)
  add_sphere_trace_by_channel_node(blueprint_name="BP_X", radius=50.0, trace_channel="Visibility")
  add_break_hit_result_node(blueprint_name="BP_X")
  add_apply_damage_node(blueprint_name="BP_X", damage_amount=25.0)
  add_get_actor_location_node(blueprint_name="BP_X")
  add_set_actor_location_node(blueprint_name="BP_X")
  add_get_actor_rotation_node(blueprint_name="BP_X")
  add_vector_add_node(blueprint_name="BP_X")
  add_normalize_vector_node(blueprint_name="BP_X")
  add_get_forward_vector_node(blueprint_name="BP_X")
  add_arithmetic_operator_node(blueprint_name="BP_X", operator="Multiply", operand_type="Float")
  add_relational_operator_node(blueprint_name="BP_X", operator="GreaterThan", operand_type="Float")
  add_clamp_node(blueprint_name="BP_X", operand_type="Float", min_value=0.0, max_value=1.0)
  add_lerp_node(blueprint_name="BP_X", operand_type="Float")
  add_random_float_in_range_node(blueprint_name="BP_X", min_value=0.0, max_value=1.0)
  add_draw_debug_line_node(blueprint_name="BP_X", duration=2.0, color="Red")
  build_trace_interaction_blueprint(blueprint_name="BP_X", trace_range=500.0, input_key="E")

SAVE GAME
  create_savegame_blueprint(name="BP_MySave", variables=[{"name":"PlayerScore","type":"Integer"},{"name":"Level","type":"Integer"}])
  setup_full_save_load_system(character_blueprint="BP_Player", save_blueprint_name="BP_MySave")
  add_save_game_to_slot_node(blueprint_name="BP_X", save_game_variable="SaveRef", slot_name_variable="SlotName")
  add_load_game_from_slot_node(blueprint_name="BP_X", slot_name_variable="SlotName", save_game_class="BP_MySave")
  add_open_level_node(blueprint_name="BP_X", level_name="MainMenu")
  add_quit_game_node(blueprint_name="BP_X")
  add_set_game_paused_node(blueprint_name="BP_X", paused=True)
  create_round_based_game_system(character_blueprint="BP_Player", round_scale_multiplier=1.5)

BLUEPRINT COMMUNICATION
  add_event_dispatcher(blueprint_name="BP_X", dispatcher_name="OnQuestComplete")
  call_event_dispatcher(blueprint_name="BP_X", dispatcher_name="OnQuestComplete", node_position={"x":200,"y":0})
  bind_event_to_dispatcher(blueprint_name="BP_X", dispatcher_blueprint="BP_QuestManager", dispatcher_name="OnQuestComplete", node_position={"x":400,"y":0})
  add_call_interface_function_node(blueprint_name="BP_X", interface_name="BPI_Interactable", function_name="Interact")
  add_direct_blueprint_reference(blueprint_name="BP_X", target_blueprint="BP_GameManager", variable_name="GameManagerRef")

PROCEDURAL / COMPONENT
  create_actor_component(name="AC_Health", variables=[{"name":"MaxHealth","type":"Float"}])
  create_scene_component(name="AC_Orbit")
  create_experience_level_component(name="AC_XPSystem", max_level=10, xp_per_level=100)
  create_circular_movement_component(name="AC_Orbit", rotation_per_second=45.0)
  add_component_to_blueprint_actor(blueprint_name="BP_Player", component_blueprint_name="AC_Health")
  create_procedural_mesh_blueprint(name="BP_ProceduralGrid", static_mesh_path="/Game/.../SM_Cube", instances_per_row=10)
  create_spline_placement_blueprint(name="BP_Road", static_mesh_path="/Game/.../SM_RoadSegment", space_between_instances=200.0)
  add_set_timer_by_event_node(blueprint_name="BP_X", time_seconds=3.0, looping=True, custom_event_name="OnTimer")
  add_clear_timer_node(blueprint_name="BP_X", timer_handle_variable="TimerHandle")

HIGH-LEVEL COMPOSITE TOOLS (build entire systems in one call)
  create_fps_character(name="BP_FPSCharacter")
  create_full_enemy_ai(enemy_name="BP_Enemy", has_attack=True, has_hearing=True, has_wandering=True)
  create_full_upgraded_enemy_ai(enemy_name="BP_Enemy")
  create_vr_pawn_blueprint(name="BP_VRPawn")
  create_enemy_spawner_blueprint(name="BP_EnemySpawner")
  create_random_spawner_blueprint(name="BP_RandomSpawner")
  create_procedural_mesh_blueprint(name="BP_Grid")
  create_spline_placement_blueprint(name="BP_Road")
  create_product_configurator_blueprint(name="BP_Configurator")
  setup_hit_material_swap(blueprint_name="BP_X", mesh_component="Mesh", default_material="/Game/.../M_Default", hit_material="/Game/.../M_Hit")
  build_trace_interaction_blueprint(blueprint_name="BP_X", trace_range=500.0, input_key="E")
  build_complete_blueprint_graph(blueprint_name="BP_X")

KNOWLEDGE BASE TOOLS (anti-hallucination — MANDATORY before implementing any system)
  list_knowledge_base_topics()
      → Returns index of all available topics with usage instructions

  get_knowledge_base(topic="ai")
      → Returns full reference doc + book extracts for the topic
      → Topics: blueprints, communication, gameplay, ai, animation, ui, data,
                materials, niagara, world, components, input, cookbook,
                packaging, animation_deep, technical_art, vfx, tools, dantooine
      → CALL THIS FIRST before building any of the above systems

  search_knowledge_base(query="behavior tree task")
      → Keyword search across all 22 KB files + 10 book extracts (1,626 pages)
      → Returns top matching sections with source file references

═══════════════════════════════════════════════
5. ASSET CREATION VIA exec_python (FOR CUSTOM FOLDERS)
═══════════════════════════════════════════════

ALWAYS use exec_python for assets in project-specific folders.
The create_blueprint tool hardcodes /Game/Blueprints/.

Standard Blueprint (exec_python code string):
  import unreal
  at = unreal.AssetToolsHelpers.get_asset_tools()
  f = unreal.BlueprintFactory()
  f.set_editor_property("parent_class", unreal.Character)
  a = at.create_asset("BP_MyCharacter", "/Game/MyProject/Blueprints/Player", unreal.Blueprint, f)
  print("OK" if a else "FAIL")

Widget Blueprint:        f = unreal.WidgetBlueprintFactory() ... unreal.WidgetBlueprint
Behavior Tree:           unreal.BehaviorTree, unreal.BehaviorTreeFactory()
Blackboard:              unreal.BlackboardData, unreal.BlackboardDataFactory()
Animation Blueprint:     f = unreal.AnimBlueprintFactory(); f.set_editor_property("target_skeleton", sk)

Create folder:           unreal.EditorAssetLibrary.make_directory("/Game/MyProject/Blueprints/Player")
Check asset exists:      exists = unreal.EditorAssetLibrary.does_asset_exist("/Game/.../BP_X"); print("EXISTS" if exists else "MISSING")
Save all assets:         unreal.EditorAssetLibrary.save_directory("/Game/MyProject", recursive=True)

═══════════════════════════════════════════════
6. STANDARD WORKFLOW PATTERNS
═══════════════════════════════════════════════

PATTERN A — Complete Blueprint Build Sequence
  1. exec_python → create_asset              (create in custom folder if needed)
  2. get_blueprint_variables                 (see what variables already exist)
  3. add_blueprint_variable                  (add needed variables)
  4. get_blueprint_graphs                    (confirm graph names)
  5. add_blueprint_event_node                (BeginPlay, Tick, etc.)
  6. add_blueprint_function_node             (each function call)
  7. get_blueprint_nodes                     ← GET ALL NODE IDs BEFORE CONNECTING
  8. connect_blueprint_nodes                 (exec wires first, then data wires)
  9. compile_blueprint
  10. get_blueprint_nodes                    (verify all connections are correct)

PATTERN B — AIController Setup
  1. exec_python → create AIController Blueprint in correct folder
  2. add_blueprint_event_node(event_name="ReceiveBeginPlay")
  3. add_blueprint_function_node(function_name="RunBehaviorTree")
  4. get_blueprint_nodes → connect BeginPlay.then → RunBehaviorTree.execute
  5. set_node_pin_value (BTAsset pin → path to BT asset)
  6. compile_blueprint
  7. set_blueprint_ai_controller on the Character Blueprint

PATTERN C — New Function With Typed I/O
  1. add_blueprint_function_with_pins (creates function graph + typed entry/result nodes)
  2. get_blueprint_nodes(graph_name="FunctionName") → get entry/result node IDs
  3. add nodes inside the function graph using graph_name="FunctionName"
  4. connect_blueprint_nodes
  5. compile_blueprint

PATTERN D — Safe Actor Reference (ALWAYS use this)
  GetPlayerCharacter
  → Cast To BP_MyCharacter
    → Cast Succeeded → As BP_MyCharacter → [use reference, store in variable]
    → Cast Failed   → [do nothing / return]

PATTERN E — Widget HUD Creation (In PlayerController BeginPlay)
  Event BeginPlay
  → Create Widget (Class: WBP_HUD, Owning Player: self)
  → Store result in HUDRef variable
  → Add to Viewport

═══════════════════════════════════════════════
7. BLUEPRINT PARENT CLASS LOOKUP
═══════════════════════════════════════════════

Actor              Static props, triggers, managers
Pawn               Simple controllable pawn
Character          Walking character (player or NPC)
PlayerController   Player input + camera handling
AIController       AI decision making
GameModeBase       Game rules (server authority)
GameInstance       Persistent data across levels
GameStateBase      Replicated match state
PlayerState        Per-player persistent state
SaveGame           Disk save file
ActorComponent     Reusable logic (no transform)
SceneComponent     Reusable with transform
BlueprintFunctionLibrary   Global static utilities
BTTask_BlueprintBase       Custom BT action
BTDecorator_BlueprintBase  Custom BT condition
BTService_BlueprintBase    Custom BT periodic logic

═══════════════════════════════════════════════
8. NAMING CONVENTIONS (MANDATORY)
═══════════════════════════════════════════════

BP_   Blueprint Class          WBP_  Widget Blueprint
BPI_  Blueprint Interface      ABP_  Animation Blueprint
BT_   Behavior Tree            BB_   Blackboard
BTT_  BT Task Blueprint        BTD_  BT Decorator Blueprint
BTS_  BT Service Blueprint     E_    Enum
ST_   Struct                   DA_   Data Asset
DT_   Data Table               IA_   Input Action
IMC_  Input Mapping Context    LS_   Level Sequence
NS_   Niagara System           M_    Material
MI_   Material Instance        T_    Texture
SK_   Skeletal Mesh            SM_   Static Mesh
AN_   Animation Sequence       AM_   Animation Montage
BS_   Blend Space              AC_   Actor Component
BFL_  Blueprint Function Library

Incorrectly named assets cannot be found by other Blueprints.

═══════════════════════════════════════════════
9. THIS PROJECT'S SPECIFIC SETUP
═══════════════════════════════════════════════

Project Name:    [PROJECT_NAME]
Engine Version:  [UE_VERSION — e.g. 5.6]
Content Root:    [CONTENT_ROOT — e.g. /Game/MyProject/]
Local Path:      [FULL LOCAL PATH on developer's machine]

Folder structure:
  [PASTE YOUR /Game/ FOLDER HIERARCHY HERE]

Assets already created:
  [LIST KEY EXISTING ASSETS, OR: "None yet — starting fresh"]

First task for this session:
  [DESCRIBE EXACTLY WHAT YOU WANT THE AGENT TO DO]
```

---

## File Structure

```
Unreal-MCP-Ghost/
├── README.md                              ← You are here
├── sandbox_ue5cli.py                      ← Low-level debug CLI (developers only; agents use MCP tools)
├── pyproject.toml
│
├── knowledge_base/                        ← 19-file reference library for AI agents
│   ├── 00_AGENT_KNOWLEDGE_BASE.md         ← Master index + mandatory agent rules
│   ├── 01_BLUEPRINT_FUNDAMENTALS.md
│   ├── 02_BLUEPRINT_COMMUNICATION.md
│   ├── 03_GAMEPLAY_FRAMEWORK.md
│   ├── 04_AI_SYSTEMS.md
│   ├── 05_ANIMATION_SYSTEM.md
│   ├── 06_UI_UMG_SYSTEMS.md
│   ├── 07_DATA_STRUCTURES.md
│   ├── 08_MATERIALS_AND_RENDERING.md
│   ├── 09_NIAGARA_VFX.md
│   ├── 10_WORLD_BUILDING.md
│   ├── 11_BLUEPRINT_LIBRARIES_AND_COMPONENTS.md
│   ├── 12_MCP_TOOL_USAGE_GUIDE.md         ← Complete command docs with examples
│   ├── 13_TOOL_EXPANSION_ROADMAP.md       ← Command development status
│   ├── 14_DANTOOINE_PROJECT_REFERENCE.md  ← Example project reference
│   ├── 15_INPUT_SYSTEM_AND_UMG.md
│   ├── 16_ANIMATION_DEEP_DIVE.md
│   ├── 17_GAME_SYSTEMS_COOKBOOK.md
│   ├── 18_PACKAGING_AND_OPTIMIZATION.md
│   ├── AI_DEVELOPER_ONBOARDING_PROMPT.md  ← Copy-paste onboarding prompt
│   └── INDEX.md
│
├── unreal_mcp_server/
│   ├── unreal_mcp_server.py               ← MCP server entry point (for AI clients)
│   ├── tools/                             ← MCP tool wrappers (31 tool modules + diagnostics + repair, 403 tools)
│   └── skills/                            ← Composition skills (2 modules: audit + repair_broken_blueprint)
│
└── unreal_plugin/
    ├── UnrealMCP.uplugin
    └── Source/UnrealMCP/
        ├── UnrealMCP.Build.cs
        ├── Public/Commands/
        │   ├── UnrealMCPBlueprintCommands.h
        │   ├── UnrealMCPBlueprintNodeCommands.h    ← 40 node commands
        │   ├── UnrealMCPExtendedCommands.h         ← 50 extended commands
        │   ├── UnrealMCPCommonUtils.h
        │   └── UnrealMCPEditorCommands.h
        └── Private/
            ├── UnrealMCPBridge.cpp                 ← Command dispatcher + TCP server
            ├── MCPServerRunnable.cpp               ← TCP accept loop
            └── Commands/
                ├── UnrealMCPBlueprintCommands.cpp  ← Blueprint class commands
                ├── UnrealMCPBlueprintNodeCommands.cpp
                ├── UnrealMCPExtendedCommands.cpp
                ├── UnrealMCPCommonUtils.cpp
                ├── UnrealMCPEditorCommands.cpp     ← Actor/level commands
                ├── UnrealMCPUMGCommands.cpp        ← Widget commands
                └── UnrealMCPProjectCommands.cpp    ← Input commands
```

---

## Architecture Notes

### TCP Socket Protocol

- The C++ plugin starts a single-threaded TCP server on `127.0.0.1:55557` when UE5 loads
- Each command is a newline-terminated JSON object: `{"command": "...", "params": {...}}\n`
- Commands execute on UE5's game thread via `AsyncTask(ENamedThreads::GameThread, ...)`
- One command executes at a time; the Python CLI queues concurrent requests

### Health-check Probe Handling

TCP proxies (Playit, ngrok, etc.) send periodic zero-byte health-check connections. The plugin handles these by polling for data for up to 5 seconds after accepting a connection — if no data arrives, the connection is classified as a probe and closed without blocking real commands.

### Build Dependencies

The plugin requires these UE5 modules (all declared in `UnrealMCP.Build.cs`):

**Public:** Core, CoreUObject, Engine, InputCore, Networking, Sockets, HTTP, Json, JsonUtilities  
**Private:** UnrealEd, EditorScriptingUtilities, AssetRegistry, BlueprintGraph, KismetCompiler, UMG, UMGEditor, AIModule, NavigationSystem, BehaviorTreeEditor, AnimGraph, AnimGraphRuntime, EnhancedInput, NiagaraEditor, LevelSequenceEditor, MovieScene, MovieSceneTracks, ProceduralMeshComponent, and more

---

## License

Based on [chongdashu/unreal-mcp](https://github.com/chongdashu/unreal-mcp). Extended under the same MIT license.
