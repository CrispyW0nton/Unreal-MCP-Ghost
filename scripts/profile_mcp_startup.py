"""Profile Unreal-MCP-Ghost startup and static tool-discovery latency.

This Phase 7 helper is intentionally offline by default: it does not connect to
Unreal Editor and it does not import the full MCP server unless explicitly
requested. That makes it safe for CI smoke jobs and for quick local baselines.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Callable, Dict, Iterable, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = REPO_ROOT / "scripts" / "tool_inventory.py"
SERVER_PATH = REPO_ROOT / "unreal_mcp_server" / "unreal_mcp_server.py"


@dataclass(frozen=True)
class Timing:
    label: str
    elapsed_ms: float
    ok: bool = True
    detail: str = ""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _load_inventory_module():
    spec = importlib.util.spec_from_file_location("tool_inventory", INVENTORY_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _time_call(label: str, fn: Callable[[], Any]) -> tuple[Timing, Any]:
    started = time.perf_counter()
    try:
        result = fn()
        return Timing(label=label, elapsed_ms=(time.perf_counter() - started) * 1000.0), result
    except Exception as exc:  # pragma: no cover - exercised by command failure paths
        return (
            Timing(
                label=label,
                elapsed_ms=(time.perf_counter() - started) * 1000.0,
                ok=False,
                detail=f"{type(exc).__name__}: {exc}",
            ),
            None,
        )


def _summarize_timings(label: str, timings: Iterable[Timing]) -> Dict[str, Any]:
    items = list(timings)
    elapsed = [item.elapsed_ms for item in items]
    failures = [item for item in items if not item.ok]
    return {
        "label": label,
        "iterations": len(items),
        "ok": not failures,
        "min_ms": min(elapsed) if elapsed else 0.0,
        "max_ms": max(elapsed) if elapsed else 0.0,
        "mean_ms": mean(elapsed) if elapsed else 0.0,
        "median_ms": median(elapsed) if elapsed else 0.0,
        "failures": [failure.detail for failure in failures],
    }


def _run_command(label: str, args: List[str], timeout: float) -> Timing:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            args,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return Timing(
            label=label,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
            ok=False,
            detail=f"Timed out after {exc.timeout}s",
        )

    detail = ""
    ok = completed.returncode == 0
    if not ok:
        stderr = (completed.stderr or completed.stdout or "").strip().splitlines()
        detail = stderr[-1] if stderr else f"exit {completed.returncode}"
    return Timing(
        label=label,
        elapsed_ms=(time.perf_counter() - started) * 1000.0,
        ok=ok,
        detail=detail,
    )


def _profile_decorator_scans(inventory_module: Any, top: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in inventory_module.iter_tool_files():
        started = time.perf_counter()
        text = path.read_text(encoding="utf-8")
        tools = inventory_module.TOOL_RE.findall(text)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        if not tools:
            continue
        rows.append(
            {
                "module": inventory_module._module_name(path),
                "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "tool_count": len(tools),
                "elapsed_ms": elapsed_ms,
            }
        )
    return sorted(rows, key=lambda row: row["elapsed_ms"], reverse=True)[:top]


def collect_profile(
    iterations: int = 3,
    include_server_help: bool = False,
    command_timeout: float = 20.0,
    top: int = 10,
) -> Dict[str, Any]:
    """Collect an offline startup/tool-discovery profile."""
    if iterations < 1:
        raise ValueError("iterations must be at least 1")
    if top < 1:
        raise ValueError("top must be at least 1")

    inventory_module = _load_inventory_module()

    inventory_timings: List[Timing] = []
    inventory_snapshot: Optional[Dict[str, Any]] = None
    for _ in range(iterations):
        timing, inventory_snapshot = _time_call("inventory_build_in_process", inventory_module.build_inventory)
        inventory_timings.append(timing)

    command_timings: List[Timing] = []
    for _ in range(iterations):
        command_timings.append(
            _run_command(
                "tool_inventory_subprocess",
                [sys.executable, str(INVENTORY_PATH), "--json"],
                timeout=command_timeout,
            )
        )

    if include_server_help:
        for _ in range(iterations):
            command_timings.append(
                _run_command(
                    "server_help_subprocess",
                    [sys.executable, str(SERVER_PATH), "--help"],
                    timeout=command_timeout,
                )
            )

    grouped_commands: Dict[str, List[Timing]] = {}
    for timing in command_timings:
        grouped_commands.setdefault(timing.label, []).append(timing)

    inventory = inventory_snapshot or inventory_module.build_inventory()
    return {
        "schema": "unreal_mcp_startup_profile.v1",
        "generated_at": _utc_now(),
        "repo_root": str(REPO_ROOT),
        "python": sys.version.split()[0],
        "iterations": iterations,
        "inventory": {
            "tool_count": inventory["tool_count"],
            "module_count": inventory["module_count"],
            "missing_category_modules": inventory["missing_category_modules"],
        },
        "timings": {
            "inventory_build_in_process": _summarize_timings(
                "inventory_build_in_process",
                inventory_timings,
            ),
            "commands": {
                label: _summarize_timings(label, timings)
                for label, timings in sorted(grouped_commands.items())
            },
        },
        "slowest_module_scans": _profile_decorator_scans(inventory_module, top=top),
    }


def format_markdown(profile: Dict[str, Any]) -> str:
    lines = [
        "# MCP Startup Profile",
        "",
        f"- Generated: {profile['generated_at']}",
        f"- Python: {profile['python']}",
        f"- Iterations: {profile['iterations']}",
        f"- Tools: {profile['inventory']['tool_count']}",
        f"- Modules: {profile['inventory']['module_count']}",
        "",
        "## Timing Summary",
        "",
        "| Measurement | OK | Median ms | Mean ms | Min ms | Max ms |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    def add_summary(summary: Dict[str, Any]) -> None:
        lines.append(
            "| {label} | {ok} | {median:.2f} | {mean:.2f} | {minv:.2f} | {maxv:.2f} |".format(
                label=summary["label"],
                ok="yes" if summary["ok"] else "no",
                median=summary["median_ms"],
                mean=summary["mean_ms"],
                minv=summary["min_ms"],
                maxv=summary["max_ms"],
            )
        )

    add_summary(profile["timings"]["inventory_build_in_process"])
    for summary in profile["timings"]["commands"].values():
        add_summary(summary)

    lines.extend(
        [
            "",
            "## Slowest Decorator Scans",
            "",
            "| Module | Tools | Scan ms | Path |",
            "|---|---:|---:|---|",
        ]
    )
    for row in profile["slowest_module_scans"]:
        lines.append(
            f"| `{row['module']}` | {row['tool_count']} | {row['elapsed_ms']:.2f} | `{row['path']}` |"
        )

    missing = profile["inventory"]["missing_category_modules"]
    lines.extend(["", "## Registry Health", ""])
    if missing:
        lines.append("Missing category metadata:")
        lines.extend(f"- `{module}`" for module in missing)
    else:
        lines.append("All tool modules have category metadata.")

    failures: List[str] = []
    inv_summary = profile["timings"]["inventory_build_in_process"]
    failures.extend(inv_summary.get("failures", []))
    for summary in profile["timings"]["commands"].values():
        failures.extend(summary.get("failures", []))
    if failures:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in failures)

    return "\n".join(lines) + "\n"


def write_reports(profile: Dict[str, Any], json_out: Optional[Path], markdown_out: Optional[Path]) -> None:
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(profile, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if markdown_out:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(format_markdown(profile), encoding="utf-8")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Profile offline Unreal-MCP-Ghost startup latency.")
    parser.add_argument("--iterations", type=int, default=3, help="Number of timing iterations.")
    parser.add_argument("--top", type=int, default=10, help="Number of slow module scans to report.")
    parser.add_argument(
        "--include-server-help",
        action="store_true",
        help="Also time `python unreal_mcp_server/unreal_mcp_server.py --help` cold starts.",
    )
    parser.add_argument("--command-timeout", type=float, default=20.0, help="Subprocess timeout in seconds.")
    parser.add_argument("--json-out", type=Path, help="Optional JSON report path.")
    parser.add_argument("--markdown-out", type=Path, help="Optional Markdown report path.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of the Markdown summary.")
    args = parser.parse_args(argv)

    profile = collect_profile(
        iterations=args.iterations,
        include_server_help=args.include_server_help,
        command_timeout=args.command_timeout,
        top=args.top,
    )
    write_reports(profile, args.json_out, args.markdown_out)
    if args.json:
        print(json.dumps(profile, indent=2, sort_keys=True))
    else:
        print(format_markdown(profile))

    command_summaries = profile["timings"]["commands"].values()
    failed = (
        not profile["timings"]["inventory_build_in_process"]["ok"]
        or any(not summary["ok"] for summary in command_summaries)
        or bool(profile["inventory"]["missing_category_modules"])
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
