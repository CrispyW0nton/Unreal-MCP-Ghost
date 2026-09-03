# Phase 3 Player Apartment Gameplay Setup - 2026-06-22

## Summary

The player apartment map now has a first playable apartment interaction pass layered onto the staged finished props in `/Game/Insanitii/Maps/Lvl_PlayerApartment`.

This pass adds:

- Native apartment activity interactions for the existing trigger boxes:
  - `Bed_bounds`
  - `Coffee_bounds`
  - `Cook_Breakfast_Bounds`
  - `Do_Laundry_Bounds`
  - `Fold_Laundry_Bounds`
  - `Eat_Food_Bounds`
  - `Listen_To_Birds_Bounds`
  - `Overwhelming_Sounds_Bounds`
  - `Tobacco_Bounds`
- A simple bed setup at the bed trigger:
  - `APT_Bed_Base`
  - `APT_Bed_Mattress`
  - `APT_Bed_Pillow`
- ElevenLabs apartment interaction and feedback sounds imported to `/Game/Insanitii/Audio/Apartment`.
- Distinct event stations staged with activity props and colored local lights so the coffee, cooking, laundry, fold laundry, food, birds, noise, and tobacco areas are readable.
- A native prop-chaos psychosis director that animates real small apartment props during low mental state / psychosis.
- A minimal default HUD path with the dense debug HUD still available through `H`.
- Apartment prop-chaos psychosis now drives the post-process controller's dramatic event path through a dedicated `ApartmentPropChaos` visual signature.
- Apartment psychosis now restores the older voice/psychosis audio pressure path and stages the active prop event around the player instead of scattering props randomly.

## Native Gameplay Additions

New C++ classes:

- `AInsanitiiApartmentActivityDirector`
  - Finds the named `TriggerBox` activity bounds in the apartment.
  - Shows a clean HUD prompt while the player is inside or near a trigger.
  - Executes the activity on `E`.
  - Applies mental-state deltas through `UInsanitiiMentalStateComponent`.
  - Triggers stabilizing or destabilizing post-process pulses through `AInsanitiiPostProcessController`.
  - Plays the matching interaction sound.
- `AInsanitiiApartmentPropChaosDirector`
  - Collects actors tagged `InsanitiiApartmentPsychosisProp`.
  - Excludes walls, kitchen pieces, ceiling/light actors, doors, windows, floors, closet, and air-conditioner actors.
  - Starts when psychosis is active or mental state falls below the configured threshold.
  - Temporarily makes tagged props movable/non-colliding, animates them through one of three prop-flight variations, then restores transforms/collision.
- `AInsanitiiPostProcessController`
  - Treats `UInsanitiiMentalStateComponent::bIsInPsychosisEvent` as an active psychosis event even when the older event director is not running.
  - Adds an `ApartmentPropChaos` visual signature with oscillating color shift, focus warp, saturation flutter, contrast, vignette, and amplified FOV pulse.
- `AInsanitiiAudioFeedbackDirector`
  - Now reacts to either the older psychosis event director or the mental-state psychosis flag.
  - This lets apartment prop-chaos psychosis trigger the established psychosis start cue, variant accents, intrusive voices, and false-cue pressure even when the apartment event is started directly by mental state.

## Psychosis Tuning Pass

Research direction:

- NIMH describes psychosis as disruption in thoughts and perceptions, with difficulty recognizing what is real and symptoms including hallucinations, delusions, suspiciousness, confused thought/speech, and sleep disruption.
- WHO frames schizophrenia around impaired reality perception, hallucinations across sensory modalities, experiences of influence/control/passivity, disorganized thinking/behavior, and cognitive difficulty.
- A 2025 Schizophrenia/Nature review of altered perceptual experiences emphasizes that voice hearing is heterogeneous; voices may feel as clear as ordinary conversation, may speak to or about the hearer, and multimodal hallucinations can increase conviction and distress.
- Stanford/Luhrmann reporting on voice-hearing culture notes that many people report both helpful and hostile voices, with U.S. subjects often describing harsher, threatening, bombardment-like experiences.

Applied design takeaways:

