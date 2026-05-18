# SkyrimTest Clairvoyance System Implementation - 2026-05-18

## Goal

Add Gragar's Hunter Clairvoyance presentation layer for the level design test:

- `E` activates clairvoyance.
- HUD prompt says `Activate Clairvoyance with E`.
- Gragar's vision shifts into a yellow clairvoyant post-process look.
- Placed clue objects appear as glowing emissive yellow markers while clairvoyance is active.

## Native Classes Added

Project source path:

```text
C:\Users\NewAdmin\Documents\Academy of Art University\2026\Gam270\Project 4\SkyrimTest\Source\SkyrimTest
```

Classes:

- `AGragarClairvoyanceManager`
  - Enables input for player 0.
  - Binds `E` to `ToggleClairvoyance`.
  - Creates the HUD prompt widget.
  - Owns an unbound post-process component.
  - Activates all `AGragarClairvoyanceRevealObject` actors for 12 seconds.
- `AGragarClairvoyanceRevealObject`
  - Placeable clue actor.
  - Hidden by default at BeginPlay.
  - Reveals as a yellow emissive sphere/light when clairvoyance is active.
  - Loads `/Game/SkyrimTest/Clairvoyance/M_ClairvoyanceReveal_Yellow` during construction.
- `UGragarClairvoyancePromptWidget`
  - Runtime-created UMG widget.
  - Inactive text: `Activate Clairvoyance with E`.
  - Active text: countdown-style clairvoyance status.

`SkyrimTest.Build.cs` now includes `UMG`, `Slate`, and `SlateCore`.

## Content Assets Created

Folder:

```text
/Game/SkyrimTest/Clairvoyance
```

Assets:

- `M_ClairvoyanceReveal_Yellow`
- `BP_ClairvoyanceManager`
- `BP_ClairvoyanceClue_Orb`
- `BP_ClairvoyanceClue_Footprints`
- `BP_ClairvoyanceClue_DragMarks`
- `BP_ClairvoyanceClue_FamilyToken`

Placed actor:

- `Clairvoyance_Manager`

## How To Stage Clues

Drag any of these into the level:

- `BP_ClairvoyanceClue_Orb`
- `BP_ClairvoyanceClue_Footprints`
- `BP_ClairvoyanceClue_DragMarks`
- `BP_ClairvoyanceClue_FamilyToken`

Place them along the investigation trail, near clues, drag marks, dropped family objects, or shrine/lair route markers. They should be invisible during normal play and appear when the player activates clairvoyance.

Only one `BP_ClairvoyanceManager`/`Clairvoyance_Manager` should be needed in the level.

## Validation

- Project rebuilt successfully:

```text
Build.bat SkyrimTestEditor Win64 Development -Project="...\SkyrimTest.uproject" -WaitMutex -NoHotReloadFromIDE
Result: Succeeded
```

- Created all Blueprint wrappers and material through the live UnrealMCP bridge.
- Compiled/saved all five clairvoyance Blueprints through `compile_blueprint` and `save_blueprint`.
- Runtime smoke test:
  - Spawned a temporary `BP_ClairvoyanceClue_Orb`.
  - Started Simulate-in-Editor.
  - Called `activate_clairvoyance()` on the manager.
  - Confirmed the temporary clue became revealed and visible.
  - Confirmed the post-process blend reached approximately `0.9999`.
  - Stopped Simulate-in-Editor.
  - Deleted the temporary probe actor.

## Notes

- The active duration is currently `12` seconds.
- The manager uses a yellow scene tint, vignette, bloom boost, and chromatic fringe for the clairvoyant effect.
- The reveal actors use an emissive yellow material plus point light for readability.
- If `E` conflicts with another interaction binding later, move this to Enhanced Input or route it through the player character.
