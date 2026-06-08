# Unreal-MCP-Ghost

Unreal-MCP-Ghost is an Unreal Engine 5.6 editor plugin plus a Python FastMCP server that lets AI agents inspect and modify live UE projects through the Model Context Protocol.

The current server registers **640 MCP tools**. The plugin exposes a TCP bridge to Unreal Editor on port `55557`, and the Python server exposes MCP over `stdio`, `sse`, or `streamable-http`. The plugin also includes an optional dockable **MCP Chat** editor window with live context chips, typed drag/drop references, and a categorized tool palette that can send messages to Cursor through the server.

## What It Can Do

- Inspect levels, actors, Blueprints, components, variables, graphs, nodes, pins, compile diagnostics, references, source control state, and project assets.
- Create and edit Blueprints, Blueprint Interfaces, variables, functions, graph nodes, comments, connections, timers, input handlers, UMG widgets, materials, data assets, save-game systems, and gameplay framework classes.
- Work with AI systems: Behavior Trees, Blackboards, AI Controllers, BT tasks/decorators/services, navmesh helpers, and higher-level AI setup workflows.
- Work with animation systems: Animation Blueprints, state machines, blend spaces, AnimGraph slot insertion, Control Rig asset/control/constraint helpers, IK Rig creation, IK Retargeter creation, skeleton bone inspection, and batch retargeting.
- Import assets: textures, static meshes, skeletal meshes, audio, folders, and KotOR/GhostRigger assets.
- Add VFX/audio/material logic: Niagara components, spawn Niagara nodes, sound nodes, material instance parameters, collision settings, and Sequencer transform tracks.
- Validate and repair Blueprints with diagnostic, repair, execution journal, action risk-evaluation, PIE, log, and viewport evidence tools.
- Provide a repo knowledge base for UE5 workflows, Blueprint patterns, MCP usage, first-person systems, retargeting, Sequencer, Control Rig, weapons, melee, force powers, and boss AI.
- Provide an editor-side chat panel with live level, actor, dirty-asset, compile, and SSE server context chips, typed asset/actor/file drag-drop references, a categorized tool palette, and an optional Cursor SDK watcher for automatic replies.

## Architecture

```text
AI client or Cursor watcher
  |
  | MCP stdio / SSE / streamable-http
  v
Python FastMCP server
  - unreal_mcp_server/unreal_mcp_server.py
  - 640 registered MCP tools
  - optional /chat/* HTTP routes on port 8000
  |
  | TCP JSON, one command per connection
  v
UnrealMCP UE plugin
  - localhost:55557
  - runs commands on the editor GameThread
  - UnrealMCP module: TCP bridge and command handlers
  - UnrealMCPEditor module: Window > MCP Chat
  |
  v
Unreal Engine Editor
```

## Repository Layout

```text
Unreal-MCP-Ghost/
|-- unreal_plugin/                 # UE5 editor plugin to copy into a project
|-- unreal_mcp_server/             # Python FastMCP server and tool modules
|-- knowledge_base/                # General Unreal/MCP reference docs
|-- docs/knowledge-base/           # Packt study guides used by agents
|-- scripts/ue-chat-agent.mjs      # Optional Cursor SDK chat watcher
|-- docs/ue-editor-chat-agent.md   # Chat watcher instructions
|-- package.json                   # Node dependency for chat watcher
`-- pyproject.toml                 # Python dependency metadata
```

## First-Time Setup

### 1. Install Prerequisites

- Unreal Engine `5.6`
- Visual Studio 2022 with **Game development with C++**
- Python `3.10+`
- Git
- Node.js `20+` if you want automatic editor chat replies
- `uv` is recommended for Python dependency/running workflows

Check basics:

```powershell
python --version
uv --version
node --version
git --version
```

### 2. Clone the Repo

```powershell
git clone https://github.com/CrispyW0nton/Unreal-MCP-Ghost.git "C:\Dev\Unreal-MCP-Ghost"
cd "C:\Dev\Unreal-MCP-Ghost"
```

### 3. Copy the Plugin into Your UE Project

The plugin must live under your project's `Plugins` folder.

```powershell
$REPO    = "C:\Dev\Unreal-MCP-Ghost"
$PROJECT = "C:\Users\You\Documents\UnrealProjects\MyGame"

New-Item -ItemType Directory -Force -Path "$PROJECT\Plugins\UnrealMCP"
Copy-Item -Recurse -Force "$REPO\unreal_plugin\*" "$PROJECT\Plugins\UnrealMCP\"
```

When updating an existing project plugin, close Unreal Editor first and remove old plugin build artifacts:

```powershell
Stop-Process -Name UnrealEditor -Force -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$PROJECT\Plugins\UnrealMCP\Binaries" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$PROJECT\Plugins\UnrealMCP\Intermediate" -ErrorAction SilentlyContinue
Copy-Item -Recurse -Force "$REPO\unreal_plugin\*" "$PROJECT\Plugins\UnrealMCP\"
```

### 4. Generate Project Files

Right-click your `.uproject` and choose **Generate Visual Studio project files**, or run:

```powershell
$UPROJECT = "$PROJECT\MyGame.uproject"
& "C:\Program Files\Epic Games\UE_5.6\Engine\Build\BatchFiles\GenerateProjectFiles.bat" `
  -project="$UPROJECT" -game -rocket
```

