# RESEARCH FINDINGS: Why BP_PassiveBot Doesn't Move

## ROOT CAUSE DISCOVERED

**AddMovementInput REQUIRES a Controller to work!**

### Key Facts:
1. AddMovementInput accumulates input vectors that are consumed by the Character/Pawn
2. Character class automatically handles this input and applies movement
3. **BUT**: The Character MUST be possessed by a Controller (Player or AI) for this to work!
4. When spawned without a controller, AddMovementInput does nothing

### From Documentation (APawn::AddMovementInput):
> "Subclasses such as Character and DefaultPawn automatically handle this input and move."

### From Community Forums:
- "Auto Possess AI must be set to 'Placed in World or Spawned'"
- "Spawned characters can't move without being possessed by an AI Controller"
- "AddMovementInput only works on possessed pawns/characters"

## THE SOLUTION

### Option 1: Set Auto Possess AI (Easiest)
In BP_PassiveBot Class Defaults:
- Pawn → AI → Auto Possess AI = **"Placed in World or Spawned"**
- This automatically creates and assigns an AIController when the bot spawns

### Option 2: Manually Spawn AI Controller
In MoveForward event:
1. SpawnAIController
2. Possess the character with that controller
3. Then AddMovementInput will work

### Option 3: Direct Movement (No Controller)
Instead of AddMovementInput, use:
- SetActorLocation (direct teleport)
- AddActorWorldOffset (direct offset)
- LaunchCharacter (physics-based)

## RECOMMENDATION
Use Option 1: Set "Auto Possess AI" to "Placed in World or Spawned"
This is the cleanest solution that maintains the Character movement system.