- The event should not read as random haunted-room physics. It should feel like ordinary apartment meaning collapsing under pressure.
- Props now orbit and close in around the player during apartment prop chaos, making the player feel surrounded by ordinary objects that have become personally salient.
- Non-orbiting props still tremble subtly so the room feels unstable without turning every prop into visual noise.
- The camera now carries stronger psychosis presentation: larger FOV pulse, shorter focal distance, wider aperture, stronger focus warp, chromatic aberration, film grain, motion blur, bloom, contrast, vignette, saturation flutter, and color drift.
- Audio is treated as an equal part of the event. Apartment prop-chaos psychosis now reuses the old psychosis start/variant sound path and escalates voice pressure/false cues through the audio feedback director.
- The tone target is "misadventure inside fragile certainty," influenced by *A Beautiful Mind* without relying only on visible hallucination spectacle.

References:

- NIMH - Understanding Psychosis: `https://www.nimh.nih.gov/health/publications/understanding-psychosis`
- WHO - Schizophrenia fact sheet: `https://www.who.int/news-room/fact-sheets/detail/schizophrenia`
- Schizophrenia/Nature - Altered perceptual experiences and hallucinations: `https://www.nature.com/articles/s41537-025-00673-3`
- Stanford - How culture shapes voice-hearing experience: `https://news.stanford.edu/stories/2014/07/voices-culture-luhrmann-071614`

## Activity Tuning

Mental-state deltas:

- Coffee: `+0.15`
- Cook breakfast: `-0.11`
- Laundry: `-0.10`
- Fold laundry: `+0.11`
- Eat food: `+0.12`
- Listen to birds: `+0.16`
- Overwhelming sounds: `-0.36`
- Tobacco: `-0.13`
- Sleep: `+0.38`

Positive values stabilize. Negative values destabilize and push the apartment toward psychosis.

Interaction audio now uses delayed feedback so the station foley reads before the generic stabilizing/destabilizing cue. Coffee is generated as brew, sip, then sigh. Tobacco is generated as lighter flicks, burn/inhale, then cough. Cooking uses pan sizzle and reveals `APT_EatFood_GroundingTable` after the cooking beat so the eat-breakfast station becomes visible as a consequence of cooking.

## Audio Assets

Generated ElevenLabs WAVs:

- `SFX_Apartment_Coffee`
- `SFX_Apartment_BreakfastSizzle`
- `SFX_Apartment_Laundry`
- `SFX_Apartment_FoldLaundry`
- `SFX_Apartment_EatFood`
- `SFX_Apartment_Birds`
- `SFX_Apartment_OverwhelmingMetal`
- `SFX_Apartment_Tobacco`
- `SFX_Apartment_SleepYawn`
- `SFX_Apartment_PleasantSigh`
- `SFX_Apartment_AnxiousHit`

Imported destination:

- `/Game/Insanitii/Audio/Apartment`

The first pass used locally generated temporary foley. The sounds were then replaced with ElevenLabs generations through `https://api.elevenlabs.io/v1/sound-generation`, converted from MP3 to WAV with `ffmpeg`, and imported over the same Unreal asset names so gameplay code kept working.

Generation receipt:

- `generated_audio/insanitii_apartment_elevenlabs/elevenlabs_generation_receipt.json`

Note: the audio import commandlet wrote a successful receipt and assets verified cleanly, but Unreal reported shutdown callstack noise after `AssetImportTasks`. This mirrors earlier commandlet instability around bulk editor operations; the verification pass confirms the imported assets are present.

## Map Staging

Staged actors:

- `INS_ApartmentActivityDirector`
- `INS_ApartmentPropChaosDirector`
- `INS_PsychosisEventDirector`
- `INS_PostProcessController`
- `INS_AudioFeedbackDirector`
- `APT_Bed_Base`
- `APT_Bed_Mattress`
- `APT_Bed_Pillow`
- `APT_Coffee_SiphonMaker`
- `APT_Coffee_Cups`
- `APT_Laundry_WasherDryer`
- `APT_FoldLaundry_Table`
- `APT_FoldLaundry_Shirt`
- `APT_EatFood_GroundingTable`
- `APT_Birds_WindowCushion`
- `APT_Overwhelming_NoiseCluster`
- `APT_Tobacco_Pipe`
- `APT_Tobacco_AshTray`
- `APT_EventLight_*` station lights for each activity area

