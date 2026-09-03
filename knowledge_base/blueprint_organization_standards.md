# Blueprint Organization Standards for Unreal-MCP-Ghost
> Created: 2026-04-30
> Purpose: Every agent using this MCP server MUST follow these standards when creating or modifying Blueprint event graph logic.

## Core Principle

Every Blueprint event graph must be readable by a stranger at a glance. Nodes must be grouped by purpose, labeled with comment boxes, aligned on a grid, and color-coded by functional category. Spaghetti graphs are never acceptable.

Comment boxes alone do not count as organization. A valid organization pass must physically move nodes into readable lanes or blocks. Adding large translucent boxes over a chaotic graph is explicitly unacceptable.

## 1. Comment Box Requirements

**Every functional block of nodes MUST be wrapped in a comment box.**

A "functional block" is any group of nodes that together accomplish one discrete purpose. Examples:

- Reading input and applying movement
- Performing a sphere trace and processing the hit result
- Checking a condition and setting a variable
- Spawning an actor and configuring it

### Comment Box Naming Convention

Use ALL CAPS category prefix followed by a dash and a descriptive label:

```text
CATEGORY — Description of What This Block Does
```

Standard category prefixes:

| Prefix | Use for |
|---|---|
| ANIMATION SYNC | Tick-driven animation variable updates (speed, aim, state flags) |
| MOVEMENT | Character/actor movement logic |
| COMBAT ENTRY | Starting an attack, raising weapons, beginning combat state |
| COMBAT EXIT | Ending attack, lowering weapons, returning to idle |
| FIRE CONTROL | Spawning projectiles, managing burst fire, cooldowns |
| PERCEPTION | Pawn sensing, sight/hearing delegates, awareness checks |
| VISIBILITY | Line traces for line-of-sight, lose-sight timers |
| INPUT | Reading Enhanced Input actions, processing axis values |
| HEALTH / DAMAGE | Taking damage, healing, death checks, shield logic |
| INTERACTION | Overlap-based pickups, interact prompts, hackable triggers |
| SPAWNING | SpawnActorFromClass calls and post-spawn configuration |
| STATE MANAGEMENT | Setting/checking boolean flags that gate behavior |
| UI / HUD | Widget creation, binding, updating display values |
| INITIALIZATION | BeginPlay setup, variable defaults, component configuration |
| CLEANUP | EndPlay, destroy logic, timer invalidation |
| DEBUG | PrintString nodes, debug draw, temporary test logic |

### Comment Box Colors

Assign consistent colors by category so graphs are scannable at a distance:

| Category | Suggested Color |
|---|---|
| INPUT | Light Blue |
| MOVEMENT | Green |
| COMBAT / FIRE CONTROL | Red / Dark Red |
| HEALTH / DAMAGE | Orange |
| PERCEPTION / VISIBILITY | Yellow |
| INTERACTION | Purple |
| SPAWNING | Teal |
| STATE MANAGEMENT | Gray |
| ANIMATION SYNC | Light Green |
| UI / HUD | Pink |
| INITIALIZATION | White |
| DEBUG | Bright Yellow (stands out as temporary) |

### Comment Box Properties

- `bColorCommentBubble`: true
- `bCommentBubbleVisible_InDetailsPanel`: true
- `MoveMode`: GroupMovement (so dragging the comment moves all contained nodes)
- Font size: default (no need to enlarge)

## 2. Node Alignment Rules

**Nodes within a comment box must be aligned horizontally or vertically on a consistent grid.**

### Horizontal Flow (Primary)

The primary execution flow reads LEFT TO RIGHT. Event/entry nodes are on the far left. Terminal actions (`DestroyActor`, final `Set Variable`) are on the far right.

```text
[Event] -> [Get/Check] -> [Branch] -> [Action] -> [Cleanup]
```

### Vertical Stacking (Secondary)

When a branch splits, the TRUE path goes UP or stays level, the FALSE path goes DOWN. Parallel operations stack vertically.

### Spacing

- Minimum horizontal gap between connected nodes: **150 units**
- Minimum vertical gap between parallel branches: **200 units**
- Minimum gap between comment boxes: **300 units**

### Comment Box Layout

Arrange comment boxes in a grid-like pattern across the event graph canvas. Related blocks should be near each other. The overall layout should follow this general spatial pattern:

