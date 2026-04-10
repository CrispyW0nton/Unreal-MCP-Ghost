#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"
#include "Logging/LogMacros.h"

/**
 * Dedicated log category for all UnrealMCP plugin messages.
 * Filter in Unreal's Output Log with:   LogMCP
 * Or in the saved log file:             grep "\[MCP\]" UnrealEditor.log
 */
DECLARE_LOG_CATEGORY_EXTERN(LogMCP, Log, All);

class FUnrealMCPModule : public IModuleInterface
{
public:
	/** IModuleInterface implementation */
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;

	static inline FUnrealMCPModule& Get()
	{
		return FModuleManager::LoadModuleChecked<FUnrealMCPModule>("UnrealMCP");
	}

	static inline bool IsAvailable()
	{
		return FModuleManager::Get().IsModuleLoaded("UnrealMCP");
	}
}; 