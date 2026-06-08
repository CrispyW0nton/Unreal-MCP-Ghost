# skill_generate_playable_slice

High-order D.7 skill for turning a one-sentence game brief into a generated
playable-slice workflow.

## Modes

- `plan`: offline, no network, no Unreal mutation. Builds and validates a
  `unreal_mcp_playable_slice_plan.v1` plan against
  `knowledge_base/v5/PLAYABLE_SLICE_SCHEMA.json`.
- `submit_assets`: paid Tripo gate. Requires `TRIPO_API_KEY`, remaining credit
  budget, and `confirm_spend=True`; submits the hero, two props, and enemy
  `text_to_model` tasks and returns task IDs plus next steps.

## Example

```python
skill_generate_playable_slice(
    brief="third-person dungeon demo with a slime, a skeleton, and a boss",
    mode="plan",
)
```

Continue from submitted task IDs with `gen_tripo_wait_for_task`,
`gen_tripo_import_to_project`, Blueprint/AI/UMG tools, PIE evidence, and
`skill_package_vertical_slice_report`.
