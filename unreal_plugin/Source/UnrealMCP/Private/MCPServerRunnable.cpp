#include "MCPServerRunnable.h"
#include "UnrealMCPBridge.h"
#include "Sockets.h"
#include "SocketSubsystem.h"
#include "Interfaces/IPv4/IPv4Address.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonReader.h"
#include "JsonObjectConverter.h"
#include "Misc/ScopeLock.h"
#include "HAL/PlatformTime.h"

// Buffer size for receiving data
// Renamed to avoid hiding the global BufferSize declared in UE5.6 engine headers
const int32 MCP_BufferSize = 8192;

FMCPServerRunnable::FMCPServerRunnable(UUnrealMCPBridge* InBridge, TSharedPtr<FSocket> InListenerSocket)
    : Bridge(InBridge)
    , ListenerSocket(InListenerSocket)
    , bRunning(true)
{
    UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Created server runnable"));
}

FMCPServerRunnable::~FMCPServerRunnable()
{
    // Note: We don't delete the sockets here as they're owned by the bridge
}

bool FMCPServerRunnable::Init()
{
    return true;
}

uint32 FMCPServerRunnable::Run()
{
    UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Server thread starting..."));
    
    while (bRunning)
    {
        bool bPending = false;
        if (ListenerSocket->HasPendingConnection(bPending) && bPending)
        {
            UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Client connection pending, accepting..."));
            
            ClientSocket = MakeShareable(ListenerSocket->Accept(TEXT("MCPClient")));
            if (ClientSocket.IsValid())
            {
                UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Client connection accepted"));
                
                // Set socket options to improve connection stability
                ClientSocket->SetNoDelay(true);
                int32 SocketBufferSize = 65536;  // 64KB buffer
                ClientSocket->SetSendBufferSize(SocketBufferSize, SocketBufferSize);
                ClientSocket->SetReceiveBufferSize(SocketBufferSize, SocketBufferSize);
                
                // ---------------------------------------------------------------
                // Playit.plus (and other TCP proxies/tunnels) send health-check
                // probes: they open a connection but send zero bytes, then close.
                // Previously the plugin would immediately break out of the recv
                // loop on the first zero-byte read, causing the real command that
                // arrives a moment later to be dropped.
                //
                // Fix: poll for pending data with a short wait (up to 5 s total,
                // 50 ms intervals) before entering the blocking recv loop.  If
                // no data arrives within that window the connection really is an
                // empty probe and we close it gracefully.
                // ---------------------------------------------------------------
                const float kProbeTimeoutSecs = 5.0f;
                const float kPollIntervalSecs = 0.05f;
                float elapsed = 0.0f;
                bool bGotData = false;

                while (bRunning && elapsed < kProbeTimeoutSecs)
                {
                    uint32 PendingBytes = 0;
                    if (ClientSocket->HasPendingData(PendingBytes) && PendingBytes > 0)
                    {
                        bGotData = true;
                        break;
                    }
                    // Also check connection state — remote may have closed already
                    if (ClientSocket->GetConnectionState() != SCS_Connected)
                    {
                        UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Probe connection closed before sending data — ignoring"));
                        break;
                    }
                    FPlatformProcess::Sleep(kPollIntervalSecs);
                    elapsed += kPollIntervalSecs;
                }

                if (!bGotData)
                {
                    UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: No data received within %.1f s — treating as health-check probe, skipping"), kProbeTimeoutSecs);
                    // Close the probe socket and loop back to accept the next real connection
                    ClientSocket->Close();
                    ClientSocket.Reset();
                    FPlatformProcess::Sleep(0.1f);
                    continue;
                }

                // Real data is pending — enter the message loop
                UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Data pending, entering message loop"));

                uint8 Buffer[8192];
                FString MessageBuffer;

                while (bRunning)
                {
                    int32 BytesRead = 0;
                    if (ClientSocket->Recv(Buffer, sizeof(Buffer) - 1, BytesRead))
                    {
                        if (BytesRead == 0)
                        {
                            UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Client disconnected (zero bytes)"));
                            break;
                        }

                        // Null-terminate and convert to FString
                        Buffer[BytesRead] = '\0';
                        FString ReceivedText = UTF8_TO_TCHAR(Buffer);
                        UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Received: %s"), *ReceivedText);

                        // Accumulate into message buffer (newline-delimited protocol)
                        MessageBuffer.Append(ReceivedText);

                        // Process all complete newline-terminated messages
                        while (MessageBuffer.Contains(TEXT("\n")))
                        {
                            int32 NewlineIdx;
                            MessageBuffer.FindChar(TEXT('\n'), NewlineIdx);
                            FString CompleteMessage = MessageBuffer.Left(NewlineIdx).TrimStartAndEnd();
                            MessageBuffer = MessageBuffer.Mid(NewlineIdx + 1);

                            if (CompleteMessage.IsEmpty())
                                continue;

                            UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Processing message: %s"), *CompleteMessage);

                            // Parse JSON
                            TSharedPtr<FJsonObject> JsonObject;
                            TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(CompleteMessage);

                            if (FJsonSerializer::Deserialize(Reader, JsonObject) && JsonObject.IsValid())
                            {
                                // Support both "type" (old format) and "command" (MCP format)
                                FString CommandType;
                                bool bHasCommand = JsonObject->TryGetStringField(TEXT("command"), CommandType);
                                if (!bHasCommand)
                                {
                                    bHasCommand = JsonObject->TryGetStringField(TEXT("type"), CommandType);
                                }

                                if (bHasCommand)
                                {
                                    TSharedPtr<FJsonObject> Params = MakeShareable(new FJsonObject());
                                    if (JsonObject->HasField(TEXT("params")))
                                    {
                                        TSharedPtr<FJsonValue> ParamsVal = JsonObject->TryGetField(TEXT("params"));
                                        if (ParamsVal.IsValid() && ParamsVal->Type == EJson::Object)
                                        {
                                            Params = ParamsVal->AsObject();
                                        }
                                    }

                                    FString Response = Bridge->ExecuteCommand(CommandType, Params);
                                    UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Sending response: %s"), *Response);

                                    // Ensure response is newline-terminated
                                    if (!Response.EndsWith(TEXT("\n")))
                                        Response += TEXT("\n");

                                    int32 BytesSent = 0;
                                    if (!ClientSocket->Send((uint8*)TCHAR_TO_UTF8(*Response), Response.Len(), BytesSent))
                                    {
                                        UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Failed to send response"));
                                    }
                                    else
                                    {
                                        UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Response sent (%d bytes)"), BytesSent);
                                    }
                                }
                                else
                                {
                                    UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Missing 'command'/'type' field in message"));
                                }
                            }
                            else
                            {
                                UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Failed to parse JSON: %s"), *CompleteMessage);
                            }
                        }
                    }
                    else
                    {
                        int32 LastError = (int32)ISocketSubsystem::Get()->GetLastErrorCode();
                        if (LastError == SE_EWOULDBLOCK)
                        {
                            FPlatformProcess::Sleep(0.01f);
                            continue;
                        }
                        else if (LastError == SE_EINTR)
                        {
                            continue;
                        }
                        else
                        {
                            UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Client disconnected or error. Code: %d"), LastError);
                            break;
                        }
                    }
                }

                UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Client session ended"));
            }
            else
            {
                UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Failed to accept client connection"));
            }
        }
        
        // Small sleep to prevent tight loop
        FPlatformProcess::Sleep(0.1f);
    }
    
    UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Server thread stopping"));
    return 0;
}

