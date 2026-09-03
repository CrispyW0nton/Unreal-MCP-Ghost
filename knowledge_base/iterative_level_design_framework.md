# Iterative Level Design Framework — MCP-Assisted Development

Source: BioWare Mass Effect 2 GDC presentation analysis
Date: 2026-04-30
Purpose: Guide how agents using Unreal-MCP-Ghost should approach level and gameplay modifications.

## Core Principle

Do only the work that answers the right question, in the right order. Any work beyond that is waste: added risk, potential rework, and scope creep.

## Phase 0: Audit and Understand

Question: What exists and what needs to change?

- Read the full knowledge base.
- Query every Blueprint, component, variable, and graph node.
- Document current state completely.
- Identify the gap between current state and requirements.
- Get human confirmation of the plan before proceeding.

Rule: No modifications happen in this phase. Only reading and planning.

## Phase 1: Foundation — Interfaces and Architecture

Question: Is the communication architecture correct?

- Create Blueprint Interfaces, or have a human create them if tool limitations exist.
- Assign interfaces to Blueprints.
- Verify interface function graphs exist but leave them empty.
- Keep the project compiled and playable.

Rule: Do not wire gameplay logic yet. Only structural changes.

## Phase 2: Core Wiring — Interface Implementations

Question: Do the interface implementations contain the correct logic?

- Wire each interface function graph, such as `DealDamage`, `ShortCircuit`, or `Hack`.
- Verify each implementation with MCP read-back.
- Test that the basic communication path works.
- Keep the project playable.

Rule: Do not touch Event Graph main logic yet. Only interface implementations.

## Phase 3: Behavior Modifications — Event Graph Changes

Question: Do actors behave correctly according to requirements?

- Modify Event Graph logic one behavior at a time.
- Wire player action handlers to use interface messages.
- Verify each behavior change individually.
- Keep the project playable after each individual change.

Rule: Make one behavior change at a time. Verify before proceeding to the next.

## Phase 4: Value Verification — Numbers and Defaults

Question: Do all values match the specification exactly?

- Verify every damage amount, range, timer, and health default.
- Fix values that do not match requirements.
- Remove debug `PrintString` nodes.
- Perform a final read-back of every Blueprint.

Rule: No structural changes in this phase. Only value adjustments and cleanup.

## Phase 5: Polish and Organization

Question: Is the Blueprint graph clean, organized, and maintainable?

- Apply comment box standards from `blueprint_organization_standards.md`.
- Align nodes within comment boxes.
- Add reroute nodes for long-distance wires.
- Categorize variables.
- Update final documentation.

Rule: Organization work happens after behavior and values are correct.

## Agent Principles

- Always playable: after every modification, the project must compile and run.
- Always foundational: every change builds on the previous phase.
- Always real work: do not create placeholder logic that will be torn out later.
- Minimize blast radius: check downstream systems when touching shared interactions.
- Prove in context: verify behavior in the actual level, not only by reading graphs.
- Flag expensive decisions early: call out unusual collision, AI, networking, or tooling complexity before implementation.

## Anti-Patterns

- The silo problem: changing one actor system without checking shared interface consumers.
- Skipping deliverables: jumping to gameplay logic before interface architecture exists.
- Special snowflake syndrome: creating one-off actor functions when a shared interface fits.
- Late integration: connecting systems only after individual behaviors are built.

## QA Alignment

- Phase 1: Interface assignment errors and compilation failures.
- Phase 2: Interface calls that do not trigger, wrong function signatures.
- Phase 3: Actor behavior bugs and wrong branch conditions.
- Phase 4: Wrong damage numbers, ranges, timers, or defaults.
- Phase 5: Disorganized graphs, missing comments, and remaining debug output.
