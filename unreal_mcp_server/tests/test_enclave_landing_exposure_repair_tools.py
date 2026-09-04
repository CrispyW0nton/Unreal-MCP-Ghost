from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase, mock

from tools import enclave_landing_exposure_repair_tools as tools


class _FakeMcp:
    def __init__(self) -> None:
        self.tools = {}

    def tool(self, *args, **kwargs):
        def decorate(function):
            self.tools[str(kwargs.get("name") or function.__name__)] = function
            return function

        return decorate


class EnclaveLandingExposureRepairToolTests(TestCase):
    def setUp(self) -> None:
        mcp = _FakeMcp()
        tools.register_enclave_landing_exposure_repair_tools(mcp)
        self.tool = mcp.tools["enclave_landing_exposure_repair"]

    def _context(self, mode: str):
        preview = mode == "dry_run"
        operation = {
            "operationId": "landing-exposure-" + mode,
            "idempotencyKey": "landing-exposure-" + mode,
            "expectedRevision": "enclave-landing-review-capture-v1",
            "intent": "preview" if preview else "apply",
            "dryRun": preview,
            "affectedStableIds": [
                "UnrealActor:61AEAD1E4CCA665CDAB8ACB3E4D9F68C",
                "/Game/ThirdPerson/Lvl_ThirdPerson",
            ],
            "rollback": {"strategy": "undo", "token": "landing-exposure-v1"},
            "invocationDigest": "a" * 64,
        }
        meta = SimpleNamespace(model_extra={"mcpstudio/operation": operation})
        return SimpleNamespace(request_context=SimpleNamespace(meta=meta))

    def test_dry_run_executes_digest_pinned_script(self) -> None:
        with mock.patch.object(
            tools,
            "_exec_structured",
            return_value={"success": True, "outputs": {"mode": "dry_run"}},
        ) as execute:
            result = self.tool(self._context("dry_run"), mode="dry_run")
        self.assertEqual(result["operationReceipt"]["outcome"], "previewed")
        code, stage = execute.call_args.args
        self.assertIn("MCPSTUDIO_MODE = 'dry_run'", code)
        self.assertEqual(stage, "enclave_landing_exposure_repair_dry_run")

    def test_apply_requires_confirmation(self) -> None:
        with mock.patch.object(tools, "_exec_structured") as execute:
            with self.assertRaisesRegex(RuntimeError, "confirm_operation=true"):
                self.tool(self._context("apply"), mode="apply")
        execute.assert_not_called()

    def test_fixed_script_changes_only_two_exposure_overrides(self) -> None:
        source = tools._SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn('settings.set_editor_property("override_auto_exposure_min_brightness", False)', source)
        self.assertIn('settings.set_editor_property("override_auto_exposure_max_brightness", False)', source)
        self.assertNotIn('set_editor_property("intensity"', source)
        self.assertNotIn('set_editor_property("fog_density"', source)


if __name__ == "__main__":
    import unittest

    unittest.main()
