---
name: html-slide
description: Use when making an HTML presentation deck. Directed-scene composition rules plus a real geometry linter for target-bound emphasis.
---

# AI Commercial Slide Director

Build presentation slides as directed scenes, not as template-filled lecture pages.

The goal is a deck that reads instantly, feels visually intentional, and uses motion only when it explains a relationship, comparison, or transformation.

**The rule that this deck type lives or dies on:** every focus/highlight effect is bound to the real target element. If emphasis can drift from the thing it emphasizes, the deck is broken no matter how good the typography is. §9 states it, `tools/slide_lint.py` enforces it.

## 0. Verification is not optional

Every clause below that says *visually*, *tight*, *oversized*, *crooked*, or *aligned* is a claim about measured geometry. Do not assert those claims from reading source. Measure them:

```bash
# everything, in order: all decks + linter self-test + motion behaviour
bash tools/verify.sh

# geometry + binding + contrast + spacing, per slide, with screenshots
python tools/slide_lint.py deck.html --shots out/

# static rules only (no browser; fast, runs on any machine)
python tools/slide_lint.py deck.html --no-browser

# behaviour: phase walk, resize binding, reduced-motion completeness
python tests/motion_check.py
```

Exit code 0 means no errors. Warnings do not block; errors do. Deliver a deck only at **0 errors**.

A slide is not "done" because the markup looks right. It is done when the linter agrees.

### Standard delivery export

For a finished deck, do **not** hand-build PDF or PPTX. Run the exporter:

```bash
python tools/export_deck.py deck.html
# optional destination
python tools/export_deck.py deck.html --out dist/deck
```

The exporter is the standard delivery path. It runs the linter first, captures every accepted static final frame at **1920×1080**, then builds both **PDF** and **16:9 PPTX** from the exact same PNG frames. This keeps HTML/PDF/PPTX visually identical. It also writes `lint.json`, `manifest.json`, and `frames/slide-NNN.png`.

Use `--skip-lint` only when the user explicitly wants an unverified emergency export. Normal delivery must stop on linter errors. PPTX is intentionally a full-frame static rendition; HTML remains the source for live motion and presenter controls.

Runtime dependencies: Python Playwright + Chromium and `python-pptx`. The exporter uses an installed system Chrome/Chromium automatically when available.

### The linter is itself tested

A rule that stops firing produces a clean report, and a clean report is indistinguishable from a passing deck. `tests/fixtures/broken-deck.html` is a deck that breaks every checkable rule on purpose, and `tests/linter_selftest.py` asserts each rule still fires while `examples/reference-3slides.html` stays clean. Silence from the linter is therefore always a decision, never an accident.

