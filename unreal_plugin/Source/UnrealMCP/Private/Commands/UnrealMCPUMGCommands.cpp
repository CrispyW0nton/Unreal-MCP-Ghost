#include "Commands/UnrealMCPUMGCommands.h"
#include "Commands/UnrealMCPCommonUtils.h"
#include "Editor.h"
#include "EditorAssetLibrary.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Blueprint/UserWidget.h"
#include "Components/TextBlock.h"
#include "WidgetBlueprint.h"
// We'll create widgets using regular Factory classes
#include "Factories/Factory.h"
// Remove problematic includes that don't exist in UE 5.5
// #include "UMGEditorSubsystem.h"
// #include "WidgetBlueprintFactory.h"
#include "WidgetBlueprintEditor.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetBlueprintGeneratedClass.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "JsonObjectConverter.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Misc/Paths.h"
#include "Styling/SlateColor.h"
#include "Components/Button.h"
#include "Components/HorizontalBox.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/PanelWidget.h"
#include "Components/ProgressBar.h"
#include "Components/SizeBox.h"
#include "Components/VerticalBox.h"
#include "K2Node_FunctionEntry.h"
#include "K2Node_CallFunction.h"
#include "K2Node_VariableGet.h"
#include "K2Node_VariableSet.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "K2Node_Event.h"

namespace
{
	UWidgetBlueprint* LoadWidgetBlueprintFromParams(const TSharedPtr<FJsonObject>& Params, FString& OutPath, FString& OutError)
	{
		FString WidgetBlueprintPath;
		if (!Params->TryGetStringField(TEXT("widget_blueprint_path"), WidgetBlueprintPath))
		{
			FString WidgetName;
			if (Params->TryGetStringField(TEXT("widget_name"), WidgetName) ||
				Params->TryGetStringField(TEXT("blueprint_name"), WidgetName))
			{
				if (WidgetName.StartsWith(TEXT("/Game/")))
				{
					WidgetBlueprintPath = WidgetName;
				}
				else
				{
					WidgetBlueprintPath = FString::Printf(TEXT("/Game/EndarSpire/UI/%s.%s"), *WidgetName, *WidgetName);
				}
			}
		}

		if (WidgetBlueprintPath.IsEmpty())
		{
			OutError = TEXT("Missing 'widget_blueprint_path' parameter");
			return nullptr;
		}

		FString AssetPath = WidgetBlueprintPath;
		if (!AssetPath.Contains(TEXT(".")))
		{
			const FString AssetName = FPaths::GetBaseFilename(AssetPath);
			AssetPath = FString::Printf(TEXT("%s.%s"), *AssetPath, *AssetName);
		}

		OutPath = AssetPath;
		UWidgetBlueprint* WidgetBlueprint = Cast<UWidgetBlueprint>(UEditorAssetLibrary::LoadAsset(AssetPath));
		if (!WidgetBlueprint)
		{
			OutError = FString::Printf(TEXT("Failed to load Widget Blueprint: %s"), *AssetPath);
		}
		return WidgetBlueprint;
	}

	UClass* ResolveWidgetClass(const FString& ChildClass)
	{
		if (ChildClass.Equals(TEXT("TextBlock"), ESearchCase::IgnoreCase)) return UTextBlock::StaticClass();
		if (ChildClass.Equals(TEXT("Image"), ESearchCase::IgnoreCase)) return UImage::StaticClass();
		if (ChildClass.Equals(TEXT("ProgressBar"), ESearchCase::IgnoreCase)) return UProgressBar::StaticClass();
		if (ChildClass.Equals(TEXT("CanvasPanel"), ESearchCase::IgnoreCase)) return UCanvasPanel::StaticClass();
		if (ChildClass.Equals(TEXT("HorizontalBox"), ESearchCase::IgnoreCase)) return UHorizontalBox::StaticClass();
		if (ChildClass.Equals(TEXT("VerticalBox"), ESearchCase::IgnoreCase)) return UVerticalBox::StaticClass();
		if (ChildClass.Equals(TEXT("Overlay"), ESearchCase::IgnoreCase)) return UOverlay::StaticClass();
		if (ChildClass.Equals(TEXT("SizeBox"), ESearchCase::IgnoreCase)) return USizeBox::StaticClass();
		if (ChildClass.Equals(TEXT("Button"), ESearchCase::IgnoreCase)) return UButton::StaticClass();
		return nullptr;
	}

	bool ParseCsvFloats(const FString& Input, TArray<float>& OutValues)
	{
		TArray<FString> Parts;
		Input.ParseIntoArray(Parts, TEXT(","), true);
		if (Parts.Num() == 1)
		{
			Input.ParseIntoArray(Parts, TEXT(" "), true);
		}

		OutValues.Reset();
		for (const FString& Part : Parts)
		{
			OutValues.Add(FCString::Atof(*Part.TrimStartAndEnd()));
		}
		return OutValues.Num() > 0;
	}

	FLinearColor ParseLinearColor(const FString& Value, const FLinearColor& DefaultColor = FLinearColor::White)
	{
		TArray<float> Values;
		if (!ParseCsvFloats(Value, Values) || Values.Num() < 3)
		{
			return DefaultColor;
		}
		return FLinearColor(Values[0], Values[1], Values[2], Values.Num() >= 4 ? Values[3] : 1.0f);
	}

	FVector2D ParseVector2D(const FString& Value, const FVector2D& DefaultValue = FVector2D::ZeroVector)
	{
		TArray<float> Values;
		if (!ParseCsvFloats(Value, Values) || Values.Num() < 2)
		{
			return DefaultValue;
		}
		return FVector2D(Values[0], Values[1]);
	}

