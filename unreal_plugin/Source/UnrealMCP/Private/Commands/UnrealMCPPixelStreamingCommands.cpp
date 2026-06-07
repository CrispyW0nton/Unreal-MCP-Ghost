#include "Commands/UnrealMCPPixelStreamingCommands.h"

#include "Commands/UnrealMCPCommonUtils.h"
#include "Dom/JsonValue.h"
#include "Interfaces/IPluginManager.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/Paths.h"
#include "Misc/ScopedSlowTask.h"
#include "ScopedTransaction.h"

namespace
{
    const FString PixelStreamingSection = TEXT("PixelStreaming");
    const FString PixelStreaming2Section = TEXT("PixelStreaming2");
    const FString UnrealMCPPixelStreamingSection = TEXT("UnrealMCP.PixelStreaming");
    const FString ProfileSectionPrefix = TEXT("UnrealMCP.PixelStreamingProfiles.");
}

FUnrealMCPPixelStreamingCommands::FUnrealMCPPixelStreamingCommands()
{
}

TSharedPtr<FJsonObject> FUnrealMCPPixelStreamingCommands::HandleCommand(
    const FString& CommandType,
    const TSharedPtr<FJsonObject>& Params)
{
    if (CommandType == TEXT("pixelstream_inspect_config")) return HandleInspectConfig(Params);
    if (CommandType == TEXT("pixelstream_configure_plugin")) return HandleConfigurePlugin(Params);
    if (CommandType == TEXT("pixelstream_configure_streamer")) return HandleConfigureStreamer(Params);
    if (CommandType == TEXT("pixelstream_create_launch_profile")) return HandleCreateLaunchProfile(Params);

    return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown Pixel Streaming command: %s"), *CommandType));
}

FString FUnrealMCPPixelStreamingCommands::GetDefaultEngineIniPath() const
{
    return FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectConfigDir(), TEXT("DefaultEngine.ini")));
}

bool FUnrealMCPPixelStreamingCommands::LoadDefaultEngineConfig(FConfigFile& ConfigFile, FString& OutPath) const
{
    OutPath = GetDefaultEngineIniPath();
    ConfigFile.Empty();
    if (FPaths::FileExists(OutPath))
    {
        ConfigFile.Read(OutPath);
    }
    return true;
}

bool FUnrealMCPPixelStreamingCommands::WriteDefaultEngineConfig(FConfigFile& ConfigFile, const FString& ConfigPath) const
{
    return ConfigFile.Write(ConfigPath);
}

FString FUnrealMCPPixelStreamingCommands::GetStringValue(
    const FConfigFile& ConfigFile,
    const FString& Section,
    const FString& Key,
    const FString& DefaultValue) const
{
    FString Value;
    if (ConfigFile.GetString(*Section, *Key, Value))
    {
        return Value;
    }
    return DefaultValue;
}

bool FUnrealMCPPixelStreamingCommands::GetBoolValue(
    const FConfigFile& ConfigFile,
    const FString& Section,
    const FString& Key,
    bool bDefaultValue) const
{
    bool bValue = bDefaultValue;
    ConfigFile.GetBool(*Section, *Key, bValue);
    return bValue;
}

int32 FUnrealMCPPixelStreamingCommands::GetIntValue(
    const FConfigFile& ConfigFile,
    const FString& Section,
    const FString& Key,
    int32 DefaultValue) const
{
    int32 Value = DefaultValue;
    ConfigFile.GetInt(*Section, *Key, Value);
    return Value;
}

void FUnrealMCPPixelStreamingCommands::SetStringValue(
    FConfigFile& ConfigFile,
    const FString& Section,
    const FString& Key,
    const FString& Value) const
{
    ConfigFile.SetString(*Section, *Key, *Value);
}

void FUnrealMCPPixelStreamingCommands::SetBoolValue(
    FConfigFile& ConfigFile,
    const FString& Section,
    const FString& Key,
    bool bValue) const
{
    ConfigFile.SetString(*Section, *Key, bValue ? TEXT("true") : TEXT("false"));
}

void FUnrealMCPPixelStreamingCommands::SetIntValue(
    FConfigFile& ConfigFile,
    const FString& Section,
    const FString& Key,
    int32 Value) const
{
    ConfigFile.SetString(*Section, *Key, *FString::FromInt(Value));
}

