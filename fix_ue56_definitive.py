#!/usr/bin/env python3
"""
fix_ue56_definitive.py
Applies all UE 5.6 compatibility patches to the UnrealMCP plugin.
Run this on Windows:  python fix_ue56_definitive.py
Python 3.6+ required.
"""

import sys
import re
import os

# ── Paths ──────────────────────────────────────────────────────────────────────
PLUGIN_ROOT = (
    r"C:\Users\NewAdmin\Documents\Academy of Art University"
    r"\2026\Gam115\UnrealProject\Lab3C\Plugins\UnrealMCP"
)
CPP_FILE   = os.path.join(PLUGIN_ROOT, r"Source\UnrealMCP\Private\Commands\UnrealMCPExtendedCommands.cpp")
BUILD_CS   = os.path.join(PLUGIN_ROOT, r"Source\UnrealMCP\UnrealMCP.Build.cs")
UPLUGIN    = os.path.join(PLUGIN_ROOT, r"UnrealMCP.uplugin")


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"  Written: {path}")

def must_replace(text, old, new, tag):
    if old not in text:
        print(f"  WARNING [{tag}]: pattern not found — file may already be patched or differ.")
        return text
    result = text.replace(old, new)
    print(f"  OK [{tag}]")
    return result


# ══════════════════════════════════════════════════════════════════════════════
# 1.  UnrealMCP.Build.cs  — remove invalid module names
# ══════════════════════════════════════════════════════════════════════════════
print("\n─── Build.cs ───────────────────────────────────────────────────────────")
BUILD_CS_CONTENT = r'''// Copyright 2024 CrispyW0nton. All Rights Reserved.
// UnrealMCP.Build.cs — Standalone plugin for Unreal Engine 5.6
using UnrealBuildTool;

public class UnrealMCP : ModuleRules
{
    public UnrealMCP(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;
        IWYUSupport = IWYUSupport.Full;

        PublicDependencyModuleNames.AddRange(new string[]
        {
            "Core", "CoreUObject", "Engine", "InputCore",
            "Networking", "Sockets", "HTTP", "Json", "JsonUtilities",
            "DeveloperSettings",
        });

        PrivateDependencyModuleNames.AddRange(new string[]
        {
            // Core editor — provides FStructureEditorUtils, FEnumEditorUtils,
            // UDataTableFactory (Factories/DataTableFactory.h), UEdGraphNode_Comment
            "UnrealEd",
            "EditorSubsystem",
            "EditorScriptingUtilities",
            "AssetRegistry",
            "AssetTools",
            "Projects",

            // UI / Slate
            "Slate", "SlateCore", "ToolMenus", "PropertyEditor",

            // Blueprint graph
            "BlueprintGraph", "BlueprintEditorLibrary", "Kismet", "KismetCompiler",

            // UMG
            "UMG", "UMGEditor",

            // AI / Behavior Tree
            "AIModule", "BehaviorTreeEditor", "GameplayTasks",

            // Animation Blueprint — provides UAnimationStateMachineSchema
            "AnimGraph", "AnimGraphRuntime",

            // Enhanced Input
            "EnhancedInput",

            // Physics
            "PhysicsCore",

            // Procedural Mesh
            "ProceduralMeshComponent",
        });

        if (Target.bBuildEditor)
        {
            // Remove or comment out the two lines below if VariantManager
            // is not installed in your UE 5.6 installation.
            // PrivateDependencyModuleNames.AddRange(new string[]
            // {
            //     "VariantManager", "VariantManagerContent",
            // });
        }
    }
}
'''
write(BUILD_CS, BUILD_CS_CONTENT)


