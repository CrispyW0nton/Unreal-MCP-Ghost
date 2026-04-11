#include "UnrealMCPBridge.h"
#include "MCPServerRunnable.h"
#include "Sockets.h"
#include "SocketSubsystem.h"
#include "HAL/RunnableThread.h"
#include "Interfaces/IPv4/IPv4Address.h"
#include "Interfaces/IPv4/IPv4Endpoint.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonWriter.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/DirectionalLight.h"
#include "Engine/PointLight.h"
#include "Engine/SpotLight.h"
#include "Camera/CameraActor.h"
#include "EditorAssetLibrary.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "JsonObjectConverter.h"
#include "GameFramework/Actor.h"
#include "Engine/Selection.h"
#include "Kismet/GameplayStatics.h"
#include "Async/Async.h"
// Add Blueprint related includes
#include "Engine/Blueprint.h"
#include "Engine/BlueprintGeneratedClass.h"
#include "Factories/BlueprintFactory.h"
#include "EdGraphSchema_K2.h"
#include "K2Node_Event.h"
#include "K2Node_VariableGet.h"
#include "K2Node_VariableSet.h"
#include "Components/StaticMeshComponent.h"
#include "Components/BoxComponent.h"
#include "Components/SphereComponent.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
// UE5.5 correct includes
#include "Engine/SimpleConstructionScript.h"
#include "Engine/SCS_Node.h"
#include "UObject/Field.h"
#include "UObject/FieldPath.h"
// Blueprint Graph specific includes
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "K2Node_CallFunction.h"
#include "K2Node_InputAction.h"
#include "K2Node_Self.h"
#include "GameFramework/InputSettings.h"
#include "EditorSubsystem.h"
#include "Subsystems/EditorActorSubsystem.h"
// Include our new command handler classes
#include "Commands/UnrealMCPEditorCommands.h"
#include "Commands/UnrealMCPBlueprintCommands.h"
#include "Commands/UnrealMCPBlueprintNodeCommands.h"
#include "Commands/UnrealMCPProjectCommands.h"
#include "Commands/UnrealMCPCommonUtils.h"
#include "Commands/UnrealMCPUMGCommands.h"
#include "Commands/UnrealMCPExtendedCommands.h"
#include "HAL/PlatformTime.h"
#include "UnrealMCPModule.h"

// Default settings
#define MCP_SERVER_HOST "127.0.0.1"
#define MCP_SERVER_PORT 55557

UUnrealMCPBridge::UUnrealMCPBridge()
{
    EditorCommands = MakeShared<FUnrealMCPEditorCommands>();
    BlueprintCommands = MakeShared<FUnrealMCPBlueprintCommands>();
    BlueprintNodeCommands = MakeShared<FUnrealMCPBlueprintNodeCommands>();
    ProjectCommands = MakeShared<FUnrealMCPProjectCommands>();
    UMGCommands = MakeShared<FUnrealMCPUMGCommands>();
    ExtendedCommands = MakeShared<FUnrealMCPExtendedCommands>();
}

UUnrealMCPBridge::~UUnrealMCPBridge()
{
    EditorCommands.Reset();
    BlueprintCommands.Reset();
    BlueprintNodeCommands.Reset();
    ProjectCommands.Reset();
    UMGCommands.Reset();
    ExtendedCommands.Reset();
}

// Initialize subsystem
void UUnrealMCPBridge::Initialize(FSubsystemCollectionBase& Collection)
{
    UE_LOG(LogTemp, Display, TEXT("UnrealMCPBridge: Initializing"));
    
    bIsRunning = false;
    ListenerSocket = nullptr;
    ConnectionSocket = nullptr;
    ServerThread = nullptr;
    Port = MCP_SERVER_PORT;
    FIPv4Address::Parse(MCP_SERVER_HOST, ServerAddress);

    // Start the server automatically
    StartServer();
}

// Clean up resources when subsystem is destroyed
void UUnrealMCPBridge::Deinitialize()
{
    UE_LOG(LogTemp, Display, TEXT("UnrealMCPBridge: Shutting down"));
    StopServer();
}

