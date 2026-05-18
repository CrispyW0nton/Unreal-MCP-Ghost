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

Follow-up HUD visibility issue:

- The first native UMG implementation relied on `WidgetTree` inside a code-only `UUserWidget`, which could result in no visible HUD in PIE.
- The HUD was rewritten as a Slate-backed `RebuildWidget()` implementation so it creates its own visible `SConstraintCanvas` without needing a Widget Blueprint tree.
- After closing Unreal Editor, a full rebuild succeeded:

```text
Build.bat SkyrimTestEditor Win64 Development -Project="...\SkyrimTest.uproject" -WaitMutex -NoHotReloadFromIDE
Result: Succeeded
```

This rebuild should load the fixed HUD class on the next editor restart.

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

- Unreal-MCP-Ghost should gain first-class tools for trigger sound assignment to avoid one-off editor scripting for audio hookup.

## Implemented Audio Wiring

Added native audio hooks:

```text
ASkyrimSequenceTriggerBox
  TriggerSounds: Array<USoundBase>
  SequenceFinishedSound: USoundBase

AGragarClairvoyanceManager
  ActivationSound: USoundBase

ASkyrimStartAudioDirector
  AmbientMusic: USoundBase
  PlayerWakeSound: USoundBase
```

Full rebuild after the C++ changes:

```text
Build.bat SkyrimTestEditor Win64 Development -Project="...\SkyrimTest.uproject" -WaitMutex -NoHotReloadFromIDE
Result: Succeeded
```

Placed/assigned actor:

```text
SkyrimStartAudioDirector
```

BeginPlay audio:

```text
AmbientMusic   -> /Game/Sounds/AmbientMusic.AmbientMusic, looping enabled
PlayerWakesup  -> /Game/Sounds/PlayerWakesup.PlayerWakesup, one play
```

Ambush trigger:

```text
Ambush_TriggerBox.TriggerSounds =
  /Game/Sounds/Goblinattack1.Goblinattack1
  /Game/Sounds/Goblinattack2.Goblinattack2
  /Game/Sounds/GoblinAttack3.GoblinAttack3
```

Clairvoyance activation:

```text
Clairvoyance_Manager.ActivationSound =
  /Game/Sounds/ClairvoyanceActivate.ClairvoyanceActivate
```

Gray Mother trigger:

```text
GrayMotherEmerges_TriggerBox.TriggerSounds =
  /Game/Sounds/SpiderEmerges.SpiderEmerges

GrayMotherEmerges_TriggerBox.SequenceFinishedSound =
  /Game/Sounds/SpiderScreech.SpiderScreech
```

Readback confirmed:

- `Ambush_TriggerBox`: `Goblinattack1`, `Goblinattack2`, `GoblinAttack3`
- `GrayMotherEmerges_TriggerBox`: `SpiderEmerges`
- `GrayMotherEmerges_TriggerBox.SequenceFinishedSound`: `SpiderScreech`
- `Clairvoyance_Manager.ActivationSound`: `ClairvoyanceActivate`
- `SkyrimStartAudioDirector`: `AmbientMusic` + `PlayerWakesup`
- `AmbientMusic.looping`: `true`

## Windows Package Pass

Packaged the project to:

```text
C:\Users\NewAdmin\Documents\Academy of Art University\2026\Gam270\Module14\JordanDelagrange_14_1
```

Executable:

```text
C:\Users\NewAdmin\Documents\Academy of Art University\2026\Gam270\Module14\JordanDelagrange_14_1\Windows\SkyrimTest.exe
```

Build command:

```text
RunUAT.bat BuildCookRun -project="...\SkyrimTest.uproject" -noP4 -platform=Win64 -clientconfig=Development -serverconfig=Development -build -cook -stage -pak -archive -archivedirectory="...\Module14\JordanDelagrange_14_1" -utf8output
```

Initial package attempt failed because Live Coding was active. Closing Unreal Editor and Live Coding resolved that blocker.

Second attempt exposed a runtime target compile issue:

```text
SkyrimSequenceTriggerBox.cpp: GetActorLabel is not a member of AActor
```

Root cause:

- `GetActorLabel()` is editor-only and cannot be used by the packaged game target.

Fix applied in the external SkyrimTest project source:

- Replaced actor-label matching with runtime-safe matching:
  - `ActorHasTag(Target.ActorLabel)`
  - `GetFName() == Target.ActorLabel`
  - `GetName().StartsWith(TargetName)`

Final package result:

```text
BUILD SUCCESSFUL
```
