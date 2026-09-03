from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from source_inventory import SOURCE_INVENTORY_SCHEMA, build_source_inventory


class SourceInventoryTests(unittest.TestCase):
    def _plugin(self, directory: str) -> Path:
        root = Path(directory) / "UnrealMCP"
        (root / "Source" / "UnrealMCP").mkdir(parents=True)
        (root / "UnrealMCP.uplugin").write_text('{"FileVersion":3}\n', encoding="utf-8")
        (root / "Source" / "UnrealMCP" / "Module.cpp").write_text(
            "int unreal_mcp_test = 1;\n", encoding="utf-8"
        )
        return root

    def test_inventory_is_deterministic_and_root_independent(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_inventory = build_source_inventory(self._plugin(first))
            second_inventory = build_source_inventory(self._plugin(second))

        self.assertEqual(first_inventory["schema"], SOURCE_INVENTORY_SCHEMA)
        self.assertEqual(first_inventory["inventory_sha256"], second_inventory["inventory_sha256"])
        self.assertEqual(first_inventory["files"], second_inventory["files"])
        self.assertNotEqual(first_inventory["plugin_root"], second_inventory["plugin_root"])

    def test_source_or_descriptor_change_changes_inventory_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._plugin(directory)
            baseline = build_source_inventory(root)["inventory_sha256"]
            source = root / "Source" / "UnrealMCP" / "Module.cpp"
            source.write_text("int unreal_mcp_test = 2;\n", encoding="utf-8")
            changed_source = build_source_inventory(root)["inventory_sha256"]
            source.write_text("int unreal_mcp_test = 1;\n", encoding="utf-8")
            (root / "UnrealMCP.uplugin").write_text(
                '{"FileVersion":3,"Version":2}\n', encoding="utf-8"
            )
            changed_descriptor = build_source_inventory(root)["inventory_sha256"]

        self.assertNotEqual(baseline, changed_source)
        self.assertNotEqual(baseline, changed_descriptor)

    def test_generated_build_products_are_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._plugin(directory)
            baseline = build_source_inventory(root)
            (root / "Binaries" / "Win64").mkdir(parents=True)
            (root / "Binaries" / "Win64" / "UnrealEditor-UnrealMCP.dll").write_bytes(b"generated")
            (root / "Intermediate").mkdir()
            (root / "Intermediate" / "generated.obj").write_bytes(b"generated")
            after = build_source_inventory(root)

        self.assertEqual(baseline["inventory_sha256"], after["inventory_sha256"])
        self.assertEqual(baseline["files"], after["files"])


if __name__ == "__main__":
    unittest.main()
