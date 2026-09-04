"""No-mutation preflight for the Unreal-MCP-Ghost IDE companion.

The script reports whether the repo, MCP registry, editor bridge, chat server,
provider config, and build wrapper are ready for an IDE companion session. It
does not call Unreal editor commands, submit provider requests, or write files.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = REPO_ROOT / "unreal_mcp_server"
TOOL_COUNT_PATH = SERVER_ROOT / "tests" / "last_tool_count.txt"
SETTINGS_PATH = REPO_ROOT / "Saved" / "MCPChat" / "generative_settings.json"
SECRETS_PATH = REPO_ROOT / "Saved" / "MCPChat" / "secrets.json"
BUILD_WRAPPER_PATH = REPO_ROOT / "scripts" / "run_insanitii_clean_build_and_tripo_verify.ps1"
LEGACY_BUILD_WRAPPER_PATH = REPO_ROOT / "_build_plugin.bat"
BUILD_WRAPPER_PATHS = [BUILD_WRAPPER_PATH, LEGACY_BUILD_WRAPPER_PATH]
PLUGIN_BUILD_RECEIPT_PATH = REPO_ROOT / "Saved" / "PluginBuildSmoke" / "last_build_receipt.json"
PLUGIN_BUILD_LOG_PATH = REPO_ROOT / "Saved" / "PluginBuildSmoke" / "last_build.log"
NO_MUTATION_RECEIPT_PATH = REPO_ROOT / "Saved" / "NoMutationTest" / "last_run_receipt.json"
CHAT_COCKPIT_START_SCRIPT = Path("scripts") / "start_chat_cockpit_server.ps1"
CHAT_COCKPIT_START_RECEIPT_PATH = Path("Saved") / "ChatCockpit" / "last_start_receipt.json"
DIRTY_PROMOTION_REVIEW_RECEIPT_PATH = REPO_ROOT / "Saved" / "DirtyPromotionReview" / "last_review_receipt.json"
BRIDGE_PING_RECEIPT_PATH = REPO_ROOT / "Saved" / "BridgePing" / "last_ping_receipt.json"
PROVIDER_CONFIG_REVIEW_RECEIPT_PATH = REPO_ROOT / "Saved" / "ProviderConfigReview" / "last_review_receipt.json"
PAID_GENERATION_EVIDENCE_REVIEW_RECEIPT_PATH = REPO_ROOT / "Saved" / "PaidGenerationEvidence" / "last_review_receipt.json"
BLUEPRINT_MUTATION_EVIDENCE_REVIEW_RECEIPT_PATH = REPO_ROOT / "Saved" / "BlueprintMutationEvidence" / "last_review_receipt.json"
PLATFORM_STABILITY_REVIEW_RECEIPT_PATH = REPO_ROOT / "Saved" / "PlatformStabilityReview" / "last_review_receipt.json"
TEST_LANE_AUDIT_PATH = REPO_ROOT / "scripts" / "audit_test_lanes.py"
HIGH_VALUE_WRAPPER_AUDIT_PATH = REPO_ROOT / "scripts" / "audit_high_value_wrapper_coverage.py"
DEVELOPMENT_BRANCH = "wip"
STABLE_BRANCH = "main"
AUTOMATION_LOG_ROOTS = [
    Path(os.environ.get("APPDATA", "")) / "Unreal Engine" / "AutomationTool" / "Logs",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Unreal Engine" / "AutomationTool" / "Logs",
]


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _load_tool_inventory() -> Any:
    spec = importlib.util.spec_from_file_location("tool_inventory", REPO_ROOT / "scripts" / "tool_inventory.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load tool inventory")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tool_inventory_status() -> Dict[str, Any]:
    inventory = _load_tool_inventory().build_inventory()
    try:
        recorded_count = int(TOOL_COUNT_PATH.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        recorded_count = None
    return {
        "tool_count": inventory["tool_count"],
        "recorded_count": recorded_count,
        "module_count": inventory["module_count"],
        "live_tools": inventory["status_counts"].get("live", 0),
        "partial_tools": inventory["status_counts"].get("partial", 0),
        "missing_category_modules": inventory["missing_category_modules"],
        "matches_recorded_count": recorded_count == inventory["tool_count"],
        "source_scope": inventory["source_scope"],
    }


def _test_lane_status() -> Dict[str, Any]:
    if not TEST_LANE_AUDIT_PATH.exists():
        return {
            "schema": "unreal_mcp_test_lane_audit.v1",
            "ok": False,
            "error": "scripts/audit_test_lanes.py is missing",
            "counts": {},
            "violations": [{"file": "scripts/audit_test_lanes.py", "reason": "missing test lane audit"}],
        }

    try:
        spec = importlib.util.spec_from_file_location("audit_test_lanes", TEST_LANE_AUDIT_PATH)
        if spec is None or spec.loader is None:
            raise RuntimeError("Could not load test lane audit")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = module.build_lane_report()
    except Exception as exc:  # pragma: no cover - defensive preflight fallback
        return {
            "schema": "unreal_mcp_test_lane_audit.v1",
            "ok": False,
            "error": str(exc),
            "counts": {},
            "violations": [{"file": "scripts/audit_test_lanes.py", "reason": str(exc)}],
        }

    counts = report.get("counts") if isinstance(report.get("counts"), dict) else {}
    lanes = report.get("lanes") if isinstance(report.get("lanes"), dict) else {}
    violations = report.get("violations") if isinstance(report.get("violations"), list) else []
    paid_provider_contract = report.get("paid_provider_contract") if isinstance(report.get("paid_provider_contract"), dict) else {}
    return {
        "schema": str(report.get("schema", "unreal_mcp_test_lane_audit.v1")),
        "ok": bool(report.get("ok", False)),
        "test_root": str(report.get("test_root", "")),
        "default_discovery_pattern": str(report.get("default_discovery_pattern", "test_*.py")),
        "counts": counts,
        "offline_count": int(counts.get("offline", 0) or 0),
        "live_bridge_count": int(counts.get("live_bridge", 0) or 0),
        "live_bridge_manual_count": int(counts.get("live_bridge_manual", 0) or 0),
        "paid_provider_count": int(counts.get("paid_provider", 0) or 0),
        "manual_count": int(counts.get("manual", 0) or 0),
        "violation_count": len(violations),
        "violations": violations,
        "offline_preview": list(lanes.get("offline", []))[:5] if isinstance(lanes.get("offline"), list) else [],
        "live_bridge_preview": list(lanes.get("live_bridge", []))[:5] if isinstance(lanes.get("live_bridge"), list) else [],
        "live_bridge_manual_preview": list(lanes.get("live_bridge_manual", []))[:5] if isinstance(lanes.get("live_bridge_manual"), list) else [],
        "paid_provider_preview": list(lanes.get("paid_provider", []))[:5] if isinstance(lanes.get("paid_provider"), list) else [],
        "paid_provider_contract": paid_provider_contract,
        "paid_provider_contract_ok": bool(paid_provider_contract.get("contract_ok", False)) if paid_provider_contract else False,
        "paid_provider_manual_command": str(paid_provider_contract.get("manual_command", "")) if paid_provider_contract else "",
        "paid_provider_required_env_vars": list(paid_provider_contract.get("required_env_vars", [])) if isinstance(paid_provider_contract.get("required_env_vars"), list) else [],
        "paid_provider_optional_env_vars": list(paid_provider_contract.get("optional_env_vars", [])) if isinstance(paid_provider_contract.get("optional_env_vars"), list) else [],
        "paid_provider_no_spend_tools": list(paid_provider_contract.get("no_spend_tools", [])) if isinstance(paid_provider_contract.get("no_spend_tools"), list) else [],
        "paid_provider_forbidden_tokens_present": list(paid_provider_contract.get("forbidden_tokens_present", [])) if isinstance(paid_provider_contract.get("forbidden_tokens_present"), list) else [],
        "paid_provider_default_ci_network_required": bool(paid_provider_contract.get("default_ci_network_required", False)) if paid_provider_contract else False,
        "paid_provider_manual_network_required": bool(paid_provider_contract.get("manual_network_required", False)) if paid_provider_contract else False,
        "paid_provider_manual_spend_required": bool(paid_provider_contract.get("manual_spend_required", False)) if paid_provider_contract else False,
        "audit_tool": "scripts/audit_test_lanes.py",
        "default_ci_safe": bool(report.get("ok", False)),
        "network_required": False,
        "spend_required": False,
        "unreal_editor_required": False,
    }


def _no_mutation_test_status(path: Path = NO_MUTATION_RECEIPT_PATH) -> Dict[str, Any]:
    operator_command_handoff = [
        {
            "id": "run_no_mutation_unittest",
            "label": "Run no-mutation unittest lane",
            "command": "python scripts\\run_no_mutation_unittest.py",
            "command_kind": "local_validation_receipt",
            "receipt_path": "Saved\\NoMutationTest\\last_run_receipt.json",
            "produces_evidence_for": "no_mutation_test_lane_safe",
            "records_evidence_only": False,
            "requires_bridge": False,
            "requires_provider_network": False,
            "requires_spend": False,
            "no_editor_mutation": True,
            "no_provider_call": True,
            "no_git_mutation": True,
            "no_task_submission": True,
        }
    ]
    receipt = _load_json(path)
    if not receipt:
        return {
            "schema": "unreal_mcp_no_mutation_unittest_receipt.v1",
            "state": "missing",
            "ok": False,
            "receipt_exists": False,
            "receipt_path": str(path),
            "status": "missing",
            "test_exit_code": None,
            "mutation_count": None,
            "mutated_paths": [],
            "tracked_file_count": None,
            "snapshot_digest_match": False,
            "snapshot_scope": "git_tracked_worktree",
            "required_command": "python scripts\\run_no_mutation_unittest.py",
            "operator_command_handoff": operator_command_handoff,
            "operator_command_handoff_ids": [item["id"] for item in operator_command_handoff],
            "operator_command_handoff_count": len(operator_command_handoff),
            "network_required": False,
            "spend_required": False,
            "unreal_editor_required": False,
        }
    mutation_count = int(receipt.get("mutation_count", 0) or 0)
    test_exit_code = receipt.get("test_exit_code")
    try:
        test_exit_code = int(test_exit_code) if test_exit_code is not None else None
    except (TypeError, ValueError):
        test_exit_code = None
    status = str(receipt.get("status", "unknown") or "unknown")
    ok = status == "success" and test_exit_code == 0 and mutation_count == 0
    return {
        "schema": str(receipt.get("schema", "unreal_mcp_no_mutation_unittest_receipt.v1")),
        "state": "ok" if ok else "blocked",
        "ok": ok,
        "receipt_exists": True,
        "receipt_path": str(path),
        "receipt_mtime": int(path.stat().st_mtime) if path.exists() else None,
        "status": status,
        "generated_at_utc": str(receipt.get("generated_at_utc", "")),
        "test_exit_code": test_exit_code,
        "mutation_count": mutation_count,
        "mutated_paths": list(receipt.get("mutated_paths", []))[:20] if isinstance(receipt.get("mutated_paths"), list) else [],
        "tracked_file_count": receipt.get("tracked_file_count"),
        "snapshot_hash_algorithm": str(receipt.get("snapshot_hash_algorithm", "")),
        "snapshot_digest_match": bool(receipt.get("snapshot_digest_match", False)),
        "snapshot_scope": str(receipt.get("snapshot_scope", "git_tracked_worktree")),
        "start_directory": str(receipt.get("start_directory", "")),
        "pattern": str(receipt.get("pattern", "")),
        "duration_ms": int(receipt.get("duration_ms", 0) or 0),
        "command": list(receipt.get("command", [])) if isinstance(receipt.get("command"), list) else [],
        "required_command": "python scripts\\run_no_mutation_unittest.py",
        "operator_command_handoff": operator_command_handoff,
        "operator_command_handoff_ids": [item["id"] for item in operator_command_handoff],
        "operator_command_handoff_count": len(operator_command_handoff),
        "network_required": False,
        "spend_required": False,
        "unreal_editor_required": False,
    }


def _runtime_status() -> Dict[str, Any]:
    return {
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "python_version_info": {
            "major": sys.version_info.major,
            "minor": sys.version_info.minor,
            "micro": sys.version_info.micro,
            "releaselevel": sys.version_info.releaselevel,
            "serial": sys.version_info.serial,
        },
        "platform": platform.platform(),
        "implementation": platform.python_implementation(),
        "cwd": str(Path.cwd()),
        "repo_root": str(REPO_ROOT),
        "virtual_env": os.environ.get("VIRTUAL_ENV", ""),
        "is_venv": bool(os.environ.get("VIRTUAL_ENV")) or sys.prefix != sys.base_prefix,
    }


def _git_status() -> Dict[str, Any]:
    branch = _git_branch_status()
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "available": False,
            "error": str(exc),
            "branch": branch,
            "dirty_count": None,
            "sample": [],
            "dirty_risk": "unknown",
            "tracked_change_count": None,
            "untracked_count": None,
            "status_counts": {},
            "risk_reasons": [str(exc)],
        }
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    parsed = _parse_git_porcelain(lines)
    parsed.update({
        "available": completed.returncode == 0,
        "returncode": completed.returncode,
        "stderr": completed.stderr.strip(),
        "branch": branch,
    })
    return parsed


def _git_branch_status() -> Dict[str, Any]:
    base = {
        "current": "",
        "development_branch": DEVELOPMENT_BRANCH,
        "stable_branch": STABLE_BRANCH,
        "role": "unknown",
        "working_branch_ok": False,
        "promotion_target": STABLE_BRANCH,
        "policy": "work on wip; promote to main only after stability evidence",
    }
    try:
        completed = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {**base, "error": str(exc)}

    current = completed.stdout.strip()
    if not current:
        return {**base, "current": "", "role": "detached", "error": completed.stderr.strip()}
    if current == DEVELOPMENT_BRANCH:
        role = "development"
        working_branch_ok = True
    elif current == STABLE_BRANCH:
        role = "stable"
        working_branch_ok = False
    else:
        role = "unexpected"
        working_branch_ok = False
    return {
        **base,
        "current": current,
        "role": role,
        "working_branch_ok": working_branch_ok,
        "returncode": completed.returncode,
        "stderr": completed.stderr.strip(),
    }


def _parse_git_porcelain(lines: List[str]) -> Dict[str, Any]:
    status_counts = {
        "modified": 0,
        "added": 0,
        "deleted": 0,
        "renamed": 0,
        "copied": 0,
        "untracked": 0,
        "conflicted": 0,
        "other": 0,
    }
    tracked_change_count = 0
    untracked_count = 0
    generated_or_local_count = 0
    generated_prefixes = (
        ".mcp_artifacts/",
        ".pytest_cache/",
        "__pycache__/",
        "Saved/",
        "build_artifacts/",
        "generated_audio/",
    )
    group_counts: Dict[str, int] = {}
    group_tracked_counts: Dict[str, int] = {}
    group_untracked_counts: Dict[str, int] = {}
    group_status_counts: Dict[str, Dict[str, int]] = {}
    group_samples: Dict[str, List[str]] = {}

    for line in lines:
        status = line[:2]
        path = line[3:].replace("\\", "/") if len(line) > 3 else ""
        group = _dirty_group_for_path(path)
        status_kind = _dirty_status_kind(status)
        group_counts[group] = group_counts.get(group, 0) + 1
        group_status_counts.setdefault(group, {})
        group_status_counts[group][status_kind] = group_status_counts[group].get(status_kind, 0) + 1
        group_samples.setdefault(group, [])
        if len(group_samples[group]) < 3:
            group_samples[group].append(line)
        if status == "??":
            status_counts["untracked"] += 1
            untracked_count += 1
            group_untracked_counts[group] = group_untracked_counts.get(group, 0) + 1
        else:
            tracked_change_count += 1
            group_tracked_counts[group] = group_tracked_counts.get(group, 0) + 1
            if "U" in status or status in {"AA", "DD"}:
                status_counts["conflicted"] += 1
            if "M" in status:
                status_counts["modified"] += 1
            if "A" in status:
                status_counts["added"] += 1
            if "D" in status:
                status_counts["deleted"] += 1
            if "R" in status:
                status_counts["renamed"] += 1
            if "C" in status:
                status_counts["copied"] += 1
            if not any(marker in status for marker in ("M", "A", "D", "R", "C", "U")):
                status_counts["other"] += 1
        if path.startswith(generated_prefixes) or "/__pycache__/" in path:
            generated_or_local_count += 1

    dirty_count = len(lines)
    risk_reasons: List[str] = []
    if dirty_count == 0:
        dirty_risk = "clean"
    elif status_counts["conflicted"]:
        dirty_risk = "high"
        risk_reasons.append("merge conflicts present")
    elif tracked_change_count >= 50 or dirty_count >= 150:
        dirty_risk = "high"
        risk_reasons.append("large dirty worktree")
    elif tracked_change_count >= 10 or dirty_count >= 50:
        dirty_risk = "elevated"
        risk_reasons.append("many changed files")
    else:
        dirty_risk = "moderate"
        risk_reasons.append("uncommitted changes present")
    if generated_or_local_count:
        risk_reasons.append(f"{generated_or_local_count} generated/local artifact path(s)")
    dirty_groups = [
        {
            "group": group,
            "count": count,
            "tracked_count": group_tracked_counts.get(group, 0),
            "untracked_count": group_untracked_counts.get(group, 0),
            "status_counts": group_status_counts.get(group, {}),
            "sample": group_samples.get(group, []),
        }
        for group, count in sorted(group_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    primary_dirty_group = dirty_groups[0]["group"] if dirty_groups else ""

    dirty_signature = _dirty_worktree_signature(lines)
    return {
        "dirty_count": dirty_count,
        "dirty_signature": dirty_signature,
        "dirty_signature_algorithm": "sha256(git_status_porcelain_v1_sorted_lines)",
        "dirty_signature_entry_count": dirty_count,
        "dirty_risk": dirty_risk,
        "tracked_change_count": tracked_change_count,
        "untracked_count": untracked_count,
        "generated_or_local_count": generated_or_local_count,
        "status_counts": status_counts,
        "risk_reasons": risk_reasons,
        "sample": lines[:12],
        "dirty_groups": dirty_groups,
        "dirty_group_count": len(dirty_groups),
        "dirty_group_preview": dirty_groups[:8],
        "primary_dirty_group": primary_dirty_group,
        "dirty_grouping_required": dirty_risk not in {"clean", "low"} or tracked_change_count > 0,
    }


def _dirty_worktree_signature(lines: List[str]) -> str:
    digest = hashlib.sha256()
    for line in sorted(str(item) for item in lines):
        digest.update(line.encode("utf-8", errors="replace"))
        digest.update(b"\0")
    return digest.hexdigest()


def _dirty_status_kind(status: str) -> str:
    if status == "??":
        return "untracked"
    if "U" in status or status in {"AA", "DD"}:
        return "conflicted"
    if "D" in status:
        return "deleted"
    if "A" in status:
        return "added"
    if "R" in status:
        return "renamed"
    if "C" in status:
        return "copied"
    if "M" in status:
        return "modified"
    return "other"


def _dirty_group_for_path(path: str) -> str:
    normalized = path.replace("\\", "/").strip()
    if not normalized:
        return "unknown"
    if normalized.startswith((".mcp_artifacts/", "Saved/", "Intermediate/", "Binaries/", "DerivedDataCache/")):
        return "local_artifacts"
    if normalized.startswith(("generated_audio/", ".tmp_", "build_artifacts/")):
        return "local_artifacts"
    if normalized.startswith("unreal_plugin/"):
        return "unreal_plugin"
    if normalized.startswith("unreal_mcp_server/tests/"):
        return "server_tests"
    if normalized.startswith("unreal_mcp_server/tools/"):
        return "server_tools"
    if normalized.startswith("unreal_mcp_server/chat/"):
        return "chat_cockpit"
    if normalized.startswith("unreal_mcp_server/skills/"):
        return "server_skills"
    if normalized.startswith("unreal_mcp_server/"):
        return "server_core"
    if normalized.startswith("scripts/"):
        return "scripts"
    if normalized.startswith("knowledge_base/Projects/"):
        return "project_knowledge"
    if normalized.startswith("knowledge_base/") or normalized.startswith("docs/"):
        return "knowledge_base_docs"
    if normalized.startswith((".cursor/", "cursor_setup/")) or normalized in {"cursor_mcp_config.json"}:
        return "agent_config"
    if normalized.startswith("BP_") or normalized.endswith("_PROJECT_REFERENCE.md"):
        return "project_notes"
    if normalized in {"README.md", "AGENTS.md"} or normalized.endswith(".md"):
        return "repo_docs"
    if normalized in {"package.json", "package-lock.json", "uv.lock"}:
        return "workspace_dependencies"
    return "repo_root"


def _tcp_reachable(host: str, port: int, timeout_s: float) -> Dict[str, Any]:
    started = time.monotonic()
    sock = socket.socket()
    sock.settimeout(timeout_s)
    try:
        result = sock.connect_ex((host, port))
    except Exception as exc:
        return {
            "checked": True,
            "ready": False,
            "host": host,
            "port": port,
            "error": str(exc),
            "duration_ms": int((time.monotonic() - started) * 1000),
        }
    finally:
        sock.close()
    return {
        "checked": True,
        "ready": result == 0,
        "host": host,
        "port": port,
        "connect_ex": result,
        "duration_ms": int((time.monotonic() - started) * 1000),
    }


def _chat_status(base_url: str, timeout_s: float) -> Dict[str, Any]:
    normalized_base_url = base_url.rstrip("/")
    url = f"{normalized_base_url}/chat/history?limit=1"
    tcp_status = _chat_tcp_status(normalized_base_url, timeout_s)
    startup_receipt = _chat_cockpit_start_receipt_status()
    startup_script = str(CHAT_COCKPIT_START_SCRIPT)
    startup_receipt_path = str(CHAT_COCKPIT_START_RECEIPT_PATH)
    startup_command = (
        "powershell -ExecutionPolicy Bypass -File "
        f"{startup_script} -BindHost 127.0.0.1 -Port 8000"
    )
    manual_startup_command = "python unreal_mcp_server\\unreal_mcp_server.py --transport sse --mcp-host 127.0.0.1 --mcp-port 8000"
    base = {
        "checked": True,
        "ready": False,
        "url": url,
        "base_url": normalized_base_url,
        "health_endpoint": "/chat/history?limit=1",
        "expected_transport": "sse",
        "expected_mcp_endpoint": f"{normalized_base_url}/sse",
        "startup_script": startup_script,
        "startup_receipt_path": startup_receipt_path,
        "startup_receipt": startup_receipt,
        "startup_receipt_exists": bool(startup_receipt.get("receipt_exists", False)),
        "startup_receipt_state": str(startup_receipt.get("state", "missing")),
        "startup_receipt_required_command": str(startup_receipt.get("required_command", "powershell -ExecutionPolicy Bypass -File scripts\\start_chat_cockpit_server.ps1")),
        "startup_command": startup_command,
        "manual_startup_command": manual_startup_command,
        "agent_command": "npm run chat:agent",
        "troubleshooting": [
            "Start the MCP server in SSE mode with scripts\\start_chat_cockpit_server.ps1 before opening the Unreal MCP Chat panel.",
            "If /chat/history returns 404, stop the old process on port 8000 and restart the current server.",
            "Run the Cursor watcher separately only after the chat routes are reachable.",
        ],
        "tcp": tcp_status,
        "tcp_ready": bool(tcp_status.get("ready", False)),
        "network_required": False,
        "spend_required": False,
        "unreal_editor_required": False,
    }
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            body = response.read().decode("utf-8", errors="replace")
            parsed = json.loads(body) if body else {}
            return {
                **base,
                "ready": response.status == 200 and isinstance(parsed.get("messages"), list),
                "http_status": response.status,
                "message_count": len(parsed.get("messages", [])) if isinstance(parsed.get("messages"), list) else None,
            }
    except urllib.error.HTTPError as exc:
        return {
            **base,
            "http_status": exc.code,
            "error": str(exc),
            "failure_mode": "old_or_wrong_http_server" if exc.code == 404 else "http_error",
        }
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return {**base, "error": str(exc), "failure_mode": "not_reachable"}


def _chat_cockpit_repair_contract(chat: Dict[str, Any]) -> Dict[str, Any]:
    ready = bool(chat.get("ready", False))
    base_url = str(chat.get("base_url", "http://127.0.0.1:8000") or "http://127.0.0.1:8000")
    health_endpoint = str(chat.get("health_endpoint", "/chat/history?limit=1") or "/chat/history?limit=1")
    health_url = str(chat.get("url", f"{base_url}{health_endpoint}") or f"{base_url}{health_endpoint}")
    startup_script = str(chat.get("startup_script", str(CHAT_COCKPIT_START_SCRIPT)) or str(CHAT_COCKPIT_START_SCRIPT))
    startup_receipt_path = str(chat.get("startup_receipt_path", str(CHAT_COCKPIT_START_RECEIPT_PATH)) or str(CHAT_COCKPIT_START_RECEIPT_PATH))
    return {
        "schema": "unreal_mcp_chat_cockpit_repair_contract.v1",
        "state": "ready" if ready else "needs_startup",
        "ready": ready,
        "base_url": base_url,
        "health_endpoint": health_endpoint,
        "health_url": health_url,
        "expected_transport": str(chat.get("expected_transport", "sse") or "sse"),
        "expected_mcp_endpoint": str(chat.get("expected_mcp_endpoint", f"{base_url}/sse") or f"{base_url}/sse"),
        "tcp_ready": bool(chat.get("tcp_ready", False)),
        "failure_mode": str(chat.get("failure_mode", "")),
        "startup_script": startup_script,
        "startup_receipt_path": startup_receipt_path,
        "startup_command": str(chat.get("startup_command", f"powershell -ExecutionPolicy Bypass -File {startup_script} -BindHost 127.0.0.1 -Port 8000")),
        "manual_startup_command": str(chat.get("manual_startup_command", "python unreal_mcp_server\\unreal_mcp_server.py --transport sse --mcp-host 127.0.0.1 --mcp-port 8000")),
        "agent_command": str(chat.get("agent_command", "npm run chat:agent")),
        "proof_command": f"Invoke-WebRequest -UseBasicParsing {health_url}",
        "proof_expected": "HTTP 200 with JSON object containing messages list",
        "startup_steps": [
            "Start MCP server in SSE mode using startup_command",
            f"Confirm startup receipt exists at {startup_receipt_path}",
            "Verify /chat/history?limit=1 returns HTTP 200 with messages list",
            "Start Cursor watcher only after chat route is reachable",
            "Open or refresh Unreal MCP Chat panel after SSE endpoint is ready",
        ],
        "required_evidence": [
            "chat_cockpit_start_receipt_success",
            "chat_tcp_ready_true",
            "chat_history_http_200",
            "chat_history_messages_list",
            "sse_transport_endpoint_available",
            "unreal_chat_panel_refresh_after_server_ready",
        ],
        "no_process_start": True,
        "no_port_kill": True,
        "no_editor_mutation": True,
        "no_provider_call": True,
        "no_git_mutation": True,
        "network_required": False,
        "spend_required": False,
        "unreal_editor_required": False,
    }


def _chat_cockpit_start_receipt_status(path: Path = REPO_ROOT / CHAT_COCKPIT_START_RECEIPT_PATH) -> Dict[str, Any]:
    display_path = "Saved\\ChatCockpit\\last_start_receipt.json"
    base = {
        "schema": "unreal_mcp_chat_cockpit_start_receipt.v1",
        "path": display_path,
        "receipt_exists": path.exists(),
        "required_command": "powershell -ExecutionPolicy Bypass -File scripts\\start_chat_cockpit_server.ps1",
        "network_required": False,
        "spend_required": False,
        "unreal_editor_required": False,
        "no_port_kill": True,
        "no_editor_mutation": True,
        "no_provider_call": True,
        "no_git_mutation": True,
    }
    if not path.exists():
        return {**base, "state": "missing", "status": "missing"}
    parsed = _load_json(path)
    schema = str(parsed.get("schema", ""))
    status = str(parsed.get("status", "unknown"))
    schema_ok = schema == "unreal_mcp_chat_cockpit_start_receipt.v1"
    if schema_ok and status in {"started", "already_running"}:
        state = "ready"
    elif schema_ok and status == "failed":
        state = "blocked"
    else:
        state = "blocked"
    return {
        **base,
        "schema": schema or base["schema"],
        "state": state,
        "status": status,
        "generated_at_utc": str(parsed.get("generated_at_utc", "")),
        "base_url": str(parsed.get("base_url", "")),
        "health_url": str(parsed.get("health_url", "")),
        "mcp_endpoint": str(parsed.get("mcp_endpoint", "")),
        "process_started": bool(parsed.get("process_started", False)),
        "process_id": parsed.get("process_id"),
        "exit_code": parsed.get("exit_code"),
        "failure_mode": str(parsed.get("failure_mode", "")),
        "no_port_kill": bool(parsed.get("no_port_kill", True)),
        "no_editor_mutation": bool(parsed.get("no_editor_mutation", True)),
        "no_provider_call": bool(parsed.get("no_provider_call", True)),
        "no_git_mutation": bool(parsed.get("no_git_mutation", True)),
    }


def _chat_tcp_status(base_url: str, timeout_s: float) -> Dict[str, Any]:
    parsed = urllib.parse.urlparse(base_url)
    host = parsed.hostname or "127.0.0.1"
    if parsed.port:
        port = parsed.port
    elif parsed.scheme == "https":
        port = 443
    else:
        port = 80
    return _tcp_reachable(host, port, timeout_s)


def _provider_config_status() -> Dict[str, Any]:
    env_key = os.environ.get("TRIPO_API_KEY", "").strip()
    uthana_env_key = os.environ.get("UTHANA_API_KEY", "").strip()
    settings = _load_json(SETTINGS_PATH)
    secrets = _load_json(SECRETS_PATH)
    stored_key = str(secrets.get("TRIPO_API_KEY") or secrets.get("tripo_api_key") or "").strip()
    uthana_stored_key = str(secrets.get("UTHANA_API_KEY") or secrets.get("uthana_api_key") or "").strip()
    source = "env" if env_key else ("secrets" if stored_key else "missing")
    uthana_source = "env" if uthana_env_key else ("secrets" if uthana_stored_key else "missing")
    key = env_key or stored_key
    uthana_key = uthana_env_key or uthana_stored_key
    masked = f"{key[:6]}...{key[-4:]}" if len(key) >= 12 else ("configured" if key else "")
    uthana_masked = f"{uthana_key[:6]}...{uthana_key[-4:]}" if len(uthana_key) >= 12 else ("configured" if uthana_key else "")
    secrets_ignored = _path_is_gitignored(SECRETS_PATH)
    settings_ignored = _path_is_gitignored(SETTINGS_PATH)
    secret_contract = {
        "secrets_path": str(SECRETS_PATH),
        "settings_path": str(SETTINGS_PATH),
        "secrets_gitignored": secrets_ignored,
        "settings_gitignored": settings_ignored,
        "raw_key_returned": False,
        "masked_status_only": True,
        "secret_storage": "env vars or ignored Saved/MCPChat/secrets.json",
    }
    repair_contract = {
        "schema": "unreal_mcp_provider_config_repair.v1",
        "config_tool": "gen_get_provider_config",
        "save_tool": "gen_save_provider_config",
        "native_settings_surface": "MCP Chat Generate Settings",
        "tripo_env_var": "TRIPO_API_KEY",
        "uthana_env_var": "UTHANA_API_KEY",
        "tripo_missing": not bool(key),
        "uthana_missing": not bool(uthana_key),
        "tripo_store_command_template": 'gen_save_provider_config(tripo_api_key="<TRIPO_API_KEY>", store_api_key=True)',
        "uthana_store_command_template": 'gen_save_provider_config(uthana_api_key="<UTHANA_API_KEY>", store_uthana_api_key=True)',
        "clear_tripo_command": "gen_save_provider_config(clear_stored_api_key=True)",
        "clear_uthana_command": "gen_save_provider_config(clear_stored_uthana_api_key=True)",
        "proof_tool": "gen_get_provider_config(include_paths=True)",
        "proof_required": [
            "api_key_configured true for Tripo before paid mesh generation",
            "uthana_api_key_configured true for Uthana before paid motion generation",
            "wallet_or_allowance_evidence recorded separately before spend",
            "explicit spend or usage confirmation recorded separately before task submission",
        ],
        "no_leak_policy": "Never place raw provider keys in chat, docs, command output, tests, or ledger evidence.",
        "network_required": False,
        "spend_required": False,
        "unreal_editor_required": False,
    }
    operator_command_handoff = [
        {
            "id": "write_provider_config_review_receipt",
            "label": "Write masked provider config review receipt",
            "command": "python scripts\\write_provider_config_review.py",
            "command_kind": "local_receipt",
            "receipt_path": "Saved\\ProviderConfigReview\\last_review_receipt.json",
            "produces_evidence_for": "provider_config_review",
            "records_evidence_only": True,
            "requires_bridge": False,
            "requires_provider_network": False,
            "requires_spend": False,
            "no_raw_key": True,
            "no_provider_call": True,
            "no_wallet_check": True,
            "no_credit_reservation": True,
            "no_task_submission": True,
            "no_download": True,
            "no_import": True,
            "no_spend_confirmation": True,
            "no_editor_mutation": True,
            "no_git_mutation": True,
        }
    ]
    review_receipt = _provider_config_review_receipt_status()
    return {
        "provider": settings.get("provider", "tripo"),
        "animation_provider": settings.get("animation_provider", "uthana"),
        "api_key_configured": bool(key),
        "api_key_source": source,
        "api_key_masked": masked,
        "uthana_api_key_configured": bool(uthana_key),
        "uthana_api_key_source": uthana_source,
        "uthana_api_key_masked": uthana_masked,
        "settings_path": str(SETTINGS_PATH),
        "settings_exists": SETTINGS_PATH.exists(),
        "secrets_path": str(SECRETS_PATH),
        "secrets_exists": SECRETS_PATH.exists(),
        "secrets_gitignored": secrets_ignored,
        "settings_gitignored": settings_ignored,
        "secret_contract": secret_contract,
        "repair_contract": repair_contract,
        "review_receipt": review_receipt,
        "review_receipt_exists": bool(review_receipt.get("receipt_exists", False)),
        "review_receipt_state": str(review_receipt.get("state", "missing")),
        "review_receipt_path": str(review_receipt.get("path", "Saved\\ProviderConfigReview\\last_review_receipt.json")),
        "review_receipt_required_command": "python scripts\\write_provider_config_review.py",
        "operator_command_handoff": operator_command_handoff,
        "operator_command_handoff_ids": [item["id"] for item in operator_command_handoff],
        "operator_command_handoff_count": len(operator_command_handoff),
        "output_folder": settings.get("output_folder", "/Game/Generated"),
        "animation_output_folder": settings.get("animation_output_folder", "/Game/Generated/Animations"),
        "session_credit_budget": settings.get("session_credit_budget", 1000),
        "network_required": False,
        "spend_required": False,
    }


def _provider_config_review_receipt_status(path: Path = PROVIDER_CONFIG_REVIEW_RECEIPT_PATH) -> Dict[str, Any]:
    display_path = "Saved\\ProviderConfigReview\\last_review_receipt.json"
    base = {
        "schema": "unreal_mcp_provider_config_review_receipt.v1",
        "path": display_path,
        "receipt_exists": path.exists(),
        "required_command": "python scripts\\write_provider_config_review.py",
        "network_required": False,
        "spend_required": False,
        "unreal_editor_required": False,
        "no_raw_key": True,
        "no_provider_call": True,
        "no_wallet_check": True,
        "no_credit_reservation": True,
        "no_spend_confirmation": True,
        "no_editor_mutation": True,
        "no_git_mutation": True,
    }
    if not path.exists():
        return {
            **base,
            "state": "missing",
            "status": "missing",
            "api_key_configured": False,
            "uthana_api_key_configured": False,
        }
    parsed = _load_json(path)
    schema = str(parsed.get("schema", ""))
    status = str(parsed.get("status", "unknown"))
    schema_ok = schema == "unreal_mcp_provider_config_review_receipt.v1"
    tripo_ready = bool(parsed.get("api_key_configured", False))
    uthana_ready = bool(parsed.get("uthana_api_key_configured", False))
    if schema_ok and status == "ready" and tripo_ready and uthana_ready:
        state = "ready"
    elif schema_ok and status in {"missing_keys", "ready"}:
        state = "missing_keys"
    else:
        state = "blocked"
    return {
        **base,
        "schema": schema or base["schema"],
        "state": state,
        "status": status,
        "generated_at_utc": str(parsed.get("generated_at_utc", "")),
        "provider": str(parsed.get("provider", "tripo")),
        "animation_provider": str(parsed.get("animation_provider", "uthana")),
        "api_key_configured": tripo_ready,
        "api_key_source": str(parsed.get("api_key_source", "missing")),
        "uthana_api_key_configured": uthana_ready,
        "uthana_api_key_source": str(parsed.get("uthana_api_key_source", "missing")),
        "secrets_gitignored": bool(parsed.get("secrets_gitignored", False)),
        "settings_gitignored": bool(parsed.get("settings_gitignored", False)),
    }


def _paid_generation_evidence_review_receipt_status(
    path: Path = PAID_GENERATION_EVIDENCE_REVIEW_RECEIPT_PATH,
) -> Dict[str, Any]:
    display_path = "Saved\\PaidGenerationEvidence\\last_review_receipt.json"
    base = {
        "schema": "unreal_mcp_paid_generation_evidence_review_receipt.v1",
        "path": display_path,
        "receipt_exists": path.exists(),
        "required_command": "python scripts\\write_paid_generation_evidence_review.py",
        "wallet_evidence_recorded": False,
        "mesh_wallet_evidence_recorded": False,
        "animation_allowance_evidence_recorded": False,
        "spend_confirmation_recorded": False,
        "explicit_spend_approval_recorded": False,
        "explicit_usage_approval_recorded": False,
        "network_required": False,
        "spend_required": False,
        "unreal_editor_required": False,
        "no_provider_call": True,
        "no_wallet_check": True,
        "no_credit_reservation": True,
        "no_task_submission": True,
        "no_download": True,
        "no_import": True,
        "no_editor_mutation": True,
        "no_git_mutation": True,
    }
    if not path.exists():
        return {
            **base,
            "state": "missing",
            "status": "missing",
        }
    parsed = _load_json(path)
    schema = str(parsed.get("schema", ""))
    status = str(parsed.get("status", "unknown"))
    schema_ok = schema == "unreal_mcp_paid_generation_evidence_review_receipt.v1"
    legacy_wallet_recorded = bool(parsed.get("wallet_evidence_recorded", False))
    mesh_wallet_recorded = bool(parsed.get("mesh_wallet_evidence_recorded", legacy_wallet_recorded))
    animation_allowance_recorded = bool(parsed.get("animation_allowance_evidence_recorded", legacy_wallet_recorded))
    wallet_recorded = bool(legacy_wallet_recorded or (mesh_wallet_recorded and animation_allowance_recorded))
    legacy_spend_recorded = bool(parsed.get("spend_confirmation_recorded", False))
    explicit_spend_recorded = bool(parsed.get("explicit_spend_approval_recorded", legacy_spend_recorded))
    explicit_usage_recorded = bool(parsed.get("explicit_usage_approval_recorded", legacy_spend_recorded))
    spend_recorded = bool(legacy_spend_recorded or (explicit_spend_recorded and explicit_usage_recorded))
    if schema_ok and status == "ready" and wallet_recorded and spend_recorded:
        state = "ready"
    elif schema_ok and status in {"missing_evidence", "ready"}:
        state = "missing_evidence"
    else:
        state = "blocked"
    return {
        **base,
        "schema": schema or base["schema"],
        "state": state,
        "status": status,
        "generated_at_utc": str(parsed.get("generated_at_utc", "")),
        "provider": str(parsed.get("provider", "tripo")),
        "animation_provider": str(parsed.get("animation_provider", "uthana")),
        "wallet_evidence_recorded": wallet_recorded,
        "mesh_wallet_evidence_recorded": mesh_wallet_recorded,
        "animation_allowance_evidence_recorded": animation_allowance_recorded,
        "spend_confirmation_recorded": spend_recorded,
        "explicit_spend_approval_recorded": explicit_spend_recorded,
        "explicit_usage_approval_recorded": explicit_usage_recorded,
        "wallet_evidence_summary": str(parsed.get("wallet_evidence_summary", "")),
        "mesh_wallet_evidence_summary": str(parsed.get("mesh_wallet_evidence_summary", "")),
        "animation_allowance_summary": str(parsed.get("animation_allowance_summary", "")),
        "spend_confirmation_summary": str(parsed.get("spend_confirmation_summary", "")),
        "explicit_spend_approval_summary": str(parsed.get("explicit_spend_approval_summary", "")),
        "usage_approval_summary": str(parsed.get("usage_approval_summary", "")),
        "estimated_spend_reviewed": bool(parsed.get("estimated_spend_reviewed", False)),
        "estimated_motion_seconds_reviewed": bool(parsed.get("estimated_motion_seconds_reviewed", parsed.get("estimated_spend_reviewed", False))),
        "human_approval_required_before_provider_work": bool(parsed.get("human_approval_required_before_provider_work", True)),
    }


def _blueprint_mutation_evidence_review_receipt_status(
    path: Path = BLUEPRINT_MUTATION_EVIDENCE_REVIEW_RECEIPT_PATH,
) -> Dict[str, Any]:
    display_path = "Saved\\BlueprintMutationEvidence\\last_review_receipt.json"
    pre_read_command = (
        'python scripts\\write_blueprint_mutation_evidence_review.py --pre-read-evidence-recorded '
        '--target-blueprint-path "<target Blueprint asset path>" '
        '--intended-mutation-summary "<intended Blueprint change>" '
        '--pre-read-summary "<read-only graph/component state summary>"'
    )
    compile_command = (
        'python scripts\\write_blueprint_mutation_evidence_review.py --compile-plan-recorded '
        '--compile-plan-summary "<compile command and failure repair plan>"'
    )
    readback_command = (
        'python scripts\\write_blueprint_mutation_evidence_review.py --readback-plan-recorded '
        '--readback-plan-summary "<expected graph/component readback proof>"'
    )
    default_handoff = _blueprint_mutation_operator_command_handoff(
        pre_read_command,
        compile_command,
        readback_command,
    )
    base = {
        "schema": "unreal_mcp_blueprint_mutation_evidence_review_receipt.v1",
        "path": display_path,
        "receipt_exists": path.exists(),
        "required_command": "python scripts\\write_blueprint_mutation_evidence_review.py",
        "pre_read_receipt_command_template": pre_read_command,
        "compile_plan_receipt_command_template": compile_command,
        "readback_plan_receipt_command_template": readback_command,
        "operator_command_handoff": default_handoff,
        "pre_read_evidence_recorded": False,
        "compile_plan_recorded": False,
        "readback_plan_recorded": False,
        "network_required": False,
        "spend_required": False,
        "unreal_editor_required": False,
        "no_bridge_ping": True,
        "no_editor_mutation": True,
        "no_blueprint_mutation": True,
        "no_compile": True,
        "no_save": True,
        "no_pie": True,
        "no_provider_call": True,
        "no_git_mutation": True,
    }
    if not path.exists():
        return {
            **base,
            "state": "missing",
            "status": "missing",
        }
    parsed = _load_json(path)
    schema = str(parsed.get("schema", ""))
    status = str(parsed.get("status", "unknown"))
    schema_ok = schema == "unreal_mcp_blueprint_mutation_evidence_review_receipt.v1"
    pre_read_recorded = bool(parsed.get("pre_read_evidence_recorded", False))
    compile_recorded = bool(parsed.get("compile_plan_recorded", False))
    readback_recorded = bool(parsed.get("readback_plan_recorded", False))
    if schema_ok and status == "ready" and pre_read_recorded and compile_recorded and readback_recorded:
        state = "ready"
    elif schema_ok and status in {"missing_evidence", "ready"}:
        state = "missing_evidence"
    else:
        state = "blocked"
    return {
        **base,
        "schema": schema or base["schema"],
        "state": state,
        "status": status,
        "generated_at_utc": str(parsed.get("generated_at_utc", "")),
        "pre_read_evidence_recorded": pre_read_recorded,
        "compile_plan_recorded": compile_recorded,
        "readback_plan_recorded": readback_recorded,
        "target_blueprint_path": str(parsed.get("target_blueprint_path", "")),
        "intended_mutation_summary": str(parsed.get("intended_mutation_summary", "")),
        "pre_read_summary": str(parsed.get("pre_read_summary", "")),
        "compile_plan_summary": str(parsed.get("compile_plan_summary", "")),
        "readback_plan_summary": str(parsed.get("readback_plan_summary", "")),
        "required_evidence": list(parsed.get("required_evidence", [])) if isinstance(parsed.get("required_evidence"), list) else [],
        "pre_read_receipt_command_template": str(parsed.get("pre_read_receipt_command_template", pre_read_command)),
        "compile_plan_receipt_command_template": str(parsed.get("compile_plan_receipt_command_template", compile_command)),
        "readback_plan_receipt_command_template": str(parsed.get("readback_plan_receipt_command_template", readback_command)),
        "operator_command_handoff": (
            list(parsed.get("operator_command_handoff", []))[:3]
            if isinstance(parsed.get("operator_command_handoff"), list)
            else default_handoff
        ),
        "merge_policy": str(parsed.get("merge_policy", "preserve_existing_evidence_unless_reset")),
        "reset_evidence": bool(parsed.get("reset_evidence", False)),
        "human_approval_required_before_blueprint_mutation": bool(parsed.get("human_approval_required_before_blueprint_mutation", True)),
    }


def _path_is_gitignored(path: Path) -> bool:
    try:
        completed = subprocess.run(
            ["git", "check-ignore", "-q", str(path.relative_to(REPO_ROOT))],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def _build_status() -> Dict[str, Any]:
    ubt_log = Path(os.environ.get("LOCALAPPDATA", "")) / "UnrealBuildTool" / "Log.txt"
    automation_log = _latest_automation_log()
    wrapper_status = _build_wrapper_status()
    receipt_status = _parse_plugin_build_receipt(PLUGIN_BUILD_RECEIPT_PATH)
    automation_status = receipt_status or (_parse_automation_log(automation_log) if automation_log else {
        "last_plugin_build_status": "unknown",
        "last_plugin_build_exit_code": None,
        "last_plugin_build_summary": [],
        "last_plugin_build_warning_count": 0,
        "last_plugin_build_warning_categories": [],
        "last_plugin_build_warning_preview": [],
        "last_plugin_build_warning_severity": "unknown",
    })
    build_health = "blocked" if wrapper_status["missing_reference_count"] else (
        "ok" if automation_status["last_plugin_build_status"] == "success" else "unknown"
    )
    return {
        "build_wrapper_exists": BUILD_WRAPPER_PATH.exists(),
        "build_wrapper_path": str(BUILD_WRAPPER_PATH),
        "build_wrapper_count": wrapper_status["wrapper_count"],
        "build_wrapper_existing_count": wrapper_status["existing_count"],
        "build_wrapper_status": wrapper_status["status"],
        "build_wrapper_project_ready": wrapper_status["project_ready"],
        "build_wrapper_plugin_ready": wrapper_status["plugin_ready"],
        "build_wrapper_tool_ready": wrapper_status["tool_ready"],
        "build_wrapper_missing_references": wrapper_status["missing_references"],
        "build_wrapper_project_paths": wrapper_status["project_paths"],
        "build_wrapper_plugin_paths": wrapper_status["plugin_paths"],
        "build_wrapper_tool_paths": wrapper_status["tool_paths"],
        "build_wrappers": wrapper_status["wrappers"],
        "build_health": build_health,
        "last_ubt_log_exists": ubt_log.exists(),
        "last_ubt_log_path": str(ubt_log),
        "last_ubt_log_mtime": int(ubt_log.stat().st_mtime) if ubt_log.exists() else None,
        "last_automation_log_exists": automation_log is not None,
        "last_automation_log_path": str(automation_log) if automation_log else "",
        "last_automation_log_mtime": int(automation_log.stat().st_mtime) if automation_log and automation_log.exists() else None,
        "local_build_receipt_exists": PLUGIN_BUILD_RECEIPT_PATH.exists(),
        "local_build_receipt_path": str(PLUGIN_BUILD_RECEIPT_PATH),
        "local_build_receipt_mtime": int(PLUGIN_BUILD_RECEIPT_PATH.stat().st_mtime) if PLUGIN_BUILD_RECEIPT_PATH.exists() else None,
        "local_build_log_path": str(PLUGIN_BUILD_LOG_PATH),
        "last_plugin_build_source": "local_receipt" if receipt_status else ("automation_log" if automation_log else "none"),
        **automation_status,
    }


def _parse_plugin_build_receipt(path: Path) -> Optional[Dict[str, Any]]:
    receipt = _load_json(path)
    if not receipt:
        return None
    status = str(receipt.get("status", "")).strip().lower()
    if status not in {"success", "failed", "unknown"}:
        status = "unknown"
    exit_code = receipt.get("exit_code")
    try:
        exit_code = int(exit_code) if exit_code is not None else None
    except (TypeError, ValueError):
        exit_code = None
    log_path = Path(str(receipt.get("log_path") or PLUGIN_BUILD_LOG_PATH))
    log_status = _parse_automation_log(log_path) if log_path.exists() else {}
    if log_status.get("last_plugin_build_status") in {"success", "failed"}:
        status = str(log_status["last_plugin_build_status"])
    if log_status.get("last_plugin_build_exit_code") is not None:
        exit_code = log_status["last_plugin_build_exit_code"]
    summary = list(log_status.get("last_plugin_build_summary", []))
    if not summary:
        summary = [
            f"Receipt status: {status}",
            f"Receipt generated at: {receipt.get('generated_at_utc', '')}",
        ]
    return {
        "last_plugin_build_status": status,
        "last_plugin_build_exit_code": exit_code,
        "last_plugin_build_summary": summary[-8:],
        "last_plugin_build_warning_count": int(log_status.get("last_plugin_build_warning_count", 0) or 0),
        "last_plugin_build_warning_categories": list(log_status.get("last_plugin_build_warning_categories", [])),
        "last_plugin_build_warning_preview": list(log_status.get("last_plugin_build_warning_preview", [])),
        "last_plugin_build_warning_severity": str(log_status.get("last_plugin_build_warning_severity", "none" if not log_status.get("last_plugin_build_warning_count") else "unknown")),
        "last_plugin_build_receipt_schema": str(receipt.get("schema", "")),
        "last_plugin_build_receipt_generated_at_utc": str(receipt.get("generated_at_utc", "")),
        "last_plugin_build_receipt_plugin_path": str(receipt.get("plugin_path", "")),
        "last_plugin_build_receipt_package_dir": str(receipt.get("package_dir", "")),
        "last_plugin_build_log_path": str(log_path),
    }


def _build_wrapper_status(paths: Optional[List[Path]] = None) -> Dict[str, Any]:
    wrapper_paths = paths or BUILD_WRAPPER_PATHS
    wrappers = [_inspect_build_wrapper(path) for path in wrapper_paths]
    existing = [wrapper for wrapper in wrappers if wrapper["exists"]]
    missing_references: List[str] = []
    project_paths: List[str] = []
    plugin_paths: List[str] = []
    tool_paths: List[str] = []
    for wrapper in wrappers:
        project_paths.extend(wrapper["project_paths"])
        plugin_paths.extend(wrapper["plugin_paths"])
        tool_paths.extend(wrapper["tool_paths"])
        missing_references.extend(wrapper["missing_project_paths"])
        missing_references.extend(wrapper["missing_plugin_paths"])
        missing_references.extend(wrapper["missing_tool_paths"])
    if not existing:
        status = "missing_wrapper"
    elif missing_references:
        status = "missing_reference"
    else:
        status = "ready"
    return {
        "status": status,
        "wrapper_count": len(wrapper_paths),
        "existing_count": len(existing),
        "project_ready": bool(existing) and not any(wrapper["missing_project_paths"] for wrapper in wrappers),
        "plugin_ready": bool(existing) and not any(wrapper["missing_plugin_paths"] for wrapper in wrappers),
        "tool_ready": bool(existing) and not any(wrapper["missing_tool_paths"] for wrapper in wrappers),
        "missing_reference_count": len(missing_references),
        "missing_references": missing_references,
        "project_paths": project_paths,
        "plugin_paths": plugin_paths,
        "tool_paths": tool_paths,
        "wrappers": wrappers,
    }


def _inspect_build_wrapper(path: Path) -> Dict[str, Any]:
    exists = path.exists()
    result: Dict[str, Any] = {
        "path": str(path),
        "exists": exists,
        "project_paths": [],
        "missing_project_paths": [],
        "plugin_paths": [],
        "missing_plugin_paths": [],
        "tool_paths": [],
        "missing_tool_paths": [],
    }
    if not exists:
        return result
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        result["read_error"] = str(exc)
        return result
    project_paths = _extract_project_paths_from_wrapper(text, base_path=path.parent)
    plugin_paths = _extract_plugin_paths_from_wrapper(text, base_path=path.parent)
    tool_paths = _extract_build_tool_paths_from_wrapper(text, base_path=path.parent)
    result["project_paths"] = [str(item) for item in project_paths]
    result["missing_project_paths"] = [str(item) for item in project_paths if not item.exists()]
    result["plugin_paths"] = [str(item) for item in plugin_paths]
    result["missing_plugin_paths"] = [str(item) for item in plugin_paths if not item.exists()]
    result["tool_paths"] = [str(item) for item in tool_paths]
    result["missing_tool_paths"] = [str(item) for item in tool_paths if not item.exists()]
    return result


def _extract_project_paths_from_wrapper(text: str, *, base_path: Optional[Path] = None) -> List[Path]:
    raw_paths: List[str] = []
    raw_paths.extend(match.group(1) for match in re.finditer(r"\$ProjectPath\s*=\s*\"([^\"]+\.uproject)\"", text, re.IGNORECASE))
    raw_paths.extend(match.group(1) for match in re.finditer(r"set\s+\"(?:PROJECT_PATH|ProjectPath)=([^\"]+\.uproject)\"", text, re.IGNORECASE))
    raw_paths.extend(match.group(1) for match in re.finditer(r"-Project=\"([^\"]+\.uproject)\"", text, re.IGNORECASE))
    raw_paths.extend(match.group(1) for match in re.finditer(r"-Project=([^\s\"]+\.uproject)", text, re.IGNORECASE))
    return _dedupe_paths(raw_paths, base_path=base_path)


def _extract_plugin_paths_from_wrapper(text: str, *, base_path: Optional[Path] = None) -> List[Path]:
    raw_paths: List[str] = []
    raw_paths.extend(match.group(1) for match in re.finditer(r"set\s+\"(?:PLUGIN_PATH|PluginPath)=([^\"]+\.uplugin)\"", text, re.IGNORECASE))
    raw_paths.extend(match.group(1) for match in re.finditer(r"-Plugin=\"([^\"]+\.uplugin)\"", text, re.IGNORECASE))
    raw_paths.extend(match.group(1) for match in re.finditer(r"-Plugin=([^\s\"]+\.uplugin)", text, re.IGNORECASE))
    return _dedupe_paths(raw_paths, base_path=base_path)


def _extract_build_tool_paths_from_wrapper(text: str, *, base_path: Optional[Path] = None) -> List[Path]:
    raw_paths: List[str] = []
    raw_paths.extend(match.group(1) for match in re.finditer(r"\$BuildBat\s*=\s*\"([^\"]+(?:Build|RunUAT)\.bat)\"", text, re.IGNORECASE))
    raw_paths.extend(match.group(1) for match in re.finditer(r"set\s+\"(?:BUILD_BAT|BuildBat|RUN_UAT|RunUAT)=([^\"]+(?:Build|RunUAT)\.bat)\"", text, re.IGNORECASE))
    raw_paths.extend(match.group(1) for match in re.finditer(r"\"(((?:[A-Za-z]:)|(?:\\\\))[^\"]+(?:Build|RunUAT)\.bat)\"", text, re.IGNORECASE))
    return _dedupe_paths(raw_paths, base_path=base_path)


def _dedupe_paths(raw_paths: List[str], *, base_path: Optional[Path] = None) -> List[Path]:
    paths: List[Path] = []
    seen = set()
    for raw_path in raw_paths:
        normalized = _normalize_wrapper_path(raw_path, base_path=base_path)
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        paths.append(Path(normalized))
    return paths


def _normalize_wrapper_path(raw_path: str, *, base_path: Optional[Path] = None) -> str:
    normalized = raw_path.strip()
    if not normalized:
        return ""
    if base_path is not None:
        wrapper_root = str(base_path) + os.sep
        normalized = re.sub(r"%~dp0", lambda _match: wrapper_root, normalized, flags=re.IGNORECASE)
    normalized = os.path.expandvars(normalized)
    if "%" in normalized:
        return ""
    path = Path(normalized)
    if base_path is not None and not path.is_absolute():
        path = base_path / path
    try:
        return str(path.resolve(strict=False))
    except OSError:
        return str(path)


def _latest_automation_log() -> Optional[Path]:
    candidates: List[Path] = []
    for root in AUTOMATION_LOG_ROOTS:
        if not root.exists():
            continue
        candidates.extend(root.rglob("Log.txt"))
    if not candidates:
        for root in AUTOMATION_LOG_ROOTS:
            if root.exists():
                candidates.extend(root.rglob("*.txt"))
    existing = [path for path in candidates if path.exists()]
    if not existing:
        return None
    existing.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return existing[0]


def _parse_automation_log(path: Path) -> Dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {
            "last_plugin_build_status": "unknown",
            "last_plugin_build_exit_code": None,
            "last_plugin_build_summary": [f"Failed to read AutomationTool log: {exc}"],
            "last_plugin_build_warning_count": 0,
            "last_plugin_build_warning_categories": [],
            "last_plugin_build_warning_preview": [],
            "last_plugin_build_warning_severity": "unknown",
        }
    tail = text[-160000:]
    exit_codes = [int(match.group(1)) for match in re.finditer(r"ExitCode=(-?\d+)", tail)]
    exit_code = exit_codes[-1] if exit_codes else None
    if "BUILD SUCCESSFUL" in tail or exit_code == 0:
        status = "success"
    elif "BUILD FAILED" in tail or (exit_code is not None and exit_code != 0):
        status = "failed"
    else:
        status = "unknown"

    summary = []
    for line in tail.splitlines():
        if any(marker in line for marker in ("BUILD SUCCESSFUL", "BUILD FAILED", "Result:", "AutomationTool exiting with ExitCode", "Took ")):
            summary.append(line.strip())
    warning_lines = _extract_build_warning_lines(tail)
    warning_categories = sorted({_classify_build_warning(line) for line in warning_lines})
    repo_categories = {"deprecated_api", "deprecated_plugin", "monolithic_header", "compiler_warning", "other_warning"}
    if not warning_lines:
        warning_severity = "none"
    elif any(category in repo_categories for category in warning_categories):
        warning_severity = "repo"
    elif set(warning_categories).issubset({"toolchain_preference"}):
        warning_severity = "toolchain"
    else:
        warning_severity = "mixed"
    return {
        "last_plugin_build_status": status,
        "last_plugin_build_exit_code": exit_code,
        "last_plugin_build_summary": summary[-8:],
        "last_plugin_build_warning_count": len(warning_lines),
        "last_plugin_build_warning_categories": warning_categories,
        "last_plugin_build_warning_preview": warning_lines[:8],
        "last_plugin_build_warning_severity": warning_severity,
    }


def _extract_build_warning_lines(text: str) -> List[str]:
    warning_lines: List[str] = []
    seen = set()
    for line in text.splitlines():
        stripped = line.strip()
        lower = stripped.lower()
        if not stripped:
            continue
        is_warning = (
            lower.startswith("warning:")
            or " warning:" in lower
            or "warning c" in lower
            or "not a preferred version" in lower
            or "which was deprecated" in lower
            or "monolithic headers should not be used" in lower
        )
        if not is_warning or "-warningsaserrors" in lower:
            continue
        if stripped in seen:
            continue
        seen.add(stripped)
        warning_lines.append(stripped)
    return warning_lines


def _classify_build_warning(line: str) -> str:
    lower = line.lower()
    if "not a preferred version" in lower or ("visual studio" in lower and "preferred" in lower):
        return "toolchain_preference"
    if "monolithic headers should not be used" in lower:
        return "monolithic_header"
    if "which was deprecated" in lower and "plugin" in lower:
        return "deprecated_plugin"
    if "deprecated" in lower:
        return "deprecated_api"
    if "warning c" in lower:
        return "compiler_warning"
    return "other_warning"


def _policy_row(
    *,
    allowed: bool,
    required_gates: List[str],
    missing_gates: List[str],
    evidence_required: List[str],
) -> Dict[str, Any]:
    return {
        "allowed": allowed,
        "required_gates": required_gates,
        "missing_gates": missing_gates,
        "evidence_required": evidence_required,
    }


def _high_value_wrapper_coverage_status() -> Dict[str, Any]:
    if not HIGH_VALUE_WRAPPER_AUDIT_PATH.exists():
        return {
            "schema": "unreal_mcp_high_value_wrapper_coverage.v1",
            "state": "missing",
            "status": "MISSING",
            "ok": False,
            "audit_tool": "scripts/audit_high_value_wrapper_coverage.py",
            "bridge_registry_tool": "scripts/bridge_command_audit.py",
            "missing_preview": ["scripts/audit_high_value_wrapper_coverage.py"],
            "capability_count": 0,
            "covered_capability_count": 0,
            "failing_capability_count": 1,
            "command_count": 0,
            "schema_command_count": 0,
            "schema_covered_command_count": 0,
            "roadmap_priority_count": 0,
            "roadmap_priority_covered_count": 0,
            "roadmap_priority_missing_count": 1,
            "roadmap_priority_preview": [],
            "roadmap_priority_missing_preview": ["scripts/audit_high_value_wrapper_coverage.py"],
            "operator_command_handoff": [],
            "operator_command_handoff_ids": [],
            "operator_command_handoff_count": 0,
            "network_required": False,
            "spend_required": False,
            "unreal_editor_required": False,
            "requires_bridge": False,
            "no_editor_mutation": True,
            "no_provider_call": True,
            "no_git_mutation": True,
        }

    try:
        module_name = "_unreal_mcp_high_value_wrapper_coverage_preflight"
        spec = importlib.util.spec_from_file_location(module_name, HIGH_VALUE_WRAPPER_AUDIT_PATH)
        if spec is None or spec.loader is None:
            raise RuntimeError("Could not load high-value wrapper coverage audit")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        report = module.build_report()
    except Exception as exc:
        return {
            "schema": "unreal_mcp_high_value_wrapper_coverage.v1",
            "state": "error",
            "status": "ERROR",
            "ok": False,
            "audit_tool": "scripts/audit_high_value_wrapper_coverage.py",
            "bridge_registry_tool": "scripts/bridge_command_audit.py",
            "error": str(exc),
            "capability_count": 0,
            "covered_capability_count": 0,
            "failing_capability_count": 1,
            "command_count": 0,
            "schema_command_count": 0,
            "schema_covered_command_count": 0,
            "roadmap_priority_count": 0,
            "roadmap_priority_covered_count": 0,
            "roadmap_priority_missing_count": 1,
            "roadmap_priority_preview": [],
            "roadmap_priority_missing_preview": ["scripts/audit_high_value_wrapper_coverage.py"],
            "operator_command_handoff": [],
            "operator_command_handoff_ids": [],
            "operator_command_handoff_count": 0,
            "network_required": False,
            "spend_required": False,
            "unreal_editor_required": False,
            "requires_bridge": False,
            "no_editor_mutation": True,
            "no_provider_call": True,
            "no_git_mutation": True,
        }

    capabilities = report.get("capabilities") if isinstance(report.get("capabilities"), list) else []
    failing = [entry for entry in capabilities if isinstance(entry, dict) and not entry.get("ok")]
    commands: List[str] = []
    for capability in capabilities:
        rows = capability.get("commands") if isinstance(capability, dict) and isinstance(capability.get("commands"), list) else []
        for row in rows:
            command = str(row.get("command", "")) if isinstance(row, dict) else ""
            if command and command not in commands:
                commands.append(command)

    schema_command_count = int(report.get("schema_command_count", 0) or 0)
    schema_covered_command_count = int(report.get("schema_covered_command_count", 0) or 0)
    roadmap_priority_count = int(report.get("roadmap_priority_count", len(capabilities)) or 0)
    roadmap_priority_covered_count = int(
        report.get("roadmap_priority_covered_count", max(0, len(capabilities) - len(failing))) or 0
    )
    roadmap_priority_missing_count = int(report.get("roadmap_priority_missing_count", len(failing)) or 0)
    ok = bool(report.get("ok")) and not failing and schema_command_count == schema_covered_command_count
    operator_command_handoff = (
        [item for item in report.get("operator_command_handoff", [])[:3] if isinstance(item, dict)]
        if isinstance(report.get("operator_command_handoff"), list)
        else []
    )
    return {
        "schema": str(report.get("schema", "unreal_mcp_high_value_wrapper_coverage.v1")),
        "state": "ok" if ok else "attention",
        "status": str(report.get("status") or ("OK" if ok else "ATTENTION")),
        "ok": ok,
        "source_scope": str(report.get("source_scope", "")),
        "audit_tool": str(report.get("audit_tool", "scripts/audit_high_value_wrapper_coverage.py")),
        "bridge_registry_tool": str(report.get("bridge_registry_tool", "scripts/bridge_command_audit.py")),
        "capability_count": len(capabilities),
        "covered_capability_count": max(0, len(capabilities) - len(failing)),
        "failing_capability_count": len(failing),
        "failing_capability_preview": [str(entry.get("name", "")) for entry in failing[:8] if isinstance(entry, dict)],
        "command_count": len(commands),
        "schema_command_count": schema_command_count,
        "schema_covered_command_count": schema_covered_command_count,
        "command_preview": sorted(commands)[:12],
        "roadmap_priority_count": roadmap_priority_count,
        "roadmap_priority_covered_count": roadmap_priority_covered_count,
        "roadmap_priority_missing_count": roadmap_priority_missing_count,
        "roadmap_priority_preview": [
            str(item)
            for item in (
                report.get("roadmap_priority_preview")
                if isinstance(report.get("roadmap_priority_preview"), list)
                else [entry.get("name", "") for entry in capabilities if isinstance(entry, dict)]
            )[:12]
        ],
        "roadmap_priority_missing_preview": [
            str(item)
            for item in (
                report.get("roadmap_priority_missing_preview")
                if isinstance(report.get("roadmap_priority_missing_preview"), list)
                else [entry.get("name", "") for entry in failing if isinstance(entry, dict)]
            )[:8]
        ],
        "operator_command_handoff": operator_command_handoff,
        "operator_command_handoff_ids": [str(item.get("id", "")) for item in operator_command_handoff if item.get("id")],
        "operator_command_handoff_count": len(operator_command_handoff),
        "network_required": False,
        "spend_required": False,
        "unreal_editor_required": False,
        "requires_bridge": bool(report.get("requires_bridge", False)),
        "no_editor_mutation": bool(report.get("no_editor_mutation", True)),
        "no_provider_call": bool(report.get("no_provider_call", True)),
        "no_git_mutation": bool(report.get("no_git_mutation", True)),
    }


def _dirty_group_review_guidance(group_name: str, tracked: int, untracked: int) -> Dict[str, Any]:
    base_commands = {
        "unreal_plugin": [
            "python -m unittest unreal_mcp_server.tests.test_c2_chat_panel_core unreal_mcp_server.tests.test_c9_command_palette",
            "python -m unittest unreal_mcp_server.tests.test_phase7_bridge_command_audit unreal_mcp_server.tests.test_phase1_high_value_wrapper_coverage",
            ".\\_build_plugin.bat",
        ],
        "chat_cockpit": [
            "python -m unittest unreal_mcp_server.tests.test_chat unreal_mcp_server.tests.test_c2_chat_panel_core unreal_mcp_server.tests.test_c9_command_palette",
            "python scripts\\audit_ide_companion_readiness.py --json",
        ],
        "server_tools": [
            "python -m unittest unreal_mcp_server.tests.test_phase7_bridge_command_audit unreal_mcp_server.tests.test_phase1_high_value_wrapper_coverage",
            "python scripts\\run_no_mutation_unittest.py",
        ],
        "server_core": [
            "python scripts\\run_no_mutation_unittest.py",
        ],
        "server_skills": [
            "python scripts\\run_no_mutation_unittest.py",
        ],
        "server_tests": [
            "python scripts\\run_no_mutation_unittest.py",
        ],
        "scripts": [
            "python -m unittest unreal_mcp_server.tests.test_phase0_ide_companion_preflight unreal_mcp_server.tests.test_phase0_no_mutation_runner",
            "python scripts\\audit_ide_companion_readiness.py --json",
        ],
        "knowledge_base_docs": [
            "python -m unittest unreal_mcp_server.tests.test_phase0_ci_smoke_docs",
            "python scripts\\audit_ide_companion_readiness.py --json",
        ],
        "project_knowledge": [
            "python scripts\\audit_ide_companion_readiness.py --json",
            "python scripts\\run_no_mutation_unittest.py",
        ],
        "agent_config": [
            "python scripts\\audit_ide_companion_readiness.py --json",
        ],
        "workspace_dependencies": [
            "python scripts\\audit_test_lanes.py",
            "python scripts\\audit_ide_companion_readiness.py --json",
        ],
        "repo_docs": [
            "python -m unittest unreal_mcp_server.tests.test_phase0_ci_smoke_docs",
        ],
        "repo_root": [
            "python scripts\\audit_ide_companion_readiness.py --json",
        ],
        "project_notes": [
            "python scripts\\audit_ide_companion_readiness.py --json",
        ],
        "local_artifacts": [
            "python scripts\\audit_ide_companion_readiness.py --json",
        ],
    }
    commands = base_commands.get(group_name, ["python scripts\\audit_ide_companion_readiness.py --json"])
    approval_evidence = [
        "owner_or_source",
        "promotion_intent",
        "focused_test_results",
        "human_approval_before_stage_commit_merge",
    ]
    if untracked:
        approval_evidence.append("artifact_policy_decision")
    if tracked:
        approval_evidence.append("tracked_diff_review")
    scope = "tracked_review" if tracked else "artifact_review"
    if group_name == "local_artifacts":
        scope = "local_artifact_exclusion_review"
    decision_prompts = [
        f"owner_or_source: identify who created or owns the {group_name} dirty group.",
        "promotion_intent: choose promote_now, keep_wip, split_batch, or exclude_artifact.",
        "focused_test_results: paste the result of the listed focused test command(s).",
        "human_approval_before_stage_commit_merge: record explicit approval before any Git mutation.",
    ]
    if untracked:
        decision_prompts.append("artifact_policy_decision: classify untracked files as promote, ignore, archive, or delete later by human request.")
    if tracked:
        decision_prompts.append("tracked_diff_review: summarize tracked diffs and why they belong in this promotion batch.")
    return {
        "candidate_batch_scope": scope,
        "focused_test_commands": commands,
        "focused_test_command_count": len(commands),
        "decision_prompts": decision_prompts,
        "decision_prompt_count": len(decision_prompts),
        "approval_evidence_required": approval_evidence,
        "approval_evidence_count": len(approval_evidence),
        "promotion_allowed_after_receipt": False,
        "stage_policy": "do_not_stage_from_receipt; require explicit human approval after owner/source, intent, and focused-test evidence",
    }


def _dirty_batch_evidence_matrix(review_batches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    matrix: List[Dict[str, Any]] = []
    for batch in review_batches:
        group_name = str(batch.get("group", ""))
        tracked = int(batch.get("tracked_count", 0) or 0)
        untracked = int(batch.get("untracked_count", 0) or 0)
        required = list(batch.get("approval_evidence_required", [])) if isinstance(batch.get("approval_evidence_required"), list) else []
        missing = [str(item) for item in required if str(item).strip()]
        matrix.append({
            "order": int(batch.get("order", 0) or 0),
            "group": group_name,
            "candidate_batch_scope": str(batch.get("candidate_batch_scope", "")),
            "tracked_count": tracked,
            "untracked_count": untracked,
            "required_evidence": missing,
            "missing_evidence": missing,
            "missing_evidence_count": len(missing),
            "decision_prompts": list(batch.get("decision_prompts", []))[:8] if isinstance(batch.get("decision_prompts"), list) else [],
            "decision_prompt_count": int(batch.get("decision_prompt_count", 0) or 0),
            "owner_or_source_recorded": False,
            "promotion_intent_recorded": False,
            "artifact_policy_required": bool(untracked),
            "artifact_policy_recorded": False,
            "tracked_diff_review_required": bool(tracked),
            "tracked_diff_review_recorded": False,
            "focused_tests_recorded": False,
            "human_approval_recorded": False,
            "promotion_allowed": False,
            "promotion_blocked_reason": (
                "local artifacts must be explicitly excluded or separately approved"
                if group_name == "local_artifacts"
                else "missing owner/source, intent, focused-test output, and explicit human approval"
            ),
        })
    return matrix


def _dirty_target_receipt_command_template(
    group_name: str,
    tracked_count: int,
    untracked_count: int,
    *,
    include_human_approval: bool = False,
) -> str:
    target_label = group_name or "target_dirty_group"
    parts = [
        "python scripts\\write_dirty_promotion_review.py",
        f'--target-owner-or-source "<owner/source for {target_label}>"',
        '--target-promotion-intent "<promote_now|keep_wip|split_batch|exclude_artifact>"',
        '--target-focused-test-results "<focused test command output summary>"',
    ]
    if untracked_count:
        parts.append('--target-artifact-policy-decision "<promote|ignore|archive|exclude generated artifacts>"')
    if tracked_count:
        parts.append('--target-tracked-diff-review "<tracked diff summary and why it belongs>"')
    if include_human_approval:
        parts.append("--target-human-approval-recorded")
        parts.append('--target-human-approval-summary "<explicit human approval summary>"')
    else:
        parts.append('--target-human-approval-summary "<pending; omit approval flag until explicit approval>"')
    return " ".join(parts)


def _dirty_target_operator_command_handoff(
    group_name: str,
    tracked_count: int,
    untracked_count: int,
) -> List[Dict[str, Any]]:
    base_command = _dirty_target_receipt_command_template(
        group_name,
        tracked_count,
        untracked_count,
        include_human_approval=False,
    )
    approval_command = _dirty_target_receipt_command_template(
        group_name,
        tracked_count,
        untracked_count,
        include_human_approval=True,
    )
    target_label = group_name or "target_dirty_group"
    return [
        {
            "id": "record_dirty_target_evidence",
            "label": f"Record evidence for {target_label}",
            "command": base_command,
            "command_kind": "local_receipt",
            "receipt_path": "Saved\\DirtyPromotionReview\\last_review_receipt.json",
            "requires_human_approval": False,
            "approval_flag_included": False,
            "records_evidence_only": True,
            "no_git_mutation": True,
            "no_stage": True,
            "no_commit": True,
            "no_branch_or_merge": True,
            "no_editor_mutation": True,
            "no_provider_call": True,
        },
        {
            "id": "record_dirty_target_human_approval",
            "label": f"Record explicit approval for {target_label}",
            "command": approval_command,
            "command_kind": "local_receipt",
            "receipt_path": "Saved\\DirtyPromotionReview\\last_review_receipt.json",
            "requires_human_approval": True,
            "approval_flag_included": True,
            "records_evidence_only": True,
            "no_git_mutation": True,
            "no_stage": True,
            "no_commit": True,
            "no_branch_or_merge": True,
            "no_editor_mutation": True,
            "no_provider_call": True,
        },
    ]


def _dirty_target_focused_test_command_handoff(
    group_name: str,
    focused_test_commands: List[str],
) -> List[Dict[str, Any]]:
    target_label = group_name or "target_dirty_group"
    handoff: List[Dict[str, Any]] = []
    for index, command in enumerate(focused_test_commands[:5], start=1):
        command_text = str(command).strip()
        if not command_text:
            continue
        handoff.append({
            "id": f"run_dirty_target_focused_test_{index}",
            "label": f"Run focused test {index} for {target_label}",
            "command": command_text,
            "command_kind": "local_validation",
            "target_group": target_label,
            "produces_evidence_for": "target_focused_test_results",
            "records_evidence_only": False,
            "requires_human_review": True,
            "no_git_mutation": True,
            "no_stage": True,
            "no_commit": True,
            "no_clean": True,
            "no_delete": True,
            "no_branch_or_merge": True,
            "no_editor_mutation": True,
            "no_provider_call": True,
            "no_spend": True,
        })
    return handoff


def _dirty_promotion_contract(git: Dict[str, Any]) -> Dict[str, Any]:
    dirty_groups = git.get("dirty_groups") if isinstance(git.get("dirty_groups"), list) else []
    tracked_change_count = int(git.get("tracked_change_count", 0) or 0)
    untracked_count = int(git.get("untracked_count", 0) or 0)
    dirty_risk = str(git.get("dirty_risk", "unknown"))
    grouping_required = bool(git.get("dirty_grouping_required", False))
    ready = not grouping_required and tracked_change_count == 0 and dirty_risk in {"clean", "low"}
    review_batches: List[Dict[str, Any]] = []
    for index, group in enumerate(dirty_groups[:8], start=1):
        if not isinstance(group, dict):
            continue
        tracked = int(group.get("tracked_count", 0) or 0)
        untracked = int(group.get("untracked_count", 0) or 0)
        guidance = _dirty_group_review_guidance(str(group.get("group", "")), tracked, untracked)
        review_batches.append({
            "order": index,
            "group": str(group.get("group", "")),
            "count": int(group.get("count", 0) or 0),
            "tracked_count": tracked,
            "untracked_count": untracked,
            "status_counts": group.get("status_counts", {}) if isinstance(group.get("status_counts"), dict) else {},
            "sample": list(group.get("sample", []))[:3] if isinstance(group.get("sample"), list) else [],
            "promotion_batch": "tracked_review" if tracked else "artifact_review",
            "recommended_review": (
                "classify tracked edits before promotion"
                if tracked
                else "classify untracked artifacts before promotion"
            ),
            **guidance,
        })
    receipt = _dirty_promotion_review_receipt_status(current_git=git)
    focused_test_commands = sorted({
        str(command)
        for batch in review_batches
        for command in (batch.get("focused_test_commands") if isinstance(batch.get("focused_test_commands"), list) else [])
        if str(command).strip()
    })
    evidence_matrix = _dirty_batch_evidence_matrix(review_batches)
    unresolved_evidence_count = sum(int(item.get("missing_evidence_count", 0) or 0) for item in evidence_matrix)
    target_review_batch = next((item for item in review_batches if isinstance(item, dict)), {})
    target_review_gap = next((item for item in evidence_matrix if isinstance(item, dict)), {})
    target_missing_evidence = (
        target_review_gap.get("missing_evidence")
        if isinstance(target_review_gap.get("missing_evidence"), list)
        else []
    )
    receipt_current = bool(receipt.get("dirty_signature_match", False))
    receipt_target_group = str(receipt.get("target_review_group", "")).strip() if receipt_current else ""
    receipt_target_order = int(receipt.get("target_review_order", 0) or 0) if receipt_current else 0
    receipt_target_scope = str(receipt.get("target_review_scope", "")).strip() if receipt_current else ""
    target_group_name = receipt_target_group or str(target_review_batch.get("group") or target_review_gap.get("group") or "")
    target_tracked_count = (
        int(receipt.get("target_review_tracked_count", 0) or 0)
        if receipt_current and receipt.get("target_review_group")
        else int(target_review_batch.get("tracked_count", target_review_gap.get("tracked_count", 0)) or 0)
    )
    target_untracked_count = (
        int(receipt.get("target_review_untracked_count", 0) or 0)
        if receipt_current and receipt.get("target_review_group")
        else int(target_review_batch.get("untracked_count", target_review_gap.get("untracked_count", 0)) or 0)
    )
    target_receipt_command_template = _dirty_target_receipt_command_template(
        target_group_name,
        target_tracked_count,
        target_untracked_count,
        include_human_approval=False,
    )
    target_approval_receipt_command_template = _dirty_target_receipt_command_template(
        target_group_name,
        target_tracked_count,
        target_untracked_count,
        include_human_approval=True,
    )
    target_operator_command_handoff = _dirty_target_operator_command_handoff(
        target_group_name,
        target_tracked_count,
        target_untracked_count,
    )
    target_focused_test_commands = (
        [str(command) for command in list(target_review_batch.get("focused_test_commands", []))[:5]]
        if isinstance(target_review_batch.get("focused_test_commands"), list)
        else []
    )
    target_focused_test_command_handoff = _dirty_target_focused_test_command_handoff(
        target_group_name,
        target_focused_test_commands,
    )
    target_missing_evidence_current = (
        list(receipt.get("target_review_missing_evidence_preview", []))[:8]
        if receipt_current and isinstance(receipt.get("target_review_missing_evidence_preview"), list) and receipt.get("target_review_group")
        else list(target_missing_evidence)[:8]
    )
    target_human_approval_recorded = (
        bool(receipt.get("target_review_human_approval_recorded", False))
        if receipt_current and receipt.get("target_review_group")
        else False
    )
    target_pending_human_approval_only = bool(
        target_missing_evidence_current == ["human_approval_before_stage_commit_merge"]
        and not target_human_approval_recorded
    )
    target_human_approval_command_handoff = [
        item
        for item in target_operator_command_handoff
        if isinstance(item, dict) and item.get("id") == "record_dirty_target_human_approval"
    ][:1]

    return {
        "schema": "unreal_mcp_dirty_promotion_contract.v1",
        "state": "ready" if ready else "needs_grouping",
        "ready_for_promotion": ready,
        "dirty_risk": dirty_risk,
        "dirty_count": int(git.get("dirty_count", 0) or 0),
        "dirty_signature": str(git.get("dirty_signature", "")),
        "dirty_signature_algorithm": str(git.get("dirty_signature_algorithm", "")),
        "dirty_signature_entry_count": int(git.get("dirty_signature_entry_count", 0) or 0),
        "tracked_change_count": tracked_change_count,
        "untracked_count": untracked_count,
        "dirty_group_count": int(git.get("dirty_group_count", len(dirty_groups)) or 0),
        "primary_dirty_group": str(git.get("primary_dirty_group", "")),
        "grouping_required": grouping_required,
        "review_batch_count": len(review_batches),
        "review_batches": review_batches,
        "evidence_review_matrix": evidence_matrix,
        "evidence_review_matrix_count": len(evidence_matrix),
        "evidence_unresolved_count": unresolved_evidence_count,
        "evidence_review_policy": "A dirty-promotion receipt records the review target only; every batch remains blocked until its matrix has owner/source, intent, focused tests, artifact/tracked-diff decisions, and explicit human approval.",
        "focused_test_command_count": len(focused_test_commands),
        "focused_test_command_preview": focused_test_commands[:8],
        "candidate_batch_review_policy": "Each dirty group needs owner/source, promotion intent, focused-test output, artifact policy decision when untracked files are present, and explicit human approval before any staging or main-promotion step.",
        "review_receipt": receipt,
        "review_receipt_exists": bool(receipt.get("receipt_exists", False)),
        "review_receipt_state": str(receipt.get("state", "missing")),
        "review_receipt_current": bool(receipt.get("dirty_signature_match", False)),
        "review_receipt_stale": bool(receipt.get("state", "") == "stale"),
        "review_receipt_dirty_signature": str(receipt.get("dirty_signature", "")),
        "review_receipt_dirty_signature_match": bool(receipt.get("dirty_signature_match", False)),
        "review_receipt_path": str(receipt.get("path", "Saved\\DirtyPromotionReview\\last_review_receipt.json")),
        "review_receipt_required_command": "python scripts\\write_dirty_promotion_review.py",
        "target_review_group": target_group_name,
        "target_review_order": receipt_target_order or int(target_review_batch.get("order", target_review_gap.get("order", 0)) or 0),
        "target_review_scope": receipt_target_scope or str(target_review_batch.get("candidate_batch_scope") or target_review_gap.get("candidate_batch_scope") or ""),
        "target_review_tracked_count": (
            int(receipt.get("target_review_tracked_count", 0) or 0)
            if receipt_current and receipt.get("target_review_group")
            else int(target_review_batch.get("tracked_count", target_review_gap.get("tracked_count", 0)) or 0)
        ),
        "target_review_untracked_count": (
            int(receipt.get("target_review_untracked_count", 0) or 0)
            if receipt_current and receipt.get("target_review_group")
            else int(target_review_batch.get("untracked_count", target_review_gap.get("untracked_count", 0)) or 0)
        ),
        "target_review_missing_evidence_count": (
            int(receipt.get("target_review_missing_evidence_count", 0) or 0)
            if receipt_current and receipt.get("target_review_group")
            else int(target_review_gap.get("missing_evidence_count", len(target_missing_evidence)) or 0)
        ),
        "target_review_missing_evidence_preview": (
            target_missing_evidence_current
        ),
        "target_review_required_evidence_preview": (
            list(receipt.get("target_review_required_evidence_preview", []))[:8]
            if receipt_current and isinstance(receipt.get("target_review_required_evidence_preview"), list) and receipt.get("target_review_group")
            else (
                list(target_review_gap.get("required_evidence", []))[:8]
                if isinstance(target_review_gap.get("required_evidence"), list)
                else []
            )
        ),
        "target_review_decision_prompt_preview": (
            list(receipt.get("target_review_decision_prompt_preview", []))[:8]
            if receipt_current and isinstance(receipt.get("target_review_decision_prompt_preview"), list) and receipt.get("target_review_group")
            else (
                list(target_review_batch.get("decision_prompts", []))[:8]
                if isinstance(target_review_batch.get("decision_prompts"), list)
                else []
            )
        ),
        "target_review_receipt_command_template": target_receipt_command_template,
        "target_review_approval_receipt_command_template": target_approval_receipt_command_template,
        "target_review_receipt_command_policy": "Use the base template for partial evidence; add --target-human-approval-recorded only after explicit human approval.",
        "target_review_operator_command_handoff": target_operator_command_handoff,
        "target_review_pending_human_approval_only": target_pending_human_approval_only,
        "target_review_human_approval_gate": "human_approval_before_stage_commit_merge",
        "target_review_human_approval_command_handoff": target_human_approval_command_handoff,
        "target_review_focused_test_command_handoff": target_focused_test_command_handoff,
        "target_review_status": (
            str(receipt.get("target_review_status") or "missing_evidence")
            if receipt_current and receipt.get("target_review_group")
            else "missing_evidence"
        ),
        "target_review_evidence_complete": (
            bool(receipt.get("target_review_evidence_complete", False))
            if receipt_current and receipt.get("target_review_group")
            else False
        ),
        "target_review_recorded_evidence_count": (
            int(receipt.get("target_review_recorded_evidence_count", 0) or 0)
            if receipt_current and receipt.get("target_review_group")
            else 0
        ),
        "target_review_recorded_evidence_preview": (
            list(receipt.get("target_review_recorded_evidence_preview", []))[:8]
            if receipt_current and isinstance(receipt.get("target_review_recorded_evidence_preview"), list) and receipt.get("target_review_group")
            else []
        ),
        "target_review_owner_or_source": (
            str(receipt.get("target_review_owner_or_source", ""))
            if receipt_current and receipt.get("target_review_group")
            else ""
        ),
        "target_review_promotion_intent": (
            str(receipt.get("target_review_promotion_intent", ""))
            if receipt_current and receipt.get("target_review_group")
            else ""
        ),
        "target_review_focused_test_results": (
            str(receipt.get("target_review_focused_test_results", ""))
            if receipt_current and receipt.get("target_review_group")
            else ""
        ),
        "target_review_artifact_policy_decision": (
            str(receipt.get("target_review_artifact_policy_decision", ""))
            if receipt_current and receipt.get("target_review_group")
            else ""
        ),
        "target_review_tracked_diff_review": (
            str(receipt.get("target_review_tracked_diff_review", ""))
            if receipt_current and receipt.get("target_review_group")
            else ""
        ),
        "target_review_human_approval_recorded": (
            target_human_approval_recorded
        ),
        "target_review_human_approval_summary": (
            str(receipt.get("target_review_human_approval_summary", ""))
            if receipt_current and receipt.get("target_review_group")
            else ""
        ),
        "target_review_focused_test_command_count": (
            int(receipt.get("target_review_focused_test_command_count", 0) or 0)
            if receipt_current and receipt.get("target_review_group")
            else int(target_review_batch.get("focused_test_command_count", 0) or 0)
        ),
        "target_review_focused_test_command_preview": (
            list(receipt.get("target_review_focused_test_command_preview", []))[:5]
            if receipt_current and isinstance(receipt.get("target_review_focused_test_command_preview"), list) and receipt.get("target_review_group")
            else (
                list(target_review_batch.get("focused_test_commands", []))[:5]
                if isinstance(target_review_batch.get("focused_test_commands"), list)
                else []
            )
        ),
        "target_review_sample_preview": (
            list(receipt.get("target_review_sample_preview", []))[:5]
            if receipt_current and isinstance(receipt.get("target_review_sample_preview"), list) and receipt.get("target_review_group")
            else (
                list(target_review_batch.get("sample", []))[:5]
                if isinstance(target_review_batch.get("sample"), list)
                else []
            )
        ),
        "target_review_promotion_allowed_after_receipt": (
            bool(receipt.get("target_review_promotion_allowed_after_receipt", False))
            if receipt_current and receipt.get("target_review_group")
            else bool(target_review_batch.get("promotion_allowed_after_receipt", False))
        ),
        "target_review_merge_policy": (
            str(receipt.get("target_review_merge_policy", "preserve_existing_evidence_when_dirty_signature_and_target_match"))
            if receipt_current and receipt.get("target_review_group")
            else "preserve_existing_evidence_when_dirty_signature_and_target_match"
        ),
        "target_review_previous_evidence_merged": (
            bool(receipt.get("target_review_previous_evidence_merged", False))
            if receipt_current and receipt.get("target_review_group")
            else False
        ),
        "target_review_reset_evidence": (
            bool(receipt.get("target_review_reset_evidence", False))
            if receipt_current and receipt.get("target_review_group")
            else False
        ),
        "target_review_source": "current_review_receipt" if receipt_current and receipt.get("target_review_group") else "current_dirty_worktree",
        "required_evidence": [
            "dirty_promotion_review_receipt",
            "owner_or_source_for_each_dirty_group",
            "promotion_intent_for_each_tracked_group",
            "artifact_policy_for_each_untracked_group",
            "focused_tests_for_groups_promoted_together",
            "promotion_evidence_matrix_for_each_candidate_batch",
            "dirty_promotion_receipt_matches_current_worktree",
            "human_review_before_stage_commit_or_merge",
        ],
        "promotion_batch_policy": "Review one coherent dirty group at a time; tracked groups require owner/source, promotion intent, and focused tests before they are staged together.",
        "artifact_policy": "Keep Saved/, .mcp_artifacts/, generated_audio/, .tmp_*, build outputs, and other generated/local artifacts out of promotion unless a human explicitly approves them.",
        "safe_promotion_next_steps": [
            "write_dirty_promotion_review_receipt",
            "rerun_dirty_promotion_review_if_receipt_stale",
            "assign_owner_or_source_for_each_dirty_group",
            "separate_generated_or_local_artifacts_from_tracked_work",
            "run_focused_tests_for_each_candidate_batch",
            "request_explicit_human_approval_before_stage_commit_merge_or_main_promotion",
        ],
        "recommended_next": (
            "review_dirty_groups_for_promotion"
            if grouping_required
            else "dirty_state_grouped_or_clean"
        ),
        "promotion_policy": "Keep work on wip; move toward main only after dirty groups are reviewed and evidence proves the promoted set is stable.",
        "no_git_mutation": True,
        "no_stage": True,
        "no_commit": True,
        "no_clean": True,
        "no_delete": True,
        "no_branch_or_merge": True,
        "no_provider_call": True,
        "no_editor_mutation": True,
        "network_required": False,
        "spend_required": False,
        "unreal_editor_required": False,
    }


def _dirty_promotion_review_receipt_status(
    path: Path = DIRTY_PROMOTION_REVIEW_RECEIPT_PATH,
    current_git: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    display_path = "Saved\\DirtyPromotionReview\\last_review_receipt.json"
    base = {
        "schema": "unreal_mcp_dirty_promotion_review_receipt.v1",
        "path": display_path,
        "receipt_exists": path.exists(),
        "required_command": "python scripts\\write_dirty_promotion_review.py",
        "network_required": False,
        "spend_required": False,
        "unreal_editor_required": False,
        "no_git_mutation": True,
        "no_stage": True,
        "no_commit": True,
        "no_clean": True,
        "no_delete": True,
        "no_branch_or_merge": True,
        "no_provider_call": True,
        "no_editor_mutation": True,
    }
    if not path.exists():
        return {
            **base,
            "state": "missing",
            "status": "missing",
            "dirty_group_count": None,
            "dirty_signature": "",
            "dirty_signature_algorithm": "",
            "dirty_signature_entry_count": 0,
            "current_dirty_signature": str(current_git.get("dirty_signature", "")) if isinstance(current_git, dict) else "",
            "dirty_signature_match": False,
            "dirty_signature_check": "missing_receipt",
            "tracked_change_count": None,
            "review_batch_count": None,
            "promotion_batch_policy": "",
            "artifact_policy": "",
            "safe_promotion_next_steps": [],
            "evidence_review_matrix": [],
            "evidence_review_matrix_count": 0,
            "evidence_unresolved_count": None,
            "evidence_review_policy": "",
            "target_review_group": "",
            "target_review_order": 0,
            "target_review_scope": "",
            "target_review_tracked_count": 0,
            "target_review_untracked_count": 0,
            "target_review_missing_evidence_count": 0,
            "target_review_missing_evidence_preview": [],
            "target_review_required_evidence_preview": [],
            "target_review_receipt_command_template": "",
            "target_review_approval_receipt_command_template": "",
            "target_review_receipt_command_policy": "",
            "target_review_operator_command_handoff": [],
            "target_review_pending_human_approval_only": False,
            "target_review_human_approval_gate": "human_approval_before_stage_commit_merge",
            "target_review_human_approval_command_handoff": [],
            "target_review_focused_test_command_handoff": [],
            "target_review_status": "",
            "target_review_evidence_complete": False,
            "target_review_recorded_evidence_count": 0,
            "target_review_recorded_evidence_preview": [],
            "target_review_owner_or_source": "",
            "target_review_promotion_intent": "",
            "target_review_focused_test_results": "",
            "target_review_artifact_policy_decision": "",
            "target_review_tracked_diff_review": "",
            "target_review_human_approval_recorded": False,
            "target_review_human_approval_summary": "",
            "target_review_focused_test_command_count": 0,
            "target_review_focused_test_command_preview": [],
            "target_review_sample_preview": [],
            "target_review_promotion_allowed_after_receipt": False,
        }
    parsed = _load_json(path)
    status = str(parsed.get("status", "unknown"))
    schema = str(parsed.get("schema", ""))
    schema_ok = schema == "unreal_mcp_dirty_promotion_review_receipt.v1"
    receipt_signature = str(parsed.get("dirty_signature", ""))
    current_signature = str(current_git.get("dirty_signature", "")) if isinstance(current_git, dict) else ""
    signature_check = "not_checked"
    signature_match = False
    if current_signature and receipt_signature:
        signature_match = current_signature == receipt_signature
        signature_check = "match" if signature_match else "mismatch"
    elif current_signature:
        signature_check = "missing_receipt_signature"
    if status == "ready" and schema_ok:
        state = "ready"
    elif status == "review_required" and schema_ok:
        state = "review_required"
    else:
        state = "blocked"
    if schema_ok and current_signature and not signature_match:
        state = "stale"
    return {
        **base,
        "schema": schema or base["schema"],
        "state": state,
        "status": status,
        "generated_at_utc": str(parsed.get("generated_at_utc", "")),
        "dirty_risk": str(parsed.get("dirty_risk", "")),
        "dirty_group_count": parsed.get("dirty_group_count"),
        "dirty_signature": receipt_signature,
        "dirty_signature_algorithm": str(parsed.get("dirty_signature_algorithm", "")),
        "dirty_signature_entry_count": int(parsed.get("dirty_signature_entry_count", 0) or 0),
        "current_dirty_signature": current_signature,
        "dirty_signature_match": signature_match,
        "dirty_signature_check": signature_check,
        "tracked_change_count": parsed.get("tracked_change_count"),
        "untracked_count": parsed.get("untracked_count"),
        "review_batch_count": parsed.get("review_batch_count"),
        "primary_dirty_group": str(parsed.get("primary_dirty_group", "")),
        "evidence_review_matrix": list(parsed.get("evidence_review_matrix", []))[:8] if isinstance(parsed.get("evidence_review_matrix"), list) else [],
        "evidence_review_matrix_count": parsed.get("evidence_review_matrix_count"),
        "evidence_unresolved_count": parsed.get("evidence_unresolved_count"),
        "evidence_review_policy": str(parsed.get("evidence_review_policy", "")),
        "target_review_group": str(parsed.get("target_review_group", "")),
        "target_review_order": int(parsed.get("target_review_order", 0) or 0),
        "target_review_scope": str(parsed.get("target_review_scope", "")),
        "target_review_tracked_count": int(parsed.get("target_review_tracked_count", 0) or 0),
        "target_review_untracked_count": int(parsed.get("target_review_untracked_count", 0) or 0),
        "target_review_missing_evidence_count": int(parsed.get("target_review_missing_evidence_count", 0) or 0),
        "target_review_missing_evidence_preview": list(parsed.get("target_review_missing_evidence_preview", []))[:8] if isinstance(parsed.get("target_review_missing_evidence_preview"), list) else [],
        "target_review_required_evidence_preview": list(parsed.get("target_review_required_evidence_preview", []))[:8] if isinstance(parsed.get("target_review_required_evidence_preview"), list) else [],
        "target_review_decision_prompt_preview": list(parsed.get("target_review_decision_prompt_preview", []))[:8] if isinstance(parsed.get("target_review_decision_prompt_preview"), list) else [],
        "target_review_receipt_command_template": str(parsed.get("target_review_receipt_command_template", "")),
        "target_review_approval_receipt_command_template": str(parsed.get("target_review_approval_receipt_command_template", "")),
        "target_review_receipt_command_policy": str(parsed.get("target_review_receipt_command_policy", "")),
        "target_review_operator_command_handoff": (
            list(parsed.get("target_review_operator_command_handoff", []))[:2]
            if isinstance(parsed.get("target_review_operator_command_handoff"), list)
            else []
        ),
        "target_review_pending_human_approval_only": bool(parsed.get("target_review_pending_human_approval_only", False)),
        "target_review_human_approval_gate": str(parsed.get("target_review_human_approval_gate", "human_approval_before_stage_commit_merge")),
        "target_review_human_approval_command_handoff": (
            list(parsed.get("target_review_human_approval_command_handoff", []))[:1]
            if isinstance(parsed.get("target_review_human_approval_command_handoff"), list)
            else []
        ),
        "target_review_focused_test_command_handoff": (
            list(parsed.get("target_review_focused_test_command_handoff", []))[:5]
            if isinstance(parsed.get("target_review_focused_test_command_handoff"), list)
            else []
        ),
        "target_review_status": str(parsed.get("target_review_status") or "missing_evidence"),
        "target_review_evidence_complete": bool(parsed.get("target_review_evidence_complete", False)),
        "target_review_recorded_evidence_count": int(parsed.get("target_review_recorded_evidence_count", 0) or 0),
        "target_review_recorded_evidence_preview": list(parsed.get("target_review_recorded_evidence_preview", []))[:8] if isinstance(parsed.get("target_review_recorded_evidence_preview"), list) else [],
        "target_review_owner_or_source": str(parsed.get("target_review_owner_or_source", "")),
        "target_review_promotion_intent": str(parsed.get("target_review_promotion_intent", "")),
        "target_review_focused_test_results": str(parsed.get("target_review_focused_test_results", "")),
        "target_review_artifact_policy_decision": str(parsed.get("target_review_artifact_policy_decision", "")),
        "target_review_tracked_diff_review": str(parsed.get("target_review_tracked_diff_review", "")),
        "target_review_human_approval_recorded": bool(parsed.get("target_review_human_approval_recorded", False)),
        "target_review_human_approval_summary": str(parsed.get("target_review_human_approval_summary", "")),
        "target_review_focused_test_command_count": int(parsed.get("target_review_focused_test_command_count", 0) or 0),
        "target_review_focused_test_command_preview": list(parsed.get("target_review_focused_test_command_preview", []))[:5] if isinstance(parsed.get("target_review_focused_test_command_preview"), list) else [],
        "target_review_sample_preview": list(parsed.get("target_review_sample_preview", []))[:5] if isinstance(parsed.get("target_review_sample_preview"), list) else [],
        "target_review_promotion_allowed_after_receipt": bool(parsed.get("target_review_promotion_allowed_after_receipt", False)),
        "target_review_merge_policy": str(parsed.get("target_review_merge_policy", "preserve_existing_evidence_when_dirty_signature_and_target_match")),
        "target_review_previous_evidence_merged": bool(parsed.get("target_review_previous_evidence_merged", False)),
        "target_review_reset_evidence": bool(parsed.get("target_review_reset_evidence", False)),
        "promotion_batch_policy": str(parsed.get("promotion_batch_policy", "")),
        "artifact_policy": str(parsed.get("artifact_policy", "")),
        "safe_promotion_next_steps": list(parsed.get("safe_promotion_next_steps", []))[:8] if isinstance(parsed.get("safe_promotion_next_steps"), list) else [],
        "ready_for_promotion": bool(parsed.get("ready_for_promotion", False)),
    }


def _platform_stability_review_receipt_status(path: Path = PLATFORM_STABILITY_REVIEW_RECEIPT_PATH) -> Dict[str, Any]:
    display_path = "Saved\\PlatformStabilityReview\\last_review_receipt.json"
    base = {
        "schema": "unreal_mcp_platform_stability_review_receipt.v1",
        "path": display_path,
        "receipt_exists": path.exists(),
        "required_command": "python scripts\\write_platform_stability_review.py",
        "network_required": False,
        "spend_required": False,
        "unreal_editor_required": False,
        "no_raw_key": True,
        "no_provider_call": True,
        "no_wallet_check": True,
        "no_credit_reservation": True,
        "no_spend_confirmation": True,
        "no_editor_mutation": True,
        "no_git_mutation": True,
        "no_stage": True,
        "no_commit": True,
    }
    if not path.exists():
        return {
            **base,
            "state": "missing",
            "status": "missing",
            "ready_for_platform_stability": False,
            "ready_for_wip_promotion": False,
            "tool_count": 0,
            "recorded_tool_count": 0,
            "partial_tool_count": 0,
            "dirty_promotion_review_batch_count": 0,
            "dirty_promotion_review_receipt_current": False,
            "dirty_promotion_review_receipt_stale": False,
            "dirty_promotion_review_receipt_signature_match": False,
            "dirty_signature_algorithm": "",
            "dirty_signature_entry_count": 0,
            "dirty_promotion_evidence_unresolved_count": 0,
            "dirty_target_review_group": "",
            "dirty_target_review_order": 0,
            "dirty_target_review_scope": "",
            "dirty_target_review_tracked_count": 0,
            "dirty_target_review_untracked_count": 0,
            "dirty_target_review_status": "",
            "dirty_target_review_evidence_complete": False,
            "dirty_target_review_recorded_evidence_count": 0,
            "dirty_target_review_recorded_evidence_preview": [],
            "dirty_target_review_human_approval_recorded": False,
            "dirty_target_review_missing_evidence_count": 0,
            "dirty_target_review_missing_evidence_preview": [],
            "dirty_target_review_pending_human_approval_only": False,
            "dirty_target_review_human_approval_gate": "human_approval_before_stage_commit_merge",
            "dirty_target_review_human_approval_command_handoff": [],
            "dirty_target_review_focused_test_command_handoff": [],
            "dirty_target_review_focused_test_command_count": 0,
            "dirty_target_review_focused_test_command_preview": [],
            "dirty_target_review_sample_preview": [],
            "dirty_target_review_promotion_allowed_after_receipt": False,
            "dirty_target_review_merge_policy": "preserve_existing_evidence_when_dirty_signature_and_target_match",
            "dirty_target_review_previous_evidence_merged": False,
            "dirty_target_review_reset_evidence": False,
            "blocking_gate_count": 0,
            "blocking_gate_preview": [],
            "readiness_repair_action_count": 0,
            "readiness_repair_recommended_next": "none",
            "readiness_repair_next_gate": "",
            "readiness_repair_next_policy_area": "",
            "readiness_repair_next_tool": "",
            "readiness_repair_next_requires_bridge": False,
            "readiness_repair_next_requires_network": False,
            "readiness_repair_next_requires_spend": False,
            "readiness_repair_action_preview": [],
            "paid_generation_evidence_receipt_state": "missing",
            "paid_generation_evidence_receipt_path": "Saved\\PaidGenerationEvidence\\last_review_receipt.json",
            "paid_generation_evidence_required_command": "python scripts\\write_paid_generation_evidence_review.py",
            "paid_generation_wallet_evidence_recorded": False,
            "paid_generation_mesh_wallet_evidence_recorded": False,
            "paid_generation_animation_allowance_evidence_recorded": False,
            "paid_generation_spend_confirmation_recorded": False,
            "paid_generation_explicit_spend_approval_recorded": False,
            "paid_generation_explicit_usage_approval_recorded": False,
            "paid_generation_estimated_spend_reviewed": False,
            "paid_generation_estimated_motion_seconds_reviewed": False,
            "paid_generation_mesh_provider": "tripo",
            "paid_generation_animation_provider": "uthana",
            "paid_generation_operator_command_handoff": [],
            "provider_config_operator_command_handoff": [],
            "provider_config_operator_command_handoff_ids": [],
            "provider_config_operator_command_handoff_count": 0,
            "blueprint_mutation_evidence_receipt_state": "missing",
            "blueprint_mutation_evidence_receipt_status": "missing",
            "blueprint_mutation_evidence_receipt_path": "Saved\\BlueprintMutationEvidence\\last_review_receipt.json",
            "blueprint_mutation_evidence_required_command": "python scripts\\write_blueprint_mutation_evidence_review.py",
            "blueprint_mutation_operator_command_handoff": [],
            "blueprint_mutation_pre_read_evidence_recorded": False,
            "blueprint_mutation_compile_plan_recorded": False,
            "blueprint_mutation_readback_plan_recorded": False,
            "blueprint_mutation_target_blueprint_path": "",
            "blueprint_mutation_intended_summary": "",
            "blueprint_mutation_pre_read_summary": "",
            "blueprint_mutation_compile_plan_summary": "",
            "blueprint_mutation_readback_plan_summary": "",
            "blueprint_mutation_evidence_required_preview": [],
            "blueprint_mutation_evidence_merge_policy": "preserve_existing_evidence_unless_reset",
            "blueprint_mutation_evidence_reset": False,
            "blueprint_mutation_human_approval_required": True,
            "blueprint_mutation_evidence_no_bridge_ping": True,
            "blueprint_mutation_evidence_no_editor_mutation": True,
            "blueprint_mutation_evidence_no_blueprint_mutation": True,
            "blueprint_mutation_evidence_no_compile": True,
            "blueprint_mutation_evidence_no_save": True,
            "blueprint_mutation_evidence_no_pie": True,
        }
    parsed = _load_json(path)
    status = str(parsed.get("status", "unknown"))
    schema = str(parsed.get("schema", ""))
    schema_ok = schema == "unreal_mcp_platform_stability_review_receipt.v1"
    ready_for_platform = bool(parsed.get("ready_for_platform_stability", False))
    if status == "ready" and schema_ok and ready_for_platform:
        state = "ready"
    elif status in {"review_required", "ready"} and schema_ok:
        state = "review_required"
    else:
        state = "blocked"
    return {
        **base,
        "schema": schema or base["schema"],
        "state": state,
        "status": status,
        "generated_at_utc": str(parsed.get("generated_at_utc", "")),
        "ready_for_platform_stability": ready_for_platform,
        "ready_for_wip_promotion": bool(parsed.get("ready_for_wip_promotion", False)),
        "tool_registry_reproducible": bool(parsed.get("tool_registry_reproducible", False)),
        "tool_count": int(parsed.get("tool_count", 0) or 0),
        "recorded_tool_count": int(parsed.get("recorded_tool_count", parsed.get("recorded_count", 0)) or 0),
        "partial_tool_count": int(parsed.get("partial_tool_count", 0) or 0),
        "test_lane_ok": bool(parsed.get("test_lane_ok", False)),
        "paid_provider_smoke_contract_ok": bool(parsed.get("paid_provider_smoke_contract_ok", False)),
        "paid_provider_smoke_manual_command": str(parsed.get("paid_provider_smoke_manual_command", "")),
        "paid_provider_smoke_required_env_vars": list(parsed.get("paid_provider_smoke_required_env_vars", [])) if isinstance(parsed.get("paid_provider_smoke_required_env_vars"), list) else [],
        "paid_provider_smoke_no_spend_tools": list(parsed.get("paid_provider_smoke_no_spend_tools", [])) if isinstance(parsed.get("paid_provider_smoke_no_spend_tools"), list) else [],
        "paid_provider_smoke_forbidden_tokens_present": list(parsed.get("paid_provider_smoke_forbidden_tokens_present", [])) if isinstance(parsed.get("paid_provider_smoke_forbidden_tokens_present"), list) else [],
        "paid_provider_smoke_default_ci_network_required": bool(parsed.get("paid_provider_smoke_default_ci_network_required", False)),
        "paid_provider_smoke_manual_network_required": bool(parsed.get("paid_provider_smoke_manual_network_required", False)),
        "paid_provider_smoke_manual_spend_required": bool(parsed.get("paid_provider_smoke_manual_spend_required", False)),
        "paid_provider_smoke_no_task_submission": bool(parsed.get("paid_provider_smoke_no_task_submission", True)),
        "paid_provider_smoke_no_download": bool(parsed.get("paid_provider_smoke_no_download", True)),
        "paid_provider_smoke_no_import": bool(parsed.get("paid_provider_smoke_no_import", True)),
        "no_mutation_test_ok": bool(parsed.get("no_mutation_test_ok", False)),
        "high_value_wrappers_covered": bool(parsed.get("high_value_wrappers_covered", False)),
        "no_mutation_test_operator_command_handoff": (
            list(parsed.get("no_mutation_test_operator_command_handoff", []))[:1]
            if isinstance(parsed.get("no_mutation_test_operator_command_handoff"), list)
            else []
        ),
        "no_mutation_test_operator_command_handoff_ids": (
            list(parsed.get("no_mutation_test_operator_command_handoff_ids", []))[:1]
            if isinstance(parsed.get("no_mutation_test_operator_command_handoff_ids"), list)
            else []
        ),
        "no_mutation_test_operator_command_handoff_count": int(parsed.get("no_mutation_test_operator_command_handoff_count", 0) or 0),
        "build_wrapper_status": str(parsed.get("build_wrapper_status", "")),
        "high_value_wrapper_operator_command_handoff": (
            list(parsed.get("high_value_wrapper_operator_command_handoff", []))[:3]
            if isinstance(parsed.get("high_value_wrapper_operator_command_handoff"), list)
            else []
        ),
        "high_value_wrapper_operator_command_handoff_ids": (
            list(parsed.get("high_value_wrapper_operator_command_handoff_ids", []))[:3]
            if isinstance(parsed.get("high_value_wrapper_operator_command_handoff_ids"), list)
            else []
        ),
        "high_value_wrapper_operator_command_handoff_count": int(parsed.get("high_value_wrapper_operator_command_handoff_count", 0) or 0),
        "build_health": str(parsed.get("build_health", "")),
        "last_plugin_build_status": str(parsed.get("last_plugin_build_status", "")),
        "chat_ready": bool(parsed.get("chat_ready", False)),
        "bridge_ping_receipt_state": str(parsed.get("bridge_ping_receipt_state", "missing")),
        "bridge_ping_operator_command_handoff": (
            list(parsed.get("bridge_ping_operator_command_handoff", []))[:1]
            if isinstance(parsed.get("bridge_ping_operator_command_handoff"), list)
            else []
        ),
        "bridge_ping_operator_command_handoff_ids": (
            list(parsed.get("bridge_ping_operator_command_handoff_ids", []))[:1]
            if isinstance(parsed.get("bridge_ping_operator_command_handoff_ids"), list)
            else []
        ),
        "bridge_ping_operator_command_handoff_count": int(parsed.get("bridge_ping_operator_command_handoff_count", 0) or 0),
        "provider_config_review_receipt_state": str(parsed.get("provider_config_review_receipt_state", "missing")),
        "provider_config_operator_command_handoff": (
            list(parsed.get("provider_config_operator_command_handoff", []))[:1]
            if isinstance(parsed.get("provider_config_operator_command_handoff"), list)
            else []
        ),
        "provider_config_operator_command_handoff_ids": (
            list(parsed.get("provider_config_operator_command_handoff_ids", []))[:1]
            if isinstance(parsed.get("provider_config_operator_command_handoff_ids"), list)
            else []
        ),
        "provider_config_operator_command_handoff_count": int(parsed.get("provider_config_operator_command_handoff_count", 0) or 0),
        "dirty_promotion_review_receipt_state": str(parsed.get("dirty_promotion_review_receipt_state", "missing")),
        "dirty_promotion_review_receipt_current": bool(parsed.get("dirty_promotion_review_receipt_current", False)),
        "dirty_promotion_review_receipt_stale": bool(parsed.get("dirty_promotion_review_receipt_stale", False)),
        "dirty_promotion_review_receipt_signature_match": bool(parsed.get("dirty_promotion_review_receipt_signature_match", False)),
        "dirty_signature_algorithm": str(parsed.get("dirty_signature_algorithm", "")),
        "dirty_signature_entry_count": int(parsed.get("dirty_signature_entry_count", 0) or 0),
        "dirty_promotion_review_batch_count": int(parsed.get("dirty_promotion_review_batch_count", 0) or 0),
        "dirty_promotion_evidence_unresolved_count": int(parsed.get("dirty_promotion_evidence_unresolved_count", 0) or 0),
        "dirty_target_review_group": str(parsed.get("dirty_target_review_group", "")),
        "dirty_target_review_order": int(parsed.get("dirty_target_review_order", 0) or 0),
        "dirty_target_review_scope": str(parsed.get("dirty_target_review_scope", "")),
        "dirty_target_review_tracked_count": int(parsed.get("dirty_target_review_tracked_count", 0) or 0),
        "dirty_target_review_untracked_count": int(parsed.get("dirty_target_review_untracked_count", 0) or 0),
        "dirty_target_review_status": str(parsed.get("dirty_target_review_status", "")),
        "dirty_target_review_evidence_complete": bool(parsed.get("dirty_target_review_evidence_complete", False)),
        "dirty_target_review_recorded_evidence_count": int(parsed.get("dirty_target_review_recorded_evidence_count", 0) or 0),
        "dirty_target_review_recorded_evidence_preview": list(parsed.get("dirty_target_review_recorded_evidence_preview", []))[:8] if isinstance(parsed.get("dirty_target_review_recorded_evidence_preview"), list) else [],
        "dirty_target_review_human_approval_recorded": bool(parsed.get("dirty_target_review_human_approval_recorded", False)),
        "dirty_target_review_missing_evidence_count": int(parsed.get("dirty_target_review_missing_evidence_count", 0) or 0),
        "dirty_target_review_missing_evidence_preview": list(parsed.get("dirty_target_review_missing_evidence_preview", []))[:8] if isinstance(parsed.get("dirty_target_review_missing_evidence_preview"), list) else [],
        "dirty_target_review_pending_human_approval_only": bool(parsed.get("dirty_target_review_pending_human_approval_only", False)),
        "dirty_target_review_human_approval_gate": str(parsed.get("dirty_target_review_human_approval_gate", "human_approval_before_stage_commit_merge")),
        "dirty_target_review_human_approval_command_handoff": (
            list(parsed.get("dirty_target_review_human_approval_command_handoff", []))[:1]
            if isinstance(parsed.get("dirty_target_review_human_approval_command_handoff"), list)
            else []
        ),
        "dirty_target_review_focused_test_command_handoff": (
            list(parsed.get("dirty_target_review_focused_test_command_handoff", []))[:5]
            if isinstance(parsed.get("dirty_target_review_focused_test_command_handoff"), list)
            else []
        ),
        "dirty_target_review_focused_test_command_count": int(parsed.get("dirty_target_review_focused_test_command_count", 0) or 0),
        "dirty_target_review_focused_test_command_preview": list(parsed.get("dirty_target_review_focused_test_command_preview", []))[:5] if isinstance(parsed.get("dirty_target_review_focused_test_command_preview"), list) else [],
        "dirty_target_review_sample_preview": list(parsed.get("dirty_target_review_sample_preview", []))[:5] if isinstance(parsed.get("dirty_target_review_sample_preview"), list) else [],
        "dirty_target_review_promotion_allowed_after_receipt": bool(parsed.get("dirty_target_review_promotion_allowed_after_receipt", False)),
        "dirty_target_review_merge_policy": str(parsed.get("dirty_target_review_merge_policy", "preserve_existing_evidence_when_dirty_signature_and_target_match")),
        "dirty_target_review_previous_evidence_merged": bool(parsed.get("dirty_target_review_previous_evidence_merged", False)),
        "dirty_target_review_reset_evidence": bool(parsed.get("dirty_target_review_reset_evidence", False)),
        "platform_missing_gate_count": parsed.get("platform_missing_gate_count"),
        "wip_promotion_missing_gate_count": parsed.get("wip_promotion_missing_gate_count"),
        "blocking_gate_count": int(parsed.get("blocking_gate_count", 0) or 0),
        "blocking_gate_preview": list(parsed.get("blocking_gate_preview", []))[:12] if isinstance(parsed.get("blocking_gate_preview"), list) else [],
        "readiness_repair_action_count": int(parsed.get("readiness_repair_action_count", 0) or 0),
        "readiness_repair_recommended_next": str(parsed.get("readiness_repair_recommended_next", "none")),
        "readiness_repair_next_gate": str(parsed.get("readiness_repair_next_gate", "")),
        "readiness_repair_next_policy_area": str(parsed.get("readiness_repair_next_policy_area", "")),
        "readiness_repair_next_tool": str(parsed.get("readiness_repair_next_tool", "")),
        "readiness_repair_next_requires_bridge": bool(parsed.get("readiness_repair_next_requires_bridge", False)),
        "readiness_repair_next_requires_network": bool(parsed.get("readiness_repair_next_requires_network", False)),
        "readiness_repair_next_requires_spend": bool(parsed.get("readiness_repair_next_requires_spend", False)),
        "readiness_repair_action_preview": [
            item for item in parsed.get("readiness_repair_action_preview", [])[:8] if isinstance(item, dict)
        ] if isinstance(parsed.get("readiness_repair_action_preview"), list) else [],
        "paid_generation_evidence_receipt_state": str(parsed.get("paid_generation_evidence_receipt_state", "missing")),
        "paid_generation_evidence_receipt_path": str(parsed.get("paid_generation_evidence_receipt_path", "Saved\\PaidGenerationEvidence\\last_review_receipt.json")),
        "paid_generation_evidence_required_command": str(parsed.get("paid_generation_evidence_required_command", "python scripts\\write_paid_generation_evidence_review.py")),
        "paid_generation_wallet_evidence_recorded": bool(parsed.get("paid_generation_wallet_evidence_recorded", False)),
        "paid_generation_mesh_wallet_evidence_recorded": bool(parsed.get("paid_generation_mesh_wallet_evidence_recorded", False)),
        "paid_generation_animation_allowance_evidence_recorded": bool(parsed.get("paid_generation_animation_allowance_evidence_recorded", False)),
        "paid_generation_spend_confirmation_recorded": bool(parsed.get("paid_generation_spend_confirmation_recorded", False)),
        "paid_generation_explicit_spend_approval_recorded": bool(parsed.get("paid_generation_explicit_spend_approval_recorded", False)),
        "paid_generation_explicit_usage_approval_recorded": bool(parsed.get("paid_generation_explicit_usage_approval_recorded", False)),
        "paid_generation_estimated_spend_reviewed": bool(parsed.get("paid_generation_estimated_spend_reviewed", False)),
        "paid_generation_estimated_motion_seconds_reviewed": bool(parsed.get("paid_generation_estimated_motion_seconds_reviewed", False)),
        "paid_generation_mesh_provider": str(parsed.get("paid_generation_mesh_provider", "tripo")),
        "paid_generation_animation_provider": str(parsed.get("paid_generation_animation_provider", "uthana")),
        "paid_generation_operator_command_handoff": (
            list(parsed.get("paid_generation_operator_command_handoff", []))[:3]
            if isinstance(parsed.get("paid_generation_operator_command_handoff"), list)
            else []
        ),
        "blueprint_mutation_evidence_receipt_state": str(parsed.get("blueprint_mutation_evidence_receipt_state", "missing")),
        "blueprint_mutation_evidence_receipt_status": str(parsed.get("blueprint_mutation_evidence_receipt_status", "missing")),
        "blueprint_mutation_evidence_receipt_path": str(parsed.get("blueprint_mutation_evidence_receipt_path", "Saved\\BlueprintMutationEvidence\\last_review_receipt.json")),
        "blueprint_mutation_evidence_required_command": str(parsed.get("blueprint_mutation_evidence_required_command", "python scripts\\write_blueprint_mutation_evidence_review.py")),
        "blueprint_mutation_operator_command_handoff": (
            list(parsed.get("blueprint_mutation_operator_command_handoff", []))[:3]
            if isinstance(parsed.get("blueprint_mutation_operator_command_handoff"), list)
            else []
        ),
        "blueprint_mutation_pre_read_evidence_recorded": bool(parsed.get("blueprint_mutation_pre_read_evidence_recorded", False)),
        "blueprint_mutation_compile_plan_recorded": bool(parsed.get("blueprint_mutation_compile_plan_recorded", False)),
        "blueprint_mutation_readback_plan_recorded": bool(parsed.get("blueprint_mutation_readback_plan_recorded", False)),
        "blueprint_mutation_target_blueprint_path": str(parsed.get("blueprint_mutation_target_blueprint_path", "")),
        "blueprint_mutation_intended_summary": str(parsed.get("blueprint_mutation_intended_summary", "")),
        "blueprint_mutation_pre_read_summary": str(parsed.get("blueprint_mutation_pre_read_summary", "")),
        "blueprint_mutation_compile_plan_summary": str(parsed.get("blueprint_mutation_compile_plan_summary", "")),
        "blueprint_mutation_readback_plan_summary": str(parsed.get("blueprint_mutation_readback_plan_summary", "")),
        "blueprint_mutation_evidence_required_preview": (
            list(parsed.get("blueprint_mutation_evidence_required_preview", []))[:8]
            if isinstance(parsed.get("blueprint_mutation_evidence_required_preview"), list)
            else []
        ),
        "blueprint_mutation_evidence_merge_policy": str(parsed.get("blueprint_mutation_evidence_merge_policy", "preserve_existing_evidence_unless_reset")),
        "blueprint_mutation_evidence_reset": bool(parsed.get("blueprint_mutation_evidence_reset", False)),
        "blueprint_mutation_human_approval_required": bool(parsed.get("blueprint_mutation_human_approval_required", True)),
        "blueprint_mutation_evidence_no_bridge_ping": bool(parsed.get("blueprint_mutation_evidence_no_bridge_ping", True)),
        "blueprint_mutation_evidence_no_editor_mutation": bool(parsed.get("blueprint_mutation_evidence_no_editor_mutation", True)),
        "blueprint_mutation_evidence_no_blueprint_mutation": bool(parsed.get("blueprint_mutation_evidence_no_blueprint_mutation", True)),
        "blueprint_mutation_evidence_no_compile": bool(parsed.get("blueprint_mutation_evidence_no_compile", True)),
        "blueprint_mutation_evidence_no_save": bool(parsed.get("blueprint_mutation_evidence_no_save", True)),
        "blueprint_mutation_evidence_no_pie": bool(parsed.get("blueprint_mutation_evidence_no_pie", True)),
    }


def _bridge_ping_receipt_status(path: Path = BRIDGE_PING_RECEIPT_PATH) -> Dict[str, Any]:
    display_path = "Saved\\BridgePing\\last_ping_receipt.json"
    operator_command_handoff = [
        {
            "id": "verify_unreal_bridge_ping",
            "label": "Verify Unreal bridge ping",
            "command": "python scripts\\bridge_ping.py",
            "command_kind": "live_bridge_validation_receipt",
            "receipt_path": display_path,
            "produces_evidence_for": "unreal_bridge_reachable",
            "records_evidence_only": False,
            "requires_bridge": True,
            "requires_unreal_editor": True,
            "requires_provider_network": False,
            "requires_spend": False,
            "no_editor_mutation": True,
            "no_pie_run": True,
            "no_provider_call": True,
            "no_git_mutation": True,
            "no_task_submission": True,
        }
    ]
    base = {
        "schema": "unreal_mcp_bridge_ping_receipt.v1",
        "path": display_path,
        "receipt_exists": path.exists(),
        "required_command": "python scripts\\bridge_ping.py",
        "operator_command_handoff": operator_command_handoff,
        "operator_command_handoff_ids": [item["id"] for item in operator_command_handoff],
        "operator_command_handoff_count": len(operator_command_handoff),
        "network_required": False,
        "spend_required": False,
        "unreal_editor_required": True,
        "no_editor_mutation": True,
        "no_provider_call": True,
        "no_git_mutation": True,
    }
    if not path.exists():
        return {
            **base,
            "state": "missing",
            "status": "missing",
            "successful_bridge_ping": False,
            "exit_code": None,
            "command_status": "",
            "actor_count": None,
        }
    parsed = _load_json(path)
    schema = str(parsed.get("schema", ""))
    status = str(parsed.get("status", "unknown"))
    exit_code = parsed.get("exit_code")
    successful = (
        schema == "unreal_mcp_bridge_ping_receipt.v1"
        and status == "success"
        and int(exit_code if exit_code is not None else -1) == 0
        and bool(parsed.get("successful_bridge_ping", False))
    )
    return {
        **base,
        "schema": schema or base["schema"],
        "state": "ok" if successful else "blocked",
        "status": status,
        "successful_bridge_ping": successful,
        "generated_at_utc": str(parsed.get("generated_at_utc", "")),
        "host": str(parsed.get("host", "")),
        "port": parsed.get("port"),
        "exit_code": exit_code,
        "command": str(parsed.get("command", "")),
        "command_status": str(parsed.get("command_status", "")),
        "actor_count": parsed.get("actor_count"),
        "error": str(parsed.get("error", "")),
    }


def _build_readiness_policy(
    *,
    tool_inventory: Dict[str, Any],
    bridge: Dict[str, Any],
    chat: Dict[str, Any],
    provider: Dict[str, Any],
    git: Optional[Dict[str, Any]] = None,
    build: Optional[Dict[str, Any]] = None,
    test_lanes: Optional[Dict[str, Any]] = None,
    no_mutation_tests: Optional[Dict[str, Any]] = None,
    high_value_wrapper_coverage: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    tool_ready = bool(tool_inventory["matches_recorded_count"] and not tool_inventory["missing_category_modules"])
    bridge_ready = bool(bridge["ready"])
    chat_ready = bool(chat["ready"])
    provider_ready = bool(provider["api_key_configured"])
    animation_provider_ready = bool(provider.get("uthana_api_key_configured", False))
    build_status = build if isinstance(build, dict) else {}
    build_wrapper_ready = str(build_status.get("build_wrapper_status", "ready")) != "missing_reference"
    build_wrapper_exists = bool(build_status.get("build_wrapper_existing_count", 1))
    build_health_blocked = str(build_status.get("build_health", "ok")) == "blocked"
    plugin_build_successful = str(build_status.get("last_plugin_build_status", "unknown")) == "success" and not build_health_blocked
    git_status = git if isinstance(git, dict) else {}
    branch_status = git_status.get("branch") if isinstance(git_status.get("branch"), dict) else {}
    working_branch_ok = bool(branch_status.get("working_branch_ok", False))
    dirty_state_grouped = (
        str(git_status.get("dirty_risk", "unknown")) in {"clean", "low"}
        and int(git_status.get("tracked_change_count", 0) or 0) == 0
    )
    test_lane_status = test_lanes if isinstance(test_lanes, dict) else {"ok": True}
    test_lanes_ok = bool(test_lane_status.get("ok", True)) and int(test_lane_status.get("violation_count", 0) or 0) == 0
    no_mutation_status = no_mutation_tests if isinstance(no_mutation_tests, dict) else {"ok": True}
    no_mutation_tests_ok = bool(no_mutation_status.get("ok", True))
    wrapper_status = high_value_wrapper_coverage if isinstance(high_value_wrapper_coverage, dict) else {"ok": True}
    high_value_wrappers_covered = bool(wrapper_status.get("ok", True)) and int(wrapper_status.get("failing_capability_count", 0) or 0) == 0
    paid_generation_review = _paid_generation_evidence_review_receipt_status()
    spend_confirmed = bool(paid_generation_review.get("spend_confirmation_recorded", False))
    wallet_evidence_recorded = bool(paid_generation_review.get("wallet_evidence_recorded", False))
    blueprint_evidence_review = _blueprint_mutation_evidence_review_receipt_status()
    blueprint_pre_read_recorded = bool(blueprint_evidence_review.get("pre_read_evidence_recorded", False))
    blueprint_compile_plan_recorded = bool(blueprint_evidence_review.get("compile_plan_recorded", False))
    blueprint_readback_plan_recorded = bool(blueprint_evidence_review.get("readback_plan_recorded", False))

    editor_missing = []
    if not tool_ready:
        editor_missing.append("tool_registry_reproducible")
    if not bridge_ready:
        editor_missing.append("unreal_bridge_reachable")

    paid_missing = []
    if not provider_ready:
        paid_missing.append("provider_api_key_configured")
    if not wallet_evidence_recorded:
        paid_missing.append("wallet_evidence_recorded")
    if not spend_confirmed:
        paid_missing.append("spend_confirmation_recorded")

    animation_paid_missing = []
    if not animation_provider_ready:
        animation_paid_missing.append("animation_provider_api_key_configured")
    if not wallet_evidence_recorded:
        animation_paid_missing.append("wallet_evidence_recorded")
    if not spend_confirmed:
        animation_paid_missing.append("spend_confirmation_recorded")

    chat_missing = [] if chat_ready else ["chat_server_reachable"]
    platform_missing = []
    if not tool_ready:
        platform_missing.append("tool_registry_reproducible")
    if not build_wrapper_exists:
        platform_missing.append("build_wrapper_present")
    if not build_wrapper_ready or build_health_blocked:
        platform_missing.append("build_wrapper_references_ready")
    if not working_branch_ok:
        platform_missing.append("working_branch_is_wip")
    if not test_lanes_ok:
        platform_missing.append("test_lane_separation")
    if not high_value_wrappers_covered:
        platform_missing.append("high_value_bridge_wrappers_covered")

    wip_promotion_missing = []
    if not working_branch_ok:
        wip_promotion_missing.append("working_branch_is_wip")
    if not tool_ready:
        wip_promotion_missing.append("tool_registry_reproducible")
    if not test_lanes_ok or not no_mutation_tests_ok:
        wip_promotion_missing.append("no_mutation_test_lane_safe")
    if not high_value_wrappers_covered:
        wip_promotion_missing.append("high_value_bridge_wrappers_covered")
    if not build_wrapper_exists:
        wip_promotion_missing.append("build_wrapper_present")
    if not build_wrapper_ready or build_health_blocked:
        wip_promotion_missing.append("build_wrapper_references_ready")
    if not plugin_build_successful:
        wip_promotion_missing.append("plugin_build_successful")
    if not dirty_state_grouped:
        wip_promotion_missing.append("dirty_state_grouped_for_promotion")
    if not chat_ready:
        wip_promotion_missing.append("chat_cockpit_reachable")

    blueprint_missing = list(editor_missing)
    if not blueprint_pre_read_recorded:
        blueprint_missing.append("blueprint_pre_read_evidence")
    if not blueprint_compile_plan_recorded:
        blueprint_missing.append("blueprint_compile_plan")
    if not blueprint_readback_plan_recorded:
        blueprint_missing.append("blueprint_readback_plan")

    return {
        "schema": "unreal_mcp_readiness_policy.v1",
        "editor_mutation": _policy_row(
            allowed=not editor_missing,
            required_gates=["tool_registry_reproducible", "unreal_bridge_reachable"],
            missing_gates=editor_missing,
            evidence_required=["successful_bridge_ping"],
        ),
        "paid_generation": _policy_row(
            allowed=provider_ready and wallet_evidence_recorded and spend_confirmed,
            required_gates=[
                "provider_api_key_configured",
                "wallet_evidence_recorded",
                "spend_confirmation_recorded",
            ],
            missing_gates=paid_missing,
            evidence_required=["provider_key_presence", "wallet_or_credit_evidence", "explicit_spend_confirmation"],
        ),
        "paid_animation_generation": _policy_row(
            allowed=animation_provider_ready and wallet_evidence_recorded and spend_confirmed,
            required_gates=[
                "animation_provider_api_key_configured",
                "wallet_evidence_recorded",
                "spend_confirmation_recorded",
            ],
            missing_gates=animation_paid_missing,
            evidence_required=["animation_provider_key_presence", "wallet_or_credit_evidence", "explicit_spend_confirmation"],
        ),
        "blueprint_mutation": _policy_row(
            allowed=not blueprint_missing,
            required_gates=[
                "tool_registry_reproducible",
                "unreal_bridge_reachable",
                "blueprint_pre_read_evidence",
                "blueprint_compile_plan",
                "blueprint_readback_plan",
            ],
            missing_gates=blueprint_missing,
            evidence_required=[
                "blueprint_pre_read",
                "compile_check_after_mutation",
                "graph_or_component_readback_after_mutation",
            ],
        ),
        "chat_cockpit": _policy_row(
            allowed=not chat_missing,
            required_gates=["chat_server_reachable"],
            missing_gates=chat_missing,
            evidence_required=["chat_history_endpoint_ready"],
        ),
        "platform_stability": _policy_row(
            allowed=not platform_missing,
            required_gates=[
                "tool_registry_reproducible",
                "working_branch_is_wip",
                "build_wrapper_present",
                "build_wrapper_references_ready",
                "test_lane_separation",
                "high_value_bridge_wrappers_covered",
            ],
            missing_gates=platform_missing,
            evidence_required=[
                "tool_count_matches_baseline",
                "git_branch_policy_evidence",
                "build_wrapper_project_and_tool_paths_resolve",
                "offline_live_paid_test_lane_audit",
                "high_value_wrapper_coverage_audit",
            ],
        ),
        "wip_promotion": _policy_row(
            allowed=not wip_promotion_missing,
            required_gates=[
                "working_branch_is_wip",
                "tool_registry_reproducible",
                "no_mutation_test_lane_safe",
                "high_value_bridge_wrappers_covered",
                "build_wrapper_present",
                "build_wrapper_references_ready",
                "plugin_build_successful",
                "dirty_state_grouped_for_promotion",
                "chat_cockpit_reachable",
            ],
            missing_gates=wip_promotion_missing,
            evidence_required=[
                "current_branch_name",
                "tool_count_matches_baseline",
                "offline_live_paid_test_lane_audit",
                "last_no_mutation_unittest_receipt",
                "high_value_wrapper_coverage_audit",
                "build_wrapper_project_and_tool_paths_resolve",
                "last_plugin_build_success",
                "dirty_state_grouped_or_clean",
                "chat_history_endpoint_ready",
            ],
        ),
        "branch_policy": _policy_row(
            allowed=working_branch_ok,
            required_gates=["working_branch_is_wip"],
            missing_gates=[] if working_branch_ok else ["working_branch_is_wip"],
            evidence_required=["current_branch_name", "wip_to_main_promotion_policy"],
        ),
        "notes": [
            "Preflight is read-only and never records wallet evidence, spend confirmation, or Blueprint action-specific evidence.",
            "Mesh and animation provider readiness are separate gates so Uthana motion work cannot be mistaken for Tripo mesh readiness.",
            "Blueprint mutation readiness is action-specific; this policy keeps it blocked until a work order supplies pre-read, compile, and readback evidence requirements.",
            "Platform stability is a promotion/build-health gate and does not by itself authorize editor mutation.",
            "WIP promotion is stricter than platform stability because dirty-state grouping, plugin build proof, and chat cockpit readiness are required before moving toward main.",
            "Branch policy keeps active development on wip and treats main as the stable promotion target.",
            "High-value bridge wrapper coverage is read-only source/test/doc evidence; it does not authorize editor mutation without the bridge and action-specific proof gates.",
            "Offline, live-bridge, and paid-provider test lanes must remain separated so default discovery is no-mutation and no-spend.",
        ],
    }


def _paid_generation_operator_command_handoff(
    mesh_wallet_command: str,
    animation_allowance_command: str,
    approval_command: str,
) -> List[Dict[str, Any]]:
    return [
        {
            "id": "record_masked_tripo_wallet_evidence",
            "label": "Record masked Tripo wallet evidence",
            "provider": "tripo",
            "command": mesh_wallet_command,
            "command_kind": "local_receipt",
            "receipt_path": "Saved\\PaidGenerationEvidence\\last_review_receipt.json",
            "requires_provider_network_approval": True,
            "requires_human_spend_or_usage_approval": False,
            "approval_flags_included": False,
            "records_evidence_only": True,
            "no_provider_call": True,
            "no_credit_reservation": True,
            "no_task_submission": True,
            "no_download": True,
            "no_import": True,
            "no_editor_mutation": True,
            "no_git_mutation": True,
        },
        {
            "id": "record_masked_uthana_allowance_evidence",
            "label": "Record masked Uthana allowance evidence",
            "provider": "uthana",
            "command": animation_allowance_command,
            "command_kind": "local_receipt",
            "receipt_path": "Saved\\PaidGenerationEvidence\\last_review_receipt.json",
            "requires_provider_network_approval": True,
            "requires_human_spend_or_usage_approval": False,
            "approval_flags_included": False,
            "records_evidence_only": True,
            "no_provider_call": True,
            "no_credit_reservation": True,
            "no_task_submission": True,
            "no_download": True,
            "no_import": True,
            "no_editor_mutation": True,
            "no_git_mutation": True,
        },
        {
            "id": "record_explicit_spend_and_usage_approval",
            "label": "Record explicit Tripo spend and Uthana usage approval",
            "provider": "tripo+uthana",
            "command": approval_command,
            "command_kind": "local_receipt",
            "receipt_path": "Saved\\PaidGenerationEvidence\\last_review_receipt.json",
            "requires_provider_network_approval": False,
            "requires_human_spend_or_usage_approval": True,
            "approval_flags_included": True,
            "records_evidence_only": True,
            "no_provider_call": True,
            "no_credit_reservation": True,
            "no_task_submission": True,
            "no_download": True,
            "no_import": True,
            "no_editor_mutation": True,
            "no_git_mutation": True,
        },
    ]


def _blueprint_mutation_operator_command_handoff(
    pre_read_command: str,
    compile_plan_command: str,
    readback_plan_command: str,
) -> List[Dict[str, Any]]:
    common = {
        "command_kind": "local_receipt",
        "receipt_path": "Saved\\BlueprintMutationEvidence\\last_review_receipt.json",
        "records_evidence_only": True,
        "no_bridge_ping": True,
        "no_editor_mutation": True,
        "no_blueprint_mutation": True,
        "no_compile": True,
        "no_save": True,
        "no_pie": True,
        "no_provider_call": True,
        "no_git_mutation": True,
        "network_required": False,
        "spend_required": False,
    }
    return [
        {
            **common,
            "id": "record_blueprint_pre_read_evidence",
            "label": "Record Blueprint pre-read evidence",
            "command": pre_read_command,
            "evidence_gate": "blueprint_pre_read_evidence",
            "future_read_only_bridge_evidence_required": True,
            "requires_bridge_evidence_before_receipt": True,
        },
        {
            **common,
            "id": "record_blueprint_compile_plan",
            "label": "Record Blueprint compile plan",
            "command": compile_plan_command,
            "evidence_gate": "blueprint_compile_plan",
            "future_read_only_bridge_evidence_required": False,
            "requires_bridge_evidence_before_receipt": False,
        },
        {
            **common,
            "id": "record_blueprint_readback_plan",
            "label": "Record Blueprint readback plan",
            "command": readback_plan_command,
            "evidence_gate": "blueprint_readback_plan",
            "future_read_only_bridge_evidence_required": False,
            "requires_bridge_evidence_before_receipt": False,
        },
    ]


def _paid_generation_evidence_contract(provider: Dict[str, Any]) -> Dict[str, Any]:
    mesh_provider = str(provider.get("provider") or "tripo")
    animation_provider = str(provider.get("animation_provider") or "uthana")
    review_receipt = _paid_generation_evidence_review_receipt_status()
    wallet_evidence_recorded = bool(review_receipt.get("wallet_evidence_recorded", False))
    mesh_wallet_evidence_recorded = bool(review_receipt.get("mesh_wallet_evidence_recorded", False))
    animation_allowance_evidence_recorded = bool(review_receipt.get("animation_allowance_evidence_recorded", False))
    spend_confirmation_recorded = bool(review_receipt.get("spend_confirmation_recorded", False))
    explicit_spend_approval_recorded = bool(review_receipt.get("explicit_spend_approval_recorded", False))
    explicit_usage_approval_recorded = bool(review_receipt.get("explicit_usage_approval_recorded", False))
    blocked_gates: List[str] = []
    if not wallet_evidence_recorded:
        blocked_gates.append("wallet_evidence_recorded")
    if not spend_confirmation_recorded:
        blocked_gates.append("spend_confirmation_recorded")
    mesh_wallet_evidence_receipt_command_template = (
        'python scripts\\write_paid_generation_evidence_review.py --record-masked-tripo-wallet-evidence '
        '--mesh-wallet-evidence-summary "<masked Tripo wallet evidence>"'
    )
    animation_allowance_receipt_command_template = (
        'python scripts\\write_paid_generation_evidence_review.py --record-masked-uthana-allowance-evidence '
        '--animation-allowance-summary "<masked Uthana allowance evidence>"'
    )
    wallet_evidence_receipt_command_template = (
        'python scripts\\write_paid_generation_evidence_review.py --mesh-wallet-evidence-recorded '
        '--animation-allowance-evidence-recorded --mesh-wallet-evidence-summary "<masked Tripo wallet evidence>" '
        '--animation-allowance-summary "<masked Uthana allowance evidence>"'
    )
    spend_confirmation_receipt_command_template = (
        'python scripts\\write_paid_generation_evidence_review.py --record-masked-tripo-wallet-evidence '
        '--record-masked-uthana-allowance-evidence --record-explicit-spend-and-usage-approval '
        '--mesh-wallet-evidence-summary "<masked Tripo wallet evidence>" '
        '--animation-allowance-summary "<masked Uthana allowance evidence>" '
        '--spend-confirmation-summary "<explicit human Tripo spend approval>" '
        '--usage-approval-summary "<explicit human Uthana usage approval>"'
    )
    return {
        "schema": "unreal_mcp_paid_generation_evidence_contract.v1",
        "wallet_evidence_recorded": wallet_evidence_recorded,
        "mesh_wallet_evidence_recorded": mesh_wallet_evidence_recorded,
        "animation_allowance_evidence_recorded": animation_allowance_evidence_recorded,
        "spend_confirmation_recorded": spend_confirmation_recorded,
        "explicit_spend_approval_recorded": explicit_spend_approval_recorded,
        "explicit_usage_approval_recorded": explicit_usage_approval_recorded,
        "estimated_spend_reviewed": bool(review_receipt.get("estimated_spend_reviewed", False)),
        "estimated_motion_seconds_reviewed": bool(review_receipt.get("estimated_motion_seconds_reviewed", False)),
        "mesh_provider": mesh_provider,
        "animation_provider": animation_provider,
        "review_receipt": review_receipt,
        "review_receipt_exists": bool(review_receipt.get("receipt_exists", False)),
        "review_receipt_state": str(review_receipt.get("state", "missing")),
        "review_receipt_path": str(review_receipt.get("path", "Saved\\PaidGenerationEvidence\\last_review_receipt.json")),
        "review_receipt_required_command": str(review_receipt.get("required_command", "python scripts\\write_paid_generation_evidence_review.py")),
        "mesh_wallet_tool": "gen_tripo_get_credit_balance",
        "animation_allowance_tools": [
            "gen_uthana_get_account",
            "gen_uthana_get_job",
            "gen_uthana_check_download_allowed",
        ],
        "ledger_tool": "skill_record_ide_companion_evidence",
        "spend_approval_field": "confirm_spend=True for Tripo; confirm_usage=True for Uthana task/download",
        "no_spend_checks": [
            "gen_get_provider_config(include_paths=True)",
            "gen_tripo_get_credit_balance after provider-network approval and no-spend intent",
            "gen_uthana_get_account / gen_uthana_get_job / gen_uthana_check_download_allowed after provider-network approval and no-spend intent",
        ],
        "wallet_evidence_review_steps": [
            "Confirm provider-network approval and no-spend intent in the cockpit.",
            "Run gen_tripo_get_credit_balance(include_raw=False) for masked Tripo wallet balance evidence.",
            "Run gen_uthana_get_account(include_user=False) for masked Uthana org allowance evidence.",
            "Write the ignored local paid-generation evidence receipt with a short non-secret summary.",
        ],
        "wallet_evidence_receipt_command_template": wallet_evidence_receipt_command_template,
        "mesh_wallet_evidence_receipt_command_template": mesh_wallet_evidence_receipt_command_template,
        "animation_allowance_receipt_command_template": animation_allowance_receipt_command_template,
        "spend_confirmation_receipt_command_template": spend_confirmation_receipt_command_template,
        "operator_command_handoff": _paid_generation_operator_command_handoff(
            mesh_wallet_evidence_receipt_command_template,
            animation_allowance_receipt_command_template,
            spend_confirmation_receipt_command_template,
        ),
        "evidence_required": [
            "masked_provider_auth_source",
            "wallet_or_allowance_evidence",
            "masked_tripo_wallet_evidence",
            "masked_uthana_allowance_evidence",
            "explicit_human_spend_or_usage_approval",
            "explicit_tripo_spend_approval",
            "explicit_uthana_usage_approval",
            "estimated_credits_or_motion_seconds_reviewed",
            "ledger_evidence_row_before_paid_task_submission",
        ],
        "blocked_gates": blocked_gates,
        "fallback_tool": "skill_compile_ide_companion_placeholder_manifest",
        "fallback_reason": "Use placeholders and lifecycle manifests until wallet/allowance and explicit spend/usage approval are recorded.",
        "network_required_now": False,
        "spend_required_now": False,
        "future_network_required": True,
        "future_spend_required": True,
        "unreal_editor_required_now": False,
        "no_provider_call": True,
        "no_credit_reservation": True,
        "no_task_submission": True,
        "no_ledger_write": True,
    }


def _readiness_repair_queue(
    *,
    blocking_gates: List[str],
    bridge: Dict[str, Any],
    chat_repair: Dict[str, Any],
    provider: Dict[str, Any],
    paid_generation_evidence: Dict[str, Any],
    dirty_promotion: Dict[str, Any],
) -> Dict[str, Any]:
    blueprint_evidence = _blueprint_mutation_evidence_review_receipt_status()
    gate_order = {
        "chat_server_reachable": 10,
        "chat_cockpit_reachable": 11,
        "dirty_state_grouped_for_promotion": 20,
        "unreal_bridge_reachable": 30,
        "blueprint_pre_read_evidence": 31,
        "blueprint_compile_plan": 32,
        "blueprint_readback_plan": 33,
        "provider_api_key_configured": 40,
        "animation_provider_api_key_configured": 41,
        "wallet_evidence_recorded": 50,
        "spend_confirmation_recorded": 60,
    }
    unique_gates = sorted(dict.fromkeys(blocking_gates), key=lambda gate: (gate_order.get(gate, 99), gate))
    actions: List[Dict[str, Any]] = []
    blueprint_operator_handoff = (
        list(blueprint_evidence.get("operator_command_handoff", []))[:3]
        if isinstance(blueprint_evidence.get("operator_command_handoff"), list)
        else []
    )

    def _blueprint_handoff(command_id: str) -> List[Dict[str, Any]]:
        return [
            item
            for item in blueprint_operator_handoff
            if isinstance(item, dict) and item.get("id") == command_id
        ][:1]

    def _append(action: Dict[str, Any]) -> None:
        actions.append({
            "order": len(actions) + 1,
            "requires_manual_operator": True,
            "requires_bridge": False,
            "requires_network": False,
            "requires_spend": False,
            "requires_unreal_editor": False,
            "no_auto_execute": True,
            "no_secret_echo": True,
            "no_git_mutation": True,
            "no_editor_mutation": True,
            **action,
        })

    for gate in unique_gates:
        if gate == "chat_server_reachable":
            _append({
                "action_id": "repair_chat_server_reachability",
                "gate": gate,
                "policy_area": "chat_cockpit",
                "title": "Start and verify MCP Chat SSE server manually",
                "recommended_tool": "scripts/audit_ide_companion_readiness.py",
                "recommended_contract": "chat_cockpit_repair_contract",
                "proof_command": str(chat_repair.get("proof_command", "")),
                "evidence_required_preview": list(chat_repair.get("required_evidence", []))[:5] if isinstance(chat_repair.get("required_evidence"), list) else [],
                "no_process_start": bool(chat_repair.get("no_process_start", True)),
                "no_port_kill": bool(chat_repair.get("no_port_kill", True)),
            })
        elif gate == "chat_cockpit_reachable":
            _append({
                "action_id": "refresh_chat_cockpit_after_server_ready",
                "gate": gate,
                "policy_area": "wip_promotion",
                "title": "Refresh Unreal MCP Chat panel after chat server proof",
                "recommended_tool": "chat_get_cockpit_overview",
                "recommended_contract": "chat_cockpit_repair_contract",
                "proof_command": str(chat_repair.get("proof_command", "")),
                "evidence_required_preview": ["chat_history_endpoint_ready", "unreal_chat_panel_refresh_after_server_ready"],
                "requires_unreal_editor": True,
            })
        elif gate == "provider_api_key_configured":
            repair = provider.get("repair_contract") if isinstance(provider.get("repair_contract"), dict) else {}
            _append({
                "action_id": "configure_tripo_provider_secret",
                "gate": gate,
                "policy_area": "paid_generation",
                "title": "Store Tripo credential through masked settings or ignored local secret",
                "recommended_tool": str(repair.get("save_tool", "gen_save_provider_config")),
                "recommended_contract": "provider_config.repair_contract",
                "review_receipt_path": str(provider.get("review_receipt_path", "Saved\\ProviderConfigReview\\last_review_receipt.json")),
                "review_receipt_state": str(provider.get("review_receipt_state", "missing")),
                "review_receipt_required_command": str(provider.get("review_receipt_required_command", "python scripts\\write_provider_config_review.py")),
                "evidence_required_preview": ["masked_provider_auth_source", "api_key_configured_true", "raw_key_absent_from_outputs"],
                "secret_placeholder": "<TRIPO_API_KEY>",
                "secret_source_options": ["native_masked_generate_settings", "env:TRIPO_API_KEY", "Saved/MCPChat/secrets.json"],
                "no_provider_call": True,
                "no_secret_storage_in_git": True,
            })
        elif gate == "animation_provider_api_key_configured":
            repair = provider.get("repair_contract") if isinstance(provider.get("repair_contract"), dict) else {}
            _append({
                "action_id": "configure_uthana_provider_secret",
                "gate": gate,
                "policy_area": "paid_animation_generation",
                "title": "Store Uthana credential through masked settings or ignored local secret",
                "recommended_tool": str(repair.get("save_tool", "gen_save_provider_config")),
                "recommended_contract": "provider_config.repair_contract",
                "review_receipt_path": str(provider.get("review_receipt_path", "Saved\\ProviderConfigReview\\last_review_receipt.json")),
                "review_receipt_state": str(provider.get("review_receipt_state", "missing")),
                "review_receipt_required_command": str(provider.get("review_receipt_required_command", "python scripts\\write_provider_config_review.py")),
                "evidence_required_preview": ["masked_animation_provider_auth_source", "uthana_api_key_configured_true", "raw_key_absent_from_outputs"],
                "secret_placeholder": "<UTHANA_API_KEY>",
                "secret_source_options": ["native_masked_generate_settings", "env:UTHANA_API_KEY", "Saved/MCPChat/secrets.json"],
                "no_provider_call": True,
                "no_secret_storage_in_git": True,
            })
        elif gate == "wallet_evidence_recorded":
            handoff = (
                list(paid_generation_evidence.get("operator_command_handoff", []))[:2]
                if isinstance(paid_generation_evidence.get("operator_command_handoff"), list)
                else []
            )
            _append({
                "action_id": "record_wallet_or_allowance_evidence",
                "gate": gate,
                "policy_area": "paid_generation",
                "title": "Record no-spend wallet or allowance evidence after credential setup",
                "recommended_tool": str(paid_generation_evidence.get("mesh_wallet_tool", "gen_tripo_get_credit_balance")),
                "secondary_tools": list(paid_generation_evidence.get("animation_allowance_tools", []))[:3] if isinstance(paid_generation_evidence.get("animation_allowance_tools"), list) else [],
                "recommended_contract": "paid_generation_evidence",
                "evidence_required_preview": ["wallet_or_allowance_evidence", "provider_network_approval", "no_spend_intent_confirmation"],
                "review_steps": list(paid_generation_evidence.get("wallet_evidence_review_steps", []))[:5] if isinstance(paid_generation_evidence.get("wallet_evidence_review_steps"), list) else [],
                "receipt_command_template": str(paid_generation_evidence.get("wallet_evidence_receipt_command_template", "")),
                "mesh_wallet_receipt_command_template": str(paid_generation_evidence.get("mesh_wallet_evidence_receipt_command_template", "")),
                "animation_allowance_receipt_command_template": str(paid_generation_evidence.get("animation_allowance_receipt_command_template", "")),
                "operator_command_handoff": handoff,
                "requires_network": True,
                "provider_call_required": True,
                "no_credit_reservation": True,
                "no_task_submission": True,
                "no_download": True,
                "no_import": True,
            })
        elif gate == "spend_confirmation_recorded":
            handoff = (
                list(paid_generation_evidence.get("operator_command_handoff", []))[2:3]
                if isinstance(paid_generation_evidence.get("operator_command_handoff"), list)
                else []
            )
            _append({
                "action_id": "record_explicit_spend_or_usage_confirmation",
                "gate": gate,
                "policy_area": "paid_generation",
                "title": "Record explicit human spend or Uthana usage approval before task submission",
                "recommended_tool": str(paid_generation_evidence.get("ledger_tool", "skill_record_ide_companion_evidence")),
                "recommended_contract": "paid_generation_evidence",
                "evidence_required_preview": ["explicit_human_spend_or_usage_approval", "estimated_credits_or_motion_seconds_reviewed", "ledger_evidence_row_before_paid_task_submission"],
                "receipt_command_template": str(paid_generation_evidence.get("spend_confirmation_receipt_command_template", "")),
                "operator_command_handoff": handoff,
                "future_spend_required": True,
                "no_provider_call": True,
                "no_credit_reservation": True,
                "no_task_submission": True,
            })
        elif gate == "dirty_state_grouped_for_promotion":
            review_batches = dirty_promotion.get("review_batches") if isinstance(dirty_promotion.get("review_batches"), list) else []
            evidence_matrix = dirty_promotion.get("evidence_review_matrix") if isinstance(dirty_promotion.get("evidence_review_matrix"), list) else []
            target_review_batch = next((item for item in review_batches if isinstance(item, dict)), {})
            target_review_gap = next((item for item in evidence_matrix if isinstance(item, dict)), {})
            target_missing_evidence = (
                target_review_gap.get("missing_evidence")
                if isinstance(target_review_gap.get("missing_evidence"), list)
                else []
            )
            target_required_evidence = (
                dirty_promotion.get("target_review_required_evidence_preview")
                if isinstance(dirty_promotion.get("target_review_required_evidence_preview"), list)
                else []
            )
            if not target_required_evidence:
                target_required_evidence = target_missing_evidence
            _append({
                "action_id": "review_dirty_groups_for_promotion",
                "gate": gate,
                "policy_area": "wip_promotion",
                "title": "Classify dirty worktree groups before staging or promotion",
                "recommended_tool": "scripts/write_dirty_promotion_review.py",
                "recommended_contract": "dirty_promotion_contract",
                "receipt_path": str(dirty_promotion.get("review_receipt_path", "Saved\\DirtyPromotionReview\\last_review_receipt.json")),
                "receipt_state": str(dirty_promotion.get("review_receipt_state", "missing")),
                "receipt_current": bool(dirty_promotion.get("review_receipt_current", False)),
                "receipt_stale": bool(dirty_promotion.get("review_receipt_stale", False)),
                "receipt_dirty_signature_match": bool(dirty_promotion.get("review_receipt_dirty_signature_match", False)),
                "current_dirty_signature": str(dirty_promotion.get("dirty_signature", "")),
                "receipt_dirty_signature": str(dirty_promotion.get("review_receipt_dirty_signature", "")),
                "required_command": str(dirty_promotion.get("review_receipt_required_command", "python scripts\\write_dirty_promotion_review.py")),
                "evidence_required_preview": list(dirty_promotion.get("required_evidence", []))[:5] if isinstance(dirty_promotion.get("required_evidence"), list) else [],
                "review_batch_count": int(dirty_promotion.get("review_batch_count", 0) or 0),
                "evidence_review_matrix_count": int(dirty_promotion.get("evidence_review_matrix_count", 0) or 0),
                "evidence_unresolved_count": int(dirty_promotion.get("evidence_unresolved_count", 0) or 0),
                "target_review_group": str(dirty_promotion.get("target_review_group") or target_review_batch.get("group") or target_review_gap.get("group") or ""),
                "target_review_order": int(dirty_promotion.get("target_review_order", target_review_batch.get("order", target_review_gap.get("order", 0))) or 0),
                "target_review_scope": str(dirty_promotion.get("target_review_scope") or target_review_batch.get("candidate_batch_scope") or target_review_gap.get("candidate_batch_scope") or ""),
                "target_review_tracked_count": int(dirty_promotion.get("target_review_tracked_count", target_review_batch.get("tracked_count", target_review_gap.get("tracked_count", 0))) or 0),
                "target_review_untracked_count": int(dirty_promotion.get("target_review_untracked_count", target_review_batch.get("untracked_count", target_review_gap.get("untracked_count", 0))) or 0),
                "target_review_status": str(dirty_promotion.get("target_review_status", "missing_evidence")),
                "target_review_evidence_complete": bool(dirty_promotion.get("target_review_evidence_complete", False)),
                "target_review_recorded_evidence_count": int(dirty_promotion.get("target_review_recorded_evidence_count", 0) or 0),
                "target_review_recorded_evidence_preview": (
                    list(dirty_promotion.get("target_review_recorded_evidence_preview", []))[:8]
                    if isinstance(dirty_promotion.get("target_review_recorded_evidence_preview"), list)
                    else []
                ),
                "target_review_human_approval_recorded": bool(dirty_promotion.get("target_review_human_approval_recorded", False)),
                "target_review_missing_evidence_count": int(
                    dirty_promotion.get("target_review_missing_evidence_count", target_review_gap.get("missing_evidence_count", len(target_missing_evidence))) or 0
                ),
                "target_review_missing_evidence_preview": (
                    list(dirty_promotion.get("target_review_missing_evidence_preview", target_missing_evidence))[:8]
                    if isinstance(dirty_promotion.get("target_review_missing_evidence_preview", target_missing_evidence), list)
                    else list(target_missing_evidence)[:8]
                ),
                "target_review_required_evidence_preview": list(target_required_evidence)[:8],
                "target_review_decision_prompt_preview": (
                    list(target_review_batch.get("decision_prompts", []))[:8]
                    if isinstance(target_review_batch.get("decision_prompts"), list)
                    else []
                ),
                "target_review_receipt_command_template": str(dirty_promotion.get("target_review_receipt_command_template", "")),
                "target_review_approval_receipt_command_template": str(
                    dirty_promotion.get("target_review_approval_receipt_command_template", "")
                ),
                "target_review_receipt_command_policy": str(dirty_promotion.get("target_review_receipt_command_policy", "")),
                "target_review_operator_command_handoff": (
                    list(dirty_promotion.get("target_review_operator_command_handoff", []))[:2]
                    if isinstance(dirty_promotion.get("target_review_operator_command_handoff"), list)
                    else []
                ),
                "target_review_pending_human_approval_only": bool(dirty_promotion.get("target_review_pending_human_approval_only", False)),
                "target_review_human_approval_gate": str(dirty_promotion.get("target_review_human_approval_gate", "human_approval_before_stage_commit_merge")),
                "target_review_human_approval_command_handoff": (
                    list(dirty_promotion.get("target_review_human_approval_command_handoff", []))[:1]
                    if isinstance(dirty_promotion.get("target_review_human_approval_command_handoff"), list)
                    else []
                ),
                "target_review_focused_test_command_handoff": (
                    list(dirty_promotion.get("target_review_focused_test_command_handoff", []))[:5]
                    if isinstance(dirty_promotion.get("target_review_focused_test_command_handoff"), list)
                    else []
                ),
                "target_review_focused_test_command_count": int(target_review_batch.get("focused_test_command_count", 0) or 0),
                "target_review_focused_test_command_preview": (
                    list(target_review_batch.get("focused_test_commands", []))[:5]
                    if isinstance(target_review_batch.get("focused_test_commands"), list)
                    else []
                ),
                "target_review_sample_preview": (
                    list(target_review_batch.get("sample", []))[:5]
                    if isinstance(target_review_batch.get("sample"), list)
                    else []
                ),
                "target_review_promotion_allowed_after_receipt": bool(target_review_batch.get("promotion_allowed_after_receipt", False)),
                "target_review_merge_policy": str(dirty_promotion.get("target_review_merge_policy", "preserve_existing_evidence_when_dirty_signature_and_target_match")),
                "target_review_previous_evidence_merged": bool(dirty_promotion.get("target_review_previous_evidence_merged", False)),
                "target_review_reset_evidence": bool(dirty_promotion.get("target_review_reset_evidence", False)),
                "evidence_review_matrix_preview": [
                    {
                        "group": str(item.get("group", "")),
                        "missing_evidence_count": int(item.get("missing_evidence_count", 0) or 0),
                        "promotion_allowed": bool(item.get("promotion_allowed", False)),
                    }
                    for item in evidence_matrix[:3]
                    if isinstance(item, dict)
                ],
                "no_stage": bool(dirty_promotion.get("no_stage", True)),
                "no_commit": bool(dirty_promotion.get("no_commit", True)),
                "no_clean": bool(dirty_promotion.get("no_clean", True)),
                "no_branch_or_merge": bool(dirty_promotion.get("no_branch_or_merge", True)),
            })
        elif gate == "unreal_bridge_reachable":
            _append({
                "action_id": "verify_unreal_bridge_reachability",
                "gate": gate,
                "policy_area": "editor_mutation",
                "title": "Open Unreal Editor and prove bridge ping before any editor mutation",
                "recommended_tool": "scripts/bridge_ping.py",
                "recommended_contract": "readiness_policy.editor_mutation",
                "receipt_path": str(bridge.get("bridge_ping_receipt_path", "Saved\\BridgePing\\last_ping_receipt.json")),
                "receipt_state": str(bridge.get("bridge_ping_receipt_state", "missing")),
                "required_command": str(bridge.get("bridge_ping_required_command", "python scripts\\bridge_ping.py")),
                "evidence_required_preview": ["bridge_ping_receipt_success", "successful_bridge_ping", "bridge_ready_true", "editor_target_project_confirmed"],
                "bridge_host": str(bridge.get("host", "127.0.0.1")),
                "bridge_port": int(bridge.get("port", 0) or 0),
                "requires_bridge": True,
                "requires_unreal_editor": True,
            })
        elif gate == "blueprint_pre_read_evidence":
            _append({
                "action_id": "record_blueprint_pre_read_evidence",
                "gate": gate,
                "policy_area": "blueprint_mutation",
                "title": "Inspect target Blueprint before graph or component mutation",
                "recommended_tool": "chat_get_cockpit_overview",
                "recommended_contract": "readiness_policy.blueprint_mutation",
                "evidence_required_preview": ["blueprint_pre_read", "target_blueprint_path", "existing_graph_or_component_state"],
                "review_steps": [
                    "Use the Blueprint mutation gate in MCP Chat to identify the target asset and intended change.",
                    "After bridge ping is proven, capture existing graph/component state with read-only Blueprint tools.",
                    "Record the pre-read evidence in the companion ledger before queue execution.",
                ],
                "receipt_path": str(blueprint_evidence.get("path", "Saved\\BlueprintMutationEvidence\\last_review_receipt.json")),
                "receipt_state": str(blueprint_evidence.get("state", "missing")),
                "required_command": str(blueprint_evidence.get("required_command", "python scripts\\write_blueprint_mutation_evidence_review.py")),
                "receipt_command_template": (
                    'python scripts\\write_blueprint_mutation_evidence_review.py --pre-read-evidence-recorded '
                    '--target-blueprint-path "<target Blueprint asset path>" '
                    '--intended-mutation-summary "<intended Blueprint change>" '
                    '--pre-read-summary "<read-only graph/component state summary>"'
                ),
                "operator_command_handoff": _blueprint_handoff("record_blueprint_pre_read_evidence"),
                "pre_read_evidence_recorded": bool(blueprint_evidence.get("pre_read_evidence_recorded", False)),
                "compile_plan_recorded": bool(blueprint_evidence.get("compile_plan_recorded", False)),
                "readback_plan_recorded": bool(blueprint_evidence.get("readback_plan_recorded", False)),
                "requires_bridge": True,
                "requires_unreal_editor": True,
                "no_blueprint_mutation": True,
            })
        elif gate == "blueprint_compile_plan":
            _append({
                "action_id": "prepare_blueprint_compile_plan",
                "gate": gate,
                "policy_area": "blueprint_mutation",
                "title": "Define the compile check required after Blueprint mutation",
                "recommended_tool": "chat_get_cockpit_overview",
                "recommended_contract": "readiness_policy.blueprint_mutation",
                "evidence_required_preview": ["compile_check_after_mutation", "compile_tool_or_bridge_command", "failure_repair_plan"],
                "review_steps": [
                    "Name the compile command or MCP wrapper that will run after mutation.",
                    "Define the failure evidence to capture if compile fails.",
                    "Record the compile plan before executing queued Blueprint writes.",
                ],
                "receipt_path": str(blueprint_evidence.get("path", "Saved\\BlueprintMutationEvidence\\last_review_receipt.json")),
                "receipt_state": str(blueprint_evidence.get("state", "missing")),
                "required_command": str(blueprint_evidence.get("required_command", "python scripts\\write_blueprint_mutation_evidence_review.py")),
                "receipt_command_template": (
                    'python scripts\\write_blueprint_mutation_evidence_review.py --compile-plan-recorded '
                    '--compile-plan-summary "<compile command and failure repair plan>"'
                ),
                "operator_command_handoff": _blueprint_handoff("record_blueprint_compile_plan"),
                "pre_read_evidence_recorded": bool(blueprint_evidence.get("pre_read_evidence_recorded", False)),
                "compile_plan_recorded": bool(blueprint_evidence.get("compile_plan_recorded", False)),
                "readback_plan_recorded": bool(blueprint_evidence.get("readback_plan_recorded", False)),
                "requires_bridge": False,
                "requires_unreal_editor": False,
                "no_blueprint_mutation": True,
            })
        elif gate == "blueprint_readback_plan":
            _append({
                "action_id": "prepare_blueprint_readback_plan",
                "gate": gate,
                "policy_area": "blueprint_mutation",
                "title": "Define graph or component readback proof after Blueprint mutation",
                "recommended_tool": "chat_get_cockpit_overview",
                "recommended_contract": "readiness_policy.blueprint_mutation",
                "evidence_required_preview": ["graph_or_component_readback_after_mutation", "expected_node_or_component_state", "ledger_evidence_row"],
                "review_steps": [
                    "Name the graph, component, or property readback that proves the mutation landed.",
                    "Define the expected state before execution.",
                    "Record the readback plan before queued Blueprint writes.",
                ],
                "receipt_path": str(blueprint_evidence.get("path", "Saved\\BlueprintMutationEvidence\\last_review_receipt.json")),
                "receipt_state": str(blueprint_evidence.get("state", "missing")),
                "required_command": str(blueprint_evidence.get("required_command", "python scripts\\write_blueprint_mutation_evidence_review.py")),
                "receipt_command_template": (
                    'python scripts\\write_blueprint_mutation_evidence_review.py --readback-plan-recorded '
                    '--readback-plan-summary "<expected graph/component readback proof>"'
                ),
                "operator_command_handoff": _blueprint_handoff("record_blueprint_readback_plan"),
                "pre_read_evidence_recorded": bool(blueprint_evidence.get("pre_read_evidence_recorded", False)),
                "compile_plan_recorded": bool(blueprint_evidence.get("compile_plan_recorded", False)),
                "readback_plan_recorded": bool(blueprint_evidence.get("readback_plan_recorded", False)),
                "requires_bridge": False,
                "requires_unreal_editor": False,
                "no_blueprint_mutation": True,
            })
        else:
            _append({
                "action_id": f"resolve_{gate}",
                "gate": gate,
                "policy_area": "readiness",
                "title": f"Resolve readiness gate {gate}",
                "recommended_tool": "scripts/audit_ide_companion_readiness.py",
                "recommended_contract": "readiness_policy",
                "evidence_required_preview": [gate],
            })

    next_action = actions[0] if actions else {}
    return {
        "schema": "unreal_mcp_readiness_repair_queue.v1",
        "state": "ready" if not actions else "blocked",
        "action_count": len(actions),
        "blocking_gate_count": len(unique_gates),
        "blocking_gate_preview": unique_gates[:12],
        "next_action": next_action,
        "action_preview": actions[:12],
        "no_auto_execute": True,
        "no_secret_echo": True,
        "no_git_mutation": True,
        "no_editor_mutation": True,
        "network_required_for_next_action": bool(next_action.get("requires_network", False)) if next_action else False,
        "spend_required_for_next_action": bool(next_action.get("requires_spend", False)) if next_action else False,
        "unreal_editor_required_for_next_action": bool(next_action.get("requires_unreal_editor", False)) if next_action else False,
        "recommended_next": str(next_action.get("action_id", "none")) if next_action else "none",
        "next_gate": str(next_action.get("gate", "")) if next_action else "",
        "next_policy_area": str(next_action.get("policy_area", "")) if next_action else "",
        "next_tool": str(next_action.get("recommended_tool", "")) if next_action else "",
        "next_operator_command_handoff": (
            (
                list(next_action.get("target_review_human_approval_command_handoff", []))[:1]
                if (
                    next_action.get("target_review_pending_human_approval_only")
                    and isinstance(next_action.get("target_review_human_approval_command_handoff"), list)
                )
                else []
            )
            or (
                list(next_action.get("operator_command_handoff", []))[:2]
                if isinstance(next_action.get("operator_command_handoff"), list)
                else []
            )
            or (
                list(next_action.get("target_review_operator_command_handoff", []))[:2]
                if isinstance(next_action.get("target_review_operator_command_handoff"), list)
                else []
            )
            if next_action
            else []
        ),
        "next_target_review_group": str(next_action.get("target_review_group", "")) if next_action else "",
        "next_target_review_order": int(next_action.get("target_review_order", 0) or 0) if next_action else 0,
        "next_target_review_scope": str(next_action.get("target_review_scope", "")) if next_action else "",
        "next_target_review_tracked_count": int(next_action.get("target_review_tracked_count", 0) or 0) if next_action else 0,
        "next_target_review_untracked_count": int(next_action.get("target_review_untracked_count", 0) or 0) if next_action else 0,
        "next_target_review_status": str(next_action.get("target_review_status", "")) if next_action else "",
        "next_target_review_evidence_complete": bool(next_action.get("target_review_evidence_complete", False)) if next_action else False,
        "next_target_review_recorded_evidence_count": int(next_action.get("target_review_recorded_evidence_count", 0) or 0) if next_action else 0,
        "next_target_review_recorded_evidence_preview": (
            list(next_action.get("target_review_recorded_evidence_preview", []))[:8]
            if next_action and isinstance(next_action.get("target_review_recorded_evidence_preview"), list)
            else []
        ),
        "next_target_review_human_approval_recorded": bool(next_action.get("target_review_human_approval_recorded", False)) if next_action else False,
        "next_target_review_missing_evidence_count": int(next_action.get("target_review_missing_evidence_count", 0) or 0) if next_action else 0,
        "next_target_review_missing_evidence_preview": (
            list(next_action.get("target_review_missing_evidence_preview", []))[:8]
            if next_action and isinstance(next_action.get("target_review_missing_evidence_preview"), list)
            else []
        ),
        "next_target_review_required_evidence_preview": (
            list(next_action.get("target_review_required_evidence_preview", []))[:8]
            if next_action and isinstance(next_action.get("target_review_required_evidence_preview"), list)
            else []
        ),
        "next_target_review_decision_prompt_preview": (
            list(next_action.get("target_review_decision_prompt_preview", []))[:8]
            if next_action and isinstance(next_action.get("target_review_decision_prompt_preview"), list)
            else []
        ),
        "next_target_review_receipt_command_template": (
            str(next_action.get("target_review_receipt_command_template", "")) if next_action else ""
        ),
        "next_target_review_approval_receipt_command_template": (
            str(next_action.get("target_review_approval_receipt_command_template", "")) if next_action else ""
        ),
        "next_target_review_receipt_command_policy": (
            str(next_action.get("target_review_receipt_command_policy", "")) if next_action else ""
        ),
        "next_target_review_operator_command_handoff": (
            list(next_action.get("target_review_operator_command_handoff", []))[:2]
            if next_action and isinstance(next_action.get("target_review_operator_command_handoff"), list)
            else []
        ),
        "next_target_review_pending_human_approval_only": bool(next_action.get("target_review_pending_human_approval_only", False)) if next_action else False,
        "next_target_review_human_approval_gate": str(next_action.get("target_review_human_approval_gate", "")) if next_action else "",
        "next_target_review_human_approval_command_handoff": (
            list(next_action.get("target_review_human_approval_command_handoff", []))[:1]
            if next_action and isinstance(next_action.get("target_review_human_approval_command_handoff"), list)
            else []
        ),
        "next_target_review_focused_test_command_handoff": (
            list(next_action.get("target_review_focused_test_command_handoff", []))[:5]
            if next_action and isinstance(next_action.get("target_review_focused_test_command_handoff"), list)
            else []
        ),
        "next_target_review_focused_test_command_count": int(next_action.get("target_review_focused_test_command_count", 0) or 0) if next_action else 0,
        "next_target_review_focused_test_command_preview": (
            list(next_action.get("target_review_focused_test_command_preview", []))[:5]
            if next_action and isinstance(next_action.get("target_review_focused_test_command_preview"), list)
            else []
        ),
        "next_target_review_sample_preview": (
            list(next_action.get("target_review_sample_preview", []))[:5]
            if next_action and isinstance(next_action.get("target_review_sample_preview"), list)
            else []
        ),
        "next_target_review_promotion_allowed_after_receipt": (
            bool(next_action.get("target_review_promotion_allowed_after_receipt", False)) if next_action else False
        ),
        "next_target_review_merge_policy": str(next_action.get("target_review_merge_policy", "")) if next_action else "",
        "next_target_review_previous_evidence_merged": bool(next_action.get("target_review_previous_evidence_merged", False)) if next_action else False,
        "next_target_review_reset_evidence": bool(next_action.get("target_review_reset_evidence", False)) if next_action else False,
        "priority_policy": "chat_health_then_wip_promotion_safety_then_bridge_proof_then_paid_provider_gates",
    }


def build_report(
    *,
    bridge_host: str = "127.0.0.1",
    bridge_port: int = 55655,
    chat_url: str = "http://127.0.0.1:8000",
    timeout_s: float = 2.0,
) -> Dict[str, Any]:
    runtime = _runtime_status()
    tool_inventory = _tool_inventory_status()
    bridge = _tcp_reachable(bridge_host, bridge_port, timeout_s)
    bridge_ping_receipt = _bridge_ping_receipt_status()
    bridge.update({
        "tcp_ready": bool(bridge.get("ready", False)),
        "receipt": bridge_ping_receipt,
        "bridge_ping_receipt_exists": bool(bridge_ping_receipt.get("receipt_exists", False)),
        "bridge_ping_receipt_state": str(bridge_ping_receipt.get("state", "missing")),
        "bridge_ping_receipt_path": str(bridge_ping_receipt.get("path", "Saved\\BridgePing\\last_ping_receipt.json")),
        "bridge_ping_required_command": str(bridge_ping_receipt.get("required_command", "python scripts\\bridge_ping.py")),
        "bridge_ping_operator_command_handoff": (
            list(bridge_ping_receipt.get("operator_command_handoff", []))[:1]
            if isinstance(bridge_ping_receipt.get("operator_command_handoff"), list)
            else []
        ),
        "bridge_ping_operator_command_handoff_ids": (
            list(bridge_ping_receipt.get("operator_command_handoff_ids", []))[:1]
            if isinstance(bridge_ping_receipt.get("operator_command_handoff_ids"), list)
            else []
        ),
        "bridge_ping_operator_command_handoff_count": int(bridge_ping_receipt.get("operator_command_handoff_count", 0) or 0),
        "successful_bridge_ping": bool(bridge_ping_receipt.get("successful_bridge_ping", False)),
        "ready": bool(bridge.get("ready", False)) and bool(bridge_ping_receipt.get("successful_bridge_ping", False)),
    })
    chat = _chat_status(chat_url, timeout_s)
    chat_repair = _chat_cockpit_repair_contract(chat)
    provider = _provider_config_status()
    git = _git_status()
    dirty_promotion = _dirty_promotion_contract(git)
    build = _build_status()
    test_lanes = _test_lane_status()
    no_mutation_tests = _no_mutation_test_status()
    high_value_wrapper_coverage = _high_value_wrapper_coverage_status()
    blueprint_mutation_evidence = _blueprint_mutation_evidence_review_receipt_status()
    blocking_gates = []
    if not tool_inventory["matches_recorded_count"] or tool_inventory["missing_category_modules"]:
        blocking_gates.append("tool_registry_reproducible")
    if not bridge["ready"]:
        blocking_gates.append("unreal_bridge_reachable")
    if not chat["ready"]:
        blocking_gates.append("chat_server_reachable")
    if not provider["api_key_configured"]:
        blocking_gates.append("provider_api_key_configured")
    if not provider.get("uthana_api_key_configured", False):
        blocking_gates.append("animation_provider_api_key_configured")
    readiness_policy = _build_readiness_policy(
        tool_inventory=tool_inventory,
        bridge=bridge,
        chat=chat,
        provider=provider,
        git=git,
        build=build,
        test_lanes=test_lanes,
        no_mutation_tests=no_mutation_tests,
        high_value_wrapper_coverage=high_value_wrapper_coverage,
    )
    platform_stability_review = _platform_stability_review_receipt_status()
    for paid_policy_name in ("paid_generation", "paid_animation_generation"):
        paid_policy = readiness_policy.get(paid_policy_name, {})
        for gate in paid_policy.get("missing_gates", []):
            if gate not in blocking_gates:
                blocking_gates.append(gate)
    platform_stability = readiness_policy.get("platform_stability", {})
    for gate in platform_stability.get("missing_gates", []):
        if gate not in blocking_gates:
            blocking_gates.append(gate)
    wip_promotion = readiness_policy.get("wip_promotion", {})
    for gate in wip_promotion.get("missing_gates", []):
        if gate not in blocking_gates:
            blocking_gates.append(gate)
    blueprint_mutation = readiness_policy.get("blueprint_mutation", {})
    for gate in blueprint_mutation.get("missing_gates", []):
        if gate not in blocking_gates:
            blocking_gates.append(gate)
    paid_generation_evidence = _paid_generation_evidence_contract(provider)
    readiness_repair_queue = _readiness_repair_queue(
        blocking_gates=blocking_gates,
        bridge=bridge,
        chat_repair=chat_repair,
        provider=provider,
        paid_generation_evidence=paid_generation_evidence,
        dirty_promotion=dirty_promotion,
    )
    return {
        "schema": "unreal_mcp_ide_companion_preflight.v1",
        "tool_count": int(tool_inventory.get("tool_count", 0) or 0),
        "recorded_tool_count": int(tool_inventory.get("recorded_count", 0) or 0),
        "partial_tool_count": int(tool_inventory.get("partial_tools", 0) or 0),
        "tool_registry_reproducible": (
            bool(tool_inventory.get("matches_recorded_count", False))
            and not bool(tool_inventory.get("missing_category_modules", []))
        ),
        "ready_for_editor_mutation": bool(readiness_policy["editor_mutation"]["allowed"]),
        "ready_for_paid_generation": bool(readiness_policy["paid_generation"]["allowed"]),
        "ready_for_paid_animation_generation": bool(readiness_policy["paid_animation_generation"]["allowed"]),
        "ready_for_blueprint_mutation": bool(readiness_policy["blueprint_mutation"]["allowed"]),
        "ready_for_chat_cockpit": bool(readiness_policy["chat_cockpit"]["allowed"]),
        "ready_for_platform_stability": bool(readiness_policy["platform_stability"]["allowed"]),
        "ready_for_wip_promotion": bool(readiness_policy["wip_promotion"]["allowed"]),
        "blocking_gates": blocking_gates,
        "runtime": runtime,
        "tool_inventory": tool_inventory,
        "bridge": bridge,
        "chat": chat,
        "chat_cockpit_repair_contract": chat_repair,
        "provider_config": provider,
        "paid_generation_evidence": paid_generation_evidence,
        "blueprint_mutation_evidence": blueprint_mutation_evidence,
        "blueprint_mutation_evidence_receipt_exists": bool(blueprint_mutation_evidence.get("receipt_exists", False)),
        "blueprint_mutation_evidence_receipt_state": str(blueprint_mutation_evidence.get("state", "missing")),
        "blueprint_mutation_evidence_receipt_path": str(blueprint_mutation_evidence.get("path", "Saved\\BlueprintMutationEvidence\\last_review_receipt.json")),
        "blueprint_mutation_evidence_receipt_required_command": str(
            blueprint_mutation_evidence.get("required_command", "python scripts\\write_blueprint_mutation_evidence_review.py")
        ),
        "blueprint_mutation_operator_command_handoff": (
            list(blueprint_mutation_evidence.get("operator_command_handoff", []))[:3]
            if isinstance(blueprint_mutation_evidence.get("operator_command_handoff"), list)
            else []
        ),
        "readiness_repair_queue": readiness_repair_queue,
        "dirty_promotion_contract": dirty_promotion,
        "platform_stability_review": platform_stability_review,
        "platform_stability_review_receipt_exists": bool(platform_stability_review.get("receipt_exists", False)),
        "platform_stability_review_receipt_state": str(platform_stability_review.get("state", "missing")),
        "platform_stability_review_receipt_path": str(platform_stability_review.get("path", "Saved\\PlatformStabilityReview\\last_review_receipt.json")),
        "platform_stability_review_receipt_required_command": str(platform_stability_review.get("required_command", "python scripts\\write_platform_stability_review.py")),
        "test_lanes": test_lanes,
        "no_mutation_tests": no_mutation_tests,
        "high_value_wrapper_coverage": high_value_wrapper_coverage,
        "readiness_policy": readiness_policy,
        "git": git,
        "build": build,
        "network_required": False,
        "spend_required": False,
        "unreal_editor_required": False,
    }


def format_text(report: Dict[str, Any]) -> str:
    policy = report["readiness_policy"]
    editor_missing = policy["editor_mutation"]["missing_gates"]
    paid_missing = policy["paid_generation"]["missing_gates"]
    animation_paid_missing = policy["paid_animation_generation"]["missing_gates"]
    blueprint_missing = policy["blueprint_mutation"]["missing_gates"]
    platform_missing = policy.get("platform_stability", {}).get("missing_gates", [])
    wip_promotion_missing = policy.get("wip_promotion", {}).get("missing_gates", [])
    branch_policy = policy.get("branch_policy", {})
    branch = report["git"].get("branch", {}) if isinstance(report["git"].get("branch"), dict) else {}
    bridge_receipt_state = report.get("bridge", {}).get("bridge_ping_receipt_state", "missing")
    bridge_receipt_path = _display_receipt_path(report.get("bridge", {}).get("bridge_ping_receipt_path", "Saved\\BridgePing\\last_ping_receipt.json"))
    chat_receipt_state = report.get("chat", {}).get("startup_receipt_state", "missing")
    chat_receipt_path = _display_receipt_path(report.get("chat", {}).get("startup_receipt_path", "Saved\\ChatCockpit\\last_start_receipt.json"))
    provider_receipt_state = report.get("provider_config", {}).get("review_receipt_state", "missing")
    provider_receipt_path = _display_receipt_path(report.get("provider_config", {}).get("review_receipt_path", "Saved\\ProviderConfigReview\\last_review_receipt.json"))
    paid_generation = report.get("paid_generation_evidence", {}) if isinstance(report.get("paid_generation_evidence"), dict) else {}
    paid_receipt_state = paid_generation.get("review_receipt_state", "missing")
    paid_receipt_path = _display_receipt_path(paid_generation.get("review_receipt_path", "Saved\\PaidGenerationEvidence\\last_review_receipt.json"))
    blueprint_evidence = report.get("blueprint_mutation_evidence", {}) if isinstance(report.get("blueprint_mutation_evidence"), dict) else {}
    blueprint_receipt_state = blueprint_evidence.get("state", "missing")
    blueprint_receipt_path = _display_receipt_path(blueprint_evidence.get("path", "Saved\\BlueprintMutationEvidence\\last_review_receipt.json"))
    dirty_promotion = report.get("dirty_promotion_contract", {}) if isinstance(report.get("dirty_promotion_contract"), dict) else {}
    dirty_receipt_state = dirty_promotion.get("review_receipt_state", "missing")
    dirty_receipt_path = _display_receipt_path(dirty_promotion.get("review_receipt_path", "Saved\\DirtyPromotionReview\\last_review_receipt.json"))
    no_mutation = report.get("no_mutation_tests", {}) if isinstance(report.get("no_mutation_tests"), dict) else {}
    no_mutation_receipt_state = no_mutation.get("state", "missing")
    no_mutation_receipt_path = _display_receipt_path(no_mutation.get("receipt_path", "Saved\\NoMutationTest\\last_run_receipt.json"))
    build = report.get("build", {}) if isinstance(report.get("build"), dict) else {}
    plugin_build_receipt_state = build.get("last_plugin_build_status", "unknown")
    plugin_build_receipt_path = _display_receipt_path(build.get("local_build_receipt_path", "Saved\\PluginBuildSmoke\\last_build_receipt.json"))
    platform_receipt_path = _display_receipt_path(report.get("platform_stability_review_receipt_path", "Saved\\PlatformStabilityReview\\last_review_receipt.json"))
    repair_queue = report.get("readiness_repair_queue", {}) if isinstance(report.get("readiness_repair_queue"), dict) else {}
    next_repair = repair_queue.get("next_action", {}) if isinstance(repair_queue.get("next_action"), dict) else {}
    next_repair_id = str(repair_queue.get("recommended_next", "none"))
    next_repair_gate = str(next_repair.get("gate", "none"))
    next_repair_tool = str(next_repair.get("recommended_tool", ""))
    next_repair_command = str(next_repair.get("required_command") or next_repair.get("proof_command") or next_repair.get("receipt_command_template") or "")
    next_repair_detail = next_repair_tool
    if next_repair_command:
        next_repair_detail = f"{next_repair_tool}; {next_repair_command}" if next_repair_tool else next_repair_command
    next_repair_evidence_line = ""
    next_matrix_count = int(next_repair.get("evidence_review_matrix_count", 0) or 0)
    next_unresolved_count = int(next_repair.get("evidence_unresolved_count", 0) or 0)
    if next_matrix_count or next_unresolved_count:
        next_repair_evidence_line = (
            f"- Next repair evidence: {next_unresolved_count} unresolved item(s) "
            f"across {next_matrix_count} batch(es)"
        )
    next_repair_target_line = ""
    next_target_group = str(next_repair.get("target_review_group", "")).strip()
    if next_target_group:
        next_target_scope = str(next_repair.get("target_review_scope", "")).strip()
        next_missing_count = int(next_repair.get("target_review_missing_evidence_count", 0) or 0)
        next_focused_count = int(next_repair.get("target_review_focused_test_command_count", 0) or 0)
        next_sample_count = len(next_repair.get("target_review_sample_preview", [])) if isinstance(next_repair.get("target_review_sample_preview"), list) else 0
        next_repair_target_line = (
            f"- Next repair target: {next_target_group}"
            f"{f' ({next_target_scope})' if next_target_scope else ''}; "
            f"missing evidence {next_missing_count}; focused tests {next_focused_count}; sample paths {next_sample_count}"
        )
    lines = [
        "# IDE Companion Preflight",
        "",
        f"- Schema: {report['schema']}",
        f"- Ready for editor mutation: {report['ready_for_editor_mutation']}",
        f"- Ready for paid generation: {report['ready_for_paid_generation']}",
        f"- Ready for paid animation generation: {report['ready_for_paid_animation_generation']}",
        f"- Ready for Blueprint mutation: {report['ready_for_blueprint_mutation']}",
        f"- Ready for chat cockpit: {report['ready_for_chat_cockpit']}",
        f"- Ready for platform stability: {report['ready_for_platform_stability']}",
        f"- Ready for WIP promotion: {report.get('ready_for_wip_promotion', False)}",
        f"- Bridge ping receipt: {bridge_receipt_state} ({bridge_receipt_path})",
        f"- Chat cockpit startup receipt: {chat_receipt_state} ({chat_receipt_path})",
        f"- Provider config review receipt: {provider_receipt_state} ({provider_receipt_path})",
        f"- Paid generation evidence receipt: {paid_receipt_state} ({paid_receipt_path})",
        f"- Blueprint mutation evidence receipt: {blueprint_receipt_state} ({blueprint_receipt_path})",
        f"- Dirty promotion review receipt: {dirty_receipt_state} ({dirty_receipt_path})",
        f"- No-mutation test receipt: {no_mutation_receipt_state} ({no_mutation_receipt_path})",
        f"- Plugin build receipt: {plugin_build_receipt_state} ({plugin_build_receipt_path})",
        f"- Platform stability review receipt: {report.get('platform_stability_review_receipt_state', 'missing')} ({platform_receipt_path})",
        f"- Blocking gates: {', '.join(report['blocking_gates']) if report['blocking_gates'] else 'none'}",
        f"- Editor mutation missing gates: {', '.join(editor_missing) if editor_missing else 'none'}",
        f"- Paid generation missing gates: {', '.join(paid_missing) if paid_missing else 'none'}",
        f"- Paid animation generation missing gates: {', '.join(animation_paid_missing) if animation_paid_missing else 'none'}",
        f"- Blueprint mutation missing gates: {', '.join(blueprint_missing) if blueprint_missing else 'none'}",
        f"- Platform stability missing gates: {', '.join(platform_missing) if platform_missing else 'none'}",
        f"- WIP promotion missing gates: {', '.join(wip_promotion_missing) if wip_promotion_missing else 'none'}",
        f"- Branch policy: {'ready' if branch_policy.get('allowed') else 'blocked'} ({branch.get('current', 'unknown')} -> {branch.get('role', 'unknown')})",
        f"- Next repair: {next_repair_id} ({next_repair_gate})" + (f" via {next_repair_detail}" if next_repair_detail else ""),
        *([next_repair_target_line] if next_repair_target_line else []),
        *([next_repair_evidence_line] if next_repair_evidence_line else []),
        f"- Repair priority: {repair_queue.get('priority_policy', 'chat_health_then_wip_promotion_safety_then_bridge_proof_then_paid_provider_gates')}",
        "",
        f"Python: {report['runtime']['python_version']} at {report['runtime']['python_executable']}",
        f"Tools: {report['tool_inventory']['tool_count']} registered, {report['tool_inventory']['partial_tools']} partial, recorded count {report['tool_inventory']['recorded_count']}",
        f"Bridge: {'ready' if report['bridge']['ready'] else 'offline'} at {report['bridge']['host']}:{report['bridge']['port']}",
        f"Chat: {'ready' if report['chat']['ready'] else 'offline'} at {report['chat']['url']}",
        f"Provider key: {report['provider_config']['api_key_source']}",
        f"Animation provider key: {report['provider_config'].get('uthana_api_key_source', 'missing')}",
        (
            f"Test lanes: {'safe' if report.get('test_lanes', {}).get('ok') else 'attention'} "
            f"(offline {report.get('test_lanes', {}).get('offline_count', 0)}, "
            f"live bridge {report.get('test_lanes', {}).get('live_bridge_count', 0)}, "
            f"paid provider {report.get('test_lanes', {}).get('paid_provider_count', 0)}, "
            f"violations {report.get('test_lanes', {}).get('violation_count', 0)})"
        ),
        (
            f"No-mutation tests: {report.get('no_mutation_tests', {}).get('status', 'missing')} "
            f"(mutations {report.get('no_mutation_tests', {}).get('mutation_count', 'unknown')}, "
            f"exit {report.get('no_mutation_tests', {}).get('test_exit_code', 'unknown')})"
        ),
        (
            f"Dirty files: {report['git']['dirty_count']} "
            f"({report['git']['dirty_risk']}; tracked {report['git']['tracked_change_count']}, "
            f"untracked {report['git']['untracked_count']})"
        ),
        (
            f"Build: wrapper {'present' if report['build']['build_wrapper_exists'] else 'missing'}, "
            f"references {str(report['build']['build_wrapper_status']).replace('_', ' ')}, "
            f"last plugin build {report['build']['last_plugin_build_status']}, "
            f"warnings {report['build'].get('last_plugin_build_warning_count', 0)} "
            f"({report['build'].get('last_plugin_build_warning_severity', 'unknown')})"
        ),
    ]
    return "\n".join(lines)


def _display_receipt_path(path_value: Any) -> str:
    text = str(path_value or "").strip()
    if not text:
        return ""
    path = Path(text)
    try:
        if path.is_absolute():
            return str(path.resolve().relative_to(REPO_ROOT)).replace("/", "\\")
    except (OSError, ValueError):
        return text
    return text.replace("/", "\\")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a no-mutation IDE companion readiness preflight.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=55655)
    parser.add_argument("--chat-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=2.0)
    args = parser.parse_args()

    report = build_report(
        bridge_host=args.bridge_host,
        bridge_port=args.bridge_port,
        chat_url=args.chat_url,
        timeout_s=max(0.1, args.timeout),
    )
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else format_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
