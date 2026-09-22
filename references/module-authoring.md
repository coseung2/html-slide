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
Built-in complex types use the vetted renderer functions in `core/renderers.py`;
new complex renderers require an explicit implementation and tests. Never inject
untrusted raw HTML or evaluate code from a manifest. Optional `styles.css` is
included only when the block is selected.

## Theme

Add `themes/<id>/manifest.json` and `theme.css`. Scope appearance tokens to
`[data-theme="<id>"]`; never alter slot sizing, stage dimensions or body overflow.
Check all text/background pairings manually and in the actual projected frame.

## Motion

A motion manifest names allowed target block IDs and intents. Authoring specs must
supply a real target ID and a reason. A new runtime effect requires implementation
in `core/runtime.js`, not just an attractive manifest name. Gate phase CSS on
`.deck-live`, preserve final static text and test forward/backward/reduced motion.
No more than two semantic effects are accepted on a slide.

## Acceptance

Add contract tests, compile a meaningful example, run browser QA, inspect screenshots
and update relevant docs. Do not advertise placeholder modules as implemented.
