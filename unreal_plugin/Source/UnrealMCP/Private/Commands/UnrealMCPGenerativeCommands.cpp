#include "Commands/UnrealMCPGenerativeCommands.h"

#include "Commands/UnrealMCPCommonUtils.h"
#include "Dom/JsonValue.h"
#include "Misc/Paths.h"

FUnrealMCPGenerativeCommands::FUnrealMCPGenerativeCommands()
{
}

TSharedPtr<FJsonObject> FUnrealMCPGenerativeCommands::HandleCommand(
    const FString& CommandType,
    const TSharedPtr<FJsonObject>& Params)
{
    if (CommandType == TEXT("gen_prepare_import_manifest")) return HandlePrepareImportManifest(Params);

    return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown Generative command: %s"), *CommandType));
}

FString FUnrealMCPGenerativeCommands::NormalizeContentPath(const FString& ContentPath) const
{
    FString Normalized = ContentPath;
    Normalized.TrimStartAndEndInline();
    Normalized.ReplaceInline(TEXT("\\"), TEXT("/"));
    while (Normalized.EndsWith(TEXT("/")) && Normalized.Len() > 5)
    {
        Normalized.LeftChopInline(1);
    }
    if (Normalized.IsEmpty())
    {
        Normalized = TEXT("/Game/Generated");
    }
    return Normalized;
}

FString FUnrealMCPGenerativeCommands::SanitizeAssetName(
    const FString& AssetName,
    const TArray<FString>& LocalFiles) const
{
    FString Sanitized = AssetName;
    Sanitized.TrimStartAndEndInline();

    if (Sanitized.IsEmpty() && LocalFiles.Num() > 0)
    {
        Sanitized = FPaths::GetBaseFilename(LocalFiles[0]);
    }
    if (Sanitized.IsEmpty())
    {
        Sanitized = TEXT("GeneratedAsset");
    }

    for (TCHAR& Ch : Sanitized)
    {
        if (!FChar::IsAlnum(Ch) && Ch != TCHAR('_'))
        {
            Ch = TCHAR('_');
        }
    }
    return Sanitized;
}

FString FUnrealMCPGenerativeCommands::InferImportKind(const FString& FilePath) const
{
    const FString Extension = FPaths::GetExtension(FilePath).ToLower();
    if (Extension == TEXT("fbx") || Extension == TEXT("obj") ||
        Extension == TEXT("gltf") || Extension == TEXT("glb") ||
        Extension == TEXT("usd") || Extension == TEXT("usdz"))
    {
        return TEXT("static_mesh");
    }
    if (Extension == TEXT("png") || Extension == TEXT("jpg") ||
        Extension == TEXT("jpeg") || Extension == TEXT("tga") ||
        Extension == TEXT("exr") || Extension == TEXT("hdr") ||
        Extension == TEXT("bmp"))
    {
        return TEXT("texture");
    }
    if (Extension == TEXT("wav") || Extension == TEXT("ogg") ||
        Extension == TEXT("flac"))
    {
        return TEXT("audio");
    }
    return TEXT("unknown");
}

TSharedPtr<FJsonObject> FUnrealMCPGenerativeCommands::MakeSourceFileEntry(const FString& FilePath) const
{
    TSharedPtr<FJsonObject> Entry = MakeShared<FJsonObject>();
    Entry->SetStringField(TEXT("file_path"), FilePath);
    Entry->SetStringField(TEXT("file_name"), FPaths::GetCleanFilename(FilePath));
    Entry->SetStringField(TEXT("extension"), FPaths::GetExtension(FilePath).ToLower());
    Entry->SetStringField(TEXT("import_kind"), InferImportKind(FilePath));
    Entry->SetBoolField(TEXT("exists_on_host"), FPaths::FileExists(FilePath));
    return Entry;
}

