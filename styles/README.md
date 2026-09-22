# Style packs

Deck-level art direction is split into three independent registries:

- `typography/`: heading, body and number font-role systems
- `palettes/`: semantic presentation colors
- `dataviz/`: chart-series colors

Each pack contains `manifest.json` plus `style.css`. The manifest is used for
automatic routing; CSS is bundled only when that pack is selected.

Do not treat these directories as slide templates. Keep layout geometry in
`modules/layouts/` and design grammar in `themes/`.

See [art-direction.md](../references/art-direction.md) for the selection contract,
metadata rules and authoring examples.
