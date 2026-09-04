from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from tools import pcg_tools  # noqa: E402


class FakeMCP:
    def __init__(self) -> None:
        self.tools: dict[str, Any] = {}

    def tool(self, *args: Any, **kwargs: Any) -> Any:
        name = kwargs.get("name")

        if len(args) == 1 and callable(args[0]) and not kwargs:
            fn = args[0]
            self.tools[getattr(fn, "__name__", "")] = fn
            return fn

        def decorator(fn: Any) -> Any:
            self.tools[name or getattr(fn, "__name__", "")] = fn
            return fn

        return decorator


class TestPCGTools(unittest.TestCase):
    def test_registers_pcg_tools(self) -> None:
        mcp = FakeMCP()
        pcg_tools.register_pcg_tools(mcp)

        self.assertEqual(
            set(mcp.tools),
            {"pcg_check_support", "pcg_create_graph_asset", "pcg_create_volume", "pcg_refresh_volume"},
        )

    def test_pcg_check_support_returns_structured_json(self) -> None:
        mcp = FakeMCP()
        pcg_tools.register_pcg_tools(mcp)
        calls: list[tuple[str, str]] = []

        def fake_exec(code: str, stage: str) -> dict[str, Any]:
            calls.append((code, stage))
            return {
                "success": True,
                "stage": stage,
                "message": "Operation completed",
                "outputs": {"pcg_available": True},
                "warnings": [],
                "errors": [],
                "log_tail": [],
            }

        with patch.object(pcg_tools, "_exec_structured", side_effect=fake_exec):
            payload = json.loads(mcp.tools["pcg_check_support"](ctx=None))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["schema"], pcg_tools.PCG_RESULT_SCHEMA)
        self.assertEqual(payload["stage"], "pcg_check_support")
        self.assertEqual(calls[0][1], "pcg_check_support")
        self.assertIn("PCGGraph", calls[0][0])
        self.assertIn("PCGVolume", calls[0][0])

    def test_pcg_create_graph_asset_uses_pcg_graph_factory(self) -> None:
        mcp = FakeMCP()
        pcg_tools.register_pcg_tools(mcp)
        calls: list[tuple[str, str]] = []

        def fake_exec(code: str, stage: str) -> dict[str, Any]:
            calls.append((code, stage))
            return {
                "success": True,
                "stage": stage,
                "message": "Operation completed",
                "outputs": {"asset_path": "/Game/PCG/PCG_Test"},
                "warnings": [],
                "errors": [],
                "log_tail": [],
            }

        with patch.object(pcg_tools, "_exec_structured", side_effect=fake_exec):
            payload = json.loads(mcp.tools["pcg_create_graph_asset"](
                ctx=None,
                graph_path="/Game/PCG/PCG_Test",
                overwrite=True,
                save=False,
            ))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["inputs"]["graph_path"], "/Game/PCG/PCG_Test")
        self.assertEqual(calls[0][1], "pcg_create_graph_asset")
        self.assertIn("PCGGraph", calls[0][0])
        self.assertIn("PCGGraphFactory", calls[0][0])
        self.assertIn("create_asset", calls[0][0])

    def test_invalid_graph_path_fails_before_unreal_execution(self) -> None:
        mcp = FakeMCP()
        pcg_tools.register_pcg_tools(mcp)

        with patch.object(pcg_tools, "_exec_structured") as fake_exec:
            payload = json.loads(mcp.tools["pcg_create_graph_asset"](ctx=None, graph_path="/Engine/PCG_Test"))

        self.assertFalse(payload["success"])
        self.assertIn("/Game", payload["errors"][0])
        fake_exec.assert_not_called()

    def test_pcg_create_volume_generates_defensive_unreal_python(self) -> None:
        mcp = FakeMCP()
        pcg_tools.register_pcg_tools(mcp)
        calls: list[tuple[str, str]] = []

        def fake_exec(code: str, stage: str) -> dict[str, Any]:
            calls.append((code, stage))
            return {
                "success": True,
                "stage": stage,
                "message": "Operation completed",
                "outputs": {"actor_label": "PCG_Test", "component_count": 1},
                "warnings": [],
                "errors": [],
                "log_tail": [],
            }

        with patch.object(pcg_tools, "_exec_structured", side_effect=fake_exec):
            payload = json.loads(mcp.tools["pcg_create_volume"](
                ctx=None,
                actor_label="PCG_Test",
                graph_path="/Game/PCG/PCG_Test",
                generate=True,
            ))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["inputs"]["actor_label"], "PCG_Test")
        self.assertEqual(calls[0][1], "pcg_create_volume")
        self.assertIn("PCGVolume", calls[0][0])
        self.assertIn("PCGComponent", calls[0][0])
        self.assertIn("generation_attempts", calls[0][0])

    def test_refresh_volume_requires_actor_label(self) -> None:
        mcp = FakeMCP()
        pcg_tools.register_pcg_tools(mcp)

        with patch.object(pcg_tools, "_exec_structured") as fake_exec:
            payload = json.loads(mcp.tools["pcg_refresh_volume"](ctx=None, actor_label=""))

        self.assertFalse(payload["success"])
        self.assertIn("actor_label is required", payload["errors"])
        fake_exec.assert_not_called()


if __name__ == "__main__":
    unittest.main()
