"""
Editor Tools - Actor management, viewport, spawning.
Ported from: https://github.com/chongdashu/unreal-mcp
"""
import json
import logging
import sys
import textwrap
import time
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def _send_unreal_command(command: str, params: Dict[str, Any]) -> Dict[str, Any]:
    from unreal_mcp_server import get_unreal_connection

    unreal = get_unreal_connection()
    if not unreal:
        return {"success": False, "message": "Not connected to Unreal Engine"}
    return unreal.send_command(command, params) or {
        "success": False,
        "message": "No response from Unreal Engine",
    }


def _parse_exec_python_json(response: Dict[str, Any]) -> Dict[str, Any]:
    inner = (response or {}).get("result") or response or {}
    output = inner.get("output", "") or ""
    command_result = inner.get("command_result", "") or ""
    candidates: List[str] = []

    for line in output.splitlines():
        line = line.strip()
        if line.startswith("[Info] "):
            line = line[len("[Info] "):].strip()
        candidates.append(line)
    if command_result:
        candidates.append(command_result.strip())

    for line in reversed(candidates):
        if not line:
            continue
        if (line.startswith("{") and line.endswith("}")) or (line.startswith("[") and line.endswith("]")):
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    return parsed
                return {"success": True, "items": parsed}
            except json.JSONDecodeError:
                continue

    if inner.get("success") is False or (response or {}).get("status") == "error":
        return {
            "success": False,
            "message": inner.get("error") or inner.get("message") or output or "exec_python failed",
        }
    return {"success": False, "message": f"Could not parse exec_python JSON output: {output!r}"}


def _is_unknown_command(response: Dict[str, Any], command: str) -> bool:
    if not isinstance(response, dict):
        return False
    message = str(response.get("error") or response.get("message") or "")
    return response.get("status") == "error" and f"Unknown command: {command}" in message


def _exec_python_json(code: str) -> Dict[str, Any]:
    return _parse_exec_python_json(_send_unreal_command("exec_python", {"code": code}))


def _native_or_python_json(command: str, params: Dict[str, Any], fallback_code: str) -> Dict[str, Any]:
    native = _send_unreal_command(command, params)
    if not _is_unknown_command(native, command):
        native.setdefault("transport", "native")
        return native

    fallback = _exec_python_json(fallback_code)
    fallback["transport"] = "exec_python_fallback"
    fallback["native_unavailable"] = True
    fallback["native_error"] = native.get("error") or native.get("message")
    return fallback


def _insanitii_actor_fallback_code(actor_name_or_label: str = "INS_") -> str:
    return textwrap.dedent(f"""
        import json, unreal

        def _class_chain(cls):
            names = []
            seen = set()
            while cls and cls not in seen:
                seen.add(cls)
                try:
                    names.append(cls.get_name())
                    cls = cls.get_super_class()
                except Exception:
                    break
            return names

        needle = {json.dumps(actor_name_or_label)}.lower()
        actors = []
        for actor in unreal.EditorLevelLibrary.get_all_level_actors():
            label = actor.get_actor_label()
            name = actor.get_name()
            full_path = actor.get_path_name()
            if needle and needle not in label.lower() and needle not in name.lower() and needle not in full_path.lower():
                continue
            cls = actor.get_class()
            actors.append({{
                "label": label,
                "name": name,
                "path": full_path,
                "class_name": cls.get_name() if cls else "",
                "class_path": cls.get_path_name() if cls else "",
                "native_class_chain": _class_chain(cls),
            }})

        print(json.dumps({{"success": True, "count": len(actors), "actors": actors}}))
    """)


def _insanitii_class_fallback_code(class_name: str) -> str:
    return textwrap.dedent(f"""
        import json, unreal

        def _class_chain(cls):
            names = []
            seen = set()
            while cls and cls not in seen:
                seen.add(cls)
                try:
                    names.append(cls.get_name())
                    cls = cls.get_super_class()
                except Exception:
                    break
            return names

        needle = {json.dumps(class_name)}.lower()
        actors = []
        for actor in unreal.EditorLevelLibrary.get_all_level_actors():
            cls = actor.get_class()
            chain = _class_chain(cls)
            haystack = [cls.get_name() if cls else "", cls.get_path_name() if cls else ""] + chain
            if not any(needle in str(item).lower() for item in haystack):
                continue
            actors.append({{
                "label": actor.get_actor_label(),
                "name": actor.get_name(),
                "path": actor.get_path_name(),
                "class_name": cls.get_name() if cls else "",
                "class_path": cls.get_path_name() if cls else "",
                "native_class_chain": chain,
            }})

        print(json.dumps({{"success": True, "count": len(actors), "actors": actors}}))
    """)


def _insanitii_blueprint_fallback_code(blueprint_path_or_name: str) -> str:
    return textwrap.dedent(f"""
        import json, unreal

        query = {json.dumps(blueprint_path_or_name)}
        known_paths = {{
            "BP_InsanitiiGameMode": "/Game/Insanitii/Core/Blueprints/BP_InsanitiiGameMode",
            "BP_InsanitiiPlayerController": "/Game/Insanitii/Core/Blueprints/BP_InsanitiiPlayerController",
            "BP_RuntimeBootstrap": "/Game/Insanitii/Core/Blueprints/BP_RuntimeBootstrap",
            "BP_MentalStateComponent": "/Game/Insanitii/Core/Components/BP_MentalStateComponent",
            "BP_InteractionDetector": "/Game/Insanitii/Core/Components/BP_InteractionDetector",
            "BP_TestInteractable": "/Game/Insanitii/Gameplay/Interactions/BP_TestInteractable",
            "BP_PostProcessController": "/Game/Insanitii/VFX/PostProcess/BP_PostProcessController",
            "BP_InsanitiiHUD": "/Game/Insanitii/UI/HUD/BP_InsanitiiHUD",
        }}
        candidates = []
        if query.startswith("/"):
            candidates.append(query)
        if query in known_paths:
            candidates.append(known_paths[query])
        try:
            for asset_path in unreal.EditorAssetLibrary.list_assets("/Game/Insanitii", recursive=True, include_folder=False):
                asset_name = asset_path.rsplit("/", 1)[-1].split(".", 1)[0]
                if asset_name == query:
                    candidates.append(asset_path)
        except Exception:
            pass

        asset = None
        chosen = ""
        for candidate in candidates:
            asset = unreal.load_asset(candidate)
            if asset:
                chosen = candidate
                break

        generated = None
        parent = None
        if asset:
            try:
                generated_attr = getattr(asset, "generated_class", None)
                generated = generated_attr() if callable(generated_attr) else None
            except Exception:
                generated = None
            try:
                parent = generated.get_super_class() if generated else None
            except Exception:
                parent = None

        print(json.dumps({{
            "success": bool(asset),
            "asset_path": chosen,
            "asset_name": asset.get_name() if asset else query,
            "has_generated_class": bool(generated),
            "generated_class": generated.get_path_name() if generated else "",
            "parent_class": parent.get_path_name() if parent else "",
        }}))
    """)


def _insanitii_imc_fallback_code(imc_path_or_name: str) -> str:
    return textwrap.dedent(f"""
        import json, unreal

        query = {json.dumps(imc_path_or_name)}
        query_name = query.rsplit("/", 1)[-1].split(".", 1)[0]
        candidates = [query] if query.startswith("/") else []
        if query_name == "IMC_Default":
            candidates.append("/Game/Input/IMC_Default")
            candidates.append("/Game/Input/IMC_Default.IMC_Default")
        try:
            for asset_path in unreal.EditorAssetLibrary.list_assets("/Game", recursive=True, include_folder=False):
                asset_name = asset_path.rsplit("/", 1)[-1].split(".", 1)[0]
                if asset_name == query_name:
                    candidates.append(asset_path)
        except Exception:
            pass

        asset = None
        chosen = ""
        for candidate in candidates:
            asset = unreal.load_asset(candidate)
            if asset:
                chosen = candidate
                break

        mappings = []
        if asset:
            try:
                raw_mappings = asset.get_editor_property("mappings")
            except Exception:
                raw_mappings = []
            for mapping in raw_mappings:
                action = None
                key = None
                try:
                    action = mapping.get_editor_property("action")
                except Exception:
                    pass
                try:
                    key = mapping.get_editor_property("key")
                except Exception:
                    pass
                mappings.append({{
                    "action_name": action.get_name() if action else "",
                    "action_path": action.get_path_name() if action else "",
                    "key": str(key) if key else "",
                }})

        print(json.dumps({{
            "success": bool(asset),
            "asset_path": chosen,
            "mapping_count": len(mappings),
            "mappings": mappings,
        }}))
    """)


def _insanitii_phase2_lifestyle_fallback_code() -> str:
    return textwrap.dedent("""
        import json, unreal

        class_paths = {
            "time_of_day_component": "/Script/Insanitii.InsanitiiTimeOfDayComponent",
            "economy_component": "/Script/Insanitii.InsanitiiEconomyComponent",
            "lifestyle_manager": "/Script/Insanitii.InsanitiiLifestyleManager",
        }
        blueprint_path = "/Game/Insanitii/Gameplay/Lifestyles/BP_LifestyleManager"
        actor_label = "INS_LifestyleManager"

        class_checks = {}
        for key, path in class_paths.items():
            cls = unreal.load_class(None, path)
            class_checks[key] = {
                "success": bool(cls),
                "class_path": path,
                "loaded_name": cls.get_name() if cls else "",
            }

        asset = unreal.load_asset(blueprint_path)
        generated = None
        parent = None
        if asset:
            try:
                generated_attr = getattr(asset, "generated_class", None)
                generated = generated_attr() if callable(generated_attr) else None
            except Exception:
                generated = None
            try:
                parent = generated.get_super_class() if generated else None
            except Exception:
                parent = None
        blueprint_check = {
            "success": bool(asset),
            "asset_path": blueprint_path,
            "has_generated_class": bool(generated),
            "generated_class": generated.get_path_name() if generated else "",
            "parent_class": parent.get_path_name() if parent else "",
        }

        found_actor = None
        for actor in unreal.EditorLevelLibrary.get_all_level_actors():
            if actor.get_actor_label() == actor_label or actor.get_name() == actor_label:
                found_actor = actor
                break

        actor_check = {"success": bool(found_actor), "label": actor_label}
        if found_actor:
            cls = found_actor.get_class()
            actor_check.update({
                "name": found_actor.get_name(),
                "path": found_actor.get_path_name(),
                "class_name": cls.get_name() if cls else "",
                "class_path": cls.get_path_name() if cls else "",
            })

        manager_probe = {
            "success": False,
            "debug_summary": "",
            "task_count": 0,
            "sample_tasks": [],
            "time": {},
            "economy": {},
        }
        if found_actor:
            try:
                summary_fn = getattr(found_actor, "get_debug_summary", None)
                if callable(summary_fn):
                    manager_probe["debug_summary"] = str(summary_fn())
            except Exception as exc:
                manager_probe["debug_summary_error"] = str(exc)

            try:
                jobs_fn = getattr(found_actor, "generate_daily_jobs", None)
                tasks = list(jobs_fn()) if callable(jobs_fn) else []
                manager_probe["task_count"] = len(tasks)
                for task in tasks[:5]:
                    def _prop(name, default=""):
                        try:
                            getter = getattr(task, "get_editor_property", None)
                            value = getter(name) if callable(getter) else getattr(task, name)
                            return str(value)
                        except Exception:
                            return default
                    manager_probe["sample_tasks"].append({
                        "task_id": _prop("task_id"),
                        "display_name": _prop("display_name"),
                        "base_payout": _prop("base_payout"),
                        "mental_state_delta_on_success": _prop("mental_state_delta_on_success"),
                        "mental_state_delta_on_failure": _prop("mental_state_delta_on_failure"),
                    })
            except Exception as exc:
                manager_probe["task_error"] = str(exc)

            try:
                time_component = found_actor.get_editor_property("time_of_day")
                if time_component:
                    formatted_fn = getattr(time_component, "get_formatted_time", None)
                    period_fn = getattr(time_component, "get_current_day_period", None)
                    manager_probe["time"] = {
                        "current_day": int(time_component.get_editor_property("current_day")),
                        "minute_of_day": float(time_component.get_editor_property("current_minute_of_day")),
                        "formatted_time": str(formatted_fn()) if callable(formatted_fn) else "",
                        "period": str(period_fn()) if callable(period_fn) else "",
                    }
            except Exception as exc:
                manager_probe["time_error"] = str(exc)

            try:
                economy = found_actor.get_editor_property("economy")
                if economy:
                    ledger = economy.get_editor_property("ledger")
                    manager_probe["economy"] = {
                        "cash_balance": float(economy.get_editor_property("cash_balance")),
                        "daily_living_cost": float(economy.get_editor_property("daily_living_cost")),
                        "ledger_count": len(ledger) if ledger else 0,
                    }
            except Exception as exc:
                manager_probe["economy_error"] = str(exc)

            manager_probe["success"] = manager_probe["task_count"] > 0

        print(json.dumps({
            "success": True,
            "class_checks": class_checks,
            "blueprint": blueprint_check,
            "actor": actor_check,
            "manager_probe": manager_probe,
        }))
    """)


def _insanitii_phase3_objective_fallback_code() -> str:
    return textwrap.dedent("""
        import json, unreal

        class_paths = {
            "slice_objective_director": "/Script/Insanitii.InsanitiiSliceObjectiveDirector",
            "task_station": "/Script/Insanitii.InsanitiiTaskStation",
            "psychosis_event_director": "/Script/Insanitii.InsanitiiPsychosisEventDirector",
        }
        expected_labels = [
            "INS_SliceObjectiveDirector",
            "INS_PsychosisEventDirector",
            "INS_TaskStation_Work_EmailTriage",
            "INS_TaskStation_Food_Sandwich",
            "INS_TaskStation_Medication",
            "INS_TaskStation_Grocery_Corner",
            "INS_TaskStation_Laundry_Washer",
            "INS_TaskStation_Package_Dropoff",
            "INS_TaskStation_Commute_Car",
            "INS_TaskStation_Sleep_Bed",
            "INS_TaskStation_Stress_OverwhelmingNoise",
        ]

        class_checks = {}
        for key, path in class_paths.items():
            cls = unreal.load_class(None, path)
            class_checks[key] = {
                "success": bool(cls),
                "class_path": path,
                "loaded_name": cls.get_name() if cls else "",
            }

        actors = {actor.get_actor_label(): actor for actor in unreal.EditorLevelLibrary.get_all_level_actors()}
        actor_checks = {}
        for label in expected_labels:
            actor = actors.get(label)
            cls = actor.get_class() if actor else None
            actor_checks[label] = {
                "success": bool(actor),
                "name": actor.get_name() if actor else "",
                "path": actor.get_path_name() if actor else "",
                "class_name": cls.get_name() if cls else "",
                "class_path": cls.get_path_name() if cls else "",
            }

        objective = actors.get("INS_SliceObjectiveDirector")
        objective_probe = {"success": False}
        if objective:
            try:
                objective_probe = {
                    "success": True,
                    "current_objective": str(objective.get_current_objective_text()),
                    "progress_summary": str(objective.get_progress_summary()),
                    "completion_percent": float(objective.get_completion_percent()),
                    "stabilized_target": float(objective.get_editor_property("stabilized_mental_state_target")),
                }
            except Exception as exc:
                objective_probe = {"success": False, "error": str(exc)}

        station_probe = {"count": 0, "stations": []}
        for label, actor in sorted(actors.items()):
            if not label.startswith("INS_TaskStation"):
                continue
            station_probe["count"] += 1
            try:
                station_probe["stations"].append({
                    "label": label,
                    "action": str(actor.get_editor_property("action")),
                    "task_index": int(actor.get_editor_property("task_index")),
                    "mental_state_delta": float(actor.get_editor_property("mental_state_delta")),
                    "prompt_text": str(actor.get_editor_property("prompt_text")),
                    "reusable": bool(actor.get_editor_property("bReusable")),
                })
            except Exception as exc:
                station_probe["stations"].append({"label": label, "error": str(exc)})

        print(json.dumps({
            "success": True,
            "class_checks": class_checks,
            "actors": actor_checks,
            "objective_probe": objective_probe,
            "station_probe": station_probe,
        }))
    """)


