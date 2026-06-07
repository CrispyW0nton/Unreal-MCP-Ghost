#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

/**
 * D.1 Generative content import-side helper commands.
 */
class UNREALMCP_API FUnrealMCPGenerativeCommands
{
public:
    FUnrealMCPGenerativeCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandlePrepareImportManifest(const TSharedPtr<FJsonObject>& Params);

    FString NormalizeContentPath(const FString& ContentPath) const;
    FString SanitizeAssetName(const FString& AssetName, const TArray<FString>& LocalFiles) const;
    FString InferImportKind(const FString& FilePath) const;
    TSharedPtr<FJsonObject> MakeSourceFileEntry(const FString& FilePath) const;
};
