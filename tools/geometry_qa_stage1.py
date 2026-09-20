#!/usr/bin/env python3
"""deck_geometry_qa.py — measure an HTML slide deck instead of eyeballing it.

Reports, in a real browser at a fixed viewport (default 1920x1080):

  overflow   content-bearing elements extending outside the slide box
  anchor     the anchoring proof: jiggle the target and confirm the emphasis
             overlay's delta AND its offsets are unchanged

Usage:
  python3 deck_geometry_qa.py deck.html
  python3 deck_geometry_qa.py deck.html --slide-index 2 \
      --target "[data-id=probe]" --overlay ".mark"

Requires: pip install playwright && playwright install chromium
Exit codes: 0 clean, 1 violations found, 2 could not measure.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

DEFAULT_SLIDE = ".slide, .reveal .slides > section, section.slide, .deck > section, body"
TOL = 0.5

MEASURE_JS = r"""
(sel) => {
  const out = [];
  document.querySelectorAll(sel).forEach((el, i) => {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || parseFloat(cs.opacity) === 0) return;
    const txt = (el.innerText || '').trim();
    out.push({
      i, tag: el.tagName.toLowerCase(),
      cls: String(el.className || '').slice(0, 60),
      text: txt.slice(0, 40), hasText: txt.length > 0,
      x: +r.x.toFixed(1), y: +r.y.toFixed(1),
      w: +r.width.toFixed(1), h: +r.height.toFixed(1)
    });
  });
  return out;
}
"""

# One evaluate so the jiggle and both reads share a single layout batch.
DRIFT_JS = r"""
([tsel, osel, dx, dy]) => {
  const t = document.querySelector(tsel), o = document.querySelector(osel);
  if (!t || !o) return { error: 'target or overlay selector not found' };
  const gap = (tr, or) => ({
    l: +(or.left - tr.left).toFixed(2), t: +(or.top - tr.top).toFixed(2),
    r: +(tr.right - or.right).toFixed(2), b: +(tr.bottom - or.bottom).toFixed(2),
    w: +(or.width - tr.width).toFixed(2), h: +(or.height - tr.height).toFixed(2)
  });
  const tr0 = t.getBoundingClientRect(), or0 = o.getBoundingClientRect();
  const before = gap(tr0, or0);
  const prev = t.style.transform;
  t.style.transform = `translate(${dx}px, ${dy}px)`;
  const tr1 = t.getBoundingClientRect(), or1 = o.getBoundingClientRect();
  t.style.transform = prev;
  return {
    target: { dx: +(tr1.left - tr0.left).toFixed(2), dy: +(tr1.top - tr0.top).toFixed(2) },
    overlay: { dx: +(or1.left - or0.left).toFixed(2), dy: +(or1.top - or0.top).toFixed(2) },
    gap_before: before, gap_after: gap(tr1, or1)
  };
}
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("deck", type=Path)
    ap.add_argument("--slide", default=DEFAULT_SLIDE, help="selector matching one slide")
    ap.add_argument("--slide-index", type=int, default=0, help="press ArrowRight N times first")
    ap.add_argument("--viewport", default="1920x1080")
    ap.add_argument("--target", help="element to jiggle (the thing being highlighted)")
    ap.add_argument("--overlay", help="emphasis layer that must follow it")
    ap.add_argument("--dx", type=float, default=31.0)
    ap.add_argument("--dy", type=float, default=23.0)
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright missing: pip install playwright && playwright install chromium")
        return 2

    if not args.deck.exists():
        print(f"no such file: {args.deck}")
        return 2

    w, _, h = args.viewport.partition("x")
    violations: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": int(w), "height": int(h)})
        page.goto(args.deck.resolve().as_uri())
        page.wait_for_load_state("load")
        # Web-font swap reflows text; measure only after it settles.
        page.evaluate("() => document.fonts.ready.then(() => true)")
        for _ in range(args.slide_index):
            page.keyboard.press("ArrowRight")
            page.wait_for_timeout(320)

        box = page.evaluate(
            """(sel) => { const el = document.querySelector(sel); if (!el) return null;
                 const r = el.getBoundingClientRect();
                 return { x: r.x, y: r.y, w: r.width, h: r.height }; }""",
            args.slide,
        )
        if not box:
            print(f"no slide matched: {args.slide}")
            return 2

        elems = page.evaluate(MEASURE_JS, args.slide)
        overflow = [
            e for e in elems
            if e["hasText"] and (
                e["x"] < box["x"] - 1 or e["y"] < box["y"] - 1
                or e["x"] + e["w"] > box["x"] + box["w"] + 1
                or e["y"] + e["h"] > box["y"] + box["h"] + 1
            )
        ]
        print(f"slide box: {box['w']:.0f}x{box['h']:.0f} at ({box['x']:.0f},{box['y']:.0f})")
        print(f"text elements measured: {sum(1 for e in elems if e['hasText'])}")
        if overflow:
            violations.append(f"{len(overflow)} overflowing element(s)")
            for e in overflow:
                print(f"  OVERFLOW <{e['tag']} class=\"{e['cls']}\"> {e['text']!r}")
        else:
            print("  overflow: none")

        if args.target and args.overlay:
            res = page.evaluate(DRIFT_JS, [args.target, args.overlay, args.dx, args.dy])
            if res.get("error"):
                print(f"  anchor: could not measure ({res['error']})")
                return 2
            dd = max(
                abs(res["target"]["dx"] - res["overlay"]["dx"]),
                abs(res["target"]["dy"] - res["overlay"]["dy"]),
            )
            gaps = max(
                abs(res["gap_before"][k] - res["gap_after"][k]) for k in res["gap_before"]
            )
            print(
                f"  anchor: target delta ({res['target']['dx']}, {res['target']['dy']}) "
                f"vs overlay delta ({res['overlay']['dx']}, {res['overlay']['dy']}); "
                f"offset drift {gaps}px"
            )
            if dd <= TOL and gaps <= TOL:
                print("  anchor: PASS — the overlay is anchored to its target")
            else:
                violations.append("overlay is not anchored to its target")
                print("  anchor: FAIL — the overlay does not follow the target")
                print("    fix: make the mark a child of the target (or place it from the")
                print("    target's rect at runtime) and animate only transform/opacity.")
        else:
            print("  anchor: skipped (pass --target and --overlay to run the proof)")

        browser.close()

    print(("FAIL: " + "; ".join(violations)) if violations else "OK: no violations")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
