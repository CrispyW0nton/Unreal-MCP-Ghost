#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

class UMassEntityConfigAsset;
class USmartObjectDefinition;
class UStateTree;
class UStateTreeEditorData;
class UStateTreeState;

/**
 * B.7 MassEntity, StateTree, and SmartObject command handler.
 */
class UNREALMCP_API FUnrealMCPMassCommands
{
public:
    FUnrealMCPMassCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleMassCreateEntityConfig(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleMassAddTrait(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleMassInspectEntityConfig(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleStateTreeCreate(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleStateTreeAddState(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleStateTreeInspect(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSmartObjectCreateDefinition(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSmartObjectAddSlot(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSmartObjectInspectDefinition(const TSharedPtr<FJsonObject>& Params);

    FString NormalizeAssetPath(const FString& InPath) const;
    FString MakeObjectPath(const FString& AssetPath) const;
    bool SplitPackagePath(const FString& AssetPath, FString& OutPackagePath, FString& OutAssetName) const;
    UObject* LoadAsset(const FString& AssetOrObjectPath) const;
    UClass* ResolveClass(const FString& ClassName, UClass* RequiredBaseClass) const;
    TArray<FString> GetStringArrayField(const TSharedPtr<FJsonObject>& Params, const FString& FieldName) const;
    TArray<TSharedPtr<FJsonValue>> MakeStringArray(const TArray<FString>& Values) const;
    TArray<TSharedPtr<FJsonValue>> MakeVectorArray(const FVector& Value) const;
    TArray<TSharedPtr<FJsonValue>> MakeRotatorArray(const FRotator& Value) const;
    TSharedPtr<FJsonObject> SummarizeMassConfig(UMassEntityConfigAsset* ConfigAsset, bool bValidate) const;
    TSharedPtr<FJsonObject> SummarizeStateTree(UStateTree* StateTree) const;
    TSharedPtr<FJsonObject> SummarizeSmartObject(USmartObjectDefinition* Definition) const;
    UStateTreeState* FindState(UStateTreeEditorData* EditorData, const FString& StateNameOrID) const;
    void AppendStateSummary(UStateTreeState* State, TArray<TSharedPtr<FJsonValue>>& OutStates, int32 Depth) const;
    int32 CountEditorStates(UStateTreeEditorData* EditorData) const;
    UWorld* GetEditorWorld() const;
};
