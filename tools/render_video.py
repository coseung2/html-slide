#!/usr/bin/env python3
"""Render one validated html-slide deck to MP4 using the local Remotion runtime."""
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
from tools.compose_video import (
    DEFAULT_BASE_SECONDS,
    DEFAULT_FPS,
    DEFAULT_LEAD_SECONDS,
    DEFAULT_STEP_SECONDS,
    DEFAULT_TRANSITION_SECONDS,
    compile_storyboard,
)
from tools.video_pipeline import (
    VideoPipelineError,
    npm_executable,
    remotion_executable,
    run_checked,
    sample_frames,
    validate_storyboard,
    write_storyboard,
)
from tools.verify_video import verify_video_artifacts

ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / "video"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--asset-root", type=Path)
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS)
    parser.add_argument("--base-seconds", type=float, default=DEFAULT_BASE_SECONDS)
    parser.add_argument("--step-seconds", type=float, default=DEFAULT_STEP_SECONDS)
    parser.add_argument("--lead-seconds", type=float, default=DEFAULT_LEAD_SECONDS)
    parser.add_argument("--transition-seconds", type=float, default=DEFAULT_TRANSITION_SECONDS)
    parser.add_argument("--concurrency", default="50%")
    parser.add_argument("--log", choices=["error", "warn", "info", "verbose"], default="info")
    parser.add_argument("--skip-typecheck", action="store_true")
    parser.add_argument("--skip-browser-ensure", action="store_true")
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
        if not VIDEO_DIR.joinpath("package.json").is_file():
            raise VideoPipelineError(f"missing Remotion runtime: {VIDEO_DIR}")

        work = (
            args.work_dir.resolve()
            if args.work_dir
            else out.parent / f"{out.stem}-video-work"
        )
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True)
        out.parent.mkdir(parents=True, exist_ok=True)

        deck = load_spec(spec_path)
        storyboard = compile_storyboard(
            deck,
            Registry(),
            asset_root=args.asset_root or spec_path.parent,
            fps=args.fps,
            base_seconds=args.base_seconds,
            step_seconds=args.step_seconds,
            lead_seconds=args.lead_seconds,
            transition_seconds=args.transition_seconds,
        )
        summary = validate_storyboard(storyboard)
        storyboard_path = work / "storyboard.json"
        write_storyboard(storyboard_path, storyboard)

        if not args.skip_typecheck:
            run_checked(
                [npm_executable(), "run", "typecheck"],
                cwd=VIDEO_DIR,
                label="Remotion typecheck",
            )

        remotion = str(remotion_executable(VIDEO_DIR))
        if not args.skip_browser_ensure:
            run_checked(
                [remotion, "browser", "ensure"],
                cwd=VIDEO_DIR,
                label="Remotion browser ensure",
            )

        run_checked(
            [
                remotion,
                "render",
                "src/index.ts",
                "DeckVideo",
                str(out),
                f"--props={storyboard_path}",
                "--codec=h264",
                "--pixel-format=yuv420p",
                f"--concurrency={args.concurrency}",
                f"--log={args.log}",
            ],
            cwd=VIDEO_DIR,
            label="Remotion render",
        )
        if not out.is_file() or out.stat().st_size == 0:
            raise VideoPipelineError(f"render completed without a non-empty MP4: {out}")

        frames_dir = None
        if not args.skip_frame_qa:
            frames = sample_frames(storyboard)
            frames_dir = work / "frames"
            frames_dir.mkdir(parents=True, exist_ok=True)
            run_checked(
                [
                    remotion,
                    "render",
                    "src/index.ts",
                    "DeckVideo",
                    str(frames_dir),
                    f"--props={storyboard_path}",
                    f"--frames={','.join(str(frame) for frame in frames)}",
                    "--sequence",
                    "--image-format=png",
                    "--image-sequence-pattern=frame-[frame].[ext]",
                    f"--concurrency={args.concurrency}",
                    f"--log={args.log}",
                ],
                cwd=VIDEO_DIR,
                label="Remotion sampled-frame render",
            )

        report = verify_video_artifacts(
            storyboard,
            video=out,
            frames_dir=frames_dir,
            video_dir=VIDEO_DIR,
        )
        report_path = out.with_suffix(".qa.json")
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        print(
            f"Rendered {out}: {summary['scenes']} scenes, "
            f"{summary['durationSeconds']:.2f}s @ {summary['fps']}fps"
        )
        print(f"Storyboard: {storyboard_path}")
        print(f"QA report: {report_path}")
        if not args.keep_work:
            shutil.rmtree(work, ignore_errors=True)
        return 0
    except (ContractError, OSError, VideoPipelineError, ValueError) as exc:
        print(f"VIDEO RENDER FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
