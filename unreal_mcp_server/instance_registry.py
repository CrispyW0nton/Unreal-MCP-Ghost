"""Which Unreal editor to talk to when several projects are open.

Each editor running the UnrealMCP bridge writes %LOCALAPPDATA%/UnrealMCP/instances/<pid>.json (schema
unreal-mcp-instance-v1: pid, host, port, project_file, project_name, ...) and answers ping with the same identity.
A client names its project with UNREAL_MCP_PROJECT (a .uproject path or a project name) or select_unreal_instance;
resolve_target() then picks that project's editor and refuses to guess when several editors are open and none was
named. Without any records (a plugin build older than the records) the configured UNREAL_HOST/UNREAL_PORT is used.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCHEMA = "unreal-mcp-instance-v1"
DEFAULT_PORT = 55655
_selected_project: Optional[str] = None


class TargetResolutionError(RuntimeError):
    """The editor for this client cannot be chosen safely."""


@dataclass(frozen=True)
class UnrealInstance:
    pid: int
    host: str
    port: int
    project_file: str
    project_name: str
    engine_version: str = ""
    started_utc: str = ""
    port_source: str = ""
    record_path: str = ""

    def describe(self) -> str:
        return f"{self.project_name} (pid {self.pid}, port {self.port})"


def registry_dir() -> Path:
    override = os.environ.get("UNREAL_MCP_INSTANCE_DIR", "").strip()
    if override:
        return Path(override)
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "UnrealMCP" / "instances"


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def list_instances(directory: Optional[Path] = None) -> List[UnrealInstance]:
    """Live editors from the instance records; records of exited editors are ignored."""
    directory = directory or registry_dir()
    out: List[UnrealInstance] = []
    if not directory.is_dir():
        return out
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("schema") != SCHEMA:
                continue
            inst = UnrealInstance(
                pid=int(data["pid"]), host=str(data.get("host") or "127.0.0.1"), port=int(data["port"]),
                project_file=str(data.get("project_file") or ""), project_name=str(data.get("project_name") or ""),
                engine_version=str(data.get("engine_version") or ""), started_utc=str(data.get("started_utc") or ""),
                port_source=str(data.get("port_source") or ""), record_path=str(path))
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if pid_alive(inst.pid):
            out.append(inst)
    return out


def _norm_path(value: str) -> str:
    return os.path.normcase(os.path.normpath(os.path.abspath(value))).replace("\\", "/")


def matches(project: str, project_file: str, project_name: str) -> bool:
    """A .uproject path matches the file; a bare name matches the project name or the file's stem."""
    target = project.strip()
    if not target:
        return False
    if target.lower().endswith(".uproject") or "/" in target or "\\" in target:
        return bool(project_file) and _norm_path(target) == _norm_path(project_file)
    stem = Path(project_file).stem if project_file else ""
    return target.lower() in {project_name.lower(), stem.lower()}


def select_project(project: Optional[str]) -> None:
    """Pin this client to a project for the rest of the session (None clears the pin)."""
    global _selected_project
    _selected_project = project.strip() if project and project.strip() else None


def selected_project() -> Optional[str]:
    return _selected_project or (os.environ.get("UNREAL_MCP_PROJECT", "").strip() or None)


def resolve_target(
    project: Optional[str] = None,
    configured_host: str = "127.0.0.1",
    configured_port: int = DEFAULT_PORT,
    port_pinned: bool = False,
    directory: Optional[Path] = None,
) -> Tuple[str, int, Optional[UnrealInstance]]:
    """(host, port, instance) of the editor this client should talk to."""
    live = list_instances(directory)
    if project:
        hits = [i for i in live if matches(project, i.project_file, i.project_name)]
        if len(hits) == 1:
            return hits[0].host, hits[0].port, hits[0]
        if len(hits) > 1:
            raise TargetResolutionError(
                f"{len(hits)} editors are open on {project}: {', '.join(i.describe() for i in hits)}. Close one, "
                "or pin a port with UNREAL_PORT and UNREAL_MCP_PORT_PINNED=1.")
        if not live:
            # no records at all: an editor built before instance records; ping confirms the project where it can
            return configured_host, configured_port, None
        raise TargetResolutionError(
            f"No open Unreal editor with the UnrealMCP bridge is on {project}. Open: "
            f"{', '.join(i.describe() for i in live) or 'none'}.")
    if port_pinned:
        return configured_host, configured_port, next((i for i in live if i.port == configured_port), None)
    if len(live) == 1:
        return live[0].host, live[0].port, live[0]
    if not live:
        return configured_host, configured_port, None
    raise TargetResolutionError(
        "Several Unreal editors are running the UnrealMCP bridge: "
        f"{', '.join(i.describe() for i in live)}. Name the project with UNREAL_MCP_PROJECT or "
        "select_unreal_instance so commands cannot reach the wrong one.")


def check_identity(ping_result: Dict[str, Any], project: Optional[str]) -> None:
    """Refuse an editor whose ping names another project (older plugins do not report identity)."""
    if not project or not isinstance(ping_result, dict):
        return
    result = ping_result.get("result", ping_result)
    project_file = str(result.get("project_file") or "")
    project_name = str(result.get("project_name") or "")
    if not project_file and not project_name:
        return
    if not matches(project, project_file, project_name):
        raise TargetResolutionError(
            f"The editor on this port is open on {project_name or project_file}, not {project}; refusing to send commands.")


def instances_report(directory: Optional[Path] = None) -> List[Dict[str, Any]]:
    return [asdict(i) for i in list_instances(directory)]
