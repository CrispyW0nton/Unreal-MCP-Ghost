# Phase 3 Player Apartment Concept Lighting - 2026-06-24

## Summary

Updated `/Game/Insanitii/Maps/Lvl_PlayerApartment` lighting to better match the provided apartment concept image: warmer, dimmer, more lived-in, and less like a bright test render.

The pass keeps gameplay readability while moving the room toward:

- Low ambient fill instead of flat white room light.
- Warm directional/key light.
- Soft warm window glow.
- Warm ceiling practical.
- Amber table pool.
- Warm kitchen/counter pool.
- Subdued station/event accent lights.
- Global post-process exposure/vignette tuning.

## Map Changes

Updated base lights:

- `APT_Key_DirectionalLight`
  - Intensity: `0.42`
  - Color: warm amber `255, 198, 134`
- `APT_SkyLight`
  - Intensity: `0.055`
  - Color: low warm-gray fill `106, 92, 78`
- `APT_Apartment_PointLight`
  - Repositioned near room center.
  - Intensity reduced to `155.0`
  - Radius: `440.0`
  - Color: warm practical `255, 190, 120`

Added concept lights:

- `APT_Concept_CeilingPractical_Warm`
  - Soft overhead warm practical.
- `APT_Concept_TablePool_Amber`
  - Amber pool centered around the main table area.
- `APT_Concept_KitchenCounter_Warm`
  - Warm kitchen/cooking area support light.
- `APT_Concept_WindowGlow_Soft`
  - Soft warm spotlight from the window/listen-to-birds side of the apartment toward the table.

Dimmed activity/event accent lights:

- Coffee and tobacco now read warm/amber instead of bright blue.
- Cooking remains warmer and slightly stronger.
- Laundry remains cooler but lower intensity.
- Fold laundry, eat food, and birds stay soft supportive colors.
- Overwhelming noise remains red but is no longer overwhelmingly bright outside psychosis.

Added:

- `APT_ConceptLighting_PostProcess`
  - Unbound post-process volume.
  - Exposure bias tuned darker.
  - Mild vignette, bloom, grain, and warmer white temperature.

## Tooling

Added scripts:

- `scripts/ue_polish_insanitii_apartment_concept_lighting.py`
- `scripts/ue_verify_insanitii_apartment_concept_lighting.py`

Updated script:

- `scripts/ue_verify_insanitii_apartment_gameplay.py`
  - The verifier now accepts the current finished-prop actor labels as valid equivalents for older `APT_*` decorative staging actors.
  - This prevents false negatives when the apartment uses placed finished props such as `SM_HawaiianShirt`, `SM_WoodenPipe`, and `SM_CoffeeTable` instead of duplicated helper actors.

The polish script records the anchor points it used for the table, kitchen, window, and room center. It also writes light readbacks to:

- `Saved/Automation/insanitii_apartment_concept_lighting_receipt.json`

The verification script writes:

- `Saved/Automation/insanitii_apartment_concept_lighting_verification_receipt.json`

## Verification

Commandlet polish:

```text
UnrealEditor-Cmd.exe Insanitii.uproject -ExecutePythonScript=scripts/ue_polish_insanitii_apartment_concept_lighting.py -unattended -nop4 -nosplash
```

Result:

- `success: true`
- `saved_level: true`
- `saved_dirty_packages: true`

Commandlet verification:

```text
UnrealEditor-Cmd.exe Insanitii.uproject -ExecutePythonScript=scripts/ue_verify_insanitii_apartment_concept_lighting.py -unattended -nop4 -nosplash
```

Result:

- `success: true`
- Missing concept lights: none.
- Missing accent lights: none.
- `APT_ConceptLighting_PostProcess` exists.
- Base light and accent intensity checks passed.

Apartment gameplay verification after the lighting pass:

- `scripts/ue_verify_insanitii_apartment_gameplay.py`: succeeded after accepting finished-prop equivalents.
- Missing triggers: none.
- Missing bed actors: none.
- Missing station actors: none.
- Missing audio assets: none.
- Director counts: one each for apartment activity, prop chaos, psychosis event, post-process, and audio feedback.
- Tagged psychosis props: `29`.

Live editor bridge:

- Relaunched editor on `Lvl_PlayerApartment`.
- `scripts/bridge_ping.py`: succeeded with `94` actors in the current level.

Saved map:

- `Content/Insanitii/Maps/Lvl_PlayerApartment.umap`
- Last write after pass: `2026-06-24 17:56:33`

## Notes

Unreal's Python `Color` constructor mapped positional args as `B, G, R, A` in this editor build, so the polish script uses a helper that writes intended RGB values correctly. The first pass caught the channel swap in the receipt before verification, and the corrected pass now records warm RGB values as expected.
