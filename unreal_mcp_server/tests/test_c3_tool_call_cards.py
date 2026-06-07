"""Static checks for Workstream C.3 tool-call visualization."""

from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
EDITOR_MODULE = REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor"
PANEL_CPP = EDITOR_MODULE / "Private" / "MCPChatPanel.cpp"
PANEL_H = EDITOR_MODULE / "Public" / "MCPChatPanel.h"


class ToolCallCardsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cpp = PANEL_CPP.read_text(encoding="utf-8")
        cls.header = PANEL_H.read_text(encoding="utf-8")

    def test_tool_call_view_model_and_renderer_exist(self) -> None:
        self.assertIn("struct FToolCallView", self.header)
        for field in ("ToolName", "ArgsSummary", "Status", "ResultSummary", "DetailJson", "LogTail", "bError"):
            with self.subTest(field=field):
                self.assertIn(field, self.header)

        self.assertIn("BuildToolCallCards", self.header)
        self.assertIn("BuildToolCallCard", self.header)
        self.assertIn("SNew(SExpandableArea)", self.cpp)

    def test_tool_cards_show_required_summary_fields(self) -> None:
        for label in ("Args:", "Result:", "Details", "Repair"):
            with self.subTest(label=label):
                self.assertIn(label, self.cpp)

        self.assertIn("ToolCardHeader", self.cpp)
        self.assertIn("ToolErrorColor", self.cpp)
        self.assertIn("Visibility(ToolCall.bError ? EVisibility::Visible : EVisibility::Collapsed)", self.cpp)

    def test_detail_drawer_contains_full_structured_result_fields(self) -> None:
        self.assertIn("ToolDetailDrawer", self.header)
        self.assertIn("ShowToolDetailDrawer", self.header)
        self.assertIn("ToolDetailTitle", self.header)
        self.assertIn("ToolDetailBody", self.header)
        for detail in ("Full detail:", "Log tail:", "Args summary:", "Status:"):
            with self.subTest(detail=detail):
                self.assertIn(detail, self.cpp)

    def test_parser_recognizes_structured_tool_result_shapes(self) -> None:
        self.assertIn("ExtractToolCallsFromMessage", self.header)
        self.assertIn("TryBuildToolCallFromJsonObject", self.header)
        for key in ("tool_call", "tool_name", "success", "outputs", "log_tail", "arguments"):
            with self.subTest(key=key):
                self.assertIn(key, self.cpp)

    def test_repair_button_queues_repair_tools_chain_prompt(self) -> None:
        self.assertIn("HandleRepairToolClicked", self.header)
        self.assertIn("Run the repair_tools chain", self.cpp)
        self.assertIn("SendHumanMessage(RepairPrompt)", self.cpp)
        self.assertIn("Repair request queued", self.cpp)


if __name__ == "__main__":
    unittest.main()
