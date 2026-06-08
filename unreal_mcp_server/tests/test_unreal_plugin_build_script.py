"""Static checks for the Unreal plugin BuildPlugin wrapper."""

from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_unreal_plugin.ps1"
CHANGELOG = REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md"


class UnrealPluginBuildScriptTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script = BUILD_SCRIPT.read_text(encoding="utf-8")
        cls.changelog = CHANGELOG.read_text(encoding="utf-8")

    def test_build_script_discovers_runuat_and_packages_plugin(self) -> None:
        for token in (
            "RunUAT.bat",
            "BuildPlugin",
            "unreal_plugin\\UnrealMCP.uplugin",
            "C:\\uebuild\\UnrealMCPBuild_",
            "-TargetPlatforms",
            "-Rocket",
            "PackageDir already exists",
            "BUILD_PACKAGE=",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.script)

    def test_build_script_has_explicit_engine_override(self) -> None:
        for token in (
            "[string]$EngineRoot",
            "Resolve-RunUat",
            "C:\\Program Files\\Epic Games\\UE_5.6",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.script)

    def test_changelog_records_build_wrapper(self) -> None:
        self.assertIn("BuildPlugin", self.changelog)
        self.assertIn("scripts/build_unreal_plugin.ps1", self.changelog)


if __name__ == "__main__":
    unittest.main()
