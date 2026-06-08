"""Tripo provider implementation for the generative content pipeline."""

from __future__ import annotations

import urllib.parse
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from . import ProviderOutputPolicy, path_has_extension


class TripoProvider:
    name = "tripo"
    display_name = "Tripo"
    base_url = "https://api.tripo3d.ai/v2/openapi"
    capabilities = (
        "text_to_model",
        "image_to_model",
        "multiview_to_model",
        "refine_model",
        "texture_model",
        "magic_brush_retexture_generate",
        "magic_brush_get_retexture",
        "magic_brush_get_retexture_images",
        "magic_brush_apply_retexture",
        "post_process",
        "download_result",
        "import_to_project",
    )
    final_statuses = ("success", "failed", "banned", "expired", "cancelled", "unknown")
    texture_from_prompt_reason = (
        "Tripo texture_model retextures an existing model task and does not "
        "create standalone BaseColor/Normal/ORM texture maps from only a prompt."
    )
    output_policy = ProviderOutputPolicy(
        model_output_keys=("model", "base_model", "pbr_model", "rendered_image", "generated_image"),
        import_output_keys=("pbr_model", "model", "base_model", "rendered_image", "generated_image"),
        model_extensions=(".fbx", ".obj", ".gltf", ".glb"),
        image_extensions=(".png", ".jpg", ".jpeg", ".tga", ".exr", ".hdr", ".bmp", ".webp"),
    )

    def describe(self, config: Mapping[str, Any]) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "display_name": self.display_name,
            "status": "configured" if config.get("api_key_configured") else "auth_missing",
            "capabilities": list(self.capabilities),
            "base_url": self.base_url,
            "output_policy": {
                "model_output_keys": list(self.output_policy.model_output_keys),
                "import_output_keys": list(self.output_policy.import_output_keys),
                "model_extensions": list(self.output_policy.model_extensions),
                "image_extensions": list(self.output_policy.image_extensions),
            },
            "unsupported_capabilities": [self.texture_from_prompt_status()],
            "config": {
                "api_key_configured": bool(config.get("api_key_configured")),
                "api_key_source": config.get("api_key_source", "missing"),
                "default_model_version": config.get("default_model_version", "tripo-default"),
                "default_texture_quality": config.get("default_texture_quality", "standard"),
                "output_folder": config.get("output_folder", "/Game/Generated"),
                "session_credit_budget": config.get("session_credit_budget", 0),
            },
            "next_milestones": ["D.8 knowledge base", "D.9 chat dock integration"],
        }

    def normalize_model_version(self, value: str | None) -> str:
        version = (value or "").strip()
        return "" if version in {"", "tripo-default", "api-default"} else version

    def estimate_credits(self, task_type: str, payload: Mapping[str, Any]) -> int:
        model_version = str(payload.get("model_version", ""))
        is_p1 = model_version.startswith("P1")
        texture = bool(payload.get("texture", True) or payload.get("pbr", True))
        quality = str(payload.get("texture_quality", "standard")).lower()
        if task_type == "text_to_model":
            base = 30 if is_p1 else 10
            credits = base + (10 if texture else 0)
        elif task_type in {"image_to_model", "multiview_to_model"}:
            base = 40 if is_p1 else 20
            credits = base + (10 if texture else 0)
        elif task_type == "texture_model":
            credits = 10
        elif task_type == "magic_brush_retexture_generate":
            credits = 10
        elif task_type == "magic_brush_apply_retexture":
            credits = 5
        elif task_type == "convert_model":
            advanced_keys = {
                "quad",
                "face_limit",
                "flatten_bottom",
                "flatten_bottom_threshold",
                "texture_size",
                "texture_format",
                "pivot_to_center_bottom",
                "scale_factor",
            }
            credits = 5 + (5 if any(key in payload and payload.get(key) not in (None, False, "", 0) for key in advanced_keys) else 0)
        elif task_type == "refine_model":
            credits = 20
        else:
            credits = 0
        if task_type in {"text_to_model", "image_to_model", "multiview_to_model", "texture_model"}:
            credits += {"standard": 10, "detailed": 20, "extreme": 30}.get(quality, 0) if texture else 0
            if payload.get("smart_low_poly"):
                credits += 10
            if payload.get("quad"):
                credits += 5
            if payload.get("generate_parts"):
                credits += 20
        return max(0, credits)

    def output_suffix(self, key: str, url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        suffix = Path(parsed.path).suffix.lower()
        if suffix:
            return suffix
        if key in {"model", "base_model", "pbr_model"}:
            return ".glb"
        if key in {"rendered_image", "generated_image"}:
            return ".png"
        return ".bin"

    def select_primary_model_download(self, downloads: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
        download_list = [dict(item) for item in downloads]
        by_key = {item.get("key"): item for item in download_list}
        for key in ("pbr_model", "model", "base_model"):
            item = by_key.get(key)
            if item and path_has_extension(str(item.get("path", "")), self.output_policy.model_extensions):
                return item
        for item in download_list:
            if path_has_extension(str(item.get("path", "")), self.output_policy.model_extensions):
                return item
        return {}

    def supports_texture_from_prompt(self) -> bool:
        return False

    def texture_from_prompt_status(self) -> Dict[str, Any]:
        return {
            "capability": "texture_from_prompt",
            "supported": False,
            "reason": self.texture_from_prompt_reason,
            "supported_alternative": "Use gen_tripo_texture_model when an original_model_task_id already exists.",
            "future_provider": "Stability, ComfyUI, or a local texture provider",
        }


TRIPO_PROVIDER = TripoProvider()
