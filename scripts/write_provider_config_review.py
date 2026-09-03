"""Write an ignored provider-config review receipt without exposing secrets."""

from __future__ import annotations

import argparse
import importlib.util
import json
import time
from pathlib import Path
from typing import Any, Dict


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_SCRIPT_PATH = REPO_ROOT / "scripts" / "audit_ide_companion_readiness.py"
DEFAULT_RECEIPT_PATH = Path("Saved") / "ProviderConfigReview" / "last_review_receipt.json"


def _load_audit_module():
    spec = importlib.util.spec_from_file_location("audit_ide_companion_readiness", AUDIT_SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {AUDIT_SCRIPT_PATH}")
    spec.loader.exec_module(module)
    return module


def build_receipt() -> Dict[str, Any]:
    audit = _load_audit_module()
    provider = audit._provider_config_status()
    tripo_ready = bool(provider.get("api_key_configured", False))
    uthana_ready = bool(provider.get("uthana_api_key_configured", False))
    return {
        "schema": "unreal_mcp_provider_config_review_receipt.v1",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "ready" if tripo_ready and uthana_ready else "missing_keys",
        "provider": str(provider.get("provider", "tripo")),
        "animation_provider": str(provider.get("animation_provider", "uthana")),
        "api_key_configured": tripo_ready,
        "api_key_source": str(provider.get("api_key_source", "missing")),
        "uthana_api_key_configured": uthana_ready,
        "uthana_api_key_source": str(provider.get("uthana_api_key_source", "missing")),
        "settings_exists": bool(provider.get("settings_exists", False)),
        "secrets_exists": bool(provider.get("secrets_exists", False)),
        "settings_gitignored": bool(provider.get("settings_gitignored", False)),
        "secrets_gitignored": bool(provider.get("secrets_gitignored", False)),
        "output_folder": str(provider.get("output_folder", "/Game/Generated")),
        "animation_output_folder": str(provider.get("animation_output_folder", "/Game/Generated/Animations")),
        "session_credit_budget": int(provider.get("session_credit_budget", 1000) or 1000),
        "required_evidence": [
            "masked_provider_auth_source",
            "raw_key_absent_from_outputs",
            "wallet_or_allowance_evidence_recorded_separately",
            "explicit_spend_or_usage_confirmation_recorded_separately",
        ],
        "repair_contract": provider.get("repair_contract", {}) if isinstance(provider.get("repair_contract"), dict) else {},
        "secret_contract": {
            "raw_key_returned": False,
            "masked_status_only": True,
            "secrets_gitignored": bool(provider.get("secrets_gitignored", False)),
            "settings_gitignored": bool(provider.get("settings_gitignored", False)),
            "secret_storage": "env vars or ignored Saved/MCPChat/secrets.json",
        },
        "no_raw_key": True,
        "no_provider_call": True,
        "no_wallet_check": True,
        "no_credit_reservation": True,
        "no_spend_confirmation": True,
        "no_editor_mutation": True,
        "no_git_mutation": True,
        "network_required": False,
        "spend_required": False,
        "unreal_editor_required": False,
    }


def write_receipt(path: Path, receipt: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a masked provider-config review receipt.")
    parser.add_argument("--receipt-path", default=str(DEFAULT_RECEIPT_PATH), help="ignored local JSON receipt path")
    args = parser.parse_args()

    receipt_path = Path(args.receipt_path)
    if not receipt_path.is_absolute():
        receipt_path = REPO_ROOT / receipt_path
    receipt = build_receipt()
    write_receipt(receipt_path, receipt)
    print(f"PROVIDER_CONFIG_RECEIPT={args.receipt_path}")
    print(f"PROVIDER_CONFIG_STATUS={receipt['status']}")
    print(f"TRIPO_CONFIGURED={receipt['api_key_configured']}")
    print(f"UTHANA_CONFIGURED={receipt['uthana_api_key_configured']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
