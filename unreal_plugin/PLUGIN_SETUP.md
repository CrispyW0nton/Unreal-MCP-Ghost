# UnrealMCP Plugin — Standalone Setup Guide for Unreal Engine 5.6

This is a **fully standalone** plugin. No external dependencies, no separate
repos to clone. Drop this one folder into your project and you're done.

---

## ✅ What This Plugin Does

Opens a TCP server on port **55557** inside the Unreal Editor. The Python MCP
server connects to it and forwards AI commands (from Cursor or Claude Desktop)
that create and manipulate Blueprints, actors, materials, AI systems, UMG
widgets, save systems, VR setups, procedural generation, and more — all 283
tools covering every chapter of *Blueprints Visual Scripting for Unreal Engine 5*.

---

## 📋 Prerequisites

| Tool | Version | Where to Get It |
|------|---------|-----------------|
| Unreal Engine | **5.6** | Epic Games Launcher |
| Visual Studio | **2022** Community (free) | visualstudio.microsoft.com |
| VS Workload | **"Game Development with C++"** | Select during VS install |
| Python | **3.10+** | python.org |
| Git | Latest | git-scm.com |
| Cursor | Latest | cursor.com |

> ⚠️ **The "Game Development with C++" workload is required.**
> Without it the plugin will fail to compile with a cryptic error.
> Open Visual Studio Installer → Modify → check that workload → Install.

---

## 📁 Step 1: Copy the Plugin Into Your Project

Your finished folder structure should look exactly like this:

```
YourProject/
├── YourProject.uproject
├── Content/
├── Source/
└── Plugins/
    └── UnrealMCP/                          ← This entire folder
        ├── UnrealMCP.uplugin
        └── Source/
            └── UnrealMCP/
                ├── UnrealMCP.Build.cs
                ├── Public/
                │   ├── UnrealMCPBridge.h
                │   ├── UnrealMCPModule.h
                │   ├── MCPServerRunnable.h
                │   └── Commands/
                │       ├── UnrealMCPCommonUtils.h
                │       ├── UnrealMCPEditorCommands.h
                │       ├── UnrealMCPBlueprintCommands.h
                │       ├── UnrealMCPBlueprintNodeCommands.h
                │       ├── UnrealMCPProjectCommands.h
                │       ├── UnrealMCPUMGCommands.h
                │       └── UnrealMCPExtendedCommands.h
                └── Private/
                    ├── UnrealMCPBridge.cpp
                    ├── UnrealMCPModule.cpp
                    ├── MCPServerRunnable.cpp
                    └── Commands/
                        ├── UnrealMCPCommonUtils.cpp
                        ├── UnrealMCPEditorCommands.cpp
                        ├── UnrealMCPBlueprintCommands.cpp
                        ├── UnrealMCPBlueprintNodeCommands.cpp
                        ├── UnrealMCPProjectCommands.cpp
                        ├── UnrealMCPUMGCommands.cpp
                        └── UnrealMCPExtendedCommands.cpp
```

**How to do it:**
1. Open File Explorer and go to your UE project folder
2. Create a `Plugins` folder if one does not already exist
3. Copy the `unreal_plugin` folder from this repo into `Plugins/`
4. Rename it from `unreal_plugin` to `UnrealMCP`

---

## 🔨 Step 2: Compile the Plugin

**Easiest method — let UE do it:**
1. Double-click your `.uproject` file
2. UE will detect the new plugin and say **"The following modules are missing or built with a different engine version. Would you like to rebuild them now?"**
3. Click **Yes**
4. Wait 3–8 minutes for first-time compilation
5. The editor opens normally when done

**Alternative — compile manually in Visual Studio:**
1. Right-click your `.uproject` → **"Generate Visual Studio project files"**
2. Open the `.sln` in Visual Studio 2022
3. Set target to **Development Editor | Win64**
4. Press **Ctrl+Shift+B**

---

## ✅ Step 3: Enable the Plugin

1. In UE 5.6 go to **Edit → Plugins**
2. Search **"UnrealMCP"**
3. Make sure it is **checked/enabled**
4. Restart the editor if prompted

**Verify it is running** — open the Output Log (Window → Output Log) and look for:
```
LogTemp: Display: UnrealMCPBridge: Server started on 127.0.0.1:55557
```

---

## 🐍 Step 4: Run the Python MCP Server

Clone this repo if you haven't already:
```powershell
# Recommended location — keeps dev tools organized, off the Desktop
cd C:\Users\NewAdmin\Documents\KotorMods\Tools
git clone https://github.com/CrispyW0nton/Unreal-MCP-Ghost.git
cd Unreal-MCP-Ghost
git checkout genspark_ai_developer
```

