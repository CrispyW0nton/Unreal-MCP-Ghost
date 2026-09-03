"""Registration-time toolset catalog for Unreal-MCP-Ghost.

This module is a clean-room reimplementation of the tool-search pattern used
by Epic's Unreal MCP integration. It adapts Ghost's existing FastMCP decorator
style into discoverable toolsets without copying Unreal Engine source.
"""

from __future__ import annotations

import functools
import inspect
import json
import os
import types
from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, Literal, Optional, Union, get_args, get_origin, get_type_hints

import anyio


META_TOOL_NAMES = frozenset({"list_toolsets", "describe_toolset", "call_tool", "tool_contribution_contract"})
TRUTHY_ENV_VALUES = frozenset({"1", "true", "yes", "on"})
TOOLSET_DESCRIPTOR_SCHEMA = "unreal_mcp_ghost.toolset_descriptor.v1"
TOOL_SEARCH_RESULT_SCHEMA = "unreal_mcp_ghost.tool_search_result.v1"
TOOL_CONTRIBUTION_CONTRACT_SCHEMA = "unreal_mcp_ghost.tool_contribution_contract.v1"


def is_tool_search_mode_enabled() -> bool:
    """Return true when only tool-search meta-tools should be exposed."""

    return os.environ.get("UNREAL_MCP_TOOL_SEARCH_MODE", "").strip().lower() in TRUTHY_ENV_VALUES


@dataclass(frozen=True)
class ToolEntry:
    """Catalog entry for a single MCP tool function."""

    name: str
    fn: Callable[..., Any]
    module: str
    toolset_name: str
    description: str
    input_schema: dict[str, Any]

    @property
    def qualified_name(self) -> str:
        return f"{self.toolset_name}.{self.name}"


@dataclass
class ToolsetEntry:
    """Catalog entry for a source module worth of tools."""

    name: str
    module: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    tools: dict[str, ToolEntry] = field(default_factory=dict)


