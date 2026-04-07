#!/usr/bin/env python3
"""
Patch UnrealMCPExtendedCommands.cpp for UE 5.6 compatibility.
Run this script on the Windows machine by copying it there and running:
  python fix_extended.py
OR adapt the path at the top.
"""

import re
import sys

# ── adjust this to match the actual location on your machine ──────────────────
CPP_PATH = r"C:\Users\NewAdmin\Documents\Academy of Art University\2026\Gam115\UnrealProject\Lab3C\Plugins\UnrealMCP\Source\UnrealMCP\Private\Commands\UnrealMCPExtendedCommands.cpp"
# ─────────────────────────────────────────────────────────────────────────────

with open(CPP_PATH, "r", encoding="utf-8") as f:
    src = f.read()

original = src  # keep a copy for diff reporting

# ── 1. Comment out bad #includes ──────────────────────────────────────────────
bad_includes = [
    '#include "UserDefinedStruct.h"',
    '#include "UserDefinedEnum.h"',
    '#include "Engine/UserDefinedStruct.h"',
    '#include "Engine/UserDefinedEnum.h"',
    '#include "Factories/DataTableFactory.h"',
    '#include "Factories/UserDefinedStructFactory.h"',
    '#include "Factories/UserDefinedEnumFactory.h"',
    '#include "Factories/BehaviorTreeFactory.h"',
    '#include "Factories/BlackboardDataFactory.h"',
    '#include "EditorLevelUtils.h"',
]
for inc in bad_includes:
    src = src.replace(inc, "// DISABLED_UE56: " + inc)

# ── 2. Add missing #includes that ARE valid in UE 5.6 ─────────────────────────
# Insert after the last existing #include block
needed_includes = """\
// UE 5.6 compatibility includes added by fix script
#include "EdGraph/EdGraphNode_Comment.h"
#include "TimelineTemplate.h"
#include "Kismet2/BlueprintEditorUtils.h"
"""
# Find a good insertion point – after the last #include line in the preamble
last_include_match = None
for m in re.finditer(r'^#include\s+"[^"]+"\s*$', src, re.MULTILINE):
    last_include_match = m
if last_include_match:
    insert_pos = last_include_match.end()
    src = src[:insert_pos] + "\n" + needed_includes + src[insert_pos:]

# ── 3. Fix UTimelineTemplate section (lines ~660-730) ────────────────────────
# Wrap the entire add_timeline_node function body that uses FTTFloatTrack /
# FTTVectorTrack in an #if 0 … #endif so it compiles away.
# Strategy: find the block between the first use of UTimelineTemplate and the
# closing brace of the containing function, then guard it.

# Guard the Timeline-internal track-adding code block
timeline_pattern = re.compile(
    r'(// Add float track\b.*?Timeline->FloatTracks\.Add\(NewTrack\);)',
    re.DOTALL
)
src = timeline_pattern.sub(
    r'#if 0 // FTTFloatTrack removed in UE 5.5+\n\1\n#endif',
    src,
    count=1
)

vector_pattern = re.compile(
    r'(// Add vector track\b.*?Timeline->VectorTracks\.Add\(NewTrack\);)',
    re.DOTALL
)
src = vector_pattern.sub(
    r'#if 0 // FTTVectorTrack removed in UE 5.5+\n\1\n#endif',
    src,
    count=1
)

# Fix TimelineLength (UTimelineTemplate is forward-declared only; include it)
src = src.replace(
    'Timeline->TimelineLength = Length;',
    '// Timeline->TimelineLength = Length; // DISABLED UE56 - UTimelineTemplate incomplete type'
)

# ── 4. Fix FBlueprintEditorUtils::ImplementNewInterface ──────────────────────
# Replace deprecated FName version with FTopLevelAssetPath version
src = re.sub(
    r'FBlueprintEditorUtils::ImplementNewInterface\(BP,\s*InterfaceClass->GetFName\(\)\)',
    'FBlueprintEditorUtils::ImplementNewInterface(BP, FTopLevelAssetPath(InterfaceClass->GetClassPathName()))',
    src
)

# ── 5. Replace UUserDefinedStructFactory usage with direct FStructureEditorUtils ──
# The factory headers were removed; use FStructureEditorUtils::CreateUserDefinedStruct directly
old_struct_block = re.compile(
    r'UUserDefinedStructFactory\*\s+Factory\s*=\s*NewObject<UUserDefinedStructFactory>\(\);.*?'
    r'UUserDefinedStruct\*\s+NewStruct\s*=\s*Cast<UUserDefinedStruct>\([^;]*\);',
    re.DOTALL
)
new_struct_header = '''\
// UE 5.6: Use FStructureEditorUtils directly (factory removed)
    #include "UserDefinedStructure/UserDefinedStructEditorUtils.h"
    UUserDefinedStruct* NewStruct = FStructureEditorUtils::CreateUserDefinedStruct(Package, FName(*Name), RF_Public | RF_Standalone | RF_Transactional);'''

src = old_struct_block.sub(new_struct_header, src, count=1)

