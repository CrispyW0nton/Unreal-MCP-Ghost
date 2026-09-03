"""Run the offline unittest suite and fail if tracked files change.

This guard lets CI verify that import/registry tests remain read-only even when
the checkout already has unrelated local changes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT_PATH = Path("Saved") / "NoMutationTest" / "last_run_receipt.json"


def _run_git_ls_files(repo_root: Path) -> List[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    paths: List[Path] = []
    for raw_path in completed.stdout.split(b"\0"):
        if raw_path:
            paths.append(repo_root / raw_path.decode("utf-8"))
    return paths


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_tracked_files(repo_root: Path, paths: Iterable[Path] | None = None) -> Dict[str, str | None]:
    tracked_paths = list(paths) if paths is not None else _run_git_ls_files(repo_root)
    snapshot: Dict[str, str | None] = {}
    for path in tracked_paths:
        rel_path = path.relative_to(repo_root).as_posix()
        snapshot[rel_path] = _hash_file(path) if path.exists() and path.is_file() else None
    return snapshot


def changed_paths(before: Dict[str, str | None], after: Dict[str, str | None]) -> List[str]:
    all_paths = sorted(set(before) | set(after))
    return [path for path in all_paths if before.get(path) != after.get(path)]


def snapshot_digest(snapshot: Dict[str, str | None]) -> str:
    digest = hashlib.sha256()
    for rel_path in sorted(snapshot):
        digest.update(rel_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(snapshot[rel_path]).encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def build_receipt(
    *,
    command: List[str],
    start_directory: str,
    pattern: str,
    test_exit_code: int,
    mutations: List[str],
    duration_ms: int,
    tracked_file_count: int = 0,
    snapshot_digest_before: str = "",
    snapshot_digest_after: str = "",
) -> Dict[str, Any]:
    snapshot_digest_match = bool(snapshot_digest_before and snapshot_digest_before == snapshot_digest_after)
    return {
        "schema": "unreal_mcp_no_mutation_unittest_receipt.v1",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "command": command,
        "start_directory": start_directory,
        "pattern": pattern,
        "test_exit_code": int(test_exit_code),
        "mutation_count": len(mutations),
        "mutated_paths": mutations,
        "status": "success" if int(test_exit_code) == 0 and not mutations else "failed",
        "duration_ms": int(duration_ms),
        "tracked_file_count": int(tracked_file_count),
        "snapshot_hash_algorithm": "sha256(path\\0content_sha256_or_missing\\0)",
        "snapshot_digest_before": snapshot_digest_before,
        "snapshot_digest_after": snapshot_digest_after,
        "snapshot_digest_match": snapshot_digest_match,
        "snapshot_scope": "git_tracked_worktree",
        "network_required": False,
        "spend_required": False,
        "unreal_editor_required": False,
        "tracked_file_mutation_guard": True,
    }


def write_receipt(path: Path, receipt: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run offline unittests and reject tracked-file mutations.")
    parser.add_argument("--start-directory", default="unreal_mcp_server/tests", help="unittest discovery start directory")
    parser.add_argument("--pattern", default="test_*.py", help="unittest discovery pattern")
    parser.add_argument("--receipt-path", default=str(DEFAULT_RECEIPT_PATH), help="ignored local JSON receipt path")
    args = parser.parse_args()

    started = time.monotonic()
    tracked_paths = _run_git_ls_files(REPO_ROOT)
    before = snapshot_tracked_files(REPO_ROOT, tracked_paths)
    command = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        args.start_directory,
        "-p",
        args.pattern,
    ]
    completed = subprocess.run(command, cwd=REPO_ROOT)
    after = snapshot_tracked_files(REPO_ROOT, tracked_paths)
    mutations = changed_paths(before, after)
    before_digest = snapshot_digest(before)
    after_digest = snapshot_digest(after)
    duration_ms = int((time.monotonic() - started) * 1000)

    print(f"TRACKED_FILE_MUTATIONS={len(mutations)}")
    for path in mutations:
        print(f"mutated: {path}")
    receipt = build_receipt(
        command=command,
        start_directory=args.start_directory,
        pattern=args.pattern,
        test_exit_code=completed.returncode,
        mutations=mutations,
        duration_ms=duration_ms,
        tracked_file_count=len(tracked_paths),
        snapshot_digest_before=before_digest,
        snapshot_digest_after=after_digest,
    )
    try:
        receipt_path = Path(args.receipt_path)
        if not receipt_path.is_absolute():
            receipt_path = REPO_ROOT / receipt_path
        write_receipt(receipt_path, receipt)
        print(f"NO_MUTATION_RECEIPT={args.receipt_path}")
    except OSError as exc:
        print(f"NO_MUTATION_RECEIPT_ERROR={exc}", file=sys.stderr)
        return 1

    if mutations:
        return 1
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
