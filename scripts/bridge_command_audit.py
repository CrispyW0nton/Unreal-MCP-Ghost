"""Audit Python-to-C++ bridge command routing metadata.

Phase 7 Slice 2: keep a machine-readable command registry so Python tool
wrappers and C++ bridge handlers do not quietly drift apart. The audit is
static and offline; it reads source files and never connects to Unreal Editor.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = REPO_ROOT / "unreal_mcp_server"
PLUGIN_ROOT = REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCP"
DEFAULT_REGISTRY = SERVER_ROOT / "bridge_command_registry.json"

CPP_COMMAND_RE = re.compile(
    r"CommandType\s*(?:==|\.Equals\()\s*TEXT\(\"([A-Za-z0-9_]+)\"\)",
)

BRIDGE_CALL_NAMES = {
    "_send",
    "_send_command",
    "_call",
    "_execute",
    "send_command",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("\\", "/")


def _git_tracked_paths(prefixes: List[str]) -> Optional[List[Path]]:
    try:
        completed = subprocess.run(
            ["git", "ls-files", *prefixes],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return [REPO_ROOT / line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _iter_python_files(include_untracked: bool = False) -> Iterable[Path]:
    if not include_untracked:
        tracked = _git_tracked_paths(["unreal_mcp_server/tools", "unreal_mcp_server/skills", "unreal_mcp_server/ue5cli.py"])
        if tracked is not None:
            return sorted(path for path in tracked if path.suffix == ".py")
    files: List[Path] = []
    for root in (SERVER_ROOT / "tools", SERVER_ROOT / "skills"):
        if root.exists():
            files.extend(root.rglob("*.py"))
    extra = SERVER_ROOT / "ue5cli.py"
    if extra.exists():
        files.append(extra)
    return sorted(files)


def _iter_cpp_files(include_untracked: bool = False) -> Iterable[Path]:
    if not PLUGIN_ROOT.exists():
        return []
    if not include_untracked:
        tracked = _git_tracked_paths(["unreal_plugin/Source/UnrealMCP"])
        if tracked is not None:
            return sorted(path for path in tracked if path.suffix in {".cpp", ".h"})
    return sorted([*PLUGIN_ROOT.rglob("*.cpp"), *PLUGIN_ROOT.rglob("*.h")])


def _category_for(command: str) -> str:
    prefixes = {
        "anim_": "animation",
        "bp_": "blueprint_graph",
        "bt_": "ai_behavior_tree",
        "crowd_": "ai_navigation",
        "eqs_": "ai_eqs",
        "material_": "technical_art",
        "mesh_": "technical_art",
        "nav_": "ai_navigation",
        "net_": "networking",
        "network_": "networking",
        "niagara_": "niagara_vfx",
        "perception_": "ai_perception",
        "pie_": "autonomous_verification",
        "renderer_": "technical_art",
        "session_": "networking",
        "shader_": "technical_art",
        "texture_": "technical_art",
        "vertex_": "technical_art",
        "viewport_": "autonomous_verification",
        "widget_": "ui_umg",
    }
    for prefix, category in prefixes.items():
        if command.startswith(prefix):
            return category
    if "blueprint" in command:
        return "blueprint"
    if "widget" in command or "umg" in command or "hud" in command:
        return "ui_umg"
    if command.startswith("create_behavior") or "blackboard" in command:
        return "ai_behavior_tree"
    if command.startswith("exec_python"):
        return "execution_substrate"
    return "general"


class PythonCommandVisitor(ast.NodeVisitor):
    def __init__(self, path: Path):
        self.path = path
        self.assignments: List[Dict[str, str]] = [{}]
        self.function_params: List[Set[str]] = [set()]
        self.commands: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.unresolved: List[Dict[str, Any]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self.assignments.append({})
        self.function_params.append({arg.arg for arg in node.args.args})
        self.generic_visit(node)
        self.function_params.pop()
        self.assignments.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Assign(self, node: ast.Assign) -> Any:
        value = self._constant_string(node.value)
        if value is not None:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.assignments[-1][target.id] = value
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
        value = self._constant_string(node.value)
        if value is not None and isinstance(node.target, ast.Name):
            self.assignments[-1][node.target.id] = value
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> Any:
        if self._is_bridge_call(node.func) and node.args:
            command = self._resolve_command_arg(node.args[0])
            if command:
                self.commands[command].append({"path": _rel(self.path), "line": node.lineno})
            elif self._is_current_function_param(node.args[0]):
                pass
            else:
                self.unresolved.append(
                    {
                        "path": _rel(self.path),
                        "line": node.lineno,
                        "arg": ast.unparse(node.args[0]) if hasattr(ast, "unparse") else type(node.args[0]).__name__,
                    }
                )
        self.generic_visit(node)

    def _is_bridge_call(self, func: ast.AST) -> bool:
        if isinstance(func, ast.Attribute):
            return func.attr == "send_command"
        if isinstance(func, ast.Name):
            return func.id in BRIDGE_CALL_NAMES
        return False

    def _resolve_command_arg(self, node: ast.AST) -> Optional[str]:
        value = self._constant_string(node)
        if value is not None:
            return value
        if isinstance(node, ast.Name):
            for scope in reversed(self.assignments):
                if node.id in scope:
                    return scope[node.id]
        return None

    def _is_current_function_param(self, node: ast.AST) -> bool:
        return isinstance(node, ast.Name) and any(node.id in params for params in reversed(self.function_params))

    @staticmethod
    def _constant_string(node: Optional[ast.AST]) -> Optional[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None


def extract_python_commands(include_untracked: bool = False) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]]:
    commands: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    unresolved: List[Dict[str, Any]] = []
    for path in _iter_python_files(include_untracked=include_untracked):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            unresolved.append({"path": _rel(path), "line": exc.lineno, "arg": f"SyntaxError: {exc.msg}"})
            continue
        visitor = PythonCommandVisitor(path)
        visitor.visit(tree)
        for command, sources in visitor.commands.items():
            commands[command].extend(sources)
        unresolved.extend(visitor.unresolved)
    return dict(sorted(commands.items())), unresolved


def extract_cpp_commands(include_untracked: bool = False) -> Dict[str, List[Dict[str, Any]]]:
    commands: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for path in _iter_cpp_files(include_untracked=include_untracked):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for index, line in enumerate(lines, start=1):
            if "CommandType" not in line or "TEXT(" not in line:
                continue
            for match in CPP_COMMAND_RE.finditer(line):
                commands[match.group(1)].append({"path": _rel(path), "line": index})
    return dict(sorted(commands.items()))


def build_registry(include_untracked: bool = False) -> Dict[str, Any]:
    python_commands, unresolved = extract_python_commands(include_untracked=include_untracked)
    cpp_commands = extract_cpp_commands(include_untracked=include_untracked)
    all_commands = sorted(set(python_commands) | set(cpp_commands))

    entries = []
    for command in all_commands:
        py_sources = python_commands.get(command, [])
        cpp_sources = cpp_commands.get(command, [])
        entries.append(
            {
                "command": command,
                "category": _category_for(command),
                "python_references": len(py_sources),
                "cpp_routes": len(cpp_sources),
                "status": "routed" if cpp_sources else "python_only",
                "python_sources": py_sources,
                "cpp_sources": cpp_sources,
            }
        )

    python_missing_cpp = sorted(command for command in python_commands if command not in cpp_commands)
    cpp_unreferenced_by_python = sorted(command for command in cpp_commands if command not in python_commands)

    return {
        "schema": "unreal_mcp_bridge_command_registry.v1",
        "generated_at": _utc_now(),
        "source_scope": "tracked_plus_untracked" if include_untracked else "git_tracked_worktree",
        "counts": {
            "commands_total": len(all_commands),
            "python_referenced": len(python_commands),
            "cpp_routed": len(cpp_commands),
            "python_missing_cpp": len(python_missing_cpp),
            "cpp_unreferenced_by_python": len(cpp_unreferenced_by_python),
            "python_unresolved_calls": len(unresolved),
        },
        "commands": entries,
        "python_missing_cpp": python_missing_cpp,
        "cpp_unreferenced_by_python": cpp_unreferenced_by_python,
        "python_unresolved_calls": unresolved,
    }


def registry_signature(registry: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "schema": registry["schema"],
        "commands": [
            {
                "command": entry["command"],
                "category": entry["category"],
                "python_references": entry["python_references"],
                "cpp_routes": entry["cpp_routes"],
                "status": entry["status"],
            }
            for entry in registry["commands"]
        ],
        "python_missing_cpp": registry["python_missing_cpp"],
        "cpp_unreferenced_by_python": registry["cpp_unreferenced_by_python"],
        "python_unresolved_calls": registry["python_unresolved_calls"],
    }


def compare_registry(current: Dict[str, Any], recorded: Dict[str, Any]) -> Dict[str, Any]:
    current_commands = {entry["command"] for entry in current["commands"]}
    recorded_commands = {entry["command"] for entry in recorded.get("commands", [])}
    return {
        "new_commands": sorted(current_commands - recorded_commands),
        "removed_commands": sorted(recorded_commands - current_commands),
        "signature_changed": registry_signature(current) != registry_signature(recorded),
    }


def format_markdown(registry: Dict[str, Any], comparison: Optional[Dict[str, Any]] = None) -> str:
    counts = registry["counts"]
    lines = [
        "# Bridge Command Registry",
        "",
        f"- Generated: {registry['generated_at']}",
        f"- Commands total: {counts['commands_total']}",
        f"- Python referenced: {counts['python_referenced']}",
        f"- C++ routed: {counts['cpp_routed']}",
        f"- Python missing C++ routes: {counts['python_missing_cpp']}",
        f"- C++ routes not referenced by Python: {counts['cpp_unreferenced_by_python']}",
        f"- Unresolved Python command calls: {counts['python_unresolved_calls']}",
        "",
        "## Drift Summary",
        "",
    ]

    if registry["python_missing_cpp"]:
        lines.append("Python commands without a discovered C++ route:")
        lines.extend(f"- `{command}`" for command in registry["python_missing_cpp"])
    else:
        lines.append("All discovered Python bridge commands have a C++ route.")

    if registry["python_unresolved_calls"]:
        lines.extend(["", "Unresolved Python command call sites:"])
        for item in registry["python_unresolved_calls"][:25]:
            lines.append(f"- `{item['path']}:{item['line']}` uses `{item['arg']}`")
        if len(registry["python_unresolved_calls"]) > 25:
            lines.append(f"- ... {len(registry['python_unresolved_calls']) - 25} more")

    if comparison is not None:
        lines.extend(["", "## Registry Comparison", ""])
        lines.append(f"- Signature changed: {'yes' if comparison['signature_changed'] else 'no'}")
        lines.append(f"- New commands: {len(comparison['new_commands'])}")
        lines.append(f"- Removed commands: {len(comparison['removed_commands'])}")

    lines.extend(
        [
            "",
            "## Commands By Category",
            "",
            "| Category | Commands | Python refs | C++ routes |",
            "|---|---:|---:|---:|",
        ]
    )
    categories: Dict[str, Dict[str, int]] = defaultdict(lambda: {"commands": 0, "python": 0, "cpp": 0})
    for entry in registry["commands"]:
        row = categories[entry["category"]]
        row["commands"] += 1
        row["python"] += entry["python_references"]
        row["cpp"] += entry["cpp_routes"]
    for category, row in sorted(categories.items()):
        lines.append(f"| {category} | {row['commands']} | {row['python']} | {row['cpp']} |")

    return "\n".join(lines) + "\n"


def write_registry(registry: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_registry(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Python/C++ bridge command metadata.")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY, help="Registry snapshot path.")
    parser.add_argument("--write-registry", action="store_true", help="Write the current registry snapshot.")
    parser.add_argument("--check", action="store_true", help="Fail if the current registry differs from the snapshot.")
    parser.add_argument("--include-untracked", action="store_true", help="Include untracked source files in the scan.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    args = parser.parse_args(argv)

    current = build_registry(include_untracked=args.include_untracked)
    comparison = None
    if args.registry.exists():
        comparison = compare_registry(current, load_registry(args.registry))

    if args.write_registry:
        write_registry(current, args.registry)

    if args.json:
        print(json.dumps(current, indent=2, sort_keys=True))
    else:
        print(format_markdown(current, comparison=comparison))

    if args.check:
        if not args.registry.exists():
            return 1
        if comparison and comparison["signature_changed"]:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
