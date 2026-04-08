"""
graph_layout.py - Utilities for creating clean, organized Blueprint Event Graphs

This module provides helpers for laying out nodes in a professional manner:
- No crossed wires
- Consistent spacing
- Left-to-right execution flow
- Data/reference nodes positioned below
"""

from typing import Dict, List, Tuple, Any, Optional


class GraphLayout:
    """
    Manages node positioning for clean Blueprint graphs.
    
    Usage:
        layout = GraphLayout(start_x=-800, start_y=0, x_spacing=320, y_spacing=120)
        
        # Add nodes to execution chain (left to right)
        tick_pos = layout.add_exec_node()
        multiply_pos = layout.add_exec_node()
        offset_pos = layout.add_exec_node()
        
        # Add data/reference nodes below the chain
        self_pos = layout.add_data_node(column=2)  # Below multiply node
    """
    
    def __init__(
        self,
        start_x: int = -800,
        start_y: int = 0,
        x_spacing: int = 320,
        y_spacing: int = 120,
    ):
        """
        Initialize the layout manager.
        
        Args:
            start_x: Starting X position (left side)
            start_y: Starting Y position for execution chain
            x_spacing: Horizontal spacing between nodes
            y_spacing: Vertical spacing for data nodes
        """
        self.start_x = start_x
        self.start_y = start_y
        self.x_spacing = x_spacing
        self.y_spacing = y_spacing
        
        # Track current column for execution nodes
        self.current_exec_column = 0
        
        # Track data node rows per column
        self.data_rows: Dict[int, int] = {}
    
    def add_exec_node(self) -> List[int]:
        """
        Get position for the next execution node in the chain.
        
        Returns:
            [x, y] position array
        """
        x = self.start_x + (self.current_exec_column * self.x_spacing)
        y = self.start_y
        self.current_exec_column += 1
        return [x, y]
    
    def add_data_node(self, column: Optional[int] = None, row: int = 1) -> List[int]:
        """
        Get position for a data/reference node below the execution chain.
        
        Args:
            column: Which execution column to align with (0-indexed).
                   If None, aligns with the previous execution node.
            row: Which row below the execution chain (1-indexed)
        
        Returns:
            [x, y] position array
        """
        if column is None:
            column = max(0, self.current_exec_column - 1)
        
        # Track the highest row used for this column
        if column not in self.data_rows:
            self.data_rows[column] = 0
        
        # Use specified row or auto-increment
        actual_row = max(row, self.data_rows[column] + 1)
        self.data_rows[column] = actual_row
        
        x = self.start_x + (column * self.x_spacing)
        y = self.start_y + (actual_row * self.y_spacing)
        return [x, y]
    
    def custom_position(self, column: int, row: int = 0) -> List[int]:
        """
        Get a custom position using column/row coordinates.
        
        Args:
            column: Column index (0 = start_x)
            row: Row index (0 = start_y, positive = below, negative = above)
        
        Returns:
            [x, y] position array
        """
        x = self.start_x + (column * self.x_spacing)
        y = self.start_y + (row * self.y_spacing)
        return [x, y]
    
    def reset(self):
        """Reset the layout to start positioning from the beginning."""
        self.current_exec_column = 0
        self.data_rows.clear()