	ESlateVisibility ParseVisibility(const FString& Value)
	{
		if (Value.Equals(TEXT("Hidden"), ESearchCase::IgnoreCase)) return ESlateVisibility::Hidden;
		if (Value.Equals(TEXT("Collapsed"), ESearchCase::IgnoreCase)) return ESlateVisibility::Collapsed;
		if (Value.Equals(TEXT("HitTestInvisible"), ESearchCase::IgnoreCase)) return ESlateVisibility::HitTestInvisible;
		if (Value.Equals(TEXT("SelfHitTestInvisible"), ESearchCase::IgnoreCase)) return ESlateVisibility::SelfHitTestInvisible;
		return ESlateVisibility::Visible;
	}

	FString VisibilityToString(const ESlateVisibility Visibility)
	{
		switch (Visibility)
		{
		case ESlateVisibility::Collapsed: return TEXT("Collapsed");
		case ESlateVisibility::Hidden: return TEXT("Hidden");
		case ESlateVisibility::HitTestInvisible: return TEXT("HitTestInvisible");
		case ESlateVisibility::SelfHitTestInvisible: return TEXT("SelfHitTestInvisible");
		default: return TEXT("Visible");
		}
	}

	void MarkWidgetBlueprintModified(UWidgetBlueprint* WidgetBlueprint)
	{
		if (!WidgetBlueprint)
		{
			return;
		}
		WidgetBlueprint->Modify();
		FBlueprintEditorUtils::MarkBlueprintAsModified(WidgetBlueprint);
		WidgetBlueprint->MarkPackageDirty();
	}

	void AddWidgetInfo(UWidget* Widget, TArray<TSharedPtr<FJsonValue>>& OutChildren)
	{
		if (!Widget)
		{
			return;
		}

		TSharedPtr<FJsonObject> ChildObj = MakeShared<FJsonObject>();
		ChildObj->SetStringField(TEXT("name"), Widget->GetName());
		ChildObj->SetStringField(TEXT("class"), Widget->GetClass()->GetName());
		ChildObj->SetStringField(TEXT("visibility"), VisibilityToString(Widget->GetVisibility()));
		ChildObj->SetBoolField(TEXT("is_variable"), Widget->bIsVariable);

		if (const UCanvasPanelSlot* CanvasSlot = Cast<UCanvasPanelSlot>(Widget->Slot))
		{
			TSharedPtr<FJsonObject> SlotObj = MakeShared<FJsonObject>();
			const FAnchors Anchors = CanvasSlot->GetAnchors();
			const FVector2D Position = CanvasSlot->GetPosition();
			const FVector2D Size = CanvasSlot->GetSize();
			const FVector2D Alignment = CanvasSlot->GetAlignment();
			SlotObj->SetNumberField(TEXT("anchor_min_x"), Anchors.Minimum.X);
			SlotObj->SetNumberField(TEXT("anchor_min_y"), Anchors.Minimum.Y);
			SlotObj->SetNumberField(TEXT("anchor_max_x"), Anchors.Maximum.X);
			SlotObj->SetNumberField(TEXT("anchor_max_y"), Anchors.Maximum.Y);
			SlotObj->SetNumberField(TEXT("position_x"), Position.X);
			SlotObj->SetNumberField(TEXT("position_y"), Position.Y);
			SlotObj->SetNumberField(TEXT("size_x"), Size.X);
			SlotObj->SetNumberField(TEXT("size_y"), Size.Y);
			SlotObj->SetNumberField(TEXT("alignment_x"), Alignment.X);
			SlotObj->SetNumberField(TEXT("alignment_y"), Alignment.Y);
			ChildObj->SetObjectField(TEXT("canvas_slot"), SlotObj);
		}

		OutChildren.Add(MakeShared<FJsonValueObject>(ChildObj));
	}
}

FUnrealMCPUMGCommands::FUnrealMCPUMGCommands()
{
}

TSharedPtr<FJsonObject> FUnrealMCPUMGCommands::HandleCommand(const FString& CommandName, const TSharedPtr<FJsonObject>& Params)
{
	if (CommandName == TEXT("create_umg_widget_blueprint"))
	{
		return HandleCreateUMGWidgetBlueprint(Params);
	}
	else if (CommandName == TEXT("add_text_block_to_widget"))
	{
		return HandleAddTextBlockToWidget(Params);
	}
	else if (CommandName == TEXT("add_widget_to_viewport"))
	{
		return HandleAddWidgetToViewport(Params);
	}
	else if (CommandName == TEXT("add_button_to_widget"))
	{
		return HandleAddButtonToWidget(Params);
	}
	else if (CommandName == TEXT("bind_widget_event"))
	{
		return HandleBindWidgetEvent(Params);
	}
	else if (CommandName == TEXT("set_text_block_binding"))
	{
		return HandleSetTextBlockBinding(Params);
	}
	else if (CommandName == TEXT("widget_add_child"))
	{
		return HandleWidgetAddChild(Params);
	}
	else if (CommandName == TEXT("widget_set_property"))
	{
		return HandleWidgetSetProperty(Params);
	}
	else if (CommandName == TEXT("widget_set_anchor"))
	{
		return HandleWidgetSetAnchor(Params);
	}
	else if (CommandName == TEXT("widget_get_children"))
	{
		return HandleWidgetGetChildren(Params);
	}
	else if (CommandName == TEXT("umg_add_widget_binding"))
	{
		return HandleAddWidgetBinding(Params);
	}

	return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Unknown UMG command: %s"), *CommandName));
}

