"""Static checks for Workstream C.5 asset drag-and-drop references."""

from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
EDITOR_MODULE = REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor"
PANEL_CPP = EDITOR_MODULE / "Private" / "MCPChatPanel.cpp"
PANEL_H = EDITOR_MODULE / "Public" / "MCPChatPanel.h"


class AssetDragDropTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cpp = PANEL_CPP.read_text(encoding="utf-8")
        cls.header = PANEL_H.read_text(encoding="utf-8")

    def test_composer_accepts_required_drop_sources(self) -> None:
        self.assertIn("virtual FReply OnDragOver", self.header)
        self.assertIn("virtual FReply OnDrop", self.header)
        self.assertIn("BuildDropReference", self.header)
        for operation_type in ("FAssetDragDropOp", "FActorDragDropOp", "FExternalDragOperation"):
            with self.subTest(operation_type=operation_type):
                self.assertIn(f"Operation->IsOfType<{operation_type}>()", self.cpp)

    def test_drop_handler_inserts_only_resolved_references(self) -> None:
        self.assertIn("const FString DropReference = BuildDropReference(Operation)", self.cpp)
        self.assertIn("DropReference.IsEmpty()", self.cpp)
        self.assertIn("Unsupported drop", self.cpp)
        self.assertIn("InsertComposerText(DropReference)", self.cpp)
        self.assertIn("Inserted dropped reference:", self.cpp)

    def test_content_browser_assets_become_asset_references(self) -> None:
        self.assertIn("AssetDragDropOp->HasAssets()", self.cpp)
        self.assertIn("for (const FAssetData& AssetData : AssetDragDropOp->GetAssets())", self.cpp)
        self.assertIn("@asset:%s", self.cpp)
        self.assertIn("AssetData.PackageName.ToString()", self.cpp)
        self.assertIn("AssetDragDropOp->HasAssetPaths()", self.cpp)
        self.assertIn("for (const FString& AssetPath : AssetDragDropOp->GetAssetPaths())", self.cpp)

    def test_outliner_actors_become_actor_references(self) -> None:
        self.assertIn("ActorDragDropOp->Actors", self.cpp)
        self.assertIn("for (const TWeakObjectPtr<AActor>& ActorPtr : ActorDragDropOp->Actors)", self.cpp)
        self.assertIn("@actor:%s", self.cpp)
        self.assertIn("ActorPtr->GetName()", self.cpp)

    def test_os_files_become_normalized_file_references(self) -> None:
        self.assertIn("#include \"Misc/Paths.h\"", self.cpp)
        self.assertIn("ExternalDragDropOp->HasFiles()", self.cpp)
        self.assertIn("for (const FString& FilePath : ExternalDragDropOp->GetFiles())", self.cpp)
        self.assertIn("FPaths::ConvertRelativePathToFull(FilePath)", self.cpp)
        self.assertIn("FPaths::MakeStandardFilename(NormalizedFilePath)", self.cpp)
        self.assertIn("@file:%s", self.cpp)

    def test_multi_item_drops_insert_one_reference_per_line(self) -> None:
        self.assertIn("TArray<FString> References", self.cpp)
        self.assertIn("References.Add", self.cpp)
        self.assertIn("FString::Join(References, LINE_TERMINATOR)", self.cpp)


if __name__ == "__main__":
    unittest.main()