// Start the MCP server
void UUnrealMCPBridge::StartServer()
{
    if (bIsRunning)
    {
        UE_LOG(LogTemp, Warning, TEXT("UnrealMCPBridge: Server is already running"));
        return;
    }

    // Create socket subsystem
    ISocketSubsystem* SocketSubsystem = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);
    if (!SocketSubsystem)
    {
        UE_LOG(LogTemp, Error, TEXT("UnrealMCPBridge: Failed to get socket subsystem"));
        return;
    }

    // Create listener socket
    TSharedPtr<FSocket> NewListenerSocket = MakeShareable(SocketSubsystem->CreateSocket(NAME_Stream, TEXT("UnrealMCPListener"), false));
    if (!NewListenerSocket.IsValid())
    {
        UE_LOG(LogTemp, Error, TEXT("UnrealMCPBridge: Failed to create listener socket"));
        return;
    }

    // Allow address reuse for quick restarts
    NewListenerSocket->SetReuseAddr(true);
    NewListenerSocket->SetNonBlocking(true);

    // Bind to address
    FIPv4Endpoint Endpoint(ServerAddress, Port);
    if (!NewListenerSocket->Bind(*Endpoint.ToInternetAddr()))
    {
        UE_LOG(LogTemp, Error, TEXT("UnrealMCPBridge: Failed to bind listener socket to %s:%d"), *ServerAddress.ToString(), Port);
        return;
    }

    // Start listening
    if (!NewListenerSocket->Listen(5))
    {
        UE_LOG(LogTemp, Error, TEXT("UnrealMCPBridge: Failed to start listening"));
        return;
    }

    ListenerSocket = NewListenerSocket;
    bIsRunning = true;
    UE_LOG(LogTemp, Display, TEXT("UnrealMCPBridge: Server started on %s:%d"), *ServerAddress.ToString(), Port);

    // Start server thread
    ServerThread = FRunnableThread::Create(
        new FMCPServerRunnable(this, ListenerSocket),
        TEXT("UnrealMCPServerThread"),
        0, TPri_Normal
    );

    if (!ServerThread)
    {
        UE_LOG(LogTemp, Error, TEXT("UnrealMCPBridge: Failed to create server thread"));
        StopServer();
        return;
    }
}

// Stop the MCP server
void UUnrealMCPBridge::StopServer()
{
    if (!bIsRunning)
    {
        return;
    }

    bIsRunning = false;

    // Clean up thread
    if (ServerThread)
    {
        ServerThread->Kill(true);
        delete ServerThread;
        ServerThread = nullptr;
    }

    // Close sockets
    if (ConnectionSocket.IsValid())
    {
        ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(ConnectionSocket.Get());
        ConnectionSocket.Reset();
    }

    if (ListenerSocket.IsValid())
    {
        ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(ListenerSocket.Get());
        ListenerSocket.Reset();
    }

    UE_LOG(LogTemp, Display, TEXT("UnrealMCPBridge: Server stopped"));
}

