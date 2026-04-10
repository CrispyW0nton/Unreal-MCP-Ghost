#include "UnrealMCPModule.h"
#include "UnrealMCPBridge.h"
#include "Modules/ModuleManager.h"
#include "EditorSubsystem.h"
#include "Editor.h"

// Define the LogMCP category here (declared in UnrealMCPModule.h)
DEFINE_LOG_CATEGORY(LogMCP);

#define LOCTEXT_NAMESPACE "FUnrealMCPModule"

void FUnrealMCPModule::StartupModule()
{
	UE_LOG(LogMCP, Display, TEXT("UnrealMCP plugin started - all MCP messages use category LogMCP"));
	UE_LOG(LogMCP, Display, TEXT("  Filter log: Output Log -> search 'LogMCP'"));
	UE_LOG(LogMCP, Display, TEXT("  Filter file: grep \"\\[MCP\\]\" UnrealEditor.log"));
}

void FUnrealMCPModule::ShutdownModule()
{
	UE_LOG(LogMCP, Display, TEXT("UnrealMCP plugin shut down"));
}

#undef LOCTEXT_NAMESPACE
	
IMPLEMENT_MODULE(FUnrealMCPModule, UnrealMCP) 