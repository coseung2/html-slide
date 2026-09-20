# Deck runtime contract (`.deck-live`)

Class lesson from building a verified deck repo: step/phase CSS that hides content will break the static frame (PDF, screenshot, reduced-motion user, linter) unless every phase rule is gated on a live class.

## The contract

- The deck runtime adds `deck-live` to `<html>` **only** when it runs with motion allowed (`prefers-reduced-motion` off).
- Every phase/step selector in CSS is scoped under `.deck-live` (e.g. `.deck-live .deck-step-0 .pat-state--before`). Without the class, plain CSS renders the accepted (finished) frame — no JS, no animation required.
- The linter measures under `emulate_media(reduced_motion="reduce")` plus a no-transition style tag, with any `deck-step-*` classes stripped: what it sees is what a capture/export sees.

## State machine (`deck-motion.js` pattern)

- One `Deck`: `slide` index + `phase` index, both read from the DOM (`data-slide`, `data-step` max, `data-start` clamped to range) — never from a config table, so markup cannot drift from behaviour.
- `next()`: phase up to max, then slide+1 at its `data-start`. `prev()`: phase down to the slide's own start, then slide−1 at its start. Back walks the machine, not the slides.
- `data-start` semantics: transforming slides (before→after, old→new value, swap) carry `data-start="0"` — they open on the *earlier* state and one advance completes them. A behaviour test caught `data-start="1"` here as a real defect: the slide opened on the new value with nowhere to advance to.
- `reflow()` on resize and on `document.fonts.ready`: re-fit the stage and re-emit `deck:reflow` so bound emphasis never sits on a stale box.
- Expose a `__deckGoto(n)` hook so the linter/tester can drive every slide, not just the visible one.
- Reduced motion collapses the machine: `phases()` reads 0, no `deck-live`, complete frame on screen. That collapsed state **is** the pass, not a skip.

## FLIP (`flip()` pattern)

First → mutate → Last → Invert → Play via `element.animate`, transform-only. Translate before scale (scaling first moves the element's own origin). Clear any `will-change` when the animation finishes.

## Behaviour checks (the six categories)

`complete` (no phase state + everything visible under reduced motion) / `presenting` (opens on `data-start`, exact forward walk incl. the clamped end) / `reversible` (exact backward walk) / `settles` (frame complete at the last phase) / `bound` (`data-hl` covers ≥85% of target at 1920×1080, 1280×720, 1024×768 with ≤1.0 unit drift — compare coverage *ratio*, stage scale shrinks pixel gaps) / `still` (target box motionless while its effect plays).

## Implementation crash to avoid

Methods the constructor calls must live on the prototype. A closure-assigned `this.measure` broke the whole runtime the moment construction order changed (`pageerror: this.measure is not a function`, caught only because the behaviour test reported "no deck runtime"). Constructor calls `reflow()` (prototype method), never a closure field.
