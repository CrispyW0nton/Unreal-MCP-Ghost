#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

class FUnrealMCPBlueprintCommands;
class FUnrealMCPExtendedCommands;

/**
 * B.4 networking command adapter.
 *
 * Keeps the public B.4 route names stable while delegating to the older
 * live-tested replication/RPC implementations where possible.
 */
class UNREALMCP_API FUnrealMCPNetworkCommands
{
public:
    FUnrealMCPNetworkCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FUnrealMCPExtendedCommands> ExtendedCommands;
    TSharedPtr<FUnrealMCPBlueprintCommands> BlueprintCommands;

    TSharedPtr<FJsonObject> HandleSetPropertyReplicated(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetFunctionRPC(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetReplicationCondition(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddReplicatedComponent(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetRoleOverride(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleGetReplicationGraphState(const TSharedPtr<FJsonObject>& Params);

    TSharedPtr<FJsonObject> Forward(const FString& CommandType, const TSharedPtr<FJsonObject>& Params) const;
    TSharedPtr<FJsonObject> CloneParams(const TSharedPtr<FJsonObject>& Params) const;
    bool ComponentExists(const TSharedPtr<FJsonObject>& DescribeResult, const FString& ComponentName) const;
};