Install dependencies and start the server:
```bash
pip install mcp asyncio aiohttp
python unreal_mcp_server/unreal_mcp_server.py
```

Expected output:
```
[MCP] Unreal MCP Server starting...
[MCP] 283 tools registered across 18 modules
[MCP] Server ready — connect your AI client
```

Keep this terminal window open while you work.

---

## 🖱️ Step 5: Connect Cursor

1. Open Cursor
2. Press **Ctrl+Shift+P** → type **"Open MCP Settings"** → Enter
3. Add a new server entry, or manually edit the config file

**Config file location:**
- Windows: `%APPDATA%\Cursor\User\mcp.json`
- macOS: `~/.cursor/mcp.json`

**Contents:**
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

Replace the path with your actual clone location, e.g.:
`C:/Users/NewAdmin/Documents/KotorMods/Tools/Unreal-MCP-Ghost/unreal_mcp_server/unreal_mcp_server.py`

4. **Restart Cursor**
5. Open the AI chat panel — you should see "unreal-mcp" listed as an available tool

---

## 🧪 Step 6: Test the Full Pipeline

With all three running simultaneously:
- ✅ Unreal Engine 5.6 open with your project (Output Log shows port 55557)
- ✅ Python MCP server running in terminal
- ✅ Cursor open with MCP configured

In Cursor's AI chat, type:
```
Create a Blueprint Actor called BP_TestCube in /Game/Blueprints
with a Static Mesh component and a float variable called Health
defaulting to 100.0, then compile it.
```

**If it works:** `BP_TestCube` appears in your Content Browser immediately. 🎉

---

## 💬 Example Prompts to Try

### Basic Blueprint
```
Create a Blueprint Actor called BP_Pickup with a Static Mesh component,
a bool variable called bIsCollected defaulting to false, and an
OnBeginOverlap event that sets bIsCollected to true and destroys the actor.
```

### Enemy AI
```
Create a complete enemy AI system with:
- BP_Enemy character with 100 health and 10 damage
- BT_EnemyBehavior behavior tree with patrol and chase states
- BB_Enemy blackboard with PlayerCharacter and TargetLocation keys
- BP_EnemyController AIController that auto-runs BT_EnemyBehavior
```

### HUD / UI
```
Create a HUD widget called WBP_GameHUD with:
- A health bar in the top left
- A score text block in the top center
- An ammo counter in the bottom right
- Bind them all to variables on the player character
```

### Save System
```
Create a SaveGame system with a SG_PlayerData class that stores
Score (int), Level (int), and PlayerHealth (float).
Add save-on-exit and load-on-begin-play to the GameMode.
```

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---------|-----|
| Plugin won't compile | Install VS 2022 with "Game Development with C++" workload |
| "Module not found" on startup | Right-click .uproject → Generate VS files → rebuild |
| Port 55557 already in use | Run: `netstat -ano \| findstr 55557` then `taskkill /PID [number] /F` |
| Output Log shows no server message | Check Edit → Plugins → UnrealMCP is enabled |
| Cursor doesn't list the tools | Restart Cursor after saving mcp.json |
| VariantManager compile error | Open Build.cs and comment out the two VariantManager lines |
| "Unknown command" in Output Log | Make sure the Python server is running and connected |

---

## 📦 What's Inside (283 Tools)

| Module | Tools | Book Chapters |
|--------|-------|---------------|
| advanced_node_tools | 57 | 2, 3, 5, 6, 8, 13, 14, 15 |
| ai_tools | 23 | 9, 10 |
| animation_tools | 8 | 17 |
| blueprint_tools | 7 | 1, 2, 3 |
| communication_tools | 13 | 4 |
| data_tools | 33 | 13 |
| editor_tools | 9 | 1 |
| gameplay_tools | 11 | 3, 5, 6 |
| library_tools | 12 | 18 |
| material_tools | 10 | 5, 6, 9, 10 |
| node_tools | 8 | 2, 3 |
| physics_tools | 39 | 14 |
| procedural_tools | 13 | 19 |
| project_tools | 3 | 1 |
| savegame_tools | 14 | 8, 11, 12 |
| umg_tools | 19 | 7 |
| variant_tools | 7 | 20 |
| vr_tools | 12 | 16 |

---

*Plugin v1.0.0 — Unreal Engine 5.6 — Standalone — April 2026*
*Based on original TCP architecture from chongdashu/unreal-mcp (MIT License)*
*Extended with 283 Blueprint Visual Scripting tools by CrispyW0nton*
