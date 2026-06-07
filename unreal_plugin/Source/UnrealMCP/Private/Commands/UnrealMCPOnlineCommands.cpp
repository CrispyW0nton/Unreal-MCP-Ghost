#include "Commands/UnrealMCPOnlineCommands.h"

#include "Commands/UnrealMCPCommonUtils.h"
#include "Dom/JsonValue.h"
#include "Interfaces/IPluginManager.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/Paths.h"
#include "Misc/ScopedSlowTask.h"
#include "ScopedTransaction.h"

namespace
{
    const FString OnlineSubsystemSection = TEXT("OnlineSubsystem");
    const FString EOSSection = TEXT("OnlineSubsystemEOS");
}

FUnrealMCPOnlineCommands::FUnrealMCPOnlineCommands()
{
}

TSharedPtr<FJsonObject> FUnrealMCPOnlineCommands::HandleCommand(
    const FString& CommandType,
    const TSharedPtr<FJsonObject>& Params)
{
    if (CommandType == TEXT("online_inspect_config")) return HandleInspectConfig(Params);
    if (CommandType == TEXT("online_configure_default_subsystem")) return HandleConfigureDefaultSubsystem(Params);
    if (CommandType == TEXT("online_create_eos_artifact_config")) return HandleCreateEOSArtifactConfig(Params);
    if (CommandType == TEXT("online_configure_eos_sessions")) return HandleConfigureEOSSessions(Params);

    return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown Online Subsystem command: %s"), *CommandType));
}

FString FUnrealMCPOnlineCommands::GetDefaultEngineIniPath() const
{
    return FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectConfigDir(), TEXT("DefaultEngine.ini")));
}

bool FUnrealMCPOnlineCommands::LoadDefaultEngineConfig(FConfigFile& ConfigFile, FString& OutPath) const
{
    OutPath = GetDefaultEngineIniPath();
    ConfigFile.Empty();
    if (FPaths::FileExists(OutPath))
    {
        ConfigFile.Read(OutPath);
    }
    return true;
}

bool FUnrealMCPOnlineCommands::WriteDefaultEngineConfig(FConfigFile& ConfigFile, const FString& ConfigPath) const
{
    return ConfigFile.Write(ConfigPath);
}

