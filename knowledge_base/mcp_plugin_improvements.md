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

For Lab4D specifically, `UnrealMCP` was enabled in `Lab4D.uproject`, the editor was launched, and port `55557` was verified open. The Phase 2 live audit then completed.

## Phase 2 Tool Results

Worked well:

- `exec_python` successfully gathered a full level/asset/actor snapshot.
- `get_blueprint_graphs` worked for all 8 Blueprint assets.
- `get_blueprint_nodes` worked after passing the exact `graph_name` string from `get_blueprint_graphs`.
- `get_blueprint_components`, `get_blueprint_variables`, and `get_blueprint_functions` worked for Blueprint-level introspection.

Limitations:

- The running MCP server still returned `[]` for disconnected `get_actors_in_level` until restarted with the newer server wrapper code; use `exec_python` or restart the server to pick up the fixed behavior.
- UE Python returned Enhanced Input `Key` structs without readable key names through the simple `str(key)` path.
- `InputSettings.get_action_mappings()` was unavailable in this UE 5.6 Python object; config file reading remains the reliable fallback for legacy mappings.
- `get_blueprint_graphs` returns graph objects with `graph_name`; automation must extract that field, not stringify the graph object.

Useful follow-up improvements:

- Add a first-class `audit_project_snapshot` tool to return levels, assets, actors, framework settings, and inputs in one structured result.
- Add readable Enhanced Input mapping extraction.
- Add a Blueprint graph summarizer that returns events/functions/variables/casts without requiring agents to post-process raw node dumps.
