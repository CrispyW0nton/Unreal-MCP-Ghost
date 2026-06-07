"""Static checks for Workstream C.11 MCP Chat onboarding."""

from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
EDITOR_MODULE = REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor"
PANEL_CPP = EDITOR_MODULE / "Private" / "MCPChatPanel.cpp"
PANEL_H = EDITOR_MODULE / "Public" / "MCPChatPanel.h"
CHANGELOG = REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md"


class OnboardingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cpp = PANEL_CPP.read_text(encoding="utf-8")
        cls.header = PANEL_H.read_text(encoding="utf-8")
        cls.changelog = CHANGELOG.read_text(encoding="utf-8")

    def test_onboarding_surface_is_declared(self) -> None:
        for symbol in (
            "struct FSamplePromptItem",
            "HandleOnboardingNextClicked",
            "HandleOnboardingDismissClicked",
            "HandleToggleSamplePromptsClicked",
            "HandleSamplePromptClicked",
            "BuildOnboardingOverlay",
            "BuildSamplePrompts",
            "GetSamplePromptItems",
            "GetOnboardingVisibility",
            "GetSamplePromptsVisibility",
            "GetOnboardingStepText",
            "GetOnboardingStepTitle",
            "GetOnboardingNextText",
            "GetSamplePromptsToggleText",
            "bOnboardingVisible",
            "bOnboardingCompleted",
            "bSamplePromptsVisible",
            "OnboardingStepIndex",
        ):
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, self.header)

    def test_first_launch_tour_is_config_backed(self) -> None:
        for token in (
            "OnboardingCompleted",
            "bOnboardingVisible = !bOnboardingCompleted",
            "GConfig->GetBool(ChatPanelConfigSection, TEXT(\"OnboardingCompleted\")",
            "GConfig->SetBool(ChatPanelConfigSection, TEXT(\"OnboardingCompleted\")",
            "HandleOnboardingDismissClicked",
            "HandleOnboardingNextClicked",
            "MCP Chat Tour {0}/4",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp)

    def test_four_tour_steps_are_present(self) -> None:
        for step in (
            "Connect server",
            "Ask a question",
            "Drag an asset",
            "Run a workflow",
        ):
            with self.subTest(step=step):
                self.assertIn(step, self.cpp)
        self.assertIn("OnboardingStepIndex < 3", self.cpp)
        self.assertIn("OnboardingStepIndex >= 3", self.cpp)

    def test_sample_prompts_button_and_six_demos(self) -> None:
        self.assertIn("Sample Prompts", self.cpp)
        self.assertIn("BuildSamplePrompts()", self.cpp)
        self.assertIn("HandleToggleSamplePromptsClicked", self.cpp)
        self.assertIn("HandleSamplePromptClicked(FSamplePromptItem Item)", self.cpp)
        for label in (
            "Health System",
            "Build Slime Enemy",
            "Dungeon Starter",
            "HUD Health Bar",
            "Repair Blueprint",
            "Asset Import Pass",
        ):
            with self.subTest(label=label):
                self.assertIn(label, self.cpp)

    def test_sample_prompts_insert_real_tool_chain_requests(self) -> None:
        for phrase in (
            "health_system skill",
            "Behavior Tree tools",
            "editor placement tools",
            "UMG HUD",
            "repair_broken_blueprint skill",
            "material tools",
            "InsertComposerText(Item.Prompt)",
            "RecordTelemetryEvent(TEXT(\"sample_prompt_inserted\"))",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.cpp)

    def test_changelog_records_c11(self) -> None:
        self.assertIn("### C.11 - Onboarding", self.changelog)
        self.assertIn("first-launch", self.changelog)
        self.assertIn("Sample Prompts", self.changelog)


if __name__ == "__main__":
    unittest.main()
