"""Write an ignored Blueprint mutation evidence receipt without editor mutation."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT_PATH = Path("Saved") / "BlueprintMutationEvidence" / "last_review_receipt.json"
RAW_SECRET_PATTERNS = (
    re.compile(r"tsk_[A-Za-z0-9_\-]{20,}"),
    re.compile(r"\b[0-9a-fA-F]{32,}\b"),
)


PRE_READ_RECEIPT_COMMAND_TEMPLATE = (
    'python scripts\\write_blueprint_mutation_evidence_review.py --pre-read-evidence-recorded '
    '--target-blueprint-path "<target Blueprint asset path>" '
    '--intended-mutation-summary "<intended Blueprint change>" '
    '--pre-read-summary "<read-only graph/component state summary>"'
)
COMPILE_PLAN_RECEIPT_COMMAND_TEMPLATE = (
    'python scripts\\write_blueprint_mutation_evidence_review.py --compile-plan-recorded '
    '--compile-plan-summary "<compile command and failure repair plan>"'
)
READBACK_PLAN_RECEIPT_COMMAND_TEMPLATE = (
    'python scripts\\write_blueprint_mutation_evidence_review.py --readback-plan-recorded '
    '--readback-plan-summary "<expected graph/component readback proof>"'
)


def _safe_summary(value: Optional[str]) -> str:
    summary = str(value or "").strip()
    for pattern in RAW_SECRET_PATTERNS:
        if pattern.search(summary):
            raise ValueError("Blueprint mutation evidence summaries must not contain raw provider keys or long hex secrets.")
    return summary


def _load_existing_receipt(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _blueprint_operator_command_handoff() -> list[Dict[str, Any]]:
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
            "command": PRE_READ_RECEIPT_COMMAND_TEMPLATE,
            "evidence_gate": "blueprint_pre_read_evidence",
            "future_read_only_bridge_evidence_required": True,
            "requires_bridge_evidence_before_receipt": True,
        },
        {
            **common,
            "id": "record_blueprint_compile_plan",
            "label": "Record Blueprint compile plan",
            "command": COMPILE_PLAN_RECEIPT_COMMAND_TEMPLATE,
            "evidence_gate": "blueprint_compile_plan",
            "future_read_only_bridge_evidence_required": False,
            "requires_bridge_evidence_before_receipt": False,
        },
        {
            **common,
            "id": "record_blueprint_readback_plan",
            "label": "Record Blueprint readback plan",
            "command": READBACK_PLAN_RECEIPT_COMMAND_TEMPLATE,
            "evidence_gate": "blueprint_readback_plan",
            "future_read_only_bridge_evidence_required": False,
            "requires_bridge_evidence_before_receipt": False,
        },
    ]


def build_receipt(
    *,
    previous_receipt: Optional[Dict[str, Any]] = None,
    reset_evidence: bool = False,
    pre_read_evidence_recorded: bool = False,
    compile_plan_recorded: bool = False,
    readback_plan_recorded: bool = False,
    target_blueprint_path: str = "",
    intended_mutation_summary: str = "",
    pre_read_summary: str = "",
    compile_plan_summary: str = "",
    readback_plan_summary: str = "",
) -> Dict[str, Any]:
    previous = previous_receipt if isinstance(previous_receipt, dict) and not reset_evidence else {}
    pre_read_recorded = bool(pre_read_evidence_recorded or previous.get("pre_read_evidence_recorded", False))
    compile_recorded = bool(compile_plan_recorded or previous.get("compile_plan_recorded", False))
    readback_recorded = bool(readback_plan_recorded or previous.get("readback_plan_recorded", False))
    target_path = _safe_summary(target_blueprint_path or str(previous.get("target_blueprint_path", "")))
    intended_summary = _safe_summary(intended_mutation_summary or str(previous.get("intended_mutation_summary", "")))
    pre_read_note = _safe_summary(pre_read_summary or str(previous.get("pre_read_summary", "")))
    compile_note = _safe_summary(compile_plan_summary or str(previous.get("compile_plan_summary", "")))
    readback_note = _safe_summary(readback_plan_summary or str(previous.get("readback_plan_summary", "")))
    ready = bool(pre_read_recorded and compile_recorded and readback_recorded)
    return {
        "schema": "unreal_mcp_blueprint_mutation_evidence_review_receipt.v1",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "ready" if ready else "missing_evidence",
        "pre_read_evidence_recorded": pre_read_recorded,
        "compile_plan_recorded": compile_recorded,
        "readback_plan_recorded": readback_recorded,
        "target_blueprint_path": target_path,
        "intended_mutation_summary": intended_summary,
        "pre_read_summary": pre_read_note,
        "compile_plan_summary": compile_note,
        "readback_plan_summary": readback_note,
        "required_evidence": [
            "target_blueprint_path",
            "intended_mutation_summary",
            "blueprint_pre_read",
            "compile_check_after_mutation",
            "graph_or_component_readback_after_mutation",
            "ledger_evidence_row_before_blueprint_mutation",
        ],
        "pre_read_receipt_command_template": PRE_READ_RECEIPT_COMMAND_TEMPLATE,
        "compile_plan_receipt_command_template": COMPILE_PLAN_RECEIPT_COMMAND_TEMPLATE,
        "readback_plan_receipt_command_template": READBACK_PLAN_RECEIPT_COMMAND_TEMPLATE,
        "operator_command_handoff": _blueprint_operator_command_handoff(),
        "merge_policy": "preserve_existing_evidence_unless_reset",
        "reset_evidence": bool(reset_evidence),
        "human_approval_required_before_blueprint_mutation": True,
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
        "unreal_editor_required": False,
    }


def write_receipt(path: Path, receipt: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a Blueprint mutation evidence review receipt.")
    parser.add_argument("--receipt-path", default=str(DEFAULT_RECEIPT_PATH), help="ignored local JSON receipt path")
    parser.add_argument("--pre-read-evidence-recorded", action="store_true", help="record that Blueprint pre-read evidence exists")
    parser.add_argument("--compile-plan-recorded", action="store_true", help="record the planned compile check after mutation")
    parser.add_argument("--readback-plan-recorded", action="store_true", help="record the planned graph/component readback proof")
    parser.add_argument("--target-blueprint-path", default="", help="target Blueprint asset path, no secrets")
    parser.add_argument("--intended-mutation-summary", default="", help="short non-secret intended mutation note")
    parser.add_argument("--pre-read-summary", default="", help="short non-secret pre-read evidence note")
    parser.add_argument("--compile-plan-summary", default="", help="short non-secret compile plan note")
    parser.add_argument("--readback-plan-summary", default="", help="short non-secret readback plan note")
    parser.add_argument("--reset-evidence", action="store_true", help="discard previous ignored receipt evidence before writing")
    args = parser.parse_args()

    receipt_path = Path(args.receipt_path)
    if not receipt_path.is_absolute():
        receipt_path = REPO_ROOT / receipt_path
    receipt = build_receipt(
        previous_receipt=_load_existing_receipt(receipt_path),
        reset_evidence=bool(args.reset_evidence),
        pre_read_evidence_recorded=bool(args.pre_read_evidence_recorded),
        compile_plan_recorded=bool(args.compile_plan_recorded),
        readback_plan_recorded=bool(args.readback_plan_recorded),
        target_blueprint_path=str(args.target_blueprint_path),
        intended_mutation_summary=str(args.intended_mutation_summary),
        pre_read_summary=str(args.pre_read_summary),
        compile_plan_summary=str(args.compile_plan_summary),
        readback_plan_summary=str(args.readback_plan_summary),
    )
    write_receipt(receipt_path, receipt)
    print(f"BLUEPRINT_MUTATION_EVIDENCE_RECEIPT={args.receipt_path}")
    print(f"BLUEPRINT_MUTATION_EVIDENCE_STATUS={receipt['status']}")
    print(f"BLUEPRINT_PRE_READ_EVIDENCE_RECORDED={receipt['pre_read_evidence_recorded']}")
    print(f"BLUEPRINT_COMPILE_PLAN_RECORDED={receipt['compile_plan_recorded']}")
    print(f"BLUEPRINT_READBACK_PLAN_RECORDED={receipt['readback_plan_recorded']}")
    print(f"BLUEPRINT_TARGET_PATH_RECORDED={bool(receipt['target_blueprint_path'])}")
    print(f"BLUEPRINT_INTENDED_MUTATION_RECORDED={bool(receipt['intended_mutation_summary'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
