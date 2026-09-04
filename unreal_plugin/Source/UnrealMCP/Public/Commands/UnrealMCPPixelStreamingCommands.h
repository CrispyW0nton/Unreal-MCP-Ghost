#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

class FConfigFile;

/**
 * B.13 Pixel Streaming command handler.
 */
class UNREALMCP_API FUnrealMCPPixelStreamingCommands
{
public:
    FUnrealMCPPixelStreamingCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleInspectConfig(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigurePlugin(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureStreamer(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateLaunchProfile(const TSharedPtr<FJsonObject>& Params);

    FString GetDefaultEngineIniPath() const;
    bool LoadDefaultEngineConfig(FConfigFile& ConfigFile, FString& OutPath) const;
    bool WriteDefaultEngineConfig(FConfigFile& ConfigFile, const FString& ConfigPath) const;
    FString GetStringValue(const FConfigFile& ConfigFile, const FString& Section, const FString& Key, const FString& DefaultValue = FString()) const;
    bool GetBoolValue(const FConfigFile& ConfigFile, const FString& Section, const FString& Key, bool bDefaultValue = false) const;
    int32 GetIntValue(const FConfigFile& ConfigFile, const FString& Section, const FString& Key, int32 DefaultValue = 0) const;
    void SetStringValue(FConfigFile& ConfigFile, const FString& Section, const FString& Key, const FString& Value) const;
    void SetBoolValue(FConfigFile& ConfigFile, const FString& Section, const FString& Key, bool bValue) const;
    void SetIntValue(FConfigFile& ConfigFile, const FString& Section, const FString& Key, int32 Value) const;
    FString SanitizeProfileName(const FString& ProfileName) const;
    TSharedPtr<FJsonObject> MakeConfigResult(const FString& StageName, const FConfigFile& ConfigFile, const FString& ConfigPath, bool bIncludePlugins) const;
    TSharedPtr<FJsonObject> MakePluginStatus(const FString& PluginName) const;
    TArray<TSharedPtr<FJsonValue>> MakeLaunchArgs(const FString& SignallingURL, const FString& StreamerId, bool bRenderOffscreen, int32 ResolutionX, int32 ResolutionY) const;
};
