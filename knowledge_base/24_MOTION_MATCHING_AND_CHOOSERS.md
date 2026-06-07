# Motion Matching and Choosers
> Source: project notes, Epic Motion Matching documentation, animation system study guide
> Last Updated: 2026-06-07 | UE 5.6+

---

## Overview

Motion Matching selects animation poses from a database using a runtime query
instead of hand-authored transition rules for every locomotion case. Choosers
select context-appropriate assets or data from rules, and are useful when
animation, weapons, traversal, or interaction sets need data-driven selection.

Use Motion Matching when the project has enough animation data and wants high
fidelity locomotion. Use traditional state machines and blend spaces for small
sets, stylized control, or simpler prototypes.

## Key Classes

| Class or Asset | Role |
| --- | --- |
| Pose Search plugin | Enables Motion Matching assets and nodes. |
| Pose Search Schema | Defines channels and query data used for pose selection. |
| Pose Search Database | Stores animation sequences and searchable pose features. |
| Motion Matching node | Animation Blueprint node that queries the database at runtime. |
| Animation Blueprint | Hosts the runtime animation graph and exposed variables. |
| Chooser Table | Rule-driven selection asset for animation/data decisions. |
| Proxy/Table inputs | Context values used by Chooser rules. |

## Common Pitfalls

- Enabling Motion Matching without enough clean locomotion clips.
- Mixing skeletons or retargeted data with inconsistent root motion/orientation.
- Forgetting to tune schema channels and weights.
- Using Motion Matching to hide gameplay movement bugs.
- Creating giant Chooser tables without stable input names.
- Failing to debug pose choices in motion matching tools before blaming the
  Animation Blueprint.

## MCP Tool Mapping

| Task | Preferred MCP direction |
| --- | --- |
| Inspect animation assets | `scan_project_assets`, animation describe tools |
| Create montages/slots/notifies | `anim_*` tools |
| Build AnimBP graph support | AnimGraph/state-machine MCP tools |
| Retarget/source data prep | IK rig, IK retargeter, batch retarget tools |
| Verify runtime | PIE, viewport screenshot, log capture, animation readbacks |

## Working Example

Goal: replace simple locomotion with Motion Matching.

1. Enable Pose Search and restart/reload as required.
2. Gather walk, jog, run, stop, start, and turn clips on one skeleton.
3. Create `PS_Schema_Locomotion` with trajectory and pose channels.
4. Create `PSD_Player_Locomotion` and add cleaned locomotion sequences.
5. In the AnimBP, feed velocity/trajectory query data into a Motion Matching
   node.
6. Use a Chooser for weapon stance or movement style if separate databases are
   needed.
7. Debug pose selection, then capture PIE footage/logs for starts, stops, and
   turns.

## Validation Checklist

- Source clips are consistent in skeleton, scale, and root behavior.
- Schema channels match the movement model.
- Pose database contains enough coverage for starts, stops, turns, and speeds.
- Chooser inputs are named and documented.
- Runtime debug evidence confirms sensible pose/database choices.

## References

- Epic: Motion Matching -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/motion-matching-in-unreal-engine
