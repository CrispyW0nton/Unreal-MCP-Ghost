# Lab4D Actor Inventory
> Audit date: 2026-04-29
> Status: Live actor inventory blocked because the Unreal editor bridge is not connected.

## Live Query Attempts

- MCP SSE server: reachable at `http://127.0.0.1:8000/sse`
- Direct UE bridge: `127.0.0.1:55557` refused connection
- `exec_python`: returned `Not connected to Unreal Engine`
- `project_find_assets`: returned `ERR_UNREAL_NOT_CONNECTED`
- `get_actors_in_level`: returned `[]`, but this is not trusted because the stronger bridge checks failed

## Current Level Evidence

Config and log evidence indicate:

- Editor startup map: `/Game/Lab-0X.Lab-0X`
- Game default map: `/Game/Lab-0X.Lab-0X`
- Editor loaded map file: `Content/Lab-0X.umap`
- Loaded world name: `Lab-0X`
- World Partition: enabled
- Map check: `0 Error(s), 0 Warning(s)`

## Actor Inventory

Not available until the editor bridge is restored. The following data must be collected with `get_actors_in_level` and per-actor property reads:

- Actor label/name
- Class
- Location, rotation, scale
- Component summary
- Collision profile and overlap settings
- Notable Blueprint variables/defaults
- References to gameplay systems such as player, drones, turrets, bullets, lasers, factory actors, nav volumes, and UI spawners

## Known Blueprint Classes From Saved MCP Data

These names likely correspond to placed actors or spawnable classes, but placement is unverified:

- `ThePlayerCharacter`
- `BP_DefenseLaser`
- `BP_PacifistDrone`
- `BP_WarDrone`
- `BP_DroneFactory`
- `BP_LaserTurret`
- `BP_Bullet`

## Required Re-Audit Command Set

After enabling `UnrealMCP` and restarting the editor:

1. Run `get_actors_in_level`.
2. For every returned actor, run `get_actor_properties`.
3. For every Blueprint class in actor results, run `get_blueprint_components`, `get_blueprint_variables`, and `get_blueprint_graphs`.
4. For every graph with logic, run `get_blueprint_nodes`.
5. Update this file with verified actor rows.
