# Phase 3 Route Wayfinding

Date: 2026-06-02

## Purpose

After the Day 1 slice was spread around the arena, the play space had more breathing room but needed stronger route readability. This pass added prototype wayfinding so the player can see the intended daily loop from home through ordinary errands, stress, recovery, and sleep.

## Implementation

Added `scripts/place_insanitii_route_guidance.py`.

The script places and saves:

- 8 route floor segments connecting the daily zones.
- 8 arrow text actors pointing toward the next destination.
- 9 numbered zone markers.
- 9 colored point-light beacons.

Route order:

```text
1 HOME -> 2 GROCERY -> 3 LAUNDRY -> 4 DELIVERY -> 5 COMMUTE -> 6 WORK -> 7 NOISE -> 8 GROUND -> 9 SLEEP
```

All route actors are tagged with:

- `InsanitiiWorldReactive`
- `InsanitiiRouteGuide`

This lets the world-reactive director include the guidance layer in psychosis/world-warp effects instead of leaving it static.

## Live Placement Result

Route placement script:

- Success: `true`
- Created actors: `34`
- Route segments: `8`
- Route markers: `9`
- Beacons: `9`
- Missing labels: none
- Saved current level: `true`

## Verification

World reactivity report after route placement:

- Status: pass
- Reactive actor count: `92`
- Tracked actor count: `92`
- Debug summary: `Reactive actors: 92 | Scale 1.00 | Intensity 0.00 | Tag InsanitiiWorldReactive`

Phase 3 PIE runtime report after route placement:

- Status: pass
- Controller: `BP_InsanitiiTemplatePlayerController_C`
- Pawn: `BP_FirstPersonCharacter_C`
- HUD: `InsanitiiHUD`
- Station count: `11`
- Scripted exercise steps: `9`
- Exercise errors: `0`
- Psychosis event fired: `HallucinationSurge`
- Objective completion: `1.0`
- World reactivity tracked count: `92`
- PIE stopped cleanly: `true`
- Blocking dialogs: `0`

## Manual Check

Walk the route in Play mode and confirm:

1. The route markers are visible from normal player height.
2. The route segments do not block movement.
3. Zone order is readable without relying only on HUD text.
4. Psychosis world-warp movement affects route guides without making the path unreadable.
