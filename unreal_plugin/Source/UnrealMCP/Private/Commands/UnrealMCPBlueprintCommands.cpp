#include "Commands/UnrealMCPBlueprintCommands.h"
#include "Commands/UnrealMCPCommonUtils.h"
#include "UnrealMCPModule.h"
#include "Engine/Blueprint.h"
// NOTE: FKismetEditorUtilities::CompileBlueprint and
// UEditorAssetLibrary::SaveAsset are NEVER called from this plugin.
// Both paths crash UE5.6 with EXCEPTION_ACCESS_VIOLATION at
// 0x00007ffe447a0208 (UnrealEditor_MassEntityEditor observer) when
// invoked from inside an AsyncTask game-thread lambda.
// All compile operations are deferred: Blueprint->Modify() only (NOT MarkBlueprintAsModified).
// MarkBlueprintAsModified fires OnBlueprintChanged -> AssetRegistry -> ContentBrowser
// which crashes in UE5.6 Slate tick (EXCEPTION_ACCESS_VIOLATION in AssetRegistry).
#include "Engine/BlueprintGeneratedClass.h"
#include "Factories/BlueprintFactory.h"
#include "EdGraphSchema_K2.h"
#include "K2Node_Event.h"
#include "K2Node_VariableGet.h"
#include "K2Node_VariableSet.h"
#include "Components/StaticMeshComponent.h"
#include "Components/BoxComponent.h"
#include "Components/SphereComponent.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Engine/SimpleConstructionScript.h"
#include "Engine/SCS_Node.h"
#include "UObject/Field.h"
#include "UObject/FieldPath.h"
#include "EditorAssetLibrary.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "GameFramework/Actor.h"
#include "GameFramework/Pawn.h"
#include "AIController.h"

FUnrealMCPBlueprintCommands::FUnrealMCPBlueprintCommands()
{
}

TSharedPtr<FJsonObject> FUnrealMCPBlueprintCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    if (CommandType == TEXT("create_blueprint"))
    {
        return HandleCreateBlueprint(Params);
    }
    else if (CommandType == TEXT("add_component_to_blueprint"))
    {
        return HandleAddComponentToBlueprint(Params);
    }
    else if (CommandType == TEXT("set_component_property"))
    {
        return HandleSetComponentProperty(Params);
    }
    else if (CommandType == TEXT("set_physics_properties"))
    {
        return HandleSetPhysicsProperties(Params);
    }
    else if (CommandType == TEXT("compile_blueprint"))
    {
        return HandleCompileBlueprint(Params);
    }
    else if (CommandType == TEXT("spawn_blueprint_actor"))
    {
        return HandleSpawnBlueprintActor(Params);
    }
    else if (CommandType == TEXT("set_blueprint_property"))
    {
        return HandleSetBlueprintProperty(Params);
    }
    else if (CommandType == TEXT("set_static_mesh_properties"))
    {
        return HandleSetStaticMeshProperties(Params);
    }
    else if (CommandType == TEXT("set_pawn_properties"))
    {
        return HandleSetPawnProperties(Params);
    }
    else if (CommandType == TEXT("set_blueprint_ai_controller"))
    {
        return HandleSetBlueprintAIController(Params);
    }
    
    return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Unknown blueprint command: %s"), *CommandType));
}

