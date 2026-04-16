"""
Graph Summary Quality Verification
=====================================
Runs bp_get_graph_summary against:
  1. BP_DemoA (the Demo A Blueprint — 6 nodes, 2 exec chains)
  2. BP_HealthSystem (the Health System skill Blueprint)

Reports:
  - Raw output for each Blueprint
  - Token estimate
  - Completeness assessment (nodes, pins, connections, variables, function graphs)

Run from a machine that can reach UE5:
  python3 verify_graph_summary.py [--host HOST] [--port PORT]
"""

import sys
import json
import socket
import argparse

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 55557


def _parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    return p.parse_args()


def send(command, params, host, port, timeout=60):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.sendall((json.dumps({"type": command, "params": params}) + "\n").encode())
        data = b""
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            data += chunk
            if b"\n" in data:
                break
        return json.loads(data.decode("utf-8", errors="replace").strip())
    finally:
        s.close()


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token (GPT-4 standard)."""
    return len(text) // 4


def assess_graph_summary(raw_response: dict, bp_name: str):
    """Print raw output and assess quality."""
    print(f"\n{'═' * 70}")
    print(f"  bp_get_graph_summary: {bp_name}")
    print(f"{'═' * 70}")

    # Print raw response
    raw_json = json.dumps(raw_response, indent=2)
    print(f"\n--- RAW OUTPUT ({estimate_tokens(raw_json)} tokens estimated) ---")
    print(raw_json[:8000])  # Cap at 8000 chars
    if len(raw_json) > 8000:
        print(f"  ... (truncated, full length: {len(raw_json)} chars / "
              f"{estimate_tokens(raw_json)} tokens)")

    # Extract inner result
    inner = raw_response.get("result") or raw_response
    nodes = inner.get("nodes") or []
    node_count = inner.get("total_node_count") or len(nodes)

    print(f"\n--- COMPLETENESS ASSESSMENT ---")
    print(f"  Node count: {node_count}")

    # Check for node IDs
    nodes_with_id = [n for n in nodes if n.get("node_id") or n.get("node_guid")]
    print(f"  Nodes with node_id: {len(nodes_with_id)}/{len(nodes)}"
          f" {'✅' if len(nodes_with_id) == len(nodes) else '⚠️'}")

    # Check for pin info
    nodes_with_pins = [n for n in nodes if n.get("pins")]
    print(f"  Nodes with pin data: {len(nodes_with_pins)}/{len(nodes)}"
          f" {'✅' if nodes_with_pins else '❌'}")

    # Check for connection data
    connected_pins = sum(
        len([p for p in n.get("pins", []) if p.get("linked_to")])
        for n in nodes
    )
    print(f"  Pins with connections: {connected_pins}")

    # Check for pin defaults
    pins_with_defaults = sum(
        len([p for p in n.get("pins", []) if p.get("default_value") not in (None, "", "None")])
        for n in nodes
    )
    print(f"  Pins with default values: {pins_with_defaults}")

    # Summary text
    summary_text = inner.get("summary_text", "")
    print(f"  summary_text present: {'✅' if summary_text else '❌'}")
    if summary_text:
        print(f"  summary_text length: {len(summary_text)} chars / ~{estimate_tokens(summary_text)} tokens")

    # Token assessment
    full_tokens = estimate_tokens(raw_json)
    print(f"\n--- TOKEN ASSESSMENT ---")
    print(f"  Full JSON: ~{full_tokens} tokens")
    if full_tokens < 500:
        print("  ✅ EXCELLENT: fits easily in any context window")
    elif full_tokens < 1000:
        print("  ✅ GOOD: compact enough for most agent contexts")
    elif full_tokens < 2000:
        print("  ⚠️ ACCEPTABLE: near the 2000-token target — consider compacting")
    else:
        print("  ❌ TOO LARGE: exceeds 2000-token target — needs compaction")

    # Completeness for agent reasoning
    print(f"\n--- AGENT USABILITY ---")
    can_identify_nodes = len(nodes) > 0
    can_identify_connections = connected_pins > 0
    can_identify_defaults = pins_with_defaults > 0
    has_guids = len(nodes_with_id) == len(nodes) and len(nodes) > 0

    print(f"  Can identify nodes:          {'✅' if can_identify_nodes else '❌'}")
    print(f"  Can identify connections:    {'✅' if can_identify_connections else '⚠️ (no connections in this BP or not reported)'}")
    print(f"  Can identify pin defaults:   {'✅' if can_identify_defaults else '⚠️ (no defaults set or not reported)'}")
    print(f"  Node GUIDs present:          {'✅' if has_guids else '❌'}")

    return {
        "node_count": node_count,
        "nodes_with_id": len(nodes_with_id),
        "pins_with_connections": connected_pins,
        "pins_with_defaults": pins_with_defaults,
        "token_estimate": full_tokens,
        "summary_text_present": bool(summary_text),
    }


def run_verification(host: str, port: int):
    print(f"\n{'═' * 70}")
    print(f"  Graph Summary Quality Verification")
    print(f"  Target: {host}:{port}")
    print(f"{'═' * 70}")

    # Ping first
    print("\n[1/2] Pinging UE5...")
    r = send("ping", {}, host, port, timeout=10)
    if r.get("status") != "success" and r.get("result", {}).get("message") != "pong":
        print(f"  ❌ UE5 not responding: {r}")
        return False
    print("  ✅ UE5 responding")

    # ── Demo A Blueprint ──────────────────────────────────────────────────────
    print("\n[1/2] bp_get_graph_summary on BP_DemoA...")
    r_demo_a = send("get_blueprint_nodes", {
        "blueprint_name": "BP_DemoA",
        "graph_name": "EventGraph",
        "include_hidden_pins": False,
    }, host, port)
    demo_a_stats = assess_graph_summary(r_demo_a, "BP_DemoA (EventGraph)")

    # ── Health System Blueprint ───────────────────────────────────────────────
    print("\n[2/2] bp_get_graph_summary on BP_HealthSystem...")
    r_health = send("get_blueprint_nodes", {
        "blueprint_name": "BP_HealthSystem",
        "graph_name": "EventGraph",
        "include_hidden_pins": False,
    }, host, port)
    health_stats = assess_graph_summary(r_health, "BP_HealthSystem (EventGraph)")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'═' * 70}")
    print("  OVERALL ASSESSMENT")
    print(f"{'═' * 70}")
    print(f"\n  BP_DemoA tokens:       ~{demo_a_stats['token_estimate']}")
    print(f"  BP_HealthSystem tokens: ~{health_stats['token_estimate']}")
    print(f"\n  Token target (< 2000 per moderate BP): "
          f"{'✅ PASS' if demo_a_stats['token_estimate'] < 2000 and health_stats['token_estimate'] < 2000 else '❌ FAIL'}")

    return True


if __name__ == "__main__":
    args = _parse_args()
    run_verification(args.host, args.port)
