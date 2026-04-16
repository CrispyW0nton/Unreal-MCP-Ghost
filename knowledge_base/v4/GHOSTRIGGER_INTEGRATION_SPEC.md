# Unreal-MCP-Ghost ↔ GhostRigger Integration Specification

> Deep research findings on both codebases with implementation specs for bridging them.

---

## 1. DISCOVERY: GhostRigger Already Has MCP Endpoints

**Critical finding**: GhostRigger's IPC server (`src/ipc/server.py`) already exposes MCP-compatible endpoints alongside its Ghostworks Pipeline IPC. This means we can bridge directly.

### GhostRigger IPC Server (Port 7001)
```
Flask-based HTTP server on http://localhost:7001

Pipeline Actions (Ghostworks IPC):
  POST /api/open_utc    — open creature blueprint
  POST /api/open_utp    — open placeable blueprint
  POST /api/open_utd    — open door blueprint
  POST /api/open_mdl    — open 3D model for viewing/editing
  POST /api/ping        — health check
  GET  /api/health      — returns {"status":"ok","program":"GhostRigger","mcp":true}

MCP Endpoints (KotorMCP):
  GET/POST /mcp/tools/list       — list all KotOR MCP tools
  POST     /mcp/tools/call       — call tool: {"name":"toolName","arguments":{...}}
  GET/POST /mcp/resources/list   — list kotor:// resource URIs
  POST     /mcp/resources/read   — read resource: {"uri":"kotor://k1/2da/appearance"}
```

### GhostRigger IPC Client (src/ipc/client.py)
```python
# Low-level call pattern — we replicate this in unreal_mcp_server
def ipc_call(port, action, payload=None, sender="GhostRigger", timeout=2.0):
    url = f"http://127.0.0.1:{port}/api/{action}"
    body = {"version": "1.0", "sender": sender, "action": action, "payload": payload or {}}
    resp = requests.post(url, json=body, timeout=timeout)
    return resp.json()
```

### Ghostworks Pipeline Port Map
| Program | Port | Role |
|---------|------|------|
| GhostRigger | 7001 | 3D model viewer, rigger, converter |
| GhostScripter | 7002 | Script editor, dialogue editor |
| GModular | 7003 | Module editor, world builder |

### GhostRigger Mesh Converter (src/converters/mesh_converter.py)
- **OBJExporter**: Exports KotorModel → OBJ + MTL (with rigging data)
- **FBXExporter**: Exports KotorModel → FBX (with skeleton and skin weights)
- GLTFExporter referenced but may not be fully implemented
- Uses `KotorModel`, `ModelNode`, `VertexSkinData`, `BoneWeight` from `core.model_data`

### GhostRigger Auto-Rigger (src/autorig/auto_rigger.py)
- Aurora-compatible skeleton generation for humanoid / creature / prop
- Library Rig: copy any model's rig onto current mesh
- GRig: manual bone assignment with weight painting
- AcuRig: guide-based biped rig with symmetry enforcement

---

## 2. INTEGRATION ARCHITECTURE

### Target System Map
```
┌─────────────────────────────────────────────────────────────────────┐
│                    AI AGENT (Claude / GenSpark)                      │
│         "Export the Bastila model, rig it, import into UE5"         │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ MCP tools
┌───────────────────────────────▼─────────────────────────────────────┐
│              unreal_mcp_server.py (311+ tools)                       │
│                                                                      │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────────────┐  │
│  │ UE5 Tools    │  │ GhostRigger      │  │ Folder Import         │  │
│  │ (TCP:55557)  │  │ Bridge Tools     │  │ Tools                 │  │
│  │              │  │ (HTTP:7001)      │  │ (Filesystem)          │  │
│  │ 311 existing │  │ NEW ~15 tools    │  │ NEW ~8 tools          │  │
│  └──────┬───────┘  └────────┬─────────┘  └──────────┬────────────┘  │
└─────────┼──────────────────┼────────────────────────┼───────────────┘
          │                  │                        │
          │ TCP              │ HTTP                   │ OS filesystem
          │                  │                        │
┌─────────▼──────┐  ┌───────▼─────────┐  ┌──────────▼─────────────┐
│  UE5 C++ Plugin│  │  GhostRigger    │  │  Export Folder         │
│  Port 55557    │  │  Port 7001      │  │  (User's disk)         │
│  119 commands  │  │  IPC + MCP      │  │  FBX/OBJ/glTF/WAV/PNG │
│                │  │  5007 tests     │  │                        │
│  ┌───────────┐ │  │  ┌────────────┐ │  │  Watched or scanned   │
│  │exec_python│ │  │  │KotorMCP    │ │  │  by import tools      │
│  │(full API) │ │  │  │tools       │ │  │                        │
│  └───────────┘ │  │  └────────────┘ │  └────────────────────────┘
└────────────────┘  └─────────────────┘
```

