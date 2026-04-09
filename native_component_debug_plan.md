# Native Component Access Debug Plan

## Problem
The `set_component_property` command reports "Component not found: CharacterMovement" even though `get_blueprint_components` shows CharacterMovement exists as a NativeC++ component.

## Root Cause Analysis

### What We Know
1. BP_PassiveBot has a CharacterMovement component (confirmed by get_blueprint_components)
2. CharacterMovement is a native C++ component from the ACharacter base class
3. The plugin's HandleSetComponentProperty function has two search paths:
   - SimpleConstructionScript (SCS) nodes - for user-added Blueprint components
   - Native components via CDO (Class Default Object) - for C++ components

### The Enhanced Code
We added native component support in HandleSetComponentProperty (lines 436-462):
```cpp
// If not found in SCS, try native C++ components from GeneratedClass CDO
if (!ComponentTemplate && Blueprint->GeneratedClass)
{
    UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Searching native components in GeneratedClass"));
    UObject* CDO = Blueprint->GeneratedClass->GetDefaultObject();
    if (CDO)
    {
        // Iterate over object properties to find component properties
        UE_LOG(LogTemp, Warning, TEXT("SetComponentProperty - Starting search for native component: %s"), *ComponentName);
        for (TFieldIterator<FObjectProperty> PropIt(Blueprint->GeneratedClass, EFieldIteratorFlags::IncludeSuper); PropIt; ++PropIt)
        {
            FObjectProperty* ObjProp = *PropIt;
            if (!ObjProp->PropertyClass || !ObjProp->PropertyClass->IsChildOf(UActorComponent::StaticClass()))
                continue;
            
            UE_LOG(LogTemp, Warning, TEXT("SetComponentProperty - Found native component property: %s (looking for: %s)"), *ObjProp->GetName(), *ComponentName);
            if (ObjProp->GetName() == ComponentName)
            {
                // Get the actual component instance from the CDO
                ComponentTemplate = ObjProp->GetObjectPropertyValue_InContainer(CDO);
                UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Found native component: %s (Class: %s)"),
                    *ComponentName,
                    ComponentTemplate ? *ComponentTemplate->GetClass()->GetName() : TEXT("NULL"));
                break;
            }
        }
        
        if (!ComponentTemplate)
        {
            UE_LOG(LogTemp, Warning, TEXT("SetComponentProperty - Native component %s NOT FOUND after searching all properties"), *ComponentName);
        }
    }
}
```

### Debug Logging Added
We've added Warning-level logs to diagnose the issue:
1. "Starting search for native component: X" - Confirms search begins
2. "Found native component property: X (looking for: Y)" - Shows each component property found during iteration
3. "Native component X NOT FOUND after searching all properties" - Confirms search completed without match

## Expected Behavior After Rebuild

### Test Command
```bash
python3 sandbox_ue5cli.py set_component_property '{"blueprint_name":"BP_PassiveBot","component_name":"CharacterMovement","property_name":"GravityScale","property_value":0.0}'
```

### Expected Logs in Unreal Engine Output Log
If working correctly:
```
SetComponentProperty - Blueprint: BP_PassiveBot, Component: CharacterMovement, Property: GravityScale
SetComponentProperty - Blueprint found: BP_PassiveBot (Class: BP_PassiveBot_C)
SetComponentProperty - Searching for component CharacterMovement in blueprint nodes
SetComponentProperty - Searching native components in GeneratedClass
SetComponentProperty - Starting search for native component: CharacterMovement
SetComponentProperty - Found native component property: Mesh (looking for: CharacterMovement)
SetComponentProperty - Found native component property: CharacterMovement (looking for: CharacterMovement)
SetComponentProperty - Found native component: CharacterMovement (Class: CharacterMovementComponent)
SetComponentProperty - Property found: GravityScale (Type: float)
SetComponentProperty - Attempting to set property GravityScale
```

If still failing, we'll see:
- Which native component properties ARE being found
- Whether CharacterMovement appears in the list
- The exact name mismatch if any

## Potential Issues to Investigate

### 1. Property Name Mismatch
The component might be stored under a different property name in C++. Common patterns:
- "CharacterMovement" (what we're looking for)
- "CharacterMovementComponent"
- "MovementComponent"

### 2. Field Iterator Flags
The `EFieldIteratorFlags::IncludeSuper` should include inherited properties from ACharacter, but there may be other flags needed.

### 3. Property Class Check
The condition `ObjProp->PropertyClass->IsChildOf(UActorComponent::StaticClass())` filters for components. CharacterMovementComponent should inherit from UActorComponent via:
- UCharacterMovementComponent → UPawnMovementComponent → UNavMovementComponent → UMovementComponent → UActorComponent

## Rebuild Steps

1. **Pull latest changes:**
   ```
   cd C:\Users\NewAdmin\Documents\Academy of Art University\2026\Gam115\UnrealProject\Lab3C\Plugins\UnrealMCP
   git pull origin genspark_ai_developer
   ```

2. **Clean and rebuild in Visual Studio 2022:**
   - Open the solution
   - Right-click the UnrealMCP project → Clean
   - Right-click the UnrealMCP project → Rebuild

3. **Restart Unreal Engine:**
   - Close Unreal Engine completely
   - Relaunch the project

4. **Test the command and check Output Log:**
   - Run the test command
   - Open Window → Developer Tools → Output Log
   - Filter for "SetComponentProperty"
   - Copy all relevant log lines

## Next Steps Based on Logs

### If We See Native Components But Wrong Name
- Update the search to try common variations
- Add fallback searches for "CharacterMovementComponent", "MovementComponent"

### If We See NO Native Components
- The field iterator may not be working correctly
- Try alternative approaches:
  - Use `GetDefaultObject()->GetComponents()` method
  - Iterate `UBlueprintGeneratedClass::ComponentTemplates`
  - Use reflection to find all UObject* properties

### If CharacterMovement Appears But Still Fails
- Check if `GetObjectPropertyValue_InContainer` returns null
- Verify the property value extraction logic
- Check if the component needs special handling like SpringArm

## Success Criteria
Once working, the command should:
1. Find the CharacterMovement component via CDO iteration
2. Locate the GravityScale property (float type)
3. Set the value to 0.0
4. Return success JSON
5. Allow BP_PassiveBot to float without falling when compiled

## Reference: How get_blueprint_components Works
The get_blueprint_components command successfully finds native components. Let's compare its approach:
- It also iterates TFieldIterator<FObjectProperty>
- Uses the same flags: EFieldIteratorFlags::IncludeSuper
- Same filter: IsChildOf(UActorComponent::StaticClass())
- Same property name access: ObjProp->GetName()

This means our approach SHOULD work - the debug logs will reveal why it doesn't.
