from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase, mock

from tools.enclave_landing_material_pass_tools import (
    register_enclave_landing_material_pass_tools,
)


class _FakeMcp:
    def __init__(self) -> None:
        self.tools = {}

    def tool(self, *args, **kwargs):
        def decorate(function):
            self.tools[str(kwargs.get("name") or function.__name__)] = function
            return function

        return decorate


class EnclaveLandingMaterialPassToolTests(TestCase):
    def setUp(self) -> None:
        self.mcp = _FakeMcp()
        register_enclave_landing_material_pass_tools(self.mcp)
        self.tool = self.mcp.tools["enclave_landing_material_pass"]

    def _context(self, mode: str):
        preview = mode == "dry_run"
        operation = {
            "operationId": f"enclave-landing-material-pass-{mode}",
            "idempotencyKey": f"enclave-landing-material-pass-{mode}-once",
            "expectedRevision": "enclave-landing-scale-baked-v1",
            "intent": "preview" if preview else "apply",
            "dryRun": preview,
            "affectedStableIds": [
                "/Game/MCPStudio/Enclave/LandingMaterials/v1",
                "UnrealActor:39A96FF046720C0C936788BC9A08FBF1",
            ],
            "rollback": {
                "strategy": "undo",
                "token": "enclave-landing-material-pass-v1",
            },
            "invocationDigest": "b" * 64,
        }
        meta = SimpleNamespace(model_extra={"mcpstudio/operation": operation})
        return SimpleNamespace(request_context=SimpleNamespace(meta=meta))

    def test_dry_run_executes_only_pinned_script(self) -> None:
        with mock.patch(
            "tools.enclave_landing_material_pass_tools._exec_structured",
            return_value={"success": True, "outputs": {"mode": "dry_run"}},
        ) as execute:
            result = self.tool(self._context("dry_run"), mode="dry_run")
        self.assertEqual(result["operationReceipt"]["outcome"], "previewed")
        code, stage = execute.call_args.args
        self.assertIn("MCPSTUDIO_MODE = 'dry_run'", code)
        self.assertEqual(stage, "enclave_landing_material_pass_dry_run")

    def test_apply_requires_confirmation_and_defers_first_mutation(self) -> None:
        with mock.patch(
            "tools.enclave_landing_material_pass_tools._exec_structured"
        ) as execute:
            with self.assertRaisesRegex(RuntimeError, "confirm_operation=true"):
                self.tool(self._context("apply"), mode="apply")
        execute.assert_not_called()

    def test_apply_returns_replay_receipt(self) -> None:
        with mock.patch(
            "tools.enclave_landing_material_pass_tools._exec_structured",
            return_value={
                "success": True,
                "outputs": {"idempotent_replay": True, "content_root": "/Game/MCPStudio/Enclave/LandingMaterials/v1"},
            },
        ):
            result = self.tool(
                self._context("apply"), mode="apply", confirm_operation=True
            )
        self.assertEqual(result["operationReceipt"]["outcome"], "replayed")


if __name__ == "__main__":
    import unittest

    unittest.main()
