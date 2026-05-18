# SkyrimTest Ambush Sequence Implementation - 2026-05-18

## Goal

Trigger the `Ambush` Level Sequence when the player overlaps a gate trigger box, moving:

- `Ambusher1`
- `Ambusher2`
- `Ambusher3`

from their staged positions toward the village gate ambush marks.

## Sequence Asset

```text
/Game/Blueprints/Ambush.Ambush
```

The sequence has transform bindings for:

- `Ambusher1`
- `Ambusher2`
- `Ambusher3`

Target positions:

- `Ambusher1`: `X=610.0, Y=-80.0, Z=-310.0`
- `Ambusher2`: `X=695.437881, Y=11.653525, Z=-290.0`
- `Ambusher3`: `X=591.139137, Y=103.423739, Z=-288.914053`

Target yaw:

```text
-252.057172 degrees
```

The original requested Z was `-200.0`, but the mannequins visually floated at the end of playback. The final/held Z keys were floor-fitted to the per-actor values above.

## Trigger

Added native trigger actor:

```text
ASkyrimSequenceTriggerBox
```

Blueprint wrapper:

```text
/Game/SkyrimTest/Sequences/BP_AmbushSequenceTrigger
```

Placed actor:

```text
Ambush_TriggerBox
```

Trigger location:

```text
X=-30.0, Y=130.0, Z=-320.0
```

The trigger is linked to the placed `Ambush` LevelSequenceActor.

## Snap-Back Fix

The ambushers initially moved during sequence playback but snapped back afterward. This was caused by Sequencer restore-state behavior.

Fix applied:

- Each transform section in `/Game/Blueprints/Ambush` uses:

```text
MovieSceneCompletionMode.KEEP_STATE
```

- The placed `Ambush` LevelSequenceActor playback settings use:

```text
MovieSceneCompletionModeOverride.FORCE_KEEP_STATE
```

This should preserve the final ambush positions after playback finishes.

## Build Notes

`SkyrimTest.Build.cs` now includes:

- `LevelSequence`
- `MovieScene`

`MovieScene` was required to link `UMovieSceneSequencePlayer::Play`.

## Validation Notes

- The sequence asset contains 3 bindings and 1 transform track per ambusher.
- The transform sections are saved as `KEEP_STATE`.
- The placed `Ambush` sequence actor is saved with `FORCE_KEEP_STATE`.
- The trigger Blueprint compiled and saved cleanly.

Manual PIE check still recommended:

- Cross the trigger near the village gate.
- Confirm all three ambushers move.
- Confirm they remain at the ambush marks after the sequence ends.
- Confirm the final per-actor Z values sit correctly on the floor. If still floating or sinking, adjust final Z keys in the sequence.
