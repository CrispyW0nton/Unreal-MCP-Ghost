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

// ─────────────────────────────────────────────────────────────────────────────
// Protocol model: one TCP connection = one JSON command = one JSON response.
//
// The Python server (unreal_mcp_server.py) opens a fresh TCP connection for
// every command it sends, waits for the full response, then closes the socket.
// The C++ side MUST match this model:
//
//   accept() → read until newline → ExecuteCommand() → Send() → Close()
//
// Why this matters:
//   • Python's socket timeout (30 / 90 / 150 s) may fire before ExecuteCommand
//     returns for slow commands.  Python closes the socket and reconnects for
//     the next command.  If C++ keeps the old socket open and tries to Send()
//     after the timeout, Windows returns WSAENOTSOCK (10038) because the
//     socket descriptor is no longer valid on Python's end.
//   • The [WinError 10038] error then poisons ClientSocket permanently for
//     the rest of the session: every subsequent Recv() also fails, causing a
//     cascade of timeouts across all following commands.
//
// Fix: close ClientSocket immediately after Send() (or on Send() failure).
//      The next command arrives on a brand-new connection → no stale handles.
// ─────────────────────────────────────────────────────────────────────────────

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

// ─── Helper: safely close and release a client socket ────────────────────────
static void CloseClientSocket(TSharedPtr<FSocket>& Sock)
{
    if (Sock.IsValid())
    {
        Sock->Close();
        Sock.Reset();
    }
}

// ─── Helper: send a UTF-8 encoded JSON response and close the socket ─────────
// Returns true if Send() succeeded.
static bool SendAndClose(TSharedPtr<FSocket>& ClientSock, const FString& Response)
{
    if (!ClientSock.IsValid())
    {
        UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: SendAndClose — socket already invalid, dropping response"));
        return false;
    }

    FString FullResponse = Response;
    if (!FullResponse.EndsWith(TEXT("\n")))
        FullResponse += TEXT("\n");

    FTCHARToUTF8 Utf8Response(*FullResponse);
    int32 BytesSent = 0;
    bool bOk = ClientSock->Send(
        (const uint8*)Utf8Response.Get(), Utf8Response.Length(), BytesSent);

    if (bOk)
        UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Response sent (%d bytes)"), BytesSent);
    else
        UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Send() failed — client likely disconnected before response"));

    // Always close after one command regardless of Send() success.
    // This prevents stale handles from poisoning future commands.
    CloseClientSocket(ClientSock);
    return bOk;
}