TSharedPtr<FJsonObject> FUnrealMCPGenerativeCommands::HandlePrepareImportManifest(
    const TSharedPtr<FJsonObject>& Params)
{
    if (!Params.IsValid())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing parameters"));
    }

    FString TaskId;
    Params->TryGetStringField(TEXT("task_id"), TaskId);
    TaskId.TrimStartAndEndInline();
    if (TaskId.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'task_id' parameter"));
    }

    FString Provider = TEXT("tripo");
    Params->TryGetStringField(TEXT("provider"), Provider);
    Provider.TrimStartAndEndInline();
    if (Provider.IsEmpty())
    {
        Provider = TEXT("tripo");
    }

    FString RequestedContentPath = TEXT("/Game/Generated");
    Params->TryGetStringField(TEXT("content_path"), RequestedContentPath);
    const FString ContentPath = NormalizeContentPath(RequestedContentPath);
    if (!ContentPath.StartsWith(TEXT("/Game/")))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("content_path must be under /Game, got '%s'"), *ContentPath));
    }

    TArray<FString> LocalFiles;
    const TArray<TSharedPtr<FJsonValue>>* LocalFileValues = nullptr;
    if (Params->TryGetArrayField(TEXT("local_files"), LocalFileValues) && LocalFileValues)
    {
        for (const TSharedPtr<FJsonValue>& Value : *LocalFileValues)
        {
            if (Value.IsValid() && !Value->AsString().IsEmpty())
            {
                LocalFiles.Add(Value->AsString());
            }
        }
    }
    if (LocalFiles.Num() == 0)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("local_files must contain at least one generated file path"));
    }

    FString RequestedAssetName;
    Params->TryGetStringField(TEXT("asset_name"), RequestedAssetName);
    const FString AssetName = SanitizeAssetName(RequestedAssetName, LocalFiles);

    bool bCreateMaterialInstance = true;
    bool bCreateBlueprint = false;
    bool bOverwriteExisting = false;
    Params->TryGetBoolField(TEXT("create_material_instance"), bCreateMaterialInstance);
    Params->TryGetBoolField(TEXT("create_blueprint"), bCreateBlueprint);
    Params->TryGetBoolField(TEXT("overwrite_existing"), bOverwriteExisting);

    TArray<TSharedPtr<FJsonValue>> SourceFiles;
    TArray<TSharedPtr<FJsonValue>> Warnings;
    bool bAllFilesPresent = true;
    for (const FString& FilePath : LocalFiles)
    {
        SourceFiles.Add(MakeShared<FJsonValueObject>(MakeSourceFileEntry(FilePath)));
        if (!FPaths::FileExists(FilePath))
        {
            bAllFilesPresent = false;
            Warnings.Add(MakeShared<FJsonValueString>(
                FString::Printf(TEXT("Source file does not exist on host yet: %s"), *FilePath)));
        }
    }

    TSharedPtr<FJsonObject> ExpectedAssets = MakeShared<FJsonObject>();
    ExpectedAssets->SetStringField(TEXT("primary_asset"), FString::Printf(TEXT("%s/%s"), *ContentPath, *AssetName));
    if (bCreateMaterialInstance)
    {
        ExpectedAssets->SetStringField(TEXT("material_instance"), FString::Printf(TEXT("%s/MI_%s"), *ContentPath, *AssetName));
    }
    if (bCreateBlueprint)
    {
        ExpectedAssets->SetStringField(TEXT("blueprint"), FString::Printf(TEXT("%s/BP_%s"), *ContentPath, *AssetName));
    }

    TSharedPtr<FJsonObject> Options = MakeShared<FJsonObject>();
    Options->SetBoolField(TEXT("create_material_instance"), bCreateMaterialInstance);
    Options->SetBoolField(TEXT("create_blueprint"), bCreateBlueprint);
    Options->SetBoolField(TEXT("overwrite_existing"), bOverwriteExisting);

    TSharedPtr<FJsonObject> Manifest = MakeShared<FJsonObject>();
    Manifest->SetStringField(TEXT("task_id"), TaskId);
    Manifest->SetStringField(TEXT("provider"), Provider);
    Manifest->SetStringField(TEXT("content_path"), ContentPath);
    Manifest->SetStringField(TEXT("asset_name"), AssetName);
    Manifest->SetArrayField(TEXT("source_files"), SourceFiles);
    Manifest->SetObjectField(TEXT("expected_assets"), ExpectedAssets);
    Manifest->SetObjectField(TEXT("options"), Options);
    Manifest->SetBoolField(TEXT("all_files_present"), bAllFilesPresent);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("stage"), TEXT("gen_prepare_import_manifest"));
    Result->SetObjectField(TEXT("manifest"), Manifest);
    Result->SetStringField(TEXT("content_path"), ContentPath);
    Result->SetStringField(TEXT("asset_name"), AssetName);
    Result->SetBoolField(TEXT("all_files_present"), bAllFilesPresent);
    Result->SetArrayField(TEXT("warnings"), Warnings);
    return Result;
}
