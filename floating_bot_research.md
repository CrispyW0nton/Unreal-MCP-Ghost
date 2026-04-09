# Research: Proper Way to Create a Floating/Flying Bot in Unreal Engine

## The Problem We've Been Having

**BP_PassiveBot is a Character class**, which means it has:
- `CharacterMovementComponent` - designed for walking on ground with gravity
- Capsule collision that tries to stay on the ground
- Gravity by default
- Complex physics interactions

This is why the bot keeps falling to the ground - **Characters are meant to walk, not float!**

## The Correct Solution: Use FloatingPawnMovement

### What is FloatingPawnMovement?

From Unreal Engine documentation:
> "FloatingPawnMovement is a movement component that provides simple movement for any Pawn class. Limits on speed and acceleration are provided, while **gravity is not implemented**."

**Key Features:**
- ✅ **No gravity** - actors stay at their Z height
- ✅ Works with `AddMovementInput` - just like CharacterMovementComponent
- ✅ Smooth acceleration/deceleration
- ✅ Configurable max speed, acceleration, deceleration
- ✅ Built-in turning boost for responsive direction changes
- ✅ Simple collision handling
- ✅ **Works perfectly for flying enemies, drones, floating objects**

### Why This Is Perfect for Our Bot

1. **No Falling** - FloatingPawnMovement doesn't apply gravity
2. **Horizontal Plane Movement** - naturally maintains Z height
3. **AddMovementInput Works** - we can use the same approach we tried before
4. **AI Compatible** - works with AI Controllers for waypoint navigation
5. **Performance** - simpler than CharacterMovementComponent

## Implementation Plan

### Option 1: Create New Blueprint (Recommended)
1. Create a new Blueprint based on **Pawn** (not Character)
2. Add a **FloatingPawnMovement** component
3. Add mesh, collision, arrow components
4. Use `AddMovementInput` in Event Tick or custom events
5. Set `MaxSpeed`, `Acceleration`, `Deceleration` properties

### Option 2: Replace CharacterMovementComponent
1. Open BP_PassiveBot
2. Delete CharacterMovement component
3. Add FloatingPawnMovement component
4. Re-parent from Character to Pawn
5. Keep existing movement logic

## How FloatingPawnMovement Works

```
Event Tick (or Custom Event):
  ↓
AddMovementInput(ForwardVector, Scale)
  ↓
FloatingPawnMovement applies acceleration
  ↓
Smooth velocity change (no instant jumps)
  ↓
Actor moves forward without falling
```

**Properties to Configure:**
- `MaxSpeed` = 400.0 (or whatever speed you want)
- `Acceleration` = 2000.0 (how fast it reaches max speed)
- `Deceleration` = 2000.0 (how fast it stops when no input)
- `TurningBoost` = 8.0 (makes turns more responsive for waypoint navigation)

## Waypoint System with FloatingPawnMovement

For the 90-degree turn requirement:
1. Create BP_Waypoint with box trigger
2. On overlap, call `AddActorWorldRotation(0, 0, 90)` on the bot
3. FloatingPawnMovement will automatically handle the new forward direction
4. Bot continues moving in the new direction

## References

- [UFloatingPawnMovement Documentation](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Engine/UFloatingPawnMovement)
- [Flying with FloatingPawnMovement Tutorial](https://dev.to/winterturtle23/flying-with-floatingpawnmovement-in-unreal-engine-a-dronewood-dev-breakdown-546c)
- [Controlling Pawn with FloatingPawnMovement YouTube](https://www.youtube.com/watch?v=c30nwXJz9GY)

## Next Steps

We should create a new BP_FloatingBot based on Pawn class with FloatingPawnMovement component instead of trying to hack the Character class to work without gravity.
