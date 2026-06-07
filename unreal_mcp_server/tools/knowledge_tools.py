"""
knowledge_tools.py — MCP tools for querying the Unreal-MCP-Ghost knowledge base.

Tools:
  get_server_info()                → startup summary for agents
  get_onboarding_context(task)     → task-specific KB packet for agents
  scan_project_assets(path, depth, class_filter) → Asset Registry inventory
  list_available_tools(domain)    → category-filtered tool discovery
  list_knowledge_base_topics()     → index of all available topics
  get_knowledge_base(topic)        → full content of a topic file
  search_knowledge_base(query)     → keyword search across all KB files

The knowledge base consists of two layers:
  1. knowledge_base/*.md           — hand-written reference docs (19 files)
  2. knowledge_base/book_extracts/ — PDF-extracted book content (10 topic files)

MANDATORY AGENT RULE: Query the knowledge base BEFORE implementing any system.
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Any

# Resolve KB directory relative to this file
_THIS_DIR = Path(__file__).parent
_REPO_ROOT = _THIS_DIR.parent.parent
KB_DIR = _REPO_ROOT / "knowledge_base"
BOOK_DIR = KB_DIR / "book_extracts"

KB_RESOURCE_DIRS = (
    (KB_DIR, ""),
    (KB_DIR / "v4", "v4/"),
    (KB_DIR / "v5", "v5/"),
)
TOOL_CATEGORY_MAP_PATH = _REPO_ROOT / "unreal_mcp_server" / "tool_inventory_categories.json"
PROJECT_CONTEXT_CACHE_TTL_S = 5.0
_PROJECT_CONTEXT_CACHE: dict[str, Any] = {"timestamp": 0.0, "context": None}

ONBOARDING_CONTEXTS: dict[str, dict[str, Any]] = {
    "blueprints": {
        "title": "Blueprint graph and asset authoring",
        "uris": [
            "kb://00_AGENT_KNOWLEDGE_BASE.md",
            "kb://01_BLUEPRINT_FUNDAMENTALS.md",
            "kb://02_BLUEPRINT_COMMUNICATION.md",
            "kb://11_BLUEPRINT_LIBRARIES_AND_COMPONENTS.md",
            "kb://12_MCP_TOOL_USAGE_GUIDE.md",
            "kb://blueprint_organization_standards.md",
            "kb://v4/GRAPH_SCRIPTING_SPEC_V4.md",
        ],
        "tool_domains": ["blueprint_asset", "blueprint_graph", "blueprint_communication", "blueprint_repair"],
        "workflow": [
            "Call get_project_context() and inspect the target Blueprint before mutation.",
            "Prefer graph-aware helpers, compile after edits, then run diagnostics or repair tools.",
            "Keep naming/searchability consistent with the Blueprint organization standards.",
        ],
    },
    "animation": {
        "title": "Animation Blueprints, retargeting, montages, and IK",
        "uris": [
            "kb://00_AGENT_KNOWLEDGE_BASE.md",
            "kb://05_ANIMATION_SYSTEM.md",
            "kb://16_ANIMATION_DEEP_DIVE.md",
            "kb://12_MCP_TOOL_USAGE_GUIDE.md",
            "kb://v4/ENGINE_SOURCE_STUDY_GUIDE_V4.md",
        ],
        "expected_future_docs": ["knowledge_base/24_MOTION_MATCHING_AND_CHOOSERS.md"],
        "tool_domains": ["animation", "blueprint_graph", "reflection"],
        "workflow": [
            "Confirm skeleton, mesh, AnimBP, and montage assets before wiring graph changes.",
            "Use reflection and graph summaries before adding or connecting animation nodes.",
            "Compile and validate Animation Blueprints after every generated graph pass.",
        ],
    },
    "ai": {
        "title": "AI, Behavior Trees, Blackboards, perception, EQS, and navigation",
        "uris": [
            "kb://00_AGENT_KNOWLEDGE_BASE.md",
            "kb://04_AI_SYSTEMS.md",
            "kb://17_GAME_SYSTEMS_COOKBOOK.md",
            "kb://ue5_ai_and_navigation.md",
            "kb://12_MCP_TOOL_USAGE_GUIDE.md",
        ],
        "expected_future_docs": ["knowledge_base/23_MASS_ENTITY_AND_STATETREE.md"],
        "tool_domains": ["ai_behavior_tree", "editor_actor_viewport", "blueprint_graph"],
        "workflow": [
            "Treat Blackboard keys as the source of truth for AI state.",
            "Validate nav mesh, pawn movement setup, and target actor references before PIE.",
            "Keep Behavior Tree tasks thin and report missing keys/assets clearly.",
        ],
    },
    "materials": {
        "title": "Materials, material instances, rendering, and texture wiring",
        "uris": [
            "kb://00_AGENT_KNOWLEDGE_BASE.md",
            "kb://08_MATERIALS_AND_RENDERING.md",
            "kb://12_MCP_TOOL_USAGE_GUIDE.md",
            "kb://v4/API_REFERENCE_CHEATSHEET.md",
        ],
        "tool_domains": ["technical_art_materials", "asset_import", "reflection"],
        "workflow": [
            "Inspect source textures and material parent assets before creating instances.",
            "Use material tools for creation and reflection tools for property discovery.",
            "Recompile/validate materials after generated expression or parameter changes.",
        ],
    },
    "niagara": {
        "title": "Niagara VFX authoring and validation",
        "uris": [
            "kb://00_AGENT_KNOWLEDGE_BASE.md",
            "kb://09_NIAGARA_VFX.md",
            "kb://08_MATERIALS_AND_RENDERING.md",
            "kb://12_MCP_TOOL_USAGE_GUIDE.md",
        ],
        "tool_domains": ["niagara_vfx", "technical_art_materials", "editor_actor_viewport"],
        "workflow": [
            "Inspect emitter/system availability and required plugin support before authoring.",
            "Keep material and texture dependencies explicit in generated VFX recipes.",
            "Spawn viewport evidence after placement-oriented VFX work.",
        ],
    },
    "umg": {
        "title": "UMG widgets, HUDs, menus, and enhanced input surfaces",
        "uris": [
            "kb://00_AGENT_KNOWLEDGE_BASE.md",
            "kb://06_UI_UMG_SYSTEMS.md",
            "kb://15_INPUT_SYSTEM_AND_UMG.md",
            "kb://12_MCP_TOOL_USAGE_GUIDE.md",
        ],
        "tool_domains": ["ui_umg", "project_input", "blueprint_graph"],
        "workflow": [
            "Create or inspect the Widget Blueprint before wiring runtime display logic.",
            "Keep input actions and widget event bindings named for searchability.",
            "Validate HUD/menu flows in PIE and capture evidence where possible.",
        ],
    },
    "world_building": {
        "title": "Level layout, world building, streaming, and iteration loops",
        "uris": [
            "kb://00_AGENT_KNOWLEDGE_BASE.md",
            "kb://10_WORLD_BUILDING.md",
            "kb://iterative_level_design_framework.md",
            "kb://18_PACKAGING_AND_OPTIMIZATION.md",
            "kb://v4/VALIDATION_TEST_MATRIX_V4.md",
        ],
        "expected_future_docs": ["knowledge_base/25_WORLD_PARTITION_AND_HLOD.md"],
        "tool_domains": ["editor_actor_viewport", "procedural_world", "project_intelligence"],
        "workflow": [
            "Read project context and current level state before spawning or moving actors.",
            "Keep layouts playable after each pass: navigation, lighting, collision, and PIE smoke.",
            "Use evidence capture and iteration notes for every world-building milestone.",
        ],
    },
    "audio": {
        "title": "Audio import, SoundCue setup, and gameplay feedback",
        "uris": [
            "kb://00_AGENT_KNOWLEDGE_BASE.md",
            "kb://17_GAME_SYSTEMS_COOKBOOK.md",
            "kb://12_MCP_TOOL_USAGE_GUIDE.md",
        ],
        "expected_future_docs": ["knowledge_base/21_METASOUNDS_AND_AUDIO_DSP.md"],
        "tool_domains": ["audio", "asset_import", "blueprint_graph"],
        "workflow": [
            "Confirm source file paths are on the UE host machine before import.",
            "Prefer clear SoundWave/SoundCue naming and explicit playback wiring.",
            "Check Output Log after audio imports and Blueprint sound node wiring.",
        ],
    },
    "generative": {
        "title": "Generative meshes, textures, import, and playable-slice pipelines",
        "uris": [
            "kb://00_AGENT_KNOWLEDGE_BASE.md",
            "kb://12_MCP_TOOL_USAGE_GUIDE.md",
            "kb://13_TOOL_EXPANSION_ROADMAP.md",
            "kb://18_PACKAGING_AND_OPTIMIZATION.md",
            "kb://v4/ROADMAP_V4.md",
        ],
        "expected_future_docs": [
            "knowledge_base/22_GEOMETRY_SCRIPT_AND_MODELING.md",
            "knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md",
            "knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md",
        ],
        "tool_domains": ["asset_import", "procedural_world", "technical_art_materials", "editor_actor_viewport"],
        "workflow": [
            "Plan generated assets as part of a playable vertical slice, not as isolated files.",
            "After generation or download, import through asset tools and validate materials/textures.",
            "Compile Blueprints, run PIE smoke, and package evidence before calling the slice complete.",
        ],
    },
    "multiplayer": {
        "title": "Networking, replication, roles, and RPC-aware gameplay",
        "uris": [
            "kb://00_AGENT_KNOWLEDGE_BASE.md",
            "kb://03_GAMEPLAY_FRAMEWORK.md",
            "kb://ue5_multiplayer_patterns.md",
            "kb://12_MCP_TOOL_USAGE_GUIDE.md",
        ],
        "expected_future_docs": [
            "knowledge_base/20_NETWORKING_AND_REPLICATION.md",
            "knowledge_base/30_ONLINE_SUBSYSTEM_AND_EOS.md",
        ],
        "tool_domains": ["gameplay_framework", "blueprint_asset", "blueprint_graph"],
        "workflow": [
            "Identify authority boundaries before adding replicated state or gameplay effects.",
            "Prefer explicit server/client RPC semantics and inspect generated classes afterward.",
            "Do not mark networking work complete without multiplayer-oriented PIE/log evidence.",
        ],
    },
    "gas": {
        "title": "Gameplay Ability System, tags, effects, cues, and attributes",
        "uris": [
            "kb://00_AGENT_KNOWLEDGE_BASE.md",
            "kb://03_GAMEPLAY_FRAMEWORK.md",
            "kb://17_GAME_SYSTEMS_COOKBOOK.md",
            "kb://12_MCP_TOOL_USAGE_GUIDE.md",
        ],
        "expected_future_docs": ["knowledge_base/19_GAMEPLAY_ABILITY_SYSTEM.md"],
        "tool_domains": ["gameplay_framework", "data_systems", "blueprint_graph"],
        "workflow": [
            "Confirm project GAS plugin/module availability before creating ability assets.",
            "Keep GameplayTags, AttributeSets, GameplayEffects, and GameplayCues named coherently.",
            "Validate granted abilities and effect application in a small playable slice.",
        ],
    },
    "metasounds": {
        "title": "MetaSounds, audio DSP, patches, sources, and runtime playback",
        "uris": [
            "kb://00_AGENT_KNOWLEDGE_BASE.md",
            "kb://17_GAME_SYSTEMS_COOKBOOK.md",
            "kb://12_MCP_TOOL_USAGE_GUIDE.md",
        ],
        "expected_future_docs": ["knowledge_base/21_METASOUNDS_AND_AUDIO_DSP.md"],
        "tool_domains": ["audio", "blueprint_graph", "reflection"],
        "workflow": [
            "Verify MetaSounds plugin availability before creating sources or patches.",
            "Keep audio graph parameters documented and tied to gameplay triggers.",
            "Validate playback and log output after any generated audio-DSP graph changes.",
        ],
    },
}

ONBOARDING_ALIASES = {
    "blueprint": "blueprints",
    "bp": "blueprints",
    "anim": "animation",
    "behavior_tree": "ai",
    "behavior tree": "ai",
    "materials_and_rendering": "materials",
    "material": "materials",
    "vfx": "niagara",
    "ui": "umg",
    "hud": "umg",
    "world": "world_building",
    "worldbuilding": "world_building",
    "level_design": "world_building",
    "networking": "multiplayer",
    "replication": "multiplayer",
    "gameplay_ability_system": "gas",
    "abilities": "gas",
    "meta_sounds": "metasounds",
    "sound": "audio",
}

TOOL_DOMAIN_ALIASES: dict[str, list[str]] = {
    "all": [],
    "blueprints": ["blueprint_asset", "blueprint_graph", "blueprint_communication", "blueprint_repair"],
    "blueprint": ["blueprint_asset", "blueprint_graph", "blueprint_communication", "blueprint_repair"],
    "bp": ["blueprint_asset", "blueprint_graph", "blueprint_communication", "blueprint_repair"],
    "animation": ["animation"],
    "ai": ["ai_behavior_tree"],
    "materials": ["technical_art_materials"],
    "material": ["technical_art_materials"],
    "niagara": ["niagara_vfx"],
    "vfx": ["niagara_vfx"],
    "umg": ["ui_umg"],
    "ui": ["ui_umg"],
    "world_building": ["editor_actor_viewport", "procedural_world", "project_intelligence"],
    "world": ["editor_actor_viewport", "procedural_world", "project_intelligence"],
    "audio": ["audio"],
    "generative": ["asset_import", "procedural_world", "technical_art_materials", "editor_actor_viewport"],
    "multiplayer": ["gameplay_framework", "blueprint_asset", "blueprint_graph"],
    "networking": ["gameplay_framework", "blueprint_asset", "blueprint_graph"],
    "gas": ["gameplay_framework", "data_systems", "blueprint_graph"],
    "metasounds": ["audio", "blueprint_graph", "reflection"],
    "meta_sounds": ["audio", "blueprint_graph", "reflection"],
}

# ── Topic routing ────────────────────────────────────────────────────────────

# Maps user-friendly topic names → KB files (hand-written + book extracts)
TOPIC_MAP = {
    # Hand-written reference docs
    "overview":          ["00_AGENT_KNOWLEDGE_BASE.md"],
    "blueprints":        ["01_BLUEPRINT_FUNDAMENTALS.md", "BOOK_BLUEPRINTS_FUNDAMENTALS.md"],
    "communication":     ["02_BLUEPRINT_COMMUNICATION.md", "BOOK_BLUEPRINT_COMMUNICATION.md"],
    "gameplay":          ["03_GAMEPLAY_FRAMEWORK.md", "BOOK_GAMEPLAY_FRAMEWORK.md"],
    "ai":                ["04_AI_SYSTEMS.md", "BOOK_AI_BEHAVIOR_TREES.md"],
    "animation":         ["05_ANIMATION_SYSTEM.md", "BOOK_ANIMATION.md"],
    "ui":                ["06_UI_UMG_SYSTEMS.md", "BOOK_UI_UMG.md"],
    "data":              ["07_DATA_STRUCTURES.md", "BOOK_DATA_STRUCTURES.md"],
    "materials":         ["08_MATERIALS_AND_RENDERING.md", "BOOK_MATERIALS_VFX.md"],
    "niagara":           ["09_NIAGARA_VFX.md", "BOOK_MATERIALS_VFX.md"],
    "world":             ["10_WORLD_BUILDING.md"],
    "components":        ["11_BLUEPRINT_LIBRARIES_AND_COMPONENTS.md", "BOOK_TECHNICAL_ART.md"],
    "tools":             ["12_MCP_TOOL_USAGE_GUIDE.md"],
    "roadmap":           ["13_TOOL_EXPANSION_ROADMAP.md"],
    "dantooine":         ["14_DANTOOINE_PROJECT_REFERENCE.md"],
    "input":             ["15_INPUT_SYSTEM_AND_UMG.md", "BOOK_INPUT.md"],
    "animation_deep":    ["16_ANIMATION_DEEP_DIVE.md", "BOOK_ANIMATION.md"],
    "cookbook":          ["17_GAME_SYSTEMS_COOKBOOK.md"],
    "packaging":         ["18_PACKAGING_AND_OPTIMIZATION.md", "BOOK_TECHNICAL_ART.md"],
    # Book-only topics
    "technical_art":     ["BOOK_TECHNICAL_ART.md"],
    "vfx":               ["BOOK_MATERIALS_VFX.md", "09_NIAGARA_VFX.md"],
}

# Aliases for common variations
ALIASES = {
    "behavior tree": "ai", "behavior_tree": "ai", "bt": "ai", "npc": "ai", "enemy": "ai",
    "widget": "ui", "hud": "ui", "umg": "ui", "menu": "ui",
    "blueprint": "blueprints", "bp": "blueprints", "nodes": "blueprints",
    "material": "materials", "shader": "materials", "rendering": "materials",
    "particle": "niagara", "vfx": "niagara", "effects": "niagara",
    "save": "data", "struct": "data", "enum": "data", "datatable": "data",
    "game mode": "gameplay", "gamemode": "gameplay", "character": "gameplay",
    "player controller": "gameplay", "playercontroller": "gameplay",
    "interface": "communication", "dispatcher": "communication", "cast": "communication",
    "anim": "animation", "skeleton": "animation", "montage": "animation",
    "enhanced input": "input", "key": "input", "binding": "input",
    "optimization": "packaging", "performance": "packaging", "lod": "technical_art",
    "component": "components", "actor component": "components",
}

def _resolve_topic(topic: str) -> str | None:
    """Resolve a topic string to a canonical topic key."""
    t = topic.lower().strip()
    if t in TOPIC_MAP:
        return t
    if t in ALIASES:
        return ALIASES[t]
    # Partial match
    for key in TOPIC_MAP:
        if t in key or key in t:
            return key
    return None

def _read_file(filename: str) -> str | None:
    """Read a KB file, checking both KB_DIR and BOOK_DIR."""
    for base in [KB_DIR, BOOK_DIR]:
        path = base / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
    return None

def _all_kb_files() -> list[tuple[str, str]]:
    """Return list of (filename, content) for all KB files."""
    files = []
    for f in sorted(KB_DIR.glob("*.md")):
        files.append((f.name, f.read_text(encoding="utf-8")))
    if BOOK_DIR.exists():
        for f in sorted(BOOK_DIR.glob("*.md")):
            files.append((f.name, f.read_text(encoding="utf-8")))
    return files

def _kb_resource_files() -> list[tuple[str, Path]]:
    """Return (kb:// URI path, file path) pairs exposed as MCP Resources."""
    files = []
    for base_dir, uri_prefix in KB_RESOURCE_DIRS:
        if not base_dir.exists():
            continue
        for path in sorted(base_dir.glob("*.md")):
            files.append((f"{uri_prefix}{path.name}", path))
    return files

def _humanize_resource_name(uri_path: str) -> str:
    """Convert a KB URI path into a stable, readable resource name."""
    stem = uri_path.removesuffix(".md").replace("/", " ")
    stem = re.sub(r"^\d+_", "", stem)
    return stem.replace("_", " ").replace("-", " ").title()

def _extract_resource_metadata(path: Path, uri_path: str) -> tuple[str, str]:
    """Derive a human title and short description from markdown content."""
    text = path.read_text(encoding="utf-8")
    title = ""
    description = ""

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            break

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("|") or line.startswith("---"):
            continue
        line = re.sub(r"[*_`>\[\]()]+", "", line)
        description = re.sub(r"\s+", " ", line).strip()
        break

    if not title:
        title = _humanize_resource_name(uri_path)
    if not description:
        description = f"Knowledge base reference: {title}"
    if len(description) > 180:
        description = description[:177].rstrip() + "..."
    return title, description

def _register_kb_markdown_resources(mcp) -> None:
    """Expose top-level and v4 knowledge_base markdown files as MCP Resources."""
    def make_reader(resource_path: Path):
        def read_kb_resource() -> str:
            return resource_path.read_text(encoding="utf-8")
        return read_kb_resource

    for uri_path, path in _kb_resource_files():
        uri = f"kb://{uri_path}"
        title, description = _extract_resource_metadata(path, uri_path)
        name = uri_path.removesuffix(".md").replace("/", "-").lower()

        read_kb_resource = make_reader(path)
        read_kb_resource.__name__ = f"resource_kb_{name.replace('-', '_')}"
        read_kb_resource.__doc__ = description

        mcp.resource(
            uri,
            name=name,
            title=title,
            description=description,
            mime_type="text/markdown",
        )(read_kb_resource)

def _server_version() -> str:
    """Read the Python package version without importing packaging helpers."""
    pyproject = _REPO_ROOT / "unreal_mcp_server" / "pyproject.toml"
    if not pyproject.exists():
        return "unknown"
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("version"):
            return line.split("=", 1)[1].strip().strip('"')
    return "unknown"

def _kb_doc_list(mcp) -> list[dict[str, str]]:
    """Return KB resource metadata in the shape A.2 exposes to agents."""
    docs = []
    for resource in sorted(mcp._resource_manager.list_resources(), key=lambda r: str(r.uri)):
        uri = str(resource.uri)
        if not uri.startswith("kb://"):
            continue
        docs.append({
            "uri": uri,
            "title": resource.title or resource.name,
            "description": resource.description or "",
        })
    return docs

def _server_transport() -> str:
    """Return the active MCP transport if launched through the server entrypoint."""
    return os.environ.get("UNREAL_MCP_TRANSPORT", "unknown")

def _load_tool_category_map() -> dict[str, dict[str, str]]:
    """Load tool module category metadata from tool_inventory_categories.json."""
    if not TOOL_CATEGORY_MAP_PATH.exists():
        return {}
    try:
        return json.loads(TOOL_CATEGORY_MAP_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

def _tool_module_name(tool: Any) -> str:
    """Return the module name used for category lookup."""
    fn = getattr(tool, "fn", None)
    return getattr(fn, "__module__", "") or ""

def _tool_parameter_names(tool: Any) -> list[str]:
    """Extract parameter names from FastMCP's JSON schema."""
    parameters = getattr(tool, "parameters", {}) or {}
    properties = parameters.get("properties", {}) if isinstance(parameters, dict) else {}
    return sorted(properties.keys())

def _available_categories(category_map: dict[str, dict[str, str]]) -> list[str]:
    """Return sorted category names from the module category map."""
    return sorted({meta.get("category", "uncategorized") for meta in category_map.values()})

def _resolve_tool_domain(domain: str, category_map: dict[str, dict[str, str]]) -> tuple[bool, list[str], str]:
    """Resolve a requested domain into one or more category names."""
    requested = (domain or "all").strip().lower().replace("-", "_")
    categories = _available_categories(category_map)
    if requested in ("", "all", "*"):
        return True, categories, "all"
    if requested in categories:
        return True, [requested], requested
    if requested in TOOL_DOMAIN_ALIASES:
        resolved = [category for category in TOOL_DOMAIN_ALIASES[requested] if category in categories]
        return bool(resolved), resolved, requested
    return False, [], requested

def _tool_discovery_payload(mcp, domain: str) -> dict[str, Any]:
    """Build the list_available_tools response from the live FastMCP registry."""
    category_map = _load_tool_category_map()
    ok, selected_categories, requested = _resolve_tool_domain(domain, category_map)
    available_categories = _available_categories(category_map)

    if not ok:
        return {
            "success": False,
            "stage": "list_available_tools",
            "domain": requested,
            "message": f"Unknown tool domain: {domain}",
            "available_categories": available_categories,
            "aliases": TOOL_DOMAIN_ALIASES,
            "tools": [],
            "total": 0,
        }

    selected = set(selected_categories)
    tools_by_category: dict[str, list[dict[str, Any]]] = {category: [] for category in selected_categories}
    for tool in sorted(mcp._tool_manager.list_tools(), key=lambda t: t.name):
        module = _tool_module_name(tool)
        meta = category_map.get(module, {
            "category": "uncategorized",
            "roadmap_phase": "unknown",
            "status": "unknown",
        })
        category = meta.get("category", "uncategorized")
        if category not in selected:
            continue
        tools_by_category.setdefault(category, []).append({
            "name": tool.name,
            "description": getattr(tool, "description", "") or "",
            "module": module,
            "category": category,
            "roadmap_phase": meta.get("roadmap_phase", "unknown"),
            "status": meta.get("status", "unknown"),
            "parameters": _tool_parameter_names(tool),
        })

    flattened = [
        tool
        for category in selected_categories
        for tool in tools_by_category.get(category, [])
    ]
    return {
        "success": True,
        "stage": "list_available_tools",
        "domain": requested,
        "resolved_categories": selected_categories,
        "available_categories": available_categories,
        "total": len(flattened),
        "tools": flattened,
        "tools_by_category": {
            category: tools_by_category.get(category, [])
            for category in selected_categories
        },
    }

def _start_here_prompt(kb_docs: list[dict[str, str]]) -> str:
    """Build a short onboarding prompt for newly connected agents."""
    kb_hint = "kb://00_AGENT_KNOWLEDGE_BASE.md"
    if kb_docs:
        kb_hint = kb_docs[0]["uri"]
    return (
        "Start by reading get_server_info(), then read "
        f"{kb_hint} and call get_knowledge_base() or search_knowledge_base() "
        "for the subsystem you plan to change. Before mutating Unreal assets, "
        "inspect existing project state and keep every change covered by smoke evidence."
    )

def _resolve_onboarding_task(task: str) -> str | None:
    """Resolve onboarding task names and aliases to a canonical task key."""
    normalized = (task or "").strip().lower().replace("-", "_")
    if normalized in ONBOARDING_CONTEXTS:
        return normalized
    return ONBOARDING_ALIASES.get(normalized)

def _path_for_kb_uri(uri: str) -> Path | None:
    """Map a kb:// URI to a safe local markdown path."""
    if not uri.startswith("kb://"):
        return None
    rel = uri[len("kb://"):]
    if "/" in rel:
        prefix, filename = rel.split("/", 1)
        if prefix not in {"v4", "v5"} or "/" in filename or "\\" in filename:
            return None
        path = KB_DIR / prefix / filename
    else:
        if "\\" in rel:
            return None
        path = KB_DIR / rel
    if path.suffix.lower() != ".md" or not path.exists():
        return None
    return path

def _read_onboarding_doc(uri: str, max_chars: int = 8000) -> dict[str, Any]:
    """Read one curated KB document and return metadata plus bounded content."""
    path = _path_for_kb_uri(uri)
    if not path:
        return {
            "uri": uri,
            "available": False,
            "title": uri,
            "description": "",
            "content": "",
            "truncated": False,
        }
    rel_name = f"{path.parent.name}/{path.name}" if path.parent.name in {"v4", "v5"} else path.name
    title, description = _extract_resource_metadata(path, rel_name)
    content = path.read_text(encoding="utf-8")
    truncated = len(content) > max_chars
    if truncated:
        content = content[:max_chars].rstrip() + "\n\n[truncated]"
    return {
        "uri": uri,
        "available": True,
        "title": title,
        "description": description,
        "content": content,
        "truncated": truncated,
    }

def _missing_expected_docs(paths: list[str]) -> list[str]:
    """Return expected future KB doc paths that are not available yet."""
    missing = []
    for doc_path in paths:
        path = (_REPO_ROOT / doc_path).resolve()
        try:
            path.relative_to(_REPO_ROOT.resolve())
        except ValueError:
            missing.append(doc_path)
            continue
        if not path.exists():
            missing.append(doc_path)
    return missing

def _parse_exec_python_json(response: dict[str, Any]) -> dict[str, Any]:
    """Extract a JSON object from common exec_python response envelopes."""
    if not response:
        return {"success": False, "message": "No response from Unreal Engine"}
    if response.get("status") == "error" or response.get("success") is False:
        return {
            "success": False,
            "message": response.get("error") or response.get("message") or "exec_python failed",
        }

    inner = response.get("result") or response.get("outputs") or response
    if isinstance(inner, dict) and "output" not in inner and "command_result" not in inner:
        return inner

    candidates = []
    if isinstance(inner, dict):
        output = inner.get("output", "") or ""
        command_result = inner.get("command_result", "") or ""
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("[Info] "):
                line = line[len("[Info] "):].strip()
            candidates.append(line)
        if command_result:
            candidates.append(command_result.strip())

    for line in reversed(candidates):
        if line.startswith("{") and line.endswith("}"):
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue

    return {"success": False, "message": f"Could not parse exec_python JSON output: {candidates!r}"}

def _project_context_code() -> str:
    """Return UE Python code for collecting live editor/project context."""
    return r'''
import json
import os

def _name(value):
    try:
        if hasattr(value, "get_name"):
            return str(value.get_name())
        if hasattr(value, "get_path_name"):
            return str(value.get_path_name())
    except Exception:
        pass
    return str(value)

def _dedupe_dicts(items, key):
    out = []
    seen = set()
    for item in items:
        marker = item.get(key)
        if marker in seen:
            continue
        seen.add(marker)
        out.append(item)
    return out

result = {
    "success": True,
    "stage": "get_project_context",
    "uproject": "",
    "project_name": "",
    "engine_version": "",
    "open_level": None,
    "selected_actor": None,
    "selected_actors": [],
    "dirty_packages": [],
    "content_folders": [],
    "plugins": [],
}

try:
    result["project_name"] = str(unreal.SystemLibrary.get_project_name())
except Exception:
    pass

try:
    result["engine_version"] = str(unreal.SystemLibrary.get_engine_version())
except Exception:
    pass

try:
    result["uproject"] = str(unreal.Paths.get_project_file_path())
except Exception:
    try:
        project_dir = str(unreal.Paths.project_dir())
        project_name = result.get("project_name") or ""
        if project_dir and project_name:
            result["uproject"] = os.path.join(project_dir, project_name + ".uproject")
    except Exception:
        pass

try:
    world = unreal.EditorLevelLibrary.get_editor_world()
    if world:
        package_name = ""
        try:
            package_name = str(world.get_outermost().get_name())
        except Exception:
            pass
        result["open_level"] = {
            "map_name": str(world.get_map_name()),
            "package_name": package_name,
        }
except Exception:
    pass

try:
    selected = unreal.EditorLevelLibrary.get_selected_level_actors()
    actors = []
    for actor in selected or []:
        item = {
            "name": "",
            "class": "",
            "path": "",
        }
        try:
            item["name"] = str(actor.get_actor_label())
        except Exception:
            item["name"] = _name(actor)
        try:
            item["class"] = str(actor.get_class().get_name())
        except Exception:
            pass
        try:
            item["path"] = str(actor.get_path_name())
        except Exception:
            pass
        actors.append(item)
    result["selected_actors"] = actors
    result["selected_actor"] = actors[0] if actors else None
except Exception:
    pass

try:
    dirty = []
    utils = unreal.EditorLoadingAndSavingUtils
    for func_name in ("get_dirty_content_packages", "get_dirty_map_packages"):
        try:
            func = getattr(utils, func_name)
            for package in func() or []:
                dirty.append(_name(package))
        except Exception:
            pass
    result["dirty_packages"] = sorted(set(dirty))
except Exception:
    pass

try:
    content_dir = str(unreal.Paths.project_content_dir())
    if os.path.isdir(content_dir):
        result["content_folders"] = sorted(
            name for name in os.listdir(content_dir)
            if os.path.isdir(os.path.join(content_dir, name))
        )
except Exception:
    pass

try:
    plugins = []
    uproject = result.get("uproject") or ""
    if uproject and os.path.isfile(uproject):
        try:
            with open(uproject, "r", encoding="utf-8") as f:
                data = json.load(f)
            for plugin in data.get("Plugins", []) or []:
                plugins.append({
                    "name": str(plugin.get("Name", "")),
                    "enabled": bool(plugin.get("Enabled", False)),
                    "source": "uproject",
                })
        except Exception:
            pass

    try:
        pbl = getattr(unreal, "PluginBlueprintLibrary", None)
        if pbl:
            for method_name in ("get_enabled_plugin_names", "get_enabled_plugins"):
                method = getattr(pbl, method_name, None)
                if not method:
                    continue
                for plugin in method() or []:
                    plugins.append({
                        "name": _name(plugin),
                        "enabled": True,
                        "source": method_name,
                    })
                break
    except Exception:
        pass

    result["plugins"] = _dedupe_dicts([p for p in plugins if p.get("name")], "name")
except Exception:
    pass

_result = result
print(json.dumps(result))
'''

def _fetch_project_context_live() -> dict[str, Any]:
    """Collect project context through the UE exec_python bridge."""
    try:
        from unreal_mcp_server import get_unreal_connection
        unreal = get_unreal_connection()
        if not unreal:
            return {
                "success": False,
                "stage": "get_project_context",
                "message": "Not connected to Unreal Engine",
            }
        response = unreal.send_command("exec_python", {"code": _project_context_code()})
        parsed = _parse_exec_python_json(response or {})
        parsed.setdefault("stage", "get_project_context")
        return parsed
    except Exception as exc:
        return {
            "success": False,
            "stage": "get_project_context",
            "message": str(exc),
        }

def _scan_project_assets_live(path: str, depth: int, class_filter: str) -> dict[str, Any]:
    """Scan Content Browser assets through the UE Asset Registry."""
    normalized_path = (path or "/Game").strip() or "/Game"
    if not normalized_path.startswith("/"):
        normalized_path = f"/{normalized_path}"
    if normalized_path == "/Game/":
        normalized_path = "/Game"
    else:
        normalized_path = normalized_path.rstrip("/")
    depth = max(0, int(depth))
    class_filters = [
        item.strip()
        for item in re.split(r"[,;|]", class_filter or "")
        if item.strip()
    ]

    code = f'''
import json
import os
from collections import Counter

scan_path = {normalized_path!r}
depth = {depth!r}
class_filters = {json.dumps(class_filters)}

def _class_name(asset_data):
    try:
        class_path = str(asset_data.asset_class_path)
        if "." in class_path:
            return class_path.rsplit(".", 1)[-1]
        if "/" in class_path:
            return class_path.rsplit("/", 1)[-1]
        return class_path
    except Exception:
        try:
            return str(asset_data.asset_class)
        except Exception:
            return ""

def _package_size(package_name):
    try:
        filename = unreal.PackageName.long_package_name_to_filename(str(package_name), ".uasset")
        if filename and os.path.exists(filename):
            return int(os.path.getsize(filename))
    except Exception:
        pass
    return 0

def _depth_from_base(package_path, base_path):
    package_path = str(package_path).rstrip("/")
    base_path = str(base_path).rstrip("/")
    if package_path == base_path:
        return 0
    prefix = base_path + "/"
    if package_path.startswith(prefix):
        rel = package_path[len(prefix):].strip("/")
        return 0 if not rel else len(rel.split("/"))
    return 999999

result = {{
    "success": True,
    "stage": "scan_project_assets",
    "path": scan_path,
    "depth": depth,
    "class_filter": class_filters,
    "total_assets": 0,
    "returned_assets": 0,
    "total_size_bytes": 0,
    "by_class": {{}},
    "assets": [],
}}

reg = unreal.AssetRegistryHelpers.get_asset_registry()
flt = unreal.ARFilter()
flt.package_paths = [scan_path]
flt.recursive_paths = True
flt.recursive_classes = True
assets = reg.get_assets(flt) or []

by_class = Counter()
rows = []
for asset in assets:
    package_path = str(asset.package_path)
    folder_depth = _depth_from_base(package_path, scan_path)
    if folder_depth > depth:
        continue

    cls = _class_name(asset)
    if class_filters and cls.lower() not in {{c.lower() for c in class_filters}}:
        continue

    package_name = str(asset.package_name)
    size_bytes = _package_size(package_name)
    try:
        referencers = reg.get_referencers(package_name, unreal.AssetRegistryDependencyType.ALL) or []
    except Exception:
        referencers = []
    try:
        dependencies = reg.get_dependencies(package_name, unreal.AssetRegistryDependencyType.ALL) or []
    except Exception:
        dependencies = []

    by_class[cls or "Unknown"] += 1
    rows.append({{
        "package_name": package_name,
        "asset_name": str(asset.asset_name),
        "package_path": package_path,
        "class": cls,
        "class_path": str(asset.asset_class_path) if hasattr(asset, "asset_class_path") else cls,
        "object_path": str(asset.get_soft_object_path()) if hasattr(asset, "get_soft_object_path") else "",
        "size_bytes": size_bytes,
        "references_count": len(referencers),
        "dependencies_count": len(dependencies),
        "folder_depth": folder_depth,
    }})

rows.sort(key=lambda item: item["package_name"])
result["assets"] = rows
result["total_assets"] = len(rows)
result["returned_assets"] = len(rows)
result["total_size_bytes"] = sum(item["size_bytes"] for item in rows)
result["by_class"] = dict(sorted(by_class.items()))

_result = result
print(json.dumps(result))
'''

    try:
        from unreal_mcp_server import get_unreal_connection
        unreal = get_unreal_connection()
        if not unreal:
            return {
                "success": False,
                "stage": "scan_project_assets",
                "message": "Not connected to Unreal Engine",
            }
        response = unreal.send_command("exec_python", {"code": code})
        parsed = _parse_exec_python_json(response or {})
        parsed.setdefault("stage", "scan_project_assets")
        return parsed
    except Exception as exc:
        return {
            "success": False,
            "stage": "scan_project_assets",
            "message": str(exc),
        }

# ── MCP Tools ────────────────────────────────────────────────────────────────

def register_knowledge_tools(mcp):
    _register_kb_markdown_resources(mcp)

    @mcp.tool()
    def get_server_info() -> str:
        """
        Return Unreal-MCP-Ghost server version, transport, tool count, KB docs,
        and a start-here prompt for newly connected MCP agents.

        KB: see knowledge_base/00_AGENT_KNOWLEDGE_BASE.md#mandatory-agent-rules

        Example:
            get_server_info()
        """
        kb_docs = _kb_doc_list(mcp)
        tools = mcp._tool_manager.list_tools()
        resources = mcp._resource_manager.list_resources()
        payload = {
            "success": True,
            "version": _server_version(),
            "tool_count": len(tools),
            "transport": _server_transport(),
            "kb_doc_count": len(kb_docs),
            "kb_docs": kb_docs,
            "resource_count": len(resources),
            "start_here": _start_here_prompt(kb_docs),
        }
        return json.dumps(payload, indent=2)

    @mcp.tool()
    def get_project_context(force_refresh: bool = False) -> str:
        """
        Return the current Unreal project/editor context with a 5 second cache.

        Includes the .uproject path, engine version, open level, selected actor,
        dirty packages, top-level Content folders, and project/plugin list.

        KB: see knowledge_base/00_AGENT_KNOWLEDGE_BASE.md#mandatory-agent-rules

        Example:
            get_project_context()
        """
        global _PROJECT_CONTEXT_CACHE
        now = time.monotonic()
        cached_context = _PROJECT_CONTEXT_CACHE.get("context")
        cached_at = float(_PROJECT_CONTEXT_CACHE.get("timestamp") or 0.0)
        cache_age = now - cached_at

        if (
            not force_refresh
            and isinstance(cached_context, dict)
            and cache_age <= PROJECT_CONTEXT_CACHE_TTL_S
        ):
            payload = dict(cached_context)
            payload["cached"] = True
            payload["cache_age_s"] = round(cache_age, 3)
            payload["cache_ttl_s"] = PROJECT_CONTEXT_CACHE_TTL_S
            return json.dumps(payload, indent=2)

        context = _fetch_project_context_live()
        if context.get("success") is not False:
            _PROJECT_CONTEXT_CACHE = {"timestamp": now, "context": dict(context)}

        payload = dict(context)
        payload["cached"] = False
        payload["cache_age_s"] = 0.0
        payload["cache_ttl_s"] = PROJECT_CONTEXT_CACHE_TTL_S
        return json.dumps(payload, indent=2)

    @mcp.tool()
    def get_onboarding_context(task: str) -> str:
        """Return a curated knowledge-base packet for a specific Unreal task domain.

        Supported tasks: blueprints, animation, ai, materials, niagara, umg,
        world_building, audio, generative, multiplayer, gas, metasounds.

        KB: see knowledge_base/00_AGENT_KNOWLEDGE_BASE.md#mandatory-agent-rules

        Example:
            get_onboarding_context(task="Example")"""
        canonical = _resolve_onboarding_task(task)
        if not canonical:
            return json.dumps({
                "success": False,
                "stage": "get_onboarding_context",
                "task": task,
                "message": f"Unknown onboarding task: {task}",
                "available_tasks": sorted(ONBOARDING_CONTEXTS.keys()),
                "aliases": ONBOARDING_ALIASES,
            }, indent=2)

        spec = ONBOARDING_CONTEXTS[canonical]
        expected_future_docs = spec.get("expected_future_docs", [])
        missing_docs = _missing_expected_docs(expected_future_docs)
        docs = [_read_onboarding_doc(uri) for uri in spec["uris"]]
        missing_uris = [doc["uri"] for doc in docs if not doc["available"]]
        warnings = []
        if missing_uris:
            warnings.append(f"Missing configured KB resources: {', '.join(missing_uris)}")
        if missing_docs:
            warnings.append(
                "Future Workstream A.7 docs not present yet: " + ", ".join(missing_docs)
            )

        payload = {
            "success": True,
            "stage": "get_onboarding_context",
            "task": canonical,
            "requested_task": task,
            "title": spec["title"],
            "summary": (
                "Read these docs before acting, then call get_project_context() "
                "and inspect the relevant assets/tools before mutation."
            ),
            "resource_uris": spec["uris"],
            "documents": docs,
            "tool_domains": spec.get("tool_domains", []),
            "workflow": spec.get("workflow", []),
            "expected_future_docs": expected_future_docs,
            "missing_expected_docs": missing_docs,
            "warnings": warnings,
            "available_tasks": sorted(ONBOARDING_CONTEXTS.keys()),
        }
        return json.dumps(payload, indent=2)

    @mcp.tool()
    def scan_project_assets(
        path: str = "/Game",
        depth: int = 2,
        class_filter: str = "",
    ) -> str:
        """Scan Content Browser assets via the Unreal Asset Registry.

        Returns structured inventory rows with class, size, referencer count,
        dependency count, package path, and folder depth.

        KB: see knowledge_base/12_MCP_TOOL_USAGE_GUIDE.md#asset-creation-patterns

        Example:
            scan_project_assets()"""
        if not path or not str(path).strip():
            path = "/Game"
        if depth < 0:
            depth = 0

        result = _scan_project_assets_live(path, depth, class_filter)
        payload = {
            "success": bool(result.get("success", True)),
            "stage": result.get("stage", "scan_project_assets"),
            "message": result.get(
                "message",
                f"Scanned {result.get('total_assets', 0)} assets under {result.get('path', path)}",
            ),
            "path": result.get("path", path),
            "depth": result.get("depth", depth),
            "class_filter": result.get("class_filter", []),
            "total_assets": result.get("total_assets", 0),
            "returned_assets": result.get("returned_assets", len(result.get("assets", []))),
            "total_size_bytes": result.get("total_size_bytes", 0),
            "by_class": result.get("by_class", {}),
            "assets": result.get("assets", []),
            "warnings": result.get("warnings", []),
            "errors": result.get("errors", []),
        }
        if "error_code" in result:
            payload["error_code"] = result["error_code"]
        return json.dumps(payload, indent=2)

    @mcp.tool()
    def list_available_tools(domain: str = "all") -> str:
        """List available MCP tools by domain/category using tool_inventory_categories.json.

        Pass a category such as blueprint_graph, ui_umg, asset_import, or a
        friendly domain alias such as blueprints, generative, multiplayer, gas,
        or world_building.

        KB: see knowledge_base/12_MCP_TOOL_USAGE_GUIDE.md#complete-command-reference

        Example:
            list_available_tools()"""
        return json.dumps(_tool_discovery_payload(mcp, domain), indent=2)

    @mcp.tool()
    def list_knowledge_base_topics() -> str:
        """List all available knowledge base topics.

        Returns an index of every topic you can query with get_knowledge_base().
        Call this first if you are unsure which topic covers the system you need.

        MANDATORY: Query the knowledge base before implementing any UE5 system.

        KB: see knowledge_base/00_AGENT_KNOWLEDGE_BASE.md#overview
        Example:
            list_knowledge_base_topics()"""
        lines = [
            "# Knowledge Base Topics",
            "",
            "Call get_knowledge_base(topic) with any topic below.",
            "Each topic includes hand-written reference docs + book extracts from",
            "4 UE5 textbooks (Romero, Tan, Penninck, Alam).",
            "",
            "## Core Reference Topics",
            "  overview         — Agent rules, mandatory guidelines, master index",
            "  blueprints       — Blueprint fundamentals: nodes, pins, variables, functions",
            "  communication    — Interfaces, event dispatchers, casting, references",
            "  gameplay         — GameMode, PlayerController, Character, Pawn, GameInstance",
            "  ai               — Behavior Trees, Blackboards, AIController, NavMesh, sensing",
            "  animation        — State machines, blend spaces, AnimBP, montages, notifies",
            "  ui               — UMG widgets, HUD, buttons, text blocks, menus",
            "  data             — Structs, enums, data tables, arrays, maps, save game",
            "  materials        — Materials, material instances, dynamic materials, rendering",
            "  niagara          — Niagara VFX, particle systems, emitters",
            "  world            — Level design, world building, streaming",
            "  components       — Actor/Scene components, component libraries",
            "  input            — Enhanced Input, action mappings, key bindings",
            "  cookbook         — Game systems cookbook: health, damage, inventory, etc.",
            "  packaging        — Packaging, optimization, performance, LOD",
            "",
            "## Deep-Dive Topics",
            "  animation_deep   — Advanced animation: IK, blend trees, retargeting",
            "  technical_art    — Technical art: optimization, shaders, procedural",
            "  vfx              — VFX deep-dive: Niagara + materials",
            "  tools            — Complete MCP tool usage guide with examples",
            "  roadmap          — Tool expansion roadmap, development status",
            "  dantooine        — Project-specific reference (asset list, folder map, implementation status)",
            "",
            "## Usage",
            "  get_knowledge_base('ai')          → AI systems reference + book extracts",
            "  get_knowledge_base('blueprints')  → Blueprint fundamentals + book extracts",
            "  search_knowledge_base('behavior tree task') → keyword search across all files",
        ]
        return "\n".join(lines)

    @mcp.tool()
    def get_knowledge_base(topic: str) -> str:
        """Retrieve knowledge base content for a given topic.

        Returns the full content of the matching reference doc(s) plus
        relevant book extracts from 4 UE5 textbooks. This is the primary
        anti-hallucination tool — always call this before implementing a system.

        Args:
            topic: Topic to retrieve. Use list_knowledge_base_topics() to see all options.
                   Examples: "ai", "blueprints", "animation", "ui", "materials",
                             "gameplay", "input", "data", "communication", "components"

        MANDATORY RULE: Call this tool before implementing ANY UE5 system.
          Before AI systems    → get_knowledge_base("ai")
          Before animation     → get_knowledge_base("animation")
          Before UI/HUD        → get_knowledge_base("ui")
          Before gameplay      → get_knowledge_base("gameplay")
          Before materials     → get_knowledge_base("materials")
          Before input         → get_knowledge_base("input")
          Before data/structs  → get_knowledge_base("data")
          Before communication → get_knowledge_base("communication")

        KB: see knowledge_base/00_AGENT_KNOWLEDGE_BASE.md#overview
        Example:
            get_knowledge_base(topic="Example")"""
        canonical = _resolve_topic(topic)
        if canonical is None:
            # Try a search as fallback
            available = ", ".join(sorted(TOPIC_MAP.keys()))
            return (
                f"Topic '{topic}' not found.\n\n"
                f"Available topics: {available}\n\n"
                f"Try search_knowledge_base('{topic}') for a keyword search across all files."
            )

        filenames = TOPIC_MAP[canonical]
        sections = []

        for filename in filenames:
            # Check both dirs
            content = _read_file(filename)
            if content:
                label = "📚 Book Extract" if filename.startswith("BOOK_") else "📖 Reference Doc"
                sections.append(f"<!-- {label}: {filename} -->\n\n{content}")

        if not sections:
            return f"No content found for topic '{topic}'. Files expected: {filenames}"

        header = (
            f"# Knowledge Base: {canonical.upper()}\n\n"
            f"> Sources: {', '.join(filenames)}\n"
            f"> IMPORTANT: Read this carefully before implementing. "
            f"Parameter names and patterns here are authoritative.\n\n"
            "---\n\n"
        )
        return header + "\n\n---\n\n".join(sections)

    @mcp.tool()
    def search_knowledge_base(query: str) -> str:
        """Search across all knowledge base files for a keyword or phrase.

        Returns matching sections from both hand-written reference docs and
        book extracts. Use this when you need a specific term, function name,
        pattern, or concept and don't know which topic file covers it.

        Args:
            query: Keyword or phrase to search for.
                   Examples: "behavior tree task", "blend space", "data table row",
                             "event dispatcher", "spawn actor", "material parameter"

        KB: see knowledge_base/00_AGENT_KNOWLEDGE_BASE.md#overview
        Example:
            search_knowledge_base(query="Example")"""
        if not query or len(query.strip()) < 2:
            return "Please provide a search query of at least 2 characters."

        query_lower = query.lower().strip()
        terms = query_lower.split()
        results = []

        all_files = _all_kb_files()

        for filename, content in all_files:
            content_lower = content.lower()

            # Score: count total term occurrences
            score = sum(content_lower.count(term) for term in terms)
            if score == 0:
                continue

            # Extract relevant snippets (paragraphs containing the terms)
            snippets = []
            paragraphs = re.split(r'\n\n+', content)
            for para in paragraphs:
                para_lower = para.lower()
                para_score = sum(para_lower.count(term) for term in terms)
                if para_score > 0 and len(para.strip()) > 50:
                    # Highlight matches
                    snippet = para.strip()[:800]
                    snippets.append((para_score, snippet))

            if snippets:
                snippets.sort(key=lambda x: x[0], reverse=True)
                top_snippets = [s[1] for s in snippets[:3]]
                label = "📚 Book" if filename.startswith("BOOK_") else "📖 Ref"
                results.append((score, filename, label, top_snippets))

        if not results:
            return (
                f"No results found for '{query}'.\n\n"
                f"Try broader terms or use list_knowledge_base_topics() "
                f"to browse available topics."
            )

        results.sort(key=lambda x: x[0], reverse=True)
        top_results = results[:6]

        lines = [
            f"# Search Results: '{query}'",
            f"",
            f"Found matches in {len(results)} files. Showing top {len(top_results)}.",
            f"Use get_knowledge_base(topic) to retrieve the full file.",
            f"",
            "---",
            "",
        ]

        for score, filename, label, snippets in top_results:
            # Map filename back to topic
            topic_hint = ""
            for topic, files in TOPIC_MAP.items():
                if filename in files or filename.replace("BOOK_", "").replace(".md", "").lower() in topic:
                    topic_hint = f" → get_knowledge_base('{topic}')"
                    break

            lines.append(f"## {label}: {filename} (score: {score}){topic_hint}")
            lines.append("")
            for snippet in snippets:
                lines.append(snippet)
                lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)