class ToolsetRegistry:
    """Collects tool declarations and exposes Epic-style tool-search helpers."""

    def __init__(self, inventory_path: Optional[Path] = None) -> None:
        self._inventory_path = inventory_path or Path(__file__).with_name("tool_inventory_categories.json")
        self._inventory = self._load_inventory(self._inventory_path)
        self._toolsets: dict[str, ToolsetEntry] = {}
        self._tools_by_name: dict[str, list[ToolEntry]] = defaultdict(list)
        self._runtime_state: Any = None

    @property
    def toolsets(self) -> Mapping[str, ToolsetEntry]:
        return self._toolsets

    def bind(self, mcp: Any, *, expose_direct_tools: bool = True) -> "ToolsetCollectingMCP":
        return ToolsetCollectingMCP(mcp, self, expose_direct_tools=expose_direct_tools)

    def attach_runtime_state(self, runtime_state: Any) -> None:
        """Attach optional runtime operation tracking for indirect dispatch."""

        self._runtime_state = runtime_state

    def register_tool(
        self,
        fn: Callable[..., Any],
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> ToolEntry:
        tool_name = name or getattr(fn, "__name__", "")
        module = getattr(fn, "__module__", "") or "unreal_mcp_server"
        toolset_name = module
        tool_description = _normalize_doc(description or inspect.getdoc(fn) or "")

        toolset = self._toolsets.get(toolset_name)
        if toolset is None:
            metadata = dict(self._inventory.get(toolset_name, {}))
            toolset = ToolsetEntry(
                name=toolset_name,
                module=module,
                description=_toolset_description(toolset_name, metadata),
                metadata=metadata,
            )
            self._toolsets[toolset_name] = toolset

        entry = ToolEntry(
            name=tool_name,
            fn=fn,
            module=module,
            toolset_name=toolset_name,
            description=tool_description,
            input_schema=_function_input_schema(fn),
        )
        toolset.tools[tool_name] = entry
        self._tools_by_name[tool_name].append(entry)
        return entry

    def refresh_inventory(self) -> dict[str, Any]:
        """Reload category/status metadata for already registered toolsets.

        Tool functions themselves are registered by FastMCP at process startup.
        This mirrors the useful part of native RefreshTools that is safe for
        Ghost's Python process: updating descriptors from the inventory file
        without re-importing modules or mutating the live tool table.
        """

        previous_keys = set(self._inventory)
        self._inventory = self._load_inventory(self._inventory_path)
        current_keys = set(self._inventory)

        for toolset_name, toolset in self._toolsets.items():
            metadata = dict(self._inventory.get(toolset_name, {}))
            toolset.metadata = metadata
            toolset.description = _toolset_description(toolset_name, metadata)

        return {
            "success": True,
            "inventory_path": str(self._inventory_path),
            "inventory_entry_count": len(self._inventory),
            "toolset_count": len(self._toolsets),
            "tool_count": sum(len(toolset.tools) for toolset in self._toolsets.values()),
            "added_inventory_keys": sorted(current_keys - previous_keys),
            "removed_inventory_keys": sorted(previous_keys - current_keys),
        }

    def list_toolsets(self, filter_text: Optional[str] = None) -> str:
        """Return a compact text catalog of toolsets."""

        matches = self.find_toolsets(filter_text=filter_text)
        rows: list[str] = []
        for toolset in matches:
            category = toolset.metadata.get("category", "uncategorized")
            status = toolset.metadata.get("status", "unknown")
            rows.append(
                f"- {toolset.name}: {len(toolset.tools)} tools; category={category}; "
                f"status={status}; {toolset.description}"
            )

        if not rows:
            return "No Unreal MCP toolsets matched the requested filter."

        return "Unreal MCP toolsets:\n" + "\n".join(rows)

    def find_toolsets(
        self,
        *,
        filter_text: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[ToolsetEntry]:
        """Return toolsets matching text/category/status filters."""

        normalized_filter = (filter_text or "").strip().lower()
        normalized_category = (category or "").strip().lower()
        normalized_status = (status or "").strip().lower()
        matches: list[ToolsetEntry] = []

        for toolset in sorted(self._toolsets.values(), key=lambda item: item.name):
            category_value = str(toolset.metadata.get("category", "")).lower()
            status_value = str(toolset.metadata.get("status", "")).lower()
            if normalized_category and normalized_category != category_value:
                continue
            if normalized_status and normalized_status != status_value:
                continue

            searchable = self._toolset_search_text(toolset)
            if normalized_filter and normalized_filter not in searchable:
                continue

            matches.append(toolset)

        return matches

    def search_tools(
        self,
        *,
        query: str,
        toolset_name: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Search registered tools and return stable descriptors."""

        normalized_query = query.strip().lower()
        safe_limit = max(1, min(limit, 250))
        candidates = self.find_toolsets(category=category, status=status)
        if toolset_name:
            resolved = self._resolve_toolset(toolset_name)
            candidates = [resolved] if resolved is not None and resolved in candidates else []

        results: list[dict[str, Any]] = []
        for toolset in candidates:
            for tool in sorted(toolset.tools.values(), key=lambda item: item.name):
                searchable = " ".join(
                    [
                        tool.name,
                        tool.qualified_name,
                        tool.description,
                        toolset.name,
                        toolset.description,
                        str(toolset.metadata.get("category", "")),
                    ]
                ).lower()
                if normalized_query and normalized_query not in searchable:
                    continue
                results.append(self._tool_descriptor(tool, include_schema=False))
                if len(results) >= safe_limit:
                    break
            if len(results) >= safe_limit:
                break

        return {
            "schema": TOOL_SEARCH_RESULT_SCHEMA,
            "success": True,
            "query": query,
            "toolset_name": toolset_name or "",
            "category": category or "",
            "status": status or "",
            "limit": safe_limit,
            "count": len(results),
            "tools": results,
        }

    def contribution_contract(self) -> dict[str, Any]:
        """Describe Ghost's clean-room tool contribution contract."""

        toolset_count = len(self._toolsets)
        tool_count = sum(len(toolset.tools) for toolset in self._toolsets.values())
        categories = sorted(
            {
                str(toolset.metadata.get("category", "uncategorized"))
                for toolset in self._toolsets.values()
            }
        )
        return {
            "schema": TOOL_CONTRIBUTION_CONTRACT_SCHEMA,
            "success": True,
            "contract_scope": {
                "ghost_owned": [
                    "Python FastMCP decorator capture via ToolsetCollectingMCP",
                    "ToolsetRegistry.register_tool descriptors and indirect dispatch",
                    "tool-search meta-tools and direct-tool compatibility mode",
                    "tool_inventory_categories.json category/status/roadmap metadata",
                    "bridge descriptor adapters over Ghost's existing TCP command registry",
                    "knowledge_base, project intelligence, higher-level skills, and city/worldbuilding workflow surfaces",
                ],
                "delegated_to_fastmcp": [
                    "MCP transport serving",
                    "JSON-RPC request envelopes",
                    "client protocol compatibility for stdio, SSE, and streamable HTTP",
                ],
                "unreal_bridge_owned": [
                    "Editor mutation execution over Ghost's TCP bridge",
                    "Unreal Python snippets executed through exec_substrate",
                    "C++ command handler coverage and transaction behavior",
                ],
            },
            "accepted_contribution_styles": [
                {
                    "style": "decorated_python_tool_module",
                    "entrypoint": "register_<domain>_tools(mcp)",
                    "registration_path": "ToolsetCollectingMCP.tool() captures @mcp.tool declarations before delegating to FastMCP when direct tools are enabled.",
                    "example_shape": "def register_demo_tools(mcp): @mcp.tool() def demo_tool(ctx, name: str = '') -> str: ...",
                },
                {
                    "style": "direct_registry_registration",
                    "entrypoint": "ToolsetRegistry.register_tool(fn, name=..., description=...)",
                    "registration_path": "Use for tests, generated adapters, or future non-decorator registration surfaces.",
                },
                {
                    "style": "bridge_descriptor_adapter",
                    "entrypoint": "bridge_descriptor_tools",
                    "registration_path": "Expose Toolset-like metadata over Ghost-owned TCP bridge commands while execution remains routed through the existing bridge.",
                },
                {
                    "style": "higher_level_skill",
                    "entrypoint": "skills.<skill>.skill",
                    "registration_path": "Expose project/workflow skills through the same registry so tool-search clients can discover them.",
                },
            ],
            "registration_invariants": [
                "Each contributed function must have a stable tool name within its module/toolset.",
                "Duplicate unqualified names are allowed across toolsets, but callers must pass toolset_name when ambiguous.",
                "Qualified names use the module toolset plus function name, for example tools.spatial_awareness_tools.spatial_scene_overview.",
                "Function signatures should use JSON-serializable parameter defaults; non-serializable defaults are omitted from generated schemas.",
                "Hidden context parameters are named ctx or context and are not exposed in the input schema.",
                "Tool results should return structured JSON-compatible dicts or JSON strings with success/error envelopes.",
                "Mutation-capable tools must expose dry_run and/or allow_mutation gates when feasible.",
                "Long-running indirect calls should participate in runtime operation tracking when dispatched through ToolsetRegistry.call_tool.",
                "Inventory metadata should declare category, roadmap_phase, status, and a coverage_note for partial or native-alignment surfaces.",
            ],
            "discovery_and_dispatch": {
                "direct_mode": "Direct tools plus meta-tools are exposed for broad client compatibility.",
                "tool_search_mode": "UNREAL_MCP_TOOL_SEARCH_MODE=1 exposes only meta-tools while retaining the full registered catalog for indirect dispatch.",
                "meta_tools": sorted(META_TOOL_NAMES),
                "descriptor_schema": TOOLSET_DESCRIPTOR_SCHEMA,
                "search_result_schema": TOOL_SEARCH_RESULT_SCHEMA,
                "contribution_contract_schema": TOOL_CONTRIBUTION_CONTRACT_SCHEMA,
                "call_tool_guard": "Meta-tools are refused through call_tool to avoid recursive self-dispatch.",
            },
            "current_registry": {
                "inventory_path": str(self._inventory_path),
                "inventory_entry_count": len(self._inventory),
                "toolset_count": toolset_count,
                "tool_count": tool_count,
                "categories": categories,
            },
            "contribution_checklist": [
                "Read the required Unreal-MCP knowledge-base guides before editing bridge, plugin, or server tooling.",
                "Add or update focused tests for schema generation, registry visibility, direct mode, and tool-search dispatch.",
                "Update tool_inventory_categories.json when adding a new module or changing category/status semantics.",
                "Document clean-room behavior, native parity gaps, and legal-review boundaries in the UE 5.8 audit when the change is native-alignment work.",
                "Run py_compile and focused pytest lanes before claiming the surface is ready.",
                "Smoke direct mode and UNREAL_MCP_TOOL_SEARCH_MODE=1 when changing registry/meta-tool behavior.",
            ],
            "unsupported_native_gaps": [
                "This is not Epic's module-level C++ AddTool API.",
                "This is not a UFUNCTION or UToolsetDefinition reflection-backed importer.",
                "This does not embed Epic ModelContextProtocol or ToolsetRegistry source.",
                "This does not make Ghost's TCP bridge a full in-editor ToolsetRegistry dispatcher.",
                "An Unreal-native C++ adapter remains future work and needs legal review if based closely on Epic source.",
            ],
            "legal_review_required": [
                "Any direct copying of Epic ModelContextProtocol, ToolsetRegistry, GASToolsets, or MCPClientToolset source.",
                "Any schema or helper behavior generated by reproducing proprietary Epic implementation details instead of Ghost-owned signatures.",
                "Any future Unreal-native module that closely follows Epic NoRedist internals.",
            ],
            "preserved_ghost_differentiators": [
                "knowledge_base tools and project context",
                "broader local client compatibility through stdio, SSE, and streamable HTTP",
                "Blueprint, graph repair, diagnostics, and project intelligence coverage",
                "higher-level skills and worldbuilding automation",
                "generative asset workflows including guarded Tripo handoffs",
                "dry-run-first spatial/interior composition tools",
            ],
        }

    def describe_toolset(self, toolset_name: str) -> str:
        """Return the JSON schema catalog for one toolset."""

        toolset = self._resolve_toolset(toolset_name)
        if toolset is None:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Unknown toolset '{toolset_name}'.",
                    "available_toolsets": sorted(self._toolsets),
                },
                indent=2,
                sort_keys=True,
            )

        payload = {
            "schema": TOOLSET_DESCRIPTOR_SCHEMA,
            "success": True,
            **self._toolset_descriptor(toolset, include_tools=True, include_schema=True),
        }
        return json.dumps(payload, indent=2, sort_keys=True)

    async def call_tool(
        self,
        tool_name: str,
        arguments: Optional[dict[str, Any]] = None,
        toolset_name: Optional[str] = None,
    ) -> Any:
        """Dispatch to a registered tool by name or toolset-qualified name."""

        if tool_name in META_TOOL_NAMES:
            return {
                "success": False,
                "error": f"Refusing to dispatch meta-tool '{tool_name}' through call_tool.",
            }

        tool = self._resolve_tool(tool_name=tool_name, toolset_name=toolset_name)
        if isinstance(tool, dict):
            return tool

        call_arguments, argument_error = _normalize_arguments(arguments)
        if argument_error is not None:
            return {
                **argument_error,
                "tool": tool.name,
                "toolset": tool.toolset_name,
                "inputSchema": tool.input_schema,
            }

        _inject_missing_context_argument(tool.fn, call_arguments)

        operation_id = self._begin_operation(tool, call_arguments)
        try:
            self._record_operation_progress(
                operation_id,
                stage="dispatching",
                message="Dispatching registered tool.",
                percent=0.25,
            )
            if self._is_operation_cancel_requested(operation_id):
                self._finish_operation(
                    operation_id,
                    status="cancelled_before_dispatch",
                    error="Operation was cancelled before tool dispatch.",
                )
                return {
                    "success": False,
                    "cancelled": True,
                    "operation_id": operation_id,
                    "tool": tool.name,
                    "toolset": tool.toolset_name,
                    "error": "Operation was cancelled before tool dispatch.",
                }

            if inspect.iscoroutinefunction(tool.fn):
                result = await tool.fn(**call_arguments)
            else:
                result = await anyio.to_thread.run_sync(
                    functools.partial(tool.fn, **call_arguments),
                    limiter=None,
                    abandon_on_cancel=False,
                )
            if inspect.isawaitable(result):
                result = await result
            self._finish_operation(operation_id, status="completed", result=result)
            return result
        except TypeError as exc:
            self._finish_operation(operation_id, status="failed", error=str(exc))
            return {
                "success": False,
                "error": str(exc),
                "tool": tool.name,
                "toolset": tool.toolset_name,
                "inputSchema": tool.input_schema,
            }
        except Exception as exc:  # pragma: no cover - defensive envelope
            self._finish_operation(operation_id, status="failed", error=str(exc))
            return {
                "success": False,
                "error": str(exc),
                "tool": tool.name,
                "toolset": tool.toolset_name,
            }

    def register_meta_tools(self, mcp: Any) -> None:
        """Register tool-search and contribution-contract meta-tools."""

        registry = self

        @mcp.tool()
        def tool_contribution_contract(response_format: str = "json") -> str:
            """Describe how Ghost tools can be contributed, discovered, and reviewed."""

            payload = registry.contribution_contract()
            if str(response_format or "json").strip().lower() == "text":
                return "\n".join(
                    [
                        "Unreal-MCP-Ghost tool contribution contract:",
                        f"- schema: {payload['schema']}",
                        f"- toolsets: {payload['current_registry']['toolset_count']}",
                        f"- tools: {payload['current_registry']['tool_count']}",
                        "- accepted styles: "
                        + ", ".join(item["style"] for item in payload["accepted_contribution_styles"]),
                        "- unsupported native gaps: "
                        + "; ".join(payload["unsupported_native_gaps"]),
                    ]
                )
            return json.dumps(payload, indent=2, sort_keys=True)

        @mcp.tool()
        def list_toolsets(
            filter_text: str = "",
            category: str = "",
            status: str = "",
            response_format: str = "text",
        ) -> str:
            """List Unreal MCP toolsets with optional text/category/status filters."""

            if response_format == "json":
                payload = {
                    "schema": "unreal_mcp_ghost.toolset_list.v1",
                    "success": True,
                    "filter_text": filter_text,
                    "category": category,
                    "status": status,
                    "toolsets": [
                        registry._toolset_descriptor(toolset, include_tools=False, include_schema=False)
                        for toolset in registry.find_toolsets(
                            filter_text=filter_text,
                            category=category,
                            status=status,
                        )
                    ],
                }
                payload["count"] = len(payload["toolsets"])
                return json.dumps(payload, indent=2, sort_keys=True)

            if category or status:
                payload = registry.find_toolsets(
                    filter_text=filter_text,
                    category=category,
                    status=status,
                )
                if not payload:
                    return "No Unreal MCP toolsets matched the requested filters."
                rows = []
                for toolset in payload:
                    rows.append(
                        f"- {toolset.name}: {len(toolset.tools)} tools; "
                        f"category={toolset.metadata.get('category', 'uncategorized')}; "
                        f"status={toolset.metadata.get('status', 'unknown')}; {toolset.description}"
                    )
                return "Unreal MCP toolsets:\n" + "\n".join(rows)

            return registry.list_toolsets(filter_text=filter_text)

        @mcp.tool()
        def describe_toolset(toolset_name: str, tool_filter: str = "") -> str:
            """Describe one Unreal MCP toolset and return tool input schemas."""

            if not tool_filter:
                return registry.describe_toolset(toolset_name)

            payload = json.loads(registry.describe_toolset(toolset_name))
            if payload.get("success") and "tools" in payload:
                needle = tool_filter.strip().lower()
                payload["tool_filter"] = tool_filter
                payload["tools"] = [
                    tool for tool in payload["tools"]
                    if needle in " ".join(
                        [
                            str(tool.get("name", "")),
                            str(tool.get("qualified_name", "")),
                            str(tool.get("description", "")),
                        ]
                    ).lower()
                ]
                payload["tool_count"] = len(payload["tools"])
            return json.dumps(payload, indent=2, sort_keys=True)

        @mcp.tool()
        async def call_tool(
            tool_name: str,
            arguments: Optional[dict[str, Any]] = None,
            toolset_name: str = "",
        ) -> Any:
            """Call a tool discovered through list_toolsets or describe_toolset."""

            return await registry.call_tool(
                tool_name=tool_name,
                arguments=arguments,
                toolset_name=toolset_name or None,
            )

    def _resolve_toolset(self, toolset_name: str) -> Optional[ToolsetEntry]:
        if toolset_name in self._toolsets:
            return self._toolsets[toolset_name]
        lowered = toolset_name.lower()
        for candidate, toolset in self._toolsets.items():
            if candidate.lower() == lowered:
                return toolset
        return None

    def _resolve_tool(self, *, tool_name: str, toolset_name: Optional[str]) -> ToolEntry | dict[str, Any]:
        if toolset_name:
            toolset = self._resolve_toolset(toolset_name)
            if toolset is None:
                return {
                    "success": False,
                    "error": f"Unknown toolset '{toolset_name}'.",
                    "available_toolsets": sorted(self._toolsets),
                }
            if tool_name in toolset.tools:
                return toolset.tools[tool_name]
            return {
                "success": False,
                "error": f"Unknown tool '{tool_name}' in toolset '{toolset.name}'.",
                "available_tools": sorted(toolset.tools),
            }

        qualified = self._resolve_qualified_name(tool_name)
        if qualified is not None:
            return qualified

        matches = self._tools_by_name.get(tool_name, [])
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            return {
                "success": False,
                "error": f"Tool name '{tool_name}' is ambiguous. Pass toolset_name.",
                "candidates": [match.qualified_name for match in matches],
            }
        return {
            "success": False,
            "error": f"Unknown tool '{tool_name}'.",
            "available_toolsets": sorted(self._toolsets),
        }

    def _resolve_qualified_name(self, qualified_name: str) -> Optional[ToolEntry]:
        for toolset_name, toolset in self._toolsets.items():
            prefix = f"{toolset_name}."
            if qualified_name.startswith(prefix):
                inner_name = qualified_name[len(prefix) :]
                return toolset.tools.get(inner_name)
        return None

    def _toolset_descriptor(
        self,
        toolset: ToolsetEntry,
        *,
        include_tools: bool,
        include_schema: bool,
    ) -> dict[str, Any]:
        metadata = dict(toolset.metadata)
        descriptor: dict[str, Any] = {
            "name": toolset.name,
            "id": toolset.name,
            "module": toolset.module,
            "description": toolset.description,
            "category": metadata.get("category", "uncategorized"),
            "status": metadata.get("status", "unknown"),
            "roadmap_phase": metadata.get("roadmap_phase", "unknown"),
            "coverage_note": metadata.get("coverage_note", ""),
            "metadata": metadata,
            "tool_count": len(toolset.tools),
        }
        if include_tools:
            descriptor["tools"] = [
                self._tool_descriptor(tool, include_schema=include_schema)
                for tool in sorted(toolset.tools.values(), key=lambda item: item.name)
            ]
        return descriptor

    def _tool_descriptor(self, tool: ToolEntry, *, include_schema: bool) -> dict[str, Any]:
        descriptor: dict[str, Any] = {
            "name": tool.name,
            "qualified_name": tool.qualified_name,
            "toolset_name": tool.toolset_name,
            "module": tool.module,
            "description": tool.description,
        }
        if include_schema:
            descriptor["inputSchema"] = tool.input_schema
        return descriptor

    def _toolset_search_text(self, toolset: ToolsetEntry) -> str:
        return " ".join(
            [
                toolset.name,
                toolset.description,
                str(toolset.metadata.get("category", "")),
                str(toolset.metadata.get("status", "")),
                str(toolset.metadata.get("roadmap_phase", "")),
                str(toolset.metadata.get("coverage_note", "")),
                " ".join(sorted(toolset.tools)),
                " ".join(tool.description for tool in toolset.tools.values()),
            ]
        ).lower()

    def _begin_operation(self, tool: ToolEntry, arguments: dict[str, Any]) -> str:
        runtime_state = self._runtime_state
        if runtime_state is None:
            return ""
        begin = getattr(runtime_state, "begin_operation", None)
        if not callable(begin):
            return ""
        return begin(
            tool_name=tool.name,
            toolset_name=tool.toolset_name,
            qualified_name=tool.qualified_name,
            metadata={
                "argument_keys": sorted(str(key) for key in arguments.keys()),
                "dispatch": "ToolsetRegistry.call_tool",
            },
        )

    def _record_operation_progress(
        self,
        operation_id: str,
        *,
        stage: str,
        message: str,
        percent: float,
    ) -> None:
        if not operation_id or self._runtime_state is None:
            return
        record = getattr(self._runtime_state, "record_operation_progress", None)
        if callable(record):
            record(operation_id, stage=stage, message=message, percent=percent)

    def _is_operation_cancel_requested(self, operation_id: str) -> bool:
        if not operation_id or self._runtime_state is None:
            return False
        requested = getattr(self._runtime_state, "is_operation_cancel_requested", None)
        return bool(callable(requested) and requested(operation_id))

    def _finish_operation(
        self,
        operation_id: str,
        *,
        status: str,
        result: Any = None,
        error: str = "",
    ) -> None:
        if not operation_id or self._runtime_state is None:
            return
        finish = getattr(self._runtime_state, "finish_operation", None)
        if callable(finish):
            finish(operation_id, status=status, result=result, error=error)

    @staticmethod
    def _load_inventory(path: Path) -> dict[str, dict[str, Any]]:
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(key): value for key, value in data.items() if isinstance(value, dict)}


