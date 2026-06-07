"""Static checks for Workstream C.8 MCP Chat session management."""

from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
EDITOR_MODULE = REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor"
PANEL_CPP = EDITOR_MODULE / "Private" / "MCPChatPanel.cpp"
PANEL_H = EDITOR_MODULE / "Public" / "MCPChatPanel.h"
CHAT_STORAGE = REPO_ROOT / "unreal_mcp_server" / "chat" / "storage.py"
CHAT_ROUTES = REPO_ROOT / "unreal_mcp_server" / "chat" / "routes.py"
CHAT_TESTS = REPO_ROOT / "unreal_mcp_server" / "tests" / "test_chat.py"
CHANGELOG = REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md"


class SessionManagementTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cpp = PANEL_CPP.read_text(encoding="utf-8")
        cls.header = PANEL_H.read_text(encoding="utf-8")
        cls.storage = CHAT_STORAGE.read_text(encoding="utf-8")
        cls.routes = CHAT_ROUTES.read_text(encoding="utf-8")
        cls.chat_tests = CHAT_TESTS.read_text(encoding="utf-8")
        cls.changelog = CHANGELOG.read_text(encoding="utf-8")

    def test_session_surface_is_declared(self) -> None:
        for symbol in (
            "struct FChatSessionEntry",
            "HandleNewSessionClicked",
            "HandleContinueLastSessionClicked",
            "HandleRenameSessionClicked",
            "HandlePinSessionClicked",
            "HandleDeleteSessionClicked",
            "HandleExportSessionClicked",
            "HandleSessionClicked",
            "BuildSessionSidebar",
            "RebuildSessionList",
            "ParseSessionsResponse",
            "CurrentSessionName",
            "ChatSessions",
            "SessionList",
        ):
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, self.header)

    def test_panel_has_session_sidebar_actions(self) -> None:
        self.assertIn("BuildSessionSidebar()", self.cpp)
        self.assertIn('LOCTEXT("SessionSidebarTitle", "Sessions")', self.cpp)
        for label in ("Continue Last", "New", "Rename", "Pin", "Delete", "Export"):
            with self.subTest(label=label):
                self.assertIn(label, self.cpp)
        self.assertIn(".OnClicked(this, &SMCPChatPanel::HandleSessionClicked, Session)", self.cpp)

    def test_panel_uses_session_scoped_chat_routes(self) -> None:
        self.assertIn('BuildServerUrl(TEXT("/chat/sessions"))', self.cpp)
        self.assertIn('TEXT("/chat/history?limit=50") + BuildSessionQueryParam()', self.cpp)
        self.assertIn('TEXT("/chat/poll?sender=agent") + BuildSessionQueryParam()', self.cpp)
        self.assertIn('TEXT("/chat/send?session=")', self.cpp)
        self.assertIn('TEXT("/chat/clear?session=")', self.cpp)
        self.assertIn('TEXT("/chat/session/export?name=")', self.cpp)
        self.assertIn('Payload->SetStringField(TEXT("session"), CurrentSessionName)', self.cpp)

    def test_server_persists_named_sessions(self) -> None:
        for token in (
            "DEFAULT_CHAT_SESSION_DIR",
            "Saved\" / \"MCPChat",
            "list_sessions",
            "create_session",
            "rename_session",
            "delete_session",
            "pin_session",
            "export_session_markdown",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.storage)

    def test_server_exposes_session_routes(self) -> None:
        for route in (
            '"/chat/sessions"',
            '"/chat/session/new"',
            '"/chat/session/rename"',
            '"/chat/session/pin"',
            '"/chat/session/delete"',
            '"/chat/session/export"',
        ):
            with self.subTest(route=route):
                self.assertIn(route, self.routes)
        self.assertIn("test_named_sessions_are_isolated_and_exportable", self.chat_tests)

    def test_changelog_records_c8(self) -> None:
        self.assertIn("### C.8 - Session management", self.changelog)
        self.assertIn("Saved/MCPChat", self.changelog)


if __name__ == "__main__":
    unittest.main()
