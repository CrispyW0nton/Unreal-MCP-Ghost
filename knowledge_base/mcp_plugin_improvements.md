# MCP Plugin Improvements
> Audit date: 2026-04-29
> Context: Lab4D audit attempt through Unreal-MCP-Ghost.

## What Worked Well

- The SSE MCP server at `http://127.0.0.1:8000/sse` was reachable.
- Tool discovery worked and exposed the expected Unreal-MCP command surface, including actor, asset, Blueprint, UMG, AI, animation, diagnostics, graph, and project intelligence tools.
- Read-only server-side tools returned structured errors for disconnected editor state, especially `project_find_assets` with `ERR_UNREAL_NOT_CONNECTED`.
- The existing knowledge base accurately predicted useful audit tools and known Blueprint Python reflection pitfalls.

## Limitations Encountered

- The UE editor bridge at `127.0.0.1:55557` was not listening.
- `Lab4D.uproject` contains the `UnrealMCP` plugin with `"Enabled": false`, so the editor can be open while MCP tools still cannot reach it.
- `get_actors_in_level` returned `[]` instead of a clearly disconnected error, while `exec_python` and `project_find_assets` correctly reported not connected. This inconsistency can mislead an audit into treating a disconnected bridge as an empty level.
- Historical saved MCP snapshots show brittle Python API reflection failures for Blueprint variables and graph internals.

## Proposed Enhancements

1. Add a `ue_connection_status` MCP tool that checks:
   - MCP server process status
   - bridge host/port reachability
   - current project name/path if connected
   - current map if connected
   - plugin enabled state if discoverable

2. Normalize disconnected behavior across all tools:
   - `get_actors_in_level` should return a structured `ERR_UNREAL_NOT_CONNECTED` result when the bridge is unavailable instead of `[]`.
   - Empty actor arrays should be reserved for confirmed connected editor sessions.

3. Add a project preflight tool:
   - Given a `.uproject` path, report whether `UnrealMCP` is present and enabled.
   - Warn if the project has a copied plugin folder but the `.uproject` plugin entry is disabled.

4. Add a one-shot audit bundle tool:
   - current map and world settings
   - actor inventory
   - asset counts by class
   - Blueprint list
   - Blueprint graphs and node summaries
   - GameMode/PlayerController/Pawn/GameState/GameInstance settings

5. Prefer native graph diagnostics over raw Python Blueprint internals:
   - Use `get_blueprint_nodes`, `bp_get_graph_summary`, and `bp_get_graph_detail`.
   - Keep Python fallbacks behind version-checked wrappers.

## Straightforward Fix Candidate

Implemented in `unreal_mcp_server/tools/editor_tools.py`:

- `get_actors_in_level` now returns a structured JSON error object when no Unreal connection exists.
- Connected success responses still return the historical compact JSON actor array.
- Syntax was verified with `python -m compileall unreal_mcp_server/tools/editor_tools.py`.

Remaining follow-up: apply the same disconnected-error normalization to other list-style tools such as `find_actors_by_name`.

## Project Recovery Step

For Lab4D specifically, enable the plugin in `Lab4D.uproject`, restart the editor, and verify port `55557` before rerunning the audit.
