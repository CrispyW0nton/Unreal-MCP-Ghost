"""Uthana provider metadata for generated animation and motion pipelines."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from . import ProviderOutputPolicy, path_has_extension


class UthanaProvider:
    name = "uthana"
    display_name = "Uthana"
    base_url = "https://uthana.com/graphql"
    capabilities = (
        "text_to_motion",
        "video_to_motion",
        "stitch_motion",
        "loop_motion",
        "auto_rig_character",
        "retarget_motion",
        "download_motion",
        "import_animation_to_project",
    )
    final_statuses = ("success", "failed", "cancelled", "unknown")
    output_policy = ProviderOutputPolicy(
        model_output_keys=("motion_fbx", "motion_glb", "motion_only_glb", "character_glb"),
        import_output_keys=("motion_fbx", "motion_glb", "motion_only_glb"),
        model_extensions=(".fbx", ".glb", ".gltf", ".bvh"),
        image_extensions=(),
    )

    def describe(self, config: Mapping[str, Any]) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "display_name": self.display_name,
            "status": "configured" if config.get("uthana_api_key_configured") else "auth_missing",
            "provider_role": "animation_motion",
            "capabilities": list(self.capabilities),
            "base_url": self.base_url,
            "output_policy": {
                "model_output_keys": list(self.output_policy.model_output_keys),
                "import_output_keys": list(self.output_policy.import_output_keys),
                "model_extensions": list(self.output_policy.model_extensions),
                "image_extensions": list(self.output_policy.image_extensions),
            },
            "config": {
                "api_key_configured": bool(config.get("uthana_api_key_configured")),
                "api_key_source": config.get("uthana_api_key_source", "missing"),
                "default_character_id": config.get("uthana_default_character_id", "cXi2eAP19XwQ"),
                "output_folder": config.get("animation_output_folder", "/Game/Generated/Animations"),
            },
            "pipeline_notes": [
                "Use Uthana for generated humanoid motion, not static mesh generation.",
                "Download FBX or GLB motion output before Unreal animation import and retarget proof.",
                "Keep Uthana calls behind provider key, wallet/quota, and explicit spend/usage gates.",
            ],
            "next_milestones": ["D.114 guarded motion tools", "retarget readback evidence", "AnimGraph and PIE proof automation"],
        }

    def normalize_model_version(self, value: str | None) -> str:
        return (value or "").strip()

    def estimate_credits(self, task_type: str, payload: Mapping[str, Any]) -> int:
        if task_type in {"text_to_motion", "video_to_motion", "retarget_motion"}:
            return int(payload.get("estimated_seconds", 5) or 5)
        return 0

    def output_suffix(self, key: str, url: str) -> str:
        suffix = Path(str(url)).suffix.lower()
        if suffix:
            return suffix
        if key.endswith("fbx"):
            return ".fbx"
        if key.endswith("glb"):
            return ".glb"
        return ".bin"

    def select_primary_model_download(self, downloads: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
        download_list = [dict(item) for item in downloads]
        for key in ("motion_fbx", "motion_glb", "motion_only_glb"):
            for item in download_list:
                if item.get("key") == key and path_has_extension(str(item.get("path", "")), self.output_policy.model_extensions):
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
            "reason": "Uthana is a motion/animation provider and does not generate texture sets.",
            "supported_alternative": "Use a texture-capable provider or Tripo texture_model for existing model tasks.",
            "future_provider": "Stability, ComfyUI, or a local texture provider",
        }


UTHANA_PROVIDER = UthanaProvider()
