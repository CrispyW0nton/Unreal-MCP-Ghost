"""Write an ignored dirty-state promotion review receipt.

The receipt makes the current dirty worktree grouping durable without staging,
committing, cleaning, deleting, or moving branches.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_SCRIPT_PATH = REPO_ROOT / "scripts" / "audit_ide_companion_readiness.py"
DEFAULT_RECEIPT_PATH = Path("Saved") / "DirtyPromotionReview" / "last_review_receipt.json"
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


TARGET_REVIEW_EVIDENCE_FIELDS = {
    "owner_or_source": "target_review_owner_or_source",
    "promotion_intent": "target_review_promotion_intent",
    "focused_test_results": "target_review_focused_test_results",
    "artifact_policy_decision": "target_review_artifact_policy_decision",
    "tracked_diff_review": "target_review_tracked_diff_review",
}


def _clean_text(value: Optional[str]) -> str:
    text = str(value or "").strip()
    for pattern in RAW_SECRET_PATTERNS:
        if pattern.search(text):
            raise ValueError("Dirty promotion evidence must not contain raw provider keys or long hex secrets.")
    return text


def _load_existing_receipt(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _target_recorded_evidence(target_evidence: Dict[str, Any], required_evidence: List[str]) -> List[str]:
    recorded: Set[str] = set()
    for evidence_key, field_name in TARGET_REVIEW_EVIDENCE_FIELDS.items():
        if _clean_text(target_evidence.get(field_name)):
            recorded.add(evidence_key)
    if bool(target_evidence.get("target_review_human_approval_recorded", False)):
        recorded.add("human_approval_before_stage_commit_merge")
    ordered = [item for item in required_evidence if item in recorded]
    for evidence_key in (*TARGET_REVIEW_EVIDENCE_FIELDS, "human_approval_before_stage_commit_merge"):
        if evidence_key in recorded and evidence_key not in ordered:
            ordered.append(evidence_key)
    return ordered


def build_receipt(
    target_evidence: Optional[Dict[str, Any]] = None,
    *,
    previous_receipt: Optional[Dict[str, Any]] = None,
    reset_target_evidence: bool = False,
) -> Dict[str, Any]:
    audit = _load_audit_module()
    git = audit._git_status()
    dirty_promotion = audit._dirty_promotion_contract(git)
    branch = git.get("branch") if isinstance(git.get("branch"), dict) else {}
    review_batches = list(dirty_promotion.get("review_batches", [])) if isinstance(dirty_promotion.get("review_batches"), list) else []
    evidence_matrix = list(dirty_promotion.get("evidence_review_matrix", [])) if isinstance(dirty_promotion.get("evidence_review_matrix"), list) else []
    target_review_batch = next((item for item in review_batches if isinstance(item, dict)), {})
    target_review_gap = next((item for item in evidence_matrix if isinstance(item, dict)), {})
    target_missing_evidence = (
        target_review_gap.get("missing_evidence")
        if isinstance(target_review_gap.get("missing_evidence"), list)
        else []
    )
    target_required_evidence = (
        list(target_review_gap.get("required_evidence", []))
        if isinstance(target_review_gap.get("required_evidence"), list)
        else []
    )
    evidence = target_evidence or {}
    target_group_name = str(target_review_batch.get("group") or target_review_gap.get("group") or "")
    target_tracked_count = int(target_review_batch.get("tracked_count", target_review_gap.get("tracked_count", 0)) or 0)
    target_untracked_count = int(target_review_batch.get("untracked_count", target_review_gap.get("untracked_count", 0)) or 0)
    previous = previous_receipt if isinstance(previous_receipt, dict) and not reset_target_evidence else {}
    previous_matches_target = bool(
        previous.get("schema") == "unreal_mcp_dirty_promotion_review_receipt.v1"
        and str(previous.get("dirty_signature", "")) == str(git.get("dirty_signature", ""))
        and str(previous.get("target_review_group", "")) == target_group_name
    )
    if previous_matches_target:
        merged_evidence = {
            "target_review_owner_or_source": _clean_text(previous.get("target_review_owner_or_source")),
            "target_review_promotion_intent": _clean_text(previous.get("target_review_promotion_intent")),
            "target_review_focused_test_results": _clean_text(previous.get("target_review_focused_test_results")),
            "target_review_artifact_policy_decision": _clean_text(previous.get("target_review_artifact_policy_decision")),
            "target_review_tracked_diff_review": _clean_text(previous.get("target_review_tracked_diff_review")),
            "target_review_human_approval_recorded": bool(previous.get("target_review_human_approval_recorded", False)),
            "target_review_human_approval_summary": _clean_text(previous.get("target_review_human_approval_summary")),
        }
        for key, value in evidence.items():
            if key == "target_review_human_approval_recorded":
                merged_evidence[key] = bool(value or merged_evidence[key])
            elif _clean_text(value):
                merged_evidence[key] = _clean_text(value)
        evidence = merged_evidence
    target_recorded_evidence = _target_recorded_evidence(evidence, target_required_evidence)
    target_missing_after_record = [item for item in target_required_evidence if item not in set(target_recorded_evidence)]
    target_evidence_complete = bool(target_required_evidence) and not target_missing_after_record
    target_human_approval_recorded = bool(evidence.get("target_review_human_approval_recorded", False))
    target_status = "reviewed" if target_evidence_complete and target_human_approval_recorded else "missing_evidence"
    target_receipt_command_template = audit._dirty_target_receipt_command_template(
        target_group_name,
        target_tracked_count,
        target_untracked_count,
        include_human_approval=False,
    )
    target_approval_receipt_command_template = audit._dirty_target_receipt_command_template(
        target_group_name,
        target_tracked_count,
        target_untracked_count,
        include_human_approval=True,
    )
    target_operator_command_handoff = audit._dirty_target_operator_command_handoff(
        target_group_name,
        target_tracked_count,
        target_untracked_count,
    )
    target_pending_human_approval_only = bool(
        target_missing_after_record == ["human_approval_before_stage_commit_merge"]
        and not target_human_approval_recorded
    )
    target_human_approval_command_handoff = [
        item
        for item in target_operator_command_handoff
        if isinstance(item, dict) and item.get("id") == "record_dirty_target_human_approval"
    ][:1]
    target_focused_test_commands = (
        list(target_review_batch.get("focused_test_commands", []))[:5]
        if isinstance(target_review_batch.get("focused_test_commands"), list)
        else []
    )
    target_focused_test_command_handoff = audit._dirty_target_focused_test_command_handoff(
        target_group_name,
        [str(command) for command in target_focused_test_commands],
    )
    return {
        "schema": "unreal_mcp_dirty_promotion_review_receipt.v1",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "ready" if dirty_promotion.get("ready_for_promotion") else "review_required",
        "current_branch": str(branch.get("current", "")),
        "branch_role": str(branch.get("role", "unknown")),
        "development_branch": str(branch.get("development_branch", "wip")),
        "stable_branch": str(branch.get("stable_branch", "main")),
        "dirty_risk": str(dirty_promotion.get("dirty_risk", "unknown")),
        "dirty_count": int(dirty_promotion.get("dirty_count", 0) or 0),
        "dirty_signature": str(git.get("dirty_signature", "")),
        "dirty_signature_algorithm": str(git.get("dirty_signature_algorithm", "")),
        "dirty_signature_entry_count": int(git.get("dirty_signature_entry_count", 0) or 0),
        "tracked_change_count": int(dirty_promotion.get("tracked_change_count", 0) or 0),
        "untracked_count": int(dirty_promotion.get("untracked_count", 0) or 0),
        "dirty_group_count": int(dirty_promotion.get("dirty_group_count", 0) or 0),
        "primary_dirty_group": str(dirty_promotion.get("primary_dirty_group", "")),
        "grouping_required": bool(dirty_promotion.get("grouping_required", False)),
        "ready_for_promotion": bool(dirty_promotion.get("ready_for_promotion", False)),
        "review_batch_count": int(dirty_promotion.get("review_batch_count", 0) or 0),
        "review_batches": list(dirty_promotion.get("review_batches", [])) if isinstance(dirty_promotion.get("review_batches"), list) else [],
        "evidence_review_matrix": list(dirty_promotion.get("evidence_review_matrix", [])) if isinstance(dirty_promotion.get("evidence_review_matrix"), list) else [],
        "evidence_review_matrix_count": int(dirty_promotion.get("evidence_review_matrix_count", 0) or 0),
        "evidence_unresolved_count": int(dirty_promotion.get("evidence_unresolved_count", 0) or 0),
        "evidence_review_policy": str(dirty_promotion.get("evidence_review_policy", "")),
        "focused_test_command_count": int(dirty_promotion.get("focused_test_command_count", 0) or 0),
        "focused_test_command_preview": list(dirty_promotion.get("focused_test_command_preview", [])) if isinstance(dirty_promotion.get("focused_test_command_preview"), list) else [],
        "candidate_batch_review_policy": str(dirty_promotion.get("candidate_batch_review_policy", "")),
        "required_evidence": list(dirty_promotion.get("required_evidence", [])) if isinstance(dirty_promotion.get("required_evidence"), list) else [],
        "promotion_batch_policy": str(dirty_promotion.get("promotion_batch_policy", "")),
        "artifact_policy": str(dirty_promotion.get("artifact_policy", "")),
        "safe_promotion_next_steps": list(dirty_promotion.get("safe_promotion_next_steps", [])) if isinstance(dirty_promotion.get("safe_promotion_next_steps"), list) else [],
        "promotion_policy": str(dirty_promotion.get("promotion_policy", "")),
        "target_review_group": target_group_name,
        "target_review_order": int(target_review_batch.get("order", target_review_gap.get("order", 0)) or 0),
        "target_review_scope": str(target_review_batch.get("candidate_batch_scope") or target_review_gap.get("candidate_batch_scope") or ""),
        "target_review_tracked_count": int(target_review_batch.get("tracked_count", target_review_gap.get("tracked_count", 0)) or 0),
        "target_review_untracked_count": int(target_review_batch.get("untracked_count", target_review_gap.get("untracked_count", 0)) or 0),
        "target_review_status": target_status,
        "target_review_evidence_complete": target_evidence_complete,
        "target_review_recorded_evidence_count": len(target_recorded_evidence),
        "target_review_recorded_evidence_preview": target_recorded_evidence[:8],
        "target_review_missing_evidence_count": len(target_missing_after_record),
        "target_review_missing_evidence_preview": target_missing_after_record[:8],
        "target_review_required_evidence_preview": target_required_evidence[:8],
        "target_review_receipt_command_template": target_receipt_command_template,
        "target_review_approval_receipt_command_template": target_approval_receipt_command_template,
        "target_review_receipt_command_policy": "Use the base template for partial evidence; add --target-human-approval-recorded only after explicit human approval.",
        "target_review_operator_command_handoff": target_operator_command_handoff,
        "target_review_pending_human_approval_only": target_pending_human_approval_only,
        "target_review_human_approval_gate": "human_approval_before_stage_commit_merge",
        "target_review_human_approval_command_handoff": target_human_approval_command_handoff,
        "target_review_focused_test_command_handoff": target_focused_test_command_handoff,
        "target_review_decision_prompt_preview": (
            list(target_review_batch.get("decision_prompts", []))[:8]
            if isinstance(target_review_batch.get("decision_prompts"), list)
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
        "target_review_owner_or_source": _clean_text(evidence.get("target_review_owner_or_source")),
        "target_review_promotion_intent": _clean_text(evidence.get("target_review_promotion_intent")),
        "target_review_focused_test_results": _clean_text(evidence.get("target_review_focused_test_results")),
        "target_review_artifact_policy_decision": _clean_text(evidence.get("target_review_artifact_policy_decision")),
        "target_review_tracked_diff_review": _clean_text(evidence.get("target_review_tracked_diff_review")),
        "target_review_human_approval_recorded": target_human_approval_recorded,
        "target_review_human_approval_summary": _clean_text(evidence.get("target_review_human_approval_summary")),
        "target_review_promotion_allowed_after_receipt": bool(target_evidence_complete and target_human_approval_recorded),
        "target_review_merge_policy": "preserve_existing_evidence_when_dirty_signature_and_target_match",
        "target_review_previous_evidence_merged": previous_matches_target,
        "target_review_reset_evidence": bool(reset_target_evidence),
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


def write_receipt(path: Path, receipt: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a no-git-mutation dirty promotion review receipt.")
    parser.add_argument("--receipt-path", default=str(DEFAULT_RECEIPT_PATH), help="ignored local JSON receipt path")
    parser.add_argument("--target-owner-or-source", default="", help="target batch owner/source review note")
    parser.add_argument("--target-promotion-intent", default="", help="target batch intent: promote_now, keep_wip, split_batch, or exclude_artifact")
    parser.add_argument("--target-focused-test-results", default="", help="target batch focused test result summary")
    parser.add_argument("--target-artifact-policy-decision", default="", help="target batch untracked artifact policy note")
    parser.add_argument("--target-tracked-diff-review", default="", help="target batch tracked diff review summary")
    parser.add_argument("--target-human-approval-recorded", action="store_true", help="record explicit human approval for this target batch")
    parser.add_argument("--target-human-approval-summary", default="", help="human approval summary; never include secrets")
    parser.add_argument("--reset-target-evidence", action="store_true", help="discard previous target evidence before writing")
    args = parser.parse_args()

    receipt_path = Path(args.receipt_path)
    if not receipt_path.is_absolute():
        receipt_path = REPO_ROOT / receipt_path
    previous_receipt = _load_existing_receipt(receipt_path)
    receipt = build_receipt({
        "target_review_owner_or_source": args.target_owner_or_source,
        "target_review_promotion_intent": args.target_promotion_intent,
        "target_review_focused_test_results": args.target_focused_test_results,
        "target_review_artifact_policy_decision": args.target_artifact_policy_decision,
        "target_review_tracked_diff_review": args.target_tracked_diff_review,
        "target_review_human_approval_recorded": args.target_human_approval_recorded,
        "target_review_human_approval_summary": args.target_human_approval_summary,
    }, previous_receipt=previous_receipt, reset_target_evidence=bool(args.reset_target_evidence))
    write_receipt(receipt_path, receipt)
    print(f"DIRTY_PROMOTION_RECEIPT={args.receipt_path}")
    print(f"DIRTY_PROMOTION_STATUS={receipt['status']}")
    print(f"DIRTY_PROMOTION_GROUPS={receipt['dirty_group_count']}")
    print(f"DIRTY_PROMOTION_REVIEW_BATCHES={receipt['review_batch_count']}")
    print(f"DIRTY_PROMOTION_EVIDENCE_UNRESOLVED={receipt['evidence_unresolved_count']}")
    print(f"DIRTY_PROMOTION_FOCUSED_TEST_COMMANDS={receipt['focused_test_command_count']}")
    print(f"DIRTY_PROMOTION_TARGET_REVIEW={receipt['target_review_group']}")
    print(f"DIRTY_PROMOTION_TARGET_SCOPE={receipt['target_review_scope']}")
    print(f"DIRTY_PROMOTION_TARGET_TRACKED={receipt['target_review_tracked_count']}")
    print(f"DIRTY_PROMOTION_TARGET_UNTRACKED={receipt['target_review_untracked_count']}")
    print(f"DIRTY_PROMOTION_TARGET_SAMPLE={' | '.join(receipt['target_review_sample_preview'])}")
    print(f"DIRTY_PROMOTION_TARGET_STATUS={receipt['target_review_status']}")
    print(f"DIRTY_PROMOTION_TARGET_RECORDED_EVIDENCE={','.join(receipt['target_review_recorded_evidence_preview'])}")
    print(f"DIRTY_PROMOTION_TARGET_MISSING_EVIDENCE={','.join(receipt['target_review_missing_evidence_preview'])}")
    print(f"DIRTY_PROMOTION_TARGET_REQUIRED_EVIDENCE={','.join(receipt['target_review_required_evidence_preview'])}")
    print(f"DIRTY_PROMOTION_TARGET_DECISION_PROMPTS={' | '.join(receipt['target_review_decision_prompt_preview'])}")
    print(f"DIRTY_PROMOTION_TARGET_EVIDENCE_COMMAND_TEMPLATE={receipt['target_review_receipt_command_template']}")
    print(f"DIRTY_PROMOTION_TARGET_APPROVAL_COMMAND_TEMPLATE={receipt['target_review_approval_receipt_command_template']}")
    print(f"DIRTY_PROMOTION_TARGET_HUMAN_APPROVAL_RECORDED={receipt['target_review_human_approval_recorded']}")
    print(f"DIRTY_PROMOTION_TARGET_PROMOTION_ALLOWED={receipt['target_review_promotion_allowed_after_receipt']}")
    print(f"DIRTY_PROMOTION_TARGET_FOCUSED_TEST_COMMANDS={receipt['target_review_focused_test_command_count']}")
    print(f"DIRTY_PROMOTION_TARGET_FOCUSED_TEST_PREVIEW={' | '.join(receipt['target_review_focused_test_command_preview'])}")
    print("DIRTY_PROMOTION_NEXT_STEP=review receipt, assign owner/source for each dirty group, then run focused tests before any human-approved staging or promotion")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