### 5. Build the Plugin

Open the generated `.sln` in Visual Studio 2022:

- Configuration: `Development Editor`
- Platform: `Win64`
- Build: `Ctrl+Shift+B`

Or build from PowerShell:

```powershell
& "C:\Program Files\Epic Games\UE_5.6\Engine\Build\BatchFiles\Build.bat" `
  MyGameEditor Win64 Development `
  -Project="$UPROJECT" `
  -WaitMutex -FromMsBuild -architecture=x64
```

Expected result:

```text
Result: Succeeded
```

Notes:

- `Visual Studio 2022 compiler is not a preferred version` is usually a warning, not a blocker.
- If build fails with exit code `6`, scroll up for the actual `error C...` compiler line.
- If Live Coding is active, close Unreal Editor or press `Ctrl+Alt+F11`.

### 6. Open Unreal and Verify the Plugin

Open the `.uproject`. In **Window > Output Log**, confirm:

```text
UnrealMCPBridge: Server started on 127.0.0.1:55557
```

PowerShell port check:

```powershell
python -c "import socket; s=socket.socket(); s.settimeout(2); r=s.connect_ex(('127.0.0.1',55557)); s.close(); print('PLUGIN RUNNING' if r==0 else 'PLUGIN NOT RUNNING')"
```

## Running the MCP Server

### Local AI Clients: stdio

Use this when Cursor, Claude Desktop, Windsurf, or another local MCP client launches the server itself:

```json
{
  "mcpServers": {
    "unrealMCP": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Dev\\Unreal-MCP-Ghost",
        "run",
        "python",
        "unreal_mcp_server\\unreal_mcp_server.py"
      ]
    }
  }
}
```

If you do not use `uv`:

```json
{
  "mcpServers": {
    "unrealMCP": {
      "command": "python",
      "args": ["C:\\Dev\\Unreal-MCP-Ghost\\unreal_mcp_server\\unreal_mcp_server.py"]
    }
  }
}
```

Restart the AI client after editing MCP config.

### HTTP/SSE Server

Use this when remote clients, Cursor SDK processes, or the Unreal editor chat panel need HTTP routes:

```powershell
cd "C:\Dev\Unreal-MCP-Ghost"
python unreal_mcp_server\unreal_mcp_server.py --transport sse --mcp-host 0.0.0.0 --mcp-port 8000
```

Expected:

```text
[UnrealMCP] SSE server listening on http://0.0.0.0:8000/sse
[UnrealMCP] UE5 plugin target: 127.0.0.1:55557
```

Quick HTTP checks:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/chat/history?limit=1"
```

### Streamable HTTP

For MCP clients supporting the newer streamable HTTP transport:

```powershell
python unreal_mcp_server\unreal_mcp_server.py --transport streamable-http --mcp-host 0.0.0.0 --mcp-port 8000
```

Endpoint: `http://127.0.0.1:8000/mcp`

## Unreal Editor Chat

The plugin registers a dockable tab:

```text
Window > MCP Chat
```

The tab is implemented in the editor-only `UnrealMCPEditor` module so the core
`UnrealMCP` module can stay focused on TCP bridge command handling.

The panel:

- Loads previous messages from `/chat/history`
- Sends human messages to `/chat/send`
- Polls agent replies from `/chat/poll?sender=agent`
- Uses a resizable conversation/composer split with multiline input, drag/drop reference insertion, and Enter-to-send / Shift+Enter newline behavior
- Renders role-tagged user, agent, and tool message bubbles with Copy, Re-run, Open Log, and Reveal Asset actions
- Renders structured MCP tool invocations as collapsible cards with args, status, result summaries, full-detail drawer, log tail, and a Repair action for failed tool results
- Renders fenced Markdown code blocks as highlighted monospaced blocks and updates streaming `data:` deltas in place when available
- Includes editor context such as current level and selected actor
- Shows connection status against `http://127.0.0.1:8000`

Start the MCP server in SSE mode before opening the chat panel:

```powershell
python unreal_mcp_server\unreal_mcp_server.py --transport sse --mcp-host 0.0.0.0 --mcp-port 8000
```

### Automatic Cursor Replies

The editor chat window is a message bridge. To make Cursor answer automatically, run the watcher in a separate terminal:

```powershell
cd "C:\Dev\Unreal-MCP-Ghost"
npm install
$env:CURSOR_API_KEY = "cursor_..."
npm run chat:agent
```

Useful options:

```powershell
$env:UE_CHAT_SERVER_URL = "http://127.0.0.1:8000"
$env:UE_CHAT_POLL_INTERVAL_MS = "2000"
$env:UE_CHAT_CATCH_UP = "1"
$env:CURSOR_MODEL = "auto"
```

