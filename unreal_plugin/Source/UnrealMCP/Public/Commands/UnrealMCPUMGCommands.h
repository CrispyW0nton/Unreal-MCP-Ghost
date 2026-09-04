#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

/**
 * Handles UMG (Widget Blueprint) related MCP commands
 * Responsible for creating and modifying UMG Widget Blueprints,
 * adding widget components, and managing widget instances in the viewport.
 */
class UNREALMCP_API FUnrealMCPUMGCommands
{
public:
    FUnrealMCPUMGCommands();

    /**
     * Handle UMG-related commands
     * @param CommandType - The type of command to handle
     * @param Params - JSON parameters for the command
     * @return JSON response with results or error
     */
    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    /**
     * Create a new UMG Widget Blueprint
     * @param Params - Must include "name" for the blueprint name
     * @return JSON response with the created blueprint details
     */
    TSharedPtr<FJsonObject> HandleCreateUMGWidgetBlueprint(const TSharedPtr<FJsonObject>& Params);

    /**
     * Add a Text Block widget to a UMG Widget Blueprint
     * @param Params - Must include:
     *                "blueprint_name" - Name of the target Widget Blueprint
     *                "widget_name" - Name for the new Text Block
     *                "text" - Initial text content (optional)
     *                "position" - [X, Y] position in the canvas (optional)
     * @return JSON response with the added widget details
     */
    TSharedPtr<FJsonObject> HandleAddTextBlockToWidget(const TSharedPtr<FJsonObject>& Params);

    /**
     * Add a widget instance to the game viewport
     * @param Params - Must include:
     *                "blueprint_name" - Name of the Widget Blueprint to instantiate
     *                "z_order" - Z-order for widget display (optional)
     * @return JSON response with the widget instance details
     */
    TSharedPtr<FJsonObject> HandleAddWidgetToViewport(const TSharedPtr<FJsonObject>& Params);

    /**
     * Add a Button widget to a UMG Widget Blueprint
     * @param Params - Must include:
     *                "blueprint_name" - Name of the target Widget Blueprint
     *                "widget_name" - Name for the new Button
     *                "text" - Button text
     *                "position" - [X, Y] position in the canvas
     * @return JSON response with the added widget details
     */
    TSharedPtr<FJsonObject> HandleAddButtonToWidget(const TSharedPtr<FJsonObject>& Params);

    /**
     * Bind an event to a widget (e.g. button click)
     * @param Params - Must include:
     *                "blueprint_name" - Name of the target Widget Blueprint
     *                "widget_name" - Name of the widget to bind
     *                "event_name" - Name of the event to bind
     * @return JSON response with the binding details
     */
    TSharedPtr<FJsonObject> HandleBindWidgetEvent(const TSharedPtr<FJsonObject>& Params);

    /**
     * Create (or reuse) a component-bound event node for a named sub-widget,
     * e.g. BTN_NEWGAME's OnHovered. Unlike bind_widget_event this resolves the
     * widget blueprint by full path, marks the sub-widget as a variable, and
     * binds the event to that specific widget property so multiple widgets of
     * the same class get distinct event nodes.
     * @param Params - Must include:
     *                "widget_blueprint_path" - Full object path of the Widget Blueprint
     *                "widget_name" - Named sub-widget in the tree (e.g. BTN_EXIT)
     *                "event_name" - Delegate property name (OnClicked/OnHovered/OnUnhovered/...)
     * @return JSON response with the bound event node GUID for graph wiring
     */
    TSharedPtr<FJsonObject> HandleBindWidgetComponentEvent(const TSharedPtr<FJsonObject>& Params);

    /**
     * Set up text block binding for dynamic updates
     * @param Params - Must include:
     *                "blueprint_name" - Name of the target Widget Blueprint
     *                "widget_name" - Name of the widget to bind
     *                "binding_name" - Name of the binding to set up
     * @return JSON response with the binding details
     */
    TSharedPtr<FJsonObject> HandleSetTextBlockBinding(const TSharedPtr<FJsonObject>& Params);

    /** Generic widget tree child creation for Widget Blueprints. */
    TSharedPtr<FJsonObject> HandleWidgetAddChild(const TSharedPtr<FJsonObject>& Params);

    /** Set common widget properties through explicit UMG APIs. */
    TSharedPtr<FJsonObject> HandleWidgetSetProperty(const TSharedPtr<FJsonObject>& Params);

    /** Set CanvasPanelSlot anchors, position, size, and alignment. */
    TSharedPtr<FJsonObject> HandleWidgetSetAnchor(const TSharedPtr<FJsonObject>& Params);

    /** List widget tree children and slot information. */
    TSharedPtr<FJsonObject> HandleWidgetGetChildren(const TSharedPtr<FJsonObject>& Params);

    /** Add or replace a Widget Blueprint delegate runtime binding. */
    TSharedPtr<FJsonObject> HandleAddWidgetBinding(const TSharedPtr<FJsonObject>& Params);
};
