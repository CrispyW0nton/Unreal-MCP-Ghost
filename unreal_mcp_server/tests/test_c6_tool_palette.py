"""Static checks for Workstream C.6 MCP Chat tool palette."""

from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
EDITOR_MODULE = REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor"
PANEL_CPP = EDITOR_MODULE / "Private" / "MCPChatPanel.cpp"
PANEL_H = EDITOR_MODULE / "Public" / "MCPChatPanel.h"
CHAT_ROUTES = REPO_ROOT / "unreal_mcp_server" / "chat" / "routes.py"
CHAT_TESTS = REPO_ROOT / "unreal_mcp_server" / "tests" / "test_chat.py"


class ToolPaletteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cpp = PANEL_CPP.read_text(encoding="utf-8")
        cls.header = PANEL_H.read_text(encoding="utf-8")
        cls.routes = CHAT_ROUTES.read_text(encoding="utf-8")
        cls.chat_tests = CHAT_TESTS.read_text(encoding="utf-8")

    def test_tool_palette_surface_is_declared(self) -> None:
        for symbol in (
            "struct FToolPaletteEntry",
            "HandleToggleToolPaletteClicked",
            "HandleRefreshToolPaletteClicked",
            "HandleToolPaletteToolClicked",
            "LoadToolPalette",
            "BuildToolPalette",
            "BuildToolPaletteCategory",
            "RebuildToolPaletteList",
            "ParseToolPaletteResponse",
            "BuildToolPromptTemplate",
            "GetToolPaletteVisibility",
            "GetToolPaletteToggleText",
            "ToolPaletteByCategory",
            "ToolPaletteList",
        ):
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, self.header)

    def test_panel_has_toggleable_left_rail(self) -> None:
        self.assertIn(".Orientation(Orient_Horizontal)", self.cpp)
        self.assertIn("BuildToolPalette()", self.cpp)
        self.assertIn(".Visibility(this, &SMCPChatPanel::GetToolPaletteVisibility)", self.cpp)
        self.assertIn(".Text(this, &SMCPChatPanel::GetToolPaletteToggleText)", self.cpp)
        self.assertIn("bToolPaletteVisible = !bToolPaletteVisible", self.cpp)

    def test_palette_fetches_list_available_tools_payload(self) -> None:
        self.assertIn('BuildServerUrl(TEXT("/tools/list?domain=all"))', self.cpp)
        self.assertIn("ParseToolPaletteResponse(Response->GetContentAsString(), ParsedTools)", self.cpp)
        self.assertIn("ToolPaletteByCategory = MoveTemp(ParsedTools)", self.cpp)
        self.assertIn("RebuildToolPaletteList()", self.cpp)

    def test_palette_renders_categories_and_tool_buttons(self) -> None:
        self.assertIn("SNew(SExpandableArea)", self.cpp)
        self.assertIn("ToolPaletteCategoryHeader", self.cpp)
        self.assertIn("ToolButtons->AddSlot()", self.cpp)
        self.assertIn(".OnClicked(this, &SMCPChatPanel::HandleToolPaletteToolClicked, Tool)", self.cpp)
        self.assertIn("Categories.Sort()", self.cpp)

    def test_tool_click_inserts_parameter_template(self) -> None:
        self.assertIn("BuildToolPromptTemplate(Tool)", self.cpp)
        self.assertIn("InsertComposerText(PromptTemplate)", self.cpp)
        self.assertIn("Use MCP tool `%s`", self.cpp)
        self.assertIn("Parameters:", self.cpp)
        self.assertIn("<%s>", self.cpp)
        self.assertIn("Return the StructuredResult", self.cpp)

    def test_http_tools_list_route_reuses_discovery_payload(self) -> None:
        self.assertIn("from tools.knowledge_tools import _tool_discovery_payload", self.routes)
        self.assertIn('mcp.custom_route("/tools/list"', self.routes)
        self.assertIn("_tool_discovery_payload(mcp, domain)", self.routes)
        self.assertIn("test_tools_list_route_uses_tool_inventory_categories", self.chat_tests)


if __name__ == "__main__":
    unittest.main()
