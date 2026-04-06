"""
Variant Manager Tools for Unreal MCP.
Covers Chapter 20 (Creating a Product Configurator Using the Variant Manager) from the Blueprint book.

Provides tools for:
- Level Variant Sets asset creation
- Variant Sets and Variants management
- Property captures per variant (material, mesh, visibility, transform)
- BP_Configurator dynamic UI generation pattern
- Variant activation via Blueprints (ActivateVariant)
- LevelVariantSets component for actors
- Product Configurator template setup
"""
import logging
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def _send(command: str, params: dict) -> Dict[str, Any]:
    from unreal_mcp_server import get_unreal_connection
    try:
        unreal = get_unreal_connection()
        if not unreal:
            return {"success": False, "message": "Not connected to Unreal Engine"}
        result = unreal.send_command(command, params)
        return result or {"success": False, "message": "No response from Unreal Engine"}
    except Exception as e:
        logger.error(f"Error in {command}: {e}")
        return {"success": False, "message": str(e)}


def register_variant_tools(mcp: FastMCP):

    @mcp.tool()
    def create_level_variant_sets(
        ctx: Context,
        name: str = "LVS_ProductConfigurator",
        variant_sets: List[Dict[str, Any]] = None,
        folder_path: str = "/Game/Configurator"
    ) -> Dict[str, Any]:
        """
        Create a Level Variant Sets asset for product configurator / variant switching.

        From Ch. 20: Level Variant Sets is an asset containing multiple Variant Sets,
        each containing Variants. Each Variant captures specific property changes
        on actors in the level (materials, meshes, visibility, transforms).

        Structure:
        LevelVariantSets (asset)
        └── VariantSet (e.g., \"Color\", \"Wheels\", \"Interior\")
            ├── Variant (e.g., \"Red\", \"Blue\", \"Green\")
            │   └── Captured Properties (actor -> property -> value)
            └── Variant (e.g., \"Black\")

        Args:
            name: Level Variant Sets asset name
            variant_sets: List of variant set definitions:
                [{\"name\": str, \"variants\": [{\"name\": str, \"captures\": [...]}]}]
            folder_path: Content browser folder

        Example:
            variant_sets=[
              {\"name\": \"Color\",
               \"variants\": [
                 {\"name\": \"Red\",
                  \"captures\": [{\"actor\": \"SM_CarBody\", \"property\": \"Material\",
                                 \"value\": \"/Game/Materials/M_CarRed\"}]},
                 {\"name\": \"Blue\",
                  \"captures\": [{\"actor\": \"SM_CarBody\", \"property\": \"Material\",
                                 \"value\": \"/Game/Materials/M_CarBlue\"}]}
               ]}
            ]
        """
        if variant_sets is None:
            variant_sets = []

        return _send("create_level_variant_sets", {
            "name": name,
            "variant_sets": variant_sets,
            "folder_path": folder_path
        })

    @mcp.tool()
    def add_variant_to_level_variant_sets(
        ctx: Context,
        lvs_name: str,
        variant_set_name: str,
        variant_name: str,
        captured_properties: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a Variant to an existing Variant Set in a Level Variant Sets asset.

        Each Variant stores property captures - snapshots of property values on
        level actors that are applied when the variant is activated.

        Args:
            lvs_name: Level Variant Sets asset name
            variant_set_name: Target Variant Set name within the LVS
            variant_name: New Variant name to create
            captured_properties: List of property captures:
                [{\"actor_name\": str, \"property_type\": str, \"property_value\": any}]
                property_type: \"Material\", \"Visibility\", \"Transform\", \"Mesh\"
        """
        if captured_properties is None:
            captured_properties = []

        return _send("add_variant_to_level_variant_sets", {
            "lvs_name": lvs_name,
            "variant_set_name": variant_set_name,
            "variant_name": variant_name,
            "captured_properties": captured_properties
        })

    @mcp.tool()
    def add_activate_variant_node(
        ctx: Context,
        blueprint_name: str,
        lvs_variable: str = "LevelVariantSets",
        variant_set_name: str = "",
        variant_name: str = "",
        node_position: List[int] = [400, 0]
    ) -> Dict[str, Any]:
        """
        Add an ActivateVariant node to switch variants via Blueprint.

        From Ch. 20: The BP_Configurator Blueprint calls ActivateVariant
        to switch between product variants when buttons are pressed.

        Args:
            blueprint_name: Blueprint to add the node to
            lvs_variable: Variable holding the Level Variant Sets reference
            variant_set_name: Name of the Variant Set to switch in
            variant_name: Name of the Variant to activate
            node_position: [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": lvs_variable,
            "function_name": "ActivateVariant",
            "params": {
                "VariantSetName": variant_set_name,
                "VariantName": variant_name
            },
            "node_position": node_position
        })

    @mcp.tool()
    def add_activate_variant_set_node(
        ctx: Context,
        blueprint_name: str,
        lvs_variable: str = "LevelVariantSets",
        variant_set_name: str = "",
        node_position: List[int] = [400, 0]
    ) -> Dict[str, Any]:
        """
        Add an ActivateVariantSet node to activate all variants in a set.

        From Ch. 20: Activates all variants within a Variant Set.
        Useful for resetting or applying a full configuration.

        Args:
            blueprint_name: Blueprint to add the node to
            lvs_variable: Variable holding the Level Variant Sets reference
            variant_set_name: Variant Set name to fully activate
            node_position: [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": lvs_variable,
            "function_name": "ActivateVariantSet",
            "params": {"VariantSetName": variant_set_name},
            "node_position": node_position
        })

    @mcp.tool()
    def create_product_configurator_blueprint(
        ctx: Context,
        name: str = "BP_Configurator",
        lvs_asset_name: str = "LVS_ProductConfigurator",
        widget_blueprint_name: str = "WBP_ConfiguratorUI",
        folder_path: str = "/Game/Configurator"
    ) -> Dict[str, Any]:
        """
        Create the BP_Configurator Blueprint from Ch. 20.

        Creates a Blueprint that:
        1. Holds a reference to the Level Variant Sets asset
        2. On BeginPlay: iterates variant sets + variants to dynamically
           build a UMG widget with buttons for each variant
        3. Each button is bound to call ActivateVariant on click

        This mirrors the product configurator pattern from the book where
        the UI is generated dynamically from the Variant Sets data.

        Args:
            name: Configurator Blueprint name
            lvs_asset_name: Level Variant Sets asset to reference
            widget_blueprint_name: Widget Blueprint to create for the UI
            folder_path: Content browser folder
        """
        return _send("create_product_configurator_blueprint", {
            "name": name,
            "lvs_asset_name": lvs_asset_name,
            "widget_blueprint_name": widget_blueprint_name,
            "folder_path": folder_path
        })

    @mcp.tool()
    def add_get_all_variants_node(
        ctx: Context,
        blueprint_name: str,
        lvs_variable: str = "LevelVariantSets",
        variant_set_name: str = "",
        node_position: List[int] = [400, 0]
    ) -> Dict[str, Any]:
        """
        Add a GetVariants node to get all variants in a Variant Set.

        From Ch. 20: Used in BP_Configurator to iterate over all variants
        and generate UI buttons dynamically.

        Returns an array of Variant objects from the specified Variant Set.

        Args:
            blueprint_name: Blueprint to add the node to
            lvs_variable: Level Variant Sets variable name
            variant_set_name: Variant Set to get variants from
            node_position: [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": lvs_variable,
            "function_name": "GetVariants",
            "params": {"VariantSetName": variant_set_name},
            "node_position": node_position
        })

    @mcp.tool()
    def add_get_variant_sets_node(
        ctx: Context,
        blueprint_name: str,
        lvs_variable: str = "LevelVariantSets",
        node_position: List[int] = [300, 0]
    ) -> Dict[str, Any]:
        """
        Add a GetVariantSets node to get all Variant Sets in a Level Variant Sets asset.

        From Ch. 20: Used in BP_Configurator to iterate over all Variant Sets
        and generate tab-style category buttons for each set.

        Args:
            blueprint_name: Blueprint to add the node to
            lvs_variable: Level Variant Sets variable name
            node_position: [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": lvs_variable,
            "function_name": "GetVariantSets",
            "params": {},
            "node_position": node_position
        })

    logger.info("Variant Manager tools registered successfully")
