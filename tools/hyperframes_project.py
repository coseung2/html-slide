#!/usr/bin/env python3
"""Build a HyperFrames project with one isolated sub-composition per html-slide scene."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from core import Registry, build_deck
from core.composer import json_script
from core.registry import ContractError
from core.renderers import esc
from core.validation import load_spec
from tools.compose_hyperframes import (
    DEFAULT_BASE_SECONDS,
    DEFAULT_CUE_SECONDS,
    DEFAULT_FPS,
    DEFAULT_LEAD_SECONDS,
    DEFAULT_STEP_SECONDS,
    _sanitize_video_styles,
    _timing,
)

_STYLE_RE = re.compile(r"<style(?P<attrs>[^>]*)>(?P<body>[\s\S]*?)</style>", re.IGNORECASE)


def _remove_presenter_runtime(html: str, registry: Registry) -> str:
    presenter_runtime = (registry.root / "core" / "runtime.js").read_text(encoding="utf-8")
    presenter_script = "<script>" + presenter_runtime + "</script>"
    if presenter_script not in html:
        raise ContractError("cannot isolate presenter runtime from generated HTML")
    return html.replace(presenter_script, "", 1)


def _shared_styles(html: str) -> str:
    styles = "\n".join(match.group("body") for match in _STYLE_RE.finditer(html))
    styles = re.sub(
        r"\bbody(?=\[data-(?:typography|palette|dataviz)=)",
        ".hf-slide-root",
        styles,
    )
    return styles


def _slide_markup(html: str, slide_id: str) -> str:
    match = re.search(
        rf'<section data-slide="{re.escape(slide_id)}"(?P<attrs>[^>]*)>(?P<body>[\s\S]*?)</section>',
        html,
    )
    if not match:
        raise ContractError(f"cannot locate generated slide markup: {slide_id}")
    return (
        f'<section data-slide="{slide_id}"{match.group("attrs")}>'
        f'{match.group("body")}</section>'
    )


def _fragment_runtime(registry: Registry, *, root_id: str, plan_id: str) -> str:
    runtime = (registry.root / "core" / "hyperframes_runtime.js").read_text(encoding="utf-8")
    runtime = runtime.replace("__HF_ROOT_ID__", root_id).replace("__HF_PLAN_ID__", plan_id)
    if "__HF_" in runtime:
        raise ContractError("unresolved HyperFrames runtime placeholder")
    if "</script" in runtime.lower():
        raise ContractError("unsafe script closing sequence in HyperFrames runtime")
    return runtime


def compile_hyperframes_project(
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
) -> tuple[str, dict[str, str], dict]:
    """Return (index_html, fragment_files, manifest)."""
    deck_html, plan = build_deck(spec, registry, asset_root=asset_root, font=font)
    deck_html = _sanitize_video_styles(_remove_presenter_runtime(deck_html, registry))
    styles = _shared_styles(deck_html)
    scenes, duration = _timing(
        plan,
        fps=fps,
        base_seconds=base_seconds,
        step_seconds=step_seconds,
        lead_seconds=lead_seconds,
        cue_seconds=cue_seconds,
    )

    typography = plan["styles"]["typography"]["id"]
    palette = plan["styles"]["palette"]["id"]
    dataviz = plan["styles"]["dataviz"]["id"]
    fragments: dict[str, str] = {}
    hosts: list[str] = []

    for scene, planned in zip(scenes, plan["slides"]):
        slide_id = scene["id"]
        composition_id = f"html-slide-{slide_id}"
        root_id = f"hf-root-{slide_id}"
        plan_id = f"hf-plan-{slide_id}"
        fragment_path = f"compositions/{slide_id}.html"

        local_scene = {
            **scene,
            "start": 0.0,
        }
        local_manifest = {
            "schemaVersion": 1,
            "source": "html-slide",
            "renderer": "hyperframes",
            "fps": fps,
            "width": 1920,
            "height": 1080,
            "durationSeconds": scene["duration"],
            "scenes": [local_scene],
        }
        runtime = _fragment_runtime(registry, root_id=root_id, plan_id=plan_id)
        slide_markup = _slide_markup(deck_html, slide_id)
        theme = planned.get("theme", spec["theme"])

        fragment = f"""<template>
<script src="../gsap.min.js"></script>
<style>
{styles}
.hf-slide-root{{position:relative;width:1920px;height:1080px;overflow:hidden;background:var(--paper);color:var(--ink);font-family:var(--font-body,'HTMLSlide Embedded',system-ui,sans-serif);font-weight:var(--body-weight,500);word-break:keep-all;overflow-wrap:break-word}}
.hf-slide-root [data-slide]{{position:absolute!important;inset:0!important;width:1920px!important;height:1080px!important;visibility:visible!important;pointer-events:none!important;margin:0!important}}
.deck-shell,.deck-shell-progress,.deck-shell-overview,.deck-shell-sr{{display:none!important}}
.hf-pattern-overlay{{font-family:inherit;color:inherit}}
</style>
<div
  id="{root_id}"
  class="hf-slide-root"
  data-hf-slide-root
  data-composition-id="{composition_id}"
  data-duration="{scene['duration']:.6f}"
  data-width="1920"
  data-height="1080"
  data-theme="{theme}"
  data-typography="{typography}"
  data-palette="{palette}"
  data-dataviz="{dataviz}"
>
{slide_markup}
<script type="application/json" id="{plan_id}">{json_script(local_manifest)}</script>
</div>
<script>{runtime}</script>
</template>
"""
        fragments[fragment_path] = fragment
        hosts.append(
            f"""<div
  id="hf-host-{slide_id}"
  class="clip"
  data-composition-id="{composition_id}"
  data-composition-src="./{fragment_path}"
  data-start="{scene['start']:.6f}"
  data-duration="{scene['duration']:.6f}"
  data-track-index="0"
  data-width="1920"
  data-height="1080"
></div>"""
        )

    index_html = f"""<!doctype html>
<html lang="{spec.get('language','ko')}" data-hf-video="1">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=1920,height=1080">
<title>{esc(spec['title'])}</title>
<script src="./gsap.min.js"></script>
<style>
*{{box-sizing:border-box}}
html,body{{margin:0;width:1920px;height:1080px;overflow:hidden;background:#111}}
#html-slide-composition{{position:relative;width:1920px;height:1080px;overflow:hidden}}
.clip{{position:absolute;inset:0;width:1920px;height:1080px}}
</style>
</head>
<body>
<main
  id="html-slide-composition"
  data-composition-id="html-slide"
  data-start="0"
  data-duration="{duration:.6f}"
  data-width="1920"
  data-height="1080"
  data-no-timeline
>
{''.join(hosts)}
</main>
</body>
</html>
"""
    manifest = {
        "schemaVersion": 1,
        "source": "html-slide",
        "renderer": "hyperframes",
        "fps": fps,
        "width": 1920,
        "height": 1080,
        "durationSeconds": duration,
        "scenes": scenes,
        "compositionFiles": sorted(fragments),
    }
    return index_html, fragments, manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
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
        index_html, fragments, manifest = compile_hyperframes_project(
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
        root = args.out_dir
        root.mkdir(parents=True, exist_ok=True)
        (root / "index.html").write_text(index_html, encoding="utf-8")
        for relative, fragment in fragments.items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(fragment, encoding="utf-8")
        (root / "video.manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            f"Built HyperFrames project {root}: "
            f"{len(manifest['scenes'])} scenes, {manifest['durationSeconds']:.2f}s"
        )
        return 0
    except (ContractError, OSError, ValueError) as exc:
        print(f"HYPERFRAMES PROJECT FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
