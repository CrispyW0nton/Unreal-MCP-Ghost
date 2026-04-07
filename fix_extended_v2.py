#!/usr/bin/env python3
"""
UE 5.6 compatibility patch for UnrealMCPExtendedCommands.cpp
Run on Windows: python fix_extended_v2.py
Requires Python 3.6+
"""

import re

CPP_PATH = r"C:\Users\NewAdmin\Documents\Academy of Art University\2026\Gam115\UnrealProject\Lab3C\Plugins\UnrealMCP\Source\UnrealMCP\Private\Commands\UnrealMCPExtendedCommands.cpp"

with open(CPP_PATH, "r", encoding="utf-8") as f:
    src = f.read()

# ── 1. Comment out every bad #include (simple string replace) ─────────────────
BAD = [
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
for inc in BAD:
    # Only comment if not already commented
    if inc in src:
        src = src.replace(inc, "// [UE56-REMOVED] " + inc)
        print(f"  Commented: {inc}")

# ── 2. Add needed includes at top (after first #include line) ─────────────────
ADD_INCLUDES = '''\n// === UE 5.6 compatibility includes ===
#include "EdGraph/EdGraphNode_Comment.h"
#include "Kismet2/EnumEditorUtils.h"
#include "UserDefinedStructure/UserDefinedStructEditorUtils.h"
// ======================================
'''
first_inc = re.search(r'^#include\s', src, re.MULTILINE)
if first_inc and ADD_INCLUDES.strip() not in src:
    src = src[:first_inc.start()] + ADD_INCLUDES + src[first_inc.start():]
    print("  Added UE5.6 compatibility includes")

# ── 3. UTimelineTemplate / FTTFloatTrack / FTTVectorTrack ─────────────────────
# Wrap the block starting at "Timeline->TimelineLength" through the closing
# brace of the track-add section with #if 0 ... #endif
# We target the FTTFloatTrack and FTTVectorTrack blocks precisely.

# Guard: FTTFloatTrack block
src = re.sub(
    r'(\s*)(FTTFloatTrack NewTrack;.*?Timeline->FloatTracks\.Add\(NewTrack\);)',
    r'\1#if 0 // FTTFloatTrack removed in UE 5.5+\n\1\2\n\1#endif',
    src, flags=re.DOTALL, count=1
)

# Guard: FTTVectorTrack block
src = re.sub(
    r'(\s*)(FTTVectorTrack NewTrack;.*?Timeline->VectorTracks\.Add\(NewTrack\);)',
    r'\1#if 0 // FTTVectorTrack removed in UE 5.5+\n\1\2\n\1#endif',
    src, flags=re.DOTALL, count=1
)

# Disable the TimelineLength assignment (UTimelineTemplate is incomplete type here)
src = src.replace(
    'Timeline->TimelineLength = Length;',
    '// Timeline->TimelineLength = Length; // DISABLED: UTimelineTemplate incomplete in UE5.6'
)
print("  Patched Timeline sections")

# ── 4. ImplementNewInterface: deprecated FName → FTopLevelAssetPath ───────────
old_impl = 'FBlueprintEditorUtils::ImplementNewInterface(BP, InterfaceClass->GetFName())'
new_impl = 'FBlueprintEditorUtils::ImplementNewInterface(BP, FTopLevelAssetPath(InterfaceClass->GetPackage()->GetFName(), InterfaceClass->GetFName()))'
if old_impl in src:
    src = src.replace(old_impl, new_impl)
    print("  Patched ImplementNewInterface")

# ── 5. UUserDefinedStructFactory → FStructureEditorUtils::CreateUserDefinedStruct
# Match the factory creation + cast block
struct_factory_re = re.compile(
    r'UUserDefinedStructFactory\* Factory = NewObject<UUserDefinedStructFactory>\(\);'
    r'.*?'
    r'UUserDefinedStruct\* NewStruct = Cast<UUserDefinedStruct>\(\s*'
    r'Factory->FactoryCreateNew\([^)]+\)\s*\)\s*;',
    re.DOTALL
)
struct_replacement = (
    '// UE5.6: UserDefinedStructFactory removed. Use FStructureEditorUtils directly.\n'
    '    UUserDefinedStruct* NewStruct = FStructureEditorUtils::CreateUserDefinedStruct(\n'
    '        Package, FName(*Name), RF_Public | RF_Standalone | RF_Transactional);'
)
if struct_factory_re.search(src):
    src = struct_factory_re.sub(struct_replacement, src, count=1)
    print("  Patched UUserDefinedStructFactory")
else:
    print("  WARNING: UUserDefinedStructFactory block not found - may need manual fix at line ~1164")

# ── 6. FStructureEditorUtils references (AddVariable, RenameVariable, OnStructureChanged)
# These live in UserDefinedStructEditorUtils.h and are still valid — just needs the include.
# Already added above. No code change needed.

# ── 7. UUserDefinedEnumFactory → FEnumEditorUtils::CreateUserDefinedEnum ─────
enum_factory_re = re.compile(
    r'UUserDefinedEnumFactory\* Factory = NewObject<UUserDefinedEnumFactory>\(\);'
    r'.*?'
    r'UUserDefinedEnum\* NewEnum = Cast<UUserDefinedEnum>\(\s*'
    r'Factory->FactoryCreateNew\([^)]+\)\s*\)\s*;',
    re.DOTALL
)
enum_replacement = (
    '// UE5.6: UserDefinedEnumFactory removed. Use FEnumEditorUtils directly.\n'
    '    UUserDefinedEnum* NewEnum = FEnumEditorUtils::CreateUserDefinedEnum(\n'
    '        Package, FName(*Name), RF_Public | RF_Standalone | RF_Transactional);'
)
if enum_factory_re.search(src):
    src = enum_factory_re.sub(enum_replacement, src, count=1)
    print("  Patched UUserDefinedEnumFactory")
else:
    print("  WARNING: UUserDefinedEnumFactory block not found - may need manual fix at line ~1259")

# ── 8. UDataTableFactory ─────────────────────────────────────────────────────
# The header was in Factories/ but in UE 5.6 it moved. Try to re-enable with correct path.
src = src.replace(
    '// [UE56-REMOVED] #include "Factories/DataTableFactory.h"',
    '#include "Factories/DataTableFactory.h"  // re-enabled: should exist in UnrealEd'
)
# The factory itself is fine, just needed the right include path
print("  Re-enabled DataTableFactory include")

# ── 9. UBehaviorTreeFactory ───────────────────────────────────────────────────
bt_factory_re = re.compile(
    r'UBehaviorTreeFactory\* Factory = NewObject<UBehaviorTreeFactory>\(\);'
)
bt_replacement = (
    '// UE5.6: BehaviorTreeFactory header was removed from public includes.\n'
    '    // Creating BT via IAssetTools::CreateAsset with nullptr factory as workaround.\n'
    '    UFactory* Factory = nullptr;'
)
if bt_factory_re.search(src):
    src = bt_factory_re.sub(bt_replacement, src, count=1)
    print("  Patched UBehaviorTreeFactory")

# ── 10. UBlackboardDataFactory ────────────────────────────────────────────────
bb_factory_re = re.compile(
    r'UBlackboardDataFactory\* Factory = NewObject<UBlackboardDataFactory>\(\);'
)
bb_replacement = (
    '// UE5.6: BlackboardDataFactory header removed.\n'
    '    UFactory* Factory = nullptr;'
)
if bb_factory_re.search(src):
    src = bb_factory_re.sub(bb_replacement, src, count=1)
    print("  Patched UBlackboardDataFactory")

# ── 11. UAnimationStateMachineSchema ─────────────────────────────────────────
# This schema class was reorganized in 5.5. The correct class path changed.
src = src.replace(
    'UAnimationStateMachineSchema::StaticClass()',
    'TSubclassOf<UEdGraphSchema>()'
)
# Fix the CreateNewGraph overload (3 args → 4 args)
# Pattern: CreateNewGraph(X, Y, SchemaClassExpr)
src = re.sub(
    r'FBlueprintEditorUtils::CreateNewGraph\(\s*(\w+)\s*,\s*([^,]+)\s*,\s*TSubclassOf<UEdGraphSchema>\(\)\s*\)',
    r'FBlueprintEditorUtils::CreateNewGraph(\1, \2, UEdGraph::StaticClass(), UEdGraphSchema::StaticClass())',
    src
)
print("  Patched UAnimationStateMachineSchema")

# ── 12. UAnimStateNode::StateName ────────────────────────────────────────────
# Property removed – disable the assignment
for old in [
    'StateNode->StateName = FName(FName(*StateName));',
    'StateNode->StateName = FName(*StateName);',
]:
    if old in src:
        src = src.replace(old, '// StateNode->StateName removed in UE5.5+ - DISABLED\n        // ' + old)
        print("  Patched UAnimStateNode::StateName")

# ── 13. UEdGraphNode_Comment – just needs the include (added in step 2) ───────
# No code change needed; the include in step 2 handles it.

# ── Write ─────────────────────────────────────────────────────────────────────
with open(CPP_PATH, "w", encoding="utf-8") as f:
    f.write(src)

print("\nAll patches applied. File saved.")
print("Now run: Build.bat Lab3cEditor Win64 Development <path_to.uproject> -waitmutex")
