# Study guide — Unreal Engine 5 Game Development with C++ Scripting (Zhenyu George Li, Packt, 2023)

**ISBN:** 978-1-80461-393-1
**Audience in this repo:** Anyone extending `unreal_plugin/` or reasoning about gameplay classes invoked from MCP.

## What the book emphasizes (paraphrased)

The progression moves from **Visual Studio + UE5 project hygiene** into **gameplay framework classes**, then a **full gameplay slice** (actors, animation, input, collisions), and closes with **multiplayer replication** and **UI/game flow**. Along the way it stresses:

- Treating Unreal C++ as **scripting against the engine API** (reflection, garbage collection, module boundaries) rather than “raw” C++ only.
- **`UPROPERTY` / `UFUNCTION`** as the contract surface between C++, Blueprints, and the editor.
- **AnimInstance subclasses** and Animation Blueprints as first-class gameplay tech, not an afterthought.
- **Collision and interaction** as designed systems (presets, channels, overlaps vs blocking).
- **Refactoring toward shared bases** (common character logic, pooling, logging discipline).

## Map to Unreal-MCP-Ghost

| Book theme | Where it shows up in our work |
| --- | --- |
| Gameplay framework (`AActor`, `APawn`, components, `GameMode`, `PlayerController`) | Designing MCP commands that assume valid world/pawn contexts; spawn/set actor tools |
| `UPROPERTY` / replication / RPC patterns | Any command that touches Blueprint-generated classes or networked defaults — know what must stay in C++ vs BP |
| Animation instances + state machines | `AnimGraph` / state-machine MCP commands; deferred compile behavior documented in plugin |
| Collision / damage / weapon-style interactions | Blueprint dumps and infantry-style weapon traces — align socket names, mesh setup, and anim montage slots |
| Code quality (shared bases, pooling, `UE_LOG`) | `SafeMarkBlueprintModified`, low-level `SavePackage` paths, crash-avoidance notes in `UnrealMCPBlueprintCommands.cpp` |

## Practices worth adopting here

1. **Prefer narrow, testable C++ helpers** over giant Blueprint graphs when MCP must touch the same logic repeatedly.
2. **When exposing a new MCP command**, ask: “Would Li’s `UFUNCTION`/`UPROPERTY` rules make this safe for BP and for hot reload?”
3. **Animation + C++ split:** keep locomotion parameters in AnimBP variables; use C++ for authoritative movement/combat if replication matters.
4. **Multiplayer caution:** any new editor automation that saves packages or marks BPs modified should respect the project’s network authority model (server-only writes for replicated state).

## Further reading inside UE docs

Pair chapters on replication with Epic’s current **Gameplay Framework** and **Networking** pages for UE 5.4+ (your project targets 5.6).