class ToolsetCollectingMCP:
    """FastMCP facade that records tool declarations before delegating them."""

    def __init__(self, mcp: Any, registry: ToolsetRegistry, *, expose_direct_tools: bool = True) -> None:
        self._mcp = mcp
        self._registry = registry
        self._expose_direct_tools = expose_direct_tools

    def tool(self, *args: Any, **kwargs: Any) -> Any:
        custom_name = kwargs.get("name")

        if len(args) == 1 and callable(args[0]) and not kwargs:
            return self._decorate_tool(args[0], name=custom_name, real_decorator=None)

        real_decorator = self._mcp.tool(*args, **kwargs) if self._expose_direct_tools else None

        def decorator(fn: Callable[..., Any]) -> Any:
            return self._decorate_tool(fn, name=custom_name, real_decorator=real_decorator)

        return decorator

    def _decorate_tool(
        self,
        fn: Callable[..., Any],
        *,
        name: Optional[str],
        real_decorator: Optional[Callable[[Callable[..., Any]], Any]],
    ) -> Any:
        self._registry.register_tool(fn, name=name)
        if real_decorator is not None:
            return real_decorator(fn)
        if self._expose_direct_tools:
            return self._mcp.tool()(fn)
        return fn

    def __getattr__(self, attr: str) -> Any:
        return getattr(self._mcp, attr)


