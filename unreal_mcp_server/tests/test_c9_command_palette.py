"""Static checks for Workstream C.9 MCP Chat command palette."""

from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
EDITOR_MODULE = REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor"
PANEL_CPP = EDITOR_MODULE / "Private" / "MCPChatPanel.cpp"
PANEL_H = EDITOR_MODULE / "Public" / "MCPChatPanel.h"
CHANGELOG = REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md"


class CommandPaletteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cpp = PANEL_CPP.read_text(encoding="utf-8")
        cls.header = PANEL_H.read_text(encoding="utf-8")
        cls.changelog = CHANGELOG.read_text(encoding="utf-8")

    def test_command_palette_surface_is_declared(self) -> None:
        for symbol in (
            "struct FCommandPaletteItem",
            "HandleOpenCommandPaletteClicked",
            "HandleCommandPaletteTextChanged",
            "HandleCommandPaletteItemClicked",
            "BuildCommandPalette",
            "RefreshCommandPaletteItems",
            "RebuildCommandPaletteResults",
            "AddCommandPaletteItem",
            "CommandPaletteItemMatches",
            "GetCommandPaletteVisibility",
            "CommandPaletteItems",
            "CommandPaletteResults",
            "CommandPaletteInput",
            "bCommandPaletteVisible",
            "CommandPaletteFilter",
        ):
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, self.header)

    def test_panel_opens_palette_from_button_and_ctrl_k(self) -> None:
        self.assertIn('LOCTEXT("CommandPalette", "Command Palette")', self.cpp)
        self.assertIn(".OnClicked(this, &SMCPChatPanel::HandleOpenCommandPaletteClicked)", self.cpp)
        self.assertIn("InKeyEvent.GetKey() == EKeys::K", self.cpp)
        self.assertIn("InKeyEvent.IsControlDown()", self.cpp)
        self.assertIn("return HandleOpenCommandPaletteClicked();", self.cpp)
        self.assertIn(".Visibility(this, &SMCPChatPanel::GetCommandPaletteVisibility)", self.cpp)

    def test_palette_widget_has_search_and_results(self) -> None:
        self.assertIn("BuildCommandPalette()", self.cpp)
        self.assertIn("SAssignNew(CommandPaletteInput, SEditableTextBox)", self.cpp)
        self.assertIn(".OnTextChanged(this, &SMCPChatPanel::HandleCommandPaletteTextChanged)", self.cpp)
        self.assertIn("SAssignNew(CommandPaletteResults, SVerticalBox)", self.cpp)
        self.assertIn("RebuildCommandPaletteResults()", self.cpp)
        self.assertIn("No command matches", self.cpp)

    def test_palette_sources_are_complete(self) -> None:
        for slash_command in ("/help", "/clear", "/undo", "/repair"):
            with self.subTest(slash_command=slash_command):
                self.assertIn(slash_command, self.cpp)
        for source in (
            "ToolPaletteByCategory.GetKeys",
            "BuildToolPromptTemplate(Tool)",
            "Start IDE Companion Session",
            "skill_compile_ide_companion_session",
            "unreal_mcp_ide_companion_session_plan.v1",
            "outputs.workflow_actions.start_companion_session.target_start_context",
            "existing ledger state",
            "Update IDE Companion Status",
            "skill_compile_ide_companion_status",
            "unreal_mcp_ide_companion_status.v1",
            "outputs.workflow_actions.refresh_companion_status.target_status_context",
            "session-plan state",
            "Generate IDE Companion Work Order",
            "skill_compile_ide_companion_work_order",
            "outputs.workflow_actions.generate_work_order.target_work_order_context",
            "session-plan/status state",
            "unreal_mcp_ide_companion_work_order.v1",
            "Review Gameplay Template Plan",
            "outputs.workflow_actions.review_gameplay_template_plan.target_gameplay_template_context",
            "outputs.work_order_template",
            "graph/component operations",
            "operation proof contracts",
            "placeholder/generated asset swap requirements",
            "generated animation prompt requirements",
            "paid-animation readiness gates",
            "Uthana allowance/evidence tools",
            "stop-before-editor/provider policy",
            "do not mutate Unreal, queue actions, run PIE",
            "Record IDE Companion Evidence",
            "skill_record_ide_companion_evidence",
            "unreal_mcp_ide_companion_evidence_record.v1",
            "outputs.workflow_actions.record_evidence.target_evidence_context",
            "outputs.workflow_actions.record_evidence.target_evidence_item",
            "outputs.evidence_recording.items",
            "generated-asset metadata",
            "queued-action metadata",
            "runtime-verification metadata",
            "artifact previews",
            "record_readiness_policy",
            "Review Evidence Requirements",
            "outputs.workflow_actions.review_evidence_requirements.target_evidence_review_context",
            "stop-before-ledger-write policy",
            "This command is review-only: do not mutate Unreal, write ledger evidence",
            "Record Queued Action Evidence",
            "outputs.workflow_actions.record_queued_action_evidence.target_evidence_context",
            "outputs.evidence_recording.items.record_editor_queue_1",
            "queued_action",
            "Record Generated Asset Evidence",
            "outputs.workflow_actions.record_generated_asset_evidence.target_evidence_context",
            "outputs.evidence_recording.items.record_generated_asset_quality_gate",
            "generated_asset",
            "Do not submit provider tasks or import assets from this command",
            "Record Paid Generation Evidence",
            "outputs.workflow_actions.record_paid_generation_evidence.target_evidence_context",
            "outputs.workflow_actions.review_provider_spend_gate.target_provider_spend_context",
            "outputs.evidence_recording.items.record_paid_generation_evidence",
            "Tripo wallet, Uthana allowance",
            "Do not call Tripo or Uthana, download files, import assets, reserve credits",
            "Record Generated Animation Evidence",
            "outputs.workflow_actions.record_generated_animation_evidence.target_evidence_context",
            "outputs.workflow_actions.compile_generated_animation_evidence",
            "outputs.evidence_recording.items.record_generated_animation_evidence",
            "generated_animation",
            "Do not call Uthana, download files, import animations, run PIE, or mutate Unreal from this command",
            "Record Feature Completion Contract",
            "outputs.workflow_actions.record_feature_completion_contract.target_evidence_context",
            "outputs.evidence_recording.items.record_feature_completion_contract",
            "feature_completion_contract",
            "Do not mutate Unreal, run PIE, call providers, or bypass missing proof from this command",
            "Record Runtime Evidence",
            "outputs.workflow_actions.record_runtime_evidence.target_evidence_context",
            "outputs.evidence_recording.items.record_runtime_verification",
            "runtime_verification",
            "Review Generated Asset Gate",
            "outputs.workflow_actions.review_generated_asset_gate.target_generated_asset_review_context",
            "outputs.generated_asset_quality_gate",
            "do not submit provider tasks",
            "Review Generated Asset Lifecycle Gate",
            "outputs.workflow_actions.review_generated_asset_lifecycle_gate.target_generated_asset_lifecycle_context",
            "outputs.generated_asset_lifecycles",
            "provider-neutral lifecycle summary",
            "do not call providers, spend credits, import assets",
            "Review Generated Animation Lifecycle Gate",
            "outputs.workflow_actions.review_generated_animation_lifecycle_gate.target_generated_animation_lifecycle_context",
            "outputs.generated_asset_lifecycles.preview_animation_assets",
            "Uthana motion generation, retarget, AnimGraph, PIE, and ledger gates",
            "animation quality proof contract",
            "quality_proof_required_preview",
            "do not call Uthana, download files, import animations",
            "Compile Generated Animation Evidence",
            "gen_compile_generated_animation_evidence",
            "outputs.workflow_actions.compile_generated_animation_evidence.target_generated_animation_lifecycle_context",
            "text_motion_result_json, job_result_json, motion_result_json, download_allowed_json, download_result_json, import_result_json, retarget_evidence_json, animgraph_evidence_json, pie_evidence_json, ledger_evidence_json, approval_note",
            "This command compiles evidence only",
            "Review Generated Asset Import Gate",
            "outputs.workflow_actions.review_generated_asset_import_gate.target_generated_asset_import_context",
            "outputs.readiness_policy.editor_mutation",
            "stop-before-import-or-quality-work policy",
            "do not import assets, mutate Unreal, replace placeholders",
            "Review Generated Asset Quality Proof Gate",
            "outputs.workflow_actions.review_generated_asset_quality_proof_gate.target_generated_asset_quality_proof_context",
            "quality proof contract",
            "quality_proof_required_preview",
            "material/collision/viewport/ledger proof flags",
            "stop-before-quality-proof-work policy",
            "do not capture viewports, mutate Unreal, import assets",
            "Review Generated Asset Replacement Gate",
            "outputs.workflow_actions.review_generated_asset_replacement_gate.target_generated_asset_replacement_context",
            "outputs.generated_asset_lifecycles.preview_assets",
            "stop-before-placeholder-replacement policy",
            "do not replace placeholders, mutate Unreal, import assets",
            "Review Provider Spend Gate",
            "outputs.workflow_actions.review_provider_spend_gate.target_provider_spend_context",
            "outputs.readiness_policy.paid_generation",
            "stop-before-provider-call policy",
            "fallback_placeholder_available",
            "fallback_action_id",
            "fallback tool/queue tool",
            "Continue With Placeholder Fallback",
            "continue_with_placeholder_fallback",
            "do not submit provider tasks, spend credits, call providers",
            "Review Generated Asset Provider Task Gate",
            "outputs.workflow_actions.review_generated_asset_provider_task_gate.target_generated_asset_provider_task_context",
            "outputs.generated_asset_lifecycles.preview_assets",
            "stop-before-provider-task-or-download policy",
            "do not call providers, poll status, download files",
            "Review Platform Preflight Gate",
            "outputs.workflow_actions.review_platform_preflight_gate.target_platform_preflight_context",
            "scripts/audit_ide_companion_readiness.py",
            "tool-count reproducibility",
            "build-wrapper reference readiness",
            "platform-stability blockers",
            "do not mutate Unreal, ping the bridge manually, call providers",
            "Review Live Editor Bridge Gate",
            "outputs.workflow_actions.review_live_editor_bridge_gate.target_live_editor_context",
            "outputs.next_safe_step",
            "stop-before-editor-or-PIE policy",
            "do not mutate Unreal, manually ping the bridge, run PIE",
            "Review WIP Promotion Gate",
            "outputs.workflow_actions.review_wip_promotion_gate.target_wip_promotion_context",
            "build-wrapper reference readiness",
            "wip-to-main promotion policy",
            "do not create branches, stage files, commit, merge",
            "Review Blueprint Mutation Gate",
            "outputs.workflow_actions.review_blueprint_mutation_gate.target_blueprint_mutation_context",
            "outputs.readiness_policy.blueprint_mutation",
            "pre-read/compile/readback gates",
            "do not mutate Blueprints, compile, save assets",
            "Review Bridge Wrapper Coverage",
            "outputs.workflow_actions.review_bridge_wrapper_coverage.target_bridge_wrapper_context",
            "scripts/audit_high_value_wrapper_coverage.py",
            "bridge registry tool",
            "do not mutate Unreal, ping the bridge, edit Blueprint assets",
            "Review Test Lane Gates",
            "outputs.workflow_actions.review_test_lane_gates.target_test_lane_context",
            "docs/ci-smoke.md",
            "default discovery pattern",
            "do not run live bridge tests, paid-provider tests",
            "Resume IDE Companion Session",
            "skill_resume_ide_companion_session",
            "unreal_mcp_ide_companion_resume.v1",
            "outputs.workflow_actions.resume_companion_session.target_resume_context",
            "next phase/tool",
            "Show IDE Companion Dashboard",
            "skill_compile_ide_companion_dashboard",
            "unreal_mcp_ide_companion_dashboard.v1",
            "outputs.workflow_actions.show_companion_dashboard.target_dashboard_context",
            "readiness state",
            "generated asset state",
            "Show Evidence Ledger",
            "chat_get_cockpit_ledger_detail",
            "unreal_mcp_chat_ledger_detail.v1",
            "outputs.workflow_actions.show_evidence_ledger.target_evidence_ledger_context",
            "timeline events",
            "artifact previews",
            "Resolve IDE Companion Blockers",
            "skill_compile_ide_companion_blocker_resolution",
            "unreal_mcp_ide_companion_blocker_resolution.v1",
            "outputs.workflow_actions.resolve_blockers",
            "target_blocker_resolution",
            "unblock_action",
            "fallback_action",
            "evidence_required",
            "can_continue_offline",
            "arguments.target_blocker",
            "arguments.current_blockers",
            "outputs.blocker_resolutions",
            "provider_api_key_configured",
            "animation_provider_api_key_configured",
            "Generate Settings",
            "TRIPO_API_KEY",
            "UTHANA_API_KEY",
            "gen_save_provider_config",
            "Compile Placeholder Asset Manifest",
            "skill_compile_ide_companion_placeholder_manifest",
            "unreal_mcp_ide_companion_placeholder_manifest.v1",
            "outputs.workflow_actions.compile_placeholder_manifest.target_placeholder_context",
            "selected target asset",
            "Compile Generated Asset Lifecycle",
            "skill_compile_ide_companion_asset_lifecycle_manifest",
            "unreal_mcp_ide_companion_generated_asset_lifecycle.v1",
            "outputs.workflow_actions.compile_asset_lifecycle_manifest.target_asset_lifecycle_compile_context",
            "outputs.work_order_template",
            "generated prompt counts",
            "outputs.generated_asset_lifecycles",
            "Resolve Generated Asset",
            "Continue from the cockpit-selected generated asset blocker",
            "selected target asset id",
            "do not submit provider tasks",
            "Review Editor Queue",
            "outputs.workflow_actions.review_editor_queue.target_queue_review_context",
            "outputs.editor_queues",
            "This command is review-only: do not mutate Unreal",
            "Queue IDE Companion Editor Actions",
            "skill_compile_ide_companion_editor_queue",
            "unreal_mcp_ide_companion_editor_queue.v1",
            "outputs.workflow_actions.queue_editor_actions.target_queue_context",
            "arguments.target_phase",
            "arguments.ledger_path",
            "Execute Next Safe Step",
            "outputs.workflow_actions.execute_next_safe_step.target_execution_review_context",
            "outputs.workflow_actions.execute_next_safe_step.target_execute_context",
            "outputs.next_safe_step",
            "can_execute_now",
            "pre_execution_checklist",
            "executor_contract",
            "post_execution_evidence_required",
            "after-execution evidence",
            "Review Runtime Verification",
            "outputs.workflow_actions.review_runtime_verification.target_runtime_review_context",
            "outputs.runtime_review",
            "outputs.runtime_verification",
            "PIE log",
            "viewport screenshot",
            "actor state",
            "Repair Failed Step",
            "outputs.workflow_actions.repair_failed_step.target_repair_review_context",
            "outputs.workflow_actions.repair_failed_step.target_repair_context",
            "outputs.failure_triage",
            "outputs.repair_loop",
            "IDE Companion Readiness",
            "gen_compile_ide_companion_readiness",
            "unreal_mcp_ide_companion_readiness.v1",
            "outputs.workflow_actions.check_readiness.target_readiness_policy_context",
            "outputs.readiness_policy",
            "Review Readiness Repair Queue",
            "outputs.workflow_actions.review_readiness_repair_queue.target_readiness_repair_queue_context",
            "outputs.readiness_repair_queue",
            "recommended next repair",
            "stop-before-running-repair policy",
            "do not execute scripts, ping the bridge, call providers",
            "Uthana animation auth",
            "Plan Gameplay Mechanic",
            "skill_plan_gameplay_mechanic",
            "unreal_mcp_gameplay_mechanic_plan.v1",
            "kb://v5/CHANGELOG.md",
            "docs/knowledge-base/README.md",
            "docs/knowledge-base/unreal-cpp-li-2023.md",
            "docs/knowledge-base/elevating-game-experiences-ue5-2e.md",
            "docs/knowledge-base/game-ai-unreal-sapio-2019.md",
            "@asset:",
            "Recent asset",
            "Recent prompt",
            "NormaliseSender(Message.Sender) != TEXT(\"user\")",
        ):
            with self.subTest(source=source):
                self.assertIn(source, self.cpp)

    def test_palette_clicks_insert_or_run_commands(self) -> None:
        self.assertIn("HandleCommandPaletteItemClicked(FCommandPaletteItem Item)", self.cpp)
        self.assertIn('Item.Kind == TEXT("slash") && Item.Label == TEXT("/clear")', self.cpp)
        self.assertIn("HandleClearClicked();", self.cpp)
        self.assertIn("InsertComposerText(Item.InsertText.IsEmpty() ? Item.Label : Item.InsertText)", self.cpp)
        self.assertIn("bCommandPaletteVisible = false", self.cpp)

    def test_palette_uses_fuzzy_matching(self) -> None:
        self.assertIn("CommandPaletteItemMatches(const FString& Filter, const FCommandPaletteItem& Item) const", self.cpp)
        self.assertIn("Haystack.Contains(Needle)", self.cpp)
        self.assertIn("NeedleIndex", self.cpp)
        self.assertIn("HaystackIndex", self.cpp)

    def test_changelog_records_c9(self) -> None:
        self.assertIn("### C.9 - Command palette", self.changelog)
        self.assertIn("Ctrl+K", self.changelog)
        self.assertIn("fuzzy", self.changelog)


if __name__ == "__main__":
    unittest.main()
