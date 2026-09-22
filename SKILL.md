---
name: html-slide
description: Build, revise and verify self-contained HTML presentation decks by selecting compatible layout, content, visual, theme and semantic-motion modules from a registry. Use for Korean or English slides, sports reports, market briefings, lessons and presentation redesigns. Accept topics, source material, existing HTML or structured deck JSON; deliver final HTML and requested static PDF/PPTX exports. Preserve target-bound emphasis, fixed-stage geometry and accessible static final frames.
---

# HTML Slide Director: modular composition

## Source of truth

Use the repository's executable registry, contracts and compiler. Do not invent a
module ID or select a whole template before deciding what each slide communicates.
The AI interprets the brief and writes a deck specification. The compiler performs
deterministic metadata ranking, compatibility checks and rendering; it does not
contain an LLM, embeddings service, factual research agent or image search service.

## Workflow

1. Establish audience, language, one communication goal per slide, factual sources,
   information density and available media. Research changing facts before authoring.
   Label synthetic examples. Never fill missing facts with plausible numbers.
2. Discover available modules and their actual data contracts:
   `python tools/compose_deck.py catalog`.
   Narrow candidates with `search --intent ranking --theme sports-broadcast`.
3. Write a version-1 JSON specification against `core/deck.schema.json`. Use an
   explicit goal and intent on every slide. A preset is an editable starting
   combination, never a mandatory page sequence.
4. Run `plan deck.json --out plan.json`. Inspect selection reasons, rejected layouts,
   slot capacities and repetition warnings. Revise or split crowded slides rather
   than truncating text or shrinking typography.
5. Build with `python tools/compose_deck.py build deck.json --out deck.html`.
   For a verified typography baseline, explicitly supply an authorized local
   WOFF2 with `--font path/to/font.woff2`. The full repository's existing font asset
   may be used in the working environment. Do not assume the compiler embedded a
   font unless that flag was supplied: the default emits a system-font warning.
6. Run `python tools/verify_modular.py deck.html --out dist/qa` and inspect the
   screenshots. Correct all errors. Test meaningful live phases and their reversal,
   static mode, reduced motion, overview, keyboard navigation and no-JS output.
7. Export requested static formats through
   `python tools/export_modular.py deck.html --out dist/export`.
   It re-runs QA and uses the same 1920x1080 frames for PDF and PptxGenJS PPTX.
   PPTX is a static full-frame rendition, not editable text/chart objects.
8. Deliver the actual HTML attachment, requested exports and an accurate verification
   summary. Report any font, factual-source, media or coverage limitations.

Commands after `catalog` share the prefix `python tools/compose_deck.py`.

## Composition contract

- `themes/`: appearance tokens only. Never change slot geometry in a theme.
- `modules/layouts/`: named slots, capacities, allowed block types and spatial CSS.
- `modules/content/`: data schemas and renderers for information.
- `modules/visuals/`: images and logos; use explicit `contain` or `cover` choices.
- `modules/motion/`: supported targets/intents and purpose-bound effects.
- `presets/`: ordinary validated specs; every choice remains overridable.
- `core/`: registry, planning, safe rendering, fixed stage and presenter state.
- `templates/`, `motion/` and the original exporter remain legacy compatibility
  paths in the full repository. Do not mix the old and new runtime in one HTML file.

## Non-negotiable scene rules

Keep a uniformly scaled 1920x1080 stage and 5% safe area. Bind every highlight to
its real target as a child, not to guessed stage coordinates. Preserve complete
static final frames in plain HTML/CSS; JavaScript and motion may explain but may
not carry otherwise missing information. Gate live phase effects on `.deck-live`.

Keep one point per slide, at most three typography levels, readable projection
sizes and varied copy placement. Keep Korean copy Korean-first with `keep-all`;
use intentional technical names rather than decorative English scaffold. Prefer
concrete labels; avoid tiny bottom explanations, pill chips, leader lines and
unmotivated visual decoration. Let evidence determine the visual, not vice versa.

Require a meaningful `reason` for every motion, a valid target and a supported
intent. Do not animate every element or apply blanket fade-up to every slide.
Static mode, reduced motion and print must present the same complete information.

Use only trusted local raster assets within the declared asset root. The compiler
embeds PNG/JPEG/GIF/WebP; it rejects SVG and remote image fetching. Retrieve and
review external media separately, retain source/license information, and never
mistake checkerboard pixels for real alpha transparency.

## Validation and extension

Run `python -m unittest discover -s tests -p 'test_modular.py'` for compiler tests.
Run `python tests/modular_runtime_check.py` for focused runtime/negative-QA checks.
Run browser QA for every finished deck; compilation alone is not visual acceptance.
The current QA harness uses `set_content` and therefore does not certify first-load
URL query/deep-link behavior. Inspect the report's coverage notes.

Read [architecture](references/modular-architecture.md) for boundaries and
[authoring](references/module-authoring.md) before adding a module. Read
[migration](references/migrating-v1.md) when working on an existing deck.
Preserve older accepted decks and compatibility tools. Do not commit build caches,
QA screenshots, export binaries or delivery ZIPs; commit maintained source and
finished example HTML only when repository changes are requested.
