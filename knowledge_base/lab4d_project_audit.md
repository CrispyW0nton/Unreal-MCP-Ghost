# Lab4D Project Audit
> Project: `C:\Users\NewAdmin\Documents\Academy of Art University\2026\Gam115\UnrealProject\Lab4D`
> Audit date: 2026-04-29
> Status: Blocked for live editor inspection; partial config/log evidence captured.

## Live MCP Status

The MCP SSE server at `http://127.0.0.1:8000/sse` is reachable and lists the expected Unreal-MCP tools. Tools that require a live Unreal bridge are not connected:

- `exec_python` returned `{"success": false, "message": "Not connected to Unreal Engine"}`.
- `project_find_assets` returned `ERR_UNREAL_NOT_CONNECTED`.
- Direct socket probe to `127.0.0.1:55557` failed.
- `get_actors_in_level` returned `[]`, but because stronger bridge checks failed, this should not be interpreted as a confirmed empty level.

## Project Configuration Evidence

`Lab4D.uproject` targets UE `5.6` and contains the `UnrealMCP` plugin entry with `"Enabled": false`. This likely explains why the editor is open but the plugin bridge is not listening on `55557`.

`DefaultEngine.ini` configures:

- Editor startup map: `/Game/Lab-0X.Lab-0X`
- Game default map: `/Game/Lab-0X.Lab-0X`
- Global default GameMode: `/Game/TopDown/Blueprints/BP_TopDownGameMode.BP_TopDownGameMode_C`
- Recast navmesh settings with agent radius `34`, agent height `144`, max slope `44`, max step height `35`
- DX12 / SM6 rendering, Lumen-style renderer settings, ray tracing enabled

`DefaultInput.ini` uses Enhanced Input component classes, but also includes legacy action/axis mappings:

- Action: `Jump` mapped to `SpaceBar` and `Gamepad_FaceButton_Bottom`
- Axis: move forward/backward via `W`, `S`, `Gamepad_LeftY`
- Axis: move right/left via `A`, `D`, `Gamepad_LeftX`
- Axis: look/turn via mouse and gamepad right stick

## Editor Log Evidence

The current log shows the editor loaded:

- Map file: `Content/Lab-0X.umap`
- World: `/Game/Lab-0X.Lab-0X`
- World Partition enabled for `Lab-0X`
- Map check completed with `0 Error(s), 0 Warning(s)`
- Asset registry discovered `8011` uncontrolled assets

Warnings observed:

- Repeated Nanite warnings for additive materials `RedBeam` and `GreenBeam` used on static mesh `arrow-basic`; Nanite only supports opaque or masked blend modes unless Nanite is disabled for the mesh/component.
- Several missing Slate editor icon resources from engine content paths; these appear editor-resource warnings rather than project gameplay failures.

## Gameplay Systems Identified From Secondary Evidence

Prior saved MCP snapshots reference these Blueprint/system names:

- `ThePlayerCharacter`
- `BP_DefenseLaser`
- `BP_PacifistDrone`
- `BP_WarDrone`
- `BP_DroneFactory`
- `BP_LaserTurret`
- `BP_Bullet`

Captured CDO/default values include:

- `ThePlayerCharacter`: `CoreHealth=100.0`, `ShieldCharges=3`, `IsDisabled=False`, `PacifistDroneClass=/Game/Blueprints/BP_PacifistDrone`
- `BP_WarDrone`: `DroneHealth=5`
- `BP_LaserTurret`: `bIsShutdown=False`, `BulletClass=/Game/Blueprints/BP_Bullet`
- `BP_DroneFactory`: `bPlayerInRange=False`
- `BP_DefenseLaser`: `bOnCooldown=False`

These are not a substitute for live Blueprint graph inspection.

## Required Next Step

Enable the `UnrealMCP` plugin for `Lab4D`, restart the editor, and confirm that `127.0.0.1:55557` accepts connections. Then rerun:

- `get_actors_in_level`
- `project_find_assets`
- `get_blueprint_graphs`
- `get_blueprint_nodes`
- `get_blueprint_components`
- `get_blueprint_variables`
- `get_blueprint_functions`

Until that is done, actor inventory, Blueprint logic mapping, UI wiring, AI setup, collision setup, and current world settings cannot be verified through the live editor.