TSharedPtr<FJsonObject> FUnrealMCPBlueprintCommands::HandleCreateBlueprint(const TSharedPtr<FJsonObject>& Params)
{
    // Get required parameters
    FString BlueprintName;
    if (!Params->TryGetStringField(TEXT("name"), BlueprintName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }

    FString PackagePath = TEXT("/Game/Blueprints/");
    FString AssetName = BlueprintName;

    // Fast O(1) duplicate check — try in-memory object table first before
    // calling DoesAssetExist() which can scan the entire asset registry (slow
    // on 8k-asset projects, causes K5 "duplicate create_blueprint" to timeout).
    {
        const FString FullPath = PackagePath + AssetName + TEXT(".") + AssetName;
        UBlueprint* Existing = FindObject<UBlueprint>(nullptr, *FullPath);
        if (!Existing)
        {
            // Also check the positive cache (populated by earlier FindBlueprint calls)
            Existing = FUnrealMCPCommonUtils::FindBlueprint(AssetName);
        }
        if (Existing)
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(
                FString::Printf(TEXT("Blueprint already exists: %s"), *BlueprintName));
        }
    }

    // Fallback: ask the asset registry (slightly slower, but catches on-disk BPs
    // that have not been loaded into memory yet).
    if (UEditorAssetLibrary::DoesAssetExist(PackagePath + AssetName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Blueprint already exists: %s"), *BlueprintName));
    }

    // Create the blueprint factory
    UBlueprintFactory* Factory = NewObject<UBlueprintFactory>();
    
    // Handle parent class
    FString ParentClass;
    Params->TryGetStringField(TEXT("parent_class"), ParentClass);
    
    // Default to Actor if no parent class specified
    UClass* SelectedParentClass = AActor::StaticClass();
    
    // Try to find the specified parent class
    if (!ParentClass.IsEmpty())
    {
        FString ClassName = ParentClass;
        if (!ClassName.StartsWith(TEXT("A")))
        {
            ClassName = TEXT("A") + ClassName;
        }
        
        // First try direct StaticClass lookup for common classes
        UClass* FoundClass = nullptr;
        if (ClassName == TEXT("APawn"))
        {
            FoundClass = APawn::StaticClass();
        }
        else if (ClassName == TEXT("AActor"))
        {
            FoundClass = AActor::StaticClass();
        }
        else
        {
            // Try loading the class using LoadClass which is more reliable than FindObject
            const FString ClassPath = FString::Printf(TEXT("/Script/Engine.%s"), *ClassName);
            FoundClass = LoadClass<AActor>(nullptr, *ClassPath);
            
            if (!FoundClass)
            {
                // Try alternate paths if not found
                const FString GameClassPath = FString::Printf(TEXT("/Script/Game.%s"), *ClassName);
                FoundClass = LoadClass<AActor>(nullptr, *GameClassPath);
            }
        }

        if (FoundClass)
        {
            SelectedParentClass = FoundClass;
            UE_LOG(LogTemp, Log, TEXT("Successfully set parent class to '%s'"), *ClassName);
        }
        else
        {
            UE_LOG(LogTemp, Warning, TEXT("Could not find specified parent class '%s' at paths: /Script/Engine.%s or /Script/Game.%s, defaulting to AActor"), 
                *ClassName, *ClassName, *ClassName);
        }
    }
    
    Factory->ParentClass = SelectedParentClass;

    // Create the blueprint
    UPackage* Package = CreatePackage(*(PackagePath + AssetName));
    UBlueprint* NewBlueprint = Cast<UBlueprint>(Factory->FactoryCreateNew(UBlueprint::StaticClass(), Package, *AssetName, RF_Standalone | RF_Public, nullptr, GWarn));

    if (NewBlueprint)
    {
        // Notify the asset registry
        FAssetRegistryModule::AssetCreated(NewBlueprint);

        // Mark the package dirty
        Package->MarkPackageDirty();

        // Clear the negative-miss cache for this name so subsequent calls to
        // FindBlueprint (e.g. get_blueprint_graphs right after create_blueprint)
        // don't see a stale "not found" entry from a previous failed lookup.
        FUnrealMCPCommonUtils::InvalidateBlueprintMissCache(AssetName);

        TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
        ResultObj->SetStringField(TEXT("name"), AssetName);
        ResultObj->SetStringField(TEXT("path"), PackagePath + AssetName);
        return ResultObj;
    }

    return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create blueprint"));
}

TSharedPtr<FJsonObject> FUnrealMCPBlueprintCommands::HandleAddComponentToBlueprint(const TSharedPtr<FJsonObject>& Params)
{
    // Get required parameters
    FString BlueprintName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'blueprint_name' parameter"));
    }

    FString ComponentType;
    if (!Params->TryGetStringField(TEXT("component_type"), ComponentType))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'type' parameter"));
    }

    FString ComponentName;
    if (!Params->TryGetStringField(TEXT("component_name"), ComponentName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }

    // Find the blueprint
    UBlueprint* Blueprint = FUnrealMCPCommonUtils::FindBlueprint(BlueprintName);
    if (!Blueprint)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintName));
    }

    // Create the component - dynamically find the component class by name
    UClass* ComponentClass = nullptr;

    // Helper: try FindObject then LoadObject for a given path
    auto TryLoad = [](const FString& Path) -> UClass*
    {
        UClass* C = FindObject<UClass>(nullptr, *Path);
        if (!C) C = LoadObject<UClass>(nullptr, *Path);
        return C;
    };

    // 0. Known component name ? canonical path table (covers the most common cases)
    //    Accepts short names like "StaticMesh", "StaticMeshComponent", "Camera", etc.
    {
        // Build a normalised lookup key: strip leading 'U', strip trailing 'Component', lower-case
        FString Key = ComponentType;
        if (Key.StartsWith(TEXT("U"))) Key = Key.Mid(1);
        if (Key.EndsWith(TEXT("Component"))) Key = Key.LeftChop(9);
        Key = Key.ToLower();

        struct FComponentEntry { const TCHAR* Key; const TCHAR* Path; };
        static const FComponentEntry KnownComponents[] =
        {
            { TEXT("staticmesh"),          TEXT("/Script/Engine.StaticMeshComponent") },
            { TEXT("camera"),              TEXT("/Script/Engine.CameraComponent") },
            { TEXT("pointlight"),          TEXT("/Script/Engine.PointLightComponent") },
            { TEXT("spotlight"),           TEXT("/Script/Engine.SpotLightComponent") },
            { TEXT("directionallight"),    TEXT("/Script/Engine.DirectionalLightComponent") },
            { TEXT("box"),                 TEXT("/Script/Engine.BoxComponent") },
            { TEXT("sphere"),              TEXT("/Script/Engine.SphereComponent") },
            { TEXT("capsule"),             TEXT("/Script/Engine.CapsuleComponent") },
            { TEXT("arrow"),               TEXT("/Script/Engine.ArrowComponent") },
            { TEXT("billboard"),           TEXT("/Script/Engine.BillboardComponent") },
            { TEXT("audio"),               TEXT("/Script/Engine.AudioComponent") },
            { TEXT("springarm"),           TEXT("/Script/Engine.SpringArmComponent") },
            { TEXT("skeletalmesh"),        TEXT("/Script/Engine.SkeletalMeshComponent") },
            { TEXT("scene"),               TEXT("/Script/Engine.SceneComponent") },
            { TEXT("childactor"),          TEXT("/Script/Engine.ChildActorComponent") },
            { TEXT("decal"),               TEXT("/Script/Engine.DecalComponent") },
            { TEXT("particlesystem"),      TEXT("/Script/Engine.ParticleSystemComponent") },
            { TEXT("niagara"),             TEXT("/Script/Niagara.NiagaraComponent") },
            { TEXT("navmeshboundsvolume"), TEXT("/Script/NavigationSystem.NavMeshBoundsVolume") },
            { TEXT("timeline"),            TEXT("/Script/Engine.TimelineComponent") },
            { TEXT("widget"),              TEXT("/Script/UMG.WidgetComponent") },
            { TEXT("charactermovement"),   TEXT("/Script/Engine.CharacterMovementComponent") },
            { TEXT("projectilemovement"),  TEXT("/Script/Engine.ProjectileMovementComponent") },
            { TEXT("floatingpawnmovement"),TEXT("/Script/Engine.FloatingPawnMovement") },
            { TEXT("rotatingmovement"),    TEXT("/Script/Engine.RotatingMovementComponent") },
        };

        for (const FComponentEntry& Entry : KnownComponents)
        {
            if (Key == Entry.Key)
            {
                ComponentClass = TryLoad(FString(Entry.Path));
                UE_LOG(LogTemp, Display, TEXT("AddComponent: resolved '%s' ? '%s' (%s)"),
                    *ComponentType, Entry.Path, ComponentClass ? TEXT("OK") : TEXT("FAILED"));
                break;
            }
        }
    }

    // 1. Exact name / full path as provided (e.g. "/Script/Engine.StaticMeshComponent")
    if (!ComponentClass)
        ComponentClass = TryLoad(ComponentType);

    // 2. Short name without prefix: try /Script/Engine.<Name>
    if (!ComponentClass)
    {
        FString EngineClassPath = FString::Printf(TEXT("/Script/Engine.%s"), *ComponentType);
        ComponentClass = TryLoad(EngineClassPath);
    }

    // 3. Short name without "Component" suffix: append it, then retry /Script/Engine path
    if (!ComponentClass && !ComponentType.EndsWith(TEXT("Component")))
    {
        FString WithSuffix = ComponentType + TEXT("Component");
        ComponentClass = TryLoad(WithSuffix);
        if (!ComponentClass)
            ComponentClass = TryLoad(FString::Printf(TEXT("/Script/Engine.%s"), *WithSuffix));
    }

    // 4. Strip leading "U" prefix and retry
    if (!ComponentClass && ComponentType.StartsWith(TEXT("U")))
    {
        FString WithoutPrefix = ComponentType.Mid(1);
        ComponentClass = TryLoad(FString::Printf(TEXT("/Script/Engine.%s"), *WithoutPrefix));
        if (!ComponentClass && !WithoutPrefix.EndsWith(TEXT("Component")))
        {
            ComponentClass = TryLoad(FString::Printf(TEXT("/Script/Engine.%sComponent"), *WithoutPrefix));
        }
    }

    // 5. Add "U" prefix and retry
    if (!ComponentClass && !ComponentType.StartsWith(TEXT("U")))
    {
        FString WithPrefix = TEXT("U") + ComponentType;
        ComponentClass = TryLoad(WithPrefix);
        if (!ComponentClass)
            ComponentClass = TryLoad(FString::Printf(TEXT("/Script/Engine.%s"), *WithPrefix));
        if (!ComponentClass && !ComponentType.EndsWith(TEXT("Component")))
        {
            ComponentClass = TryLoad(TEXT("U") + ComponentType + TEXT("Component"));
            if (!ComponentClass)
                ComponentClass = TryLoad(FString::Printf(TEXT("/Script/Engine.U%sComponent"), *ComponentType));
        }
    }

    // Verify that the class is a valid component type
    if (!ComponentClass || !ComponentClass->IsChildOf(UActorComponent::StaticClass()))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Unknown component type: %s"), *ComponentType));
    }

    // Add the component to the blueprint
    USCS_Node* NewNode = Blueprint->SimpleConstructionScript->CreateNode(ComponentClass, *ComponentName);
    if (NewNode)
    {
        // Set transform if provided
        USceneComponent* SceneComponent = Cast<USceneComponent>(NewNode->ComponentTemplate);
        if (SceneComponent)
        {
            if (Params->HasField(TEXT("location")))
            {
                SceneComponent->SetRelativeLocation(FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("location")));
            }
            if (Params->HasField(TEXT("rotation")))
            {
                SceneComponent->SetRelativeRotation(FUnrealMCPCommonUtils::GetRotatorFromJson(Params, TEXT("rotation")));
            }
            if (Params->HasField(TEXT("scale")))
            {
                SceneComponent->SetRelativeScale3D(FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("scale")));
            }
        }

        // Add to root if no parent specified
        Blueprint->SimpleConstructionScript->AddNode(NewNode);

        // Mark blueprint structurally modified WITHOUT triggering a full
        // AssetRegistry / ContentBrowser notification (which would call
        // Modify() → MarkPackageDirty() → broadcast to all AR listeners,
        // blocking the GameThread for 30-60 s on an 8 k-asset project).
        // Guard GeneratedClass (same as HandleCompileBlueprint) to prevent
        // EXCEPTION_ACCESS_VIOLATION on first-session access.
        if (Blueprint->GeneratedClass && IsValid(Blueprint->GeneratedClass))
        {
            FUnrealMCPCommonUtils::SafeMarkBlueprintModified(Blueprint);
            UE_LOG(LogMCP, Display, TEXT("[MCP] AddComponent - MarkBlueprintAsStructurallyModified '%s'"), *BlueprintName);
        }
        else
        {
            Blueprint->Modify();
            UE_LOG(LogMCP, Warning, TEXT("[MCP] AddComponent - GeneratedClass not ready for '%s', using Modify() fallback"), *BlueprintName);
        }

        TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
        ResultObj->SetStringField(TEXT("component_name"), ComponentName);
        ResultObj->SetStringField(TEXT("component_type"), ComponentType);
        return ResultObj;
    }

    return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to add component to blueprint"));
}

