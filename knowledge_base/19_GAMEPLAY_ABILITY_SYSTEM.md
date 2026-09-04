# Gameplay Ability System
> Source: project notes, Epic Gameplay Ability System documentation, Li C++/replication study guide
> Last Updated: 2026-06-07 | UE 5.6+

---

## Overview

The Gameplay Ability System (GAS) is the right foundation when gameplay needs
networked abilities, attributes, costs, cooldowns, gameplay tags, prediction, or
stacking effects. Keep it data-driven, but do not treat it as Blueprint-only
magic: the stable production pattern is a C++ `AbilitySystemComponent`, C++
attribute sets, Blueprint ability assets for designer-authored behavior, and
small verification slices for replication.

In Unreal-MCP-Ghost, use GAS as a planned system rather than an incidental node
cluster. First inspect the owning Actor/Pawn/PlayerState, then create or verify
the component, tags, attributes, ability assets, input binding, and network
mode. Finish with PIE evidence.

## Key Classes

| Class or Asset | Role |
| --- | --- |
| `UAbilitySystemComponent` | Owns ability specs, active gameplay effects, tags, prediction, and replication. |
| `IAbilitySystemInterface` | Standard way for other systems to fetch the ASC from an Actor. |
| `UGameplayAbility` | Active or passive ability behavior, often Blueprint-authored from a C++ base. |
| `UGameplayEffect` | Attribute modification, duration, stacking, costs, cooldowns, and status effects. |
| `UAttributeSet` | Replicated gameplay attributes such as Health, Stamina, or Mana. |
| `FGameplayTag` / tag tables | Semantic state, ability categories, requirements, and blocked states. |
| `FGameplayAbilitySpec` | Runtime granted ability entry, level, input id/tag, and source object. |
| `UAbilityTask` | Async ability behavior such as waiting for target data, montage events, or delays. |

## Common Pitfalls

- Placing the ASC on a Pawn that is destroyed during respawn when persistent
  player attributes should live on `PlayerState`.
- Forgetting `IAbilitySystemInterface`, then scattering ASC lookups across
  casts and Blueprint variables.
- Replicating raw health variables outside the attribute set and creating two
  sources of truth.
- Calling ability activation from clients without thinking through prediction,
  server authority, and failure rollback.
- Treating gameplay tags as strings instead of a governed tag vocabulary.
- Adding reliable RPC spam for ability input when GAS prediction or RepNotify
  state would be cleaner.
- Building a big ability before validating one small grant/activate/effect loop.

## MCP Tool Mapping

| Task | Preferred MCP direction |
| --- | --- |
| Inspect current project state | `get_project_context`, `scan_project_assets`, `list_available_tools("gas")` |
| Find gameplay classes/assets | `scan_project_assets(path="/Game", class_filter="Blueprint")`, C++/reflection inspection tools |
| Create Blueprint-facing assets | `gas_create_ability`, `gas_create_gameplay_effect`, `gas_create_gameplay_cue`, `gas_create_attribute_set` |
| Author default grants/effects/tags | `gas_grant_ability`, `gas_apply_effect`, `gas_add_tag` |
| Add ability async task nodes | `gas_create_ability_task_node` |
| Add variables/graphs | `bp_*` graph tools for small Blueprint ability helpers |
| Verify replication shape | `net_describe_blueprint_replication`, `network_debug_replication`, PIE/log tools |
| Document the slice | `execution_journal_*`, `skill_package_vertical_slice_report` |

## MCP GAS Tools

Workstream B.3 adds a focused GAS authoring surface:

- `gas_create_ability` creates a Blueprint asset parented to `UGameplayAbility`
  or a supplied ability base class.
- `gas_create_gameplay_effect` creates a Blueprint `UGameplayEffect`.
- `gas_create_gameplay_cue` creates an actor or static GameplayCue notify.
- `gas_create_attribute_set` creates an AttributeSet Blueprint when the target
  project supports Blueprint AttributeSet subclasses.
- `gas_grant_ability`, `gas_apply_effect`, and `gas_add_tag` ensure an
  `AbilitySystemComponent` exists on the target Blueprint when requested and
  record auditable package metadata for the intended default grant/effect/tag.
- `gas_create_ability_task_node` adds a static BlueprintCallable AbilityTask
  factory call node to a GameplayAbility graph.

These tools create and annotate assets; they do not replace project-specific
C++ base classes for replicated attributes, input binding, prediction policy, or
runtime grant code. After using them, run `compile_blueprint_and_report` and a
small PIE validation slice.

## Working Example

Goal: create a health-and-dash ability slice.

1. Add a C++ character or player state that implements `IAbilitySystemInterface`
   and owns `UAbilitySystemComponent`.
2. Add `UHeroAttributeSet` with replicated `Health` and `MoveEnergy`.
3. Create tags such as `Ability.Movement.Dash`, `State.Stunned`, and
   `Cooldown.Dash`.
4. Create `GA_Dash` from a C++ `UGameplayAbility` base; require
   `MoveEnergy >= 25`, spend energy through a `GameplayEffect`, and apply a
   short cooldown tag.
5. Bind Enhanced Input to request activation by ability tag.
6. Run one server/client PIE pass: confirm the server owns the final movement,
   the owning client predicts or receives timely feedback, and other clients see
   the replicated result.
7. Record ability activation, attribute deltas, and any replication warnings in
   the execution journal.

## Validation Checklist

- ASC location is intentional: Pawn for disposable state, PlayerState for
  persistent state.
- Attributes replicate through an attribute set with clear `OnRep` handlers.
- Tags are documented and searchable.
- Ability grant and activation are verified in PIE, not only in editor assets.
- Networked abilities have either a prediction plan or a deliberate server-only
  plan.

## References

- Epic: Gameplay Ability System -
  https://dev.epicgames.com/documentation/unreal-engine/gameplay-ability-system-for-unreal-engine
- Epic: Gameplay Ability -
  https://dev.epicgames.com/documentation/unreal-engine/using-gameplay-abilities-in-unreal-engine
- Epic: Gameplay Attributes and Attribute Sets -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/gameplay-attributes-and-attribute-sets-for-the-gameplay-ability-system-in-unreal-engine
