#include "Commands/UnrealMCPNetworkCommands.h"

#include "Commands/UnrealMCPBlueprintCommands.h"
#include "Commands/UnrealMCPCommonUtils.h"
#include "Commands/UnrealMCPExtendedCommands.h"
#include "Dom/JsonValue.h"

FUnrealMCPNetworkCommands::FUnrealMCPNetworkCommands()
    : ExtendedCommands(MakeShared<FUnrealMCPExtendedCommands>())
    , BlueprintCommands(MakeShared<FUnrealMCPBlueprintCommands>())
{
}

TSharedPtr<FJsonObject> FUnrealMCPNetworkCommands::HandleCommand(
    const FString& CommandType,
    const TSharedPtr<FJsonObject>& Params)
{
    if (CommandType == TEXT("net_set_property_replicated")) return HandleSetPropertyReplicated(Params);
    if (CommandType == TEXT("net_set_function_rpc")) return HandleSetFunctionRPC(Params);
    if (CommandType == TEXT("net_set_replication_condition")) return HandleSetReplicationCondition(Params);
    if (CommandType == TEXT("net_add_replicated_component")) return HandleAddReplicatedComponent(Params);
    if (CommandType == TEXT("net_set_role_override")) return HandleSetRoleOverride(Params);
    if (CommandType == TEXT("net_get_replication_graph_state")) return HandleGetReplicationGraphState(Params);

    return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown network command: %s"), *CommandType));
}

TSharedPtr<FJsonObject> FUnrealMCPNetworkCommands::CloneParams(const TSharedPtr<FJsonObject>& Params) const
{
    TSharedPtr<FJsonObject> Copy = MakeShared<FJsonObject>();
    if (Params.IsValid())
    {
        Copy->Values = Params->Values;
    }
    return Copy;
}

TSharedPtr<FJsonObject> FUnrealMCPNetworkCommands::Forward(
    const FString& CommandType,
    const TSharedPtr<FJsonObject>& Params) const
{
    return ExtendedCommands->HandleCommand(CommandType, Params);
}

TSharedPtr<FJsonObject> FUnrealMCPNetworkCommands::HandleSetPropertyReplicated(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> ForwardParams = CloneParams(Params);
    FString ReplicationMode;
    if (!ForwardParams->TryGetStringField(TEXT("replication_mode"), ReplicationMode))
    {
        bool bRepNotify = false;
        bool bReplicated = true;
        ForwardParams->TryGetBoolField(TEXT("repnotify"), bRepNotify);
        ForwardParams->TryGetBoolField(TEXT("replicated"), bReplicated);
        ForwardParams->SetStringField(
            TEXT("replication_mode"),
            bRepNotify ? TEXT("repnotify") : (bReplicated ? TEXT("replicated") : TEXT("none")));
    }
    return Forward(TEXT("net_configure_replicated_property"), ForwardParams);
}

TSharedPtr<FJsonObject> FUnrealMCPNetworkCommands::HandleSetFunctionRPC(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> ForwardParams = CloneParams(Params);
    FString FunctionName;
    if (ForwardParams->TryGetStringField(TEXT("function_name"), FunctionName) && !FunctionName.IsEmpty())
    {
        ForwardParams->SetStringField(TEXT("event_name"), FunctionName);
    }

    bool bCreateIfMissing = true;
    ForwardParams->TryGetBoolField(TEXT("create_if_missing"), bCreateIfMissing);
    return Forward(bCreateIfMissing ? TEXT("net_create_rpc_event") : TEXT("net_configure_rpc"), ForwardParams);
}

TSharedPtr<FJsonObject> FUnrealMCPNetworkCommands::HandleSetReplicationCondition(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> ForwardParams = CloneParams(Params);
    FString ReplicationMode;
    if (!ForwardParams->TryGetStringField(TEXT("replication_mode"), ReplicationMode) || ReplicationMode.IsEmpty())
    {
        ForwardParams->SetStringField(TEXT("replication_mode"), TEXT("replicated"));
    }
    return Forward(TEXT("net_configure_replicated_property"), ForwardParams);
}

