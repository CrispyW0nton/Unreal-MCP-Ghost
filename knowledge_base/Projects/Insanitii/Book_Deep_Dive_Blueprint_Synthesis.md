# Insanitii Book Deep Dive - Blueprint Synthesis

## Purpose

This document captures a deep synthesis of project-relevant guidance from the Insanitii knowledge base and referenced Unreal books, then translates that into actionable architecture guidance for ongoing development.

Current architecture note: this synthesis is no longer a Blueprint-only or Blueprint-first constraint. Treat its Blueprint guidance as graph-quality and iteration guidance inside the current best-fit native C++ plus Blueprint-wrapper architecture.

The goal is practical: avoid repeating prior input/graph instability and move directly into robust, testable gameplay logic.

## Sources Reviewed

### Existing repo knowledge guides

- `docs/knowledge-base/README.md`
- `docs/knowledge-base/unreal-cpp-li-2023.md`
- `docs/knowledge-base/elevating-game-experiences-ue5-2e.md`
- `docs/knowledge-base/game-ai-unreal-sapio-2019.md`
- `knowledge_base/Projects/Insanitii/Phase1_Status.md`
- `knowledge_base/Projects/Insanitii/Phase1_Implementation_Log.md`

### Local book files sampled deeply

- Zhenyu George Li, *Unreal Engine 5 Game Development with C++ Scripting* (Packt, 2023)
- Goncalo Marques et al., *Elevating Game Experiences with Unreal Engine 5* (Packt, 2nd ed.)
- Marcos Romero and Brenden Sewell, *Blueprints Visual Scripting for Unreal Engine 5* (Packt, 3rd ed.)
- Francesco Sapio, *Hands-On Artificial Intelligence with Unreal Engine* (Packt, 2019)
- Greg Penninck and Stuart Butler, *Mastering Technical Art in Unreal Engine* (CRC, 2025)
- Muhammad A. Moniem, *Learning Unreal Engine iOS Game Development* (Packt, 2015)

## High-Value Patterns Repeated Across Sources

## 1) One authoritative gameplay path

Across Blueprint and C++ texts, the strongest repeated rule is that gameplay systems must have one authoritative execution path per concern.

Insanitii implication:

- Input must have one owner path (Enhanced Input events in character graph), not parallel polling in HUD, bootstrap, and controller.
- State updates must have one owner path (mental state function pipeline), not hidden side writes from unrelated graphs.

## 2) Event-driven graph architecture beats Tick-heavy architecture

The Blueprint sources consistently favor event-driven logic, explicit functions, and bounded state transitions over heavy Tick usage.

Insanitii implication:

- Use `IA_*` events, timers, and latent actions for mechanics.
- Keep Tick only for bounded, unavoidable continuous systems (for example post-process interpolation), and gate it with booleans.

## 3) Communication contracts matter more than node count

Romero and Sapio both emphasize clear communication boundaries (direct references, interfaces, dispatchers, Blackboard-like shared state contracts).

Insanitii implication:

- Use `BPI_Interactable` as a strict contract for interactions.
- Use dispatcher-style events from state logic to UI/VFX/audio listeners instead of direct hard references when possible.

## 4) Data-driven tuning is required for iteration speed

Li, Elevating, and technical-art guidance all point to authorable parameters, not hardcoded constants, for rapid balancing.

Insanitii implication:

- Move mental-state tuning to curves/data assets.
- Expose key values in one tuning struct or data asset so designers can iterate without graph surgery.

## 5) Readability and naming are production features

The books consistently frame graph clarity as a quality lever, not a style preference.

Insanitii implication:

- Standard naming and foldering for every gameplay Blueprint.
- Functions and macros should read like intent statements (for example `ApplyFocusStart`, `ResolveInteractionTarget`, `UpdatePsychosisVisuals`).

## Source-Specific Takeaways Applied to Insanitii

## Romero (Blueprints Visual Scripting UE5)

Observed relevant themes:

