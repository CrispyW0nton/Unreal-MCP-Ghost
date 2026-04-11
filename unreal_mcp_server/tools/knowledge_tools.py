"""
knowledge_tools.py — MCP tools for querying the Unreal-MCP-Ghost knowledge base.

Three tools:
  list_knowledge_base_topics()     → index of all available topics
  get_knowledge_base(topic)        → full content of a topic file
  search_knowledge_base(query)     → keyword search across all KB files

The knowledge base consists of two layers:
  1. knowledge_base/*.md           — hand-written reference docs (19 files)
  2. knowledge_base/book_extracts/ — PDF-extracted book content (10 topic files)

MANDATORY AGENT RULE: Query the knowledge base BEFORE implementing any system.
"""

import os
import re
from pathlib import Path

# Resolve KB directory relative to this file
_THIS_DIR = Path(__file__).parent
_REPO_ROOT = _THIS_DIR.parent.parent
KB_DIR = _REPO_ROOT / "knowledge_base"
BOOK_DIR = KB_DIR / "book_extracts"

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

# ── MCP Tools ────────────────────────────────────────────────────────────────

def register_knowledge_tools(mcp):

    @mcp.tool()
    def list_knowledge_base_topics() -> str:
        """
        List all available knowledge base topics.

        Returns an index of every topic you can query with get_knowledge_base().
        Call this first if you are unsure which topic covers the system you need.

        MANDATORY: Query the knowledge base before implementing any UE5 system.
        """
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
        """
        Retrieve knowledge base content for a given topic.

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
        """
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
        """
        Search across all knowledge base files for a keyword or phrase.

        Returns matching sections from both hand-written reference docs and
        book extracts. Use this when you need a specific term, function name,
        pattern, or concept and don't know which topic file covers it.

        Args:
            query: Keyword or phrase to search for.
                   Examples: "behavior tree task", "blend space", "data table row",
                             "event dispatcher", "spawn actor", "material parameter"
        """
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