More detail: [`docs/ue-editor-chat-agent.md`](docs/ue-editor-chat-agent.md).

## Knowledge Base

Agents should read repository knowledge before making Unreal changes:

- `docs/knowledge-base/README.md`
- `docs/knowledge-base/unreal-cpp-li-2023.md`
- `docs/knowledge-base/elevating-game-experiences-ue5-2e.md`
- `docs/knowledge-base/game-ai-unreal-sapio-2019.md`
- `knowledge_base/`

## Current Tool Surface

The server currently registers **640 MCP tools**, including:

- Core editor/actor tools
- Blueprint creation, graph editing, node connection, variable/function tools
- UMG/widget tools
- Gameplay framework tools
- AI, Behavior Tree, Blackboard, BT task/decorator/service tools
- Animation Blueprint, IK Rig, IK Retargeter, skeleton, and batch retargeting tools
- Data, struct, enum, DataTable, save-game, input, and Enhanced Input tools
- Material, VFX, Niagara, audio, physics, math, trace, procedural, VR, and variant tools
- Asset import and folder import tools
- GhostRigger bridge tools
- Safe execution substrate, execution journals, action risk evaluation, PIE/log/viewport evidence capture, reflection, diagnostics, source control, project intelligence, C++ bridge, and repair tools
- Higher-level skills such as blueprint health audit, health system creation, vertical slice report packaging, and broken blueprint repair
- Chat tools: `chat_poll_messages`, `chat_send_response`, `chat_get_context`

Use `list_knowledge_base_topics`, `get_knowledge_base`, and `search_knowledge_base` before implementing systems. Use `get_blueprint_nodes`, `get_blueprint_variables`, and `get_blueprint_components` before modifying any Blueprint.

Canonical offline inventory command:

```powershell
python scripts\tool_inventory.py --markdown
```

The inventory uses [unreal_mcp_server/tool_inventory_categories.json](unreal_mcp_server/tool_inventory_categories.json) to map modules to roadmap categories and phases. Keep this in sync when adding new tool modules.

Phase 7 startup/tool-discovery profiler:

```powershell
python scripts\profile_mcp_startup.py --iterations 3 --markdown-out knowledge_base\Reports\mcp_startup_profile.md --json-out knowledge_base\Reports\mcp_startup_profile.json
```

Phase 7 bridge command metadata audit:

```powershell
python scripts\bridge_command_audit.py
```

For repeatable offline CI smoke commands, see [docs/ci-smoke.md](docs/ci-smoke.md).

## Safe Blueprint Workflow

1. Read relevant knowledge docs.
2. Inspect current state:
   - `get_blueprint_nodes`
   - `get_blueprint_variables`
   - `get_blueprint_components`
   - `get_blueprint_graphs`
3. Report findings and plan.
4. Make one scoped change.
5. Compile and save.
6. Read back and verify.
7. Keep the project playable after each change.

Never hard-code node IDs. Always query nodes after creation before connecting pins.

## Troubleshooting

### `/chat/history` or `/chat/poll` returns 404

You are running an old MCP server process. Stop the process listening on port 8000 and restart the current server:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen | Select-Object OwningProcess
Stop-Process -Id <PID> -Force
python unreal_mcp_server\unreal_mcp_server.py --transport sse --mcp-host 0.0.0.0 --mcp-port 8000
```

### Editor chat says "MCP Server offline"

- Confirm the SSE server is running on port `8000`.
- Confirm `/chat/history` returns `200`.
- Close and reopen `Window > MCP Chat`.

### AI cannot reach Unreal

- Confirm Unreal Editor is open.
- Confirm Output Log says the bridge started on `127.0.0.1:55557`.
- Confirm no firewall or tunnel is blocking the port.
- Restart the MCP server after restarting Unreal.

### Build fails with Live Coding active

Close Unreal Editor or press `Ctrl+Alt+F11`, then rebuild.

### PawnSensing deprecation warnings

The plugin suppresses the known UE 5.6 deprecation warning around legacy `UPawnSensingComponent` usage. New AI work should prefer AI Perception.

## Updating the Plugin in a Project

From a clean repo checkout:

```powershell
cd "C:\Dev\Unreal-MCP-Ghost"
git fetch origin
git status
```

Review local changes before updating. Then copy the plugin source into your project:

```powershell
$REPO    = "C:\Dev\Unreal-MCP-Ghost"
$PROJECT = "C:\Users\You\Documents\UnrealProjects\MyGame"

Stop-Process -Name UnrealEditor -Force -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$PROJECT\Plugins\UnrealMCP\Binaries" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$PROJECT\Plugins\UnrealMCP\Intermediate" -ErrorAction SilentlyContinue
Copy-Item -Recurse -Force "$REPO\unreal_plugin\*" "$PROJECT\Plugins\UnrealMCP\"
```

Regenerate project files and rebuild `Development Editor | Win64`.

## License

Based on [chongdashu/unreal-mcp](https://github.com/chongdashu/unreal-mcp). Extended under the same MIT license.