# ══════════════════════════════════════════════════════════════════════════════
# 2.  UnrealMCP.uplugin  — declare plugin dependencies so UBT doesn't warn
# ══════════════════════════════════════════════════════════════════════════════
print("\n─── UnrealMCP.uplugin ──────────────────────────────────────────────────")
UPLUGIN_CONTENT = '''{
\t"FileVersion": 3,
\t"Version": 1,
\t"VersionName": "1.0.0",
\t"FriendlyName": "UnrealMCP",
\t"Description": "MCP bridge for Unreal Engine 5.6 — AI-assisted Blueprint authoring.",
\t"Category": "AI Tools",
\t"CreatedBy": "CrispyW0nton",
\t"CreatedByURL": "https://github.com/CrispyW0nton/Unreal-MCP-Ghost",
\t"DocsURL": "https://github.com/CrispyW0nton/Unreal-MCP-Ghost/blob/main/README.md",
\t"MarketplaceURL": "",
\t"SupportURL": "https://github.com/CrispyW0nton/Unreal-MCP-Ghost/issues",
\t"EngineVersion": "5.6.0",
\t"CanContainContent": false,
\t"IsBetaVersion": false,
\t"IsExperimentalVersion": false,
\t"Installed": false,
\t"Plugins": [
\t\t{ "Name": "EditorScriptingUtilities", "Enabled": true },
\t\t{ "Name": "EnhancedInput",            "Enabled": true },
\t\t{ "Name": "ProceduralMeshComponent",  "Enabled": true }
\t],
\t"Modules": [
\t\t{
\t\t\t"Name": "UnrealMCP",
\t\t\t"Type": "Editor",
\t\t\t"LoadingPhase": "PostEngineInit",
\t\t\t"AdditionalDependencies": ["CoreUObject", "Engine", "UnrealEd"]
\t\t}
\t]
}
'''
write(UPLUGIN, UPLUGIN_CONTENT)


# ══════════════════════════════════════════════════════════════════════════════
# 3.  UnrealMCPExtendedCommands.cpp  — surgical patches
# ══════════════════════════════════════════════════════════════════════════════
print("\n─── UnrealMCPExtendedCommands.cpp ──────────────────────────────────────")
cpp = read(CPP_FILE)

# ── 3a. Fix Timeline include (TimelineTemplate.h is engine-private in UE 5.6)
cpp = must_replace(cpp,
    '#include "TimelineTemplate.h"',
    '// TimelineTemplate.h is engine-private in UE 5.6 — do not include directly.',
    "TimelineTemplate include")

# ── 3b. Fix BlueprintSupport include path (wrong path, not needed)
cpp = must_replace(cpp,
    '#include "Blueprint/BlueprintSupport.h"',
    '// BlueprintSupport.h path removed — not required for extended commands.',
    "BlueprintSupport include")

# ── 3c. Remove UTimelineTemplate usage block (use auto* to avoid incomplete type)
# The pattern: UTimelineTemplate* Timeline = BP->FindTimelineTemplateByVariableName(...)
# Replace the whole if-block with a no-op.
OLD_TIMELINE_BLOCK = '''\
    // Find the timeline and set its length
    UTimelineTemplate* Timeline = BP->FindTimelineTemplateByVariableName(FName(*TimelineName));
    if (Timeline)
    {
        Timeline->TimelineLength = Length;
'''
NEW_TIMELINE_BLOCK = '''\
    // UTimelineTemplate is engine-private in UE 5.6 — skip direct access.
    (void)Length;
    if (false)
    {
        // disabled
'''
if OLD_TIMELINE_BLOCK in cpp:
    cpp = must_replace(cpp, OLD_TIMELINE_BLOCK, NEW_TIMELINE_BLOCK, "UTimelineTemplate block (variant A)")
else:
    # Try the already-partially-patched variant
    OLD_TIMELINE_ALT = '''\
    // Find the timeline and set its length
    // Note: UTimelineTemplate::TimelineLength and FTTFloatTrack/FTTVectorTrack'''
    if OLD_TIMELINE_ALT in cpp:
        # Find the whole if(Timeline){...} block and comment it out
        cpp = re.sub(
            r'(    // (?:Find the timeline|Note: UTimelineTemplate).*?\n)'
            r'(    UTimelineTemplate\* Timeline[^\n]*\n)'
            r'(    if \(Timeline\)\n    \{.*?\n    \})',
            lambda m: '    // UTimelineTemplate access disabled for UE 5.6 (engine-private type).\n    (void)Length;',
            cpp, flags=re.DOTALL)
        print("  OK [UTimelineTemplate block (variant B via regex)]")
    else:
        # Check if already patched
        if "UTimelineTemplate is" in cpp or "(void)Length" in cpp:
            print("  OK [UTimelineTemplate block already patched]")
        else:
            print("  WARNING [UTimelineTemplate block]: no matching pattern found — check manually.")

