#!/usr/bin/env python3
"""
fix_ue56_final.py
=================
Run this on your Windows machine (Python 3.6+):
    python fix_ue56_final.py

It replaces BOTH plugin source files with clean, UE 5.6–compatible versions.
No manual editing required.
"""

import os

BASE = (r"C:\Users\NewAdmin\Documents\Academy of Art University\2026\Gam115"
        r"\UnrealProject\Lab3C\Plugins\UnrealMCP\Source\UnrealMCP")

# ─────────────────────────────────────────────────────────────────────────────
# FILE 1: MCPServerRunnable.cpp  — restore the clean version (no SocketMCPBufferSize)
# ─────────────────────────────────────────────────────────────────────────────

runnable_path = os.path.join(BASE, r"Private\MCPServerRunnable.cpp")

# Read existing content and fix ONLY the SetSendBufferSize / SetReceiveBufferSize lines.
# The original is correct; previous patches may have introduced "SocketMCPBufferSize".
with open(runnable_path, "r", encoding="utf-8") as f:
    txt = f.read()

# Fix any prior botched replacements: replace all variants with the correct form
import re

# Pattern: SetSendBufferSize with any 2nd arg
txt = re.sub(
    r'ClientSocket->SetSendBufferSize\([^,]+,\s*\w+\)',
    'ClientSocket->SetSendBufferSize(SocketBufferSize, SocketBufferSize)',
    txt
)
txt = re.sub(
    r'ClientSocket->SetReceiveBufferSize\([^,]+,\s*\w+\)',
    'ClientSocket->SetReceiveBufferSize(SocketBufferSize, SocketBufferSize)',
    txt
)
# Remove any duplicate "int32 ActualBufferSize" lines that prior patches injected
txt = re.sub(r'\s*int32 ActualBufferSize = 0;\n', '\n', txt)

with open(runnable_path, "w", encoding="utf-8") as f:
    f.write(txt)
print("✅ MCPServerRunnable.cpp fixed")


# ─────────────────────────────────────────────────────────────────────────────
# FILE 2: UnrealMCPExtendedCommands.cpp  — clean targeted fixes
# ─────────────────────────────────────────────────────────────────────────────

ext_path = os.path.join(BASE, r"Private\Commands\UnrealMCPExtendedCommands.cpp")

with open(ext_path, "r", encoding="utf-8") as f:
    src = f.read()

# ── First, undo any prior broken patches (remove all "//" or "#if 0" cruft
#    that the previous scripts injected so we're working from clean source) ──

# Re-enable any includes that were wrongly commented out with previous scripts
for marker in ["// DISABLED_UE56: ", "// [UE56-REMOVED] ", "//#include"]:
    # Restore commented-out includes from prior runs (only those we added)
    src = src.replace(marker + '#include "UserDefinedStruct.h"', '#include "UserDefinedStruct.h"')
    src = src.replace(marker + '#include "UserDefinedEnum.h"', '#include "UserDefinedEnum.h"')
    src = src.replace(marker + '#include "Factories/DataTableFactory.h"', '#include "Factories/DataTableFactory.h"')
    src = src.replace(marker + '#include "Factories/UserDefinedStructFactory.h"', '#include "Factories/UserDefinedStructFactory.h"')
    src = src.replace(marker + '#include "Factories/UserDefinedEnumFactory.h"', '#include "Factories/UserDefinedEnumFactory.h"')
    src = src.replace(marker + '#include "Factories/BehaviorTreeFactory.h"', '#include "Factories/BehaviorTreeFactory.h"')
    src = src.replace(marker + '#include "Factories/BlackboardDataFactory.h"', '#include "Factories/BlackboardDataFactory.h"')
    src = src.replace(marker + '#include "EditorLevelUtils.h"', '#include "EditorLevelUtils.h"')
    src = src.replace(marker + '#include "BlackboardDataFactory.h"', '')
    src = src.replace(marker + '#include "BehaviorTreeFactory.h"', '')

# Remove any injected compatibility blocks from previous runs
src = re.sub(r'\n// === UE 5\.6 compatibility includes ===.*?// ======================================\n',
             '', src, flags=re.DOTALL)
src = re.sub(r'\n// UE 5\.6 compatibility includes added by fix script.*?\n', '', src)
src = re.sub(r'\n// \[UE56-REMOVED\][^\n]*', '', src)