def _insanitii_pie_status_code() -> str:
    return textwrap.dedent("""
        import json, unreal

        subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        try:
            pie_worlds = list(unreal.EditorLevelLibrary.get_pie_worlds(False))
        except Exception:
            pie_worlds = []

        print(json.dumps({
            "success": True,
            "is_in_play_in_editor": bool(subsystem.is_in_play_in_editor()),
            "pie_world_count": len(pie_worlds),
            "pie_world_names": [w.get_name() for w in pie_worlds],
        }))
    """)


def _insanitii_pie_launch_request_code(mode: str) -> str:
    return textwrap.dedent(f"""
        import json, unreal

        requested_mode = {mode!r}
        subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        was_in_pie = bool(subsystem.is_in_play_in_editor())
        launch_requested = False
        if not was_in_pie:
            if str(requested_mode).lower() in ("simulate", "sie"):
                subsystem.editor_play_simulate()
                requested_mode = "simulate"
            else:
                subsystem.editor_request_begin_play()
                requested_mode = "play"
            launch_requested = True

        print(json.dumps({{
            "success": True,
            "requested_mode": requested_mode,
            "launch_requested": launch_requested,
            "was_in_pie": was_in_pie,
            "is_in_play_in_editor": bool(subsystem.is_in_play_in_editor()),
        }}))
    """)


def _insanitii_pie_stop_request_code() -> str:
    return textwrap.dedent("""
        import json, unreal

        subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        was_in_pie = bool(subsystem.is_in_play_in_editor())
        if was_in_pie:
            subsystem.editor_request_end_play()
            try:
                unreal.EditorLevelLibrary.editor_end_play()
            except Exception:
                pass

        print(json.dumps({
            "success": True,
            "stop_requested": was_in_pie,
            "is_in_play_in_editor": bool(subsystem.is_in_play_in_editor()),
        }))
    """)


def _insanitii_phase3_pie_runtime_probe_code(
    mode: str,
    wait_seconds: float,
    stop_after_probe: bool,
    exercise_loop: bool,
    allow_launch: bool = True,
) -> str:
    return textwrap.dedent(f"""
        import json, time, unreal

        requested_mode = {mode!r}
        wait_seconds = max(0.5, min(float({wait_seconds!r}), 15.0))
        stop_after_probe = {bool(stop_after_probe)!r}
        exercise_loop = {bool(exercise_loop)!r}
        allow_launch = {bool(allow_launch)!r}

        def _prop(obj, *names, default=None):
            if not obj:
                return default
            for name in names:
                try:
                    return obj.get_editor_property(name)
                except Exception:
                    pass
                try:
                    return getattr(obj, name)
                except Exception:
                    pass
            return default

        def _call(obj, name, *args):
            fn = getattr(obj, name, None)
            if callable(fn):
                return fn(*args)
            raise RuntimeError(f"{{obj.get_name() if obj else 'None'}} has no callable {{name}}")

        def _actors_by_label(world, cls):
            actors = {{}}
            if not world or not cls:
                return actors
            try:
                found = unreal.GameplayStatics.get_all_actors_of_class(world, cls)
            except Exception:
                found = []
            for actor in found:
                label = ""
                try:
                    label = actor.get_actor_label()
                except Exception:
                    label = actor.get_name()
                actors[label] = actor
            return actors

        subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        was_in_pie = bool(subsystem.is_in_play_in_editor())
        launch_requested = False
        if not was_in_pie and allow_launch:
            if str(requested_mode).lower() in ("simulate", "sie"):
                subsystem.editor_play_simulate()
                requested_mode = "simulate"
            else:
                subsystem.editor_request_begin_play()
                requested_mode = "play"
            launch_requested = True

        deadline = time.time() + wait_seconds
        pie_worlds = []
        while time.time() < deadline:
            try:
                pie_worlds = list(unreal.EditorLevelLibrary.get_pie_worlds(False))
            except Exception:
                pie_worlds = []
            if pie_worlds:
                break
            time.sleep(0.25)

        world = pie_worlds[0] if pie_worlds else None
        if world is None:
            try:
                world = unreal.EditorLevelLibrary.get_game_world()
            except Exception:
                world = None

        result = {{
            "success": bool(world),
            "requested_mode": requested_mode,
            "launch_requested": launch_requested,
            "was_in_pie": was_in_pie,
            "is_in_play_in_editor": bool(subsystem.is_in_play_in_editor()),
            "pie_world_count": len(pie_worlds),
            "pie_world_names": [w.get_name() for w in pie_worlds],
            "world_name": world.get_name() if world else "",
            "mode_note": "Scripted station interactions are runtime API probes, not human movement/mouse validation.",
            "exercise": {{"requested": exercise_loop, "steps": [], "errors": []}},
            "runtime": {{}},
            "stop": {{}},
        }}

        controller = None
        pawn = None
        hud = None
        if world:
            try:
                controller = unreal.GameplayStatics.get_player_controller(world, 0)
            except Exception:
                controller = None
            try:
                pawn = controller.get_pawn() if controller else None
            except Exception:
                pawn = None
            if not pawn:
                try:
                    pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
                except Exception:
                    pawn = None
            if not pawn and controller:
                try:
                    repair_fn = getattr(controller, "ensure_possessed_pawn", None)
                    if callable(repair_fn):
                        repair_fn()
                        time.sleep(0.1)
                        result["pawn_repair"] = {{"attempted": True, "method": "ensure_possessed_pawn"}}
                except Exception as exc:
                    result["pawn_repair"] = {{"attempted": True, "error": str(exc)}}
                try:
                    pawn = controller.get_pawn()
                except Exception:
                    pawn = None
                if not pawn:
                    try:
                        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
                    except Exception:
                        pawn = None
            try:
                hud = controller.get_hud() if controller else None
            except Exception:
                hud = None

        mental_cls = unreal.load_class(None, "/Script/Insanitii.InsanitiiMentalStateComponent")
        objective_cls = unreal.load_class(None, "/Script/Insanitii.InsanitiiSliceObjectiveDirector")
        psychosis_cls = unreal.load_class(None, "/Script/Insanitii.InsanitiiPsychosisEventDirector")
        lifestyle_cls = unreal.load_class(None, "/Script/Insanitii.InsanitiiLifestyleManager")
        station_cls = unreal.load_class(None, "/Script/Insanitii.InsanitiiTaskStation")
        world_reactivity_cls = unreal.load_class(None, "/Script/Insanitii.InsanitiiWorldReactiveDirector")
        post_process_cls = unreal.load_class(None, "/Script/Insanitii.InsanitiiPostProcessController")
        audio_cls = unreal.load_class(None, "/Script/Insanitii.InsanitiiAudioFeedbackDirector")

        mental = None
        try:
            mental = pawn.get_component_by_class(mental_cls) if pawn and mental_cls else None
        except Exception:
            mental = None

        objectives = _actors_by_label(world, objective_cls)
        psychosis_directors = _actors_by_label(world, psychosis_cls)
        lifestyle_managers = _actors_by_label(world, lifestyle_cls)
        stations = _actors_by_label(world, station_cls)
        world_reactivity_directors = _actors_by_label(world, world_reactivity_cls)
        post_process_controllers = _actors_by_label(world, post_process_cls)
        audio_directors = _actors_by_label(world, audio_cls)

        objective = objectives.get("INS_SliceObjectiveDirector") or next(iter(objectives.values()), None)
        psychosis = psychosis_directors.get("INS_PsychosisEventDirector") or next(iter(psychosis_directors.values()), None)
        lifestyle = lifestyle_managers.get("INS_LifestyleManager") or next(iter(lifestyle_managers.values()), None)
        world_reactivity = world_reactivity_directors.get("INS_WorldReactiveDirector") or next(iter(world_reactivity_directors.values()), None)
        post_process = post_process_controllers.get("INS_PostProcessController") or next(iter(post_process_controllers.values()), None)
        audio = audio_directors.get("INS_AudioFeedbackDirector") or next(iter(audio_directors.values()), None)

        def _read_runtime():
            objective_text = ""
            progress = ""
            completion = None
            if objective:
                try:
                    objective_text = str(objective.get_current_objective_text())
                except Exception as exc:
                    objective_text = f"<error: {{exc}}>"
                try:
                    progress = str(objective.get_progress_summary())
                except Exception as exc:
                    progress = f"<error: {{exc}}>"
                try:
                    completion = float(objective.get_completion_percent())
                except Exception:
                    completion = None

            psychosis_summary = ""
            psychosis_active = False
            if psychosis:
                try:
                    psychosis_summary = str(psychosis.get_debug_summary())
                except Exception as exc:
                    psychosis_summary = f"<error: {{exc}}>"
                try:
                    psychosis_active = bool(psychosis.is_event_active())
                except Exception:
                    psychosis_active = False

            economy = None
            time_of_day = None
            if lifestyle:
                economy = _prop(lifestyle, "economy")
                time_of_day = _prop(lifestyle, "time_of_day")

            world_reactivity_summary = ""
            world_reactivity_tracked_count = 0
            world_reactivity_intensity = None
            if world_reactivity:
                try:
                    summary_fn = getattr(world_reactivity, "get_debug_summary", None)
                    world_reactivity_summary = str(summary_fn()) if callable(summary_fn) else ""
                except Exception as exc:
                    world_reactivity_summary = f"<error: {{exc}}>"
                try:
                    count_fn = getattr(world_reactivity, "get_tracked_actor_count", None)
                    world_reactivity_tracked_count = int(count_fn()) if callable(count_fn) else 0
                except Exception:
                    world_reactivity_tracked_count = 0
                try:
                    world_reactivity_intensity = float(world_reactivity.get_editor_property("current_reactive_intensity"))
                except Exception:
                    world_reactivity_intensity = None

            hud_status = ""
            objective_marker_summary = ""
            if hud:
                try:
                    status_fn = getattr(hud, "get_demo_status_debug_summary", None)
                    hud_status = str(status_fn()) if callable(status_fn) else ""
                except Exception as exc:
                    hud_status = f"<error: {{exc}}>"
                try:
                    marker_fn = getattr(hud, "get_objective_marker_debug_summary", None)
                    objective_marker_summary = str(marker_fn()) if callable(marker_fn) else ""
                except Exception as exc:
                    objective_marker_summary = f"<error: {{exc}}>"

            post_process_summary = ""
            task_feedback_pulse = None
            task_feedback_color_shift = None
            if post_process:
                try:
                    summary_fn = getattr(post_process, "get_debug_summary", None)
                    post_process_summary = str(summary_fn()) if callable(summary_fn) else ""
                except Exception as exc:
                    post_process_summary = f"<error: {{exc}}>"
                try:
                    task_feedback_pulse = float(post_process.get_task_feedback_pulse_strength())
                    task_feedback_color_shift = float(post_process.get_task_feedback_color_shift())
                except Exception:
                    task_feedback_pulse = None
                    task_feedback_color_shift = None

            return {{
                "controller_class": controller.get_class().get_name() if controller else "",
                "controller_name": controller.get_name() if controller else "",
                "pawn_class": pawn.get_class().get_name() if pawn else "",
                "pawn_name": pawn.get_name() if pawn else "",
                "hud_class": hud.get_class().get_name() if hud else "",
                "hud_status": hud_status,
                "objective_marker_summary": objective_marker_summary,
                "post_process_summary": post_process_summary,
                "task_feedback_pulse": task_feedback_pulse,
                "task_feedback_color_shift": task_feedback_color_shift,
                "mental_state": float(_prop(mental, "mental_state", "MentalState", default=-1.0)) if mental else None,
                "focus_charges": float(_prop(mental, "focus_charges", "FocusCharges", default=-1.0)) if mental else None,
                "breathe_cooldown": float(_prop(mental, "breathe_cooldown", "BreatheCooldown", default=-1.0)) if mental else None,
                "in_psychosis_event": bool(_prop(mental, "b_is_in_psychosis_event", "bIsInPsychosisEvent", default=False)) if mental else False,
                "objective_text": objective_text,
                "objective_progress": progress,
                "objective_completion_percent": completion,
                "psychosis_summary": psychosis_summary,
                "psychosis_active": psychosis_active,
                "station_count": len(stations),
                "world_reactivity_tracked_count": world_reactivity_tracked_count,
                "world_reactivity_intensity": world_reactivity_intensity,
                "world_reactivity_summary": world_reactivity_summary,
                "cash_balance": float(_prop(economy, "cash_balance", "CashBalance", default=-1.0)) if economy else None,
                "formatted_time": str(time_of_day.get_formatted_time()) if time_of_day and hasattr(time_of_day, "get_formatted_time") else "",
            }}

        result["runtime"]["before_exercise"] = _read_runtime()

        if hud and mental:
            anchor_samples = {{}}
            original_mental_state = float(_prop(mental, "mental_state", "MentalState", default=1.0))
            try:
                mental.set_editor_property("MentalState", 1.0)
                time.sleep(0.1)
                anchor_samples["clean"] = _read_runtime().get("objective_marker_summary", "")

                mental.set_editor_property("MentalState", 0.15)
                time.sleep(0.1)
                anchor_samples["strained"] = _read_runtime().get("objective_marker_summary", "")

                if psychosis:
                    if not psychosis.is_event_active():
                        psychosis.start_random_psychosis_event(0.05)
                    time.sleep(0.2)
                    anchor_samples["psychosis"] = _read_runtime().get("objective_marker_summary", "")
                    if psychosis.is_event_active():
                        psychosis.end_active_psychosis_event()

                if audio:
                    false_fn = getattr(audio, "trigger_false_instruction_for_debug", None)
                    if callable(false_fn):
                        false_fn()
                        time.sleep(0.15)
                        anchor_samples["false_cue"] = _read_runtime().get("objective_marker_summary", "")

                mental.set_editor_property("MentalState", original_mental_state)
                result["objective_anchor_samples"] = anchor_samples
            except Exception as exc:
                try:
                    mental.set_editor_property("MentalState", original_mental_state)
                except Exception:
                    pass
                result["objective_anchor_samples"] = anchor_samples
                result["exercise"]["errors"].append(f"objective_anchor_samples: {{exc}}")

        if exercise_loop and pawn:
            if mental:
                try:
                    mental.set_editor_property("MentalState", 0.35)
                    mental.set_editor_property("BreatheCooldown", 0.0)
                    mental.set_editor_property("FocusCharges", 100.0)
                    mental.set_editor_property("bIsFocusActive", False)
                    breathe_result = bool(mental.attempt_breathe())
                    time.sleep(0.1)
                    breathe_after = _read_runtime()
                    focus_result = bool(mental.activate_focus(1.0))
                    time.sleep(0.1)
                    focus_after = _read_runtime()
                    try:
                        mental.deactivate_focus()
                    except Exception:
                        pass
                    result["exercise"]["stabilization_tools"] = {{
                        "breathe_result": breathe_result,
                        "breathe_after": breathe_after,
                        "focus_result": focus_result,
                        "focus_after": focus_after,
                    }}
                except Exception as exc:
                    result["exercise"]["errors"].append(f"stabilization_tools: {{exc}}")

            ordered = [
                ("food", "INS_TaskStation_Food_Sandwich"),
                ("medication", "INS_TaskStation_Medication"),
                ("grocery", "INS_TaskStation_Grocery_Corner"),
                ("laundry", "INS_TaskStation_Laundry_Washer"),
                ("package", "INS_TaskStation_Package_Dropoff"),
                ("commute", "INS_TaskStation_Commute_Car"),
                ("work", "INS_TaskStation_Work_EmailTriage"),
                ("stress", "INS_TaskStation_Stress_OverwhelmingNoise"),
            ]
            for step_name, label in ordered:
                station = stations.get(label)
                if not station:
                    result["exercise"]["errors"].append(f"Missing station {{label}}")
                    continue
                try:
                    before = _read_runtime()
                    _call(station, "on_interact", pawn)
                    if mental:
                        try:
                            mental.tick_mental_state(0.25)
                        except Exception:
                            pass
                    time.sleep(0.1)
                    after = _read_runtime()
                    result["exercise"]["steps"].append({{"step": step_name, "station": label, "before": before, "after": after}})
                except Exception as exc:
                    result["exercise"]["errors"].append(f"{{label}}: {{exc}}")

            if psychosis:
                try:
                    if not psychosis.is_event_active():
                        psychosis.start_random_psychosis_event(float(_prop(mental, "mental_state", "MentalState", default=0.0)) if mental else 0.0)
                    time.sleep(0.2)
                    result["exercise"]["after_psychosis_start"] = _read_runtime()
                    if psychosis.is_event_active():
                        psychosis.end_active_psychosis_event()
                    if mental:
                        try:
                            mental.adjust_mental_state(1.0)
                        except Exception:
                            pass
                    time.sleep(0.1)
                    result["exercise"]["after_psychosis_end"] = _read_runtime()
                except Exception as exc:
                    result["exercise"]["errors"].append(f"psychosis: {{exc}}")

            sleep_station = stations.get("INS_TaskStation_Sleep_Bed")
            if sleep_station:
                try:
                    before = _read_runtime()
                    _call(sleep_station, "on_interact", pawn)
                    time.sleep(0.1)
                    after = _read_runtime()
                    result["exercise"]["steps"].append({{"step": "sleep", "station": "INS_TaskStation_Sleep_Bed", "before": before, "after": after}})
                except Exception as exc:
                    result["exercise"]["errors"].append(f"sleep: {{exc}}")
            else:
                result["exercise"]["errors"].append("Missing station INS_TaskStation_Sleep_Bed")

            friction_station = stations.get("INS_TaskStation_Grocery_Corner")
            if friction_station and mental:
                try:
                    friction_station.set_editor_property("bHasBeenUsed", False)
                    friction_station.set_editor_property("bUseMentalFriction", True)
                    friction_station.set_editor_property("FrictionThreshold", 0.90)
                    friction_station.set_editor_property("CriticalFrictionThreshold", 0.25)
                    friction_station.set_editor_property("MaxFrictionSlipChance", 1.0)
                    friction_station.set_editor_property("FrictionFailurePenalty", 0.08)
                    mental.set_editor_property("MentalState", 0.05)
                    mental.set_editor_property("bIsFocusActive", False)
                    _call(friction_station, "on_interact", pawn)
                    time.sleep(0.1)
                    result["exercise"]["friction_slip"] = {{
                        "station": "INS_TaskStation_Grocery_Corner",
                        "station_used": bool(friction_station.get_editor_property("bHasBeenUsed")),
                        "last_use_succeeded": bool(friction_station.get_editor_property("bLastUseSucceeded")),
                        "friction_risk": float(friction_station.get_editor_property("LastFrictionRisk")),
                        "feedback": str(friction_station.get_editor_property("LastUseFeedback")),
                        "after": _read_runtime(),
                    }}
                    mental.set_editor_property("MentalState", 1.0)
                except Exception as exc:
                    result["exercise"]["errors"].append(f"friction_slip: {{exc}}")
            else:
                result["exercise"]["errors"].append("Missing station or mental state for friction slip check")

        result["runtime"]["after_exercise"] = _read_runtime()

        if stop_after_probe:
            was_in_pie_before_stop = bool(subsystem.is_in_play_in_editor())
            if was_in_pie_before_stop:
                subsystem.editor_request_end_play()
                try:
                    unreal.EditorLevelLibrary.editor_end_play()
                except Exception:
                    pass
                time.sleep(0.5)
            try:
                remaining_worlds = list(unreal.EditorLevelLibrary.get_pie_worlds(False))
            except Exception:
                remaining_worlds = []
            result["stop"] = {{
                "requested": was_in_pie_before_stop,
                "is_in_play_in_editor": bool(subsystem.is_in_play_in_editor()),
                "pie_world_count": len(remaining_worlds),
                "pie_world_names": [w.get_name() for w in remaining_worlds],
            }}

        print(json.dumps(result))
    """)