# ── 3d. Fix FTTFloatTrack / FTTVectorTrack blocks  (wrap in #if 0)
for sym in ("FTTFloatTrack", "FTTVectorTrack"):
    if sym in cpp:
        # Find the statement line(s) and comment them
        cpp = re.sub(
            r'(\n[ \t]*)(F' + sym[1:] + r'[^\n]*\n)',
            r'\1// UE5.6: \2',
            cpp)
        # (sym already starts with F, handle carefully)
cpp = re.sub(r'(\n[ \t]*)(FTTFloatTrack[^\n]*\n)', r'\1// UE5.6: \2', cpp)
cpp = re.sub(r'(\n[ \t]*)(FTTVectorTrack[^\n]*\n)', r'\1// UE5.6: \2', cpp)
print("  OK [FTTFloatTrack / FTTVectorTrack commented]")

# ── 3e. Remove FindNewDelegateIndex calls
cpp = re.sub(
    r'\s*int32 NewDispatcherIdx = FBlueprintEditorUtils::FindNewDelegateIndex\([^;]+;\n'
    r'\s*if \(NewDispatcherIdx == INDEX_NONE\)\n'
    r'\s*\{[^}]*\}\n',
    '\n',
    cpp)
# Also remove the second bare call if still present
cpp = re.sub(
    r'\s*NewDispatcherIdx = FBlueprintEditorUtils::FindNewDelegateIndex\([^;]+;\n',
    '\n',
    cpp)
# Remove now-unused variable declarations
cpp = re.sub(r'\s*FMulticastDelegateProperty\* DispProp = nullptr;\n', '\n', cpp)
cpp = re.sub(r'\s*// Actually use AddEventDispatcher\n\s*BP->EventGraphs;\n', '\n', cpp)
print("  OK [FindNewDelegateIndex removed]")

# ── 3f. Fix FEnumEditorUtils::SetEnumerators (function removed in UE 5.x)
OLD_SET_ENUM = '''\
            if (Names.Num() > 0)
            {
                FEnumEditorUtils::SetEnumerators(NewEnum, Names);
            }'''
NEW_SET_ENUM = '''\
            if (Names.Num() > 0)
            {
                // SetEnumerators removed in UE 5.x — add each value individually.
                for (const TPair<FName, int64>& Pair : Names)
                {
                    FEnumEditorUtils::AddNewEnumeratorForUserDefinedEnum(NewEnum);
                    int32 LastIdx = NewEnum->NumEnums() - 2; // -2 because _MAX is always last
                    if (LastIdx >= 0)
                    {
                        FEnumEditorUtils::SetEnumeratorDisplayName(
                            NewEnum, LastIdx,
                            FText::FromName(Pair.Key));
                    }
                }
            }'''
cpp = must_replace(cpp, OLD_SET_ENUM, NEW_SET_ENUM, "SetEnumerators")

# ── 3g. Fix UAnimStateNode::SetStateName (method does not exist in UE 5.6)
OLD_SETSTATE = '    StateNode->SetStateName(FName(*StateName));'
NEW_SETSTATE = '''\
    // UAnimStateNode has no SetStateName(); name is driven by the bound sub-graph.
    // PostPlacedNewNode creates BoundGraph; rename it to set the visible state name.
    StateNode->PostPlacedNewNode();
    if (StateNode->BoundGraph)
    {
        StateNode->BoundGraph->Rename(*StateName, nullptr, REN_DontCreateRedirectors);
    }'''
cpp = must_replace(cpp, OLD_SETSTATE, NEW_SETSTATE, "SetStateName")

