# Phase 3: Station Foley Overrides

Date: 2026-06-04

## Intent

Move the playable slice closer to the requirement that every ordinary task has accompanying sound.

Before this pass, `AInsanitiiTaskStation` already played localized one-shots, but all `INS_TaskStation_*` actors left `StationUseSound` and `StationSlipSound` empty and relied on generic fallback routing. That proved the sound path but made different tasks feel too similar.

## ElevenLabs Status

Chrome DevTools could see two signed-in ElevenLabs Sound Effects history tabs for the user-approved account.

The signed-in history page showed the existing station Foley prompt:

`Insanitii ordinary task station Foley layer, 8 seconds, dry close-mic everyday actions: bread bag rustle, pill bottle rattle, water glass set down, grocery scanner beep, laundry washer door clunk, cardboard package thud, keyboard taps, car door click, calm room tone, no music, no speech, no crowd.`

The station Foley entry exposes four 1.0 second variants, but its download controls were disabled in the card DOM during this pass. The preferred Chrome extension control path also failed again with the Windows sandbox refresh issue, so no new ElevenLabs station WAV was successfully downloaded.

## Implemented Fallback

Added helper:

`scripts/import_insanitii_station_foley.py`

The helper generates provisional 48 kHz mono WAV cues under:

`generated_audio/insanitii_station_foley/`

It imports them into Unreal as SoundWave assets under:

`/Game/Insanitii/Audio/Generated/StationFoley`

Imported/generated assets:

- `INS_Foley_Sandwich`
- `INS_Foley_Medication`
- `INS_Foley_Sleep`
- `INS_Foley_Grocery`
- `INS_Foley_Laundry`
- `INS_Foley_Package`
- `INS_Foley_Commute`
- `INS_Foley_Work`
- `INS_Foley_Stress`
- `INS_Foley_Grounding_Card`
- `INS_Foley_Grounding_Snack`
- `INS_Foley_Task_Slip`

The sounds are simple synthesized placeholders, but each task now has a distinct audible identity: sandwich rustle/clicks, medication rattles, sleep bed tone, grocery beep, laundry rumble, package thud, commute click/engine, work typing, stress tone/noise, grounding card/snack, and a separate task-slip cue.

## Station Wiring

The helper assigned `StationUseSound` on all 11 task stations:

- `INS_TaskStation_Food_Sandwich` -> `INS_Foley_Sandwich`
- `INS_TaskStation_Medication` -> `INS_Foley_Medication`
- `INS_TaskStation_Sleep_Bed` -> `INS_Foley_Sleep`
- `INS_TaskStation_Grocery_Corner` -> `INS_Foley_Grocery`
- `INS_TaskStation_Laundry_Washer` -> `INS_Foley_Laundry`
- `INS_TaskStation_Package_Dropoff` -> `INS_Foley_Package`
- `INS_TaskStation_Commute_Car` -> `INS_Foley_Commute`
- `INS_TaskStation_Work_EmailTriage` -> `INS_Foley_Work`
- `INS_TaskStation_Stress_OverwhelmingNoise` -> `INS_Foley_Stress`
- `INS_TaskStation_Grounding_Card` -> `INS_Foley_Grounding_Card`
- `INS_TaskStation_Grounding_Snack` -> `INS_Foley_Grounding_Snack`

Every station also uses `INS_Foley_Task_Slip` for `StationSlipSound`.

The helper set station volume to `0.72`, then saved the current level and dirty packages.

## Tooling Update

Updated:

`scripts/probe_insanitii_station_audio.py`

The probe now verifies:

- the original generated fallback SoundWaves still exist;
- all 12 StationFoley SoundWave assets exist;
- every task station has a non-empty `StationUseSound`;
- every task station has a non-empty `StationSlipSound`.

## Verification

Passed:

- `python scripts\import_insanitii_station_foley.py`
  - generated 12 WAVs;
  - imported 12 SoundWave assets;
  - assigned all 11 stations;
  - `saved_current_level: true`;
  - `saved_dirty_packages: true`.
- `python scripts\probe_insanitii_station_audio.py`
  - all fallback assets exist;
  - all StationFoley assets exist;
  - all stations have use/slip override sounds assigned.
- `python scripts\probe_insanitii_tripo_station_readiness.py`
  - all stations still use direct Tripo meshes and remain interactable.
- `python scripts\report_insanitii_layout_positions.py`
  - passed with `max_deviation: 0.0`.
- `python scripts\probe_insanitii_task_station_hud_feedback.py`
  - PIE report passed with 9 task-complete statuses, forced friction-slip HUD/visual feedback, and breathe/focus stabilization feedback.
- `python -m py_compile scripts\import_insanitii_station_foley.py scripts\probe_insanitii_station_audio.py`
  - passed.

## Remaining Audio Work

These StationFoley assets are useful for gameplay validation but should be replaced or layered with dedicated ElevenLabs downloads when the signed-in history entry exposes working download controls.

Next high-value audio pass:

1. Download the station Foley variants from ElevenLabs when available.
2. Import them into `/Game/Insanitii/Audio/ElevenLabs/StationFoley`.
3. Reassign the same `StationUseSound` slots to the ElevenLabs assets.
4. Add separate reality-test success/failure and hallucinated-voice spatialized cues.
