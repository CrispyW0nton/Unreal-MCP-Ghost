"""
Editor Tools - Actor management, viewport, spawning.
Ported from: https://github.com/chongdashu/unreal-mcp
"""
import json
import logging
import sys
import textwrap
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
        """Ping the UnrealMCP bridge and return its health response."""
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
        """Return actor labels, object names, full paths, classes, and Blueprint generated-class paths."""
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
        """Find placed actors by native or Blueprint-generated class name/path."""
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
        """List visible Unreal/Windows dialogs that can block MCP automation."""
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
        """Click a named button on a visible Unreal/Windows dialog, such as Yes, OK, Replace, or Cancel."""
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
        """
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
            if ping.get("status") != "success" and ping.get("success") is not True:
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
        """
        warnings: List[str] = []
        failures: List[str] = []

        try:
            ping = _send_unreal_command("ping", {})
            if ping.get("status") != "success" and ping.get("success") is not True:
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
        """
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
        """Find actors in the level by name pattern (supports wildcards)."""
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
        """
        Spawn a new actor in the current level.

        Args:
            name: Unique name for the actor
            type: Actor type (StaticMeshActor, PointLight, Camera, etc.)
            location: [X, Y, Z] world location
            rotation: [Pitch, Yaw, Roll] in degrees
        """
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
        """Delete an actor from the level by name."""
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
        """Set the transform (location, rotation, scale) of an actor."""
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
        """Get all properties of an actor by name."""
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
        """Set a specific property on an actor instance."""
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
        """
        Spawn an actor in the level from a Blueprint class.

        Args:
            blueprint_name: Name of the Blueprint asset
            actor_name: Name to give the spawned actor
            location: [X, Y, Z] world location
            rotation: [Pitch, Yaw, Roll] in degrees
        """
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
        """Take a screenshot of the Unreal Editor viewport."""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("take_screenshot", {
                "filename": filename,
                "show_ui": show_ui,
                "resolution": resolution
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def exec_python(ctx: Context, code: str) -> Dict[str, Any]:
        """
        Execute arbitrary Python code inside Unreal Engine via the Python plugin.

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
        """
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
        """
        Persist a Blueprint package to disk using the UnrealMCP C++ bridge.

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
        """
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
        """
        Move the Unreal Editor viewport camera to focus on a world location.

        Args:
            location: [X, Y, Z] world-space position to look at
            distance: How far back from the location to place the camera (cm)
        """
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
