"""Offline smoke coverage for Workstream D.5 provider abstraction."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVER_ROOT.parent
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))


class TestD5GenerativeProviderAbstraction(unittest.TestCase):
    def test_tripo_provider_satisfies_contract_and_describes_capabilities(self):
        from tools.generative import GenerativeProvider, ProviderRegistry
        from tools.generative.tripo import TRIPO_PROVIDER

        self.assertIsInstance(TRIPO_PROVIDER, GenerativeProvider)
        registry = ProviderRegistry([TRIPO_PROVIDER])
        provider = registry.get("tripo")
        description = provider.describe({
            "api_key_configured": True,
            "api_key_source": "env:TRIPO_API_KEY",
            "default_model_version": "tripo-default",
            "default_texture_quality": "standard",
            "output_folder": "/Game/Generated",
            "session_credit_budget": 500,
        })

        self.assertEqual(description["provider"], "tripo")
        self.assertEqual(description["status"], "configured")
        self.assertIn("text_to_model", description["capabilities"])
        self.assertIn("import_to_project", description["capabilities"])
        self.assertIn(".glb", description["output_policy"]["model_extensions"])
        self.assertIn("D.8 knowledge base", description["next_milestones"])
        self.assertFalse(description["unsupported_capabilities"][0]["supported"])

    def test_tripo_provider_owns_credit_and_output_policy(self):
        from tools.generative.tripo import TRIPO_PROVIDER

        text_payload = {
            "type": "text_to_model",
            "texture": True,
            "pbr": True,
            "texture_quality": "standard",
            "smart_low_poly": True,
        }
        convert_payload = {
            "type": "convert_model",
            "format": "FBX",
            "face_limit": 12000,
        }

        self.assertEqual(TRIPO_PROVIDER.normalize_model_version("tripo-default"), "")
        self.assertGreaterEqual(TRIPO_PROVIDER.estimate_credits("text_to_model", text_payload), 30)
        self.assertEqual(TRIPO_PROVIDER.estimate_credits("convert_model", convert_payload), 10)
        self.assertEqual(TRIPO_PROVIDER.output_suffix("model", "https://signed.example/model"), ".glb")
        primary = TRIPO_PROVIDER.select_primary_model_download([
            {"key": "rendered_image", "path": "C:/Gen/task_rendered_image.png"},
            {"key": "base_model", "path": "C:/Gen/task_base_model.glb"},
        ])
        self.assertEqual(primary["key"], "base_model")

    def test_d5_static_files_and_kb(self):
        generative_text = (SERVER_ROOT / "tools" / "generative_tools.py").read_text(encoding="utf-8")
        contract_text = (SERVER_ROOT / "tools" / "generative" / "__init__.py").read_text(encoding="utf-8")
        tripo_text = (SERVER_ROOT / "tools" / "generative" / "tripo.py").read_text(encoding="utf-8")
        cpp_header = (REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCP" / "Public" / "Generative" / "IGenerativeProvider.h").read_text(encoding="utf-8")
        kb_text = (REPO_ROOT / "knowledge_base" / "31_GENERATIVE_CONTENT_PIPELINE.md").read_text(encoding="utf-8")
        changelog_text = (REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md").read_text(encoding="utf-8")

        self.assertIn("ProviderRegistry", generative_text)
        self.assertIn("class GenerativeProvider", contract_text)
        self.assertIn("class TripoProvider", tripo_text)
        self.assertIn("class UNREALMCP_API IGenerativeProvider", cpp_header)
        self.assertIn("Provider Abstraction", kb_text)
        self.assertIn("D.5 - Generative provider abstraction", changelog_text)


if __name__ == "__main__":
    unittest.main()
