#!/usr/bin/env python3
"""Compile one deck spec into the canonical HTML plus HyperFrames timing attributes."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import Registry, build_deck
from core.registry import ContractError
from core.validation import load_spec
from tools.video_pipeline import (
    DEFAULT_BASE_SECONDS,
    DEFAULT_FPS,
    DEFAULT_LEAD_SECONDS,
    DEFAULT_STEP_SECONDS,
    DEFAULT_TRANSITION_SECONDS,
    VideoPipelineError,
    compile_video_timing,
    instrument_hyperframes_html,
    write_video_timing,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VIDEO_FONT = ROOT / "assets" / "fonts" / "PretendardVariable.woff2"


def build_hyperframes_composition(
    spec: dict[str, Any],
    registry: Registry | None = None,
    *,
    asset_root: str | Path = ".",
    font: str | Path | None = DEFAULT_VIDEO_FONT,
    fps: int = DEFAULT_FPS,
    base_seconds: float = DEFAULT_BASE_SECONDS,
    step_seconds: float = DEFAULT_STEP_SECONDS,
    lead_seconds: float = DEFAULT_LEAD_SECONDS,
    transition_seconds: float = DEFAULT_TRANSITION_SECONDS,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Build exactly one visual renderer: HTML. HyperFrames only receives timing metadata."""
    registry = registry or Registry()
    embedded_font = Path(font) if font is not None else None
    if embedded_font is not None and not embedded_font.is_file():
        raise VideoPipelineError(f"missing video font: {embedded_font}")

    html, plan = build_deck(
        spec,
        registry,
        asset_root=asset_root,
        font=embedded_font,
    )
    timing = compile_video_timing(
        spec,
        plan,
        fps=fps,
        base_seconds=base_seconds,
        step_seconds=step_seconds,
        lead_seconds=lead_seconds,
        transition_seconds=transition_seconds,
    )
    return instrument_hyperframes_html(html, timing), timing, plan


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", type=Path, required=True, help="HyperFrames index.html")
    parser.add_argument("--timing-out", type=Path)
    parser.add_argument("--asset-root", type=Path)
    parser.add_argument("--font", type=Path, default=DEFAULT_VIDEO_FONT)
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS)
    parser.add_argument("--base-seconds", type=float, default=DEFAULT_BASE_SECONDS)
    parser.add_argument("--step-seconds", type=float, default=DEFAULT_STEP_SECONDS)
    parser.add_argument("--lead-seconds", type=float, default=DEFAULT_LEAD_SECONDS)
    parser.add_argument("--transition-seconds", type=float, default=DEFAULT_TRANSITION_SECONDS)
    args = parser.parse_args(argv)

    try:
        if args.out.suffix.lower() != ".html":
            raise VideoPipelineError("--out must end in .html")
        spec = load_spec(args.spec)
        html, timing, _ = build_hyperframes_composition(
            spec,
            Registry(),
            asset_root=args.asset_root or args.spec.parent,
            font=args.font,
            fps=args.fps,
            base_seconds=args.base_seconds,
            step_seconds=args.step_seconds,
            lead_seconds=args.lead_seconds,
            transition_seconds=args.transition_seconds,
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(html, encoding="utf-8")
        if args.timing_out:
            write_video_timing(args.timing_out, timing)
        print(
            f"Built HyperFrames composition {args.out}: "
            f"{len(timing['scenes'])} scenes, "
            f"{timing['durationInFrames'] / timing['fps']:.2f}s @ {timing['fps']}fps"
        )
        return 0
    except (ContractError, OSError, VideoPipelineError, ValueError) as exc:
        print(f"VIDEO COMPOSE FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
