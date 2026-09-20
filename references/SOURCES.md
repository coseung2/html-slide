# Source trail — where the motion numbers and methods come from

This repo implements values; it does not invent them. The full provenance for
each claim lives in the files below. All three are MIT-licensed (emilkowalski,
open-slide) or public documentation (animationpatterns.art, FLIP explainers),
so short attributed excerpts are kept here alongside the rules they justify.
Rule text always wins over this file; this file only says *who said it first*.

| # | Source | File here | Justifies |
|---|--------|-----------|-----------|
| 1 | emilkowalski/skill (38.9k★, MIT) — AUDIT.md §1–3 | `references/emilkowalski-audit-excerpt.md` | transform/opacity-only; custom easings; press feedback; no scale(0) |
| 2 | animationpatterns.art — full catalog | `references/animation-patterns-notes.md` | duration table; stagger 30–80ms; ease-out/ease-in-out choice; transitions-vs-keyframes interruptibility |
| 3 | open-slide `review-animations` + `STANDARDS.md` (7.6k★, MIT) | `references/review-animations-summary.md` | the "justified motion" bar: why-is-this-animating as a blocking review standard |
| 4 | Paul Lewis FLIP; Comeau / CSS-Tricks / reactperf explainers | `motion/README.md` "Where the numbers come from" + `deck-motion.js flip()` | shared-element moves without layout animation |

The libraries that also do this (GSAP Flip, Framer Motion `layout`,
AutoAnimate, React Flip Move, View Transitions API) are surveyed in
`motion/README.md` and deliberately not vendored.
