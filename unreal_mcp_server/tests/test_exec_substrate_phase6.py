import asyncio
import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path


_SERVER_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _SERVER_ROOT.parent
if str(_SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVER_ROOT))


class _MockMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def _decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return _decorator

    def list_tool_names(self):
        return list(self.tools)


class TestExecSubstratePhase6(unittest.TestCase):
    def setUp(self):
        from tools.exec_substrate import register_exec_substrate_tools

        self.mcp = _MockMCP()
        register_exec_substrate_tools(self.mcp)

    def test_phase_6_tools_register(self):
        names = set(self.mcp.list_tool_names())
        self.assertIn("execution_journal_start", names)
        self.assertIn("execution_journal_log", names)
        self.assertIn("execution_journal_finish", names)
        self.assertIn("risk_evaluate_action", names)
        self.assertIn("pie_launch_session", names)
        self.assertIn("pie_stop_session", names)
        self.assertIn("pie_capture_log", names)
        self.assertIn("pie_simulate_input", names)
        self.assertIn("viewport_capture_screenshot", names)
        self.assertIn("viewport_compare_screenshot", names)

    def test_execution_journal_lifecycle(self):
        with tempfile.TemporaryDirectory(dir=_REPO_ROOT) as tmp_dir:
            start = json.loads(asyncio.run(self.mcp.tools["execution_journal_start"](
                None,
                "Phase 6 Smoke",
                "Verify the journal lifecycle",
                "Lab5E",
                tmp_dir,
                ["phase6", "smoke"],
                {"branch": "test"},
            )))
            self.assertTrue(start["success"])
            journal_path = start["outputs"]["journal_path"]
            self.assertTrue(Path(journal_path).exists())

            logged = json.loads(asyncio.run(self.mcp.tools["execution_journal_log"](
                None,
                journal_path,
                "Created test evidence",
                "verification",
                "unit_test",
                True,
                "info",
                {"input": "value"},
                {"output": "value"},
                ["/Game/MCP_Test/Phase6"],
                "low",
                {"note": "ok"},
            )))
            self.assertTrue(logged["success"])
            self.assertEqual(logged["outputs"]["entry_count"], 1)

            finished = json.loads(asyncio.run(self.mcp.tools["execution_journal_finish"](
                None,
                journal_path,
                "completed",
                "Journal lifecycle passed",
                ["/Game/MCP_Test/Phase6"],
                {"tests": "passed"},
            )))
            self.assertTrue(finished["success"])
            self.assertEqual(finished["outputs"]["status"], "completed")
            self.assertEqual(finished["outputs"]["stats"]["entry_count"], 1)

            data = json.loads(Path(journal_path).read_text(encoding="utf-8"))
            self.assertEqual(data["schema"], "unreal_mcp_execution_journal.v1")
            self.assertEqual(data["status"], "completed")
            self.assertEqual(data["verification"]["tests"], "passed")

    def test_risk_evaluate_action_levels(self):
        low = json.loads(asyncio.run(self.mcp.tools["risk_evaluate_action"](
            None,
            "Inspect an existing Blueprint graph",
            "/Game/BP_Player",
            "inspect",
            ["/Game/BP_Player"],
            False,
            False,
            False,
            False,
            "single_asset",
            ["journal"],
        )))
        self.assertTrue(low["success"])
        self.assertEqual(low["outputs"]["risk_level"], "low")
        self.assertTrue(low["outputs"]["can_autoproceed"])

        high = json.loads(asyncio.run(self.mcp.tools["risk_evaluate_action"](
            None,
            "Delete and overwrite generated plugin source",
            "unreal_plugin",
            "delete",
            ["/Game/BP_Player", "/Engine/Transient"],
            True,
            True,
            True,
            True,
            "project_wide",
            [],
        )))
        self.assertTrue(high["success"])
        self.assertIn(high["outputs"]["risk_level"], {"high", "critical"})
        self.assertFalse(high["outputs"]["can_autoproceed"])
        self.assertIn("manual_approval_required", high["outputs"]["recommended_gate"])

    def test_viewport_compare_screenshot_identical_pngs(self):
        png_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGA"
            "WjR9awAAAABJRU5ErkJggg=="
        )
        with tempfile.TemporaryDirectory(dir=_REPO_ROOT) as tmp_dir:
            base = Path(tmp_dir) / "baseline.png"
            cand = Path(tmp_dir) / "candidate.png"
            base.write_bytes(png_bytes)
            cand.write_bytes(png_bytes)

            result = json.loads(asyncio.run(self.mcp.tools["viewport_compare_screenshot"](
                None,
                str(base),
                str(cand),
                0.995,
            )))
            self.assertTrue(result["success"])
            self.assertTrue(result["outputs"]["byte_equal"])
            self.assertTrue(result["outputs"]["dimensions_match"])
            self.assertEqual(result["outputs"]["baseline"]["width"], 1)
            self.assertEqual(result["outputs"]["baseline"]["height"], 1)


if __name__ == "__main__":
    unittest.main()
