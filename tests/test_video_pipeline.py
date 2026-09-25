"""Contracts for the canonical HTML-to-HyperFrames video pipeline."""
from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import Registry
from core.registry import ContractError
from core.validation import validate_deck
from tools.compose_video import build_hyperframes_composition
from tools.motion_patterns import load_motion_patterns, motion_pattern_ids, rank_motion_patterns
from tools.render_request import RenderRequestError, resolve_push_request
from tools.video_pipeline import (
    VideoPipelineError,
    compile_video_timing,
    sample_frames,
    validate_video_timing,
)
from tools.verify_video import verify_frame_directory, validate_h264_pixel_format

ROOT = Path(__file__).resolve().parents[1]


class VideoPipelineTests(unittest.TestCase):
    def setUp(self):
        self.registry = Registry(ROOT)
        self.spec = {
            "schemaVersion": 1,
            "title": "Video test",
            "language": "ko",
            "theme": "tech",
            "slides": [{
                "id": "one",
                "title": "하나의 핵심",
                "communication_goal": "한 가지 메시지를 강조한다",
                "intent": "thesis",
                "blocks": [{
                    "id": "message",
                    "module": "statement",
                    "data": {"text": "핵심 메시지"}
                }],
                "motion": [{
                    "module": "focus",
                    "target": "message",
                    "reason": "핵심 문장을 주목시킨다"
                }]
            }]
        }

    def compose(self):
        return build_hyperframes_composition(self.spec, self.registry)

    def test_video_composition_is_deterministic(self):
        html_a, timing_a, _ = self.compose()
        html_b, timing_b, _ = self.compose()
        self.assertEqual(timing_a, timing_b)
        self.assertEqual(html_a, html_b)

    def test_html_is_the_only_visual_source_of_truth(self):
        html, timing, _ = self.compose()
        self.assertIn('data-composition-id="html-slide-video"', html)
        self.assertIn('data-no-timeline', html)
        self.assertIn('class="clip layout-', html)
        self.assertIn('id="hf-slide-0"', html)
        self.assertIn('id="s-one--message"', html)
        self.assertIn('핵심 메시지', html)
        scene = timing["scenes"][0]
        self.assertNotIn("blocks", scene)
        self.assertNotIn("slots", scene)
        self.assertNotIn("design", timing)
        self.assertNotIn("communicationGoal", scene)

    def test_hyperframes_contract_has_explicit_size_duration_and_fps(self):
        html, timing, _ = self.compose()
        self.assertIn('data-width="1920"', html)
        self.assertIn('data-height="1080"', html)
        self.assertIn('data-fps="30"', html)
        self.assertRegex(html, r'data-duration="[0-9.]+"')
        summary = validate_video_timing(timing)
        self.assertEqual(summary["width"], 1920)
        self.assertEqual(summary["height"], 1080)
        self.assertEqual(summary["fps"], 30)

    def test_timing_preserves_semantic_motion(self):
        _, timing, _ = self.compose()
        scene = timing["scenes"][0]
        cue = scene["cues"][0]
        self.assertEqual(cue["target"], "message")
        self.assertEqual(cue["module"], "focus")
        self.assertEqual(cue["reason"], "핵심 문장을 주목시킨다")
        self.assertGreater(scene["durationFrames"], cue["atFrame"])

    def test_video_adapter_has_no_wall_clock_animation(self):
        runtime = (ROOT / "core" / "hyperframes_runtime.js").read_text(encoding="utf-8")
        for forbidden in (
            "requestAnimationFrame(",
            "performance.now(",
            "Date.now(",
            "Math.random(",
            "setTimeout(",
            "setInterval(",
        ):
            self.assertNotIn(forbidden, runtime)
        self.assertIn(".animate(", runtime)
        self.assertIn(".pause()", runtime)

    def test_video_css_disables_transitions(self):
        html, _, _ = self.compose()
        self.assertIn("transition:none!important", html)

    def test_all_motion_patterns_are_canonical_core_entries(self):
        patterns = load_motion_patterns()
        self.assertEqual(len(patterns), 27)
        self.assertEqual(set(patterns), motion_pattern_ids())
        for pattern in patterns.values():
            self.assertNotIn("html", pattern)
            self.assertNotIn("remotion", pattern)
            self.assertTrue(pattern["targets"])
            self.assertTrue(pattern["semanticModules"])
            self.assertTrue(pattern["intents"])
            self.assertTrue(pattern["tones"])
            self.assertIn(pattern["intensity"], {"low", "medium", "high"})
            self.assertIn(pattern["complexity"], {"light", "medium", "heavy"})

    def test_selected_pattern_is_preserved_in_html_and_timing(self):
        self.spec["slides"][0]["motion"][0]["pattern"] = "glitch"
        validate_deck(self.spec, self.registry)
        html, timing, _ = self.compose()
        cue = timing["scenes"][0]["cues"][0]
        self.assertEqual(cue["pattern"], "glitch")
        self.assertEqual(cue["patternSource"], "explicit")
        self.assertIn('data-pattern="glitch"', html)

    def test_auto_pattern_uses_single_renderer_ranking(self):
        self.spec["style"] = {
            "signals": {"tone": ["technical"], "density": "medium"}
        }
        self.spec["slides"][0]["motion"][0].update(pattern="auto", intensity="high")
        expected = rank_motion_patterns(
            intent="thesis",
            target="statement",
            semantic_module="focus",
            tones=["technical"],
            intensity="high",
            density="medium",
            topic="하나의 핵심 한 가지 메시지를 강조한다",
        )[0]["id"]
        _, timing, _ = self.compose()
        cue = timing["scenes"][0]["cues"][0]
        self.assertEqual(cue["pattern"], expected)
        self.assertEqual(cue["patternSource"], "auto")
        self.assertTrue(cue["patternReasons"])

    def test_explicit_pattern_rejects_incompatible_target(self):
        png = (
            "data:image/png;base64,"
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZgL8AAAAASUVORK5CYII="
        )
        self.spec["slides"][0].update(
            intent="scene",
            blocks=[{
                "id": "photo",
                "module": "image",
                "data": {"src": png, "alt": "test", "fit": "cover"},
            }],
            motion=[{
                "module": "focus",
                "target": "photo",
                "reason": "사진을 강조한다",
                "pattern": "scramble-decode",
            }],
        )
        with self.assertRaises(ContractError):
            self.compose()

    def test_image_blocks_remain_embedded_in_same_html(self):
        png = (
            "data:image/png;base64,"
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZgL8AAAAASUVORK5CYII="
        )
        self.spec["slides"][0].update(
            intent="scene",
            blocks=[{
                "id": "photo",
                "module": "image",
                "data": {"src": png, "alt": "test image", "fit": "cover"}
            }],
            motion=[{
                "module": "focus",
                "target": "photo",
                "reason": "사진 근거를 주목시킨다"
            }]
        )
        html, _, _ = self.compose()
        self.assertIn("data:image/png;base64,", html)

    def test_sequence_motion_expands_to_phase_cues(self):
        self.spec["slides"][0]["intent"] = "sequence"
        self.spec["slides"][0]["blocks"] = [{
            "id": "steps",
            "module": "timeline",
            "data": {"items": ["a", "b", "c"]}
        }]
        self.spec["slides"][0]["motion"] = [{
            "module": "sequence-step",
            "target": "steps",
            "reason": "순서를 단계별로 보여준다"
        }]
        _, timing, _ = self.compose()
        cues = timing["scenes"][0]["cues"]
        self.assertEqual([cue["step"] for cue in cues], [1, 2, 3])
        self.assertEqual([cue["atFrame"] for cue in cues], [18, 54, 90])

    def test_timing_contract_and_sample_frames(self):
        _, timing, _ = self.compose()
        summary = validate_video_timing(timing)
        self.assertEqual(summary["scenes"], 1)
        frames = sample_frames(timing)
        self.assertEqual(frames[0], 0)
        self.assertEqual(frames[-1], timing["durationInFrames"] - 1)
        self.assertIn(timing["scenes"][0]["cues"][0]["atFrame"], frames)

    def test_timing_rejects_cue_overflow(self):
        _, timing, _ = self.compose()
        timing["scenes"][0]["cues"][0]["durationFrames"] = timing["scenes"][0]["durationFrames"]
        with self.assertRaises(VideoPipelineError):
            validate_video_timing(timing)

    def test_compile_video_timing_rejects_invalid_fps(self):
        _, _, plan = self.compose()
        with self.assertRaises(VideoPipelineError):
            compile_video_timing(self.spec, plan, fps=0)

    def test_png_frame_contract(self):
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZgL8AAAAASUVORK5CYII="
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "frame-000.png").write_bytes(png)
            report = verify_frame_directory(root, [0], width=1, height=1)
            self.assertEqual(report["count"], 1)

    def test_h264_420_pixel_format_contract(self):
        self.assertEqual(validate_h264_pixel_format("yuv420p"), "yuv420p")
        self.assertEqual(validate_h264_pixel_format("yuvj420p"), "yuvj420p")
        with self.assertRaises(VideoPipelineError):
            validate_h264_pixel_format("yuv422p")

    def test_push_render_request_defaults_to_hyperframes_auto_workers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "deck.json").write_text("{}", encoding="utf-8")
            request = resolve_push_request(root, ref_name="render/pohang-intro")
            self.assertEqual(request["output_name"], "pohang-intro")
            self.assertEqual(request["render_workers"], "auto")
            self.assertEqual(Path(request["spec_real"]), root / "deck.json")

    def test_push_render_request_accepts_workers_override(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "jobs").mkdir()
            (root / "jobs" / "deck.json").write_text("{}", encoding="utf-8")
            (root / "request.json").write_text(
                '{"spec_path":"jobs/deck.json","output_name":"pohang-60s","workers":"2"}',
                encoding="utf-8",
            )
            request = resolve_push_request(root, ref_name="render/ignored-default")
            self.assertEqual(request["output_name"], "pohang-60s")
            self.assertEqual(request["render_workers"], "2")
            self.assertEqual(Path(request["asset_root"]), root / "jobs")

    def test_push_render_request_rejects_legacy_remotion_concurrency(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "deck.json").write_text("{}", encoding="utf-8")
            (root / "request.json").write_text(
                '{"spec_path":"deck.json","concurrency":"50%"}',
                encoding="utf-8",
            )
            with self.assertRaises(RenderRequestError):
                resolve_push_request(root, ref_name="render/legacy")

    def test_push_render_request_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root.parent / "outside-render-request.json"
            outside.write_text("{}", encoding="utf-8")
            try:
                (root / "request.json").write_text(
                    '{"spec_path":"../outside-render-request.json"}',
                    encoding="utf-8",
                )
                with self.assertRaises(RenderRequestError):
                    resolve_push_request(root, ref_name="render/unsafe")
            finally:
                outside.unlink(missing_ok=True)

    def test_root_package_pins_hyperframes_and_not_remotion(self):
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(package["dependencies"]["hyperframes"], "0.8.73")
        all_dependencies = set(package.get("dependencies", {})) | set(package.get("devDependencies", {}))
        self.assertFalse(any("remotion" in name.lower() for name in all_dependencies))


if __name__ == "__main__":
    unittest.main()
