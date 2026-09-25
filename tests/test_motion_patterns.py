"""Renderer-independent motion pattern catalog and routing contracts."""
from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import Registry
from core.motion_patterns import (
    MotionPatternError,
    load_motion_patterns,
    motion_pattern_ids,
    rank_motion_patterns,
    validate_pattern_use,
)

ROOT = Path(__file__).resolve().parents[1]


class MotionPatternTests(unittest.TestCase):
    def setUp(self):
        self.registry = Registry(ROOT)

    def test_all_patterns_are_registered_for_html_and_hyperframes(self):
        patterns = load_motion_patterns()
        self.assertEqual(len(patterns), 27)
        self.assertEqual(set(patterns), motion_pattern_ids())
        for pattern in patterns.values():
            self.assertEqual(pattern["html"], "supported", pattern["id"])
            self.assertEqual(pattern["hyperframes"], "supported", pattern["id"])
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

    def test_hyperframes_ranking_is_deterministic(self):
        args = dict(
            intent="thesis",
            target="statement",
            semantic_module="focus",
            renderer="hyperframes",
            tones=["technical"],
            intensity="high",
            density="medium",
            topic="deterministic motion",
        )
        self.assertEqual(rank_motion_patterns(**args), rank_motion_patterns(**args))

    def test_immediate_repetition_is_penalized(self):
        base = dict(
            intent="thesis",
            target="statement",
            semantic_module="focus",
            renderer="hyperframes",
            tones=["technical"],
            intensity="high",
            density="medium",
            topic="headline",
        )
        first = rank_motion_patterns(**base)[0]["id"]
        second = rank_motion_patterns(**base, recent=[first])[0]["id"]
        self.assertNotEqual(first, second)

    def test_conflicting_patterns_are_rejected(self):
        with self.assertRaises(MotionPatternError):
            validate_pattern_use(
                "street-collage",
                target="statement",
                semantic_module="focus",
                renderer="hyperframes",
                selected=["particle-warp"],
            )

    def test_incompatible_target_is_rejected(self):
        with self.assertRaises(MotionPatternError):
            validate_pattern_use(
                "scramble-decode",
                target="image",
                semantic_module="focus",
                renderer="hyperframes",
            )


if __name__ == "__main__":
    unittest.main()
