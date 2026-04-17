# Graph Scripting Specification V4

> **Date**: 2026-04-16 | **Phase**: Phase 2 of Roadmap V4
> **Goal**: Define the technical specification for Ghost's graph-native Blueprint and material scripting layer

---

## 1. Design Principles

1. **Atomic first**: Every graph operation should be a single, testable, undo-able primitive
2. **Composable**: Higher-order skills compose atomic operations, never bypass them
3. **Verified**: Every mutation triggers compile + error capture
4. **Readable**: AI-generated graphs must be auto-formatted for human readability
5. **Transactional**: All mutations wrapped in `ScopedEditorTransaction`
6. **Structured**: All results use the standard `StructuredResult` schema

---

## 2. Blueprint Graph Operations

### 2.1 Graph Management

#### `bp_create_graph`
```python
def bp_create_graph(
    blueprint_path: str,       # e.g., "/Game/BP_Player"
    graph_name: str,           # e.g., "EventGraph", "OnTakeDamage"
    graph_type: str            # "event" | "function" | "macro"
) -> StructuredResult:
    """Create a new graph in the specified Blueprint."""
```

#### `bp_get_graph_summary`
```python
def bp_get_graph_summary(
    blueprint_path: str,
    graph_name: str = None,    # None = all graphs
    depth: int = 1,            # Nested graph traversal depth (1-5)
    format: str = "compact"    # "compact" | "full" | "ai_readable"
) -> StructuredResult:
    """Serialize graph(s) to structured JSON for AI reasoning.
    
    Compact format reduces tokens by 60-90% vs native UE text format.
    Inspired by NodeToCode's K2Node/K2Pin serialization approach.
    
    Output schema (compact):
    {
        "graph_name": "EventGraph",
        "nodes": [
            {
                "id": "node_guid",
                "type": "K2Node_CallFunction",
                "function": "PrintString",
                "position": [400, 200],
                "pins": {
                    "exec_in": {"connected_to": "prev_node.exec_out"},
                    "InString": {"default": "Hello World"},
                    "exec_out": {"connected_to": null}
                }
            }
        ],
        "variables": [...],
        "comments": [...]
    }
    """
```

### 2.2 Node Operations

#### `bp_add_node`
```python
def bp_add_node(
    blueprint_path: str,
    graph_name: str,
    node_class: str,           # e.g., "K2Node_CallFunction", "K2Node_IfThenElse"
    position_x: int = 0,
    position_y: int = 0,
    # Class-specific params:
    function_name: str = None, # For CallFunction nodes
    event_name: str = None,    # For Event nodes
    variable_name: str = None, # For Variable Get/Set nodes
    custom_params: dict = None # Escape hatch for unusual node types
) -> StructuredResult:
    """Add a node to the specified graph.
    
    Returns node_guid in outputs for subsequent connection operations.
    
    outputs: {
        "node_guid": "abc123-...",
        "pins": {
            "exec": {"direction": "input", "type": "exec"},
            "then": {"direction": "output", "type": "exec"},
            "ReturnValue": {"direction": "output", "type": "float"}
        }
    }
    """
```

#### `bp_remove_node`
```python
def bp_remove_node(
    blueprint_path: str,
    graph_name: str,
    node_guid: str
) -> StructuredResult
```

#### `bp_inspect_node`
```python
def bp_inspect_node(
    blueprint_path: str,
    graph_name: str,
    node_guid: str
) -> StructuredResult:
    """Get complete node details: class, pins, connections, position, comments.
    
    outputs: {
        "node_guid": "abc123",
        "node_class": "K2Node_CallFunction",
        "node_title": "Print String",
        "position": [400, 200],
        "comment": "Debug output",
        "pins": [
            {
                "name": "execute",
                "direction": "input",
                "type": "exec",
                "connected_to": [{"node": "xyz789", "pin": "then"}],
                "default_value": null
            },
            ...
        ]
    }
    """
```

### 2.3 Connection Operations

