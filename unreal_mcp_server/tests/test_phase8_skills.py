import asyncio
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


class TestPhase8Skills(unittest.TestCase):
    def test_vertical_slice_report_skill_registers(self):
        from skills.health_system import register_health_system_skill

        mcp = _MockMCP()
        register_health_system_skill(mcp)

        self.assertIn("skill_create_health_system", mcp.tools)
        self.assertIn("skill_package_vertical_slice_report", mcp.tools)

    def test_vertical_slice_report_packages_journal(self):
        from skills.health_system import skill_package_vertical_slice_report

        with tempfile.TemporaryDirectory(dir=_REPO_ROOT) as tmp_dir:
            tmp = Path(tmp_dir)
            journal_path = tmp / "journal.json"
            report_dir = tmp / "reports"
            journal_path.write_text(json.dumps({
                "schema": "unreal_mcp_execution_journal.v1",
                "journal_id": "phase8test",
                "title": "Phase 8 Test Journal",
                "goal": "Package evidence",
                "project_name": "Lab5E",
                "status": "completed",
                "started_at": "2026-05-17T00:00:00Z",
                "finished_at": "2026-05-17T00:01:00Z",
                "entries": [
                    {
                        "timestamp": "2026-05-17T00:00:10Z",
                        "event_type": "verification",
                        "severity": "info",
                        "success": True,
                        "message": "PIE smoke passed",
                    }
                ],
                "artifacts": ["/Game/MCP_Test/Phase8"],
                "verification": {"tests": "passed"},
                "summary": "Journal summary.",
                "stats": {"entry_count": 1, "failure_count": 0},
            }), encoding="utf-8")

            result = skill_package_vertical_slice_report(
                title="Phase 8 Vertical Slice",
                summary="Packaged report summary.",
                journal_path=str(journal_path),
                report_dir=str(report_dir),
                artifacts=["/Game/MCP_Test/ExtraArtifact"],
                verification={"screenshot_similarity": 1.0},
            )

            self.assertTrue(result["success"])
            report_path = Path(result["outputs"]["report_path"])
            self.assertTrue(report_path.exists())
            text = report_path.read_text(encoding="utf-8")
            self.assertIn("# Phase 8 Vertical Slice", text)
            self.assertIn("Packaged report summary.", text)
            self.assertIn("PIE smoke passed", text)
            self.assertIn("/Game/MCP_Test/Phase8", text)
            self.assertIn("screenshot_similarity", text)
            self.assertEqual(result["outputs"]["artifact_count"], 2)

    def test_vertical_slice_report_tool_returns_json(self):
        from skills.health_system import register_health_system_skill

        mcp = _MockMCP()
        register_health_system_skill(mcp)
        with tempfile.TemporaryDirectory(dir=_REPO_ROOT) as tmp_dir:
            result = json.loads(asyncio.run(mcp.tools["skill_package_vertical_slice_report"](
                None,
                "Tool Report",
                "Tool summary.",
                "",
                tmp_dir,
                "Lab5E",
                ["/Game/TestAsset"],
                {"unit": "passed"},
                False,
                10,
            )))
            self.assertTrue(result["success"])
            self.assertTrue(Path(result["outputs"]["report_path"]).exists())


if __name__ == "__main__":
    unittest.main()
