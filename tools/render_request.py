"""Validate GitHub Actions HyperFrames render requests."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

OUTPUT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
WORKERS_RE = re.compile(r"^(auto|[1-9]|1[0-9]|2[0-4])$")
ALLOWED_REQUEST_KEYS = {"spec_path", "output_name", "workers"}


class RenderRequestError(ValueError):
    """Raised when a render request is unsafe or malformed."""


def _validate_output_name(value: str) -> str:
    if not OUTPUT_RE.fullmatch(value):
        raise RenderRequestError(
            "output_name must match ^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"
        )
    return value


def _validate_workers(value: str) -> str:
    if not WORKERS_RE.fullmatch(value):
        raise RenderRequestError("workers must be auto or an integer from 1 to 24")
    return value


def _resolve_spec(root: Path, spec_path: str) -> Path:
    requested = Path(spec_path)
    if requested.is_absolute():
        raise RenderRequestError("spec_path must be relative to the render root")
    resolved_root = root.resolve(strict=True)
    resolved_spec = (resolved_root / requested).resolve(strict=True)
    try:
        resolved_spec.relative_to(resolved_root)
    except ValueError as exc:
        raise RenderRequestError("spec_path must stay inside the render root") from exc
    if resolved_spec.suffix.lower() != ".json":
        raise RenderRequestError("spec_path must point to a .json file")
    return resolved_spec


def _default_output_name(ref_name: str) -> str:
    name = ref_name[len("render/") :] if ref_name.startswith("render/") else ref_name
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", name).strip("-_")
    if not slug:
        slug = "html-slide-video"
    if not slug[0].isalnum():
        slug = f"render-{slug}"
    return slug[:64]


def _resolve(
    root: Path,
    *,
    spec_path: str,
    output_name: str,
    workers: str,
) -> dict[str, str]:
    spec_real = _resolve_spec(root, spec_path)
    return {
        "spec_real": str(spec_real),
        "asset_root": str(spec_real.parent),
        "output_name": _validate_output_name(output_name),
        "render_workers": _validate_workers(workers),
    }


def resolve_manual_request(
    root: Path,
    *,
    spec_path: str,
    output_name: str,
    workers: str,
) -> dict[str, str]:
    return _resolve(
        root,
        spec_path=spec_path,
        output_name=output_name,
        workers=workers,
    )


def resolve_push_request(
    root: Path,
    *,
    ref_name: str,
    request_name: str = "request.json",
) -> dict[str, str]:
    values: dict[str, Any] = {
        "spec_path": "deck.json",
        "output_name": _default_output_name(ref_name),
        "workers": "auto",
    }
    request_path = (root / request_name).resolve()
    if request_path.exists():
        try:
            payload = json.loads(request_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RenderRequestError(f"invalid render request JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise RenderRequestError("render request must be a JSON object")
        unknown = sorted(set(payload) - ALLOWED_REQUEST_KEYS)
        if unknown:
            raise RenderRequestError(
                "unsupported render request keys: " + ", ".join(unknown)
            )
        values.update(payload)

    for key in ALLOWED_REQUEST_KEYS:
        if not isinstance(values[key], str) or not values[key]:
            raise RenderRequestError(f"{key} must be a non-empty string")

    return _resolve(
        root,
        spec_path=values["spec_path"],
        output_name=values["output_name"],
        workers=values["workers"],
    )


def emit_github_outputs(values: dict[str, str]) -> None:
    for key in ("spec_real", "asset_root", "output_name", "render_workers"):
        print(f"{key}={values[key]}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)

    manual = subparsers.add_parser("manual")
    manual.add_argument("--root", type=Path, required=True)
    manual.add_argument("--spec-path", required=True)
    manual.add_argument("--output-name", required=True)
    manual.add_argument("--workers", required=True)

    push = subparsers.add_parser("push")
    push.add_argument("--root", type=Path, required=True)
    push.add_argument("--ref-name", required=True)
    push.add_argument("--request-name", default="request.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.mode == "manual":
            values = resolve_manual_request(
                args.root,
                spec_path=args.spec_path,
                output_name=args.output_name,
                workers=args.workers,
            )
        else:
            values = resolve_push_request(
                args.root,
                ref_name=args.ref_name,
                request_name=args.request_name,
            )
    except RenderRequestError as exc:
        print(f"render request error: {exc}", file=sys.stderr)
        return 2
    emit_github_outputs(values)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