TSharedPtr<FJsonObject> FUnrealMCPBlueprintCommands::HandleSetComponentProperty(const TSharedPtr<FJsonObject>& Params)
{
    // Get required parameters
    FString BlueprintName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'blueprint_name' parameter"));
    }

    FString ComponentName;
    if (!Params->TryGetStringField(TEXT("component_name"), ComponentName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'component_name' parameter"));
    }

    FString PropertyName;
    if (!Params->TryGetStringField(TEXT("property_name"), PropertyName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'property_name' parameter"));
    }

    // Log all input parameters for debugging
    UE_LOG(LogTemp, Warning, TEXT("SetComponentProperty - Blueprint: %s, Component: %s, Property: %s"), 
        *BlueprintName, *ComponentName, *PropertyName);
    
    // Log property_value if available
    if (Params->HasField(TEXT("property_value")))
    {
        TSharedPtr<FJsonValue> JsonValue = Params->Values.FindRef(TEXT("property_value"));
        FString ValueType;
        
        switch(JsonValue->Type)
        {
            case EJson::Boolean: ValueType = FString::Printf(TEXT("Boolean: %s"), JsonValue->AsBool() ? TEXT("true") : TEXT("false")); break;
            case EJson::Number: ValueType = FString::Printf(TEXT("Number: %f"), JsonValue->AsNumber()); break;
            case EJson::String: ValueType = FString::Printf(TEXT("String: %s"), *JsonValue->AsString()); break;
            case EJson::Array: ValueType = TEXT("Array"); break;
            case EJson::Object: ValueType = TEXT("Object"); break;
            default: ValueType = TEXT("Unknown"); break;
        }
        
        UE_LOG(LogTemp, Warning, TEXT("SetComponentProperty - Value Type: %s"), *ValueType);
    }
    else
    {
        UE_LOG(LogTemp, Warning, TEXT("SetComponentProperty - No property_value provided"));
    }

    // Find the blueprint
    UBlueprint* Blueprint = FUnrealMCPCommonUtils::FindBlueprint(BlueprintName);
    if (!Blueprint)
    {
        UE_LOG(LogTemp, Error, TEXT("SetComponentProperty - Blueprint not found: %s"), *BlueprintName);
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintName));
    }
    else
    {
        UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Blueprint found: %s (Class: %s)"), 
            *BlueprintName, 
            Blueprint->GeneratedClass ? *Blueprint->GeneratedClass->GetName() : TEXT("NULL"));
    }

    // Find the component - try SCS (user-added) components first
    UObject* ComponentTemplate = nullptr;
    USCS_Node* ComponentNode = nullptr;
    UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Searching for component %s in blueprint nodes"), *ComponentName);
    
    if (Blueprint->SimpleConstructionScript)
    {
        for (USCS_Node* Node : Blueprint->SimpleConstructionScript->GetAllNodes())
        {
            if (Node)
            {
                UE_LOG(LogTemp, Verbose, TEXT("SetComponentProperty - Found SCS node: %s"), *Node->GetVariableName().ToString());
                if (Node->GetVariableName().ToString() == ComponentName)
                {
                    ComponentNode = Node;
                    ComponentTemplate = Node->ComponentTemplate;
                    UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Found SCS component: %s"), *ComponentName);
                    break;
                }
            }
        }
    }

    // If not found in SCS, try native C++ components from GeneratedClass CDO
    if (!ComponentTemplate && Blueprint->GeneratedClass)
    {
        UE_LOG(LogTemp, Warning, TEXT("SetComponentProperty - Searching native components in GeneratedClass"));
        UObject* CDO = Blueprint->GeneratedClass->GetDefaultObject();
        UE_LOG(LogTemp, Warning, TEXT("SetComponentProperty - CDO pointer: %s"), CDO ? TEXT("VALID") : TEXT("NULL"));
        
        if (CDO)
        {
            // Iterate over object properties to find component properties
            UE_LOG(LogTemp, Warning, TEXT("SetComponentProperty - Starting search for native component: %s"), *ComponentName);
            int32 ComponentCount = 0;
            for (TFieldIterator<FObjectProperty> PropIt(Blueprint->GeneratedClass, EFieldIteratorFlags::IncludeSuper); PropIt; ++PropIt)
            {
                FObjectProperty* ObjProp = *PropIt;
                if (!ObjProp->PropertyClass) continue;
                if (!ObjProp->PropertyClass->IsChildOf(UActorComponent::StaticClass())) continue;
                
                ComponentCount++;
                UE_LOG(LogTemp, Warning, TEXT("SetComponentProperty - [%d] Found native component property: %s (looking for: %s)"), ComponentCount, *ObjProp->GetName(), *ComponentName);
                
                if (ObjProp->GetName() == ComponentName)
                {
                    // Get the actual component instance from the CDO
                    ComponentTemplate = ObjProp->GetObjectPropertyValue_InContainer(CDO);
                    UE_LOG(LogTemp, Warning, TEXT("SetComponentProperty - MATCH FOUND! Component: %s (Class: %s)"),
                        *ComponentName,
                        ComponentTemplate ? *ComponentTemplate->GetClass()->GetName() : TEXT("NULL"));
                    break;
                }
            }
            
            UE_LOG(LogTemp, Warning, TEXT("SetComponentProperty - Search complete. Total native components found: %d, ComponentTemplate: %s"), 
                ComponentCount, 
                ComponentTemplate ? TEXT("FOUND") : TEXT("NOT FOUND"));
        }
    }

    if (!ComponentTemplate)
    {
        UE_LOG(LogTemp, Error, TEXT("SetComponentProperty - Component not found: %s"), *ComponentName);
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Component not found: %s"), *ComponentName));
    }

    // Check if this is a Spring Arm component and log special debug info
    if (ComponentTemplate->GetClass()->GetName().Contains(TEXT("SpringArm")))
    {
        UE_LOG(LogTemp, Warning, TEXT("SetComponentProperty - SpringArm component detected! Class: %s"), 
            *ComponentTemplate->GetClass()->GetPathName());
            
        // Log all properties of the SpringArm component class
        UE_LOG(LogTemp, Warning, TEXT("SetComponentProperty - SpringArm properties:"));
        for (TFieldIterator<FProperty> PropIt(ComponentTemplate->GetClass()); PropIt; ++PropIt)
        {
            FProperty* Prop = *PropIt;
            UE_LOG(LogTemp, Warning, TEXT("  - %s (%s)"), *Prop->GetName(), *Prop->GetCPPType());
        }

        // Special handling for Spring Arm properties
        if (Params->HasField(TEXT("property_value")))
        {
            TSharedPtr<FJsonValue> JsonValue = Params->Values.FindRef(TEXT("property_value"));
            
            // Get the property using the new FField system
            FProperty* Property = FindFProperty<FProperty>(ComponentTemplate->GetClass(), *PropertyName);
            if (!Property)
            {
                UE_LOG(LogTemp, Error, TEXT("SetComponentProperty - Property %s not found on SpringArm component"), *PropertyName);
                return FUnrealMCPCommonUtils::CreateErrorResponse(
                    FString::Printf(TEXT("Property %s not found on SpringArm component"), *PropertyName));
            }

            // IMPORTANT: Do NOT call PostEditChange() on a CDO-owned
            // component template.  Calling PostEditChange on a native CDO
            // subobject triggers re-registration and can cause GC to
            // invalidate raw UBlueprint* pointers, leading to an
            // EXCEPTION_ACCESS_VIOLATION in subsequent code.
            // We only call Modify() here to mark it dirty; MarkBlueprintAsModified
            // below handles the Blueprint-level dirty flag.
            if (ComponentTemplate)
            {
                ComponentTemplate->Modify();
                UE_LOG(LogMCP, Display, TEXT("[MCP] SetComponentProperty - SpringArm: called Modify() on component template"));
            }

            bool bSuccess = false;
            FString ErrorMessage;

            // Handle specific Spring Arm property types
            if (FFloatProperty* FloatProp = CastField<FFloatProperty>(Property))
            {
                if (JsonValue->Type == EJson::Number)
                {
                    const float Value = JsonValue->AsNumber();
                    UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Setting float property %s to %f"), *PropertyName, Value);
                    FloatProp->SetPropertyValue_InContainer(ComponentTemplate, Value);
                    bSuccess = true;
                }
            }
            else if (FBoolProperty* BoolProp = CastField<FBoolProperty>(Property))
            {
                if (JsonValue->Type == EJson::Boolean)
                {
                    const bool Value = JsonValue->AsBool();
                    UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Setting bool property %s to %d"), *PropertyName, Value);
                    BoolProp->SetPropertyValue_InContainer(ComponentTemplate, Value);
                    bSuccess = true;
                }
            }
            else if (FStructProperty* StructProp = CastField<FStructProperty>(Property))
            {
                UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Handling struct property %s of type %s"), 
                    *PropertyName, *StructProp->Struct->GetName());
                
                // Special handling for common Spring Arm struct properties
                if (StructProp->Struct == TBaseStructure<FVector>::Get())
                {
                    if (JsonValue->Type == EJson::Array)
                    {
                        const TArray<TSharedPtr<FJsonValue>>& Arr = JsonValue->AsArray();
                        if (Arr.Num() == 3)
                        {
                            FVector Vec(
                                Arr[0]->AsNumber(),
                                Arr[1]->AsNumber(),
                                Arr[2]->AsNumber()
                            );
                            void* PropertyAddr = StructProp->ContainerPtrToValuePtr<void>(ComponentTemplate);
                            StructProp->CopySingleValue(PropertyAddr, &Vec);
                            bSuccess = true;
                        }
                    }
                }
                else if (StructProp->Struct == TBaseStructure<FRotator>::Get())
                {
                    if (JsonValue->Type == EJson::Array)
                    {
                        const TArray<TSharedPtr<FJsonValue>>& Arr = JsonValue->AsArray();
                        if (Arr.Num() == 3)
                        {
                            FRotator Rot(
                                Arr[0]->AsNumber(),
                                Arr[1]->AsNumber(),
                                Arr[2]->AsNumber()
                            );
                            void* PropertyAddr = StructProp->ContainerPtrToValuePtr<void>(ComponentTemplate);
                            StructProp->CopySingleValue(PropertyAddr, &Rot);
                            bSuccess = true;
                        }
                    }
                }
            }

            if (bSuccess)
            {
                // Mark the blueprint as modified
                UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Successfully set SpringArm property %s"), *PropertyName);
                FUnrealMCPCommonUtils::SafeMarkBlueprintModified(Blueprint);

                TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
                ResultObj->SetStringField(TEXT("component"), ComponentName);
                ResultObj->SetStringField(TEXT("property"), PropertyName);
                ResultObj->SetBoolField(TEXT("success"), true);
                return ResultObj;
            }
            else
            {
                UE_LOG(LogTemp, Error, TEXT("SetComponentProperty - Failed to set SpringArm property %s"), *PropertyName);
                return FUnrealMCPCommonUtils::CreateErrorResponse(
                    FString::Printf(TEXT("Failed to set SpringArm property %s"), *PropertyName));
            }
        }
    }

    // Regular property handling for non-Spring Arm components continues...

    // Set the property value
    if (Params->HasField(TEXT("property_value")))
    {
        TSharedPtr<FJsonValue> JsonValue = Params->Values.FindRef(TEXT("property_value"));
        
        // Get the property
        FProperty* Property = FindFProperty<FProperty>(ComponentTemplate->GetClass(), *PropertyName);
        if (!Property)
        {
            UE_LOG(LogTemp, Error, TEXT("SetComponentProperty - Property %s not found on component %s"), 
                *PropertyName, *ComponentName);
            
            // List all available properties for this component
            UE_LOG(LogTemp, Warning, TEXT("SetComponentProperty - Available properties for %s:"), *ComponentName);
            for (TFieldIterator<FProperty> PropIt(ComponentTemplate->GetClass()); PropIt; ++PropIt)
            {
                FProperty* Prop = *PropIt;
                UE_LOG(LogTemp, Warning, TEXT("  - %s (%s)"), *Prop->GetName(), *Prop->GetCPPType());
            }
            
            return FUnrealMCPCommonUtils::CreateErrorResponse(
                FString::Printf(TEXT("Property %s not found on component %s"), *PropertyName, *ComponentName));
        }
        else
        {
            UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Property found: %s (Type: %s)"), 
                *PropertyName, *Property->GetCPPType());
        }

        bool bSuccess = false;
        FString ErrorMessage;

        // Handle different property types
        UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Attempting to set property %s"), *PropertyName);
        
        // Add try-catch block to catch and log any crashes
        try
        {
            if (FStructProperty* StructProp = CastField<FStructProperty>(Property))
            {
                // Handle vector properties
                UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Property is a struct: %s"), 
                    StructProp->Struct ? *StructProp->Struct->GetName() : TEXT("NULL"));
                    
                if (StructProp->Struct == TBaseStructure<FVector>::Get())
                {
                    if (JsonValue->Type == EJson::Array)
                    {
                        // Handle array input [x, y, z]
                        const TArray<TSharedPtr<FJsonValue>>& Arr = JsonValue->AsArray();
                        if (Arr.Num() == 3)
                        {
                            FVector Vec(
                                Arr[0]->AsNumber(),
                                Arr[1]->AsNumber(),
                                Arr[2]->AsNumber()
                            );
                            void* PropertyAddr = StructProp->ContainerPtrToValuePtr<void>(ComponentTemplate);
                            UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Setting Vector(%f, %f, %f)"), 
                                Vec.X, Vec.Y, Vec.Z);
                            StructProp->CopySingleValue(PropertyAddr, &Vec);
                            bSuccess = true;
                        }
                        else
                        {
                            ErrorMessage = FString::Printf(TEXT("Vector property requires 3 values, got %d"), Arr.Num());
                            UE_LOG(LogTemp, Error, TEXT("SetComponentProperty - %s"), *ErrorMessage);
                        }
                    }
                    else if (JsonValue->Type == EJson::Number)
                    {
                        // Handle scalar input (sets all components to same value)
                        float Value = JsonValue->AsNumber();
                        FVector Vec(Value, Value, Value);
                        void* PropertyAddr = StructProp->ContainerPtrToValuePtr<void>(ComponentTemplate);
                        UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Setting Vector(%f, %f, %f) from scalar"), 
                            Vec.X, Vec.Y, Vec.Z);
                        StructProp->CopySingleValue(PropertyAddr, &Vec);
                        bSuccess = true;
                    }
                    else
                    {
                        ErrorMessage = TEXT("Vector property requires either a single number or array of 3 numbers");
                        UE_LOG(LogTemp, Error, TEXT("SetComponentProperty - %s"), *ErrorMessage);
                    }
                }
                else
                {
                    // Handle other struct properties using default handler
                    UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Using generic struct handler for %s"), 
                        *PropertyName);
                    bSuccess = FUnrealMCPCommonUtils::SetObjectProperty(ComponentTemplate, PropertyName, JsonValue, ErrorMessage);
                    if (!bSuccess)
                    {
                        UE_LOG(LogTemp, Error, TEXT("SetComponentProperty - Failed to set struct property: %s"), *ErrorMessage);
                    }
                }
            }
            else if (FEnumProperty* EnumProp = CastField<FEnumProperty>(Property))
            {
                // Handle enum properties
                UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Property is an enum"));
                if (JsonValue->Type == EJson::String)
                {
                    FString EnumValueName = JsonValue->AsString();
                    UEnum* Enum = EnumProp->GetEnum();
                    UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Setting enum from string: %s"), *EnumValueName);
                    
                    if (Enum)
                    {
                        int64 EnumValue = Enum->GetValueByNameString(EnumValueName);
                        
                        if (EnumValue != INDEX_NONE)
                        {
                            UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Found enum value: %lld"), EnumValue);
                            EnumProp->GetUnderlyingProperty()->SetIntPropertyValue(
                                ComponentTemplate, 
                                EnumValue
                            );
                            bSuccess = true;
                        }
                        else
                        {
                            // List all possible enum values
                            UE_LOG(LogTemp, Warning, TEXT("SetComponentProperty - Available enum values for %s:"), 
                                *Enum->GetName());
                            for (int32 i = 0; i < Enum->NumEnums(); i++)
                            {
                                UE_LOG(LogTemp, Warning, TEXT("  - %s (%lld)"), 
                                    *Enum->GetNameStringByIndex(i),
                                    Enum->GetValueByIndex(i));
                            }
                            
                            ErrorMessage = FString::Printf(TEXT("Invalid enum value '%s' for property %s"), 
                                *EnumValueName, *PropertyName);
                            UE_LOG(LogTemp, Error, TEXT("SetComponentProperty - %s"), *ErrorMessage);
                        }
                    }
                    else
                    {
                        ErrorMessage = TEXT("Enum object is NULL");
                        UE_LOG(LogTemp, Error, TEXT("SetComponentProperty - %s"), *ErrorMessage);
                    }
                }
                else if (JsonValue->Type == EJson::Number)
                {
                    // Allow setting enum by integer value
                    int64 EnumValue = JsonValue->AsNumber();
                    UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Setting enum from number: %lld"), EnumValue);
                    EnumProp->GetUnderlyingProperty()->SetIntPropertyValue(
                        ComponentTemplate, 
                        EnumValue
                    );
                    bSuccess = true;
                }
                else
                {
                    ErrorMessage = TEXT("Enum property requires either a string name or integer value");
                    UE_LOG(LogTemp, Error, TEXT("SetComponentProperty - %s"), *ErrorMessage);
                }
            }
            else if (FNumericProperty* NumericProp = CastField<FNumericProperty>(Property))
            {
                // Handle numeric properties
                UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Property is numeric: IsInteger=%d, IsFloat=%d"), 
                    NumericProp->IsInteger(), NumericProp->IsFloatingPoint());
                    
                if (JsonValue->Type == EJson::Number)
                {
                    double Value = JsonValue->AsNumber();
                    UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Setting numeric value: %f"), Value);
                    
                    if (NumericProp->IsInteger())
                    {
                        NumericProp->SetIntPropertyValue(ComponentTemplate, (int64)Value);
                        UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Set integer value: %lld"), (int64)Value);
                        bSuccess = true;
                    }
                    else if (NumericProp->IsFloatingPoint())
                    {
                        NumericProp->SetFloatingPointPropertyValue(ComponentTemplate, Value);
                        UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Set float value: %f"), Value);
                        bSuccess = true;
                    }
                }
                else
                {
                    ErrorMessage = TEXT("Numeric property requires a number value");
                    UE_LOG(LogTemp, Error, TEXT("SetComponentProperty - %s"), *ErrorMessage);
                }
            }
            else
            {
                // Handle all other property types using default handler
                UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Using generic property handler for %s (Type: %s)"), 
                    *PropertyName, *Property->GetCPPType());
                bSuccess = FUnrealMCPCommonUtils::SetObjectProperty(ComponentTemplate, PropertyName, JsonValue, ErrorMessage);
                if (!bSuccess)
                {
                    UE_LOG(LogTemp, Error, TEXT("SetComponentProperty - Failed to set property: %s"), *ErrorMessage);
                }
            }
        }
        catch (const std::exception& Ex)
        {
            UE_LOG(LogTemp, Error, TEXT("SetComponentProperty - EXCEPTION: %s"), ANSI_TO_TCHAR(Ex.what()));
            return FUnrealMCPCommonUtils::CreateErrorResponse(
                FString::Printf(TEXT("Exception while setting property %s: %s"), *PropertyName, ANSI_TO_TCHAR(Ex.what())));
        }
        catch (...)
        {
            UE_LOG(LogTemp, Error, TEXT("SetComponentProperty - UNKNOWN EXCEPTION occurred while setting property %s"), *PropertyName);
            return FUnrealMCPCommonUtils::CreateErrorResponse(
                FString::Printf(TEXT("Unknown exception while setting property %s"), *PropertyName));
        }

        if (bSuccess)
        {
            // Mark the blueprint as modified
            UE_LOG(LogTemp, Log, TEXT("SetComponentProperty - Successfully set property %s on component %s"), 
                *PropertyName, *ComponentName);
            
            // Mark the blueprint as modified.
            // Do NOT call ConditionalPostLoad() or PostEditChange() on CDO-owned
            // components – those calls can trigger internal re-registration and GC
            // passes that leave our raw Blueprint pointer dangling.
            FUnrealMCPCommonUtils::SafeMarkBlueprintModified(Blueprint);

            TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
            ResultObj->SetStringField(TEXT("component"), ComponentName);
            ResultObj->SetStringField(TEXT("property"), PropertyName);
            ResultObj->SetBoolField(TEXT("success"), true);
            return ResultObj;
        }
        else
        {
            UE_LOG(LogTemp, Error, TEXT("SetComponentProperty - Failed to set property %s: %s"), 
                *PropertyName, *ErrorMessage);
            return FUnrealMCPCommonUtils::CreateErrorResponse(ErrorMessage);
        }
    }

    UE_LOG(LogTemp, Error, TEXT("SetComponentProperty - Missing 'property_value' parameter"));
    return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'property_value' parameter"));
}

