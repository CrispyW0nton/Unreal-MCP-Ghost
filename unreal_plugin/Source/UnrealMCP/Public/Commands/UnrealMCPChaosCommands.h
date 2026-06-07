#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

class AActor;
class AChaosSolverActor;
class AGeometryCollectionActor;
class UGeometryCollectionComponent;
class USkeletalMeshComponent;

/**
 * B.10 Chaos destruction and cloth command handler.
 */
class UNREALMCP_API FUnrealMCPChaosCommands
{
public:
    FUnrealMCPChaosCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleCreateSolverActor(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureSolverActor(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleInspectGeometryCollection(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureGeometryCollection(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureClothComponent(const TSharedPtr<FJsonObject>& Params);

    UWorld* GetEditorWorld() const;
    AActor* FindActorByNameOrLabel(const FString& Query) const;
    AChaosSolverActor* FindSolverActor(const FString& Query) const;
    UGeometryCollectionComponent* FindGeometryCollectionComponent(const FString& ActorName, AGeometryCollectionActor** OutActor = nullptr) const;
    USkeletalMeshComponent* FindSkeletalMeshComponent(const FString& ActorName, const FString& ComponentName, AActor** OutActor = nullptr) const;
    UObject* LoadAsset(const FString& AssetOrObjectPath) const;
    FVector GetVectorField(const TSharedPtr<FJsonObject>& Params, const TCHAR* FieldName, const FVector& DefaultValue) const;
    TArray<float> GetFloatArrayField(const TSharedPtr<FJsonObject>& Params, const FString& FieldName) const;
    TSharedPtr<FJsonObject> MakeSolverResult(const FString& StageName, AChaosSolverActor* Solver) const;
    TSharedPtr<FJsonObject> MakeGeometryCollectionResult(const FString& StageName, AGeometryCollectionActor* Actor, UGeometryCollectionComponent* Component) const;
    TSharedPtr<FJsonObject> MakeClothResult(const FString& StageName, AActor* Actor, USkeletalMeshComponent* Component) const;
};
