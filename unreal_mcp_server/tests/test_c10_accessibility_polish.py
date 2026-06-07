"""Static checks for Workstream C.10 MCP Chat accessibility and polish."""

from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
EDITOR_MODULE = REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor"
PANEL_CPP = EDITOR_MODULE / "Private" / "MCPChatPanel.cpp"
PANEL_H = EDITOR_MODULE / "Public" / "MCPChatPanel.h"
CHANGELOG = REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md"


class AccessibilityPolishTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cpp = PANEL_CPP.read_text(encoding="utf-8")
        cls.header = PANEL_H.read_text(encoding="utf-8")
        cls.changelog = CHANGELOG.read_text(encoding="utf-8")

    def test_polish_surface_is_declared(self) -> None:
        for symbol in (
            "LoadLayoutSettings",
            "SaveLayoutSettings",
            "RecordHorizontalSplitterResize",
            "RecordVerticalSplitterResize",
            "RecordServerLatency",
            "RecordTelemetryEvent",
            "GetMetricsFilePath",
            "GetStatusFooterText",
            "GetTelemetryToggleText",
            "HandleToggleTelemetryClicked",
            "SessionSidebarSize",
            "ToolPaletteSize",
            "ChatWorkspaceSize",
            "ConversationSize",
            "ComposerSize",
            "LastServerLatencyMs",
            "ToolCount",
            "KbDocCount",
            "bTelemetryEnabled",
        ):
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, self.header)

    def test_splitters_are_persisted_and_resizable(self) -> None:
        for token in (
            "LoadLayoutSettings();",
            "SaveLayoutSettings();",
            "GEditorPerProjectIni",
            "ChatPanelConfigSection",
            "OnSlotResized(SSplitter::FOnSlotResized::CreateSP(this, &SMCPChatPanel::RecordHorizontalSplitterResize",
            "OnSlotResized(SSplitter::FOnSlotResized::CreateSP(this, &SMCPChatPanel::RecordVerticalSplitterResize",
            "ResizeMode(ESplitterResizeMode::Fill)",
            "FMath::Clamp",
            "SessionSidebarSize",
            "ComposerSize",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp)

    def test_footer_reports_operational_status(self) -> None:
        self.assertIn("GetStatusFooterText() const", self.cpp)
        for label in ("Latency:", "Tools:", "KB docs:", "Queue:", "Metrics:"):
            with self.subTest(label=label):
                self.assertIn(label, self.cpp)
        for token in (
            "LastServerLatencyMs",
            "ToolCount",
            "KbDocCount",
            "ActiveRequests.Num()",
            "CoreCommandPaletteKbDocCount",
            "FPlatformTime::Seconds()",
            "RecordServerLatency(RequestStartSeconds)",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp)

    def test_telemetry_is_opt_in_and_local(self) -> None:
        for token in (
            "HandleToggleTelemetryClicked",
            "Enable Metrics",
            "Disable Metrics",
            "bTelemetryEnabled = !bTelemetryEnabled",
            "TelemetryEnabled",
            "RecordTelemetryEvent(TEXT(\"telemetry_enabled\"))",
            "RecordTelemetryEvent(TEXT(\"message_sent\"))",
            "RecordTelemetryEvent(TEXT(\"command_palette_opened\"))",
            "SavedDir",
            "MCPChat",
            "metrics.json",
            "FFileHelper::SaveStringToFile",
            "IFileManager::Get().MakeDirectory",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp)

    def test_theming_uses_editor_style_tokens(self) -> None:
        for token in (
            "FAppStyle::GetBrush(\"Brushes.Panel\")",
            "FAppStyle::GetBrush(\"Brushes.Recessed\")",
            "FAppStyle::GetFontStyle(\"NormalFontBold\")",
            "FSlateColor::UseSubduedForeground()",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp)

    def test_changelog_records_c10(self) -> None:
        self.assertIn("### C.10 - Accessibility and polish", self.changelog)
        self.assertIn("status footer", self.changelog)
        self.assertIn("metrics.json", self.changelog)


if __name__ == "__main__":
    unittest.main()