void FMCPServerRunnable::Stop()
{
    bRunning = false;
}

void FMCPServerRunnable::Exit()
{
}

void FMCPServerRunnable::HandleClientConnection(TSharedPtr<FSocket> InClientSocket)
{
    if (!InClientSocket.IsValid())
    {
        UE_LOG(LogTemp, Error, TEXT("MCPServerRunnable: Invalid client socket passed to HandleClientConnection"));
        return;
    }

    UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Starting to handle client connection"));
    
    // Set socket options for better connection stability
    InClientSocket->SetNonBlocking(false);
    UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Set socket to blocking mode"));
    
    // Properly read full message with timeout
    const int32 MaxBufferSize = 4096;
    uint8 Buffer[MaxBufferSize];
    FString MessageBuffer;
    
    UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Starting message receive loop"));
    
    while (bRunning && InClientSocket.IsValid())
    {
        // Log socket state
        bool bIsConnected = InClientSocket->GetConnectionState() == SCS_Connected;
        UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Socket state - Connected: %s"), 
               bIsConnected ? TEXT("true") : TEXT("false"));
        
        // Log pending data status before receive
        uint32 PendingDataSize = 0;
        bool HasPendingData = InClientSocket->HasPendingData(PendingDataSize);
        UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Before Recv - HasPendingData=%s, Size=%d"), 
               HasPendingData ? TEXT("true") : TEXT("false"), PendingDataSize);
        
        // Try to receive data with timeout
        int32 BytesRead = 0;
        bool bReadSuccess = false;
        
        UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Attempting to receive data..."));
        bReadSuccess = InClientSocket->Recv(Buffer, MaxBufferSize, BytesRead, ESocketReceiveFlags::None);
        
        UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Recv attempt complete - Success=%s, BytesRead=%d"), 
               bReadSuccess ? TEXT("true") : TEXT("false"), BytesRead);
        
        if (BytesRead > 0)
        {
            // Log raw data for debugging
            FString HexData;
            for (int32 i = 0; i < FMath::Min(BytesRead, 50); ++i)
            {
                HexData += FString::Printf(TEXT("%02X "), Buffer[i]);
            }
            UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Raw data (first 50 bytes hex): %s%s"), 
                   *HexData, BytesRead > 50 ? TEXT("...") : TEXT(""));
            
            // Convert and log received data
            Buffer[BytesRead] = 0; // Null terminate
            FString ReceivedData = UTF8_TO_TCHAR(Buffer);
            UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Received data as string: '%s'"), *ReceivedData);
            
            // Append to message buffer
            MessageBuffer.Append(ReceivedData);
            
            // Process complete messages (messages are terminated with newline)
            if (MessageBuffer.Contains(TEXT("\n")))
            {
                UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Newline detected in buffer, processing messages"));
                
                TArray<FString> Messages;
                MessageBuffer.ParseIntoArray(Messages, TEXT("\n"), true);
                
                UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Found %d message(s) in buffer"), Messages.Num());
                
                // Process all complete messages
                for (int32 i = 0; i < Messages.Num() - 1; ++i)
                {
                    UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Processing message %d: '%s'"), 
                           i + 1, *Messages[i]);
                    ProcessMessage(InClientSocket, Messages[i]);
                }
                
                // Keep any incomplete message in the buffer
                MessageBuffer = Messages.Last();
                UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Remaining buffer after processing: %s"), 
                       *MessageBuffer);
            }
            else
            {
                UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: No complete message yet (no newline detected)"));
            }
        }
        else if (!bReadSuccess)
        {
            UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Connection closed or error occurred - Last error: %d"), 
                   (int32)ISocketSubsystem::Get()->GetLastErrorCode());
            break;
        }
        
        // Small sleep to prevent tight loop
        FPlatformProcess::Sleep(0.01f);
    }
    
    UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Exited message receive loop"));
}

