#include "Commands/UnrealMCPAudioCommands.h"

#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetToolsModule.h"
#include "Commands/UnrealMCPCommonUtils.h"
#include "EditorAssetLibrary.h"
#include "Engine/Attenuation.h"
#include "Factories/SoundAttenuationFactory.h"
#include "Factories/SoundConcurrencyFactory.h"
#include "Factories/SoundCueFactoryNew.h"
#include "Metasound.h"
#include "MetasoundBuilderBase.h"
#include "MetasoundBuilderSubsystem.h"
#include "MetasoundDocumentInterface.h"
#include "MetasoundFactory.h"
#include "MetasoundFrontendDocument.h"
#include "MetasoundSource.h"
#include "Misc/ScopedSlowTask.h"
#include "ScopedTransaction.h"
#include "Sound/SoundAttenuation.h"
#include "Sound/SoundConcurrency.h"
#include "Sound/SoundCue.h"
#include "Sound/SoundWave.h"
#include "UObject/Package.h"

FUnrealMCPAudioCommands::FUnrealMCPAudioCommands()
{
}

TSharedPtr<FJsonObject> FUnrealMCPAudioCommands::HandleCommand(
    const FString& CommandType,
    const TSharedPtr<FJsonObject>& Params)
{
    if (CommandType == TEXT("metasound_create_source")) return HandleCreateMetaSoundSource(Params);
    if (CommandType == TEXT("metasound_create_patch")) return HandleCreateMetaSoundPatch(Params);
    if (CommandType == TEXT("metasound_add_node")) return HandleMetaSoundAddNode(Params);
    if (CommandType == TEXT("metasound_connect_pins")) return HandleMetaSoundConnectPins(Params);
    if (CommandType == TEXT("metasound_compile")) return HandleMetaSoundCompile(Params);
    if (CommandType == TEXT("audio_create_soundcue")) return HandleCreateSoundCue(Params);
    if (CommandType == TEXT("audio_create_attenuation")) return HandleCreateAttenuation(Params);
    if (CommandType == TEXT("audio_create_concurrency")) return HandleCreateConcurrency(Params);

    return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown audio command: %s"), *CommandType));
}

FString FUnrealMCPAudioCommands::MakeObjectPath(const FString& AssetPathOrObjectPath) const
{
    if (AssetPathOrObjectPath.Contains(TEXT(".")))
    {
        return AssetPathOrObjectPath;
    }

    FString AssetName;
    int32 SlashIndex = INDEX_NONE;
    if (AssetPathOrObjectPath.FindLastChar(TEXT('/'), SlashIndex))
    {
        AssetName = AssetPathOrObjectPath.Mid(SlashIndex + 1);
    }
    else
    {
        AssetName = AssetPathOrObjectPath;
    }
    return FString::Printf(TEXT("%s.%s"), *AssetPathOrObjectPath, *AssetName);
}

UObject* FUnrealMCPAudioCommands::LoadAssetObject(const FString& AssetPathOrObjectPath) const
{
    if (AssetPathOrObjectPath.IsEmpty())
    {
        return nullptr;
    }

    if (UObject* Loaded = UEditorAssetLibrary::LoadAsset(MakeObjectPath(AssetPathOrObjectPath)))
    {
        return Loaded;
    }
    return UEditorAssetLibrary::LoadAsset(AssetPathOrObjectPath);
}

void FUnrealMCPAudioCommands::SetCommonAssetFields(
    TSharedPtr<FJsonObject> Result,
    UObject* Asset,
    const FString& AssetPath,
    const FString& ObjectPath) const
{
    if (!Result.IsValid())
    {
        return;
    }
    Result->SetBoolField(TEXT("success"), Asset != nullptr);
    Result->SetStringField(TEXT("asset_path"), AssetPath);
    Result->SetStringField(TEXT("object_path"), ObjectPath);
    if (Asset)
    {
        Result->SetStringField(TEXT("asset_class"), Asset->GetClass()->GetPathName());
        Result->SetStringField(TEXT("asset_name"), Asset->GetName());
    }
}

