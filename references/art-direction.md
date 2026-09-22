# Art direction packs

The modular engine separates **design grammar** from **art direction**.

- `themes/` define the visual grammar of a scene: border treatment, corner behavior
  and other appearance rules that must not change slot geometry.
- `styles/typography/` define display/body/number font roles and weight/line-height
  behavior.
- `styles/palettes/` define semantic presentation colors such as paper, ink, surface,
  accent, positive, negative and warning.
- `styles/dataviz/` define chart-series colors independently from the main palette.

This separation is deliberate. A single education theme can be combined with a
friendly classroom typography system or a more restrained professional system
without duplicating layouts or page templates.

## Deck contract

Art direction is deck-level. Do not change typography or the main palette on every
slide merely to add variety. A deck spec may omit `style` entirely, or use `auto`:

```json
{
  "theme": "education",
  "style": {
    "typography": "auto",
    "palette": "auto",
    "dataviz": "auto",
    "signals": {
      "domain": "education",
      "audience": "elementary",
      "tone": ["approachable", "clear"],
      "density": "medium"
    }
  }
}
```

The AI supplies semantic signals. The deterministic compiler does the final pack
selection and records the selected pack, score, reasons and top alternatives in the
plan. Explicit pack IDs override automatic selection.

## Automatic selection

The registry scores a pack using reviewed manifest metadata:

1. recommendation for the chosen theme,
2. domain match,
3. audience match,
4. tone matches,
5. tag overlap with the topic/theme/signals,
6. density fit,
7. Korean/English support for typography.

The scores are routing heuristics, not aesthetic truth. The AI must still inspect the
rendered result. If a pack is visually unsuitable, pin a different reviewed pack and
rerun QA instead of editing random CSS inside the deck.

Typical defaults:

| Theme | Typography | Palette | Data visualization |
|---|---|---|---|
| `education` | `classroom-friendly` | `classroom-warm` | `categorical-soft` |
| `kids` | `kids-rounded` | `soft-pastel` | `categorical-soft` |
| `sports-broadcast` | `sports-condensed` | `broadcast-lime` | `categorical-6` |
| `financial-report` | `data-dense` | `financial-teal` | `finance-up-down` |
| `tech` | `tech-modern` | `midnight-blue` | `categorical-6` |
| `editorial` | `editorial-serif` | `warm-editorial` | `diverging-red-blue` |
| `documentary` | `editorial-serif` | `documentary-gold` | `diverging-red-blue` |

Signals can legitimately override these defaults. For example, an education deck for
a professional teacher-training audience can rank `clean-sans` above the classroom
default while preserving the education scene grammar.

## Typography rules

A typography pack declares role stacks, not bundled proprietary font files. Every
stack has Korean-capable fallbacks. The selected pack controls hierarchy even when a
specific font family is unavailable.

For delivery where font metrics must be fixed, pass an authorized local WOFF2 with
`--font`. The compiler embeds it as the custom family used by all roles, then browser
QA must be rerun. Do not add font-file copies merely to make a style pack appear more
distinct; license and distribution rights must be explicit.

## Palette rules

Components must consume semantic variables such as `--paper`, `--ink`, `--surface`
and `--accent`. Never hard-code a theme color inside a layout. Positive, negative and
warning colors belong to the palette so meaning survives palette changes.

Data visualization uses `--viz-1` through `--viz-6` and is intentionally independent
from `--accent`. A deck can therefore keep one restrained brand accent while charts
still have enough categorical separation.

## Authoring a new pack

Create `styles/<family>/<id>/manifest.json` plus `style.css`. IDs are lowercase
kebab-case and must match the directory. The registry validates required CSS tokens.

Before adding a pack, verify that it creates a materially useful art-direction choice,
not a near-duplicate color swap. Add metadata that makes the intended audience,
domain, tone, density and compatible themes discoverable. Add a unit test when the
new pack changes selection behavior.

Use the CLI to inspect routing:

```sh
python tools/compose_deck.py search \
  --type typography \
  --theme education \
  --domain education \
  --audience elementary \
  --tone approachable \
  --tone clear
```

The finished HTML carries `data-typography`, `data-palette` and `data-dataviz` on
`body`, and the embedded plan preserves the selection provenance.
