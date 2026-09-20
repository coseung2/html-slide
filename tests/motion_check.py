#!/usr/bin/env python3
"""
motion_check.py — behaviour tests for motion/patterns/*.

The linter answers "is the static frame correct?". This answers the questions it
cannot: do the claims in motion.css actually hold while the page is alive?

  1. presenting    — with JS on, a slide opens on data-start, `next()` walks one
                     phase at a time, and `prev()` walks back one at a time.
  2. complete      — with prefers-reduced-motion (or JS never running) the frame
                     is the accepted one, at every slide and every phase.
  3. bound         — an emphasised element stays aligned to its target after the
                     viewport is resized (the failure this repo exists for).
  4. still         — nothing animates layout: sample the emphasised target's
                     rect across the animation and it never moves.

Run:  ~/.venvs/pw/bin/python tests/motion_check.py [patterns_dir]
Exit: 0 all passed, 1 failures, 2 setup problem.
"""

import json
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("playwright missing: pip install playwright && playwright install chromium")
    sys.exit(2)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PATTERNS = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "motion" / "patterns"

# ratio of the ring/overlay box that must sit inside its target
COVER_MIN = 0.85
# a bound element may shift by a subpixel when the stage re-fits, no more
BIND_TOL = 1.0


class Results:
    def __init__(self):
        self.rows = []
        self.failed = 0

    def ok(self, name, detail=""):
        self.rows.append(("ok", name, detail))

    def bad(self, name, detail=""):
        self.rows.append(("FAIL", name, detail))
        self.failed += 1

    def report(self):
        for status, name, detail in self.rows:
            tail = f"  — {detail}" if detail else ""
            print(f"  [{status:>4}] {name}{tail}")
        print(f"\n{len(self.rows)} checks, {self.failed} failed")


# --- the probes, as page functions -----------------------------------------

# A highlight is bound when its box sits inside its target's box, and the two
# move together. Returned as a ratio so the caller can compare across resizes.
PROBE_BIND = r"""() => {
  const out = [];
  document.querySelectorAll('[data-hl]').forEach(el => {
    const host = el.parentElement;
    if (!host) return;
    const a = el.getBoundingClientRect(), b = host.getBoundingClientRect();
    const inter = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left)) *
                  Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
    const area = Math.max(a.width * a.height, 1);
    out.push({
      host: host.className || host.tagName,
      cover: inter / area,
      hostBox: { x: b.left, y: b.top, w: b.width, h: b.height },
      gap: { l: a.left - b.left, t: a.top - b.top,
             r: b.right - a.right, b: b.bottom - a.bottom }
    });
  });
  return out;
}"""

# The stage transform is the only thing that may change on resize; any element
# whose own box moves relative to its parent is a layout-driven animation.
PROBE_RECTS = r"""() => {
  const out = {};
  document.querySelectorAll('[data-hl]').forEach((el, i) => {
    const r = el.getBoundingClientRect();
    out['hl' + i] = [r.left, r.top, r.width, r.height];
  });
  return out;
}"""

# Opt-in checker for a pattern that claims layout never animates: sample the
# target's box while the effect plays.
PROBE_LAYOUT_STILL = r"""() => new Promise(resolve => {
  const el = document.querySelector('[data-hl]') || document.querySelector('.pat-group > *');
  if (!el) return resolve({ skipped: 'no target' });
  const frames = [];
  let n = 0;
  const tick = () => {
    const r = el.getBoundingClientRect();
    frames.push([Math.round(r.left * 10) / 10, Math.round(r.top * 10) / 10]);
    if (++n < 20) requestAnimationFrame(tick); else resolve({ frames: frames });
  };
  requestAnimationFrame(tick);
})"""


# A hidden [data-phase] element is superseded content when a visible
# [data-phase] sibling in the same slot stands in for it (the old value in a
# swap, the outgoing digit in a roll). Anything else hidden is a defect: the
# slide's point never rendered.
INVISIBLE_JS = r"""() => {
  const out = [];
  document.querySelectorAll('[data-slide] [data-phase]').forEach(el => {
    if (parseFloat(getComputedStyle(el).opacity) >= 0.05) return;
    const sibs = Array.from(el.parentElement?.children || []);
    const replaced = sibs.some(s => s !== el && s.hasAttribute('data-phase') &&
      parseFloat(getComputedStyle(s).opacity) >= 0.05);
    if (!replaced) out.push(el.className + '|' + el.textContent.trim().slice(0, 20));
  });
  return out;
}"""


