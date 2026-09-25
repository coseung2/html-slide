#!/usr/bin/env python3
"""Compile a validated html-slide deck into a HyperFrames-compatible HTML composition."""
from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import Registry, build_deck
from core.composer import json_script
from core.registry import ContractError
from core.validation import load_spec

DEFAULT_FPS = 30
DEFAULT_BASE_SECONDS = 4.0
DEFAULT_STEP_SECONDS = 1.2
DEFAULT_LEAD_SECONDS = 0.6
DEFAULT_CUE_SECONDS = 0.8

_STAGE_RE = re.compile(r"<main data-stage\b")
_SLIDE_RE = re.compile(r'<section data-slide="([^"]+)"([^>]*)>')
_STYLE_RE = re.compile(r"<style(?P<attrs>[^>]*)>(?P<body>[\s\S]*?)</style>", re.IGNORECASE)
_TRANSITION_RE = re.compile(
    r"(?<![-\w])transition(?:-[a-z-]+)?\s*:[^;}]+;?",
    re.IGNORECASE,
)


def _sanitize_video_styles(source: str) -> str:
    """Remove browser-clock transitions and collapse browser font fallbacks to the embedded face."""
    def replace(match: re.Match[str]) -> str:
        body = _TRANSITION_RE.sub("", match.group("body"))
        for alias in (
            "'Pretendard Variable'",
            '"Pretendard Variable"',
            "Pretendard Variable",
            "'Noto Sans CJK KR'",
            '"Noto Sans CJK KR"',
            "Noto Sans CJK KR",
        ):
            body = body.replace(alias, "'HTMLSlide Embedded'")
        body = re.sub(
            r"(?i)(?<![A-Za-z0-9_-])(?:['\"])?Pretendard(?:['\"])?(?![A-Za-z0-9_-])",
            "'HTMLSlide Embedded'",
            body,
        )
        return f'<style{match.group("attrs")}>{body}</style>'

    return _STYLE_RE.sub(replace, source)


def _timing(
    plan: dict,
    *,
    fps: int,
    base_seconds: float,
    step_seconds: float,
    lead_seconds: float,
    cue_seconds: float,
) -> tuple[list[dict], float]:
    if fps < 1 or fps > 120:
        raise ContractError("fps must be between 1 and 120")
    if base_seconds <= 0 or step_seconds < 0 or lead_seconds < 0 or cue_seconds <= 0:
        raise ContractError(
            "base_seconds and cue_seconds must be positive; step_seconds and lead_seconds non-negative"
        )
    cursor = 0.0
    scenes = []
    for slide in plan["slides"]:
        duration = base_seconds + int(slide.get("steps", 0)) * step_seconds
        cues = []
        for motion in slide.get("motion", []):
            start_step = int(motion.get("startStep", 1))
            end_step = int(motion.get("endStep", start_step))
            for step in range(start_step, end_step + 1):
                at = min(duration - 0.001, lead_seconds + (step - 1) * step_seconds)
                cue_duration = max(0.001, min(cue_seconds, duration - at))
                cue = {
                    "module": motion["module"],
                    "target": motion["target"],
                    "reason": motion["reason"],
                    "step": step,
                    "at": at,
                    "duration": cue_duration,
                }
                if motion.get("pattern"):
                    cue["pattern"] = motion["pattern"]
                if motion["module"] == "sequence-step":
                    cue["itemIndex"] = step - start_step
                cues.append(cue)
        scenes.append(
            {
                "id": slide["id"],
                "start": cursor,
                "duration": duration,
                "cues": cues,
            }
        )
        cursor += duration
    return scenes, cursor


