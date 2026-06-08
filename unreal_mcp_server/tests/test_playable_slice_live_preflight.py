"""Coverage for the no-spend playable-slice live preflight."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT = REPO_ROOT / "scripts" / "playable_slice_live_preflight.py"
CHANGELOG = REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md"
PLAYABLE_KB = REPO_ROOT / "knowledge_base" / "32_AGENT_PLAYABLE_SLICE_RECIPE.md"


def _load_preflight_module():
    spec = importlib.util.spec_from_file_location("playable_slice_live_preflight", PREFLIGHT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class PlayableSliceLivePreflightTest(unittest.TestCase):
    def test_preflight_script_reports_schema_without_spend(self) -> None:
        result = subprocess.run(
            [sys.executable, str(PREFLIGHT), "--bridge-timeout-s", "0.01"],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema"], "unreal_mcp_playable_slice_live_preflight.v1")
        self.assertFalse(payload["network_required"])
        self.assertFalse(payload["spend_required"])
        for gate_id in ("tripo_api_key", "credit_budget", "unreal_build_tooling", "packaged_plugin", "unreal_bridge"):
            with self.subTest(gate_id=gate_id):
                self.assertIn(gate_id, {gate["id"] for gate in payload["gates"]})

    def test_preflight_ready_when_all_gates_are_satisfied(self) -> None:
        module = _load_preflight_module()
        with tempfile.TemporaryDirectory() as repo_tmp, tempfile.TemporaryDirectory() as package_tmp:
            repo = Path(repo_tmp)
            (repo / "scripts").mkdir()
            (repo / "scripts" / "build_unreal_plugin.ps1").write_text("# build wrapper", encoding="utf-8")
            (repo / "unreal_plugin").mkdir()
            (repo / "unreal_plugin" / "UnrealMCP.uplugin").write_text("{}", encoding="utf-8")
            chat_dir = repo / "Saved" / "MCPChat"
            chat_dir.mkdir(parents=True)
            (chat_dir / "secrets.json").write_text(json.dumps({"TRIPO_API_KEY": "tsk_test_secret_123456"}), encoding="utf-8")
            (chat_dir / "generative_settings.json").write_text(json.dumps({
                "session_credit_budget": 500,
                "credit_usage_by_session": {"playable-slice": 20},
                "output_folder": "/Game/Generated",
            }), encoding="utf-8")
            package = Path(package_tmp) / "UnrealMCPBuild_test"
            (package / "Binaries" / "Win64").mkdir(parents=True)
            (package / "UnrealMCP.uplugin").write_text("{}", encoding="utf-8")

            args = SimpleNamespace(
                repo_root=str(repo),
                engine_root="",
                package_root=str(package_tmp),
                bridge_host="127.0.0.1",
                bridge_port=55557,
                bridge_timeout_s=0.01,
                session_name="playable-slice",
                estimated_credits=120,
            )
            with patch.object(module, "find_runuat", return_value="C:\\UE\\RunUAT.bat"), patch.object(module, "check_bridge", return_value={"reachable": True, "host": "127.0.0.1", "port": 55557}):
                payload = module.build_preflight(args)

        self.assertTrue(payload["ready_for_live_spend"])
        self.assertEqual(payload["api_key"]["source"], str(chat_dir / "secrets.json"))
        self.assertEqual(payload["settings"]["session_credits_remaining"], 480)
        self.assertTrue(all(gate["status"] == "ready" for gate in payload["gates"]))

    def test_docs_record_preflight_contract(self) -> None:
        script_text = PREFLIGHT.read_text(encoding="utf-8")
        changelog = CHANGELOG.read_text(encoding="utf-8")
        kb = PLAYABLE_KB.read_text(encoding="utf-8")
        for token in (
            "ready_for_live_spend",
            "tripo_api_key",
            "credit_budget",
            "packaged_plugin",
            "unreal_bridge",
        ):
            with self.subTest(token=token):
                self.assertIn(token, script_text)
        self.assertIn("playable_slice_live_preflight.py", changelog)
        self.assertIn("Live Preflight", kb)


if __name__ == "__main__":
    unittest.main()
