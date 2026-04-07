# UnrealMCP Plugin — Setup Guide for Unreal Engine 5.6

This plugin is the C++ bridge that allows the MCP Python server to communicate
with the Unreal Engine 5.6 editor. It opens a TCP server on port **55557** inside
the editor and executes Blueprint creation commands sent by the MCP server.

---

## ⚠️ Prerequisites

Before installing this plugin you need:

| Tool | Version | Download |
|------|---------|----------|
| Unreal Engine | **5.6** | Epic Games Launcher |
| Visual Studio | **2022** (Community is free) | visualstudio.microsoft.com |
| VS Workload | **"Game Development with C++"** | Select during VS install |
| .NET SDK | 6.0 or newer (usually installed with VS) | dotnet.microsoft.com |

> **Important:** The "Game Development with C++" workload in Visual Studio is
> required. Without it, the plugin will fail to compile. During VS installation,
> check this workload — it installs the C++ compiler, Windows SDK, and UE
> integration headers.

---

## 📁 Step 1: Copy the Plugin to Your Project

Your Unreal project folder should look like this when you are done:

```
YourProject/
├── YourProject.uproject
├── Content/
├── Source/
└── Plugins/                    ← Create this folder if it doesn't exist
    └── UnrealMCP/              ← Copy this entire folder here
        ├── UnrealMCP.uplugin   ← Plugin descriptor (targets UE 5.6)
        └── Source/
            └── UnrealMCP/
                ├── UnrealMCP.Build.cs
                ├── Public/
                │   └── Commands/
                │       └── UnrealMCPExtendedCommands.h
                └── Private/
                    └── Commands/
                        └── UnrealMCPExtendedCommands.cpp
```

**Copy the entire `unreal_plugin/` folder** from this repository into your
project's `Plugins/` folder, then rename it from `unreal_plugin` to `UnrealMCP`.

---

## 🔧 Step 2: Install the Base Plugin First

This plugin **extends** the original `chongdashu/unreal-mcp` plugin. You need
the base plugin installed first, then apply the patch from this repo on top.

### 2A. Get the base plugin
```bash
# Clone the base plugin (separate from this repo)
git clone https://github.com/chongdashu/unreal-mcp.git
```

Copy its plugin folder into your project's `Plugins/` directory the same way.

### 2B. Apply the integration patch
The file `UnrealMCPBridge_Integration.patch` in this repo describes exactly what
to add to the base plugin's `UnrealMCPBridge.cpp` and `.h` files. Open those
files and follow the 6 steps in the patch file to wire in the extended commands.

---

## 🔨 Step 3: Compile the Plugin

1. **Right-click** your `.uproject` file in File Explorer
2. Select **"Generate Visual Studio project files"**
3. Open the generated `.sln` file in Visual Studio 2022
4. Set the build target to **Development Editor | Win64**
5. Press **Ctrl+Shift+B** to build
6. Wait 3–10 minutes for first compilation

**OR** — simply open the project in Unreal Engine 5.6. It will detect the new
plugin and prompt you to rebuild. Click **Yes** and it compiles automatically.

---

## ✅ Step 4: Enable the Plugin in UE 5.6

1. Open your project in Unreal Engine 5.6
2. Go to **Edit → Plugins**
3. Search for **"UnrealMCP"**
4. Make sure the checkbox is **enabled**
5. Restart the editor if prompted

---

## 🔍 Step 5: Verify It's Running

Open the **Output Log** in UE (Window → Output Log) and look for:

```
LogUnrealMCP: TCP Server listening on port 55557
```

If you see this line, the plugin is running and ready to receive MCP commands.

---

## 🐍 Step 6: Run the MCP Python Server

In a separate terminal/Command Prompt:

```bash
cd path/to/Unreal-MCP-Ghost/unreal_mcp_server
pip install mcp asyncio aiohttp
python unreal_mcp_server.py
```

Expected output:
```
[MCP] Unreal MCP Server starting...
[MCP] 283 tools registered across 18 modules
[MCP] Server ready — connect your AI client
```

---

## 🖱️ Step 7: Connect Cursor (AI Client)

Create or edit `%APPDATA%\Cursor\User\mcp.json` (Windows) or
`~/.cursor/mcp.json` (Mac/Linux):

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

Restart Cursor. In the AI chat, you should now be able to say things like:

```
Create a BP_Enemy Blueprint with 100 health, an AIController, 
and a Behavior Tree for patrol and chase behavior.
```

And the Blueprint will appear in your Content Browser instantly.

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| "Plugin failed to compile" | Make sure VS 2022 + "Game Development with C++" workload is installed |
| Port 55557 already in use | Kill existing process: `netstat -ano \| findstr 55557` |
| No output log message | Check plugin is enabled in Edit → Plugins |
| Cursor doesn't see tools | Restart Cursor after editing mcp.json |
| "Unknown command" errors | Make sure the patch was applied to UnrealMCPBridge.cpp |
| VariantManager compile error | Skip that module — comment out the VariantManager lines in Build.cs if your UE install doesn't include it |

---

## 📦 What This Plugin Adds (283 Tools)

The extended commands in this plugin cover all 20 chapters of
*Blueprints Visual Scripting for Unreal Engine 5* by Marcos Romero:

- **Flow Control**: Branch, Sequence, FlipFlop, DoOnce, DoN, Gate, ForEachLoop, WhileLoop
- **Variables**: Get/Set variable nodes, all container types (Array, Set, Map)
- **AI / Behavior Trees**: Full BT asset creation, tasks, decorators, services, blackboard
- **Materials**: Create materials, dynamic instances, parameter nodes, hit swaps
- **Save Systems**: SaveGame class creation, save/load slots, round systems, pause menus
- **UMG Widgets**: Full HUD creation, buttons, sliders, checkboxes, animations
- **Animation**: Animation Blueprints, state machines, blend spaces
- **Physics**: Traces (line/sphere/capsule/box), transforms, collision, debug draw
- **Procedural**: Splines, instanced meshes, PCG, editor utility Blueprints
- **VR**: VR Pawn, motion controllers, grab components, teleportation
- **Variant Manager**: Level Variant Sets, product configurator
- **Libraries**: Function libraries, macro libraries, actor/scene components
- **Data**: Structs, Enums, DataTables, Switch nodes, MultiGate
- **Communication**: Event dispatchers, Blueprint interfaces, direct references
- **Gameplay**: Game modes, player controllers, game instances, HUD, overlaps

---

*Plugin version 1.0.0 — Unreal Engine 5.6 — April 2026*
