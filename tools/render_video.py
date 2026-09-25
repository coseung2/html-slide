#!/usr/bin/env python3
"""Render one validated html-slide deck to MP4 using HyperFrames."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import Registry
from core.registry import ContractError
from core.validation import load_spec
from tools.compose_hyperframes import (
    DEFAULT_BASE_SECONDS,
    DEFAULT_CUE_SECONDS,
    DEFAULT_FPS,
    DEFAULT_LEAD_SECONDS,
    DEFAULT_STEP_SECONDS,
)
from tools.hyperframes_project import compile_hyperframes_project
from tools.hyperframes_pipeline import (
    HyperFramesPipelineError,
    gsap_browser_file,
    hyperframes_executable,
    run_checked,
    sample_times,
    validate_manifest,
)
from tools.verify_hyperframes import verify_video_artifacts

ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / "video"
DEFAULT_FONT = ROOT / "assets" / "fonts" / "PretendardVariable.woff2"


def _workers(explicit: int | None, legacy: str | None) -> int:
    if explicit is not None:
        return max(1, min(24, explicit))
    if legacy:
        value = legacy.strip()
        if value.endswith("%"):
            try:
                fraction = float(value[:-1]) / 100
            except ValueError as exc:
                raise HyperFramesPipelineError(f"invalid --concurrency value: {legacy}") from exc
            return max(1, min(24, round((os.cpu_count() or 2) * fraction)))
        try:
            return max(1, min(24, int(value)))
        except ValueError as exc:
            raise HyperFramesPipelineError(f"invalid --concurrency value: {legacy}") from exc
    return max(1, min(24, (os.cpu_count() or 2) // 2 or 1))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--asset-root", type=Path)
    parser.add_argument("--font", type=Path)
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS)
    parser.add_argument("--base-seconds", type=float, default=DEFAULT_BASE_SECONDS)
    parser.add_argument("--step-seconds", type=float, default=DEFAULT_STEP_SECONDS)
    parser.add_argument("--lead-seconds", type=float, default=DEFAULT_LEAD_SECONDS)
    parser.add_argument("--cue-seconds", type=float, default=DEFAULT_CUE_SECONDS)
    parser.add_argument("--workers", type=int)
    parser.add_argument(
        "--concurrency",
        help="Deprecated compatibility alias; percentages are mapped to HyperFrames workers.",
    )
    parser.add_argument(
        "--quality",
        choices=["draft", "looks", "delivery", "standard", "high"],
        default="high",
    )
    parser.add_argument("--skip-frame-qa", action="store_true")
    parser.add_argument("--keep-work", action="store_true")
    args = parser.parse_args(argv)

    try:
        spec_path = args.spec.resolve()
        if not spec_path.is_file():
            raise HyperFramesPipelineError(f"missing deck spec: {spec_path}")
        out = args.out.resolve()
        if out.suffix.lower() != ".mp4":
            raise HyperFramesPipelineError("--out must end in .mp4")
        if not VIDEO_DIR.joinpath("package.json").is_file():
            raise HyperFramesPipelineError(f"missing video runtime package: {VIDEO_DIR}")

        workers = _workers(args.workers, args.concurrency)
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
        font = args.font.resolve() if args.font else DEFAULT_FONT
        if not font.is_file():
            raise HyperFramesPipelineError(f"missing video font: {font}")

        composition, fragments, manifest = compile_hyperframes_project(
            deck,
            Registry(),
            asset_root=args.asset_root or spec_path.parent,
            font=font,
            fps=args.fps,
            base_seconds=args.base_seconds,
            step_seconds=args.step_seconds,
            lead_seconds=args.lead_seconds,
            cue_seconds=args.cue_seconds,
        )
        summary = validate_manifest(manifest)
        composition_path = work / "index.html"
        manifest_path = work / "video.manifest.json"
        composition_path.write_text(composition, encoding="utf-8")
        for relative, fragment in fragments.items():
            target = work / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(fragment, encoding="utf-8")
        font_asset = work / manifest["fontAsset"]
        font_asset.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(font, font_asset)
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        shutil.copy2(gsap_browser_file(VIDEO_DIR), work / "gsap.min.js")

        hyperframes = str(hyperframes_executable(VIDEO_DIR))
        times = sample_times(manifest)
        at = ",".join(f"{value:.6f}" for value in times)

        check = run_checked(
            [
                hyperframes,
                "check",
                str(work),
                "--json",
                "--samples",
                "9",
                "--timeout",
                "5000",
            ],
            cwd=ROOT,
            label="HyperFrames check",
            capture_output=True,
        )
        check_path = work / "hyperframes-check.json"
        check_path.write_text(check.stdout or "{}\n", encoding="utf-8")

        frames_dir = None
        if not args.skip_frame_qa:
            frames_dir = work / "frames"
            run_checked(
                [
                    hyperframes,
                    "snapshot",
                    str(work),
                    "--at",
                    at,
                    "--output",
                    str(frames_dir),
                    "--no-end",
                    "--describe",
                    "false",
                ],
                cwd=ROOT,
                label="HyperFrames sampled-frame snapshot",
            )

        run_checked(
            [
                hyperframes,
                "render",
                str(work),
                "--output",
                str(out),
                "--format",
                "mp4",
                "--fps",
                str(args.fps),
                "--quality",
                args.quality,
                "--workers",
                str(workers),
            ],
            cwd=ROOT,
            label="HyperFrames render",
        )
        if not out.is_file() or out.stat().st_size == 0:
            raise HyperFramesPipelineError(
                f"render completed without a non-empty MP4: {out}"
            )

        report = verify_video_artifacts(
            manifest,
            video=out,
            frames_dir=frames_dir,
        )
        report["hyperframes"] = {
            "workers": workers,
            "quality": args.quality,
            "check": str(check_path),
        }
        report_path = out.with_suffix(".qa.json")
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        print(
            f"Rendered {out}: {summary['scenes']} scenes, "
            f"{summary['durationSeconds']:.2f}s @ {summary['fps']}fps"
        )
        print(f"Composition: {composition_path}")
        print(f"Manifest: {manifest_path}")
        print(f"QA report: {report_path}")
        if not args.keep_work:
            shutil.rmtree(work, ignore_errors=True)
        return 0
    except (
        ContractError,
        OSError,
        HyperFramesPipelineError,
        ValueError,
    ) as exc:
        print(f"VIDEO RENDER FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
