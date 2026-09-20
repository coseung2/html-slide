# Motion timing — the values and where they come from

Nothing here is invented timing. These are the consensus values across the
references listed at the bottom; the recipes implement them verbatim.
Disagreeing with a number means disagreeing with the source, not the recipe.

| Item | Value | Source |
|---|---|---|
| Press feedback | `scale(0.97)`, 100–160ms, `ease-out` | emilkowalski §2, animationpatterns Physicality |
| Small UI state | 150–250ms | animationpatterns Duration |
| Emphasis (stroke/ring/trace) | 200–300ms | deck budget, emilkowalski §1 |
| State change / morph | 300–450ms | deck budget |
| Scene transition | 400–700ms | deck budget |
| UI ceiling | under 300ms unless justified | emilkowalski §2 |
| Group stagger | 30–80ms between members, never blocking interaction | animationpatterns Stagger |
| Entering / responding easing | `ease-out` or a strong custom cubic-bezier (`cubic-bezier(0.23,1,0.32,1)`); **never `ease-in` on UI** | emilkowalski §1, animationpatterns Easing |
| On-screen movement easing | `ease-in-out` (`cubic-bezier(0.77,0,0.175,1)`) | animationpatterns Easing |
| Animatable properties | `transform` + `opacity` only (plus `clip-path` for wipes); `top/left/width/height/margin/padding` trigger layout + paint + composite | emilkowalski §3 |
| Entrances | from `scale(0.9–0.97)` + `opacity: 0`; **never `scale(0)`** — nothing appears from nothing | animationpatterns Physicality |
| Trigger-anchored II | `transform-origin` from the trigger's rect; modals exempt (centred) | animationpatterns Physicality, emilkowalski §2 |
| Rapid triggers | transitions (interruptible, retargetable), not keyframes (which restart from zero); Back is a state machine, not a rewind | animationpatterns Interruptibility |
| Reduced motion | fewer and gentler, not zero — drop movement, keep comprehension aids | animationpatterns Accessibility |
| Red emphasis | pair with a shape cue (thickness, sweep) — ~6% of men have red-green deficiency | deck rule, WCAG |
| Review bar | every animation must answer "why does this animate"; unjustified motion on frequent elements is a block | open-slide review-animations |

## Why these sources and not the libraries

Surveyed and deliberately **not vendored**: GSAP Flip, Framer Motion `layout`,
AutoAnimate, React Flip Move. A deck needs a small state machine plus one
`element.animate` call, not a dependency — and a dependency is another thing
that can silently break the alignment this repo exists to protect.

Sources: (1) `emilkowalski/skill` AUDIT.md (MIT, 38.9k★) — fundamentals/feel/
performance; (2) `animationpatterns.art` catalog — duration/physicality/
stagger/interruptibility/accessibility; (3) `open-slide` review-animations +
STANDARDS.md (MIT) — the "justified motion" blocking bar; (4) FLIP method
(Paul Lewis; Comeau, CSS-Tricks, reactperf explainers) — shared-element moves
without layout animation.

Longer excerpts live beside the implementing code: `SOURCES.md`,
`emilkowalski-audit-excerpt.md`, `animation-patterns-notes.md`,
`review-animations-summary.md`. **Rule text in `SKILL.md` always wins over
this file on conflict.**
