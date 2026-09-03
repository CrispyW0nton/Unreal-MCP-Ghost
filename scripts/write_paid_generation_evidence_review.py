"""Write an ignored paid-generation evidence review receipt without provider calls."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_SCRIPT_PATH = REPO_ROOT / "scripts" / "audit_ide_companion_readiness.py"
DEFAULT_RECEIPT_PATH = Path("Saved") / "PaidGenerationEvidence" / "last_review_receipt.json"
RAW_SECRET_PATTERNS = (
    re.compile(r"tsk_[A-Za-z0-9_\-]{20,}"),
    re.compile(r"\b[0-9a-fA-F]{32,}\b"),
)


def _load_audit_module():
    spec = importlib.util.spec_from_file_location("audit_ide_companion_readiness", AUDIT_SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {AUDIT_SCRIPT_PATH}")
    spec.loader.exec_module(module)
    return module


def build_receipt(
    *,
    previous_receipt: Optional[Dict[str, Any]] = None,
    reset_evidence: bool = False,
    wallet_evidence_recorded: bool = False,
    mesh_wallet_evidence_recorded: bool = False,
    animation_allowance_evidence_recorded: bool = False,
    spend_confirmation_recorded: bool = False,
    explicit_usage_approval_recorded: bool = False,
    wallet_evidence_summary: str = "",
    mesh_wallet_evidence_summary: str = "",
    animation_allowance_summary: str = "",
    spend_confirmation_summary: str = "",
    usage_approval_summary: str = "",
    estimated_spend_reviewed: bool = False,
    estimated_motion_seconds_reviewed: bool = False,
) -> Dict[str, Any]:
    audit = _load_audit_module()
    provider = audit._provider_config_status()
    contract = audit._paid_generation_evidence_contract(provider)
    previous = previous_receipt if isinstance(previous_receipt, dict) and not reset_evidence else {}
    mesh_wallet_recorded = bool(
        mesh_wallet_evidence_recorded
        or wallet_evidence_recorded
        or previous.get("mesh_wallet_evidence_recorded", False)
        or previous.get("wallet_evidence_recorded", False)
    )
    animation_allowance_recorded = bool(
        animation_allowance_evidence_recorded
        or wallet_evidence_recorded
        or previous.get("animation_allowance_evidence_recorded", False)
        or previous.get("wallet_evidence_recorded", False)
    )
    explicit_spend_recorded = bool(spend_confirmation_recorded or previous.get("explicit_spend_approval_recorded", previous.get("spend_confirmation_recorded", False)))
    usage_approval_recorded = bool(
        explicit_usage_approval_recorded
        or spend_confirmation_recorded
        or previous.get("explicit_usage_approval_recorded", previous.get("spend_confirmation_recorded", False))
    )
    combined_wallet_recorded = bool(mesh_wallet_recorded and animation_allowance_recorded)
    combined_spend_recorded = bool(explicit_spend_recorded and usage_approval_recorded)
    estimated_spend = bool(estimated_spend_reviewed or previous.get("estimated_spend_reviewed", False))
    estimated_motion_reviewed = bool(
        estimated_motion_seconds_reviewed
        or estimated_spend_reviewed
        or previous.get("estimated_motion_seconds_reviewed", previous.get("estimated_spend_reviewed", False))
    )
    ready = bool(combined_wallet_recorded and combined_spend_recorded and estimated_spend and estimated_motion_reviewed)

    mesh_wallet_summary = _safe_summary(
        mesh_wallet_evidence_summary or str(previous.get("mesh_wallet_evidence_summary", ""))
    )
    animation_summary = _safe_summary(
        animation_allowance_summary or str(previous.get("animation_allowance_summary", ""))
    )
    spend_summary = _safe_summary(
        spend_confirmation_summary or str(previous.get("explicit_spend_approval_summary", previous.get("spend_confirmation_summary", "")))
    )
    usage_summary = _safe_summary(
        usage_approval_summary or str(previous.get("usage_approval_summary", ""))
    )
    if wallet_evidence_summary:
        combined_wallet_summary = _safe_summary(wallet_evidence_summary)
    elif mesh_wallet_summary or animation_summary:
        combined_wallet_summary = "; ".join(
            item
            for item in (
                f"mesh:{mesh_wallet_summary}" if mesh_wallet_summary else "",
                f"animation:{animation_summary}" if animation_summary else "",
            )
            if item
        )
    else:
        combined_wallet_summary = _safe_summary(str(previous.get("wallet_evidence_summary", "")))
    combined_spend_summary = spend_summary or usage_summary
    return {
        "schema": "unreal_mcp_paid_generation_evidence_review_receipt.v1",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "ready" if ready else "missing_evidence",
        "provider": str(contract.get("mesh_provider", "tripo")),
        "animation_provider": str(contract.get("animation_provider", "uthana")),
        "wallet_evidence_recorded": combined_wallet_recorded,
        "mesh_wallet_evidence_recorded": mesh_wallet_recorded,
        "animation_allowance_evidence_recorded": animation_allowance_recorded,
        "spend_confirmation_recorded": combined_spend_recorded,
        "explicit_spend_approval_recorded": explicit_spend_recorded,
        "explicit_usage_approval_recorded": usage_approval_recorded,
        "estimated_spend_reviewed": estimated_spend,
        "estimated_motion_seconds_reviewed": estimated_motion_reviewed,
        "wallet_evidence_summary": combined_wallet_summary,
        "mesh_wallet_evidence_summary": mesh_wallet_summary,
        "animation_allowance_summary": animation_summary,
        "spend_confirmation_summary": combined_spend_summary,
        "explicit_spend_approval_summary": spend_summary,
        "usage_approval_summary": usage_summary,
        "merge_policy": "preserve_existing_evidence_unless_reset",
        "mesh_wallet_tool": str(contract.get("mesh_wallet_tool", "gen_tripo_get_credit_balance")),
        "animation_allowance_tools": contract.get("animation_allowance_tools", []),
        "spend_approval_field": str(contract.get("spend_approval_field", "")),
        "required_evidence": [
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
        "human_approval_required_before_provider_work": True,
        "no_provider_call": True,
        "no_wallet_check": True,
        "no_credit_reservation": True,
        "no_task_submission": True,
        "no_download": True,
        "no_import": True,
        "no_editor_mutation": True,
        "no_git_mutation": True,
        "network_required": False,
        "spend_required": False,
        "unreal_editor_required": False,
    }


def _safe_summary(value: str) -> str:
    summary = str(value or "").strip()
    for pattern in RAW_SECRET_PATTERNS:
        if pattern.search(summary):
            raise ValueError("Evidence summaries must be masked and must not contain raw provider keys or long hex secrets.")
    return summary


def load_existing_receipt(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def write_receipt(path: Path, receipt: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a paid-generation evidence review receipt.")
    parser.add_argument("--receipt-path", default=str(DEFAULT_RECEIPT_PATH), help="ignored local JSON receipt path")
    parser.add_argument("--wallet-evidence-recorded", action="store_true", help="record that wallet/allowance evidence was reviewed elsewhere")
    parser.add_argument("--mesh-wallet-evidence-recorded", action="store_true", help="record that masked Tripo wallet evidence was reviewed elsewhere")
    parser.add_argument("--animation-allowance-evidence-recorded", action="store_true", help="record that masked Uthana allowance evidence was reviewed elsewhere")
    parser.add_argument("--spend-confirmation-recorded", action="store_true", help="record that explicit human spend/usage approval was reviewed")
    parser.add_argument("--explicit-usage-approval-recorded", action="store_true", help="record that explicit Uthana usage approval was reviewed")
    parser.add_argument("--estimated-spend-reviewed", action="store_true", help="record that estimated credits or motion seconds were reviewed")
    parser.add_argument("--estimated-motion-seconds-reviewed", action="store_true", help="record that estimated Uthana motion seconds were reviewed")
    parser.add_argument("--record-masked-tripo-wallet-evidence", action="store_true", help="handoff alias for recording masked Tripo wallet evidence")
    parser.add_argument("--record-masked-uthana-allowance-evidence", action="store_true", help="handoff alias for recording masked Uthana allowance evidence")
    parser.add_argument("--record-explicit-spend-and-usage-approval", action="store_true", help="handoff alias for recording explicit Tripo spend and Uthana usage approval")
    parser.add_argument("--reset-evidence", action="store_true", help="discard previous ignored receipt evidence before writing")
    parser.add_argument("--wallet-evidence-summary", default="", help="short non-secret wallet/allowance evidence note")
    parser.add_argument("--mesh-wallet-evidence-summary", default="", help="short non-secret Tripo wallet evidence note")
    parser.add_argument("--animation-allowance-summary", default="", help="short non-secret Uthana allowance evidence note")
    parser.add_argument("--spend-confirmation-summary", default="", help="short non-secret spend/usage approval note")
    parser.add_argument("--usage-approval-summary", default="", help="short non-secret Uthana usage approval note")
    args = parser.parse_args()

    receipt_path = Path(args.receipt_path)
    if not receipt_path.is_absolute():
        receipt_path = REPO_ROOT / receipt_path
    previous_receipt = load_existing_receipt(receipt_path)
    mesh_wallet_recorded = bool(args.mesh_wallet_evidence_recorded or args.record_masked_tripo_wallet_evidence)
    animation_allowance_recorded = bool(args.animation_allowance_evidence_recorded or args.record_masked_uthana_allowance_evidence)
    approval_recorded = bool(args.spend_confirmation_recorded or args.record_explicit_spend_and_usage_approval)
    usage_recorded = bool(args.explicit_usage_approval_recorded or args.record_explicit_spend_and_usage_approval)
    estimated_spend_reviewed = bool(args.estimated_spend_reviewed or args.record_explicit_spend_and_usage_approval)
    estimated_motion_seconds_reviewed = bool(args.estimated_motion_seconds_reviewed or args.record_explicit_spend_and_usage_approval)
    receipt = build_receipt(
        previous_receipt=previous_receipt,
        reset_evidence=bool(args.reset_evidence),
        wallet_evidence_recorded=bool(args.wallet_evidence_recorded),
        mesh_wallet_evidence_recorded=mesh_wallet_recorded,
        animation_allowance_evidence_recorded=animation_allowance_recorded,
        spend_confirmation_recorded=approval_recorded,
        explicit_usage_approval_recorded=usage_recorded,
        wallet_evidence_summary=str(args.wallet_evidence_summary),
        mesh_wallet_evidence_summary=str(args.mesh_wallet_evidence_summary),
        animation_allowance_summary=str(args.animation_allowance_summary),
        spend_confirmation_summary=str(args.spend_confirmation_summary),
        usage_approval_summary=str(args.usage_approval_summary),
        estimated_spend_reviewed=estimated_spend_reviewed,
        estimated_motion_seconds_reviewed=estimated_motion_seconds_reviewed,
    )
    write_receipt(receipt_path, receipt)
    print(f"PAID_GENERATION_EVIDENCE_RECEIPT={args.receipt_path}")
    print(f"PAID_GENERATION_EVIDENCE_STATUS={receipt['status']}")
    print(f"WALLET_EVIDENCE_RECORDED={receipt['wallet_evidence_recorded']}")
    print(f"MESH_WALLET_EVIDENCE_RECORDED={receipt['mesh_wallet_evidence_recorded']}")
    print(f"ANIMATION_ALLOWANCE_EVIDENCE_RECORDED={receipt['animation_allowance_evidence_recorded']}")
    print(f"SPEND_CONFIRMATION_RECORDED={receipt['spend_confirmation_recorded']}")
    print(f"EXPLICIT_USAGE_APPROVAL_RECORDED={receipt['explicit_usage_approval_recorded']}")
    print(f"ESTIMATED_SPEND_REVIEWED={receipt['estimated_spend_reviewed']}")
    print(f"ESTIMATED_MOTION_SECONDS_REVIEWED={receipt['estimated_motion_seconds_reviewed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