### Communication Protocols
| Connection | Protocol | Port | Direction |
|------------|----------|------|-----------|
| MCP Server → UE5 Plugin | TCP JSON | 55557 | Server → Plugin |
| MCP Server → GhostRigger | HTTP JSON | 7001 | Server → GhostRigger |
| GhostRigger → GModular | HTTP JSON | 7003 | GhostRigger → GModular |
| MCP Server → Filesystem | OS API | N/A | Server reads export folder |

---

## 3. NEW TOOL SPECIFICATIONS

### 3A. GhostRigger Bridge Tools (HTTP to port 7001)

These tools let the AI agent control GhostRigger remotely through the MCP server.

#### `ghostrigger_ping`
```python
@mcp_server.tool()
async def ghostrigger_ping() -> str:
    """Check if GhostRigger is running.
    Returns: {"running": true/false, "version": "...", "mcp": true/false}
    """
    import requests, json
    try:
        resp = requests.get("http://127.0.0.1:7001/api/health", timeout=2)
        return json.dumps(resp.json())
    except requests.exceptions.ConnectionError:
        return json.dumps({"running": False, "error": "GhostRigger not running on port 7001"})
```

#### `ghostrigger_open_model`
```python
@mcp_server.tool()
async def ghostrigger_open_model(resref: str, module_dir: str = "") -> str:
    """Open a KotOR model in GhostRigger for viewing/editing.
    
    Args:
        resref: Model resource reference (e.g., 'c_bastila', 'p_hk47')
        module_dir: Optional module directory path
    """
    import requests, json
    try:
        resp = requests.post("http://127.0.0.1:7001/api/open_mdl", 
            json={"version": "1.0", "sender": "UnrealMCP", "action": "open_mdl",
                  "payload": {"resref": resref, "module_dir": module_dir}},
            timeout=5)
        return json.dumps(resp.json())
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
```

#### `ghostrigger_list_kotor_tools`
```python
@mcp_server.tool()
async def ghostrigger_list_kotor_tools() -> str:
    """List all available KotOR MCP tools from GhostRigger."""
    import requests, json
    resp = requests.get("http://127.0.0.1:7001/mcp/tools/list", timeout=5)
    return json.dumps(resp.json())
```

#### `ghostrigger_call_kotor_tool`
```python
@mcp_server.tool()
async def ghostrigger_call_kotor_tool(tool_name: str, arguments: str = "{}") -> str:
    """Call a KotOR MCP tool via GhostRigger.
    
    Args:
        tool_name: Name of the KotOR tool to call
        arguments: JSON string of arguments for the tool
    """
    import requests, json
    args = json.loads(arguments) if isinstance(arguments, str) else arguments
    resp = requests.post("http://127.0.0.1:7001/mcp/tools/call",
        json={"name": tool_name, "arguments": args}, timeout=30)
    return json.dumps(resp.json())
```

#### `ghostrigger_read_kotor_resource`
```python
@mcp_server.tool()
async def ghostrigger_read_kotor_resource(uri: str) -> str:
    """Read a KotOR resource from GhostRigger.
    
    Args:
        uri: KotOR resource URI (e.g., 'kotor://k1/2da/appearance', 'kotor://k2/model/c_bastila')
    """
    import requests, json
    resp = requests.post("http://127.0.0.1:7001/mcp/resources/read",
        json={"uri": uri}, timeout=10)
    return json.dumps(resp.json())
```