TSharedPtr<FJsonObject> FUnrealMCPUMGCommands::HandleAddWidgetBinding(const TSharedPtr<FJsonObject>& Params)
{
	FString BlueprintPath;
	FString Error;
	UWidgetBlueprint* WidgetBlueprint = LoadWidgetBlueprintFromParams(Params, BlueprintPath, Error);
	if (!WidgetBlueprint)
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(Error);
	}

	FString PropertyPath;
	if (!Params->TryGetStringField(TEXT("property_path"), PropertyPath) || PropertyPath.IsEmpty())
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'property_path' parameter"));
	}

	FString BindingTarget;
	if (!Params->TryGetStringField(TEXT("binding_target"), BindingTarget) || BindingTarget.IsEmpty())
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'binding_target' parameter"));
	}

	FString ObjectName;
	FString PropertyName;
	if (!PropertyPath.Split(TEXT("."), &ObjectName, &PropertyName, ESearchCase::CaseSensitive, ESearchDir::FromEnd))
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(
			TEXT("property_path must be '<WidgetName>.<PropertyName>' (for example 'HealthText.Text')"));
	}

	if (!WidgetBlueprint->WidgetTree || !WidgetBlueprint->WidgetTree->FindWidget(FName(*ObjectName)))
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(
			FString::Printf(TEXT("Widget not found in WidgetTree: %s"), *ObjectName));
	}

	FString BindingKindString = TEXT("function");
	Params->TryGetStringField(TEXT("binding_kind"), BindingKindString);

	FDelegateEditorBinding Binding;
	Binding.ObjectName = ObjectName;
	Binding.PropertyName = FName(*PropertyName);
	if (BindingKindString.Equals(TEXT("property"), ESearchCase::IgnoreCase))
	{
		Binding.SourceProperty = FName(*BindingTarget);
		Binding.Kind = EBindingKind::Property;
	}
	else
	{
		Binding.FunctionName = FName(*BindingTarget);
		Binding.Kind = EBindingKind::Function;
		if (WidgetBlueprint->SkeletonGeneratedClass)
		{
			UBlueprint::GetGuidFromClassByFieldName<UFunction>(
				WidgetBlueprint->SkeletonGeneratedClass,
				Binding.FunctionName,
				Binding.MemberGuid);
		}
	}

	WidgetBlueprint->Modify();
	for (int32 Index = WidgetBlueprint->Bindings.Num() - 1; Index >= 0; --Index)
	{
		const FDelegateEditorBinding& Existing = WidgetBlueprint->Bindings[Index];
		if (Existing.ObjectName == Binding.ObjectName && Existing.PropertyName == Binding.PropertyName)
		{
			WidgetBlueprint->Bindings.RemoveAt(Index);
		}
	}
	WidgetBlueprint->Bindings.Add(Binding);

	MarkWidgetBlueprintModified(WidgetBlueprint);
	FKismetEditorUtilities::CompileBlueprint(WidgetBlueprint);

	TSharedPtr<FJsonObject> Response = MakeShared<FJsonObject>();
	Response->SetBoolField(TEXT("success"), true);
	Response->SetStringField(TEXT("widget_blueprint_path"), BlueprintPath);
	Response->SetStringField(TEXT("property_path"), PropertyPath);
	Response->SetStringField(TEXT("widget_name"), ObjectName);
	Response->SetStringField(TEXT("property_name"), PropertyName);
	Response->SetStringField(TEXT("binding_target"), BindingTarget);
	Response->SetStringField(TEXT("binding_kind"), Binding.Kind == EBindingKind::Property ? TEXT("property") : TEXT("function"));
	Response->SetNumberField(TEXT("binding_count"), WidgetBlueprint->Bindings.Num());
	return Response;
}

TSharedPtr<FJsonObject> FUnrealMCPUMGCommands::HandleCreateUMGWidgetBlueprint(const TSharedPtr<FJsonObject>& Params)
{
	// Get required parameters
	FString BlueprintName;
	if (!Params->TryGetStringField(TEXT("name"), BlueprintName))
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
	}

	// Create the full asset path
	FString PackagePath = TEXT("/Game/Widgets/");
	FString AssetName = BlueprintName;
	FString FullPath = PackagePath + AssetName;

	// Check if asset already exists
	if (UEditorAssetLibrary::DoesAssetExist(FullPath))
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Widget Blueprint '%s' already exists"), *BlueprintName));
	}

	// Create package
	UPackage* Package = CreatePackage(*FullPath);
	if (!Package)
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create package"));
	}

	// Create Widget Blueprint using KismetEditorUtilities
	UBlueprint* NewBlueprint = FKismetEditorUtilities::CreateBlueprint(
		UUserWidget::StaticClass(),  // Parent class
		Package,                     // Outer package
		FName(*AssetName),           // Blueprint name
		BPTYPE_Normal,               // Blueprint type
		UBlueprint::StaticClass(),   // Blueprint class
		UBlueprintGeneratedClass::StaticClass(), // Generated class
		FName("CreateUMGWidget")     // Creation method name
	);

	// Make sure the Blueprint was created successfully
	UWidgetBlueprint* WidgetBlueprint = Cast<UWidgetBlueprint>(NewBlueprint);
	if (!WidgetBlueprint)
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create Widget Blueprint"));
	}

	// Add a default Canvas Panel if one doesn't exist
	if (!WidgetBlueprint->WidgetTree->RootWidget)
	{
		UCanvasPanel* RootCanvas = WidgetBlueprint->WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass());
		WidgetBlueprint->WidgetTree->RootWidget = RootCanvas;
	}

	// Mark the package dirty and notify asset registry
	Package->MarkPackageDirty();
	FAssetRegistryModule::AssetCreated(WidgetBlueprint);

	// Compile the blueprint
	FKismetEditorUtilities::CompileBlueprint(WidgetBlueprint);

	// Create success response
	TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
	ResultObj->SetStringField(TEXT("name"), BlueprintName);
	ResultObj->SetStringField(TEXT("path"), FullPath);
	return ResultObj;
}

