"""Contracts for the deck-to-Remotion storyboard compiler."""
from __future__ import annotations

import base64
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import Registry
from core.registry import ContractError
from core.validation import validate_deck
from tools.compose_video import compile_storyboard
from tools.motion_patterns import load_motion_patterns, rank_motion_patterns
from tools.render_request import RenderRequestError, resolve_push_request
from tools.video_pipeline import (
    VideoPipelineError,
    motion_pattern_ids,
    sample_frames,
    validate_storyboard,
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

    def test_storyboard_is_deterministic(self):
        a = compile_storyboard(self.spec, self.registry)
        b = compile_storyboard(self.spec, self.registry)
        self.assertEqual(a, b)

    def test_scene_preserves_semantics(self):
        board = compile_storyboard(self.spec, self.registry)
        scene = board["scenes"][0]
        self.assertEqual(scene["communicationGoal"], "한 가지 메시지를 강조한다")
        self.assertEqual(scene["blocks"][0]["id"], "message")
        self.assertEqual(scene["cues"][0]["target"], "message")
        self.assertGreater(scene["durationFrames"], scene["cues"][0]["atFrame"])

    def test_all_reel_motion_patterns_are_registered(self):
        patterns = load_motion_patterns()
        self.assertEqual(len(patterns), 19)
        self.assertEqual(set(patterns), motion_pattern_ids())
        self.assertIn("kinetic-type", patterns)
        self.assertIn("particle-warp", patterns)
        self.assertIn("path-drawing", patterns)
        for pattern in patterns.values():
            self.assertTrue(pattern["targets"])
            self.assertTrue(pattern["semanticModules"])
            self.assertTrue(pattern["intents"])
            self.assertTrue(pattern["tones"])
            self.assertIn(pattern["intensity"], {"low", "medium", "high"})
            self.assertIn(pattern["complexity"], {"light", "medium", "heavy"})
            valid_pairs = []
            for semantic in pattern["semanticModules"]:
                motion = self.registry.get("motion", semantic)
                for target in pattern["targets"]:
                    if target in motion.get("supports", []):
                        valid_pairs.append((semantic, target))
            self.assertTrue(valid_pairs, pattern["id"])

    def test_selected_pattern_is_preserved_in_storyboard(self):
        self.spec["slides"][0]["motion"][0]["pattern"] = "glitch"
        validate_deck(self.spec, self.registry)
        board = compile_storyboard(self.spec, self.registry)
        cue = board["scenes"][0]["cues"][0]
        self.assertEqual(cue["pattern"], "glitch")
        self.assertEqual(cue["patternSource"], "explicit")

    def test_auto_pattern_uses_ranked_metadata_and_records_reasons(self):
        self.spec["style"] = {
            "signals": {
                "tone": ["technical"],
                "density": "medium",
            }
        }
        self.spec["slides"][0]["motion"][0].update(pattern="auto", intensity="high")
        expected = rank_motion_patterns(
            intent="thesis",
            target="statement",
            semantic_module="focus",
            renderer="remotion",
            tones=["technical"],
            intensity="high",
            density="medium",
            topic="하나의 핵심 한 가지 메시지를 강조한다",
        )[0]["id"]
        board = compile_storyboard(self.spec, self.registry)
        cue = board["scenes"][0]["cues"][0]
        self.assertEqual(cue["pattern"], expected)
        self.assertEqual(cue["patternSource"], "auto")
        self.assertTrue(cue["patternReasons"])

    def test_auto_pattern_penalizes_immediate_repetition(self):
        self.spec["style"] = {"signals": {"tone": ["technical"], "density": "medium"}}
        self.spec["slides"][0]["motion"][0].update(pattern="auto", intensity="high")
        second = {
            **self.spec["slides"][0],
            "id": "two",
            "title": "둘째 핵심",
            "blocks": [{
                "id": "message-two",
                "module": "statement",
                "data": {"text": "둘째 메시지"},
            }],
            "motion": [{
                "module": "focus",
                "target": "message-two",
                "reason": "둘째 핵심을 주목시킨다",
                "pattern": "auto",
                "intensity": "high",
            }],
        }
        self.spec["slides"] = [self.spec["slides"][0], second]
        board = compile_storyboard(self.spec, self.registry)
        first = board["scenes"][0]["cues"][0]["pattern"]
        next_pattern = board["scenes"][1]["cues"][0]["pattern"]
        self.assertNotEqual(first, next_pattern)

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
            compile_storyboard(self.spec, self.registry)

    def test_two_high_intensity_patterns_are_rejected_on_same_scene(self):
        self.spec["slides"][0].update(
            intent="overview",
            layout="split-left",
            blocks=[
                {"id": "a", "module": "statement", "data": {"text": "A"}},
                {"id": "b", "module": "statement", "data": {"text": "B"}},
            ],
            motion=[
                {
                    "module": "focus",
                    "target": "a",
                    "reason": "첫 메시지를 강조한다",
                    "pattern": "kinetic-type",
                },
                {
                    "module": "focus",
                    "target": "b",
                    "reason": "둘째 메시지를 강조한다",
                    "pattern": "scramble-decode",
                },
            ],
        )
        with self.assertRaises(ContractError):
            compile_storyboard(self.spec, self.registry)

    def test_conflicting_patterns_are_rejected_on_same_scene(self):
        self.spec["slides"][0].update(
            intent="overview",
            layout="split-left",
            blocks=[
                {"id": "a", "module": "statement", "data": {"text": "A"}},
                {"id": "b", "module": "statement", "data": {"text": "B"}},
            ],
            motion=[
                {
                    "module": "focus",
                    "target": "a",
                    "reason": "첫 메시지를 강조한다",
                    "pattern": "particle-warp",
                },
                {
                    "module": "focus",
                    "target": "b",
                    "reason": "둘째 메시지를 강조한다",
                    "pattern": "street-collage",
                },
            ],
        )
        with self.assertRaises(ContractError):
            compile_storyboard(self.spec, self.registry)

    def test_unknown_pattern_is_rejected_by_deck_schema(self):
        self.spec["slides"][0]["motion"][0]["pattern"] = "made-up-effect"
        with self.assertRaises(ContractError):
            validate_deck(self.spec, self.registry)

    def test_duration_matches_scene_sum(self):
        self.spec["slides"] *= 2
        self.spec["slides"][1] = {**self.spec["slides"][1], "id": "two", "title": "둘"}
        board = compile_storyboard(self.spec, self.registry)
        self.assertEqual(
            board["durationInFrames"],
            sum(scene["durationFrames"] for scene in board["scenes"])
        )

    def test_layout_slots_and_design_tokens_are_preserved(self):
        board = compile_storyboard(self.spec, self.registry)
        scene = board["scenes"][0]
        self.assertEqual(scene["slots"]["main"], ["message"])
        self.assertIn("paper", board["design"]["palette"])
        self.assertIn("ink", board["design"]["palette"])
        self.assertIn("viz-1", board["design"]["dataviz"])

    def test_image_blocks_are_self_contained(self):
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
        board = compile_storyboard(self.spec, self.registry)
        src = board["scenes"][0]["blocks"][0]["data"]["src"]
        self.assertTrue(src.startswith("data:image/png;base64,"))

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
        board = compile_storyboard(self.spec, self.registry)
        cues = board["scenes"][0]["cues"]
        self.assertEqual([cue["step"] for cue in cues], [1, 2, 3])
        self.assertEqual([cue["atFrame"] for cue in cues], [18, 54, 90])
        self.assertEqual(len({cue["atFrame"] for cue in cues}), 3)

    def test_storyboard_contract_and_sample_frames(self):
        board = compile_storyboard(self.spec, self.registry)
        summary = validate_storyboard(board)
        self.assertEqual(summary["scenes"], 1)
        frames = sample_frames(board)
        self.assertEqual(frames[0], 0)
        self.assertEqual(frames[-1], board["durationInFrames"] - 1)
        self.assertIn(board["scenes"][0]["cues"][0]["atFrame"], frames)

    def test_storyboard_rejects_cue_overflow(self):
        board = compile_storyboard(self.spec, self.registry)
        board["scenes"][0]["cues"][0]["durationFrames"] = board["scenes"][0]["durationFrames"]
        with self.assertRaises(VideoPipelineError):
            validate_storyboard(board)

    def test_storyboard_rejects_unknown_pattern(self):
        board = compile_storyboard(self.spec, self.registry)
        board["scenes"][0]["cues"][0]["pattern"] = "made-up-effect"
        with self.assertRaises(VideoPipelineError):
            validate_storyboard(board)

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

    def test_invalid_fps_rejected(self):
        with self.assertRaises(ContractError):
            compile_storyboard(self.spec, self.registry, fps=0)

    def test_push_render_request_defaults_from_branch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "deck.json").write_text("{}", encoding="utf-8")
            request = resolve_push_request(root, ref_name="render/pohang-intro")
            self.assertEqual(request["output_name"], "pohang-intro")
            self.assertEqual(request["render_concurrency"], "50%")
            self.assertEqual(Path(request["spec_real"]), root / "deck.json")

    def test_push_render_request_accepts_safe_overrides(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "jobs").mkdir()
            (root / "jobs" / "deck.json").write_text("{}", encoding="utf-8")
            (root / "request.json").write_text(
                '{"spec_path":"jobs/deck.json","output_name":"pohang-60s","concurrency":"2"}',
                encoding="utf-8",
            )
            request = resolve_push_request(root, ref_name="render/ignored-default")
            self.assertEqual(request["output_name"], "pohang-60s")
            self.assertEqual(request["render_concurrency"], "2")
            self.assertEqual(Path(request["asset_root"]), root / "jobs")

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

    def test_push_render_request_rejects_unknown_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "deck.json").write_text("{}", encoding="utf-8")
            (root / "request.json").write_text(
                '{"spec_path":"deck.json","shell":"do-not-run"}',
                encoding="utf-8",
            )
            with self.assertRaises(RenderRequestError):
                resolve_push_request(root, ref_name="render/unsafe")


if __name__ == "__main__":
    unittest.main()
