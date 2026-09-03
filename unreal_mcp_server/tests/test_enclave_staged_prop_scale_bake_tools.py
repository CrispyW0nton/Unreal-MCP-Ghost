from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase, mock

from tools.enclave_staged_prop_scale_bake_tools import (
    register_enclave_staged_prop_scale_bake_tools,
)


class _FakeMcp:
    def __init__(self) -> None:
        self.tools = {}

    def tool(self, *args, **kwargs):
        def decorate(function):
            self.tools[str(kwargs.get("name") or function.__name__)] = function
            return function

        return decorate


class EnclaveStagedPropScaleBakeToolTests(TestCase):
    def setUp(self) -> None:
        self.mcp = _FakeMcp()
        register_enclave_staged_prop_scale_bake_tools(self.mcp)
        self.tool = self.mcp.tools["enclave_staged_prop_scale_bake"]

    def _context(self, mode: str, batch: int = 0):
        preview = mode == "dry_run"
        operation = {
            "operationId": f"staged-scale-bake-{mode}-{batch}",
            "idempotencyKey": f"staged-scale-bake-{mode}-{batch}-once",
            "expectedRevision": "enclave-staged-modular-v1",
            "intent": "preview" if preview else "apply",
            "dryRun": preview,
            "affectedStableIds": [
                f"enclave-staged-scale-bake-batch-{batch}",
                f"/Game/MCPStudio/Enclave/StagedScaleBake/v1/Batch{batch}",
            ],
            "rollback": {"strategy": "undo", "token": f"staged-scale-bake-v1-{batch}"},
            "invocationDigest": "d" * 64,
        }
        meta = SimpleNamespace(model_extra={"mcpstudio/operation": operation})
        return SimpleNamespace(request_context=SimpleNamespace(meta=meta))

    def test_dry_run_is_pinned_to_modular_kit_and_stable_batch(self) -> None:
        with mock.patch(
            "tools.enclave_staged_prop_scale_bake_tools._exec_structured",
            return_value={"success": True, "outputs": {"mode": "dry_run"}},
        ) as execute:
            result = self.tool(self._context("dry_run", 3), mode="dry_run", batch=3)
        self.assertEqual(result["operationReceipt"]["outcome"], "previewed")
        code, stage = execute.call_args.args
        self.assertIn("_MCPSTUDIO_FIXED_MODE = 'dry_run'", code)
        self.assertIn("_MCPSTUDIO_FIXED_BATCH = 3", code)
        self.assertIn("/Game/LevelPrototyping/ModularKit/", code)
        self.assertIn("BATCH_COUNT = 8", code)
        self.assertIn("MergeStaticMeshActorsOptions", code)
        self.assertNotIn("Cube blockout", code)
        self.assertEqual(stage, "enclave_staged_prop_scale_bake_dry_run_batch_3")

    def test_apply_requires_confirmation_and_defers_merge_work(self) -> None:
        with mock.patch(
            "tools.enclave_staged_prop_scale_bake_tools._exec_structured",
            return_value={"success": True, "outputs": {}},
        ) as execute:
            with self.assertRaisesRegex(RuntimeError, "confirm_operation=true"):
                self.tool(self._context("apply"), mode="apply", batch=0)
            self.tool(
                self._context("apply"),
                mode="apply",
                batch=0,
                confirm_operation=True,
            )
        code = execute.call_args.args[0]
        self.assertIn("register_slate_post_tick_callback", code)
        self.assertIn("enclave_staged_prop_scale_bake_v1_batch_0_receipt.json", code)
        self.assertIn("enclave_staged_prop_scale_bake_v1_batch_0_failure.json", code)

    def test_batch_is_bounded(self) -> None:
        with self.assertRaisesRegex(ValueError, "batch must be between 0 and 7"):
            self.tool(self._context("dry_run"), mode="dry_run", batch=8)


if __name__ == "__main__":
    import unittest

    unittest.main()
