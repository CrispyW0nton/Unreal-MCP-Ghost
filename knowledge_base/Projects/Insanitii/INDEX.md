# Insanitii Project Knowledge Base

## Project Direction

Insanitii is a mechanics-first Unreal Engine 5.6 first-person project focused on validating core psychosis simulation systems before custom content production.

Current source of truth as of the 2026-05-17 smoke test: Phase 1 has pivoted from the older Blueprint-only plan to a **native C++ logic + Blueprint wrapper** architecture. Native classes own the core runtime mechanics; Blueprint wrappers under `/Game/Insanitii/...` keep the systems designer-accessible.

## Knowledge Base Rule

All Insanitii-specific project notes, implementation logs, audit findings, and phase reports belong under:

`knowledge_base/Projects/Insanitii/`

## Core Project Docs

- `Phase1_Status.md`: current runtime status, blockers, and verification state.
- `Phase1_Implementation_Log.md`: detailed implementation chronology and audit trail.
- `Book_Deep_Dive_Blueprint_Synthesis.md`: cross-book synthesis for Insanitii architecture, quality, and workflow.
- `Blueprint_Logic_Implementation_Plan.md`: concrete event-graph and subsystem plan for next implementation passes.
- `Insanitii_Development_Roadmap.md`: in-depth multi-phase production roadmap, milestones, and exit gates.
- `Phase1_Smoke_Test_2026-05-17.md`: live Unreal Editor smoke-test report against the open Insanitii project.
- `Phase1_Repair_Pass_2026-05-17.md`: repair log for the missing level actors and broken wrapper generated classes found during the smoke test.
- `Phase7_MCP_Smoke_Tooling_2026-05-17.md`: MCP tooling report for Insanitii-specific smoke wrappers and prompt/dialog handling.

## Phase Roadmap (Updated)

1. Phase 1: Core systems foundation (input, mental state, interaction, debug visibility).
2. Phase 2: Blueprint logic hardening (state model, interactions, visual/audio feedback loops, test harness).
3. Phase 3: Gameplay scenarios and content pass using validated Blueprint architecture.
4. Phase 4: Optimization, stabilization, and selective native migration only where justified.

## Current Status

- Bridge access is currently available through Unreal-MCP-Ghost on `127.0.0.1:55655`.
- Phase 1 automated smoke blockers from `Phase1_Smoke_Test_2026-05-17.md` were repaired in `Phase1_Repair_Pass_2026-05-17.md`.
- Phase 1 still needs Jarrod's manual Play-in-Editor checklist before Phase 2 begins.
- Use the smoke-test report plus the newer context handoff as the source of truth when it conflicts with older Blueprint-only planning notes.
