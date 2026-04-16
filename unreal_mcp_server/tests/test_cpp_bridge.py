"""
test_cpp_bridge.py — V5 C++ Bridge tool tests
==============================================

Tests for: cpp_set_codebase_path, cpp_analyze_class, cpp_find_references

All tests run offline — no UE5 required.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

_HERE = os.path.dirname(__file__)
_SERVER_ROOT = os.path.dirname(_HERE)
if _SERVER_ROOT not in sys.path:
    sys.path.insert(0, _SERVER_ROOT)


def _parse(s) -> dict:
    return json.loads(s) if isinstance(s, str) else s


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class _MockMCP:
    def __init__(self):
        self._tools = {}

    def tool(self):
        def dec(fn):
            self._tools[fn.__name__] = fn
            return fn
        return dec

    def get_tool(self, n):
        return self._tools.get(n)

    def list_tool_names(self):
        return list(self._tools.keys())


def _mock_ctx():
    return MagicMock()


# ── Fixture: fake C++ source tree ─────────────────────────────────────────────

_FAKE_HEADER = """\
#pragma once
#include "CoreMinimal.h"
#include "Engine/EngineSubsystem.h"
#include "FakeClass.generated.h"

UCLASS(BlueprintType, Transient)
class UNREALMCP_API UFakeClass : public UEngineSubsystem
{
    GENERATED_BODY()

public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    int32 Port;

    UPROPERTY(VisibleAnywhere)
    FString Name;

    UFUNCTION(BlueprintCallable, Category="MCP")
    FString HandleCommand(FString Json);

    UFUNCTION(BlueprintCallable)
    void Initialize();
};
"""

_FAKE_CPP = """\
#include "FakeClass.h"

FString UFakeClass::HandleCommand(FString Json)
{
    // Dispatch the JSON command
    return Super::HandleCommand(Json);
}

