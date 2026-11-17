"""Target resolution when several Unreal editors run the UnrealMCP bridge (instance_registry.py)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import instance_registry as ir  # noqa: E402

LIVE = os.getpid()      # this test process: alive
DEAD = 2 ** 22 + 7      # no such process


def record(d: Path, pid: int, port: int, project: str) -> None:
    (d / f"{pid}.json").write_text(json.dumps({
        "schema": ir.SCHEMA, "pid": pid, "host": "127.0.0.1", "port": port,
        "project_file": f"C:/Projects/{project}/{project}.uproject", "project_name": project}), encoding="utf-8")


class ResolveTargetTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        ir.select_project(None)

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_records_uses_configured_port(self):
        self.assertEqual(ir.resolve_target(None, "127.0.0.1", 55655, directory=self.dir), ("127.0.0.1", 55655, None))
        self.assertEqual(ir.resolve_target("Seoul", "127.0.0.1", 55655, directory=self.dir)[1], 55655)

    def test_single_editor_is_used_without_a_project(self):
        record(self.dir, LIVE, 55656, "EightLimbsSeoul")
        self.assertEqual(ir.resolve_target(None, directory=self.dir)[1], 55656)

    def test_project_picks_its_editor_by_name_or_path(self):
        record(self.dir, LIVE, 55656, "EightLimbsSeoul")
        (self.dir / "other.json").write_text(json.dumps({
            "schema": ir.SCHEMA, "pid": LIVE, "port": 55657, "project_file": "C:/Projects/DathomirBuildKit/DathomirBuildKit.uproject",
            "project_name": "DathomirBuildKit"}), encoding="utf-8")
        self.assertEqual(ir.resolve_target("DathomirBuildKit", directory=self.dir)[1], 55657)
        self.assertEqual(ir.resolve_target(r"c:\projects\eightlimbsseoul\EightLimbsSeoul.uproject", directory=self.dir)[1], 55656)

    def test_several_editors_without_a_project_are_refused(self):
        record(self.dir, LIVE, 55656, "EightLimbsSeoul")
        (self.dir / "b.json").write_text(json.dumps({"schema": ir.SCHEMA, "pid": LIVE, "port": 55657, "project_file": "C:/P/B/B.uproject",
                                                     "project_name": "B"}), encoding="utf-8")
        with self.assertRaises(ir.TargetResolutionError):
            ir.resolve_target(None, directory=self.dir)
        self.assertEqual(ir.resolve_target(None, "127.0.0.1", 55657, port_pinned=True, directory=self.dir)[1], 55657)

    def test_unknown_project_is_refused_when_others_are_open(self):
        record(self.dir, LIVE, 55656, "EightLimbsSeoul")
        with self.assertRaises(ir.TargetResolutionError):
            ir.resolve_target("DathomirBuildKit", directory=self.dir)

    def test_records_of_exited_editors_are_ignored(self):
        record(self.dir, DEAD, 55656, "EightLimbsSeoul")
        self.assertEqual(ir.resolve_target(None, "127.0.0.1", 55655, directory=self.dir), ("127.0.0.1", 55655, None))

    def test_ping_identity_must_match(self):
        ir.check_identity({"status": "success", "result": {"message": "pong"}}, "Seoul")          # old plugin: no identity
        ir.check_identity({"result": {"project_name": "EightLimbsSeoul", "project_file": "C:/P/EightLimbsSeoul.uproject"}}, "EightLimbsSeoul")
        with self.assertRaises(ir.TargetResolutionError):
            ir.check_identity({"result": {"project_name": "DathomirBuildKit", "project_file": "C:/P/DathomirBuildKit.uproject"}}, "EightLimbsSeoul")

    def test_selected_project_overrides_environment(self):
        os.environ["UNREAL_MCP_PROJECT"] = "A"
        try:
            self.assertEqual(ir.selected_project(), "A")
            ir.select_project("B")
            self.assertEqual(ir.selected_project(), "B")
        finally:
            del os.environ["UNREAL_MCP_PROJECT"]
            ir.select_project(None)


if __name__ == "__main__":
    unittest.main()
