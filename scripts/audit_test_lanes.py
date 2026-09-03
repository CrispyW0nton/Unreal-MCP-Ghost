"""Audit offline, live-bridge, and paid-provider test lane naming.

Default CI discovers ``test_*.py`` files. Live bridge and paid provider tests
must use non-default filenames so offline CI never mutates Unreal or spends
provider credits by accident.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = REPO_ROOT / "unreal_mcp_server" / "tests"
DEFAULT_PATTERN = "test_*.py"
PAID_PROVIDER_SMOKE_NAME = "paid_provider_generative_smoke.py"
PAID_PROVIDER_REQUIRED_ENV_VARS = (
    "RUN_UNREAL_MCP_PAID_PROVIDER_SMOKE",
    "UNREAL_MCP_PROVIDER_NETWORK_APPROVED",
    "UNREAL_MCP_CONFIRM_NO_SPEND_PROVIDER_CHECKS",
)
PAID_PROVIDER_OPTIONAL_ENV_VARS = ("UTHANA_SMOKE_JOB_ID", "UTHANA_SMOKE_MOTION_ID")
PAID_PROVIDER_NO_SPEND_TOOLS = (
    "gen_get_provider_config",
    "gen_tripo_get_credit_balance",
    "gen_uthana_get_account",
    "gen_uthana_get_job",
    "gen_uthana_check_download_allowed",
)
PAID_PROVIDER_FORBIDDEN_TOKENS = (
    "gen_uthana_download_motion(",
    "gen_uthana_text_to_motion(",
    "gen_uthana_video_to_motion(",
    "gen_tripo_text_to_model(",
    "gen_tripo_image_to_model(",
    "gen_tripo_multiview_to_model(",
    "confirm_spend=True",
    "confirm_usage=True",
)


def _lane_for_name(name: str) -> str:
    if name.startswith("paid_provider_"):
        return "paid_provider"
    if name.startswith("live_bridge_"):
        return "live_bridge"
    if name.endswith("_live.py"):
        return "live_bridge_manual"
    if fnmatch.fnmatch(name, DEFAULT_PATTERN):
        return "offline"
    return "manual"


def _display_test_root(test_root: Path) -> str:
    try:
        return str(test_root.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(test_root)


def _is_repo_test_root(test_root: Path) -> bool:
    try:
        return test_root.resolve() == TEST_ROOT.resolve()
    except OSError:
        return False


def _paid_provider_smoke_contract(test_root: Path, lanes: Dict[str, List[str]]) -> Dict[str, Any]:
    smoke_path = test_root / PAID_PROVIDER_SMOKE_NAME
    smoke_text = ""
    if smoke_path.exists():
        try:
            smoke_text = smoke_path.read_text(encoding="utf-8")
        except OSError:
            smoke_text = ""

    required_tokens = (
        *PAID_PROVIDER_REQUIRED_ENV_VARS,
        *PAID_PROVIDER_NO_SPEND_TOOLS,
        "include_raw=False",
        "include_user=False",
    )
    missing_required_tokens = [
        token for token in required_tokens
        if token not in smoke_text
    ]
    forbidden_tokens_present = [
        token for token in PAID_PROVIDER_FORBIDDEN_TOKENS
        if token in smoke_text
    ]
    in_paid_lane = PAID_PROVIDER_SMOKE_NAME in lanes.get("paid_provider", [])
    exists = smoke_path.exists()
    contract_ok = bool(exists and in_paid_lane and not missing_required_tokens and not forbidden_tokens_present)

    return {
        "schema": "unreal_mcp_paid_provider_smoke_contract.v1",
        "smoke_file": PAID_PROVIDER_SMOKE_NAME,
        "smoke_path": str(Path(_display_test_root(test_root)) / PAID_PROVIDER_SMOKE_NAME).replace("\\", "/"),
        "smoke_exists": exists,
        "in_paid_provider_lane": in_paid_lane,
        "manual_command": "python -m unittest unreal_mcp_server.tests.paid_provider_generative_smoke",
        "required_env_vars": list(PAID_PROVIDER_REQUIRED_ENV_VARS),
        "optional_env_vars": list(PAID_PROVIDER_OPTIONAL_ENV_VARS),
        "no_spend_tools": list(PAID_PROVIDER_NO_SPEND_TOOLS),
        "forbidden_tokens": list(PAID_PROVIDER_FORBIDDEN_TOKENS),
        "missing_required_tokens": missing_required_tokens,
        "forbidden_tokens_present": forbidden_tokens_present,
        "contract_ok": contract_ok,
        "default_discovered": fnmatch.fnmatch(PAID_PROVIDER_SMOKE_NAME, DEFAULT_PATTERN),
        "default_ci_network_required": False,
        "default_ci_spend_required": False,
        "manual_network_required": True,
        "manual_spend_required": False,
        "no_task_submission": True,
        "no_download": True,
        "no_import": True,
        "no_editor_mutation": True,
        "no_credit_reservation": True,
        "no_raw_secret_output": True,
    }


def build_lane_report(test_root: Path = TEST_ROOT) -> Dict[str, Any]:
    files = sorted(path for path in test_root.iterdir() if path.is_file() and path.suffix == ".py")
    lanes: Dict[str, List[str]] = {
        "offline": [],
        "live_bridge": [],
        "live_bridge_manual": [],
        "paid_provider": [],
        "manual": [],
    }
    violations: List[Dict[str, str]] = []

    for path in files:
        name = path.name
        lane = _lane_for_name(name)
        lanes[lane].append(name)
        default_discovered = fnmatch.fnmatch(name, DEFAULT_PATTERN)

        if default_discovered and name.startswith("test_live_bridge_"):
            violations.append(
                {
                    "file": name,
                    "reason": "live bridge tests must be named live_bridge_*.py so default offline discovery excludes them",
                }
            )
        if default_discovered and name.startswith("test_paid_provider_"):
            violations.append(
                {
                    "file": name,
                    "reason": "paid provider tests must be named paid_provider_*.py so default offline discovery excludes them",
                }
            )

    paid_provider_contract = _paid_provider_smoke_contract(test_root, lanes)
    if _is_repo_test_root(test_root) and not paid_provider_contract["contract_ok"]:
        violations.append(
            {
                "file": PAID_PROVIDER_SMOKE_NAME,
                "reason": "paid provider smoke contract must remain opt-in, no-spend, no-download, and outside default discovery",
            }
        )

    return {
        "schema": "unreal_mcp_test_lane_audit.v1",
        "test_root": _display_test_root(test_root),
        "default_discovery_pattern": DEFAULT_PATTERN,
        "counts": {lane: len(names) for lane, names in lanes.items()},
        "lanes": lanes,
        "violations": violations,
        "paid_provider_contract": paid_provider_contract,
        "ok": not violations,
    }


def format_report(report: Dict[str, Any]) -> str:
    lines = [
        "# Test Lane Audit",
        "",
        f"- Schema: {report['schema']}",
        f"- Default discovery pattern: `{report['default_discovery_pattern']}`",
        f"- OK: {report['ok']}",
        "",
        "## Counts",
    ]
    for lane, count in report["counts"].items():
        lines.append(f"- {lane}: {count}")
    contract = report.get("paid_provider_contract") if isinstance(report.get("paid_provider_contract"), dict) else {}
    if contract:
        lines.extend([
            "",
            "## Paid Provider Smoke Contract",
            f"- File: {contract.get('smoke_file', '')}",
            f"- Contract OK: {contract.get('contract_ok', False)}",
            f"- Manual command: `{contract.get('manual_command', '')}`",
            f"- Default CI network required: {contract.get('default_ci_network_required', False)}",
            f"- Manual spend required: {contract.get('manual_spend_required', False)}",
        ])
    if report["violations"]:
        lines.extend(["", "## Violations"])
        for violation in report["violations"]:
            lines.append(f"- {violation['file']}: {violation['reason']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit test lane filename separation.")
    parser.add_argument("--json", action="store_true", help="Print the full lane report as JSON.")
    args = parser.parse_args()

    report = build_lane_report()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(format_report(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