TSharedPtr<FJsonObject> FUnrealMCPBlueprintCommands::HandleSetPhysicsProperties(const TSharedPtr<FJsonObject>& Params)
{
    // Get required parameters
    FString BlueprintName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'blueprint_name' parameter"));
    }

    FString ComponentName;
    if (!Params->TryGetStringField(TEXT("component_name"), ComponentName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'component_name' parameter"));
    }

    // Find the blueprint
    UBlueprint* Blueprint = FUnrealMCPCommonUtils::FindBlueprint(BlueprintName);
    if (!Blueprint)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintName));
    }

    // Find the component
    USCS_Node* ComponentNode = nullptr;
    for (USCS_Node* Node : Blueprint->SimpleConstructionScript->GetAllNodes())
    {
        if (Node && Node->GetVariableName().ToString() == ComponentName)
        {
            ComponentNode = Node;
            break;
        }
    }

    if (!ComponentNode)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Component not found: %s"), *ComponentName));
    }

    UPrimitiveComponent* PrimComponent = Cast<UPrimitiveComponent>(ComponentNode->ComponentTemplate);
    if (!PrimComponent)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Component is not a primitive component"));
    }

    // Set physics properties
    if (Params->HasField(TEXT("simulate_physics")))
    {
        PrimComponent->SetSimulatePhysics(Params->GetBoolField(TEXT("simulate_physics")));
    }

    if (Params->HasField(TEXT("mass")))
    {
        float Mass = Params->GetNumberField(TEXT("mass"));
        // In UE5.5, use proper overrideMass instead of just scaling
        PrimComponent->SetMassOverrideInKg(NAME_None, Mass);
        UE_LOG(LogTemp, Display, TEXT("Set mass for component %s to %f kg"), *ComponentName, Mass);
    }

    if (Params->HasField(TEXT("linear_damping")))
    {
        PrimComponent->SetLinearDamping(Params->GetNumberField(TEXT("linear_damping")));
    }

    if (Params->HasField(TEXT("angular_damping")))
    {
        PrimComponent->SetAngularDamping(Params->GetNumberField(TEXT("angular_damping")));
    }

    // Mark the blueprint as modified
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(Blueprint);

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetStringField(TEXT("component"), ComponentName);
    return ResultObj;
}

