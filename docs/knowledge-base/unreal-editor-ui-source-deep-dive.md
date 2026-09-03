# Unreal editor UI source deep dive for Unreal-MCP-Ghost

Source studied: a local Unreal Engine source checkout (UE 5.6).

This guide records the editor-source patterns that should shape the Tripo
Workspace and the broader Unreal-MCP-Ghost UI. It is not a copy of engine
source; it is an implementation-focused map of how Unreal's editor UI hangs
together and what we should copy or grow toward.

## Why this matters

The user-facing product direction is moving from "an MCP panel in Unreal" to an
AI-native Unreal IDE. For that to feel native, generation work should not feel
like a web form bolted onto the editor. It should behave like other Unreal
asset-editing experiences: double-click asset, open a substantial editor window,
inspect in a real editor viewport, expose details/settings in familiar panels,
use menus/toolbars/commands, preserve layout, and keep chat as the conversational
orchestration layer.

## Source files worth re-reading before UI work

| Area | Engine source files | Why it matters |
| --- | --- | --- |
| Standalone asset editors | `Engine/Source/Editor/UnrealEd/Private/Toolkits/AssetEditorToolkit.cpp`, `.../Public/Toolkits/AssetEditorToolkit.h` | Defines the normal asset editor lifecycle, standalone vs world-centric modes, major tabs, layout restore, menu/toolbar creation, and asset-open notifications. |
| Standalone toolkit host | `Engine/Source/Editor/UnrealEd/Private/Toolkits/SStandaloneAssetEditorToolkitHost.cpp` | Shows how an asset editor host owns restored tab layouts, toolbar slot, menu overlay, panel drawer, status bar, close handling, and `BringToFront`. |
| Workflow modes | `Engine/Source/Editor/UnrealEd/Private/WorkflowCentricApplication.cpp`, `.../Private/WorkflowOrientedApp/WorkflowTabManager.cpp` | Shows how editors with modes swap layouts, tab factories, toolbar extenders, and workspace menu categories. |
| Base editor viewport | `Engine/Source/Editor/UnrealEd/Public/SEditorViewport.h`, `.../Private/SEditorViewport.cpp` | Defines the `SViewport` plus `FSceneViewport` plus `FEditorViewportClient` wiring used by native editor viewports. |
| Preview scenes | `Engine/Source/Editor/AdvancedPreviewScene/Public/AdvancedPreviewScene.h`, `.../Private/AdvancedPreviewScene.cpp` | Provides floor, environment, lighting, post-process, grid, and preview-profile behavior used by asset preview windows. |
| Static Mesh editor | `Engine/Source/Editor/StaticMeshEditor/Private/StaticMeshEditor.cpp`, `SStaticMeshEditorViewport.*`, `StaticMeshEditorViewportClient.*` | Best direct comparison for generated mesh inspection: viewport, preview component, details view, LOD/show menus, Nanite/collision/UV overlays, refresh paths. |
| Material editor | `Engine/Source/Editor/MaterialEditor/Private/MaterialEditor.*`, `SMaterialEditorViewport.*`, `MaterialEditorActions.h` | Shows preview mesh/material switching, live preview commands, details panels, graph/editor split, and custom preview behavior. |
| Persona/animation editors | `Engine/Source/Editor/Persona/Public/PersonaAssetEditorToolkit.h`, `AnimationEditorViewportClient.h`, `Private/AnimationEditorPreviewScene.cpp`, viewport toolbar files | Useful for multi-mode editors, preview-scene control, playback/follow menus, and richer viewport interaction. |
| Details panels | `Engine/Source/Editor/PropertyEditor/Public/PropertyEditorModule.h`, `IDetailsView.h`, `DetailsViewArgs.h` | Native right-side property panels should be `IDetailsView` or structure details when editing UObject/struct state. |
| Mesh paint | `Engine/Source/Editor/MeshPaint`, `Engine/Source/Editor/UnrealEd/Public/MeshPaintRendering.h`, `.../Private/MeshPaintRendering.cpp`, `EditorFramework/Public/EditorModes.h` | Source path for brush radius, viewport paint rays, mesh paint adapters, shader-based texture paint rendering, and editor mode activation. |
| Menus and style | `ToolMenus` usage across `LevelEditor`, `StaticMeshEditor`, `MaterialEditor`, and `Persona`; `Runtime/SlateCore/Private/Styling/AppStyle.cpp` | Use `UToolMenus`, `FUICommandList`, `TCommands`, `FSlateIcon`, and `FAppStyle` instead of custom-looking ad hoc controls. |

## How native standalone asset editors work

`FAssetEditorToolkit::InitAssetEditor` is the core pattern behind "double-click
an asset and get a real editor." In standalone mode, it creates a major tab,
asks editor settings where asset editors should open, inserts the tab through
`FGlobalTabmanager`, creates a new tab manager for that editor, and places an
`SStandaloneAssetEditorToolkitHost` inside the major tab.

