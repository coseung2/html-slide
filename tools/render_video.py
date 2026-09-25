#!/usr/bin/env python3
"""Render one validated html-slide deck to MP4 through HyperFrames."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import Registry
from core.registry import ContractError
from core.validation import load_spec
from tools.compose_video import DEFAULT_VIDEO_FONT, build_hyperframes_composition
from tools.video_pipeline import (
    DEFAULT_BASE_SECONDS,
    DEFAULT_FPS,
    DEFAULT_LEAD_SECONDS,
    DEFAULT_STEP_SECONDS,
    DEFAULT_TRANSITION_SECONDS,
    ROOT,
    VideoPipelineError,
    hyperframes_executable,
    run_checked,
    sample_frames,
    validate_video_timing,
    write_video_timing,
)
from tools.verify_video import verify_video_artifacts


def _frame_times(timing: dict) -> str:
    fps = timing["fps"]
    return ",".join(f"{frame / fps:.6f}" for frame in sample_frames(timing))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--asset-root", type=Path)
    parser.add_argument("--font", type=Path, default=DEFAULT_VIDEO_FONT)
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS)
    parser.add_argument("--base-seconds", type=float, default=DEFAULT_BASE_SECONDS)
    parser.add_argument("--step-seconds", type=float, default=DEFAULT_STEP_SECONDS)
    parser.add_argument("--lead-seconds", type=float, default=DEFAULT_LEAD_SECONDS)
    parser.add_argument("--transition-seconds", type=float, default=DEFAULT_TRANSITION_SECONDS)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--quality", choices=["draft", "looks", "standard", "delivery", "high"], default="delivery")
    parser.add_argument("--skip-lint", action="store_true")
    parser.add_argument("--skip-frame-qa", action="store_true")
    parser.add_argument("--keep-work", action="store_true")
    args = parser.parse_args(argv)

    try:
        spec_path = args.spec.resolve()
        if not spec_path.is_file():
            raise VideoPipelineError(f"missing deck spec: {spec_path}")
        out = args.out.resolve()
        if out.suffix.lower() != ".mp4":
            raise VideoPipelineError("--out must end in .mp4")
        if args.workers is not None and not 1 <= args.workers <= 24:
            raise VideoPipelineError("--workers must be between 1 and 24")

        work = args.work_dir.resolve() if args.work_dir else out.parent / f"{out.stem}-video-work"
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True)
        out.parent.mkdir(parents=True, exist_ok=True)

        deck = load_spec(spec_path)
        html, timing, _ = build_hyperframes_composition(
            deck,
            Registry(),
            asset_root=args.asset_root or spec_path.parent,
            font=args.font,
            fps=args.fps,
            base_seconds=args.base_seconds,
            step_seconds=args.step_seconds,
            lead_seconds=args.lead_seconds,
            transition_seconds=args.transition_seconds,
        )
        summary = validate_video_timing(timing)
        composition = work / "index.html"
        composition.write_text(html, encoding="utf-8")
        timing_path = work / "timing.json"
        write_video_timing(timing_path, timing)

        hyperframes = str(hyperframes_executable(ROOT))
        version = run_checked(
            [hyperframes, "--version"],
            cwd=work,
            label="HyperFrames version",
            capture_output=True,
        ).stdout.strip()

        if not args.skip_lint:
            run_checked(
                [hyperframes, "lint", ".", "--strict"],
                cwd=work,
                label="HyperFrames lint",
            )

        command = [
            hyperframes,
            "render",
            "--composition",
            "index.html",
            "--output",
            str(out),
            "--format",
            "mp4",
            "--codec",
            "h264",
            "--fps",
            str(args.fps),
            "--quality",
            args.quality,
            "--strict",
        ]
        if args.workers is not None:
            command += ["--workers", str(args.workers)]
        run_checked(command, cwd=work, label="HyperFrames render")
        if not out.is_file() or out.stat().st_size == 0:
            raise VideoPipelineError(f"render completed without a non-empty MP4: {out}")

        frames_dir = None
        if not args.skip_frame_qa:
            frames_dir = work / "frames"
            run_checked(
                [
                    hyperframes,
                    "snapshot",
                    ".",
                    "--at",
                    _frame_times(timing),
                    "--output",
                    str(frames_dir),
                    "--no-end",
                    "--describe",
                    "false",
                ],
                cwd=work,
                label="HyperFrames sampled-frame capture",
            )

        report = verify_video_artifacts(
            timing,
            video=out,
            frames_dir=frames_dir,
        )
        report["renderer"] = {
            "name": "HyperFrames",
            "version": version,
            "composition": "canonical html-slide HTML",
        }
        report_path = out.with_suffix(".qa.json")
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        print(
            f"Rendered {out}: {summary['scenes']} scenes, "
            f"{summary['durationSeconds']:.2f}s @ {summary['fps']}fps with HyperFrames {version}"
        )
        print(f"Composition: {composition}")
        print(f"Timing: {timing_path}")
        print(f"QA report: {report_path}")
        if not args.keep_work:
            shutil.rmtree(work, ignore_errors=True)
        return 0
    except (ContractError, OSError, VideoPipelineError, ValueError) as exc:
        print(f"VIDEO RENDER FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