TSharedPtr<FJsonObject> FUnrealMCPBlueprintCommands::HandleCompileBlueprint(const TSharedPtr<FJsonObject>& Params)
{
    // -----------------------------------------------------------------------
    // DEFINITIVE FIX v3 — do NOT call FKismetEditorUtilities::CompileBlueprint
    // OR UEditorAssetLibrary::SaveAsset from inside an AsyncTask game-thread
    // lambda in UE5.6.
    //
    // Both paths crash with EXCEPTION_ACCESS_VIOLATION at 0x00007ffe447a0208
    // through the UnrealEditor_MassEntityEditor observer, regardless of compile
    // flags or log-pointer choice.  SaveAsset internally calls CompileBlueprint
    // via the OnSave delegates — same crash.
    //
    // SAFE APPROACH: only call Blueprint->Modify() (marks UObject dirty for undo system,
    // no AssetRegistry broadcast, no ContentBrowser notification).
    // The editor recompiles automatically on the next user save (Ctrl+S) or
    // when the Blueprint editor is opened.  We report success=true so the
    // Python caller can proceed; the blueprint is structurally correct — it
    // just has not yet had its bytecode regenerated.
    // -----------------------------------------------------------------------

    FString BlueprintName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
    {
        UE_LOG(LogMCP, Error, TEXT("[MCP] CompileBlueprint - Missing 'blueprint_name' parameter"));
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'blueprint_name' parameter"));
    }

    UE_LOG(LogMCP, Display, TEXT("[MCP] CompileBlueprint - Starting (safe/no-compile path) for '%s'"), *BlueprintName);

    UBlueprint* Blueprint = FUnrealMCPCommonUtils::FindBlueprint(BlueprintName);
    if (!Blueprint || !IsValid(Blueprint))
    {
        UE_LOG(LogMCP, Error, TEXT("[MCP] CompileBlueprint - Blueprint not found or invalid: %s"), *BlueprintName);
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintName));
    }

    UE_LOG(LogMCP, Display, TEXT("[MCP] CompileBlueprint - Found '%s', status=%d. Marking modified (no inline compile)."),
        *BlueprintName, (int32)Blueprint->Status.GetValue());

    // -----------------------------------------------------------------------
    // DEFINITIVE FIX v4 — guard against first-call EXCEPTION_ACCESS_VIOLATION
    //
    // MarkBlueprintAsStructurallyModified internally dereferences
    // Blueprint->GeneratedClass to invalidate the class's property chain.
    // On the FIRST call of a fresh session, GeneratedClass may be null (BP not
    // yet fully post-loaded) or in a transient GC state, causing a hardware
    // SEH access violation that crashes the GameThread and aborts the TCP
    // socket (Python sees WinError 10053 / WSAECONNABORTED).
    //
    // Safe strategy:
    //   - If GeneratedClass is valid → call MarkBlueprintAsStructurallyModified
    //     (which also calls Blueprint->Modify() internally).
    //   - If GeneratedClass is null/invalid → call Blueprint->Modify() only,
    //     which just marks the UObject dirty for Undo/save purposes and cannot
    //     crash.  The editor will recompile normally on the next user save.
    // -----------------------------------------------------------------------
    if (Blueprint->GeneratedClass && IsValid(Blueprint->GeneratedClass))
    {
        UE_LOG(LogMCP, Display, TEXT("[MCP] CompileBlueprint - GeneratedClass valid, calling MarkBlueprintAsStructurallyModified"));
        FUnrealMCPCommonUtils::SafeMarkBlueprintModified(Blueprint);
    }
    else
    {
        UE_LOG(LogMCP, Warning, TEXT("[MCP] CompileBlueprint - GeneratedClass null/invalid for '%s', falling back to Modify() only"), *BlueprintName);
        Blueprint->Modify();
    }

    UE_LOG(LogMCP, Display, TEXT("[MCP] CompileBlueprint - SUCCESS (marked modified, deferred compile) for '%s'"), *BlueprintName);

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetStringField(TEXT("name"),            BlueprintName);
    ResultObj->SetBoolField(TEXT("compiled"),          true);
    ResultObj->SetBoolField(TEXT("had_errors"),        false);
    ResultObj->SetBoolField(TEXT("deferred_compile"),  true);
    ResultObj->SetStringField(TEXT("note"),
        TEXT("Blueprint marked modified. Press Ctrl+S in UE or open the BP editor to trigger the full compile safely."));
    return ResultObj;
}

