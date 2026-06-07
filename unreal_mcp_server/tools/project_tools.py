"""
Project Tools - Input mappings and project-wide settings.
"""
import json
import logging
from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def _send_unreal_command(command: str, params: Dict[str, Any]) -> Dict[str, Any]:
    from unreal_mcp_server import get_unreal_connection

    unreal = get_unreal_connection()
    if not unreal:
        return {"success": False, "message": "Not connected to Unreal Engine"}
    return unreal.send_command(command, params) or {
        "success": False,
        "message": "No response from Unreal Engine",
    }


def _parse_exec_python_json(response: Dict[str, Any]) -> Dict[str, Any]:
    inner = (response or {}).get("result") or response or {}
    output = inner.get("output", "") or ""
    command_result = inner.get("command_result", "") or ""
    candidates = []
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("[Info] "):
            line = line[len("[Info] "):].strip()
        candidates.append(line)
    if command_result:
        candidates.append(command_result.strip())

    for line in reversed(candidates):
        if line.startswith("{") and line.endswith("}"):
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue

    if inner.get("success") is False or (response or {}).get("status") == "error":
        return {
            "success": False,
            "message": inner.get("error") or inner.get("message") or output or "exec_python failed",
        }
    return {"success": False, "message": f"Could not parse exec_python JSON output: {output!r}"}


def register_project_tools(mcp: FastMCP):

    @mcp.tool()
    def create_input_mapping(
        ctx: Context,
        action_name: str,
        key: str,
        input_type: str = "Action"
    ) -> Dict[str, Any]:
        """Create an input mapping in the project settings (legacy input system).

        Args:
            action_name: Name of the input action (e.g., "Jump", "Fire", "MoveForward")
            key: Key binding (SpaceBar, LeftMouseButton, W, A, S, D,
                 Gamepad_FaceButton_Bottom, etc.)
            input_type: "Action" (button press) or "Axis" (analog/continuous)

        KB: see knowledge_base/15_INPUT_SYSTEM_AND_UMG.md#overview
        Example:
            create_input_mapping(action_name="ExampleName", key="ExampleName")"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("create_input_mapping", {
                "action_name": action_name,
                "key": key,
                "input_type": input_type
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def create_enhanced_input_action(
        ctx: Context,
        action_name: str,
        value_type: str = "Digital",
        path: str = "/Game/Input"
    ) -> Dict[str, Any]:
        """Create an Enhanced Input Action asset (UE5 modern input system).

        Args:
            action_name: Name of the input action asset
            value_type: "Digital" (bool), "Axis1D" (float), "Axis2D" (Vector2D), "Axis3D"
            path: Content browser path

        KB: see knowledge_base/15_INPUT_SYSTEM_AND_UMG.md#overview
        Example:
            create_enhanced_input_action(action_name="ExampleName")"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("create_enhanced_input_action", {
                "action_name": action_name,
                "value_type": value_type,
                "path": path
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def create_input_mapping_context(
        ctx: Context,
        context_name: str,
        mappings: List[Dict[str, str]] = None,
        path: str = "/Game/Input"
    ) -> Dict[str, Any]:
        """Create an Input Mapping Context for Enhanced Input system.

        Args:
            context_name: Name of the IMC asset
            mappings: List of dicts with 'action' and 'key' fields
            path: Content browser path

        Example mappings:
            [{"action": "IA_Jump", "key": "SpaceBar"},
             {"action": "IA_Move", "key": "W"}]

        KB: see knowledge_base/15_INPUT_SYSTEM_AND_UMG.md#overview
        Example:
            create_input_mapping_context(context_name="ExampleName")"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("create_input_mapping_context", {
                "context_name": context_name,
                "mappings": mappings or [],
                "path": path
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_input_mapping(imc_name: str, action_name: str, key: str) -> dict:
        """Add an input mapping to an existing Input Mapping Context (IMC).

        Args:
            imc_name: Name of the Input Mapping Context (e.g., "IMC_Default")
            action_name: Name of the Input Action (e.g., "IA_Jump", "IA_WormholeTP")
            key: Key name to bind (e.g., "SpaceBar", "V", "T", "LeftMouseButton")

        Returns:
            dict with success status, imc_name, action_name, key, and mapping_index

        Example:
            add_input_mapping(imc_name="ExampleName", action_name="ExampleName", key="ExampleName")

        KB: see knowledge_base/15_INPUT_SYSTEM_AND_UMG.md#overview"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_input_mapping", {
                "imc_name": imc_name,
                "action_name": action_name,
                "key": key
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def inspect_input_mapping_context(
        ctx: Context,
        imc_path_or_name: str,
    ) -> Dict[str, Any]:
        """Inspect an Enhanced Input Mapping Context and return action/key mappings.

        KB: see knowledge_base/15_INPUT_SYSTEM_AND_UMG.md#overview
        Example:
            inspect_input_mapping_context(imc_path_or_name="/Game/MCP_Test/Example")"""
        try:
            return _send_unreal_command("inspect_input_mapping_context", {
                "imc_path_or_name": imc_path_or_name,
            })
        except Exception as e:
            logger.error(f"Error inspecting Input Mapping Context: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def check_blueprint_generated_class(
        ctx: Context,
        blueprint_path_or_name: str,
    ) -> Dict[str, Any]:
        """Verify that a Blueprint asset has a valid generated class and report parent/native class data.

        KB: see knowledge_base/15_INPUT_SYSTEM_AND_UMG.md#overview
        Example:
            check_blueprint_generated_class(blueprint_path_or_name="/Game/MCP_Test/BP_Example")"""
        try:
            return _send_unreal_command("check_blueprint_generated_class", {
                "blueprint_path_or_name": blueprint_path_or_name,
            })
        except Exception as e:
            logger.error(f"Error checking Blueprint generated class: {e}")
            return {"success": False, "message": str(e)}

    logger.info("Project tools registered")
