"""Static checks for Workstream C.7 inline evidence rendering."""

from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
EDITOR_MODULE = REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor"
PANEL_CPP = EDITOR_MODULE / "Private" / "MCPChatPanel.cpp"
PANEL_H = EDITOR_MODULE / "Public" / "MCPChatPanel.h"
CHANGELOG = REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md"


class InlineEvidenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cpp = PANEL_CPP.read_text(encoding="utf-8")
        cls.header = PANEL_H.read_text(encoding="utf-8")
        cls.changelog = CHANGELOG.read_text(encoding="utf-8")

    def test_evidence_surface_is_declared(self) -> None:
        for symbol in (
            "ScreenshotPaths",
            "LogSnippets",
            "PieResults",
            "EvidenceReadinessSummary",
            "GeneratedAssetEvidenceSummary",
            "PreflightLabel",
            "PreflightSummary",
            "ProofGateSummaries",
            "bHasPreflight",
            "bPreflightReady",
            "bHasEvidenceReadiness",
            "bLivePlayableSliceProven",
            "bHasGeneratedAssetEvidence",
            "bGeneratedAssetProven",
            "BuildEvidencePanel",
            "BuildScreenshotEvidenceWidget",
            "ExtractEvidenceFromJsonObject",
            "ExtractEvidenceFromJsonValue",
            "ExtractEvidenceReadinessFromJsonObject",
            "ExtractGeneratedAssetEvidenceFromJsonObject",
            "ExtractPreflightFromJsonObject",
            "EvidenceImageBrushes",
        ):
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, self.header)

    def test_tool_cards_render_inline_evidence_section(self) -> None:
        self.assertIn("BuildEvidencePanel(ToolCall)", self.cpp)
        self.assertIn('LOCTEXT("InlineEvidencePanel", "Evidence")', self.cpp)
        self.assertIn('LOCTEXT("InlinePieEvidence", "PIE: {0}")', self.cpp)
        self.assertIn('LOCTEXT("InlineLogEvidence", "Log: {0}")', self.cpp)
        self.assertIn('LOCTEXT("InlineScreenshotPath", "Screenshot: {0}")', self.cpp)
        self.assertIn('LOCTEXT("PlayableSliceEvidenceReadinessStatus", "Playable Slice Proof: {0}")', self.cpp)
        self.assertIn('LOCTEXT("PlayableSliceProofGate", "Proof gate: {0}")', self.cpp)
        self.assertIn('LOCTEXT("GeneratedAssetEvidenceStatus", "Generate Asset Proof: {0}")', self.cpp)
        self.assertIn('LOCTEXT("GeneratedAssetProofGate", "Asset proof gate: {0}")', self.cpp)
        self.assertIn('LOCTEXT("PreflightEvidenceStatus", "{0}: {1}")', self.cpp)
        self.assertIn('LOCTEXT("PlayableSlicePreflightGate", "Preflight gate: {0}")', self.cpp)

    def test_screenshots_render_as_image_widgets_when_present(self) -> None:
        self.assertIn('#include "Brushes/SlateDynamicImageBrush.h"', self.cpp)
        self.assertIn('#include "Widgets/Images/SImage.h"', self.cpp)
        self.assertIn("FPaths::FileExists(NormalizedPath)", self.cpp)
        self.assertIn("MakeShared<FSlateDynamicImageBrush>", self.cpp)
        self.assertIn("EvidenceImageBrushes.Add(ScreenshotBrush)", self.cpp)
        self.assertIn("SNew(SImage)", self.cpp)
        self.assertIn(".Image(ScreenshotBrush.Get())", self.cpp)

    def test_evidence_parser_covers_viewport_log_and_pie_fields(self) -> None:
        for token in (
            "screenshot",
            "thumbnail",
            "viewport_image",
            "image_path",
            "log_tail",
            "log_snippet",
            "pie",
            "play_in_editor",
            "evidence_readiness",
            "unreal_mcp_playable_slice_live_preflight.v1",
            "unreal_mcp_generate_asset_live_preflight.v1",
            "unreal_mcp_generate_asset_evidence.v1",
            "Generate Asset Proof",
            "bGeneratedAssetProven",
            "GeneratedAssetEvidenceSummary",
            "Generate Asset Preflight",
            "ready_for_live_spend",
            "next_actions",
            "PreflightSummary",
            "live_playable_slice_proven",
            "ProofGateSummaries",
            "ExtractEvidenceFromJsonObject(Object, OutToolCall)",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp)

    def test_detail_drawer_lists_evidence(self) -> None:
        self.assertIn("Inline evidence:", self.cpp)
        self.assertIn("Screenshots:", self.cpp)
        self.assertIn("PIE results:", self.cpp)
        self.assertIn("Log snippets:", self.cpp)
        self.assertIn("Playable Slice Proof:", self.cpp)
        self.assertIn("Generate Asset Proof:", self.cpp)
        self.assertIn("PreflightLabel", self.cpp)

    def test_changelog_records_c7(self) -> None:
        self.assertIn("### C.7 - PIE/log/viewport evidence inline", self.changelog)
        self.assertIn("inline evidence section", self.changelog)


if __name__ == "__main__":
    unittest.main()