def _insanitii_load_level_code(level_path: str = "/Game/FirstPerson/Lvl_FirstPerson") -> str:
    return textwrap.dedent(f"""
        import json, unreal

        result = {{"success": True, "level_path": {json.dumps(level_path)}, "errors": []}}
        try:
            level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            result["loaded"] = bool(level_subsystem.load_level({json.dumps(level_path)}))
        except Exception as exc:
            result["success"] = False
            result["loaded"] = False
            result["errors"].append(str(exc))

        print(json.dumps(result))
    """)


def _insanitii_place_task_station_code(spec: Dict[str, Any]) -> str:
    return textwrap.dedent(f"""
        import json, unreal

        spec = {json.dumps(spec)}
        result = {{"success": True, "errors": []}}
        actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actors = {{actor.get_actor_label(): actor for actor in actor_subsystem.get_all_level_actors()}}
        label = spec["label"]
        location = unreal.Vector(*spec["location"])
        rotation = unreal.Rotator(0.0, 0.0, 0.0)
        scale = unreal.Vector(*spec["scale"])
        action = getattr(unreal.InsanitiiTaskStationAction, spec["action"])

        actor = actors.get(label)
        if actor is None:
            actor = actor_subsystem.spawn_actor_from_class(unreal.InsanitiiTaskStation, location, rotation)
            actor.set_actor_label(label)
            result["created"] = True
        else:
            result["created"] = False

        actor.set_actor_location(location, False, False)
        actor.set_actor_scale3d(scale)
        for prop, value in [
            ("action", action),
            ("prompt_text", spec["prompt"]),
            ("mental_state_delta", float(spec["mental_state_delta"])),
            ("money_delta", int(spec["money_delta"])),
            ("task_index", int(spec.get("task_index", 0))),
            ("bReusable", True),
        ]:
            try:
                actor.set_editor_property(prop, value)
            except Exception as exc:
                result["errors"].append(f"{{prop}}: {{exc}}")

        try:
            label_component = actor.get_editor_property("label_component")
            if label_component:
                label_component.set_text(spec["prompt"])
                label_component.set_world_size(26.0)
        except Exception as exc:
            result["errors"].append(f"label_component: {{exc}}")

        loc = actor.get_actor_location()
        final_scale = actor.get_actor_scale3d()
        result.update({{
            "label": actor.get_actor_label(),
            "action": str(actor.get_editor_property("action")),
            "prompt": str(actor.get_editor_property("prompt_text")),
            "money_delta": int(actor.get_editor_property("money_delta")),
            "mental_state_delta": float(actor.get_editor_property("mental_state_delta")),
            "location": [round(loc.x, 2), round(loc.y, 2), round(loc.z, 2)],
            "scale": [round(final_scale.x, 2), round(final_scale.y, 2), round(final_scale.z, 2)],
        }})
        result["success"] = result["success"] and not result["errors"]
        print(json.dumps(result))
    """)


def _insanitii_save_current_level_code() -> str:
    return textwrap.dedent("""
        import json, unreal

        result = {"success": True, "errors": []}
        try:
            level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            result["saved_current_level"] = bool(level_subsystem.save_current_level())
        except Exception as exc:
            result["success"] = False
            result["saved_current_level"] = False
            result["errors"].append(str(exc))

        print(json.dumps(result))
    """)


def _insanitii_ordinary_errand_station_specs() -> List[Dict[str, Any]]:
    return [
        {
            "label": "INS_TaskStation_Grocery_Corner",
            "action": "GROCERY",
            "prompt": "Buy Groceries",
            "location": [-1150.0, -620.0, 120.0],
            "scale": [0.75, 0.75, 0.42],
            "mental_state_delta": 0.07,
            "money_delta": 32,
        },
        {
            "label": "INS_TaskStation_Laundry_Washer",
            "action": "LAUNDRY",
            "prompt": "Do Laundry",
            "location": [-250.0, -900.0, 120.0],
            "scale": [0.70, 0.70, 0.50],
            "mental_state_delta": 0.05,
            "money_delta": 12,
        },
        {
            "label": "INS_TaskStation_Package_Dropoff",
            "action": "PACKAGE_DELIVERY",
            "prompt": "Deliver Package",
            "location": [650.0, -880.0, 120.0],
            "scale": [0.58, 0.58, 0.35],
            "mental_state_delta": 0.08,
            "money_delta": 35,
        },
        {
            "label": "INS_TaskStation_Commute_Car",
            "action": "COMMUTE",
            "prompt": "Drive to Work",
            "location": [1250.0, -560.0, 110.0],
            "scale": [1.50, 0.68, 0.28],
            "mental_state_delta": 0.10,
            "money_delta": 0,
        },
    ]


def _insanitii_day1_set_dressing_specs() -> List[Dict[str, Any]]:
    cube = "/Engine/BasicShapes/Cube.Cube"
    cylinder = "/Engine/BasicShapes/Cylinder.Cylinder"
    sphere = "/Engine/BasicShapes/Sphere.Sphere"
    return [
        {"kind": "static_mesh", "label": "INS_Day1_Path_HomeFloor", "mesh": cube, "location": [-1250.0, 820.0, 72.0], "scale": [2.85, 1.80, 0.04]},
        {"kind": "static_mesh", "label": "INS_Day1_Home_KitchenCounter", "mesh": cube, "location": [-1405.0, 700.0, 115.0], "scale": [0.35, 1.05, 0.32]},
        {"kind": "static_mesh", "label": "INS_Day1_Home_MedicineShelf", "mesh": cube, "location": [-1375.0, 895.0, 160.0], "scale": [0.25, 0.55, 0.65]},
        {"kind": "static_mesh", "label": "INS_Day1_Home_BedBackdrop", "mesh": cube, "location": [-1065.0, 930.0, 110.0], "scale": [1.20, 0.32, 0.28]},
        {"kind": "text", "label": "INS_Day1_Sign_Home", "text": "HOME", "location": [-1250.0, 1080.0, 220.0], "rotation": [0.0, 155.0, 0.0], "scale": [1.0, 1.0, 1.0], "color": [255, 221, 170, 255], "world_size": 34.0},
        {"kind": "light", "label": "INS_Day1_Light_Home", "location": [-1250.0, 820.0, 330.0], "color": [255, 191, 128, 255], "intensity": 1750.0, "radius": 580.0},

        {"kind": "static_mesh", "label": "INS_Day1_Path_GroceryFloor", "mesh": cube, "location": [-1150.0, -620.0, 72.0], "scale": [2.25, 1.25, 0.04]},
        {"kind": "static_mesh", "label": "INS_Day1_Grocery_ShelvesLeft", "mesh": cube, "location": [-1365.0, -640.0, 135.0], "scale": [0.28, 1.05, 0.55]},
        {"kind": "static_mesh", "label": "INS_Day1_Grocery_ShelvesRight", "mesh": cube, "location": [-905.0, -640.0, 135.0], "scale": [0.28, 1.05, 0.55]},
        {"kind": "static_mesh", "label": "INS_Day1_Grocery_Checkout", "mesh": cube, "location": [-1145.0, -505.0, 112.0], "scale": [1.10, 0.24, 0.30]},
        {"kind": "text", "label": "INS_Day1_Sign_Grocery", "text": "GROCERY", "location": [-1150.0, -470.0, 230.0], "rotation": [0.0, 170.0, 0.0], "scale": [1.0, 1.0, 1.0], "color": [146, 255, 179, 255], "world_size": 30.0},
        {"kind": "light", "label": "INS_Day1_Light_Grocery", "location": [-1150.0, -620.0, 330.0], "color": [120, 255, 170, 255], "intensity": 1450.0, "radius": 520.0},

        {"kind": "static_mesh", "label": "INS_Day1_Path_LaundryFloor", "mesh": cube, "location": [-250.0, -900.0, 72.0], "scale": [2.15, 1.15, 0.04]},
        {"kind": "static_mesh", "label": "INS_Day1_Laundry_WasherLeft", "mesh": cylinder, "location": [-420.0, -925.0, 122.0], "scale": [0.42, 0.42, 0.45]},
        {"kind": "static_mesh", "label": "INS_Day1_Laundry_WasherRight", "mesh": cylinder, "location": [80.0, -925.0, 122.0], "scale": [0.42, 0.42, 0.45]},
        {"kind": "text", "label": "INS_Day1_Sign_Laundry", "text": "LAUNDRY", "location": [-250.0, -745.0, 230.0], "rotation": [0.0, -165.0, 0.0], "scale": [1.0, 1.0, 1.0], "color": [153, 220, 255, 255], "world_size": 30.0},
        {"kind": "light", "label": "INS_Day1_Light_Laundry", "location": [-250.0, -900.0, 330.0], "color": [130, 210, 255, 255], "intensity": 1350.0, "radius": 500.0},

        {"kind": "static_mesh", "label": "INS_Day1_Path_PackageFloor", "mesh": cube, "location": [650.0, -880.0, 72.0], "scale": [2.1, 1.1, 0.04]},
        {"kind": "static_mesh", "label": "INS_Day1_Package_DoorLeft", "mesh": cube, "location": [500.0, -895.0, 145.0], "scale": [0.18, 0.28, 0.85]},
        {"kind": "static_mesh", "label": "INS_Day1_Package_DoorRight", "mesh": cube, "location": [755.0, -895.0, 145.0], "scale": [0.18, 0.28, 0.85]},
        {"kind": "static_mesh", "label": "INS_Day1_Package_DoorTop", "mesh": cube, "location": [630.0, -895.0, 230.0], "scale": [1.45, 0.25, 0.16]},
        {"kind": "static_mesh", "label": "INS_Day1_Package_BoxStack", "mesh": cube, "location": [900.0, -820.0, 112.0], "scale": [0.45, 0.35, 0.30]},
        {"kind": "text", "label": "INS_Day1_Sign_Package", "text": "DELIVERY", "location": [650.0, -735.0, 265.0], "rotation": [0.0, 125.0, 0.0], "scale": [1.0, 1.0, 1.0], "color": [255, 205, 120, 255], "world_size": 29.0},
        {"kind": "light", "label": "INS_Day1_Light_Package", "location": [650.0, -880.0, 320.0], "color": [255, 190, 95, 255], "intensity": 1500.0, "radius": 520.0},

        {"kind": "static_mesh", "label": "INS_Day1_Path_CommuteRoad", "mesh": cube, "location": [1250.0, -560.0, 72.0], "scale": [3.7, 1.20, 0.04]},
        {"kind": "static_mesh", "label": "INS_Day1_Commute_LaneLineA", "mesh": cube, "location": [1110.0, -560.0, 76.0], "scale": [0.20, 1.0, 0.025]},
        {"kind": "static_mesh", "label": "INS_Day1_Commute_LaneLineB", "mesh": cube, "location": [1390.0, -560.0, 76.0], "scale": [0.20, 1.0, 0.025]},
        {"kind": "text", "label": "INS_Day1_Sign_Commute", "text": "COMMUTE", "location": [1250.0, -710.0, 225.0], "rotation": [0.0, 55.0, 0.0], "scale": [1.0, 1.0, 1.0], "color": [178, 202, 255, 255], "world_size": 29.0},
        {"kind": "light", "label": "INS_Day1_Light_Commute", "location": [1250.0, -560.0, 315.0], "color": [150, 175, 255, 255], "intensity": 1250.0, "radius": 540.0},

        {"kind": "static_mesh", "label": "INS_Day1_Path_WorkFloor", "mesh": cube, "location": [1280.0, 150.0, 72.0], "scale": [2.25, 1.25, 0.04]},
        {"kind": "static_mesh", "label": "INS_Day1_Work_Desk", "mesh": cube, "location": [1140.0, 150.0, 120.0], "scale": [0.55, 1.05, 0.30]},
        {"kind": "static_mesh", "label": "INS_Day1_Work_Monitor", "mesh": cube, "location": [1140.0, 150.0, 168.0], "scale": [0.12, 0.58, 0.34]},
        {"kind": "text", "label": "INS_Day1_Sign_Work", "text": "WORK", "location": [1280.0, 300.0, 225.0], "rotation": [0.0, -125.0, 0.0], "scale": [1.0, 1.0, 1.0], "color": [160, 244, 255, 255], "world_size": 32.0},
        {"kind": "light", "label": "INS_Day1_Light_Work", "location": [1280.0, 150.0, 320.0], "color": [145, 238, 255, 255], "intensity": 1400.0, "radius": 500.0},

        {"kind": "static_mesh", "label": "INS_Day1_Path_StressFloor", "mesh": cube, "location": [760.0, 820.0, 72.0], "scale": [2.25, 1.25, 0.04]},
        {"kind": "static_mesh", "label": "INS_Day1_Stress_SpeakerLeft", "mesh": cube, "location": [580.0, 795.0, 155.0], "scale": [0.32, 0.28, 0.75]},
        {"kind": "static_mesh", "label": "INS_Day1_Stress_SpeakerRight", "mesh": cube, "location": [950.0, 795.0, 155.0], "scale": [0.32, 0.28, 0.75]},
        {"kind": "static_mesh", "label": "INS_Day1_Stress_PulseOrb", "mesh": sphere, "location": [760.0, 820.0, 205.0], "scale": [0.38, 0.38, 0.38]},
        {"kind": "text", "label": "INS_Day1_Sign_Stress", "text": "NOISE", "location": [760.0, 975.0, 265.0], "rotation": [0.0, -140.0, 0.0], "scale": [1.0, 1.0, 1.0], "color": [255, 95, 130, 255], "world_size": 35.0},
        {"kind": "light", "label": "INS_Day1_Light_Stress", "location": [760.0, 820.0, 330.0], "color": [255, 65, 125, 255], "intensity": 2200.0, "radius": 610.0},
    ]


