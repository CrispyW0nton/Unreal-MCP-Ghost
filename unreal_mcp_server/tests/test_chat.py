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


class TestChatRoutes(unittest.TestCase):
    def test_send_poll_history_and_clear(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chat_history.json"
            app = Starlette(routes=[
                Route("/chat/send", routes.chat_send, methods=["POST"]),
                Route("/chat/poll", routes.chat_poll, methods=["GET"]),
                Route("/chat/history", routes.chat_history, methods=["GET"]),
                Route("/chat/clear", routes.chat_clear, methods=["POST"]),
            ])

            with patch.object(storage, "DEFAULT_CHAT_HISTORY_PATH", path):
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

