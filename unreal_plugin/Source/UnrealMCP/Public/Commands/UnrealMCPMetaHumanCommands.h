#pragma once

#include "CoreMinimal.h"
#include "AssetRegistry/AssetData.h"
#include "Dom/JsonObject.h"

class FConfigFile;

/**
 * B.14 MetaHuman package registration and animation-link command handler.
 */
class UNREALMCP_API FUnrealMCPMetaHumanCommands
{
public:
    FUnrealMCPMetaHumanCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleImport(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleLinkToSkeleton(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAssignDNA(const TSharedPtr<FJsonObject>& Params);

    FString GetDefaultEngineIniPath() const;
    bool LoadDefaultEngineConfig(FConfigFile& ConfigFile, FString& OutPath) const;
    bool WriteDefaultEngineConfig(FConfigFile& ConfigFile, const FString& ConfigPath) const;
    void SetStringValue(FConfigFile& ConfigFile, const FString& Section, const FString& Key, const FString& Value) const;
    void SetBoolValue(FConfigFile& ConfigFile, const FString& Section, const FString& Key, bool bValue) const;
    FString NormalizeAssetPath(const FString& InPath) const;
    FString MakeObjectPath(const FString& AssetPath) const;
    FString SanitizeName(const FString& Name) const;
    UObject* LoadAsset(const FString& AssetOrObjectPath) const;
    TArray<FAssetData> ScanAssetsUnderRoot(const FString& RootPath) const;
    TArray<TSharedPtr<FJsonValue>> MakeAssetSummaries(const TArray<FAssetData>& Assets) const;
    TSharedPtr<FJsonObject> MakeAssetClassCounts(const TArray<FAssetData>& Assets) const;
    FString MakeManifestSection(const FString& CharacterName) const;
};