def _insanitii_place_set_dressing_actor_code(spec: Dict[str, Any]) -> str:
    return textwrap.dedent(f"""
        import json, unreal

        spec = {json.dumps(spec)}
        result = {{"success": True, "errors": []}}
        actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actors = {{actor.get_actor_label(): actor for actor in actor_subsystem.get_all_level_actors()}}
        label = spec["label"]
        kind = spec["kind"]
        location = unreal.Vector(*spec["location"])
        rotation_values = spec.get("rotation", [0.0, 0.0, 0.0])
        rotation = unreal.Rotator(*rotation_values)
        scale_values = spec.get("scale", [1.0, 1.0, 1.0])

        actor = actors.get(label)
        if actor is None:
            if kind == "static_mesh":
                actor = actor_subsystem.spawn_actor_from_class(unreal.StaticMeshActor, location, rotation)
            elif kind == "text":
                actor = actor_subsystem.spawn_actor_from_class(unreal.TextRenderActor, location, rotation)
            elif kind == "light":
                actor = actor_subsystem.spawn_actor_from_class(unreal.PointLight, location, rotation)
            else:
                raise RuntimeError(f"Unsupported set-dressing kind: {{kind}}")
            actor.set_actor_label(label)
            result["created"] = True
        else:
            result["created"] = False

        actor.set_actor_location(location, False, False)
        actor.set_actor_rotation(rotation, False)
        tags = list(actor.get_editor_property("tags") or [])
        reactive_tag = unreal.Name("InsanitiiWorldReactive")
        if reactive_tag not in tags:
            tags.append(reactive_tag)
            actor.set_editor_property("tags", tags)
        if kind != "light":
            actor.set_actor_scale3d(unreal.Vector(*scale_values))

        if kind == "static_mesh":
            component = actor.get_component_by_class(unreal.StaticMeshComponent)
            mesh = unreal.load_asset(spec["mesh"])
            if component and mesh:
                component.set_static_mesh(mesh)
                component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                component.set_cast_shadow(True)
            else:
                result["errors"].append("Missing static mesh component or mesh asset")
        elif kind == "text":
            component = actor.get_component_by_class(unreal.TextRenderComponent)
            if component:
                color = spec.get("color", [255, 255, 255, 255])
                component.set_text(spec["text"])
                component.set_text_render_color(unreal.Color(*color))
                component.set_world_size(float(spec.get("world_size", 30.0)))
                component.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
                component.set_vertical_alignment(unreal.VerticalTextAligment.EVRTA_TEXT_CENTER)
            else:
                result["errors"].append("Missing text render component")
        elif kind == "light":
            component = actor.get_component_by_class(unreal.PointLightComponent)
            if component:
                color = spec.get("color", [255, 255, 255, 255])
                component.set_editor_property("intensity", float(spec.get("intensity", 1000.0)))
                component.set_editor_property("attenuation_radius", float(spec.get("radius", 400.0)))
                component.set_editor_property("light_color", unreal.Color(*color))
            else:
                result["errors"].append("Missing point light component")

        loc = actor.get_actor_location()
        actor_scale = actor.get_actor_scale3d()
        result.update({{
            "label": actor.get_actor_label(),
            "kind": kind,
            "location": [round(loc.x, 2), round(loc.y, 2), round(loc.z, 2)],
            "scale": [round(actor_scale.x, 2), round(actor_scale.y, 2), round(actor_scale.z, 2)],
        }})
        result["success"] = result["success"] and not result["errors"]
        print(json.dumps(result))
    """)


def _insanitii_world_reactivity_probe_code() -> str:
    return textwrap.dedent("""
        import json, unreal

        result = {"success": True, "errors": []}
        world_director_cls = unreal.load_class(None, "/Script/Insanitii.InsanitiiWorldReactiveDirector")
        result["class"] = {
            "success": bool(world_director_cls),
            "class_path": "/Script/Insanitii.InsanitiiWorldReactiveDirector",
            "loaded_name": world_director_cls.get_name() if world_director_cls else "",
        }

        actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actors = actor_subsystem.get_all_level_actors()
        reactive_actors = []
        director = None
        for actor in actors:
            label = actor.get_actor_label()
            tags = [str(tag) for tag in actor.tags]
            if "InsanitiiWorldReactive" in tags:
                reactive_actors.append({
                    "label": label,
                    "class": actor.get_class().get_name(),
                    "tags": tags,
                })
            if label == "INS_WorldReactiveDirector" or actor.get_class().get_name() == "InsanitiiWorldReactiveDirector":
                director = actor

        director_probe = {"success": False}
        if director:
            try:
                rebind = getattr(director, "rebind_world_actors", None)
                if callable(rebind):
                    rebind()
            except Exception as exc:
                result["errors"].append("rebind: %s" % exc)
            try:
                summary_fn = getattr(director, "get_debug_summary", None)
                tracked_fn = getattr(director, "get_tracked_actor_count", None)
                director_probe = {
                    "success": True,
                    "label": director.get_actor_label(),
                    "class": director.get_class().get_name(),
                    "tracked_actor_count": int(tracked_fn()) if callable(tracked_fn) else -1,
                    "current_reactive_intensity": float(director.get_editor_property("current_reactive_intensity")),
                    "debug_summary": str(summary_fn()) if callable(summary_fn) else "",
                    "reactive_actor_tag": str(director.get_editor_property("reactive_actor_tag")),
                }
            except Exception as exc:
                director_probe = {"success": False, "error": str(exc)}

        result["director"] = director_probe
        result["reactive_actor_count"] = len(reactive_actors)
        result["reactive_actors"] = sorted(reactive_actors, key=lambda item: item["label"])
        print(json.dumps(result))
    """)


def _insanitii_save_load_runtime_probe_code() -> str:
    return textwrap.dedent("""
        import json, time, unreal

        result = {"success": False, "errors": []}

        def _pie_world():
            try:
                worlds = list(unreal.EditorLevelLibrary.get_pie_worlds(False))
            except Exception:
                worlds = []
            if worlds:
                return worlds[0]
            try:
                return unreal.EditorLevelLibrary.get_editor_world()
            except Exception:
                return None

        def _actors_by_label(world, cls):
            actors = {}
            if not world or not cls:
                return actors
            try:
                found = unreal.GameplayStatics.get_all_actors_of_class(world, cls)
            except Exception:
                found = []
            for actor in found:
                try:
                    label = actor.get_actor_label()
                except Exception:
                    label = actor.get_name()
                actors[label] = actor
            return actors

        def _read_state(world, manager, lifestyle, mental):
            economy = None
            time_of_day = None
            if lifestyle:
                try:
                    economy = lifestyle.get_editor_property("economy")
                except Exception:
                    economy = None
                try:
                    time_of_day = lifestyle.get_editor_property("time_of_day")
                except Exception:
                    time_of_day = None
            return {
                "day": int(time_of_day.get_editor_property("current_day")) if time_of_day else None,
                "minute": float(time_of_day.get_editor_property("current_minute_of_day")) if time_of_day else None,
                "cash": int(economy.get_editor_property("cash_balance")) if economy else None,
                "ledger_count": len(economy.get_editor_property("ledger")) if economy else None,
                "lifestyle_skill": float(lifestyle.get_editor_property("lifestyle_skill")) if lifestyle else None,
                "reputation": float(lifestyle.get_editor_property("reputation")) if lifestyle else None,
                "mental_state": float(mental.get_editor_property("mental_state")) if mental else None,
                "focus_charges": float(mental.get_editor_property("focus_charges")) if mental else None,
                "save_summary": str(manager.get_debug_summary()) if manager else "",
            }

        try:
            world = _pie_world()
            result["world_name"] = world.get_name() if world else ""
            if not world:
                result["errors"].append("No PIE/editor world available")
            else:
                save_cls = unreal.load_class(None, "/Script/Insanitii.InsanitiiSaveGameManager")
                lifestyle_cls = unreal.load_class(None, "/Script/Insanitii.InsanitiiLifestyleManager")
                mental_cls = unreal.load_class(None, "/Script/Insanitii.InsanitiiMentalStateComponent")
                manager = _actors_by_label(world, save_cls).get("INS_SaveGameManager") if save_cls else None
                lifestyle = _actors_by_label(world, lifestyle_cls).get("INS_LifestyleManager") if lifestyle_cls else None
                controller = unreal.GameplayStatics.get_player_controller(world, 0)
                pawn = None
                try:
                    pawn = controller.get_pawn() if controller else None
                except Exception:
                    pawn = None
                if not pawn:
                    try:
                        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
                    except Exception:
                        pawn = None
                mental = pawn.get_component_by_class(mental_cls) if pawn and mental_cls else None

                if not manager:
                    result["errors"].append("INS_SaveGameManager not found")
                if not lifestyle:
                    result["errors"].append("INS_LifestyleManager not found")
                if not mental:
                    result["errors"].append("Mental state component not found")

                if not result["errors"]:
                    try:
                        manager.rebind_runtime_state()
                    except Exception as exc:
                        result["errors"].append("rebind: %s" % exc)

                if not result["errors"]:
                    before = _read_state(world, manager, lifestyle, mental)
                    save_success = bool(manager.save_demo_state())
                    saved = _read_state(world, manager, lifestyle, mental)

                    economy = lifestyle.get_editor_property("economy")
                    time_of_day = lifestyle.get_editor_property("time_of_day")
                    economy.set_cash_balance(int(before["cash"] or 0) + 77, "MCP_SaveProbeMutation", int(before["day"] or 1), int(before["minute"] or 480))
                    time_of_day.set_clock_time(int(before["day"] or 1) + 2, min(float(before["minute"] or 480.0) + 123.0, 1439.0))
                    mental.adjust_mental_state(-0.23)
                    mutated = _read_state(world, manager, lifestyle, mental)

                    load_success = bool(manager.load_demo_state())
                    time.sleep(0.1)
                    restored = _read_state(world, manager, lifestyle, mental)

                    result.update({
                        "success": save_success and load_success,
                        "save_success": save_success,
                        "load_success": load_success,
                        "save_exists": bool(manager.does_demo_save_exist()),
                        "before": before,
                        "saved": saved,
                        "mutated": mutated,
                        "restored": restored,
                        "restored_matches": {
                            "day": restored["day"] == before["day"],
                            "cash": restored["cash"] == before["cash"],
                            "mental_state": abs(float(restored["mental_state"] or 0.0) - float(before["mental_state"] or 0.0)) < 0.01,
                        },
                    })
        except Exception as exc:
            result["errors"].append("exception: %s" % exc)
        print(json.dumps(result))
    """)


def _insanitii_audio_feedback_probe_code() -> str:
    return textwrap.dedent("""
        import json, unreal

        level_path = "/Game/FirstPerson/Lvl_FirstPerson"
        asset_paths = {
            "room_tone": "/Game/Insanitii/Audio/Generated/INS_Audio_RoomTone.INS_Audio_RoomTone",
            "stress_layer": "/Game/Insanitii/Audio/Generated/INS_Audio_PsychosisStress.INS_Audio_PsychosisStress",
            "stabilize": "/Game/Insanitii/Audio/Generated/INS_Audio_Stabilize.INS_Audio_Stabilize",
            "psychosis_start": "/Game/Insanitii/Audio/Generated/INS_Audio_PsychosisStart.INS_Audio_PsychosisStart",
            "psychosis_end": "/Game/Insanitii/Audio/Generated/INS_Audio_PsychosisEnd.INS_Audio_PsychosisEnd",
        }
        slot_names = {
            "room_tone": "room_tone_sound",
            "stress_layer": "stress_layer_sound",
            "stabilize": "stabilize_cue_sound",
            "psychosis_start": "psychosis_start_sound",
            "psychosis_end": "psychosis_end_sound",
        }
        looping_expected = {
            "room_tone": True,
            "stress_layer": True,
            "stabilize": False,
            "psychosis_start": False,
            "psychosis_end": False,
        }

        def _asset_info(path):
            asset = unreal.load_asset(path)
            info = {
                "exists": bool(asset),
                "path": path,
                "class": asset.get_class().get_name() if asset else "",
                "looping": None,
                "duration": None,
            }
            if asset:
                for prop in ("looping", "duration"):
                    try:
                        info[prop] = asset.get_editor_property(prop)
                    except Exception:
                        try:
                            info[prop] = getattr(asset, prop)
                        except Exception:
                            pass
            return info

        result = {
            "success": True,
            "level_path": level_path,
            "assets": {key: _asset_info(path) for key, path in asset_paths.items()},
            "actor": None,
            "slot_assignments": {},
            "looping_expected": looping_expected,
            "errors": [],
        }

        try:
            unreal.EditorLevelLibrary.load_level(level_path)
        except Exception as exc:
            result["errors"].append(f"level_load: {exc}")

        actor = None
        try:
            for candidate in unreal.EditorLevelLibrary.get_all_level_actors():
                try:
                    label = candidate.get_actor_label()
                except Exception:
                    label = candidate.get_name()
                if label == "INS_AudioFeedbackDirector" or candidate.get_class().get_name() == "InsanitiiAudioFeedbackDirector":
                    actor = candidate
                    break
        except Exception as exc:
            result["errors"].append(f"actor_scan: {exc}")

        if actor:
            result["actor"] = {
                "name": actor.get_name(),
                "label": actor.get_actor_label(),
                "class": actor.get_class().get_name(),
            }
            for key, slot_name in slot_names.items():
                assigned = None
                try:
                    assigned = actor.get_editor_property(slot_name)
                except Exception as exc:
                    result["errors"].append(f"{slot_name}: {exc}")
                assigned_path = assigned.get_path_name() if assigned else ""
                expected_prefix = asset_paths[key].split(".")[0]
                result["slot_assignments"][key] = {
                    "slot": slot_name,
                    "assigned": bool(assigned),
                    "path": assigned_path,
                    "expected": asset_paths[key],
                    "matches_expected": bool(assigned_path.startswith(expected_prefix)),
                }
        else:
            result["errors"].append("INS_AudioFeedbackDirector actor was not found in Lvl_FirstPerson.")

        print(json.dumps(result))
    """)


