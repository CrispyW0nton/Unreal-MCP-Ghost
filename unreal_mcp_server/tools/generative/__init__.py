"""Provider contracts for AI-generated content pipelines.

D.5 keeps the public MCP tools stable while giving future Meshy, Stability, or
ComfyUI integrations a shared surface for metadata, output policy, and task
cost estimation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Protocol, Sequence, runtime_checkable


@dataclass(frozen=True)
class ProviderOutputPolicy:
    """Provider-owned rules for result URLs and local import selection."""

    model_output_keys: Sequence[str]
    import_output_keys: Sequence[str]
    model_extensions: Sequence[str]
    image_extensions: Sequence[str]


@dataclass(frozen=True)
class ProviderTaskResult:
    """Normalized provider task state used by MCP tools."""

    provider: str
    task_id: str
    status: str
    output: Mapping[str, Any]
    trace_id: str = ""
    raw: Mapping[str, Any] | None = None


@runtime_checkable
class GenerativeProvider(Protocol):
    """Protocol every generated-content provider must satisfy."""

    name: str
    display_name: str
    base_url: str
    capabilities: Sequence[str]
    final_statuses: Sequence[str]
    output_policy: ProviderOutputPolicy

    def describe(self, config: Mapping[str, Any]) -> Dict[str, Any]:
        """Return provider metadata safe to expose through MCP."""

    def normalize_model_version(self, value: str | None) -> str:
        """Map local sentinel/default values to provider request values."""

    def estimate_credits(self, task_type: str, payload: Mapping[str, Any]) -> int:
        """Return a conservative local estimate for a provider task."""

    def output_suffix(self, key: str, url: str) -> str:
        """Infer a local file suffix for a provider output URL."""

    def select_primary_model_download(self, downloads: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
        """Choose the best downloaded model file for Unreal import."""


class ProviderRegistry:
    """Small in-process provider registry used by generative tools."""

    def __init__(self, providers: Iterable[GenerativeProvider]):
        self._providers = {provider.name: provider for provider in providers}

    def get(self, name: str) -> GenerativeProvider:
        try:
            return self._providers[name]
        except KeyError as exc:
            raise KeyError(f"Unknown generative provider: {name}") from exc

    def list(self) -> List[GenerativeProvider]:
        return list(self._providers.values())


def path_has_extension(path: str, extensions: Sequence[str]) -> bool:
    """Return true when path has a provider-supported file extension."""

    return Path(str(path)).suffix.lower() in {ext.lower() for ext in extensions}
