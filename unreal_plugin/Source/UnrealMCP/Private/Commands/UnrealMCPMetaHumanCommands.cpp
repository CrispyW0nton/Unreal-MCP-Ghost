#include "Commands/UnrealMCPMetaHumanCommands.h"

#include "Animation/Skeleton.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Commands/UnrealMCPCommonUtils.h"
#include "Dom/JsonValue.h"
#include "Engine/SkeletalMesh.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/Paths.h"
#include "Misc/ScopedSlowTask.h"
#include "Modules/ModuleManager.h"
#include "ScopedTransaction.h"

namespace
{
    const FString MetaHumanSectionPrefix = TEXT("UnrealMCP.MetaHuman.");
}

FUnrealMCPMetaHumanCommands::FUnrealMCPMetaHumanCommands()
{
}

TSharedPtr<FJsonObject> FUnrealMCPMetaHumanCommands::HandleCommand(
    const FString& CommandType,
    const TSharedPtr<FJsonObject>& Params)
{
    if (CommandType == TEXT("metahuman_import")) return HandleImport(Params);
    if (CommandType == TEXT("metahuman_inspect_package")) return HandleInspectPackage(Params);
    if (CommandType == TEXT("metahuman_link_to_skeleton")) return HandleLinkToSkeleton(Params);
    if (CommandType == TEXT("metahuman_assign_dna")) return HandleAssignDNA(Params);
    if (CommandType == TEXT("metahuman_configure_wrapper")) return HandleConfigureWrapper(Params);

    return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown MetaHuman command: %s"), *CommandType));
}

FString FUnrealMCPMetaHumanCommands::GetDefaultEngineIniPath() const
{
    return FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectConfigDir(), TEXT("DefaultEngine.ini")));
}

bool FUnrealMCPMetaHumanCommands::LoadDefaultEngineConfig(FConfigFile& ConfigFile, FString& OutPath) const
{
    OutPath = GetDefaultEngineIniPath();
    ConfigFile.Empty();
    if (FPaths::FileExists(OutPath))
    {
        ConfigFile.Read(OutPath);
    }
    return true;
}

bool FUnrealMCPMetaHumanCommands::WriteDefaultEngineConfig(FConfigFile& ConfigFile, const FString& ConfigPath) const
{
    return ConfigFile.Write(ConfigPath);
}