def _list_windows(process_name_contains: str = "UnrealEditor") -> Dict[str, Any]:
    """Enumerate visible Windows top-level dialogs using ctypes only."""
    if sys.platform != "win32":
        return {
            "success": False,
            "message": "Window prompt automation is only available on Windows",
            "windows": [],
        }

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    PROCESS_VM_READ = 0x0010

    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    EnumChildProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _window_text(hwnd) -> str:
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value

    def _class_name(hwnd) -> str:
        buffer = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buffer, 256)
        return buffer.value

    def _process_image(pid: int) -> str:
        access = PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ
        handle = kernel32.OpenProcess(access, False, pid)
        if not handle:
            return ""
        try:
            buffer = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(len(buffer))
            if psapi.GetModuleFileNameExW(handle, None, buffer, len(buffer)):
                return buffer.value
            if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                return buffer.value
            return ""
        finally:
            kernel32.CloseHandle(handle)

    def _children(hwnd) -> List[Dict[str, Any]]:
        found: List[Dict[str, Any]] = []

        def _enum_child(child_hwnd, _lparam):
            text = _window_text(child_hwnd)
            cls = _class_name(child_hwnd)
            if text or cls in ("Button", "Edit", "Static"):
                found.append({
                    "hwnd": int(child_hwnd),
                    "class": cls,
                    "text": text,
                })
            return True

        user32.EnumChildWindows(hwnd, EnumChildProc(_enum_child), 0)
        return found

    windows: List[Dict[str, Any]] = []

    def _enum(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True

        title = _window_text(hwnd)
        if not title:
            return True

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        image = _process_image(pid.value)
        image_lower = image.lower()
        process_match = (
            not process_name_contains
            or process_name_contains.lower() in image_lower
            or process_name_contains.lower() in title.lower()
        )
        if process_match:
            child_controls = _children(hwnd)
            windows.append({
                "hwnd": int(hwnd),
                "title": title,
                "class": _class_name(hwnd),
                "process_id": int(pid.value),
                "process_image": image,
                "children": child_controls,
                "buttons": [
                    child["text"] for child in child_controls
                    if child.get("class") == "Button" and child.get("text")
                ],
            })
        return True

    user32.EnumWindows(EnumWindowsProc(_enum), 0)
    return {"success": True, "windows": windows, "count": len(windows)}


def register_editor_tools(mcp: FastMCP):

    @mcp.tool()
    def ping_unreal(ctx: Context) -> Dict[str, Any]:
        """Ping the UnrealMCP bridge and return its health response.

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            ping_unreal()"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected to Unreal Engine"}
            return unreal.send_command("ping", {}) or {}
        except Exception as e:
            logger.error(f"Error pinging Unreal bridge: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def get_actor_identity(
        ctx: Context,
        actor_name_or_label: str = "",
        include_all: bool = False,
    ) -> Dict[str, Any]:
        """Return actor labels, object names, full paths, classes, and Blueprint generated-class paths.

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            get_actor_identity()"""
        try:
            return _send_unreal_command("get_actor_identity", {
                "actor_name_or_label": actor_name_or_label,
                "include_all": include_all,
            })
        except Exception as e:
            logger.error(f"Error getting actor identity: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def find_actors_by_class(
        ctx: Context,
        class_name: str,
        exact: bool = False,
    ) -> Dict[str, Any]:
        """Find placed actors by native or Blueprint-generated class name/path.

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            find_actors_by_class(class_name="Actor")"""
        try:
            return _send_unreal_command("find_actors_by_class", {
                "class_name": class_name,
                "exact": exact,
            })
        except Exception as e:
            logger.error(f"Error finding actors by class: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def editor_list_blocking_dialogs(
        ctx: Context,
        process_name_contains: str = "UnrealEditor",
        title_contains: str = "",
    ) -> Dict[str, Any]:
        """List visible Unreal/Windows dialogs that can block MCP automation.

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            editor_list_blocking_dialogs()"""
        try:
            result = _list_windows(process_name_contains=process_name_contains)
            if not result.get("success"):
                return result
            if title_contains:
                needle = title_contains.lower()
                result["windows"] = [
                    window for window in result["windows"]
                    if needle in window.get("title", "").lower()
                    or any(needle in child.get("text", "").lower() for child in window.get("children", []))
                ]
                result["count"] = len(result["windows"])
            return result
        except Exception as e:
            logger.error(f"Error listing blocking dialogs: {e}")
            return {"success": False, "message": str(e), "windows": []}

    @mcp.tool()
    def editor_dismiss_blocking_dialog(
        ctx: Context,
        button_text: str,
        process_name_contains: str = "UnrealEditor",
        title_contains: str = "",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Click a named button on a visible Unreal/Windows dialog, such as Yes, OK, Replace, or Cancel.

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            editor_dismiss_blocking_dialog(button_text="Example")"""
        if not button_text:
            return {"success": False, "message": "button_text is required for safety"}
        if sys.platform != "win32":
            return {"success": False, "message": "Dialog dismissal is only available on Windows"}

        try:
            import ctypes

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            BM_CLICK = 0x00F5

            windows = editor_list_blocking_dialogs(
                ctx=ctx,
                process_name_contains=process_name_contains,
                title_contains=title_contains,
            )
            if not windows.get("success"):
                return windows

            target = button_text.strip().lower()
            candidates = []
            for window in windows.get("windows", []):
                for child in window.get("children", []):
                    if child.get("class") == "Button" and child.get("text", "").strip().lower() == target:
                        candidates.append({"window": window, "button": child})

            if not candidates:
                return {
                    "success": False,
                    "message": f"No matching '{button_text}' button found",
                    "windows": windows.get("windows", []),
                }

            candidate = candidates[0]
            if not dry_run:
                user32.SendMessageW(candidate["button"]["hwnd"], BM_CLICK, 0, 0)

            return {
                "success": True,
                "dry_run": dry_run,
                "clicked_button": candidate["button"]["text"],
                "window_title": candidate["window"]["title"],
                "matched_count": len(candidates),
            }
        except Exception as e:
            logger.error(f"Error dismissing blocking dialog: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def insanitii_phase1_readiness_report(
        ctx: Context,
        include_dialogs: bool = True,
    ) -> Dict[str, Any]:
        """Run the Insanitii Phase 1 smoke-readiness checklist against the open editor.

        The report prefers native bridge routes added for project smoke testing, then
        falls back to read-only UE Python probes when the running editor has not yet
        reloaded the latest UnrealMCP plugin binary.

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            insanitii_phase1_readiness_report()"""
        expected_actor_labels = {
            "INS_RuntimeBootstrap",
            "INS_PostProcessController",
            "INS_TestCube_PleasantMemory",
            "INS_TestCube_BriefComfort",
            "INS_TestCube_NeutralMoment",
            "INS_TestCube_MinorSetback",
            "INS_TestCube_BadMemory",
        }
        expected_actions = {
            "IA_Focus",
            "IA_Breathe",
            "IA_Interact",
            "IA_DebugDecreaseState",
            "IA_DebugIncreaseState",
            "IA_ToggleHUD",
        }
        expected_blueprints = [
            "BP_InsanitiiGameMode",
            "BP_InsanitiiPlayerController",
            "BP_RuntimeBootstrap",
            "BP_MentalStateComponent",
            "BP_InteractionDetector",
            "BP_TestInteractable",
            "BP_PostProcessController",
            "BP_InsanitiiHUD",
        ]

        warnings: List[str] = []
        failures: List[str] = []
        native_fallbacks: List[str] = []

        try:
            ping = _send_unreal_command("ping", {})
            if ping.get("status") != "success" and ping.get("success") is not True and ping.get("message") != "pong":
                failures.append("Unreal bridge ping did not report success.")

            identity = _native_or_python_json(
                "get_actor_identity",
                {"actor_name_or_label": "INS_", "include_all": False},
                _insanitii_actor_fallback_code("INS_"),
            )
            if identity.get("native_unavailable"):
                native_fallbacks.append("get_actor_identity")
            actors = identity.get("actors", []) if identity.get("success", identity.get("status") != "error") else []
            actor_labels = {actor.get("label") or actor.get("name") for actor in actors}
            missing_actors = sorted(expected_actor_labels - actor_labels)
            if missing_actors:
                failures.append(f"Missing expected Insanitii actors: {', '.join(missing_actors)}.")

            bp_class = _native_or_python_json(
                "find_actors_by_class",
                {"class_name": "BP_TestInteractable", "exact": False},
                _insanitii_class_fallback_code("BP_TestInteractable"),
            )
            if bp_class.get("native_unavailable"):
                native_fallbacks.append("find_actors_by_class:BP_TestInteractable")
            bp_class_count = int(bp_class.get("count") or len(bp_class.get("actors", [])))
            if bp_class_count < 5:
                failures.append(f"Expected 5 BP_TestInteractable actors; found {bp_class_count}.")

            native_class = _native_or_python_json(
                "find_actors_by_class",
                {"class_name": "InsanitiiTestInteractable", "exact": False},
                _insanitii_class_fallback_code("InsanitiiTestInteractable"),
            )
            if native_class.get("native_unavailable"):
                native_fallbacks.append("find_actors_by_class:InsanitiiTestInteractable")
            native_class_count = int(native_class.get("count") or len(native_class.get("actors", [])))
            if native_class_count < 5:
                warnings.append(
                    "Native parent-class lookup for InsanitiiTestInteractable found fewer than 5 actors. "
                    "This is expected until the editor reloads the latest UnrealMCP native routes."
                )

            blueprint_checks = []
            for blueprint_name in expected_blueprints:
                result = _native_or_python_json(
                    "check_blueprint_generated_class",
                    {"blueprint_path_or_name": blueprint_name},
                    _insanitii_blueprint_fallback_code(blueprint_name),
                )
                if result.get("native_unavailable"):
                    native_fallbacks.append(f"check_blueprint_generated_class:{blueprint_name}")
                blueprint_checks.append(result)
                if not result.get("success") or not result.get("has_generated_class"):
                    failures.append(f"{blueprint_name} does not have a valid generated class.")

            imc = _native_or_python_json(
                "inspect_input_mapping_context",
                {"imc_path_or_name": "/Game/Input/IMC_Default"},
                _insanitii_imc_fallback_code("/Game/Input/IMC_Default"),
            )
            if imc.get("native_unavailable"):
                native_fallbacks.append("inspect_input_mapping_context")
            mappings = imc.get("mappings", [])
            action_names = {
                mapping.get("action_name") or str(mapping.get("action") or "").split(".")[-1].strip("'\"")
                for mapping in mappings
            }
            missing_actions = sorted(expected_actions - action_names)
            if missing_actions:
                failures.append(f"Missing expected Enhanced Input actions: {', '.join(missing_actions)}.")

            dialogs: Dict[str, Any] = {"success": True, "count": 0, "windows": []}
            if include_dialogs:
                dialogs = editor_list_blocking_dialogs(ctx=ctx)
                if dialogs.get("success") and dialogs.get("count", 0) > 0:
                    warnings.append(f"{dialogs.get('count')} visible Unreal/editor dialog(s) may block automation.")
                elif not dialogs.get("success"):
                    warnings.append(dialogs.get("message", "Could not inspect blocking dialogs."))

            if native_fallbacks:
                warnings.append(
                    "Used exec_python fallback for commands not loaded in the active editor: "
                    + ", ".join(sorted(set(native_fallbacks)))
                )

            status = "pass"
            if failures:
                status = "fail"
            elif warnings:
                status = "warn"

            return {
                "success": not failures,
                "status": status,
                "project": "Insanitii",
                "phase": "Phase 1 readiness",
                "summary": {
                    "bridge_ping": ping,
                    "expected_actor_count": len(expected_actor_labels),
                    "found_insanitii_actor_count": len(actors),
                    "bp_test_interactable_count": bp_class_count,
                    "native_test_interactable_count": native_class_count,
                    "blueprints_checked": len(blueprint_checks),
                    "input_mapping_count": imc.get("mapping_count", len(mappings)),
                    "blocking_dialog_count": dialogs.get("count", 0),
                    "native_fallback_count": len(set(native_fallbacks)),
                },
                "checks": {
                    "actors": {
                        "missing": missing_actors,
                        "labels": sorted(label for label in actor_labels if label),
                        "raw": identity,
                    },
                    "classes": {
                        "bp_test_interactable": bp_class,
                        "native_test_interactable": native_class,
                    },
                    "blueprints": blueprint_checks,
                    "input": {
                        "missing_actions": missing_actions,
                        "action_names": sorted(action for action in action_names if action),
                        "raw": imc,
                    },
                    "dialogs": dialogs,
                },
                "warnings": warnings,
                "failures": failures,
                "next_manual_pie_checklist": [
                    "WASD movement works",
                    "Mouse look works",
                    "F activates Focus and consumes charges",
                    "Tab triggers Breathe and observes cooldown",
                    "- and = adjust Mental State with visible feedback",
                    "E interacts with focused cubes and mutates Mental State",
                    "~ toggles the HUD",
                    "Post-process feedback responds to Mental State",
                    "Consecutive failures increment cascade pressure",
                ],
            }
        except Exception as e:
            logger.error(f"Error building Insanitii readiness report: {e}")
            return {"success": False, "status": "fail", "project": "Insanitii", "message": str(e)}

    @mcp.tool()
    def insanitii_phase2_lifestyle_report(
        ctx: Context,
        include_dialogs: bool = True,
    ) -> Dict[str, Any]:
        """Run the Insanitii Phase 2 lifestyle-framework readiness checklist.

        This smoke workflow verifies that the native time, economy, and lifestyle
        manager classes are visible to the editor, the Blueprint wrapper exists,
        the manager actor is placed, and the manager can generate daily job
        options for the current lifestyle.

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            insanitii_phase2_lifestyle_report()"""
        warnings: List[str] = []
        failures: List[str] = []

        try:
            ping = _send_unreal_command("ping", {})
            if ping.get("status") != "success" and ping.get("success") is not True and ping.get("message") != "pong":
                failures.append("Unreal bridge ping did not report success.")

            probe = _exec_python_json(_insanitii_phase2_lifestyle_fallback_code())
            if not probe.get("success"):
                failures.append(probe.get("message", "Phase 2 editor probe failed."))
                class_checks = {}
                blueprint = {}
                actor = {}
                manager_probe = {}
            else:
                class_checks = probe.get("class_checks", {})
                blueprint = probe.get("blueprint", {})
                actor = probe.get("actor", {})
                manager_probe = probe.get("manager_probe", {})

                missing_classes = [
                    name for name, check in class_checks.items()
                    if not check.get("success")
                ]
                if missing_classes:
                    failures.append(
                        "Native Phase 2 classes are not loaded in the editor: "
                        + ", ".join(missing_classes)
                        + ". Trigger Live Coding or restart the editor after compiling."
                    )

                if not blueprint.get("success"):
                    failures.append("Missing BP_LifestyleManager wrapper at /Game/Insanitii/Gameplay/Lifestyles.")
                elif not blueprint.get("has_generated_class"):
                    failures.append("BP_LifestyleManager exists but has no valid generated class.")

                if not actor.get("success"):
                    failures.append("Missing placed INS_LifestyleManager actor in the current level.")

                if actor.get("success") and not manager_probe.get("success"):
                    failures.append("INS_LifestyleManager is placed but did not generate lifestyle tasks.")

                if manager_probe.get("success") and manager_probe.get("task_count", 0) < 3:
                    warnings.append("Lifestyle manager generated fewer than 3 daily task options.")

            dialogs: Dict[str, Any] = {"success": True, "count": 0, "windows": []}
            if include_dialogs:
                dialogs = editor_list_blocking_dialogs(ctx=ctx)
                if dialogs.get("success") and dialogs.get("count", 0) > 0:
                    warnings.append(f"{dialogs.get('count')} visible Unreal/editor dialog(s) may block automation.")
                elif not dialogs.get("success"):
                    warnings.append(dialogs.get("message", "Could not inspect blocking dialogs."))

            status = "pass"
            if failures:
                status = "fail"
            elif warnings:
                status = "warn"

            return {
                "success": not failures,
                "status": status,
                "project": "Insanitii",
                "phase": "Phase 2 lifestyle framework",
                "summary": {
                    "bridge_ping": ping,
                    "native_class_count": sum(1 for check in class_checks.values() if check.get("success")),
                    "blueprint_has_generated_class": bool(blueprint.get("has_generated_class")),
                    "manager_actor_placed": bool(actor.get("success")),
                    "generated_task_count": int(manager_probe.get("task_count") or 0),
                    "cash_balance": manager_probe.get("economy", {}).get("cash_balance"),
                    "formatted_time": manager_probe.get("time", {}).get("formatted_time"),
                    "blocking_dialog_count": dialogs.get("count", 0),
                },
                "checks": {
                    "classes": class_checks,
                    "blueprint": blueprint,
                    "actor": actor,
                    "manager_probe": manager_probe,
                    "dialogs": dialogs,
                },
                "warnings": warnings,
                "failures": failures,
                "next_manual_pie_checklist": [
                    "Clock advances while PIE is running",
                    "Morning, work, evening, and sleep periods roll over at expected times",
                    "Daily living cost applies once per new day",
                    "Cash balance updates after task success and failure",
                    "Lifestyle task options differ by selected lifestyle",
                    "Transition checks prevent impossible lifestyle changes",
                ],
            }
        except Exception as e:
            logger.error(f"Error building Insanitii Phase 2 lifestyle report: {e}")
            return {"success": False, "status": "fail", "project": "Insanitii", "message": str(e)}

    @mcp.tool()
    def insanitii_phase3_objective_report(
        ctx: Context,
        include_dialogs: bool = True,
    ) -> Dict[str, Any]:
        """Run the Insanitii Phase 3 objective-loop readiness checklist.

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            insanitii_phase3_objective_report()"""
        warnings: List[str] = []
        failures: List[str] = []

        try:
            ping = _send_unreal_command("ping", {})
            if ping.get("status") != "success" and ping.get("success") is not True and ping.get("message") != "pong":
                failures.append("Unreal bridge ping did not report success.")

            probe = _exec_python_json(_insanitii_phase3_objective_fallback_code())
            if not probe.get("success"):
                failures.append(probe.get("message", "Phase 3 objective probe failed."))
                class_checks = {}
                actor_checks = {}
                objective_probe = {}
                station_probe = {}
            else:
                class_checks = probe.get("class_checks", {})
                actor_checks = probe.get("actors", {})
                objective_probe = probe.get("objective_probe", {})
                station_probe = probe.get("station_probe", {})

                missing_classes = [
                    name for name, check in class_checks.items()
                    if not check.get("success")
                ]
                if missing_classes:
                    failures.append(
                        "Native Phase 3 classes are not loaded in the editor: "
                        + ", ".join(missing_classes)
                        + ". Run a closed-editor build and relaunch."
                    )

                missing_actors = [
                    label for label, check in actor_checks.items()
                    if not check.get("success")
                ]
                if missing_actors:
                    failures.append("Missing Phase 3 objective actors: " + ", ".join(missing_actors) + ".")

                if not objective_probe.get("success"):
                    failures.append("INS_SliceObjectiveDirector did not return objective readback.")

                if int(station_probe.get("count") or 0) < 5:
                    failures.append("Expected at least 5 INS_TaskStation actors for the Day 1 loop.")

                stress_station = None
                for station in station_probe.get("stations", []):
                    if station.get("label") == "INS_TaskStation_Stress_OverwhelmingNoise":
                        stress_station = station
                        break
                if not stress_station:
                    failures.append("Missing stress station readback.")
                elif float(stress_station.get("mental_state_delta") or 0.0) < 0.70:
                    warnings.append("Stress station mental-state delta is below the current one-interaction psychosis test target.")

            dialogs: Dict[str, Any] = {"success": True, "count": 0, "windows": []}
            if include_dialogs:
                dialogs = editor_list_blocking_dialogs(ctx=ctx)
                if dialogs.get("success") and dialogs.get("count", 0) > 0:
                    warnings.append(f"{dialogs.get('count')} visible Unreal/editor dialog(s) may block automation.")
                elif not dialogs.get("success"):
                    warnings.append(dialogs.get("message", "Could not inspect blocking dialogs."))

            status = "pass"
            if failures:
                status = "fail"
            elif warnings:
                status = "warn"

            return {
                "success": not failures,
                "status": status,
                "project": "Insanitii",
                "phase": "Phase 3 objective loop",
                "summary": {
                    "bridge_ping": ping,
                    "native_class_count": sum(1 for check in class_checks.values() if check.get("success")),
                    "objective_actor_placed": bool(actor_checks.get("INS_SliceObjectiveDirector", {}).get("success")),
                    "task_station_count": int(station_probe.get("count") or 0),
                    "current_objective": objective_probe.get("current_objective"),
                    "completion_percent": objective_probe.get("completion_percent"),
                    "blocking_dialog_count": dialogs.get("count", 0),
                },
                "checks": {
                    "classes": class_checks,
                    "actors": actor_checks,
                    "objective_probe": objective_probe,
                    "station_probe": station_probe,
                    "dialogs": dialogs,
                },
                "warnings": warnings,
                "failures": failures,
                "next_manual_pie_checklist": [
                    "Interact with sandwich, medication, groceries, laundry, package delivery, commute, work, stress, and sleep stations in objective order",
                    "Confirm HUD objective text advances after each station",
                    "Confirm stress station pushes Mental State below the psychosis threshold",
                    "Confirm a random psychosis event starts and then ends",
                    "Confirm stabilization tools allow progress to the sleep objective",
                    "Confirm sleep completes the Day 1 loop and applies living cost once",
                ],
            }
        except Exception as e:
            logger.error(f"Error building Insanitii Phase 3 objective report: {e}")
            return {"success": False, "status": "fail", "project": "Insanitii", "message": str(e)}

    @mcp.tool()
    def insanitii_place_ordinary_errand_stations(
        ctx: Context,
        load_level: bool = True,
        save_level: bool = True,
    ) -> Dict[str, Any]:
        """Place Insanitii ordinary-errand stations using small, crash-resistant UE Python chunks.

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            insanitii_place_ordinary_errand_stations()"""
        warnings: List[str] = []
        failures: List[str] = []
        placements: List[Dict[str, Any]] = []
        load_result: Dict[str, Any] = {}
        save_result: Dict[str, Any] = {}

        try:
            ping = _send_unreal_command("ping", {})
            if ping.get("status") != "success" and ping.get("success") is not True and ping.get("message") != "pong":
                failures.append("Unreal bridge ping did not report success.")

            if load_level:
                load_result = _exec_python_json(_insanitii_load_level_code())
                if not load_result.get("success"):
                    failures.append("Failed to load /Game/FirstPerson/Lvl_FirstPerson before placement.")

            for spec in _insanitii_ordinary_errand_station_specs():
                placement = _exec_python_json(_insanitii_place_task_station_code(spec))
                placement["requested_spec"] = spec
                placements.append(placement)
                if not placement.get("success"):
                    failures.append(f"Failed to place {spec['label']}: {placement.get('message') or placement.get('errors')}")

            if save_level:
                save_result = _exec_python_json(_insanitii_save_current_level_code())
                if not save_result.get("success") or not save_result.get("saved_current_level"):
                    failures.append("Failed to save current level after ordinary errand station placement.")

            status = "pass"
            if failures:
                status = "fail"
            elif warnings:
                status = "warn"

            return {
                "success": not failures,
                "status": status,
                "project": "Insanitii",
                "phase": "Ordinary errand station placement",
                "summary": {
                    "bridge_ping": ping,
                    "load_requested": load_level,
                    "load_success": bool(load_result.get("success")) if load_level else None,
                    "placement_count": len(placements),
                    "placement_success_count": sum(1 for placement in placements if placement.get("success")),
                    "save_requested": save_level,
                    "save_success": bool(save_result.get("success") and save_result.get("saved_current_level")) if save_level else None,
                },
                "checks": {
                    "load": load_result,
                    "placements": placements,
                    "save": save_result,
                },
                "warnings": warnings,
                "failures": failures,
            }
        except Exception as e:
            logger.error(f"Error placing Insanitii ordinary errand stations: {e}")
            return {"success": False, "status": "fail", "project": "Insanitii", "message": str(e)}

    @mcp.tool()
    def insanitii_place_day1_set_dressing(
        ctx: Context,
        load_level: bool = True,
        save_level: bool = True,
    ) -> Dict[str, Any]:
        """Place readable Day 1 prototype set dressing in small UE Python chunks.

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            insanitii_place_day1_set_dressing()"""
        warnings: List[str] = []
        failures: List[str] = []
        placements: List[Dict[str, Any]] = []
        load_result: Dict[str, Any] = {}
        save_result: Dict[str, Any] = {}

        try:
            ping = _send_unreal_command("ping", {})
            if ping.get("status") != "success" and ping.get("success") is not True and ping.get("message") != "pong":
                failures.append("Unreal bridge ping did not report success.")

            if load_level:
                load_result = _exec_python_json(_insanitii_load_level_code())
                if not load_result.get("success"):
                    failures.append("Failed to load /Game/FirstPerson/Lvl_FirstPerson before set dressing.")

            for spec in _insanitii_day1_set_dressing_specs():
                placement = _exec_python_json(_insanitii_place_set_dressing_actor_code(spec))
                placement["requested_spec"] = {
                    "label": spec.get("label"),
                    "kind": spec.get("kind"),
                }
                placements.append(placement)
                if not placement.get("success"):
                    failures.append(f"Failed to place {spec['label']}: {placement.get('message') or placement.get('errors')}")

            if save_level:
                save_result = _exec_python_json(_insanitii_save_current_level_code())
                if not save_result.get("success") or not save_result.get("saved_current_level"):
                    failures.append("Failed to save current level after Day 1 set dressing.")

            status = "pass"
            if failures:
                status = "fail"
            elif warnings:
                status = "warn"

            kind_counts: Dict[str, int] = {}
            for placement in placements:
                kind = str(placement.get("kind") or placement.get("requested_spec", {}).get("kind") or "unknown")
                kind_counts[kind] = kind_counts.get(kind, 0) + 1

            return {
                "success": not failures,
                "status": status,
                "project": "Insanitii",
                "phase": "Day 1 set dressing",
                "summary": {
                    "bridge_ping": ping,
                    "load_requested": load_level,
                    "load_success": bool(load_result.get("success")) if load_level else None,
                    "placement_count": len(placements),
                    "placement_success_count": sum(1 for placement in placements if placement.get("success")),
                    "kind_counts": kind_counts,
                    "save_requested": save_level,
                    "save_success": bool(save_result.get("success") and save_result.get("saved_current_level")) if save_level else None,
                },
                "checks": {
                    "load": load_result,
                    "placements": placements,
                    "save": save_result,
                },
                "warnings": warnings,
                "failures": failures,
            }
        except Exception as e:
            logger.error(f"Error placing Insanitii Day 1 set dressing: {e}")
            return {"success": False, "status": "fail", "project": "Insanitii", "message": str(e)}

    @mcp.tool()
    def insanitii_world_reactivity_report(ctx: Context) -> Dict[str, Any]:
        """Verify Insanitii Day 1 reactive world actor tagging and director wiring.

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            insanitii_world_reactivity_report()"""
        warnings: List[str] = []
        failures: List[str] = []

        try:
            ping = _send_unreal_command("ping", {})
            if ping.get("status") != "success" and ping.get("success") is not True and ping.get("message") != "pong":
                failures.append("Unreal bridge ping did not report success.")

            probe = _exec_python_json(_insanitii_world_reactivity_probe_code())
            class_check = probe.get("class", {}) if isinstance(probe, dict) else {}
            director = probe.get("director", {}) if isinstance(probe, dict) else {}
            reactive_actor_count = int(probe.get("reactive_actor_count") or 0) if isinstance(probe, dict) else 0
            tracked_actor_count = int(director.get("tracked_actor_count") or 0) if isinstance(director, dict) else 0

            if not class_check.get("success"):
                failures.append("InsanitiiWorldReactiveDirector native class is not visible to Unreal reflection.")
            if not director.get("success"):
                failures.append("INS_WorldReactiveDirector actor is not placed or could not be probed.")
            if reactive_actor_count < 40:
                failures.append("Expected at least 40 tagged Day 1 reactive set-dressing actors.")
            if tracked_actor_count < 40:
                failures.append("World reactive director did not bind at least 40 tagged actors.")

            errors = probe.get("errors") or [] if isinstance(probe, dict) else []
            if errors:
                warnings.extend(str(error) for error in errors)

            status = "pass"
            if failures:
                status = "fail"
            elif warnings:
                status = "warn"

            return {
                "success": not failures,
                "status": status,
                "project": "Insanitii",
                "phase": "World reactivity",
                "summary": {
                    "bridge_ping": ping,
                    "class_visible": bool(class_check.get("success")),
                    "director_present": bool(director.get("success")),
                    "reactive_actor_count": reactive_actor_count,
                    "tracked_actor_count": tracked_actor_count,
                    "debug_summary": director.get("debug_summary", ""),
                },
                "checks": probe,
                "warnings": warnings,
                "failures": failures,
            }
        except Exception as e:
            logger.error(f"Error building Insanitii world reactivity report: {e}")
            return {"success": False, "status": "fail", "project": "Insanitii", "message": str(e)}

    @mcp.tool()
    def insanitii_save_load_report(
        ctx: Context,
        mode: str = "play",
        wait_seconds: float = 8.0,
        stop_after_probe: bool = True,
    ) -> Dict[str, Any]:
        """Verify the Insanitii demo save/load skeleton restores day, cash, and mental state in PIE.

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            insanitii_save_load_report()"""
        warnings: List[str] = []
        failures: List[str] = []

        try:
            bounded_wait = max(1.0, min(float(wait_seconds), 30.0))
            ping = _send_unreal_command("ping", {})
            if ping.get("status") != "success" and ping.get("success") is not True and ping.get("message") != "pong":
                failures.append("Unreal bridge ping did not report success.")

            initial_status = _exec_python_json(_insanitii_pie_status_code())
            launch_probe = _exec_python_json(_insanitii_pie_launch_request_code(mode))
            time.sleep(bounded_wait)
            probe = _exec_python_json(_insanitii_save_load_runtime_probe_code())

            stop_request: Dict[str, Any] = {}
            stop_status: Dict[str, Any] = {}
            if stop_after_probe:
                stop_request = _exec_python_json(_insanitii_pie_stop_request_code())
                time.sleep(min(2.0, bounded_wait))
                stop_status = _exec_python_json(_insanitii_pie_status_code())

            if not probe.get("success"):
                failures.append("Save/load runtime probe did not report success.")
            if not probe.get("save_success"):
                failures.append("SaveDemoState did not succeed.")
            if not probe.get("load_success"):
                failures.append("LoadDemoState did not succeed.")
            if not probe.get("save_exists"):
                failures.append("Demo save slot does not exist after saving.")

            restored_matches = probe.get("restored_matches") or {}
            for key in ("day", "cash", "mental_state"):
                if not restored_matches.get(key):
                    failures.append(f"Saved {key} did not restore to its original value.")

            if stop_after_probe and stop_status and (
                stop_status.get("is_in_play_in_editor") or int(stop_status.get("pie_world_count") or 0) > 0
            ):
                failures.append("PIE was still active after the save/load stop request.")

            errors = probe.get("errors") or []
            if errors:
                warnings.extend(str(error) for error in errors)

            status = "pass"
            if failures:
                status = "fail"
            elif warnings:
                status = "warn"

            return {
                "success": not failures,
                "status": status,
                "project": "Insanitii",
                "phase": "Save/load skeleton",
                "summary": {
                    "bridge_ping": ping,
                    "requested_mode": mode,
                    "launch_requested": bool(launch_probe.get("launch_requested")),
                    "save_success": bool(probe.get("save_success")),
                    "load_success": bool(probe.get("load_success")),
                    "save_exists": bool(probe.get("save_exists")),
                    "restored_matches": restored_matches,
                    "before": probe.get("before"),
                    "mutated": probe.get("mutated"),
                    "restored": probe.get("restored"),
                    "stopped_cleanly": bool(stop_after_probe and stop_status and not stop_status.get("is_in_play_in_editor") and int(stop_status.get("pie_world_count") or 0) == 0),
                },
                "checks": {
                    "initial_status": initial_status,
                    "launch_probe": launch_probe,
                    "probe": probe,
                    "stop_request": stop_request,
                    "stop_status": stop_status,
                },
                "warnings": warnings,
                "failures": failures,
            }
        except Exception as e:
            logger.error(f"Error building Insanitii save/load report: {e}")
            return {"success": False, "status": "fail", "project": "Insanitii", "message": str(e)}

    @mcp.tool()
    def insanitii_phase3_pie_runtime_report(
        ctx: Context,
        mode: str = "play",
        wait_seconds: float = 4.0,
        exercise_loop: bool = True,
        stop_after_probe: bool = True,
        include_dialogs: bool = True,
    ) -> Dict[str, Any]:
        """Launch PIE, probe Insanitii runtime systems, optionally exercise the Day 1 loop, and stop PIE.

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            insanitii_phase3_pie_runtime_report()"""
        warnings: List[str] = []
        failures: List[str] = []

        try:
            ping = _send_unreal_command("ping", {})
            if ping.get("status") != "success" and ping.get("success") is not True and ping.get("message") != "pong":
                failures.append("Unreal bridge ping did not report success.")

            normalized_mode = str(mode or "play").lower()
            if normalized_mode in ("simulate", "sie"):
                warnings.append("PIE was requested in simulate mode; possessed input and HUD behavior still need manual play-mode validation.")
            elif normalized_mode != "play":
                warnings.append(f"Unknown PIE mode '{mode}' was requested; probe will fall back to play mode.")

            bounded_wait = max(0.5, min(float(wait_seconds), 15.0))
            initial_status = _exec_python_json(_insanitii_pie_status_code())
            launch_probe: Dict[str, Any] = {
                "success": True,
                "requested_mode": mode,
                "launch_requested": False,
                "was_in_pie": bool(initial_status.get("is_in_play_in_editor")),
            }
            if not initial_status.get("is_in_play_in_editor"):
                launch_probe = _exec_python_json(_insanitii_pie_launch_request_code(mode))
                time.sleep(bounded_wait)

            probe = _exec_python_json(_insanitii_phase3_pie_runtime_probe_code(
                mode=mode,
                wait_seconds=0.5,
                stop_after_probe=False,
                exercise_loop=exercise_loop,
                allow_launch=False,
            ))
            probe_attempts = [probe]
            if not probe.get("success") and launch_probe.get("launch_requested"):
                time.sleep(min(2.0, bounded_wait))
                probe = _exec_python_json(_insanitii_phase3_pie_runtime_probe_code(
                    mode=mode,
                    wait_seconds=0.5,
                    stop_after_probe=False,
                    exercise_loop=exercise_loop,
                    allow_launch=False,
                ))
                probe_attempts.append(probe)

            stop_request: Dict[str, Any] = {}
            if stop_after_probe:
                stop_request = _exec_python_json(_insanitii_pie_stop_request_code())
                time.sleep(min(2.0, bounded_wait))
                stop_status = _exec_python_json(_insanitii_pie_status_code())
                probe["stop"] = {
                    "requested": bool(stop_request.get("stop_requested")),
                    "is_in_play_in_editor": bool(stop_status.get("is_in_play_in_editor")),
                    "pie_world_count": int(stop_status.get("pie_world_count") or 0),
                    "pie_world_names": stop_status.get("pie_world_names") or [],
                    "request": stop_request,
                    "status": stop_status,
                }

            probe["initial_status"] = initial_status
            probe["launch_probe"] = launch_probe
            probe["probe_attempt_count"] = len(probe_attempts)
            if not probe.get("success"):
                failures.append(probe.get("message", "PIE runtime probe did not return a game world."))

            runtime = probe.get("runtime", {}) if isinstance(probe, dict) else {}
            before = runtime.get("before_exercise", {}) if isinstance(runtime, dict) else {}
            after = runtime.get("after_exercise", {}) if isinstance(runtime, dict) else {}
            exercise = probe.get("exercise", {}) if isinstance(probe, dict) else {}
            stop = probe.get("stop", {}) if isinstance(probe, dict) else {}

            pie_world_count = int(probe.get("pie_world_count") or 0) if isinstance(probe, dict) else 0
            station_count = int(before.get("station_count") or after.get("station_count") or 0)
            world_reactivity_tracked_count = max(
                int(before.get("world_reactivity_tracked_count") or 0),
                int(after.get("world_reactivity_tracked_count") or 0),
            )
            controller_class = str(before.get("controller_class") or "")
            pawn_class = str(before.get("pawn_class") or "")
            hud_class = str(before.get("hud_class") or "")
            mental_state = before.get("mental_state")
            objective_text = str(after.get("objective_text") or before.get("objective_text") or "")
            objective_marker_summary = str(after.get("objective_marker_summary") or before.get("objective_marker_summary") or "")
            objective_anchor_samples = probe.get("objective_anchor_samples") if isinstance(probe, dict) else {}

            if pie_world_count <= 0:
                failures.append("No PIE world was available after the wait window.")
            if not controller_class:
                failures.append("No player controller was available in PIE.")
            if not pawn_class:
                failures.append("No player pawn was available in PIE.")
            if "Spectator" in pawn_class or "Spectator" in controller_class:
                warnings.append("PIE resolved to a spectator-style controller or pawn; possessed gameplay still needs manual validation.")
            if not hud_class:
                failures.append("No HUD was available from the PIE player controller.")
            if mental_state is None:
                failures.append("No Insanitii mental-state component readback was available from the PIE pawn.")
            if not objective_text:
                failures.append("No objective director readback was available in PIE.")
            if station_count < 9:
                failures.append("Expected at least 9 task stations in the PIE world.")
            if not before.get("psychosis_summary") and not after.get("psychosis_summary"):
                failures.append("No psychosis event director readback was available in PIE.")
            if world_reactivity_tracked_count < 40:
                failures.append("World reactivity director did not bind at least 40 Day 1 set-dressing actors in PIE.")

            exercise_errors = exercise.get("errors") or []
            exercise_steps = exercise.get("steps") or []
            friction_slip = exercise.get("friction_slip") or {}
            stabilization_tools = exercise.get("stabilization_tools") or {}
            if exercise_loop:
                if exercise_errors:
                    failures.append("Scripted PIE Day 1 loop reported errors: " + "; ".join(str(error) for error in exercise_errors))
                breathe_after = stabilization_tools.get("breathe_after") or {}
                focus_after = stabilization_tools.get("focus_after") or {}
                if not stabilization_tools.get("breathe_result"):
                    failures.append("Scripted PIE breathe stabilization did not succeed.")
                elif "Breathing steadied" not in str(breathe_after.get("hud_status") or ""):
                    failures.append("Scripted PIE breathe stabilization did not produce HUD feedback.")
                elif float(breathe_after.get("task_feedback_pulse") or 0.0) >= 0.0:
                    failures.append("Scripted PIE breathe stabilization did not produce a clarity pulse.")
                elif float(breathe_after.get("task_feedback_color_shift") or 0.0) >= 0.0:
                    failures.append("Scripted PIE breathe stabilization did not produce a cool color-shift pulse.")

                if not stabilization_tools.get("focus_result"):
                    failures.append("Scripted PIE focus stabilization did not succeed.")
                elif "Focus anchor held" not in str(focus_after.get("hud_status") or ""):
                    failures.append("Scripted PIE focus stabilization did not produce HUD feedback.")
                elif float(focus_after.get("task_feedback_pulse") or 0.0) >= 0.0:
                    failures.append("Scripted PIE focus stabilization did not produce a clarity pulse.")
                elif float(focus_after.get("task_feedback_color_shift") or 0.0) >= 0.0:
                    failures.append("Scripted PIE focus stabilization did not produce a cool color-shift pulse.")
                if len(exercise_steps) < 9:
                    failures.append("Scripted PIE Day 1 loop did not record all nine station interactions.")
                task_hud_steps = [
                    step for step in exercise_steps
                    if "Task complete" in str((step.get("after") or {}).get("hud_status") or "")
                ]
                if len(task_hud_steps) < len(exercise_steps):
                    failures.append("Scripted PIE task interactions did not all produce HUD task-complete feedback.")
                stabilizing_task_pulse_steps = [
                    step for step in exercise_steps
                    if step.get("step") in ("food", "medication", "grocery", "laundry", "sleep")
                    and float((step.get("after") or {}).get("task_feedback_pulse") or 0.0) < 0.0
                    and float((step.get("after") or {}).get("task_feedback_color_shift") or 0.0) < 0.0
                ]
                if len(stabilizing_task_pulse_steps) < 5:
                    failures.append("Scripted PIE stabilizing task interactions did not all produce clarity/cooling post-process pulses.")
                friction_hud_status = str((friction_slip.get("after") or {}).get("hud_status") or "")
                if not friction_slip:
                    failures.append("Scripted PIE friction slip check did not run.")
                elif friction_slip.get("station_used") or friction_slip.get("last_use_succeeded"):
                    failures.append("Scripted PIE friction slip unexpectedly completed the station.")
                elif float(friction_slip.get("friction_risk") or 0.0) <= 0.0:
                    failures.append("Scripted PIE friction slip did not report positive friction risk.")
                elif "Task slipped" not in friction_hud_status or "Friction risk" not in friction_hud_status:
                    failures.append("Scripted PIE friction slip did not produce HUD slip feedback.")
                elif float((friction_slip.get("after") or {}).get("task_feedback_pulse") or 0.0) <= 0.0:
                    failures.append("Scripted PIE friction slip did not produce a distortion post-process pulse.")
                elif float((friction_slip.get("after") or {}).get("task_feedback_color_shift") or 0.0) <= 0.0:
                    failures.append("Scripted PIE friction slip did not produce a warm color-shift pulse.")
                completion = after.get("objective_completion_percent")
                if completion is not None and float(completion) < 1.0:
                    warnings.append("Scripted loop completed without errors but objective completion stayed below 100 percent.")
                stress_intensity = None
                for step in exercise_steps:
                    if step.get("step") == "stress":
                        stress_after = step.get("after") or {}
                        stress_intensity = stress_after.get("world_reactivity_intensity")
                        break
                if stress_intensity is not None and float(stress_intensity) <= 0.0:
                    warnings.append("World reactivity intensity did not rise during the scripted stress beat.")

            if stop_after_probe:
                if stop and (stop.get("is_in_play_in_editor") or int(stop.get("pie_world_count") or 0) > 0):
                    failures.append("PIE was still active after the stop request.")
                elif not stop:
                    warnings.append("PIE stop status was not returned by the runtime probe.")

            if before.get("cash_balance") is None and after.get("cash_balance") is None:
                warnings.append("Lifestyle/economy readback was not available in PIE.")

            dialogs: Dict[str, Any] = {"success": True, "count": 0, "windows": []}
            if include_dialogs:
                dialogs = editor_list_blocking_dialogs(ctx=ctx)
                if dialogs.get("success") and dialogs.get("count", 0) > 0:
                    warnings.append(f"{dialogs.get('count')} visible Unreal/editor dialog(s) may block automation.")
                elif not dialogs.get("success"):
                    warnings.append(dialogs.get("message", "Could not inspect blocking dialogs."))

            status = "pass"
            if failures:
                status = "fail"
            elif warnings:
                status = "warn"

            return {
                "success": not failures,
                "status": status,
                "project": "Insanitii",
                "phase": "Phase 3 PIE runtime loop",
                "summary": {
                    "bridge_ping": ping,
                    "requested_mode": probe.get("requested_mode") if isinstance(probe, dict) else mode,
                    "launch_requested": bool(launch_probe.get("launch_requested")) if isinstance(probe, dict) else False,
                    "was_in_pie": bool(launch_probe.get("was_in_pie")) if isinstance(probe, dict) else False,
                    "is_in_play_in_editor": bool(probe.get("is_in_play_in_editor")) if isinstance(probe, dict) else False,
                    "pie_world_count": pie_world_count,
                    "world_name": probe.get("world_name") if isinstance(probe, dict) else "",
                    "controller_class": controller_class,
                    "pawn_class": pawn_class,
                    "hud_class": hud_class,
                    "last_task_hud_status": after.get("hud_status", before.get("hud_status")),
                    "friction_slip_hud_status": (friction_slip.get("after") or {}).get("hud_status") if isinstance(friction_slip, dict) else "",
                    "friction_slip_task_pulse": (friction_slip.get("after") or {}).get("task_feedback_pulse") if isinstance(friction_slip, dict) else None,
                    "friction_slip_task_color_shift": (friction_slip.get("after") or {}).get("task_feedback_color_shift") if isinstance(friction_slip, dict) else None,
                    "breathe_hud_status": (stabilization_tools.get("breathe_after") or {}).get("hud_status") if isinstance(stabilization_tools, dict) else "",
                    "focus_hud_status": (stabilization_tools.get("focus_after") or {}).get("hud_status") if isinstance(stabilization_tools, dict) else "",
                    "mental_state": mental_state,
                    "objective_text": objective_text,
                    "objective_marker_summary": objective_marker_summary,
                    "objective_anchor_samples": objective_anchor_samples if isinstance(objective_anchor_samples, dict) else {},
                    "objective_completion_percent": after.get("objective_completion_percent", before.get("objective_completion_percent")),
                    "psychosis_active": bool(after.get("psychosis_active", before.get("psychosis_active", False))),
                    "station_count": station_count,
                    "world_reactivity_tracked_count": world_reactivity_tracked_count,
                    "world_reactivity_intensity": after.get("world_reactivity_intensity", before.get("world_reactivity_intensity")),
                    "exercise_step_count": len(exercise_steps),
                    "exercise_error_count": len(exercise_errors),
                    "stopped_cleanly": bool(stop_after_probe and stop and not stop.get("is_in_play_in_editor") and int(stop.get("pie_world_count") or 0) == 0),
                    "blocking_dialog_count": dialogs.get("count", 0),
                },
                "checks": {
                    "initial_status": initial_status,
                    "launch_probe": launch_probe,
                    "probe_attempts": probe_attempts,
                    "stop_request": stop_request,
                    "probe": probe,
                    "runtime_before_exercise": before,
                    "runtime_after_exercise": after,
                    "exercise": exercise,
                    "stop": stop,
                    "dialogs": dialogs,
                },
                "warnings": warnings,
                "failures": failures,
                "next_manual_pie_checklist": [
                    "Possess the player in Play mode and move through food, meds, groceries, laundry, delivery, commute, work, stress, and sleep using normal input",
                    "Confirm HUD objective, mental state, and psychosis text remain readable during movement",
                    "Confirm mouse/keyboard interaction prompts fire from player proximity",
                    "Confirm psychosis visual effects feel engaging and do not permanently break the level",
                    "Confirm audio assets play from authenticated generated content once ElevenLabs access is restored",
                ],
            }
        except Exception as e:
            logger.error(f"Error building Insanitii Phase 3 PIE runtime report: {e}")
            return {"success": False, "status": "fail", "project": "Insanitii", "message": str(e)}

    @mcp.tool()
    def insanitii_audio_feedback_report(ctx: Context) -> Dict[str, Any]:
        """Verify Insanitii generated SoundWave assets and the level audio feedback director wiring.

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            insanitii_audio_feedback_report()"""
        warnings: List[str] = []
        failures: List[str] = []

        try:
            ping = _send_unreal_command("ping", {})
            if ping.get("status") != "success" and ping.get("success") is not True and ping.get("message") != "pong":
                failures.append("Unreal bridge ping did not report success.")

            probe = _exec_python_json(_insanitii_audio_feedback_probe_code())
            assets = probe.get("assets", {}) if isinstance(probe, dict) else {}
            slots = probe.get("slot_assignments", {}) if isinstance(probe, dict) else {}
            actor = probe.get("actor") if isinstance(probe, dict) else None
            errors = probe.get("errors") or [] if isinstance(probe, dict) else []

            if not actor:
                failures.append("INS_AudioFeedbackDirector actor is not present in Lvl_FirstPerson.")

            for key, info in assets.items():
                if not info.get("exists"):
                    failures.append(f"Missing generated audio asset: {key}")
                elif info.get("class") not in ("SoundWave", "SoundCue", "MetaSoundSource"):
                    warnings.append(f"Audio asset {key} loaded as {info.get('class')}, not a standard SoundWave/Cue.")

            looping_expected = probe.get("looping_expected", {}) if isinstance(probe, dict) else {}
            for key, expected in looping_expected.items():
                info = assets.get(key, {})
                if info.get("looping") is not None and bool(info.get("looping")) != bool(expected):
                    warnings.append(f"Audio asset {key} looping={info.get('looping')} but expected {expected}.")

            for key, info in slots.items():
                if not info.get("assigned"):
                    failures.append(f"Audio director slot {key} is not assigned.")
                elif not info.get("matches_expected"):
                    warnings.append(f"Audio director slot {key} points to {info.get('path')} instead of {info.get('expected')}.")

            if errors:
                warnings.extend(str(error) for error in errors)

            status = "pass"
            if failures:
                status = "fail"
            elif warnings:
                status = "warn"

            return {
                "success": not failures,
                "status": status,
                "project": "Insanitii",
                "phase": "Audio feedback slice",
                "summary": {
                    "bridge_ping": ping,
                    "actor_present": bool(actor),
                    "actor_class": actor.get("class") if isinstance(actor, dict) else "",
                    "asset_count": sum(1 for item in assets.values() if item.get("exists")),
                    "assigned_slot_count": sum(1 for item in slots.values() if item.get("assigned")),
                    "looping_asset_count": sum(1 for item in assets.values() if item.get("looping") is True),
                },
                "checks": probe,
                "warnings": warnings,
                "failures": failures,
                "next_manual_pie_checklist": [
                    "Confirm room tone is audible after Play starts",
                    "Drive mental state downward and confirm the stress layer fades in",
                    "Use a stabilizing action and confirm the stabilization cue plays",
                    "Trigger a psychosis event and confirm start/end one-shot cues fire",
                    "Replace generated placeholders with ElevenLabs downloads when the account UI permits audio download",
                ],
            }
        except Exception as e:
            logger.error(f"Error building Insanitii audio feedback report: {e}")
            return {"success": False, "status": "fail", "project": "Insanitii", "message": str(e)}

    @mcp.tool()
    def get_actors_in_level(ctx: Context) -> str:
        """Get a list of all actors in the current UE5 level.

        Returns a compact single-line JSON array of actor objects when the
        editor is connected. When Unreal is unavailable, returns a structured
        JSON error object instead of an empty array so audits do not mistake a
        disconnected bridge for an empty level.
        Example: [{"name": "BP_MyActor", "type": "StaticMeshActor"}, ...]

        Bug #3 fix:
        - Returns a JSON *string* so FastMCP sends it verbatim as a single
          TextContent block (no pydantic_core indent=2 pretty-printing).
        - Connected success responses keep the historical top-level JSON array.

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            get_actors_in_level()"""
        import json as _json
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return _json.dumps({
                    "success": False,
                    "error_code": "ERR_UNREAL_NOT_CONNECTED",
                    "message": "Not connected to Unreal Engine"
                })
            response = unreal.send_command("get_actors_in_level", {})
            if not response:
                return _json.dumps({
                    "success": False,
                    "error_code": "ERR_UNREAL_NO_RESPONSE",
                    "message": "No response from Unreal Engine"
                })
            if "result" in response and "actors" in response["result"]:
                actors = response["result"]["actors"]
            elif "actors" in response:
                actors = response["actors"]
            else:
                actors = []
            # Compact single-line JSON array — no embedded newlines.
            return _json.dumps(actors)
        except Exception as e:
            logger.error(f"Error getting actors: {e}")
            return _json.dumps({
                "success": False,
                "error_code": "ERR_GET_ACTORS_FAILED",
                "message": str(e)
            })

    @mcp.tool()
    def find_actors_by_name(ctx: Context, pattern: str) -> List[str]:
        """Find actors in the level by name pattern (supports wildcards).

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            find_actors_by_name(pattern="Example")"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return []
            response = unreal.send_command("find_actors_by_name", {"pattern": pattern})
            if not response:
                return []
            return response.get("actors", [])
        except Exception as e:
            logger.error(f"Error finding actors: {e}")
            return []

    @mcp.tool()
    def spawn_actor(
        ctx: Context,
        name: str,
        type: str,
        location: List[float] = [0.0, 0.0, 0.0],
        rotation: List[float] = [0.0, 0.0, 0.0]
    ) -> Dict[str, Any]:
        """Spawn a new actor in the current level.

        Args:
            name: Unique name for the actor
            type: Actor type (StaticMeshActor, PointLight, Camera, etc.)
            location: [X, Y, Z] world location
            rotation: [Pitch, Yaw, Roll] in degrees

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            spawn_actor(name="ExampleName", type="Example")"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected to Unreal Engine"}
            params = {
                "name": name,
                "type": type.upper(),
                "location": [float(v) for v in location],
                "rotation": [float(v) for v in rotation]
            }
            response = unreal.send_command("spawn_actor", params)
            return response or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def delete_actor(ctx: Context, name: str) -> Dict[str, Any]:
        """Delete an actor from the level by name.

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            delete_actor(name="ExampleName")"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("delete_actor", {"name": name}) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def set_actor_transform(
        ctx: Context,
        name: str,
        location: List[float] = None,
        rotation: List[float] = None,
        scale: List[float] = None
    ) -> Dict[str, Any]:
        """Set the transform (location, rotation, scale) of an actor.

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            set_actor_transform(name="ExampleName")"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            params = {"name": name}
            if location is not None:
                params["location"] = location
            if rotation is not None:
                params["rotation"] = rotation
            if scale is not None:
                params["scale"] = scale
            return unreal.send_command("set_actor_transform", params) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def get_actor_properties(ctx: Context, name: str) -> Dict[str, Any]:
        """Get all properties of an actor by name.

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            get_actor_properties(name="ExampleName")"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("get_actor_properties", {"name": name}) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def set_actor_property(
        ctx: Context,
        name: str,
        property_name: str,
        property_value
    ) -> Dict[str, Any]:
        """Set a specific property on an actor instance.

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            set_actor_property(name="ExampleName", property_name="ExampleName", property_value="ExampleName")"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("set_actor_property", {
                "name": name,
                "property_name": property_name,
                "property_value": property_value
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def spawn_blueprint_actor(
        ctx: Context,
        blueprint_name: str,
        actor_name: str,
        location: List[float] = [0.0, 0.0, 0.0],
        rotation: List[float] = [0.0, 0.0, 0.0]
    ) -> Dict[str, Any]:
        """Spawn an actor in the level from a Blueprint class.

        Args:
            blueprint_name: Name of the Blueprint asset
            actor_name: Name to give the spawned actor
            location: [X, Y, Z] world location
            rotation: [Pitch, Yaw, Roll] in degrees

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            spawn_blueprint_actor(blueprint_name="/Game/MCP_Test/BP_Example", actor_name="ExampleName")"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            params = {
                "blueprint_name": blueprint_name,
                "actor_name": actor_name,
                "location": [float(v) for v in location],
                "rotation": [float(v) for v in rotation]
            }
            return unreal.send_command("spawn_blueprint_actor", params) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def take_screenshot(
        ctx: Context,
        filename: str = "screenshot",
        show_ui: bool = False,
        resolution: List[int] = [1920, 1080]
    ) -> Dict[str, Any]:
        """Take a screenshot of the Unreal Editor viewport.

        The native bridge expects ``filepath``; keep the public ``filename``
        argument for compatibility and forward both names.

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            take_screenshot()"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("take_screenshot", {
                "filename": filename,
                "filepath": filename,
                "show_ui": show_ui,
                "resolution": resolution
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def exec_python(ctx: Context, code: str) -> Dict[str, Any]:
        """Execute arbitrary Python code inside Unreal Engine via the Python plugin.

        Use this tool when you need to:
        - Create assets in custom project folders (create_blueprint always uses /Game/Blueprints/)
        - Query engine version: import unreal; print(unreal.SystemLibrary.get_engine_version())
        - Count or list assets: unreal.EditorAssetLibrary.list_assets('/Game', recursive=True)
        - Create Widget Blueprints, Behavior Trees, Blackboards, Animation Blueprints
          (use the appropriate factory class since they cannot be created with create_blueprint)
        - Perform bulk operations not covered by other MCP tools

        Args:
            code: Valid Python code string to execute inside UE5.
                  The 'unreal' module is available automatically.
                  Example: "import unreal; print(unreal.SystemLibrary.get_engine_version())"

        Returns:
            dict with 'output' (captured stdout) and 'success' flag.

        IMPORTANT: Always use exec_python for:
          - Assets outside /Game/Blueprints/ (specify full path via AssetTools)
          - Widget Blueprints (WidgetBlueprintFactory)
          - Behavior Trees / Blackboards (BehaviorTreeFactory / BlackboardDataFactory)
          - Animation Blueprints (AnimBlueprintFactory)
          - Checking existing assets before creating duplicates

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            exec_python(code="Example")"""
        from unreal_mcp_server import get_unreal_connection
        import traceback as _tb

        # ── Pre-validate syntax on the Python side (instant, no UE5 round-trip) ──
        # UE5's ExecPythonCommandEx can hang for 30+ s even when a SyntaxError
        # is caught by our try/except wrapper, because the GIL flush after
        # execution is slow on log-heavy projects.
        # Catching SyntaxErrors here returns an error instantly without touching UE5.
        try:
            compile(code, "<mcp_exec>", "exec")
        except SyntaxError as syn_e:
            return {
                "success": False,
                "error": f"SyntaxError: {syn_e}",
                "output": f"SyntaxError: {syn_e}\n{_tb.format_exc()}",
            }

        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected to Unreal Engine"}
            response = unreal.send_command("exec_python", {"code": code}) or {}
            # Normalize response fields — the C++ bridge may use 'output' or 'result'
            if "output" not in response and "result" in response:
                response["output"] = response["result"]
            if "success" not in response:
                response["success"] = response.get("status") != "error"
            return response
        except Exception as e:
            logger.error(f"exec_python error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def save_blueprint(
        ctx: Context,
        blueprint_name: str,
        only_if_dirty: bool = False,
    ) -> Dict[str, Any]:
        """Persist a Blueprint package to disk using the UnrealMCP C++ bridge.

        This invokes the native `save_blueprint` MCP command, which writes the
        package via `UEditorLoadingAndSavingUtils::SavePackages` (UnrealEd). It
        does **not** call Python `unreal.EditorAssetLibrary.save_asset` /
        `save_loaded_asset`, which has crashed with EXCEPTION_ACCESS_VIOLATION in
        EditorScriptingUtilities on some UE 5.6 sessions.

        Typical flow after editing a BP via MCP:
          1. `compile_blueprint(blueprint_name=...)` — marks modified (plugin safe path)
          2. `save_blueprint(blueprint_name=...)` — writes `.uasset`

        Optional: `only_if_dirty=True` maps to the engine's "only save dirty
        packages" behavior; default False saves the listed package regardless.

        Args:
            blueprint_name: Blueprint asset name (e.g. "BP_Cabal")
            only_if_dirty: If True, only persist if the package is dirty

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            save_blueprint(blueprint_name="/Game/MCP_Test/BP_Example")"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected to Unreal Engine"}
            raw = unreal.send_command(
                "save_blueprint",
                {"blueprint_name": blueprint_name, "only_if_dirty": only_if_dirty},
            ) or {}
            saved = bool(raw.get("saved", raw.get("success")))
            return {
                "success": saved,
                "saved": saved,
                "blueprint": raw.get("blueprint", blueprint_name),
                "package": raw.get("package"),
                "raw": raw,
            }
        except Exception as e:
            logger.error(f"save_blueprint error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def focus_viewport(
        ctx: Context,
        location: List[float] = [0.0, 0.0, 0.0],
        distance: float = 1000.0
    ) -> Dict[str, Any]:
        """Move the Unreal Editor viewport camera to focus on a world location.

        Args:
            location: [X, Y, Z] world-space position to look at
            distance: How far back from the location to place the camera (cm)

        KB: see knowledge_base/10_WORLD_BUILDING.md#overview
        Example:
            focus_viewport()"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("focus_viewport", {
                "location": [float(v) for v in location],
                "distance": float(distance)
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    logger.info("Editor tools registered")
