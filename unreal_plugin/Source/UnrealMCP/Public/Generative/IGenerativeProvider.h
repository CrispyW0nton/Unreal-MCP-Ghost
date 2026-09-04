#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

/**
 * D.5 provider interface for generated-content integrations.
 *
 * Python owns the current Tripo transport, while Unreal import-side helpers use
 * this contract as the C++ shape for future provider-specific import metadata.
 */
class UNREALMCP_API IGenerativeProvider
{
public:
    virtual ~IGenerativeProvider() = default;

    virtual FString GetProviderName() const = 0;
    virtual FString GetDisplayName() const = 0;
    virtual FString GetBaseUrl() const = 0;
    virtual TArray<FString> GetCapabilities() const = 0;
    virtual TArray<FString> GetModelOutputKeys() const = 0;
    virtual TArray<FString> GetImportOutputKeys() const = 0;
    virtual TArray<FString> GetSupportedModelExtensions() const = 0;
    virtual TArray<FString> GetFinalStatuses() const = 0;

    virtual TSharedPtr<FJsonObject> DescribeProvider() const = 0;
};
