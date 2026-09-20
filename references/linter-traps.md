# Measured geometry QA for HTML decks

Eyeballing a rendered slide does not catch drift, clipping, or overlap — and a text-only agent cannot see a screenshot at all. Measure in a real browser and report numbers.

```bash
python3 -m venv ~/.venvs/pw
~/.venvs/pw/bin/pip install playwright
~/.venvs/pw/bin/playwright install chromium
```

## The anchoring proof (the check that matters)

This is what distinguishes "the mark looks like it is on the box" from "the mark is attached to the box". It is the same probe used to validate the technique end-to-end.

1. Load the deck at 1920×1080 and advance to the slide.
2. Read `getBoundingClientRect()` for the **target** and the **overlay**, plus the overlay's offsets inside the target (left/top/right/bottom/width/height differences). Those offsets are the invariant.
3. Jiggle the target: set `target.style.transform = 'translate(31px, 23px)'`.
4. Re-read both rects, then restore the inline transform.
5. **Pass only if** the overlay's delta equals the target's delta (±0.5px) **and** every offset is unchanged (±0.5px).

A `position: absolute` overlay with `left`/`top` fails step 5 — the target moves, the overlay does not. A child-anchored overlay passes with identical deltas. Wrap the whole thing in one `page.evaluate` so the jiggle and both reads happen in the same layout cycle batch (`scripts/deck_geometry_qa.py` implements exactly this).

Measured result from the reference run: target Δ(31, 23) vs overlay Δ(31, 23), offsets L10/T10/R10/B10 unchanged on every slide — pass.

## Static checks worth automating

- **Overflow** — any element with visible text whose rect extends past the slide box. Report the offending element's class and text, not just a count.
- **Clipping** — content whose box exceeds its own container (`scrollWidth > clientWidth`, or an `overflow: hidden` ancestor cutting a text rect).
- **Overlap** — collect only elements that really bear glyphs; a container and its child always "overlap" and are not findings. Skip wrapper/inline-wrap elements or you will drown in false positives.
- **Contrast** — sample the element's background behind the glyphs (walking up to the first non-transparent background) and compute a WCAG ratio for meaningful text.

## Traps

- **Measure after fonts settle.** `await page.evaluate("() => document.fonts.ready.then(() => true)")` before reading rects; web-font swap reflows text and silently shifts everything.
- **Exclude decoration from the report.** Rings/brackets/marks intentionally overlap their target — exclude overlay classes from the overlap/overflow pass or they become permanent false violations.
- **Prefer waiting for a deterministic layout** over a fixed sleep: sample the measurement twice and proceed only once two consecutive reads agree.
- **One viewport is not verification.** Check the deck at the presentation size and at the scaled size; scaling is where absolute coordinates come apart.
- **Render ≠ measure.** Screenshot scripts (headless Chrome `--screenshot`) produce images; they assert nothing. Keep rendering for visual review and measurement for the verdict.

## Extending

For a real-world reference implementation of this class of validator, see `references/deck-skill-ecosystem.md` (notably `kaisersong/slide-creator`'s `browser_geometry_qa.py`, which measures `title_clipped` / `content_clipped` / `text_overflow` / `character_overlap` / contrast and waits for deterministic layout first).
