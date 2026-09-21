# html-slide

**English** · [한국어 README](README.ko.md)

A reusable skill for building HTML presentation decks with **measured layout, deterministic QA, motion discipline, Korean copy checks, and one-command export**.

The repository does not prescribe one visual style. The core is a **specification + enforcement layer** that applies to any deck. Optional visual directions live under `templates/` and should be used only when they match the requested format.

## Core pieces

- `SKILL.md` — authoring rules and markup contract
- `tools/slide_lint.py` — static checks + real-browser geometry checks
- `tests/motion_check.py` — motion, phase and target-binding regressions
- `tools/copy_lint.py` — Korean-first visible-copy lint
- `tools/export_deck.py` — accepted frames -> PNG + PDF + PPTX
- `templates/` — optional visual starting points
- `motion/` — reusable motion patterns grouped by what they explain

The goal is simple:

> **Do not ship a deck that only looks correct in one screenshot.**

---

## Quick start

```bash
pip install playwright
playwright install chromium
```

For PPTX export:

```bash
pip install python-pptx
```

Lint one deck:

```bash
python tools/slide_lint.py examples/reference-3slides.html
```

Save QA screenshots:

```bash
python tools/slide_lint.py examples/reference-3slides.html --shots out/shots
```

Run the whole repository gate:

```bash
bash tools/verify.sh
```

A deliverable state ends with:

```text
ALL GREEN
```

---

## Core rules

### Bind emphasis to the real target

A highlight must be structurally linked to what it emphasizes: as a child, through `data-target`, or from a target-derived clone.

Do not draw a highlight at arbitrary slide coordinates.

The linter measures target/highlight geometry across multiple viewport sizes and fails drifting emphasis.

### One core point per slide

The title, explanation and visual should all support one claim or relationship.

Prefer showing over explaining. A useful default is roughly **70% visual / 30% copy**, adjusted to the content rather than enforced as a template.

### Motion explains relationships

Default animation properties are `transform` and `opacity`.

Use motion to explain things such as:

- this object is the subject
- before became after
- this value changed by this much
- these steps happen in order
- these objects are connected

Do not animate every object for decoration.

### Static state is the accepted state

A captured frame, reduced-motion mode, print, PDF and PPTX must still show the complete message.

Live presentation motion is scoped to `.deck-live`.

### Keep one fixed coordinate system

Author at 1920×1080 and scale the stage as one unit with `transform: scale()`.

This keeps geometry, line breaks, emphasis and accepted-frame export stable across windows and projectors.

### Templates are optional starting points

Files under `templates/` are **visual grammars, not core rules**.

Use one when it matches the user's requested format. If the content does not fit, recompose the scene instead of forcing the template.

---

## Templates

Two reference directions are currently included.

### Broadcast data report

`templates/sports-broadcast.html`

A dark, high-contrast, data-heavy direction for scoreboards, rankings, comparisons and media-heavy reports.

Domain-specific details stay in [its own guide](templates/sports-broadcast.md), not in the core README.

### Lecture / editorial explanation

`templates/lecture-editorial.html`

A light editorial direction with one accent color, large examples, cause/result scenes, steps and before/after comparison.

See [its guide](templates/lecture-editorial.md).

Template policy and extension rules live in [templates/README.ko.md](templates/README.ko.md).

---

## Korean-first copy

For Korean decks, write audience-facing copy in Korean first rather than translating English scaffolding after layout.

Keep English when it is genuinely faster or canonical: technical acronyms, official product names, standards, quoted phrases, sources or metadata.

Examples:

| Avoid by default | Prefer |
|---|---|
| KEY TAKEAWAYS | 핵심 정리 |
| NEXT STEPS | 다음 단계 |
| PROJECT OVERVIEW | 프로젝트 개요 |
| STATUS | 상태 |
| SUMMARY | 요약 |

Run:

```bash
python tools/copy_lint.py deck.html --strict
```

Mark a reviewed exception with `data-copy-en-ok`.

Detailed editorial guidance is in [references/korean-copy.md](references/korean-copy.md).

---

## Verification gates

`tools/verify.sh` runs five layers:

1. all shipped deck lint
2. linter self-test
3. motion behaviour regressions
4. presenter and template regressions
5. Korean-copy linter self-test

`tools/lint_all.sh` covers HTML in:

- `examples/`
- `motion/patterns/`
- `templates/`

The linter checks clipping, safe insets, text overflow, target binding, typography budgets, Korean `keep-all`, spacing, bottom-caption patterns and animation properties that move layout.

`tests/motion_check.py` currently drives **134 behaviour checks**.

The presenter/template regression suite currently contains **35 checks**.

The copy-lint self-test currently contains **8 checks**.

---

## Motion library

`motion/patterns/index.html` is the gallery.

Patterns are grouped by **what the motion explains**:

| Group | Explains | Patterns |
|---|---|---|
| EMPHASIS | this object is the subject | `pat-ring`, `pat-pulse`, `pat-recede` |
| REVEAL | how material arrives | `pat-group`, `pat-line-step` |
| TRANSFORM | before became after | `pat-state`, FLIP |
| QUANTITY | how much changed | `pat-roll`, `pat-bar` |
| SEQUENCE | ordered phases | `pat-steps` |
| CONNECTIVE | these objects are related | `pat-path` |
| SWAP | this replaced that | `pat-swap` |
| TYPE | text is being written | `pat-type` |
| TRANSITION | one scene gives way to another | `pat-wipe`, `pat-focus-pull` |

Read [motion/README.md](motion/README.md) before adding a new pattern.

---

## Final export

Do not hand-rebuild PDF or PPTX after the HTML is accepted.

`tools/export_deck.py` lints the deck, captures the accepted 1920×1080 static frames, and feeds the same PNGs to both PDF and PPTX.

```bash
python tools/export_deck.py deck.html
```

Optional destination:

```bash
python tools/export_deck.py deck.html --out dist/deck
```

Output:

```text
dist/deck/
├── frames/
├── deck.pdf
├── deck.pptx
├── lint.json
└── manifest.json
```

HTML remains the live presentation source. PDF and PPTX are static delivery formats.

---

## Repository structure

```text
SKILL.md                  core authoring rules

tools/
├─ slide_lint.py
├─ copy_lint.py
├─ media_qa.py
├─ export_deck.py
├─ lint_all.sh
└─ verify.sh

tests/
├─ linter_selftest.py
├─ motion_check.py
├─ template_runtime_check.py
├─ copy_lint_selftest.py
└─ ...

templates/
├─ README.ko.md
├─ sports-broadcast.html
├─ sports-broadcast.md
├─ lecture-editorial.html
└─ lecture-editorial.md

motion/
├─ deck-motion.js
├─ deck-shell.js
├─ motion.css
├─ README.md
└─ patterns/

references/
├─ korean-copy.md
├─ runtime-contract.md
├─ geometry-qa.md
├─ motion-timing.md
└─ SOURCES.md
```

## License and provenance

The specification, linter, tests, examples, templates and motion library are this repository's work.

Timing and method references are documented in `references/SOURCES.md`.

Pretendard Variable is distributed under the SIL Open Font License in `assets/fonts/`.
