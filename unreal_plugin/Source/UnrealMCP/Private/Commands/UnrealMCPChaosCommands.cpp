#include "Commands/UnrealMCPChaosCommands.h"

#include "Chaos/ChaosSolverActor.h"
#include "Commands/UnrealMCPCommonUtils.h"
#include "Components/SkeletalMeshComponent.h"
#include "Editor.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GeometryCollection/GeometryCollectionActor.h"
#include "GeometryCollection/GeometryCollectionComponent.h"
#include "GeometryCollection/GeometryCollectionObject.h"
#include "Misc/Paths.h"
#include "ScopedTransaction.h"

FUnrealMCPChaosCommands::FUnrealMCPChaosCommands()
{
}

TSharedPtr<FJsonObject> FUnrealMCPChaosCommands::HandleCommand(
    const FString& CommandType,
    const TSharedPtr<FJsonObject>& Params)
{
    if (CommandType == TEXT("chaos_create_solver_actor")) return HandleCreateSolverActor(Params);
    if (CommandType == TEXT("chaos_configure_solver_actor")) return HandleConfigureSolverActor(Params);
    if (CommandType == TEXT("chaos_inspect_geometry_collection")) return HandleInspectGeometryCollection(Params);
    if (CommandType == TEXT("chaos_configure_geometry_collection")) return HandleConfigureGeometryCollection(Params);
    if (CommandType == TEXT("chaos_configure_cloth_component")) return HandleConfigureClothComponent(Params);

    return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown Chaos command: %s"), *CommandType));
}

UWorld* FUnrealMCPChaosCommands::GetEditorWorld() const
{
    return GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
}

AActor* FUnrealMCPChaosCommands::FindActorByNameOrLabel(const FString& Query) const
{
    if (Query.IsEmpty())
    {
        return nullptr;
    }

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return nullptr;
    }

    for (TActorIterator<AActor> It(World); It; ++It)
    {
        AActor* Actor = *It;
        if (Actor && (Actor->GetName().Equals(Query, ESearchCase::IgnoreCase) ||
            Actor->GetActorLabel().Equals(Query, ESearchCase::IgnoreCase) ||
            Actor->GetPathName().Equals(Query, ESearchCase::IgnoreCase)))
        {
            return Actor;
        }
    }
    return nullptr;
}

AChaosSolverActor* FUnrealMCPChaosCommands::FindSolverActor(const FString& Query) const
{
    if (Query.IsEmpty())
    {
        return nullptr;
    }

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return nullptr;
    }

    for (TActorIterator<AChaosSolverActor> It(World); It; ++It)
    {
        AChaosSolverActor* Solver = *It;
        if (Solver && (Solver->GetName().Equals(Query, ESearchCase::IgnoreCase) ||
            Solver->GetActorLabel().Equals(Query, ESearchCase::IgnoreCase) ||
            Solver->GetPathName().Equals(Query, ESearchCase::IgnoreCase)))
        {
            return Solver;
        }
    }
    return nullptr;
}

UGeometryCollectionComponent* FUnrealMCPChaosCommands::FindGeometryCollectionComponent(
    const FString& ActorName,
    AGeometryCollectionActor** OutActor) const
{
    if (OutActor)
    {
        *OutActor = nullptr;
    }

    AActor* Actor = FindActorByNameOrLabel(ActorName);
    if (!Actor)
    {
        return nullptr;
    }

    AGeometryCollectionActor* GeometryActor = Cast<AGeometryCollectionActor>(Actor);
    if (OutActor)
    {
        *OutActor = GeometryActor;
    }

    if (GeometryActor && GeometryActor->GetGeometryCollectionComponent())
    {
        return GeometryActor->GetGeometryCollectionComponent();
    }
    return Actor->FindComponentByClass<UGeometryCollectionComponent>();
}