bool FUnrealMCPNetworkCommands::ComponentExists(
    const TSharedPtr<FJsonObject>& DescribeResult,
    const FString& ComponentName) const
{
    if (!DescribeResult.IsValid())
    {
        return false;
    }
    const TArray<TSharedPtr<FJsonValue>>* Components = nullptr;
    if (!DescribeResult->TryGetArrayField(TEXT("components"), Components) || !Components)
    {
        return false;
    }
    for (const TSharedPtr<FJsonValue>& ComponentValue : *Components)
    {
        TSharedPtr<FJsonObject> ComponentObj = ComponentValue.IsValid() ? ComponentValue->AsObject() : nullptr;
        if (!ComponentObj.IsValid())
        {
            continue;
        }
        FString Name;
        if (ComponentObj->TryGetStringField(TEXT("name"), Name) &&
            Name.Equals(ComponentName, ESearchCase::IgnoreCase))
        {
            return true;
        }
    }
    return false;
}

TSharedPtr<FJsonObject> FUnrealMCPNetworkCommands::HandleAddReplicatedComponent(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName) || BPName.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    }

    FString ComponentName;
    if (!Params->TryGetStringField(TEXT("component_name"), ComponentName) || ComponentName.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'component_name'"));
    }

    FString ComponentType;
    Params->TryGetStringField(TEXT("component_type"), ComponentType);
    bool bCreateIfMissing = true;
    Params->TryGetBoolField(TEXT("create_if_missing"), bCreateIfMissing);

    TSharedPtr<FJsonObject> DescribeParams = MakeShared<FJsonObject>();
    DescribeParams->SetStringField(TEXT("blueprint_name"), BPName);
    TSharedPtr<FJsonObject> DescribeResult = Forward(TEXT("net_describe_blueprint_replication"), DescribeParams);
    if (DescribeResult.IsValid() && DescribeResult->HasField(TEXT("success")) && !DescribeResult->GetBoolField(TEXT("success")))
    {
        return DescribeResult;
    }

    bool bCreated = false;
    if (!ComponentExists(DescribeResult, ComponentName))
    {
        if (!bCreateIfMissing || ComponentType.IsEmpty())
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(
                FString::Printf(TEXT("Component '%s' not found and no component_type was supplied"), *ComponentName));
        }

        TSharedPtr<FJsonObject> AddParams = MakeShared<FJsonObject>();
        AddParams->SetStringField(TEXT("blueprint_name"), BPName);
        AddParams->SetStringField(TEXT("component_name"), ComponentName);
        AddParams->SetStringField(TEXT("component_type"), ComponentType);
        TSharedPtr<FJsonObject> AddResult = BlueprintCommands->HandleCommand(TEXT("add_component_to_blueprint"), AddParams);
        if (!AddResult.IsValid())
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("add_component_to_blueprint returned no result"));
        }
        if (AddResult->HasField(TEXT("success")) && !AddResult->GetBoolField(TEXT("success")))
        {
            return AddResult;
        }
        if (AddResult->HasField(TEXT("error")))
        {
            return AddResult;
        }
        bCreated = true;
    }

    TSharedPtr<FJsonObject> SetParams = CloneParams(Params);
    TSharedPtr<FJsonObject> SetResult = Forward(TEXT("net_set_component_replicates"), SetParams);
    if (SetResult.IsValid())
    {
        SetResult->SetBoolField(TEXT("component_created"), bCreated);
    }
    return SetResult;
}

TSharedPtr<FJsonObject> FUnrealMCPNetworkCommands::HandleSetRoleOverride(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> Result = Forward(TEXT("net_add_role_switch"), CloneParams(Params));
    if (Result.IsValid())
    {
        Result->SetStringField(TEXT("role_override_route"), TEXT("net_add_role_switch"));
    }
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPNetworkCommands::HandleGetReplicationGraphState(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> Result = Forward(TEXT("network_debug_replication"), CloneParams(Params));
    if (Result.IsValid())
    {
        Result->SetStringField(TEXT("state_route"), TEXT("network_debug_replication"));
    }
    return Result;
}