FString FUnrealMCPPixelStreamingCommands::SanitizeProfileName(const FString& ProfileName) const
{
    FString Sanitized = ProfileName;
    Sanitized.TrimStartAndEndInline();
    if (Sanitized.IsEmpty())
    {
        Sanitized = TEXT("LocalPixelStreaming");
    }

    for (TCHAR& Ch : Sanitized)
    {
        if (!FChar::IsAlnum(Ch) && Ch != TCHAR('_') && Ch != TCHAR('-'))
        {
            Ch = TCHAR('_');
        }
    }
    return Sanitized;
}

TSharedPtr<FJsonObject> FUnrealMCPPixelStreamingCommands::MakePluginStatus(const FString& PluginName) const
{
    TSharedPtr<FJsonObject> Status = MakeShared<FJsonObject>();
    Status->SetStringField(TEXT("plugin"), PluginName);

    TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(PluginName);
    Status->SetBoolField(TEXT("installed"), Plugin.IsValid());
    if (Plugin.IsValid())
    {
        Status->SetBoolField(TEXT("enabled"), Plugin->IsEnabled());
        Status->SetStringField(TEXT("base_dir"), Plugin->GetBaseDir());
        Status->SetStringField(TEXT("version_name"), Plugin->GetDescriptor().VersionName);
    }
    return Status;
}

TArray<TSharedPtr<FJsonValue>> FUnrealMCPPixelStreamingCommands::MakeLaunchArgs(
    const FString& SignallingURL,
    const FString& StreamerId,
    bool bRenderOffscreen,
    int32 ResolutionX,
    int32 ResolutionY) const
{
    TArray<TSharedPtr<FJsonValue>> Args;
    Args.Add(MakeShared<FJsonValueString>(FString::Printf(TEXT("-PixelStreamingURL=%s"), *SignallingURL)));
    Args.Add(MakeShared<FJsonValueString>(FString::Printf(TEXT("-PixelStreamingStreamerId=%s"), *StreamerId)));
    if (bRenderOffscreen)
    {
        Args.Add(MakeShared<FJsonValueString>(TEXT("-RenderOffscreen")));
    }
    Args.Add(MakeShared<FJsonValueString>(TEXT("-ForceRes")));
    Args.Add(MakeShared<FJsonValueString>(FString::Printf(TEXT("-ResX=%d"), ResolutionX)));
    Args.Add(MakeShared<FJsonValueString>(FString::Printf(TEXT("-ResY=%d"), ResolutionY)));
    return Args;
}

