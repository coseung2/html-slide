"""Security and compatibility contracts for transient video render requests."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.render_request import RenderRequestError, resolve_push_request


class RenderRequestTests(unittest.TestCase):
    def test_push_render_request_defaults_from_branch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "deck.json").write_text("{}", encoding="utf-8")
            request = resolve_push_request(root, ref_name="render/pohang-intro")
            self.assertEqual(request["output_name"], "pohang-intro")
            self.assertEqual(request["render_concurrency"], "50%")
            self.assertGreaterEqual(int(request["render_workers"]), 1)
            self.assertLessEqual(int(request["render_workers"]), 24)
            self.assertEqual(Path(request["spec_real"]), root / "deck.json")

    def test_push_render_request_accepts_safe_overrides(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "jobs").mkdir()
            (root / "jobs" / "deck.json").write_text("{}", encoding="utf-8")
            (root / "request.json").write_text(
                '{"spec_path":"jobs/deck.json","output_name":"pohang-60s","concurrency":"2","workers":"3"}',
                encoding="utf-8",
            )
            request = resolve_push_request(root, ref_name="render/ignored-default")
            self.assertEqual(request["output_name"], "pohang-60s")
            self.assertEqual(request["render_concurrency"], "2")
            self.assertEqual(request["render_workers"], "3")
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

    def test_push_render_request_rejects_invalid_workers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "deck.json").write_text("{}", encoding="utf-8")
            (root / "request.json").write_text(
                '{"spec_path":"deck.json","workers":"25"}',
                encoding="utf-8",
            )
            with self.assertRaises(RenderRequestError):
                resolve_push_request(root, ref_name="render/unsafe")


if __name__ == "__main__":
    unittest.main()