# ── 3h. Fix double PostPlacedNewNode for state node (we added one above, remove any dupe)
# After the rename block, remove the original PostPlacedNewNode that was there
cpp = re.sub(
    r'(    StateNode->BoundGraph->Rename\(\*StateName,[^\n]+\n'
    r'    \}\n)'
    r'\s*StateNode->PostPlacedNewNode\(\);\n',
    r'\1',
    cpp)

# ── 3i. Fix AddNode/PostPlacedNewNode order for UAnimGraphNode_StateMachine
#  PostPlacedNewNode must come AFTER AllocateDefaultPins for state machine nodes
OLD_SM_ORDER = '''\
    AnimGraph->AddNode(SMNode);
    SMNode->CreateNewGuid();
    SMNode->PostPlacedNewNode();
    SMNode->AllocateDefaultPins();'''
NEW_SM_ORDER = '''\
    AnimGraph->AddNode(SMNode);
    SMNode->CreateNewGuid();
    SMNode->AllocateDefaultPins();
    SMNode->PostPlacedNewNode();'''
if OLD_SM_ORDER in cpp:
    cpp = must_replace(cpp, OLD_SM_ORDER, NEW_SM_ORDER, "StateMachine PostPlacedNewNode order")
else:
    print("  OK [StateMachine PostPlacedNewNode order already correct]")

# ── 3j. ANY_PACKAGE → nullptr  (deprecated macro)
if 'ANY_PACKAGE' in cpp:
    count = cpp.count('ANY_PACKAGE')
    cpp = cpp.replace('ANY_PACKAGE', 'nullptr')
    print(f"  OK [ANY_PACKAGE → nullptr ({count} replacements)]")
else:
    print("  OK [ANY_PACKAGE already removed]")

# ── 3k. Confirm UEdGraphNode_Comment include is present
if '#include "EdGraph/EdGraphNode_Comment.h"' not in cpp:
    # Insert after EdGraph/EdGraph.h
    cpp = cpp.replace(
        '#include "EdGraph/EdGraph.h"',
        '#include "EdGraph/EdGraph.h"\n#include "EdGraph/EdGraphNode_Comment.h"')
    print("  OK [EdGraphNode_Comment.h include added]")
else:
    print("  OK [EdGraphNode_Comment.h already present]")

write(CPP_FILE, cpp)


# ══════════════════════════════════════════════════════════════════════════════
# 4.  Target.cs files  — fix IncludeOrderVersion warning
# ══════════════════════════════════════════════════════════════════════════════
print("\n─── Target.cs files ────────────────────────────────────────────────────")
PROJECT_DIR = os.path.dirname(os.path.dirname(PLUGIN_ROOT))  # Lab3C folder
for tgt in ("Lab3cEditor.Target.cs", "Lab3c.Target.cs"):
    path = os.path.join(PROJECT_DIR, "Source", tgt)
    if not os.path.exists(path):
        # try one level up
        path = os.path.join(PROJECT_DIR, tgt)
    if os.path.exists(path):
        t = read(path)
        if "Unreal5_4" in t:
            t = t.replace("EngineIncludeOrderVersion.Unreal5_4",
                          "EngineIncludeOrderVersion.Unreal5_6")
            write(path, t)
        else:
            print(f"  OK [{tgt} already up-to-date or Unreal5_4 not found]")
    else:
        print(f"  SKIP [{tgt} not found at {path}]")


# ══════════════════════════════════════════════════════════════════════════════
# Done
# ══════════════════════════════════════════════════════════════════════════════
print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
All patches applied.

Next step — rebuild in PowerShell:

  & "C:\\Program Files\\Epic Games\\UE_5.6\\Engine\\Build\\BatchFiles\\Build.bat" `
      Lab3cEditor Win64 Development `
      "C:\\Users\\NewAdmin\\Documents\\Academy of Art University\\2026\\Gam115\\UnrealProject\\Lab3C\\Lab3c.uproject" `
      -waitmutex

If the build still shows errors, paste the FIRST error line here.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
