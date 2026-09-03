from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase, mock

from tools.enclave_landing_scale_bake_tools import register_enclave_landing_scale_bake_tools


class _FakeMcp:
    def __init__(self) -> None:
        self.tools = {}

    def tool(self, *args, **kwargs):
        def decorate(function):
            self.tools[str(kwargs.get("name") or function.__name__)] = function
            return function

        return decorate


class EnclaveLandingScaleBakeToolTests(TestCase):
    def setUp(self) -> None:
        self.mcp = _FakeMcp()
        register_enclave_landing_scale_bake_tools(self.mcp)
        self.tool = self.mcp.tools["enclave_landing_scale_bake"]

    def _context(self, mode: str):
        preview = mode == "dry_run"
        operation = {
            "operationId": f"landing-scale-bake-{mode}",
            "idempotencyKey": f"landing-scale-bake-{mode}-once",
            "expectedRevision": "enclave-landing-staged-v1",
            "intent": "preview" if preview else "apply",
            "dryRun": preview,
            "affectedStableIds": [
                "04B40FE441C580AE34D06B94E7FAFBF2",
                "/Game/MCPStudio/Enclave/LandingScaleBake/v1",
            ],
            "rollback": {"strategy": "undo", "token": "landing-scale-bake-v1"},
            "invocationDigest": "c" * 64,
        }
        meta = SimpleNamespace(model_extra={"mcpstudio/operation": operation})
        return SimpleNamespace(request_context=SimpleNamespace(meta=meta))

    def test_dry_run_uses_only_the_pinned_five_actor_script(self) -> None:
        with mock.patch(
            "tools.enclave_landing_scale_bake_tools._exec_structured",
            return_value={"success": True, "outputs": {"mode": "dry_run"}},
        ) as execute:
            result = self.tool(self._context("dry_run"), mode="dry_run")
        self.assertEqual(result["operationReceipt"]["outcome"], "previewed")
        code, stage = execute.call_args.args
        self.assertIn("_MCPSTUDIO_FIXED_MODE = 'dry_run'", code)
        self.assertIn("04B40FE441C580AE34D06B94E7FAFBF2", code)
        self.assertIn("C312879645CACBA863C2FE93E5CC514D", code)
        self.assertIn('settings.set_editor_property("build_scale3d"', code)
        self.assertIn("EditorLoadingAndSavingUtils.save_packages", code)
        self.assertEqual(stage, "enclave_landing_scale_bake_dry_run")

    def test_apply_requires_confirmation_and_defers_asset_rebuild(self) -> None:
        with mock.patch(
            "tools.enclave_landing_scale_bake_tools._exec_structured",
            return_value={"success": True, "outputs": {}},
        ) as execute:
            with self.assertRaisesRegex(RuntimeError, "confirm_operation=true"):
                self.tool(self._context("apply"), mode="apply")
            self.tool(self._context("apply"), mode="apply", confirm_operation=True)
        code = execute.call_args.args[0]
        self.assertIn("register_slate_post_tick_callback", code)
        self.assertIn("enclave_landing_scale_bake_v1_receipt.json", code)
        self.assertIn("enclave_landing_scale_bake_v1_persistence.json", code)

    def test_operation_binding_is_mandatory(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "operation binding"):
            self.tool(None, mode="dry_run")


if __name__ == "__main__":
    import unittest

    unittest.main()
