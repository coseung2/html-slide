"""Contracts for HyperFrames composition compilation."""
from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import Registry
from tools.compose_hyperframes import compile_hyperframes

ROOT = Path(__file__).resolve().parents[1]


class HyperFramesCompositionTests(unittest.TestCase):
    def setUp(self):
        self.registry = Registry(ROOT)
        self.spec = {
            "schemaVersion": 1,
            "title": "HyperFrames test",
            "language": "ko",
            "theme": "tech",
            "slides": [
                {
                    "id": "one",
                    "title": "첫 장",
                    "communication_goal": "첫 메시지를 설명한다",
                    "intent": "thesis",
                    "blocks": [
                        {
                            "id": "message",
                            "module": "statement",
                            "data": {"text": "첫 메시지"},
                        }
                    ],
                    "motion": [
                        {
                            "module": "focus",
                            "target": "message",
                            "reason": "첫 메시지를 강조한다",
                            "pattern": "kinetic-type",
                        }
                    ],
                },
                {
                    "id": "two",
                    "title": "둘째 장",
                    "communication_goal": "둘째 메시지를 설명한다",
                    "intent": "conclusion",
                    "blocks": [
                        {
                            "id": "message-two",
                            "module": "statement",
                            "data": {"text": "둘째 메시지"},
                        }
                    ],
                },
            ],
        }

    def test_composition_root_has_hyperframes_contract(self):
        html, manifest = compile_hyperframes(self.spec, self.registry)
        self.assertIn('data-composition-id="html-slide"', html)
        self.assertIn('data-start="0"', html)
        self.assertIn('data-width="1920"', html)
        self.assertIn('data-height="1080"', html)
        self.assertNotIn('data-no-timeline', html)
        self.assertIn('<script src="./gsap.min.js"></script>', html)
        self.assertIn("window.__timelines['html-slide'] = tl", html)
        self.assertEqual(manifest["renderer"], "hyperframes")
        self.assertEqual(manifest["fps"], 30)

    def test_slides_are_timed_clips(self):
        html, manifest = compile_hyperframes(
            self.spec,
            self.registry,
            base_seconds=4.0,
            step_seconds=1.2,
        )
        self.assertIn('data-slide="one"', html)
        self.assertIn('data-track-index="0"', html)
        self.assertEqual(manifest["scenes"][0]["start"], 0.0)
        self.assertAlmostEqual(manifest["scenes"][0]["duration"], 5.2)
        self.assertAlmostEqual(manifest["scenes"][1]["start"], 5.2)
        self.assertAlmostEqual(manifest["durationSeconds"], 9.2)

    def test_semantic_motion_becomes_seekable_cue(self):
        html, manifest = compile_hyperframes(
            self.spec,
            self.registry,
            lead_seconds=0.6,
            cue_seconds=0.8,
        )
        cue = manifest["scenes"][0]["cues"][0]
        self.assertEqual(cue["module"], "focus")
        self.assertEqual(cue["target"], "message")
        self.assertEqual(cue["pattern"], "kinetic-type")
        self.assertAlmostEqual(cue["at"], 0.6)
        self.assertAlmostEqual(cue["duration"], 0.8)
        self.assertIn('id="hf-plan"', html)

    def test_presenter_runtime_and_browser_clock_transitions_are_removed(self):
        html, _ = compile_hyperframes(self.spec, self.registry)
        self.assertNotIn("/* One state owner.", html)
        self.assertNotIn("performance.now()", html)
        self.assertNotIn("requestAnimationFrame", html)
        self.assertNotRegex(html, r"(?i)transition(?:-[a-z-]+)?\\s*:")
        self.assertIn('data-hf-video="1"', html)
        self.assertIn('id="hf-slide-one"', html)


if __name__ == "__main__":
    unittest.main()
