"""Toolset-like descriptors for the Unreal-MCP-Ghost TCP bridge.

This is a clean-room adapter layer over Ghost's own bridge command registry.
It does not replace the TCP bridge; it gives the existing command surface a
stable, ToolsetRegistry-style metadata shape that a future Unreal-native module
can consume.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


BRIDGE_REGISTRY_SCHEMA = "unreal_mcp_bridge_command_registry.v1"
BRIDGE_TOOLSET_DESCRIPTOR_SCHEMA = "unreal_mcp_ghost.bridge_toolset_descriptor.v1"
BRIDGE_COMMAND_SEARCH_SCHEMA = "unreal_mcp_ghost.bridge_command_search.v1"
BRIDGE_SUMMARY_SCHEMA = "unreal_mcp_ghost.bridge_descriptor_summary.v1"
BRIDGE_COMMAND_CALL_SCHEMA = "unreal_mcp_ghost.bridge_command_call.v1"

READ_ONLY_PREFIXES = (
    "get_",
    "list_",
    "find_",
    "inspect_",
    "check_",
    "scan_",
    "describe_",
    "ping",
    "bt_get_",
)

WRITE_PREFIXES = (
    "add_",
    "bind_",
    "call_",
    "compile_",
    "connect_",
    "create_",
    "delete_",
    "disconnect_",
    "exec_",
    "generate_",
    "grant_",
    "import_",
    "move_",
    "reconstruct_",
    "rename_",
    "save_",
    "set_",
    "spawn_",
    "umg_add_",
    "widget_add_",
    "widget_set_",
)


@dataclass(frozen=True)
class BridgeCommandDescriptor:
    command: str
    category: str
    status: str
    cpp_routes: int
    python_references: int
    cpp_sources: list[dict[str, Any]]
    python_sources: list[dict[str, Any]]
    review: dict[str, Any]

    @property
    def toolset_name(self) -> str:
        return f"bridge.{self.category}"

    @property
    def qualified_name(self) -> str:
        return f"{self.toolset_name}.{self.command}"

    @property
    def mutation_class(self) -> str:
        return mutation_class_for_command(self.command)


class BridgeDescriptorRegistry:
    """Loads and describes Ghost bridge commands as Toolset-like metadata."""

    def __init__(self, registry_path: Optional[Path] = None) -> None:
        self.registry_path = registry_path or default_registry_path()
        self._registry = self._load_registry(self.registry_path)
        self._review_by_command = {
            entry.get("command", ""): entry
            for entry in self._registry.get("cpp_unreferenced_review", [])
            if isinstance(entry, dict)
        }
        self._commands = [self._command_from_entry(entry) for entry in self._registry.get("commands", [])]
        self._by_category: dict[str, list[BridgeCommandDescriptor]] = defaultdict(list)
        self._by_command: dict[str, BridgeCommandDescriptor] = {}
        for command in self._commands:
            self._by_category[command.category].append(command)
            self._by_command[command.command] = command
        for commands in self._by_category.values():
            commands.sort(key=lambda item: item.command)

    @property
    def command_count(self) -> int:
        return len(self._commands)

    @property
    def categories(self) -> list[str]:
        return sorted(self._by_category)

    def summary(self) -> dict[str, Any]:
        category_counts = Counter(command.category for command in self._commands)
        mutation_counts = Counter(command.mutation_class for command in self._commands)
        return {
            "schema": BRIDGE_SUMMARY_SCHEMA,
            "success": True,
            "source_schema": self._registry.get("schema", ""),
            "source_scope": self._registry.get("source_scope", ""),
            "registry_path": str(self.registry_path),
            "counts": self._registry.get("counts", {}),
            "category_counts": dict(sorted(category_counts.items())),
            "mutation_class_counts": dict(sorted(mutation_counts.items())),
            "categories": self.categories,
        }

    def list_toolsets(
        self,
        *,
        category: str = "",
        status: str = "",
        response_format: str = "text",
    ) -> str:
        descriptors = self._matching_toolsets(category=category, status=status)
        if response_format == "json":
            payload = {
                "schema": "unreal_mcp_ghost.bridge_toolset_list.v1",
                "success": True,
                "count": len(descriptors),
                "toolsets": descriptors,
            }
            return json.dumps(payload, indent=2, sort_keys=True)

        if not descriptors:
            return "No bridge toolsets matched the requested filters."

        rows = [
            (
                f"- {item['name']}: {item['command_count']} commands; "
                f"category={item['category']}; routed={item['routed_count']}; "
                f"python_referenced={item['python_referenced_count']}"
            )
            for item in descriptors
        ]
        return "Unreal MCP bridge toolsets:\n" + "\n".join(rows)

    def describe_toolset(self, toolset_name: str, command_filter: str = "") -> str:
        category = _category_from_toolset_name(toolset_name)
        commands = self._by_category.get(category)
        if not commands:
            return json.dumps(
                {
                    "schema": BRIDGE_TOOLSET_DESCRIPTOR_SCHEMA,
                    "success": False,
                    "error": f"Unknown bridge toolset '{toolset_name}'.",
                    "available_toolsets": [f"bridge.{name}" for name in self.categories],
                },
                indent=2,
                sort_keys=True,
            )

        needle = command_filter.strip().lower()
        command_descriptors = [
            self._command_descriptor(command, include_sources=True)
            for command in commands
            if not needle or needle in self._command_search_text(command)
        ]
        payload = {
            "schema": BRIDGE_TOOLSET_DESCRIPTOR_SCHEMA,
            "success": True,
            **self._toolset_descriptor(category),
            "command_filter": command_filter,
            "commands": command_descriptors,
        }
        payload["filtered_command_count"] = len(command_descriptors)
        return json.dumps(payload, indent=2, sort_keys=True)

    def get_command(self, command_name: str) -> Optional[BridgeCommandDescriptor]:
        """Resolve a bridge command by plain or qualified descriptor name."""

        normalized = _command_from_qualified_name(command_name)
        return self._by_command.get(normalized)

    def command_call_plan(
        self,
        *,
        command_name: str,
        params: Optional[dict[str, Any]] = None,
        dry_run: bool = True,
        allow_mutation: bool = False,
        allow_unknown: bool = False,
    ) -> dict[str, Any]:
        """Build the guarded call envelope for a bridge command."""

        safe_params = dict(params or {})
        descriptor = self.get_command(command_name)
        command = _command_from_qualified_name(command_name)
        if descriptor is None and not allow_unknown:
            return {
                "schema": BRIDGE_COMMAND_CALL_SCHEMA,
                "success": False,
                "dry_run": dry_run,
                "will_execute": False,
                "error": f"Unknown bridge command '{command_name}'.",
                "available_command_count": self.command_count,
            }

        if descriptor is None:
            mutation_class = mutation_class_for_command(command)
            command_descriptor = {
                "schema": "unreal_mcp_ghost.bridge_command_descriptor.v1",
                "command": command,
                "name": command,
                "qualified_name": f"bridge.unknown.{command}",
                "toolset_name": "bridge.unknown",
                "category": "unknown",
                "status": "unknown",
                "mutation_class": mutation_class,
                "cpp_routes": 0,
                "python_references": 0,
                "review": {},
            }
        else:
            mutation_class = descriptor.mutation_class
            command_descriptor = self._command_descriptor(descriptor, include_sources=True)

        if mutation_class != "read_only" and not allow_mutation:
            return {
                "schema": BRIDGE_COMMAND_CALL_SCHEMA,
                "success": False,
                "dry_run": dry_run,
                "will_execute": False,
                "error": (
                    f"Bridge command '{command}' is classified as {mutation_class}; "
                    "pass allow_mutation=true to execute it."
                ),
                "command": command,
                "params": safe_params,
                "descriptor": command_descriptor,
            }

        return {
            "schema": BRIDGE_COMMAND_CALL_SCHEMA,
            "success": True,
            "dry_run": dry_run,
            "will_execute": not dry_run,
            "command": command,
            "params": safe_params,
            "descriptor": command_descriptor,
            "safety": {
                "mutation_class": mutation_class,
                "allow_mutation": allow_mutation,
                "allow_unknown": allow_unknown,
                "execution_path": "Ghost TCP JSON bridge via configured command sender",
            },
        }

    def search_commands(
        self,
        *,
        query: str = "",
        category: str = "",
        status: str = "",
        mutation_class: str = "",
        include_sources: bool = False,
        limit: int = 50,
    ) -> dict[str, Any]:
        normalized_query = query.strip().lower()
        normalized_category = category.strip().lower()
        normalized_status = status.strip().lower()
        normalized_mutation = mutation_class.strip().lower()
        safe_limit = max(1, min(limit, 250))
        matches: list[dict[str, Any]] = []

        for command in sorted(self._commands, key=lambda item: item.command):
            if normalized_category and normalized_category != command.category.lower():
                continue
            if normalized_status and normalized_status != command.status.lower():
                continue
            if normalized_mutation and normalized_mutation != command.mutation_class.lower():
                continue
            if normalized_query and normalized_query not in self._command_search_text(command):
                continue

            matches.append(self._command_descriptor(command, include_sources=include_sources))
            if len(matches) >= safe_limit:
                break

        return {
            "schema": BRIDGE_COMMAND_SEARCH_SCHEMA,
            "success": True,
            "query": query,
            "category": category,
            "status": status,
            "mutation_class": mutation_class,
            "include_sources": include_sources,
            "limit": safe_limit,
            "count": len(matches),
            "commands": matches,
        }

    def _matching_toolsets(self, *, category: str, status: str) -> list[dict[str, Any]]:
        normalized_category = category.strip().lower()
        normalized_status = status.strip().lower()
        descriptors = []
        for category_name in self.categories:
            if normalized_category and normalized_category != category_name.lower():
                continue
            descriptor = self._toolset_descriptor(category_name)
            if normalized_status and normalized_status != descriptor["status"].lower():
                continue
            descriptors.append(descriptor)
        return descriptors

    def _toolset_descriptor(self, category: str) -> dict[str, Any]:
        commands = self._by_category.get(category, [])
        routed_count = sum(1 for command in commands if command.cpp_routes > 0)
        python_count = sum(1 for command in commands if command.python_references > 0)
        mutation_counts = Counter(command.mutation_class for command in commands)
        status_counts = Counter(command.status for command in commands)
        status = "complete" if routed_count == len(commands) and python_count == len(commands) else "needs_review"
        return {
            "id": f"bridge.{category}",
            "name": f"bridge.{category}",
            "category": category,
            "status": status,
            "description": f"TCP bridge commands in the {category} category.",
            "command_count": len(commands),
            "routed_count": routed_count,
            "python_referenced_count": python_count,
            "mutation_class_counts": dict(sorted(mutation_counts.items())),
            "command_status_counts": dict(sorted(status_counts.items())),
        }

    def _command_from_entry(self, entry: dict[str, Any]) -> BridgeCommandDescriptor:
        command = str(entry.get("command", ""))
        return BridgeCommandDescriptor(
            command=command,
            category=str(entry.get("category", "uncategorized")),
            status=str(entry.get("status", "unknown")),
            cpp_routes=int(entry.get("cpp_routes", 0) or 0),
            python_references=int(entry.get("python_references", 0) or 0),
            cpp_sources=list(entry.get("cpp_sources", []) or []),
            python_sources=list(entry.get("python_sources", []) or []),
            review=dict(self._review_by_command.get(command, {})),
        )

    def _command_descriptor(
        self,
        command: BridgeCommandDescriptor,
        *,
        include_sources: bool,
    ) -> dict[str, Any]:
        descriptor: dict[str, Any] = {
            "schema": "unreal_mcp_ghost.bridge_command_descriptor.v1",
            "command": command.command,
            "name": command.command,
            "qualified_name": command.qualified_name,
            "toolset_name": command.toolset_name,
            "category": command.category,
            "status": command.status,
            "mutation_class": command.mutation_class,
            "cpp_routes": command.cpp_routes,
            "python_references": command.python_references,
            "review": command.review,
        }
        if include_sources:
            descriptor["cpp_sources"] = command.cpp_sources
            descriptor["python_sources"] = command.python_sources
        return descriptor

    def _command_search_text(self, command: BridgeCommandDescriptor) -> str:
        review_text = " ".join(str(value) for value in command.review.values())
        return " ".join(
            [
                command.command,
                command.qualified_name,
                command.category,
                command.status,
                command.mutation_class,
                review_text,
            ]
        ).lower()

    @staticmethod
    def _load_registry(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {
                "schema": BRIDGE_REGISTRY_SCHEMA,
                "source_scope": "missing",
                "counts": {},
                "commands": [],
                "cpp_unreferenced_review": [],
            }
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"Bridge command registry root must be an object: {path}")
        return data


def default_registry_path() -> Path:
    return Path(__file__).resolve().parent.parent / "knowledge_base" / "Reports" / "bridge_command_registry.json"


def _category_from_toolset_name(toolset_name: str) -> str:
    normalized = toolset_name.strip()
    if normalized.startswith("bridge."):
        return normalized[len("bridge.") :]
    return normalized


def _command_from_qualified_name(command_name: str) -> str:
    normalized = command_name.strip()
    if normalized.startswith("bridge."):
        parts = normalized.split(".")
        if len(parts) >= 3:
            return parts[-1]
    return normalized


def mutation_class_for_command(command_name: str) -> str:
    if command_name.startswith(READ_ONLY_PREFIXES):
        return "read_only"
    if command_name.startswith(WRITE_PREFIXES):
        return "editor_mutation"
    return "unknown"
