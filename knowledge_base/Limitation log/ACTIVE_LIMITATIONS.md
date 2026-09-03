# Active Limitations

## Unreal Editor / Build Workflow

- [ ] LIM-0001 - New native `UCLASS` and plugin routes do not reliably load through Live Coding alone
  - Impact: Insanitii native class additions and new UnrealMCP C++ routes may be invisible until the editor reloads the module from a clean build.
  - Evidence: `knowledge_base/Projects/Insanitii/Phase2_Lifestyle_Framework_Slice1_2026-05-17.md`, `knowledge_base/Projects/Insanitii/Phase8_Readiness_Workflow_2026-05-17.md`, `knowledge_base/Projects/Insanitii/Plugin_Sync_2026-05-18.md`, `knowledge_base/Projects/Insanitii/Phase2A_Daily_Actions_2026-05-18.md`, and `knowledge_base/Projects/Insanitii/Crash_Recovery_2026-05-18.md`.
  - Workaround: For reflected C++ changes, close Unreal Editor and Live Coding, run `Build.bat InsanitiiEditor Win64 Development`, reopen the project, verify reflection/actor counts, then save assets. Avoid saving dirty levels from a session that has Live Coding patch DLLs for new or changed reflected APIs.
  - Fix target: Documented reload workflow first; later investigate safer plugin hot-reload or explicit editor restart automation with dirty-package preflight and post-reload validation.
  - Removal test: Add a native C++ route/class, reload without closing the editor, and verify the route/class is visible through MCP and UE reflection.

- [ ] LIM-0002 - Command-line UBT builds are blocked while Live Coding is active
  - Impact: A normal `Build.bat` verification cannot complete while the running editor owns Live Coding state.
  - Evidence: `Plugin_Sync_2026-05-18.md` records `Unable to build while Live Coding is active`.
  - Workaround: Use editor Live Coding for small changes, or close Unreal Editor before command-line builds.
  - Fix target: Workflow/tooling. Add a preflight build helper that detects UnrealEditor/LiveCoding and reports the exact next action.
  - Removal test: Helper reliably distinguishes buildable state from blocked state and gives a one-command or one-action recovery path.

## UE Python / Editor API Gaps

- [ ] LIM-0003 - UE Python does not expose `unreal.KismetEditorUtilities` in this environment
  - Impact: Direct Python Blueprint compile/save workflows are unreliable for Insanitii automation.
  - Evidence: `Phase2_Lifestyle_Framework_Slice1_2026-05-17.md`.
  - Workaround: Use MCP bridge routes `compile_blueprint` and `save_blueprint`.
  - Fix target: Python server docs and tooling guardrails; avoid direct Python compile paths when the bridge has a native route.
  - Removal test: Either UE Python compile utilities are available and verified, or all project automation has migrated to reliable native MCP compile/save routes.

- [ ] LIM-0008 - Large combined UE Python level-authoring payloads can crash the bridge/editor
  - Impact: A single `exec_python` payload that loads a level, spawns/configures multiple actors, and saves the map can trip the bridge's guarded native access-violation path and may exit the running Unreal Editor session.
  - Evidence: `knowledge_base/Projects/Insanitii/Phase3_Ordinary_Errand_Task_Expansion_2026-06-02.md` records a crash while placing the grocery/laundry/package/commute stations through one large `exec_python` payload.
  - Workaround: Split level-authoring automation into small calls: first probe editor health, then spawn/configure one actor per `exec_python` call through `EditorActorSubsystem`, then save separately through `LevelEditorSubsystem.save_current_level()`.
  - Fix target: Add a safer MCP level-authoring wrapper that batches operations on the Python side but sends them to Unreal in bounded chunks, with bridge health checks between chunks and a separate save phase.
  - Removal test: The wrapper can place and save at least four `AInsanitiiTaskStation` actors in `Lvl_FirstPerson` without editor exit, then a follow-up objective report sees all expected stations.

## Project Readiness / Smoke Coverage

- [ ] LIM-0004 - Some Insanitii readiness checks still require Python fallbacks when native smoke routes are not reloaded
  - Impact: Read-only validation can continue, but native class-chain matching and newer route coverage may be stale in a running editor.
  - Evidence: `Phase8_Readiness_Workflow_2026-05-17.md`.
  - Workaround: Use `exec_python` fallback probes for static readiness, then perform a clean editor restart/build before relying on new native routes.
  - Fix target: Plugin reload workflow plus readiness report messaging.
  - Removal test: `insanitii_phase1_readiness_report()` uses first-class native routes without fallback warnings after a clean plugin build/reload.

- [ ] LIM-0005 - PIE launch/readback is asynchronous and active-PIE `exec_python` payload capture is unreliable
  - Impact: A PIE request can return before the PIE world exists, and deeper runtime probes during active PIE may return empty output even when the command reports success.
  - Evidence: `knowledge_base/Projects/Insanitii/Phase2A_HUD_Daily_Loop_Surface_2026-05-18.md` and `knowledge_base/Projects/Insanitii/Phase3_PIE_Runtime_Probe_2026-06-02.md`.
  - Workaround: For Insanitii, use `insanitii_phase3_pie_runtime_report`, which splits launch/status/probe/stop into separate bridge calls so editor ticks can occur between phases. Generic PIE helpers may still need the same hardening.
  - Fix target: Migrate the async-safe launch/probe/stop pattern from the Insanitii report into generic MCP `pie_launch_session`, `pie_runtime_probe`, and `pie_stop_session` workflows.
  - Removal test: Generic PIE tools, not only the Insanitii-specific report, launch PIE, wait until `pie_world_count > 0`, return player controller/pawn/HUD/manager facts, and stop PIE cleanly.

## Browser / Authenticated Content Generation

- [ ] LIM-0007 - Chrome plugin kernel is unstable; ElevenLabs generation works but download/playback remains gated
  - Impact: Authenticated ElevenLabs/Tripo browser work for Insanitii still cannot proceed through the Codex Chrome plugin because the node-backed kernel exits. Local `ChromeMCP` CDP tools can now see the authenticated ElevenLabs and Tripo tabs, but ElevenLabs Sound Effects kept generated variants unplayable and direct downloads disabled.
  - Evidence: On 2026-06-02, repeated Chrome plugin attempts failed with `node_repl kernel exited unexpectedly` and `windows sandbox failed: setup refresh failed with status exit code: 1`. Later `ChromeMCP chrome_tabs` exposed the signed-in Tripo tab and ElevenLabs Sound Effects tab. The ElevenLabs tab showed `ElevenCreative`, `50 credits / 10,000 credits`, generated two Insanitii sound-effect history entries, and moved to `50 credits / 9,600 credits`; after refresh, Play remained inert, Download buttons stayed disabled, and no audio media URL was exposed.
  - Workaround: Record ElevenLabs history IDs in Insanitii docs and use local generated placeholder WAVs imported into `/Game/Insanitii/Audio/Generated` for the playable slice. Continue using `ChromeMCP` only for authenticated UI observation/actions that do not inspect credentials or session stores.
  - Fix target: Restore Codex Chrome plugin runtime stability and/or determine why ElevenLabs Sound Effects download/playback is disabled for the signed-in workspace despite available credits.
  - Removal test: Chrome control can claim authenticated ElevenLabs/Tripo tabs, ElevenLabs generated Sound Effects expose playable media/downloadable audio, and imported Unreal SoundWave placeholders can be replaced by the ElevenLabs files.
