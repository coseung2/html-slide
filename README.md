# html-slide: modular slide engine

Compose by **communication goal**, not by filling a mandatory template.
The AI writes a structured deck; the engine finds compatible modules, explains its
choices, validates data and slots, and emits a self-contained HTML presentation.

## What this repository is

`html-slide` is an **AI-facing slide production skill, workflow and toolset**.
It is not a repository for accumulating completed presentations.

The intended loop is:

1. AI reads `SKILL.md`, `AGENTS.md`, the catalog and relevant references.
2. AI interprets the user's topic, sources and audience.
3. AI chooses compatible layouts, content modules, art direction and semantic motion.
4. AI generates and verifies the user's HTML and requested exports in a temporary or
   ignored working location.
5. AI explains the important choices and their reasons to the user.
6. AI delivers the finished artifacts directly in the chat.

Git should accumulate **reusable capability**: rules, modules, styles, validators,
exporters, tests and documentation. It should not accumulate user-specific HTML,
PDF/PPTX files, deck specs, plan reports, QA captures or downloaded media from
individual jobs.

If a real deck reveals a reusable problem, the reusable fix can be added here. The
deck that exposed the problem still remains a user delivery artifact, not repository
history.

## Quick start

Python 3.10+ and `jsonschema` are required for composition. Browser QA additionally
requires Playwright and Chromium. Node.js 22+ is used for PptxGenJS and the pinned
HyperFrames CLI; local video rendering also requires FFmpeg.

```sh
python -m pip install -r requirements-modular.txt
python -m playwright install chromium
npm install
python tools/compose_deck.py catalog
python tools/compose_deck.py search --intent ranking --theme sports-broadcast
python tools/compose_deck.py search --type typography --theme education --domain education --audience elementary --tone clear
python tools/compose_deck.py init --preset sports-match-report --out dist/work/deck.json
python tools/compose_deck.py plan dist/work/deck.json --out dist/work/plan.json
python tools/compose_deck.py build dist/work/deck.json --out dist/work/deck.html
python tools/verify_modular.py dist/work/deck.html --out dist/work/qa
python tools/export_modular.py dist/work/deck.html --out dist/work/export
python tools/compose_video.py dist/work/deck.json --out dist/work/video/index.html --timing-out dist/work/video/timing.json
python tools/render_video.py dist/work/deck.json --out dist/work/video.mp4
```

`--font /absolute/path/font.woff2` embeds an explicitly supplied authorized font.
Typography packs otherwise select role-based system fallback stacks, so omitting the
font file still emits a warning because metrics can vary across machines.
An existing system Chromium can be selected with `CHROME_PATH` or
`PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`. No network calls or API key are needed to
compose a deck. The repository does **not** provide an LLM or autonomous research
service: AI reasoning happens outside the deterministic compiler.

## Architecture

| Directory | Responsibility |
|---|---|
| `core/` | Registry, strict contracts, slot solver, composer, safe rendering, stage/navigation and HyperFrames seek adapter |
| `modules/layouts/` | Spatial skeletons and capacity/type-constrained slots |
| `modules/content/` | Schema-checked information blocks |
| `modules/visuals/` | Reviewed local images and logos |
| `modules/motion/` | Intent/target-constrained semantic emphasis |
| `themes/` | Design grammar such as corner/border treatment, not page layouts or colors |
| `styles/typography/` | Deck-level display/body/number font-role systems |
| `styles/palettes/` | Semantic main colors for paper, ink, surfaces, accents and status |
| `styles/dataviz/` | Chart-series colors independent from the main accent |
| `presets/` | Editable example combinations, not mandatory templates |
| `tools/` | Discovery, planning, building, browser QA and export |

The current catalog includes 10 layouts, 11 content blocks, 2 visual blocks,
5 motion effects, 7 themes, 7 typography packs, 8 main palettes, 5 data-visualization
palettes and 3 starter presets. Registry discovery is automatic. The plan records
layout selection reasons, rejected candidates, resolved slots, repetition warnings,
and the selected art-direction packs with scores and alternatives.

Art direction resolves once per deck. Leave `style.typography`, `style.palette`
and `style.dataviz` as `auto`, then provide optional domain, audience, tone and
density signals. The deterministic planner combines those signals with the selected
theme's metadata. Any pack can also be pinned explicitly without changing content or
layout.

See [module authoring](references/module-authoring.md),
[architecture](references/modular-architecture.md),
[art direction](references/art-direction.md),
[migration](references/migrating-v1.md) and [Korean guide](README.ko.md).

## Repository examples vs. user results

`examples/` is reserved for deliberately maintained **synthetic reference and
regression fixtures**. It is not a folder for saving completed user jobs.

For example, `examples/modular-showcase.json` demonstrates the engine with synthetic
data so core behavior can be tested consistently. Real user decks should be generated
in a temporary/ignored path, verified, and delivered to the user rather than committed.

The planner's style/layout scores and selection reasons are execution metadata. They
may be shown or summarized to the user to explain the result, but should not be
committed as per-job history.

## Presenter controls

Use arrows or the stage halves to move, **S** for static/live, **O** for overview,
**F** for fullscreen, and Home/End for endpoints. Sources appear in overview.
Every slide remains complete with JavaScript disabled or reduced motion enabled.
PDF and PPTX use the exact same final-frame PNGs; PPTX is intentionally not editable.

## Verification

```sh
python -m unittest discover -s tests -p 'test_modular.py'
python tests/modular_runtime_check.py
python tools/compose_deck.py build examples/modular-showcase.json --out examples/modular-showcase.html
python tools/verify_modular.py examples/modular-showcase.html --out dist/showcase-qa
```

QA checks safe-area boundaries, text/box overflow, sibling overlap, loaded media,
target-bound highlights, four viewport sizes, phase reversal, static navigation,
overview, hash changes, reduced motion, print restoration and no-JS final values.
Reports explicitly state coverage limitations; initial URL loading is not certified
by the managed-browser `set_content` harness. Compilation is not visual acceptance.

## Compatibility

The original `motion/`, `templates/`, reference material and old examples are kept
in the full repository. The original `tools/export_deck.py` remains for legacy HTML.
New specs use the modular tools above. Do not include both runtimes in the same deck.
Read `SKILL.md` as the active AI entrypoint; historical scene direction is retained
in `references/legacy-direction.md` in the full repository.