USkeletalMeshComponent* FUnrealMCPChaosCommands::FindSkeletalMeshComponent(
    const FString& ActorName,
    const FString& ComponentName,
    AActor** OutActor) const
{
    if (OutActor)
    {
        *OutActor = nullptr;
    }

    AActor* Actor = FindActorByNameOrLabel(ActorName);
    if (!Actor)
    {
        return nullptr;
    }
    if (OutActor)
    {
        *OutActor = Actor;
    }

    TArray<USkeletalMeshComponent*> Components;
    Actor->GetComponents<USkeletalMeshComponent>(Components);
    if (!ComponentName.IsEmpty())
    {
        for (USkeletalMeshComponent* Component : Components)
        {
            if (Component && (Component->GetName().Equals(ComponentName, ESearchCase::IgnoreCase) ||
                Component->GetPathName().Equals(ComponentName, ESearchCase::IgnoreCase)))
            {
                return Component;
            }
        }
        return nullptr;
    }

    return Components.Num() > 0 ? Components[0] : nullptr;
}

UObject* FUnrealMCPChaosCommands::LoadAsset(const FString& AssetOrObjectPath) const
{
    if (AssetOrObjectPath.IsEmpty())
    {
        return nullptr;
    }

    if (UObject* Loaded = StaticLoadObject(UObject::StaticClass(), nullptr, *AssetOrObjectPath))
    {
        return Loaded;
    }

    if (AssetOrObjectPath.StartsWith(TEXT("/Game/")) && !AssetOrObjectPath.Contains(TEXT(".")))
    {
        const FString ObjectPath = FString::Printf(TEXT("%s.%s"), *AssetOrObjectPath, *FPaths::GetBaseFilename(AssetOrObjectPath));
        return StaticLoadObject(UObject::StaticClass(), nullptr, *ObjectPath);
    }
    return nullptr;
}

FVector FUnrealMCPChaosCommands::GetVectorField(
    const TSharedPtr<FJsonObject>& Params,
    const TCHAR* FieldName,
    const FVector& DefaultValue) const
{
    if (Params.IsValid() && Params->HasField(FieldName))
    {
        return FUnrealMCPCommonUtils::GetVectorFromJson(Params, FieldName);
    }
    return DefaultValue;
}

TArray<float> FUnrealMCPChaosCommands::GetFloatArrayField(const TSharedPtr<FJsonObject>& Params, const FString& FieldName) const
{
    TArray<float> Values;
    const TArray<TSharedPtr<FJsonValue>>* JsonValues = nullptr;
    if (Params.IsValid() && Params->TryGetArrayField(FieldName, JsonValues))
    {
        for (const TSharedPtr<FJsonValue>& JsonValue : *JsonValues)
        {
            if (JsonValue.IsValid())
            {
                Values.Add(static_cast<float>(JsonValue->AsNumber()));
            }
        }
    }
    return Values;
}

