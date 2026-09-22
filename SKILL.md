---
name: html-slide
description: Build, revise and verify self-contained HTML presentation decks and matching Remotion videos by selecting compatible layout, content, visual, theme, typography, palette, data-visualization and semantic-motion modules from a registry. Use for Korean or English slides, sports reports, market briefings, lessons and presentation redesigns. Accept topics, source material, existing HTML or structured deck JSON; deliver final HTML, requested static PDF/PPTX exports, and MP4 when requested. Preserve target-bound emphasis, fixed-stage geometry and accessible static final frames.
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
2. Discover available modules and art-direction packs with
   `python tools/compose_deck.py catalog`. Narrow layouts with
   `search --intent ranking --theme sports-broadcast`; inspect style routing with
   `search --type typography --theme education --domain education --audience elementary`.
3. Write a version-1 JSON specification against `core/deck.schema.json`. Use an
   explicit goal and intent on every slide. Keep typography, main palette and dataviz
   at deck scope. Prefer `auto` plus domain/audience/tone/density signals unless the
   user requests a specific visual system. A preset is an editable starting
   combination, never a mandatory page sequence.
4. Run `plan deck.json --out plan.json`. Inspect layout selection reasons, rejected
   layouts, slot capacities, repetition warnings, and the selected typography,
   palette and dataviz packs with their alternatives. Revise or split crowded slides
   rather than truncating text or shrinking typography.
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
9. When the user requests a Remotion video, keep the same validated deck JSON as the
   content source of truth. Choose the semantic motion first. If the user did not
   request a specific expression, use `pattern: "auto"` or inspect candidates with
   `python tools/motion_patterns.py search --intent ... --target ... --semantic ...`
   instead of guessing from the effect catalog. After `video/` dependencies are
   installed, use `python tools/render_video.py deck.json --out dist/video.mp4` as
   the canonical entrypoint. It must compile and validate the storyboard, typecheck
   the runtime, ensure the Remotion browser, render H.264, sample semantic key frames
   and verify the encoded output. Read `references/video-pipeline.md`; do not invent
   a second content spec or add blanket motion absent from semantic motion declarations.
   When an agent can push Git branches but cannot call `workflow_dispatch`, use the
   documented disposable `render/**` transport branch; keep job input under `.render/`,
   never merge that branch, and rely on the workflow cleanup after a successful render.

Commands after `catalog` share the prefix `python tools/compose_deck.py`.

## Composition contract

- `themes/`: design grammar such as corner/border treatment. Never own layout geometry, font families or deck colors.
- `styles/typography/`: deck-level heading/body/number font roles, weights and line-height behavior.
- `styles/palettes/`: semantic paper/ink/surface/accent/status colors.
- `styles/dataviz/`: chart-series colors independent from the main accent.
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
sizes and varied copy placement. Resolve typography/palette/dataviz once per deck;
do not switch style packs slide-by-slide merely to create variety. Keep Korean copy Korean-first with `keep-all`;
use intentional technical names rather than decorative English scaffold. Prefer
concrete labels; avoid tiny bottom explanations, pill chips, leader lines and
unmotivated visual decoration. Let evidence determine the visual, not vice versa.

Before polishing explanatory copy, delete prose that merely repeats a visible title,
label, chart or table. Keep caveats only when omitting them would materially mislead.
Release-status metadata such as `잠정치`, `예비치` or later-revision warnings should
normally appear once in a footnote/source area, not in body copy. Keep it in the
body only when preliminary-vs-final data is itself the slide's subject.

Require a meaningful `reason` for every motion, a valid target and a supported
intent. Choose the semantic motion from the relationship being explained, not from
an effect catalog. Remotion expression patterns are a second-stage choice governed
by target compatibility, scene tone, density, intensity, recent repetition and
pairwise conflicts; `pattern: "auto"` uses those deterministic rules. Read
`references/motion-semantics.md` before authoring data-driven or multi-beat motion.
Do not animate every element or apply blanket fade-up to every slide. Different
slides may share timing, but their motion grammar should follow
their meaning: quantities grow, gaps measure, states swap, paths travel, sequences
resolve and timelines advance.

The presenter state machine is part of the deck contract. A live slide must open on
its declared start phase and wait for presenter input. Slide activation must never
auto-advance a meaningful phase. One presenter advance equals exactly one declared
phase; a short stagger may occur inside that phase. Back reverses exactly one phase
before crossing a slide boundary. Right-half click, ArrowRight, Space and Enter move
forward; left-half click and ArrowLeft move backward. Static mode skips phase
interaction and renders the completed frame. Whole-deck progress must include phase
progress. Do not rebuild a second presenter state machine inside an individual deck.

Static mode, reduced motion and print must present the same complete information.

Use only trusted local raster assets within the declared asset root. The compiler
embeds PNG/JPEG/GIF/WebP; it rejects SVG and remote image fetching. Retrieve and
review external media separately, retain source/license information, and never
mistake checkerboard pixels for real alpha transparency.

## Validation and extension

Run `python -m unittest discover -s tests -p 'test_modular.py'` for compiler tests.
Run `python tests/modular_runtime_check.py` for focused runtime/negative-QA checks.
Run browser QA for every finished deck; compilation alone is not visual acceptance.
For video output, inspect the sampled PNGs generated around scene/cue boundaries in
addition to the automated encoded-output checks. A passing codec/duration report is
not a substitute for visual review of emphasis, clipping or text fit.
The current QA harness uses `set_content` and therefore does not certify first-load
URL query/deep-link behavior. Inspect the report's coverage notes.

For legacy decks, preserve the shared presenter runtime and linter contract in
`motion/deck-motion.js`, `motion/deck-shell.js`, `tools/slide_lint.py`,
`references/runtime-contract.md` and `references/navigation.md`. The legacy linter
must reject slide-entry autoplay on stepped decks and verify presenter phase state.

Read [architecture](references/modular-architecture.md) for boundaries,
[art direction](references/art-direction.md) for automatic typography/color routing,
and [authoring](references/module-authoring.md) before adding a module or style pack.
Read [migration](references/migrating-v1.md) when working on an existing deck and
[video pipeline](references/video-pipeline.md) when producing Remotion output.
Preserve older accepted decks and compatibility tools. Treat this repository as the
AI's reusable production skill, not as a history of completed user jobs. Generate
user-specific specs, HTML, QA captures and exports in temporary or ignored locations,
deliver them in chat, and do not commit them. Commit only reusable framework changes
and deliberately maintained synthetic regression/reference fixtures.
