#pragma once

#include "Modules/ModuleInterface.h"
#include "Modules/ModuleManager.h"

class IUnrealMCPEditorModule : public IModuleInterface
{
public:
	static IUnrealMCPEditorModule& Get()
	{
		return FModuleManager::LoadModuleChecked<IUnrealMCPEditorModule>(TEXT("UnrealMCPEditor"));
	}

	static bool IsAvailable()
	{
		return FModuleManager::Get().IsModuleLoaded(TEXT("UnrealMCPEditor"));
	}

	virtual void OpenTripoWorkspaceWindow() = 0;
};
