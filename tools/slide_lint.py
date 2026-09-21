#!/usr/bin/env python3
"""
slide_lint.py — verification for AI Commercial Slide Director decks.

Two layers:

  static   regex/AST-free scan of the HTML/CSS. Catches rule violations that are
           visible in source: layout-triggering animation, scale(0), hard-coded
           highlight coordinates, external fonts, missing keep-all, forbidden
           chip/callout patterns. Runs anywhere, no browser needed.

  browser  real Chromium measurement via Playwright. Catches everything the
           source cannot tell you: overflow, clipping, contrast, off-centre text,
           internal gaps, and — the reason this tool exists — whether every
           data-hl highlight is actually bound to its target and stays bound
           when the viewport changes.

Usage:
    python tools/slide_lint.py deck.html --shots out/
    python tools/slide_lint.py deck.html --no-browser
    python tools/slide_lint.py deck.html --json report.json

Exit code 0 = no errors. Warnings do not fail the run.

Markup contract (see SKILL.md §0):
    data-stage      the 1920x1080 stage wrapper
    data-slide      each slide root
    data-copy       copy cluster        data-visual   visual cluster
    data-hl         emphasis element    data-target   selector it emphasizes
    data-step       animation phase     data-bleed    allowed to exceed inset
    data-motion-ok  deliberate exception for a static check
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

# --------------------------------------------------------------------------- #
# finding model
# --------------------------------------------------------------------------- #

ERROR = "error"
WARN = "warn"
INFO = "info"


@dataclass
class Finding:
    code: str
    severity: str
    message: str
    hint: str = ""
    slide: int | None = None
    selector: str = ""
    layer: str = "static"

    def line(self) -> str:
        loc = f"slide {self.slide}" if self.slide is not None else "-"
        sel = f" {self.selector}" if self.selector else ""
        out = f"  [{self.severity:5s}] {self.code:20s} ({loc}) {self.message}{sel}"
        if self.hint:
            out += f"\n          -> {self.hint}"
        return out


@dataclass
class Report:
    path: str
    findings: list[Finding] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def add(self, *args, **kwargs) -> None:
        self.findings.append(Finding(*args, **kwargs))

    def count(self, severity: str) -> int:
        return sum(1 for f in self.findings if f.severity == severity)

    def worst(self) -> int:
        n = self.count(ERROR)
        if n:
            return 2
        return 1 if self.count(WARN) else 0


# --------------------------------------------------------------------------- #
# thresholds (SKILL.md §13)
# --------------------------------------------------------------------------- #

STAGE_W, STAGE_H = 1920, 1080
SAFE_INSET = 0.05          # §2 letterbox/projector safety
BODY_MIN = 28.0            # §13 projection floor
LABEL_MIN = 22.0
TITLE_MAX = 96.0
CONTRAST_BODY = 4.5
CONTRAST_LARGE = 3.0
LARGE_PX = 32.0
GAP_MAX = 80.0             # §4 proximity
GAP_SCENE_MIN = 12.0
LARGE_GAP = 100.0          # §5 title -> huge gap -> body
CENTER_TOL = 2.0           # §6
BASELINE_TOL = 2.0
DRIFT_TOL = 1.5            # stage units
CROWD = 0.40               # ≥40% overlap of the smaller box = overlap
BOTTOM_BAND = 0.06         # §1 no bottom captions

VIEWPORTS = [(1920, 1080), (1280, 720), (1024, 768)]

LAYOUT_PROPS = ("top", "left", "right", "bottom", "width", "height",
                "margin", "padding", "inset")

HIGHLIGHT_RE = re.compile(
    r"(highlight|\bhl\b|hl-|hl_|ring|sweep|mask|dim|trace|zoom|focus|outline|marker)",
    re.I)
PILL_RE = re.compile(r"(\bpill\b|\bchip\b|callout|leader|footnote|"
                     r"\bcaption\b|annotation)", re.I)
ANCHORED_RE = re.compile(r"(popover|tooltip|dropdown|menu|select|badge)", re.I)
TITLE_HINT_RE = re.compile(r"(title|headline|heading|h1|display|thesis|claim)", re.I)
HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")


# --------------------------------------------------------------------------- #
# static layer
# --------------------------------------------------------------------------- #

def _css_and_html(text: str) -> tuple[str, str]:
    """Return (css, html_without_style_blocks)."""
    css_blocks = re.findall(r"<style[^>]*>(.*?)</style>", text, re.S | re.I)
    stripped = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.S | re.I)
    return "\n".join(css_blocks), stripped


def _motion_ok_near(context: str) -> bool:
    return "data-motion-ok" in context


def _linked_css(path: Path, raw: str, seen: set | None = None) -> str:
    """Inline the CSS of local <link rel=stylesheet> hops.

    A deck may keep its stylesheet beside the HTML; without following the link
    the static layer would silently check nothing (and report a false
    missing-keep-all). Remote sheets stay out: the @font-face check is what
    should flag those.
    """
    seen = seen if seen is not None else set()
    out: list[str] = []
    for m in re.finditer(r"<link\b[^>]*>", raw, re.I):
        tag = m.group(0)
        if not re.search(r'rel\s*=\s*["\']?[^"\'>]*stylesheet', tag, re.I):
            continue
        href = re.search(r'href\s*=\s*["\']([^"\']+)["\']', tag)
        if not href:
            continue
        rel = href.group(1)
        if re.match(r"(https?:)?//", rel) or rel.startswith("data:"):
            continue
        target = (path.parent / rel.split("?")[0]).resolve()
        if target in seen or not target.is_file():
            continue
        seen.add(target)
        body = target.read_text(encoding="utf-8", errors="replace")
        out.append(f"\n/* --- linked: {rel} --- */\n{body}")
        # one level of @import / nested links is enough for a deck stylesheet
        out.append(_linked_css(target, body, seen))
    return "".join(out)


def static_checks(path: Path, rep: Report) -> None:
    raw = path.read_text(encoding="utf-8", errors="replace")
    css, html = _css_and_html(raw)
    css += _linked_css(path, raw)

    # --- layout-triggering animation (the root cause of drifting emphasis) ---
    for m in re.finditer(r"transition(?:-property)?\s*:\s*([^;{}]+)", css, re.I):
        decl = m.group(1)
        if re.search(r"(^|[\s,])all($|[\s,])", decl, re.I) and not _motion_ok_near(m.group(0)):
            rep.add("transition-all", ERROR,
                    "transition: all can animate layout properties implicitly",
                    "list only compositor-safe properties explicitly; normally "
                    "transform and opacity (§8)",
                    selector=f"transition: {decl.strip()[:60]}")
            continue
        hit = [p for p in LAYOUT_PROPS if re.search(rf"(^|[\s,]){p}($|[\s,])", decl)]
        if hit and not _motion_ok_near(m.group(0)):
            rep.add("layout-animation", ERROR,
                    f"transition animates layout property: {', '.join(hit)}",
                    "animate transform/opacity instead; layout animation is how "
                    "emphasis drifts off its target (§8)",
                    selector=f"transition: {decl.strip()[:60]}")

    for m in re.finditer(r"@keyframes\s+([\w-]+)\s*\{", css):
        name = m.group(1)
        # brace-aware: a keyframe body contains nested blocks, so a lazy
        # regex would stop at the first inner "}"
        depth, j = 1, m.end()
        while j < len(css) and depth:
            if css[j] == "{":
                depth += 1
            elif css[j] == "}":
                depth -= 1
            j += 1
        body = css[m.end():j - 1]
        hit = [p for p in LAYOUT_PROPS
               if re.search(rf"(^|[\s;{{]){p}\s*:", body)]
        if hit and not _motion_ok_near(body):
            rep.add("layout-animation", ERROR,
                    f"@keyframes {name} animates layout property: {', '.join(hit)}",
                    "animate transform/opacity only (§8)",
                    selector=f"@keyframes {name}")

    # --- nothing appears from nothing ---
    for m in re.finditer(r"scale\(\s*0(?:\.0+)?\s*\)", css + html):
        if not _motion_ok_near(m.group(0)):
            rep.add("scale-zero", ERROR, "scale(0) entrance",
                    "use scale(0.9-0.97) + opacity: 0 (§13)")

    # --- origin anchoring ---
    for m in re.finditer(r"transform-origin\s*:\s*([^;{}]+)", css, re.I):
        val = m.group(1).strip()
        start = max(0, m.start() - 600)
        ctx = css[start:m.end() + 200]
        if val.startswith("center") and ANCHORED_RE.search(ctx):
            rep.add("transform-origin", WARN,
                    "transform-origin: center on a trigger-anchored object",
                    "popovers/dropdowns/tooltips scale from their trigger; "
                    "only modals are centred", selector=val)

    # --- hard-coded highlight coordinates ---
    # ...and in a stylesheet rule. This is the form an agent actually writes:
    # `.hl{position:absolute;left:412px;top:268px}`. A check that reads only
    # inline styles reports nothing while the deck links its CSS.
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        # Comments preceding a rule are not part of its selector. In particular,
        # the presenter-shell header mentions "highlight binding" but its fixed
        # bottom position is chrome, not a detached emphasis. Preserve offsets
        # in the original CSS for the explicit motion-exception lookup below.
        sel = re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S).strip()
        body = re.sub(r"/\*.*?\*/", "", m.group(2), flags=re.S)
        if not HIGHLIGHT_RE.search(sel):
            continue                                          # not a highlight rule
        if re.search(r"@|:\s*(root|hover|active|focus)", sel):
            continue                                          # at-rules / states
        if "position" not in body or not re.search(
                r"(^|;|\s)(left|top|right|bottom|inset)\s*:\s*-?\d+(\.\d+)?px", body):
            continue                                          # not absolute pixel placement
        if "inset" in body and re.search(r"inset\s*:\s*0\b", body):
            continue                                          # inset:0 = child-fill, allowed
        if _motion_ok_near(css[max(0, m.start() - 200):m.end() + 200]):
            continue
        rep.add("hardcoded-highlight", ERROR,
                "highlight positioned with fixed pixel coordinates in a stylesheet rule",
                "bind it with data-target, or make it a child with inset:0 (§9)",
                selector=sel[:60])

    # Inline style on the element itself.
    for m in re.finditer(r"<([a-zA-Z][\w-]*)([^>]*)>", html):
        tag, attrs = m.group(1), m.group(2)
        cls = re.search(r'class\s*=\s*"([^"]*)"', attrs)
        classname = cls.group(1) if cls else ""
        is_hl = "data-hl" in attrs or bool(HIGHLIGHT_RE.search(classname))
        if not is_hl:
            continue
        style = re.search(r'style\s*=\s*"([^"]*)"', attrs)
        if style and re.search(
                r"(^|;)\s*(left|top|right|bottom|inset)\s*:\s*-?\d+(\.\d+)?px",
                style.group(1)):
            rep.add("hardcoded-highlight", ERROR,
                    "highlight positioned with fixed pixel coordinates",
                    "bind it with data-target, or make it a child with inset:0 (§9)",
                    selector=f"<{tag} class=\"{classname[:40]}\">")

    # --- forbidden patterns (class/id only: prose comments must not trip it) ---
    for m in re.finditer(r'(class|id)\s*=\s*"([^"]*)"', html):
        name = m.group(2)
        hit = PILL_RE.search(name)
        if hit and "data-motion-ok" not in html[max(0, m.start() - 200):m.end() + 200]:
            rep.add("forbidden-pattern", WARN,
                    f"'{hit.group(0)}' pattern in {m.group(1)}=\"{name[:40]}\"",
                    "no pill chips, callout chips, or leader-line annotations (§1)")

    # --- external font host ---
    for m in re.finditer(
            r"(fonts\.googleapis|fonts\.gstatic|cdn\.jsdelivr|use\.typekit|"
            r"fontawesome|cdnjs\.cloudflare)", raw, re.I):
        rep.add("external-font", ERROR,
                f"external font/asset host: {m.group(1)}",
                "self-host Pretendard; a CDN font changes metrics and invalidates "
                "every measurement you verified (§13)")

    for m in re.finditer(
            r"@font-face\s*\{[^}]*src\s*:[^}]*url\(\s*['\"]?(https?:)?//",
            css, re.I):
        rep.add("external-font", ERROR, "@font-face loads from a remote URL",
                "vendor the woff2 into assets/fonts/ (§13)")

    # --- font family ---
    if "@font-face" in css or "font-family" in css:
        if "Pretendard" not in css:
            rep.add("font-family", WARN,
                    "no Pretendard in the stylesheet",
                    "the deck font is Pretendard Variable, self-hosted (§1)")

    # --- keep-all is the mechanical form of the line-break rule ---
    body_text = re.sub(r"<[^>]+>", " ", html)
    if HANGUL_RE.search(body_text) and not re.search(
            r"word-break\s*:\s*keep-all", css, re.I):
        rep.add("keep-all", ERROR,
                "Korean copy without word-break: keep-all",
                "'never break a phrase to balance a text box' is only enforced by "
                "keep-all; without it 프론트엔드 splits mid-word (§3/§13)")

    # --- letter-spacing on Hangul ---
    for m in re.finditer(r"letter-spacing\s*:\s*([^;{}]+)", css, re.I):
        val = m.group(1).strip()
        if val.lower() in ("normal", "0", "0px", "initial", "inherit"):
            continue
        rep.add("letter-spacing", WARN, f"letter-spacing: {val}",
                "letter-spacing widens gaps between jamo blocks; it is a Latin "
                "tool — do not use it on Hangul (§13)")

    # --- type level budget (advisory: 3 levels, sizes may vary inside them) ---
    sizes = sorted({round(float(m.group(1)), 1) for m in re.finditer(
        r"font-size\s*:\s*(\d+(?:\.\d+)?)px", css, re.I)})
    if len(sizes) > 5:
        rep.add("type-levels", WARN,
                f"{len(sizes)} distinct font sizes ({', '.join(f'{s:g}' for s in sizes)})",
                "the deck allows 3 typography levels; sizes inside a level should "
                "be deliberate, not incidental (§1)")

    # --- projection floor + title cap (declared values) ---
    for m in re.finditer(r"font-size\s*:\s*(\d+(?:\.\d+)?)px", css, re.I):
        px = float(m.group(1))
        ctx = css[max(0, m.start() - 300):m.start()]
        sel_match = re.findall(r"([^{}]+)\{", ctx)
        sel = sel_match[-1].strip()[:60] if sel_match else ""
        if px < LABEL_MIN:
            rep.add("min-font", WARN, f"font-size {px:g}px below projection floor",
                    f"labels ≥ {LABEL_MIN:g}px, body ≥ {BODY_MIN:g}px (§13)",
                    selector=sel)
        if px > TITLE_MAX and TITLE_HINT_RE.search(sel):
            rep.add("title-size", WARN,
                    f"title font-size {px:g}px exceeds {TITLE_MAX:g}px",
                    "the title shares the scene with the example (§1)", selector=sel)

    # --- missing stage ---
    if not re.search(r"data-stage", html):
        rep.add("no-stage", WARN, "no [data-stage] wrapper found",
                "fix the coordinate system at 1920x1080 and scale it as a whole; "
                "a reflowing layout is what makes emphasis drift (§2)")

    # --- markup contract coverage ---
    if not re.search(r"data-slide", html):
        rep.add("no-slide-marker", WARN, "no [data-slide] roots found",
                "the linter measures slides individually; without the attribute it "
                "falls back to .slide and may miss boundaries (§0)")


# --------------------------------------------------------------------------- #
# browser layer
# --------------------------------------------------------------------------- #

MEASURE_JS = r"""
() => {
  const round = n => Math.round(n * 100) / 100;
  // An element belongs to a step phase if it or any ancestor declares one.
  // States that coexist by design (skeleton/loaded, phase 1/2) are not
  // overlapping copy, however deeply the text sits inside them.
  const inStep = el => {
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      if (n.hasAttribute('data-step')) return true;
    }
    return false;
  };
  const path = el => {
    if (!el || el.nodeType !== 1) return '';
    if (el.id) return '#' + el.id;
    let s = el.tagName.toLowerCase();
    if (el.classList.length) s += '.' + [...el.classList].slice(0, 3).join('.');
    // disambiguate: sibling runs get the same tag+class, and a selector that
    // matches two elements cannot be used to track one of them
    const sibs = el.parentElement
      ? [...el.parentElement.children].filter(c => c.tagName === el.tagName)
      : [];
    if (sibs.length > 1) s += ':nth-of-type(' + (sibs.indexOf(el) + 1) + ')';
    const p = el.parentElement;
    if (!p || p.tagName === 'BODY' || p.tagName === 'HTML') return s;
    return path(p) + ' > ' + s;
  };
  const cs = el => getComputedStyle(el);
  const box = el => { const r = el.getBoundingClientRect();
    return { x: r.x, y: r.y, w: r.width, h: r.height, top: r.top, left: r.left,
             right: r.right, bottom: r.bottom }; };
  const textRect = el => {
    const rng = document.createRange();
    let found = null;
    for (const n of el.childNodes) {
      if (n.nodeType === 3 && n.textContent.trim()) {
        rng.selectNodeContents(n);
        const r = rng.getBoundingClientRect();
        if (r.width > 0 || r.height > 0) found = found ? {
          x: Math.min(found.x, r.x), y: Math.min(found.y, r.y),
          right: Math.max(found.right, r.right), bottom: Math.max(found.bottom, r.bottom)
        } : { x: r.x, y: r.y, right: r.right, bottom: r.bottom };
      }
    }
    if (!found) return null;
    return { x: found.x, y: found.y, w: found.right - found.x, h: found.bottom - found.y,
             right: found.right, bottom: found.bottom };
  };
  const ownText = el => [...el.childNodes]
      .filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim();

  const stage = document.querySelector('[data-stage]');
  const stageCS = stage ? cs(stage) : null;
  const stageUnitW = stage ? parseFloat(stageCS.width) : 1920;
  const stageRect = stage ? box(stage) : null;
  const k = stageRect && stageUnitW ? stageRect.w / stageUnitW : 1;

  const slides = [...document.querySelectorAll('[data-slide]')];
  const roots = slides.length ? slides : [...document.querySelectorAll('.slide')];

  // everything is reported relative to the stage origin, so letterboxing does not
  // look like reflow when the viewport changes
  const sOriginX = stageRect ? stageRect.x : 0;
  const sOriginY = stageRect ? stageRect.y : 0;
  const toStage = b => ({ x: (b.x - sOriginX) / k, y: (b.y - sOriginY) / k,
                          w: b.w / k, h: b.h / k,
                          right: (b.right - sOriginX) / k,
                          bottom: (b.bottom - sOriginY) / k });

  const elements = [];
  let i = 0;
  for (const el of document.querySelectorAll('body *')) {
    const c = cs(el);
    if (c.display === 'none' || c.visibility === 'hidden') continue;
    const b = box(el);
    if (b.w === 0 && b.h === 0) continue;
    const text = ownText(el);
    const leaf = text.length > 0 && el.children.length === 0;
    let slideIdx = null;
    for (let s = 0; s < roots.length; s++) {
      if (roots[s] === el || roots[s].contains(el)) { slideIdx = s; break; }
    }
    // effective background: walk up until a non-transparent colour
    let bg = 'rgba(0, 0, 0, 0)', node = el;
    while (node && (bg === 'rgba(0, 0, 0, 0)' || bg === 'transparent')) {
      const cc = cs(node);
      if (cc.backgroundImage && cc.backgroundImage !== 'none') { bg = 'IMAGE'; break; }
      bg = cc.backgroundColor;
      node = node.parentElement;
    }
    elements.push({
      idx: i++, sel: path(el), slide: slideIdx,
      rect: b, stageRect: toStage(b),
      font: c.fontFamily, size: parseFloat(c.fontSize),
      weight: c.fontWeight, color: c.color, bg: bg,
      opacity: parseFloat(c.opacity),
      position: c.position,
      display: c.display, justify: c.justifyContent, align: c.alignItems,
      textAlign: c.textAlign, lineHeight: c.lineHeight,
      overflowX: c.overflowX, overflowY: c.overflowY,
      scrollW: el.scrollWidth, scrollH: el.scrollHeight,
      clientW: el.clientWidth, clientH: el.clientHeight,
      cls: [...el.classList].join(' '),
      attrs: { hl: el.hasAttribute('data-hl'), step: inStep(el) ? 'yes' : null,
               target: el.getAttribute('data-target'),
               bleed: el.hasAttribute('data-bleed'),
               copy: el.hasAttribute('data-copy'), visual: el.hasAttribute('data-visual'),
               recede: el.hasAttribute('data-recede'),
               recedeKeep: el.hasAttribute('data-recede-keep') },
      text: text.slice(0, 60), isText: leaf,
      textRect: leaf ? textRect(el) : null,
      borderTop: c.borderTopWidth, borderLeft: c.borderLeftWidth,
      outline: c.outlineWidth, boxShadow: c.boxShadow,
      beforeContent: getComputedStyle(el, '::before').content,
      afterContent: getComputedStyle(el, '::after').content,
      depth: (() => { let d = 0, p = el; while (p.parentElement) { d++; p = p.parentElement; } return d; })(),
      parentSel: el.parentElement ? path(el.parentElement) : '',
      zIndex: c.zIndex
    });
  }

  const highlights = [];
  // same vocabulary as HIGHLIGHT_RE in the static layer, so both layers agree
  // on what counts as an emphasis overlay
  for (const el of document.querySelectorAll(
        '[data-hl], [class*="hl-"], [class*="hl_"], [class*="highlight"], ' +
        '[class*="sweep"], [class*="mask"], [class*="dim"], [class*="trace"], ' +
        '[class*="zoom"], [class*="focus"], [class*="ring"], [class*="marker"]')) {
    const c = cs(el);
    if (c.display === 'none') continue;
    const own = ownText(el);
    const b = box(el);
    const targetSel = el.getAttribute('data-target');
    let target = targetSel ? document.querySelector(targetSel) : null;
    let form = target ? 'data-target' : 'none';
    if (!target) {
      if (targetSel) {
        form = 'unresolved';          // declared a target that is not in the DOM
      } else {
        // descendant form: the highlight is a child of the thing it emphasises.
        // If that turns out to be the slide itself, the overlay is positioned
        // against the canvas — which is the failure mode, not a binding.
        target = el.parentElement;
        form = (target && (target.hasAttribute('data-slide') ||
                           target.hasAttribute('data-stage')))
          ? 'parent-slide' : 'descendant';
      }
    }
    const tr = target ? box(target) : null;
    highlights.push({
      sel: path(el), slide: (() => { for (let s = 0; s < roots.length; s++)
        if (roots[s].contains(el)) return s; return null; })(),
      form: form, targetSel: target ? path(target) : null,
      resolved: !!target, rect: b, targetRect: tr,
      offset: tr ? { dx: round(b.x - tr.x), dy: round(b.y - tr.y),
                     dw: round(b.w - tr.w), dh: round(b.h - tr.h) } : null,
      offsetStage: tr ? { dx: round((b.x - tr.x) / k), dy: round((b.y - tr.y) / k),
                          dw: round((b.w - tr.w) / k), dh: round((b.h - tr.h) / k) } : null,
      opacity: parseFloat(c.opacity), zIndex: c.zIndex,
      styleHints: {
        border: parseFloat(c.borderTopWidth) + parseFloat(c.borderLeftWidth) > 0,
        outline: c.outlineWidth !== '0px' && c.outlineStyle !== 'none',
        shadow: c.boxShadow !== 'none',
        bg: c.backgroundColor !== 'rgba(0, 0, 0, 0)',
        pseudo: getComputedStyle(el, '::before').content !== 'none' ||
                getComputedStyle(el, '::after').content !== 'none',
        stroke: el.tagName.toLowerCase() === 'path' || el.tagName.toLowerCase() === 'circle'
      },
      text: own.slice(0, 40)
    });
  }

  return {
    stageRect: stageRect, k: k, stageUnitW: stageUnitW,
    slides: roots.map((el, idx) => ({ idx: idx, sel: path(el), rect: box(el),
      stageRect: toStage(box(el)),
      children: [...el.children].map(ch => path(ch)) })),
    elements: elements, highlights: highlights,
    fontsReady: document.fonts ? document.fonts.status : 'unknown',
    docW: document.documentElement.scrollWidth,
    docH: document.documentElement.scrollHeight
  };
}
"""


def _lum(rgb: tuple[float, float, float]) -> float:
    def ch(v: float) -> float:
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _parse_rgb(s: str) -> tuple[float, float, float, float] | None:
    m = re.match(r"rgba?\(([^)]+)\)", s or "")
    if not m:
        return None
    parts = [p.strip() for p in m.group(1).replace("/", " ").split(",")]
    try:
        vals = [float(p) for p in parts[:3]]
    except ValueError:
        return None
    alpha = float(parts[3]) if len(parts) > 3 else 1.0
    return vals[0], vals[1], vals[2], alpha


def _composite(fg, bg):
    a = fg[3]
    return (fg[0] * a + bg[0] * (1 - a),
            fg[1] * a + bg[1] * (1 - a),
            fg[2] * a + bg[2] * (1 - a))


def _contrast(fg, bg) -> float:
    l1, l2 = _lum(fg[:3]), _lum(bg[:3])
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def _overlap_area(a: dict, b: dict) -> float:
    w = min(a["right"], b["right"]) - max(a["x"], b["x"])
    h = min(a["bottom"], b["bottom"]) - max(a["y"], b["y"])
    return max(0.0, w) * max(0.0, h)


def _gap(a: dict, b: dict) -> tuple[float, float]:
    """Return (horizontal gap, vertical gap) between two boxes; 0 if overlapping."""
    hx = max(0.0, max(a["x"], b["x"]) - min(a["right"], b["right"]))
    vy = max(0.0, max(a["y"], b["y"]) - min(a["bottom"], b["bottom"]))
    return hx, vy


def browser_checks(path: Path, data: dict, rep: Report, shots: Path | None,
                   viewports: list[tuple[int, int]]) -> None:
    k = data.get("k") or 1.0
    stage = data.get("stageRect")
    els = data.get("elements", [])
    slides = data.get("slides", [])
    hls = data.get("highlights", [])

    if data.get("fontsReady") not in ("loaded", "unknown"):
        rep.add("fonts-not-ready", WARN,
                f"document.fonts.status = {data.get('fontsReady')}",
                "measure only after fonts load; a late metric swap reflows the deck",
                layer="browser")

    # accumulate: this runs once per slide
    rep.stats["elements"] = rep.stats.get("elements", 0) + len(els)
    rep.stats["highlights"] = rep.stats.get("highlights", 0) + len(hls)

    by_sel = {e["sel"]: e for e in els}

    # ---- per-slide geometry -------------------------------------------------
    def _visible(e: dict) -> bool:
        """Opacity ~0 means the element is not in the static frame at all."""
        return e.get("opacity", 1) >= 0.05

    for s in slides:
        sr = s["stageRect"]
        band = sr["y"] + sr["h"] * (1 - BOTTOM_BAND)

        members = [e for e in els if e["slide"] == s["idx"]]
        visible = [e for e in members if _visible(e)]
        if not members:
            continue

        for e in members:
            r = e["stageRect"]
            if e["attrs"]["bleed"]:
                continue
            # out of stage bounds
            if (r["x"] < -1 or r["y"] < -1 or
                    r["x"] + r["w"] > sr["w"] + 1 or r["y"] + r["h"] > sr["h"] + 1):
                rep.add("overflow", ERROR, "element extends outside the stage",
                        "keep content inside the 1920x1080 stage; mark intentional "
                        "full-bleed art with data-bleed (§2)",
                        slide=s["idx"], selector=e["sel"], layer="browser")
                continue
            # safe inset for meaningful content
            if e["isText"] or e["attrs"]["hl"]:
                inset_x, inset_y = sr["w"] * SAFE_INSET, sr["h"] * SAFE_INSET
                if (r["x"] < inset_x - 1 or r["y"] < inset_y - 1 or
                        r["x"] + r["w"] > sr["w"] - inset_x + 1 or
                        r["y"] + r["h"] > sr["h"] - inset_y + 1):
                    rep.add("unsafe-inset", WARN,
                            "content inside the 5% safe inset",
                            "4:3 projectors crop the outer 5%; move it inward or "
                            "accept the crop knowingly (§2)",
                            slide=s["idx"], selector=e["sel"], layer="browser")
            # clipped / scrollable overflow
            if e["overflowY"] in ("hidden", "auto", "scroll") and \
                    e["scrollH"] > e["clientH"] + 1:
                rep.add("clip", ERROR,
                        f"content clipped vertically ({e['scrollH']} > {e['clientH']})",
                        "simplify the mockup instead of hiding the excess (§7)",
                        slide=s["idx"], selector=e["sel"], layer="browser")
            if e["overflowX"] in ("hidden", "auto", "scroll") and \
                    e["scrollW"] > e["clientW"] + 1:
                rep.add("clip", ERROR,
                        f"content clipped horizontally ({e['scrollW']} > {e['clientW']})",
                        "shorten the line or widen the box (§7)",
                        slide=s["idx"], selector=e["sel"], layer="browser")
            if e["isText"]:
                if e["scrollW"] > e["clientW"] + 1:
                    rep.add("text-overflow", ERROR, "text overflows its box",
                            "give it room; do not shrink below the projection floor",
                            slide=s["idx"], selector=e["sel"], layer="browser")
                if e["font"] and "Pretendard" not in e["font"] and \
                        not re.search(r"(system-ui|-apple-system|sans-serif)", e["font"]):
                    rep.add("font-family", WARN,
                            f"text renders in '{e['font'].split(',')[0]}'",
                            "Pretendard Variable everywhere (§1)",
                            slide=s["idx"], selector=e["sel"], layer="browser")
                if e["size"] < LABEL_MIN:
                    rep.add("min-font", WARN,
                            f"text at {e['size']:g}px is below the projection floor",
                            f"labels ≥ {LABEL_MIN:g}px (§13)",
                            slide=s["idx"], selector=e["sel"], layer="browser")

        # ---- overlap of unrelated boxes ------------------------------------
        texts = [e for e in visible if e["isText"] and e["attrs"]["step"] is None]
        for a_i in range(len(texts)):
            for b_i in range(a_i + 1, len(texts)):
                a, b = texts[a_i], texts[b_i]
                ra, rb = a["rect"], b["rect"]
                if a["sel"] in b["parentSel"] or b["sel"] in a["parentSel"]:
                    continue
                ov = _overlap_area(ra, rb)
                if ov <= 0:
                    continue
                small = min(ra["w"] * ra["h"], rb["w"] * rb["h"])
                if small > 0 and ov / small >= CROWD:
                    rep.add("overlap", ERROR,
                            f"text boxes overlap by {ov / small * 100:.0f}%",
                            "recompose: overlapping copy is unreadable at "
                            "projection scale (§5)",
                            slide=s["idx"],
                            selector=f"{a['sel']} <> {b['sel']}", layer="browser")

        # ---- contrast -------------------------------------------------------
        for e in visible:
            if not e["isText"] or not e["bg"]:
                continue
            if e["bg"] == "IMAGE":
                continue
            fg = _parse_rgb(e["color"])
            bg = _parse_rgb(e["bg"])
            if not fg or not bg or bg[3] == 0:
                continue
            eff_fg = _composite(fg, bg) if fg[3] < 1 else fg[:3]
            ratio = _contrast(eff_fg, bg)
            large = e["size"] >= LARGE_PX or (
                e["size"] >= 24 and int(float(e["weight"] or 400)) >= 700)
            need = CONTRAST_LARGE if large else CONTRAST_BODY
            if ratio < need:
                rep.add("contrast", ERROR,
                        f"contrast {ratio:.2f}:1 (needs {need}:1) for {e['size']:g}px text",
                        "darken the text or lighten the surface (§13)",
                        slide=s["idx"], selector=e["sel"], layer="browser")

        # ---- centring of text inside containers -----------------------------
        for e in visible:
            if not e["textRect"] or e["attrs"]["hl"]:
                continue
            if not e["isText"] or e["textAlign"] != "center":
                continue
            container = next((c for c in visible if c["sel"] == e["parentSel"]), None)
            if not container:
                continue
            tr, cr = e["textRect"], container["rect"]
            dx = (tr["x"] + tr["w"] / 2) - (cr["x"] + cr["w"] / 2)
            # horizontal centring is only meaningful when the line fills its box
            if abs(e["rect"]["w"] - cr["w"]) <= 4 and abs(dx) > CENTER_TOL:
                rep.add("text-offcenter", WARN,
                        f"text off-centre horizontally by {dx:+.1f}px",
                        "fix with flex centring or line-height, never a padding nudge (§6)",
                        slide=s["idx"], selector=e["sel"], layer="browser")
            # vertical centring only when the container holds this one text child
            sole = [c for c in visible
                    if c["parentSel"] == container["sel"] and c["isText"]]
            if len(sole) == 1 and container["align"] == "center":
                dy = (tr["y"] + tr["h"] / 2) - (cr["y"] + cr["h"] / 2)
                if abs(dy) > CENTER_TOL:
                    rep.add("text-offcenter", WARN,
                            f"text off-centre vertically by {dy:+.1f}px",
                            "align-items: center, or an explicit line-height equal "
                            "to the box height (§6)",
                            slide=s["idx"], selector=e["sel"], layer="browser")

        # ---- text centred inside flex/pressable containers -------------------
        for e in visible:
            if e["display"] not in ("flex", "inline-flex"):
                continue
            if e["justify"] not in ("center", "space-around", "space-evenly"):
                continue
            kids = [c for c in visible
                    if c["parentSel"] == e["sel"] and c["isText"] and c["textRect"]]
            if not kids:
                continue
            left = min(k["textRect"]["x"] for k in kids)
            right = max(k["textRect"]["right"] for k in kids)
            dx = ((left + right) / 2) - (e["rect"]["x"] + e["rect"]["w"] / 2)
            if abs(dx) > CENTER_TOL:
                rep.add("text-offcenter", WARN,
                        f"contents off-centre horizontally by {dx:+.1f}px",
                        "flex centring, not a padding nudge: button and badge text "
                        "must be centred on both axes (§6)",
                        slide=s["idx"], selector=e["sel"], layer="browser")

        # ---- repeated-object baselines --------------------------------------
        groups: dict[str, list[dict]] = {}
        for e in visible:
            if e["isText"] and e["cls"] and e["textRect"]:
                groups.setdefault(e["cls"], []).append(e)
        for cls, group in groups.items():
            if len(group) < 2:
                continue
            # a group is "repeated objects" only if they share size and width;
            # a scaled clone or a differently-sized variant is not a baseline pair
            if len({round(g["size"], 1) for g in group}) != 1:
                continue
            widths = [g["rect"]["w"] for g in group]
            if max(widths) - min(widths) > 2:
                continue
            # Only objects on the SAME row must share a baseline. Group by
            # vertical overlap first: the second row of a 2x2 grid is a
            # different row, not a misaligned one.
            rows: list[list[dict]] = []
            for g in sorted(group, key=lambda e: e["rect"]["y"]):
                for r in rows:
                    top = max([g["rect"]["y"]] + [x["rect"]["y"] for x in r])
                    bottom = min([g["rect"]["y"] + g["rect"]["h"]] +
                                 [x["rect"]["y"] + x["rect"]["h"] for x in r])
                    if bottom - top > 0:
                        r.append(g)
                        break
                else:
                    rows.append([g])
            for r in rows:
                if len(r) < 2:
                    continue
                # and they must sit side by side. Stacked paragraphs in a column
                # are a list, not a row of repeated objects, so tops are free.
                lefts = [g["rect"]["x"] for g in r]
                if max(lefts) - min(lefts) <= 20:
                    continue
                tops = [g["textRect"]["y"] for g in r]
                spread = max(tops) - min(tops)
                if spread > max(BASELINE_TOL, 4):
                    rep.add("baseline-mismatch", WARN,
                            f"repeated '.{cls.split()[0]}' texts differ by {spread:.1f}px",
                            "repeated objects share baselines and edges (§6)",
                            slide=s["idx"], selector=f".{cls.split()[0]}",
                            layer="browser")

        # ---- internal gaps --------------------------------------------------
        roots = [e for e in visible if e["parentSel"] and
                 e["parentSel"] == s["sel"]]
        roots.sort(key=lambda e: e["stageRect"]["y"])
        for a, b in zip(roots, roots[1:]):
            _, vy = _gap(a["stageRect"], b["stageRect"])
            if vy > LARGE_GAP:
                rep.add("large-gap", WARN,
                        f"{vy:.0f}px internal gap between content blocks",
                        "the title/huge gap/body pattern is the layout this deck "
                        "exists to avoid; place the cluster by its visual anchor (§4/§5)",
                        slide=s["idx"],
                        selector=f"{a['sel']} -> {b['sel']}", layer="browser")

        copy_el = next((e for e in visible if e["attrs"]["copy"]), None)
        vis_el = next((e for e in visible if e["attrs"]["visual"]), None)
        if copy_el and vis_el:
            hx, vy = _gap(copy_el["stageRect"], vis_el["stageRect"])
            gap = min(hx, vy) if hx and vy else (hx or vy)
            if gap > GAP_MAX:
                rep.add("copy-visual-gap", WARN,
                        f"{gap:.0f}px between copy cluster and visual",
                        f"objects that explain each other stay within ~{GAP_MAX:g}px (§4)",
                        slide=s["idx"], layer="browser")
            elif 0 < gap < GAP_SCENE_MIN and hx and vy:
                rep.add("copy-visual-gap", WARN,
                        f"copy cluster and visual nearly touch ({gap:.0f}px)",
                        "give distinct clusters breathing room (§4)",
                        slide=s["idx"], layer="browser")

        # ---- reading order --------------------------------------------------
        cluster = next((e for e in members if e["attrs"]["copy"]), None)
        if cluster:
            kids = [e for e in visible
                    if e["parentSel"] == cluster["sel"] and e["isText"]]
            if len(kids) >= 2:
                kids.sort(key=lambda e: e["stageRect"]["y"])
                title = max(kids, key=lambda e: e["size"])
                body = min(kids, key=lambda e: e["size"])
                if title is not body and body["stageRect"]["y"] < title["stageRect"]["y"] - 2:
                    rep.add("reading-order", WARN,
                            "body copy sits above the title",
                            "default hierarchy is title -> body -> example (§3)"
                            if not HANGUL_RE.search("") else
                            "default hierarchy is title -> body -> example (poster "
                            "treatment must be an explicit request) (§3)",
                            slide=s["idx"], selector=cluster["sel"], layer="browser")

        # ---- bottom captions ------------------------------------------------
        for e in visible:
            if not e["isText"] or e["attrs"]["bleed"]:
                continue
            r = e["stageRect"]
            if r["y"] + r["h"] < band:
                continue
            captionish = bool(PILL_RE.search(e["cls"])) or e["size"] <= LABEL_MIN
            if not captionish:
                continue
            others = [o for o in visible
                      if o is not e and o["stageRect"]["y"] + o["stageRect"]["h"]
                      < r["y"] - 40]
            if others:
                rep.add("bottom-caption", WARN,
                        f"text in the bottom band reads as an explanatory caption: "
                        f"\"{e['text'][:34]}\"",
                        "no bottom captions; put the line beside the object it "
                        "explains (§1/§3)",
                        slide=s["idx"], selector=e["sel"], layer="browser")

        # ---- emphasis must survive as a state -------------------------------
        for h in hls:
            if h["slide"] != s["idx"]:
                continue
            sh = h["styleHints"]
            has_mechanism = any([sh["border"], sh["outline"], sh["shadow"],
                                 sh["bg"], sh["pseudo"], sh["stroke"]])
            if not has_mechanism:
                rep.add("emphasis-undefined", ERROR,
                        "highlight has no visible appearance of its own",
                        "an emphasis that exists only in JavaScript is invisible in "
                        "a static frame; declare its final state in CSS (§8/§9)",
                        slide=s["idx"], selector=h["sel"], layer="browser")
            if h["opacity"] < 0.5:
                rep.add("emphasis-state", WARN,
                        f"highlight is at opacity {h['opacity']:g} in the static frame",
                        "motion explains, state remains — the end state must be "
                        "visible without animation (§8)",
                        slide=s["idx"], selector=h["sel"], layer="browser")

    # ---- recede-the-rest: the emphasis is the target keeping its weight ------
    for e in visible:
        if not e["attrs"].get("recedeKeep"):
            continue
        if e["opacity"] < 0.95:
            rep.add("recede-target", ERROR,
                    f"the kept element is dimmed to opacity {e['opacity']:g}",
                    "de-emphasising the rest must not touch the target; mark the "
                    "target with data-recede-keep and leave it at full opacity (§9)",
                    slide=s["idx"], selector=e["sel"], layer="browser")
    for e in visible:
        if not e["attrs"].get("recede"):
            continue
        kids = [c for c in visible if c["parentSel"] == e["sel"]]
        keep = [c for c in kids if c["attrs"].get("recedeKeep")]
        receded = [c for c in kids if c["opacity"] < 0.7]
        if not keep:
            rep.add("recede-target", ERROR,
                    "recede container marks no target",
                    "mark exactly one child with data-recede-keep, so the "
                    "emphasis has a real anchor (§9)",
                    slide=s["idx"], selector=e["sel"], layer="browser")
        elif not receded:
            rep.add("recede-target", WARN,
                    "nothing actually recedes",
                    "if every child stays at full weight the pattern explains "
                    "nothing; drop it (§8)",
                    slide=s["idx"], selector=e["sel"], layer="browser")

    # ---- target binding -----------------------------------------------------
    for h in hls:
        if not h["resolved"] or h.get("form") == "parent-slide":
            why = ("highlight is positioned against the slide canvas, not against "
                   "a target"
                   if h.get("form") == "parent-slide"
                   else "highlight cannot be resolved to a target element")
            rep.add("unbound-highlight", ERROR,
                    why,
                    "bind it with data-target, or make it a descendant of the "
                    "element it emphasises (§9)",
                    slide=h["slide"], selector=h["sel"], layer="browser")
            continue
        tr, r = h["targetRect"], h["rect"]
        if not tr:
            continue
        # containment: the highlight must sit on/around its target, not float
        slack = max(tr["w"], tr["h"]) * 0.25 + 8
        outside = (r["x"] < tr["x"] - slack or r["y"] < tr["y"] - slack or
                   r["right"] > tr["right"] + slack or
                   r["bottom"] > tr["bottom"] + slack)
        if outside:
            over_x = max(0.0, tr["x"] - r["x"], r["right"] - tr["right"])
            over_y = max(0.0, tr["y"] - r["y"], r["bottom"] - tr["bottom"])
            rep.add("detached-highlight", ERROR,
                    f"highlight extends {over_x:.0f}px / {over_y:.0f}px past its target",
                    "emphasis must be drawn on the target, not near it — use a "
                    "descendant overlay or a clone (§9)",
                    slide=h["slide"], selector=f"{h['sel']} -> {h['targetSel']}",
                    layer="browser")


def _slice_for_slide(data: dict, idx: int) -> dict:
    """Restrict a measurement to one slide, so every slide is checked on its own."""
    return {
        "k": data.get("k", 1.0),
        "stageRect": data.get("stageRect"),
        "slides": [s for s in data.get("slides", []) if s["idx"] == idx],
        "elements": [e for e in data.get("elements", []) if e.get("slide") == idx],
        "highlights": [h for h in data.get("highlights", []) if h.get("slide") == idx],
        "fontsReady": data.get("fontsReady"),
    }


def _hl_index(data: dict) -> dict:
    """(highlight, target) -> offset, in stage units, for every bound highlight."""
    return {(h["sel"], h["targetSel"]): h["offsetStage"]
            for h in data.get("highlights", [])
            if h.get("resolved") and h.get("offsetStage")}


def _reflow_check(base: dict, other: dict, base_key: tuple, key: tuple,
                  seen: set, rep: Report) -> None:
    """Stage-unit geometry must be identical across viewports for a fixed stage."""
    base_by_sel = {e["sel"]: e for e in base.get("elements", [])}
    for e in other.get("elements", []):
        if e.get("slide") is None:
            continue
        be = base_by_sel.get(e["sel"])
        if not be:
            continue
        diff = max(abs(e["stageRect"][k] - be["stageRect"][k])
                   for k in ("x", "y", "w", "h"))
        if diff <= DRIFT_TOL:
            continue
        ident = (base_key[2], e["sel"])
        if ident in seen:
            continue
        seen.add(ident)
        rep.add("reflow", ERROR,
                f"layout moved {diff:.1f}px between {base_key[0]}x{base_key[1]} "
                f"and {key[0]}x{key[1]}",
                "the stage must scale as a whole, not reflow; reflow is what makes "
                "bound highlights drift (§2)",
                slide=e["slide"], selector=e["sel"], layer="browser")


def drift_check(path: Path, reads: dict[tuple[int, int, int], dict],
                rep: Report) -> None:
    """Re-measure across viewport sizes: offsets and geometry must not move."""
    for sidx in sorted({k[2] for k in reads}):
        keys = sorted(k for k in reads if k[2] == sidx)
        if len(keys) < 2:
            continue
        base_key = keys[0]
        base = reads[base_key]
        if not base.get("stageRect"):
            continue
        b_idx = _hl_index(base)
        seen: set = set()
        for key in keys[1:]:
            data = reads[key]
            idx = _hl_index(data)
            for ident, off in idx.items():
                if ident not in b_idx:
                    rep.add("binding-drift", ERROR,
                            "highlight binds to a target in one viewport but not another",
                            "the binding depends on layout state; bind it "
                            "structurally (§9)",
                            slide=sidx, selector=f"{ident[0]} -> {ident[1]}",
                            layer="browser")
                    continue
                d = max(abs(off[k] - b_idx[ident][k]) for k in ("dx", "dy", "dw", "dh"))
                if d > DRIFT_TOL:
                    rep.add("binding-drift", ERROR,
                            f"highlight moved {d:.1f}px relative to its target between "
                            f"{base_key[0]}x{base_key[1]} and {key[0]}x{key[1]}",
                            "the effect must stay aligned when the browser or mockup "
                            "changes size; it must follow automatically (§9)",
                            slide=sidx, selector=f"{ident[0]} -> {ident[1]}",
                            layer="browser")
            for ident in b_idx:
                if ident not in idx:
                    rep.add("binding-drift", ERROR,
                            "highlight disappears when the viewport changes",
                            "an emphasis that only resolves at one size is not "
                            "bound to its target (§9)",
                            slide=sidx, selector=f"{ident[0]} -> {ident[1]}",
                            layer="browser")
            _reflow_check(base, data, base_key, key, seen, rep)


# --------------------------------------------------------------------------- #
# runner
# --------------------------------------------------------------------------- #

def lint(path: Path, use_browser: bool, shots: Path | None,
         viewports: list[tuple[int, int]], quiet: bool) -> Report:
    rep = Report(path=str(path))
    static_checks(path, rep)

    if not use_browser:
        return rep

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        rep.add("no-browser", WARN, "playwright not installed; static checks only",
                "pip install playwright && playwright install chromium",
                layer="browser")
        return rep

    no_motion = ("*,*::before,*::after{transition:none!important;"
                 "animation:none!important;}")
    # The accepted frame is the frame without motion. Measuring under
    # prefers-reduced-motion is what proves the deck is complete on its own:
    # anything that only exists while an animation plays disappears here.
    settle = r"""() => {
      document.documentElement.classList.remove('deck-live');
      document.body.classList.remove('deck-live');
      document.querySelectorAll('*').forEach(el => {
        [...el.classList].filter(c => c.startsWith('deck-step-')).forEach(
          c => el.classList.remove(c));
      });
    }"""
    reads: dict[tuple[int, int, int], dict] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for vw, vh in viewports:
                page = browser.new_page(viewport={"width": vw, "height": vh},
                                        device_scale_factor=1,
                                        reduced_motion="reduce")
                page.goto(path.resolve().as_uri(), wait_until="load")
                # deterministic layout: no animation, no transitions, fonts settled
                page.add_style_tag(content=no_motion)
                try:
                    page.evaluate(settle)
                except Exception:
                    pass
                try:
                    page.evaluate("() => document.fonts.ready")
                except Exception:
                    pass
                page.wait_for_timeout(150)

                n = page.evaluate(
                    "() => document.querySelectorAll('[data-slide]').length || "
                    "document.querySelectorAll('.slide').length")
                # a staged deck can step through its slides for us; without the
                # hook only the initially visible slide can be measured
                hooked = page.evaluate("() => typeof window.__deckGoto === 'function'")
                counts = range(n) if (hooked and n > 1) else [0]
                for i in counts:
                    if hooked and n > 1:
                        page.evaluate(f"() => window.__deckGoto({i})")
                        page.wait_for_timeout(80)
                    data = page.evaluate(MEASURE_JS)
                    slidx = data["slides"][i]["idx"] if len(data["slides"]) > i else i
                    reads[(vw, vh, slidx)] = _slice_for_slide(data, slidx)
                    if shots and (vw, vh) == viewports[0]:
                        shots.mkdir(parents=True, exist_ok=True)
                        handle = page.query_selector_all("[data-slide]")
                        if len(handle) > i:
                            name = (handle[i].get_attribute("data-slide")
                                    or f"slide-{i}")
                            safe = re.sub(r"[^\w.-]+", "-", name)[:40]
                            try:
                                handle[i].screenshot(path=str(shots / f"{safe}.png"))
                            except Exception:
                                pass
                page.close()
        finally:
            browser.close()

    slides_seen = sorted({k[2] for k in reads})
    for sidx in slides_seen:
        first = reads.get((viewports[0][0], viewports[0][1], sidx))
        if first:
            browser_checks(path, first, rep, shots, viewports)
    rep.stats["slides"] = len(slides_seen)
    if len(reads) > 1:
        drift_check(path, reads, rep)
    return rep


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Lint an HTML slide deck.")
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--no-browser", action="store_true",
                    help="static checks only")
    ap.add_argument("--shots", type=Path, default=None,
                    help="write per-slide screenshots here")
    ap.add_argument("--json", type=Path, default=None, help="write a JSON report")
    ap.add_argument("--viewport", action="append", default=None,
                    metavar="WxH", help="measure at this viewport (repeatable)")
    ap.add_argument("--quiet", action="store_true", help="errors only")
    args = ap.parse_args(argv)

    viewports = VIEWPORTS
    if args.viewport:
        viewports = []
        for spec in args.viewport:
            w, _, h = spec.lower().partition("x")
            viewports.append((int(w), int(h)))

    reports = []
    worst = 0
    for f in args.files:
        if not f.exists():
            print(f"missing file: {f}", file=sys.stderr)
            worst = max(worst, 2)
            continue
        rep = lint(f, not args.no_browser, args.shots, viewports, args.quiet)
        reports.append(rep)
        worst = max(worst, rep.worst())

        print(f"\n=== {f} ===")
        if args.no_browser:
            print("  (static checks only)")
        shown = [x for x in rep.findings
                 if not args.quiet or x.severity == ERROR]
        for fnd in sorted(shown, key=lambda x: (x.severity != ERROR,
                                                x.severity != WARN, x.slide or 0)):
            print(fnd.line())

        st = rep.stats
        if st:
            print(f"  measured: {st.get('slides', 0)} slides, "
                  f"{st.get('elements', 0)} elements, "
                  f"{st.get('highlights', 0)} highlights")
        n_err, n_warn, n_info = rep.count(ERROR), rep.count(WARN), rep.count(INFO)
        verdict = "PASS" if n_err == 0 else "FAIL"
        print(f"  {verdict}: {n_err} errors, {n_warn} warnings, {n_info} info")

    if args.json:
        payload = [{"path": r.path,
                    "findings": [asdict(x) for x in r.findings],
                    "stats": r.stats} for r in reports]
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                             encoding="utf-8")
        print(f"\njson -> {args.json}")

    return worst


if __name__ == "__main__":
    raise SystemExit(main())
