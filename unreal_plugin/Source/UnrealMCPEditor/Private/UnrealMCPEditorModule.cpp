#include "MCPChatPanel.h"

#include "Framework/Commands/UIAction.h"
#include "Framework/Docking/TabManager.h"
#include "Modules/ModuleManager.h"
#include "Textures/SlateIcon.h"
#include "ToolMenus.h"
#include "Widgets/Docking/SDockTab.h"

#define LOCTEXT_NAMESPACE "FUnrealMCPEditorModule"

namespace
{
	const FName UnrealMCPChatTabId(TEXT("UnrealMCPChat"));
}

class FUnrealMCPEditorModule : public IModuleInterface
{
public:
	virtual void StartupModule() override
	{
		FGlobalTabmanager::Get()->RegisterNomadTabSpawner(
			UnrealMCPChatTabId,
			FOnSpawnTab::CreateRaw(this, &FUnrealMCPEditorModule::SpawnChatTab)
		)
		.SetDisplayName(LOCTEXT("UnrealMCPChatTabTitle", "MCP Chat"))
		.SetTooltipText(LOCTEXT("UnrealMCPChatTooltip", "Open the Unreal MCP chat panel for Cursor communication."))
		.SetMenuType(ETabSpawnerMenuType::Hidden);

		UToolMenus::RegisterStartupCallback(
			FSimpleMulticastDelegate::FDelegate::CreateRaw(this, &FUnrealMCPEditorModule::RegisterMenus)
		);
	}

	virtual void ShutdownModule() override
	{
		if (UToolMenus::IsToolMenuUIEnabled())
		{
			UToolMenus::UnRegisterStartupCallback(this);
			UToolMenus::UnregisterOwner(this);
		}

		FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(UnrealMCPChatTabId);
	}

private:
	TSharedRef<SDockTab> SpawnChatTab(const FSpawnTabArgs& Args)
	{
		return SNew(SDockTab)
			.TabRole(ETabRole::NomadTab)
			.Label(LOCTEXT("UnrealMCPChatTabLabel", "MCP Chat"))
			[
				SNew(SMCPChatPanel)
			];
	}

	void RegisterMenus()
	{
		FToolMenuOwnerScoped OwnerScoped(this);

		UToolMenu* WindowMenu = UToolMenus::Get()->ExtendMenu(TEXT("LevelEditor.MainMenu.Window"));
		FToolMenuSection& Section = WindowMenu->FindOrAddSection(TEXT("WindowLayout"));
		Section.AddMenuEntry(
			TEXT("OpenUnrealMCPChat"),
			LOCTEXT("OpenUnrealMCPChatLabel", "MCP Chat"),
			LOCTEXT("OpenUnrealMCPChatTooltip", "Open the Unreal MCP chat panel."),
			FSlateIcon(),
			FUIAction(FExecuteAction::CreateStatic([]()
			{
				FGlobalTabmanager::Get()->TryInvokeTab(UnrealMCPChatTabId);
			}))
		);
	}
};

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FUnrealMCPEditorModule, UnrealMCPEditor)