#### `ghostrigger_export_model`
```python
@mcp_server.tool()
async def ghostrigger_export_model(
    resref: str,
    export_format: str = "fbx",
    output_dir: str = "",
    auto_rig: bool = True,
    export_animations: bool = True
) -> str:
    """Export a KotOR model from GhostRigger to FBX/OBJ/glTF for UE5 import.
    
    This is a compound operation:
    1. Opens the model in GhostRigger
    2. Auto-rigs if requested
    3. Exports to the specified format
    4. Returns the exported file path for UE5 import
    
    Args:
        resref: Model resource reference (e.g., 'c_bastila')
        export_format: 'fbx', 'obj', or 'gltf'
        output_dir: Export directory (default: temp dir)
        auto_rig: Auto-rig the model before export (default: True)
        export_animations: Include animations in export (default: True)
    """
    # Implementation calls GhostRigger's KotorMCP tools:
    # 1. Call kotor tool to load model
    # 2. Call auto-rig tool if auto_rig=True
    # 3. Call export tool with format
    # 4. Return file path
```

#### `ghostrigger_export_and_import_to_ue5`
```python
@mcp_server.tool()
async def ghostrigger_export_and_import_to_ue5(
    resref: str,
    export_format: str = "fbx",
    ue5_destination: str = "/Game/KotOR/",
    auto_rig: bool = True,
    import_as_skeletal: bool = True
) -> str:
    """End-to-end pipeline: KotOR model → GhostRigger export → UE5 import.
    
    Combines GhostRigger export with UE5 import in one operation.
    
    Args:
        resref: KotOR model reference
        export_format: Export format (fbx recommended for skeletal)
        ue5_destination: UE5 Content Browser destination path
        auto_rig: Auto-rig before export
        import_as_skeletal: Import as SkeletalMesh (True) or StaticMesh (False)
    """
    # 1. Export from GhostRigger → temp file
    # 2. Call import_skeletal_mesh or import_static_mesh on the temp file
    # 3. Return imported asset path
```

### 3B. Folder-Based Batch Import Tools (Filesystem)

These tools scan a directory of pre-exported assets and import them all into UE5.

#### `scan_export_folder`
```python
@mcp_server.tool()
async def scan_export_folder(
    folder_path: str,
    recursive: bool = True
) -> str:
    """Scan a folder for importable assets and return a manifest.
    
    Detects: FBX, OBJ, glTF/GLB, WAV, OGG, MP3, PNG, JPG, TGA, EXR, HDR
    
    Args:
        folder_path: Absolute OS path to scan
        recursive: Scan subdirectories (default: True)
    
    Returns: JSON manifest with categorized files and counts.
    """
    code = f'''
import os, json

MESH_EXTS = {{'.fbx', '.obj', '.gltf', '.glb'}}
TEX_EXTS = {{'.png', '.jpg', '.jpeg', '.tga', '.exr', '.hdr', '.bmp', '.tif', '.tiff'}}
AUDIO_EXTS = {{'.wav', '.ogg', '.mp3', '.flac'}}
ANIM_EXTS = {{'.bvh'}}

manifest = {{"meshes": [], "textures": [], "audio": [], "animations": [], "other": []}}
folder = r"{folder_path}"

for root, dirs, files in os.walk(folder) if {recursive} else [(folder, [], os.listdir(folder))]:
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        fpath = os.path.join(root if isinstance(root, str) else folder, f)
        entry = {{"filename": f, "path": fpath, "size_kb": os.path.getsize(fpath) // 1024}}
        if ext in MESH_EXTS:
            manifest["meshes"].append(entry)
        elif ext in TEX_EXTS:
            manifest["textures"].append(entry)
        elif ext in AUDIO_EXTS:
            manifest["audio"].append(entry)
        elif ext in ANIM_EXTS:
            manifest["animations"].append(entry)
        else:
            entry["extension"] = ext
            manifest["other"].append(entry)

summary = {{k: len(v) for k, v in manifest.items()}}
manifest["summary"] = summary
manifest["total"] = sum(summary.values())
print(json.dumps(manifest))
'''
    # This runs on the MCP server side (Python), NOT exec_python
    # because it reads the local filesystem, not UE5
    import os, json
    # ... (implementation mirrors the code above but runs locally)
```

