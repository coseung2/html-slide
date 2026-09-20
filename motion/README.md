# Motion library — `motion/`

Fifteen motion recipes for HTML slide decks, grouped by **what the motion
explains** — not by how it looks. Every recipe is a self-contained demo page
in `patterns/`; the shared library is `motion.css` on top of `_base.css`, and
the step/stage runtime is `deck-motion.js`.

## The contract (non-negotiable)

Three rules hold for every recipe:

1. **Only `transform`, `opacity`, `filter`, and `clip-path` animate.**
   `top/left/width/height/margin/padding` are never animated — that is the
   mechanism by which an emphasis drifts off its target. This is why there is
   no `width: 0 → 100%` typewriter anywhere in this library: the box is
   reserved and the glyphs fade.
2. **The end state is the static state.** Declared in plain CSS, no animation
   required. A captured frame, a PDF, or `prefers-reduced-motion` shows the
   same complete frame. Step phases follow the `.deck-live` contract: phase
   rules only apply while the deck runtime is presenting.
3. **Every effect is bound to its target's own DOM** — a descendant, a
   `data-target` sibling, or a target-derived clone. No slide coordinates
   anywhere, so a resize cannot break the alignment.

## The patterns

| Group | Pattern | Demo | Explains |
|---|---|---|---|
| EMPHASIS | `pat-ring` | `emphasis-ring-trace.html` | one object is the subject — trace its outline |
| EMPHASIS | `pat-pulse` | `emphasis-cell-pulse.html` | one cell of a grid, without moving the grid |
| EMPHASIS | `pat-recede` | `emphasis-recede.html` | this one differs — the rest steps back |
| REVEAL | `pat-group` | `reveal-group-stagger.html` | the cluster arrives as one object |
| REVEAL | `pat-line-step` | `reveal-line-step.html` | lines arrive complete, one at a time |
| TRANSFORM | `pat-state` | `transform-before-after.html` | before became after, same box |
| TRANSFORM | FLIP | `transform-flip-move.html` | one object moved here from there |
| QUANTITY | `pat-roll` | `quantity-number-roll.html` | a number changed to this value |
| QUANTITY | `pat-bar` | `quantity-bar-grow.html` | magnitude as length, from the baseline |
| SEQUENCE | `pat-steps` | `sequence-reversible-steps.html` | phases, reversible one at a time |
| CONNECTIVE | `pat-path` | `connective-path-draw.html` | these two are related |
| SWAP | `pat-swap` | `swap-text-in-place.html` | this replaced that, in place |
| TYPE | `pat-type` | `type-syllable-write.html` | the text is being written, per 음절 |
| TRANSITION | `pat-wipe` | `transition-wipe.html` | this scene gave way to that one |
| TRANSITION | `pat-focus-pull` | `transition-focus-pull.html` | same subject, focus resolved |

Standard references: `patterns/index.html` is an annotated gallery — open it in
the same browser window and click through. Each pattern is also documented with
*use-when / do-not-use* comments at the top of its recipe in `motion.css`.

## Verification

Two layers, both runnable:

```bash
# static frame: geometry, binding, contrast, spacing (per slide)
~/.venvs/pw/bin/python ../../tools/slide_lint.py patterns/<demo>.html

# behaviour: static completeness, phase walk, resize binding, layout stillness
~/.venvs/pw/bin/python ../../tests/motion_check.py
```

All 15 patterns pass the linter at 0 errors / 0 warnings, and `motion_check`
drives 134 behaviour checks across them (complete / presenting / reversible /
settles / bound / still / typed / transition).

## Where the numbers come from

Nothing here is invented timing. The budgets implemented by every recipe —

- emphasis 200–300ms, state change 300–450ms, scene 400–700ms
- press feedback `scale(0.97)` at ~140––160ms
- group stagger 30–80ms between members
- `ease-out` for entering/responding, `ease-in-out` for on-screen moves,
  never `ease-in` on UI
- `transform`/`opacity`-only animation, `transform-origin` at the trigger,
  never `scale(0)`

— are the standing consensus of three sources:

1. **emilkowalski/skill** (38.9k★, MIT) — `references/AUDIT.md`
   (§1 Fundamentals, §2 Feel, §3 Performance). "Animate `transform` and
   `opacity` only. `width/height/margin/padding/top/left` trigger layout +
   paint + composite." Custom strong curves over built-in easings.
2. **animationpatterns.art** — duration table, physicality ("never `scale(0)`",
   "origin-aware popovers", "button press feedback"), and the interruptibility
   analysis (transitions retarget mid-flight; keyframes restart — which is why
   rapid triggers use transitions, and why Back is a state machine, not
   a rewind).
3. **Typewriter practice** (CodePen/steps() lineage, MDN `steps()`, and the
   obfuscated-text article family) — the canonical implementation animates
   `width` and is therefore rejected here. What survives the rejection is the
   *per-glyph reveal at a metered pace*: `pat-type` keeps the sentence as real
   laid-out text and changes only opacity. Per-glyph is also why it splits on
   code points, not UTF-16 units.
4. **The FLIP method** (Paul Lewis; Josh Comeau, CSS-Tricks, reactperf) — First,
   Last, Invert, Play. The element *lives* at its new layout position from the
   start and only the transform delta is animated (translate before scale).
   `deck-motion.js` implements this in `flip()`; the View Transitions API is
   the native successor but is unnecessary weight for a deck runtime.

The FLIP-family libraries (GSAP Flip, Framer Motion `layout`, AutoAnimate,
React Flip Move) were studied and deliberately **not** vendored: a deck needs
a kilobyte state machine and one `element.animate` call, not a dependency.
Their collective lesson — *the move is a transform, the layout is not the
animation* — is what the recipes encode.
