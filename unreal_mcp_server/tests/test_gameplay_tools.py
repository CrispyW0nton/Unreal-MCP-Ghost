import sys
import unittest
from pathlib import Path


_SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(_SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVER_ROOT))


class _MockMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def _decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return _decorator

    def list_tool_names(self):
        return list(self.tools)


class TestGameplayToolsRegistration(unittest.TestCase):
    def test_phase_3_networking_tools_register(self):
        from tools.gameplay_tools import register_gameplay_tools

        mcp = _MockMCP()
        register_gameplay_tools(mcp)

        names = set(mcp.list_tool_names())
        self.assertIn("net_describe_blueprint_replication", names)
        self.assertIn("net_set_actor_replicates", names)
        self.assertIn("net_set_component_replicates", names)
        self.assertIn("net_configure_replicated_property", names)
        self.assertIn("net_add_repnotify_variable", names)
        self.assertIn("net_create_rpc_event", names)
        self.assertIn("net_configure_rpc", names)
        self.assertIn("net_add_authority_gate", names)
        self.assertIn("net_add_role_switch", names)
        self.assertIn("net_set_owner_reference", names)
        self.assertIn("session_create_blueprint_flow", names)
        self.assertIn("session_find_blueprint_flow", names)
        self.assertIn("network_debug_replication", names)
        self.assertIn("net_validate_common_mistakes", names)


if __name__ == "__main__":
    unittest.main()
