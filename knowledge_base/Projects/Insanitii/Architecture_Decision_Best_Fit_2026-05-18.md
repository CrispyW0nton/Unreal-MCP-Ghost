# Insanitii Architecture Decision - Best-Fit Implementation

Date: 2026-05-18

## Decision

Insanitii is not constrained to Blueprint-only implementation.

Use the implementation layer that best serves the system:

- Native C++ for stable core runtime mechanics, reflected data models, reusable components, performance-sensitive logic, editor/MCP smoke-test routes, and systems that benefit from compile-time structure.
- Blueprint wrappers and Blueprint logic for designer-facing tuning, asset wiring, readable event orchestration, quick iteration, UI presentation, and content-specific behavior.
- Data assets, curves, and tables for values that need frequent tuning without code or graph changes.

## Why

The project already works best as a native C++ logic plus Blueprint wrapper architecture. The current priority is reliability and playable behavior, not adherence to a single implementation style.

The earlier Blueprint-only notes remain useful for graph hygiene, Enhanced Input routing discipline, event-driven structure, and PIE verification, but they should not block native work when native work is the cleaner or safer choice.

## Working Rule

For every new gameplay concern, pick one authoritative runtime path and document it.

Examples:

- Mental-state math can live in native components if that keeps clamping, derived intensity, and debug reporting deterministic.
- Blueprint wrappers should expose designer-friendly parameters and project-specific hookups.
- Input should still avoid duplicate runtime paths, regardless of whether the handler body is native or Blueprint.
- Debug and smoke-test visibility must be present before a feature is treated as complete.

## Validation Rule

Compile success is not completion.

Every implementation pass should address:

- native compile or Blueprint compile as applicable,
- generated class validity for wrappers,
- MCP/readiness checks where available,
- manual PIE behavior for player-facing mechanics.
