from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from client_config import (  # noqa: E402
    CODEX_BEGIN,
    ClientConfigOptions,
    build_server_url,
    write_client_configurations,
)


class TestClientConfigGeneration(unittest.TestCase):
    def test_streamable_http_json_config_merges_existing_servers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base_dir = Path(temp)
            cursor_path = base_dir / ".cursor" / "mcp.json"
            cursor_path.parent.mkdir(parents=True)
            cursor_path.write_text(
                json.dumps({"mcpServers": {"other": {"command": "node"}}}),
                encoding="utf-8",
            )

            result = write_client_configurations(
                ClientConfigOptions(
                    target="cursor",
                    transport="streamable-http",
                    base_dir=base_dir,
                    mcp_host="127.0.0.1",
                    mcp_port=9000,
                )
            )

            self.assertTrue(result["success"])
            written = json.loads(cursor_path.read_text(encoding="utf-8"))
            self.assertEqual(written["mcpServers"]["other"]["command"], "node")
            self.assertEqual(written["mcpServers"]["unreal-mcp"]["url"], "http://127.0.0.1:9000/mcp")

    def test_all_clients_dry_run_uses_epic_style_locations(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base_dir = Path(temp)
            result = write_client_configurations(
                ClientConfigOptions(target="all", transport="streamable-http", base_dir=base_dir, dry_run=True)
            )

            self.assertTrue(result["success"])
            self.assertEqual(result["written_count"], 0)
            paths = {Path(item["path"]).relative_to(base_dir).as_posix() for item in result["results"]}
            self.assertEqual(
                paths,
                {
                    ".mcp.json",
                    ".cursor/mcp.json",
                    ".vscode/mcp.json",
                    ".gemini/settings.json",
                    ".codex/config.toml",
                },
            )
            entries = {item["client"]: item["entry"] for item in result["results"]}
            self.assertEqual(entries["claude_code"]["type"], "http")
            self.assertEqual(entries["vscode"]["type"], "http")
            self.assertEqual(entries["gemini"]["httpUrl"], "http://127.0.0.1:8000/mcp")
            self.assertEqual(entries["codex"]["url"], "http://127.0.0.1:8000/mcp")

    def test_stdio_config_writes_codex_managed_block(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base_dir = Path(temp)
            result = write_client_configurations(
                ClientConfigOptions(
                    target="codex",
                    transport="stdio",
                    base_dir=base_dir,
                    python_command="python",
                    server_script=SERVER_ROOT / "unreal_mcp_server.py",
                    unreal_host="127.0.0.1",
                    unreal_port=55655,
                    tool_search_mode=True,
                )
            )

            self.assertTrue(result["success"])
            content = (base_dir / ".codex" / "config.toml").read_text(encoding="utf-8")
            self.assertIn(CODEX_BEGIN, content)
            self.assertIn("[mcp_servers.unreal-mcp]", content)
            self.assertIn('command = "python"', content)
            self.assertIn('UNREAL_PORT = "55655"', content)
            self.assertIn('UNREAL_MCP_TOOL_SEARCH_MODE = "1"', content)

    def test_codex_managed_block_replaces_only_generated_section(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base_dir = Path(temp)
            codex_path = base_dir / ".codex" / "config.toml"
            codex_path.parent.mkdir(parents=True)
            codex_path.write_text(
                'model = "gpt-5"\n\n'
                '# BEGIN Unreal-MCP-Ghost generated MCP server\n'
                '[mcp_servers.unreal-mcp]\n'
                'url = "http://old.example/mcp"\n'
                '# END Unreal-MCP-Ghost generated MCP server\n\n'
                '[projects.example]\n'
                'trust_level = "trusted"\n',
                encoding="utf-8",
            )

            result = write_client_configurations(
                ClientConfigOptions(
                    target="codex",
                    transport="streamable-http",
                    base_dir=base_dir,
                    mcp_host="localhost",
                    mcp_port=8123,
                )
            )

            self.assertTrue(result["success"])
            content = codex_path.read_text(encoding="utf-8")
            self.assertIn('model = "gpt-5"', content)
            self.assertIn('url = "http://localhost:8123/mcp"', content)
            self.assertNotIn("old.example", content)
            self.assertIn("[projects.example]", content)

    def test_build_server_url_rejects_stdio(self) -> None:
        self.assertEqual(build_server_url("sse", "127.0.0.1", 8000), "http://127.0.0.1:8000/sse")
        with self.assertRaises(ValueError):
            build_server_url("stdio", "127.0.0.1", 8000)  # type: ignore[arg-type]

    def test_server_name_rejects_toml_injection_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base_dir = Path(temp)
            result = write_client_configurations(
                ClientConfigOptions(
                    target="codex",
                    base_dir=base_dir,
                    server_name='safe]\ncommand = "cmd.exe"\n[mcp_servers.injected',
                )
            )

            self.assertFalse(result["success"])
            self.assertIn("server_name", result["error"])
            self.assertFalse((base_dir / ".codex" / "config.toml").exists())


if __name__ == "__main__":
    unittest.main()