TSharedPtr<FJsonObject> FUnrealMCPUMGCommands::HandleAddTextBlockToWidget(const TSharedPtr<FJsonObject>& Params)
{
	// Get required parameters
	FString BlueprintName;
	if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'blueprint_name' parameter"));
	}

	FString WidgetName;
	if (!Params->TryGetStringField(TEXT("widget_name"), WidgetName))
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'widget_name' parameter"));
	}

	// Find the Widget Blueprint
	FString FullPath = TEXT("/Game/Widgets/") + BlueprintName;
	UWidgetBlueprint* WidgetBlueprint = Cast<UWidgetBlueprint>(UEditorAssetLibrary::LoadAsset(FullPath));
	if (!WidgetBlueprint)
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Widget Blueprint '%s' not found"), *BlueprintName));
	}

	// Get optional parameters
	FString InitialText = TEXT("New Text Block");
	Params->TryGetStringField(TEXT("text"), InitialText);

	FVector2D Position(0.0f, 0.0f);
	if (Params->HasField(TEXT("position")))
	{
		const TArray<TSharedPtr<FJsonValue>>* PosArray;
		if (Params->TryGetArrayField(TEXT("position"), PosArray) && PosArray->Num() >= 2)
		{
			Position.X = (*PosArray)[0]->AsNumber();
			Position.Y = (*PosArray)[1]->AsNumber();
		}
	}

	// Create Text Block widget
	UTextBlock* TextBlock = WidgetBlueprint->WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), *WidgetName);
	if (!TextBlock)
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create Text Block widget"));
	}

	// Set initial text
	TextBlock->SetText(FText::FromString(InitialText));

	// Add to canvas panel
	UCanvasPanel* RootCanvas = Cast<UCanvasPanel>(WidgetBlueprint->WidgetTree->RootWidget);
	if (!RootCanvas)
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Root Canvas Panel not found"));
	}

	UCanvasPanelSlot* PanelSlot = RootCanvas->AddChildToCanvas(TextBlock);
	PanelSlot->SetPosition(Position);

	// Mark the package dirty and compile
	WidgetBlueprint->MarkPackageDirty();
	FKismetEditorUtilities::CompileBlueprint(WidgetBlueprint);

	// Create success response
	TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
	ResultObj->SetStringField(TEXT("widget_name"), WidgetName);
	ResultObj->SetStringField(TEXT("text"), InitialText);
	return ResultObj;
}

TSharedPtr<FJsonObject> FUnrealMCPUMGCommands::HandleAddWidgetToViewport(const TSharedPtr<FJsonObject>& Params)
{
	// Get required parameters
	FString BlueprintName;
	if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'blueprint_name' parameter"));
	}

	// Find the Widget Blueprint
	FString FullPath = TEXT("/Game/Widgets/") + BlueprintName;
	UWidgetBlueprint* WidgetBlueprint = Cast<UWidgetBlueprint>(UEditorAssetLibrary::LoadAsset(FullPath));
	if (!WidgetBlueprint)
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Widget Blueprint '%s' not found"), *BlueprintName));
	}

	// Get optional Z-order parameter
	int32 ZOrder = 0;
	Params->TryGetNumberField(TEXT("z_order"), ZOrder);

	// Create widget instance
	UClass* WidgetClass = WidgetBlueprint->GeneratedClass;
	if (!WidgetClass)
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get widget class"));
	}

	// Note: This creates the widget but doesn't add it to viewport
	// The actual addition to viewport should be done through Blueprint nodes
	// as it requires a game context

	// Create success response with instructions
	TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
	ResultObj->SetStringField(TEXT("blueprint_name"), BlueprintName);
	ResultObj->SetStringField(TEXT("class_path"), WidgetClass->GetPathName());
	ResultObj->SetNumberField(TEXT("z_order"), ZOrder);
	ResultObj->SetStringField(TEXT("note"), TEXT("Widget class ready. Use CreateWidget and AddToViewport nodes in Blueprint to display in game."));
	return ResultObj;
}

TSharedPtr<FJsonObject> FUnrealMCPUMGCommands::HandleAddButtonToWidget(const TSharedPtr<FJsonObject>& Params)
{
	TSharedPtr<FJsonObject> Response = MakeShared<FJsonObject>();

	// Get required parameters
	FString BlueprintName;
	if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
	{
		Response->SetStringField(TEXT("error"), TEXT("Missing blueprint_name parameter"));
		return Response;
	}

	FString WidgetName;
	if (!Params->TryGetStringField(TEXT("widget_name"), WidgetName))
	{
		Response->SetStringField(TEXT("error"), TEXT("Missing widget_name parameter"));
		return Response;
	}

	FString ButtonText;
	if (!Params->TryGetStringField(TEXT("text"), ButtonText))
	{
		Response->SetStringField(TEXT("error"), TEXT("Missing text parameter"));
		return Response;
	}

	// Load the Widget Blueprint
	const FString BlueprintPath = FString::Printf(TEXT("/Game/Widgets/%s.%s"), *BlueprintName, *BlueprintName);
	UWidgetBlueprint* WidgetBlueprint = Cast<UWidgetBlueprint>(UEditorAssetLibrary::LoadAsset(BlueprintPath));
	if (!WidgetBlueprint)
	{
		Response->SetStringField(TEXT("error"), FString::Printf(TEXT("Failed to load Widget Blueprint: %s"), *BlueprintPath));
		return Response;
	}

	// Create Button widget
	UButton* Button = NewObject<UButton>(WidgetBlueprint->GeneratedClass->GetDefaultObject(), UButton::StaticClass(), *WidgetName);
	if (!Button)
	{
		Response->SetStringField(TEXT("error"), TEXT("Failed to create Button widget"));
		return Response;
	}

	// Set button text
	UTextBlock* ButtonTextBlock = NewObject<UTextBlock>(Button, UTextBlock::StaticClass(), *(WidgetName + TEXT("_Text")));
	if (ButtonTextBlock)
	{
		ButtonTextBlock->SetText(FText::FromString(ButtonText));
		Button->AddChild(ButtonTextBlock);
	}

	// Get canvas panel and add button
	UCanvasPanel* RootCanvas = Cast<UCanvasPanel>(WidgetBlueprint->WidgetTree->RootWidget);
	if (!RootCanvas)
	{
		Response->SetStringField(TEXT("error"), TEXT("Root widget is not a Canvas Panel"));
		return Response;
	}

	// Add to canvas and set position
	UCanvasPanelSlot* ButtonSlot = RootCanvas->AddChildToCanvas(Button);
	if (ButtonSlot)
	{
		const TArray<TSharedPtr<FJsonValue>>* Position;
		if (Params->TryGetArrayField(TEXT("position"), Position) && Position->Num() >= 2)
		{
			FVector2D Pos(
				(*Position)[0]->AsNumber(),
				(*Position)[1]->AsNumber()
			);
			ButtonSlot->SetPosition(Pos);
		}
	}

	// Save the Widget Blueprint
	FKismetEditorUtilities::CompileBlueprint(WidgetBlueprint);
	UEditorAssetLibrary::SaveAsset(BlueprintPath, false);

	Response->SetBoolField(TEXT("success"), true);
	Response->SetStringField(TEXT("widget_name"), WidgetName);
	return Response;
}