#### `bp_connect_pins`
```python
def bp_connect_pins(
    blueprint_path: str,
    graph_name: str,
    source_node_guid: str,
    source_pin_name: str,      # Case-sensitive! Verify with bp_inspect_node first
    target_node_guid: str,
    target_pin_name: str
) -> StructuredResult:
    """Connect an output pin to an input pin.
    
    IMPORTANT: Pin names are case-sensitive.
    ALWAYS use bp_inspect_node to verify exact pin names before connecting.
    
    The tool should internally call CheckConnectionResponse() and return
    the result. If the connection is invalid, return success=false with
    the specific incompatibility reason.
    """
```

#### `bp_disconnect_pin`
```python
def bp_disconnect_pin(
    blueprint_path: str,
    graph_name: str,
    node_guid: str,
    pin_name: str,
    target_node_guid: str = None  # None = break all connections on this pin
) -> StructuredResult
```

#### `bp_set_pin_default`
```python
def bp_set_pin_default(
    blueprint_path: str,
    graph_name: str,
    node_guid: str,
    pin_name: str,
    value: str                    # String representation of value
) -> StructuredResult
```

### 2.4 Variable & Function Operations

#### `bp_add_variable`
```python
def bp_add_variable(
    blueprint_path: str,
    variable_name: str,
    variable_type: str,          # "bool", "int", "float", "FVector", "UStaticMesh*", etc.
    category: str = "",
    default_value: str = None,
    is_replicated: bool = False,
    rep_condition: str = None,   # "COND_None", "COND_OwnerOnly", etc.
    expose_on_spawn: bool = False,
    is_editable: bool = True
) -> StructuredResult
```

#### `bp_add_function`
```python
def bp_add_function(
    blueprint_path: str,
    function_name: str,
    inputs: list = None,         # [{"name": "Damage", "type": "float"}, ...]
    outputs: list = None,        # [{"name": "IsDead", "type": "bool"}, ...]
    is_pure: bool = False,
    access: str = "public"       # "public" | "protected" | "private"
) -> StructuredResult
```

### 2.5 Compile & Validate

#### `bp_compile`
```python
def bp_compile(
    blueprint_path: str,
    capture_log: bool = True     # Capture output log during compilation
) -> StructuredResult:
    """Compile the Blueprint and return structured results.
    
    outputs: {
        "compiled": true/false,
        "errors": [
            {"node_guid": "abc", "pin": "InFloat", "message": "Type mismatch", "severity": "error"}
        ],
        "warnings": [...],
        "log_tail": "last 20 lines of output log during compile"
    }
    """
```

#### `bp_diff_snapshot`
```python
def bp_diff_snapshot(
    blueprint_path: str,
    action: str = "capture"      # "capture" (save current state) | "compare" (diff against captured)
) -> StructuredResult:
    """Capture or compare Blueprint state for before/after diffing.
    
    Usage:
    1. Call with action="capture" before mutations
    2. Perform mutations
    3. Call with action="compare" to see what changed
    
    outputs (compare): {
        "nodes_added": [...],
        "nodes_removed": [...],
        "connections_added": [...],
        "connections_removed": [...],
        "variables_changed": [...],
        "compilation_status_changed": true/false
    }
    """
```

### 2.6 Graph Layout

#### `bp_auto_format_graph`
```python
def bp_auto_format_graph(
    blueprint_path: str,
    graph_name: str = None,      # None = all graphs
    spacing_x: int = 350,        # Horizontal spacing between node layers
    group_by_comments: bool = True,
    insert_reroutes: bool = True, # Insert reroute nodes for long connections
    max_connection_length: int = 800  # Threshold for reroute insertion
) -> StructuredResult
```

---

## 3. Material Graph Operations

### `mat_create_material`
```python
def mat_create_material(
    material_path: str,          # e.g., "/Game/Materials/M_Metal"
    material_domain: str = "Surface",  # "Surface" | "DeferredDecal" | "PostProcess" | "UI"
    blend_mode: str = "Opaque",
    shading_model: str = "DefaultLit"
) -> StructuredResult
```

### `mat_add_expression`
```python
def mat_add_expression(
    material_path: str,
    expression_class: str,       # "MaterialExpressionTextureSample", "MaterialExpressionMultiply", etc.
    position_x: int = 0,
    position_y: int = 0,
    params: dict = None          # Expression-specific parameters
) -> StructuredResult:
    """Returns expression_guid for connection operations."""
```

