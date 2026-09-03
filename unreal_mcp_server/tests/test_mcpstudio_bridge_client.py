from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from mcpstudio_bridge_client import (
    CapturePolicy,
    McpStudioUnrealConnection,
    _canonical_bytes,
    _sign,
    _verify,
)


class McpStudioBridgeClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name).resolve()
        self.token = "ab" * 32
        self.token_file = self.root / "unreal_mcp_bridge.token"
        self.token_file.write_text(f"{self.token}\n", encoding="ascii")
        self.spool = self.root / "unreal-spatial-bridge-spool"
        self.requests = self.spool / "requests"
        self.responses = self.spool / "responses"
        self.requests.mkdir(parents=True)
        self.responses.mkdir()
        self.capture_path = self.root / "landing_review.png"
        self.capture_policy_path = self.root / "capture-policy.json"
        self.capture_policy_path.write_text(
            json.dumps(
                {
                    "focus_views": [
                        {
                            "location": [-14500.0, -12000.0, 5800.0],
                            "distance": 0.0,
                            "orientation": [-17.3, 47.8, 0.0],
                        }
                    ],
                    "screenshot_paths": [str(self.capture_path)],
                    "screenshot_resolution": [1600, 900],
                }
            ),
            encoding="utf-8",
        )
        self.environment = {
            "UNREAL_MCP_REQUIRE_AUTH": "1",
            "UNREAL_MCP_PRIVATE_TOKEN_FILE": str(self.token_file),
            "UNREAL_MCP_SPOOL_ROOT": str(self.spool),
            "UNREAL_MCP_SPOOL_TIMEOUT_MS": "2000",
            "UNREAL_MCP_SPOOL_MAX_RESPONSE_BYTES": "1048576",
            "UNREAL_MCP_SPATIAL_CAPTURE_POLICY": str(self.capture_policy_path),
        }

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def test_exec_python_round_trip_is_authenticated_and_digest_bound(self) -> None:
        observed: dict[str, object] = {}

        def broker() -> None:
            deadline = time.monotonic() + 1.5
            request_path = None
            while time.monotonic() < deadline:
                candidates = list(self.requests.glob("*.json"))
                if candidates:
                    request_path = candidates[0]
                    break
                time.sleep(0.01)
            self.assertIsNotNone(request_path)
            envelope = json.loads(request_path.read_text(encoding="utf-8"))
            request_id = request_path.stem
            request, request_digest = _verify(
                envelope, self.token.encode("ascii"), request_id
            )
            observed.update(request)
            response = {
                "schema": "unreal-spatial-bridge-spool/v1",
                "id": request_id,
                "request_sha256": request_digest,
                "ok": True,
                "result": {"success": True, "actor_count": 7},
            }
            (self.responses / f"{request_id}.json").write_bytes(
                _canonical_bytes(_sign(response, self.token.encode("ascii")))
            )
            request_path.unlink(missing_ok=True)

        worker = threading.Thread(target=broker)
        worker.start()
        with patch.dict(os.environ, self.environment, clear=False):
            result = McpStudioUnrealConnection().send_command(
                "exec_python",
                {"code": "print(7)", "mode": "evaluate_statement"},
            )
        worker.join(timeout=3)

        self.assertFalse(worker.is_alive())
        self.assertEqual(result, {"success": True, "actor_count": 7})
        self.assertEqual(observed["method"], "exec_python")
        self.assertEqual(
            observed["params"],
            {"code": "print(7)", "mode": "evaluate_statement"},
        )
        self.assertEqual(list(self.requests.iterdir()), [])
        self.assertEqual(list(self.responses.iterdir()), [])

    def test_non_spatial_command_is_rejected_without_publishing_request(self) -> None:
        with patch.dict(os.environ, self.environment, clear=False):
            result = McpStudioUnrealConnection().send_command("delete_asset", {})

        self.assertEqual(result["status"], "error")
        self.assertIn("allowlist", result["error"])
        self.assertEqual(list(self.requests.iterdir()), [])

    def test_capture_policy_allows_only_configured_evidence_targets(self) -> None:
        policy = CapturePolicy(
            (
                {
                    "location": [1.0, 2.0, 3.0],
                    "distance": 0.0,
                    "orientation": [4.0, 5.0, 6.0],
                },
            ),
            frozenset({os.path.normcase(os.path.realpath(self.capture_path))}),
            (1600, 900),
        )

        self.assertTrue(
            policy.allows_focus(
                {
                    "location": [1.0, 2.0, 3.0],
                    "distance": 0.0,
                    "orientation": [4.0, 5.0, 6.0],
                }
            )
        )
        self.assertTrue(
            policy.allows_screenshot(
                {
                    "filepath": str(self.capture_path),
                    "show_ui": False,
                    "resolution": [1600, 900],
                }
            )
        )
        self.assertFalse(
            policy.allows_screenshot(
                {
                    "filepath": str(self.root / "not-allowed.png"),
                    "show_ui": False,
                    "resolution": [1600, 900],
                }
            )
        )

    def test_static_mesh_section_request_is_typed_and_bounded(self) -> None:
        observed: dict[str, object] = {}

        def broker() -> None:
            deadline = time.monotonic() + 1.5
            request_path = None
            while time.monotonic() < deadline:
                candidates = list(self.requests.glob("*.json"))
                if candidates:
                    request_path = candidates[0]
                    break
                time.sleep(0.01)
            self.assertIsNotNone(request_path)
            envelope = json.loads(request_path.read_text(encoding="utf-8"))
            request_id = request_path.stem
            request, request_digest = _verify(
                envelope, self.token.encode("ascii"), request_id
            )
            observed.update(request)
            response = {
                "schema": "unreal-spatial-bridge-spool/v1",
                "id": request_id,
                "request_sha256": request_digest,
                "ok": True,
                "result": {"status": "success", "result": {"success": True}},
            }
            (self.responses / f"{request_id}.json").write_bytes(
                _canonical_bytes(_sign(response, self.token.encode("ascii")))
            )
            request_path.unlink(missing_ok=True)

        worker = threading.Thread(target=broker)
        worker.start()
        params = {
            "asset_path": "/Game/LevelPrototyping/KotorModels/m13aa_05a",
            "lod_index": 0,
            "max_sections": 64,
        }
        with patch.dict(os.environ, self.environment, clear=False):
            result = McpStudioUnrealConnection().send_command(
                "inspect_static_mesh_sections", params
            )
        worker.join(timeout=3)

        self.assertFalse(worker.is_alive())
        self.assertEqual(result["status"], "success")
        self.assertEqual(observed["method"], "inspect_static_mesh_sections")
        self.assertEqual(observed["params"], params)

    def test_static_mesh_section_request_rejects_invalid_bounds(self) -> None:
        invalid_params = (
            {
                "asset_path": "C:/outside.uasset",
                "lod_index": 0,
                "max_sections": 64,
            },
            {
                "asset_path": "/Game/Mesh",
                "lod_index": 8,
                "max_sections": 64,
            },
            {
                "asset_path": "/Game/Mesh",
                "lod_index": 0,
                "max_sections": 129,
            },
        )
        with patch.dict(os.environ, self.environment, clear=False):
            for params in invalid_params:
                with self.subTest(params=params):
                    result = McpStudioUnrealConnection().send_command(
                        "inspect_static_mesh_sections", params
                    )
                    self.assertEqual(result["status"], "error")
                    self.assertIn("invalid", result["error"].lower())
        self.assertEqual(list(self.requests.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
