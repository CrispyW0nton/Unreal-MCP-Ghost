#pragma once

#include "CoreMinimal.h"
#include "EditorSubsystem.h"
#include "Sockets.h"
#include "SocketSubsystem.h"
#include "Http.h"
#include "Json.h"
#include "Interfaces/IPv4/IPv4Address.h"
#include "Interfaces/IPv4/IPv4Endpoint.h"
#include "Containers/Ticker.h"
#include "Commands/UnrealMCPEditorCommands.h"
#include "Commands/UnrealMCPBlueprintCommands.h"
#include "Commands/UnrealMCPBlueprintNodeCommands.h"
#include "Commands/UnrealMCPProjectCommands.h"
#include "Commands/UnrealMCPUMGCommands.h"
#include "Commands/UnrealMCPExtendedCommands.h"
#include "Engine/TimerHandle.h"
#include "UnrealMCPBridge.generated.h"

class AActor;
class FMCPServerRunnable;

struct FSithTrooperCombatState
{
	TWeakObjectPtr<AActor> Target;
	FVector SpawnLocation = FVector::ZeroVector;
	float LastSeenTime = -1000.0f;
	float NextMoveTime = 0.0f;
	float NextShotTime = 0.0f;
	float BurstEndTime = 0.0f;
	float ArrivalSettleUntil = 0.0f;
	int32 ShotsRemaining = 0;
	int32 BurstsBeforeMove = 0;
	bool bWasInCombat = false;
	bool bPlayedRaise = false;
	bool bMoveInProgress = false;
	bool bClearedBlueprintMoveTimer = false;
	bool bAppliedRuntimeOptimizations = false;
	bool bDeathMontageStarted = false;
	bool bDeathRagdollActivated = false;
	float DeathRagdollTime = 0.0f;
	float SmoothedAnimSpeed = 0.0f;
	float SmoothedAnimDirection = 0.0f;
};

/**
 * Editor subsystem for MCP Bridge
 * Handles communication between external tools and the Unreal Editor
 * through a TCP socket connection. Commands are received as JSON and
 * routed to appropriate command handlers.
 */
UCLASS()
class UNREALMCP_API UUnrealMCPBridge : public UEditorSubsystem
{
	GENERATED_BODY()

public:
	UUnrealMCPBridge();
	virtual ~UUnrealMCPBridge();

	// UEditorSubsystem implementation
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	// Server functions
	void StartServer();
	void StopServer();
	bool IsRunning() const { return bIsRunning; }

	// Watchdog: called periodically to restart the server thread if it died
	UFUNCTION()
	void WatchdogTick();

	// Command execution
	FString ExecuteCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
	// Server state
	bool bIsRunning;
	TSharedPtr<FSocket> ListenerSocket;
	TSharedPtr<FSocket> ConnectionSocket;
	FRunnableThread* ServerThread;

	// Server configuration
	FIPv4Address ServerAddress;
	uint16 Port;

	// Watchdog timer handle
	FTimerHandle WatchdogTimerHandle;
	FTSTicker::FDelegateHandle SithCombatTickerHandle;
	TMap<TWeakObjectPtr<AActor>, FSithTrooperCombatState> SithCombatStates;

	bool SithCombatDirectorTick(float DeltaTime);

	// Command handler instances
	TSharedPtr<FUnrealMCPEditorCommands> EditorCommands;
	TSharedPtr<FUnrealMCPBlueprintCommands> BlueprintCommands;
	TSharedPtr<FUnrealMCPBlueprintNodeCommands> BlueprintNodeCommands;
	TSharedPtr<FUnrealMCPProjectCommands> ProjectCommands;
	TSharedPtr<FUnrealMCPUMGCommands> UMGCommands;
	TSharedPtr<FUnrealMCPExtendedCommands> ExtendedCommands;
}; 