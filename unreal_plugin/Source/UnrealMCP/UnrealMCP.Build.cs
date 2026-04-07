// Copyright 2024 CrispyW0nton. All Rights Reserved.
// UnrealMCP.Build.cs — Standalone plugin for Unreal Engine 5.6
// Merges base unreal-mcp dependencies with extended Blueprint Visual Scripting tools.

using UnrealBuildTool;

public class UnrealMCP : ModuleRules
{
    public UnrealMCP(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;
        IWYUSupport = IWYUSupport.Full;

        PublicIncludePaths.AddRange(
            new string[] { }
        );

        PrivateIncludePaths.AddRange(
            new string[] { }
        );

        // ── Public dependencies (available to dependent modules) ─────────────
        PublicDependencyModuleNames.AddRange(
            new string[]
            {
                "Core",
                "CoreUObject",
                "Engine",
                "InputCore",
                "Networking",
                "Sockets",
                "HTTP",
                "Json",
                "JsonUtilities",
                "DeveloperSettings",
            }
        );

        // ── Private dependencies (internal to this plugin) ───────────────────
        PrivateDependencyModuleNames.AddRange(
            new string[]
            {
                // Core editor
                "UnrealEd",
                "EditorSubsystem",
                "EditorScriptingUtilities",
                "AssetRegistry",
                "AssetTools",
                "Projects",

                // UI / Slate
                "Slate",
                "SlateCore",
                "ToolMenus",
                "PropertyEditor",

                // Blueprint graph editing (base)
                "BlueprintGraph",
                "BlueprintEditorLibrary",
                "Kismet",
                "KismetCompiler",

                // UMG / Widget editing (base + extended)
                "UMG",
                "UMGEditor",

                // AI / Behavior Tree (extended — Chapters 9, 10)
                "AIModule",
                "BehaviorTreeEditor",
                "GameplayTasks",

                // Animation Blueprint (extended — Chapter 17)
                "AnimGraph",
                "AnimGraphRuntime",

                // Enhanced Input (extended — Chapter 6, input nodes)
                "EnhancedInput",

                // Physics / Collision (extended — Chapter 14)
                "PhysicsCore",

                // Procedural Mesh (extended — Chapter 19)
                "ProceduralMeshComponent",
            }
        );

        // ── Editor-only dependencies ──────────────────────────────────────────
        if (Target.bBuildEditor)
        {
            PrivateDependencyModuleNames.AddRange(
                new string[]
                {
                    // Variant Manager (extended — Chapter 20)
                    // NOTE: Comment these two lines out if your UE install
                    // does not include the Variant Manager plugin.
                    "VariantManager",
                    "VariantManagerContent",
                }
            );
        }

        DynamicallyLoadedModuleNames.AddRange(
            new string[] { }
        );
    }
}
