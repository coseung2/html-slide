# Deck runtime contract (`.deck-live`)

Acceptance constants (stage, viewport set, motion properties) live in `references/acceptance.md`.

Class lesson from building a verified deck repo: step/phase CSS that hides content will break the static frame (PDF, screenshot, reduced-motion user, linter) unless every phase rule is gated on a live class.

## The contract

- The deck runtime adds `deck-live` to `<html>` **only** when it runs with motion allowed (`prefers-reduced-motion` off).
- Every phase/step selector in CSS is scoped under `.deck-live` (e.g. `.deck-live .deck-step-0 .pat-state--before`). Without the class, plain CSS renders the accepted (finished) frame — no JS, no animation required.
- The linter measures under `emulate_media(reduced_motion="reduce")` plus a no-transition style tag, with any `deck-step-*` classes stripped: what it sees is what a capture/export sees.
- The presenter state machine is shared infrastructure. Deck-specific HTML may theme the shell and declare phases, but must not replace navigation with its own `go()/next()/prev()` clock. A self-contained build may inline the standard runtime unchanged.
- Activating a slide is not a phase trigger. A stepped slide enters at `data-start` and remains there indefinitely until presenter input.
- One input advances one phase. A phase may internally stagger marks for a few hundred milliseconds, but no timer may advance the machine to the next phase or slide.

## State machine (`deck-motion.js` pattern)

- One `Deck`: `slide` index + `phase` index, both read from the DOM (`data-slide`, `data-step` max, `data-start` clamped to range) — never from a config table, so markup cannot drift from behaviour.
- `next()`: phase up to max, then slide+1 at its `data-start`. `prev()`: phase down to the slide's own start, then slide−1 at its start. Back walks the machine, not the slides.
- `data-start` semantics: transforming slides (before→after, old→new value, swap) carry `data-start="0"` — they open on the *earlier* state and one advance completes them. A behaviour test caught `data-start="1"` here as a real defect: the slide opened on the new value with nowhere to advance to.
- `reflow()` on resize and on `document.fonts.ready`: re-fit the stage and re-emit `deck:reflow` so bound emphasis never sits on a stale box.
- Expose a `__deckGoto(n)` hook so the linter/tester can drive every slide, not just the visible one.
- Reduced motion collapses the machine: `phases()` reads 0, no `deck-live`, complete frame on screen. That collapsed state **is** the pass, not a skip.

## Autoplay defect

On a deck that declares `data-step`, CSS such as:

```css
.deck-live .slide.is-active .metric { animation: pop 420ms both; }
```

is a defect when that animation carries a presentation beat. It starts from slide entry instead of phase state. Bind the beat to `.deck-step-N`:

```css
.deck-live .slide.deck-step-1 .metric { animation: pop 420ms both; }
```

An `animation-delay` may stagger objects within the same phase; it may not serve as a hidden phase sequencer.

## FLIP (`flip()` pattern)

First → mutate → Last → Invert → Play via `element.animate`, transform-only. Translate before scale (scaling first moves the element's own origin). Clear any `will-change` when the animation finishes.

## Behaviour checks

`complete` (no phase state + everything visible under reduced motion) / `presenting` (opens on `data-start`, exact forward walk incl. the clamped end) / `reversible` (exact backward walk) / `settles` (frame complete at the last phase) / `bound` (`data-hl` covers ≥85% of target at 1920×1080, 1280×720, 1024×768 with ≤1.0 unit drift — compare coverage *ratio*, stage scale shrinks pixel gaps) / `still` (target box motionless while its effect plays).

For a multi-slide stepped deck, also prove `idle` (phase is unchanged after waiting longer than the longest beat), `click-forward` / `click-back` (right/left stage halves change exactly one phase), and `static` (static mode advances slides while displaying every final phase).

## Implementation crash to avoid

Methods the constructor calls must live on the prototype. A closure-assigned `this.measure` broke the whole runtime the moment construction order changed (`pageerror: this.measure is not a function`, caught only because the behaviour test reported "no deck runtime"). Constructor calls `reflow()` (prototype method), never a closure field.