TSharedPtr<FJsonObject> FUnrealMCPAudioCommands::CreateAsset(
    const TSharedPtr<FJsonObject>& Params,
    const FString& DefaultName,
    const FString& DefaultPath,
    UClass* AssetClass,
    UFactory* Factory,
    const FString& StageName) const
{
    if (!AssetClass || !Factory)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("%s: missing asset class or factory"), *StageName));
    }

    FString Name = DefaultName;
    Params->TryGetStringField(TEXT("name"), Name);
    FString Path = DefaultPath;
    Params->TryGetStringField(TEXT("path"), Path);
    Params->TryGetStringField(TEXT("folder_path"), Path);

    if (Name.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }
    if (Path.IsEmpty())
    {
        Path = DefaultPath;
    }
    Path.RemoveFromEnd(TEXT("/"));
    if (!Path.StartsWith(TEXT("/Game")))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Audio asset path must be under /Game"));
    }

    bool bOverwrite = false;
    Params->TryGetBoolField(TEXT("overwrite"), bOverwrite);
    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);

    const FString AssetPath = FString::Printf(TEXT("%s/%s"), *Path, *Name);
    const FString ObjectPath = MakeObjectPath(AssetPath);
    if (UEditorAssetLibrary::DoesAssetExist(ObjectPath))
    {
        if (!bOverwrite)
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(
                FString::Printf(TEXT("Asset already exists: %s"), *ObjectPath));
        }
        UEditorAssetLibrary::DeleteAsset(ObjectPath);
    }

    FScopedSlowTask SlowTask(2.0f, FText::FromString(StageName));
    SlowTask.MakeDialog(false);
    SlowTask.EnterProgressFrame(1.0f, FText::FromString(TEXT("Creating audio asset")));
    const FScopedTransaction Transaction(FText::FromString(StageName));

    UEditorAssetLibrary::MakeDirectory(Path);
    FAssetToolsModule& AssetToolsModule = FModuleManager::LoadModuleChecked<FAssetToolsModule>(TEXT("AssetTools"));
    UObject* NewAsset = AssetToolsModule.Get().CreateAsset(Name, Path, AssetClass, Factory);
    if (!NewAsset)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Failed to create asset: %s"), *ObjectPath));
    }

    SlowTask.EnterProgressFrame(1.0f, FText::FromString(TEXT("Registering asset")));
    NewAsset->MarkPackageDirty();
    FAssetRegistryModule::AssetCreated(NewAsset);
    if (bSave)
    {
        UEditorAssetLibrary::SaveAsset(ObjectPath, false);
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetStringField(TEXT("stage"), StageName);
    SetCommonAssetFields(Result, NewAsset, AssetPath, ObjectPath);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPAudioCommands::HandleCreateMetaSoundSource(const TSharedPtr<FJsonObject>& Params)
{
    UMetaSoundSourceFactory* Factory = NewObject<UMetaSoundSourceFactory>();
    TSharedPtr<FJsonObject> Result = CreateAsset(
        Params,
        TEXT("MS_NewSource"),
        TEXT("/Game/Audio/MetaSounds"),
        UMetaSoundSource::StaticClass(),
        Factory,
        TEXT("metasound_create_source"));

    if (Result.IsValid() && Result->GetBoolField(TEXT("success")))
    {
        bool bOneShot = true;
        Params->TryGetBoolField(TEXT("one_shot"), bOneShot);
        Result->SetBoolField(TEXT("one_shot"), bOneShot);
        Result->SetStringField(TEXT("note"), TEXT("Created MetaSound Source asset; use metasound_add_node/connect_pins for graph authoring."));
    }
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPAudioCommands::HandleCreateMetaSoundPatch(const TSharedPtr<FJsonObject>& Params)
{
    UMetaSoundFactory* Factory = NewObject<UMetaSoundFactory>();
    return CreateAsset(
        Params,
        TEXT("MSP_NewPatch"),
        TEXT("/Game/Audio/MetaSounds/Patches"),
        UMetaSoundPatch::StaticClass(),
        Factory,
        TEXT("metasound_create_patch"));
}

UMetaSoundBuilderBase* FUnrealMCPAudioCommands::AttachBuilder(UObject* MetaSoundObject, FString& OutError) const
{
    OutError.Empty();
    if (!MetaSoundObject)
    {
        OutError = TEXT("MetaSound asset not found");
        return nullptr;
    }
    if (!MetaSoundObject->GetClass()->IsChildOf(UMetaSoundSource::StaticClass()) &&
        !MetaSoundObject->GetClass()->IsChildOf(UMetaSoundPatch::StaticClass()))
    {
        OutError = FString::Printf(TEXT("Asset is not a MetaSound Source/Patch: %s"), *MetaSoundObject->GetClass()->GetName());
        return nullptr;
    }

PRAGMA_DISABLE_DEPRECATION_WARNINGS
    UMetaSoundBuilderBase& Builder = UMetaSoundBuilderSubsystem::GetChecked().AttachBuilderToAssetChecked(*MetaSoundObject);
PRAGMA_ENABLE_DEPRECATION_WARNINGS
    return &Builder;
}

bool FUnrealMCPAudioCommands::ParseGuidField(
    const TSharedPtr<FJsonObject>& Params,
    const TCHAR* FieldName,
    FGuid& OutGuid,
    FString& OutError) const
{
    FString Value;
    if (!Params->TryGetStringField(FieldName, Value) || Value.IsEmpty())
    {
        OutError = FString::Printf(TEXT("Missing '%s' parameter"), FieldName);
        return false;
    }
    if (!FGuid::Parse(Value, OutGuid))
    {
        OutError = FString::Printf(TEXT("Invalid GUID for '%s': %s"), FieldName, *Value);
        return false;
    }
    return true;
}

TSharedPtr<FJsonObject> FUnrealMCPAudioCommands::HandleMetaSoundAddNode(const TSharedPtr<FJsonObject>& Params)
{
    FString MetaSoundPath;
    if (!Params->TryGetStringField(TEXT("metasound"), MetaSoundPath))
    {
        Params->TryGetStringField(TEXT("asset_path"), MetaSoundPath);
    }
    UObject* MetaSoundAsset = LoadAssetObject(MetaSoundPath);
    FString Error;
    UMetaSoundBuilderBase* Builder = AttachBuilder(MetaSoundAsset, Error);
    if (!Builder)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(Error);
    }

    FString Namespace;
    Params->TryGetStringField(TEXT("class_namespace"), Namespace);
    FString Name;
    Params->TryGetStringField(TEXT("class_name"), Name);
    FString Variant;
    Params->TryGetStringField(TEXT("class_variant"), Variant);
    if (Name.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'class_name' parameter"));
    }

    int32 MajorVersion = 1;
    Params->TryGetNumberField(TEXT("major_version"), MajorVersion);
    FMetasoundFrontendClassName ClassName{
        FName(*Namespace),
        FName(*Name),
        FName(*Variant)};

    EMetaSoundBuilderResult BuildResult = EMetaSoundBuilderResult::Failed;
    FMetaSoundNodeHandle NodeHandle = Builder->AddNodeByClassName(ClassName, BuildResult, MajorVersion);
    if (BuildResult != EMetaSoundBuilderResult::Succeeded || !NodeHandle.IsSet())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Failed to add MetaSound node '%s:%s:%s'"), *Namespace, *Name, *Variant));
    }

    const TArray<TSharedPtr<FJsonValue>>* Position = nullptr;
    if (Params->TryGetArrayField(TEXT("node_position"), Position) && Position && Position->Num() >= 2)
    {
        EMetaSoundBuilderResult PositionResult = EMetaSoundBuilderResult::Failed;
        Builder->SetNodeLocation(
            NodeHandle,
            FVector2D((*Position)[0]->AsNumber(), (*Position)[1]->AsNumber()),
            PositionResult);
    }

    MetaSoundAsset->MarkPackageDirty();
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("stage"), TEXT("metasound_add_node"));
    Result->SetStringField(TEXT("metasound"), MetaSoundPath);
    Result->SetStringField(TEXT("node_id"), NodeHandle.NodeID.ToString(EGuidFormats::DigitsWithHyphens));
    Result->SetStringField(TEXT("class_namespace"), Namespace);
    Result->SetStringField(TEXT("class_name"), Name);
    Result->SetStringField(TEXT("class_variant"), Variant);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPAudioCommands::HandleMetaSoundConnectPins(const TSharedPtr<FJsonObject>& Params)
{
    FString MetaSoundPath;
    if (!Params->TryGetStringField(TEXT("metasound"), MetaSoundPath))
    {
        Params->TryGetStringField(TEXT("asset_path"), MetaSoundPath);
    }
    UObject* MetaSoundAsset = LoadAssetObject(MetaSoundPath);
    FString Error;
    UMetaSoundBuilderBase* Builder = AttachBuilder(MetaSoundAsset, Error);
    if (!Builder)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(Error);
    }

    FGuid FromNode;
    FGuid FromVertex;
    FGuid ToNode;
    FGuid ToVertex;
    if (!ParseGuidField(Params, TEXT("from_node_id"), FromNode, Error) ||
        !ParseGuidField(Params, TEXT("from_output_id"), FromVertex, Error) ||
        !ParseGuidField(Params, TEXT("to_node_id"), ToNode, Error) ||
        !ParseGuidField(Params, TEXT("to_input_id"), ToVertex, Error))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(Error);
    }

    FMetaSoundBuilderNodeOutputHandle OutputHandle(FromNode, FromVertex);
    FMetaSoundBuilderNodeInputHandle InputHandle(ToNode, ToVertex);
    EMetaSoundBuilderResult ConnectResult = EMetaSoundBuilderResult::Failed;
    Builder->ConnectNodes(OutputHandle, InputHandle, ConnectResult);
    if (ConnectResult != EMetaSoundBuilderResult::Succeeded)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to connect MetaSound pins"));
    }

    MetaSoundAsset->MarkPackageDirty();
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("stage"), TEXT("metasound_connect_pins"));
    Result->SetStringField(TEXT("metasound"), MetaSoundPath);
    Result->SetStringField(TEXT("from_node_id"), FromNode.ToString(EGuidFormats::DigitsWithHyphens));
    Result->SetStringField(TEXT("from_output_id"), FromVertex.ToString(EGuidFormats::DigitsWithHyphens));
    Result->SetStringField(TEXT("to_node_id"), ToNode.ToString(EGuidFormats::DigitsWithHyphens));
    Result->SetStringField(TEXT("to_input_id"), ToVertex.ToString(EGuidFormats::DigitsWithHyphens));
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPAudioCommands::HandleMetaSoundCompile(const TSharedPtr<FJsonObject>& Params)
{
    FString MetaSoundPath;
    if (!Params->TryGetStringField(TEXT("metasound"), MetaSoundPath))
    {
        Params->TryGetStringField(TEXT("asset_path"), MetaSoundPath);
    }
    UObject* MetaSoundAsset = LoadAssetObject(MetaSoundPath);
    FString Error;
    UMetaSoundBuilderBase* Builder = AttachBuilder(MetaSoundAsset, Error);
    if (!Builder)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(Error);
    }

    EMetaSoundBuilderResult InjectResult = EMetaSoundBuilderResult::Failed;
    Builder->InitNodeLocations();
    Builder->InjectInputTemplateNodes(false, InjectResult);
    Builder->RemoveUnusedDependencies();
    TScriptInterface<IMetaSoundDocumentInterface> MetaSoundDocument;
    MetaSoundDocument.SetObject(MetaSoundAsset);
    MetaSoundDocument.SetInterface(Cast<IMetaSoundDocumentInterface>(MetaSoundAsset));
    Builder->BuildAndOverwriteMetaSound(MetaSoundDocument, false);
    Builder->ConformObjectToDocument();

    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);
    MetaSoundAsset->MarkPackageDirty();
    const FString ObjectPath = MakeObjectPath(MetaSoundPath);
    if (bSave)
    {
        UEditorAssetLibrary::SaveAsset(ObjectPath, false);
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("stage"), TEXT("metasound_compile"));
    Result->SetStringField(TEXT("metasound"), MetaSoundPath);
    Result->SetBoolField(TEXT("saved"), bSave);
    Result->SetStringField(TEXT("object_path"), ObjectPath);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPAudioCommands::HandleCreateSoundCue(const TSharedPtr<FJsonObject>& Params)
{
    USoundCueFactoryNew* Factory = NewObject<USoundCueFactoryNew>();
    FString SoundWavePath;
    Params->TryGetStringField(TEXT("sound_wave"), SoundWavePath);
    if (!SoundWavePath.IsEmpty())
    {
        if (USoundWave* SoundWave = Cast<USoundWave>(LoadAssetObject(SoundWavePath)))
        {
            Factory->InitialSoundWaves.Add(TWeakObjectPtr<USoundWave>(SoundWave));
        }
    }
    return CreateAsset(
        Params,
        TEXT("SC_NewCue"),
        TEXT("/Game/Audio/Cues"),
        USoundCue::StaticClass(),
        Factory,
        TEXT("audio_create_soundcue"));
}

