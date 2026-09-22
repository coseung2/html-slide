#!/usr/bin/env python3
"""linter_selftest.py — prove the linter still detects what it claims to.

A rule that stops firing produces a clean report, and a clean report looks
exactly like a deck that passes. This test pins the difference:

  tests/fixtures/broken-deck.html   every violation, deliberate and commented
  examples/reference-3slides.html   the passing baseline

If a check silently breaks (a regex narrows, a guard swallows the finding, a
refactor drops a call), the fixture's expected code disappears from the report
and this test fails. The linter's silence is therefore always a decision.

Usage:  python tests/linter_selftest.py
Exit:   0 all expectations met, 1 something regressed, 2 could not run.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable or "python3"


def run(path: Path) -> tuple[int, str]:
    p = subprocess.run(
        [PY, str(ROOT / "tools" / "slide_lint.py"), str(path)],
        capture_output=True, text=True, cwd=ROOT)
    return p.returncode, p.stdout + p.stderr


def codes(out: str) -> set[str]:
    return set(re.findall(r"\[(?:error|warn )\] ([a-z-]+)", out))


# Each entry: a rule code that the fixture is built to trigger, and the reason
# it matters. Removing the offending construct from the fixture must break this.
EXPECTED = {
    "layout-animation":   "`transition: top` is the mechanism by which emphasis drifts",
    "transition-all":      "`transition: all` silently includes layout properties",
    "scale-zero":         "nothing in the real world appears from nothing",
    "hardcoded-highlight": "a highlight drawn at slide coordinates cannot follow its target",
    "unbound-highlight":  "emphasis must point at a target that exists",
    "emphasis-undefined": "declared emphasis with no effect is a claim with no evidence",
    "external-font":      "a CDN font breaks every verified alignment offline",
    "keep-all":           "Korean body copy splits mid-word without it",
    "overflow":           "content outside the stage is cropped on a projector",
    "bottom-caption":     "the caption rule is a hard rule, not a preference",
    "min-font":           "text below the projection floor is unreadable from the back",
    "title-size":         "an oversized title takes the scene from the example",
    "large-gap":          "objects read together must not sit 80px+ apart",
    "copy-visual-gap":    "the example must sit physically near what explains it",
    "letter-spacing":     "letter-spacing on Hangul separates the jamo",
    "forbidden-pattern":  "pill chips and leader lines are hard rules",
}

# Rules the fixture cannot express as pure markup, kept here so the gap is
# recorded rather than forgotten.
LIVE_ONLY = {
    "binding-drift":  "needs a real resize → tests/motion_check.py `bound`",
    "baseline-mismatch": "needs measured boxes → motion_check/linter browser pass",
    "contrast":       "needs computed colours from a rendered frame",
    "text-offcenter": "needs measured text boxes",
}


def main() -> int:
    fixture = ROOT / "tests" / "fixtures" / "broken-deck.html"
    baseline = ROOT / "examples" / "reference-3slides.html"
    for p in (fixture, baseline):
        if not p.exists():
            print(f"cannot run: missing {p}")
            return 2

    rc_f, out_f = run(fixture)
    rc_b, out_b = run(baseline)
    found = codes(out_f)
    found_b = codes(out_b)

    print(f"fixture  rc={rc_f}  {len(found)} distinct codes")
    print(f"baseline rc={rc_b}  {len(found_b)} distinct codes")

    failures: list[str] = []

    # 1. The fixture must fail, loudly.
    if rc_f == 0:
        failures.append("fixture passed — the linter has gone blind")
    errors = len(re.findall(r"\[error\]", out_f))
    if errors < 5:
        failures.append(f"fixture produced only {errors} errors; expected ≥5")

    # 2. Every rule the fixture exists to exercise must still fire.
    for code, why in EXPECTED.items():
        if code not in found:
            failures.append(f"rule stopped firing: {code} — {why}")

    # 3. The passing baseline must stay clean, or the rules have become noise.
    if rc_b != 0 or found_b:
        failures.append(
            f"baseline no longer clean: rc={rc_b} codes={sorted(found_b)}")

    # A prose header mentioning highlight binding must not turn the next
    # ordinary fixed-position rule into a highlight. Actual selectors still fail.
    sys.path.insert(0, str(ROOT / "tools"))
    from slide_lint import Report, static_checks
    cases = [
        ("comment-before-chrome", "/* highlight binding */ .deck-shell {position:fixed;bottom:12px}", False),
        ("real-highlight-after-comment", "/* presenter chrome */ .hl {position:absolute;left:412px;top:268px}", True),
        ("commented-coordinates", ".hl {position:relative;inset:0;/* left:412px */}", False),
    ]
    with tempfile.TemporaryDirectory(prefix="slide-lint-comments-") as tmp:
        for name, css, expected in cases:
            path = Path(tmp) / (name + ".html")
            path.write_text("<!doctype html><style>" + css + "</style><p>Sample</p>", encoding="utf-8")
            report = Report(path=str(path))
            static_checks(path, report)
            found_hardcoded = any(f.code == "hardcoded-highlight" for f in report.findings)
            if found_hardcoded != expected:
                failures.append("CSS comment regression: " + name)
    print("CSS comment regressions: 3 checked")

    # A stepped deck must bind meaningful beats to phase state, not to the
    # moment a slide receives .is-active.
    autoplay_cases = [
        ("stepped-autoplay",
         '<style>.deck-live .slide.is-active .metric{animation:pop .4s both}'
         '@keyframes pop{from{opacity:.2}to{opacity:1}}</style>'
         '<section class="slide" data-slide data-step="1"><b class="metric">1</b></section>',
         True),
        ("stepped-phase",
         '<style>.deck-live .slide.deck-step-1 .metric{animation:pop .4s both}'
         '@keyframes pop{from{opacity:.2}to{opacity:1}}</style>'
         '<section class="slide" data-slide data-step="1"><b class="metric">1</b></section>',
         False),
        ("legacy-autoplay",
         '<style>.deck-live .slide.is-active .metric{animation:pop .4s both}'
         '@keyframes pop{from{opacity:.2}to{opacity:1}}</style>'
         '<section class="slide" data-slide><b class="metric">1</b></section>',
         False),
    ]
    with tempfile.TemporaryDirectory(prefix="slide-lint-autoplay-") as tmp:
        for name, source, expected in autoplay_cases:
            path = Path(tmp) / (name + ".html")
            path.write_text("<!doctype html>" + source, encoding="utf-8")
            report = Report(path=str(path))
            static_checks(path, report)
            found_autoplay = any(f.code == "slide-entry-autoplay"
                                 for f in report.findings)
            if found_autoplay != expected:
                failures.append("autoplay contract regression: " + name)
    print("autoplay contract regressions: 3 checked")

    if failures:
        print("\nFAIL")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("\nPASS")
    print(f"  fixture triggers {len(found)} codes, "
          f"{errors} errors; baseline 0 errors, 0 warnings")
    print(f"  unchecked by static markup alone: {', '.join(sorted(LIVE_ONLY))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
