#!/usr/bin/env python3
"""Inspect and deterministically rank canonical HTML motion-expression patterns."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from core.motion_patterns import (
    MotionPatternError,
    load_motion_patterns,
    motion_pattern_ids,
    rank_motion_patterns,
    select_motion_pattern,
    validate_pattern_use,
)

def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("catalog")
    search = commands.add_parser("search")
    search.add_argument("--intent", required=True)
    search.add_argument("--target", required=True)
    search.add_argument("--semantic", required=True)
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
                "version": 3,
                "patterns": list(load_motion_patterns().values()),
            }
        else:
            result = rank_motion_patterns(
                intent=args.intent,
                target=args.target,
                semantic_module=args.semantic,
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