TSharedPtr<FJsonObject> FUnrealMCPChaosCommands::MakeSolverResult(const FString& StageName, AChaosSolverActor* Solver) const
{
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), Solver != nullptr);
    Result->SetStringField(TEXT("stage"), StageName);
    if (Solver)
    {
        Result->SetStringField(TEXT("actor_name"), Solver->GetActorLabel());
        Result->SetStringField(TEXT("actor_path"), Solver->GetPathName());
        Result->SetBoolField(TEXT("has_floor"), Solver->bHasFloor);
        Result->SetNumberField(TEXT("floor_height"), Solver->FloorHeight);
        Result->SetNumberField(TEXT("position_iterations"), Solver->Properties.PositionIterations);
        Result->SetNumberField(TEXT("velocity_iterations"), Solver->Properties.VelocityIterations);
        Result->SetNumberField(TEXT("projection_iterations"), Solver->Properties.ProjectionIterations);
        Result->SetBoolField(TEXT("generate_collision_data"), Solver->Properties.bGenerateCollisionData);
        Result->SetBoolField(TEXT("generate_break_data"), Solver->Properties.bGenerateBreakData);
        Result->SetBoolField(TEXT("generate_trailing_data"), Solver->Properties.bGenerateTrailingData);
        Result->SetBoolField(TEXT("optimize_runtime_memory"), Solver->Properties.DestructionSettings.bOptimizeForRuntimeMemory);
        Result->SetNumberField(TEXT("per_advance_breaks_allowed"), Solver->Properties.DestructionSettings.PerAdvanceBreaksAllowed);
        Result->SetNumberField(TEXT("per_advance_breaks_reschedule_limit"), Solver->Properties.DestructionSettings.PerAdvanceBreaksRescheduleLimit);
    }
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPChaosCommands::MakeGeometryCollectionResult(
    const FString& StageName,
    AGeometryCollectionActor* Actor,
    UGeometryCollectionComponent* Component) const
{
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), Component != nullptr);
    Result->SetStringField(TEXT("stage"), StageName);
    if (Actor)
    {
        Result->SetStringField(TEXT("actor_name"), Actor->GetActorLabel());
        Result->SetStringField(TEXT("actor_path"), Actor->GetPathName());
    }
    if (Component)
    {
        const UGeometryCollection* RestCollection = Component->GetRestCollection();
        Result->SetStringField(TEXT("component_name"), Component->GetName());
        Result->SetStringField(TEXT("component_path"), Component->GetPathName());
        Result->SetStringField(TEXT("rest_collection"), RestCollection ? RestCollection->GetPathName() : TEXT(""));
        Result->SetBoolField(TEXT("simulate_physics"), Component->IsSimulatingPhysics());
        Result->SetBoolField(TEXT("gravity_enabled"), Component->IsGravityEnabled());
        Result->SetBoolField(TEXT("enable_clustering"), Component->EnableClustering);
        Result->SetNumberField(TEXT("cluster_group_index"), Component->ClusterGroupIndex);
        Result->SetNumberField(TEXT("max_cluster_level"), Component->MaxClusterLevel);
        Result->SetNumberField(TEXT("max_simulated_level"), Component->MaxSimulatedLevel);
        Result->SetBoolField(TEXT("notify_breaks"), Component->bNotifyBreaks);
        Result->SetBoolField(TEXT("notify_collisions"), Component->bNotifyCollisions);
        Result->SetBoolField(TEXT("enable_damage_from_collision"), Component->bEnableDamageFromCollision);
        Result->SetStringField(TEXT("solver_actor"), Component->ChaosSolverActor ? Component->ChaosSolverActor->GetActorLabel() : TEXT(""));

        TArray<TSharedPtr<FJsonValue>> Thresholds;
        for (const float Threshold : Component->GetDamageThreshold())
        {
            Thresholds.Add(MakeShared<FJsonValueNumber>(Threshold));
        }
        Result->SetArrayField(TEXT("damage_thresholds"), Thresholds);

        const FBox Bounds = Component->Bounds.GetBox();
        Result->SetStringField(TEXT("bounds"), Bounds.ToString());
    }
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPChaosCommands::MakeClothResult(
    const FString& StageName,
    AActor* Actor,
    USkeletalMeshComponent* Component) const
{
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), Component != nullptr);
    Result->SetStringField(TEXT("stage"), StageName);
    if (Actor)
    {
        Result->SetStringField(TEXT("actor_name"), Actor->GetActorLabel());
        Result->SetStringField(TEXT("actor_path"), Actor->GetPathName());
    }
    if (Component)
    {
        const USkeletalMesh* SkeletalMesh = Component->GetSkeletalMeshAsset();
        Result->SetStringField(TEXT("component_name"), Component->GetName());
        Result->SetStringField(TEXT("component_path"), Component->GetPathName());
        Result->SetStringField(TEXT("skeletal_mesh"), SkeletalMesh ? SkeletalMesh->GetPathName() : TEXT(""));
        Result->SetBoolField(TEXT("can_simulate_clothing"), Component->CanSimulateClothing());
        Result->SetBoolField(TEXT("is_suspended"), Component->IsClothingSimulationSuspended());
        Result->SetBoolField(TEXT("allow_cloth_actors"), Component->GetAllowClothActors());
        Result->SetBoolField(TEXT("update_cloth_in_editor"), Component->GetUpdateClothInEditor());
        Result->SetNumberField(TEXT("cloth_max_distance_scale"), Component->GetClothMaxDistanceScale());
        Result->SetNumberField(TEXT("cloth_blend_weight"), Component->ClothBlendWeight);
        Result->SetBoolField(TEXT("wait_for_parallel_cloth_task"), Component->bWaitForParallelClothTask);
        Result->SetBoolField(TEXT("disable_cloth_simulation"), Component->bDisableClothSimulation);
    }
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPChaosCommands::HandleCreateSolverActor(const TSharedPtr<FJsonObject>& Params)
{
    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    FString ActorName = TEXT("ChaosSolver_MCP");
    Params->TryGetStringField(TEXT("actor_name"), ActorName);
    if (ActorName.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'actor_name' parameter"));
    }

    bool bOverwrite = false;
    Params->TryGetBoolField(TEXT("overwrite"), bOverwrite);
    if (AChaosSolverActor* Existing = FindSolverActor(ActorName))
    {
        if (!bOverwrite)
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(
                FString::Printf(TEXT("Chaos solver actor already exists: %s"), *ActorName));
        }
        Existing->Destroy();
    }

    const FVector Location = GetVectorField(Params, TEXT("location"), FVector::ZeroVector);
    const FRotator Rotation = Params->HasField(TEXT("rotation"))
        ? FUnrealMCPCommonUtils::GetRotatorFromJson(Params, TEXT("rotation"))
        : FRotator::ZeroRotator;

    const FScopedTransaction Transaction(FText::FromString(TEXT("MCP Create Chaos Solver Actor")));
    AChaosSolverActor* Solver = World->SpawnActor<AChaosSolverActor>(Location, Rotation);
    if (!Solver)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to spawn Chaos solver actor"));
    }
    Solver->SetActorLabel(ActorName);

    bool bSetAsWorldSolver = false;
    Params->TryGetBoolField(TEXT("set_as_world_solver"), bSetAsWorldSolver);
    if (bSetAsWorldSolver)
    {
        Solver->SetAsCurrentWorldSolver();
    }

    TSharedPtr<FJsonObject> Result = MakeSolverResult(TEXT("chaos_create_solver_actor"), Solver);
    Result->SetBoolField(TEXT("set_as_world_solver"), bSetAsWorldSolver);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPChaosCommands::HandleConfigureSolverActor(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("actor_name"), ActorName) || ActorName.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'actor_name' parameter"));
    }

    AChaosSolverActor* Solver = FindSolverActor(ActorName);
    if (!Solver)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Chaos solver actor not found: %s"), *ActorName));
    }

    const FScopedTransaction Transaction(FText::FromString(TEXT("MCP Configure Chaos Solver Actor")));
    Solver->Modify();

    bool bBoolValue = false;
    int32 IntValue = 0;
    double NumberValue = 0.0;
    if (Params->TryGetBoolField(TEXT("active"), bBoolValue))
    {
        Solver->SetSolverActive(bBoolValue);
    }
    if (Params->TryGetBoolField(TEXT("has_floor"), bBoolValue))
    {
        Solver->bHasFloor = bBoolValue;
    }
    if (Params->TryGetNumberField(TEXT("floor_height"), NumberValue))
    {
        Solver->FloorHeight = static_cast<float>(NumberValue);
    }
    if (Params->TryGetNumberField(TEXT("position_iterations"), IntValue))
    {
        Solver->Properties.PositionIterations = FMath::Max(0, IntValue);
    }
    if (Params->TryGetNumberField(TEXT("velocity_iterations"), IntValue))
    {
        Solver->Properties.VelocityIterations = FMath::Max(0, IntValue);
    }
    if (Params->TryGetNumberField(TEXT("projection_iterations"), IntValue))
    {
        Solver->Properties.ProjectionIterations = FMath::Max(0, IntValue);
    }
    if (Params->TryGetBoolField(TEXT("generate_collision_data"), bBoolValue))
    {
        Solver->Properties.bGenerateCollisionData = bBoolValue;
    }
    if (Params->TryGetBoolField(TEXT("generate_break_data"), bBoolValue))
    {
        Solver->Properties.bGenerateBreakData = bBoolValue;
    }
    if (Params->TryGetBoolField(TEXT("generate_trailing_data"), bBoolValue))
    {
        Solver->Properties.bGenerateTrailingData = bBoolValue;
    }
    if (Params->TryGetBoolField(TEXT("optimize_runtime_memory"), bBoolValue))
    {
        Solver->Properties.DestructionSettings.bOptimizeForRuntimeMemory = bBoolValue;
    }
    if (Params->TryGetNumberField(TEXT("per_advance_breaks_allowed"), IntValue))
    {
        Solver->Properties.DestructionSettings.PerAdvanceBreaksAllowed = FMath::Max(0, IntValue);
    }
    if (Params->TryGetNumberField(TEXT("per_advance_breaks_reschedule_limit"), IntValue))
    {
        Solver->Properties.DestructionSettings.PerAdvanceBreaksRescheduleLimit = FMath::Max(0, IntValue);
    }

    bool bSetAsWorldSolver = false;
    Params->TryGetBoolField(TEXT("set_as_world_solver"), bSetAsWorldSolver);
    if (bSetAsWorldSolver)
    {
        Solver->SetAsCurrentWorldSolver();
    }

    TSharedPtr<FJsonObject> Result = MakeSolverResult(TEXT("chaos_configure_solver_actor"), Solver);
    Result->SetBoolField(TEXT("set_as_world_solver"), bSetAsWorldSolver);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPChaosCommands::HandleInspectGeometryCollection(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    FString AssetPath;
    Params->TryGetStringField(TEXT("actor_name"), ActorName);
    Params->TryGetStringField(TEXT("asset"), AssetPath);

    AGeometryCollectionActor* Actor = nullptr;
    UGeometryCollectionComponent* Component = nullptr;
    if (!ActorName.IsEmpty())
    {
        Component = FindGeometryCollectionComponent(ActorName, &Actor);
    }

    TSharedPtr<FJsonObject> Result = MakeGeometryCollectionResult(TEXT("chaos_inspect_geometry_collection"), Actor, Component);
    if (!AssetPath.IsEmpty())
    {
        UGeometryCollection* Collection = Cast<UGeometryCollection>(LoadAsset(AssetPath));
        Result->SetBoolField(TEXT("success"), Result->GetBoolField(TEXT("success")) || Collection != nullptr);
        Result->SetStringField(TEXT("asset_path"), Collection ? Collection->GetPathName() : TEXT(""));
        Result->SetBoolField(TEXT("asset_found"), Collection != nullptr);
    }
    if (!Result->GetBoolField(TEXT("success")))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Provide a valid Geometry Collection actor_name or asset path"));
    }
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPChaosCommands::HandleConfigureGeometryCollection(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("actor_name"), ActorName) || ActorName.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'actor_name' parameter"));
    }

    AGeometryCollectionActor* Actor = nullptr;
    UGeometryCollectionComponent* Component = FindGeometryCollectionComponent(ActorName, &Actor);
    if (!Component)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Geometry Collection component not found on actor: %s"), *ActorName));
    }

    const FScopedTransaction Transaction(FText::FromString(TEXT("MCP Configure Geometry Collection")));
    Component->Modify();

    bool bBoolValue = false;
    int32 IntValue = 0;
    if (Params->TryGetBoolField(TEXT("simulate_physics"), bBoolValue))
    {
        Component->SetSimulatePhysics(bBoolValue);
    }
    if (Params->TryGetBoolField(TEXT("gravity_enabled"), bBoolValue))
    {
        Component->SetEnableGravity(bBoolValue);
    }
    if (Params->TryGetBoolField(TEXT("enable_clustering"), bBoolValue))
    {
        Component->EnableClustering = bBoolValue;
    }
    if (Params->TryGetBoolField(TEXT("notify_breaks"), bBoolValue))
    {
        Component->SetNotifyBreaks(bBoolValue);
    }
    if (Params->TryGetBoolField(TEXT("notify_collisions"), bBoolValue))
    {
        Component->SetNotifyRigidBodyCollision(bBoolValue);
        Component->SetNotifyGlobalCollision(bBoolValue);
    }
    if (Params->TryGetBoolField(TEXT("enable_damage_from_collision"), bBoolValue))
    {
        Component->SetEnableDamageFromCollision(bBoolValue);
    }
    if (Params->TryGetNumberField(TEXT("cluster_group_index"), IntValue))
    {
        Component->ClusterGroupIndex = IntValue;
    }
    if (Params->TryGetNumberField(TEXT("max_cluster_level"), IntValue))
    {
        Component->MaxClusterLevel = FMath::Max(0, IntValue);
    }
    if (Params->TryGetNumberField(TEXT("max_simulated_level"), IntValue))
    {
        Component->MaxSimulatedLevel = FMath::Max(0, IntValue);
    }

    const TArray<float> DamageThresholds = GetFloatArrayField(Params, TEXT("damage_thresholds"));
    if (DamageThresholds.Num() > 0)
    {
        Component->SetDamageThreshold(DamageThresholds);
    }

    FString SolverName;
    if (Params->TryGetStringField(TEXT("solver_actor"), SolverName))
    {
        Component->ChaosSolverActor = SolverName.IsEmpty() ? nullptr : FindSolverActor(SolverName);
    }

    Component->MarkRenderStateDirty();
    return MakeGeometryCollectionResult(TEXT("chaos_configure_geometry_collection"), Actor, Component);
}

