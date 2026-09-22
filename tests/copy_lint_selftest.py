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

    natural = lint_text('<html lang="ko"><body><h1>프로젝트 현재 상태</h1><p>다음 단계에서 달라지는 점</p></body></html>')
    check("natural Korean passes", natural["errors"] == 0 and natural["warnings"] == 0)

    template = lint_text('<html lang="ko"><body><h1>KEY TAKEAWAYS</h1><p>핵심 변화</p></body></html>')
    check("template English is rejected", any(f["code"] == "copy-template-english" for f in template["findings"]))

    heavy = lint_text('<html lang="ko"><body><h1>Product Strategy Review Framework</h1><p>검토 기준</p></body></html>')
    check("English-heavy heading is rejected", any(f["code"] == "copy-english-heavy" for f in heavy["findings"]))

    allowed = lint_text('<html lang="ko"><body><h1>다음 단계</h1><p data-copy-en-ok>OpenAI API</p></body></html>')
    check("reviewed English exception passes", allowed["errors"] == 0)

    abbrev = lint_text('<html lang="ko"><body><h1>AI UI 검토</h1><p>API, HTML, UX</p></body></html>')
    check("compact abbreviations pass", abbrev["errors"] == 0)

    prohibited = lint_text('<html lang="ko"><body><h1>물가 · 고용 — 전망</h1><p>3–8월</p></body></html>')
    check("middle dot and long dashes are rejected", sum(f["code"] == "copy-prohibited-punctuation" for f in prohibited["findings"]) == 3)

    punct_exception = lint_text('<html lang="ko"><body><p data-copy-en-ok>OpenAI · API</p></body></html>')
    check("English exception cannot bypass punctuation rule", any(f["code"] == "copy-prohibited-punctuation" for f in punct_exception["findings"]))

    tilde_range = lint_text('<html lang="ko"><body><h1>물가와 고용 전망</h1><p>3~8월</p></body></html>')
    check("tilde numeric range passes", tilde_range["errors"] == 0)

    boundary = lint_text('<html lang="ko"><body><h1>SUMMARYCARD 구성</h1><p>요약 카드</p></body></html>')
    check("template token uses word boundaries", not any(f["code"] == "copy-template-english" for f in boundary["findings"]))

    missing_lang = lint_text('<html><body><h1>현재 상태와 다음 단계에서 달라지는 핵심 정리</h1></body></html>')
    check("missing Korean lang is warned", any(f["code"] == "copy-lang" for f in missing_lang["findings"]))

    body_caveat = lint_text('<html lang="ko"><body><p class="body">고용은 크게 늘었다. 다만 8월 수치는 잠정치다.</p><div class="asterisk">8월 잠정치.</div></body></html>')
    check("release-status caveat is rejected in main body", any(f["code"] == "copy-body-release-caveat" for f in body_caveat["findings"]))

    footnote_caveat = lint_text('<html lang="ko"><body><p class="body">고용은 크게 늘었다.</p><div class="asterisk">8월 잠정치.</div></body></html>')
    check("release-status caveat is allowed in footnote", footnote_caveat["errors"] == 0)

    caveat_exception = lint_text('<html lang="ko"><body><p class="body" data-copy-caveat-ok>잠정치와 확정치의 차이를 비교한다.</p></body></html>')
    check("reviewed caveat exception passes", caveat_exception["errors"] == 0)

    english = lint_text('<html lang="en"><body><h1>Product Strategy Review Framework</h1></body></html>')
    check("English deck is not policed", english["errors"] == 0 and not english["koreanMode"])

    passed = sum(ok for _, ok in checks)
    print(f"copy lint self-test: {passed}/{len(checks)} passed")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
