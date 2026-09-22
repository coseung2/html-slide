# html-slide: modular slide engine

Compose by **communication goal**, not by filling a mandatory template.
The AI writes a structured deck; the engine finds compatible modules, explains its
choices, validates data and slots, and emits a self-contained HTML presentation.

## Quick start

Python 3.10+ and `jsonschema` are required for composition. Browser QA additionally
requires Playwright and Chromium. Node.js and PptxGenJS are needed only for PPTX export.

```sh
python -m pip install -r requirements-modular.txt
python -m playwright install chromium
npm install
python tools/compose_deck.py catalog
python tools/compose_deck.py search --intent ranking --theme sports-broadcast
python tools/compose_deck.py init --preset sports-match-report --out deck.json
python tools/compose_deck.py plan deck.json --out plan.json
python tools/compose_deck.py build deck.json --out deck.html
python tools/verify_modular.py deck.html --out dist/qa
python tools/export_modular.py deck.html --out dist/export
```

`--font /absolute/path/font.woff2` embeds an explicitly supplied font; omitting it
uses system fonts and emits a warning because metrics can vary across machines.
An existing system Chromium can be selected with `CHROME_PATH` or
`PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`. No network calls or API key are needed to
compose a deck. The repository does **not** provide an LLM or autonomous research
service: AI reasoning happens outside the deterministic compiler.

## Architecture

| Directory | Responsibility |
|---|---|
| `core/` | Registry, strict contracts, slot solver, composer, safe rendering, stage and navigation |
| `modules/layouts/` | Spatial skeletons and capacity/type-constrained slots |
| `modules/content/` | Schema-checked information blocks |
| `modules/visuals/` | Reviewed local images and logos |
| `modules/motion/` | Intent/target-constrained semantic emphasis |
| `themes/` | Independent appearance tokens, not page layouts |
| `presets/` | Editable example combinations, not mandatory templates |
| `tools/` | Discovery, planning, building, browser QA and export |

The current catalog includes 10 layouts, 11 content blocks, 2 visual blocks,
5 motion effects, 7 themes and 3 starter presets. Add a module directory with a
manifest, template and styles; discovery is automatic. The plan records selection
reasons, rejected candidates, resolved slots and repetition warnings.

See [module authoring](references/module-authoring.md),
[architecture](references/modular-architecture.md),
[migration](references/migrating-v1.md) and [Korean guide](README.ko.md).

## Example and controls

Build `examples/modular-showcase.json` with the CLI, then open the resulting HTML:
12 Korean slides demonstrate goal-driven
composition across sports, finance, education, editorial and technology contexts.
All illustrative scores, tables and series are synthetic, not current factual data.
The source is `examples/modular-showcase.json`.

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
