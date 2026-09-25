#!/usr/bin/env python3
"""Contracts and helpers for the html-slide HyperFrames video backend."""
from __future__ import annotations

import math
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from tools.motion_patterns import MotionPatternError, motion_pattern_ids


class HyperFramesPipelineError(ValueError):
    """Raised when a HyperFrames composition or render environment violates the contract."""


def _number(value: Any, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise HyperFramesPipelineError(f"{label} must be a finite number")
    number = float(value)
    if positive and number <= 0:
        raise HyperFramesPipelineError(f"{label} must be positive")
    return number


def _integer(value: Any, label: str, *, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise HyperFramesPipelineError(f"{label} must be an integer >= {minimum}")
    return value


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if manifest.get("schemaVersion") != 1:
        raise HyperFramesPipelineError("manifest schemaVersion must be 1")
    if manifest.get("source") != "html-slide":
        raise HyperFramesPipelineError("manifest source must be html-slide")
    if manifest.get("renderer") != "hyperframes":
        raise HyperFramesPipelineError("manifest renderer must be hyperframes")

    fps = _integer(manifest.get("fps"), "fps")
    width = _integer(manifest.get("width"), "width")
    height = _integer(manifest.get("height"), "height")
    duration = _number(manifest.get("durationSeconds"), "durationSeconds", positive=True)

    scenes = manifest.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise HyperFramesPipelineError("scenes must be a non-empty array")

    try:
        pattern_ids = motion_pattern_ids()
    except MotionPatternError as exc:
        raise HyperFramesPipelineError(f"invalid motion pattern catalog: {exc}") from exc

    cursor = 0.0
    total_cues = 0
    seen: set[str] = set()
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            raise HyperFramesPipelineError(f"scene {index} must be an object")
        scene_id = scene.get("id")
        if not isinstance(scene_id, str) or not scene_id:
            raise HyperFramesPipelineError(f"scene {index} has invalid id")
        if scene_id in seen:
            raise HyperFramesPipelineError(f"duplicate scene id: {scene_id}")
        seen.add(scene_id)

        start = _number(scene.get("start"), f"{scene_id}.start")
        scene_duration = _number(scene.get("duration"), f"{scene_id}.duration", positive=True)
        if not math.isclose(start, cursor, rel_tol=0, abs_tol=1e-6):
            raise HyperFramesPipelineError(
                f"{scene_id}.start must be contiguous: expected {cursor:.6f}, got {start:.6f}"
            )

        cues = scene.get("cues", [])
        if not isinstance(cues, list):
            raise HyperFramesPipelineError(f"{scene_id}.cues must be an array")
        for cue_index, cue in enumerate(cues):
            if not isinstance(cue, dict):
                raise HyperFramesPipelineError(f"{scene_id}.cues[{cue_index}] must be an object")
            if not isinstance(cue.get("module"), str) or not cue["module"]:
                raise HyperFramesPipelineError(f"{scene_id}.cues[{cue_index}] missing module")
            if not isinstance(cue.get("target"), str) or not cue["target"]:
                raise HyperFramesPipelineError(f"{scene_id}.cues[{cue_index}] missing target")
            if not isinstance(cue.get("reason"), str) or not cue["reason"].strip():
                raise HyperFramesPipelineError(f"{scene_id}.cues[{cue_index}] missing reason")
            at = _number(cue.get("at"), f"{scene_id}.cues[{cue_index}].at")
            cue_duration = _number(
                cue.get("duration"),
                f"{scene_id}.cues[{cue_index}].duration",
                positive=True,
            )
            if at < 0 or at >= scene_duration:
                raise HyperFramesPipelineError(
                    f"{scene_id}.cues[{cue_index}].at leaves the scene"
                )
            if at + cue_duration > scene_duration + 1e-6:
                raise HyperFramesPipelineError(
                    f"{scene_id}.cues[{cue_index}] extends beyond the scene"
                )
            pattern = cue.get("pattern")
            if pattern is not None and pattern not in pattern_ids:
                raise HyperFramesPipelineError(
                    f"{scene_id}.cues[{cue_index}] unknown motion pattern {pattern}"
                )
        total_cues += len(cues)
        cursor += scene_duration

    if not math.isclose(cursor, duration, rel_tol=0, abs_tol=1e-6):
        raise HyperFramesPipelineError(
            f"durationSeconds mismatch: expected {cursor:.6f}, got {duration:.6f}"
        )

    return {
        "scenes": len(scenes),
        "cues": total_cues,
        "fps": fps,
        "width": width,
        "height": height,
        "durationSeconds": duration,
        "durationInFrames": round(duration * fps),
    }


def sample_times(manifest: dict[str, Any]) -> list[float]:
    summary = validate_manifest(manifest)
    frame = 1 / summary["fps"]
    times: set[float] = set()
    for scene in manifest["scenes"]:
        start = float(scene["start"])
        duration = float(scene["duration"])
        last = max(start, start + duration - frame)
        times.add(start)
        times.add(min(last, start + duration / 2))
        for cue in scene.get("cues", []):
            cue_start = start + float(cue["at"])
            cue_end = min(last, cue_start + float(cue["duration"]))
            cue_mid = cue_start + max(0.0, (cue_end - cue_start) / 2)
            times.update((cue_start, cue_mid, cue_end))
        times.add(last)
    return sorted(round(value, 6) for value in times)


def npm_executable() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def hyperframes_executable(video_dir: str | Path) -> Path:
    root = Path(video_dir)
    name = "hyperframes.cmd" if os.name == "nt" else "hyperframes"
    binary = root / "node_modules" / ".bin" / name
    if not binary.is_file():
        raise HyperFramesPipelineError(
            f"HyperFrames is not installed in {root}. Run 'npm install' in video/ first."
        )
    return binary


def gsap_browser_file(video_dir: str | Path) -> Path:
    path = Path(video_dir) / "node_modules" / "gsap" / "dist" / "gsap.min.js"
    if not path.is_file():
        raise HyperFramesPipelineError(
            f"GSAP browser runtime is missing: {path}. Run 'npm install' in video/ first."
        )
    return path


def ffprobe_executable() -> str:
    command = shutil.which("ffprobe")
    if not command:
        raise HyperFramesPipelineError(
            "ffprobe is required by the HyperFrames video QA path but was not found on PATH"
        )
    return command


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
        raise HyperFramesPipelineError(f"{label}: command not found: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = ""
        if capture_output:
            detail = (exc.stderr or exc.stdout or "").strip()
        suffix = f": {detail}" if detail else ""
        raise HyperFramesPipelineError(
            f"{label} failed with exit code {exc.returncode}{suffix}"
        ) from exc
