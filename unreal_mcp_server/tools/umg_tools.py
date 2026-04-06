"""
UMG Tools - Widget Blueprint creation and manipulation.
Covers Chapter on UI/UMG from the Blueprint book.
"""
import logging
from typing import Dict, List, Any
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def register_umg_tools(mcp: FastMCP):

    @mcp.tool()
    def create_umg_widget_blueprint(
        ctx: Context,
        widget_name: str,
        parent_class: str = "UserWidget",
        path: str = "/Game/UI"
    ) -> Dict[str, Any]:
        """
        Create a new UMG Widget Blueprint.

        Args:
            widget_name: Widget asset name (e.g., "WBP_HUD", "WBP_MainMenu")
            parent_class: Parent class (default: "UserWidget")
            path: Content browser path (default: "/Game/UI")
        """
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
        """
        Add a Text Block to a Widget Blueprint.

        Args:
            widget_name: Widget Blueprint name
            text_block_name: Component name for the text block
            text: Display text
            position: [X, Y] canvas position
            size: [Width, Height]
            font_size: Font size in points
            color: [R, G, B, A] (0.0-1.0)
        """
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
        """
        Add a Button to a Widget Blueprint.

        Args:
            widget_name: Widget Blueprint name
            button_name: Component name for the button
            text: Button label
            position: [X, Y] canvas position
            size: [Width, Height]
            font_size: Font size
            color: [R,G,B,A] text color
            background_color: [R,G,B,A] button background color
        """
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
    def bind_widget_event(
        ctx: Context,
        widget_name: str,
        widget_component_name: str,
        event_name: str,
        function_name: str = ""
    ) -> Dict[str, Any]:
        """
        Bind a widget event (e.g., OnClicked) to a function.

        Args:
            widget_name: Widget Blueprint name
            widget_component_name: Component name (e.g., button name)
            event_name: Event to bind ("OnClicked", "OnHovered", "OnUnhovered",
                        "OnPressed", "OnReleased")
            function_name: Target function name (auto-generated if empty)
        """
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
        """
        Instantiate a Widget Blueprint and add it to the game viewport.

        Args:
            widget_name: Widget Blueprint name
            z_order: Rendering order (higher = on top)
        """
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
        """
        Set up a dynamic property binding on a Text Block widget.

        Args:
            widget_name: Widget Blueprint name
            text_block_name: Text Block component name
            binding_property: Blueprint variable to bind to
            binding_type: "Text", "Visibility", "ColorAndOpacity"
        """
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
        """
        Add a Progress Bar widget (useful for health/ammo bars).

        Args:
            widget_name: Widget Blueprint name
            progress_bar_name: Component name
            position: [X, Y] position
            size: [Width, Height]
            fill_color: [R,G,B,A] fill color
            background_color: [R,G,B,A] background
            percent: Initial fill (0.0-1.0)
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_progress_bar_to_widget", {
                "widget_name": widget_name,
                "progress_bar_name": progress_bar_name,
                "position": position,
                "size": size,
                "fill_color": fill_color,
                "background_color": background_color,
                "percent": percent
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

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
        """
        Add an Image widget to a Widget Blueprint.

        Args:
            widget_name: Widget Blueprint name
            image_name: Component name
            texture_path: Texture asset path (optional)
            position: [X, Y] position
            size: [Width, Height]
            color: [R,G,B,A] tint color
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_image_to_widget", {
                "widget_name": widget_name,
                "image_name": image_name,
                "texture_path": texture_path,
                "position": position,
                "size": size,
                "color": color
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    logger.info("UMG tools registered")
