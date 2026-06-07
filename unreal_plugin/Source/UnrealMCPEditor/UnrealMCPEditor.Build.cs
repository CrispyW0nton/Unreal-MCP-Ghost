// Copyright 2024 CrispyW0nton. All Rights Reserved.

using UnrealBuildTool;

public class UnrealMCPEditor : ModuleRules
{
    public UnrealMCPEditor(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;
        IWYUSupport = IWYUSupport.Full;

        PublicDependencyModuleNames.AddRange(
            new string[]
            {
                "Core",
                "CoreUObject",
                "Engine",
                "Slate",
                "SlateCore"
            }
        );

        PrivateDependencyModuleNames.AddRange(
            new string[]
            {
                "EditorStyle",
                "UnrealEd",
                "AssetTools",
                "ContentBrowser",
                "ToolMenus",
                "WebBrowser",
                "HTTP",
                "Json",
                "JsonUtilities"
            }
        );
    }
}
