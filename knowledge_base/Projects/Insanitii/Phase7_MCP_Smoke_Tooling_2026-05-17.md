# Phase 7 MCP Smoke Tooling Report - 2026-05-17

## Purpose

Use Insanitii as the live smoke project while expanding Unreal-MCP-Ghost's project verification surface.

## MCP Tooling Added

- `get_actor_identity`: returns placed actor label, object name, full object path, generated class, class path, and native class chain.
- `find_actors_by_class`: finds placed actors by Blueprint-generated class or native parent class.
- `check_blueprint_generated_class`: verifies that a Blueprint wrapper has a valid generated class, parent class, and class default object.
- `inspect_input_mapping_context`: reads Enhanced Input Mapping Context actions, keys, modifiers, and triggers.
- `editor_list_blocking_dialogs`: lists visible Unreal/Windows dialogs that can block automation.
- `editor_dismiss_blocking_dialog`: clicks an explicit named button on a blocking dialog, such as `Yes`, `OK`, `Replace`, or `Cancel`.

## Live Insanitii Readback

Before the new native commands were reloaded into the editor, the Python-side smoke wrappers confirmed:

- Bridge `ping` returned `pong`.
- `get_actor_identity(actor_name_or_label="INS_")` found 7 placed Insanitii actors.
- `check_blueprint_generated_class("BP_RuntimeBootstrap")` reported a valid generated class.
- `inspect_input_mapping_context("/Game/Input/IMC_Default")` reported 18 mappings.
- `editor_list_blocking_dialogs()` found 0 visible blocking dialogs.

## Finding

UE Python does not expose enough Blueprint parent-class reflection in this project to reliably match `InsanitiiTestInteractable` through the native superclass chain. The route was promoted to native C++ so `UClass::GetSuperClass()` can be used directly after Live Coding or editor reload.

## Prompt Handling Policy

Prompt dismissal is intentionally explicit. The MCP should list dialogs first and only click a named button chosen by the agent/user for the current operation. This avoids accidentally accepting destructive prompts.

## Next Validation

Live Coding hotkey was sent after syncing the focused plugin source files into the Insanitii project plugin. The running bridge still reported the new native commands as unknown, so Unreal had not reloaded the module.

UnrealBuildTool was then run for `InsanitiiEditor`. The updated UnrealMCP C++ files compiled, including `UnrealMCPEditorCommands.cpp` and `UnrealMCPBridge.cpp`, but final linking failed because the open editor and LiveCodingConsole were locking `UnrealEditor-Insanitii.dll`, `UnrealEditor-UnrealMCP.dll`, and `UnrealEditor-UnrealMCP.pdb`.

After Live Coding successfully reloads or the editor is restarted, run:

1. `find_actors_by_class(class_name="InsanitiiTestInteractable")`
2. `find_actors_by_class(class_name="BP_TestInteractable")`
3. `inspect_input_mapping_context("/Game/Input/IMC_Default")`
4. `editor_list_blocking_dialogs()`

Expected result: five test interactables for both class queries, 18 input mappings, and no blocking dialogs.