def _toolset_description(toolset_name: str, metadata: Mapping[str, Any]) -> str:
    category = metadata.get("category")
    phase = metadata.get("roadmap_phase")
    coverage = metadata.get("coverage_note")
    pieces = [str(piece) for piece in (category, phase, coverage) if piece]
    if pieces:
        return "; ".join(pieces)
    return f"Tools registered from {toolset_name}."


def _normalize_doc(doc: str) -> str:
    return " ".join(line.strip() for line in doc.strip().splitlines() if line.strip())


def _function_input_schema(fn: Callable[..., Any]) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []

    try:
        signature = inspect.signature(fn)
    except (TypeError, ValueError):
        return {"type": "object", "properties": properties, "required": required}

    try:
        resolved_hints = get_type_hints(fn, include_extras=True)
    except (NameError, TypeError):
        resolved_hints = {}

    for name, parameter in signature.parameters.items():
        if _is_hidden_parameter(name, parameter):
            continue

        schema = _annotation_to_schema(resolved_hints.get(name, parameter.annotation))
        if parameter.default is not inspect.Parameter.empty:
            default = _jsonable_default(parameter.default)
            if default is not _NO_DEFAULT:
                schema["default"] = default
        else:
            required.append(name)

        properties[name] = schema

    payload: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        payload["required"] = required
    return payload


