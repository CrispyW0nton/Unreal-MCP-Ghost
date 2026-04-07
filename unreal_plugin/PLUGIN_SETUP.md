# UnrealMCP Plugin — Standalone Setup Guide for Unreal Engine 5.6

This is a **fully standalone** C++ plugin. No external plugins or repositories
required. Clone this repo, copy one folder into your project, compile, done.

---

## ⚠️ Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| Unreal Engine | **5.6** | Epic Games Launcher → Library |
| Visual Studio | **2022** (Community is free) | visualstudio.microsoft.com |
| VS Workload | **"Game Development with C++"** | Select during VS install |

> **The single most common mistake:** Forgetting the "Game Development with C++"
> workload in Visual Studio. If the plugin fails to compile, this is why.
> Reinstall/modify VS and check that workload.

---

## 📁 Step 1: Copy the Plugin Into Your Project

Your project folder should look like this when done:

```
YourGame/
├── YourGame.uproject
├── Content/
├── Source/
└── Plugins/                         ← Create this if it doesn't exist
    └── UnrealMCP/                   ← Copy this entire folder here
        ├── UnrealMCP.uplugin
        └── Source/
            └── UnrealMCP/
                ├── UnrealMCP.Build.cs
                ├── Public/
                │   ├── UnrealMCPBridge.h
                │   ├── UnrealMCPModule.h
                │   ├── MCPServerRunnable.h
                │   └── Commands/
                │       ├── UnrealMCPEditorCommands.h
                │       ├── UnrealMCPBlueprintCommands.h
                │       ├── UnrealMCPBlueprintNodeCommands.h
                │       ├── UnrealMCPProjectCommands.h
                │       ├── UnrealMCPUMGCommands.h
                │       ├── UnrealMCPCommonUtils.h
                │       └── UnrealMCPExtendedCommands.h   ← Our 283 tools
                └── Private/
                    ├── UnrealMCPBridge.cpp
                    ├── UnrealMCPModule.cpp
                    ├── MCPServerRunnable.cpp
                    └── Commands/
                        ├── UnrealMCPEditorCommands.cpp
                        ├── UnrealMCPBlueprintCommands.cpp
                        ├── UnrealMCPBlueprintNodeCommands.cpp
                        ├── UnrealMCPProjectCommands.cpp
                        ├── UnrealMCPUMGCommands.cpp
                        ├── UnrealMCPCommonUtils.cpp
                        └── UnrealMCPExtendedCommands.cpp ← Our 283 tools
```

**How to do it:**
1. Open the cloned repo folder
2. Copy the entire `unreal_plugin/` folder
3. Paste it into your project's `Plugins/` directory
4. Rename it from `unreal_plugin` to `UnrealMCP`

---

## 🔨 Step 2: Compile the Plugin

**Option A — Let UE compile it automatically (recommended):**
1. Open your `.uproject` in Unreal Engine 5.6
2. UE detects the new plugin and shows a dialog: **"Missing modules"**
3. Click **"Yes"** to rebuild
4. Wait 3–8 minutes for first compilation

**Option B — Compile manually in Visual Studio:**
1. Right-click your `.uproject` → **"Generate Visual Studio project files"**
2. Open the `.sln` in Visual Studio 2022
3. Set configuration to **Development Editor | Win64**
4. Press **Ctrl+Shift+B** to build

---

## ✅ Step 3: Enable the Plugin

1. Open your project in UE 5.6
2. Go to **Edit → Plugins**
3. Search for **"UnrealMCP"**
4. Check the box to enable it
5. Restart the editor if prompted

**Verify it's working** — open the Output Log (Window → Output Log) and look for:
```
LogTemp: Display: UnrealMCPBridge: Server started on 127.0.0.1:55557
```

---

## 🐍 Step 4: Run the MCP Python Server

Open a terminal/Command Prompt and run:

```bash
# Install dependencies (one-time)
pip install mcp asyncio aiohttp

# Start the server
cd path/to/Unreal-MCP-Ghost/unreal_mcp_server
python unreal_mcp_server.py
```

