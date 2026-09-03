from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from pathlib import Path

from bridge_auth import (
    BridgeAuthenticationError,
    load_bridge_authentication,
)


class BridgeAuthenticationTests(unittest.TestCase):
    def test_private_token_file_adds_auth_to_command_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            token_file = Path(directory) / "bridge.token"
            token_file.write_text("ab" * 32, encoding="ascii")
            authentication = load_bridge_authentication({
                "UNREAL_MCP_REQUIRE_AUTH": "1",
                "UNREAL_MCP_PRIVATE_TOKEN_FILE": str(token_file.resolve()),
            })

        self.assertTrue(authentication.required)
        self.assertTrue(authentication.enabled)
        self.assertEqual(authentication.source, "private-token-file")
        self.assertEqual(authentication.command_payload("ping", {})["auth"], "ab" * 32)

    def test_required_auth_fails_closed_without_token(self) -> None:
        with self.assertRaisesRegex(BridgeAuthenticationError, "required"):
            load_bridge_authentication({"UNREAL_MCP_REQUIRE_AUTH": "true"})

    def test_invalid_token_and_multiple_sources_fail_closed(self) -> None:
        with self.assertRaises(BridgeAuthenticationError):
            load_bridge_authentication({"UNREAL_MCP_BRIDGE_TOKEN": "short"})
        with tempfile.TemporaryDirectory() as directory:
            token_file = Path(directory) / "bridge.token"
            token_file.write_text("ab" * 32, encoding="ascii")
            with self.assertRaisesRegex(BridgeAuthenticationError, "one UnrealMCP token source"):
                load_bridge_authentication({
                    "UNREAL_MCP_PRIVATE_TOKEN_FILE": str(token_file.resolve()),
                    "UNREAL_MCP_BRIDGE_TOKEN": "cd" * 32,
                })

    def test_legacy_mode_is_explicit_and_omits_auth_field(self) -> None:
        authentication = load_bridge_authentication({})
        self.assertFalse(authentication.required)
        self.assertFalse(authentication.enabled)
        self.assertNotIn("auth", authentication.command_payload("ping", {}))

    def test_direct_token_is_trimmed_and_normalized(self) -> None:
        authentication = load_bridge_authentication({
            "UNREAL_MCP_BRIDGE_TOKEN": f"  {'AB' * 32}  ",
        })

        self.assertEqual(authentication.command_payload("ping", {})["auth"], "ab" * 32)

    def test_standalone_bridge_clients_apply_authentication(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        for relative_path in (
            "scripts/bridge_ping.py",
            "unreal_mcp_server/ue5cli.py",
            "unreal_mcp_server/proxy.py",
        ):
            with self.subTest(path=relative_path):
                text = (repo_root / relative_path).read_text(encoding="utf-8")
                self.assertIn("load_bridge_authentication", text)
                self.assertIn("command_payload", text)

    def test_native_bridge_normalizes_direct_tokens(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        bridge_source = (
            repo_root / "unreal_plugin/Source/UnrealMCP/Private/UnrealMCPBridge.cpp"
        ).read_text(encoding="utf-8")

        self.assertIn("DirectToken = DirectToken.TrimStartAndEnd().ToLower();", bridge_source)


if __name__ == "__main__":
    unittest.main()