def _is_hidden_parameter(name: str, parameter: inspect.Parameter) -> bool:
    if name in {"self", "cls", "ctx", "context"}:
        return True
    annotation = parameter.annotation
    annotation_name = getattr(annotation, "__name__", "")
    return annotation_name in {"Context", "RequestContext"}


def _annotation_to_schema(annotation: Any) -> dict[str, Any]:
    if annotation is inspect.Parameter.empty or annotation is Any:
        return {}
    if isinstance(annotation, str):
        return {}

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Annotated:
        return _annotation_to_schema(args[0]) if args else {}

    if origin is Literal:
        values = list(args)
        schema: dict[str, Any] = {"enum": values}
        value_types = {type(value) for value in values}
        if len(value_types) == 1 and values:
            schema.update(_annotation_to_schema(type(values[0])))
        return schema

    if origin in (Union, types.UnionType):
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1 and len(non_none_args) != len(args):
            schema = _annotation_to_schema(non_none_args[0])
            schema["nullable"] = True
            return schema
        return {"anyOf": [_annotation_to_schema(arg) for arg in args]}

    if origin in (list, tuple, set, frozenset):
        item_schema = _annotation_to_schema(args[0]) if args else {}
        return {"type": "array", "items": item_schema}

    if origin in (dict, Mapping):
        return {"type": "object"}

    if annotation is str:
        return {"type": "string"}
    if annotation is bool:
        return {"type": "boolean"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}
    if annotation is dict:
        return {"type": "object"}
    if annotation is list:
        return {"type": "array"}
    if annotation is type(None):
        return {"type": "null"}

    annotation_name = getattr(annotation, "__name__", None)
    if annotation_name:
        return {"type": "object", "title": annotation_name}
    return {}


