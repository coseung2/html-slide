#!/usr/bin/env python3
"""Regression tests for the Korean-first copy linter."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from copy_lint import lint_text


def main() -> int:
    checks = []

    def check(name, condition):
        checks.append((name, bool(condition)))
        if not condition:
            print("FAIL:", name)

    natural = lint_text('<html lang="ko"><body><h1>EPL 5라운드 상위권 판도</h1><p>맨시티, 3점 차 단독 선두</p></body></html>')
    check("natural Korean passes", natural["errors"] == 0 and natural["warnings"] == 0)

    template = lint_text('<html lang="ko"><body><h1>TOP SIX MARKET REPORT</h1><p>맨시티 전승</p></body></html>')
    check("template English is rejected", any(f["code"] == "copy-template-english" for f in template["findings"]))

    heavy = lint_text('<html lang="ko"><body><h1>Premier League Power Ranking Update</h1><p>상위권 판도</p></body></html>')
    check("English-heavy heading is rejected", any(f["code"] == "copy-english-heavy" for f in heavy["findings"]))

    allowed = lint_text('<html lang="ko"><body><h1>다음 경기</h1><p data-copy-en-ok>UEFA CHAMPIONS LEAGUE</p></body></html>')
    check("reviewed English exception passes", allowed["errors"] == 0)

    abbrev = lint_text('<html lang="ko"><body><h1>EPL 5라운드</h1><p>MCI 15 · ARS 12 · LIV 9</p></body></html>')
    check("compact abbreviations pass", abbrev["errors"] == 0)

    boundary = lint_text('<html lang="ko"><body><h1>FORMATION 전술</h1><p>포메이션 변화</p></body></html>')
    check("template token uses word boundaries", not any(f["code"] == "copy-template-english" for f in boundary["findings"]))

    missing_lang = lint_text('<html><body><h1>이번 라운드 상위권 판도와 다음 경기 핵심 정리</h1></body></html>')
    check("missing Korean lang is warned", any(f["code"] == "copy-lang" for f in missing_lang["findings"]))

    english = lint_text('<html lang="en"><body><h1>Premier League Power Ranking Update</h1></body></html>')
    check("English deck is not policed", english["errors"] == 0 and not english["koreanMode"])

    passed = sum(ok for _, ok in checks)
    print(f"copy lint self-test: {passed}/{len(checks)} passed")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
