"""
UMG Tools - Widget Blueprint creation and manipulation.
Covers Chapter on UI/UMG from the Blueprint book.
"""
import logging
from typing import Dict, List, Any
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def _retired_umg_route(tool_name: str, replacement: str) -> Dict[str, Any]:
    return {
        "success": False,
        "status": "retired_route",
        "tool": tool_name,
        "message": (
            f"{tool_name} no longer calls its retired native bridge route. "
            f"{replacement}"
        ),
    }


def register_umg_tools(mcp: FastMCP):
    def _structured_umg_result(
        raw: Dict[str, Any],
        *,
        stage: str,
        message: str,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        raw = raw or {}
        error_message = raw.get("error") or raw.get("message") or ""
        success = raw.get("success") is not False and raw.get("status") != "error" and not raw.get("error")
        return {
            "success": success,
            "stage": stage,
            "message": message if success else (error_message or f"{stage} failed"),
            "inputs": inputs,
            "outputs": {
                key: value
                for key, value in raw.items()
                if key not in {"success", "status", "message", "error"}
            } if success else {},
            "warnings": [],
            "errors": [] if success else [error_message or f"{stage} failed"],
            "log_tail": [],
        }

    @mcp.tool()
    def create_umg_widget_blueprint(
        ctx: Context,
        widget_name: str,
        parent_class: str = "UserWidget",
        path: str = "/Game/UI"
    ) -> Dict[str, Any]:
        """Create a new UMG Widget Blueprint.

        Args:
            widget_name: Widget asset name (e.g., "WBP_HUD", "WBP_MainMenu")
            parent_class: Parent class (default: "UserWidget")
            path: Content browser path (default: "/Game/UI")

        KB: see knowledge_base/06_UI_UMG_SYSTEMS.md#overview
        Example:
            create_umg_widget_blueprint(widget_name="/Game/MCP_Test/WBP_Example")"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("create_umg_widget_blueprint", {
                "widget_name": widget_name,
                "parent_class": parent_class,
                "path": path
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_text_block_to_widget(
        ctx: Context,
        widget_name: str,
        text_block_name: str,
        text: str = "",
        position: List[float] = [0.0, 0.0],
        size: List[float] = [200.0, 50.0],
        font_size: int = 12,
        color: List[float] = [1.0, 1.0, 1.0, 1.0]
    ) -> Dict[str, Any]:
        """Add a Text Block to a Widget Blueprint.

        Args:
            widget_name: Widget Blueprint name
            text_block_name: Component name for the text block
            text: Display text
            position: [X, Y] canvas position
            size: [Width, Height]
            font_size: Font size in points
            color: [R, G, B, A] (0.0-1.0)

        KB: see knowledge_base/06_UI_UMG_SYSTEMS.md#overview
        Example:
            add_text_block_to_widget(widget_name="/Game/MCP_Test/WBP_Example", text_block_name="ExampleName")"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_text_block_to_widget", {
                "widget_name": widget_name,
                "text_block_name": text_block_name,
                "text": text,
                "position": position,
                "size": size,
                "font_size": font_size,
                "color": color
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_button_to_widget(
        ctx: Context,
        widget_name: str,
        button_name: str,
        text: str = "",
        position: List[float] = [0.0, 0.0],
        size: List[float] = [200.0, 50.0],
        font_size: int = 12,
        color: List[float] = [1.0, 1.0, 1.0, 1.0],
        background_color: List[float] = [0.1, 0.1, 0.1, 1.0]
    ) -> Dict[str, Any]:
        """Add a Button to a Widget Blueprint.

        Args:
            widget_name: Widget Blueprint name
            button_name: Component name for the button
            text: Button label
            position: [X, Y] canvas position
            size: [Width, Height]
            font_size: Font size
            color: [R,G,B,A] text color
            background_color: [R,G,B,A] button background color

        KB: see knowledge_base/06_UI_UMG_SYSTEMS.md#overview
        Example:
            add_button_to_widget(widget_name="/Game/MCP_Test/WBP_Example", button_name="ExampleName")"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_button_to_widget", {
                "widget_name": widget_name,
                "button_name": button_name,
                "text": text,
                "position": position,
                "size": size,
                "font_size": font_size,
                "color": color,
                "background_color": background_color
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def umg_add_widget_binding(
        ctx: Context,
        widget: str,
        property_path: str,
        binding_target: str,
        binding_kind: str = "function",
    ) -> Dict[str, Any]:
        """Add or replace a Widget Blueprint property binding.

        property_path uses '<WidgetName>.<PropertyName>' such as
        'HealthText.Text' or 'HealthBar.Percent'. binding_target is the
        Blueprint function or property name that should drive the binding.

        Args:
            widget: Widget Blueprint asset name or path.
            property_path: Widget tree property path, '<WidgetName>.<PropertyName>'.
            binding_target: Blueprint function/property that supplies the value.
            binding_kind: 'function' or 'property'. Default 'function'.

        KB: see knowledge_base/06_UI_UMG_SYSTEMS.md#overview
        Example:
            umg_add_widget_binding(widget="/Game/MCP_Test/WBP_Example", property_path="HealthText.Text", binding_target="GetHealthText")
        """
        from unreal_mcp_server import get_unreal_connection
        inputs = {
            "widget": widget,
            "property_path": property_path,
            "binding_target": binding_target,
            "binding_kind": binding_kind,
        }
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {
                    "success": False,
                    "stage": "umg_add_widget_binding",
                    "message": "Not connected to Unreal Engine",
                    "inputs": inputs,
                    "outputs": {},
                    "warnings": [],
                    "errors": ["Not connected to Unreal Engine"],
                    "log_tail": [],
                }
            raw = unreal.send_command("umg_add_widget_binding", {
                "widget_blueprint_path": widget,
                "property_path": property_path,
                "binding_target": binding_target,
                "binding_kind": binding_kind,
            }) or {}
            return _structured_umg_result(
                raw,
                stage="umg_add_widget_binding",
                message=f"Bound '{property_path}' on '{widget}' to '{binding_target}'",
                inputs=inputs,
            )
        except Exception as e:
            return {
                "success": False,
                "stage": "umg_add_widget_binding",
                "message": str(e),
                "inputs": inputs,
                "outputs": {},
                "warnings": [],
                "errors": [str(e)],
                "log_tail": [],
            }

    @mcp.tool()
    def bind_widget_event(
        ctx: Context,
        widget_name: str,
        widget_component_name: str,
        event_name: str,
        function_name: str = ""
    ) -> Dict[str, Any]:
        """Bind a widget event (e.g., OnClicked) to a function.

        Args:
            widget_name: Widget Blueprint name
            widget_component_name: Component name (e.g., button name)
            event_name: Event to bind ("OnClicked", "OnHovered", "OnUnhovered",
                        "OnPressed", "OnReleased")
            function_name: Target function name (auto-generated if empty)

        KB: see knowledge_base/06_UI_UMG_SYSTEMS.md#overview
        Example:
            bind_widget_event(widget_name="/Game/MCP_Test/WBP_Example", widget_component_name="/Game/MCP_Test/WBP_Example", event_name="ExampleName")"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            if not function_name:
                function_name = f"{widget_component_name}_{event_name}"
            return unreal.send_command("bind_widget_event", {
                "widget_name": widget_name,
                "widget_component_name": widget_component_name,
                "event_name": event_name,
                "function_name": function_name
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_widget_to_viewport(
        ctx: Context,
        widget_name: str,
        z_order: int = 0
    ) -> Dict[str, Any]:
        """Instantiate a Widget Blueprint and add it to the game viewport.

        Args:
            widget_name: Widget Blueprint name
            z_order: Rendering order (higher = on top)

        KB: see knowledge_base/06_UI_UMG_SYSTEMS.md#overview
        Example:
            add_widget_to_viewport(widget_name="/Game/MCP_Test/WBP_Example")"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_widget_to_viewport", {
                "widget_name": widget_name,
                "z_order": z_order
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def set_text_block_binding(
        ctx: Context,
        widget_name: str,
        text_block_name: str,
        binding_property: str,
        binding_type: str = "Text"
    ) -> Dict[str, Any]:
        """Set up a dynamic property binding on a Text Block widget.

        Args:
            widget_name: Widget Blueprint name
            text_block_name: Text Block component name
            binding_property: Blueprint variable to bind to
            binding_type: "Text", "Visibility", "ColorAndOpacity"

        KB: see knowledge_base/06_UI_UMG_SYSTEMS.md#overview
        Example:
            set_text_block_binding(widget_name="/Game/MCP_Test/WBP_Example", text_block_name="ExampleName", binding_property="ExampleName")"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("set_text_block_binding", {
                "widget_name": widget_name,
                "text_block_name": text_block_name,
                "binding_property": binding_property,
                "binding_type": binding_type
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_progress_bar_to_widget(
        ctx: Context,
        widget_name: str,
        progress_bar_name: str,
        position: List[float] = [0.0, 0.0],
        size: List[float] = [300.0, 25.0],
        fill_color: List[float] = [0.0, 1.0, 0.0, 1.0],
        background_color: List[float] = [0.2, 0.2, 0.2, 1.0],
        percent: float = 1.0
    ) -> Dict[str, Any]:
        """Add a Progress Bar widget (useful for health/ammo bars).

        Args:
            widget_name: Widget Blueprint name
            progress_bar_name: Component name
            position: [X, Y] position
            size: [Width, Height]
            fill_color: [R,G,B,A] fill color
            background_color: [R,G,B,A] background
            percent: Initial fill (0.0-1.0)

        KB: see knowledge_base/06_UI_UMG_SYSTEMS.md#overview
        Example:
            add_progress_bar_to_widget(widget_name="/Game/MCP_Test/WBP_Example", progress_bar_name="ExampleName")"""
        return _retired_umg_route(
            "add_progress_bar_to_widget",
            "Use create_umg_widget_blueprint plus the generic widget tree tools once widget_add_child is part of the committed plugin route set.",
        )

    @mcp.tool()
    def add_image_to_widget(
        ctx: Context,
        widget_name: str,
        image_name: str,
        texture_path: str = "",
        position: List[float] = [0.0, 0.0],
        size: List[float] = [100.0, 100.0],
        color: List[float] = [1.0, 1.0, 1.0, 1.0]
    ) -> Dict[str, Any]:
        """Add an Image widget to a Widget Blueprint.

        Args:
            widget_name: Widget Blueprint name
            image_name: Component name
            texture_path: Texture asset path (optional)
            position: [X, Y] position
            size: [Width, Height]
            color: [R,G,B,A] tint color

        KB: see knowledge_base/06_UI_UMG_SYSTEMS.md#overview
        Example:
            add_image_to_widget(widget_name="/Game/MCP_Test/WBP_Example", image_name="ExampleName")"""
        return _retired_umg_route(
            "add_image_to_widget",
            "Use create_umg_widget_blueprint plus the generic widget tree tools once widget_add_child is part of the committed plugin route set.",
        )

    # ── Advanced UMG Widgets (Ch. 7, 8, 11, 20) ───────────────────────────────

    @mcp.tool()
    def add_horizontal_box_to_widget(
        ctx: Context,
        widget_name: str,
        box_name: str,
        position: List[float] = [0.0, 0.0],
        size: List[float] = [400.0, 60.0],
        anchor_preset: str = "TopCenter",
        size_to_content: bool = False
    ) -> Dict[str, Any]:
        """Add a Horizontal Box layout container to a Widget Blueprint.

        From Ch. 11 (Round Transition screen): Horizontal Box arranges child widgets
        horizontally (left to right). Used for side-by-side text + values.

        Args:
            widget_name: Widget Blueprint name
            box_name: Component name for the Horizontal Box
            position: [X, Y] position
            size: [Width, Height]
            anchor_preset: UMG anchor preset ("TopLeft", "TopCenter", "Center", etc.)
            size_to_content: Auto-size to fit children

        KB: see knowledge_base/06_UI_UMG_SYSTEMS.md#overview
        Example:
            add_horizontal_box_to_widget(widget_name="/Game/MCP_Test/WBP_Example", box_name="ExampleName")"""
        return _retired_umg_route(
            "add_horizontal_box_to_widget",
            "Use create_umg_widget_blueprint plus the generic widget tree tools once widget_add_child is part of the committed plugin route set.",
        )

    @mcp.tool()
    def add_vertical_box_to_widget(
        ctx: Context,
        widget_name: str,
        box_name: str,
        position: List[float] = [0.0, 0.0],
        size: List[float] = [200.0, 400.0],
        anchor_preset: str = "TopLeft",
        size_to_content: bool = False
    ) -> Dict[str, Any]:
        """Add a Vertical Box layout container to a Widget Blueprint.

        Vertical Box arranges child widgets vertically (top to bottom).
        Perfect for stacking buttons, labels, and stats in a menu.

        Args:
            widget_name: Widget Blueprint name
            box_name: Component name for the Vertical Box
            position: [X, Y] position
            size: [Width, Height]
            anchor_preset: UMG anchor preset
            size_to_content: Auto-size to fit children

        KB: see knowledge_base/06_UI_UMG_SYSTEMS.md#overview
        Example:
            add_vertical_box_to_widget(widget_name="/Game/MCP_Test/WBP_Example", box_name="ExampleName")"""
        return _retired_umg_route(
            "add_vertical_box_to_widget",
            "Use create_umg_widget_blueprint plus the generic widget tree tools once widget_add_child is part of the committed plugin route set.",
        )

    @mcp.tool()
    def add_canvas_panel_to_widget(
        ctx: Context,
        widget_name: str,
        panel_name: str = "CanvasPanel"
    ) -> Dict[str, Any]:
        """Add a Canvas Panel to a Widget Blueprint (free-placement layout).

        From Ch. 7: Canvas Panel allows absolute positioning of child widgets
        (drag and drop anywhere). It's the default root panel for most UMG widgets.

        Args:
            widget_name: Widget Blueprint name
            panel_name: Component name for the Canvas Panel

        KB: see knowledge_base/06_UI_UMG_SYSTEMS.md#overview
        Example:
            add_canvas_panel_to_widget(widget_name="/Game/MCP_Test/WBP_Example")"""
        return _retired_umg_route(
            "add_canvas_panel_to_widget",
            "Use create_umg_widget_blueprint for the default root canvas, or the generic widget tree tools once widget_add_child is part of the committed plugin route set.",
        )

    @mcp.tool()
    def add_slider_to_widget(
        ctx: Context,
        widget_name: str,
        slider_name: str,
        position: List[float] = [0.0, 0.0],
        size: List[float] = [200.0, 40.0],
        min_value: float = 0.0,
        max_value: float = 1.0,
        default_value: float = 0.5,
        step_size: float = 0.01
    ) -> Dict[str, Any]:
        """Add a Slider widget for adjustable values (audio volume, sensitivity, etc.).

        Args:
            widget_name: Widget Blueprint name
            slider_name: Component name
            position: [X, Y] position
            size: [Width, Height]
            min_value: Minimum slider value
            max_value: Maximum slider value
            default_value: Initial slider value
            step_size: Increment step

        KB: see knowledge_base/06_UI_UMG_SYSTEMS.md#overview
        Example:
            add_slider_to_widget(widget_name="/Game/MCP_Test/WBP_Example", slider_name="ExampleName")"""
        return _retired_umg_route(
            "add_slider_to_widget",
            "Use create_umg_widget_blueprint plus the generic widget tree tools once widget_add_child is part of the committed plugin route set.",
        )

    @mcp.tool()
    def add_checkbox_to_widget(
        ctx: Context,
        widget_name: str,
        checkbox_name: str,
        label_text: str = "",
        position: List[float] = [0.0, 0.0],
        is_checked: bool = False
    ) -> Dict[str, Any]:
        """Add a Checkbox widget for boolean toggles in menus.

        Args:
            widget_name: Widget Blueprint name
            checkbox_name: Component name
            label_text: Optional label text next to the checkbox
            position: [X, Y] position
            is_checked: Initial checked state

        KB: see knowledge_base/06_UI_UMG_SYSTEMS.md#overview
        Example:
            add_checkbox_to_widget(widget_name="/Game/MCP_Test/WBP_Example", checkbox_name="ExampleName")"""
        return _retired_umg_route(
            "add_checkbox_to_widget",
            "Use create_umg_widget_blueprint plus the generic widget tree tools once widget_add_child is part of the committed plugin route set.",
        )

    @mcp.tool()
    def add_named_slot_to_widget(
        ctx: Context,
        widget_name: str,
        slot_name: str,
        position: List[float] = [0.0, 0.0],
        size: List[float] = [200.0, 200.0]
    ) -> Dict[str, Any]:
        """Add a Named Slot placeholder to a Widget Blueprint.

        Named Slots allow child widget content injection when the widget is
        used as a parent. Essential for reusable frame/container widgets.

        Args:
            widget_name: Widget Blueprint name
            slot_name: Named slot identifier
            position: [X, Y] position
            size: [Width, Height]

        KB: see knowledge_base/06_UI_UMG_SYSTEMS.md#overview
        Example:
            add_named_slot_to_widget(widget_name="/Game/MCP_Test/WBP_Example", slot_name="ExampleName")"""
        return _retired_umg_route(
            "add_named_slot_to_widget",
            "Use create_umg_widget_blueprint plus the generic widget tree tools once widget_add_child is part of the committed plugin route set.",
        )

    @mcp.tool()
    def create_hud_widget(
        ctx: Context,
        widget_name: str = "WBP_HUD",
        health_bar: bool = True,
        stamina_bar: bool = True,
        ammo_counter: bool = True,
        targets_counter: bool = True,
        target_goal_display: bool = True,
        round_display: bool = False,
        folder_path: str = "/Game/UI"
    ) -> Dict[str, Any]:
        """Create a complete HUD Widget Blueprint from Ch. 7.

        Builds a full first-person HUD with health bar, stamina bar, ammo counter,
        and targets-eliminated counter. Each element uses bindings to display
        live player variable values.

        Mirrors the HUD created in Chapters 7-8 of the book:
        - Health/Stamina: Progress Bars with float bindings
        - Ammo: Text Block with integer binding
        - Targets Eliminated / Target Goal: Text Blocks

        Args:
            widget_name: Widget Blueprint name
            health_bar: Include a health progress bar
            stamina_bar: Include a stamina progress bar
            ammo_counter: Include an ammo count text display
            targets_counter: Include a targets eliminated counter
            target_goal_display: Include a target goal counter
            round_display: Include a round number display
            folder_path: Content browser folder

        KB: see knowledge_base/06_UI_UMG_SYSTEMS.md#overview
        Example:
            create_hud_widget()"""
        return _retired_umg_route(
            "create_hud_widget",
            "Use create_umg_widget_blueprint with add_text_block_to_widget and add_button_to_widget, then add progress/image controls after a committed widget tree route lands.",
        )

    @mcp.tool()
    def create_win_menu_widget(
        ctx: Context,
        widget_name: str = "WBP_WinMenu",
        title_text: str = "You Win!",
        title_color: List[float] = [0.0, 0.8, 0.0, 1.0],
        show_restart_button: bool = True,
        show_quit_button: bool = True,
        show_round_info: bool = False,
        folder_path: str = "/Game/UI"
    ) -> Dict[str, Any]:
        """Create a Win/Victory screen Widget Blueprint as described in Ch. 8.

        Creates a UMG Widget with a centered win message and buttons.
        From the book: "You Win!" message, Restart and Quit buttons.

        Args:
            widget_name: Widget Blueprint name
            title_text: Main message (e.g., "You Win!", "Victory!")
            title_color: RGBA color for the title text
            show_restart_button: Include a Restart (reload level) button
            show_quit_button: Include a Quit Game button
            show_round_info: Include current round number display
            folder_path: Content browser folder

        KB: see knowledge_base/06_UI_UMG_SYSTEMS.md#overview
        Example:
            create_win_menu_widget()"""
        return _retired_umg_route(
            "create_win_menu_widget",
            "Use create_umg_widget_blueprint, add_text_block_to_widget, and add_button_to_widget to build the screen with currently routed commands.",
        )

    @mcp.tool()
    def add_widget_animation(
        ctx: Context,
        widget_name: str,
        animation_name: str,
        animated_property: str = "Opacity",
        start_value: float = 0.0,
        end_value: float = 1.0,
        duration: float = 0.5,
        loop: bool = False
    ) -> Dict[str, Any]:
        """Add a UMG Widget Animation to animate widget properties over time.

        Widget Animations allow smooth fades, slides, and scale effects in UI.
        Use PlayAnimation / StopAnimation nodes in Blueprint to trigger them.

        Args:
            widget_name: Widget Blueprint name
            animation_name: Name for the animation (e.g., "FadeIn", "SlideOut")
            animated_property: Property to animate ("Opacity", "Scale", "Position")
            start_value: Starting value
            end_value: Ending value
            duration: Animation duration in seconds
            loop: Whether the animation loops

        KB: see knowledge_base/06_UI_UMG_SYSTEMS.md#overview
        Example:
            add_widget_animation(widget_name="/Game/MCP_Test/WBP_Example", animation_name="ExampleName")"""
        return _retired_umg_route(
            "add_widget_animation",
            "Use exec_python for a project-specific UMG animation script until a native animation route is added.",
        )

    @mcp.tool()
    def add_remove_from_parent_node(
        ctx: Context,
        blueprint_name: str,
        widget_variable: str = "",
        node_position: List[float] = [400, 0]
    ) -> Dict[str, Any]:
        """Add a RemoveFromParent node to hide/remove a widget from the viewport.

        From Ch. 8 and Ch. 11: Used to close menus. When a player clicks
        "Resume" on the pause menu, RemoveFromParent removes the widget.

        Args:
            blueprint_name: Blueprint to add the node to
            widget_variable: Variable holding the widget reference (empty = self)
            node_position: [X, Y] graph position

        KB: see knowledge_base/06_UI_UMG_SYSTEMS.md#overview
        Example:
            add_remove_from_parent_node(blueprint_name="/Game/MCP_Test/BP_Example")"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_blueprint_function_node", {
                "blueprint_name": blueprint_name,
                "target": widget_variable if widget_variable else "self",
                "function_name": "RemoveFromParent",
                "params": {},
                "node_position": node_position
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_create_widget_node(
        ctx: Context,
        blueprint_name: str,
        widget_class: str = "",
        owning_player_variable: str = "",
        store_in_variable: str = "",
        node_position: List[float] = [300, 0]
    ) -> Dict[str, Any]:
        """Add a CreateWidget node to instantiate a Widget Blueprint at runtime.

        From Ch. 7 (Displaying HUD), Ch. 8 (Win menu), Ch. 11 (Lose/Pause menus):
        Creates a widget instance and optionally adds it to the viewport.

        Args:
            blueprint_name: Blueprint to add the node to
            widget_class: Widget Blueprint class to instantiate
            owning_player_variable: PlayerController variable (empty = Get Player Controller)
            store_in_variable: Variable to store the widget reference (for later use)
            node_position: [X, Y] graph position

        KB: see knowledge_base/06_UI_UMG_SYSTEMS.md#overview
        Example:
            add_create_widget_node(blueprint_name="/Game/MCP_Test/BP_Example")"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_blueprint_function_node", {
                "blueprint_name": blueprint_name,
                "target": "GameplayStatics",
                "function_name": "CreateWidget",
                "params": {
                    "widget_class": widget_class,
                    "owning_player_variable": owning_player_variable,
                    "store_in_variable": store_in_variable,
                },
                "node_position": node_position
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    logger.info("UMG tools registered")
