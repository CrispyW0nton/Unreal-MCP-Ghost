# Unreal-MCP-Ghost — Native Mode Enhancement Specification

> Making Claude Desktop / Cursor / Windsurf experience equal to GenSpark AI Developer.

---

## Problem Statement

Currently, **Non-Native mode** (GenSpark AI Developer via SSE) provides a superior development experience because the AI agent can:
1. Browse and edit all project source files
2. Read all 19 knowledge base documents for context
3. Use MCP tools AND file system simultaneously
4. Get auto-onboarded with project context

**Native mode** (Claude Desktop via stdio) only has access to the 311 MCP tools. The AI agent arrives "blind" — no project context, no knowledge base, no file browsing. Users must manually paste onboarding prompts and explain project structure.

---

## Solution: 7 Enhancements

### Enhancement 1: MCP Resources for Knowledge Base ← HIGH PRIORITY

**What:** Expose all 19 `knowledge_base/*.md` files as MCP Resources that Claude Desktop can discover and read.

**Implementation in `unreal_mcp_server.py`:**

```python
import os
from mcp.server import Server
from mcp.types import Resource, TextResourceContents

KB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'knowledge_base')

@mcp_server.list_resources()
async def list_resources():
    """List all knowledge base documents as MCP resources."""
    resources = []
    if os.path.isdir(KB_DIR):
        for fname in sorted(os.listdir(KB_DIR)):
            if fname.endswith('.md'):
                display_name = fname.replace('.md', '').replace('_', ' ')
                resources.append(Resource(
                    uri=f"knowledge-base:///{fname}",
                    name=display_name,
                    description=f"Knowledge base: {display_name}",
                    mimeType="text/markdown"
                ))
    return resources

@mcp_server.read_resource()
async def read_resource(uri: str):
    """Read a specific knowledge base document."""
    # Extract filename from URI
    fname = uri.split('/')[-1]
    if not fname.endswith('.md'):
        fname += '.md'
    
    fpath = os.path.join(KB_DIR, fname)
    if not os.path.exists(fpath):
        raise FileNotFoundError(f"Knowledge base file not found: {fname}")
    
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return [TextResourceContents(
        uri=uri,
        text=content,
        mimeType="text/markdown"
    )]
```

**Claude Desktop will see:**
```
Resources:
├── 00 AGENT KNOWLEDGE BASE (Master index)
├── 01 BLUEPRINT FUNDAMENTALS
├── 02 BLUEPRINT COMMUNICATION
├── 03 GAMEPLAY FRAMEWORK
├── 04 AI SYSTEMS
├── 05 ANIMATION SYSTEM
├── 06 UI UMG SYSTEMS
├── ...
└── 18 PACKAGING AND OPTIMIZATION
```

**Testing:** In Claude Desktop, the resources should appear in the MCP server panel. Clicking a resource fetches its content.

---

### Enhancement 2: `get_project_context` Tool

**What:** A tool that returns comprehensive information about the current UE5 project state.

```python
@mcp_server.tool()
async def get_project_context() -> str:
    """Get current UE5 project context including project name, current level,
    loaded actors, and project structure. Call this at the START of every 
    session to understand what you're working with.
    
    Returns JSON with project_name, current_level, ue_version, actor_count,
    actor_type_breakdown, content_browser_structure.
    """
    code = '''
import unreal
import os
import json

# Project info
project_path = unreal.Paths.get_project_file_path()
project_name = os.path.basename(project_path).replace('.uproject', '')

# Engine version
engine_ver = unreal.SystemLibrary.get_engine_version()

# Current level
world = unreal.EditorLevelLibrary.get_editor_world()
level_name = world.get_name() if world else "No level loaded"

# Actor breakdown
actors = unreal.EditorLevelLibrary.get_all_level_actors()
type_counts = {}
for a in actors:
    cls = a.get_class().get_name()
    type_counts[cls] = type_counts.get(cls, 0) + 1

# Top-level content folders
content_path = "/Game/"
asset_reg = unreal.AssetRegistryHelpers.get_asset_registry()
top_folders = []
try:
    # List immediate subdirectories of /Game/
    all_assets = unreal.EditorAssetLibrary.list_assets(content_path, recursive=False)
    folder_set = set()
    for a in all_assets[:200]:  # Limit scan
        parts = a.split('/')
        if len(parts) > 2:
            folder_set.add(parts[2])
    top_folders = sorted(list(folder_set))[:20]
except:
    top_folders = ["(scan failed)"]

# Plugin status
plugin_running = True  # If we got here, it's running

result = {
    "project_name": project_name,
    "engine_version": engine_ver,
    "current_level": level_name,
    "actor_count": len(actors),
    "actor_types": dict(sorted(type_counts.items(), key=lambda x: -x[1])[:15]),
    "content_folders": top_folders,
    "plugin_status": "running",
    "mcp_tools_available": 311
}
print(json.dumps(result))
'''
    return await send_command("exec_python", {"code": code})
```