Expected output:
```
[MCP] Unreal MCP Server starting...
[MCP] 283 tools registered across 18 modules
[MCP] Server ready — connect your AI client
```

Keep this window open while you work.

---

## 🖱️ Step 5: Connect Cursor (AI Client)

### Install Cursor
Download from **cursor.com** — free tier works for this.

### Configure MCP in Cursor
Create or edit the Cursor MCP config file:

- **Windows:** `%APPDATA%\Cursor\User\mcp.json`
- **Mac:** `~/.cursor/mcp.json`

```json
{
  "mcpServers": {
    "unreal-mcp": {
      "command": "python",
      "args": ["C:/path/to/Unreal-MCP-Ghost/unreal_mcp_server/unreal_mcp_server.py"]
    }
  }
}
```

Replace the path with your actual clone location. Restart Cursor.

---

## 🎮 Step 6: Start Building

With UE 5.6 open, MCP server running, and Cursor connected, open Cursor's AI
chat and describe what you want. Examples:

```
Create a BP_Enemy Blueprint with 100 health, a Behavior Tree 
for patrol and chase, and an AIController that auto-possesses it.
```

```
Create a full save game system with a SG_PlayerData class storing
score, health, and current level. Add save/load to the player BP.
```

```
Create a HUD widget with a health bar top-left, ammo counter 
bottom-right, and a score display at the top center.
```

The Blueprint appears in your Content Browser instantly. ✅

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---------|-----|
| Plugin fails to compile | Install VS 2022 with "Game Development with C++" workload |
| VariantManager compile error | Open Build.cs, comment out the VariantManager lines |
| Port 55557 in use | Run: `netstat -ano \| findstr 55557` then kill the PID |
| No log message in UE | Check Edit → Plugins → UnrealMCP is enabled |
| Cursor doesn't see tools | Restart Cursor after editing mcp.json |
| "Unknown command" errors | Make sure the Python MCP server is running |

### Disabling Variant Manager (if needed)
If your UE 5.6 install doesn't include the Variant Manager plugin, open
`Source/UnrealMCP/UnrealMCP.Build.cs` and comment out these two lines:

```csharp
// "VariantManager",
// "VariantManagerContent",
```

---

## 📦 What's Included — 283 Tools Across 18 Modules

| Module | Tools | Covers |
|--------|-------|--------|
| Blueprint Tools | 7 | Create blueprints, add components, compile |
| Blueprint Node Tools | 8 | Event nodes, function nodes, variable nodes, connections |
| Editor Tools | 9 | Spawn/find/delete actors, transforms, screenshots |
| Project Tools | 3 | Input mappings |
| UMG Tools | 19 | Widgets, buttons, text blocks, sliders, checkboxes, animations |
| Gameplay Tools | 11 | Game modes, controllers, game instances, HUD, overlaps |
| Communication Tools | 13 | Event dispatchers, interfaces, direct references |
| Data Tools | 33 | Arrays, Maps, Sets, Structs, Enums, DataTables, Switch nodes |
| Advanced Node Tools | 57 | Math, logic, flow control, timelines, traces, delays, timers |
| AI Tools | 23 | Behavior Trees, Blackboards, AIControllers, BT Tasks/Decorators |
| Animation Tools | 8 | Animation Blueprints, state machines, blend spaces |
| Physics Tools | 39 | Transforms, vectors, line/sphere/capsule/box traces, collision |
| Material Tools | 10 | Create materials, dynamic instances, parameter nodes |
| Save/Game State Tools | 14 | SaveGame class, save/load slots, pause, round systems |
| Library Tools | 12 | Function libraries, macro libraries, actor components, timers |
| Procedural Tools | 13 | Splines, instanced meshes, PCG, editor utilities |
| VR Tools | 12 | VR Pawn, motion controllers, grab, teleportation |
| Variant Tools | 7 | Level Variant Sets, product configurator |

Covers all 20 chapters of *Blueprints Visual Scripting for Unreal Engine 5*
by Marcos Romero — 566 pages, 100% audit coverage.

---

*UnrealMCP v1.0.0 — Unreal Engine 5.6 — Standalone — April 2026*
