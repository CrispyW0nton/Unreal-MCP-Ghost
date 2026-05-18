# SkyrimTest HUD, GrayMother Scale, and Audio Cue Pass - 2026-05-18

## GrayMother Scale Fix

The `GrayMotherEmerges` Level Sequence scale channels were locked so the mesh no longer grows during playback.

Sequence:

```text
/Game/Blueprints/GrayMotherEmerges.GrayMotherEmerges
```

Scale keyframes:

| Frame | Scale |
| --- | --- |
| 0 | `X=-0.25, Y=-0.25, Z=-0.25` |
| 72 | `X=-0.25, Y=-0.25, Z=-0.25` |
| 150 | `X=-0.25, Y=-0.25, Z=-0.25` |
| 165 | `X=-0.25, Y=-0.25, Z=-0.25` |

The placed `GrayMother` actor was also set to:

```text
X=-0.25, Y=-0.25, Z=-0.25
```

The transform section remains:

```text
MovieSceneCompletionMode.KEEP_STATE
```

This should keep the scale after the level sequence finishes.

## Skyrim-Style HUD Stub

Updated native widget:

```text
Source/SkyrimTest/GragarClairvoyancePromptWidget.h
Source/SkyrimTest/GragarClairvoyancePromptWidget.cpp
```

The existing `Clairvoyance_Manager` still spawns this widget, but the widget now presents a broader Skyrim-style HUD:

- Top-left readable text:

```text
Press E to use Hunter Clairvoyance
```

- Bottom-left status:
  - Health red bar
  - Magicka blue bar beneath health
- Bottom-center status:
  - Stamina green bar

The prompt text updates while clairvoyance is active:

```text
Hunter Clairvoyance Active: {seconds}s
```

## Build / Reload Notes

Normal UBT build reached object compilation but could not link while the editor held:

```text
UnrealEditor-SkyrimTest.dll
UnrealEditor-SkyrimTest.pdb
```

Live Coding was triggered with `Ctrl+Alt+F11` and succeeded afterward.

Log confirmation:

```text
LogLiveCoding: Display: Live coding succeeded
```

## Audio Suggestions

These are implementation-ready placeholder specs for later import or sound-cue creation.

### Player Start

Ambient music:

- Low Nordic drone with sparse bowed strings.
- Slow heartbeat-like drum every 8-12 seconds.
- Wind bed, cold village ambience, distant crows, faint wood creaks.
- Mood: grief, confusion, aftermath, not combat.

Suggested cue name:

```text
SCue_PlayerStart_RansackedVillage_Ambience
```

Waking voice line:

- Male player voice, close mic, strained and disoriented.
- Line option:

```text
"Camilla...? Where is everyone?"
```

Alternate line:

```text
"My head... the village... no, no, no."
```

Suggested cue name:

```text
SCue_PlayerStart_GragarWakeLine
```

### Hunter Clairvoyance Activation

Sound:

- Short inhale, low magical swell, bright tonal shimmer.
- Layer in a muffled pulse and a faint whispered reverse tail.
- Should feel like a hunter sense opening rather than a spell explosion.

Suggested cue name:

```text
SCue_HunterClairvoyance_Activate
```

### Ambush Trigger

Sound:

- Sudden bow-string snap or leather creak.
- Three quick enemy movement stingers panned around the player.
- Low threat hit, then fast hostile percussion for the sequence.

Suggested cue name:

```text
SCue_Ambush_Gate_Triggered
```

### Gray Mother Trigger

Sound:

- Cave rumble and ceiling dust fall.
- Wet stone scrape / claw drag overhead.
- Deep creature breath, then a descending sub hit as she drops.
- Avoid generic monster roar until she is visible; the reveal should build dread first.

Suggested cue name:

```text
SCue_GrayMother_Emerges
```

## Follow-Up Implementation Notes

- Add sound slots to `ASkyrimSequenceTriggerBox` so each trigger can play a `USoundBase` when activated.
- Add a sound slot to `AGragarClairvoyanceManager` for clairvoyance activation.
- Add a small `APlayerStartAudioDirector` or extend the existing level bootstrap to play the village ambience and wake line once at BeginPlay.
- Unreal-MCP-Ghost should gain first-class tools for trigger sound assignment to avoid one-off editor scripting for audio hookup.
