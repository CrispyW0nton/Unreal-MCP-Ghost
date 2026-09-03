"""Manual paid-provider lane smoke for Tripo and Uthana no-spend checks.

This file is intentionally not named ``test_*.py`` so default offline CI never
discovers it. Run it only after explicit operator approval:

    $env:RUN_UNREAL_MCP_PAID_PROVIDER_SMOKE='1'
    $env:UNREAL_MCP_PROVIDER_NETWORK_APPROVED='1'
    $env:UNREAL_MCP_CONFIRM_NO_SPEND_PROVIDER_CHECKS='1'
    # Optional: prove Uthana async job status for an existing video-to-motion job.
    # $env:UTHANA_SMOKE_JOB_ID='<existing-job-id>'
    # Optional: prove Uthana pre-download allowance for an existing motion.
    # $env:UTHANA_SMOKE_MOTION_ID='<existing-motion-id>'
    python -m unittest unreal_mcp_server.tests.paid_provider_generative_smoke

The smoke performs provider-network auth/quota checks only. It must not submit
Tripo generation tasks, create Uthana motions, download files, import assets,
reserve credits, run PIE, or mutate Unreal.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))


class _MockMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn
        return decorator


def _approved() -> bool:
    return (
        os.environ.get("RUN_UNREAL_MCP_PAID_PROVIDER_SMOKE") == "1"
        and os.environ.get("UNREAL_MCP_PROVIDER_NETWORK_APPROVED") == "1"
        and os.environ.get("UNREAL_MCP_CONFIRM_NO_SPEND_PROVIDER_CHECKS") == "1"
    )


def _assert_structured(testcase: unittest.TestCase, payload: dict, stage: str):
    for key in ("success", "stage", "message", "inputs", "outputs", "warnings", "errors", "log_tail", "meta"):
        testcase.assertIn(key, payload)
    testcase.assertEqual(payload["stage"], stage)
    testcase.assertEqual(payload["meta"]["tool"], stage)


class PaidProviderGenerativeSmoke(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        if not _approved():
            self.skipTest(
                "Set RUN_UNREAL_MCP_PAID_PROVIDER_SMOKE=1, "
                "UNREAL_MCP_PROVIDER_NETWORK_APPROVED=1, and "
                "UNREAL_MCP_CONFIRM_NO_SPEND_PROVIDER_CHECKS=1 to run this manual no-spend provider lane."
            )

        from tools.generative_tools import register_generative_tools

        self.mcp = _MockMCP()
        register_generative_tools(self.mcp)

    async def _provider_config(self) -> dict:
        payload = json.loads(await self.mcp.tools["gen_get_provider_config"](
            ctx=None,
            include_paths=False,
        ))
        _assert_structured(self, payload, "gen_get_provider_config")
        self.assertTrue(payload["success"])
        text = json.dumps(payload)
        for env_name in ("TRIPO_API_KEY", "UTHANA_API_KEY"):
            raw = os.environ.get(env_name, "")
            if raw:
                self.assertNotIn(raw, text)
        self.assertFalse(payload["outputs"].get("network_required", True))
        self.assertFalse(payload["outputs"].get("spend_required", True))
        return payload

    async def test_provider_config_is_masked_and_no_spend(self):
        payload = await self._provider_config()

        self.assertIn("api_key_configured", payload["outputs"])
        self.assertIn("uthana_api_key_configured", payload["outputs"])
        self.assertNotIn("settings_path", payload["outputs"])
        self.assertNotIn("secrets_path", payload["outputs"])

    async def test_tripo_wallet_balance_is_no_spend(self):
        config = await self._provider_config()
        if not config["outputs"].get("api_key_configured", False):
            self.skipTest("TRIPO_API_KEY or Saved/MCPChat/secrets.json Tripo key is required for this provider lane.")

        payload = json.loads(await self.mcp.tools["gen_tripo_get_credit_balance"](
            ctx=None,
            include_raw=False,
            timeout_s=30,
        ))

        _assert_structured(self, payload, "gen_tripo_get_credit_balance")
        self.assertEqual(payload["outputs"]["provider"], "tripo")
        self.assertTrue(payload["outputs"]["network_required"])
        self.assertFalse(payload["outputs"]["spend_required"])
        self.assertNotIn("raw_response", payload["outputs"])
        self.assertIn("api_wallet", payload["outputs"])

    async def test_uthana_account_allowance_is_no_spend(self):
        config = await self._provider_config()
        if not config["outputs"].get("uthana_api_key_configured", False):
            self.skipTest("UTHANA_API_KEY or Saved/MCPChat/secrets.json Uthana key is required for this provider lane.")

        payload = json.loads(await self.mcp.tools["gen_uthana_get_account"](
            ctx=None,
            include_user=False,
            timeout_s=30,
        ))

        _assert_structured(self, payload, "gen_uthana_get_account")
        self.assertEqual(payload["outputs"]["provider"], "uthana")
        self.assertTrue(payload["outputs"]["network_required"])
        self.assertFalse(payload["outputs"]["spend_required"])
        self.assertNotIn("email", payload["outputs"].get("user", {}))
        self.assertIn("motion_download_secs_per_month_remaining", payload["outputs"])

    async def test_uthana_job_status_is_no_spend_when_job_id_is_supplied(self):
        config = await self._provider_config()
        if not config["outputs"].get("uthana_api_key_configured", False):
            self.skipTest("UTHANA_API_KEY or Saved/MCPChat/secrets.json Uthana key is required for this provider lane.")

        job_id = os.environ.get("UTHANA_SMOKE_JOB_ID", "").strip()
        if not job_id:
            self.skipTest("Set UTHANA_SMOKE_JOB_ID to an existing Uthana job ID to verify async job status.")

        payload = json.loads(await self.mcp.tools["gen_uthana_get_job"](
            ctx=None,
            job_id=job_id,
            timeout_s=30,
        ))

        _assert_structured(self, payload, "gen_uthana_get_job")
        self.assertEqual(payload["outputs"]["provider"], "uthana")
        self.assertTrue(payload["outputs"]["network_required"])
        self.assertFalse(payload["outputs"]["spend_required"])
        self.assertIn("job_status", payload["outputs"])
        self.assertIn("download_ready", payload["outputs"])
        self.assertNotIn("download", payload["outputs"])

    async def test_uthana_download_allowance_is_no_spend_when_motion_id_is_supplied(self):
        config = await self._provider_config()
        if not config["outputs"].get("uthana_api_key_configured", False):
            self.skipTest("UTHANA_API_KEY or Saved/MCPChat/secrets.json Uthana key is required for this provider lane.")

        motion_id = os.environ.get("UTHANA_SMOKE_MOTION_ID", "").strip()
        if not motion_id:
            self.skipTest("Set UTHANA_SMOKE_MOTION_ID to an existing motion ID to verify pre-download allowance.")

        payload = json.loads(await self.mcp.tools["gen_uthana_check_download_allowed"](
            ctx=None,
            motion_id=motion_id,
            timeout_s=30,
        ))

        _assert_structured(self, payload, "gen_uthana_check_download_allowed")
        self.assertEqual(payload["outputs"]["provider"], "uthana")
        self.assertTrue(payload["outputs"]["network_required"])
        self.assertFalse(payload["outputs"]["spend_required"])
        self.assertIn("allowed", payload["outputs"])
        self.assertIn("reason", payload["outputs"])
        self.assertNotIn("download", payload["outputs"])


if __name__ == "__main__":
    unittest.main()
