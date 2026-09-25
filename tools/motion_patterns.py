#!/usr/bin/env python3
"""Inspect and deterministically rank cross-renderer motion-expression patterns."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "video" / "motion-patterns.json"
INTENSITY_ORDER = {"low": 0, "medium": 1, "high": 2}
RENDER_STATUS = {"supported", "limited", "unsupported"}
COMPLEXITY = {"light", "medium", "heavy"}


class MotionPatternError(ValueError):
    """The motion-pattern catalog or selection request violates its contract."""


def _strings(value: Any, field: str, pattern_id: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise MotionPatternError(f"{pattern_id}.{field} must be a non-empty array")
    if any(not isinstance(item, str) or not item for item in value):
        raise MotionPatternError(f"{pattern_id}.{field} must contain non-empty strings")
    if len(value) != len(set(value)):
        raise MotionPatternError(f"{pattern_id}.{field} contains duplicates")
    return value


def load_motion_patterns(path: str | Path = CATALOG) -> dict[str, dict[str, Any]]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MotionPatternError(f"cannot read motion pattern catalog: {exc}") from exc
    if payload.get("version") != 2:
        raise MotionPatternError("motion pattern catalog version must be 2")
    raw = payload.get("patterns")
    if not isinstance(raw, list) or not raw:
        raise MotionPatternError("motion pattern catalog must contain patterns")

    patterns: dict[str, dict[str, Any]] = {}
    for item in raw:
        if not isinstance(item, dict):
            raise MotionPatternError("each motion pattern must be an object")
        pattern_id = item.get("id")
        if not isinstance(pattern_id, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", pattern_id):
            raise MotionPatternError("motion pattern id must be kebab-case")
        if pattern_id in patterns:
            raise MotionPatternError(f"duplicate motion pattern id: {pattern_id}")
        if not isinstance(item.get("label"), str) or not item["label"]:
            raise MotionPatternError(f"{pattern_id}.label is required")
        if not isinstance(item.get("category"), str) or not item["category"]:
            raise MotionPatternError(f"{pattern_id}.category is required")
        for renderer in ("html", "remotion"):
            if item.get(renderer) not in RENDER_STATUS:
                raise MotionPatternError(
                    f"{pattern_id}.{renderer} must be one of {sorted(RENDER_STATUS)}"
                )
        _strings(item.get("semanticModules"), "semanticModules", pattern_id)
        _strings(item.get("targets"), "targets", pattern_id)
        _strings(item.get("intents"), "intents", pattern_id)
        _strings(item.get("tones"), "tones", pattern_id)
        _strings(item.get("tags"), "tags", pattern_id)
        _strings(item.get("conflicts"), "conflicts", pattern_id, allow_empty=True)
        if item.get("intensity") not in INTENSITY_ORDER:
            raise MotionPatternError(f"{pattern_id}.intensity must be low, medium or high")
        if not isinstance(item.get("denseSafe"), bool):
            raise MotionPatternError(f"{pattern_id}.denseSafe must be boolean")
        if item.get("complexity") not in COMPLEXITY:
            raise MotionPatternError(f"{pattern_id}.complexity must be light, medium or heavy")
        if not isinstance(item.get("description"), str) or not item["description"]:
            raise MotionPatternError(f"{pattern_id}.description is required")
        patterns[pattern_id] = item

    ids = set(patterns)
    for pattern_id, item in patterns.items():
        unknown = set(item["conflicts"]) - ids
        if unknown:
            raise MotionPatternError(
                f"{pattern_id}.conflicts references unknown patterns: {', '.join(sorted(unknown))}"
            )
        if pattern_id in item["conflicts"]:
            raise MotionPatternError(f"{pattern_id} may not conflict with itself")
    for pattern_id, item in patterns.items():
        for other in item["conflicts"]:
            if pattern_id not in patterns[other]["conflicts"]:
                raise MotionPatternError(
                    f"conflict must be symmetric: {pattern_id} <-> {other}"
                )
    return patterns


def motion_pattern_ids(path: str | Path = CATALOG) -> set[str]:
    return set(load_motion_patterns(path))


def _terms(*values: str) -> set[str]:
    return set(re.findall(r"[\w-]+", " ".join(values).lower()))


def _compatible(
    item: dict[str, Any],
    *,
    target: str,
    semantic_module: str,
    renderer: str,
    selected: Iterable[str],
    patterns: dict[str, dict[str, Any]],
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    status = item.get(renderer)
    if status not in ("supported", "limited"):
        return False, [f"{renderer} renderer unsupported"]
    if target not in item["targets"]:
        return False, [f"target {target} unsupported"]
    if semantic_module not in item["semanticModules"]:
        return False, [f"semantic module {semantic_module} unsupported"]
    selected_ids = set(selected)
    selected_items = [patterns[pattern_id] for pattern_id in selected_ids if pattern_id in patterns]
    if item["intensity"] == "high" and any(
        other["intensity"] == "high" for other in selected_items
    ):
        return False, ["only one high-intensity pattern is allowed per scene"]
    if item["complexity"] == "heavy" and any(
        other["complexity"] == "heavy" for other in selected_items
    ):
        return False, ["only one heavy-complexity pattern is allowed per scene"]
    conflicts = selected_ids.intersection(set(item["conflicts"]))
    if conflicts:
        return False, ["conflicts with " + ", ".join(sorted(conflicts))]
    for other in selected_ids:
        if other in patterns and item["id"] in patterns[other]["conflicts"]:
            return False, [f"conflicts with {other}"]
    reasons.append(f"{renderer} {status}")
    reasons.append(f"target {target}")
    reasons.append(f"semantic {semantic_module}")
    return True, reasons


def rank_motion_patterns(
    *,
    intent: str,
    target: str,
    semantic_module: str,
    renderer: str = "remotion",
    tones: Iterable[str] = (),
    intensity: str = "medium",
    density: str = "medium",
    topic: str = "",
    selected: Iterable[str] = (),
    recent: Iterable[str] = (),
    path: str | Path = CATALOG,
) -> list[dict[str, Any]]:
    if renderer not in ("html", "remotion"):
        raise MotionPatternError("renderer must be html or remotion")
    if intensity not in INTENSITY_ORDER:
        raise MotionPatternError("intensity must be low, medium or high")
    if density not in ("low", "medium", "high"):
        raise MotionPatternError("density must be low, medium or high")

    patterns = load_motion_patterns(path)
    tone_set = {value.lower() for value in tones if value}
    topic_terms = _terms(topic)
    recent_ids = list(recent)
    results: list[dict[str, Any]] = []
    for item in patterns.values():
        ok, reasons = _compatible(
            item,
            target=target,
            semantic_module=semantic_module,
            renderer=renderer,
            selected=selected,
            patterns=patterns,
        )
        if not ok:
            continue
        score = 100
        warnings: list[str] = []

        if intent in item["intents"]:
            score += 32
            reasons.append("intent match")
        else:
            score -= 12
            reasons.append("intent fallback")

        tone_hits = tone_set.intersection(set(item["tones"]))
        if tone_hits:
            score += 14 * len(tone_hits)
            reasons.append("tone: " + ", ".join(sorted(tone_hits)))

        requested_level = INTENSITY_ORDER[intensity]
        candidate_level = INTENSITY_ORDER[item["intensity"]]
        delta = abs(requested_level - candidate_level)
        if delta == 0:
            score += 18
            reasons.append("intensity match")
        elif delta == 1:
            score += 6
            reasons.append("nearby intensity")
        else:
            score -= 8
            reasons.append("intensity mismatch")

        tag_hits = topic_terms.intersection(set(item["tags"]))
        if tag_hits:
            score += 7 * len(tag_hits)
            reasons.append("tags: " + ", ".join(sorted(tag_hits)))

        if density == "high":
            if item["denseSafe"]:
                score += 10
                reasons.append("dense-safe")
            else:
                score -= 24
                warnings.append("not recommended for high-density scenes")
        elif density == "low" and item["complexity"] == "heavy":
            score += 4
            reasons.append("space for complex expression")

        status = item[renderer]
        if status == "supported":
            score += 8
        else:
            score -= 14
            warnings.append(f"{renderer} support is limited")

        if recent_ids:
            if item["id"] == recent_ids[-1]:
                score -= 28
                reasons.append("exact repetition penalty")
            recent_categories = [
                patterns[r]["category"] for r in recent_ids[-2:] if r in patterns
            ]
            if item["category"] in recent_categories:
                score -= 12
                reasons.append("recent category penalty")

        results.append(
            {
                "id": item["id"],
                "label": item["label"],
                "category": item["category"],
                "score": score,
                "intensity": item["intensity"],
                "complexity": item["complexity"],
                "reasons": reasons,
                "warnings": warnings,
            }
        )
    return sorted(results, key=lambda row: (-row["score"], row["id"]))


def select_motion_pattern(**kwargs: Any) -> dict[str, Any]:
    ranked = rank_motion_patterns(**kwargs)
    if not ranked:
        raise MotionPatternError(
            "no compatible motion pattern for the target, semantic module and conflicts"
        )
    return ranked[0]


def validate_pattern_use(
    pattern_id: str,
    *,
    target: str,
    semantic_module: str,
    renderer: str = "remotion",
    selected: Iterable[str] = (),
    path: str | Path = CATALOG,
) -> None:
    patterns = load_motion_patterns(path)
    try:
        item = patterns[pattern_id]
    except KeyError as exc:
        raise MotionPatternError(f"unknown motion pattern: {pattern_id}") from exc
    ok, reasons = _compatible(
        item,
        target=target,
        semantic_module=semantic_module,
        renderer=renderer,
        selected=selected,
        patterns=patterns,
    )
    if not ok:
        raise MotionPatternError(f"{pattern_id}: {reasons[0]}")


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("catalog")
    search = commands.add_parser("search")
    search.add_argument("--intent", required=True)
    search.add_argument("--target", required=True)
    search.add_argument("--semantic", required=True)
    search.add_argument("--renderer", choices=["html", "remotion"], default="remotion")
    search.add_argument("--tone", action="append", default=[])
    search.add_argument("--intensity", choices=["low", "medium", "high"], default="medium")
    search.add_argument("--density", choices=["low", "medium", "high"], default="medium")
    search.add_argument("--topic", default="")
    search.add_argument("--with-pattern", action="append", default=[])
    search.add_argument("--recent", action="append", default=[])
    search.add_argument("--limit", type=int, default=8)
    args = parser.parse_args(argv)

    try:
        if args.command == "catalog":
            result = {
                "version": 2,
                "patterns": list(load_motion_patterns().values()),
            }
        else:
            result = rank_motion_patterns(
                intent=args.intent,
                target=args.target,
                semantic_module=args.semantic,
                renderer=args.renderer,
                tones=args.tone,
                intensity=args.intensity,
                density=args.density,
                topic=args.topic,
                selected=args.with_pattern,
                recent=args.recent,
            )[: max(1, args.limit)]
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (MotionPatternError, OSError, ValueError) as exc:
        print(f"MOTION PATTERN FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(_cli())