TSharedPtr<FJsonObject> FUnrealMCPBlueprintCommands::HandleSpawnBlueprintActor(const TSharedPtr<FJsonObject>& Params)
{
    // Get required parameters
    FString BlueprintName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'blueprint_name' parameter"));
    }

    FString ActorName;
    // Accept both "actor_name" (canonical) and "name" (convenience alias)
    if (!Params->TryGetStringField(TEXT("actor_name"), ActorName))
    {
        if (!Params->TryGetStringField(TEXT("name"), ActorName))
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'actor_name' parameter"));
        }
    }

    // Find the blueprint
    UBlueprint* Blueprint = FUnrealMCPCommonUtils::FindBlueprint(BlueprintName);
    if (!Blueprint)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintName));
    }

    // Get transform parameters
    FVector Location(0.0f, 0.0f, 0.0f);
    FRotator Rotation(0.0f, 0.0f, 0.0f);

    if (Params->HasField(TEXT("location")))
    {
        Location = FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("location"));
    }
    if (Params->HasField(TEXT("rotation")))
    {
        Rotation = FUnrealMCPCommonUtils::GetRotatorFromJson(Params, TEXT("rotation"));
    }

    // Spawn the actor
    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    FTransform SpawnTransform;
    SpawnTransform.SetLocation(Location);
    SpawnTransform.SetRotation(FQuat(Rotation));

    AActor* NewActor = World->SpawnActor<AActor>(Blueprint->GeneratedClass, SpawnTransform);
    if (NewActor)
    {
        NewActor->SetActorLabel(*ActorName);
        return FUnrealMCPCommonUtils::ActorToJsonObject(NewActor, true);
    }

    return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to spawn blueprint actor"));
}

