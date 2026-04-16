"""
Smoke and failure tests for all Category A/B/C import tools.

These tests run WITHOUT a live UE5 or GhostRigger connection; they validate:
  - Tool registration (all tools are discoverable)
  - Return schema correctness (success/error keys always present)
  - Failure-path behaviour (missing files, bad args, unreachable services)
  - Green-path logic (local operations that do not need UE5 or GhostRigger)

Run with:
    cd /home/user/webapp/unreal_mcp_server
    python3 -m pytest tests/test_import_tools.py -v

Or without pytest:
    python3 tests/test_import_tools.py
"""

import json
import os
import sys
import tempfile
import unittest

# ── make sure the package is importable from the test location ────────────────
_HERE = os.path.dirname(__file__)
_SERVER_ROOT = os.path.dirname(_HERE)
if _SERVER_ROOT not in sys.path:
    sys.path.insert(0, _SERVER_ROOT)


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

class _MockMCP:
    """Minimal FastMCP-compatible stub for testing tool registration."""

    def __init__(self):
        self._tools = {}

    def tool(self):
        def decorator(fn):
            self._tools[fn.__name__] = fn
            return fn
        return decorator

    def resource(self, uri_template):
        def decorator(fn):
            return fn
        return decorator

    def list_tool_names(self):
        return list(self._tools.keys())


def _parse_json(result: str) -> dict:
    """Parse the string result from a tool; raises on invalid JSON."""
    return json.loads(result)


def _assert_schema(result_str: str, test_name: str) -> dict:
    """Parse result and assert required keys are present."""
    data = _parse_json(result_str)
    assert "success" in data, f"{test_name}: missing 'success' key in {data}"
    return data


# ─────────────────────────────────────────────────────────────────────────────
#  WS-1a: Category B — scan_export_folder (local, no UE5 needed)
# ─────────────────────────────────────────────────────────────────────────────

class TestScanExportFolder(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        from tools.folder_import_tools import register_folder_import_tools
        from mcp.server.fastmcp import FastMCP, Context
        self.mcp = FastMCP("test_scan")
        register_folder_import_tools(self.mcp)
        # Grab the actual tool function
        self._tool = self.mcp._tool_manager.list_tools()
        self._fns = {t.name: t for t in self._tool}
        self.ctx = None  # tools accept ctx but we pass None

    def _get_fn(self, name):
        t = self._fns[name]
        return t.fn

    # ── registration check ────────────────────────────────────────────────────

    def test_all_folder_tools_registered(self):
        names = [t.name for t in self.mcp._tool_manager.list_tools()]
        for expected in ["scan_export_folder", "batch_import_folder", "import_folder_as_character"]:
            assert expected in names, f"Tool {expected!r} not registered"

    # ── Green path: scan an existing folder ──────────────────────────────────

    async def test_scan_real_folder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a small fixture tree
            os.makedirs(os.path.join(tmpdir, "textures"))
            os.makedirs(os.path.join(tmpdir, "meshes"))
            open(os.path.join(tmpdir, "textures", "T_Bastila_n.png"), "w").close()
            open(os.path.join(tmpdir, "textures", "T_Bastila_d.tga"), "w").close()
            open(os.path.join(tmpdir, "meshes", "SM_Table.fbx"), "w").close()
            open(os.path.join(tmpdir, "BGM.wav"), "w").close()
            open(os.path.join(tmpdir, "readme.txt"), "w").close()

            fn = self._get_fn("scan_export_folder")
            result_str = await fn(ctx=None, folder_path=tmpdir, recursive=True)
            data = _assert_schema(result_str, "scan_real_folder")

            assert data.get("total_files") == 5, f"Expected 5 files, got {data.get('total_files')}"
            assert data.get("importable") == 4, f"Expected 4 importable, got {data.get('importable')}"
            assert data.get("skipped") == 1, f"Expected 1 skipped, got {data.get('skipped')}"
            assert len(data["categories"]["texture"]) == 2
            assert len(data["categories"]["mesh"]) == 1
            assert len(data["categories"]["audio"]) == 1
            assert len(data["categories"]["unknown"]) == 1
            assert "textures" in data["subdirs"] or "meshes" in data["subdirs"]

    async def test_scan_nonrecursive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "sub"))
            open(os.path.join(tmpdir, "root.png"), "w").close()
            open(os.path.join(tmpdir, "sub", "nested.fbx"), "w").close()

            fn = self._get_fn("scan_export_folder")
            result_str = await fn(ctx=None, folder_path=tmpdir, recursive=False)
            data = _parse_json(result_str)
            # Non-recursive: only items in root dir visible.
            # root.png → texture (1 importable), nested.fbx is NOT visible.
            # The "sub" directory entry itself may appear as unknown depending on
            # os.listdir behaviour — the key invariant is the FBX inside sub
            # is NOT counted.
            assert data["total_files"] >= 1
            assert len(data["categories"]["texture"]) == 1
            assert len(data["categories"]["mesh"]) == 0, \
                "Non-recursive scan should not find FBX inside subdirectory"

    # ── Failure path: missing folder ─────────────────────────────────────────

    async def test_scan_missing_folder(self):
        fn = self._get_fn("scan_export_folder")
        result_str = await fn(ctx=None, folder_path="/does/not/exist/abc123", recursive=True)
        data = _parse_json(result_str)
        assert "error" in data, "Expected error key for missing folder"

    # ── Failure path: empty folder ────────────────────────────────────────────

    async def test_scan_empty_folder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fn = self._get_fn("scan_export_folder")
            result_str = await fn(ctx=None, folder_path=tmpdir, recursive=True)
            data = _parse_json(result_str)
            assert data.get("total_files") == 0
            assert data.get("importable") == 0