// Execute a command received from a client
FString UUnrealMCPBridge::ExecuteCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    UE_LOG(LogTemp, Display, TEXT("UnrealMCPBridge: Executing command: %s"), *CommandType);
    
    // Create a promise to wait for the result
    TPromise<FString> Promise;
    TFuture<FString> Future = Promise.GetFuture();
    
    // Queue execution on Game Thread
    AsyncTask(ENamedThreads::GameThread, [this, CommandType, Params, Promise = MoveTemp(Promise)]() mutable
    {
        TSharedPtr<FJsonObject> ResponseJson = MakeShareable(new FJsonObject);

        // ---------------------------------------------------------------
        // Pre-command diagnostic logging so we can trace every MCP action
        // even if Unreal crashes before the command completes.
        // These lines appear in Saved/Logs/UnrealEditor.log.
        // ---------------------------------------------------------------
        UE_LOG(LogMCP, Display, TEXT("[MCP] >>> BEGIN command: '%s'"), *CommandType);

        // Serialize params for debugging (keep it short – first 512 chars)
        {
            FString ParamsStr;
            TSharedRef<TJsonWriter<>> PWriter = TJsonWriterFactory<>::Create(&ParamsStr);
            FJsonSerializer::Serialize(Params.ToSharedRef(), PWriter);
            if (ParamsStr.Len() > 512)
            {
                ParamsStr = ParamsStr.Left(509) + TEXT("...");
            }
            UE_LOG(LogMCP, Display, TEXT("[MCP]   Params: %s"), *ParamsStr);
        }

        const double CommandStartTime = FPlatformTime::Seconds();
        
        try
        {
            TSharedPtr<FJsonObject> ResultJson;
            
            if (CommandType == TEXT("ping"))
            {
                ResultJson = MakeShareable(new FJsonObject);
                ResultJson->SetStringField(TEXT("message"), TEXT("pong"));
            }
            // Editor Commands (including actor manipulation)
            else if (CommandType == TEXT("get_actors_in_level") || 
                     CommandType == TEXT("find_actors_by_name") ||
                     CommandType == TEXT("spawn_actor") ||
                     CommandType == TEXT("create_actor") ||
                     CommandType == TEXT("delete_actor") || 
                     CommandType == TEXT("set_actor_transform") ||
                     CommandType == TEXT("get_actor_properties") ||
                     CommandType == TEXT("set_actor_property") ||
                     CommandType == TEXT("spawn_blueprint_actor") ||
                     CommandType == TEXT("focus_viewport") || 
                     CommandType == TEXT("take_screenshot") ||
                     CommandType == TEXT("exec_python"))
            {
                ResultJson = EditorCommands->HandleCommand(CommandType, Params);
            }
            // Blueprint Commands
            else if (CommandType == TEXT("create_blueprint") || 
                     CommandType == TEXT("add_component_to_blueprint") || 
                     CommandType == TEXT("set_component_property") || 
                     CommandType == TEXT("set_physics_properties") || 
                     CommandType == TEXT("compile_blueprint") || 
                     CommandType == TEXT("set_blueprint_property") || 
                     CommandType == TEXT("set_static_mesh_properties") ||
                     CommandType == TEXT("set_pawn_properties") ||
                     CommandType == TEXT("set_blueprint_ai_controller"))
            {
                ResultJson = BlueprintCommands->HandleCommand(CommandType, Params);
            }
            // Blueprint Node Commands
            else if (CommandType == TEXT("get_blueprint_nodes") ||
                     CommandType == TEXT("find_blueprint_nodes") ||
                     CommandType == TEXT("get_blueprint_graphs") ||
                     CommandType == TEXT("get_node_by_id") ||
                     CommandType == TEXT("connect_blueprint_nodes") ||
                     CommandType == TEXT("disconnect_blueprint_nodes") ||
                     CommandType == TEXT("delete_blueprint_node") ||
                     CommandType == TEXT("set_node_pin_value") ||
                     CommandType == TEXT("add_blueprint_event_node") ||
                     CommandType == TEXT("add_blueprint_custom_event_node") ||
                     CommandType == TEXT("set_spawn_actor_class") ||
                     CommandType == TEXT("add_blueprint_function_node") ||
                     CommandType == TEXT("add_blueprint_variable_get_node") ||
                     CommandType == TEXT("add_blueprint_variable_set_node") ||
                     CommandType == TEXT("add_blueprint_variable") ||
                     CommandType == TEXT("add_blueprint_input_action_node") ||
                     CommandType == TEXT("add_blueprint_enhanced_input_action_node") ||
                     CommandType == TEXT("add_blueprint_self_reference") ||
                     CommandType == TEXT("add_blueprint_get_self_component_reference") ||
                     CommandType == TEXT("add_blueprint_get_component_node") ||
                     CommandType == TEXT("add_blueprint_set_component_property") ||
                     CommandType == TEXT("add_blueprint_branch_node") ||
                     CommandType == TEXT("add_blueprint_cast_node") ||
                     // Phase 2: structural nodes (L-012)
                     CommandType == TEXT("add_blueprint_for_loop_node") ||
                     CommandType == TEXT("add_blueprint_for_each_loop_node") ||
                     CommandType == TEXT("add_blueprint_sequence_node") ||
                     CommandType == TEXT("add_blueprint_do_once_node") ||
                     CommandType == TEXT("add_blueprint_gate_node") ||
                     CommandType == TEXT("add_blueprint_flip_flop_node") ||
                     CommandType == TEXT("add_blueprint_switch_on_int_node") ||
                     CommandType == TEXT("add_blueprint_spawn_actor_node") ||
                     // Phase 2: comment + reposition (L-018, L-019)
                     CommandType == TEXT("add_blueprint_comment_node") ||
                     CommandType == TEXT("move_blueprint_node") ||
                     // Phase 3: variable defaults (L-013)
                     CommandType == TEXT("get_blueprint_variable_defaults") ||
                     CommandType == TEXT("set_blueprint_variable_default") ||
                     // Phase 4: component inspection (L-020)
                     CommandType == TEXT("get_blueprint_components") ||
                     // Phase 5: NavMesh (L-014)
                     CommandType == TEXT("setup_navmesh") ||
                     // Phase 6: variable + function introspection
                     CommandType == TEXT("get_blueprint_variables") ||
                     CommandType == TEXT("get_blueprint_functions"))
            {
                ResultJson = BlueprintNodeCommands->HandleCommand(CommandType, Params);
            }
            // Project Commands
            else if (CommandType == TEXT("create_input_mapping"))
            {
                ResultJson = ProjectCommands->HandleCommand(CommandType, Params);
            }
            // UMG Commands
            else if (CommandType == TEXT("create_umg_widget_blueprint") ||
                     CommandType == TEXT("add_text_block_to_widget") ||
                     CommandType == TEXT("add_button_to_widget") ||
                     CommandType == TEXT("bind_widget_event") ||
                     CommandType == TEXT("set_text_block_binding") ||
                     CommandType == TEXT("add_widget_to_viewport"))
            {
                ResultJson = UMGCommands->HandleCommand(CommandType, Params);
            }
            // Extended Commands ? all 283 tools from Blueprints Visual Scripting for UE5
            else if (ExtendedCommands.IsValid())
            {
                TSharedPtr<FJsonObject> ExtResult = ExtendedCommands->HandleCommand(CommandType, Params);
                if (ExtResult.IsValid())
                {
                    ResultJson = ExtResult;
                }
                else
                {
                    ResponseJson->SetStringField(TEXT("status"), TEXT("error"));
                    ResponseJson->SetStringField(TEXT("error"), FString::Printf(TEXT("Unknown command: %s"), *CommandType));
                    FString ResultString;
                    TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> Writer =
                        TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&ResultString);
                    FJsonSerializer::Serialize(ResponseJson.ToSharedRef(), Writer);
                    Promise.SetValue(ResultString);
                    return;
                }
            }
            else
            {
                ResponseJson->SetStringField(TEXT("status"), TEXT("error"));
                ResponseJson->SetStringField(TEXT("error"), FString::Printf(TEXT("Unknown command: %s"), *CommandType));
                
                FString ResultString;
                TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> Writer =
                    TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&ResultString);
                FJsonSerializer::Serialize(ResponseJson.ToSharedRef(), Writer);
                Promise.SetValue(ResultString);
                return;
            }
            
            // Check if the result contains an error
            bool bSuccess = true;
            FString ErrorMessage;
            
            if (ResultJson->HasField(TEXT("success")))
            {
                bSuccess = ResultJson->GetBoolField(TEXT("success"));
                if (!bSuccess && ResultJson->HasField(TEXT("error")))
                {
                    ErrorMessage = ResultJson->GetStringField(TEXT("error"));
                }
            }
            
            if (bSuccess)
            {
                // Set success status and include the result
                ResponseJson->SetStringField(TEXT("status"), TEXT("success"));
                ResponseJson->SetObjectField(TEXT("result"), ResultJson);
            }
            else
            {
                // Set error status and include the error message
                ResponseJson->SetStringField(TEXT("status"), TEXT("error"));
                ResponseJson->SetStringField(TEXT("error"), ErrorMessage);
            }

            const double ElapsedMs = (FPlatformTime::Seconds() - CommandStartTime) * 1000.0;
            UE_LOG(LogMCP, Display, TEXT("[MCP] <<< END command: '%s' | success=%d | %.1f ms"),
                *CommandType, bSuccess ? 1 : 0, ElapsedMs);
        }
        catch (const std::exception& e)
        {
            const double ElapsedMs = (FPlatformTime::Seconds() - CommandStartTime) * 1000.0;
            UE_LOG(LogMCP, Error, TEXT("[MCP] <<< EXCEPTION in command '%s' after %.1f ms: %s"),
                *CommandType, ElapsedMs, UTF8_TO_TCHAR(e.what()));
            ResponseJson->SetStringField(TEXT("status"), TEXT("error"));
            ResponseJson->SetStringField(TEXT("error"), UTF8_TO_TCHAR(e.what()));
        }
        catch (...)
        {
            // This catch block handles non-std exceptions (e.g. SEH exceptions
            // on Windows that have been translated by _set_se_translator).
            // Note: raw hardware exceptions (EXCEPTION_ACCESS_VIOLATION) do NOT
            // reach here in a normal UE build – they are caught by the engine's
            // crash handler.  But structured exceptions translated to C++
            // exceptions via _set_se_translator WILL land here.
            const double ElapsedMs = (FPlatformTime::Seconds() - CommandStartTime) * 1000.0;
            UE_LOG(LogMCP, Error, TEXT("[MCP] <<< UNKNOWN EXCEPTION in command '%s' after %.1f ms"),
                *CommandType, ElapsedMs);
            ResponseJson->SetStringField(TEXT("status"), TEXT("error"));
            ResponseJson->SetStringField(TEXT("error"),
                FString::Printf(TEXT("Unknown exception in command '%s'"), *CommandType));
        }
        
        // Use condensed (single-line) JSON so the newline-delimited socket protocol
        // is never confused by embedded newlines inside large actor arrays, etc.
        FString ResultString;
        TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> Writer =
            TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&ResultString);
        FJsonSerializer::Serialize(ResponseJson.ToSharedRef(), Writer);
        Promise.SetValue(ResultString);
    });
    
    // -----------------------------------------------------------------------
    // Per-command GameThread timeout budget.
    //
    // Background:
    //   Without a timeout, Future.Get() blocks the TCP receiver thread forever
    //   when the GameThread handler stalls (AddMemberVariable on 8k-asset project,
    //   StaticLoadObject on cold asset, BP compile with many errors, etc.).
    //   The stalled TCP thread holds the socket; Python times out after 30/90 s
    //   and reconnects, but its AsyncTask is queued BEHIND the still-running
    //   stalled task — causing every subsequent command to wait in line.
    //
    // Per-command budgets:
    //   • compile_blueprint / save_blueprint / exec_python:
    //       80 s  — these legitimately run long; give them the full Python budget.
    //   • add_blueprint_variable / get_blueprint_* / add_component_to_blueprint:
    //       80 s  — AddMemberVariable + MarkStructurallyModified can notify the
    //               ContentBrowser which is expensive on large projects.
    //               FindBlueprint AR scan is slow on cold cache.
    //   • Everything else: 24 s  — frees the socket before Python's 30 s fires.
    // -----------------------------------------------------------------------
    double TimeoutSeconds = 24.0;  // default: fast commands
    if (CommandType == TEXT("exec_python"))
    {
        // exec_python tier-3: factory scripts (BehaviorTree, WidgetBlueprint) can
        // run 60-120 s inside UE5. Give a 140 s budget so C++ never cuts them off
        // before they finish. Python has 150 s (see _VERY_SLOW_COMMANDS).
        TimeoutSeconds = 140.0;
    }
    else if (CommandType == TEXT("compile_blueprint") ||
             CommandType == TEXT("save_blueprint")    ||
             CommandType == TEXT("create_blueprint"))
    {
        TimeoutSeconds = 80.0;   // legitimately slow
    }
    else if (CommandType == TEXT("add_blueprint_variable")    ||
             CommandType == TEXT("get_blueprint_variables")   ||
             CommandType == TEXT("get_blueprint_functions")   ||
             CommandType == TEXT("get_blueprint_graphs")      ||
             CommandType == TEXT("add_component_to_blueprint")||
             CommandType == TEXT("get_actors_in_level")       ||
             CommandType == TEXT("focus_viewport"))
    {
        TimeoutSeconds = 80.0;   // AR scan + possible notification chain
    }

    const FTimespan WaitTimeout = FTimespan::FromSeconds(TimeoutSeconds);
    const bool bCompleted = Future.WaitFor(WaitTimeout);
    if (!bCompleted)
    {
        // Return a JSON error immediately so the TCP socket is freed and the
        // next command is not blocked behind this stalled GameThread task.
        TSharedPtr<FJsonObject> TimeoutResponse = MakeShareable(new FJsonObject);
        TimeoutResponse->SetStringField(TEXT("status"), TEXT("error"));
        TimeoutResponse->SetStringField(TEXT("error"),
            FString::Printf(TEXT("GameThread timeout after %.0fs for command '%s'. "
                "The operation may still be running in the background. "
                "Possible causes: (1) AddMemberVariable / MarkStructurallyModified "
                "triggered a ContentBrowser/AssetRegistry refresh on a large project "
                "(8k+ assets); (2) StaticLoadObject blocked on an uncached asset; "
                "(3) Blueprint compile with many errors held the compiler lock. "
                "Retry after a few seconds; if persistent, compile+save the Blueprint "
                "first or restart the UE5 editor."),
                TimeoutSeconds, *CommandType));
        FString TimeoutResultString;
        TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> TWriter =
            TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&TimeoutResultString);
        FJsonSerializer::Serialize(TimeoutResponse.ToSharedRef(), TWriter);
        UE_LOG(LogMCP, Error,
            TEXT("[MCP] <<< TIMEOUT: command '%s' did not complete within %.0fs"),
            *CommandType, TimeoutSeconds);
        return TimeoutResultString;
    }
    return Future.Get();
}