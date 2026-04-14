# Cursor MCP Setup Guide — UnrealMCP (2026-04-13)

This guide sets up **Cursor IDE** to control UE5 directly via the 321-tool MCP server,
using `stdio` transport (no port-forwarding, no SSE, no Playit tunnel needed).

There are now two supported backends:
- **plugin** — default, full existing Ghost behavior through the UnrealMCP plugin
- **native-python** — plugin-free, uses UE5 Python Remote Execution and supports `exec_python`-based workflows

---

## Step 1 — Prerequisites

| Requirement | Check |
|-------------|-------|
| Python 3.10+ on PATH | `python --version` in terminal |
| MCP + FastMCP installed | `pip install "mcp>=1.2.0" "fastmcp>=2.0.0" "pydantic-core>=2.28.0" anyio` |
| UE5 Editor open with EnclaveProject | Required for both backends |
| Plugin mode only: UnrealMCP plugin active | Check Plugins menu and Output Log for port 55557 listener |
| Native mode only: UE5 Python Script Plugin + Remote Python Execution enabled | Required for plugin-free startup |

---

## Step 2 — Install the MCP config into Cursor

Cursor reads MCP servers from **one of two places** (use whichever fits):

### Option A — Global (applies to ALL projects)

Copy `mcp.json` to:
```
%APPDATA%\Cursor\User\globalStorage\cursor.mcp\mcp.json
```
Or open Cursor → **Settings** → search **"MCP"** → click **"Edit in mcp.json"** — paste the JSON below.

### Option B — Project-local (only for this project)

Create a `.cursor` folder inside your project root and put `mcp.json` inside it:
```
EnclaveProject\
  .cursor\
    mcp.json          ← create this
```

---

## Step 3 — Pick a config

Use one of the bundled examples:
- `cursor_setup/mcp.json` — plugin mode
- `cursor_setup/mcp.native-python.json` — native mode

### Plugin mode

```json
{
  "mcpServers": {
    "unreal-mcp": {
      "command": "python",
      "args": [
        "C:\\Users\\NewAdmin\\Documents\\Academy of Art University\\2026\\Gam270\\Project2\\EnclaveProject\\unreal_mcp_server\\unreal_mcp_server.py"
      ],
      "env": {
        "UNREAL_HOST": "127.0.0.1",
        "UNREAL_PORT": "55557"
      }
    }
  }
}
```

### Native mode

```json
{
  "mcpServers": {
    "unreal-mcp": {
      "command": "python",
      "args": [
        "C:\\Users\\NewAdmin\\Documents\\Academy of Art University\\2026\\Gam270\\Project2\\EnclaveProject\\unreal_mcp_server\\unreal_mcp_server.py"
      ],
      "env": {
        "UNREAL_MCP_BACKEND": "native-python"
      }
    }
  }
}
```

> In native mode, omit `UNREAL_PORT` if you want UE5 Python Remote Execution discovery.
> Set both `UNREAL_HOST` and `UNREAL_PORT` only when you want a direct native connection.

> **Important**: The path in `args` must match where `unreal_mcp_server.py` actually lives on your machine.
> Adjust the path if your project is in a different location.

---

## Step 4 — Verify the connection

1. Open Cursor.
2. Open the Chat panel (Ctrl+L or Cmd+L).
3. Make sure **Agent** mode is selected (not "Ask" or "Edit").
4. Type one of these:
  - Plugin mode: `List the actors in the current UE5 level`
  - Native mode: `Use exec_python to print unreal.SystemLibrary.get_engine_version()`

If connected, you'll see tool calls like `get_actors_in_level` being invoked and results returned.

If you get "MCP server not found" errors, check:
- The `python` command works in your terminal (or use the full path: `C:\Python312\python.exe`)
- UE5 is open and the Output Log shows `[MCP] Server listening on port 55557`
- The path in `mcp.json` exactly matches the location of `unreal_mcp_server.py`

---

## Step 5 — Paste the System Prompt into Cursor

1. Open Cursor → **Settings** → **General** → **Rules for AI** (or **System Prompt**).
2. Paste the entire contents of `cursor_system_prompt.md` into that field.
3. Save.

This tells Cursor how to use all 321 tools correctly, with the right parameter formats,
retry logic, and workflow order.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Connection refused` | UE5 is not open or the plugin is not loaded. Check Output Log. |
| `No UE5 Python Remote Execution endpoint was discovered` | Enable the UE5 Python Script Plugin and Remote Python Execution, or supply a direct `UNREAL_PORT`. |
| `Command '...' requires the UnrealMCP plugin backend` | That tool still needs the plugin path. Use `exec_python` or switch back to plugin mode. |
| `Timeout after 30s` | The command is slow (compile, add_component). The server auto-retries up to 90–150 s. Wait. |
| `Blueprint not found` | The Blueprint must already exist in the Content Browser under `/Game/`. |
| `python: command not found` | Use full path: `C:\Python312\python.exe` in the `command` field. |
| MCP tools not showing in Cursor | Restart Cursor after editing `mcp.json`. |
| UE5 freezes after many commands | Wait 10 s; the health-check ping will auto-recover. |

---

## Quick Test Commands for Cursor

Once connected, try these in the Cursor chat:

```
# Verify connection
List all actors in the current level

# Create a simple test blueprint
Create a Blueprint called BP_TestSpinner that rotates 1 degree per tick

# Inspect existing blueprints
Show me all variables in BP_MyCharacter

# Full AI enemy setup
Create a full enemy AI with behavior tree for a melee enemy called BP_Enemy_Grunt
```
