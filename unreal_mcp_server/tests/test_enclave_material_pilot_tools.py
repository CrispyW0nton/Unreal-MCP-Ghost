from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase, mock

from tools.enclave_material_pilot_tools import register_enclave_material_pilot_tools


class _FakeMcp:
    def __init__(self) -> None:
        self.tools = {}

    def tool(self, *args, **kwargs):
        def decorate(function):
            self.tools[str(kwargs.get("name") or function.__name__)] = function
            return function

        return decorate


class EnclaveMaterialPilotToolTests(TestCase):
    def setUp(self) -> None:
        self.mcp = _FakeMcp()
        register_enclave_material_pilot_tools(self.mcp)
        self.tool = self.mcp.tools["enclave_sandstone_pilot"]

    def _context(self, mode: str):
        preview = mode == "dry_run"
        operation = {
            "operationId": f"enclave-pilot-{mode}",
            "idempotencyKey": f"enclave-pilot-{mode}-once",
            "expectedRevision": "enclave-working-copy-v1",
            "intent": "preview" if preview else "apply",
            "dryRun": preview,
            "affectedStableIds": ["/Game/MCPStudio/EnclavePilot/v1"],
            "rollback": {"strategy": "undo", "token": "enclave-pilot-v1"},
            "invocationDigest": "a" * 64,
        }
        meta = SimpleNamespace(model_extra={"mcpstudio/operation": operation})
        return SimpleNamespace(request_context=SimpleNamespace(meta=meta))

    def test_dry_run_executes_only_the_pinned_dry_run_script(self) -> None:
        with mock.patch(
            "tools.enclave_material_pilot_tools._exec_structured",
            return_value={"success": True, "outputs": {"mode": "dry_run"}},
        ) as execute:
            result = self.tool(
                self._context("dry_run"),
                mode="dry_run",
                confirm_operation=False,
            )
        receipt = result["operationReceipt"]
        self.assertEqual(receipt["outcome"], "previewed")
        self.assertEqual(receipt["beforeRevision"], receipt["afterRevision"])
        code, stage = execute.call_args.args
        self.assertIn('"mode": "dry_run"', code)
        self.assertEqual(stage, "enclave_sandstone_pilot_dry_run")

    def test_apply_fails_closed_without_explicit_confirmation(self) -> None:
        with mock.patch("tools.enclave_material_pilot_tools._exec_structured") as execute:
            with self.assertRaisesRegex(RuntimeError, "confirm_operation=true"):
                self.tool(
                    self._context("apply"),
                    mode="apply",
                    confirm_operation=False,
                )
        execute.assert_not_called()

    def test_apply_and_rollback_select_distinct_pinned_scripts(self) -> None:
        with mock.patch(
            "tools.enclave_material_pilot_tools._exec_structured",
            return_value={"success": True, "outputs": {}},
        ) as execute:
            self.tool(
                self._context("apply"), mode="apply", confirm_operation=True
            )
            apply_code = execute.call_args.args[0]
            self.tool(
                self._context("rollback"),
                mode="rollback",
                confirm_operation=True,
            )
            rollback_code = execute.call_args.args[0]
        self.assertIn('"mode": "apply"', apply_code)
        self.assertIn("register_slate_post_tick_callback", apply_code)
        self.assertIn("unregister_slate_post_tick_callback", apply_code)
        self.assertIn('"mode": "rollback"', rollback_code)
        self.assertNotEqual(apply_code, rollback_code)

    def test_first_apply_fails_closed_after_queueing_deferred_work(self) -> None:
        with mock.patch(
            "tools.enclave_material_pilot_tools._exec_structured",
            return_value={
                "success": True,
                "outputs": {
                    "queued_deferred_apply": True,
                    "receipt_path": "fixed-receipt.json",
                    "failure_path": "fixed-failure.json",
                },
            },
        ):
            with self.assertRaisesRegex(RuntimeError, "queued on Unreal's next editor tick"):
                self.tool(
                    self._context("apply"), mode="apply", confirm_operation=True
                )

    def test_operation_binding_is_required_and_cannot_be_supplied_as_arguments(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "operation binding"):
            self.tool(None, mode="dry_run", confirm_operation=False)

    def test_apply_returns_an_exact_receipt_and_marks_replay(self) -> None:
        with mock.patch(
            "tools.enclave_material_pilot_tools._exec_structured",
            return_value={
                "success": True,
                "outputs": {
                    "idempotent_replay": True,
                    "content_root": "/Game/MCPStudio/EnclavePilot/v1",
                },
            },
        ):
            result = self.tool(
                self._context("apply"), mode="apply", confirm_operation=True
            )
        receipt = result["operationReceipt"]
        self.assertEqual(receipt["outcome"], "replayed")
        self.assertEqual(receipt["invocationDigest"], "a" * 64)
        self.assertEqual(receipt["affectedStableIds"], ["/Game/MCPStudio/EnclavePilot/v1"])


if __name__ == "__main__":
    import unittest

    unittest.main()
