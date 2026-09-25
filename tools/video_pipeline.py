#!/usr/bin/env python3
"""Shared timing, HyperFrames HTML adaptation, and render helpers."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HYPERFRAMES_RUNTIME = ROOT / "core" / "hyperframes_runtime.js"

DEFAULT_FPS = 30
DEFAULT_BASE_SECONDS = 4.0
DEFAULT_STEP_SECONDS = 1.2
DEFAULT_LEAD_SECONDS = 0.6
DEFAULT_TRANSITION_SECONDS = 0.35


class VideoPipelineError(ValueError):
    """Raised when video timing or the HyperFrames environment violates the contract."""


def _int(value: Any, label: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise VideoPipelineError(f"{label} must be an integer")
    if minimum is not None and value < minimum:
        raise VideoPipelineError(f"{label} must be >= {minimum}")
    return value


def compile_video_timing(
    spec: dict[str, Any],
    plan: dict[str, Any],
    *,
    fps: int = DEFAULT_FPS,
    base_seconds: float = DEFAULT_BASE_SECONDS,
    step_seconds: float = DEFAULT_STEP_SECONDS,
    lead_seconds: float = DEFAULT_LEAD_SECONDS,
    transition_seconds: float = DEFAULT_TRANSITION_SECONDS,
) -> dict[str, Any]:
    """Compile only execution timing; visual/content truth stays in the built HTML."""
    if fps < 1 or fps > 120:
        raise VideoPipelineError("fps must be between 1 and 120")
    if base_seconds <= 0 or step_seconds < 0 or lead_seconds < 0 or transition_seconds < 0:
        raise VideoPipelineError(
            "video timing values must be non-negative and base_seconds must be positive"
        )
    if len(spec.get("slides", [])) != len(plan.get("slides", [])):
        raise VideoPipelineError("spec/plan slide count mismatch")

    scenes: list[dict[str, Any]] = []
    cursor = 0
    cue_gap = round(step_seconds * fps)
    cue_lead = round(lead_seconds * fps)
    for index, (source, planned) in enumerate(zip(spec["slides"], plan["slides"])):
        steps = int(planned.get("steps", 0))
        duration_frames = max(1, round((base_seconds + steps * step_seconds) * fps))
        targets = [block["id"] for block in source["blocks"]]
        cues: list[dict[str, Any]] = []
        for motion in planned.get("motion", []):
            start_step = int(motion.get("startStep", 1))
            end_step = int(motion.get("endStep", start_step))
            for step in range(start_step, end_step + 1):
                at_frame = min(duration_frames - 1, cue_lead + (step - 1) * cue_gap)
                cue = {
                    "module": motion["module"],
                    "target": motion["target"],
                    "reason": motion["reason"],
                    "step": step,
                    "atFrame": at_frame,
                    "durationFrames": max(
                        1,
                        min(round(0.8 * fps), duration_frames - at_frame),
                    ),
                }
                for key in ("pattern", "patternSource", "patternReasons", "patternWarnings", "intensity"):
                    if motion.get(key) is not None:
                        cue[key] = motion[key]
                cues.append(cue)

        scenes.append(
            {
                "id": source["id"],
                "index": index,
                "targets": targets,
                "steps": steps,
                "startFrame": cursor,
                "durationFrames": duration_frames,
                "transitionFrames": 0 if index == 0 else min(
                    duration_frames - 1, round(transition_seconds * fps)
                ),
                "cues": cues,
            }
        )
        cursor += duration_frames

    timing = {
        "schemaVersion": 2,
        "source": "html-slide-html",
        "renderer": "hyperframes",
        "fps": fps,
        "width": 1920,
        "height": 1080,
        "durationInFrames": cursor,
        "scenes": scenes,
    }
    validate_video_timing(timing)
    return timing


def validate_video_timing(timing: dict[str, Any]) -> dict[str, Any]:
    if timing.get("schemaVersion") != 2:
        raise VideoPipelineError("video timing schemaVersion must be 2")
    if timing.get("source") != "html-slide-html":
        raise VideoPipelineError("video timing source must be html-slide-html")
    if timing.get("renderer") != "hyperframes":
        raise VideoPipelineError("video timing renderer must be hyperframes")

    fps = _int(timing.get("fps"), "fps", minimum=1)
    width = _int(timing.get("width"), "width", minimum=1)
    height = _int(timing.get("height"), "height", minimum=1)
    duration = _int(timing.get("durationInFrames"), "durationInFrames", minimum=1)
    scenes = timing.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise VideoPipelineError("scenes must be a non-empty array")

    expected_start = 0
    total_cues = 0
    seen_ids: set[str] = set()
    for scene_index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            raise VideoPipelineError(f"scene {scene_index} must be an object")
        scene_id = scene.get("id")
        if not isinstance(scene_id, str) or not scene_id:
            raise VideoPipelineError(f"scene {scene_index} has invalid id")
        if scene_id in seen_ids:
            raise VideoPipelineError(f"duplicate scene id: {scene_id}")
        seen_ids.add(scene_id)

        start = _int(scene.get("startFrame"), f"{scene_id}.startFrame", minimum=0)
        frames = _int(scene.get("durationFrames"), f"{scene_id}.durationFrames", minimum=1)
        transition = _int(scene.get("transitionFrames"), f"{scene_id}.transitionFrames", minimum=0)
        _int(scene.get("steps"), f"{scene_id}.steps", minimum=0)
        if start != expected_start:
            raise VideoPipelineError(
                f"{scene_id}.startFrame must be contiguous: expected {expected_start}, got {start}"
            )
        if transition >= frames:
            raise VideoPipelineError(f"{scene_id}.transitionFrames must be shorter than the scene")

        targets = scene.get("targets")
        if not isinstance(targets, list) or not targets or any(
            not isinstance(item, str) or not item for item in targets
        ):
            raise VideoPipelineError(f"{scene_id}.targets must contain block ids")
        if len(targets) != len(set(targets)):
            raise VideoPipelineError(f"{scene_id}.targets contains duplicates")

        cues = scene.get("cues", [])
        if not isinstance(cues, list):
            raise VideoPipelineError(f"{scene_id}.cues must be an array")
        for cue_index, cue in enumerate(cues):
            if not isinstance(cue, dict):
                raise VideoPipelineError(f"{scene_id}.cues[{cue_index}] must be an object")
            if cue.get("target") not in targets:
                raise VideoPipelineError(
                    f"{scene_id}.cues[{cue_index}]: unknown target {cue.get('target')}"
                )
            if not isinstance(cue.get("module"), str) or not cue["module"]:
                raise VideoPipelineError(f"{scene_id}.cues[{cue_index}]: missing module")
            if not isinstance(cue.get("reason"), str) or not cue["reason"].strip():
                raise VideoPipelineError(f"{scene_id}.cues[{cue_index}]: missing reason")
            _int(cue.get("step"), f"{scene_id}.cues[{cue_index}].step", minimum=1)
            at_frame = _int(
                cue.get("atFrame"), f"{scene_id}.cues[{cue_index}].atFrame", minimum=0
            )
            cue_frames = _int(
                cue.get("durationFrames"),
                f"{scene_id}.cues[{cue_index}].durationFrames",
                minimum=1,
            )
            if at_frame >= frames:
                raise VideoPipelineError(f"{scene_id}.cues[{cue_index}].atFrame leaves the scene")
            if at_frame + cue_frames > frames:
                raise VideoPipelineError(f"{scene_id}.cues[{cue_index}] extends beyond the scene")
        total_cues += len(cues)
        expected_start += frames

    if expected_start != duration:
        raise VideoPipelineError(
            f"durationInFrames mismatch: expected {expected_start}, got {duration}"
        )
    return {
        "scenes": len(scenes),
        "cues": total_cues,
        "fps": fps,
        "width": width,
        "height": height,
        "durationInFrames": duration,
        "durationSeconds": duration / fps,
    }


def sample_frames(timing: dict[str, Any]) -> list[int]:
    """Representative global frames around scene and semantic-motion boundaries."""
    validate_video_timing(timing)
    frames: set[int] = set()
    for scene in timing["scenes"]:
        start = scene["startFrame"]
        duration = scene["durationFrames"]
        last_local = duration - 1
        frames.add(start)
        if scene["transitionFrames"]:
            frames.add(start + min(last_local, scene["transitionFrames"]))
        for cue in scene.get("cues", []):
            cue_start = cue["atFrame"]
            cue_last = min(last_local, cue_start + cue["durationFrames"] - 1)
            cue_mid = cue_start + max(0, (cue_last - cue_start) // 2)
            frames.update((start + cue_start, start + cue_mid, start + cue_last))
        frames.add(start + last_local)
    return sorted(frames)


def _seconds(frames: int, fps: int) -> str:
    return f"{frames / fps:.6f}".rstrip("0").rstrip(".")


def instrument_hyperframes_html(html: str, timing: dict[str, Any]) -> str:
    """Adapt the already-built HTML into one HyperFrames composition without re-rendering it."""
    summary = validate_video_timing(timing)
    if "data-composition-id=" in html:
        raise VideoPipelineError("built deck unexpectedly already declares a HyperFrames composition")

    html = html.replace(
        "<html ",
        '<html class="deck-video" ',
        1,
    )
    html = html.replace('data-mode="static"', 'data-mode="live"', 1)
    duration = _seconds(timing["durationInFrames"], timing["fps"])
    root_attrs = (
        'id="html-slide-video" data-composition-id="html-slide-video" '
        f'data-start="0" data-duration="{duration}" '
        f'data-width="{summary["width"]}" data-height="{summary["height"]}" '
        f'data-fps="{summary["fps"]}" data-no-timeline '
    )
    html = html.replace("<main data-stage", f"<main {root_attrs}data-stage", 1)

    for scene in timing["scenes"]:
        scene_id = re.escape(scene["id"])
        pattern = re.compile(rf'<section\s+data-slide="{scene_id}"[^>]*>')
        match = pattern.search(html)
        if not match:
            raise VideoPipelineError(f"built HTML is missing slide {scene['id']}")
        tag = match.group(0)
        if ' id="' in tag:
            raise VideoPipelineError(f"slide {scene['id']} unexpectedly already has an id")
        start = _seconds(scene["startFrame"], timing["fps"])
        scene_duration = _seconds(scene["durationFrames"], timing["fps"])
        tag = tag.replace(
            f'data-slide="{scene["id"]}"',
            (
                f'id="hf-slide-{scene["index"]}" class="clip" '
                f'data-start="{start}" data-duration="{scene_duration}" '
                f'data-track-index="0" data-slide="{scene["id"]}"'
            ),
            1,
        )
        # Composer already emits one layout class; merge it rather than creating a second class attr.
        tag = tag.replace(' class="layout-', ' data-layout-class="layout-', 1)
        layout_match = re.search(r'data-layout-class="([^"]+)"', tag)
        if layout_match:
            layout_class = layout_match.group(1)
            tag = tag.replace(
                f'data-layout-class="{layout_class}"',
                f'class="clip {layout_class}"',
                1,
            )
            tag = tag.replace('class="clip" ', "", 1)
        html = html[: match.start()] + tag + html[match.end() :]

    video_css = """
