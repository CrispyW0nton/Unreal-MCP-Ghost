#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

class UChooserTable;
class UPoseSearchDatabase;
class UPoseSearchSchema;

/**
 * B.8 Motion Matching / Pose Search and Chooser command handler.
 */
class UNREALMCP_API FUnrealMCPMotionCommands
{
public:
    FUnrealMCPMotionCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleCreatePoseSearchSchema(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreatePoseSearchDatabase(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddPoseSearchSequence(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleInspectPoseSearchAsset(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateChooserTable(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddChooserAssetRow(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleInspectChooserTable(const TSharedPtr<FJsonObject>& Params);

    FString NormalizeAssetPath(const FString& InPath) const;
    FString MakeObjectPath(const FString& AssetPath) const;
    bool SplitPackagePath(const FString& AssetPath, FString& OutPackagePath, FString& OutAssetName) const;
    UObject* LoadAsset(const FString& AssetOrObjectPath) const;
    UClass* ResolveClass(const FString& ClassName, UClass* RequiredBaseClass) const;
    TArray<FString> GetStringArrayField(const TSharedPtr<FJsonObject>& Params, const FString& FieldName) const;
    TArray<TSharedPtr<FJsonValue>> MakeStringArray(const TArray<FString>& Values) const;
    TSharedPtr<FJsonObject> SummarizePoseSearchSchema(UPoseSearchSchema* Schema) const;
    TSharedPtr<FJsonObject> SummarizePoseSearchDatabase(UPoseSearchDatabase* Database) const;
    TSharedPtr<FJsonObject> SummarizeChooserTable(UChooserTable* Chooser) const;
};
