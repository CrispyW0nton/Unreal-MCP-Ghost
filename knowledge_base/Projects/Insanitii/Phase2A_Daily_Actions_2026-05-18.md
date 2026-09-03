# Phase 2A Daily Actions - 2026-05-18

## Purpose

Turn the visible Phase 2A daily-loop HUD into a minimally interactive loop: generated tasks can produce outcomes, those outcomes can affect economy and mental state, and sleep can advance the day.

This is still a debug/player-development surface, not the final home-base UI.

## Implemented

Updated external Unreal project source:

- `C:\Users\NewAdmin\Documents\KaiGenInteractive\Insanitii\Insanitii\Source\Insanitii\InsanitiiMentalStateComponent.h`
- `C:\Users\NewAdmin\Documents\KaiGenInteractive\Insanitii\Insanitii\Source\Insanitii\InsanitiiMentalStateComponent.cpp`
- `C:\Users\NewAdmin\Documents\KaiGenInteractive\Insanitii\Insanitii\Source\Insanitii\InsanitiiLifestyleManager.h`
- `C:\Users\NewAdmin\Documents\KaiGenInteractive\Insanitii\Insanitii\Source\Insanitii\InsanitiiLifestyleManager.cpp`
- `C:\Users\NewAdmin\Documents\KaiGenInteractive\Insanitii\Insanitii\Source\Insanitii\InsanitiiHUD.h`
- `C:\Users\NewAdmin\Documents\KaiGenInteractive\Insanitii\Insanitii\Source\Insanitii\InsanitiiHUD.cpp`

Changes:

- Added `UInsanitiiMentalStateComponent::ApplyLifestyleTaskResult`.
  - Applies an explicit mental-state delta.
  - Tracks completed/failed task totals.
  - Updates consecutive success/failure counters based on the actual task result.
  - Emits existing mental-state/cascade delegates.
- Added `AInsanitiiLifestyleManager::ExecuteDailyTaskByIndex`.
  - Regenerates the current task list.
  - Validates task index.
  - Uses `EvaluateTaskOutcome`.
  - Applies optional mental-state impact through `UInsanitiiMentalStateComponent`.
  - Stores last task/outcome for HUD and Blueprint access.
  - Broadcasts `OnDailyTaskExecuted`.
- Added `AInsanitiiLifestyleManager::SleepToNextMorning`.
  - Advances the time component to the next morning.
  - Stores the last advanced day for HUD and Blueprint access.
  - Broadcasts `OnSleepAdvanced`.
  - Daily living cost is still handled by the existing `OnDayStarted` economy hook.
- Expanded native HUD output.
  - Displays last task result, money delta, and mental-state delta.
  - Displays last sleep/day advance.
- Added temporary native debug controls:
  - `1`, `2`, `3`: succeed generated task option 1-3.
  - `Shift+1`, `Shift+2`, `Shift+3`: fail generated task option 1-3.
  - `N`: sleep to next morning.

## Validation

Live Coding compile after the daily-action implementation:

- Result: succeeded.
- Remaining warning: `UImage::SetBrushSize` deprecation in the UnrealMCP plugin UMG command path.
- This warning is already tracked as `LIM-0006`.

Live editor probe before a clean editor restart:

```text
Manager count: 1
Initial summary: Office Worker | Day 1 08:00 | Cash $250 | Skill 0.10 | Rep 0.00
Initial tasks: Email Triage, Data Entry Sprint, Client Meeting
```

The running editor did not expose the newly-added `ExecuteDailyTaskByIndex` or `SleepToNextMorning` functions through UE Python reflection after Live Coding:

```text
AttributeError: 'InsanitiiLifestyleManager' object has no attribute 'execute_daily_task_by_index'
AttributeError: 'InsanitiiLifestyleManager' object has no attribute 'sleep_to_next_morning'
```

This matches `LIM-0001`: new reflected native API on already-loaded classes often requires a clean editor restart and command-line rebuild before Blueprint/Python reflection sees it.

Live Coding compile after adding C++ HUD debug controls:

- Result: succeeded.
- Same plugin deprecation warning only.

## Not Yet Verified

- Manual possessed-PIE use of `1`/`2`/`3`, `Shift+1`/`Shift+2`/`Shift+3`, and `N`.
- Whether HUD text remains readable after several task and sleep actions.
- A clean closed-editor `Build.bat InsanitiiEditor Win64 Development` pass.
- Post-restart Blueprint/Python reflection visibility for the new `UFUNCTION`s.

## Production Read

This pass gives the project an immediate playable debug path for:

```text
Morning visible state -> task outcome -> cash/mental-state update -> sleep -> next day/living cost
```

The next production layer should replace direct debug keys with actual home-base/work interaction actors while keeping these debug controls available until the first Office Worker task UI exists.

## Suggested Next Steps

1. Clean restart Unreal Editor, run a full command-line build, then re-run the reflection probe.
2. Manually possess PIE and verify the temporary controls:
   - task success raises/lowers cash and updates last-outcome HUD text,
   - task failure applies the failure branch and mental-state pressure,
   - sleep advances day and applies living cost once.
3. Add home-base placeholder interactables:
   - bed calls `SleepToNextMorning`,
   - work desk/front door calls the first generated task,
   - medication/food actors become explicit economy plus mental-state actions.
4. Start Phase 2B save/load skeleton once the day loop is manually proven.
