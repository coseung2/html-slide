#!/usr/bin/env python3
"""Verify a HyperFrames manifest, sampled PNG frames, and encoded MP4."""
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

from tools.hyperframes_pipeline import (
    HyperFramesPipelineError,
    ffprobe_executable,
    sample_times,
    validate_manifest,
)

H264_8BIT_420_PIXEL_FORMATS = frozenset({"yuv420p", "yuvj420p"})


def validate_h264_pixel_format(pixel_format: Any) -> str:
    if not isinstance(pixel_format, str) or pixel_format not in H264_8BIT_420_PIXEL_FORMATS:
        raise HyperFramesPipelineError(
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
        raise HyperFramesPipelineError(f"invalid PNG frame: {path}")
    return struct.unpack(">II", data[16:24])


def verify_frame_directory(
    frames_dir: str | Path,
    expected_times: list[float],
    *,
    width: int,
    height: int,
) -> dict[str, Any]:
    root = Path(frames_dir)
    if not root.is_dir():
        raise HyperFramesPipelineError(f"missing sampled-frame directory: {root}")
    files = sorted(root.glob("*.png"))
    if len(files) != len(expected_times):
        raise HyperFramesPipelineError(
            f"sampled-frame count mismatch: expected {len(expected_times)}, got {len(files)}"
        )
    for frame in files:
        size = _png_dimensions(frame)
        if size != (width, height):
            raise HyperFramesPipelineError(
                f"sampled frame has wrong size: {frame.name}: {size[0]}x{size[1]}"
            )
    return {
        "count": len(files),
        "expectedTimes": expected_times,
        "files": [item.name for item in files],
    }


def probe_video(video: str | Path) -> dict[str, Any]:
    source = Path(video)
    if not source.is_file() or source.stat().st_size == 0:
        raise HyperFramesPipelineError(f"missing or empty video: {source}")
    command = [
        ffprobe_executable(),
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(source),
    ]
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
    except FileNotFoundError as exc:
        raise HyperFramesPipelineError(f"ffprobe command not found: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise HyperFramesPipelineError(
            f"ffprobe failed with exit code {exc.returncode}: {detail}"
        ) from exc
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise HyperFramesPipelineError("ffprobe did not return JSON") from exc
    if not isinstance(value, dict):
        raise HyperFramesPipelineError("ffprobe result must be an object")
    return value


def verify_video_artifacts(
    manifest: dict[str, Any],
    *,
    video: str | Path,
    frames_dir: str | Path | None = None,
) -> dict[str, Any]:
    summary = validate_manifest(manifest)
    probe = probe_video(video)
    streams = probe.get("streams", [])
    if not isinstance(streams, list):
        raise HyperFramesPipelineError("ffprobe streams must be an array")
    video_streams = [
        stream
        for stream in streams
        if isinstance(stream, dict) and stream.get("codec_type") == "video"
    ]
    if len(video_streams) != 1:
        raise HyperFramesPipelineError(
            f"expected exactly one video stream, got {len(video_streams)}"
        )
    stream = video_streams[0]
    if stream.get("codec_name") not in ("h264", "avc1"):
        raise HyperFramesPipelineError(f"unexpected video codec: {stream.get('codec_name')}")
    if int(stream.get("width", 0)) != summary["width"]:
        raise HyperFramesPipelineError(
            f"video width mismatch: expected {summary['width']}, got {stream.get('width')}"
        )
    if int(stream.get("height", 0)) != summary["height"]:
        raise HyperFramesPipelineError(
            f"video height mismatch: expected {summary['height']}, got {stream.get('height')}"
        )
    pixel_format = validate_h264_pixel_format(stream.get("pix_fmt"))

    rate_text = str(stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "0")
    actual_fps = _ratio(rate_text)
    if not math.isclose(actual_fps, summary["fps"], rel_tol=0, abs_tol=0.01):
        raise HyperFramesPipelineError(
            f"video fps mismatch: expected {summary['fps']}, got {actual_fps:.4f}"
        )

    format_data = probe.get("format", {})
    if not isinstance(format_data, dict):
        raise HyperFramesPipelineError("ffprobe format must be an object")
    duration_text = format_data.get("duration") or stream.get("duration")
    if duration_text is None:
        raise HyperFramesPipelineError("ffprobe did not report video duration")
    actual_duration = float(duration_text)
    expected_duration = float(summary["durationSeconds"])
    tolerance = max(0.08, 2 / summary["fps"])
    if abs(actual_duration - expected_duration) > tolerance:
        raise HyperFramesPipelineError(
            f"video duration mismatch: expected {expected_duration:.3f}s, "
            f"got {actual_duration:.3f}s"
        )

    report: dict[str, Any] = {
        "renderer": "hyperframes",
        "manifest": summary,
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
                1
                for item in streams
                if isinstance(item, dict) and item.get("codec_type") == "audio"
            ),
        },
    }
    if frames_dir is not None:
        times = sample_times(manifest)
        report["sampledFrames"] = verify_frame_directory(
            frames_dir,
            times,
            width=summary["width"],
            height=summary["height"],
        )
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--video", type=Path)
    parser.add_argument("--frames-dir", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        if args.video:
            report = verify_video_artifacts(
                manifest,
                video=args.video,
                frames_dir=args.frames_dir,
            )
        else:
            report = {"renderer": "hyperframes", "manifest": validate_manifest(manifest)}
            if args.frames_dir:
                summary = report["manifest"]
                report["sampledFrames"] = verify_frame_directory(
                    args.frames_dir,
                    sample_times(manifest),
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
    except (OSError, json.JSONDecodeError, HyperFramesPipelineError, ValueError) as exc:
        print(f"VIDEO QA FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
