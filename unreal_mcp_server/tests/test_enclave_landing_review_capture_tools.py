from __future__ import annotations

import hashlib
import inspect
import unittest
from unittest.mock import patch

from tools import enclave_landing_review_capture_tools as tools


class LandingReviewCaptureToolTests(unittest.TestCase):
    def test_pinned_script_digest_and_scope(self) -> None:
        body = tools._SCRIPT_PATH.read_bytes()
        self.assertEqual(hashlib.sha256(body).hexdigest(), tools._SCRIPT_SHA256)
        text = body.decode("utf-8")
        self.assertIn('replace("_v2", "_v3")', text)
        self.assertIn("CAMERAS_V3", text)
        self.assertIn('MODE == "finalize"', text)
        self.assertIn('MODE == "prepare_native_capture"', text)
        self.assertIn("eject_pilot_level_actor", text)
        self.assertIn("set_level_viewport_camera_info", text)
        self.assertIn("unreal.UnrealEditorSubsystem", text)
        self.assertNotIn("set_level_viewport_fov", text)
        self.assertIn('"position_wide": "wide"', text)
        self.assertIn('"position_mid": "mid"', text)
        self.assertIn('"position_entry": "entry"', text)
        self.assertIn('"render_wide": "wide"', text)
        self.assertIn('"render_mid": "mid"', text)
        self.assertIn('"render_entry": "entry"', text)
        self.assertIn("unreal.SceneCapture2D", text)
        self.assertIn("create_render_target2d", text)
        self.assertIn("capture_scene", text)
        self.assertIn("export_render_target", text)
        self.assertIn("release_render_target2d", text)
        self.assertIn("_superseded_identical_views.json", text)
        self.assertIn('"superseded_reason": "identical-capture-hashes"', text)
        self.assertIn("len(existing_hashes) == 1", text)
        self.assertIn("len(current_hashes) == len(CAMERAS)", text)
        self.assertIn("os.replace(replacement_path, receipt_path)", text)
        self.assertIn("capture_sha256", text)
        self.assertIn("capture_bytes", text)
        self.assertIn("take_high_res_screenshot", text)
        self.assertNotIn("is_task_done", text)
        self.assertNotIn("register_slate_post_tick_callback", text)
        self.assertNotIn('"queued": True', text)
        self.assertNotIn("eval(", text)

    def test_deferred_apply_is_receipt_reconciled(self) -> None:
        code = tools._deferred_apply_code("_result.update({'ok': True})")
        compile(code, "<landing-review-deferred>", "exec")
        self.assertIn("register_slate_post_tick_callback", code)
        self.assertIn('_review_state["namespace"]', code)
        self.assertIn('_review_state["started"]', code)
        self.assertIn("_REVIEW_RECEIPT", code)
        self.assertIn("_REVIEW_FAILURE", code)
        self.assertIn("enclave_landing_review_capture_v3_receipt.json", code)
        self.assertIn("enclave_landing_review_capture_v3_failure.json", code)

    def test_exact_capture_uses_fixed_transient_scene_render(self) -> None:
        self.assertEqual(len(tools._CAPTURE_VIEWS), 3)
        source = inspect.getsource(tools._capture_exact_views)
        self.assertIn('_pinned_script("render_" + key)', source)
        self.assertIn('render_outputs.get("rendered") is not True', source)
        self.assertNotIn('"focus_viewport"', source)
        self.assertNotIn('"take_screenshot"', source)

    def test_apply_ejects_any_automation_camera_lock_before_native_capture(self) -> None:
        source = inspect.getsource(tools.register_enclave_landing_review_capture_tools)
        self.assertIn('_pinned_script("prepare_native_capture")', source)
        self.assertIn('preparation_outputs.get("prepared") is not True', source)

    def test_exact_capture_requires_attested_output_for_each_scene_render(self) -> None:
        paths = {
            "wide": r"C:\fixed\landing_review_wide_v1.png",
            "mid": r"C:\fixed\landing_review_mid_v1.png",
            "entry": r"C:\fixed\landing_review_entry_v1.png",
        }
        responses = []
        for index in range(3):
            responses.append(
                {"outputs": {"rendered": True, "capture_bytes": index + 1, "capture_sha256": f"{index + 1:064x}"}}
            )
        with patch.object(tools, "_exec_structured", side_effect=responses) as render:
            captures = tools._capture_exact_views(paths)
        self.assertEqual(render.call_count, 3)
        self.assertEqual([item["capture_bytes"] for item in captures], [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
