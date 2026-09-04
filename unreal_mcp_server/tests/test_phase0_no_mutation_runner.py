"""Offline tests for the tracked-file no-mutation unittest runner."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_no_mutation_unittest.py"


def _load_runner_module():
    spec = importlib.util.spec_from_file_location("run_no_mutation_unittest", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class NoMutationRunnerTest(unittest.TestCase):
    def test_snapshot_detects_changed_tracked_file(self) -> None:
        module = _load_runner_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            tracked = repo_root / "tracked.txt"
            tracked.write_text("before", encoding="utf-8")

            before = module.snapshot_tracked_files(repo_root, [tracked])
            tracked.write_text("after", encoding="utf-8")
            after = module.snapshot_tracked_files(repo_root, [tracked])

        self.assertEqual(module.changed_paths(before, after), ["tracked.txt"])

    def test_snapshot_does_not_report_unchanged_dirty_file(self) -> None:
        module = _load_runner_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            tracked = repo_root / "tracked.txt"
            tracked.write_text("already dirty but stable", encoding="utf-8")

            before = module.snapshot_tracked_files(repo_root, [tracked])
            after = module.snapshot_tracked_files(repo_root, [tracked])

        self.assertEqual(module.changed_paths(before, after), [])
        self.assertEqual(module.snapshot_digest(before), module.snapshot_digest(after))

    def test_snapshot_digest_changes_when_tracked_content_changes(self) -> None:
        module = _load_runner_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            tracked = repo_root / "tracked.txt"
            tracked.write_text("before", encoding="utf-8")
            before = module.snapshot_tracked_files(repo_root, [tracked])
            tracked.write_text("after", encoding="utf-8")
            after = module.snapshot_tracked_files(repo_root, [tracked])

        self.assertNotEqual(module.snapshot_digest(before), module.snapshot_digest(after))

    def test_receipt_schema_records_clean_and_mutating_runs(self) -> None:
        module = _load_runner_module()

        clean = module.build_receipt(
            command=["python", "-m", "unittest"],
            start_directory="unreal_mcp_server/tests",
            pattern="test_*.py",
            test_exit_code=0,
            mutations=[],
            duration_ms=123,
            tracked_file_count=42,
            snapshot_digest_before="abc",
            snapshot_digest_after="abc",
        )
        dirty = module.build_receipt(
            command=["python", "-m", "unittest"],
            start_directory="unreal_mcp_server/tests",
            pattern="test_*.py",
            test_exit_code=0,
            mutations=["unreal_mcp_server/tests/last_tool_count.txt"],
            duration_ms=456,
            tracked_file_count=42,
            snapshot_digest_before="abc",
            snapshot_digest_after="def",
        )

        self.assertEqual(clean["schema"], "unreal_mcp_no_mutation_unittest_receipt.v1")
        self.assertEqual(clean["status"], "success")
        self.assertEqual(clean["mutation_count"], 0)
        self.assertEqual(clean["tracked_file_count"], 42)
        self.assertEqual(clean["snapshot_scope"], "git_tracked_worktree")
        self.assertTrue(clean["snapshot_digest_match"])
        self.assertEqual(clean["snapshot_hash_algorithm"], "sha256(path\\0content_sha256_or_missing\\0)")
        self.assertTrue(clean["tracked_file_mutation_guard"])
        self.assertFalse(clean["network_required"])
        self.assertFalse(clean["spend_required"])
        self.assertFalse(clean["unreal_editor_required"])
        self.assertEqual(dirty["status"], "failed")
        self.assertEqual(dirty["mutation_count"], 1)
        self.assertFalse(dirty["snapshot_digest_match"])

    def test_write_receipt_creates_ignored_local_json_shape(self) -> None:
        module = _load_runner_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            receipt_path = Path(tmpdir) / "Saved" / "NoMutationTest" / "last_run_receipt.json"
            receipt = module.build_receipt(
                command=["python", "-m", "unittest"],
                start_directory="tests",
                pattern="test_*.py",
                test_exit_code=0,
                mutations=[],
                duration_ms=1,
            )
            module.write_receipt(receipt_path, receipt)

            text = receipt_path.read_text(encoding="utf-8")

        self.assertIn("unreal_mcp_no_mutation_unittest_receipt.v1", text)
        self.assertIn('"status": "success"', text)


if __name__ == "__main__":
    unittest.main()
