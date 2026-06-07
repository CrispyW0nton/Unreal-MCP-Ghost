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
class APawn;
class FMCPServerRunnable;
class UAudioComponent;
class UNavigationSystemV1;

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

struct FDarkJediBossCombatState
{
	TWeakObjectPtr<AActor> Target;
	TWeakObjectPtr<UAudioComponent> SaberHumComponent;
	FVector SpawnLocation = FVector::ZeroVector;
	float LastSeenTime = -1000.0f;
	float LostSightStartTime = -1.0f;
	float StateEnterTime = 0.0f;
	float NextMoveTime = 0.0f;
	float NextAttackTime = 0.0f;
	float NextDecisionTime = 0.0f;
	float NextIncomingDamageTime = 0.0f;
	float ForceEffectTime = 0.0f;
	float ForceEndTime = 0.0f;
	float NextLightningTickTime = 0.0f;
	float NextLightningVfxTime = 0.0f;
	float DeathRagdollTime = 0.0f;
	float SmoothedAnimSpeed = 0.0f;
	float SmoothedAnimDirection = 0.0f;
	int32 CombatState = 0;
	int32 ComboAttempts = 0;
	int32 DesiredComboLength = 2;
	int32 LastForceState = 4;
	bool bAppliedRuntimeSetup = false;
	bool bWasInCombat = false;
	bool bSaberActivated = false;
	bool bIssuedStateMove = false;
	bool bDamageAppliedThisSwing = false;
	bool bForceEffectApplied = false;
	bool bDeathMontageStarted = false;
	bool bDeathRagdollActivated = false;
	float StrafeSign = 1.0f;
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
	TMap<TWeakObjectPtr<AActor>, FDarkJediBossCombatState> DarkJediBossStates;

	bool SithCombatDirectorTick(float DeltaTime);
	void DarkJediBossDirectorTick(
		AActor* BossActor,
		FDarkJediBossCombatState& State,
		APawn* PlayerPawn,
		UNavigationSystemV1* NavSystem,
		float DeltaTime,
		float Now);

	// Command handler instances
	TSharedPtr<FUnrealMCPEditorCommands> EditorCommands;
	TSharedPtr<FUnrealMCPBlueprintCommands> BlueprintCommands;
	TSharedPtr<FUnrealMCPBlueprintNodeCommands> BlueprintNodeCommands;
	TSharedPtr<FUnrealMCPProjectCommands> ProjectCommands;
	TSharedPtr<FUnrealMCPUMGCommands> UMGCommands;
	TSharedPtr<FUnrealMCPExtendedCommands> ExtendedCommands;
}; 