#### `batch_import_folder`
```python
@mcp_server.tool()
async def batch_import_folder(
    folder_path: str,
    ue5_base_path: str = "/Game/Imported/",
    import_meshes: bool = True,
    import_textures: bool = True,
    import_audio: bool = True,
    mesh_import_as_skeletal: bool = False,
    auto_create_materials: bool = True,
    organize_by_type: bool = True
) -> str:
    """Batch import all assets from a folder into UE5 Content Browser.
    
    Scans the folder, categorizes files, and imports them with appropriate
    settings. Optionally organizes into subfolders by type.
    
    Args:
        folder_path: OS path to the folder of exported assets
        ue5_base_path: Content Browser root for imported assets
        import_meshes: Import FBX/OBJ/glTF files (default: True)
        import_textures: Import PNG/JPG/TGA files (default: True)
        import_audio: Import WAV/OGG/MP3 files (default: True)
        mesh_import_as_skeletal: Treat meshes as skeletal (default: False)
        auto_create_materials: Auto-create materials from textures (default: True)
        organize_by_type: Create Meshes/, Textures/, Audio/ subfolders (default: True)
    
    Returns: JSON with import results for each file.
    """
    # Implementation:
    # 1. Scan folder (reuse scan_export_folder logic)
    # 2. Create UE5 destination folders via exec_python
    # 3. Build AssetImportTask list for all files
    # 4. Execute batch import via exec_python
    # 5. If auto_create_materials, run create_material_from_textures for each texture set
    # 6. Return results
```

#### `watch_export_folder`
```python
@mcp_server.tool()
async def watch_export_folder(
    folder_path: str,
    ue5_base_path: str = "/Game/Imported/",
    poll_interval: int = 5
) -> str:
    """Start watching a folder for new assets and auto-import them into UE5.
    
    Creates a background watcher that polls for new files and automatically
    imports them. Useful for GhostRigger export workflow — export from
    GhostRigger, files appear in watched folder, auto-imported into UE5.
    
    Args:
        folder_path: OS path to watch
        ue5_base_path: UE5 destination
        poll_interval: Check interval in seconds (default: 5)
    """
    # Uses threading + filesystem polling
    # Tracks seen files to only import new ones
```

#### `import_folder_as_character`
```python
@mcp_server.tool()
async def import_folder_as_character(
    folder_path: str,
    character_name: str,
    ue5_base_path: str = "/Game/Characters/",
    auto_ik_setup: bool = True,
    retarget_from: str = ""
) -> str:
    """Import a complete character folder (mesh + textures + animations) and
    set up as a game-ready character in UE5.
    
    Expected folder structure:
      character_folder/
        model.fbx          (skeletal mesh)
        textures/
          BaseColor.png
          Normal.png
          Roughness.png
        animations/
          idle.fbx
          walk.fbx
          run.fbx
    
    This tool:
    1. Imports skeletal mesh
    2. Imports all textures with auto-type detection
    3. Creates PBR material from textures
    4. Assigns material to mesh
    5. Imports all animations (reusing the skeleton)
    6. Optionally creates IK Rig with auto-setup
    7. Optionally retargets animations from another skeleton
    
    Args:
        folder_path: Path to character folder
        character_name: Name for the character (e.g., 'Bastila')
        ue5_base_path: Content Browser destination
        auto_ik_setup: Auto-create IK Rig for retargeting
        retarget_from: Source skeleton path to retarget FROM (optional)
    """
```

---

## 4. GHOSTRIGGER-SPECIFIC PIPELINE: KotOR → UE5

