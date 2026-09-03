# Phase 3 Variable Psychosis Events - 2026-06-22

## Summary

Psychosis events now have a wider variable event set and a stronger apartment prop-chaos presentation.

Implemented event outcomes:

- Chase
- Hallucination Surge
- World Shift
- Apartment Prop Chaos
- Imaginary Friend
- Psychedelic Dimension

The first psychedelic dimension map is:

- `/Game/Insanitii/Maps/Lvl_PsychedelicDimension_PrismApartment`

## Flying Prop Tuning

`AInsanitiiApartmentPropChaosDirector` now adds:

- Random per-prop scale pulsing while selected props orbit the player.
- Axis-warped scale variation so props feel visually unstable while rotating.
- Whole-room ground-bounce behavior for non-orbit props instead of small local trembles.
- New tuning knobs:
  - `OrbitScalePulseStrength`
  - `GroundBounceRoomRadius`
  - `GroundBounceHeight`

Runtime defaults:

- `OrbitScalePulseStrength = 0.42`
- `GroundBounceRoomRadius = 1120.0`
- `GroundBounceHeight = 82.0`

The goal is for the room to feel like ordinary props have become self-important and threatening: some orbit the player, while others bounce/skitter around the whole apartment.

Follow-up correction after playtest:

- Prop chaos no longer starts just because `UInsanitiiMentalStateComponent::bIsInPsychosisEvent` is true.
- `AInsanitiiApartmentPropChaosDirector` now checks the active `AInsanitiiPsychosisEventDirector`.
- If a named psychosis event is active, props only fly when the event type is `ApartmentPropChaos`.
- Imaginary Friend, Psychedelic Dimension, Chase, Hallucination Surge, and World Shift now block prop-chaos startup.
- The old low-mental-state fallback is disabled whenever a named psychosis event director exists, so prop chaos cannot preempt the central random event system.

## Imaginary Friend Event

`EInsanitiiPsychosisEventType` now includes `ImaginaryFriend`.

`AInsanitiiPsychosisEventDirector` can start it through:

- `StartImaginaryFriendForDebug()`

The event spawns an `AInsanitiiPsychosisChaser` in a special imaginary-friend mode:

- Follows near the player instead of chasing aggressively.
- Stays reality-testable as an imagined presence.
- Applies low ongoing mental-state pressure.
- Shows strange recurring HUD lines.
- Plays a quiet psychosis-stress accent when it speaks.

Current imaginary friend lines:

- `You left the morning folded under the table.`
- `Everyone can hear the wallpaper thinking.`
- `Stay ordinary. That is how they lose you.`
- `The cup remembers what you said yesterday.`
- `I am helping. Do not ask why I know that.`

## Psychedelic Dimension Event

`EInsanitiiPsychosisEventType` now includes `PsychedelicDimension`.

`AInsanitiiPsychosisEventDirector` can start it through:

- `StartPsychedelicDimensionForDebug()`

The director owns a data-driven map list:

- `PsychedelicDimensionMapNames`

Default entry:

- `/Game/Insanitii/Maps/Lvl_PsychedelicDimension_PrismApartment`

When this event starts, the player is transported with `UGameplayStatics::OpenLevel` to a randomly selected map from that list.

Follow-up correction after playtest:

- `OpenPsychedelicDimension()` now converts `/Game/...` package paths to the short level name before calling `OpenLevel`.
- Random psychosis selection now uses an explicit event pool, with Psychedelic Dimension appearing twice in the pool to make it more likely during playtests.
- `scripts/ue_restore_insanitii_apartment_psychosis_stack.py` and `scripts/ue_stage_insanitii_apartment_gameplay.py` now force the placed apartment psychosis director's `PsychedelicDimensionMapNames` to include `/Game/Insanitii/Maps/Lvl_PsychedelicDimension_PrismApartment`.

Second follow-up correction after playtest:

- `bForceFirstRandomEventToPsychedelicDimension` was added and defaults to `true` for the playable-slice tuning pass.
- `PsychedelicDimensionCadence` was added and defaults to `3`; if the dimension event has not happened recently, random psychosis selection forces it by cadence.
- `RandomPsychosisEventsStarted`, `RandomEventsSinceLastPsychedelicDimension`, and `LastPsychedelicDimensionTravelTarget` are now exposed in debug summaries.
- The placed apartment director is explicitly configured with:
  - `PsychedelicDimensionMapNames = ["/Game/Insanitii/Maps/Lvl_PsychedelicDimension_PrismApartment"]`
  - `bForceFirstRandomEventToPsychedelicDimension = true`
  - `PsychedelicDimensionCadence = 3`