FString FUnrealMCPOnlineCommands::GetStringValue(
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

bool FUnrealMCPOnlineCommands::GetBoolValue(
    const FConfigFile& ConfigFile,
    const FString& Section,
    const FString& Key,
    bool bDefaultValue) const
{
    bool bValue = bDefaultValue;
    ConfigFile.GetBool(*Section, *Key, bValue);
    return bValue;
}

void FUnrealMCPOnlineCommands::SetStringValue(
    FConfigFile& ConfigFile,
    const FString& Section,
    const FString& Key,
    const FString& Value) const
{
    ConfigFile.SetString(*Section, *Key, *Value);
}

void FUnrealMCPOnlineCommands::SetBoolValue(
    FConfigFile& ConfigFile,
    const FString& Section,
    const FString& Key,
    bool bValue) const
{
    ConfigFile.SetString(*Section, *Key, bValue ? TEXT("true") : TEXT("false"));
}

FString FUnrealMCPOnlineCommands::MaskSecret(const FString& Value) const
{
    if (Value.IsEmpty())
    {
        return FString();
    }
    if (Value.Len() <= 4)
    {
        return TEXT("****");
    }
    return FString::Printf(TEXT("%s****%s"), *Value.Left(2), *Value.Right(2));
}

TSharedPtr<FJsonObject> FUnrealMCPOnlineCommands::MakePluginStatus(const FString& PluginName) const
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

TSharedPtr<FJsonObject> FUnrealMCPOnlineCommands::MakeConfigResult(
    const FString& StageName,
    const FConfigFile& ConfigFile,
    const FString& ConfigPath,
    bool bIncludePlugins) const
{
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("stage"), StageName);
    Result->SetStringField(TEXT("config_path"), ConfigPath);

    TSharedPtr<FJsonObject> Online = MakeShared<FJsonObject>();
    Online->SetStringField(TEXT("default_platform_service"),
        GetStringValue(ConfigFile, OnlineSubsystemSection, TEXT("DefaultPlatformService")));
    Online->SetStringField(TEXT("native_platform_service"),
        GetStringValue(ConfigFile, OnlineSubsystemSection, TEXT("NativePlatformService")));
    Online->SetBoolField(TEXT("enabled"),
        GetBoolValue(ConfigFile, OnlineSubsystemSection, TEXT("bEnabled")));
    Result->SetObjectField(TEXT("online_subsystem"), Online);

    TSharedPtr<FJsonObject> EOS = MakeShared<FJsonObject>();
    EOS->SetBoolField(TEXT("enabled"), GetBoolValue(ConfigFile, EOSSection, TEXT("bEnabled")));
    EOS->SetStringField(TEXT("product_id"), GetStringValue(ConfigFile, EOSSection, TEXT("ProductId")));
    EOS->SetStringField(TEXT("sandbox_id"), GetStringValue(ConfigFile, EOSSection, TEXT("SandboxId")));
    EOS->SetStringField(TEXT("deployment_id"), GetStringValue(ConfigFile, EOSSection, TEXT("DeploymentId")));
    EOS->SetStringField(TEXT("client_id"), GetStringValue(ConfigFile, EOSSection, TEXT("ClientId")));
    EOS->SetStringField(TEXT("client_secret_masked"), MaskSecret(GetStringValue(ConfigFile, EOSSection, TEXT("ClientSecret"))));
    EOS->SetStringField(TEXT("encryption_key_masked"), MaskSecret(GetStringValue(ConfigFile, EOSSection, TEXT("EncryptionKey"))));
    EOS->SetBoolField(TEXT("use_eos_sessions"), GetBoolValue(ConfigFile, EOSSection, TEXT("bUseEOSSessions")));
    EOS->SetBoolField(TEXT("use_eos_lobbies"), GetBoolValue(ConfigFile, EOSSection, TEXT("bUseLobbiesIfAvailable")));
    EOS->SetBoolField(TEXT("use_eos_presence"), GetBoolValue(ConfigFile, EOSSection, TEXT("bUseEOSPresence")));
    EOS->SetBoolField(TEXT("use_eos_connect"), GetBoolValue(ConfigFile, EOSSection, TEXT("bUseEOSConnect")));
    EOS->SetBoolField(TEXT("mirror_stats_to_eos"), GetBoolValue(ConfigFile, EOSSection, TEXT("bMirrorStatsToEOS")));

    const FString ArtifactName = GetStringValue(ConfigFile, EOSSection, TEXT("DefaultArtifactName"));
    EOS->SetStringField(TEXT("default_artifact_name"), ArtifactName);
    if (!ArtifactName.IsEmpty())
    {
        const FString ArtifactSection = FString::Printf(TEXT("OnlineSubsystemEOS.Artifacts.%s"), *ArtifactName);
        TSharedPtr<FJsonObject> Artifact = MakeShared<FJsonObject>();
        Artifact->SetStringField(TEXT("artifact_name"), ArtifactName);
        Artifact->SetStringField(TEXT("product_id"), GetStringValue(ConfigFile, ArtifactSection, TEXT("ProductId")));
        Artifact->SetStringField(TEXT("sandbox_id"), GetStringValue(ConfigFile, ArtifactSection, TEXT("SandboxId")));
        Artifact->SetStringField(TEXT("deployment_id"), GetStringValue(ConfigFile, ArtifactSection, TEXT("DeploymentId")));
        Artifact->SetStringField(TEXT("client_id"), GetStringValue(ConfigFile, ArtifactSection, TEXT("ClientId")));
        Artifact->SetStringField(TEXT("client_secret_masked"), MaskSecret(GetStringValue(ConfigFile, ArtifactSection, TEXT("ClientSecret"))));
        Artifact->SetStringField(TEXT("encryption_key_masked"), MaskSecret(GetStringValue(ConfigFile, ArtifactSection, TEXT("EncryptionKey"))));
        EOS->SetObjectField(TEXT("default_artifact"), Artifact);
    }
    Result->SetObjectField(TEXT("eos"), EOS);

    if (bIncludePlugins)
    {
        TArray<TSharedPtr<FJsonValue>> Plugins;
        Plugins.Add(MakeShared<FJsonValueObject>(MakePluginStatus(TEXT("OnlineSubsystem"))));
        Plugins.Add(MakeShared<FJsonValueObject>(MakePluginStatus(TEXT("OnlineSubsystemUtils"))));
        Plugins.Add(MakeShared<FJsonValueObject>(MakePluginStatus(TEXT("OnlineSubsystemEOS"))));
        Plugins.Add(MakeShared<FJsonValueObject>(MakePluginStatus(TEXT("OnlineServicesEOS"))));
        Plugins.Add(MakeShared<FJsonValueObject>(MakePluginStatus(TEXT("OnlineServicesEOSGS"))));
        Result->SetArrayField(TEXT("plugins"), Plugins);
    }
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPOnlineCommands::HandleInspectConfig(const TSharedPtr<FJsonObject>& Params)
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
    return MakeConfigResult(TEXT("online_inspect_config"), ConfigFile, ConfigPath, bIncludePlugins);
}

