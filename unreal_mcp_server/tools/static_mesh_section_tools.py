"""Bounded read-only static-mesh section inspection for Unreal MCP."""

from __future__ import annotations

import logging
from typing import Annotated, Literal

from mcp.server.fastmcp import Context
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from tools.tool_registration_surface import ToolRegistrationSurface
from tools.unreal_connection_tools import send_unreal_command


logger = logging.getLogger("UnrealMCP")
BoundedText = Annotated[str, Field(max_length=4096)]
Count = Annotated[int, Field(ge=0, le=100_000_000)]
SectionIndex = Annotated[int, Field(ge=0, le=127)]


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", populate_by_name=True, serialize_by_alias=True
    )


class StaticMaterial(_StrictModel):
    material_index: SectionIndex
    slot_name: BoundedText
    imported_slot_name: BoundedText
    material_path: BoundedText


class PolygonGroup(_StrictModel):
    polygon_group_id: SectionIndex
    imported_slot_name: BoundedText
    material_index: Annotated[int, Field(ge=-1, le=127)]
    polygon_count: Count
    triangle_count: Count
    resolved_slot_name: BoundedText
    resolved_imported_slot_name: BoundedText
    resolved_material_path: BoundedText


class RenderSection(_StrictModel):
    section_index: SectionIndex
    material_index: SectionIndex
    first_index: Count
    triangle_count: Count
    min_vertex_index: Count
    max_vertex_index: Count
    collision_enabled: bool
    casts_shadow: bool


class StaticMeshSectionSnapshot(_StrictModel):
    success: Literal[True]
    schema_version: Literal["unreal-mcp/static-mesh-section-snapshot/v1"] = Field(
        alias="schema"
    )
    read_only: Literal[True]
    engine_version: Annotated[str, Field(min_length=1, max_length=4096)]
    asset_path: Annotated[str, Field(min_length=7, max_length=512)]
    object_path: Annotated[str, Field(min_length=1, max_length=4096)]
    lod_index: Annotated[int, Field(ge=0, le=7)]
    source_model_count: Annotated[int, Field(ge=1, le=8)]
    vertex_count: Count
    vertex_instance_count: Count
    polygon_count: Count
    triangle_count: Count
    uv_channel_count: Annotated[int, Field(ge=0, le=16)]
    lightmap_coordinate_index: Annotated[int, Field(ge=-1, le=15)]
    render_data_available: bool
    package_dirty_before: bool
    package_dirty_after: bool
    static_materials: Annotated[list[StaticMaterial], Field(max_length=128)]
    polygon_groups: Annotated[list[PolygonGroup], Field(max_length=128)]
    render_sections: Annotated[list[RenderSection], Field(max_length=128)]


class StaticMeshSectionFailure(_StrictModel):
    success: Literal[False]
    error_code: Annotated[str, Field(min_length=1, max_length=128)]
    message: Annotated[str, Field(min_length=1, max_length=512)]


def _failure(error_code: str, message: str) -> StaticMeshSectionFailure:
    return StaticMeshSectionFailure(
        success=False, error_code=error_code, message=message[:512]
    )


def _native_failure_code(message: str) -> str:
    lowered = message.lower()
    if "not found" in lowered:
        return "ERR_STATIC_MESH_NOT_FOUND"
    if "lod" in lowered and "unavailable" in lowered:
        return "ERR_STATIC_MESH_LOD_UNAVAILABLE"
    if "meshdescription" in lowered:
        return "ERR_STATIC_MESH_DESCRIPTION_UNAVAILABLE"
    if "budget exceeded" in lowered:
        return "ERR_STATIC_MESH_SECTION_BUDGET_EXCEEDED"
    if "dirty state" in lowered:
        return "ERR_STATIC_MESH_PACKAGE_STATE_MUTATED"
    return "ERR_STATIC_MESH_SECTION_INSPECTION_FAILED"


def register_static_mesh_section_tools(mcp: ToolRegistrationSurface) -> None:
    @mcp.tool()
    def inspect_static_mesh_sections(
        ctx: Context,
        asset_path: Annotated[str, Field(min_length=7, max_length=512)],
        lod_index: Annotated[int, Field(ge=0, le=7)] = 0,
        max_sections: Annotated[int, Field(ge=1, le=128)] = 64,
    ) -> StaticMeshSectionSnapshot | StaticMeshSectionFailure:
        """Inspect one static mesh's original material and render sections.

        KB: see knowledge_base/22_GEOMETRY_SCRIPT_AND_MODELING.md#working-example

        Example:
            inspect_static_mesh_sections(asset_path="/Game/Props/SM_Console", lod_index=0)

        This is a bounded read-only native bridge operation. It accepts only a
        project asset below ``/Game/`` and never saves, modifies, or exports the
        mesh. Polygon-group names preserve imported material-section identity
        needed for DCC round trips and material-family classification.
        """
        normalized_path = asset_path.strip()
        if (
            not normalized_path.startswith("/Game/")
            or len(normalized_path) > 512
            or normalized_path.endswith("/")
            or normalized_path != asset_path
            or "//" in normalized_path
            or "/./" in normalized_path
            or "." in normalized_path
            or "\\" in normalized_path
            or ".." in normalized_path
            or any(ord(character) < 32 for character in normalized_path)
        ):
            return _failure(
                "ERR_INVALID_ASSET_PATH",
                "asset_path must name one canonical project asset under /Game/",
            )
        if isinstance(lod_index, bool) or not 0 <= lod_index <= 7:
            return _failure(
                "ERR_INVALID_LOD_INDEX",
                "lod_index must be an integer from 0 through 7",
            )
        if isinstance(max_sections, bool) or not 1 <= max_sections <= 128:
            return _failure(
                "ERR_INVALID_SECTION_LIMIT",
                "max_sections must be an integer from 1 through 128",
            )

        try:
            response = send_unreal_command(
                "inspect_static_mesh_sections",
                {
                    "asset_path": normalized_path,
                    "lod_index": lod_index,
                    "max_sections": max_sections,
                },
            )
            if response.get("status") == "success":
                response = response.get("result", {})
            if response.get("success") is True:
                return StaticMeshSectionSnapshot.model_validate(response)
            message = str(response.get("message") or response.get("error") or "")
            if not message:
                message = "Unreal did not return a static-mesh section snapshot"
            return _failure(_native_failure_code(message), message)
        except ValidationError as exc:
            logger.error("Invalid static-mesh section snapshot: %s", exc)
            return _failure(
                "ERR_STATIC_MESH_SECTION_SNAPSHOT_INVALID",
                "Unreal returned a static-mesh section snapshot that failed its exact contract",
            )
        except Exception as exc:
            logger.error("Error inspecting static mesh sections: %s", exc)
            return _failure(
                "ERR_STATIC_MESH_SECTION_INSPECTION_FAILED", str(exc)
            )