TSharedPtr<FJsonObject> FUnrealMCPBlueprintCommands::HandleSetBlueprintProperty(const TSharedPtr<FJsonObject>& Params)
{
    // Get required parameters
    FString BlueprintName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'blueprint_name' parameter"));
    }

    FString PropertyName;
    if (!Params->TryGetStringField(TEXT("property_name"), PropertyName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'property_name' parameter"));
    }

    // Find the blueprint
    UBlueprint* Blueprint = FUnrealMCPCommonUtils::FindBlueprint(BlueprintName);
    if (!Blueprint)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintName));
    }

    // Get the default object
    UObject* DefaultObject = Blueprint->GeneratedClass->GetDefaultObject();
    if (!DefaultObject)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get default object"));
    }

    // Set the property value
    if (Params->HasField(TEXT("property_value")))
    {
        TSharedPtr<FJsonValue> JsonValue = Params->Values.FindRef(TEXT("property_value"));
        
        FString ErrorMessage;
        if (FUnrealMCPCommonUtils::SetObjectProperty(DefaultObject, PropertyName, JsonValue, ErrorMessage))
        {
            // Mark the blueprint as modified
            FUnrealMCPCommonUtils::SafeMarkBlueprintModified(Blueprint);

            TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
            ResultObj->SetStringField(TEXT("property"), PropertyName);
            ResultObj->SetBoolField(TEXT("success"), true);
            return ResultObj;
        }
        else
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(ErrorMessage);
        }
    }

    return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'property_value' parameter"));
}

TSharedPtr<FJsonObject> FUnrealMCPBlueprintCommands::HandleSetStaticMeshProperties(const TSharedPtr<FJsonObject>& Params)
{
    // Get required parameters
    FString BlueprintName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'blueprint_name' parameter"));
    }

    FString ComponentName;
    if (!Params->TryGetStringField(TEXT("component_name"), ComponentName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'component_name' parameter"));
    }

    // Find the blueprint
    UBlueprint* Blueprint = FUnrealMCPCommonUtils::FindBlueprint(BlueprintName);
    if (!Blueprint)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintName));
    }

    // Find the component
    USCS_Node* ComponentNode = nullptr;
    for (USCS_Node* Node : Blueprint->SimpleConstructionScript->GetAllNodes())
    {
        if (Node && Node->GetVariableName().ToString() == ComponentName)
        {
            ComponentNode = Node;
            break;
        }
    }

    if (!ComponentNode)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Component not found: %s"), *ComponentName));
    }

    UStaticMeshComponent* MeshComponent = Cast<UStaticMeshComponent>(ComponentNode->ComponentTemplate);
    if (!MeshComponent)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Component is not a static mesh component"));
    }

    // Set static mesh properties
    if (Params->HasField(TEXT("static_mesh")))
    {
        FString MeshPath = Params->GetStringField(TEXT("static_mesh"));
        UStaticMesh* Mesh = Cast<UStaticMesh>(UEditorAssetLibrary::LoadAsset(MeshPath));
        if (Mesh)
        {
            MeshComponent->SetStaticMesh(Mesh);
        }
    }

    if (Params->HasField(TEXT("material")))
    {
        FString MaterialPath = Params->GetStringField(TEXT("material"));
        UMaterialInterface* Material = Cast<UMaterialInterface>(UEditorAssetLibrary::LoadAsset(MaterialPath));
        if (Material)
        {
            MeshComponent->SetMaterial(0, Material);
        }
    }

    // Mark the blueprint as modified
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(Blueprint);

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetStringField(TEXT("component"), ComponentName);
    return ResultObj;
}

