# SkyrimTest GrayMotherEmerges Sequence Implementation - 2026-05-18

## Goal

Play the `GrayMotherEmerges` Level Sequence when the player reaches the cave entrance, then animate the `GrayMother` mesh from its staged ceiling-side position to the center of the lair ceiling and down to the ground.

## Trigger

Placed trigger actor:

```text
GrayMotherEmerges_TriggerBox
```

Location:

```text
X=16240.0, Y=270.0, Z=2490.0
```

Class:

```text
/Game/SkyrimTest/Sequences/BP_AmbushSequenceTrigger
```

The trigger is linked to the placed Level Sequence actor:

```text
GrayMotherEmerges
```

The ambush-specific direct movement fallback is disabled on this trigger.

## Sequence

Sequence asset:

```text
/Game/Blueprints/GrayMotherEmerges.GrayMotherEmerges
```

Placed Level Sequence actor:

```text
GrayMotherEmerges
```

Linked sequence:

```text
/Game/Blueprints/GrayMotherEmerges.GrayMotherEmerges
```

## Bound Actor

The sequence has one transform binding:

```text
GrayMother
```

Bound placed actor class:

```text
StaticMeshActor
```

## Transform Keys

Channel order used by UE 5.6 Python scripting:

```text
Location.X, Location.Y, Location.Z, Rotation.X, Rotation.Y, Rotation.Z, Scale.X, Scale.Y, Scale.Z
```

Verified keyframes:

| Frame | Location | Rotation XYZ |
| --- | --- | --- |
| 0 | `X=18810.0, Y=-660.0, Z=3110.0` | `X=93.157715, Y=0.0, Z=-73.949922` |
| 72 | `X=18810.0, Y=660.0, Z=3110.0` | `X=93.157715, Y=0.0, Z=11.422034` |
| 150 | `X=18810.0, Y=660.0, Z=2000.0` | `X=270.614548, Y=-1.106329, Z=6.080213` |
| 165 | `X=18810.0, Y=660.0, Z=2000.0` | `X=270.614548, Y=-1.106329, Z=6.080213` |

The final hold key keeps the Gray Mother grounded after the descent.

## Completion Mode

The transform section is set to:

```text
MovieSceneCompletionMode.KEEP_STATE
```

This should prevent the mesh from snapping back when sequence playback ends.

## Validation Notes

Bridge readback confirmed:

- `GrayMotherEmerges_TriggerBox` exists at `X=16240.0, Y=270.0, Z=2490.0`.
- `GrayMotherEmerges` Level Sequence actor exists and points to `/Game/Blueprints/GrayMotherEmerges.GrayMotherEmerges`.
- The trigger's `SequenceActor` property points to `GrayMotherEmerges`.
- The trigger's ambush direct-move fallback is disabled.
- The `GrayMother` binding has one `MovieScene3DTransformTrack`.
- The transform section is `KEEP_STATE`.
- The transform channel values match the table above.

Manual PIE check:

- Approach the cave entrance trigger.
- Confirm the Gray Mother moves from the side ceiling position to the room center.
- Confirm she descends to `Z=2000.0`.
- Confirm the final leg-down orientation reads correctly from the player view.
- Confirm she remains at the final transform after playback.

## MCP Tooling Limitation Found

UE 5.6 exposes transform section scripting channels through:

```text
section.get_all_channels()
```

not:

```text
section.get_channels()
```

This is a useful follow-up for Unreal-MCP-Ghost: add or harden a first-class Level Sequence authoring tool that can create placed sequence actors, bind placed actors, add transform keys, set keep-state behavior, and create overlap triggers without falling back to ad hoc `exec_python`.
