"""Contracts for HyperFrames composition compilation."""
from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import Registry
from tools.compose_hyperframes import compile_hyperframes
from tools.hyperframes_pipeline import (
    HyperFramesPipelineError,
    sample_times,
    validate_manifest,
)
from tools.hyperframes_project import compile_hyperframes_project
from tools.render_video import _workers
from tools.verify_hyperframes import validate_h264_pixel_format

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
        self.assertIn("window.__timelines[stage.dataset.compositionId] = tl", html)
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

    def test_manifest_contract_and_sample_times(self):
        _, manifest = compile_hyperframes(self.spec, self.registry)
        summary = validate_manifest(manifest)
        self.assertEqual(summary["scenes"], 2)
        self.assertEqual(summary["cues"], 1)
        times = sample_times(manifest)
        self.assertEqual(times[0], 0.0)
        self.assertLess(times[-1], manifest["durationSeconds"])
        self.assertIn(0.6, times)
        self.assertIn(2.6, times)
        self.assertIn(7.2, times)

    def test_manifest_rejects_cue_overflow(self):
        _, manifest = compile_hyperframes(self.spec, self.registry)
        manifest["scenes"][0]["cues"][0]["duration"] = 99
        with self.assertRaises(HyperFramesPipelineError):
            validate_manifest(manifest)

    def test_worker_compatibility_mapping(self):
        self.assertEqual(_workers(3, None), 3)
        self.assertEqual(_workers(99, None), 24)
        self.assertGreaterEqual(_workers(None, "50%"), 1)
        self.assertEqual(_workers(None, "2"), 2)
        with self.assertRaises(HyperFramesPipelineError):
            _workers(None, "bad")

    def test_h264_420_pixel_format_contract(self):
        self.assertEqual(validate_h264_pixel_format("yuv420p"), "yuv420p")
        self.assertEqual(validate_h264_pixel_format("yuvj420p"), "yuvj420p")
        with self.assertRaises(HyperFramesPipelineError):
            validate_h264_pixel_format("yuv422p")

    def test_project_splits_slides_into_isolated_subcompositions(self):
        index_html, fragments, manifest = compile_hyperframes_project(
            self.spec,
            self.registry,
        )
        self.assertIn("data-no-timeline", index_html)
        self.assertIn('data-composition-src="./compositions/one.html"', index_html)
        self.assertEqual(
            set(fragments),
            {"compositions/one.html", "compositions/two.html"},
        )
        self.assertIn('data-composition-id="html-slide-one"', fragments["compositions/one.html"])
        self.assertIn('data-slide="one"', fragments["compositions/one.html"])
        self.assertNotIn('data-slide="two"', fragments["compositions/one.html"])
        self.assertEqual(
            manifest["compositionFiles"],
            ["compositions/one.html", "compositions/two.html"],
        )

    def test_presenter_runtime_and_browser_clock_transitions_are_removed(self):
        html, _ = compile_hyperframes(self.spec, self.registry)
        self.assertNotIn("/* One state owner.", html)
        self.assertNotIn("performance.now()", html)
        self.assertNotIn("requestAnimationFrame", html)
        self.assertNotRegex(html, r"(?i)transition(?:-[a-z-]+)?\s*:")
        self.assertNotIn("Pretendard Variable", html)
        self.assertNotRegex(html, r"(?i)(?<![A-Za-z0-9_-])Pretendard(?![A-Za-z0-9_-])")
        self.assertNotIn("Noto Sans CJK KR", html)
        self.assertIn('data-hf-video="1"', html)
        self.assertIn('.clip[style*="visibility: hidden"] *{visibility:hidden!important}', html)
        self.assertIn('id="hf-slide-one"', html)


if __name__ == "__main__":
    unittest.main()