TSharedPtr<FJsonObject> FUnrealMCPPixelStreamingCommands::MakeConfigResult(
    const FString& StageName,
    const FConfigFile& ConfigFile,
    const FString& ConfigPath,
    bool bIncludePlugins) const
{
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("stage"), StageName);
    Result->SetStringField(TEXT("config_path"), ConfigPath);

    TSharedPtr<FJsonObject> PluginConfig = MakeShared<FJsonObject>();
    PluginConfig->SetBoolField(TEXT("pixel_streaming_enabled"),
        GetBoolValue(ConfigFile, UnrealMCPPixelStreamingSection, TEXT("bPixelStreamingEnabled")));
    PluginConfig->SetBoolField(TEXT("pixel_streaming_2_enabled"),
        GetBoolValue(ConfigFile, UnrealMCPPixelStreamingSection, TEXT("bPixelStreaming2Enabled")));
    PluginConfig->SetBoolField(TEXT("prefer_pixel_streaming_2"),
        GetBoolValue(ConfigFile, UnrealMCPPixelStreamingSection, TEXT("bPreferPixelStreaming2")));
    Result->SetObjectField(TEXT("plugin_config"), PluginConfig);

    TSharedPtr<FJsonObject> PixelStreaming = MakeShared<FJsonObject>();
    PixelStreaming->SetBoolField(TEXT("enabled"), GetBoolValue(ConfigFile, PixelStreamingSection, TEXT("bEnabled")));
    PixelStreaming->SetStringField(TEXT("signalling_url"), GetStringValue(ConfigFile, PixelStreamingSection, TEXT("SignallingServerURL")));
    PixelStreaming->SetStringField(TEXT("streamer_id"), GetStringValue(ConfigFile, PixelStreamingSection, TEXT("StreamerId")));
    PixelStreaming->SetBoolField(TEXT("use_secure_websocket"), GetBoolValue(ConfigFile, PixelStreamingSection, TEXT("bUseSecureWebSocket")));
    PixelStreaming->SetBoolField(TEXT("render_offscreen"), GetBoolValue(ConfigFile, PixelStreamingSection, TEXT("bRenderOffscreen"), true));
    PixelStreaming->SetNumberField(TEXT("web_server_port"), GetIntValue(ConfigFile, PixelStreamingSection, TEXT("WebServerPort"), 80));
    PixelStreaming->SetNumberField(TEXT("signalling_port"), GetIntValue(ConfigFile, PixelStreamingSection, TEXT("SignallingPort"), 8888));
    PixelStreaming->SetNumberField(TEXT("encoder_target_bitrate"), GetIntValue(ConfigFile, PixelStreamingSection, TEXT("EncoderTargetBitrate"), 20000000));
    Result->SetObjectField(TEXT("pixel_streaming"), PixelStreaming);

    TSharedPtr<FJsonObject> PixelStreaming2 = MakeShared<FJsonObject>();
    PixelStreaming2->SetBoolField(TEXT("enabled"), GetBoolValue(ConfigFile, PixelStreaming2Section, TEXT("bEnabled")));
    PixelStreaming2->SetStringField(TEXT("signalling_url"), GetStringValue(ConfigFile, PixelStreaming2Section, TEXT("SignallingServerURL")));
    PixelStreaming2->SetStringField(TEXT("streamer_id"), GetStringValue(ConfigFile, PixelStreaming2Section, TEXT("StreamerId")));
    Result->SetObjectField(TEXT("pixel_streaming_2"), PixelStreaming2);

    if (bIncludePlugins)
    {
        TArray<TSharedPtr<FJsonValue>> Plugins;
        Plugins.Add(MakeShared<FJsonValueObject>(MakePluginStatus(TEXT("PixelStreaming"))));
        Plugins.Add(MakeShared<FJsonValueObject>(MakePluginStatus(TEXT("PixelStreaming2"))));
        Plugins.Add(MakeShared<FJsonValueObject>(MakePluginStatus(TEXT("PixelStreamingPlayer"))));
        Plugins.Add(MakeShared<FJsonValueObject>(MakePluginStatus(TEXT("PixelCapture"))));
        Result->SetArrayField(TEXT("plugins"), Plugins);
    }
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPPixelStreamingCommands::HandleInspectConfig(const TSharedPtr<FJsonObject>& Params)
{
    FConfigFile ConfigFile;
    FString ConfigPath;
    if (!LoadDefaultEngineConfig(ConfigFile, ConfigPath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to read Config/DefaultEngine.ini"));
    }

    bool bIncludePlugins = true;
    if (Params.IsValid())
    {
        Params->TryGetBoolField(TEXT("include_plugins"), bIncludePlugins);
    }
    return MakeConfigResult(TEXT("pixelstream_inspect_config"), ConfigFile, ConfigPath, bIncludePlugins);
}

TSharedPtr<FJsonObject> FUnrealMCPPixelStreamingCommands::HandleConfigurePlugin(const TSharedPtr<FJsonObject>& Params)
{
    bool bEnablePixelStreaming = true;
    bool bEnablePixelStreaming2 = false;
    bool bPreferPixelStreaming2 = false;
    if (Params.IsValid())
    {
        Params->TryGetBoolField(TEXT("enable_pixel_streaming"), bEnablePixelStreaming);
        Params->TryGetBoolField(TEXT("enable_pixel_streaming_2"), bEnablePixelStreaming2);
        Params->TryGetBoolField(TEXT("prefer_pixel_streaming_2"), bPreferPixelStreaming2);
    }

    FConfigFile ConfigFile;
    FString ConfigPath;
    if (!LoadDefaultEngineConfig(ConfigFile, ConfigPath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to read Config/DefaultEngine.ini"));
    }

    const FScopedTransaction Transaction(NSLOCTEXT("UnrealMCP", "ConfigurePixelStreamingPlugin", "Configure Pixel Streaming Plugin"));
    FScopedSlowTask SlowTask(1.0f, NSLOCTEXT("UnrealMCP", "ConfigurePixelStreamingPluginTask", "Configuring Pixel Streaming plugin flags"));
    SlowTask.MakeDialog(false);
    SlowTask.EnterProgressFrame(1.0f);

    SetBoolValue(ConfigFile, UnrealMCPPixelStreamingSection, TEXT("bPixelStreamingEnabled"), bEnablePixelStreaming);
    SetBoolValue(ConfigFile, UnrealMCPPixelStreamingSection, TEXT("bPixelStreaming2Enabled"), bEnablePixelStreaming2);
    SetBoolValue(ConfigFile, UnrealMCPPixelStreamingSection, TEXT("bPreferPixelStreaming2"), bPreferPixelStreaming2);
    SetBoolValue(ConfigFile, PixelStreamingSection, TEXT("bEnabled"), bEnablePixelStreaming);
    SetBoolValue(ConfigFile, PixelStreaming2Section, TEXT("bEnabled"), bEnablePixelStreaming2);

    if (!WriteDefaultEngineConfig(ConfigFile, ConfigPath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to write Config/DefaultEngine.ini"));
    }
    return MakeConfigResult(TEXT("pixelstream_configure_plugin"), ConfigFile, ConfigPath, true);
}

TSharedPtr<FJsonObject> FUnrealMCPPixelStreamingCommands::HandleConfigureStreamer(const TSharedPtr<FJsonObject>& Params)
{
    FString SignallingURL = TEXT("ws://127.0.0.1:8888");
    FString StreamerId = TEXT("DefaultStreamer");
    bool bUseSecureWebSocket = false;
    bool bRenderOffscreen = true;
    int32 WebServerPort = 80;
    int32 SignallingPort = 8888;
    int32 EncoderTargetBitrate = 20000000;

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("signalling_url"), SignallingURL);
        Params->TryGetStringField(TEXT("streamer_id"), StreamerId);
        Params->TryGetBoolField(TEXT("use_secure_websocket"), bUseSecureWebSocket);
        Params->TryGetBoolField(TEXT("render_offscreen"), bRenderOffscreen);

        double NumberValue = 0.0;
        if (Params->TryGetNumberField(TEXT("web_server_port"), NumberValue))
        {
            WebServerPort = FMath::Max(0, FMath::RoundToInt(NumberValue));
        }
        if (Params->TryGetNumberField(TEXT("signalling_port"), NumberValue))
        {
            SignallingPort = FMath::Max(0, FMath::RoundToInt(NumberValue));
        }
        if (Params->TryGetNumberField(TEXT("encoder_target_bitrate"), NumberValue))
        {
            EncoderTargetBitrate = FMath::Max(0, FMath::RoundToInt(NumberValue));
        }
    }

    FConfigFile ConfigFile;
    FString ConfigPath;
    if (!LoadDefaultEngineConfig(ConfigFile, ConfigPath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to read Config/DefaultEngine.ini"));
    }

    const FScopedTransaction Transaction(NSLOCTEXT("UnrealMCP", "ConfigurePixelStreamingStreamer", "Configure Pixel Streaming Streamer"));
    FScopedSlowTask SlowTask(1.0f, NSLOCTEXT("UnrealMCP", "ConfigurePixelStreamingStreamerTask", "Configuring Pixel Streaming streamer"));
    SlowTask.MakeDialog(false);
    SlowTask.EnterProgressFrame(1.0f);

    SetBoolValue(ConfigFile, UnrealMCPPixelStreamingSection, TEXT("bPixelStreamingEnabled"), true);
    SetBoolValue(ConfigFile, PixelStreamingSection, TEXT("bEnabled"), true);
    SetStringValue(ConfigFile, PixelStreamingSection, TEXT("SignallingServerURL"), SignallingURL);
    SetStringValue(ConfigFile, PixelStreamingSection, TEXT("StreamerId"), StreamerId);
    SetBoolValue(ConfigFile, PixelStreamingSection, TEXT("bUseSecureWebSocket"), bUseSecureWebSocket);
    SetBoolValue(ConfigFile, PixelStreamingSection, TEXT("bRenderOffscreen"), bRenderOffscreen);
    SetIntValue(ConfigFile, PixelStreamingSection, TEXT("WebServerPort"), WebServerPort);
    SetIntValue(ConfigFile, PixelStreamingSection, TEXT("SignallingPort"), SignallingPort);
    SetIntValue(ConfigFile, PixelStreamingSection, TEXT("EncoderTargetBitrate"), EncoderTargetBitrate);

    if (GetBoolValue(ConfigFile, UnrealMCPPixelStreamingSection, TEXT("bPixelStreaming2Enabled")))
    {
        SetStringValue(ConfigFile, PixelStreaming2Section, TEXT("SignallingServerURL"), SignallingURL);
        SetStringValue(ConfigFile, PixelStreaming2Section, TEXT("StreamerId"), StreamerId);
    }

    if (!WriteDefaultEngineConfig(ConfigFile, ConfigPath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to write Config/DefaultEngine.ini"));
    }
    return MakeConfigResult(TEXT("pixelstream_configure_streamer"), ConfigFile, ConfigPath, true);
}

TSharedPtr<FJsonObject> FUnrealMCPPixelStreamingCommands::HandleCreateLaunchProfile(const TSharedPtr<FJsonObject>& Params)
{
    FString ProfileName = TEXT("LocalPixelStreaming");
    FString SignallingURL = TEXT("ws://127.0.0.1:8888");
    FString StreamerId = TEXT("DefaultStreamer");
    bool bRenderOffscreen = true;
    int32 ResolutionX = 1280;
    int32 ResolutionY = 720;

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("profile_name"), ProfileName);
        Params->TryGetStringField(TEXT("signalling_url"), SignallingURL);
        Params->TryGetStringField(TEXT("streamer_id"), StreamerId);
        Params->TryGetBoolField(TEXT("render_offscreen"), bRenderOffscreen);

        double NumberValue = 0.0;
        if (Params->TryGetNumberField(TEXT("resolution_x"), NumberValue))
        {
            ResolutionX = FMath::Max(1, FMath::RoundToInt(NumberValue));
        }
        if (Params->TryGetNumberField(TEXT("resolution_y"), NumberValue))
        {
            ResolutionY = FMath::Max(1, FMath::RoundToInt(NumberValue));
        }
    }

    const FString SanitizedProfileName = SanitizeProfileName(ProfileName);
    const FString ProfileSection = ProfileSectionPrefix + SanitizedProfileName;

    FConfigFile ConfigFile;
    FString ConfigPath;
    if (!LoadDefaultEngineConfig(ConfigFile, ConfigPath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to read Config/DefaultEngine.ini"));
    }

    const FScopedTransaction Transaction(NSLOCTEXT("UnrealMCP", "CreatePixelStreamingLaunchProfile", "Create Pixel Streaming Launch Profile"));
    FScopedSlowTask SlowTask(1.0f, NSLOCTEXT("UnrealMCP", "CreatePixelStreamingLaunchProfileTask", "Creating Pixel Streaming launch profile"));
    SlowTask.MakeDialog(false);
    SlowTask.EnterProgressFrame(1.0f);

    SetStringValue(ConfigFile, ProfileSection, TEXT("ProfileName"), ProfileName);
    SetStringValue(ConfigFile, ProfileSection, TEXT("SanitizedProfileName"), SanitizedProfileName);
    SetStringValue(ConfigFile, ProfileSection, TEXT("SignallingServerURL"), SignallingURL);
    SetStringValue(ConfigFile, ProfileSection, TEXT("StreamerId"), StreamerId);
    SetBoolValue(ConfigFile, ProfileSection, TEXT("bRenderOffscreen"), bRenderOffscreen);
    SetIntValue(ConfigFile, ProfileSection, TEXT("ResolutionX"), ResolutionX);
    SetIntValue(ConfigFile, ProfileSection, TEXT("ResolutionY"), ResolutionY);

    if (!WriteDefaultEngineConfig(ConfigFile, ConfigPath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to write Config/DefaultEngine.ini"));
    }

    TSharedPtr<FJsonObject> Result = MakeConfigResult(TEXT("pixelstream_create_launch_profile"), ConfigFile, ConfigPath, true);
    TSharedPtr<FJsonObject> Profile = MakeShared<FJsonObject>();
    Profile->SetStringField(TEXT("profile_name"), ProfileName);
    Profile->SetStringField(TEXT("sanitized_profile_name"), SanitizedProfileName);
    Profile->SetStringField(TEXT("section"), ProfileSection);
    Profile->SetStringField(TEXT("signalling_url"), SignallingURL);
    Profile->SetStringField(TEXT("streamer_id"), StreamerId);
    Profile->SetBoolField(TEXT("render_offscreen"), bRenderOffscreen);
    Profile->SetNumberField(TEXT("resolution_x"), ResolutionX);
    Profile->SetNumberField(TEXT("resolution_y"), ResolutionY);
    Result->SetObjectField(TEXT("launch_profile"), Profile);
    Result->SetArrayField(TEXT("launch_args"), MakeLaunchArgs(SignallingURL, StreamerId, bRenderOffscreen, ResolutionX, ResolutionY));
    return Result;
}
