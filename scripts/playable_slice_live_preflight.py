#!/usr/bin/env python3
"""No-spend preflight for a live Tripo + Unreal playable-slice run."""

from __future__ import annotations

import argparse
import json
import os
import socket
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_SETTINGS = {
    "provider": "tripo",
    "default_model_version": "tripo-default",
    "default_texture_quality": "standard",
    "output_folder": "/Game/Generated",
    "session_credit_budget": 1000,
    "credit_usage_by_session": {},
}


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def mask_key(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    return f"{value[:4]}...{value[-4:]}" if len(value) >= 8 else "configured"


def resolve_api_key(repo_root: Path) -> Dict[str, Any]:
    env_key = os.environ.get("TRIPO_API_KEY", "").strip()
    if env_key:
        return {"configured": True, "source": "env:TRIPO_API_KEY", "masked": mask_key(env_key)}

    secrets_path = repo_root / "Saved" / "MCPChat" / "secrets.json"
    secrets = read_json(secrets_path)
    stored_key = str(secrets.get("TRIPO_API_KEY") or secrets.get("tripo_api_key") or "").strip()
    if stored_key:
        return {"configured": True, "source": str(secrets_path), "masked": mask_key(stored_key)}
    return {"configured": False, "source": "missing", "masked": ""}


def load_settings(repo_root: Path) -> Dict[str, Any]:
    settings = dict(DEFAULT_SETTINGS)
    settings_path = repo_root / "Saved" / "MCPChat" / "generative_settings.json"
    settings.update(read_json(settings_path))
    settings["session_credit_budget"] = safe_int(settings.get("session_credit_budget"), 0)
    usage = settings.get("credit_usage_by_session", {})
    settings["credit_usage_by_session"] = usage if isinstance(usage, dict) else {}
    settings["settings_path"] = str(settings_path)
    return settings


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def find_runuat(engine_root: str = "") -> str:
    roots = [engine_root] if engine_root else [
        r"C:\Program Files\Epic Games\UE_5.6",
        r"C:\Program Files\Epic Games\UE_5.5",
        r"C:\Program Files\Epic Games\UE_5.4",
    ]
    for root in roots:
        if not root:
            continue
        candidate = Path(root) / "Engine" / "Build" / "BatchFiles" / "RunUAT.bat"
        if candidate.exists():
            return str(candidate)
    return ""


def latest_plugin_package(package_root: Path) -> Dict[str, Any]:
    if not package_root.exists():
        return {"found": False, "path": "", "has_descriptor": False, "has_win64_binaries": False}

    candidates = sorted(
        [path for path in package_root.glob("UnrealMCPBuild*") if path.is_dir()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        descriptor = candidate / "UnrealMCP.uplugin"
        binaries = candidate / "Binaries" / "Win64"
        if descriptor.exists() or binaries.exists():
            return {
                "found": descriptor.exists() and binaries.exists(),
                "path": str(candidate),
                "has_descriptor": descriptor.exists(),
                "has_win64_binaries": binaries.exists(),
            }
    return {"found": False, "path": "", "has_descriptor": False, "has_win64_binaries": False}


def check_bridge(host: str, port: int, timeout_s: float) -> Dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return {"reachable": True, "host": host, "port": port}
    except Exception as exc:
        return {"reachable": False, "host": host, "port": port, "error": str(exc)}


def gate(gate_id: str, label: str, passed: bool, observed: List[str], missing: List[str]) -> Dict[str, Any]:
    return {
        "id": gate_id,
        "label": label,
        "status": "ready" if passed else "missing",
        "observed": observed,
        "missing": missing,
    }


def build_preflight(args: argparse.Namespace) -> Dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    settings = load_settings(repo_root)
    key_state = resolve_api_key(repo_root)
    runuat = find_runuat(args.engine_root)
    wrapper = repo_root / "scripts" / "build_unreal_plugin.ps1"
    plugin = repo_root / "unreal_plugin" / "UnrealMCP.uplugin"
    package = latest_plugin_package(Path(args.package_root))
    bridge = check_bridge(args.bridge_host, args.bridge_port, args.bridge_timeout_s)

    session_name = args.session_name
    used = safe_int(settings["credit_usage_by_session"].get(session_name), 0)
    budget = max(0, safe_int(settings.get("session_credit_budget"), 0))
    remaining = max(0, budget - used)
    estimated_credits = max(0, args.estimated_credits)

    gates = [
        gate(
            "tripo_api_key",
            "Tripo API key is configured without exposing the secret",
            bool(key_state["configured"]),
            [key_state["source"]] if key_state["configured"] else [],
            ["TRIPO_API_KEY env var or Saved/MCPChat/secrets.json"] if not key_state["configured"] else [],
        ),
        gate(
            "credit_budget",
            "Session credit budget can cover the estimated playable-slice spend",
            remaining >= estimated_credits and budget > 0,
            [f"budget={budget}", f"used={used}", f"remaining={remaining}", f"estimated={estimated_credits}"],
            [f"remaining credits < estimated credits ({remaining} < {estimated_credits})"] if remaining < estimated_credits else [],
        ),
        gate(
            "unreal_build_tooling",
            "UE BuildPlugin tooling and wrapper are available",
            bool(runuat) and wrapper.exists() and plugin.exists(),
            [item for item in (runuat, str(wrapper) if wrapper.exists() else "", str(plugin) if plugin.exists() else "") if item],
            [
                item for item, ok in (
                    ("RunUAT.bat", bool(runuat)),
                    ("scripts/build_unreal_plugin.ps1", wrapper.exists()),
                    ("unreal_plugin/UnrealMCP.uplugin", plugin.exists()),
                ) if not ok
            ],
        ),
        gate(
            "packaged_plugin",
            "A packaged Win64 UnrealMCP plugin build is available",
            bool(package["found"]),
            [package["path"]] if package["found"] else [],
            [
                item for item, ok in (
                    ("packaged UnrealMCP.uplugin", package["has_descriptor"]),
                    ("packaged Binaries/Win64", package["has_win64_binaries"]),
                ) if not ok
            ],
        ),
        gate(
            "unreal_bridge",
            "Unreal MCP bridge socket is reachable",
            bool(bridge["reachable"]),
            [f"{bridge['host']}:{bridge['port']}"] if bridge["reachable"] else [],
            [f"{bridge['host']}:{bridge['port']}"] if not bridge["reachable"] else [],
        ),
    ]

    ready_for_live_spend = all(item["status"] == "ready" for item in gates)
    next_actions = []
    for item in gates:
        if item["status"] != "ready":
            next_actions.append(f"{item['id']}: {', '.join(item['missing'])}")

    return {
        "schema": "unreal_mcp_playable_slice_live_preflight.v1",
        "ready_for_live_spend": ready_for_live_spend,
        "network_required": False,
        "spend_required": False,
        "repo_root": str(repo_root),
        "settings": {
            "settings_path": settings["settings_path"],
            "output_folder": settings.get("output_folder", ""),
            "default_model_version": settings.get("default_model_version", ""),
            "default_texture_quality": settings.get("default_texture_quality", ""),
            "session_name": session_name,
            "session_credit_budget": budget,
            "session_credits_used": used,
            "session_credits_remaining": remaining,
            "estimated_credits": estimated_credits,
        },
        "api_key": key_state,
        "build": {"runuat": runuat, "wrapper": str(wrapper), "plugin": str(plugin), "package": package},
        "bridge": bridge,
        "gates": gates,
        "next_actions": next_actions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="No-spend readiness check for a live playable-slice run.")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--engine-root", default=os.environ.get("UE_ENGINE_ROOT", ""))
    parser.add_argument("--package-root", default=r"C:\uebuild")
    parser.add_argument("--bridge-host", default=os.environ.get("UNREAL_HOST", "127.0.0.1"))
    parser.add_argument("--bridge-port", type=int, default=int(os.environ.get("UNREAL_PORT", "55557")))
    parser.add_argument("--bridge-timeout-s", type=float, default=1.0)
    parser.add_argument("--session-name", default="playable-slice")
    parser.add_argument("--estimated-credits", type=int, default=120)
    parser.add_argument("--require-ready", action="store_true", help="Exit nonzero when any gate is missing.")
    args = parser.parse_args()

    report = build_preflight(args)
    print(json.dumps(report, indent=2))
    return 0 if report["ready_for_live_spend"] or not args.require_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