TSharedPtr<FJsonObject> FUnrealMCPChaosCommands::HandleConfigureClothComponent(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("actor_name"), ActorName) || ActorName.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'actor_name' parameter"));
    }

    FString ComponentName;
    Params->TryGetStringField(TEXT("component_name"), ComponentName);

    AActor* Actor = nullptr;
    USkeletalMeshComponent* Component = FindSkeletalMeshComponent(ActorName, ComponentName, &Actor);
    if (!Component)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("SkeletalMeshComponent not found on actor: %s"), *ActorName));
    }

    const FScopedTransaction Transaction(FText::FromString(TEXT("MCP Configure Cloth Component")));
    Component->Modify();

    bool bBoolValue = false;
    double NumberValue = 0.0;
    if (Params->TryGetBoolField(TEXT("suspend"), bBoolValue))
    {
        if (bBoolValue)
        {
            Component->SuspendClothingSimulation();
        }
        else
        {
            Component->ResumeClothingSimulation();
        }
    }
    if (Params->TryGetBoolField(TEXT("allow_cloth_actors"), bBoolValue))
    {
        Component->SetAllowClothActors(bBoolValue);
    }
    if (Params->TryGetBoolField(TEXT("update_in_editor"), bBoolValue))
    {
        Component->SetUpdateClothInEditor(bBoolValue);
    }
    if (Params->TryGetBoolField(TEXT("wait_for_parallel_task"), bBoolValue))
    {
        Component->bWaitForParallelClothTask = bBoolValue;
    }
    if (Params->TryGetNumberField(TEXT("cloth_max_distance_scale"), NumberValue))
    {
        Component->SetClothMaxDistanceScale(static_cast<float>(FMath::Max(0.0, NumberValue)));
    }
    if (Params->TryGetNumberField(TEXT("cloth_blend_weight"), NumberValue))
    {
        Component->ClothBlendWeight = static_cast<float>(FMath::Clamp(NumberValue, 0.0, 1.0));
    }
    if (Params->TryGetBoolField(TEXT("force_teleport"), bBoolValue) && bBoolValue)
    {
        Component->ForceClothNextUpdateTeleport();
    }
    if (Params->TryGetBoolField(TEXT("force_reset"), bBoolValue) && bBoolValue)
    {
        Component->ForceClothNextUpdateTeleportAndReset();
    }
    if (Params->TryGetBoolField(TEXT("recreate_actors"), bBoolValue) && bBoolValue)
    {
        Component->RecreateClothingActors();
    }

    return MakeClothResult(TEXT("chaos_configure_cloth_component"), Actor, Component);
}