### Full Pipeline Flow
```
┌──────────────────────────────────────────────────────────────┐
│ Step 1: AI Agent says "Import Bastila into my UE5 project"   │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│ Step 2: ghostrigger_ping() — verify GhostRigger is running   │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│ Step 3: ghostrigger_open_model("c_bastila")                  │
│         Opens model in GhostRigger viewer                    │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│ Step 4: ghostrigger_call_kotor_tool("auto_rig", {})          │
│         Auto-rigs with Aurora skeleton                       │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│ Step 5: ghostrigger_call_kotor_tool("export_fbx",            │
│         {"output_dir": "C:/Exports/bastila/"})               │
│         Exports FBX + textures to disk                       │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│ Step 6: import_folder_as_character(                          │
│         "C:/Exports/bastila/", "Bastila",                    │
│         auto_ik_setup=True,                                  │
│         retarget_from="/Game/Mannequin/SK_Mannequin")        │
│                                                              │
│  → imports mesh, textures, creates material, IK rig,         │
│    retargets Mannequin animations onto Bastila skeleton      │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│ Step 7: spawn_actor + set mesh + set material                │
│         Character appears in the level, animated, playable   │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. UNREAL MCP SERVER SOURCE CODE ANALYSIS

### Key Implementation Details from unreal_mcp_server.py

**UnrealConnection class** (TCP to UE5 plugin):
```python
class UnrealConnection:
    def __init__(self):
        self.socket = None
        self.connected = False
    
    def connect(self) -> bool:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((UNREAL_HOST, UNREAL_PORT))  # default 127.0.0.1:55557
        self.connected = True
    
    def send_command(self, command, params=None):
        # Monkey-patched to send_command_with_health_check after init
        return self._send_command_raw(command, params)
    
    def send_command_with_health_check(self, command, params=None):
        # Checks GameThread health before expensive commands
        # Auto-retries with backoff on connection issues
```

**Tool Registration Pattern:**
```python
# In unreal_mcp_server.py:
from tools.editor_tools import register_editor_tools
from tools.blueprint_tools import register_blueprint_tools
# ... 18 modules total

register_editor_tools(mcp)
register_blueprint_tools(mcp)
# ...

# In each tool module (e.g., tools/editor_tools.py):
def register_editor_tools(mcp):
    @mcp.tool()
    async def get_actors_in_level() -> str:
        """..."""
        return await send_command("get_actors_in_level", {})
```

**Adding GhostRigger Bridge** — Create new file `tools/ghostrigger_tools.py`:
```python
def register_ghostrigger_tools(mcp):
    """Register all GhostRigger bridge tools."""
    import requests
    import json
    
    GR_BASE = "http://127.0.0.1:7001"
    GR_TIMEOUT = 5
    
    def _gr_call(endpoint, method="POST", json_body=None, timeout=GR_TIMEOUT):
        """Helper to call GhostRigger IPC server."""
        try:
            if method == "GET":
                resp = requests.get(f"{GR_BASE}{endpoint}", timeout=timeout)
            else:
                resp = requests.post(f"{GR_BASE}{endpoint}", json=json_body, timeout=timeout)
            return resp.json()
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "GhostRigger not running on port 7001"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @mcp.tool()
    async def ghostrigger_ping() -> str:
        """Check if GhostRigger is running."""
        return json.dumps(_gr_call("/api/health", method="GET"))
    
    # ... (all other tools from Section 3A above)
```

**Adding Folder Import Tools** — Create new file `tools/folder_import_tools.py`:
```python
def register_folder_import_tools(mcp):
    """Register folder-based batch import tools."""
    import json, os
    
    @mcp.tool()
    async def scan_export_folder(folder_path: str, recursive: bool = True) -> str:
        """Scan folder for importable assets."""
        # Runs on MCP server side (local filesystem)
        # ...
    
    @mcp.tool()
    async def batch_import_folder(folder_path: str, ...) -> str:
        """Batch import from folder into UE5."""
        # 1. Scan locally
        # 2. Build exec_python code for batch AssetImportTask
        # 3. Send to UE5 via send_command("exec_python", ...)