TSharedPtr<FJsonObject> FUnrealMCPUMGCommands::HandleBindWidgetEvent(const TSharedPtr<FJsonObject>& Params)
{
	TSharedPtr<FJsonObject> Response = MakeShared<FJsonObject>();

	// Get required parameters
	FString BlueprintName;
	if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
	{
		Response->SetStringField(TEXT("error"), TEXT("Missing blueprint_name parameter"));
		return Response;
	}

	FString WidgetName;
	if (!Params->TryGetStringField(TEXT("widget_name"), WidgetName))
	{
		Response->SetStringField(TEXT("error"), TEXT("Missing widget_name parameter"));
		return Response;
	}

	FString EventName;
	if (!Params->TryGetStringField(TEXT("event_name"), EventName))
	{
		Response->SetStringField(TEXT("error"), TEXT("Missing event_name parameter"));
		return Response;
	}

	// Load the Widget Blueprint
	const FString BlueprintPath = FString::Printf(TEXT("/Game/Widgets/%s.%s"), *BlueprintName, *BlueprintName);
	UWidgetBlueprint* WidgetBlueprint = Cast<UWidgetBlueprint>(UEditorAssetLibrary::LoadAsset(BlueprintPath));
	if (!WidgetBlueprint)
	{
		Response->SetStringField(TEXT("error"), FString::Printf(TEXT("Failed to load Widget Blueprint: %s"), *BlueprintPath));
		return Response;
	}

	// Create the event graph if it doesn't exist
	UEdGraph* EventGraph = FBlueprintEditorUtils::FindEventGraph(WidgetBlueprint);
	if (!EventGraph)
	{
		Response->SetStringField(TEXT("error"), TEXT("Failed to find or create event graph"));
		return Response;
	}

	// Find the widget in the blueprint
	UWidget* Widget = WidgetBlueprint->WidgetTree->FindWidget(*WidgetName);
	if (!Widget)
	{
		Response->SetStringField(TEXT("error"), FString::Printf(TEXT("Failed to find widget: %s"), *WidgetName));
		return Response;
	}

	// Create the event node (e.g., OnClicked for buttons)
	UK2Node_Event* EventNode = nullptr;

	// Find existing nodes first
	TArray<UK2Node_Event*> AllEventNodes;
	FBlueprintEditorUtils::GetAllNodesOfClass<UK2Node_Event>(WidgetBlueprint, AllEventNodes);

	for (UK2Node_Event* Node : AllEventNodes)
	{
		if (Node->CustomFunctionName == FName(*EventName) && Node->EventReference.GetMemberParentClass() == Widget->GetClass())
		{
			EventNode = Node;
			break;
		}
	}

	// If no existing node, create a new one
	if (!EventNode)
	{
		// Calculate position - place it below existing nodes
		float MaxHeight = 0.0f;
		for (UEdGraphNode* Node : EventGraph->Nodes)
		{
			MaxHeight = FMath::Max(MaxHeight, Node->NodePosY);
		}

		const FVector2D NodePos(200, MaxHeight + 200);

		// Call CreateNewBoundEventForClass, which returns void, so we can't capture the return value directly
		// We'll need to find the node after creating it
		FKismetEditorUtilities::CreateNewBoundEventForClass(
			Widget->GetClass(),
			FName(*EventName),
			WidgetBlueprint,
			nullptr  // We don't need a specific property binding
		);

		// Now find the newly created node
		TArray<UK2Node_Event*> UpdatedEventNodes;
		FBlueprintEditorUtils::GetAllNodesOfClass<UK2Node_Event>(WidgetBlueprint, UpdatedEventNodes);

		for (UK2Node_Event* Node : UpdatedEventNodes)
		{
			if (Node->CustomFunctionName == FName(*EventName) && Node->EventReference.GetMemberParentClass() == Widget->GetClass())
			{
				EventNode = Node;

				// Set position of the node
				EventNode->NodePosX = NodePos.X;
				EventNode->NodePosY = NodePos.Y;

				break;
			}
		}
	}

	if (!EventNode)
	{
		Response->SetStringField(TEXT("error"), TEXT("Failed to create event node"));
		return Response;
	}

	// Save the Widget Blueprint
	FKismetEditorUtilities::CompileBlueprint(WidgetBlueprint);
	UEditorAssetLibrary::SaveAsset(BlueprintPath, false);

	Response->SetBoolField(TEXT("success"), true);
	Response->SetStringField(TEXT("event_name"), EventName);
	return Response;
}

