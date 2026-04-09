# Final Research Conclusion: Bot Movement Problem

## The Core Issue - FLYING MODE + BUOYANCY

After extensive research, I found the root cause:

**MOVE_Flying mode is affected by Physics Volumes and BUOYANCY!**

From EngineTypes.h documentation:
> "MOVE_Flying: Flying, ignoring the effects of gravity. **Affected by the current physics volume's fluid friction.**"

The character is floating upward because:
1. Flying mode disables gravity
2. BUT it's still affected by the default Physics Volume in the level
3. The Physics Volume has a **default buoyancy value** that pushes objects UP
4. This buoyancy force causes continuous upward movement

## The Solution

We have THREE options:

### Option 1: Set Gravity Scale to a Negative Value (RECOMMENDED)
- Keep Flying mode
- Set `GravityScale` to -1.0 or similar to counteract buoyancy
- This creates a downward force that balances the upward buoyancy
- Bot will move horizontally without drifting up or down

### Option 2: Disable Flying Mode Entirely  
- Use `MOVE_Walking` mode instead
- Disable gravity with `SetGravityEnabled(false)` or `GravityScale = 0`
- Use `SetActorLocation` with a timer to update position each frame
- This bypasses the CharacterMovementComponent's physics entirely

### Option 3: Create a Custom Physics Volume
- Place a Physics Volume in the level
- Set its Buoyancy to 0.0 to eliminate upward force
- Spawn bots inside this volume
- More complex, affects level design

Flying mode in CharacterMovementComponent:
- **Disables gravity completely**
- Has no built-in way to constrain vertical movement
- Even with bConstrainToPlane, something is causing upward drift
- This is NOT the right approach for a bot that needs to float at constant height

## The REAL Solution
**Stop using CharacterMovementComponent for this!**

Since the bot needs to:
1. Float at a constant height
2. Move forward smoothly
3. NOT be affected by gravity or physics

We should use:
**Simple SetActorLocation with a repeating timer**

This is much simpler and more predictable than fighting with CharacterMovementComponent's flying mode.

## Implementation Plan
1. Delete all the flying mode / AddMovementInput logic
2. In MoveForward event: Start a timer (0.016s = 60fps)
3. Timer function: Get current location, add (X, 0, 0), SetActorLocation
4. Bot moves forward at constant height, no physics involved