FString FUnrealMCPMetaHumanCommands::GetStringValue(
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

void FUnrealMCPMetaHumanCommands::SetStringValue(
    FConfigFile& ConfigFile,
    const FString& Section,
    const FString& Key,
    const FString& Value) const
{
    ConfigFile.SetString(*Section, *Key, *Value);
}

void FUnrealMCPMetaHumanCommands::SetBoolValue(
    FConfigFile& ConfigFile,
    const FString& Section,
    const FString& Key,
    bool bValue) const
{
    ConfigFile.SetString(*Section, *Key, bValue ? TEXT("true") : TEXT("false"));
}

FString FUnrealMCPMetaHumanCommands::NormalizeAssetPath(const FString& InPath) const
{
    FString AssetPath = InPath;
    AssetPath.TrimStartAndEndInline();
    if (AssetPath.Contains(TEXT(".")))
    {
        AssetPath.LeftInline(AssetPath.Find(TEXT(".")));
    }
    AssetPath.RemoveFromEnd(TEXT("/"));
    return AssetPath;
}

FString FUnrealMCPMetaHumanCommands::MakeObjectPath(const FString& AssetPath) const
{
    const FString CleanPath = NormalizeAssetPath(AssetPath);
    return FString::Printf(TEXT("%s.%s"), *CleanPath, *FPaths::GetBaseFilename(CleanPath));
}

FString FUnrealMCPMetaHumanCommands::SanitizeName(const FString& Name) const
{
    FString Sanitized = Name;
    Sanitized.TrimStartAndEndInline();
    if (Sanitized.IsEmpty())
    {
        Sanitized = TEXT("MetaHuman");
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

FString FUnrealMCPMetaHumanCommands::MakeManifestSection(const FString& CharacterName) const
{
    return MetaHumanSectionPrefix + SanitizeName(CharacterName);
}

UObject* FUnrealMCPMetaHumanCommands::LoadAsset(const FString& AssetOrObjectPath) const
{
    if (AssetOrObjectPath.IsEmpty())
    {
        return nullptr;
    }
    const FString ObjectPath = AssetOrObjectPath.Contains(TEXT("."))
        ? AssetOrObjectPath
        : MakeObjectPath(AssetOrObjectPath);
    if (UObject* Loaded = StaticLoadObject(UObject::StaticClass(), nullptr, *ObjectPath))
    {
        return Loaded;
    }
    return StaticLoadObject(UObject::StaticClass(), nullptr, *AssetOrObjectPath);
}

TArray<FAssetData> FUnrealMCPMetaHumanCommands::ScanAssetsUnderRoot(const FString& RootPath) const
{
    TArray<FAssetData> Assets;
    const FString CleanRoot = NormalizeAssetPath(RootPath);
    if (!CleanRoot.StartsWith(TEXT("/Game")))
    {
        return Assets;
    }

    FAssetRegistryModule& AssetRegistryModule =
        FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));
    FARFilter Filter;
    Filter.PackagePaths.Add(FName(*CleanRoot));
    Filter.bRecursivePaths = true;
    AssetRegistryModule.Get().GetAssets(Filter, Assets);
    return Assets;
}

TArray<TSharedPtr<FJsonValue>> FUnrealMCPMetaHumanCommands::MakeAssetSummaries(const TArray<FAssetData>& Assets) const
{
    TArray<TSharedPtr<FJsonValue>> Summaries;
    for (const FAssetData& Asset : Assets)
    {
        TSharedPtr<FJsonObject> Summary = MakeShared<FJsonObject>();
        Summary->SetStringField(TEXT("asset_name"), Asset.AssetName.ToString());
        Summary->SetStringField(TEXT("package_name"), Asset.PackageName.ToString());
        Summary->SetStringField(TEXT("object_path"), Asset.GetObjectPathString());
        Summary->SetStringField(TEXT("class"), Asset.AssetClassPath.GetAssetName().ToString());
        Summaries.Add(MakeShared<FJsonValueObject>(Summary));
    }
    return Summaries;
}

TSharedPtr<FJsonObject> FUnrealMCPMetaHumanCommands::MakeAssetClassCounts(const TArray<FAssetData>& Assets) const
{
    TMap<FString, int32> Counts;
    for (const FAssetData& Asset : Assets)
    {
        Counts.FindOrAdd(Asset.AssetClassPath.GetAssetName().ToString())++;
    }

    TSharedPtr<FJsonObject> CountsObject = MakeShared<FJsonObject>();
    for (const TPair<FString, int32>& Pair : Counts)
    {
        CountsObject->SetNumberField(Pair.Key, Pair.Value);
    }
    return CountsObject;
}

TSharedPtr<FJsonObject> FUnrealMCPMetaHumanCommands::HandleImport(const TSharedPtr<FJsonObject>& Params)
{
    if (!Params.IsValid())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing parameters"));
    }

    FString CharacterName;
    Params->TryGetStringField(TEXT("character_name"), CharacterName);
    CharacterName.TrimStartAndEndInline();
    if (CharacterName.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'character_name' parameter"));
    }

    FString MetaHumanRoot = FString::Printf(TEXT("/Game/MetaHumans/%s"), *SanitizeName(CharacterName));
    Params->TryGetStringField(TEXT("metahuman_root"), MetaHumanRoot);
    MetaHumanRoot = NormalizeAssetPath(MetaHumanRoot);

    FString ExpectedBlueprint;
    FString BodySkeletalMesh;
    FString FaceSkeletalMesh;
    Params->TryGetStringField(TEXT("expected_blueprint"), ExpectedBlueprint);
    Params->TryGetStringField(TEXT("body_skeletal_mesh"), BodySkeletalMesh);
    Params->TryGetStringField(TEXT("face_skeletal_mesh"), FaceSkeletalMesh);

    bool bCreateManifest = true;
    Params->TryGetBoolField(TEXT("create_manifest"), bCreateManifest);

    TArray<TSharedPtr<FJsonValue>> Warnings;
    const TArray<FAssetData> Assets = ScanAssetsUnderRoot(MetaHumanRoot);
    if (Assets.Num() == 0)
    {
        Warnings.Add(MakeShared<FJsonValueString>(
            FString::Printf(TEXT("No assets discovered under %s; run after MetaHuman assembly/import or pass the exact root."), *MetaHumanRoot)));
    }

    FConfigFile ConfigFile;
    FString ConfigPath;
    if (!LoadDefaultEngineConfig(ConfigFile, ConfigPath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to read Config/DefaultEngine.ini"));
    }

    const FScopedTransaction Transaction(NSLOCTEXT("UnrealMCP", "RegisterMetaHumanPackage", "Register MetaHuman Package"));
    FScopedSlowTask SlowTask(1.0f, NSLOCTEXT("UnrealMCP", "RegisterMetaHumanPackageTask", "Registering MetaHuman package"));
    SlowTask.MakeDialog(false);
    SlowTask.EnterProgressFrame(1.0f);

    const FString Section = MakeManifestSection(CharacterName);
    if (bCreateManifest)
    {
        SetStringValue(ConfigFile, Section, TEXT("CharacterName"), CharacterName);
        SetStringValue(ConfigFile, Section, TEXT("MetaHumanRoot"), MetaHumanRoot);
        SetStringValue(ConfigFile, Section, TEXT("ExpectedBlueprint"), ExpectedBlueprint);
        SetStringValue(ConfigFile, Section, TEXT("BodySkeletalMesh"), BodySkeletalMesh);
        SetStringValue(ConfigFile, Section, TEXT("FaceSkeletalMesh"), FaceSkeletalMesh);
        SetStringValue(ConfigFile, Section, TEXT("AssetCount"), FString::FromInt(Assets.Num()));
        SetBoolValue(ConfigFile, Section, TEXT("bRegisteredByMCP"), true);

        if (!WriteDefaultEngineConfig(ConfigFile, ConfigPath))
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to write Config/DefaultEngine.ini"));
        }
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("stage"), TEXT("metahuman_import"));
    Result->SetStringField(TEXT("config_path"), ConfigPath);
    Result->SetStringField(TEXT("manifest_section"), Section);
    Result->SetStringField(TEXT("character_name"), CharacterName);
    Result->SetStringField(TEXT("metahuman_root"), MetaHumanRoot);
    Result->SetBoolField(TEXT("manifest_created"), bCreateManifest);
    Result->SetNumberField(TEXT("asset_count"), Assets.Num());
    Result->SetObjectField(TEXT("asset_class_counts"), MakeAssetClassCounts(Assets));
    Result->SetArrayField(TEXT("assets"), MakeAssetSummaries(Assets));
    Result->SetArrayField(TEXT("warnings"), Warnings);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPMetaHumanCommands::HandleInspectPackage(const TSharedPtr<FJsonObject>& Params)
{
    if (!Params.IsValid())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing parameters"));
    }

    FString CharacterName;
    Params->TryGetStringField(TEXT("character_name"), CharacterName);
    CharacterName.TrimStartAndEndInline();
    if (CharacterName.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'character_name' parameter"));
    }

    FConfigFile ConfigFile;
    FString ConfigPath;
    if (!LoadDefaultEngineConfig(ConfigFile, ConfigPath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to read Config/DefaultEngine.ini"));
    }

    const FString Section = MakeManifestSection(CharacterName);
    FString MetaHumanRoot = GetStringValue(ConfigFile, Section, TEXT("MetaHumanRoot"),
        FString::Printf(TEXT("/Game/MetaHumans/%s"), *SanitizeName(CharacterName)));
    Params->TryGetStringField(TEXT("metahuman_root"), MetaHumanRoot);
    MetaHumanRoot = NormalizeAssetPath(MetaHumanRoot);

    const TArray<FAssetData> Assets = ScanAssetsUnderRoot(MetaHumanRoot);

    TSharedPtr<FJsonObject> Manifest = MakeShared<FJsonObject>();
    Manifest->SetStringField(TEXT("character_name"), GetStringValue(ConfigFile, Section, TEXT("CharacterName"), CharacterName));
    Manifest->SetStringField(TEXT("metahuman_root"), MetaHumanRoot);
    Manifest->SetStringField(TEXT("expected_blueprint"), GetStringValue(ConfigFile, Section, TEXT("ExpectedBlueprint")));
    Manifest->SetStringField(TEXT("body_skeletal_mesh"), GetStringValue(ConfigFile, Section, TEXT("BodySkeletalMesh")));
    Manifest->SetStringField(TEXT("face_skeletal_mesh"), GetStringValue(ConfigFile, Section, TEXT("FaceSkeletalMesh")));
    Manifest->SetStringField(TEXT("target_skeleton"), GetStringValue(ConfigFile, Section, TEXT("TargetSkeleton")));
    Manifest->SetStringField(TEXT("ik_rig"), GetStringValue(ConfigFile, Section, TEXT("IKRig")));
    Manifest->SetStringField(TEXT("retargeter"), GetStringValue(ConfigFile, Section, TEXT("Retargeter")));
    Manifest->SetStringField(TEXT("anim_blueprint"), GetStringValue(ConfigFile, Section, TEXT("AnimBlueprint")));
    Manifest->SetStringField(TEXT("post_process_anim_blueprint"), GetStringValue(ConfigFile, Section, TEXT("PostProcessAnimBlueprint")));
    Manifest->SetStringField(TEXT("dna_asset"), GetStringValue(ConfigFile, Section, TEXT("DNAAsset")));
    Manifest->SetStringField(TEXT("dna_file"), GetStringValue(ConfigFile, Section, TEXT("DNAFile")));
    Manifest->SetStringField(TEXT("rig_logic_asset"), GetStringValue(ConfigFile, Section, TEXT("RigLogicAsset")));
    Manifest->SetStringField(TEXT("wrapper_blueprint"), GetStringValue(ConfigFile, Section, TEXT("WrapperBlueprint")));
    Manifest->SetStringField(TEXT("wrapper_parent_class"), GetStringValue(ConfigFile, Section, TEXT("WrapperParentClass")));

    TArray<TSharedPtr<FJsonValue>> Warnings;
    if (Assets.Num() == 0)
    {
        Warnings.Add(MakeShared<FJsonValueString>(FString::Printf(TEXT("No assets discovered under %s"), *MetaHumanRoot)));
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("stage"), TEXT("metahuman_inspect_package"));
    Result->SetStringField(TEXT("config_path"), ConfigPath);
    Result->SetStringField(TEXT("manifest_section"), Section);
    Result->SetObjectField(TEXT("manifest"), Manifest);
    Result->SetNumberField(TEXT("asset_count"), Assets.Num());
    Result->SetObjectField(TEXT("asset_class_counts"), MakeAssetClassCounts(Assets));
    Result->SetArrayField(TEXT("assets"), MakeAssetSummaries(Assets));
    Result->SetArrayField(TEXT("warnings"), Warnings);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPMetaHumanCommands::HandleLinkToSkeleton(const TSharedPtr<FJsonObject>& Params)
{
    if (!Params.IsValid())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing parameters"));
    }

    FString CharacterName;
    FString BodySkeletalMeshPath;
    Params->TryGetStringField(TEXT("character_name"), CharacterName);
    Params->TryGetStringField(TEXT("body_skeletal_mesh"), BodySkeletalMeshPath);
    CharacterName.TrimStartAndEndInline();
    BodySkeletalMeshPath.TrimStartAndEndInline();
    if (CharacterName.IsEmpty() || BodySkeletalMeshPath.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'character_name' or 'body_skeletal_mesh' parameter"));
    }

    USkeletalMesh* BodyMesh = Cast<USkeletalMesh>(LoadAsset(BodySkeletalMeshPath));
    if (!BodyMesh)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Body skeletal mesh not found: %s"), *BodySkeletalMeshPath));
    }

    FString TargetSkeletonPath;
    FString IKRigPath;
    FString RetargeterPath;
    FString AnimBlueprintPath;
    FString PostProcessAnimBlueprintPath;
    Params->TryGetStringField(TEXT("target_skeleton"), TargetSkeletonPath);
    Params->TryGetStringField(TEXT("ik_rig"), IKRigPath);
    Params->TryGetStringField(TEXT("retargeter"), RetargeterPath);
    Params->TryGetStringField(TEXT("anim_blueprint"), AnimBlueprintPath);
    Params->TryGetStringField(TEXT("post_process_anim_blueprint"), PostProcessAnimBlueprintPath);

    TArray<TSharedPtr<FJsonValue>> Warnings;
    USkeleton* TargetSkeleton = nullptr;
    if (!TargetSkeletonPath.IsEmpty())
    {
        TargetSkeleton = Cast<USkeleton>(LoadAsset(TargetSkeletonPath));
        if (!TargetSkeleton)
        {
            Warnings.Add(MakeShared<FJsonValueString>(FString::Printf(TEXT("Target skeleton was not found: %s"), *TargetSkeletonPath)));
        }
    }
    if (!TargetSkeleton && BodyMesh->GetSkeleton())
    {
        TargetSkeleton = BodyMesh->GetSkeleton();
        TargetSkeletonPath = TargetSkeleton->GetPathName();
    }

    const TMap<FString, FString> OptionalAssets = {
        {TEXT("ik_rig"), IKRigPath},
        {TEXT("retargeter"), RetargeterPath},
        {TEXT("anim_blueprint"), AnimBlueprintPath},
        {TEXT("post_process_anim_blueprint"), PostProcessAnimBlueprintPath}
    };
    for (const TPair<FString, FString>& Pair : OptionalAssets)
    {
        if (!Pair.Value.IsEmpty() && !LoadAsset(Pair.Value))
        {
            Warnings.Add(MakeShared<FJsonValueString>(FString::Printf(TEXT("%s asset was not found: %s"), *Pair.Key, *Pair.Value)));
        }
    }

    FConfigFile ConfigFile;
    FString ConfigPath;
    if (!LoadDefaultEngineConfig(ConfigFile, ConfigPath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to read Config/DefaultEngine.ini"));
    }

    const FScopedTransaction Transaction(NSLOCTEXT("UnrealMCP", "LinkMetaHumanSkeleton", "Link MetaHuman Skeleton"));
    FScopedSlowTask SlowTask(1.0f, NSLOCTEXT("UnrealMCP", "LinkMetaHumanSkeletonTask", "Linking MetaHuman skeleton"));
    SlowTask.MakeDialog(false);
    SlowTask.EnterProgressFrame(1.0f);

    const FString Section = MakeManifestSection(CharacterName);
    SetStringValue(ConfigFile, Section, TEXT("CharacterName"), CharacterName);
    SetStringValue(ConfigFile, Section, TEXT("BodySkeletalMesh"), NormalizeAssetPath(BodySkeletalMeshPath));
    SetStringValue(ConfigFile, Section, TEXT("TargetSkeleton"), TargetSkeletonPath);
    SetStringValue(ConfigFile, Section, TEXT("IKRig"), IKRigPath);
    SetStringValue(ConfigFile, Section, TEXT("Retargeter"), RetargeterPath);
    SetStringValue(ConfigFile, Section, TEXT("AnimBlueprint"), AnimBlueprintPath);
    SetStringValue(ConfigFile, Section, TEXT("PostProcessAnimBlueprint"), PostProcessAnimBlueprintPath);
    SetBoolValue(ConfigFile, Section, TEXT("bSkeletonLinkedByMCP"), true);

    if (!WriteDefaultEngineConfig(ConfigFile, ConfigPath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to write Config/DefaultEngine.ini"));
    }

    TSharedPtr<FJsonObject> Links = MakeShared<FJsonObject>();
    Links->SetStringField(TEXT("body_skeletal_mesh"), NormalizeAssetPath(BodySkeletalMeshPath));
    Links->SetStringField(TEXT("target_skeleton"), TargetSkeletonPath);
    Links->SetStringField(TEXT("ik_rig"), IKRigPath);
    Links->SetStringField(TEXT("retargeter"), RetargeterPath);
    Links->SetStringField(TEXT("anim_blueprint"), AnimBlueprintPath);
    Links->SetStringField(TEXT("post_process_anim_blueprint"), PostProcessAnimBlueprintPath);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("stage"), TEXT("metahuman_link_to_skeleton"));
    Result->SetStringField(TEXT("config_path"), ConfigPath);
    Result->SetStringField(TEXT("manifest_section"), Section);
    Result->SetObjectField(TEXT("skeleton_links"), Links);
    Result->SetArrayField(TEXT("warnings"), Warnings);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPMetaHumanCommands::HandleConfigureWrapper(const TSharedPtr<FJsonObject>& Params)
{
    if (!Params.IsValid())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing parameters"));
    }

    FString CharacterName;
    FString WrapperBlueprint;
    Params->TryGetStringField(TEXT("character_name"), CharacterName);
    Params->TryGetStringField(TEXT("wrapper_blueprint"), WrapperBlueprint);
    CharacterName.TrimStartAndEndInline();
    WrapperBlueprint.TrimStartAndEndInline();
    if (CharacterName.IsEmpty() || WrapperBlueprint.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'character_name' or 'wrapper_blueprint' parameter"));
    }

    FString ParentClass = TEXT("/Script/Engine.Character");
    FString BodyComponentName = TEXT("Body");
    FString FaceComponentName = TEXT("Face");
    FString AttachToComponent = TEXT("Mesh");
    FString GameplayTag = TEXT("Character.MetaHuman");
    Params->TryGetStringField(TEXT("parent_class"), ParentClass);
    Params->TryGetStringField(TEXT("body_component_name"), BodyComponentName);
    Params->TryGetStringField(TEXT("face_component_name"), FaceComponentName);
    Params->TryGetStringField(TEXT("attach_to_component"), AttachToComponent);
    Params->TryGetStringField(TEXT("gameplay_tag"), GameplayTag);

    FConfigFile ConfigFile;
    FString ConfigPath;
    if (!LoadDefaultEngineConfig(ConfigFile, ConfigPath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to read Config/DefaultEngine.ini"));
    }

    const FScopedTransaction Transaction(NSLOCTEXT("UnrealMCP", "ConfigureMetaHumanWrapper", "Configure MetaHuman Wrapper"));
    FScopedSlowTask SlowTask(1.0f, NSLOCTEXT("UnrealMCP", "ConfigureMetaHumanWrapperTask", "Configuring MetaHuman wrapper metadata"));
    SlowTask.MakeDialog(false);
    SlowTask.EnterProgressFrame(1.0f);

    const FString Section = MakeManifestSection(CharacterName);
    SetStringValue(ConfigFile, Section, TEXT("CharacterName"), CharacterName);
    SetStringValue(ConfigFile, Section, TEXT("WrapperBlueprint"), NormalizeAssetPath(WrapperBlueprint));
    SetStringValue(ConfigFile, Section, TEXT("WrapperParentClass"), ParentClass);
    SetStringValue(ConfigFile, Section, TEXT("BodyComponentName"), BodyComponentName);
    SetStringValue(ConfigFile, Section, TEXT("FaceComponentName"), FaceComponentName);
    SetStringValue(ConfigFile, Section, TEXT("AttachToComponent"), AttachToComponent);
    SetStringValue(ConfigFile, Section, TEXT("GameplayTag"), GameplayTag);
    SetBoolValue(ConfigFile, Section, TEXT("bWrapperConfiguredByMCP"), true);

    if (!WriteDefaultEngineConfig(ConfigFile, ConfigPath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to write Config/DefaultEngine.ini"));
    }

    TSharedPtr<FJsonObject> Wrapper = MakeShared<FJsonObject>();
    Wrapper->SetStringField(TEXT("wrapper_blueprint"), NormalizeAssetPath(WrapperBlueprint));
    Wrapper->SetStringField(TEXT("parent_class"), ParentClass);
    Wrapper->SetStringField(TEXT("body_component_name"), BodyComponentName);
    Wrapper->SetStringField(TEXT("face_component_name"), FaceComponentName);
    Wrapper->SetStringField(TEXT("attach_to_component"), AttachToComponent);
    Wrapper->SetStringField(TEXT("gameplay_tag"), GameplayTag);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("stage"), TEXT("metahuman_configure_wrapper"));
    Result->SetStringField(TEXT("config_path"), ConfigPath);
    Result->SetStringField(TEXT("manifest_section"), Section);
    Result->SetObjectField(TEXT("wrapper"), Wrapper);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPMetaHumanCommands::HandleAssignDNA(const TSharedPtr<FJsonObject>& Params)
{
    if (!Params.IsValid())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing parameters"));
    }

    FString CharacterName;
    FString DNAAsset;
    FString DNAFile;
    FString FaceSkeletalMesh;
    FString RigLogicAsset;
    Params->TryGetStringField(TEXT("character_name"), CharacterName);
    Params->TryGetStringField(TEXT("dna_asset"), DNAAsset);
    Params->TryGetStringField(TEXT("dna_file"), DNAFile);
    Params->TryGetStringField(TEXT("face_skeletal_mesh"), FaceSkeletalMesh);
    Params->TryGetStringField(TEXT("rig_logic_asset"), RigLogicAsset);
    CharacterName.TrimStartAndEndInline();
    DNAAsset.TrimStartAndEndInline();
    DNAFile.TrimStartAndEndInline();
    if (CharacterName.IsEmpty() || (DNAAsset.IsEmpty() && DNAFile.IsEmpty()))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'character_name' and either 'dna_asset' or 'dna_file' parameter"));
    }

    TArray<TSharedPtr<FJsonValue>> Warnings;
    if (!DNAAsset.IsEmpty() && !LoadAsset(DNAAsset))
    {
        Warnings.Add(MakeShared<FJsonValueString>(FString::Printf(TEXT("DNA asset was not found: %s"), *DNAAsset)));
    }
    if (!DNAFile.IsEmpty() && !FPaths::FileExists(DNAFile))
    {
        Warnings.Add(MakeShared<FJsonValueString>(FString::Printf(TEXT("DNA file was not found on disk: %s"), *DNAFile)));
    }
    if (!FaceSkeletalMesh.IsEmpty() && !LoadAsset(FaceSkeletalMesh))
    {
        Warnings.Add(MakeShared<FJsonValueString>(FString::Printf(TEXT("Face skeletal mesh was not found: %s"), *FaceSkeletalMesh)));
    }
    if (!RigLogicAsset.IsEmpty() && !LoadAsset(RigLogicAsset))
    {
        Warnings.Add(MakeShared<FJsonValueString>(FString::Printf(TEXT("Rig logic asset was not found: %s"), *RigLogicAsset)));
    }

    FConfigFile ConfigFile;
    FString ConfigPath;
    if (!LoadDefaultEngineConfig(ConfigFile, ConfigPath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to read Config/DefaultEngine.ini"));
    }

    const FScopedTransaction Transaction(NSLOCTEXT("UnrealMCP", "AssignMetaHumanDNA", "Assign MetaHuman DNA"));
    FScopedSlowTask SlowTask(1.0f, NSLOCTEXT("UnrealMCP", "AssignMetaHumanDNATask", "Assigning MetaHuman DNA metadata"));
    SlowTask.MakeDialog(false);
    SlowTask.EnterProgressFrame(1.0f);

    const FString Section = MakeManifestSection(CharacterName);
    SetStringValue(ConfigFile, Section, TEXT("CharacterName"), CharacterName);
    SetStringValue(ConfigFile, Section, TEXT("DNAAsset"), DNAAsset);
    SetStringValue(ConfigFile, Section, TEXT("DNAFile"), DNAFile);
    SetStringValue(ConfigFile, Section, TEXT("FaceSkeletalMesh"), FaceSkeletalMesh);
    SetStringValue(ConfigFile, Section, TEXT("RigLogicAsset"), RigLogicAsset);
    SetBoolValue(ConfigFile, Section, TEXT("bDNAAssignedByMCP"), true);

    if (!WriteDefaultEngineConfig(ConfigFile, ConfigPath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to write Config/DefaultEngine.ini"));
    }

    TSharedPtr<FJsonObject> DNA = MakeShared<FJsonObject>();
    DNA->SetStringField(TEXT("dna_asset"), DNAAsset);
    DNA->SetStringField(TEXT("dna_file"), DNAFile);
    DNA->SetStringField(TEXT("face_skeletal_mesh"), FaceSkeletalMesh);
    DNA->SetStringField(TEXT("rig_logic_asset"), RigLogicAsset);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("stage"), TEXT("metahuman_assign_dna"));
    Result->SetStringField(TEXT("config_path"), ConfigPath);
    Result->SetStringField(TEXT("manifest_section"), Section);
    Result->SetObjectField(TEXT("dna"), DNA);
    Result->SetArrayField(TEXT("warnings"), Warnings);
    return Result;
}