<style id="html-slide-hyperframes">
html.deck-video,html.deck-video body{width:1920px;height:1080px;overflow:hidden!important}
html.deck-video [data-stage]{width:1920px!important;height:1080px!important;position:relative!important;left:0!important;top:0!important;transform:none!important}
html.deck-video [data-slide]{position:absolute!important;inset:0!important;width:1920px!important;height:1080px!important;pointer-events:none!important}
html.deck-video .deck-shell,html.deck-video .deck-shell-progress,html.deck-video .deck-shell-overview,html.deck-video .deck-shell-sr{display:none!important}
html.deck-video *,html.deck-video *::before,html.deck-video *::after{transition:none!important}
html.deck-video [data-motion-run="1"],html.deck-video [data-motion-run="1"] *,html.deck-video [data-motion-run="1"]::before,html.deck-video [data-motion-run="1"]::after{animation-play-state:paused!important;animation-fill-mode:both!important;animation-iteration-count:1!important}
html.deck-video [data-motion-run="1"] [data-pattern-primary],html.deck-video [data-motion-run="1"]::before,html.deck-video [data-motion-run="1"]::after,html.deck-video [data-motion-run="1"] .motion-text-path,html.deck-video [data-motion-run="1"] .motion-text-path path{animation-delay:var(--hf-start,0s)!important}
html.deck-video [data-pattern="particle-warp"][data-motion-run="1"] .motion-particle{animation-delay:calc(var(--hf-start,0s) + var(--i)*14ms)!important}
html.deck-video [data-pattern="swiss-grid"][data-motion-run="1"]::after{animation-delay:calc(var(--hf-start,0s) + 110ms)!important}
html.deck-video .hf-final-text{position:relative;z-index:1}
html.deck-video .hf-motion-overlay,html.deck-video .hf-value-frame{position:absolute;inset:0;z-index:2;pointer-events:none;font:inherit;font-variation-settings:inherit;font-feature-settings:inherit;font-kerning:inherit;letter-spacing:inherit;line-height:inherit;color:inherit;white-space:pre-wrap}
html.deck-video .hf-value-host{position:relative!important;display:inline-block}
html.deck-video .hf-value-spacer{opacity:0}
</style>
"""
    timing_json = json.dumps(timing, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\/"
    )
    runtime = HYPERFRAMES_RUNTIME.read_text(encoding="utf-8")
    if "</script" in runtime.lower():
        raise VideoPipelineError("unsafe script closing sequence in HyperFrames adapter")
    html = html.replace("</head>", video_css + "</head>", 1)
    html = html.replace(
        "</body>",
        (
            f'<script type="application/json" id="hf-video-timing">{timing_json}</script>'
            f"<script>{runtime}</script></body>"
        ),
        1,
    )
    return html


def read_video_timing(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VideoPipelineError(f"cannot read video timing: {source}: {exc}") from exc
    if not isinstance(value, dict):
        raise VideoPipelineError("video timing root must be an object")
    return value


def write_video_timing(path: str | Path, timing: dict[str, Any]) -> None:
    validate_video_timing(timing)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(timing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def npm_executable() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def hyperframes_executable(root: str | Path = ROOT) -> Path:
    base = Path(root)
    name = "hyperframes.cmd" if os.name == "nt" else "hyperframes"
    binary = base / "node_modules" / ".bin" / name
    if not binary.is_file():
        raise VideoPipelineError(
            f"HyperFrames is not installed in {base}. Run 'npm install' at the repository root first."
        )
    return binary


def ffprobe_executable() -> str:
    binary = shutil.which("ffprobe")
    if not binary:
        raise VideoPipelineError("ffprobe is required; install FFmpeg before rendering video")
    return binary


def run_checked(
    command: list[str],
    *,
    cwd: str | Path,
    label: str,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=Path(cwd),
            check=True,
            text=True,
            capture_output=capture_output,
        )
    except FileNotFoundError as exc:
        raise VideoPipelineError(f"{label}: command not found: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = ""
        if capture_output:
            detail = (exc.stderr or exc.stdout or "").strip()
        suffix = f": {detail}" if detail else ""
        raise VideoPipelineError(f"{label} failed with exit code {exc.returncode}{suffix}") from exc
