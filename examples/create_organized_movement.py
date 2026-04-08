#!/usr/bin/env python3
"""
Example: Create an organized movement system using the graph_layout helpers.

This demonstrates how to create clean, professional Blueprint graphs with:
- No crossed wires
- Consistent spacing
- Proper left-to-right execution flow
- Data nodes positioned below
"""

import sys
sys.path.insert(0, '/home/user/webapp')

from unreal_mcp_server.tools.graph_layout import NodeBuilder, GraphLayout


def create_movement_system(blueprint_name: str):
    """
    Create a clean Event Tick movement system in the specified Blueprint.
    
    Args:
        blueprint_name: Name of the Blueprint to modify (e.g., "BP_PassiveBot")
    """
    # Import connection here to avoid issues if module not available
    from unreal_mcp_server import get_unreal_connection
    
    conn = get_unreal_connection()
    if not conn:
        print("❌ Error: Not connected to Unreal Engine")
        return
    
    print(f"🔧 Creating organized movement system in {blueprint_name}...")
    
    # Create layout manager with custom spacing
    layout = GraphLayout(
        start_x=-800,   # Start position
        start_y=0,      # Execution chain Y position
        x_spacing=320,  # Horizontal spacing between nodes
        y_spacing=120,  # Vertical spacing for data nodes
    )
    
    # Create node builder
    builder = NodeBuilder(conn, blueprint_name, layout=layout)
    
    print("  ├─ Adding Event Tick...")
    tick_id = builder.add_event("ReceiveTick")
    
    print("  ├─ Adding Multiply node...")
    multiply_id = builder.add_function("Multiply_VectorFloat", target="KismetMathLibrary")
    
    print("  ├─ Adding AddActorLocalOffset...")
    offset_id = builder.add_function("K2_AddActorLocalOffset")
    
    print("  ├─ Adding Self reference (below column 2)...")
    self_id = builder.add_self_ref(below_column=2, row=1)
    
    print("  ├─ Setting movement speed vector...")
    builder.set_pin_value(multiply_id, "A", "100.0, 0.0, 0.0")  # 100 units/sec forward
    
    print("  ├─ Connecting execution flow...")
    builder.connect(tick_id, "then", offset_id, "execute")
    
    print("  ├─ Connecting data flow...")
    builder.connect(tick_id, "DeltaSeconds", multiply_id, "B")
    builder.connect(multiply_id, "ReturnValue", offset_id, "DeltaLocation")
    builder.connect(self_id, "self", offset_id, "self")
    
    print("  ├─ Compiling Blueprint...")
    result = builder.compile()
    
    if result.get("compiled") and not result.get("had_errors"):
        print(f"  └─ ✅ Success! {blueprint_name} compiled with 0 errors")
        print("\n📐 Node Layout:")
        print("   Event Tick [-800, 0]")
        print("        │")
        print("        ├─> Multiply [-480, 0]")
        print("        │      ├─ A: (100, 0, 0)")
        print("        │      └─ B: DeltaSeconds")
        print("        │")
        print("        └─> AddActorLocalOffset [-160, 0]")
        print("               ├─ DeltaLocation: Multiply output")
        print("               └─ self: Self [-320, 120]")
        print("\n✨ The graph is now organized with no crossed wires!")
    else:
        print(f"  └─ ❌ Compilation failed: {result.get('error', 'Unknown error')}")
        if result.get("messages"):
            for msg in result["messages"]:
                print(f"      {msg}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 create_organized_movement.py <BlueprintName>")
        print("Example: python3 create_organized_movement.py BP_PassiveBot")
        sys.exit(1)
    
    blueprint_name = sys.argv[1]
    create_movement_system(blueprint_name)