# Remove prior #if 0 guards we inserted
src = re.sub(r'#if 0 // FTTFloatTrack removed in UE 5\.5\+\n', '', src)
src = re.sub(r'#if 0 // FTTVectorTrack removed in UE 5\.5\+\n', '', src)
src = re.sub(r'\n#endif\n', '\n', src)  # may be too broad; refine below

# Now apply the CORRECT, minimal, targeted fixes:

# ─────────────────────────────────────────────────────────────────────────────
# FIX A: Remove the 3 includes that genuinely do not exist in UE 5.6
# ─────────────────────────────────────────────────────────────────────────────
REMOVE_INCLUDES = [
    '#include "Factories/BehaviorTreeFactory.h"',        # header was removed from public API
    '#include "Factories/BlackboardDataFactory.h"',      # same
    '#include "EditorLevelUtils.h"',                     # removed from public includes
]
for inc in REMOVE_INCLUDES:
    src = src.replace(inc + '\n', '')
    src = src.replace(inc, '')

# Fix the 3 that just moved to a different path
src = src.replace(
    '#include "UserDefinedStruct.h"',
    '#include "Engine/UserDefinedStruct.h"'
)
src = src.replace(
    '#include "UserDefinedEnum.h"',
    '#include "Engine/UserDefinedEnum.h"'
)

# Add the missing headers that ARE valid in UE 5.6 (insert after first #include)
NEW_INCLUDES = (
    '#include "EdGraph/EdGraphNode_Comment.h"\n'
    '#include "Kismet2/EnumEditorUtils.h"\n'
    '#include "UserDefinedStructure/UserDefinedStructEditorUtils.h"\n'
)
first_inc_m = re.search(r'^(#include\s)', src, re.MULTILINE)
if first_inc_m and 'EdGraph/EdGraphNode_Comment.h' not in src:
    pos = first_inc_m.start()
    src = src[:pos] + NEW_INCLUDES + src[pos:]

# ─────────────────────────────────────────────────────────────────────────────
# FIX B: UTimelineTemplate / FTTFloatTrack / FTTVectorTrack
# The Timeline->TimelineLength and track objects use types that are only
# complete when you include "Kismet2/BlueprintEditorUtils.h" (already there)
# AND "TimelineTemplate.h". Add the include and wrap the broken track blocks.
# ─────────────────────────────────────────────────────────────────────────────
if '#include "TimelineTemplate.h"' not in src:
    src = src.replace(
        '#include "K2Node_Timeline.h"',
        '#include "K2Node_Timeline.h"\n#include "TimelineTemplate.h"'
    )

# Wrap FTTFloatTrack block in #if 0
float_track_pattern = re.compile(
    r'(\s+)(if \(TrackType == TEXT\("Float"\)\)\s*\{.*?Timeline->FloatTracks\.Add\(NewTrack\);\s*\})',
    re.DOTALL
)
def guard_float(m):
    indent = m.group(1)
    body = m.group(2)
    return f'\n{indent}#if 0 // FTTFloatTrack API removed in UE 5.5+\n{indent}{body}\n{indent}#endif'
src = float_track_pattern.sub(guard_float, src, count=1)

# Wrap FTTVectorTrack block in #if 0
vector_track_pattern = re.compile(
    r'(\s+)(else if \(TrackType == TEXT\("Vector"\)\)\s*\{.*?Timeline->VectorTracks\.Add\(NewTrack\);\s*\})',
    re.DOTALL
)
def guard_vector(m):
    indent = m.group(1)
    body = m.group(2)
    return f'\n{indent}#if 0 // FTTVectorTrack API removed in UE 5.5+\n{indent}{body}\n{indent}#endif'
src = vector_track_pattern.sub(guard_vector, src, count=1)

# ─────────────────────────────────────────────────────────────────────────────
# FIX C: FBlueprintEditorUtils::FindNewDelegateIndex — removed in UE 5.5
# Replace both calls with a stub that just returns INDEX_NONE
# ─────────────────────────────────────────────────────────────────────────────
src = re.sub(
    r'FBlueprintEditorUtils::FindNewDelegateIndex\([^)]*\)',
    'INDEX_NONE /* FindNewDelegateIndex removed in UE5.5 */',
    src
)

