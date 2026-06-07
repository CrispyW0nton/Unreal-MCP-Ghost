"""Offline tests for the UE editor chat bridge."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

_HERE = os.path.dirname(__file__)
_SERVER_ROOT = os.path.dirname(_HERE)
if _SERVER_ROOT not in sys.path:
    sys.path.insert(0, _SERVER_ROOT)

from chat import routes, storage  # noqa: E402


class _MockMCP:
    def __init__(self):
        self._tools: Dict[str, Any] = {}

    def tool(self):
        def dec(fn):
            self._tools[fn.__name__] = fn
            return fn
        return dec

    def get_tool(self, name):
        return self._tools.get(name)

    def list_tool_names(self):
        return list(self._tools.keys())


class _FakeTool:
    def __init__(self, name: str, module: str):
        def _fn():
            return None

        _fn.__module__ = module
        self.name = name
        self.description = "Fake tool for route tests."
        self.parameters = {"properties": {"blueprint_name": {"type": "string"}}}
        self.fn = _fn


class _MockRouteMCP:
    def __init__(self):
        self._routes = []
        self._tool_manager = self
        self._tools = [_FakeTool("get_server_info", "tools.knowledge_tools")]

    def custom_route(self, path, methods, name):
        def dec(fn):
            self._routes.append(Route(path, fn, methods=methods))
            return fn
        return dec

    def list_tools(self):
        return self._tools


def _parse(result: str) -> dict:
    return json.loads(result)


class TestChatStorage(unittest.TestCase):
    def test_append_poll_and_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Saved" / "MCP" / "chat_history.json"

            first = storage.append_message({
                "sender": "human",
                "message": "Can you check this laser?",
                "timestamp": "2026-04-30T14:23:00Z",
                "context": {"selected_actor": "BP_DefenseLaser3"},
            }, path=path)
            storage.append_message({
                "sender": "agent",
                "message": "I can check BP_DefenseLaser3.",
                "timestamp": "2026-04-30T14:24:00Z",
            }, path=path)

            self.assertTrue(first["message_id"])
            human_messages = storage.poll_messages(
                sender="human",
                since="2026-04-30T14:22:00Z",
                path=path,
            )
            self.assertEqual(len(human_messages), 1)
            self.assertEqual(human_messages[0]["context"]["selected_actor"], "BP_DefenseLaser3")
            self.assertEqual(len(storage.get_recent_messages(limit=1, path=path)), 1)

    def test_rejects_invalid_sender(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chat_history.json"
            with self.assertRaises(ValueError):
                storage.append_message({
                    "sender": "bot",
                    "message": "bad",
                    "timestamp": "2026-04-30T14:23:00Z",
                }, path=path)

    def test_named_sessions_are_isolated_and_exportable(self):
        with tempfile.TemporaryDirectory() as tmp:
            session_dir = Path(tmp) / "Saved" / "MCPChat"
            storage.append_message({
                "sender": "human",
                "message": "Dungeon run",
                "timestamp": "2026-04-30T14:23:00Z",
            }, session="Dungeon", session_dir=session_dir)
            storage.append_message({
                "sender": "human",
                "message": "Slime run",
                "timestamp": "2026-04-30T14:24:00Z",
            }, session="Slime", session_dir=session_dir)

            self.assertEqual(
                [item["message"] for item in storage.get_recent_messages(session="Dungeon", session_dir=session_dir)],
                ["Dungeon run"],
            )
            sessions = storage.list_sessions(session_dir=session_dir)
            self.assertEqual({item["name"] for item in sessions["sessions"]}, {"Dungeon", "Slime"})
            storage.pin_session("Dungeon", session_dir=session_dir)
            storage.rename_session("Slime", "Boss Room", session_dir=session_dir)
            markdown = storage.export_session_markdown("Boss Room", session_dir=session_dir)
            self.assertIn("# MCP Chat Session: Boss Room", markdown)
            self.assertIn("Slime run", markdown)
            storage.delete_session("Dungeon", session_dir=session_dir)
            self.assertFalse((session_dir / "Dungeon.json").exists())


class TestChatRoutes(unittest.TestCase):
    def test_send_poll_history_and_clear(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chat_history.json"
            app = Starlette(routes=[
                Route("/chat/send", routes.chat_send, methods=["POST"]),
                Route("/chat/poll", routes.chat_poll, methods=["GET"]),
                Route("/chat/history", routes.chat_history, methods=["GET"]),
                Route("/chat/clear", routes.chat_clear, methods=["POST"]),
                Route("/chat/sessions", routes.chat_sessions, methods=["GET"]),
                Route("/chat/session/new", routes.chat_session_new, methods=["POST"]),
                Route("/chat/session/rename", routes.chat_session_rename, methods=["POST"]),
                Route("/chat/session/pin", routes.chat_session_pin, methods=["POST"]),
                Route("/chat/session/delete", routes.chat_session_delete, methods=["POST"]),
                Route("/chat/session/export", routes.chat_session_export, methods=["GET"]),
            ])

            with patch.object(storage, "DEFAULT_CHAT_HISTORY_PATH", path), patch.object(storage, "DEFAULT_CHAT_SESSION_DIR", Path(tmp) / "MCPChat"):
                client = TestClient(app)
                send_resp = client.post("/chat/send", json={
                    "sender": "human",
                    "message": "Hello from UE",
                    "timestamp": "2026-04-30T14:23:00Z",
                })
                self.assertEqual(send_resp.status_code, 200)
                self.assertEqual(send_resp.json()["status"], "ok")

                poll_resp = client.get("/chat/poll?sender=human&since=2026-04-30T14:22:00Z")
                self.assertEqual(poll_resp.status_code, 200)
                self.assertEqual(len(poll_resp.json()["messages"]), 1)

                history_resp = client.get("/chat/history?limit=50")
                self.assertEqual(history_resp.status_code, 200)
                self.assertEqual(len(history_resp.json()["messages"]), 1)

                clear_resp = client.post("/chat/clear")
                self.assertEqual(clear_resp.status_code, 200)
                self.assertEqual(client.get("/chat/history").json()["messages"], [])

                new_resp = client.post("/chat/session/new", json={"name": "Dungeon"})
                self.assertEqual(new_resp.status_code, 200)
                self.assertEqual(new_resp.json()["session"]["name"], "Dungeon")
                session_send = client.post("/chat/send?session=Dungeon", json={
                    "sender": "human",
                    "message": "Session scoped",
                    "timestamp": "2026-04-30T14:25:00Z",
                })
                self.assertEqual(session_send.status_code, 200)
                self.assertEqual(len(client.get("/chat/history?session=Dungeon").json()["messages"]), 1)
                self.assertEqual(client.get("/chat/history").json()["messages"], [])
                self.assertEqual(client.post("/chat/session/pin", json={"name": "Dungeon", "pinned": True}).status_code, 200)
                self.assertEqual(client.post("/chat/session/rename", json={"old_name": "Dungeon", "new_name": "Boss"}).status_code, 200)
                export_resp = client.get("/chat/session/export?name=Boss")
                self.assertEqual(export_resp.status_code, 200)
                self.assertIn("Session scoped", export_resp.text)
                self.assertIn("Boss", {item["name"] for item in client.get("/chat/sessions").json()["sessions"]})
                self.assertEqual(client.post("/chat/session/delete", json={"name": "Boss"}).status_code, 200)

    def test_tools_list_route_uses_tool_inventory_categories(self):
        mcp = _MockRouteMCP()
        routes.register_chat_routes(mcp)
        app = Starlette(routes=mcp._routes)
        client = TestClient(app)

        response = client.get("/tools/list?domain=knowledge_base")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertIn("knowledge_base", payload["tools_by_category"])
        self.assertEqual(payload["tools"][0]["name"], "get_server_info")
        self.assertEqual(payload["tools"][0]["parameters"], ["blueprint_name"])


class TestChatTools(unittest.TestCase):
    def setUp(self):
        from tools import chat_tools

        self.chat_tools = chat_tools
        self.mcp = _MockMCP()
        self.chat_tools.register_chat_tools(self.mcp)
        self.chat_tools._LAST_HUMAN_POLL_SINCE = None

    def test_tools_registered(self):
        self.assertEqual({
            "chat_poll_messages",
            "chat_send_response",
            "chat_get_context",
        }, set(self.mcp.list_tool_names()))

    def test_send_and_poll_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chat_history.json"
            with patch.object(storage, "DEFAULT_CHAT_HISTORY_PATH", path):
                storage.append_message({
                    "sender": "human",
                    "message": "What phase are we in?",
                    "timestamp": "2026-04-30T14:23:00Z",
                })

                poll = _parse(self.mcp.get_tool("chat_poll_messages")(
                    since="2026-04-30T14:22:00Z",
                    limit=10,
                ))
                self.assertTrue(poll["success"])
                self.assertEqual(len(poll["outputs"]["messages"]), 1)

                send = _parse(self.mcp.get_tool("chat_send_response")(
                    message="We are still in audit.",
                    context={"phase": "0"},
                ))
                self.assertTrue(send["success"])
                self.assertEqual(send["outputs"]["message"]["sender"], "agent")

                context = _parse(self.mcp.get_tool("chat_get_context")(message_limit=10))
                self.assertTrue(context["success"])
                self.assertIn("knowledge_base", context["outputs"])


if __name__ == "__main__":
    unittest.main()

