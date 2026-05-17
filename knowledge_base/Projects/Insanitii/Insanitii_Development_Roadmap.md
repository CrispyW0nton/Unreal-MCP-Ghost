# Insanitii In-Depth Development Roadmap

Last updated: 2026-05-17

## Mission

Build a reliable, mechanics-first psychological FPS foundation in Unreal Engine 5.6 using a native C++ logic + Blueprint wrapper architecture, then scale into lifestyle loops, encounters, content, and optimization without breaking core feel.

## Strategic Principles

1. Single gameplay authority path per system (especially input and mental-state mutation).
2. Event-driven Blueprint logic over Tick-heavy logic.
3. Data-driven tuning for all player-facing values.
4. Visible runtime diagnostics before feature expansion.
5. "Playable slice first, complexity second" delivery cadence.

## Current Baseline (Start Point)

- Enhanced input action assets exist for the six core actions.
- Phase 1 core systems currently live in native C++ classes with Blueprint wrappers under `/Game/Insanitii/...`.
- The open project should be treated as the active Unreal-MCP-Ghost smoke target while MCP coverage expands.
- Knowledge base now contains synthesis, implementation logs, smoke reports, and repair notes for the current hybrid architecture.

## MCP Smoke-Test Contract

Every Unreal-MCP-Ghost development pass that touches project verification should try to validate against Insanitii with read-only tools first:

1. `ping_unreal` confirms the bridge is responsive.
2. `get_actor_identity(actor_name_or_label="INS_")` confirms the placed Insanitii actors, labels, full paths, and generated classes.
3. `find_actors_by_class(class_name="BP_TestInteractable")` confirms the five placed test interactables; after the native plugin reloads, `find_actors_by_class(class_name="InsanitiiTestInteractable")` should also work through the native parent-class chain.
4. `check_blueprint_generated_class("BP_RuntimeBootstrap")` confirms Blueprint wrappers have valid generated classes.
5. `inspect_input_mapping_context("/Game/Input/IMC_Default")` confirms the Enhanced Input mappings for Focus, Breathe, Interact, debug state controls, and HUD toggle. The older `/Game/FirstPerson/Input/IMC_Default` path should be treated as stale for the current Insanitii project.
6. `editor_list_blocking_dialogs()` should run before and after long asset operations. If Unreal opens a blocking prompt, use `editor_dismiss_blocking_dialog(button_text="Yes"|"OK"|"Replace"|"Cancel", title_contains="...")` only with an explicit button choice.
7. `insanitii_phase1_readiness_report()` should be run at the start of each development pass. It bundles the checks above, uses read-only `exec_python` fallbacks when the active editor has not reloaded new native MCP routes, and returns the manual PIE checklist that still requires human validation.

## Roadmap Structure

## Phase 0 - Stabilization and Architecture Lock (1-2 sessions)

### Goals

- Remove ambiguity from architecture and freeze rules for implementation.
- Ensure every contributor follows the same Blueprint standards.

### Deliverables

- Finalized canonical variable model on `BP_FirstPersonCharacter`.
- Finalized naming conventions for functions/macros/events.
- Explicit "single input authority" sign-off.

### Exit Criteria

- No duplicate mechanics input paths remain active.
- All six `IA_*` events route into dedicated handler functions.

## Phase 1 - Core Mechanics Loop (2-4 sessions)

### Goals

- Turn all six actions into real gameplay logic.
- Establish stable mental-state loop and interaction loop.

### Workstreams

#### 1) Input and action handlers

- Implement:
  - `Handle_FocusInput`
  - `Handle_BreatheInput`
  - `Handle_InteractInput`
  - `Handle_DebugDecreaseMentalState`
  - `Handle_DebugIncreaseMentalState`
  - `Handle_ToggleHUDInput`

#### 2) Mental-state runtime model

- Implement canonical APIs:
  - `AddMentalStateDelta`
  - `SetMentalState`
  - `ClampMentalState`
  - `RecomputePsychosisIntensity`

#### 3) Interaction pipeline

- Implement camera-forward trace resolver.
- Validate `BPI_Interactable` contract usage for all interaction targets.

#### 4) Debug observability

- Expand debug HUD to include:
  - `MentalState`
  - `PsychosisIntensity`
  - focus/breathe states
  - current interaction target
  - last action fired

### Exit Criteria

