# Phase 2 Lifestyle Framework Slice 1 - 2026-05-17

## Purpose

Begin Insanitii Phase 2 after manual Phase 1 validation by adding the first native lifestyle-loop foundation: time, money, daily tasks, and a placed manager actor that can be inspected by Unreal-MCP-Ghost.

## Implemented In Insanitii

- Added `EInsanitiiDayPeriod`, `EInsanitiiLifestyleType`, `FInsanitiiLifestyleTaskOption`, `FInsanitiiTaskOutcome`, and `FInsanitiiLedgerEntry`.
- Added `UInsanitiiTimeOfDayComponent`.
  - Tracks day and minute-of-day.
  - Advances with `MinutesPerRealSecond`.
  - Broadcasts minute, day, and day-period changes.
  - Supports sleep-to-next-morning.
- Added `UInsanitiiEconomyComponent`.
  - Tracks cash balance, living cost, and a capped ledger.
  - Supports earning, spending, affordability checks, daily living cost, and destitution warning.
- Added `AInsanitiiLifestyleManager`.
  - Owns the time and economy components.
  - Generates three task options for each MVP lifestyle.
  - Evaluates task success/failure into money, skill, reputation, and mental-state pressure.
  - Applies living cost on day rollover.
  - Exposes lifestyle transition checks.
- Created `/Game/Insanitii/Gameplay/Lifestyles/BP_LifestyleManager`.
- Placed `INS_LifestyleManager` in `Lvl_FirstPerson`.

## MCP Tool Added

- `insanitii_phase2_lifestyle_report`

The report checks:

- bridge ping
- native class visibility for the time, economy, and lifestyle manager classes
- `BP_LifestyleManager` generated-class validity
- placed `INS_LifestyleManager`
- generated lifestyle task count
- current cash/time readback
- visible blocking dialogs
- manual PIE checklist for Phase 2 behavior

## Validation

- Full UBT build succeeded while the editor was closed.
- Reopened Insanitii and confirmed the new native classes load:
  - `InsanitiiTimeOfDayComponent`
  - `InsanitiiEconomyComponent`
  - `InsanitiiLifestyleManager`
- Ran `insanitii_phase2_lifestyle_report()` against the live editor.
  - Status: `pass`
  - Native class count: 3
  - Blueprint generated class: true
  - Manager actor placed: true
  - Generated task count: 3
  - Cash balance: 250
  - Time: `Day 1 08:00`
  - Blocking dialogs: 0
- Ran Simulate-in-Editor runtime smoke.
  - PIE world count: 1
  - `INS_LifestyleManager` existed in PIE.
  - Clock advanced from `Day 1 08:00` to `Day 1 08:13` after a short simulation.
  - Cash remained `$250`.
  - PIE stop request succeeded.

## Tooling Limitation Found

New native `UCLASS` files cannot be reliably loaded through Live Coding alone. The safe workflow was:

1. Save dirty packages.
2. Close Unreal Editor and Live Coding.
3. Run `Build.bat InsanitiiEditor Win64 Development`.
4. Reopen the project.
5. Re-run the class visibility probe.

UE Python in this environment also does not expose `unreal.KismetEditorUtilities`, so Blueprint compile/save should use the MCP bridge `compile_blueprint` and `save_blueprint` routes rather than direct UE Python utilities.

## Remaining Phase 2 Work

- Add a player-facing/debug HUD surface for time and money.
- Add a home-base hub placeholder with sleep/day-advance interaction.
- Add lifestyle transition interaction points.
- Add first playable task execution flow that calls `EvaluateTaskOutcome`.
- Add save/load skeleton for time, cash, lifestyle, skill, and reputation.
