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
| Create Pose Search schemas | `motion_create_pose_search_schema` |
| Create Pose Search databases | `motion_create_pose_search_database` |
| Add animation clips to databases | `motion_add_database_sequence` |
| Inspect Pose Search assets | `motion_inspect_pose_search_asset` |
| Create Chooser tables | `chooser_create_table` |
| Add asset result rows | `chooser_add_asset_row` |
| Inspect Chooser tables | `chooser_inspect_table` |
| Inspect animation assets | `scan_project_assets`, animation describe tools |
| Create montages/slots/notifies | `anim_*` tools |
| Build AnimBP graph support | AnimGraph/state-machine MCP tools |
| Retarget/source data prep | IK rig, IK retargeter, batch retarget tools |
| Verify runtime | PIE, viewport screenshot, log capture, animation readbacks |

## MCP Motion Matching and Chooser Tools

Use the B.8 native bridge tools to create the authoring assets, then tune schema
channels and Chooser conditions in the editor before runtime validation.

```python
motion_create_pose_search_schema(
    name="PSS_Locomotion",
    path="/Game/Animation/MotionMatching",
    skeleton="/Game/Characters/Hero/SK_Hero",
    sample_rate=30,
    add_default_channels=True,
    overwrite=True
)
motion_create_pose_search_database(
    name="PSD_Locomotion",
    schema="/Game/Animation/MotionMatching/PSS_Locomotion",
    sequences=["/Game/Characters/Hero/Animations/A_Run"],
    search_mode="pca_kd_tree",
    overwrite=True
)
motion_add_database_sequence(
    database="/Game/Animation/MotionMatching/PSD_Locomotion",
    sequence="/Game/Characters/Hero/Animations/A_Stop",
    mirror_option="both",
    sampling_range=[0.0, 0.0]
)
motion_inspect_pose_search_asset(asset="/Game/Animation/MotionMatching/PSD_Locomotion")
```

Chooser tables can be seeded with direct asset result rows:

```python
chooser_create_table(
    name="CH_Locomotion",
    path="/Game/Animation/Choosers",
    result_class="/Script/Engine.AnimationAsset",
    overwrite=True
)
chooser_add_asset_row(
    chooser="/Game/Animation/Choosers/CH_Locomotion",
    asset="/Game/Characters/Hero/Animations/A_Run",
    enabled=True
)
chooser_inspect_table(chooser="/Game/Animation/Choosers/CH_Locomotion")
```

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