```text
┌─────────────────┐   ┌──────────────────┐
│ INITIALIZATION  │   │ ANIMATION SYNC   │
└─────────────────┘   └──────────────────┘

┌─────────────────┐   ┌──────────────────┐
│ MOVEMENT        │   │ PERCEPTION       │
└─────────────────┘   └──────────────────┘

┌─────────────────┐   ┌──────────────────┐
│ COMBAT ENTRY    │   │ COMBAT EXIT      │
└─────────────────┘   └──────────────────┘

┌─────────────────┐   ┌──────────────────┐
│ FIRE CONTROL    │   │ HEALTH / DAMAGE  │
└─────────────────┘   └──────────────────┘
```

## 3. Reroute Node Usage

**Use reroute nodes to prevent wire spaghetti.**

When a wire must travel a long distance across the graph:

1. Double-click the wire to create a reroute node.
2. Route the wire around other comment boxes, not through them.
3. Use right-angle routing (horizontal then vertical, or vice versa).

When a single output pin connects to multiple distant nodes:

1. Create a reroute node near the source.
2. Branch from the reroute to each destination with clean right-angle paths.

## 4. Variable Organization

### Naming

- Boolean variables: prefix with `b` (e.g., `bIsHacked`, `bOnCooldown`, `bPlayerInRange`)
- Private/protected variables: prefix with underscore (e.g., `_HealthPoints`, `_AttackCountingDown`)
- All names: PascalCase (e.g., `CoreHealth`, `ShieldCharges`, `MoveSpeed`)

### Categories

Every variable MUST be assigned to a category. Default uncategorized variables are not acceptable in a finished Blueprint.

Standard categories:

| Category | Contains |
|---|---|
| Stats | Health, damage, speed, armor, strength values |
| State | Boolean flags (`IsDisabled`, `IsShortCircuited`, `bIsHacked`) |
| Combat | Attack range, fire rate, bullet class, weapon references |
| References | Cached actor/component pointers (`TargetActor`, `AnimInstance`) |
| Config | Tuning values meant to be set per-instance in the editor |
| Internal | Countdown timers, temporary calculation storage |

## 5. Function Extraction Rules

**If a sequence of nodes appears more than once in the same Blueprint, extract it into a function.**

**If a sequence of nodes appears across multiple Blueprints, extract it into a Blueprint Function Library.**

Functions should:

- Have descriptive names (not `MyFunction` or `DoStuff`)
- Use local variables instead of polluting the Blueprint's variable list
- Have input/output pins properly named and typed

## 6. Interface Usage Over Direct Casts

**When an actor needs to call a function on another actor it found through a trace or overlap, use a Blueprint Interface message, not a direct cast.**

This reduces coupling and makes the graph cleaner because:

- Interface message nodes are a single node instead of Cast + Function Call
- No need to handle cast failure paths
- New actor types can implement the interface without modifying the caller

## 7. Graph Separation

**If a Blueprint's event graph exceeds roughly 15-20 comment boxes, consider splitting logic into separate graphs using Collapse to Graph.**

Suggested graph splits:

- Main EventGraph: events, initialization, tick
- Input graph: all input action handlers
- Combat graph: attack, damage, fire control
- AI/Movement graph: pathfinding, sensing, chase logic

## 8. MCP Tool Enforcement

When using MCP tools to create or modify Blueprint nodes, the agent MUST:

1. **Plan the layout before placing nodes**: Determine which comment box the new nodes belong to, calculate approximate positions, and place nodes within those bounds.
2. **Create the comment box FIRST**, then place nodes inside it.
3. **Use `move_blueprint_node`** to align nodes after creation if they end up misaligned.
4. **Add reroute nodes** for any wire that spans more than 800 units horizontally or 400 units vertically.
5. **Verify visual organization** after completing each comment box by reading back node positions and confirming they fall within the comment box bounds.
6. **Never leave nodes floating outside a comment box** unless they are temporary debug nodes (which should be in their own DEBUG comment box).

When reorganizing an existing graph, reverse steps 2 and 3 as needed: first identify functional blocks, move existing nodes into clean lanes, then resize/create comment boxes tightly around those moved nodes. The final graph should resemble a readable stack of functional blocks, not one giant overlapping canvas.