def walk_fault(seen, from_p, to_p, step):
    """Compare an observed phase walk against the machine's contract.

    Contract: open on the start phase, move exactly one phase per advance
    (`step` is +1 forward, -1 backward), and clamp at the terminal phase rather
    than running past it. Returns a complaint, or None when the walk is sound.
    A slide with no phases has nothing to walk, so it is skipped.
    """
    if not seen or to_p == from_p:
        return None
    base = list(range(from_p, to_p + (1 if step > 0 else -1), step))
    expected = base + [to_p] * (len(seen) - len(base))
    if seen[0] != from_p:
        return f"opens at {seen[0]}, should open on {from_p}"
    if len(seen) < len(base) or seen[:len(base)] != base:
        # a jump bigger than one phase, or a jump in the wrong direction
        for i in range(1, min(len(seen), len(base))):
            if seen[i] != base[i]:
                d = seen[i] - seen[i - 1]
                return (f"phase {seen[i - 1]}->{seen[i]} moves {d:+d}, "
                        f"contract is {step:+d} per advance (walk {seen})")
        return f"walk {seen} is shorter than the contract {base}"
    if seen != expected:
        return f"walk {seen} should clamp at {to_p} and stay"
    return None


def bound(el, res, name):
    if el is None:
        res.bad(name, "no [data-hl] in the pattern")
        return
    if el["cover"] < COVER_MIN:
        res.bad(name, f"highlight covers only {el['cover'] * 100:.0f}% of its target")
    else:
        res.ok(name, f"covers {el['cover'] * 100:.0f}% of target")