Important behavior to mirror:

- The asset editor is a toolkit, not just a widget. The toolkit owns edited
  objects, commands, menus, toolbars, and the tab manager.
- Standalone and world-centric are both first-class. The same editor can open
  as its own workspace or inside the level editor depending on editor settings.
- Unreal does not simply spawn arbitrary windows for asset editors. It inserts
  a major tab in a location chosen by `UEditorStyleSettings` and saved layout
  state, then brings the parent window to front.
- `FLayoutSaveRestore` loads user layout from config before restoring the
  tabbed UI. Native editors remember user layout.
- `UAssetEditorSubsystem` is notified before widgets are created and after
  assets are opened. That is part of why asset editors participate in editor
  lifecycle, analytics, and asset-open behavior.

Current Tripo implication:

- Our immediate `SWindow` path is a good bridge because the user explicitly
  wants a separate workspace window now.
- The more native long-term target is a small `FAssetEditorToolkit` or
  `FWorkflowCentricApplication` for a Tripo session UObject/asset. That would
  give us layout persistence, menu/toolbar/status-bar behavior, and proper
  participation in the editor's asset-editor lifecycle.

## The standalone toolkit host is the real native shell

`SStandaloneAssetEditorToolkitHost` is the shell that makes standalone asset
editors feel like Unreal rather than ordinary Slate windows. It registers or
extends a tool menu for the app name, restores the tab layout, builds a vertical
asset-editor body, inserts the toolbar slot, restores a panel drawer, creates a
status bar through `UStatusBarSubsystem`, and wires tab-close callbacks.

Design lessons for Tripo Workspace:

- Keep the viewport, generation controls, texture-paint controls, evidence,
  and details as tabs or panels in a restorable layout.
- Use a top toolbar for common commands: Generate, Wait, Import, Frame, Save,
  Texture Paint, Capture Snapshot, Compile Evidence.
- Use a status bar for credit/spend/session state instead of putting every
  status line in the side panel.
- Reuse/focus an existing workspace instance when possible. Unreal asset
  editors avoid scattering duplicate windows for the same editing context.

## Workflow modes map cleanly to generation modes

`FWorkflowCentricApplication::SetCurrentMode` shows the native pattern for
editors with modes. When the mode changes, Unreal deactivates the old mode,
unregisters tab spawners, activates the new mode layout, restores it, then
regenerates mode-specific toolbar/menu content.

Tripo mapping:

- `text_to_model`, `multiview_to_model`, and `texture_paint` should eventually
  be application modes, not only button state.
- Each mode can own a layout: Text mode has prompt/settings/evidence; Multiview
  adds ordered reference panels; Texture Paint has viewport, generated texture
  preview, brush controls, paint pass history, and save/evidence tabs.
- Mode-specific toolbar names should be registered through `UToolMenus` so
  extensions can add commands later.

## Native editor viewport anatomy

`SEditorViewport` is the base widget that turns Slate into an editor viewport.
Its construction flow is:

1. Create an `SViewport` and an overlay.
2. Ask the subclass for an `FEditorViewportClient`.
3. Create an `FSceneViewport` connected to the client and `SViewport`.
4. Bind viewport commands through an `FUICommandList`.
5. Add focus indicators and toolbar overlays.
6. Use active timers when the viewport is realtime.

Tripo mapping:

- The current `STripoAssetViewport : SEditorViewport` direction is correct.
- The next native upgrade is to use an `SAssetEditorViewport` style and a
  dedicated viewport client rather than a generic `FEditorViewportClient`.
- The viewport should expose its command list to toolbar/menu generation.
- Frame, view mode, show grid/floor/environment, LOD, Nanite/fallback, UV,
  collision, and texture-paint overlay commands should be command-list actions,
  not only loose buttons.

## Preview scene and generated mesh inspection

`FAdvancedPreviewScene` derives from `FPreviewScene` and is tickable in the
editor. It reads asset viewer settings, manages environment/floor/grid, updates
lighting/post-processing, and exposes command-list actions for preview-scene
toggles.

The Static Mesh editor shows the practical mesh preview pattern:

- It owns a preview mesh component and adds it to an advanced preview scene.
- It keeps the preview component referenced through `FGCObject`.
- The viewport client owns mesh-specific rendering toggles and selection/focus
  behavior.
- The editor refreshes the viewport when mesh/object properties change.
- Details panels are created through `FPropertyEditorModule::CreateDetailView`
  and pointed at the current mesh or selected subobjects.

Tripo mapping:

- Generated imports should load into a preview component inside an advanced
  preview scene, with GC-safe references.
- The side panel should grow into a real details view for a Tripo session
  UObject and selected generated asset, not only manually laid out text boxes.
- Game-readiness checks belong in viewport overlays and details sections:
  topology status, face count, LOD state, collision state, UV/material slots,
  Nanite setting, imported textures, and evidence status.