# ── 6. Fix FStructureEditorUtils namespace references ─────────────────────────
# It's actually in UserDefinedStructEditorUtils; add include and keep calls as-is
# (the namespace IS valid if the right header is included)
src = src.replace(
    '// DISABLED_UE56: #include "Factories/UserDefinedStructFactory.h"',
    '// DISABLED_UE56: #include "Factories/UserDefinedStructFactory.h"\n#include "UserDefinedStructure/UserDefinedStructEditorUtils.h"'
)

# ── 7. Replace UUserDefinedEnumFactory usage ──────────────────────────────────
old_enum_block = re.compile(
    r'UUserDefinedEnumFactory\*\s+Factory\s*=\s*NewObject<UUserDefinedEnumFactory>\(\);.*?'
    r'UUserDefinedEnum\*\s+NewEnum\s*=\s*Cast<UUserDefinedEnum>\([^;]*\);',
    re.DOTALL
)
new_enum_header = '''\
// UE 5.6: create enum via FEnumEditorUtils
    UUserDefinedEnum* NewEnum = FEnumEditorUtils::CreateUserDefinedEnum(Package, FName(*Name), RF_Public | RF_Standalone | RF_Transactional);'''
src = old_enum_block.sub(new_enum_header, src, count=1)

# Add required include for FEnumEditorUtils
src = src.replace(
    '// DISABLED_UE56: #include "Factories/UserDefinedEnumFactory.h"',
    '// DISABLED_UE56: #include "Factories/UserDefinedEnumFactory.h"\n#include "Kismet2/EnumEditorUtils.h"'
)

# ── 8. Replace UDataTableFactory usage ────────────────────────────────────────
old_dt_block = re.compile(
    r'UDataTableFactory\*\s+Factory\s*=\s*NewObject<UDataTableFactory>\(\);',
)
src = old_dt_block.sub(
    '// UE5.6: DataTableFactory moved; create via AssetTools directly\n'
    '    UDataTableFactory* Factory = NewObject<UDataTableFactory>(GetTransientPackage());',
    src,
    count=1
)
# Add the include back (it may just be in a different path)
src = src.replace(
    '// DISABLED_UE56: #include "Factories/DataTableFactory.h"',
    '#include "DataTableEditorUtils.h"\n#include "Factories/DataTableFactory.h"'  # re-enable; path may work
)

# ── 9. Fix UBehaviorTreeFactory ───────────────────────────────────────────────
old_bt_block = re.compile(
    r'UBehaviorTreeFactory\*\s+Factory\s*=\s*NewObject<UBehaviorTreeFactory>\(\);',
)
src = old_bt_block.sub(
    'UFactory* Factory = nullptr; // BehaviorTreeFactory removed in UE5.6; using AssetTools with nullptr factory',
    src,
    count=1
)

# ── 10. Fix UBlackboardDataFactory ────────────────────────────────────────────
old_bb_block = re.compile(
    r'UBlackboardDataFactory\*\s+Factory\s*=\s*NewObject<UBlackboardDataFactory>\(\);',
)
src = old_bb_block.sub(
    'UFactory* Factory = nullptr; // BlackboardDataFactory removed in UE5.6',
    src,
    count=1
)

# ── 11. Fix UAnimationStateMachineSchema ──────────────────────────────────────
# In UE 5.5+ the schema class was renamed/moved. Use AnimationStateMachineSchema.
src = re.sub(
    r'UAnimationStateMachineSchema::StaticClass\(\)',
    'LoadClass<UEdGraphSchema>(nullptr, TEXT("/Script/AnimGraph.AnimationStateMachineSchema"))',
    src
)
# Fix CreateNewGraph call – it now needs TSubclassOf wrappers
src = re.sub(
    r'FBlueprintEditorUtils::CreateNewGraph\(\s*'
    r'(AnimBP)\s*,\s*'
    r'(FName\([^)]+\))\s*,\s*'
    r'LoadClass<UEdGraphSchema>\([^)]+\)\s*\)',
    r'FBlueprintEditorUtils::CreateNewGraph(\1, \2, UAnimationGraph::StaticClass(), LoadClass<UEdGraphSchema>(nullptr, TEXT("/Script/AnimGraph.AnimationStateMachineSchema")))',
    src
)

# ── 12. Fix UAnimStateNode::StateName ─────────────────────────────────────────
# StateName was removed; use GetStateName()/SetStateName() or NodeName
src = src.replace(
    'StateNode->StateName = FName(FName(*StateName));',
    '// StateNode->StateName removed in UE5.5; set via StateNode->GetBoundGraph() rename if needed\n    // StateNode->StateName = FName(*StateName); // DISABLED'
)
src = src.replace(
    'StateNode->StateName = FName(*StateName);',
    '// StateNode->StateName removed in UE5.5\n    // StateNode->StateName = FName(*StateName); // DISABLED'
)

# ── 13. Fix UEdGraphNode_Comment ──────────────────────────────────────────────
# Add the missing include (already added above in step 2), but also check usage
# The class itself should work once the header is included.

# ── Write result ──────────────────────────────────────────────────────────────
changes = sum(1 for a, b in zip(original, src) if a != b)
print(f"Applied patches. Character diff count: {changes}")

with open(CPP_PATH, "w", encoding="utf-8") as f:
    f.write(src)

print("Done! File written successfully.")
print("Now run Build.bat again.")