- All six actions affect game state, not just print output.
- Mental state remains bounded and deterministic.
- Interaction works on placed test actors.
- HUD toggle and diagnostics behave correctly in PIE.

## Phase 2 - Sensory Experience Layer (2-4 sessions)

### Goals

- Convert mechanics state into player-perceived feedback.
- Build first-pass "Insanitii feel" through visuals/audio.

### Workstreams

#### 1) Visual distortion

- Map `PsychosisIntensity` to post-process parameters.
- Add interpolation/smoothing function for non-jarring transitions.

#### 2) Focus and breathe feel

- Focus: temporary clarity/accuracy modulation.
- Breathe: de-escalation burst with cooldown and UI confirmation.

#### 3) Audio feedback framework

- Define event hooks from state changes (focus start/end, breathe, threshold crossing).
- Use placeholder cues first; defer final content assets.

### Exit Criteria

- State changes are clearly felt without relying on debug text.
- Visuals and audio stay synchronized with state transitions.

## Phase 3 - Gameplay Slice and Scenario Scaffolding (3-6 sessions)

### Goals

- Build one full playable loop with objective pressure and recoverability.

### Workstreams

#### 1) Scenario blueprinting

- Implement 1-2 objective loops using placeholder geometry.
- Integrate interaction dependencies and state pressure moments.

#### 2) Encounter pacing

- Introduce timed disturbances tied to mental-state thresholds.
- Add safe zones or recovery windows for loop balance.

#### 3) UI progression layer

- Add objective state, warning cues, and failure/recovery messaging.

### Exit Criteria

- One complete scenario is playable from start to finish.
- Failure and recovery states are both testable and understandable.

## Phase 4 - Systems Hardening and Content Integration (ongoing)

### Goals

- Prepare mechanics foundation for broader production.

### Workstreams

- Refactor shared Blueprint functions into reusable components/libs where stable.
- Replace placeholders with production assets incrementally.
- Profile and eliminate heavy graph hotspots.
- Introduce selective native migration only where profiling proves need.

### Exit Criteria

- Stable 30+ minute play sessions without major logic regressions.
- Performance and readability acceptable for team scaling.

## Phase 5 - Vertical Slice and Pre-Production Gate

### Goals

- Package a polished vertical slice demonstrating core Insanitii identity.

### Deliverables

- Stable first-person mechanics loop with psychosis systems.
- Cohesive sensory feedback and interaction reliability.
- Internal QA checklist pass.

### Exit Criteria

- Slice is demo-ready and repeatable.
- Clear backlog exists for full production expansion.

## Cross-Phase Backlog Themes

1. Data assets for tuning (mental-state curves, cooldown profiles, visual intensity maps).
2. Interaction taxonomy (`Inspect`, `Use`, `Collect`, `Stabilize`).
3. Objective framework and event sequencing.
4. AI pressure systems (future BT/EQS integration once core loop stable).
5. Save/load and session persistence design.

## Technical Governance (Must Always Hold)

1. No hidden gameplay mutations outside canonical state APIs.
2. No parallel input systems when Enhanced Input path is active.
3. Every feature includes a debug signal and a player-facing signal.
4. Compile success is not completion; PIE behavior validation is required.
5. Every roadmap milestone updates the Insanitii knowledge base docs.

## Execution Cadence

- Per session:
  1) read current Insanitii KB docs,
  2) implement one bounded milestone,
  3) run PIE validation checklist,
  4) update status/log docs with factual outcomes.

- Per week:
  - one stabilization pass,
  - one feature pass,
  - one QA and cleanup pass.

## Immediate Next Milestone

Finish Phase 1 validation, then begin Phase 2 Lifestyle Framework:

- Run the manual PIE checklist for WASD, mouse look, F Focus, Tab Breathe, E interactions, debug +/- state changes, HUD toggle, post-process response, and cascade behavior.
- Run `insanitii_phase1_readiness_report()` before and after plugin changes. Current live result on 2026-05-17 is `warn`: all static readiness checks pass, but the editor is still using fallback probes because the latest native smoke routes need Live Coding reload or editor restart.
- Once Phase 1 manual validation passes, implement the Phase 2 time-of-day, money/economy, lifestyle base, home hub, transition framework, and save/load skeleton.
- Keep all new docs and smoke reports in `knowledge_base/Projects/Insanitii/`.