TSharedPtr<FJsonObject> FUnrealMCPUMGCommands::HandleSetTextBlockBinding(const TSharedPtr<FJsonObject>& Params)
{
	TSharedPtr<FJsonObject> Response = MakeShared<FJsonObject>();

	// Get required parameters
	FString BlueprintName;
	if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
	{
		Response->SetStringField(TEXT("error"), TEXT("Missing blueprint_name parameter"));
		return Response;
	}

	FString WidgetName;
	if (!Params->TryGetStringField(TEXT("widget_name"), WidgetName))
	{
		Response->SetStringField(TEXT("error"), TEXT("Missing widget_name parameter"));
		return Response;
	}

	FString BindingName;
	if (!Params->TryGetStringField(TEXT("binding_name"), BindingName))
	{
		Response->SetStringField(TEXT("error"), TEXT("Missing binding_name parameter"));
		return Response;
	}

	// Load the Widget Blueprint
	const FString BlueprintPath = FString::Printf(TEXT("/Game/Widgets/%s.%s"), *BlueprintName, *BlueprintName);
	UWidgetBlueprint* WidgetBlueprint = Cast<UWidgetBlueprint>(UEditorAssetLibrary::LoadAsset(BlueprintPath));
	if (!WidgetBlueprint)
	{
		Response->SetStringField(TEXT("error"), FString::Printf(TEXT("Failed to load Widget Blueprint: %s"), *BlueprintPath));
		return Response;
	}

	// Create a variable for binding if it doesn't exist
	FBlueprintEditorUtils::AddMemberVariable(
		WidgetBlueprint,
		FName(*BindingName),
		FEdGraphPinType(UEdGraphSchema_K2::PC_Text, NAME_None, nullptr, EPinContainerType::None, false, FEdGraphTerminalType())
	);

	// Find the TextBlock widget
	UTextBlock* TextBlock = Cast<UTextBlock>(WidgetBlueprint->WidgetTree->FindWidget(FName(*WidgetName)));
	if (!TextBlock)
	{
		Response->SetStringField(TEXT("error"), FString::Printf(TEXT("Failed to find TextBlock widget: %s"), *WidgetName));
		return Response;
	}

	// Create binding function
	const FString FunctionName = FString::Printf(TEXT("Get%s"), *BindingName);
	UEdGraph* FuncGraph = FBlueprintEditorUtils::CreateNewGraph(
		WidgetBlueprint,
		FName(*FunctionName),
		UEdGraph::StaticClass(),
		UEdGraphSchema_K2::StaticClass()
	);

	if (FuncGraph)
	{
		// Add the function to the blueprint with proper template parameter
		// Template requires null for last parameter when not using a signature-source
		FBlueprintEditorUtils::AddFunctionGraph<UClass>(WidgetBlueprint, FuncGraph, false, nullptr);

		// Create entry node
		UK2Node_FunctionEntry* EntryNode = nullptr;

		// Create entry node - use the API that exists in UE 5.5
		EntryNode = NewObject<UK2Node_FunctionEntry>(FuncGraph);
		FuncGraph->AddNode(EntryNode, false, false);
		EntryNode->NodePosX = 0;
		EntryNode->NodePosY = 0;
		EntryNode->FunctionReference.SetExternalMember(FName(*FunctionName), WidgetBlueprint->GeneratedClass);
		EntryNode->AllocateDefaultPins();

		// Create get variable node
		UK2Node_VariableGet* GetVarNode = NewObject<UK2Node_VariableGet>(FuncGraph);
		GetVarNode->VariableReference.SetSelfMember(FName(*BindingName));
		FuncGraph->AddNode(GetVarNode, false, false);
		GetVarNode->NodePosX = 200;
		GetVarNode->NodePosY = 0;
		GetVarNode->AllocateDefaultPins();

		// Connect nodes
		UEdGraphPin* EntryThenPin = EntryNode->FindPin(UEdGraphSchema_K2::PN_Then);
		UEdGraphPin* GetVarOutPin = GetVarNode->FindPin(UEdGraphSchema_K2::PN_ReturnValue);
		if (EntryThenPin && GetVarOutPin)
		{
			EntryThenPin->MakeLinkTo(GetVarOutPin);
		}
	}

	// Save the Widget Blueprint
	FKismetEditorUtilities::CompileBlueprint(WidgetBlueprint);
	UEditorAssetLibrary::SaveAsset(BlueprintPath, false);

	Response->SetBoolField(TEXT("success"), true);
	Response->SetStringField(TEXT("binding_name"), BindingName);
	return Response;
}

TSharedPtr<FJsonObject> FUnrealMCPUMGCommands::HandleWidgetAddChild(const TSharedPtr<FJsonObject>& Params)
{
	FString BlueprintPath;
	FString Error;
	UWidgetBlueprint* WidgetBlueprint = LoadWidgetBlueprintFromParams(Params, BlueprintPath, Error);
	if (!WidgetBlueprint)
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(Error);
	}

	FString ChildClass;
	if (!Params->TryGetStringField(TEXT("child_class"), ChildClass))
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'child_class' parameter"));
	}

	FString ChildName;
	if (!Params->TryGetStringField(TEXT("child_name"), ChildName))
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'child_name' parameter"));
	}

	UClass* WidgetClass = ResolveWidgetClass(ChildClass);
	if (!WidgetClass)
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Unsupported widget child_class '%s'"), *ChildClass));
	}

	if (!WidgetBlueprint->WidgetTree)
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Widget Blueprint has no WidgetTree"));
	}

	UWidget* ExistingWidget = WidgetBlueprint->WidgetTree->FindWidget(FName(*ChildName));
	UWidget* NewWidget = ExistingWidget;
	if (!NewWidget)
	{
		NewWidget = WidgetBlueprint->WidgetTree->ConstructWidget<UWidget>(WidgetClass, FName(*ChildName));
	}
	if (!NewWidget)
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Failed to construct widget '%s'"), *ChildName));
	}
	NewWidget->bIsVariable = true;

	FString ParentName;
	Params->TryGetStringField(TEXT("parent_name"), ParentName);

	if (ParentName.IsEmpty())
	{
		if (!WidgetBlueprint->WidgetTree->RootWidget)
		{
			WidgetBlueprint->WidgetTree->RootWidget = NewWidget;
		}
		else if (WidgetBlueprint->WidgetTree->RootWidget != NewWidget)
		{
			UPanelWidget* RootPanel = Cast<UPanelWidget>(WidgetBlueprint->WidgetTree->RootWidget);
			if (!RootPanel)
			{
				return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Root widget exists but is not a panel; provide a panel parent_name"));
			}
			if (!NewWidget->Slot)
			{
				RootPanel->AddChild(NewWidget);
			}
		}
	}
	else
	{
		UWidget* ParentWidget = WidgetBlueprint->WidgetTree->FindWidget(FName(*ParentName));
		UPanelWidget* ParentPanel = Cast<UPanelWidget>(ParentWidget);
		if (!ParentPanel)
		{
			return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Parent widget '%s' not found or is not a panel"), *ParentName));
		}
		if (!NewWidget->Slot)
		{
			ParentPanel->AddChild(NewWidget);
		}
	}

	MarkWidgetBlueprintModified(WidgetBlueprint);

	TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
	ResultObj->SetBoolField(TEXT("success"), true);
	ResultObj->SetStringField(TEXT("widget_blueprint_path"), BlueprintPath);
	ResultObj->SetStringField(TEXT("child_name"), NewWidget->GetName());
	ResultObj->SetStringField(TEXT("child_class"), NewWidget->GetClass()->GetName());
	ResultObj->SetBoolField(TEXT("is_variable"), NewWidget->bIsVariable);
	return ResultObj;
}

