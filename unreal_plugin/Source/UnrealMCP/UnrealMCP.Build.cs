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

                // Python scripting — required for exec_python command
                // Provides IPythonScriptPlugin, FPythonCommandEx, EPythonCommandExecutionMode, etc.
                // The user must have the "Python Editor Script Plugin" enabled in UE5.
                "PythonScriptPlugin",

                // All of FStructureEditorUtils, FEnumEditorUtils, UEdGraphNode_Comment,
                // UDataTableFactory, and UAnimationStateMachineSchema are provided by
                // UnrealEd and AnimGraph which are already listed above.
                // "StructureEditor" — does not exist as a standalone module in UE 5.6
                // "DataTableEditor" — UDataTableFactory is in UnrealEd, not DataTableEditor
                // "GraphEditor"     — does not exist as a standalone module in UE 5.6
            }
        );

        // ── Editor-only dependencies ──────────────────────────────────────────
        if (Target.bBuildEditor)
        {
            // VariantManager is an optional plugin — only add if it is installed.
            // Standard UE5 installs from the Epic Launcher do NOT include it.
            // If you see a "Module VariantManager could not be found" error,
            // these two lines are already commented out for you.
            // "VariantManager",
            // "VariantManagerContent",
        }

        DynamicallyLoadedModuleNames.AddRange(
            new string[] { }
        );
    }
}
