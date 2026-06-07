#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

class UBlueprint;
class UClass;
class UEdGraph;
class UFunction;
class USCS_Node;

/**
 * Native routes for Gameplay Ability System authoring and inspection support.
 */
class UNREALMCP_API FUnrealMCPGASCommands
{
public:
    FUnrealMCPGASCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleCreateAbility(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateGameplayEffect(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateGameplayCue(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateAttributeSet(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleGrantAbility(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleApplyEffect(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddTag(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateAbilityTaskNode(const TSharedPtr<FJsonObject>& Params);

    UClass* ResolveClass(const FString& ClassPathOrName, UClass* FallbackClass) const;
    TSharedPtr<FJsonObject> CreateBlueprintAsset(
        const TSharedPtr<FJsonObject>& Params,
        const FString& DefaultName,
        const FString& DefaultPath,
        UClass* DefaultParentClass,
        const FString& StageName) const;
    UBlueprint* FindBlueprintChecked(const FString& BlueprintName, FString& OutError) const;
    UEdGraph* FindGraph(UBlueprint* Blueprint, const FString& GraphName) const;
    UFunction* ResolveAbilityTaskFactory(UClass* TaskClass, const FString& FunctionName) const;
    USCS_Node* EnsureAbilitySystemComponent(UBlueprint* Blueprint, bool& bCreated, FString& OutError) const;
    TSharedPtr<FJsonObject> AppendBlueprintMetadata(
        const TSharedPtr<FJsonObject>& Params,
        const FString& MetadataKey,
        const FString& ValueField,
        const FString& StageName) const;
};