## Material and texture work

The Material editor combines a graph/document workspace, preview viewport,
details view, live preview commands, preview mesh selection, and refresh
delegates. For the Tripo texture-generation workflow, this suggests a split
between:

- Generated texture prompt/result state.
- A material/texture preview and details panel.
- A mesh viewport that can show the current painted/blended result.
- Commands for live update, force refresh, save/apply, and revert.

The mesh paint source is the stronger reference for actual painting. It uses
editor modes, paint settings, geometry adapters, viewport-derived paint rays,
component-space brush radius, front-facing filters, paint actions, and
shader-based texture paint rendering/dilation.

Tripo texture-paint implication:

- Do not hand-roll final brush interaction as generic mouse math in the Tripo
  widget.
- Study `MeshPaint` and the Interactive Tools Framework before implementing
  real brush strokes.
- Short term, our evidence flow can record paint passes and snapshots.
- Long term, Tripo texture paint should integrate with an editor mode or tool
  that uses mesh-paint-style adapters and viewport rendering, then apply AI
  texture imagery through a material/texture pipeline.

## Details panels and settings

Native editors use `FPropertyEditorModule`, `FDetailsViewArgs`, and
`IDetailsView` for editable state. Static Mesh and Material editors create
detail views, hide or customize the name area, register class customizations,
and call `SetObject` or `SetObjects` as selection changes.

Tripo mapping:

- Create a UObject-backed `UTripoWorkspaceSession` or similar editor-only
  settings object for provider, API balance, local credit budget, output folder,
  Smart Mesh policy, active task ids, import target, and texture-paint state.
- Put that object in an `IDetailsView` so the UI immediately feels like Unreal
  and gains property editing behavior.
- Keep secrets such as the API key in the existing saved secrets path, but show
  non-secret status in the details/status bar.

## Menus, commands, and style

Unreal's editor UI is command driven. Editors define `TCommands`, bind them to
`FUICommandList`, and surface them through `UToolMenus`, toolbar entries,
viewport menus, context menus, and keyboard shortcuts. Visual styling comes
from `FAppStyle` keys such as editor fonts, panel brushes, toolbar styles, menu
styles, details-view rows, and editor viewport icons.

Tripo mapping:

- Replace important text-only buttons with command-backed toolbar actions and
  `FSlateIcon(FAppStyle::GetAppStyleSetName(), "...")` when a matching icon
  exists.
- Keep dense editor panels using `Brushes.Panel`, `Brushes.Recessed`,
  `DetailsView` row styles, and standard fonts.
- Avoid web-app composition inside Unreal. No marketing hero sections, no big
  decorative cards, no one-off color system.
- Use menus for option sets and command groups; use details views for editable
  state; use viewport overlays for viewport-specific feedback.

## Recommended architecture for the Tripo Workspace

Short-term bridge, already aligned:

1. Open/focus a standalone Tripo Workspace window from chat, menu, and preview
   cards.
2. Keep using `SEditorViewport` plus `FAdvancedPreviewScene` for generated mesh
   preview.
3. Poll config handoff for `PreviewAssetPath` so imported `/Game/...` assets
   open in the workspace.
4. Keep Smart Mesh defaults visible in workspace state.
5. Use a transient `UTripoWorkspaceSession` in an `IDetailsView` for native
   session/settings display while the dedicated toolkit does not exist yet.

Next native pass:

1. Add a dedicated viewport client for Tripo preview behavior.
2. Add a top toolbar using `UToolMenus`/`FUICommandList`.
3. Extend the existing `IDetailsView` to include selected generated asset
   details alongside the session UObject.
4. Move credit/session readout into a status bar-like footer or toolbar area.
5. Add viewport show menus: grid, floor, environment, collision, UV, LOD,
   Nanite/fallback, bounds, texture overlay.

Long-term native asset-editor pass:

1. Create an editor-only Tripo session asset or UObject model.
2. Wrap the workspace in `FAssetEditorToolkit` or `FWorkflowCentricApplication`.
3. Represent Text to 3D, Multi Image to 3D, and Texture Paint as workflow modes.
4. Persist layouts with `FTabManager::FLayout`.
5. Use tab factories for viewport, task/evidence, details, texture result,
   paint history, and logs.
6. Investigate `MeshPaint` and Interactive Tools Framework for brush-authoring
   rather than implementing paint interaction as plain widget callbacks.

## Current gap against native Unreal feel

The current Tripo Workspace is much closer than a chat-only panel, but it is
still a custom `SWindow` containing one custom compound widget. It needs the
toolkit host pattern, command lists, details view, status bar, and viewport
toolbar before it truly feels like an Unreal asset editor. The source-backed
target is clear: generation should become an editor toolkit with a rich preview
viewport and mode-specific layouts, while chat remains the command/evidence
conversation surface.
