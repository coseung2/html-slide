#!/usr/bin/env python3
"""Verify Remotion storyboard, sampled PNG frames, and an encoded MP4."""
from __future__ import annotations

import argparse
import json
import math
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.video_pipeline import (
    VideoPipelineError,
    read_storyboard,
    remotion_executable,
    sample_frames,
    validate_storyboard,
)

ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / "video"
H264_8BIT_420_PIXEL_FORMATS = frozenset({"yuv420p", "yuvj420p"})


def validate_h264_pixel_format(pixel_format: Any) -> str:
    """Accept FFmpeg's limited- and full-range names for planar 8-bit 4:2:0."""
    if not isinstance(pixel_format, str) or pixel_format not in H264_8BIT_420_PIXEL_FORMATS:
        raise VideoPipelineError(
            "unexpected H.264 8-bit 4:2:0 pixel format: "
            f"{pixel_format}; expected one of {sorted(H264_8BIT_420_PIXEL_FORMATS)}"
        )
    return pixel_format


def _ratio(value: str) -> float:
    if "/" in value:
        numerator, denominator = value.split("/", 1)
        denominator_value = float(denominator)
        if denominator_value == 0:
            return 0.0
        return float(numerator) / denominator_value
    return float(value)


def _png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise VideoPipelineError(f"invalid PNG frame: {path}")
    return struct.unpack(">II", data[16:24])


def verify_frame_directory(
    frames_dir: str | Path,
    expected_frames: list[int],
    *,
    width: int,
    height: int,
) -> dict[str, Any]:
    root = Path(frames_dir)
    if not root.is_dir():
        raise VideoPipelineError(f"missing sampled-frame directory: {root}")
    files = sorted(root.glob("*.png"))
    if len(files) != len(expected_frames):
        raise VideoPipelineError(
            f"sampled-frame count mismatch: expected {len(expected_frames)}, got {len(files)}"
        )
    for frame in files:
        size = _png_dimensions(frame)
        if size != (width, height):
            raise VideoPipelineError(
                f"sampled frame has wrong size: {frame.name}: {size[0]}x{size[1]}"
            )
    return {
        "count": len(files),
        "expectedFrames": expected_frames,
        "files": [item.name for item in files],
    }


def probe_video(video: str | Path, *, video_dir: str | Path = VIDEO_DIR) -> dict[str, Any]:
    source = Path(video)
    if not source.is_file() or source.stat().st_size == 0:
        raise VideoPipelineError(f"missing or empty video: {source}")
    remotion = str(remotion_executable(video_dir))
    command = [
        remotion,
        "ffprobe",
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(source),
    ]
    try:
        result = subprocess.run(
            command,
            cwd=Path(video_dir),
            check=True,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise VideoPipelineError(f"ffprobe command not found: {remotion}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise VideoPipelineError(
            f"ffprobe failed with exit code {exc.returncode}: {detail}"
        ) from exc
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise VideoPipelineError("ffprobe did not return JSON") from exc
    if not isinstance(value, dict):
        raise VideoPipelineError("ffprobe result must be an object")
    return value


def verify_video_artifacts(
    storyboard: dict[str, Any],
    *,
    video: str | Path,
    frames_dir: str | Path | None = None,
    video_dir: str | Path = VIDEO_DIR,
) -> dict[str, Any]:
    summary = validate_storyboard(storyboard)
    probe = probe_video(video, video_dir=video_dir)
    streams = probe.get("streams", [])
    if not isinstance(streams, list):
        raise VideoPipelineError("ffprobe streams must be an array")
    video_streams = [
        stream for stream in streams
        if isinstance(stream, dict) and stream.get("codec_type") == "video"
    ]
    if len(video_streams) != 1:
        raise VideoPipelineError(
            f"expected exactly one video stream, got {len(video_streams)}"
        )
    stream = video_streams[0]
    if stream.get("codec_name") not in ("h264", "avc1"):
        raise VideoPipelineError(f"unexpected video codec: {stream.get('codec_name')}")
    if int(stream.get("width", 0)) != summary["width"]:
        raise VideoPipelineError(
            f"video width mismatch: expected {summary['width']}, got {stream.get('width')}"
        )
    if int(stream.get("height", 0)) != summary["height"]:
        raise VideoPipelineError(
            f"video height mismatch: expected {summary['height']}, got {stream.get('height')}"
        )
    pixel_format = validate_h264_pixel_format(stream.get("pix_fmt"))

    rate_text = str(stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "0")
    actual_fps = _ratio(rate_text)
    if not math.isclose(actual_fps, summary["fps"], rel_tol=0, abs_tol=0.01):
        raise VideoPipelineError(
            f"video fps mismatch: expected {summary['fps']}, got {actual_fps:.4f}"
        )

    format_data = probe.get("format", {})
    if not isinstance(format_data, dict):
        raise VideoPipelineError("ffprobe format must be an object")
    duration_text = format_data.get("duration") or stream.get("duration")
    if duration_text is None:
        raise VideoPipelineError("ffprobe did not report video duration")
    actual_duration = float(duration_text)
    expected_duration = float(summary["durationSeconds"])
    tolerance = max(0.08, 2 / summary["fps"])
    if abs(actual_duration - expected_duration) > tolerance:
        raise VideoPipelineError(
            f"video duration mismatch: expected {expected_duration:.3f}s, "
            f"got {actual_duration:.3f}s"
        )

    report: dict[str, Any] = {
        "storyboard": summary,
        "video": {
            "path": str(Path(video)),
            "bytes": Path(video).stat().st_size,
            "codec": stream.get("codec_name"),
            "pixelFormat": pixel_format,
            "colorRange": stream.get("color_range"),
            "width": int(stream["width"]),
            "height": int(stream["height"]),
            "fps": actual_fps,
            "durationSeconds": actual_duration,
            "audioStreams": sum(
                1 for item in streams
                if isinstance(item, dict) and item.get("codec_type") == "audio"
            ),
        },
    }
    if frames_dir is not None:
        frames = sample_frames(storyboard)
        report["sampledFrames"] = verify_frame_directory(
            frames_dir,
            frames,
            width=summary["width"],
            height=summary["height"],
        )
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("storyboard", type=Path)
    parser.add_argument("--video", type=Path)
    parser.add_argument("--frames-dir", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        storyboard = read_storyboard(args.storyboard)
        if args.video:
            report = verify_video_artifacts(
                storyboard,
                video=args.video,
                frames_dir=args.frames_dir,
            )
        else:
            report = {"storyboard": validate_storyboard(storyboard)}
            if args.frames_dir:
                summary = report["storyboard"]
                report["sampledFrames"] = verify_frame_directory(
                    args.frames_dir,
                    sample_frames(storyboard),
                    width=summary["width"],
                    height=summary["height"],
                )
        text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text, encoding="utf-8")
        else:
            print(text, end="")
        return 0
    except (OSError, VideoPipelineError, ValueError) as exc:
        print(f"VIDEO QA FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
