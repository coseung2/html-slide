# html-slide

An agent skill for building presentation decks as HTML — with the discipline
enforced by a linter, not by good intentions.

The problem this solves: an agent asked to "highlight the second column" writes
`left: 412px; top: 268px`. It looks right in the screenshot and breaks the
moment the layout or the window changes. Decks also slide into decoration —
every element animating, motion that explains nothing, captions under the
visual, a title in the corner. Those are habits, and habits need a check that
runs.

So this repo is two things at once: a **specification** (`SKILL.md`, the
author's rules tightened into a normative document) and an **enforcement layer**
(`tools/slide_lint.py`, `tests/motion_check.py`) that fails a deck which breaks
the rules — including the rules that can only be checked by rendering the page
in a real browser and measuring boxes.

## What's here

```
SKILL.md                    the rules — §1 type, §3 spacing, §8 motion, §9 binding, §10 state machine, §17 pitfalls
tools/slide_lint.py         the linter: static pass + instrumented browser geometry pass
tools/verify.sh             all four gates in order; exit 0 means deliverable
tools/export_deck.py        final delivery: QA -> 1920x1080 PNG -> PDF + PPTX
tools/lint_all.sh           every shipped deck, one pass/fail total
tests/motion_check.py       behaviour tests: reduced-motion completeness, phase walk, resize binding
tests/linter_selftest.py    proves each rule still fires (fixture vs clean baseline)
tests/fixtures/broken-deck.html    a deck that breaks every checkable rule on purpose
examples/reference-3slides.html    a 3-slide deck that passes, used as the baseline
motion/                     fifteen motion recipes, grouped by what the motion explains
motion/README.md            the contract, the pattern index, and the source trail
references/SOURCES.md       where every timing value and method came from
references/runtime-contract.md     the `.deck-live` / `data-start` contract, in full
references/geometry-qa.md   the anchoring proof, the static checks, and the measurement traps
references/motion-timing.md       every timing value with its source
references/ecosystem-survey.md     the adjacent skill repos, read rather than summarised
assets/fonts/               Pretendard Variable (OFL) — self-hosted, no CDN call
```

## The two failures worth naming

**Emphasis that leaves its target.** The rule is that a highlight is a child of
its target, or a sibling bound by `data-target`, or a clone derived from it —
never a box drawn at slide coordinates. The linter proves the binding: it
renders at 1920×1080, 1280×720 and 1024×768, measures the highlight's overlap
with its target, and fails if the coverage drops or the alignment drifts by
more than one stage unit. The reference deck and the ring/pulse patterns
measure 100% coverage and 0.00 drift at every size.

**Motion that carries meaning.** `transform` and `opacity` are the default
animation properties. `filter` and `clip-path` are conditional effects only
when they explain the scene without moving target geometry. `top`, `width`, `height`, `margin` trigger layout and
paint, which is how a target moves out from under its own highlight. This is
also why the typewriter here does not animate `width`: the box is reserved and
the glyphs fade in, so a Korean syllable is never clipped through its interior. Duration and easing are
not invented here; they come from the published references (see
`references/SOURCES.md`) and the recipes implement them verbatim.

## Running it

```bash
# one deck, geometry and rules (~10s)
~/.venvs/pw/bin/python tools/slide_lint.py examples/reference-3slides.html

# with screenshots written out
~/.venvs/pw/bin/python tools/slide_lint.py deck.html --shots /tmp/shots

# the whole gate: every deck + linter self-test + motion behaviour
bash tools/verify.sh

# final delivery: QA, static frames, PDF and PPTX in one command
python tools/export_deck.py deck.html
# -> dist/deck/frames/*.png + deck.pdf + deck.pptx + lint.json + manifest.json
```

`export_deck.py` uses the same accepted 1920x1080 static frames for both PDF and
PPTX, so the deliverables stay visually identical. The PPTX is a static 16:9
full-frame rendition; HTML remains the source for live motion and presenter
controls. Linter errors abort export by default.

Current state: `reference-3slides.html` and all 15 patterns pass the linter
with 0 errors and 0 warnings; `linter_selftest.py` confirms the fixture still
triggers 17 rule codes (9 errors) while the baseline stays clean;
`motion_check.py` runs 134 behaviour checks, 0 failed.

Requires Playwright (`pip install playwright && playwright install chromium`).
PPTX export also requires `python-pptx`; the exporter auto-detects an installed system Chrome/Chromium when available.

## Sports reports and media safety

For standings, scoreboards and fixture decks, see `references/sports-decks.md`.
The opt-in `motion/sports.css` adds shared-scale comparison bars and target-bound
record emphasis; normal labels, crests and tables stay static. The guide covers
photo/information separation, alpha-fragment inspection, source labeling and
save/reopen safety with the standard presenter shell.

```bash
python tools/sports_qa.py selfcontained-deck.html --out out/sports-qa
python tests/sports_check.py
# Select a Python environment without editing machine-specific paths:
PYTHON=/path/to/venv/bin/python bash tools/verify.sh
```

The sports QA supplements the main linter. It checks five viewport sizes,
including phone portrait and short landscape, with external requests blocked.
It reports image/text collisions, clipping, broken images, chrome occlusion and
layout drift. It does not verify match facts, image identity, rights or subject
cropping; inspect the rendered screenshots. `verify.sh` also runs the 35 sports
and presenter regression checks.

## Korean-first copy

For Korean decks, read `references/korean-copy.md` before final layout polish.
The rule is not "translate every English word"; it is to write titles, section
labels and explanatory copy in natural Korean first, retaining only abbreviations,
brands and quoted/original spellings that genuinely help the audience.

```bash
python tools/copy_lint.py deck.html --strict
```

The copy linter checks `lang="ko"` decks for English-heavy visible strings and
common English template labels. Mark a deliberately retained item with
`data-copy-en-ok`. The linter cannot judge naturalness or translationese reliably;
that remains an editorial pass using the examples in the reference guide.

## The motion library

`motion/patterns/index.html` is the gallery. Fifteen recipes, grouped by what
the motion *explains* rather than how it looks:

| Group | Explains | Recipes |
|---|---|---|
| EMPHASIS | this object is the subject | `pat-ring`, `pat-pulse`, `pat-recede` |
| REVEAL | how the material arrives | `pat-group`, `pat-line-step` |
| TRANSFORM | before became after | `pat-state`, FLIP move |
| QUANTITY | this changed by this much | `pat-roll`, `pat-bar` |
| SEQUENCE | this happens in these steps | `pat-steps` (reversible) |
| CONNECTIVE | these two are related | `pat-path` |
| SWAP | this replaced that | `pat-swap` |
| TYPE | this text is being written | `pat-type` (per 음절) |
| TRANSITION | this scene gave way to that one | `pat-wipe`, `pat-focus-pull` |

Each pattern is a runnable page, documented with *use-when / do-not-use* notes
at its recipe, and linted like any other slide. Start with
`motion/patterns/index.html`; read `motion/README.md` before adding one.

## Layout

The stage is a fixed 16:9 box fitted with a `transform: scale()`, so slide
coordinates are stable and layout never animates on resize. Step phases are
scoped to `.deck-live`, which the runtime only adds when motion is wanted — so
a captured frame, a PDF export, or `prefers-reduced-motion` all show the same
complete slide.

A Korean translation lives in `README.ko.md`.

## License and provenance

The specification, linter, tests, examples and motion library are this repo's
own work. The motion timing values are sourced from MIT-licensed references and
public documentation; `references/SOURCES.md` gives the trail and
`references/` keeps the attributed excerpts. Pretendard Variable is licensed
under the SIL Open Font License (`assets/fonts/`).