TSharedPtr<FJsonObject> FUnrealMCPUMGCommands::HandleWidgetSetProperty(const TSharedPtr<FJsonObject>& Params)
{
	FString BlueprintPath;
	FString Error;
	UWidgetBlueprint* WidgetBlueprint = LoadWidgetBlueprintFromParams(Params, BlueprintPath, Error);
	if (!WidgetBlueprint)
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(Error);
	}

	FString WidgetName;
	if (!Params->TryGetStringField(TEXT("widget_name"), WidgetName))
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'widget_name' parameter"));
	}

	FString PropertyName;
	if (!Params->TryGetStringField(TEXT("property_name"), PropertyName))
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'property_name' parameter"));
	}

	FString PropertyValue;
	if (!Params->TryGetStringField(TEXT("property_value"), PropertyValue))
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'property_value' parameter"));
	}

	UWidget* Widget = WidgetBlueprint->WidgetTree ? WidgetBlueprint->WidgetTree->FindWidget(FName(*WidgetName)) : nullptr;
	if (!Widget)
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Widget '%s' not found"), *WidgetName));
	}

	bool bHandled = true;
	if (PropertyName.Equals(TEXT("Text"), ESearchCase::IgnoreCase))
	{
		if (UTextBlock* TextBlock = Cast<UTextBlock>(Widget))
		{
			TextBlock->SetText(FText::FromString(PropertyValue));
		}
		else
		{
			bHandled = false;
		}
	}
	else if (PropertyName.Equals(TEXT("FontSize"), ESearchCase::IgnoreCase) ||
			 PropertyName.Equals(TEXT("Font.Size"), ESearchCase::IgnoreCase))
	{
		if (UTextBlock* TextBlock = Cast<UTextBlock>(Widget))
		{
			FSlateFontInfo Font = TextBlock->GetFont();
			Font.Size = FCString::Atoi(*PropertyValue);
			TextBlock->SetFont(Font);
		}
		else
		{
			bHandled = false;
		}
	}
	else if (PropertyName.Equals(TEXT("ColorAndOpacity"), ESearchCase::IgnoreCase))
	{
		const FLinearColor Color = ParseLinearColor(PropertyValue);
		if (UTextBlock* TextBlock = Cast<UTextBlock>(Widget))
		{
			TextBlock->SetColorAndOpacity(FSlateColor(Color));
		}
		else if (UImage* Image = Cast<UImage>(Widget))
		{
			Image->SetColorAndOpacity(Color);
		}
		else
		{
			bHandled = false;
		}
	}
	else if (PropertyName.Equals(TEXT("BrushTintColor"), ESearchCase::IgnoreCase))
	{
		if (UImage* Image = Cast<UImage>(Widget))
		{
			Image->SetColorAndOpacity(ParseLinearColor(PropertyValue));
		}
		else
		{
			bHandled = false;
		}
	}
	else if (PropertyName.Equals(TEXT("BrushSize"), ESearchCase::IgnoreCase))
	{
		if (UImage* Image = Cast<UImage>(Widget))
		{
			Image->SetDesiredSizeOverride(ParseVector2D(PropertyValue));
		}
		else
		{
			bHandled = false;
		}
	}
	else if (PropertyName.Equals(TEXT("Percent"), ESearchCase::IgnoreCase))
	{
		if (UProgressBar* ProgressBar = Cast<UProgressBar>(Widget))
		{
			ProgressBar->SetPercent(FCString::Atof(*PropertyValue));
		}
		else
		{
			bHandled = false;
		}
	}
	else if (PropertyName.Equals(TEXT("FillColorAndOpacity"), ESearchCase::IgnoreCase))
	{
		if (UProgressBar* ProgressBar = Cast<UProgressBar>(Widget))
		{
			ProgressBar->SetFillColorAndOpacity(ParseLinearColor(PropertyValue));
		}
		else
		{
			bHandled = false;
		}
	}
	else if (PropertyName.Equals(TEXT("Visibility"), ESearchCase::IgnoreCase))
	{
		Widget->SetVisibility(ParseVisibility(PropertyValue));
	}
	else if (PropertyName.Equals(TEXT("RenderTransformAngle"), ESearchCase::IgnoreCase))
	{
		Widget->SetRenderTransformAngle(FCString::Atof(*PropertyValue));
	}
	else
	{
		bHandled = false;
	}

	if (!bHandled)
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Property '%s' is not supported for widget '%s'"), *PropertyName, *WidgetName));
	}

	MarkWidgetBlueprintModified(WidgetBlueprint);

	TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
	ResultObj->SetBoolField(TEXT("success"), true);
	ResultObj->SetStringField(TEXT("widget_name"), WidgetName);
	ResultObj->SetStringField(TEXT("property_name"), PropertyName);
	ResultObj->SetStringField(TEXT("property_value"), PropertyValue);
	return ResultObj;
}