void FMCPServerRunnable::ProcessMessage(TSharedPtr<FSocket> Client, const FString& Message)
{
    UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Processing message: %s"), *Message);
    
    // Parse message as JSON
    TSharedPtr<FJsonObject> JsonMessage;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Message);
    
    if (!FJsonSerializer::Deserialize(Reader, JsonMessage) || !JsonMessage.IsValid())
    {
        UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Failed to parse message as JSON"));
        return;
    }
    
    // Extract command type and parameters using MCP protocol format
    FString CommandType;
    TSharedPtr<FJsonObject> Params = MakeShareable(new FJsonObject());
    
    if (!JsonMessage->TryGetStringField(TEXT("command"), CommandType))
    {
        UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Message missing 'command' field"));
        return;
    }
    
    // Parameters are optional in MCP protocol
    if (JsonMessage->HasField(TEXT("params")))
    {
        TSharedPtr<FJsonValue> ParamsValue = JsonMessage->TryGetField(TEXT("params"));
        if (ParamsValue.IsValid() && ParamsValue->Type == EJson::Object)
        {
            Params = ParamsValue->AsObject();
        }
    }
    
    UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Executing command: %s"), *CommandType);
    
    // Execute command
    FString Response = Bridge->ExecuteCommand(CommandType, Params);
    
    // Send response with newline terminator
    Response += TEXT("\n");
    int32 BytesSent = 0;
    
    UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Sending response: %s"), *Response);
    
    if (!Client->Send((uint8*)TCHAR_TO_UTF8(*Response), Response.Len(), BytesSent))
    {
        UE_LOG(LogTemp, Error, TEXT("MCPServerRunnable: Failed to send response"));
    }
}
