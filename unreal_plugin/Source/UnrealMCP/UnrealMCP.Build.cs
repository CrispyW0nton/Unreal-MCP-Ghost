// Copyright 2024 CrispyW0nton. All Rights Reserved.
// UnrealMCP.Build.cs — UE 5.6 compatible

using UnrealBuildTool;

public class UnrealMCP : ModuleRules
{
    public UnrealMCP(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicIncludePaths.AddRange(
            new string[] {
                // Add public include paths here
            }
        );

        PrivateIncludePaths.AddRange(
            new string[] {
                // Add private include paths here
            }
        );

        // ── Core dependencies (always required) ──────────────────────────────
        PublicDependencyModuleNames.AddRange(
            new string[]
            {
                "Core",
                "CoreUObject",
                "Engine",
                "InputCore",
                "Json",
                "JsonUtilities",
                "Networking",
                "Sockets",
            }
        );

        // ── Editor-only dependencies ──────────────────────────────────────────
        // These are only available when building for the editor (not packaged builds)
        if (Target.bBuildEditor)
        {
            PrivateDependencyModuleNames.AddRange(
                new string[]
                {
                    // Core editor modules
                    "UnrealEd",
                    "EditorFramework",
                    "AssetTools",
                    "AssetRegistry",
                    "ContentBrowser",
                    "LevelEditor",

                    // Blueprint graph editing
                    "BlueprintGraph",
                    "Kismet",
                    "KismetCompiler",
                    "KismetWidgets",
                    "GraphEditor",

                    // AI / Behavior Tree editing
                    "AIModule",
                    "BehaviorTreeEditor",
                    "GameplayTasks",

                    // Animation Blueprint editing
                    "AnimGraph",
                    "AnimGraphRuntime",
                    "Persona",

                    // UMG / Widget editing
                    "UMG",
                    "UMGEditor",
                    "SlateCore",
                    "Slate",

                    // Material editing
                    "MaterialEditor",

                    // Enhanced Input (UE 5.1+, required for input action nodes)
                    "EnhancedInput",

                    // Variant Manager (UE 5.x)
                    "VariantManager",
                    "VariantManagerContent",

                    // Physics / Collision
                    "PhysicsCore",

                    // Procedural / PCG
                    "ProceduralMeshComponent",

                    // Additional editor utilities
                    "EditorSubsystem",
                    "EditorScriptingUtilities",
                    "ToolMenus",

                    // Property editor (for details panel access)
                    "PropertyEditor",
                }
            );
        }

        // ── Definitions ───────────────────────────────────────────────────────
        PublicDefinitions.Add("WITH_UNREALMCP=1");

        // ── Platform settings ─────────────────────────────────────────────────
        // Ensure bUseRTTI is enabled for JSON serialization helpers
        bEnableExceptions = false;
        bUseRTTI = false;
    }
}