TSharedPtr<FJsonObject> FUnrealMCPUMGCommands::HandleWidgetSetAnchor(const TSharedPtr<FJsonObject>& Params)
{
	FString BlueprintPath;
	FString Error;
	UWidgetBlueprint* WidgetBlueprint = LoadWidgetBlueprintFromParams(Params, BlueprintPath, Error);
	if (!WidgetBlueprint)
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(Error);
	}

	FString WidgetName;
	if (!Params->TryGetStringField(TEXT("widget_name"), WidgetName))
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'widget_name' parameter"));
	}

	UWidget* Widget = WidgetBlueprint->WidgetTree ? WidgetBlueprint->WidgetTree->FindWidget(FName(*WidgetName)) : nullptr;
	if (!Widget)
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Widget '%s' not found"), *WidgetName));
	}

	UCanvasPanelSlot* CanvasSlot = Cast<UCanvasPanelSlot>(Widget->Slot);
	if (!CanvasSlot)
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Widget '%s' is not in a CanvasPanelSlot"), *WidgetName));
	}

	double AnchorMinX = 0.0;
	double AnchorMinY = 0.0;
	double AnchorMaxX = 0.0;
	double AnchorMaxY = 0.0;
	double PositionX = 0.0;
	double PositionY = 0.0;
	double SizeX = 100.0;
	double SizeY = 30.0;
	double AlignmentX = 0.0;
	double AlignmentY = 0.0;

	Params->TryGetNumberField(TEXT("anchor_min_x"), AnchorMinX);
	Params->TryGetNumberField(TEXT("anchor_min_y"), AnchorMinY);
	Params->TryGetNumberField(TEXT("anchor_max_x"), AnchorMaxX);
	Params->TryGetNumberField(TEXT("anchor_max_y"), AnchorMaxY);
	Params->TryGetNumberField(TEXT("position_x"), PositionX);
	Params->TryGetNumberField(TEXT("position_y"), PositionY);
	Params->TryGetNumberField(TEXT("size_x"), SizeX);
	Params->TryGetNumberField(TEXT("size_y"), SizeY);
	Params->TryGetNumberField(TEXT("alignment_x"), AlignmentX);
	Params->TryGetNumberField(TEXT("alignment_y"), AlignmentY);

	CanvasSlot->SetAnchors(FAnchors(
		static_cast<float>(AnchorMinX),
		static_cast<float>(AnchorMinY),
		static_cast<float>(AnchorMaxX),
		static_cast<float>(AnchorMaxY)));
	CanvasSlot->SetPosition(FVector2D(PositionX, PositionY));
	CanvasSlot->SetSize(FVector2D(SizeX, SizeY));
	CanvasSlot->SetAlignment(FVector2D(AlignmentX, AlignmentY));

	MarkWidgetBlueprintModified(WidgetBlueprint);

	TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
	ResultObj->SetBoolField(TEXT("success"), true);
	ResultObj->SetStringField(TEXT("widget_name"), WidgetName);
	ResultObj->SetNumberField(TEXT("position_x"), PositionX);
	ResultObj->SetNumberField(TEXT("position_y"), PositionY);
	ResultObj->SetNumberField(TEXT("size_x"), SizeX);
	ResultObj->SetNumberField(TEXT("size_y"), SizeY);
	return ResultObj;
}

TSharedPtr<FJsonObject> FUnrealMCPUMGCommands::HandleWidgetGetChildren(const TSharedPtr<FJsonObject>& Params)
{
	FString BlueprintPath;
	FString Error;
	UWidgetBlueprint* WidgetBlueprint = LoadWidgetBlueprintFromParams(Params, BlueprintPath, Error);
	if (!WidgetBlueprint)
	{
		return FUnrealMCPCommonUtils::CreateErrorResponse(Error);
	}

	TArray<TSharedPtr<FJsonValue>> Children;
	FString ParentName;
	if (Params->TryGetStringField(TEXT("parent_name"), ParentName) && !ParentName.IsEmpty())
	{
		UWidget* ParentWidget = WidgetBlueprint->WidgetTree ? WidgetBlueprint->WidgetTree->FindWidget(FName(*ParentName)) : nullptr;
		if (UPanelWidget* ParentPanel = Cast<UPanelWidget>(ParentWidget))
		{
			for (int32 Index = 0; Index < ParentPanel->GetChildrenCount(); ++Index)
			{
				AddWidgetInfo(ParentPanel->GetChildAt(Index), Children);
			}
		}
		else
		{
			return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Parent widget '%s' not found or is not a panel"), *ParentName));
		}
	}
	else if (WidgetBlueprint->WidgetTree && WidgetBlueprint->WidgetTree->RootWidget)
	{
		AddWidgetInfo(WidgetBlueprint->WidgetTree->RootWidget, Children);
		if (UPanelWidget* RootPanel = Cast<UPanelWidget>(WidgetBlueprint->WidgetTree->RootWidget))
		{
			for (int32 Index = 0; Index < RootPanel->GetChildrenCount(); ++Index)
			{
				AddWidgetInfo(RootPanel->GetChildAt(Index), Children);
			}
		}
	}

	TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
	ResultObj->SetBoolField(TEXT("success"), true);
	ResultObj->SetStringField(TEXT("widget_blueprint_path"), BlueprintPath);
	ResultObj->SetArrayField(TEXT("children"), Children);
	return ResultObj;
}