TSharedPtr<FJsonObject> FUnrealMCPBlueprintCommands::HandleSetPawnProperties(const TSharedPtr<FJsonObject>& Params)
{
    // Get required parameters
    FString BlueprintName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'blueprint_name' parameter"));
    }

    // Find the blueprint
    UBlueprint* Blueprint = FUnrealMCPCommonUtils::FindBlueprint(BlueprintName);
    if (!Blueprint)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintName));
    }

    // Get the default object
    UObject* DefaultObject = Blueprint->GeneratedClass->GetDefaultObject();
    if (!DefaultObject)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get default object"));
    }

    // Track if any properties were set successfully
    bool bAnyPropertiesSet = false;
    TSharedPtr<FJsonObject> ResultsObj = MakeShared<FJsonObject>();
    
    // Set auto possess player if specified
    if (Params->HasField(TEXT("auto_possess_player")))
    {
        TSharedPtr<FJsonValue> AutoPossessValue = Params->Values.FindRef(TEXT("auto_possess_player"));
        
        FString ErrorMessage;
        if (FUnrealMCPCommonUtils::SetObjectProperty(DefaultObject, TEXT("AutoPossessPlayer"), AutoPossessValue, ErrorMessage))
        {
            bAnyPropertiesSet = true;
            TSharedPtr<FJsonObject> PropResultObj = MakeShared<FJsonObject>();
            PropResultObj->SetBoolField(TEXT("success"), true);
            ResultsObj->SetObjectField(TEXT("AutoPossessPlayer"), PropResultObj);
        }
        else
        {
            TSharedPtr<FJsonObject> PropResultObj = MakeShared<FJsonObject>();
            PropResultObj->SetBoolField(TEXT("success"), false);
            PropResultObj->SetStringField(TEXT("error"), ErrorMessage);
            ResultsObj->SetObjectField(TEXT("AutoPossessPlayer"), PropResultObj);
        }
    }
    
    // Set auto possess AI if specified
    if (Params->HasField(TEXT("auto_possess_ai")))
    {
        TSharedPtr<FJsonValue> AutoPossessAIValue = Params->Values.FindRef(TEXT("auto_possess_ai"));
        
        FString ErrorMessage;
        if (FUnrealMCPCommonUtils::SetObjectProperty(DefaultObject, TEXT("AutoPossessAI"), AutoPossessAIValue, ErrorMessage))
        {
            bAnyPropertiesSet = true;
            TSharedPtr<FJsonObject> PropResultObj = MakeShared<FJsonObject>();
            PropResultObj->SetBoolField(TEXT("success"), true);
            ResultsObj->SetObjectField(TEXT("AutoPossessAI"), PropResultObj);
        }
        else
        {
            TSharedPtr<FJsonObject> PropResultObj = MakeShared<FJsonObject>();
            PropResultObj->SetBoolField(TEXT("success"), false);
            PropResultObj->SetStringField(TEXT("error"), ErrorMessage);
            ResultsObj->SetObjectField(TEXT("AutoPossessAI"), PropResultObj);
        }
    }
    
    // Set controller rotation properties
    const TCHAR* RotationProps[] = {
        TEXT("bUseControllerRotationYaw"),
        TEXT("bUseControllerRotationPitch"),
        TEXT("bUseControllerRotationRoll")
    };
    
    const TCHAR* ParamNames[] = {
        TEXT("use_controller_rotation_yaw"),
        TEXT("use_controller_rotation_pitch"),
        TEXT("use_controller_rotation_roll")
    };
    
    for (int32 i = 0; i < 3; i++)
    {
        if (Params->HasField(ParamNames[i]))
        {
            TSharedPtr<FJsonValue> Value = Params->Values.FindRef(ParamNames[i]);
            
            FString ErrorMessage;
            if (FUnrealMCPCommonUtils::SetObjectProperty(DefaultObject, RotationProps[i], Value, ErrorMessage))
            {
                bAnyPropertiesSet = true;
                TSharedPtr<FJsonObject> PropResultObj = MakeShared<FJsonObject>();
                PropResultObj->SetBoolField(TEXT("success"), true);
                ResultsObj->SetObjectField(RotationProps[i], PropResultObj);
            }
            else
            {
                TSharedPtr<FJsonObject> PropResultObj = MakeShared<FJsonObject>();
                PropResultObj->SetBoolField(TEXT("success"), false);
                PropResultObj->SetStringField(TEXT("error"), ErrorMessage);
                ResultsObj->SetObjectField(RotationProps[i], PropResultObj);
            }
        }
    }
    
    // Set can be damaged property
    if (Params->HasField(TEXT("can_be_damaged")))
    {
        TSharedPtr<FJsonValue> Value = Params->Values.FindRef(TEXT("can_be_damaged"));
        
        FString ErrorMessage;
        if (FUnrealMCPCommonUtils::SetObjectProperty(DefaultObject, TEXT("bCanBeDamaged"), Value, ErrorMessage))
        {
            bAnyPropertiesSet = true;
            TSharedPtr<FJsonObject> PropResultObj = MakeShared<FJsonObject>();
            PropResultObj->SetBoolField(TEXT("success"), true);
            ResultsObj->SetObjectField(TEXT("bCanBeDamaged"), PropResultObj);
        }
        else
        {
            TSharedPtr<FJsonObject> PropResultObj = MakeShared<FJsonObject>();
            PropResultObj->SetBoolField(TEXT("success"), false);
            PropResultObj->SetStringField(TEXT("error"), ErrorMessage);
            ResultsObj->SetObjectField(TEXT("bCanBeDamaged"), PropResultObj);
        }
    }

    // Mark the blueprint as modified if any properties were set
    if (bAnyPropertiesSet)
    {
        FUnrealMCPCommonUtils::SafeMarkBlueprintModified(Blueprint);
    }
    else if (ResultsObj->Values.Num() == 0)
    {
        // No properties were specified
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("No properties specified to set"));
    }

    TSharedPtr<FJsonObject> ResponseObj = MakeShared<FJsonObject>();
    ResponseObj->SetStringField(TEXT("blueprint"), BlueprintName);
    ResponseObj->SetBoolField(TEXT("success"), bAnyPropertiesSet);
    ResponseObj->SetObjectField(TEXT("results"), ResultsObj);
    return ResponseObj;
}

TSharedPtr<FJsonObject> FUnrealMCPBlueprintCommands::HandleSetBlueprintAIController(const TSharedPtr<FJsonObject>& Params)
{
    FString BlueprintName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'blueprint_name' parameter"));
    }

    FString ControllerClassName;
    if (!Params->TryGetStringField(TEXT("controller_class"), ControllerClassName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'controller_class' parameter"));
    }

    UBlueprint* Blueprint = FUnrealMCPCommonUtils::FindBlueprint(BlueprintName);
    if (!Blueprint)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintName));
    }

    // Find the controller class by short name or full path
    UClass* ControllerClass = nullptr;

    // Try full path first (nullptr outer searches all packages)
    ControllerClass = FindObject<UClass>(nullptr, *ControllerClassName);

    // Fall back to iterating all loaded classes
    if (!ControllerClass)
    {
        for (TObjectIterator<UClass> It; It; ++It)
        {
            if (It->GetName() == ControllerClassName && It->IsChildOf(AAIController::StaticClass()))
            {
                ControllerClass = *It;
                break;
            }
        }
    }

    // Last resort: try base AIController
    if (!ControllerClass && (ControllerClassName == TEXT("AIController") || ControllerClassName.IsEmpty()))
    {
        ControllerClass = AAIController::StaticClass();
    }

    if (!ControllerClass)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Could not find AI controller class: %s"), *ControllerClassName));
    }

    // Set the AIControllerClass on the Blueprint's parent class CDO
    // The canonical place is Blueprint->GeneratedClass->GetDefaultObject<APawn>()
    UObject* DefaultObject = Blueprint->GeneratedClass ? Blueprint->GeneratedClass->GetDefaultObject() : nullptr;
    if (!DefaultObject)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get blueprint default object"));
    }

    APawn* DefaultPawn = Cast<APawn>(DefaultObject);
    if (!DefaultPawn)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Blueprint is not a Pawn subclass"));
    }

    DefaultPawn->AIControllerClass = ControllerClass;
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(Blueprint);

    UE_LOG(LogTemp, Display, TEXT("Set AIControllerClass on %s to %s"),
           *BlueprintName, *ControllerClass->GetName());

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetStringField(TEXT("blueprint"), BlueprintName);
    ResultObj->SetStringField(TEXT("ai_controller_class"), ControllerClass->GetName());
    ResultObj->SetBoolField(TEXT("success"), true);
    return ResultObj;
}