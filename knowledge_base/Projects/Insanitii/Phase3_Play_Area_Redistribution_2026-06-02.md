# Phase 3 Play Area Redistribution

Date: 2026-06-02

## Purpose

The Day 1 slice was mechanically functional, but the prototype stations and set dressing were visually cramped into a narrow lane. This pass redistributed the playable beats around the available arena so the route reads as distinct daily spaces instead of a stacked checklist.

## Layout Direction

The new route uses both X and Y space:

| Zone | Center |
| --- | --- |
| Home / morning self-care | `(-900, 650, 72)` |
| Grocery | `(-150, 1000, 72)` |
| Laundry | `(760, 940, 72)` |
| Package delivery | `(-950, -100, 72)` |
| Commute road | `(-100, -560, 72)` |
| Work | `(900, -220, 72)` |
| Stress / noise | `(1210, 360, 72)` |
| Grounding pocket | `(980, -760, 74)` |

`PlayerStart` was moved to the home zone at `(-1180, 610, 92)` so the first view starts in the morning/self-care space.

## Source-of-Truth Fix

The first layout move looked correct in the editor, then reverted because older placement specs still contained the original single-lane coordinates around `X=420`.

Updated source files:

- `scripts/redistribute_insanitii_day1_layout.py`: new reusable layout redistribution pass.
- `unreal_mcp_server/tools/editor_tools.py`: ordinary errand station specs and Day 1 set-dressing specs now use the spread layout.
- `scripts/place_insanitii_grounding_pocket.py`: grounding pocket placement now uses the south-east recovery space instead of the old near-stress location.

Validation search:

```text
rg -n "420\.0, (660|820|-340|-520|20|-160|330)|245\.0, (180|340|500|20)|255\.0, 660|645\.0, 660|260\.0, 820|640\.0, 820|250\.0, -160|650\.0, -160" scripts unreal_mcp_server\tools\editor_tools.py
```

Result: no matches in the placement source files.

## Live Verification

Redistribution script:

- Success: `true`
- Updated actors: `60`
- Missing labels: none
- Saved current level: `true`

World reactivity report after redistribution:

- Status: pass
- Reactive actors: `58`
- Tracked actors: `58`
- Debug summary: `Reactive actors: 58 | Scale 1.00 | Intensity 0.00 | Tag InsanitiiWorldReactive`

Phase 3 PIE runtime report after redistribution and source patch:

- Status: pass
- Station count: `11`
- Scripted exercise steps: `9`
- Exercise errors: `0`
- Psychosis event fired: `HallucinationSurge`
- Objective completion: `1.0`
- World reactivity tracked count: `58`
- PIE stopped cleanly: `true`
- Blocking dialogs: `0`

Audio feedback report after redistribution:

- Status: pass
- `INS_AudioFeedbackDirector` present
- SoundWave asset count: `5`
- Assigned slot count: `5`

## Remaining Manual Check

Walk the route in Play mode and confirm the spread feels better at human scale:

1. Start at home and complete food/medication.
2. Move through grocery and laundry as separate north-side spaces.
3. Cross to package delivery, commute, and work.
4. Trigger stress/noise and verify the psychosis beat still has room to breathe.
5. Use the grounding pocket as a separate recovery area before returning to sleep.
