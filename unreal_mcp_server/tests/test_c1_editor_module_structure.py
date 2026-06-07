"""Static checks for the Workstream C.1 editor chat module split."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = REPO_ROOT / "unreal_plugin"
EDITOR_MODULE = PLUGIN_ROOT / "Source" / "UnrealMCPEditor"
CORE_MODULE = PLUGIN_ROOT / "Source" / "UnrealMCP"


class EditorModuleStructureTest(unittest.TestCase):
    def test_editor_module_files_and_dependencies_exist(self) -> None:
        build_cs = EDITOR_MODULE / "UnrealMCPEditor.Build.cs"
        module_cpp = EDITOR_MODULE / "Private" / "UnrealMCPEditorModule.cpp"
        panel_cpp = EDITOR_MODULE / "Private" / "MCPChatPanel.cpp"
        panel_h = EDITOR_MODULE / "Public" / "MCPChatPanel.h"

        for path in (build_cs, module_cpp, panel_cpp, panel_h):
            with self.subTest(path=path):
                self.assertTrue(path.exists(), f"missing expected editor module file: {path}")

        build_text = build_cs.read_text(encoding="utf-8")
        for dependency in (
            "Slate",
            "SlateCore",
            "EditorStyle",
            "UnrealEd",
            "AssetTools",
            "ContentBrowser",
            "ToolMenus",
            "WebBrowser",
            "HTTP",
            "Json",
        ):
            with self.subTest(dependency=dependency):
                self.assertIn(f'"{dependency}"', build_text)

    def test_chat_registration_lives_in_editor_module(self) -> None:
        editor_module_text = (EDITOR_MODULE / "Private" / "UnrealMCPEditorModule.cpp").read_text(encoding="utf-8")
        core_module_text = (CORE_MODULE / "Private" / "UnrealMCPModule.cpp").read_text(encoding="utf-8")
        bridge_text = (CORE_MODULE / "Private" / "UnrealMCPBridge.cpp").read_text(encoding="utf-8")

        self.assertIn("RegisterNomadTabSpawner", editor_module_text)
        self.assertIn("UnrealMCPChat", editor_module_text)
        self.assertIn("UToolMenus::RegisterStartupCallback", editor_module_text)
        self.assertIn("SNew(SMCPChatPanel)", editor_module_text)

        forbidden_core_terms = (
            "MCPChatPanel.h",
            "RegisterNomadTabSpawner",
            "UToolMenus",
            "SMCPChatPanel",
        )
        for term in forbidden_core_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, core_module_text)
                self.assertNotIn(term, bridge_text)

    def test_plugin_descriptor_declares_editor_module(self) -> None:
        descriptor = json.loads((PLUGIN_ROOT / "UnrealMCP.uplugin").read_text(encoding="utf-8"))
        modules = {module["Name"]: module for module in descriptor["Modules"]}

        self.assertIn("UnrealMCP", modules)
        self.assertIn("UnrealMCPEditor", modules)
        self.assertEqual(modules["UnrealMCPEditor"]["Type"], "Editor")
        self.assertEqual(modules["UnrealMCPEditor"]["LoadingPhase"], "PostEngineInit")

    def test_chat_panel_removed_from_core_module_source_tree(self) -> None:
        self.assertFalse((CORE_MODULE / "Private" / "MCPChatPanel.cpp").exists())
        self.assertFalse((CORE_MODULE / "Private" / "MCPChatPanel.h").exists())


if __name__ == "__main__":
    unittest.main()
