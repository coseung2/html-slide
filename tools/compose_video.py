#!/usr/bin/env python3
"""Compile an html-slide deck spec into a deterministic Remotion storyboard."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import Registry, plan_deck
from core.registry import ContractError
from core.validation import load_spec

DEFAULT_FPS = 30
DEFAULT_BASE_SECONDS = 4.0
DEFAULT_STEP_SECONDS = 1.2
DEFAULT_TRANSITION_SECONDS = 0.35


def compile_storyboard(
    spec: dict,
    registry: Registry,
    *,
    fps: int = DEFAULT_FPS,
    base_seconds: float = DEFAULT_BASE_SECONDS,
    step_seconds: float = DEFAULT_STEP_SECONDS,
    transition_seconds: float = DEFAULT_TRANSITION_SECONDS,
) -> dict:
    if fps < 1 or fps > 120:
        raise ContractError("fps must be between 1 and 120")
    if base_seconds <= 0 or step_seconds < 0 or transition_seconds < 0:
        raise ContractError("video timing values must be non-negative and base_seconds must be positive")

    plan = plan_deck(spec, registry)
    scenes = []
    cursor = 0

    for index, (slide, planned) in enumerate(zip(spec["slides"], plan["slides"])):
        steps = int(planned.get("steps", 0))
        duration_frames = max(
            1,
            round((base_seconds + steps * step_seconds) * fps),
        )
        cue_gap = round(step_seconds * fps)
        cue_start = round(base_seconds * fps)
        cues = []
        for cue_index, motion in enumerate(slide.get("motion", [])):
            cues.append(
                {
                    "module": motion["module"],
                    "target": motion["target"],
                    "reason": motion["reason"],
                    "atFrame": min(duration_frames - 1, cue_start + cue_index * cue_gap),
                    "durationFrames": max(1, min(round(0.8 * fps), duration_frames)),
                }
            )

        scenes.append(
            {
                "id": slide["id"],
                "index": index,
                "title": slide["title"],
                "summary": slide.get("summary", ""),
                "communicationGoal": slide["communication_goal"],
                "intent": slide["intent"],
                "layout": planned["layout"],
                "theme": slide.get("theme", spec["theme"]),
                "style": plan.get("styles", {}),
                "blocks": slide["blocks"],
                "cues": cues,
                "startFrame": cursor,
                "durationFrames": duration_frames,
                "transitionFrames": 0 if index == 0 else round(transition_seconds * fps),
            }
        )
        cursor += duration_frames

    return {
        "schemaVersion": 1,
        "source": "html-slide",
        "title": spec["title"],
        "language": spec.get("language", "ko"),
        "fps": fps,
        "width": 1920,
        "height": 1080,
        "durationInFrames": cursor,
        "scenes": scenes,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS)
    parser.add_argument("--base-seconds", type=float, default=DEFAULT_BASE_SECONDS)
    parser.add_argument("--step-seconds", type=float, default=DEFAULT_STEP_SECONDS)
    parser.add_argument("--transition-seconds", type=float, default=DEFAULT_TRANSITION_SECONDS)
    args = parser.parse_args(argv)

    try:
        spec = load_spec(args.spec)
        storyboard = compile_storyboard(
            spec,
            Registry(),
            fps=args.fps,
            base_seconds=args.base_seconds,
            step_seconds=args.step_seconds,
            transition_seconds=args.transition_seconds,
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(storyboard, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            f"Built {args.out}: {len(storyboard['scenes'])} scenes, "
            f"{storyboard['durationInFrames']} frames @ {storyboard['fps']}fps"
        )
        return 0
    except (ContractError, OSError, ValueError) as exc:
        print(f"VIDEO COMPOSE FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