class NodeBuilder:
    """
    High-level helper for building organized graphs with automatic positioning.
    
    Usage:
        builder = NodeBuilder(
            connection=unreal_connection,
            blueprint_name="BP_MyBlueprint",
            graph_name="EventGraph"
        )
        
        # Create nodes with automatic positioning
        tick_id = builder.add_event("ReceiveTick")
        multiply_id = builder.add_function("Multiply_VectorFloat", target="KismetMathLibrary")
        offset_id = builder.add_function("K2_AddActorLocalOffset")
        self_id = builder.add_self_ref(below_column=2)
        
        # Connect them
        builder.connect(tick_id, "then", offset_id, "execute")
        builder.connect(tick_id, "DeltaSeconds", multiply_id, "B")
        # ... etc
    """
    
    def __init__(
        self,
        connection,
        blueprint_name: str,
        graph_name: str = "EventGraph",
        layout: Optional[GraphLayout] = None,
    ):
        """
        Initialize the node builder.
        
        Args:
            connection: Unreal MCP connection object
            blueprint_name: Blueprint asset name
            graph_name: Graph to build in
            layout: Optional GraphLayout instance (creates default if None)
        """
        self.connection = connection
        self.blueprint_name = blueprint_name
        self.graph_name = graph_name
        self.layout = layout or GraphLayout()
        
        # Track created nodes
        self.nodes: Dict[str, Dict[str, Any]] = {}
    
    def add_event(self, event_name: str, auto_position: bool = True) -> str:
        """
        Add an event node to the graph.
        
        Args:
            event_name: Event name (e.g., "ReceiveTick", "ReceiveBeginPlay")
            auto_position: Use automatic positioning
        
        Returns:
            Node ID (GUID)
        """
        pos = self.layout.add_exec_node() if auto_position else [0, 0]
        
        result = self.connection.send_command("add_blueprint_event_node", {
            "blueprint_name": self.blueprint_name,
            "graph_name": self.graph_name,
            "event_name": event_name,
            "node_position": pos,
        })
        
        node_id = result.get("node_id", "")
        self.nodes[node_id] = {
            "name": result.get("node_name", ""),
            "type": "event",
            "position": pos,
        }
        return node_id
    
    def add_function(
        self,
        function_name: str,
        target: str = "",
        auto_position: bool = True,
    ) -> str:
        """
        Add a function call node to the graph.
        
        Args:
            function_name: Function to call
            target: Target class (optional)
            auto_position: Use automatic positioning
        
        Returns:
            Node ID (GUID)
        """
        pos = self.layout.add_exec_node() if auto_position else [0, 0]
        
        result = self.connection.send_command("add_blueprint_function_node", {
            "blueprint_name": self.blueprint_name,
            "graph_name": self.graph_name,
            "function_name": function_name,
            "target": target,
            "node_position": pos,
        })
        
        node_id = result.get("node_id", "")
        self.nodes[node_id] = {
            "name": result.get("node_name", ""),
            "type": "function",
            "position": pos,
        }
        return node_id
    
    def add_self_ref(self, below_column: Optional[int] = None, row: int = 1) -> str:
        """
        Add a self reference node below the execution chain.
        
        Args:
            below_column: Column to place below (None = previous exec node)
            row: Row below execution chain
        
        Returns:
            Node ID (GUID)
        """
        pos = self.layout.add_data_node(column=below_column, row=row)
        
        result = self.connection.send_command("add_blueprint_self_reference", {
            "blueprint_name": self.blueprint_name,
            "graph_name": self.graph_name,
            "node_position": pos,
        })
        
        node_id = result.get("node_id", "")
        self.nodes[node_id] = {
            "name": result.get("node_name", ""),
            "type": "self",
            "position": pos,
        }
        return node_id
    
    def connect(
        self,
        source_id: str,
        source_pin: str,
        target_id: str,
        target_pin: str,
    ) -> bool:
        """
        Connect two nodes by pin names.
        
        Args:
            source_id: Source node ID
            source_pin: Source pin name
            target_id: Target node ID
            target_pin: Target pin name
        
        Returns:
            True if connection succeeded
        """
        result = self.connection.send_command("connect_blueprint_nodes", {
            "blueprint_name": self.blueprint_name,
            "graph_name": self.graph_name,
            "source_node_id": source_id,
            "source_pin": source_pin,
            "target_node_id": target_id,
            "target_pin": target_pin,
        })
        
        return result.get("connection_verified", False)
    
    def set_pin_value(self, node_id: str, pin_name: str, value: str) -> bool:
        """
        Set a default value on a pin.
        
        Args:
            node_id: Node ID
            pin_name: Pin name
            value: Value as string
        
        Returns:
            True if successful
        """
        result = self.connection.send_command("set_node_pin_value", {
            "blueprint_name": self.blueprint_name,
            "graph_name": self.graph_name,
            "node_id": node_id,
            "pin_name": pin_name,
            "value": value,
        })
        
        return "node_id" in result
    
    def compile(self) -> Dict[str, Any]:
        """
        Compile the blueprint.
        
        Returns:
            Compile result dict
        """
        return self.connection.send_command("compile_blueprint", {
            "blueprint_name": self.blueprint_name,
        })


def create_simple_movement_graph(
    connection,
    blueprint_name: str,
    speed: float = 100.0,
    direction: Tuple[float, float, float] = (100.0, 0.0, 0.0),
) -> Dict[str, Any]:
    """
    Helper to create a standard Tick-based movement graph.
    
    Args:
        connection: Unreal MCP connection
        blueprint_name: Blueprint to modify
        speed: Movement speed in units/second
        direction: Movement direction vector (local space)
    
    Returns:
        Dict with node IDs and compile result
    """
    builder = NodeBuilder(connection, blueprint_name)
    
    # Create nodes with automatic positioning
    tick_id = builder.add_event("ReceiveTick")
    multiply_id = builder.add_function("Multiply_VectorFloat", target="KismetMathLibrary")
    offset_id = builder.add_function("K2_AddActorLocalOffset")
    self_id = builder.add_self_ref(below_column=2)
    
    # Set values
    builder.set_pin_value(multiply_id, "A", f"{direction[0]}, {direction[1]}, {direction[2]}")
    
    # Connect execution flow
    builder.connect(tick_id, "then", offset_id, "execute")
    
    # Connect data flow
    builder.connect(tick_id, "DeltaSeconds", multiply_id, "B")
    builder.connect(multiply_id, "ReturnValue", offset_id, "DeltaLocation")
    builder.connect(self_id, "self", offset_id, "self")
    
    # Compile
    compile_result = builder.compile()
    
    return {
        "nodes": {
            "tick": tick_id,
            "multiply": multiply_id,
            "offset": offset_id,
            "self": self_id,
        },
        "compile": compile_result,
    }