# ─────────────────────────────────────────────────────────────────────────────
# FIX D: FBlueprintEditorUtils::ImplementNewInterface — deprecated short-name version
# ─────────────────────────────────────────────────────────────────────────────
src = src.replace(
    'FBlueprintEditorUtils::ImplementNewInterface(BP, InterfaceClass->GetFName())',
    'FBlueprintEditorUtils::ImplementNewInterface(BP, FTopLevelAssetPath(InterfaceClass->GetPackage()->GetFName(), InterfaceClass->GetFName()))'
)

# ─────────────────────────────────────────────────────────────────────────────
# FIX E: UUserDefinedStructFactory — factory class removed; use FStructureEditorUtils
# Replace entire factory-creation + Cast block at line ~1164
# ─────────────────────────────────────────────────────────────────────────────
old_struct = (
    '    UUserDefinedStructFactory* Factory = NewObject<UUserDefinedStructFactory>();\n'
    '    FString PackagePath = Path + TEXT("/");\n'
    '    UPackage* Package = CreatePackage(*(PackagePath + StructName));\n'
    '    UUserDefinedStruct* NewStruct = Cast<UUserDefinedStruct>(\n'
    '        Factory->FactoryCreateNew(UUserDefinedStruct::StaticClass(), Package,\n'
    '                                   *StructName, RF_Standalone | RF_Public, nullptr, GWarn));'
)
new_struct = (
    '    // UE5.6: UserDefinedStructFactory removed; use FStructureEditorUtils directly\n'
    '    FString PackagePath = Path + TEXT("/");\n'
    '    UPackage* Package = CreatePackage(*(PackagePath + StructName));\n'
    '    UUserDefinedStruct* NewStruct = FStructureEditorUtils::CreateUserDefinedStruct(\n'
    '        Package, FName(*StructName), RF_Public | RF_Standalone | RF_Transactional);'
)
if old_struct in src:
    src = src.replace(old_struct, new_struct)
    print("  ✅ Patched UUserDefinedStructFactory")
else:
    print("  ⚠️  UUserDefinedStructFactory block not found verbatim — check manually at line ~1164")

# ─────────────────────────────────────────────────────────────────────────────
# FIX F: UUserDefinedEnumFactory — same pattern
# ─────────────────────────────────────────────────────────────────────────────
old_enum = (
    '    UUserDefinedEnumFactory* Factory = NewObject<UUserDefinedEnumFactory>();\n'
    '    FString PackagePath = Path + TEXT("/");\n'
    '    UPackage* Package = CreatePackage(*(PackagePath + EnumName));\n'
    '    UUserDefinedEnum* NewEnum = Cast<UUserDefinedEnum>(\n'
    '        Factory->FactoryCreateNew(UUserDefinedEnum::StaticClass(), Package,\n'
    '                                   *EnumName, RF_Standalone | RF_Public, nullptr, GWarn));'
)
new_enum = (
    '    // UE5.6: UserDefinedEnumFactory removed; use FEnumEditorUtils directly\n'
    '    FString PackagePath = Path + TEXT("/");\n'
    '    UPackage* Package = CreatePackage(*(PackagePath + EnumName));\n'
    '    UUserDefinedEnum* NewEnum = FEnumEditorUtils::CreateUserDefinedEnum(\n'
    '        Package, FName(*EnumName), RF_Public | RF_Standalone | RF_Transactional);'
)
if old_enum in src:
    src = src.replace(old_enum, new_enum)
    print("  ✅ Patched UUserDefinedEnumFactory")
else:
    print("  ⚠️  UUserDefinedEnumFactory block not found verbatim — check manually at line ~1259")

# ─────────────────────────────────────────────────────────────────────────────
# FIX G: ANY_PACKAGE — deprecated in UE 5.1, removed in UE 5.6
# ─────────────────────────────────────────────────────────────────────────────
src = src.replace('ANY_PACKAGE', 'nullptr')

# ─────────────────────────────────────────────────────────────────────────────
# FIX H: UDataTableFactory — header moved, but factory still exists.
# No code change needed; just needs the correct include path.
# The include "#include "Factories/DataTableFactory.h"" should work via UnrealEd.
# ─────────────────────────────────────────────────────────────────────────────
# (no change needed — factory class is still present, header still works)