uint32 FMCPServerRunnable::Run()
{
    UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Server thread starting (one-command-per-connection model)"));

    while (bRunning)
    {
        // ── 1. Accept a new connection ────────────────────────────────────────
        bool bPending = false;
        if (!ListenerSocket->HasPendingConnection(bPending) || !bPending)
        {
            FPlatformProcess::Sleep(0.05f);
            continue;
        }

        UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Accepting new connection..."));
        TSharedPtr<FSocket> ClientSock = MakeShareable(ListenerSocket->Accept(TEXT("MCPClient")));
        if (!ClientSock.IsValid())
        {
            UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Accept() failed"));
            FPlatformProcess::Sleep(0.05f);
            continue;
        }

        // Socket options
        ClientSock->SetNoDelay(true);
        ClientSock->SetNonBlocking(false);   // blocking reads — simpler recv loop
        ClientSock->SetSendBufferSize(131072, 131072);
        ClientSock->SetReceiveBufferSize(131072, 131072);

        UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Connection accepted"));

        // ── 2. Read until we have a complete newline-terminated JSON line ─────
        //       Timeout: 10 s for the client to send its command.
        const double kReadDeadline = FPlatformTime::Seconds() + 10.0;
        FString MessageBuffer;
        bool bGotCommand = false;

        // Switch to non-blocking for the read phase so we can honour the deadline
        ClientSock->SetNonBlocking(true);

        while (bRunning && FPlatformTime::Seconds() < kReadDeadline)
        {
            uint8 Buf[8192];
            int32 BytesRead = 0;
            const bool bRecvOk = ClientSock->Recv(Buf, sizeof(Buf) - 1, BytesRead);

            if (bRecvOk && BytesRead > 0)
            {
                Buf[BytesRead] = '\0';
                MessageBuffer.Append(UTF8_TO_TCHAR(Buf));

                if (MessageBuffer.Contains(TEXT("\n")))
                {
                    bGotCommand = true;
                    break;
                }
            }
            else if (!bRecvOk)
            {
                int32 ErrCode = (int32)ISocketSubsystem::Get()->GetLastErrorCode();
                if (ErrCode == SE_EWOULDBLOCK || ErrCode == SE_EAGAIN)
                {
                    FPlatformProcess::Sleep(0.005f);
                    continue;
                }
                // Real error or remote closed
                UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Read error/close during recv — code %d"), ErrCode);
                break;
            }
            else
            {
                // BytesRead == 0 → peer closed connection (health-check probe)
                UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Zero-byte recv — health-check probe, closing"));
                break;
            }
        }

        if (!bGotCommand)
        {
            UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: No command received — closing connection"));
            CloseClientSocket(ClientSock);
            continue;
        }

        // ── 3. Extract the first complete JSON line ───────────────────────────
        int32 NlIdx;
        MessageBuffer.FindChar(TEXT('\n'), NlIdx);
        FString JsonLine = MessageBuffer.Left(NlIdx).TrimStartAndEnd();

        if (JsonLine.IsEmpty())
        {
            UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Empty JSON line received"));
            CloseClientSocket(ClientSock);
            continue;
        }

        UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Received command line: %s"), *JsonLine);

        // ── 4. Parse JSON ─────────────────────────────────────────────────────
        TSharedPtr<FJsonObject> JsonObject;
        TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonLine);
        if (!FJsonSerializer::Deserialize(Reader, JsonObject) || !JsonObject.IsValid())
        {
            UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Failed to parse JSON"));
            FString ErrResp = TEXT("{\"status\":\"error\",\"error\":\"Invalid JSON command\"}\n");
            SendAndClose(ClientSock, ErrResp);
            continue;
        }

        // Support both "type" (legacy) and "command" field names
        FString CommandType;
        bool bHasCommand = JsonObject->TryGetStringField(TEXT("command"), CommandType);
        if (!bHasCommand)
            bHasCommand = JsonObject->TryGetStringField(TEXT("type"), CommandType);

        if (!bHasCommand || CommandType.IsEmpty())
        {
            UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Missing command/type field"));
            SendAndClose(ClientSock, TEXT("{\"status\":\"error\",\"error\":\"Missing command type\"}"));
            continue;
        }

        // Extract params (optional)
        TSharedPtr<FJsonObject> Params = MakeShareable(new FJsonObject());
        if (JsonObject->HasField(TEXT("params")))
        {
            TSharedPtr<FJsonValue> ParamsVal = JsonObject->TryGetField(TEXT("params"));
            if (ParamsVal.IsValid() && ParamsVal->Type == EJson::Object)
                Params = ParamsVal->AsObject();
        }

        // ── 5. Switch socket back to blocking for the Send() call ─────────────
        //       ExecuteCommand can take up to 140 s (exec_python factory scripts).
        //       The socket stays open during this time; we switch to blocking mode
        //       so Send() doesn't spuriously fail with EWOULDBLOCK on large payloads.
        ClientSock->SetNonBlocking(false);

        // ── 6. Execute the command (may block for up to 140 s) ───────────────
        UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Executing command '%s'"), *CommandType);
        FString Response = Bridge->ExecuteCommand(CommandType, Params);
        UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Command complete, sending response (%d chars)"), Response.Len());

        // ── 7. Send response and CLOSE the socket ────────────────────────────
        //       CRITICAL: always close after one command so the next command
        //       arrives on a fresh socket. This prevents [WinError 10038].
        SendAndClose(ClientSock, Response);

        // ClientSock is now Reset() inside SendAndClose — loop back to accept()
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

// ─── Legacy helpers kept for API compatibility ────────────────────────────────
// HandleClientConnection and ProcessMessage are declared in the header but are
// no longer called by Run(). They are kept so the header doesn't need changes.

void FMCPServerRunnable::HandleClientConnection(TSharedPtr<FSocket> InClientSocket)
{
    // No longer used — Run() handles connections directly (one-command-per-connection).
    UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: HandleClientConnection called (legacy path — should not happen)"));
    CloseClientSocket(InClientSocket);
}

void FMCPServerRunnable::ProcessMessage(TSharedPtr<FSocket> Client, const FString& Message)
{
    // No longer used — Run() dispatches commands directly.
    UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: ProcessMessage called (legacy path — should not happen)"));
}