- Blueprint communication modes: direct references, casting, event dispatchers.
- Function/macro/event differentiation.
- Trace-driven interaction examples.
- Blueprint complexity control and best practices.

Applied decisions:

- Keep interaction flow as: `IA_Interact` -> `ResolveTraceTarget` -> `BPI_Interactable`.
- Use functions for deterministic transformations and effects.
- Use macros only for compact reusable graph snippets that do not require latent behavior.

## Elevating Game Experiences UE5

Observed relevant themes:

- Enhanced Input setup discipline.
- Reparenting and class relationship hygiene.
- Iterative editor validation and player-facing feedback loops.

Applied decisions:

- Keep all Insanitii actions in one known mapping context and validate bindings as a dedicated checklist item each pass.
- Build UX-facing debug visibility first (mental state value, focus active flag, interact target name, breathe cooldown).

## Li (UE5 C++ Scripting)

Observed relevant themes:

- Gameplay framework boundaries (character/controller/game mode roles).
- Collisions/traces and interaction handling.
- Refactoring to shared, maintainable patterns.

Applied decisions:

- Use native C++ where it provides the clearest runtime authority, reflection, component structure, or smoke-test surface; keep Blueprint wrappers for designer-facing tuning, event orchestration, and presentation.
- Keep traces and hit processing in a dedicated interaction function set, not spread across event graph branches.

## Sapio (AI with Unreal)

Observed relevant themes:

- Blackboard/BT design emphasizes single source of truth for state and explicit decision boundaries.
- Nav and perception systems require strict naming consistency for reliability.

Applied decisions:

- Even before AI phase, use Blackboard-like thinking in player systems: one canonical state model with explicit keys/variables.
- Define a stable set of state variables now so AI and encounter systems can consume them later.

## Penninck (Technical Art in Unreal)

Observed relevant themes:

- Master material parameterization and organization for reusable visuals.
- Resource-conscious design choices instead of all-in-one graph abuse.

Applied decisions:

- Build post-process and VFX controls as parameterized systems with staged complexity.
- Avoid monolithic "do everything" post-process material graphs early.

## Moniem (iOS UE4, legacy but useful process lessons)

Observed relevant themes:

- Blueprint workflow tips, project organization, feedback loops, and communication between Blueprints.

Applied decisions:

- Keep gameplay loops complete and testable in small increments.
- Prioritize "working loop visibility" over large speculative graph expansion.

## Gaps Found in Current Insanitii Knowledge Base

Current docs are strong on chronology and blocker tracking, but missing:

- A normalized best-fit architecture after the pivot away from Blueprint-only planning.
- A definitive "single input authority" rule and verification checklist.
- A practical function-level implementation sequence for the six existing `IA_*` events.
- A testing protocol that distinguishes compile success from in-PIE behavior success.

## Best-Fit Architecture Rules (Current Standard)

1. One runtime path owns Enhanced Input handling for each action.
2. Every `IA_*` event immediately calls one named handler path; no long inline chains in the event node area.
3. Mental state writes happen only through one update API family.
4. Interaction dispatch must go through `BPI_Interactable`.
5. UI and debug display read state; they do not author gameplay state.
6. No duplicate key polling in HUD/controller/bootstrap while Enhanced Input is active.
7. Every mechanic has a visible debug signal in PIE.

## Minimum Variable Model for Phase 2

Keep these as the canonical runtime state, whether stored in native components, Blueprint wrappers, or both:

- `MentalState` (float 0..100)
- `FocusActive` (bool)
- `BreatheActive` (bool)
- `InteractionTarget` (actor ref, nullable)
- `HUDVisible` (bool)
- `PsychosisIntensity` (float 0..1, derived)

## Immediate Next Action

Use `Blueprint_Logic_Implementation_Plan.md` for event-routing and verification discipline, and `Architecture_Decision_Best_Fit_2026-05-18.md` for choosing native C++ versus Blueprint implementation.

This synthesis should be treated as the quality bar and architecture reference for all near-term Insanitii logic changes.
