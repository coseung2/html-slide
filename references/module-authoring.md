# Adding a module

## Discover first

Run `python tools/compose_deck.py catalog` and inspect an existing module in the
same family. Each directory has a version-1 `manifest.json`; its kebab-case ID must
match the directory name. IDs are unique within each family; content and visual IDs must be unambiguous. Resource paths must stay
inside that directory. Registry discovery needs no central import-list edit.

## Layout

Add `modules/layouts/<id>/manifest.json`, `template.html` and `styles.css`.
Declare a named slot mapping; each entry has `accepts`, `min` and `max`. Put each `{{slot.name}}`
placeholder in the template exactly where the corresponding slot belongs. Use
`{{copy}}` for the title/summary cluster. Match the existing manifest format,
including `type`, `version`, `intents`, `tags` and `density`.

Use stage pixels, min-width:0 for flexible cells and explicit internal capacities.
Keep meaningful content inside 5% safe insets. Do not write viewport-relative
geometry or color tokens that defeat theme separation. Test crowded and empty
allowed cases; an accepted data schema alone does not prove geometry is safe.

## Information or visual block

Add a manifest with the correct `type`, an object `schema` with
`additionalProperties:false`, and a template using escaped scalar placeholders.
Declare `visualRole` when the block has a stable role in deck-level quality analysis:
`evidence` for concrete image/data proof, `structure` for process/timeline/diagram
scaffolding, `support` for marks such as logos, or `copy` for primarily textual
blocks. New visual modules that omit this metadata are not assumed to be concrete
evidence. Built-in complex types use the vetted renderer functions in
`core/renderers.py`; new complex renderers require an explicit implementation and
tests. Never inject untrusted raw HTML or evaluate code from a manifest. Optional
`styles.css` is included only when the block is selected.

## Theme

Add `themes/<id>/manifest.json` and `theme.css`. A theme owns design grammar such as
corner, border and surface-treatment behavior. It does **not** own deck color or font
families. Scope appearance tokens to `[data-theme="<id>"]`; never alter slot sizing,
stage dimensions or body overflow.

## Art-direction style pack

Add `styles/typography/<id>/`, `styles/palettes/<id>/` or `styles/dataviz/<id>/`
with a version-1 `manifest.json` and `style.css`. Typography packs must expose
`--font-body`, `--font-heading` and `--font-number`; palettes must expose semantic
paper/text/surface/accent/status variables; dataviz packs must expose `--viz-1`
through `--viz-6`. Scope CSS to the matching body data attribute.

Metadata should describe useful theme recommendations, domains, audiences, tones
and density rather than aesthetic adjectives alone. Typography also declares
supported languages. Do not bundle a font file just to create a new style pack;
font distribution rights must be explicit. Read `references/art-direction.md`
before changing automatic selection behavior.

## Motion

A motion manifest names allowed target block IDs and intents. Authoring specs must
supply a real target ID and a reason. A new runtime effect requires implementation
in `core/runtime.js`, not just an attractive manifest name. Gate phase CSS on
`.deck-live`, preserve final static text and test forward/backward/reduced motion.
No more than two semantic effects are accepted on a slide.

## Acceptance

Add contract tests, compile a meaningful example, run browser QA, inspect screenshots
and update relevant docs. Do not advertise placeholder modules as implemented.