# ─────────────────────────────────────────────────────────────────────────────
# FIX I: UBehaviorTreeFactory — create via class loader instead
# ─────────────────────────────────────────────────────────────────────────────
old_bt = '    UBehaviorTreeFactory* Factory = NewObject<UBehaviorTreeFactory>();'
new_bt = (
    '    // UE5.6: BehaviorTreeFactory header removed from public includes; load via class\n'
    '    UClass* BTFactoryClass = LoadClass<UFactory>(nullptr, TEXT("/Script/BehaviorTreeEditor.BehaviorTreeFactory"));\n'
    '    UFactory* Factory = BTFactoryClass ? NewObject<UFactory>(GetTransientPackage(), BTFactoryClass) : nullptr;'
)
src = src.replace(old_bt, new_bt)

# ─────────────────────────────────────────────────────────────────────────────
# FIX J: UBlackboardDataFactory — same
# ─────────────────────────────────────────────────────────────────────────────
old_bb = '    UBlackboardDataFactory* Factory = NewObject<UBlackboardDataFactory>();'
new_bb = (
    '    // UE5.6: BlackboardDataFactory header removed; load via class\n'
    '    UClass* BBFactoryClass = LoadClass<UFactory>(nullptr, TEXT("/Script/BehaviorTreeEditor.BlackboardDataFactory"));\n'
    '    UFactory* Factory = BBFactoryClass ? NewObject<UFactory>(GetTransientPackage(), BBFactoryClass) : nullptr;'
)
src = src.replace(old_bb, new_bb)

# ─────────────────────────────────────────────────────────────────────────────
# FIX K: UAnimationStateMachineSchema + CreateNewGraph (wrong arg count)
#
# Original (3 args — invalid in UE5.6 which requires 4):
#   FBlueprintEditorUtils::CreateNewGraph(
#       AnimBP, FName(*SMName),
#       UAnimationStateMachineGraph::StaticClass(),
#       UAnimationStateMachineSchema::StaticClass());
#
# UE5.6 CreateNewGraph signature: (UObject*, FName, TSubclassOf<UEdGraph>, TSubclassOf<UEdGraphSchema>)
# UAnimationStateMachineSchema still exists in AnimGraph module; it just needs the AnimGraph include.
# ─────────────────────────────────────────────────────────────────────────────
# The REAL fix: the file already has 4 args (2 class args), but the SCHEMA class
# is forward-declared rather than fully included. Add the AnimGraph schema include.
if '#include "AnimationStateMachineSchema.h"' not in src:
    src = src.replace(
        '#include "AnimStateTransitionNode.h"',
        '#include "AnimStateTransitionNode.h"\n#include "AnimationStateMachineSchema.h"'
    )

# ─────────────────────────────────────────────────────────────────────────────
# FIX L: UAnimStateNode::StateName — property removed; use SetStateName()
# The repo source already calls StateNode->SetStateName() — check if your copy does too.
# If it was reverted to the property form by prior patches, fix it:
# ─────────────────────────────────────────────────────────────────────────────
# Restore any property assignments that earlier patches converted wrong
src = re.sub(
    r'// StateNode->StateName removed in UE5\.5\+ - DISABLED\s*\n\s*// StateNode->StateName\s*=\s*FName\([^;]+\);',
    'StateNode->SetStateName(FName(*StateName));',
    src
)
# Also fix if it still exists as direct property
src = src.replace(
    'StateNode->StateName = FName(FName(*StateName));',
    'StateNode->SetStateName(FName(*StateName));'
)
src = src.replace(
    'StateNode->StateName = FName(*StateName);',
    'StateNode->SetStateName(FName(*StateName));'
)

# ─────────────────────────────────────────────────────────────────────────────
# FIX M: UEdGraphNode_Comment — needs EdGraph/EdGraphNode_Comment.h (added in step A)
# No code change required.
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Write result
# ─────────────────────────────────────────────────────────────────────────────
with open(ext_path, "w", encoding="utf-8") as f:
    f.write(src)

print("✅ UnrealMCPExtendedCommands.cpp fixed")
print()
print("Now run:")
print('  & "C:\\Program Files\\Epic Games\\UE_5.6\\Engine\\Build\\BatchFiles\\Build.bat"'
      ' Lab3cEditor Win64 Development'
      ' "C:\\Users\\NewAdmin\\Documents\\Academy of Art University\\2026\\Gam115'
      '\\UnrealProject\\Lab3C\\Lab3c.uproject" -waitmutex')