The linter answers *"is the static frame correct"*. A second layer answers what a linter cannot: whether the motion claims hold while the page is alive. `tests/motion_check.py` covers six categories — **complete** (nothing hidden under reduced motion), **presenting** (opens on `data-start`, one phase per advance), **reversible** (Back undoes one phase at a time), **settles** (last phase restores a complete frame), **bound** (a highlight covers ≥85% of its target at 1920×1080, 1280×720 and 1024×768, drift ≤1.0 stage unit), **still** (the target's box never moves while its effect plays).

### Markup contract

The linter needs anchors in the DOM. These attributes are the contract — they are cheap to add and they are what makes the checks possible:

| Attribute | Applies to | Meaning |
|---|---|---|
| `data-stage` | one wrapper | The 1920×1080 stage (contains `--stage-w/--stage-h`) |
| `data-slide` | each slide root | One slide; one core point |
| `data-copy` | copy cluster | The title + body cluster (§3) |
| `data-visual` | visual cluster | The example / mockup cluster |
| `data-hl` | emphasis element | A highlight whose binding will be verified (§9) |
| `data-target` | on `data-hl` | Selector of the element it emphasizes (`#id` or a CSS selector) |
| `data-step` | on `data-hl` | Which animation phase it belongs to (§10) |
| `data-bleed` | full-bleed art | Explicitly allowed to exceed the safe inset |
| `data-motion-ok` | any element | Guard for one deliberate exception; requires a comment |
| `data-copy-en-ok` | intentional English copy | Exempt one reviewed English label/name from Korean copy lint (§3) |

Everything else is free. The linter is deliberately permissive about structure and strict about geometry.

### What the linter checks

Errors: out-of-stage / clipped content, text overflow, unbound or drifting emphasis, mid-animation layout properties, contrast below threshold, missing `keep-all` on Korean body copy, `scale(0)`, hard-coded highlight coordinates.

Warnings: type levels over budget, font-size below the projection floor, internal gaps over the proximity limit, forbidden chip/callout/leader-line patterns, bottom captions, external font hosts, `transform-origin: center` on trigger-anchored objects, `letter-spacing` on Hangul.

## 1. Hard rules

Apply these unless the user explicitly overrides them.

- Use **Pretendard Variable** as the presentation font, **self-hosted** (§13). A CDN font is a defect: offline it renders as fallback metrics and every alignment you verified is invalid.
- Use **no more than three typography levels** across the deck:
  1. title / key statement
  2. main body / primary UI number
  3. secondary UI text / labels
  Weight and color are *tools inside* a level, not a fourth level. Raising a level means promoting text up this list, not adding a size.
- Do **not** use conversational or spoken-style slide titles. Prefer concise noun phrases or declarative fragments.
- Do **not** make titles excessively large. The title must share the scene with the example, not dominate the entire viewport. Caps: title ≤ 96px, and the copy cluster ≤ 35% of the stage area (§13).
- Do **not** lock every title to the top-left. Place the title where the composition has the strongest visual focus — and make it real: **at least one slide in three must place the copy cluster somewhere other than top-center/top-left.** A rule that no slide violates is not being applied.
- Do **not** use pill chips, floating callout chips, or leader-line annotations.
- Do **not** add small explanatory captions at the bottom of slides.
- Do **not** animate every object individually. Whole groups may appear at once.
- Do **not** use meaningless decoration: gradients, glow, shadows, borders, or rounded containers must have a reason.
- One slide should communicate one core point.
- Prefer showing over explaining. Default balance: example/visual **70%**, text **30%**.

**The accepted frame must be complete without motion.** Gate every step/phase CSS rule on a `.deck-live` class that only the deck runtime adds to `<html>`. Without it — JS disabled, file opened from disk, `prefers-reduced-motion`, PDF export, screenshot — the browser renders the finished frame from plain CSS alone. A transforming slide (before/after, number roll, swap) opens on the *earlier* state via `data-start="0"` so that one advance completes it; `data-start="1"` on such a slide leaves nowhere to advance to. Motion replays how the frame got there; it never carries the meaning. Full contract: `references/runtime-contract.md`.

## 2. Stage and coordinate system

Target-bound emphasis (§9) is only meaningful against a fixed coordinate system. Define it once, at the top of the deck:

```css
#stage {
  width: 1920px; height: 1080px;      /* the only coordinate system that exists */
  position: relative; overflow: hidden;
  transform: scale(var(--k));          /* --k = min(vw/1920, vh/1080) */
  transform-origin: top left;
}
```

- **Fixed 1920×1080 stage, scaled as a whole.** Reflowing layout is what makes highlights drift. Scale, don't reflow.
- **Letterbox, never stretch.** `--k` uses `min()`. If you use separate x/y scales, circles become ellipses and every radius trace lies.
- **4:3 and 16:10 projectors are still common in classrooms and venues.** A 16:9 stage on a 4:3 projector loses its left and right edges. Keep everything meaningful inside a **5% safe inset** on every side; let only backgrounds bleed to the edge, and mark those `data-bleed`.
- **Units inside the stage are CSS px, never viewport px.** `calc()` against `vw` or `vh` inside the stage breaks the invariant the linter tests.
- **Never** size a highlight against the viewport. Size it against its target.

## 3. Copy style

### Korean-first decks

When the deck language is Korean, write the slide copy **in Korean first**. Do not design an English deck and translate labels afterward.

- Keep titles, section names, metric labels and explanatory copy in natural Korean by default.
- Retain English only when it is the established form the audience actually reads faster: league/product acronyms (`EPL`, `VAR`, `AI`, `HTML`), short team codes (`MCI`, `ARS`), official brand names, source titles, or an intentionally quoted phrase.
- Transliterate familiar people/team names into Korean in audience-facing prose when that is the normal Korean editorial form. Keep the original spelling in sources or metadata when useful.
- Do not leave template English such as `TOP SIX MARKET REPORT`, `TITLE RACE`, `THE PACK`, `NEXT UP`, `POINTS`, `GOALS`, or `FORM` merely because it looks "broadcast-like". Korean sports graphics get their tone from compression and hierarchy, not from unnecessary English.
- Avoid literal translation syntax. Rewrite for the Korean audience's reading order and register instead of preserving English noun stacks, abstract verbs, or source sentence structure.
- Prefer concrete newsroom/editorial verbs and nouns: `단독 선두`, `승점 3점 차`, `득점 선두`, `상위권 판도`, `다음 라운드`, `핵심 정리`. Avoid vague constructions such as `~을 설명한다`, `~을 재검증한다`, or `~의 시그널` when a direct Korean label says the same thing.
- Use `data-copy-en-ok` only for reviewed exceptions. It is not a blanket escape hatch for an English-heavy slide.

For detailed before/after examples, sports phrasing, and the final editorial pass, read `references/korean-copy.md`. For Korean decks, run `python tools/copy_lint.py deck.html --strict` before delivery; it catches excessive/template English but does **not** certify that prose sounds natural.

### Titles

Short. Non-conversational. Prefer noun phrases or compact declarative phrases. Avoid questions and chatty hooks unless the user explicitly asks for them.

Good:

```
프론트엔드 생성의 자동화
반복되는 시각 문법
AI Slop의 원인
```

Avoid:

```
근데 왜 다 비슷하지?
이제 됐을까요?
AI가 왜 이러는 걸까요?
```

### Body

Use terse, list-like Korean. Avoid long prose. Prefer one concept per line. If a line explains an example, place it **physically close** to that example.

### Reading order

Default hierarchy: **Title → main body → example**.

Do not place the main body above the title unless the slide is intentionally poster-like and the user asked for that treatment.

### Body placement rule

Treat title and body as **one copy cluster**. Place that cluster according to its relationship with the main visual:

| Main visual | Copy cluster |
|---|---|
| centered below | top-center |
| on the right | left, vertically aligned to the visual |
| on the left | right |
| none (text-only thesis) | near the optical center |

Do not let body copy float independently between title and example. Body position is determined by the main visual anchor, not by filling empty space.

**Line breaks must follow semantic units.** Never break a phrase simply to balance a text box. In Korean this means `word-break: keep-all` (§13) — without it the browser will split `프론트엔드` mid-word and no amount of care in the source will prevent it.

## 4. Spacing system

The deck should feel spacious globally but compact locally.

**Core principle: large outer margin + small internal gap.** Whitespace belongs *around* the content cluster, not *between* related objects.

Use an 8px-based system:

| Relationship | Gap |
|---|---|
| title ↔ body | 12–24px |
| body ↔ example | 24–40px |
| related UI objects | 8–24px |
| major scene separation | 48–64px |
| **any two objects meant to be read together** | **never 80px+** |

**Proximity rule.** If two objects explain each other, keep their visible gap ≈ 40px or less unless scale requires otherwise.

Do not judge spacing only by CSS grid column width. Judge the **actual visible gap between content bounds** — which is what the linter measures, including padding, margin collapse, and transforms.

## 5. Composition

Treat every slide as a commercial frame.

- Do not repeat one template across the deck. Recompose each slide around its message.
- Use asymmetry when it improves focus.
- Allow generous empty space at the outer edges.
- Keep related content in one visual cluster.
- Avoid the common pattern of title at top → **huge gap** → body → **huge gap** → mockup.
- Use the full 16:9 frame intentionally, but do not stretch content merely to fill space.

Typical compositions:

**Text + example** — compact text cluster on one side, example immediately adjacent, gap between clusters visibly tight.

**Text-only thesis** — remove mockups if they dilute the point. Pull the copy toward the optical center. Use scale, weight, or a single accent to create hierarchy.

**Example-led** — make the example the dominant object. Put terse explanatory lines close to the relevant example area.

## 6. Alignment

Alignment is a hard quality requirement.

- Use Grid/Flexbox alignment rather than manual pixel nudges whenever possible.
- Text inside buttons, badges, cards, or centered objects must be **visibly centered on both axes** when intended.
- Use `display:flex/grid`, `align-items`, `justify-content`, and explicit `line-height` to stabilize alignment.
- Repeated objects must share baselines, edges, and internal padding.
- Check **optical** alignment, not only numeric alignment.
- Never leave text visually crooked inside a container.

Mechanically: text content boxes must be centred to within 1px of their container's centre on the intended axis, and repeated objects must share their baseline within 2px. Remedy for a 1–2px error is a line-height or font-metric fix, never a `padding-top: 3px` nudge.

## 7. Mockups

Mockups should feel like believable product UI, but remain presentation-safe.

- Simplify enough to stay legible at presentation scale.
- Keep the entire important example visible; do not crop meaningful content accidentally.
- Avoid putting presentation commentary inside the mockup. Presentation copy belongs outside the mockup.
- Use **real DOM/CSS objects** instead of flattened screenshots when motion or focus effects are required — a screenshot cannot host a target-bound highlight.

## 8. Motion direction

Motion is explanatory, not decorative.

**Use motion for:** compare / before-after, focus / inspection, transformation, cause-and-effect, state changes, revealing the mechanism behind a visual pattern.

**Avoid:** every text line sliding in separately, unnecessary fade-up on every object, motion whose only purpose is "making the slide feel alive".

### Budgets

| Motion | Duration |
|---|---|
| emphasis (stroke sweep, ring, trace) | 200–300ms |
| state change / morph | 300–450ms |
| scene transition | 400–700ms |
| any UI element | under 300ms unless justified |

Entering elements use `ease-out` or a strong custom cubic-bezier. **`ease-in` on UI is a defect** — it delays the part the viewer watches most. Built-in CSS easings are too weak; expect custom curves.

**Animate `transform` and `opacity` only.** `top`, `left`, `width`, `height`, `margin`, and `padding` trigger layout, and a layout-triggering animation is precisely the mechanism by which emphasis drifts away from its target. This is an error, not a warning.

### Scene-level motion

Prefer **one or two meaningful beats per slide**. Examples:

- a finished UI replaces a generation skeleton
- a repeated visual pattern is highlighted
- a UI state transforms into another state
- a single thesis statement resolves from blur to sharp focus

### Emphasis must survive as a state

An animation that ends by removing itself leaves nothing behind. When the same slide is viewed statically — a PDF export, a screenshot, a `prefers-reduced-motion` user — the emphasis must still be visible.

**Rule: motion explains, state remains.** A highlight animates in and *stays*. The final frame of every emphasis beat is a valid static frame.

Under `prefers-reduced-motion: reduce`, skip the transition and render the **end state immediately**. Never drop the emphasis itself.

### Emphasis motion

When inspecting a visual detail, the emphasis should feel like a commercial motion graphic. Example for radius:

- The actual target object becomes the source of emphasis.
- The target enlarges, or clones into an enlarged detail view.
- A thick red stroke sweeps along the **actual** rounded corner.
- The motion ends quickly and leaves the viewer with a clear inspected feature.

**Do not use detached annotation lines or globally positioned overlays that merely approximate the target.**

Red alone is not sufficient emphasis: ~6% of men have red-green deficiency. Pair the stroke with a shape cue (thickness, sweep) or a contrast cue so the emphasis reads in grayscale.

### Motion timing comes from outside

Deck timing is not invented here. Press feedback (100–160ms), small UI state
(150–250ms), stagger (30–80ms per member), easing (`ease-out` for entering and
responding, `ease-in-out` for moving on screen, never `ease-in` on UI), and
`transform`/`opacity`-only animation are the standing consensus across the
major web-animation references. The recipes implement those values verbatim —
see `motion/README.md` for the source trail and `references/motion-timing.md`
for the full table with per-value provenance. Disagreeing with a number means
disagreeing with the source, not the recipe.

## 9. Target-bound effects — mandatory

All focus/highlight effects must be attached to the real target element.

- Prefer **pseudo-elements, child overlays, or target-derived DOM clones**.
- **Never** hard-code slide-level coordinates for highlights.
- The effect must stay aligned when the browser or mockup changes size.
- If a target is resized, the highlight must follow **automatically**, with no recomputation step the author has to remember to run.

Mandatory for: red borders, sweep lines, radius traces, focus masks, zoom-ins, dimming of non-target elements.

### How to bind

Mark the emphasis element with `data-hl` and point it at its target:

```html
<button class="btn" id="cta">생성</button>
<span class="hl-sweep" data-hl data-target="#cta"></span>
```

Allowed forms, in order of preference:

1. **Descendant** — the highlight is a child of the target and positioned with `inset:0` / percentages. Cannot drift; there is nothing to drift from.
2. **Target-derived clone** — for zoom-ins, clone the target (`target.cloneNode(true)`)
   and wrap it; a clone carries its own geometry. The reference for why this
   class of transform is correct is the FLIP method (measure → mutate → animate
   the difference; see `motion/README.md` for the source trail) — and the rule
   "translate before scale" is honoured in `deck-motion.js`'s `flip()`.
3. **Sibling overlay bound by `data-target`** — allowed only when 1 and 2 are impossible, and the linter verifies the binding and the resize invariance.

Disallowed: an overlay positioned with slide coordinates, a highlight whose selector was correct when written and silently rots when layout changes, an annotation line drawn from outside the target.

### Detection patterns

When reviewing a deck by hand, hunt for exactly these:

```bash
# emphasis positioned by slide coordinates
rg -n 'data-hl|class="[^"]*(highlight|ring|sweep|mask|dim|trace|zoom)' -A3 | rg -n 'left:|top:|inset: *[0-9]'

# layout-triggering animation (the root cause of drifting emphasis)
rg -n 'transition[^;]*(top|left|right|bottom|width|height|margin|padding)'
rg -n '@keyframes' -A15 | rg -n '(top|left|width|height):'

# nothing appears from nothing
rg -n 'scale\(0\)'

# origin-anchored objects whose origin is the centre
rg -n 'transform-origin: *center' -B4 | rg -n 'popover|tooltip|dropdown|menu|scale\('
```

The linter runs these as static checks and then **verifies the result in a real browser**: it resolves each `data-hl` target, measures the highlight's offset relative to that target, and re-measures at 1280×720 and 1440×900. If the offset moves, the binding is not real.

The linter cannot guess intent. If a deliberate exception exists, mark it `data-motion-ok` and say why in a comment.

## 10. Step sequencing and Back

When a slide has step animations, the deck has a **state machine**, not a set of slides. Model it as one:

```js
// one phase index per slide; Back walks the machine backwards, not the slides.
// The implementation lives in motion/deck-motion.js and is exercised by
// tests/motion_check.py — data-start, one phase per advance, and the complete
// frame when reduced motion is on.
const steps = { 3: 2, 4: 1 };          // slide index -> phase count
let phase = {};                        // slide index -> current phase (0 = none)
```

Rules:

- **Back must reverse one animation phase at a time before changing slides.** Forward steps, backward steps, then slide change — in that order, never mixed.
- Each phase is declared in markup with `data-step="N"`, so phase state is readable and testable rather than inferred from CSS class names.
- A phase must be **idempotent**: replaying it from any prior phase produces the same final state. Forward, back, forward must land in the same visual state as forward alone.
- **On resize, re-measure the current phase's highlights immediately.** Resizing with an emphasis on screen is the most common way a bound highlight silently becomes unbound.
- `prefers-reduced-motion` collapses the machine: one step per slide, every phase rendered in its end state.

Keep presentation controls minimal: Arrow keys / Space / Enter advance; Back reverses one phase, then changes slides; optional slide number; optional progress bar. Do not add bottom explanatory captions.

## 11. Revision discipline

When the user asks to change only one dimension, **preserve the others**.

| Request | Preserve |
|---|---|
| "change the entrance motion" | copy, layout |
| "reduce spacing" | the visual concept |
| "fix alignment" | no new decoration |
| "make motion stronger" | composition, unless motion cannot work without a structural change |

Treat the latest accepted version as the baseline. Make **surgical edits** — a diff that touches one dimension should touch one dimension.

Before editing, state the baseline: which file, which slide, which element. After editing, re-run the linter and report the before/after error count. If the edit was motion-only, the linter's static and layout findings must be **identical** to the baseline — a motion change that moves geometry is a structural change the user did not ask for.

When a request is ambiguous about which dimension it changes, ask; do not guess by rewriting.

## 12. Deck-level narrative

A deck is not a set of slides that each pass the checklist. It has a shape:

- **Arc.** Open with the claim, develop it, close on the consequence. Three to five movements is usual; a deck with one movement is an article.
- **Rhythm.** Alternate dense and spare slides. Three example-led slides in a row read as a catalogue; follow a dense comparison with a text-only thesis to let it land.
- **Variety floor.** No composition may be used more than twice consecutively. If every slide is "title top-center, mockup below", the deck has one slide printed N times.
- **Transitions mark structure.** A scene change is a movement boundary, not decoration; use them where the argument turns, not on every slide.
- **Dwell time follows density.** A comparison slide needs reading time; a thesis slide needs almost none. Sequence dense slides where the audience is fresh, not at the end.
- **One core point per slide, and the points must be ordered.** If two slides could swap without changing the argument, one of them is not doing work.

Report the arc before generating slides: a one-line claim per slide, in order. If that list is not an argument, the deck is not ready to style.

## 13. Numbers and Korean typography

### Type scale (at 1920×1080)

| Level | Size | Line-height |
|---|---|---|
| title / key statement | 64–96px | 1.15–1.3 |
| main body / primary UI number | 28–40px | 1.6–1.75 |
| secondary UI text / labels | 22–26px | 1.5–1.6 |

**Projection floor: body ≥ 28px, label ≥ 22px.** Below that, the back row cannot read it, and no amount of contrast saves it.

### Contrast

| Text | Minimum ratio |
|---|---|
| body | 4.5:1 |
| large (≥32px, or ≥24px bold) | 3:1 |

### Korean typesetting

- **`word-break: keep-all`** on every Korean body copy container. This is the mechanical form of the "never break a phrase to balance a box" rule.
- **`text-wrap: balance` on titles, `pretty` on body.**
- **Never `letter-spacing` on Hangul.** It widens the gaps between jamo blocks and makes text look broken; letter-spacing is a Latin tool.
- `line-height` per the table above — Hangul needs more leading than Latin at the same size.
- `font-variant-numeric: tabular-nums` on any UI number that sits in a column or animates.
- Titles end without a trailing period; body lines may omit final punctuation.

### Font: self-host it

```css
@font-face {
  font-family: 'Pretendard Variable';
  src: url('assets/fonts/PretendardVariable.woff2') format('woff2-variations');
  font-weight: 45 920;
  font-style: normal;
  font-display: block;   /* block: a late font shift invalidates every measurement */
}
```

`font-display: block` rather than `swap` is deliberate: a metric swap after first paint reflows the deck and moves every highlight. Wait for the font (`document.fonts.ready`) before measuring or entering step animations.

The vendored subset in `assets/fonts/` is OFL-licensed; keep its `LICENSE.txt` beside it.

### Motion numbers

| Motion | Values |
|---|---|
| emphasis | 200–300ms, `ease-out` |
| state change | 300–450ms, custom cubic-bezier |
| scene transition | 400–700ms |
| press feedback | `transform: scale(0.97)`, 160ms `ease-out` |

Entering transforms start at `scale(0.9–0.97)` with `opacity: 0`. **Never `scale(0)`** — nothing in the real world appears from nothing.

## 14. Recommended technical stack

For web-based decks:

- HTML + CSS + JavaScript
- Pretendard Variable, self-hosted
- native CSS transitions/keyframes for simple motion
- GSAP/Flip **only** when layout morphing genuinely benefits from it (FLIP records state → mutate → animate the delta; it is the correct tool when an object must move between two layouts and the emphasis must follow it)
- SVG only for precise shape animation that cannot be expressed directly on DOM elements

Avoid adding frameworks unless the interaction complexity justifies them.

## 15. Slide implementation workflow

1. Identify the one core point of the slide.
2. Decide whether the slide is text-led, example-led, or transformation-led.
3. Write minimal title/body copy first.
4. Build one content cluster with tight internal spacing.
5. Use outer whitespace to frame the cluster.
6. Build mockups as DOM when they need motion.
7. Add only the motion that explains the point.
8. Attach all emphasis effects to actual target elements (`data-hl` + `data-target`).
9. Check alignment at presentation size — with the linter, not by eye.
10. Check that nothing important is cropped.
11. Confirm the slide is understandable in a static frame before relying on animation.
12. Run `python tools/export_deck.py deck.html`; fix any QA errors it reports, then deliver the HTML plus generated PDF/PPTX at 0 errors.

## 16. QA checklist

Before delivering a slide or deck, verify all of the following. The column on the right is what to run, not what to believe.

### Typography
- [ ] Pretendard only, self-hosted — *linter: `external-font`*
- [ ] ≤ 3 type levels — *linter: `type-levels`*
- [ ] title ≤ 96px, not oversized — *linter: `title-size`*
- [ ] title not conversational unless requested — *human*

### Hierarchy
- [ ] title appears before body in the reading order — *linter: `reading-order`*
- [ ] one core point per slide; deck arc reported — *human, §12*
- [ ] no unnecessary microcopy
- [ ] no bottom explanatory caption — *linter: `bottom-caption`*

### Spacing
- [ ] outer margin large, related objects close — *linter: `large-gap`, `loose-pair`*
- [ ] text-to-example gap visually tight — *linter: `copy-visual-gap`*
- [ ] no unexplained 80px+ internal gaps

### Alignment
- [ ] button text centred on both axes — *linter: `text-offcenter`*
- [ ] repeated cards aligned — *linter: `baseline-mismatch`*
- [ ] text baselines stable, nothing crooked
- [ ] repeated objects share internal padding

### Mockups
- [ ] critical UI fully visible — *linter: `clip`, `overflow`*
- [ ] presentation copy outside mockup
- [ ] mockup simple enough for projection — *linter: `min-font`*

### Motion
- [ ] no animation on every element — *human*
- [ ] motion has explanatory purpose — *human*
- [ ] no `top/left/width/height` animation — *linter: `layout-animation`*
- [ ] no `scale(0)` — *linter: `scale-zero`*
- [ ] emphasis survives in a static frame — *linter: `emphasis-state`*
- [ ] target emphasis bound to actual target DOM — *linter: `unbound-highlight`*
- [ ] highlight stays aligned under resize — *linter: `binding-drift`*
- [ ] Back reverses one phase at a time — *test: `tests/motion_check.py`*
- [ ] motion-only revisions did not alter accepted structure/content — *linter diff vs baseline*

### Behaviour (only a live browser can run these)

`tests/motion_check.py` drives every pattern in `motion/patterns/`: **complete** (nothing hides under reduced motion), **presenting** / **reversible** (opens on `data-start`, one phase per advance, Back undoes one), **settles** (last phase restores the full frame), **bound** (highlight covers ≥85% of its target at three viewports), **still** (the target does not move while its effect plays), **typed** (one span per glyph, reserved box, no animated layout property in the chain), **transition** (the active scene settles at rest after a round trip).

`motion/patterns/index.html` lists all fifteen; open it in a browser to see each one move.

The motion library is grouped by **what the motion explains**, never by how it looks: EMPHASIS (`pat-ring`, `pat-pulse`, `pat-recede`), REVEAL (`pat-group`, `pat-line-step`), TRANSFORM (`pat-state`, FLIP), QUANTITY (`pat-roll`, `pat-bar`), SEQUENCE (`pat-steps`), CONNECTIVE (`pat-path`), SWAP (`pat-swap`), TYPE (`pat-type`), TRANSITION (`pat-wipe`, `pat-focus-pull`). Pick the group from the sentence you are drawing, then the recipe from the group; each recipe carries its own *use-when / do-not-use* comment.

## 17. Pitfalls

These are failures that were made and fixed while building this repo. Each one passed a visual check.

- **Never write a phase/step CSS rule that hides content without gating it on the live class.** An ungated `opacity: 0` base state deletes the content the moment motion is off — the exact failure this deck type exists to prevent.
- **Never define a runtime method as a constructor closure when the constructor calls it mid-construction.** A reorder then throws `this.measure is not a function`; the crash gets masked by a defensive closure and the page silently renders unmeasured. Put it on the prototype.
- **Do not assert a step walk from a hand-counted loop.** Record the phase before the first advance and after the last one. Off-by-one walks (`[1,2,3,3]` vs `[1,2,3,3,3]`) pass eyeballing and fail the machine.
- **Baselines are per-row, not per-class.** Group same-class texts by vertical overlap before comparing tops; the second row of a 2×2 grid is a different row, not a misaligned one. Same fix applies to any "repeated objects share X" check.
- **Step membership is ancestor-aware.** An element belongs to a step phase if it *or any ancestor* declares it — walk with `closest('[data-step]')`, not a self-attribute read, or phase siblings read as overlapping copy.
- **Follow local stylesheets.** A linter that only scans inline `<style>` silently checks nothing when the deck links its CSS. Resolve local `<link rel=stylesheet>` targets one hop; skip remote ones.
- **Measure the frame the user exports.** Run the browser pass with transitions and animations disabled and step classes stripped. Anything existing only mid-animation disappears — which is exactly what a PDF or screenshot shows.
- **Compare ratios across viewports, not pixels.** Stage scale shrinks absolute gaps on small viewports; binding drift must be judged on coverage ratio and scale-normalised offsets.
- **A typewriter that animates `width` is a layout animation, and it clips Korean mid-syllable.** `width: 0 → 100%` with `steps()` is the canonical implementation and it is wrong twice: `width` reflows the line every frame, and the clip lands on a pixel boundary, so a 음절's interior strokes get sliced. Reserve the box and change opacity per glyph instead.
- **Probe the whole chain, not the element you were thinking of.** The first version of the typewriter check inspected the glyph spans only, so the classic container-level `width` animation passed it cleanly — the check was green and the deck was broken. When a check guards a mechanism, widen it to every node that could implement the mechanism (here: the container *and* its children), and prove it fails on a deliberately broken fixture before trusting it.
- **A check that runs after the thing it measures is not a check.** The "sentence is whole at the end" probe first ran ~700ms after load, by which time the animation was long over, so it passed at 0ms on a deck that never typed anything. Reload before measuring, and fail on an implausibly short duration as well as on a missing result.
- **A transition is a pair, not a state.** Give the leaving scene its own class and clear it on the next render; do not leave every non-active slide translated, or the next render starts from a moved box. Direction matters too — forwards and backwards must not play the same motion, or Back reads as a bug.
- **Do not hand-place a highlight.** `left: 412px; top: 268px` looks correct in a screenshot and breaks on the next resize. Slide-level coordinates for emphasis are an error, and the linter fails them. Use pseudo-elements, child overlays, or a target-derived clone.

## 18. Reference implementation

`examples/reference-3slides.html` is a working three-slide reference: text + example, text-only thesis, and a transformation beat. Use it as a visual and structural reference. **Preserve the rules above rather than mechanically copying its layout.**

Run the linter on it to see what a passing deck looks like:

```bash
python tools/slide_lint.py examples/reference-3slides.html --shots out/
```

`tools/` also contains an earlier standalone geometry checker (`geometry_qa_stage1.py`) that `slide_lint.py` superseded. Its probe — the anchoring proof in `references/geometry-qa.md` — is what established that target-derived placement holds, so it is kept as the readable reference for the technique.