class _NoDefault:
    pass


_NO_DEFAULT = _NoDefault()


def _jsonable_default(value: Any) -> Any:
    try:
        json.dumps(value)
    except TypeError:
        return _NO_DEFAULT
    return value


def _normalize_arguments(arguments: Any) -> tuple[dict[str, Any], Optional[dict[str, Any]]]:
    if arguments is None:
        return {}, None
    if isinstance(arguments, dict):
        return dict(arguments), None
    if isinstance(arguments, str):
        if not arguments.strip():
            return {}, None
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError as exc:
            return {}, {
                "success": False,
                "error": f"arguments must be an object or JSON object string: {exc.msg}",
            }
        if isinstance(parsed, dict):
            return parsed, None
        return {}, {
            "success": False,
            "error": "arguments JSON must decode to an object.",
        }
    return {}, {
        "success": False,
        "error": f"arguments must be an object, JSON object string, or null; got {type(arguments).__name__}.",
    }


def _inject_missing_context_argument(fn: Callable[..., Any], arguments: dict[str, Any]) -> None:
    try:
        signature = inspect.signature(fn)
    except (TypeError, ValueError):
        return

    for name, parameter in signature.parameters.items():
        if name not in {"ctx", "context"}:
            continue
        if name in arguments:
            continue
        if parameter.default is inspect.Parameter.empty:
            arguments[name] = None
