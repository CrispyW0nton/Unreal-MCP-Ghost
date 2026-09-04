#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

class UFactory;
class UMetaSoundBuilderBase;
class UObject;

/**
 * B.5 MetaSounds and audio asset command handler.
 */
class UNREALMCP_API FUnrealMCPAudioCommands
{
public:
    FUnrealMCPAudioCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleCreateMetaSoundSource(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateMetaSoundPatch(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleMetaSoundAddNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleMetaSoundConnectPins(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleMetaSoundCompile(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateSoundCue(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateAttenuation(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateConcurrency(const TSharedPtr<FJsonObject>& Params);

    TSharedPtr<FJsonObject> CreateAsset(
        const TSharedPtr<FJsonObject>& Params,
        const FString& DefaultName,
        const FString& DefaultPath,
        UClass* AssetClass,
        UFactory* Factory,
        const FString& StageName) const;

    UObject* LoadAssetObject(const FString& AssetPathOrObjectPath) const;
    UMetaSoundBuilderBase* AttachBuilder(UObject* MetaSoundObject, FString& OutError) const;
    bool ParseGuidField(const TSharedPtr<FJsonObject>& Params, const TCHAR* FieldName, FGuid& OutGuid, FString& OutError) const;
    FString MakeObjectPath(const FString& AssetPathOrObjectPath) const;
    void SetCommonAssetFields(TSharedPtr<FJsonObject> Result, UObject* Asset, const FString& AssetPath, const FString& ObjectPath) const;
};
