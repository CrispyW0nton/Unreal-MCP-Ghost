"""Generic UMG widget tree tools.

These expose the native `widget_*` C++ bridge routes as first-class MCP tools.
They are intentionally lower-level than the historical convenience UMG tools:
agents can compose CanvasPanel, TextBlock, Image, ProgressBar, Button, and layout
widgets without each control type needing its own native route.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import Context, FastMCP


def register_widget_tools(mcp: FastMCP):
    @mcp.tool()
    def widget_add_child(
        ctx: Context,
        widget_blueprint_path: str,
        child_class: str,
        child_name: str,
        parent_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a child widget to a Widget Blueprint tree.

        Args:
            widget_blueprint_path: Full Widget Blueprint asset path, e.g.
                `/Game/UI/WBP_HUD` or `/Game/UI/WBP_HUD.WBP_HUD`.
            child_class: Supported UMG class name such as `CanvasPanel`,
                `TextBlock`, `Image`, `ProgressBar`, `Button`, `HorizontalBox`,
                `VerticalBox`, `Overlay`, or `SizeBox`.
            child_name: Name for the new child widget.
            parent_name: Optional panel widget to attach under. If omitted, the
                child becomes the root when no root exists, or attaches to the
                root when the root is a panel.
        """
        from unreal_mcp_server import get_unreal_connection

        unreal = get_unreal_connection()
        if not unreal:
            return {"success": False, "message": "Not connected"}
        params: Dict[str, Any] = {
            "widget_blueprint_path": widget_blueprint_path,
            "child_class": child_class,
            "child_name": child_name,
        }
        if parent_name:
            params["parent_name"] = parent_name
        return unreal.send_command("widget_add_child", params) or {}

    @mcp.tool()
    def widget_set_property(
        ctx: Context,
        widget_blueprint_path: str,
        widget_name: str,
        property_name: str,
        property_value: str,
    ) -> Dict[str, Any]:
        """Set a common property on a child widget.

        Supported native properties include `Text`, `FontSize`,
        `ColorAndOpacity`, `BrushTintColor`, `BrushSize`, `Percent`,
        `FillColorAndOpacity`, `Visibility`, and `RenderTransformAngle`.
        Color and vector values should be comma-separated strings such as
        `1,0.2,0.1,1` or `256,64`.
        """
        from unreal_mcp_server import get_unreal_connection

        unreal = get_unreal_connection()
        if not unreal:
            return {"success": False, "message": "Not connected"}
        return unreal.send_command(
            "widget_set_property",
            {
                "widget_blueprint_path": widget_blueprint_path,
                "widget_name": widget_name,
                "property_name": property_name,
                "property_value": property_value,
            },
        ) or {}

    @mcp.tool()
    def widget_set_anchor(
        ctx: Context,
        widget_blueprint_path: str,
        widget_name: str,
        anchor_min_x: float,
        anchor_min_y: float,
        anchor_max_x: float,
        anchor_max_y: float,
        position_x: float,
        position_y: float,
        size_x: float,
        size_y: float,
        alignment_x: float = 0.0,
        alignment_y: float = 0.0,
    ) -> Dict[str, Any]:
        """Set CanvasPanelSlot anchor, position, size, and alignment."""
        from unreal_mcp_server import get_unreal_connection

        unreal = get_unreal_connection()
        if not unreal:
            return {"success": False, "message": "Not connected"}
        return unreal.send_command(
            "widget_set_anchor",
            {
                "widget_blueprint_path": widget_blueprint_path,
                "widget_name": widget_name,
                "anchor_min_x": anchor_min_x,
                "anchor_min_y": anchor_min_y,
                "anchor_max_x": anchor_max_x,
                "anchor_max_y": anchor_max_y,
                "position_x": position_x,
                "position_y": position_y,
                "size_x": size_x,
                "size_y": size_y,
                "alignment_x": alignment_x,
                "alignment_y": alignment_y,
            },
        ) or {}

    @mcp.tool()
    def widget_get_children(
        ctx: Context,
        widget_blueprint_path: str,
        parent_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List children in a Widget Blueprint tree.

        If `parent_name` is omitted, the native route returns the root widget
        plus the root panel's immediate children.
        """
        from unreal_mcp_server import get_unreal_connection

        unreal = get_unreal_connection()
        if not unreal:
            return {"success": False, "message": "Not connected"}
        params: Dict[str, Any] = {"widget_blueprint_path": widget_blueprint_path}
        if parent_name:
            params["parent_name"] = parent_name
        return unreal.send_command("widget_get_children", params) or {}
