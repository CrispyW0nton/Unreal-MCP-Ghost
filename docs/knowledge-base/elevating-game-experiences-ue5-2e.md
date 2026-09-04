# Study guide — Elevating Game Experiences with Unreal Engine 5, 2nd ed. (Marques, Sherry, Pereira, Fozi; Packt, 2022)

**ISBN:** 978-1-80323-986-6
**Audience in this repo:** Tool authors and anyone running MCP against live editor sessions.

## What the book emphasizes (paraphrased)

The second edition is structured as a **skills ladder inside the editor**: project setup, editor navigation, Blueprint actors, materials and meshes, gameplay building blocks, UI, audio/VFX touchpoints, packaging, and optimization themes. The through-line is **player-facing quality**—clarity of feedback, readability of levels, and disciplined iteration.

## Map to Unreal-MCP-Ghost

| Book theme | Practical tie-in |
| --- | --- |
| Editor literacy (viewport, content browser, asset hygiene) | Reduces surprise when MCP triggers `MarkPackageDirty`, asset registry refreshes, or deferred compiles |
| Blueprint clarity (variables, functions, modular actors) | MCP `get_blueprint_nodes` / connect tools succeed when graphs stay small and named consistently |
| Materials and meshes as authored data | Commands that set mesh/material properties must respect LOD and asset outer packages |
| Packaging / performance mindset | Explains why some save/compile paths are avoided in the plugin (MassEntityEditor / delegate chains) |

## Practices worth adopting here

1. **Name things for searchability** — MCP and JSON-RPC flows grep graph dumps and node metadata; cryptic macros slow everyone down.
2. **Prefer “vertical slices”** — when validating a new MCP feature, build a tiny BP that mirrors a real game pattern (input → pawn → UI) instead of only testing empty graphs.
3. **Treat editor stability as a feature** — close heavy asset editors before bulk MCP writes; matches the book’s emphasis on controlled iteration.
4. **Document failure visibly** — elevated experiences require clear in-editor errors; MCP commands should return structured JSON errors, not silent no-ops.

## Complement

Use Epic’s **Editor interface** documentation for 5.6 specifics (viewport gizmos, world partition notes) alongside this book’s workflow lessons.
