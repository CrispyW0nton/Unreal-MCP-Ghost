#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

class FConfigFile;

/**
 * B.12 Online Subsystem and EOS command handler.
 */
class UNREALMCP_API FUnrealMCPOnlineCommands
{
public:
    FUnrealMCPOnlineCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleInspectConfig(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureDefaultSubsystem(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateEOSArtifactConfig(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureEOSSessions(const TSharedPtr<FJsonObject>& Params);

    FString GetDefaultEngineIniPath() const;
    bool LoadDefaultEngineConfig(FConfigFile& ConfigFile, FString& OutPath) const;
    bool WriteDefaultEngineConfig(FConfigFile& ConfigFile, const FString& ConfigPath) const;
    FString GetStringValue(const FConfigFile& ConfigFile, const FString& Section, const FString& Key, const FString& DefaultValue = FString()) const;
    bool GetBoolValue(const FConfigFile& ConfigFile, const FString& Section, const FString& Key, bool bDefaultValue = false) const;
    void SetStringValue(FConfigFile& ConfigFile, const FString& Section, const FString& Key, const FString& Value) const;
    void SetBoolValue(FConfigFile& ConfigFile, const FString& Section, const FString& Key, bool bValue) const;
    TSharedPtr<FJsonObject> MakeConfigResult(const FString& StageName, const FConfigFile& ConfigFile, const FString& ConfigPath, bool bIncludePlugins) const;
    TSharedPtr<FJsonObject> MakePluginStatus(const FString& PluginName) const;
    FString MaskSecret(const FString& Value) const;
};
