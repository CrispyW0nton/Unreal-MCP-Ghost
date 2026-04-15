"""
fix_blueprint_connections.py
Fixes disconnected nodes and compile errors in ThePlayerCharacter Event Graph.

Issues resolved:
1. BreakHitResult nodes (x3) had no 'Hit' input connected → Cast nodes had
   undetermined Object type, causing 3x "Object Wildcard" fatal errors.
2. SphereOverlapActors ObjectTypes pin had static default (ObjectTypeQuery1)
   that triggered "Array inputs must have input wired" warning — resolved by
   the prior deletion of the orphan GetAllActorsOfClass chains.
3. Orphan K2_DestroyActor at y=672 (no exec connections at all) was removed.

Result: ThePlayerCharacter compiles with 0 fatal issues, 0 warnings.
"""
import sys
sys.path.insert(0, '/home/user/webapp')
import mcp_client
import asyncio

BP = 'ThePlayerCharacter'

# Node GUIDs (verified from live blueprint query)
BREAK_SHOTGUN        = '0DBADBAC414E7E0918A29F942AF54D80'  # y=-112
BREAK_HACK_200       = '610F3FE841E77FA75845B0B611CA8DD1'  # y=1536
BREAK_HACK_80        = '6E01104F483DF0F55B97209461CD45E0'  # y=2048
SPHERE_TRACE_SHOTGUN = '0302348545764BC8C887B0AD780CE5A5'  # y=-32
SPHERE_TRACE_200     = 'ED251A004FF74B70230CE1804FDA9DA5'  # y=1536
SPHERE_TRACE_80      = 'AD5BFEB04823FA393BF9ECA2E007AC27'  # y=2304


async def connect(src_node, src_pin, tgt_node, tgt_pin):
    r = await mcp_client.call_tool('connect_blueprint_nodes', {
        'blueprint_name': BP,
        'source_node_id': src_node,
        'source_pin': src_pin,
        'target_node_id': tgt_node,
        'target_pin': tgt_pin,
    })
    ok = r.get('success', False) or r.get('connection_verified', False)
    print(f"  {src_node[:8]}.{src_pin} -> {tgt_node[:8]}.{tgt_pin}: {'OK' if ok else 'FAIL '+str(r)}")
    return ok


async def main():
    print("=== Wire SphereTrace.OutHit -> BreakHitResult.Hit ===")
    await connect(SPHERE_TRACE_SHOTGUN, 'OutHit', BREAK_SHOTGUN,  'Hit')
    await connect(SPHERE_TRACE_200,     'OutHit', BREAK_HACK_200, 'Hit')
    await connect(SPHERE_TRACE_80,      'OutHit', BREAK_HACK_80,  'Hit')

    print("\n=== Compile ===")
    r = await mcp_client.call_tool('compile_blueprint', {'blueprint_name': BP})
    print(f"  compiled={r.get('compiled')}, had_errors={r.get('had_errors')}")
    msgs = r.get('compile_results', [])
    print(f"  Messages: {msgs if msgs else 'none (clean)'}")


if __name__ == '__main__':
    asyncio.run(main())
