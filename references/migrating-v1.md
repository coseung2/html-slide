# Migrating existing decks

1. Preserve the accepted original HTML and its capture. Existing `motion/` and
   `templates/` consumers keep their original dependencies and exporter.
2. Extract each slide's communication goal, facts, citations and media. Do not copy
   a template's incidental decoration into the new module taxonomy.
3. Run the catalog and map information to supported block schemas. Start with a
   preset only when its contents and purpose fit. Custom visuals may remain in the
   legacy deck until a real, tested module exists; do not fake migration support.
4. Write a JSON spec, inspect its plan, build and compare static final frames.
5. Verify phases, keyboard and click controls, static/reduced motion and no-JS.
   Validate raster assets and embed an authorized font explicitly for delivery.
6. Deliver the new HTML alongside any requested exports. Do not delete the old
   source until the migrated result is accepted.

Legacy command: `python tools/export_deck.py old-deck.html`.
Modular command: `python tools/export_modular.py new-deck.html`.

The source repository preserves the historical director rules in
`references/legacy-direction.md`. They are reference material, not a second active
entrypoint. New authoring starts with the root `SKILL.md` and executable catalog.
