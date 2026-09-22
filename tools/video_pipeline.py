#!/usr/bin/env python3
"""Shared contracts and helpers for html-slide video rendering."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MOTION_PATTERN_CATALOG = ROOT / "video" / "motion-patterns.json"


class VideoPipelineError(ValueError):
    """Raised when a storyboard or video-render environment violates the contract."""


def motion_pattern_ids() -> set[str]:
    try:
        catalog = json.loads(MOTION_PATTERN_CATALOG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VideoPipelineError(f"cannot read motion pattern catalog: {exc}") from exc
    patterns = catalog.get("patterns")
    if not isinstance(patterns, list):
        raise VideoPipelineError("motion pattern catalog must contain a patterns array")
    ids = {
        item.get("id")
        for item in patterns
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    if len(ids) != len(patterns):
        raise VideoPipelineError("motion pattern catalog contains invalid or duplicate ids")
    return ids


def read_storyboard(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VideoPipelineError(f"cannot read storyboard: {source}: {exc}") from exc
    if not isinstance(value, dict):
        raise VideoPipelineError("storyboard root must be an object")
    return value


def write_storyboard(path: str | Path, storyboard: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(storyboard, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _int(value: Any, label: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise VideoPipelineError(f"{label} must be an integer")
    if minimum is not None and value < minimum:
        raise VideoPipelineError(f"{label} must be >= {minimum}")
    return value


def validate_storyboard(storyboard: dict[str, Any]) -> dict[str, Any]:
    """Validate deterministic timing, slot assignment, and motion target integrity."""
    if storyboard.get("schemaVersion") != 1:
        raise VideoPipelineError("storyboard schemaVersion must be 1")
    if storyboard.get("source") != "html-slide":
        raise VideoPipelineError("storyboard source must be html-slide")

    fps = _int(storyboard.get("fps"), "fps", minimum=1)
    width = _int(storyboard.get("width"), "width", minimum=1)
    height = _int(storyboard.get("height"), "height", minimum=1)
    duration = _int(storyboard.get("durationInFrames"), "durationInFrames", minimum=1)

    design = storyboard.get("design")
    if not isinstance(design, dict):
        raise VideoPipelineError("design must be an object")
    palette = design.get("palette")
    dataviz = design.get("dataviz")
    if not isinstance(palette, dict) or not {"paper", "ink"}.issubset(palette):
        raise VideoPipelineError("design.palette must include paper and ink")
    if not isinstance(dataviz, dict) or "viz-1" not in dataviz:
        raise VideoPipelineError("design.dataviz must include viz-1")

    scenes = storyboard.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise VideoPipelineError("scenes must be a non-empty array")

    patterns = motion_pattern_ids()
    expected_start = 0
    total_cues = 0
    seen_scene_ids: set[str] = set()
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            raise VideoPipelineError(f"scene {index} must be an object")
        scene_id = scene.get("id")
        if not isinstance(scene_id, str) or not scene_id:
            raise VideoPipelineError(f"scene {index} has invalid id")
        if scene_id in seen_scene_ids:
            raise VideoPipelineError(f"duplicate scene id: {scene_id}")
        seen_scene_ids.add(scene_id)

        start = _int(scene.get("startFrame"), f"{scene_id}.startFrame", minimum=0)
        frames = _int(scene.get("durationFrames"), f"{scene_id}.durationFrames", minimum=1)
        transition = _int(scene.get("transitionFrames"), f"{scene_id}.transitionFrames", minimum=0)
        if start != expected_start:
            raise VideoPipelineError(
                f"{scene_id}.startFrame must be contiguous: expected {expected_start}, got {start}"
            )
        if transition >= frames:
            raise VideoPipelineError(f"{scene_id}.transitionFrames must be shorter than the scene")

        blocks = scene.get("blocks")
        if not isinstance(blocks, list) or not blocks:
            raise VideoPipelineError(f"{scene_id}.blocks must be a non-empty array")
        block_ids: list[str] = []
        for block in blocks:
            if not isinstance(block, dict):
                raise VideoPipelineError(f"{scene_id}: each block must be an object")
            block_id = block.get("id")
            if not isinstance(block_id, str) or not block_id:
                raise VideoPipelineError(f"{scene_id}: block id must be a non-empty string")
            block_ids.append(block_id)
        if len(block_ids) != len(set(block_ids)):
            raise VideoPipelineError(f"{scene_id}: duplicate block id")

        slots = scene.get("slots")
        if not isinstance(slots, dict) or not slots:
            raise VideoPipelineError(f"{scene_id}.slots must be a non-empty object")
        assigned: list[str] = []
        for slot_name, ids in slots.items():
            if not isinstance(slot_name, str) or not slot_name:
                raise VideoPipelineError(f"{scene_id}: invalid slot name")
            if not isinstance(ids, list):
                raise VideoPipelineError(f"{scene_id}.{slot_name}: slot value must be an array")
            for block_id in ids:
                if block_id not in block_ids:
                    raise VideoPipelineError(
                        f"{scene_id}.{slot_name}: unknown block target {block_id}"
                    )
                assigned.append(block_id)
        if len(assigned) != len(set(assigned)):
            raise VideoPipelineError(f"{scene_id}: a block may not occupy multiple slots")
        if set(assigned) != set(block_ids):
            missing = sorted(set(block_ids) - set(assigned))
            raise VideoPipelineError(f"{scene_id}: unassigned blocks: {', '.join(missing)}")

        cues = scene.get("cues", [])
        if not isinstance(cues, list):
            raise VideoPipelineError(f"{scene_id}.cues must be an array")
        for cue_index, cue in enumerate(cues):
            if not isinstance(cue, dict):
                raise VideoPipelineError(f"{scene_id}.cues[{cue_index}] must be an object")
            target = cue.get("target")
            if target not in block_ids:
                raise VideoPipelineError(
                    f"{scene_id}.cues[{cue_index}]: unknown target {target}"
                )
            step = _int(cue.get("step"), f"{scene_id}.cues[{cue_index}].step", minimum=1)
            at_frame = _int(
                cue.get("atFrame"),
                f"{scene_id}.cues[{cue_index}].atFrame",
                minimum=0,
            )
            cue_frames = _int(
                cue.get("durationFrames"),
                f"{scene_id}.cues[{cue_index}].durationFrames",
                minimum=1,
            )
            if at_frame >= frames:
                raise VideoPipelineError(
                    f"{scene_id}.cues[{cue_index}].atFrame leaves the scene"
                )
            if at_frame + cue_frames > frames:
                raise VideoPipelineError(
                    f"{scene_id}.cues[{cue_index}] extends beyond the scene"
                )
            if not isinstance(cue.get("module"), str) or not cue["module"]:
                raise VideoPipelineError(f"{scene_id}.cues[{cue_index}]: missing module")
            if not isinstance(cue.get("reason"), str) or not cue["reason"].strip():
                raise VideoPipelineError(f"{scene_id}.cues[{cue_index}]: missing reason")
            pattern = cue.get("pattern")
            if pattern is not None and pattern not in patterns:
                raise VideoPipelineError(
                    f"{scene_id}.cues[{cue_index}]: unknown motion pattern {pattern}"
                )
            if step < 1:
                raise VideoPipelineError(f"{scene_id}.cues[{cue_index}]: invalid step")
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


def sample_frames(storyboard: dict[str, Any]) -> list[int]:
    """Return representative global frames around scene and semantic-motion boundaries."""
    validate_storyboard(storyboard)
    frames: set[int] = set()
    for scene in storyboard["scenes"]:
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


def npm_executable() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def remotion_executable(video_dir: str | Path) -> Path:
    root = Path(video_dir)
    name = "remotion.cmd" if os.name == "nt" else "remotion"
    binary = root / "node_modules" / ".bin" / name
    if not binary.is_file():
        raise VideoPipelineError(
            f"Remotion is not installed in {root}. Run 'npm install' in video/ first."
        )
    return binary


def run_checked(
    command: list[str],
    *,
    cwd: str | Path,
    label: str,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=Path(cwd),
            check=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise VideoPipelineError(f"{label}: command not found: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise VideoPipelineError(f"{label} failed with exit code {exc.returncode}") from exc
