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
from tools.compose_video import compile_storyboard
from tools.video_pipeline import VideoPipelineError, sample_frames, validate_storyboard
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


if __name__ == "__main__":
    unittest.main()