TSharedPtr<FJsonObject> FUnrealMCPOnlineCommands::HandleConfigureDefaultSubsystem(const TSharedPtr<FJsonObject>& Params)
{
    if (!Params.IsValid())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing parameters"));
    }

    FString DefaultService = TEXT("EOS");
    Params->TryGetStringField(TEXT("default_service"), DefaultService);
    if (DefaultService.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'default_service' parameter"));
    }

    FString NativeService;
    Params->TryGetStringField(TEXT("native_service"), NativeService);
    bool bEnableOnlineSubsystem = true;
    Params->TryGetBoolField(TEXT("enable_online_subsystem"), bEnableOnlineSubsystem);

    FConfigFile ConfigFile;
    FString ConfigPath;
    if (!LoadDefaultEngineConfig(ConfigFile, ConfigPath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to read Config/DefaultEngine.ini"));
    }

    const FScopedTransaction Transaction(NSLOCTEXT("UnrealMCP", "ConfigureDefaultOnlineSubsystem", "Configure Default Online Subsystem"));
    FScopedSlowTask SlowTask(1.0f, NSLOCTEXT("UnrealMCP", "ConfigureDefaultOnlineSubsystemTask", "Configuring Online Subsystem"));
    SlowTask.MakeDialog(false);
    SlowTask.EnterProgressFrame(1.0f);

    SetBoolValue(ConfigFile, OnlineSubsystemSection, TEXT("bEnabled"), bEnableOnlineSubsystem);
    SetStringValue(ConfigFile, OnlineSubsystemSection, TEXT("DefaultPlatformService"), DefaultService);
    if (!NativeService.IsEmpty())
    {
        SetStringValue(ConfigFile, OnlineSubsystemSection, TEXT("NativePlatformService"), NativeService);
    }

    if (!WriteDefaultEngineConfig(ConfigFile, ConfigPath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to write Config/DefaultEngine.ini"));
    }
    return MakeConfigResult(TEXT("online_configure_default_subsystem"), ConfigFile, ConfigPath, true);
}

TSharedPtr<FJsonObject> FUnrealMCPOnlineCommands::HandleCreateEOSArtifactConfig(const TSharedPtr<FJsonObject>& Params)
{
    if (!Params.IsValid())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing parameters"));
    }

    FString ArtifactName;
    Params->TryGetStringField(TEXT("artifact_name"), ArtifactName);
    ArtifactName.TrimStartAndEndInline();
    if (ArtifactName.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'artifact_name' parameter"));
    }

    bool bStoreSecrets = false;
    Params->TryGetBoolField(TEXT("store_secrets"), bStoreSecrets);

    FConfigFile ConfigFile;
    FString ConfigPath;
    if (!LoadDefaultEngineConfig(ConfigFile, ConfigPath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to read Config/DefaultEngine.ini"));
    }

    const FScopedTransaction Transaction(NSLOCTEXT("UnrealMCP", "CreateEOSArtifactConfig", "Create EOS Artifact Config"));
    FScopedSlowTask SlowTask(1.0f, NSLOCTEXT("UnrealMCP", "CreateEOSArtifactConfigTask", "Configuring EOS artifact"));
    SlowTask.MakeDialog(false);
    SlowTask.EnterProgressFrame(1.0f);

    SetBoolValue(ConfigFile, EOSSection, TEXT("bEnabled"), true);
    SetStringValue(ConfigFile, EOSSection, TEXT("DefaultArtifactName"), ArtifactName);

    const FString ArtifactSection = FString::Printf(TEXT("OnlineSubsystemEOS.Artifacts.%s"), *ArtifactName);
    SetStringValue(ConfigFile, ArtifactSection, TEXT("ArtifactName"), ArtifactName);

    const TArray<FString> PublicKeys = {
        TEXT("product_id"),
        TEXT("sandbox_id"),
        TEXT("deployment_id"),
        TEXT("client_id")
    };
    const TMap<FString, FString> KeyMap = {
        {TEXT("product_id"), TEXT("ProductId")},
        {TEXT("sandbox_id"), TEXT("SandboxId")},
        {TEXT("deployment_id"), TEXT("DeploymentId")},
        {TEXT("client_id"), TEXT("ClientId")}
    };
    for (const FString& InputKey : PublicKeys)
    {
        FString Value;
        if (Params->TryGetStringField(*InputKey, Value) && !Value.IsEmpty())
        {
            if (const FString* OutputKey = KeyMap.Find(InputKey))
            {
                SetStringValue(ConfigFile, EOSSection, *OutputKey, Value);
                SetStringValue(ConfigFile, ArtifactSection, *OutputKey, Value);
            }
        }
    }

    if (bStoreSecrets)
    {
        FString ClientSecret;
        if (Params->TryGetStringField(TEXT("client_secret"), ClientSecret) && !ClientSecret.IsEmpty())
        {
            SetStringValue(ConfigFile, EOSSection, TEXT("ClientSecret"), ClientSecret);
            SetStringValue(ConfigFile, ArtifactSection, TEXT("ClientSecret"), ClientSecret);
        }
        FString EncryptionKey;
        if (Params->TryGetStringField(TEXT("encryption_key"), EncryptionKey) && !EncryptionKey.IsEmpty())
        {
            SetStringValue(ConfigFile, EOSSection, TEXT("EncryptionKey"), EncryptionKey);
            SetStringValue(ConfigFile, ArtifactSection, TEXT("EncryptionKey"), EncryptionKey);
        }
    }

    if (!WriteDefaultEngineConfig(ConfigFile, ConfigPath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to write Config/DefaultEngine.ini"));
    }

    TSharedPtr<FJsonObject> Result = MakeConfigResult(TEXT("online_create_eos_artifact_config"), ConfigFile, ConfigPath, true);
    Result->SetBoolField(TEXT("secrets_stored"), bStoreSecrets);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPOnlineCommands::HandleConfigureEOSSessions(const TSharedPtr<FJsonObject>& Params)
{
    FConfigFile ConfigFile;
    FString ConfigPath;
    if (!LoadDefaultEngineConfig(ConfigFile, ConfigPath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to read Config/DefaultEngine.ini"));
    }

    const FScopedTransaction Transaction(NSLOCTEXT("UnrealMCP", "ConfigureEOSSessions", "Configure EOS Sessions"));
    FScopedSlowTask SlowTask(1.0f, NSLOCTEXT("UnrealMCP", "ConfigureEOSSessionsTask", "Configuring EOS session flags"));
    SlowTask.MakeDialog(false);
    SlowTask.EnterProgressFrame(1.0f);

    bool bUseEOSSessions = true;
    bool bUseEOSLobbies = true;
    bool bUseEOSPresence = true;
    bool bUseEOSConnect = true;
    bool bMirrorStatsToEOS = false;
    if (Params.IsValid())
    {
        Params->TryGetBoolField(TEXT("use_eos_sessions"), bUseEOSSessions);
        Params->TryGetBoolField(TEXT("use_eos_lobbies"), bUseEOSLobbies);
        Params->TryGetBoolField(TEXT("use_eos_presence"), bUseEOSPresence);
        Params->TryGetBoolField(TEXT("use_eos_connect"), bUseEOSConnect);
        Params->TryGetBoolField(TEXT("mirror_stats_to_eos"), bMirrorStatsToEOS);
    }

    SetBoolValue(ConfigFile, EOSSection, TEXT("bEnabled"), true);
    SetBoolValue(ConfigFile, EOSSection, TEXT("bUseEOSSessions"), bUseEOSSessions);
    SetBoolValue(ConfigFile, EOSSection, TEXT("bUseLobbiesIfAvailable"), bUseEOSLobbies);
    SetBoolValue(ConfigFile, EOSSection, TEXT("bUseEOSPresence"), bUseEOSPresence);
    SetBoolValue(ConfigFile, EOSSection, TEXT("bUseEOSConnect"), bUseEOSConnect);
    SetBoolValue(ConfigFile, EOSSection, TEXT("bMirrorStatsToEOS"), bMirrorStatsToEOS);

    if (!WriteDefaultEngineConfig(ConfigFile, ConfigPath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to write Config/DefaultEngine.ini"));
    }
    return MakeConfigResult(TEXT("online_configure_eos_sessions"), ConfigFile, ConfigPath, true);
}
