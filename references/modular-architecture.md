# Architecture and decisions

## Boundaries

The AI is the director, not a hidden runtime dependency. It researches the brief,
chooses each slide's communication goal, supplies evidence and reviews the plan.
The compiler is deterministic and offline: schema validation -> metadata ranking
-> capacity/type-aware slot assignment -> safe rendering -> inline CSS/JS HTML.

Themes change appearance tokens only. Layouts own slots and geometry. Information
blocks own schemas and renderers. Visual blocks ingest reviewed raster assets.
Motion modules constrain supported intents and target block types. The core owns
fixed-stage scaling, active slide and phase state, accessibility and presenter UI.
Presets are full ordinary deck specs, so all of their choices can be edited.

## Selection

Search matches intent/tags, density and theme eligibility. It ranks candidates by
explicit numeric rules, not embeddings or a remote semantic-search service. The
planner filters incompatible layouts using backtracking slot assignment; pinned
layouts must also pass compatibility. Excess content fails rather than being
silently dropped. Reusing the same layout three times produces a warning, not a
hard rule that would force an inappropriate layout.

## Output and compatibility

The accepted frame is static markup; semantic motions explain how that frame is
reached. Every transition is reversible. A focus ring is inside its real target.
No-JS output retains all slides in document order; print and reduced motion expose
complete final values. Export uses verified static PNGs for both PDF and PPTX.

The modular runtime implements the legacy public capture hooks (`__deckGoto`,
`__deckState`, `__deckNext`, `__deckPrev`) and familiar bottom presenter shell.
Existing legacy source files are preserved, not secretly redirected. This is an
intentional compatibility boundary; never load both runtimes together.

## Trust boundary

Strict JSON schema rejects unknown keys, invalid IDs, wrong numeric types and
non-finite numbers. User text is HTML-escaped; embedded plan JSON neutralizes
script terminators. Source links allow HTTP(S), without credentials. Local image
paths are confined to the asset root; supported signatures are checked and the
browser verifies decoding. SVG, arbitrary HTML blocks and remote image fetching
are not supported. Module manifests/templates are trusted repository code.

## Known limits

Metadata search is not AI reasoning. No automatic research or photo search is
included. No editable chart/text PPTX export is promised. System-font builds can
vary between computers. Browser QA is a geometry/behavior gate, not a full WCAG
accessibility audit, factual verification or aesthetic guarantee. Initial URL
query/deep-link loading is not covered by the current managed-browser harness.