### Position Calculation Reference

When placing nodes programmatically:

- Standard node width: ~200-400 units depending on pins
- Standard node height: ~50-150 units depending on pins
- Comment box padding: 50 units on each side beyond the contained nodes
- Start position for a new comment box: find the lowest/rightmost existing comment box and offset by 400 units

### Comment Box Creation Template

When creating a comment box via MCP:

```json
{
  "node_type": "Comment",
  "comment_text": "CATEGORY — Description",
  "position_x": "<calculated>",
  "position_y": "<calculated>",
  "size_x": "<calculated to contain all nodes + padding>",
  "size_y": "<calculated to contain all nodes + padding>",
  "comment_color": {"r": "<R>", "g": "<G>", "b": "<B>", "a": 1.0}
}
```

For the current MCP command surface, map this template to `add_blueprint_comment_node` parameters:

- `node_position`: `[position_x, position_y]`
- `width`: `size_x`
- `height`: `size_y`
- `color`: `[r, g, b, a]`

## 9. Quality Checklist

Before marking any Blueprint modification as complete, verify:

- [ ] Every functional block has a labeled comment box.
- [ ] Comment boxes use the standard naming convention (`CAPS PREFIX — Description`).
- [ ] Comment boxes have category-appropriate colors.
- [ ] Nodes within each box are aligned horizontally/vertically.
- [ ] No execution wires cross through unrelated comment boxes.
- [ ] Reroute nodes are used for long-distance connections.
- [ ] All variables are categorized.
- [ ] All variables follow naming conventions.
- [ ] No duplicate logic exists that should be a function.
- [ ] Interface messages are used instead of direct casts where applicable.
- [ ] No orphaned nodes exist (nodes not connected to any execution flow).
- [ ] Debug `PrintString` nodes are in their own clearly labeled DEBUG box or removed.

## Enforcement Prompt Addition

Add this to the beginning of every Cursor prompt that involves Blueprint modifications:

```text
MANDATORY: Blueprint Organization Standards
Before creating or modifying ANY Blueprint event graph logic, read and follow: knowledge_base/blueprint_organization_standards.md

Key enforcement rules:

EVERY group of related nodes MUST be inside a labeled comment box using the format: "CATEGORY — Description"
Comment boxes MUST be color-coded by category (combat=red, input=blue, movement=green, etc.)
Nodes MUST be aligned on a grid within their comment box — no floating or overlapping nodes
Reroute nodes MUST be used for wires spanning long distances
Create the comment box FIRST, then place nodes inside it
After placing all nodes in a block, verify positions fall within the comment box bounds
All variables must be assigned to categories, all booleans prefixed with 'b'
Use interface messages instead of direct casts when calling functions on traced/overlapped actors
If the MCP tools cannot create properly positioned comment boxes or cannot set node positions accurately, DOCUMENT THE LIMITATION and tell the human what manual cleanup is needed, specifying exact comment box labels, colors, and which nodes belong in each box.

Do not proceed to the next functional block until the current one passes the organization checklist.
```

## Plugin Enhancement Recommendations

Based on the organization standards, the MCP plugin would benefit from these capabilities.

### High Priority — Needed for the Standards to Work

First, a `create_comment_box` tool or parameter on existing node creation that creates a comment node with specified text, position, size, and color. Without this, the agent has to ask the human to manually add every comment box, which defeats the purpose.

Second, a `set_node_position` or `move_node` tool that can reposition existing nodes after creation. Blueprint node placement through MCP often does not land exactly where intended, and post-placement adjustment is essential for alignment.

Third, a `get_graph_layout` tool that returns all node positions and comment box bounds for a given graph, so the agent can calculate where to place new content without overlapping existing blocks.

### Medium Priority — Quality of Life

A `create_reroute_node` tool that inserts a reroute node on an existing wire at a specified position.

An `auto_align_nodes` tool that takes a list of node IDs and snaps them to a grid within a specified bounding box.

A `validate_graph_organization` tool that checks whether all nodes are inside comment boxes, whether wires cross through unrelated boxes, and whether nodes are aligned, returning a list of violations.

These would make the organization standards automatically enforceable rather than relying on the agent's manual position calculations.
