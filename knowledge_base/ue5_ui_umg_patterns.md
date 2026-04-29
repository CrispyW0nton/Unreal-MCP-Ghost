# UE5 UI And UMG Patterns Reference
> Sources: Marques/Sherry/Pereira/Fozi, Li; synthesized for Unreal-MCP-Ghost.
> Updated: 2026-04-29

## Widget Structure

Use Widget Blueprints (`WBP_`) for HUDs, menus, prompts, and dialogue. Designer layout owns visual hierarchy and anchors; Graph logic owns construction, event binding, and value updates. Prefer `CanvasPanel` for HUD layout, box/overlay/grid containers for responsive composition, and anchors/safe zones for resolution independence.

## Creation Pattern

PlayerController `BeginPlay` commonly creates the HUD widget, stores the reference, adds it to viewport, and sets input mode. Temporary widgets such as dialogue boxes, pause menus, and level-complete screens should own their open/close input mode transitions.

## Data Updates

- Bindings are quick but run frequently; use them only for simple values.
- Event dispatchers are preferred for health, score, quest, and objective changes.
- Widgets should cache owning player/pawn refs after validation rather than casting every Tick.

## MCP Notes

- `create_umg_widget_blueprint`, text/button tools, and widget event binding can create basic widgets.
- Full Designer canvas layout remains a known automation limitation; document manual layout requirements.
- Audit widget usage by inspecting Blueprint graphs for `CreateWidget`, `AddToViewport`, `RemoveFromParent`, `SetInputMode*`, and dispatcher bindings.

## Audit Checklist

- List all `WBP_` assets, their creation sites, viewport Z order if known, and input mode changes.
- Flag UI created in arbitrary actors when PlayerController/GameInstance ownership would be cleaner.
- Flag tick bindings or Tick-heavy widgets where event-driven updates would be safer.