---

### Enhancement 3: `get_onboarding_context` Tool

**What:** Returns a curated subset of knowledge base content relevant to what the user is trying to do.

```python
@mcp_server.tool()
async def get_onboarding_context(task_domain: str = "general") -> str:
    """Get relevant knowledge base content for your current task.
    
    Args:
        task_domain: One of: general, blueprint, animation, material, ai, 
                     ui, vfx, world, audio, packaging, import
    
    Returns: Curated knowledge base content for the specified domain.
    """
    domain_map = {
        "general": ["00_AGENT_KNOWLEDGE_BASE.md", "12_MCP_TOOL_USAGE_GUIDE.md"],
        "blueprint": ["01_BLUEPRINT_FUNDAMENTALS.md", "02_BLUEPRINT_COMMUNICATION.md", "11_BLUEPRINT_LIBRARIES_AND_COMPONENTS.md"],
        "animation": ["05_ANIMATION_SYSTEM.md", "16_ANIMATION_DEEP_DIVE.md"],
        "material": ["08_MATERIALS_AND_RENDERING.md"],
        "ai": ["04_AI_SYSTEMS.md"],
        "ui": ["06_UI_UMG_SYSTEMS.md", "15_INPUT_SYSTEM_AND_UMG.md"],
        "vfx": ["09_NIAGARA_VFX.md"],
        "world": ["10_WORLD_BUILDING.md"],
        "audio": ["12_MCP_TOOL_USAGE_GUIDE.md"],  # Audio section
        "packaging": ["18_PACKAGING_AND_OPTIMIZATION.md"],
        "import": ["12_MCP_TOOL_USAGE_GUIDE.md", "13_TOOL_EXPANSION_ROADMAP.md"],
    }
    
    files = domain_map.get(task_domain, domain_map["general"])
    content_parts = []
    
    for fname in files:
        fpath = os.path.join(KB_DIR, fname)
        if os.path.exists(fpath):
            with open(fpath, 'r', encoding='utf-8') as f:
                content_parts.append(f"# {fname}\n\n{f.read()}")
    
    return "\n\n---\n\n".join(content_parts)
```

---

### Enhancement 4: `scan_project_assets` Tool

**What:** Deep scan of the Content Browser to give the AI a complete picture of available assets.

```python
@mcp_server.tool()
async def scan_project_assets(
    root_path: str = "/Game/",
    asset_types: str = "all",
    max_results: int = 500
) -> str:
    """Scan the Content Browser and return a structured inventory of all assets.
    
    Args:
        root_path: Content Browser path to scan (default: /Game/)
        asset_types: Filter by type: all, StaticMesh, SkeletalMesh, Material, 
                     MaterialInstance, Texture, SoundWave, Blueprint, AnimSequence, 
                     AnimBlueprint, NiagaraSystem, WidgetBlueprint
        max_results: Maximum assets to return (default: 500)
    
    Returns: JSON with categorized asset inventory.
    """
    code = f'''
import unreal
import json

root = "{root_path}"
filter_type = "{asset_types}"
max_r = {max_results}

all_assets = unreal.EditorAssetLibrary.list_assets(root, recursive=True)

categorized = {{}}
count = 0
for asset_path in all_assets:
    if count >= max_r:
        break
    try:
        data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        cls = str(data.asset_class_path.asset_name) if hasattr(data, 'asset_class_path') else str(data.asset_class)
        
        if filter_type != "all" and filter_type not in cls:
            continue
        
        if cls not in categorized:
            categorized[cls] = []
        categorized[cls].append(asset_path)
        count += 1
    except:
        pass

summary = {{}}
for cls, paths in categorized.items():
    summary[cls] = {{
        "count": len(paths),
        "assets": paths[:50]  # Limit per category
    }}

result = {{
    "root_path": root,
    "total_scanned": count,
    "categories": summary
}}
print(json.dumps(result, indent=2))
'''
    return await send_command("exec_python", {"code": code})
```

---

### Enhancement 5: `list_available_tools` Tool

**What:** Organized tool discovery by domain, so AI agents know what's available.

```python
@mcp_server.tool()
async def list_available_tools(domain: str = "all") -> str:
    """List all available MCP tools, optionally filtered by domain.
    
    Args:
        domain: Filter tools by domain: all, actor, blueprint, blueprint_node, 
                animation, material, ai, vfx, ui, sequencer, data, input, 
                world, editor, import, project
    
    Returns: Organized list of tools with descriptions.
    """
    # This would introspect the registered tools on the MCP server
    # Implementation depends on FastMCP's introspection API
    tools = mcp_server.list_tools()
    
    if domain == "all":
        return json.dumps([{"name": t.name, "description": t.description} for t in tools])
    
    # Filter by domain keyword in tool name or description
    filtered = [t for t in tools if domain.lower() in t.name.lower() 
                or domain.lower() in (t.description or "").lower()]
    return json.dumps([{"name": t.name, "description": t.description} for t in filtered])
```

