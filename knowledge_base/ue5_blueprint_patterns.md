# UE5 Blueprint Patterns Reference
> Sources: Li, Marques/Sherry/Pereira/Fozi, Sapio; synthesized for Unreal-MCP-Ghost.
> Updated: 2026-04-29

## Blueprint Structure

Blueprints work best when graphs stay small, named, and grouped by responsibility. Use variables for authored defaults, functions for reusable behavior with return values, macros sparingly for local graph simplification, event dispatchers for one-to-many notifications, and Blueprint Interfaces for loosely coupled calls across unrelated classes.

## Event Graph Patterns

- `BeginPlay`: cache references, initialize widgets, bind dispatchers, add input mapping contexts, start behavior trees.
- `Tick`: use only for continuous behavior; multiply movement by `DeltaSeconds`.
- Overlap/hit events: validate the other actor, check interface/collision intent, then branch to interaction logic.
- Custom events: use for dispatcher handlers, timeline callbacks, and readable graph entry points.

## Communication

- Direct references are acceptable for owned components or cached framework refs.
- Cast only when the relationship is real and handle `Cast Failed`.
- Interfaces are preferred for interactables, damage receivers, and generic use actions.
- Event dispatchers are preferred for UI updates, quest stage changes, health changes, and completion signals.

## MCP Notes

- Use `get_blueprint_graphs`, `get_blueprint_nodes`, `get_blueprint_variables`, `get_blueprint_functions`, and `get_blueprint_components` before modifying or interpreting a Blueprint.
- Use returned node IDs and exact pin names; never hardcode GUIDs.
- Compile and save after graph mutations.
- Use `exec_python` when a direct command cannot express the asset path or editor operation.

## Audit Checklist

- Record listened events, called functions, variables read/set, casts, interfaces, and dispatchers.
- Flag unhandled casts, unguarded external refs, per-frame casts, and Tick logic that should be event-driven.
- Note whether Blueprint names follow `BP_`, `WBP_`, `BPI_`, `ABP_`, `BT_`, and related prefixes.
