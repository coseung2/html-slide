#!/usr/bin/env python3
"""Compile an html-slide deck spec into a deterministic Remotion storyboard."""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import Registry, plan_deck
from core.registry import ContractError
from core.renderers import media_data
from core.validation import load_spec
from tools.motion_patterns import MotionPatternError, select_motion_pattern, validate_pattern_use

DEFAULT_FPS = 30
DEFAULT_BASE_SECONDS = 4.0
DEFAULT_STEP_SECONDS = 1.2
DEFAULT_LEAD_SECONDS = 0.6
DEFAULT_TRANSITION_SECONDS = 0.35
CSS_VAR = re.compile(r"--([a-z0-9-]+)\s*:\s*([^;}]+)")


def _css_vars(css: str) -> dict[str, str]:
    return {name: value.strip() for name, value in CSS_VAR.findall(css)}


def _design_tokens(plan: dict, registry: Registry) -> dict:
    palette_id = plan["styles"]["palette"]["id"]
    dataviz_id = plan["styles"]["dataviz"]["id"]
    typography_id = plan["styles"]["typography"]["id"]
    palette = registry.get("palettes", palette_id)
    dataviz = registry.get("dataviz", dataviz_id)
    return {
        "paletteId": palette_id,
        "datavizId": dataviz_id,
        "typographyId": typography_id,
        "palette": _css_vars(registry.resource(palette, "style.css")),
        "dataviz": _css_vars(registry.resource(dataviz, "style.css")),
    }


def _video_blocks(blocks: list[dict], asset_root: Path) -> list[dict]:
    result = copy.deepcopy(blocks)
    for block in result:
        if block["module"] in ("image", "logo"):
            block["data"]["src"] = media_data(block["data"]["src"], asset_root)
    return result


def _default_motion_intensity(intent: str, density: str) -> str:
    if density == "high":
        return "low"
    if intent in {"thesis", "result", "identity", "conclusion"}:
        return "high"
    return "medium"


def compile_storyboard(
    spec: dict,
    registry: Registry,
    *,
    asset_root: str | Path | None = None,
    fps: int = DEFAULT_FPS,
    base_seconds: float = DEFAULT_BASE_SECONDS,
    step_seconds: float = DEFAULT_STEP_SECONDS,
    lead_seconds: float = DEFAULT_LEAD_SECONDS,
    transition_seconds: float = DEFAULT_TRANSITION_SECONDS,
) -> dict:
    if fps < 1 or fps > 120:
        raise ContractError("fps must be between 1 and 120")
    if base_seconds <= 0 or step_seconds < 0 or lead_seconds < 0 or transition_seconds < 0:
        raise ContractError(
            "video timing values must be non-negative and base_seconds must be positive"
        )

    plan = plan_deck(spec, registry)
    resolved_asset_root = Path(asset_root or registry.root).resolve()
    scenes = []
    cursor = 0
    signals = spec.get("style", {}).get("signals", {})
    deck_tones = signals.get("tone", [])
    deck_density = signals.get("density", "medium")
    recent_patterns: list[str] = []

    for index, (slide, planned) in enumerate(zip(spec["slides"], plan["slides"])):
        steps = int(planned.get("steps", 0))
        duration_frames = max(
            1,
            round((base_seconds + steps * step_seconds) * fps),
        )
        cue_gap = round(step_seconds * fps)
        cue_start = round(lead_seconds * fps)
        cues = []
        scene_patterns: list[str] = []
        density = slide.get("density", deck_density)
        topic = " ".join(
            value for value in (
                spec.get("topic", ""),
                slide["title"],
                slide["communication_goal"],
            ) if value
        )
        for motion in planned.get("motion", []):
            target_block = next(
                block for block in slide["blocks"] if block["id"] == motion["target"]
            )
            requested_pattern = motion.get("pattern")
            pattern = None
            pattern_source = None
            pattern_reasons: list[str] = []
            pattern_warnings: list[str] = []
            try:
                if requested_pattern == "auto":
                    choice = select_motion_pattern(
                        intent=slide["intent"],
                        target=target_block["module"],
                        semantic_module=motion["module"],
                        renderer="remotion",
                        tones=deck_tones,
                        intensity=motion.get("intensity")
                        or _default_motion_intensity(slide["intent"], density),
                        density=density,
                        topic=topic,
                        selected=scene_patterns,
                        recent=recent_patterns,
                    )
                    pattern = choice["id"]
                    pattern_source = "auto"
                    pattern_reasons = choice["reasons"]
                    pattern_warnings = choice["warnings"]
                elif requested_pattern:
                    validate_pattern_use(
                        requested_pattern,
                        target=target_block["module"],
                        semantic_module=motion["module"],
                        renderer="remotion",
                        selected=scene_patterns,
                    )
                    pattern = requested_pattern
                    pattern_source = "explicit"
            except MotionPatternError as exc:
                raise ContractError(
                    f"{slide['id']}.{motion['target']}: {exc}"
                ) from exc

            if pattern:
                scene_patterns.append(pattern)

            start_step = int(motion.get("startStep", 1))
            end_step = int(motion.get("endStep", start_step))
            for step in range(start_step, end_step + 1):
                at_frame = min(
                    duration_frames - 1,
                    cue_start + (step - 1) * cue_gap,
                )
                cues.append(
                    {
                        "module": motion["module"],
                        "target": motion["target"],
                        "reason": motion["reason"],
                        **({"pattern": pattern} if pattern else {}),
                        **({"patternSource": pattern_source} if pattern_source else {}),
                        **({"patternReasons": pattern_reasons} if pattern_reasons else {}),
                        **({"patternWarnings": pattern_warnings} if pattern_warnings else {}),
                        "step": step,
                        "atFrame": at_frame,
                        "durationFrames": max(
                            1,
                            min(round(0.8 * fps), duration_frames - at_frame),
                        ),
                    }
                )

        recent_patterns.extend(scene_patterns)
        recent_patterns = recent_patterns[-4:]

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
                "blocks": _video_blocks(slide["blocks"], resolved_asset_root),
                "slots": planned["slots"],
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
        "design": _design_tokens(plan, registry),
        "scenes": scenes,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--asset-root", type=Path)
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS)
    parser.add_argument("--base-seconds", type=float, default=DEFAULT_BASE_SECONDS)
    parser.add_argument("--step-seconds", type=float, default=DEFAULT_STEP_SECONDS)
    parser.add_argument("--lead-seconds", type=float, default=DEFAULT_LEAD_SECONDS)
    parser.add_argument("--transition-seconds", type=float, default=DEFAULT_TRANSITION_SECONDS)
    args = parser.parse_args(argv)

    try:
        spec = load_spec(args.spec)
        storyboard = compile_storyboard(
            spec,
            Registry(),
            asset_root=args.asset_root or args.spec.parent,
            fps=args.fps,
            base_seconds=args.base_seconds,
            step_seconds=args.step_seconds,
            lead_seconds=args.lead_seconds,
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