---

### Enhancement 6: Inline Tool Documentation

**What:** Enhance every tool's docstring with examples and KB references.

**Before:**
```python
@mcp_server.tool()
async def create_blueprint(name: str, parent_class: str = "Actor") -> str:
    """Create a new Blueprint class."""
```

**After:**
```python
@mcp_server.tool()
async def create_blueprint(
    name: str,
    parent_class: str = "Actor",
    path: str = "/Game/Blueprints/"
) -> str:
    """Create a new Blueprint class in the Content Browser.
    
    Args:
        name: Blueprint name (e.g., 'BP_PlayerCharacter')
        parent_class: Parent class name. Common values:
            - 'Actor' (default, general purpose)
            - 'Character' (for player/NPC characters with movement)
            - 'Pawn' (for possessed entities without CharacterMovement)
            - 'GameModeBase' (for game mode logic)
            - 'PlayerController' (for input handling)
            - 'AIController' (for AI-controlled pawns)
            - 'HUD' (for HUD rendering)
            - 'ActorComponent' (for reusable components)
        path: Content Browser folder (default: /Game/Blueprints/)
    
    Returns:
        JSON: {"success": true, "blueprint_path": "/Game/Blueprints/BP_PlayerCharacter"}
    
    Example workflow:
        1. create_blueprint("BP_Enemy", "Character")
        2. add_component_to_blueprint("BP_Enemy", "SkeletalMeshComponent", "Mesh")
        3. add_blueprint_variable("BP_Enemy", "Health", "Float", "100.0")
        4. compile_blueprint("BP_Enemy")
    
    See also: knowledge_base/01_BLUEPRINT_FUNDAMENTALS.md
    """
```

**Apply this pattern to ALL 311 tools.** Priority: the 50 most-used tools first.

---

### Enhancement 7: Session Welcome Message

**What:** When the MCP server starts, it should provide a welcome context to the connecting client.

**Implementation:** Add a `get_server_info` tool that's designed to be called first:

```python
@mcp_server.tool()
async def get_server_info() -> str:
    """Get MCP server information and quick-start guide.
    CALL THIS FIRST when starting a new session.
    
    Returns server version, available tool count, and quick-start instructions.
    """
    return json.dumps({
        "server": "Unreal-MCP-Ghost",
        "version": "2.0.0",
        "branch": "genspark_ai_developer",
        "total_tools": 311,
        "tool_domains": [
            "Actor/Level (spawn, transform, properties)",
            "Blueprint (create, compile, variables, functions)",
            "Blueprint Nodes (40 node types, pin wiring)",
            "Animation (notifies, sequences, montages)",
            "Material (instances, parameters)",
            "AI/BehaviorTree (blackboards, tasks, decorators)",
            "Niagara VFX (systems, emitters)",
            "UI/UMG (widgets, bindings)",
            "Sequencer (tracks, keyframes)",
            "Data (tables, structs)",
            "Input (actions, mappings)",
            "World Building (landscape, foliage)",
            "Editor Utilities (screenshots, viewport)",
            "exec_python (escape hatch — full UE5 Python API)"
        ],
        "quick_start": [
            "1. Call get_project_context() to see current project state",
            "2. Call get_onboarding_context('general') for knowledge base",
            "3. Call scan_project_assets() to see what exists",
            "4. Start building!"
        ],
        "knowledge_base": "19 docs available as MCP Resources — read them for UE5 patterns"
    })
```

---

## Implementation Priority

| Enhancement | Effort | Impact | Sprint |
|-------------|--------|--------|--------|
| 1. MCP Resources for KB | Low (2hrs) | Critical | Sprint 2 |
| 2. get_project_context | Low (2hrs) | High | Sprint 2 |
| 3. get_onboarding_context | Low (1hr) | High | Sprint 2 |
| 4. scan_project_assets | Medium (4hrs) | High | Sprint 2 |
| 5. list_available_tools | Low (1hr) | Medium | Sprint 2 |
| 6. Inline documentation | High (ongoing) | High | Sprint 2+ |
| 7. Session welcome | Low (30min) | Medium | Sprint 2 |

**Total estimated effort for Sprint 2 native mode work: ~12 hours**

---

## Verification Checklist

After implementing all enhancements:

- [ ] Claude Desktop discovers all 19 KB resources in MCP panel
- [ ] Claude Desktop can read any KB doc by clicking it
- [ ] `get_project_context` returns current project state
- [ ] `get_onboarding_context("blueprint")` returns BP-specific docs
- [ ] `scan_project_assets` returns categorized Content Browser inventory
- [ ] `list_available_tools("animation")` filters to animation tools
- [ ] `get_server_info` provides clear quick-start guidance
- [ ] All new tools work via both stdio AND SSE transport
