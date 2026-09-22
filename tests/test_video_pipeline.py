"""Contracts for the deck-to-Remotion storyboard compiler."""
from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import Registry
from core.registry import ContractError
from tools.compose_video import compile_storyboard

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

    def test_invalid_fps_rejected(self):
        with self.assertRaises(ContractError):
            compile_storyboard(self.spec, self.registry, fps=0)


if __name__ == "__main__":
    unittest.main()
