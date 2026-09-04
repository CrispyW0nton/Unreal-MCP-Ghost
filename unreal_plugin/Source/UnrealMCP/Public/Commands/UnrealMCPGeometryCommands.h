#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

class ADynamicMeshActor;
class UDynamicMesh;

/**
 * B.6 Geometry Script and Modeling Mode command handler.
 */
class UNREALMCP_API FUnrealMCPGeometryCommands
{
public:
    FUnrealMCPGeometryCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleCreateDynamicMesh(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleBooleanOp(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleExtrude(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleRemesh(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleUVUnwrap(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleBakeToStaticMesh(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleApplyDisplacement(const TSharedPtr<FJsonObject>& Params);

    UWorld* GetEditorWorld() const;
    ADynamicMeshActor* FindDynamicMeshActor(const FString& ActorName) const;
    UDynamicMesh* GetDynamicMesh(const FString& ActorName, ADynamicMeshActor** OutActor = nullptr) const;
    FVector GetVectorField(const TSharedPtr<FJsonObject>& Params, const TCHAR* FieldName, const FVector& DefaultValue) const;
    TSharedPtr<FJsonObject> MakeMeshResult(const FString& StageName, ADynamicMeshActor* Actor, UDynamicMesh* Mesh) const;
};
