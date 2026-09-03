# Insanitii GDD Integration - 2026-05-18

## Source

User-provided master GDD, version 1.0, dated 2026-05-12.

This document records the GDD as current creative direction, then adjusts the production plan to match the actual project state, Unreal-MCP-Ghost workflow, and solo-development risk.

## Creative Direction To Preserve

- Title: `INSANITII`, subtitle `A Psychosis Simulation`.
- Mantra: "Stability is not the default state; it is an achievement."
- Genre: first-person psychological simulation and lifestyle sandbox.
- Tone: empathy engine, not horror game.
- Core experience: the exhausting work of maintaining stability while daily responsibilities continue.
- Four intended lifestyle paths: Office Worker, Gig Economy Worker, Artist/Freelancer, Street Hustler.
- Core loop: morning preparation, commute or transition, work shift, evening choice, night recovery.
- Ethical constraint: psychosis is a lived constraint, not a villain, superpower, or scare aesthetic.

## Production Adjustments

### 1) MVP Scope

The full GDD is the long-term product vision, but four complete lifestyles plus 15+ endings is too large for a reliable 9-week solo MVP.

Recommended MVP target:

- One complete vertical-slice lifestyle: Office Worker.
- One thin secondary lifestyle path or fallback: Gig Economy, only if Office is stable early.
- Native framework support for all four lifestyles, so future expansion is not throwaway work.
- A 7-10 day playable arc for Early Access prototype quality, then expand toward the 30-day arc.

This keeps the "GTA feeling" of agency through meaningful choices without requiring open-world scope.

### 2) Architecture

Use the best-fit architecture decision:

- Native C++ for stable systems: mental state, time, economy, lifestyle manager, save data, smoke-test surfaces.
- Blueprint wrappers for tuning, designer-facing defaults, UI hooks, placed actors, and content-specific behavior.
- Data assets/curves/tables for economy, task, mental-state, and psychosis tuning values.

### 3) Current Project Truth

The GDD says Phase 1 is 75% complete and Phase 2 pending. Repo evidence says:

- Phase 1 foundation exists but still needs manual possessed-PIE validation.
- Phase 2 Slice 1 exists: native time, economy, and lifestyle manager are implemented and previously smoke-tested.
- UnrealMCP plugin source is synchronized into the Insanitii project plugin, but a hard command-line rebuild is blocked while Live Coding is active.

So the next work should not start from the GDD's Phase 2 blank slate. It should harden and connect the existing Phase 2 slice into a playable loop.

### 4) Mental State Scale

The GDD uses `0.0-1.0`; older KB notes sometimes use `0-100`.

Canonical decision:

- Internal gameplay value: `0.0-1.0`.
- UI display: percentage when helpful.
- Any existing `0-100` wording should be treated as presentation or legacy planning unless the source code proves otherwise.

### 5) Input Canonicalization

Current canonical input mapping is `/Game/Input/IMC_Default`, not the older `/Game/FirstPerson/Input/IMC_Default`.

HUD toggle should remain `H`, not tilde/backtick, because tilde opens the Unreal console.

### 6) Ethical and Review Gate

Mental health professional or lived-experience review should happen before public marketing claims harden, not only at the end of Phase 8.

Street Hustler content should remain late-scope until the consequence framing, content warnings, and non-stigmatizing presentation are proven in less risky lifestyles.

### 7) Toolchain Development

Unreal-MCP-Ghost improvements are part of the production plan, not a side quest.

When Insanitii exposes MCP limitations:

1. Log them in `knowledge_base/Limitation log/ACTIVE_LIMITATIONS.md`.
2. Continue with a safe workaround if possible.
3. Fix the plugin/server/tooling when the limitation becomes a recurring blocker.
4. Move the entry to `RESOLVED_LIMITATIONS.md` after verification.

## Revised MVP Definition

The next credible MVP is:

- A stable first-person loop with movement/look intact.
- Focus, Breathe, interaction, mental-state mutation, and debug/player feedback validated in possessed PIE.
- Time and money visible to the player.
- Home base with sleep/day advance and daily living cost.
- One executable Office task flow that affects money, skill/reputation, and mental state.
- Save/load skeleton for day, time, money, lifestyle, skill, reputation, and mental-state baseline.
- First-pass sensory feedback tied to mental state and Focus.

The full four-lifestyle sandbox remains the Early Access expansion direction after the core daily loop proves fun, understandable, and stable.
