"""Lint FastMCP tool docstrings for KB links and examples."""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = REPO_ROOT / "unreal_mcp_server"
TOOL_INVENTORY_PATH = REPO_ROOT / "scripts" / "tool_inventory.py"

KB_RE = re.compile(r"^\s*KB:\s+see\s+knowledge_base/(?:v\d+/)?[A-Za-z0-9_./ -]+\.md#[A-Za-z0-9_-]+", re.MULTILINE)
EXAMPLE_RE = re.compile(r"^\s*Example:\s*$", re.MULTILINE)


def _load_tool_inventory():
    spec = importlib.util.spec_from_file_location("tool_inventory", TOOL_INVENTORY_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _tool_functions(path: Path, tool_names: set[str]) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in tool_names
    }


def lint_tool_docstrings(include_untracked: bool = False) -> dict[str, Any]:
    """Return docstring lint results for FastMCP tools."""
    inventory_module = _load_tool_inventory()
    inventory = inventory_module.build_inventory(include_untracked=include_untracked)
    violations: list[dict[str, Any]] = []
    checked = 0

    for module in inventory["modules"]:
        path = REPO_ROOT / module["path"]
        functions = _tool_functions(path, set(module["tools"]))
        for tool_name in module["tools"]:
            checked += 1
            node = functions.get(tool_name)
            docstring = ast.get_docstring(node) if node else None
            missing: list[str] = []
            if not docstring:
                missing.append("docstring")
            else:
                if not KB_RE.search(docstring):
                    missing.append("KB")
                if not EXAMPLE_RE.search(docstring):
                    missing.append("Example")

            if missing:
                violations.append(
                    {
                        "module": module["module"],
                        "path": module["path"],
                        "tool": tool_name,
                        "line": getattr(node, "lineno", None),
                        "missing": missing,
                    }
                )

    return {
        "success": not violations,
        "checked": checked,
        "violations": violations,
        "violation_count": len(violations),
        "source_scope": inventory["source_scope"],
    }


def format_markdown(result: dict[str, Any], limit: int = 80) -> str:
    lines = [
        "# Tool Docstring Lint",
        "",
        f"- Checked: {result['checked']}",
        f"- Violations: {result['violation_count']}",
        f"- Source scope: {result['source_scope']}",
    ]
    if not result["violations"]:
        lines.append("")
        lines.append("All FastMCP tool docstrings include a KB link and an example.")
        return "\n".join(lines)

    lines.extend(
        [
            "",
            "| Tool | Missing | Location |",
            "|---|---|---|",
        ]
    )
    for violation in result["violations"][:limit]:
        location = violation["path"]
        if violation["line"]:
            location = f"{location}:{violation['line']}"
        lines.append(
            f"| `{violation['tool']}` | {', '.join(violation['missing'])} | `{location}` |"
        )
    remaining = len(result["violations"]) - limit
    if remaining > 0:
        lines.append("")
        lines.append(f"...and {remaining} more violations.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate FastMCP tool docstrings.")
    parser.add_argument("--json", action="store_true", help="Print lint results as JSON.")
    parser.add_argument("--include-untracked", action="store_true", help="Include untracked tool files.")
    parser.add_argument("--limit", type=int, default=80, help="Maximum violations to print in Markdown.")
    args = parser.parse_args()

    result = lint_tool_docstrings(include_untracked=args.include_untracked)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(format_markdown(result, limit=args.limit))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