def compile_hyperframes(
    spec: dict,
    registry: Registry,
    *,
    asset_root: str | Path = ".",
    font: str | Path | None = None,
    fps: int = DEFAULT_FPS,
    base_seconds: float = DEFAULT_BASE_SECONDS,
    step_seconds: float = DEFAULT_STEP_SECONDS,
    lead_seconds: float = DEFAULT_LEAD_SECONDS,
    cue_seconds: float = DEFAULT_CUE_SECONDS,
) -> tuple[str, dict]:
    html, plan = build_deck(spec, registry, asset_root=asset_root, font=font)
    presenter_runtime = (registry.root / "core" / "runtime.js").read_text(encoding="utf-8")
    presenter_script = "<script>" + presenter_runtime + "</script>"
    if presenter_script not in html:
        raise ContractError("cannot isolate presenter runtime from generated HTML")
    html = html.replace(presenter_script, "", 1)
    html = _sanitize_video_styles(html)
    scenes, duration = _timing(
        plan,
        fps=fps,
        base_seconds=base_seconds,
        step_seconds=step_seconds,
        lead_seconds=lead_seconds,
        cue_seconds=cue_seconds,
    )
    by_id = {scene["id"]: scene for scene in scenes}

    root_attrs = (
        '<main id="html-slide-composition" data-stage data-composition-id="html-slide" data-start="0" '
        f'data-duration="{duration:.6f}" data-fps="{fps}" '
        'data-width="1920" data-height="1080"'
    )
    html = _STAGE_RE.sub(root_attrs, html, count=1)

    def slide_repl(match: re.Match[str]) -> str:
        slide_id = html_lib.unescape(match.group(1))
        try:
            scene = by_id[slide_id]
        except KeyError as exc:
            raise ContractError(f"missing HyperFrames timing for slide {slide_id}") from exc
        attrs = match.group(2)
        class_match = re.search(r'class="([^"]*)"', attrs)
        if class_match:
            classes = class_match.group(1).split()
            if "clip" not in classes:
                classes.append("clip")
            attrs = (
                attrs[: class_match.start()]
                + f'class="{" ".join(classes)}"'
                + attrs[class_match.end() :]
            )
        else:
            attrs += ' class="clip"'
        if not re.search(r'\\sid="[^"]+"', attrs):
            attrs += f' id="hf-slide-{slide_id}"'
        attrs += (
            f' data-start="{scene["start"]:.6f}"'
            f' data-duration="{scene["duration"]:.6f}"'
            ' data-track-index="0"'
        )
        return f'<section data-slide="{match.group(1)}"{attrs}>'

    html = _SLIDE_RE.sub(slide_repl, html)

    hf_css = """
<script src="./gsap.min.js"></script>
<style id="hyperframes-video-overrides">
html,body{width:1920px!important;height:1080px!important;overflow:hidden!important}
[data-stage]{width:1920px!important;height:1080px!important;position:relative!important;transform:none!important;overflow:hidden!important}
[data-slide]{position:absolute!important;inset:0!important;width:1920px!important;height:1080px!important;margin:0!important}
.clip[style*="visibility: hidden"] *{visibility:hidden!important}
.deck-shell,.deck-shell-progress,.deck-shell-overview,.deck-shell-sr{display:none!important}
.hf-pattern-overlay{font-family:inherit;color:inherit}
</style>
"""
    html = html.replace("<html ", '<html data-hf-video="1" ', 1)
    html = html.replace("</head>", hf_css + "</head>", 1)

    hf_plan = {
        "schemaVersion": 1,
        "source": "html-slide",
        "renderer": "hyperframes",
        "fps": fps,
        "width": 1920,
        "height": 1080,
        "durationSeconds": duration,
        "scenes": scenes,
    }
    runtime = (registry.root / "core" / "hyperframes_runtime.js").read_text(encoding="utf-8")
    if "</script" in runtime.lower():
        raise ContractError("unsafe script closing sequence in HyperFrames runtime")
    payload = (
        '<script type="application/json" id="hf-plan">'
        + json_script(hf_plan)
        + "</script><script>"
        + runtime
        + "</script><script>window.__mountHtmlSlideHyperframes('html-slide-composition','hf-plan')</script>"
    )
    html = html.replace("</body>", payload + "</body>", 1)
    return html, hf_plan


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--asset-root", type=Path)
    parser.add_argument("--font", type=Path)
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS)
    parser.add_argument("--base-seconds", type=float, default=DEFAULT_BASE_SECONDS)
    parser.add_argument("--step-seconds", type=float, default=DEFAULT_STEP_SECONDS)
    parser.add_argument("--lead-seconds", type=float, default=DEFAULT_LEAD_SECONDS)
    parser.add_argument("--cue-seconds", type=float, default=DEFAULT_CUE_SECONDS)
    args = parser.parse_args(argv)
    try:
        spec = load_spec(args.spec)
        composition, manifest = compile_hyperframes(
            spec,
            Registry(),
            asset_root=args.asset_root or args.spec.parent,
            font=args.font,
            fps=args.fps,
            base_seconds=args.base_seconds,
            step_seconds=args.step_seconds,
            lead_seconds=args.lead_seconds,
            cue_seconds=args.cue_seconds,
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(composition, encoding="utf-8")
        if args.manifest:
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            args.manifest.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        print(
            f"Built HyperFrames composition {args.out}: "
            f"{len(manifest['scenes'])} scenes, {manifest['durationSeconds']:.2f}s"
        )
        return 0
    except (ContractError, OSError, ValueError) as exc:
        print(f"HYPERFRAMES COMPOSE FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
