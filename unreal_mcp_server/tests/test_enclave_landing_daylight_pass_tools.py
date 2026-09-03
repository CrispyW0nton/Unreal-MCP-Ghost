from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase, mock

from tools import enclave_landing_daylight_pass_tools as tools


class _FakeMcp:
    def __init__(self) -> None:
        self.tools = {}
    def tool(self, *args, **kwargs):
        def decorate(function):
            self.tools[str(kwargs.get("name") or function.__name__)] = function
            return function
        return decorate


class EnclaveLandingDaylightPassToolTests(TestCase):
    def setUp(self) -> None:
        mcp = _FakeMcp()
        tools.register_enclave_landing_daylight_pass_tools(mcp)
        self.tool = mcp.tools["enclave_landing_daylight_pass"]

    def _context(self, mode: str):
        preview = mode == "dry_run"
        operation = {
            "operationId": "landing-daylight-" + mode,
            "idempotencyKey": "landing-daylight-" + mode,
            "expectedRevision": "enclave-landing-review-v2",
            "intent": "preview" if preview else "apply",
            "dryRun": preview,
            "affectedStableIds": [
                "UnrealActor:648F0DD8460F534C038DBA8FD49BBEBD",
                "UnrealActor:7C51FF6946709420F344E583FE7EC95F",
            ],
            "rollback": {"strategy": "undo", "token": "landing-daylight-v1"},
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

    def test_fixed_scope_contains_no_caller_values(self) -> None:
        source = tools._SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn('DIRECTIONAL_GUID = "648F0DD8460F534C038DBA8FD49BBEBD"', source)
        self.assertIn('SKYLIGHT_GUID = "7C51FF6946709420F344E583FE7EC95F"', source)
        self.assertIn("TARGET_ROTATION = (-35.0, -45.0, 0.0)", source)
        self.assertNotIn("input(", source)


if __name__ == "__main__":
    import unittest
    unittest.main()
