from __future__ import annotations

import inspect
import json
from unittest import TestCase, mock

from tools import enclave_landing_lighting_audit_tools as tools


class _FakeMcp:
    def __init__(self) -> None:
        self.tools = {}

    def tool(self, *args, **kwargs):
        def decorate(function):
            self.tools[str(kwargs.get("name") or function.__name__)] = function
            return function

        return decorate


class EnclaveLandingLightingAuditToolTests(TestCase):
    def setUp(self) -> None:
        self.mcp = _FakeMcp()
        tools.register_enclave_landing_lighting_audit_tools(self.mcp)
        self.tool = self.mcp.tools["enclave_landing_lighting_audit"]

    def test_executes_only_digest_pinned_script(self) -> None:
        observed = {
            "success": True,
            "outputs": {
                "schema": "unreal_mcp_ghost.enclave-landing-lighting-audit/v1"
            },
        }
        with mock.patch.object(tools, "_exec_structured", return_value=observed) as execute:
            result = self.tool(object())
        self.assertEqual(json.loads(result), observed)
        code, stage = execute.call_args.args
        self.assertIn("EXPECTED_MAP = \"/Game/ThirdPerson/Lvl_ThirdPerson\"", code)
        self.assertEqual(stage, "enclave_landing_lighting_audit")

    def test_surface_is_read_only_and_accepts_no_scope_parameters(self) -> None:
        signature = inspect.signature(self.tool)
        self.assertEqual(list(signature.parameters), ["ctx"])
        source = inspect.getsource(tools.register_enclave_landing_lighting_audit_tools)
        self.assertIn("readOnlyHint=True", source)
        self.assertIn("destructiveHint=False", source)

    def test_fixed_script_has_explicit_property_allowlists(self) -> None:
        source = tools._SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("POST_PROCESS_PROPERTIES", source)
        self.assertIn("DIRECTIONAL_PROPERTIES", source)
        self.assertIn("SKYLIGHT_PROPERTIES", source)
        self.assertNotIn("__dict__", source)
        self.assertNotIn("inspect.", source)
        self.assertNotIn("exec(", source)


if __name__ == "__main__":
    import unittest

    unittest.main()
