"""Build a static inventory of registered Unreal-MCP-Ghost tools.

This is the canonical offline inventory command for Phase 0 registry hygiene.
It scans FastMCP decorators without importing the full server or connecting to
Unreal Editor.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = REPO_ROOT / "unreal_mcp_server"
CATEGORY_MAP_PATH = SERVER_ROOT / "tool_inventory_categories.json"
TOOL_RE = re.compile(
    r"@mcp\.tool\(\)\s+(?:async\s+def|def)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
    re.MULTILINE,
)


def _module_name(path: Path) -> str:
    rel = path.relative_to(SERVER_ROOT).with_suffix("")
    return ".".join(rel.parts)


def load_category_map(path: Path = CATEGORY_MAP_PATH) -> Dict[str, Dict[str, str]]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_tool_files() -> Iterable[Path]:
    for root_name in ("tools", "skills"):
        root = SERVER_ROOT / root_name
        if not root.exists():
            continue
        yield from sorted(root.rglob("*.py"))


def build_inventory() -> Dict[str, Any]:
    categories = load_category_map()
    modules: List[Dict[str, Any]] = []
    missing_category: List[str] = []

    for path in iter_tool_files():
        text = path.read_text(encoding="utf-8")
        tool_names = TOOL_RE.findall(text)
        if not tool_names:
            continue

        module = _module_name(path)
        meta = categories.get(module)
        if meta is None:
            missing_category.append(module)
            meta = {"category": "uncategorized", "roadmap_phase": "unknown", "status": "unknown"}

        modules.append(
            {
                "module": module,
                "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "tool_count": len(tool_names),
                "tools": tool_names,
                "category": meta["category"],
                "roadmap_phase": meta["roadmap_phase"],
                "status": meta["status"],
            }
        )

    category_counts = Counter()
    phase_counts = Counter()
    status_counts = Counter()
    for module in modules:
        category_counts[module["category"]] += module["tool_count"]
        phase_counts[module["roadmap_phase"]] += module["tool_count"]
        status_counts[module["status"]] += module["tool_count"]

    return {
        "tool_count": sum(module["tool_count"] for module in modules),
        "module_count": len(modules),
        "modules": modules,
        "category_counts": dict(sorted(category_counts.items())),
        "phase_counts": dict(sorted(phase_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "missing_category_modules": missing_category,
    }


def format_summary(inventory: Dict[str, Any]) -> str:
    lines = [
        f"tool_count={inventory['tool_count']}",
        f"module_count={inventory['module_count']}",
        "",
        "Tools by status:",
    ]
    for status, count in inventory["status_counts"].items():
        lines.append(f"  {status}: {count}")
    lines.append("")
    lines.append("Tools by roadmap phase:")
    for phase, count in inventory["phase_counts"].items():
        lines.append(f"  {phase}: {count}")
    return "\n".join(lines)


def format_markdown(inventory: Dict[str, Any]) -> str:
    lines = [
        "# MCP Tool Inventory",
        "",
        f"- Tools: {inventory['tool_count']}",
        f"- Modules: {inventory['module_count']}",
        "",
        "| Module | Tools | Category | Roadmap phase | Status |",
        "|---|---:|---|---|---|",
    ]
    for module in inventory["modules"]:
        lines.append(
            f"| `{module['module']}` | {module['tool_count']} | "
            f"{module['category']} | {module['roadmap_phase']} | {module['status']} |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Print the static MCP tool inventory.")
    parser.add_argument("--json", action="store_true", help="Print full inventory as JSON.")
    parser.add_argument("--markdown", action="store_true", help="Print inventory as Markdown.")
    args = parser.parse_args()

    inventory = build_inventory()
    if args.json:
        print(json.dumps(inventory, indent=2, sort_keys=True))
    elif args.markdown:
        print(format_markdown(inventory))
    else:
        print(format_summary(inventory))
    return 1 if inventory["missing_category_modules"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