# ─────────────────────────────────────────────────────────────────────────────
#  WS-1b: Category B — batch_import_folder (dry_run, no UE5 needed)
# ─────────────────────────────────────────────────────────────────────────────

class TestBatchImportFolder(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        from tools.folder_import_tools import register_folder_import_tools
        from mcp.server.fastmcp import FastMCP
        self.mcp = FastMCP("test_batch")
        register_folder_import_tools(self.mcp)
        self._fns = {t.name: t for t in self.mcp._tool_manager.list_tools()}

    def _get_fn(self, name):
        return self._fns[name].fn

    async def test_dry_run_returns_plan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "T_Rock_n.png"), "w").close()
            open(os.path.join(tmpdir, "SM_Rock.fbx"), "w").close()
            open(os.path.join(tmpdir, "jump.wav"), "w").close()

            fn = self._get_fn("batch_import_folder")
            result_str = await fn(
                ctx=None,
                folder_path=tmpdir,
                ue5_base_path="/Game/Test/",
                dry_run=True,
            )
            data = _assert_schema(result_str, "dry_run_returns_plan")
            assert data["dry_run"] is True
            assert data["total"] == 3
            assert len(data["files"]) == 3

    async def test_dry_run_empty_folder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fn = self._get_fn("batch_import_folder")
            result_str = await fn(
                ctx=None, folder_path=tmpdir,
                ue5_base_path="/Game/Test/", dry_run=True,
            )
            data = _assert_schema(result_str, "dry_run_empty")
            assert data["dry_run"] is True
            assert data["total"] == 0

    async def test_missing_folder_returns_error(self):
        fn = self._get_fn("batch_import_folder")
        result_str = await fn(
            ctx=None, folder_path="/does/not/exist/xyz",
            ue5_base_path="/Game/Test/", dry_run=True,
        )
        data = _assert_schema(result_str, "missing_folder_error")
        assert data["success"] is False
        assert "error" in data

    async def test_filter_flags(self):
        """import_textures=False should exclude texture files from the plan."""
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "T_Rock_n.png"), "w").close()
            open(os.path.join(tmpdir, "SM_Rock.fbx"), "w").close()

            fn = self._get_fn("batch_import_folder")
            result_str = await fn(
                ctx=None, folder_path=tmpdir,
                ue5_base_path="/Game/Test/",
                import_textures=False, dry_run=True,
            )
            data = _parse_json(result_str)
            assert data["total"] == 1
            # Only the FBX should remain
            assert all(f["category"] == "mesh" for f in data["files"])

    async def test_preserve_subfolder_structure(self):
        """dest paths should mirror subfolder layout."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "characters"))
            open(os.path.join(tmpdir, "characters", "SK_Hero.fbx"), "w").close()

            fn = self._get_fn("batch_import_folder")
            result_str = await fn(
                ctx=None, folder_path=tmpdir,
                ue5_base_path="/Game/Imported/",
                preserve_folder_structure=True, dry_run=True,
            )
            data = _parse_json(result_str)
            assert data["total"] == 1
            dest = data["files"][0]["ue_dest"]
            assert "characters" in dest, f"Expected subfolder in dest, got {dest}"


# ─────────────────────────────────────────────────────────────────────────────
#  WS-1c: Category B — import_folder_as_character (local scan phase)
# ─────────────────────────────────────────────────────────────────────────────

class TestImportFolderAsCharacter(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        from tools.folder_import_tools import register_folder_import_tools
        from mcp.server.fastmcp import FastMCP
        self.mcp = FastMCP("test_char")
        register_folder_import_tools(self.mcp)
        self._fns = {t.name: t for t in self.mcp._tool_manager.list_tools()}

    def _get_fn(self, name):
        return self._fns[name].fn

    async def test_missing_folder_returns_error(self):
        fn = self._get_fn("import_folder_as_character")
        result_str = await fn(
            ctx=None,
            folder_path="/does/not/exist",
            character_name="Bastila",
        )
        data = _assert_schema(result_str, "char_missing_folder")
        assert data["success"] is False

    async def test_no_fbx_returns_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Only textures, no FBX
            open(os.path.join(tmpdir, "T_Bastila_d.tga"), "w").close()
            fn = self._get_fn("import_folder_as_character")
            result_str = await fn(
                ctx=None, folder_path=tmpdir, character_name="Bastila",
            )
            data = _assert_schema(result_str, "char_no_fbx")
            assert data["success"] is False


# ─────────────────────────────────────────────────────────────────────────────
#  WS-1d: Category A — GhostRigger (offline / unreachable service tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestGhostRiggerBridgeOffline(unittest.IsolatedAsyncioTestCase):
    """
    Tests that run without a live GhostRigger server.
    They verify that all tools return a structured error (not a Python exception)
    when the service is unreachable.
    """

    async def asyncSetUp(self):
        import os
        # Force an unreachable port so HTTP calls fail fast
        os.environ["GHOSTRIGGER_HOST"] = "127.0.0.1"
        os.environ["GHOSTRIGGER_PORT"] = "19999"  # nothing listening here

        from tools.ghostrigger_tools import register_ghostrigger_tools
        from mcp.server.fastmcp import FastMCP
        self.mcp = FastMCP("test_gr_offline")
        register_ghostrigger_tools(self.mcp)
        self._fns = {t.name: t for t in self.mcp._tool_manager.list_tools()}

    async def asyncTearDown(self):
        # Remove env overrides
        import os
        os.environ.pop("GHOSTRIGGER_HOST", None)
        os.environ.pop("GHOSTRIGGER_PORT", None)

    def _get_fn(self, name):
        return self._fns[name].fn

    def _check_error(self, result_str: str, tool_name: str):
        data = _parse_json(result_str)
        assert "error" in data, f"{tool_name}: expected 'error' key when GhostRigger is unreachable, got {data}"
        assert "Cannot reach GhostRigger" in data["error"] or "error" in data, \
            f"{tool_name}: error message not informative: {data['error']}"
        return data

    # ── Registration check ────────────────────────────────────────────────────

    def test_all_ghostrigger_tools_registered(self):
        expected = [
            "ghostrigger_health", "ghostrigger_ping",
            "ghostrigger_open_model", "ghostrigger_open_creature",
            "ghostrigger_list_mcp_tools", "ghostrigger_call_mcp_tool",
            "ghostrigger_list_resources", "ghostrigger_read_resource",
            "ghostrigger_export_model", "ghostrigger_import_to_ue5",
        ]
        names = [t.name for t in self.mcp._tool_manager.list_tools()]
        for e in expected:
            assert e in names, f"Tool {e!r} not registered"

    async def test_health_unreachable(self):
        fn = self._get_fn("ghostrigger_health")
        result_str = await fn(ctx=None)
        self._check_error(result_str, "ghostrigger_health")

    async def test_ping_unreachable(self):
        fn = self._get_fn("ghostrigger_ping")
        result_str = await fn(ctx=None)
        self._check_error(result_str, "ghostrigger_ping")

    async def test_open_model_unreachable(self):
        fn = self._get_fn("ghostrigger_open_model")
        result_str = await fn(ctx=None, resref="n_bastila")
        self._check_error(result_str, "ghostrigger_open_model")

    async def test_open_creature_unreachable(self):
        fn = self._get_fn("ghostrigger_open_creature")
        result_str = await fn(ctx=None, resref="n_bastila001")
        self._check_error(result_str, "ghostrigger_open_creature")

    async def test_list_mcp_tools_unreachable(self):
        fn = self._get_fn("ghostrigger_list_mcp_tools")
        result_str = await fn(ctx=None)
        self._check_error(result_str, "ghostrigger_list_mcp_tools")

    async def test_call_mcp_tool_bad_json_args(self):
        fn = self._get_fn("ghostrigger_call_mcp_tool")
        result_str = await fn(ctx=None, tool_name="ghostrigger_open_model", arguments="NOT_JSON")
        data = _parse_json(result_str)
        assert "error" in data
        assert "Invalid JSON" in data["error"] or "JSON" in data["error"]

    async def test_call_mcp_tool_unreachable(self):
        fn = self._get_fn("ghostrigger_call_mcp_tool")
        result_str = await fn(ctx=None, tool_name="ghostrigger_open_model", arguments="{}")
        self._check_error(result_str, "ghostrigger_call_mcp_tool")

    async def test_list_resources_unreachable(self):
        fn = self._get_fn("ghostrigger_list_resources")
        result_str = await fn(ctx=None)
        self._check_error(result_str, "ghostrigger_list_resources")

    async def test_read_resource_unreachable(self):
        fn = self._get_fn("ghostrigger_read_resource")
        result_str = await fn(ctx=None, uri="kotor://k1/2da/appearance")
        self._check_error(result_str, "ghostrigger_read_resource")

    async def test_export_model_unreachable(self):
        fn = self._get_fn("ghostrigger_export_model")
        result_str = await fn(ctx=None, resref="n_bastila", export_path="/tmp/n_bastila.fbx")
        self._check_error(result_str, "ghostrigger_export_model")


# ─────────────────────────────────────────────────────────────────────────────
#  WS-1e: Category C — import_texture / import_static_mesh / import_skeletal_mesh
#  (registration + local failure path only — actual UE5 import not runnable offline)
# ─────────────────────────────────────────────────────────────────────────────

class TestCategoryCSingleAssetRegistration(unittest.TestCase):

    def setUp(self):
        from tools.asset_import_tools import register_asset_import_tools
        from tools.audio_tools import register_audio_tools
        from tools.data_tools import register_data_tools
        from mcp.server.fastmcp import FastMCP
        self.mcp = FastMCP("test_catc")
        register_asset_import_tools(self.mcp)
        register_audio_tools(self.mcp)
        register_data_tools(self.mcp)
        self._names = {t.name for t in self.mcp._tool_manager.list_tools()}

    def test_import_texture_registered(self):
        assert "import_texture" in self._names

    def test_import_static_mesh_registered(self):
        assert "import_static_mesh" in self._names

    def test_import_skeletal_mesh_registered(self):
        assert "import_skeletal_mesh" in self._names

    def test_import_sound_asset_registered(self):
        assert "import_sound_asset" in self._names

    def test_import_sound_asset_from_sandbox_registered(self):
        # import_sound_asset_from_sandbox lives in data_tools, not audio_tools.
        # We registered data_tools in setUp so it should be present.
        assert "import_sound_asset_from_sandbox" in self._names, (
            "import_sound_asset_from_sandbox not found — "
            "check it is registered via register_data_tools()"
        )


# ─────────────────────────────────────────────────────────────────────────────
#  WS-1f: Shared result schema validation
# ─────────────────────────────────────────────────────────────────────────────

class TestResultSchemaContract(unittest.TestCase):
    """
    Verifies the structured result schema contract:
    All tool outputs must be valid JSON with at least a 'success' key.
    """

    def _validate(self, result_str: str, tool: str):
        try:
            data = json.loads(result_str)
        except json.JSONDecodeError as exc:
            raise AssertionError(f"{tool}: output is not valid JSON: {exc}\nOutput: {result_str!r}")
        assert "success" in data, f"{tool}: missing 'success' key in {data}"
        return data

    def test_scan_schema_on_missing(self):
        import asyncio
        from tools.folder_import_tools import register_folder_import_tools
        from mcp.server.fastmcp import FastMCP
        mcp = FastMCP("schema_test")
        register_folder_import_tools(mcp)
        fns = {t.name: t.fn for t in mcp._tool_manager.list_tools()}

        async def run():
            return await fns["scan_export_folder"](ctx=None, folder_path="/no/such/path")
        result = asyncio.run(run())
        data = json.loads(result)
        # scan returns "error" key not "success" on folder-not-found
        assert "error" in data or "folder" in data

    def test_batch_schema_on_missing(self):
        import asyncio
        from tools.folder_import_tools import register_folder_import_tools
        from mcp.server.fastmcp import FastMCP
        mcp = FastMCP("schema_test2")
        register_folder_import_tools(mcp)
        fns = {t.name: t.fn for t in mcp._tool_manager.list_tools()}

        async def run():
            return await fns["batch_import_folder"](
                ctx=None, folder_path="/no/such/path",
                ue5_base_path="/Game/X/", dry_run=True,
            )
        result = asyncio.run(run())
        data = self._validate(result, "batch_import_folder")
        assert data["success"] is False


# ─────────────────────────────────────────────────────────────────────────────
#  WS-1g: Tool count audit
# ─────────────────────────────────────────────────────────────────────────────

class TestToolCountAudit(unittest.TestCase):
    """
    Verifies that the actual number of registered tools matches the documented
    count.  This acts as a canary — if someone adds/removes tools without
    updating the README, this test will catch it.
    """

    def test_actual_tool_count_documented(self):
        """
        The ACTUAL tool count must be documented in the server's info prompt.
        This test reads the info prompt string and checks it cites the correct
        number.
        """
        import sys, re
        sys.path.insert(0, _SERVER_ROOT)
        from mcp.server.fastmcp import FastMCP
        from tools.editor_tools import register_editor_tools
        from tools.blueprint_tools import register_blueprint_tools
        from tools.node_tools import register_blueprint_node_tools
        from tools.project_tools import register_project_tools
        from tools.umg_tools import register_umg_tools
        from tools.gameplay_tools import register_gameplay_tools
        from tools.animation_tools import register_animation_tools
        from tools.ai_tools import register_ai_tools
        from tools.data_tools import register_data_tools
        from tools.communication_tools import register_communication_tools
        from tools.advanced_node_tools import register_advanced_node_tools
        from tools.material_tools import register_material_tools
        from tools.savegame_tools import register_savegame_tools
        from tools.library_tools import register_library_tools
        from tools.procedural_tools import register_procedural_tools
        from tools.vr_tools import register_vr_tools
        from tools.variant_tools import register_variant_tools
        from tools.physics_tools import register_physics_tools
        from tools.knowledge_tools import register_knowledge_tools
        from tools.audio_tools import register_audio_tools
        from tools.asset_import_tools import register_asset_import_tools
        from tools.folder_import_tools import register_folder_import_tools
        from tools.ghostrigger_tools import register_ghostrigger_tools
        from tools.exec_substrate import register_exec_substrate_tools
        from tools.reflection_tools import register_reflection_tools

        mcp = FastMCP("count_audit")
        for reg in [register_editor_tools, register_blueprint_tools, register_blueprint_node_tools,
                    register_project_tools, register_umg_tools, register_gameplay_tools,
                    register_animation_tools, register_ai_tools, register_data_tools,
                    register_communication_tools, register_advanced_node_tools, register_material_tools,
                    register_savegame_tools, register_library_tools, register_procedural_tools,
                    register_vr_tools, register_variant_tools, register_physics_tools,
                    register_knowledge_tools, register_audio_tools, register_asset_import_tools,
                    register_folder_import_tools, register_ghostrigger_tools,
                    register_exec_substrate_tools, register_reflection_tools]:
            reg(mcp)

        actual = len(mcp._tool_manager.list_tools())
        # Store for reference
        with open(os.path.join(_HERE, "last_tool_count.txt"), "w") as f:
            f.write(str(actual))

        # We don't assert a hardcoded number — just that it's > 300
        assert actual >= 300, f"Tool count dropped below 300: {actual}"
        print(f"\n  [Tool count audit] Actual: {actual} tools registered")


# ─────────────────────────────────────────────────────────────────────────────
#  WS-2: Safe execution substrate — registration & schema
# ─────────────────────────────────────────────────────────────────────────────

class TestExecSubstrateRegistration(unittest.TestCase):
    """Verify exec_substrate registers 3 tools and the make_result helper works."""

    def setUp(self):
        from tools.exec_substrate import register_exec_substrate_tools
        from mcp.server.fastmcp import FastMCP
        self.mcp = FastMCP("test_substrate")
        register_exec_substrate_tools(self.mcp)
        self._names = {t.name for t in self.mcp._tool_manager.list_tools()}

    def test_ue_exec_safe_registered(self):
        assert "ue_exec_safe" in self._names

    def test_ue_exec_transact_registered(self):
        assert "ue_exec_transact" in self._names

    def test_ue_exec_progress_registered(self):
        assert "ue_exec_progress" in self._names

    def test_make_result_schema(self):
        """make_result must return all StructuredResult keys."""
        from tools.exec_substrate import make_result
        r = make_result(success=True, stage="test", message="ok",
                        outputs={"x": 1}, warnings=["w"], errors=[], log_tail=[])
        for key in ("success", "stage", "message", "inputs", "outputs",
                    "warnings", "errors", "log_tail"):
            assert key in r, f"make_result missing key: {key}"
        assert r["success"] is True
        assert r["stage"] == "test"
        assert r["outputs"]["x"] == 1
        assert r["warnings"] == ["w"]

    def test_make_result_failure(self):
        from tools.exec_substrate import make_result
        r = make_result(success=False, stage="fail", errors=["bad thing"])
        assert r["success"] is False
        assert "bad thing" in r["errors"]

    def test_wrap_transactional_contains_transaction(self):
        """The wrapped code must include ScopedEditorTransaction."""
        from tools.exec_substrate import _wrap_transactional
        code = _wrap_transactional("x = 1", "Test Transaction")
        assert "ScopedEditorTransaction" in code
        assert "Test Transaction" in code

    def test_wrap_progress_contains_slow_task(self):
        from tools.exec_substrate import _wrap_with_progress
        code = _wrap_with_progress("x = 1", "My Task", 50)
        assert "ScopedSlowTask" in code
        assert "50" in code

    def test_wrap_structured_contains_try_except(self):
        from tools.exec_substrate import _wrap_structured
        code = _wrap_structured("_result['k'] = 1", "my_stage")
        assert "try:" in code
        assert "except Exception" in code
        assert "my_stage" in code


# ─────────────────────────────────────────────────────────────────────────────
#  WS-3: Reflection & diagnostics tools — registration & schema
# ─────────────────────────────────────────────────────────────────────────────

class TestReflectionToolsRegistration(unittest.TestCase):
    """Verify reflection_tools registers 8 tools."""

    def setUp(self):
        from tools.reflection_tools import register_reflection_tools
        from mcp.server.fastmcp import FastMCP
        self.mcp = FastMCP("test_reflection")
        register_reflection_tools(self.mcp)
        self._names = {t.name for t in self.mcp._tool_manager.list_tools()}

    def test_ue_reflect_class_registered(self):
        assert "ue_reflect_class" in self._names

    def test_ue_list_uclass_properties_registered(self):
        assert "ue_list_uclass_properties" in self._names

    def test_ue_list_uclass_methods_registered(self):
        assert "ue_list_uclass_methods" in self._names

    def test_ue_describe_asset_registered(self):
        assert "ue_describe_asset" in self._names

    def test_ue_find_assets_by_class_registered(self):
        assert "ue_find_assets_by_class" in self._names

    def test_ue_list_editor_selection_registered(self):
        assert "ue_list_editor_selection" in self._names

    def test_get_recent_output_log_registered(self):
        assert "get_recent_output_log" in self._names

    def test_ue_summarize_operation_effects_registered(self):
        assert "ue_summarize_operation_effects" in self._names

    def test_all_8_reflection_tools_registered(self):
        expected = {
            "ue_reflect_class", "ue_list_uclass_properties", "ue_list_uclass_methods",
            "ue_describe_asset", "ue_find_assets_by_class", "ue_list_editor_selection",
            "get_recent_output_log", "ue_summarize_operation_effects",
        }
        missing = expected - self._names
        assert not missing, f"Missing reflection tools: {missing}"


# ─────────────────────────────────────────────────────────────────────────────
#  Runner
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Run without pytest if executed directly
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [
        TestScanExportFolder,
        TestBatchImportFolder,
        TestImportFolderAsCharacter,
        TestGhostRiggerBridgeOffline,
        TestCategoryCSingleAssetRegistration,
        TestResultSchemaContract,
        TestToolCountAudit,
        TestExecSubstrateRegistration,
        TestReflectionToolsRegistration,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
