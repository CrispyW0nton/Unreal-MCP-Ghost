"""Structural protocol shared by full and narrow FastMCP registrars."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol


class ToolRegistrationSurface(Protocol):
    def tool(
        self, *decorator_args: Any, **decorator_kwargs: Any
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...
