from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase, mock

from tools import enclave_landing_ground_material_repair_tools as tools


class _FakeMcp:
    def __init__(self) -> None:
        self.tools = {}
    def tool(self, *args, **kwargs):
        def decorate(function):
            self.tools[str(kwargs.get("name") or function.__name__)] = function
            return function
        return decorate


class EnclaveLandingGroundMaterialRepairToolTests(TestCase):
    def setUp(self) -> None:
        mcp = _FakeMcp()
        tools.register_enclave_landing_ground_material_repair_tools(mcp)
        self.tool = mcp.tools["enclave_landing_ground_material_repair"]

    def _context(self, mode: str):
        preview = mode == "dry_run"
        operation = {
            "operationId": "landing-ground-material-" + mode,
            "idempotencyKey": "landing-ground-material-" + mode,
            "expectedRevision": "enclave-landing-daylight-v1",
            "intent": "preview" if preview else "apply",
            "dryRun": preview,
            "affectedStableIds": [
                "UnrealAsset:/Game/MCPStudio/Enclave/LandingMaterials/v1/Materials/M_Enclave_Landing_Grassland_v1",
            ],
            "rollback": {"strategy": "undo", "token": "landing-ground-material-v1"},
            "invocationDigest": "b" * 64,
        }
        meta = SimpleNamespace(model_extra={"mcpstudio/operation": operation})
        return SimpleNamespace(request_context=SimpleNamespace(meta=meta))

    def test_dry_run_executes_digest_pinned_script(self) -> None:
        with mock.patch.object(
            tools, "_exec_structured",
            return_value={"success": True, "outputs": {"mode": "dry_run"}},
        ) as execute:
            result = self.tool(self._context("dry_run"), mode="dry_run")
        self.assertEqual(result["operationReceipt"]["outcome"], "previewed")
        self.assertIn("MCPSTUDIO_MODE = 'dry_run'", execute.call_args.args[0])

    def test_apply_requires_confirmation(self) -> None:
        with mock.patch.object(tools, "_exec_structured") as execute:
            with self.assertRaisesRegex(RuntimeError, "confirm_operation=true"):
                self.tool(self._context("apply"), mode="apply")
        execute.assert_not_called()

    def test_deferred_apply_wrapper_compiles(self) -> None:
        compile(tools._deferred_apply_code("pass"), "<ground-material-deferred>", "exec")

    def test_fixed_scope_contains_physical_tiling_and_no_caller_values(self) -> None:
        source = tools._SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("TARGET_U_TILING = 40.0", source)
        self.assertIn("TARGET_V_TILING = 30.0", source)
        self.assertIn('SOURCE_MATERIAL = "/Game/MCPStudio/Enclave/LandingMaterials/v1/Materials/M_Enclave_Landing_Grassland_v1.M_Enclave_Landing_Grassland_v1"', source)
        self.assertIn('OUTPUT_ROOT = "/Game/MCPStudio/Enclave/LandingMaterials/v2"', source)
        self.assertIn('component.set_material(TARGETS[key]["slot"], material)', source)
        self.assertIn('item["component_overrides"] == [OUTPUT_MATERIAL]', source)
        self.assertIn("_is_partial_mesh_state(current)", source)
        self.assertIn("recoverable_source", source)
        self.assertIn("recoverable_after", source)
        self.assertIn("EditorLoadingAndSavingUtils.save_packages", source)
        self.assertNotIn("set_dirty_flag", source)
        self.assertNotIn("gained component overrides", source)
        self.assertNotIn("input(", source)


if __name__ == "__main__":
    import unittest
    unittest.main()