- The Unreal Python property name for the bool is `force_first_random_event_to_psychedelic_dimension`; the restore/stage scripts were corrected after the first verifier caught the naming mismatch.
- `OpenPsychedelicDimension()` now sends the configured long package path directly to `UGameplayStatics::OpenLevel`, records the target in debug state, logs `Insanitii psychedelic dimension travel requested: ...`, and flashes the HUD line `The apartment gives way.` before travel.

## Prism Apartment Map

Created by:

- `scripts/ue_create_insanitii_psychedelic_dimension.py`

Concept:

- Prism Apartment is a recognizable apartment echo where room logic has broken.
- It uses impossible wall fragments, memory columns, false-star orbs, colored pressure lights, a global post-process volume, and the native Insanitii post-process/audio/psychosis directors.
- The first line of readable world text is `this is still the apartment`, keeping the event tied to reality-testing rather than pure fantasy.

Created actors:

- `PSY_Prism_Floor_ImpossibleSquare`
- `PSY_ApartmentWall_Fragment_00` through `PSY_ApartmentWall_Fragment_07`
- `PSY_MemoryColumn_00` through `PSY_MemoryColumn_09`
- `PSY_FalseStar_Orb_00` through `PSY_FalseStar_Orb_11`
- `PSY_Prism_Light_00` through `PSY_Prism_Light_04`
- `PSY_KeyLight_SkewedMorning`
- `PSY_SkyLight_InternalWeather`
- `PSY_Global_PostProcess_BreathingColor`
- `PSY_Anchor_Text_ReturnToOrdinary`
- `PlayerStart`
- `INS_PostProcessController`
- `INS_AudioFeedbackDirector`
- `INS_PsychosisEventDirector`

## Future Psychedelic Worlds

Candidate worlds to add to `PsychedelicDimensionMapNames` later:

- Endless Grocery Aisle: shelves repeat forever, labels whisper contradictions, ordinary items become objective decoys.
- Laundry Cathedral: washer doors become circular portals, clothing piles form human silhouettes, spin-cycle rhythm drives camera pulse.
- Static Commute: a road or hallway loops back on itself, traffic/noise compresses time, signs argue with the HUD objective marker.
- Apartment Afterimage: the real apartment duplicated into offset ghost layers; only one layer contains real interactables.

## Verification

Build:

- `Build.bat InsanitiiEditor Win64 Development ... -NoHotReload`
- Result: succeeded.

Map creation:

- `UnrealEditor-Cmd.exe ... -run=pythonscript -script=scripts/ue_create_insanitii_psychedelic_dimension.py`
- Result: succeeded.

Receipt:

- `Saved/Automation/insanitii_psychedelic_dimension_receipt.json`
  - `success: true`
  - `map: /Game/Insanitii/Maps/Lvl_PsychedelicDimension_PrismApartment`
  - `spawned_count: 44`

Non-mutating editor probe:

- `dimension_maps` includes `/Game/Insanitii/Maps/Lvl_PsychedelicDimension_PrismApartment`
- `has_start_imaginary_friend: true`
- `has_start_dimension: true`
- `enum_loaded: true`
- `prop_scale_pulse: 0.42`
- `ground_bounce_room_radius: 1120.0`
- `has_friend_mode: true`
- `friend_line_count: 5`
- `psy_map_actor_count: 44`
- `psy_has_required: true`

Follow-up build/readback after playtest correction:

- Build: succeeded.
- Apartment psychosis stack restore commandlet: succeeded.
- Bridge ping: succeeded with the editor relaunched on `Lvl_PlayerApartment`.
- Placed `INS_PsychosisEventDirector` readback:
  - `dimension_maps: ["/Game/Insanitii/Maps/Lvl_PsychedelicDimension_PrismApartment"]`
  - `has_start_prop_debug: true`
  - `has_start_friend_debug: true`
  - `has_start_dimension_debug: true`
  - Coverage summary now includes `ApartmentPropChaos`.
- Placed `INS_ApartmentPropChaosDirector` readback:
  - `prop_scale_pulse: 0.42`
  - `ground_bounce_room_radius: 1120.0`

Second dimension-event verifier:

- Build: succeeded.
- Restore commandlet: succeeded.
- `scripts/ue_verify_insanitii_dimension_event_config.py`: succeeded.
- Receipt: `Saved/Automation/insanitii_dimension_event_config_receipt.json`
  - `success: true`
  - `dimension_map_exists: true`
  - `dimension_maps: ["/Game/Insanitii/Maps/Lvl_PsychedelicDimension_PrismApartment"]`
  - `force_first_dimension: true`
  - `dimension_cadence: 3`
  - Coverage summary includes `PsychedelicDimension`, `Random`, `SinceDimension`, and `Travel`.

Note: the available bridge in this editor session did not expose the old `launch_pie` / `stop_pie` command names, so this pass used build verification, commandlet map creation, bridge ping, and non-mutating reflected editor readback instead of a full automated PIE run.