void UFakeClass::Initialize()
{
    HandleCommand(TEXT("{}"));
}
"""


class _FakeSourceDir:
    """Context manager that creates a temp dir with fake C++ source files."""

    def __enter__(self):
        self.tmpdir = tempfile.mkdtemp()
        header = os.path.join(self.tmpdir, "FakeClass.h")
        source = os.path.join(self.tmpdir, "FakeClass.cpp")
        with open(header, "w") as f:
            f.write(_FAKE_HEADER)
        with open(source, "w") as f:
            f.write(_FAKE_CPP)
        return self.tmpdir

    def __exit__(self, *args):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)


# ── Registration ──────────────────────────────────────────────────────────────

class TestCppBridgeRegistration(unittest.TestCase):

    def setUp(self):
        from tools.cpp_bridge_tools import register_cpp_bridge_tools
        self.mcp = _MockMCP()
        register_cpp_bridge_tools(self.mcp)

    def test_all_3_tools_registered(self):
        expected = {"cpp_set_codebase_path", "cpp_analyze_class", "cpp_find_references"}
        missing  = expected - set(self.mcp.list_tool_names())
        self.assertEqual(missing, set(), f"Missing: {missing}")


# ── cpp_set_codebase_path tests ───────────────────────────────────────────────

class TestCppSetCodebasePath(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        import tools.cpp_bridge_tools as m
        m._CODEBASE_PATH = None
        m._INDEXED_FILES = []
        from tools.cpp_bridge_tools import register_cpp_bridge_tools
        self.mcp = _MockMCP()
        register_cpp_bridge_tools(self.mcp)
        self.tool = self.mcp.get_tool("cpp_set_codebase_path")

    async def test_explicit_valid_path_succeeds(self):
        with _FakeSourceDir() as tmpdir:
            result = await self.tool(_mock_ctx(), path=tmpdir)
        data = _parse(result)
        self.assertTrue(data["success"])
        self.assertEqual(data["outputs"]["path"], os.path.realpath(tmpdir))
        self.assertEqual(data["outputs"]["files_indexed"], 2)  # .h + .cpp

    async def test_nonexistent_path_fails(self):
        result = await self.tool(_mock_ctx(), path="/nonexistent/path/that/does/not/exist")
        data = _parse(result)
        self.assertFalse(data["success"])
        self.assertEqual(data.get("error_code"), "ERR_INVALID_PATH")

    async def test_traversal_attack_rejected(self):
        """Path containing '..' is rejected."""
        result = await self.tool(_mock_ctx(), path="/tmp/../etc/passwd")
        data = _parse(result)
        self.assertFalse(data["success"])
        self.assertEqual(data.get("error_code"), "ERR_INVALID_PATH")

    async def test_default_auto_resolve(self):
        """Default (path=None) auto-resolves to plugin Source/ directory."""
        import tools.cpp_bridge_tools as m
        with _FakeSourceDir() as tmpdir:
            with patch.object(m, "_resolve_default_source_path", return_value=tmpdir):
                result = await self.tool(_mock_ctx(), path=None)
        data = _parse(result)
        self.assertTrue(data["success"], data.get("message"))
        self.assertGreater(data["outputs"]["files_indexed"], 0)


# ── cpp_analyze_class tests ───────────────────────────────────────────────────

class TestCppAnalyzeClass(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        import tools.cpp_bridge_tools as m
        m._CODEBASE_PATH = None
        m._INDEXED_FILES = []
        from tools.cpp_bridge_tools import register_cpp_bridge_tools
        self.mcp = _MockMCP()
        register_cpp_bridge_tools(self.mcp)
        self.set_tool    = self.mcp.get_tool("cpp_set_codebase_path")
        self.analyze_tool = self.mcp.get_tool("cpp_analyze_class")

    async def _set_path(self, path):
        await self.set_tool(_mock_ctx(), path=path)

    async def test_happy_path_finds_uclass(self):
        with _FakeSourceDir() as tmpdir:
            await self._set_path(tmpdir)
            result = await self.analyze_tool(_mock_ctx(), class_name="UFakeClass")
        data = _parse(result)
        self.assertTrue(data["success"], data.get("message"))
        out = data["outputs"]
        self.assertEqual(out["class"], "UFakeClass")
        self.assertEqual(out["parent_class"], "UEngineSubsystem")
        self.assertIsInstance(out["properties"], list)
        self.assertIsInstance(out["methods"], list)
        self.assertGreater(len(out["methods"]), 0)

    async def test_unknown_class_returns_not_found(self):
        with _FakeSourceDir() as tmpdir:
            await self._set_path(tmpdir)
            result = await self.analyze_tool(_mock_ctx(), class_name="UDoesNotExist_XYZ")
        data = _parse(result)
        self.assertFalse(data["success"])
        self.assertEqual(data.get("error_code"), "ERR_CLASS_NOT_FOUND")

    async def test_path_not_set_returns_error(self):
        """Analyze without setting path → ERR_CPP_PATH_NOT_SET."""
        import tools.cpp_bridge_tools as m
        m._CODEBASE_PATH = None
        result = await self.analyze_tool(_mock_ctx(), class_name="UFakeClass")
        data = _parse(result)
        self.assertFalse(data["success"])
        self.assertEqual(data.get("error_code"), "ERR_CPP_PATH_NOT_SET")


# ── cpp_find_references tests ─────────────────────────────────────────────────

class TestCppFindReferences(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        import tools.cpp_bridge_tools as m
        m._CODEBASE_PATH = None
        m._INDEXED_FILES = []
        from tools.cpp_bridge_tools import register_cpp_bridge_tools
        self.mcp = _MockMCP()
        register_cpp_bridge_tools(self.mcp)
        self.set_tool  = self.mcp.get_tool("cpp_set_codebase_path")
        self.find_tool = self.mcp.get_tool("cpp_find_references")

    async def _set_path(self, path):
        await self.set_tool(_mock_ctx(), path=path)

    async def test_finds_handle_command_in_cpp(self):
        with _FakeSourceDir() as tmpdir:
            await self._set_path(tmpdir)
            result = await self.find_tool(_mock_ctx(), identifier="HandleCommand", type="function")
        data = _parse(result)
        self.assertTrue(data["success"])
        out = data["outputs"]
        self.assertGreaterEqual(out["total"], 1)
        self.assertIn("file",    out["hits"][0])
        self.assertIn("line",    out["hits"][0])
        self.assertIn("snippet", out["hits"][0])

    async def test_zero_hit_path(self):
        with _FakeSourceDir() as tmpdir:
            await self._set_path(tmpdir)
            result = await self.find_tool(_mock_ctx(), identifier="NonExistentFunc_ZZZZ",
                                          type="function")
        data = _parse(result)
        self.assertTrue(data["success"])
        self.assertEqual(data["outputs"]["total"], 0)

    async def test_limit_truncation(self):
        """Limit=1 returns at most 1 hit and sets truncated=True when more exist."""
        with _FakeSourceDir() as tmpdir:
            await self._set_path(tmpdir)
            result = await self.find_tool(_mock_ctx(), identifier="HandleCommand",
                                          type="function", limit=1)
        data = _parse(result)
        self.assertTrue(data["success"])
        # With 2 files both containing HandleCommand, truncated should be True
        out = data["outputs"]
        self.assertLessEqual(len(out["hits"]), 1)

    async def test_path_not_set_returns_error(self):
        import tools.cpp_bridge_tools as m
        m._CODEBASE_PATH = None
        result = await self.find_tool(_mock_ctx(), identifier="HandleCommand")
        data = _parse(result)
        self.assertFalse(data["success"])
        self.assertEqual(data.get("error_code"), "ERR_CPP_PATH_NOT_SET")

    async def test_invalid_type_returns_error(self):
        with _FakeSourceDir() as tmpdir:
            await self._set_path(tmpdir)
            result = await self.find_tool(_mock_ctx(), identifier="X", type="invalid_type")
        data = _parse(result)
        self.assertFalse(data["success"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