Tagged psychosis props: 30.

Tagged examples include:

- `SM_Guitar`
- `SM_CoffeeTable`
- `SM_Cups`
- `SM_AshTray`
- `SM_MetalTeapot`
- `SM_SiphonCoffeeMaker`
- `SM_WoodenPipe`
- `SM_PortableGasStove`
- `SM_PaperStack1`
- `SM_PaperStack2`
- `SM_HawaiianShirt`
- `SM_SnareDrumn`

Excluded by design:

- Walls
- Kitchen wall pieces
- Ceiling light
- Doors/windows
- Closet/air-conditioner/floor actors

## Verification

Build:

- `Build.bat InsanitiiEditor Win64 Development ... -NoHotReload`
- Result: succeeded.

Receipts:

- `Saved/Automation/insanitii_apartment_audio_import_receipt.json`
  - `success: true`
  - `imported_count: 11`
- `Saved/Automation/insanitii_apartment_gameplay_stage_receipt.json`
  - `success: true`
  - `created_or_found_fold_laundry_trigger: Fold_Laundry_Bounds`
  - `tagged_prop_count: 30`
- `Saved/Automation/insanitii_apartment_gameplay_verification_receipt.json`
  - `success: true`
  - Missing triggers: none
  - Missing bed actors: none
  - Missing station actors: none
  - Missing audio assets: none
  - Activity director count: 1
  - Prop chaos director count: 1
  - Psychosis event director count: 1
  - Post-process controller count: 1
  - Audio feedback director count: 1
  - Tagged prop count: 30

Project map defaults:

- `Config/DefaultEngine.ini`
  - `EditorStartupMap=/Game/Insanitii/Maps/Lvl_PlayerApartment.Lvl_PlayerApartment`
  - `GameDefaultMap=/Game/Insanitii/Maps/Lvl_PlayerApartment.Lvl_PlayerApartment`
  - `ServerDefaultMap=/Game/Insanitii/Maps/Lvl_PlayerApartment.Lvl_PlayerApartment`

Follow-up live editor correction:

- `FoldLaundry` remains wired in C++ to the `Fold_Laundry_Bounds` actor label.
- The duplicate auto-created `Fold_Laundry_Bounds` trigger was removed after the designer-added bounds was restored; live readback now reports exactly one fold-laundry bounds actor.
- `APT_Cook_PortableStove` was removed because the cooking bounds already sits near the apartment stove model.
- `scripts/ue_stage_insanitii_apartment_gameplay.py` no longer spawns a portable stove for the cook station, and `scripts/ue_verify_insanitii_apartment_gameplay.py` no longer expects one.
- `scripts/ue_restore_insanitii_apartment_psychosis_stack.py` now restores the apartment psychosis event director, post-process controller, and audio feedback director without moving designer-staged station props.

Live PIE psychosis probe:

- Forced `AInsanitiiApartmentPropChaosDirector::ForcePropChaos(0)` in PIE.
- Prop chaos summary: `ApartmentPropChaos Active | Props 29 | Variation 0 | 2.0s`.
- Orbit sample average distance around the player: about `257 cm`, confirming props encircle the player rather than bouncing from their original positions.
- Post-process summary: `EventVisual ApartmentPropChaos`, FOV about `107.2`, focus about `283`, event focus warp `0.69`, event FOV multiplier `1.47`, event contrast `0.23`, event vignette `0.13`.
- Audio summary: pressure reached `Psychosis`, active line `Leave the task. Go now.`, false cue `Skip the groceries. The shelves are watching.`, psychosis start cue assigned, and four psychosis variants available.

## Scripts Added

- `scripts/generate_insanitii_apartment_audio.py`
- `scripts/generate_elevenlabs_insanitii_apartment_audio.py`
- `scripts/ue_import_insanitii_apartment_audio.py`
- `scripts/ue_stage_insanitii_apartment_gameplay.py`
- `scripts/ue_verify_insanitii_apartment_gameplay.py`

## Next Notes

- The imported apartment audio now comes from ElevenLabs. Keep the local generated-audio script only as an offline fallback.
- The bed is blockout geometry for interaction staging. Replace with a finished or Tripo-generated bed prop later.
- In PIE, use `H` to switch between minimal HUD and dense debug HUD.
