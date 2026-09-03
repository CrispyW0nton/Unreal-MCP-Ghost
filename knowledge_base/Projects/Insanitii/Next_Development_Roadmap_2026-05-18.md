# Insanitii Next Development Roadmap - 2026-05-18

## Roadmap Basis

This roadmap integrates:

- the user-provided GDD v1.0,
- current Insanitii KB status,
- the best-fit C++ plus Blueprint-wrapper architecture decision,
- current UnrealMCP plugin/build limitations.

## Current State

- Unreal project: `C:\Users\NewAdmin\Documents\KaiGenInteractive\Insanitii\Insanitii`
- UnrealMCP bridge target: `127.0.0.1:55655`
- Plugin source sync: complete as of `Plugin_Sync_2026-05-18.md`
- Hard command-line plugin/project rebuild: blocked while Live Coding is active
- Phase 1: foundation staged, manual possessed-PIE validation still required
- Phase 2 Slice 1: time, economy, and lifestyle manager implemented and previously smoke-tested

## Development Principle

Build a playable daily-life vertical slice before broadening lifestyle count.

The GDD's four lifestyles stay as product vision, but the first production target is one complete Office Worker loop with the shared systems needed by the other lifestyles.

## Phase 0 - Repo And Tooling Organization

Status: complete for initial setup on 2026-05-18.

Deliverables:

- Global limitation log under `knowledge_base/Limitation log/`.
- Insanitii GDD integration note.
- Updated Insanitii KB index.
- Explicit rule that project work records belong under `knowledge_base/Projects/Insanitii/`.

Exit criteria:

- New planning and limitation documents are discoverable from the KB indexes.
- Active UnrealMCP limitations have task-list entries.

## Phase 1 Gate - Stabilize Foundation Before Feature Expansion

Goal: prove the existing foundation works in real possessed PIE, not just static editor or Simulate-in-Editor checks.

Tasks:

1. Close or reload Unreal so native plugin routes/classes are current.
2. Run a clean `InsanitiiEditor` build.
3. Run `insanitii_phase1_readiness_report()`.
4. Run `insanitii_phase2_lifestyle_report()`.
5. Manual possessed-PIE checklist:
   - WASD movement works.
   - Mouse look works.
   - Focus works on `F`.
   - Breathe works on `Tab`.
   - Interact works on `E`.
   - Debug decrease/increase works on `-` and `=`.
   - HUD toggle works on `H`.
   - Test interactables mutate mental state.
   - Post-process/HUD reacts to state changes.
6. Audit and collapse any remaining duplicate input authority paths.

Exit criteria:

- Native build succeeds.
- Readiness reports are pass or documented warn with safe workaround.
- Manual PIE proves movement/look and all six mechanics inputs.
- Any tool limitation discovered is logged.

## Phase 2A - Daily Loop Surface

Goal: make the existing time/economy/lifestyle manager visible and interactive.

Status: in progress. HUD data surface started in `Phase2A_HUD_Daily_Loop_Surface_2026-05-18.md`; native daily task execution, sleep advance actions, and temporary debug controls are recorded in `Phase2A_Daily_Actions_2026-05-18.md`.

Tasks:

1. Add player-facing/debug HUD fields for: `(started)`
   - day,
   - time,
   - current lifestyle,
   - cash,
   - daily living cost,
   - current task options.
2. Add Home Base placeholder actors:
   - bed/sleep interaction,
   - food/eat interaction,
   - medication interaction,
   - front door/work transition marker.
3. Wire sleep/day advance: `(native API compiled; interaction actor pending)`
   - advances to next morning,
   - applies living cost exactly once,
   - updates HUD and ledger.
4. Add a first task execution interaction: `(native API and debug keys compiled; world interaction pending)`
   - picks one generated task,
   - calls `EvaluateTaskOutcome`,
   - applies money, skill/reputation, and mental-state pressure.

Exit criteria:

- A player can complete a minimal morning -> task -> evening/night -> next day loop.
- Time and money are visible without reading logs.
- Ledger entries can be inspected through debug/MCP.

## Phase 2B - Persistence Skeleton

Goal: avoid building loops that cannot survive a session boundary.

Tasks:

1. Add native SaveGame data structures for:
   - day/time,
   - cash,
   - current lifestyle,
   - lifestyle skill/reputation,
   - mental-state baseline,
   - task seed/history.
2. Add save/load commands or debug actions.
3. Add MCP smoke probe for save/load facts.

Exit criteria:

- Save, reload, and inspect restore the daily loop state.
- Failure to save/load is visible in HUD or debug output.

## Phase 3 - Office Worker Vertical Slice

Goal: build the first complete lifestyle path from the GDD.

Tasks:

1. Implement Office task schema and data assets.
2. Build one playable task first: Email Triage or Data Entry.
3. Add office placeholder environment/hub.
4. Add task success/failure scoring.
5. Route outcomes into:
   - cash,
   - skill/reputation,
   - mental state,
   - consecutive success/failure counters.
6. Add first promotion/progress meter.

Exit criteria:

- One in-game workday can be completed from home start to night save.
- At least one Office task is replayable with variable difficulty or generated details.
- Failures cascade visibly but remain recoverable.

## Phase 4 - Sensory Experience Layer V1

Goal: make mental state felt, not just displayed.

Tasks:

1. Replace placeholder `M_PsychosisPostProcess` with a real parameterized material or native PP stack.
2. Map psychosis intensity to visual parameters with smoothing.
3. Focus smoothly suppresses distortion.
4. Breathe has audiovisual confirmation.
5. Add first placeholder hallucination audio events.

Exit criteria:

- State changes are legible without opening the debug HUD.
- Focus and Breathe have distinct player-facing feedback.

## Phase 5 - Early Access Prototype Gate

Goal: produce a credible first public prototype path.

Tasks:

1. Add main menu and pause menu.
2. Add settings with accessibility controls for distortion intensity.
3. Add tutorialized Day 1.
4. Package a Windows build.
5. Begin mental health/lived-experience review.

Exit criteria:

- A new player can start, learn, complete a short Office loop, save, quit, reload, and continue.
- Content warnings are present.
- No known stubs are presented as finished systems.

## Toolchain Improvement Policy

Improve Unreal-MCP-Ghost when:

- a missing command blocks repeated Insanitii work,
- a workaround is risky or slow,
- a smoke report cannot prove a required exit criterion,
- plugin/server state diverges from the running editor without clear feedback.

Every such issue starts in `knowledge_base/Limitation log/ACTIVE_LIMITATIONS.md`.
