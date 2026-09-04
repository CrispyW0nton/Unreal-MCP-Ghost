# UE5 Input Systems Reference
> Sources: Li, Marques/Sherry/Pereira/Fozi; synthesized for Unreal-MCP-Ghost.
> Updated: 2026-04-29

## Enhanced Input

UE5 projects should prefer Enhanced Input. `InputAction` assets describe semantic actions such as move, look, jump, interact, attack, and block. `InputMappingContext` assets map those actions to keyboard, mouse, gamepad, or touch inputs and can be layered by priority.

## Common Setup

- Create `IA_` assets with the correct value type: Digital, Axis1D, Axis2D, or Axis3D.
- Create `IMC_` assets and bind keys/sticks/buttons to actions.
- In local player startup, add the mapping context through the Enhanced Input Local Player Subsystem.
- In the pawn or controller, bind action events such as Started, Triggered, Completed, Canceled, and Ongoing.

## Gameplay Patterns

- Move: Axis2D -> control rotation yaw -> forward/right vectors -> `AddMovementInput`.
- Look: Axis2D -> `AddControllerYawInput` and `AddControllerPitchInput`.
- Jump: Digital Started -> `Jump`; Completed -> `StopJumping`.
- Interact/Attack/Block: Digital actions that call validated gameplay functions or interface calls.

## MCP Notes

- Use input asset listing plus graph inspection to verify actions and bindings.
- `add_blueprint_enhanced_input_action_node` expects a full `action_asset` path.
- If direct tools cannot read mapping details, use `exec_python` against `InputMappingContext` assets.

## Audit Checklist

- List all `IA_` and `IMC_` assets, action value types, key mappings, and binding Blueprints.
- Confirm the mapping context is added at runtime.
- Flag legacy input mappings mixed with Enhanced Input unless intentional.