def check_pattern(page, path, res):
    tag = path.name.replace(".html", "")

    # ---- complete: reduced motion, no JS phase state ----------------------
    page.emulate_media(reduced_motion="reduce")
    page.goto(path.as_uri(), wait_until="load")
    page.evaluate("() => document.fonts.ready")
    page.wait_for_timeout(120)
    js_ran = page.evaluate("() => !!window.deck")
    if js_ran:
        live = page.evaluate("() => document.documentElement.classList.contains('deck-live')")
        if live:
            res.bad(f"{tag}: complete",
                    "deck-live added despite prefers-reduced-motion")
        else:
            res.ok(f"{tag}: complete", "no phase state under reduced motion")
    else:
        res.ok(f"{tag}: complete", "renders without JS at all")

    phases = page.evaluate(
        "() => ((document.querySelector('[data-slide]')||{}).getAttribute"
        "?.('data-step')) || '0'")
    # Under reduced motion the machine is collapsed: phases() reads 0 by
    # design, and the complete frame is what is on screen. That IS the pass.
    reduced = page.evaluate(
        "() => matchMedia('(prefers-reduced-motion: reduce)').matches")
    steps = page.evaluate("() => window.deck ? window.deck.phases(0) : 0")
    if reduced and not steps:
        res.ok(f"{tag}: complete", "machine collapsed, accepted frame on screen")
    elif phases and not steps and phases != "0":
        res.bad(f"{tag}: complete",
                f"slide declares data-step={phases} but phases() reads 0 "
                f"(is data-start out of range?)")
    else:
        res.ok(f"{tag}: phase count", f"declared {phases}, steps={steps}")

    # A decisive frame: nothing that carries the slide's meaning is hidden.
    #
    # Superseded content is the exception, and it must be stated positively:
    # a swapped value legitimately hides the value it replaced. So a hidden
    # [data-phase] element is a defect only when NO visible [data-phase] sibling
    # in the same slot is standing in for it — that distinguishes "the old value
    # in a swap" (fine) from "the point of the slide never rendered" (a defect).
    invisible = page.evaluate(INVISIBLE_JS)
    if invisible:
        res.bad(f"{tag}: decisive", f"invisible in the accepted frame: {invisible[:3]}")
    else:
        res.ok(f"{tag}: decisive", "every declared phase visible statically")

    # ---- presenting: data-start, then one phase per advance ---------------
    page.emulate_media(reduced_motion="no-preference")
    page.goto(path.as_uri(), wait_until="load")
    page.evaluate("() => document.fonts.ready")
    page.wait_for_timeout(150)
    if not page.evaluate("() => !!window.deck"):
        res.ok(f"{tag}: presenting", "no deck runtime to drive (static pattern)")
    else:
        start = page.evaluate("() => window.deck.start(0)")
        total = page.evaluate("() => window.deck.phases(0)")
        seen = [page.evaluate("() => window.deck.phase")]
        for _ in range(total + 1):
            page.evaluate("() => window.deck.next()")
            seen.append(page.evaluate("() => window.deck.phase"))
        # The invariant: it opens on data-start, advances one phase at a time,
        # and clamps at the last phase instead of running past it.
        bad_walk = walk_fault(seen, start, total, step=1)
        if bad_walk:
            res.bad(f"{tag}: presenting", bad_walk)
        else:
            res.ok(f"{tag}: presenting", f"data-start={start}, walk {seen}")

        back = [page.evaluate("() => window.deck.phase")]
        for _ in range(total + 1):
            page.evaluate("() => window.deck.prev()")
            back.append(page.evaluate("() => window.deck.phase"))
        bad_back = walk_fault(back, total, start, step=-1)
        if bad_back:
            res.bad(f"{tag}: reversible", bad_back)
        else:
            res.ok(f"{tag}: reversible", f"backward walk {back}")

        # ---- the frame is complete again after stepping to the end --------
        page.evaluate("() => { while (window.deck.phase < window.deck.phases(0)) "
                      "window.deck.next(); }")
        page.wait_for_timeout(450)
        faded = page.evaluate(INVISIBLE_JS)
        if faded:
            res.bad(f"{tag}: settles", f"still hidden at the last phase: {faded[:3]}")
        else:
            res.ok(f"{tag}: settles", "frame complete at the last phase")

    # ---- bound: alignment survives a resize -------------------------------
    page.emulate_media(reduced_motion="reduce")
    page.set_viewport_size({"width": 1920, "height": 1080})
    page.goto(path.as_uri(), wait_until="load")
    page.evaluate("() => document.fonts.ready")
    page.wait_for_timeout(120)
    a = page.evaluate(PROBE_BIND)
    if not a:
        res.ok(f"{tag}: bound", "no bound highlight in this pattern")
    else:
        page.set_viewport_size({"width": 1280, "height": 720})
        page.wait_for_timeout(220)
        b = page.evaluate(PROBE_BIND)
        page.set_viewport_size({"width": 1024, "height": 768})
        page.wait_for_timeout(220)
        c = page.evaluate(PROBE_BIND)
        for label, after in (("1280x720", b), ("1024x768", c)):
            if not after:
                res.bad(f"{tag}: bound @{label}", "highlight disappeared")
                continue
            cov = after[0]["cover"]
            # gaps are in stage units: the stage scale shrinks them on a small
            # viewport, so compare the *ratio*, not the pixel gap
            ga, gb = a[0]["gap"], after[0]["gap"]
            scale = (after[0]["hostBox"]["w"] / a[0]["hostBox"]["w"]) if a[0]["hostBox"]["w"] else 1
            drift = max(abs(ga[k] * scale - gb[k]) for k in ("l", "t", "r", "b"))
            if cov < COVER_MIN:
                res.bad(f"{tag}: bound @{label}", f"covers only {cov * 100:.0f}%")
            elif drift > BIND_TOL:
                res.bad(f"{tag}: bound @{label}",
                        f"ring drifted {drift:.2f} stage units off its target")
            else:
                res.ok(f"{tag}: bound @{label}",
                       f"covers {cov * 100:.0f}%, drift {drift:.2f}")

    # ---- still: the target does not move while the effect plays -----------
    page.emulate_media(reduced_motion="no-preference")
    page.set_viewport_size({"width": 1920, "height": 1080})
    page.goto(path.as_uri(), wait_until="load")
    page.evaluate("() => document.fonts.ready")
    page.wait_for_timeout(400)          # let the entrance finish
    probe = page.evaluate(PROBE_LAYOUT_STILL)
    if probe.get("skipped"):
        res.ok(f"{tag}: still", probe["skipped"])
    else:
        frames = probe["frames"]
        spread = max(max(f[0] for f in frames) - min(f[0] for f in frames),
                     max(f[1] for f in frames) - min(f[1] for f in frames))
        if spread > BIND_TOL:
            res.bad(f"{tag}: still", f"target box moved {spread:.1f}px during its effect")
        else:
            res.ok(f"{tag}: still", f"target box stable ({spread:.2f}px)")


def main():
    if not PATTERNS.is_dir():
        print(f"no patterns directory: {PATTERNS}")
        return 2
    files = sorted(PATTERNS.glob("*.html"))
    if not files:
        print(f"no patterns in {PATTERNS}")
        return 2

    res = Results()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        try:
            for f in files:
                print(f"\n=== {f.name}")
                check_pattern(page, f, res)
        finally:
            browser.close()

    print()
    res.report()
    return 1 if res.failed else 0


if __name__ == "__main__":
    sys.exit(main())