### `mat_connect_expressions`
```python
def mat_connect_expressions(
    material_path: str,
    source_guid: str,
    source_output: int = 0,      # Output index
    target_guid: str = None,     # None = connect to material output
    target_input: int = 0,       # Input index, or material input name
    target_input_name: str = None  # "BaseColor", "Metallic", "Roughness", "Normal", etc.
) -> StructuredResult
```

### `mat_create_instance`
```python
def mat_create_instance(
    instance_path: str,
    parent_material_path: str
) -> StructuredResult
```

### `mat_set_parameter`
```python
def mat_set_parameter(
    material_or_instance_path: str,
    parameter_name: str,
    value: str,                  # String representation
    parameter_type: str = "auto" # "scalar" | "vector" | "texture" | "auto"
) -> StructuredResult
```

### `mat_compile`
```python
def mat_compile(
    material_path: str,
    capture_log: bool = True
) -> StructuredResult
```

---

## 4. Implementation Notes

### Pin Name Discovery
Pin names are **case-sensitive** and not always obvious. The recommended workflow:
1. Call `bp_add_node` to create the node
2. Call `bp_inspect_node` to enumerate all pins with exact names
3. Call `bp_connect_pins` using the exact names from step 2

This matches flopperam's guidance: "If unsure about pin names, create the node and hover over pins to reveal their internal names."

### Graph Spacing Rules (from flopperam + GraphFormatter)
- **X spacing**: 300-400 units between node columns
- **Y alignment**: Keep related nodes on similar Y coordinates
- **Comment grouping**: Wrap logical groups in comment nodes
- **Reroute threshold**: Insert reroute nodes for connections > 800 units
- **Variable duplication**: For high-fan-out nodes, consider creating variable references instead

### Transaction Wrapping
Every graph mutation MUST be wrapped:
```python
with unreal.ScopedEditorTransaction("AI: Add Health Variable") as transaction:
    # perform mutations
    pass
```

### Auto-Compile Policy
After every batch of related graph mutations:
1. Call `bp_compile()` or `mat_compile()`
2. Check for errors in the structured result
3. If errors: report them with node/pin context for agent diagnosis
4. If clean: proceed to next operation

### StructuredResult Schema
```json
{
    "success": true,
    "stage": "bp_add_node",
    "message": "Added K2Node_CallFunction 'PrintString' at (400, 200)",
    "outputs": {
        "node_guid": "abc123-def456",
        "pins": {...}
    },
    "warnings": [],
    "errors": [],
    "log_tail": ""
}
```

---

## 5. C++ Plugin Commands Required

The Python MCP tools above will need corresponding C++ plugin commands on the TCP bridge (port 55557). Estimated new commands:

| Command | Category |
|---|---|
| `bp_create_graph` | Blueprint Graph |
| `bp_add_node` | Blueprint Graph |
| `bp_remove_node` | Blueprint Graph |
| `bp_inspect_node` | Blueprint Graph |
| `bp_connect_pins` | Blueprint Graph |
| `bp_disconnect_pin` | Blueprint Graph |
| `bp_set_pin_default` | Blueprint Graph |
| `bp_add_variable` | Blueprint Graph |
| `bp_add_function` | Blueprint Graph |
| `bp_compile` | Blueprint Graph |
| `bp_get_graph_summary` | Blueprint Graph |
| `bp_auto_format_graph` | Blueprint Graph |
| `mat_create_material` | Material Graph |
| `mat_add_expression` | Material Graph |
| `mat_connect_expressions` | Material Graph |
| `mat_create_instance` | Material Graph |
| `mat_set_parameter` | Material Graph |
| `mat_compile` | Material Graph |

This adds ~18 new C++ commands, bringing the total to ~137.

---

## 6. Test Requirements

Each graph operation tool MUST have:
1. **Smoke test**: Create → verify → cleanup
2. **Failure test**: Invalid input → structured error → no crash
3. **Undo test**: Create → undo → verify reverted
4. **Integration test**: Multi-step workflow (add node + connect + compile)

Target: 40+ new tests for Phase 2 (bringing total to 120+).