```

**Register in unreal_mcp_server.py:**
```python
# Add to imports
from tools.ghostrigger_tools import register_ghostrigger_tools
from tools.folder_import_tools import register_folder_import_tools

# Add to registration
register_ghostrigger_tools(mcp)
register_folder_import_tools(mcp)
```

---

## 6. UE5 INTERCHANGE FRAMEWORK (For glTF Import)

### Why Interchange Matters
GhostRigger can export glTF. UE5's Interchange Framework is the modern way to import glTF with full control over the pipeline.

### Python Interchange Pipeline
```python
import unreal

@unreal.uclass()
class GhostRiggerImportPipeline(unreal.InterchangePythonPipelineBase):
    """Custom Interchange pipeline for assets exported from GhostRigger."""
    
    create_folders = unreal.uproperty(bool, meta=dict(default_value=True))
    
    @unreal.ufunction(override=True)
    def scripted_execute_pipeline(self, source_data, node_container, pipeline_result):
        """Pre-import: set up folders, rename assets, configure options."""
        # Auto-organize into Meshes/, Textures/, Materials/ subfolders
        # Apply naming conventions (prefix with GR_ for GhostRigger assets)
        pass
    
    @unreal.ufunction(override=True)
    def scripted_execute_post_import_pipeline(self, source_data, node_container, 
                                               pipeline_result, factory_created_nodes):
        """Post-import: validate, optimize, create materials."""
        # Check poly count, texture resolution
        # Auto-generate LODs if Nanite disabled
        # Create PBR materials from imported textures
        pass
```

---

## 7. OPEN SOURCE TOOLS FOR FURTHER INTEGRATION

### PyKotor (Python library for KotOR file formats)
- **URL:** https://github.com/NickHugi/PyKotor
- **Also:** https://github.com/OldRepublicDevs/PyKotor
- **What:** Reads/modifies KotOR file formats (MDL, MDX, 2DA, TPC, GFF, ERF, RIM, BIF)
- **GhostRigger already uses this** via `pykotor_bridge.py`
- **Integration:** Could expose PyKotor functions as MCP tools for direct game data manipulation

### Blender MCP (Reference for external tool bridging)
- **URL:** https://github.com/ahujasid/blender-mcp
- **What:** MCP server that controls Blender
- **Pattern:** Similar to what we're doing with GhostRigger — bridge MCP ↔ external tool
- **Learning:** Their IPC pattern uses JSON-RPC over local socket

### AccuRIG (Free auto-rigging)
- **URL:** https://actorcore.reallusion.com/auto-rig
- **Integration:** Export from GhostRigger → AccuRIG for advanced rigging → FBX → UE5

### MDLOps (KotOR model compiler/decompiler)
- **Already integrated** in GhostRigger (MDLOps Bridge in Resource Browser)
- **Compile ASCII MDL → Binary** and vice versa

---

## 8. IMPLEMENTATION PRIORITY

| Tool | Effort | Dependencies | Sprint |
|------|--------|-------------|--------|
| `ghostrigger_ping` | 15 min | GhostRigger running | 1 |
| `ghostrigger_open_model` | 30 min | ping working | 1 |
| `ghostrigger_list_kotor_tools` | 15 min | ping working | 1 |
| `ghostrigger_call_kotor_tool` | 30 min | ping working | 1 |
| `ghostrigger_read_kotor_resource` | 30 min | ping working | 1 |
| `scan_export_folder` | 1 hr | None | 1 |
| `batch_import_folder` | 3 hrs | import_* tools working | 2 |
| `ghostrigger_export_model` | 2 hrs | KotorMCP export tools | 2 |
| `ghostrigger_export_and_import_to_ue5` | 2 hrs | export + import working | 2 |
| `watch_export_folder` | 2 hrs | batch_import working | 3 |
| `import_folder_as_character` | 4 hrs | All Phase 1-3 tools | 4 |
| Interchange Pipeline | 4 hrs | glTF import working | 3 |