TSharedPtr<FJsonObject> FUnrealMCPAudioCommands::HandleCreateAttenuation(const TSharedPtr<FJsonObject>& Params)
{
    USoundAttenuationFactory* Factory = NewObject<USoundAttenuationFactory>();
    TSharedPtr<FJsonObject> Result = CreateAsset(
        Params,
        TEXT("SA_NewAttenuation"),
        TEXT("/Game/Audio/Attenuation"),
        USoundAttenuation::StaticClass(),
        Factory,
        TEXT("audio_create_attenuation"));

    if (!Result.IsValid() || !Result->GetBoolField(TEXT("success")))
    {
        return Result;
    }

    USoundAttenuation* Attenuation = Cast<USoundAttenuation>(LoadAssetObject(Result->GetStringField(TEXT("object_path"))));
    if (!Attenuation)
    {
        return Result;
    }

    bool bSpatialize = true;
    Params->TryGetBoolField(TEXT("spatialize"), bSpatialize);
    bool bAttenuate = true;
    Params->TryGetBoolField(TEXT("attenuate"), bAttenuate);
    double Radius = 400.0;
    Params->TryGetNumberField(TEXT("radius"), Radius);
    double Falloff = 3600.0;
    Params->TryGetNumberField(TEXT("falloff_distance"), Falloff);

    Attenuation->Attenuation.bSpatialize = bSpatialize;
    Attenuation->Attenuation.bAttenuate = bAttenuate;
    Attenuation->Attenuation.AttenuationShape = EAttenuationShape::Sphere;
    Attenuation->Attenuation.AttenuationShapeExtents = FVector(Radius, 0.0, 0.0);
    Attenuation->Attenuation.FalloffDistance = static_cast<float>(Falloff);
    Attenuation->MarkPackageDirty();
    UEditorAssetLibrary::SaveAsset(Result->GetStringField(TEXT("object_path")), false);

    Result->SetBoolField(TEXT("spatialize"), bSpatialize);
    Result->SetBoolField(TEXT("attenuate"), bAttenuate);
    Result->SetNumberField(TEXT("radius"), Radius);
    Result->SetNumberField(TEXT("falloff_distance"), Falloff);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPAudioCommands::HandleCreateConcurrency(const TSharedPtr<FJsonObject>& Params)
{
    USoundConcurrencyFactory* Factory = NewObject<USoundConcurrencyFactory>();
    TSharedPtr<FJsonObject> Result = CreateAsset(
        Params,
        TEXT("SCN_NewConcurrency"),
        TEXT("/Game/Audio/Concurrency"),
        USoundConcurrency::StaticClass(),
        Factory,
        TEXT("audio_create_concurrency"));

    if (!Result.IsValid() || !Result->GetBoolField(TEXT("success")))
    {
        return Result;
    }

    USoundConcurrency* Concurrency = Cast<USoundConcurrency>(LoadAssetObject(Result->GetStringField(TEXT("object_path"))));
    if (!Concurrency)
    {
        return Result;
    }

    int32 MaxCount = 8;
    Params->TryGetNumberField(TEXT("max_count"), MaxCount);
    bool bLimitToOwner = false;
    Params->TryGetBoolField(TEXT("limit_to_owner"), bLimitToOwner);
    double RetriggerTime = 0.0;
    Params->TryGetNumberField(TEXT("retrigger_time"), RetriggerTime);

    FString ResolutionRule;
    Params->TryGetStringField(TEXT("resolution_rule"), ResolutionRule);
    EMaxConcurrentResolutionRule::Type Rule = EMaxConcurrentResolutionRule::StopFarthestThenOldest;
    if (ResolutionRule.Equals(TEXT("prevent_new"), ESearchCase::IgnoreCase))
    {
        Rule = EMaxConcurrentResolutionRule::PreventNew;
    }
    else if (ResolutionRule.Equals(TEXT("stop_oldest"), ESearchCase::IgnoreCase))
    {
        Rule = EMaxConcurrentResolutionRule::StopOldest;
    }
    else if (ResolutionRule.Equals(TEXT("stop_quietest"), ESearchCase::IgnoreCase))
    {
        Rule = EMaxConcurrentResolutionRule::StopQuietest;
    }
    else if (ResolutionRule.Equals(TEXT("stop_lowest_priority"), ESearchCase::IgnoreCase))
    {
        Rule = EMaxConcurrentResolutionRule::StopLowestPriority;
    }

    Concurrency->Concurrency.MaxCount = MaxCount;
    Concurrency->Concurrency.bLimitToOwner = bLimitToOwner;
    Concurrency->Concurrency.RetriggerTime = static_cast<float>(RetriggerTime);
    Concurrency->Concurrency.ResolutionRule = Rule;
    Concurrency->MarkPackageDirty();
    UEditorAssetLibrary::SaveAsset(Result->GetStringField(TEXT("object_path")), false);

    Result->SetNumberField(TEXT("max_count"), MaxCount);
    Result->SetBoolField(TEXT("limit_to_owner"), bLimitToOwner);
    Result->SetNumberField(TEXT("retrigger_time"), RetriggerTime);
    Result->SetStringField(TEXT("resolution_rule"), ResolutionRule.IsEmpty() ? TEXT("stop_farthest_then_oldest") : ResolutionRule);
    return Result;
}
