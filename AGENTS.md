# html-slide repository contract

Read `SKILL.md` before authoring or changing a deck. It is the active entrypoint.
Read the executable catalog before adding a new module or selecting a layout.

## Repository role

This repository is an **AI slide-production skill and workflow**, not a presentation
archive. Its purpose is to give an AI reusable rules, modules, art-direction packs,
runtime behavior, validation tools and export procedures.

A normal user request should use this repository to produce artifacts **outside the
maintained repository history**, then deliver those artifacts to the user. Do not
commit a user's deck merely because it was generated with this framework.

The repository should accumulate reusable capability, not completed jobs.

## Default authoring

Start with communication goals and evidence, then write JSON and inspect the plan.
Treat presets as editable combinations, not mandatory templates. Use `core/`,
`modules/`, `themes/`, `styles/` and the modular CLI for new work. Keep theme grammar,
typography, main palette, dataviz palette, layout geometry, data rendering, media and
meaningful motion independently owned. Resolve art-direction packs once per deck and
record automatic selection reasons. Never fabricate missing facts or silently
truncate overflowing data.

For each real deck:

1. Read this repository's rules and catalog.
2. Interpret/research the user's topic and source material.
3. Generate the deck spec and artifacts in a temporary or ignored working location.
4. Verify the finished HTML and requested exports.
5. Tell the user the important composition/art-direction choices and why they were
   made.
6. Deliver the actual HTML/PDF/PPTX or other requested artifacts in the chat.

The generated `*.plan.json` is an execution aid. Its scores, reasons and alternatives
help the AI explain the result to the user; they are not per-job history that belongs
in Git.

## Changes and verification

Add schema/compatibility tests with new modules. Run compiler and focused browser
regressions plus visual QA of the finished HTML. Inspect actual screenshots.
`bash tools/verify_modular.sh` runs the modular suite; `bash tools/verify.sh` in the
full repository additionally runs legacy regression suites. Do not claim the
legacy suite passed when only the modular suite was executed.

Preserve legacy `motion/`, templates, old examples and the legacy exporter unless
an explicit migration is requested. Never load both runtimes in one deck.
Do not weaken a validator merely to obtain a passing screenshot. Distinguish
compiler acceptance, automated geometry checks and human visual review.

## Repository artifact policy

Commit only material that improves future slide-generation work:

- AI instructions and workflow contracts
- reusable layouts, content, visual and motion modules
- reusable themes, typography packs, palettes and dataviz packs
- generic presets
- compiler/runtime/export/validation tools
- tests and deliberately maintained synthetic regression fixtures
- documentation and migration guidance

Do **not** commit:

- a user's finished HTML, PDF, PPTX or other delivery artifact
- task-specific deck JSON/specs or plan reports
- QA screenshots, rendered frames, delivery ZIPs or caches
- user-provided source documents
- web images/media downloaded only for one user's deck
- per-job selection logs or result history

`examples/` exists only for small, deliberate, synthetic reference/regression
fixtures. It is not a destination for finished user work and must not become an
archive of prior slide requests.

If a real deck exposes a reusable weakness, extract the **generic improvement** into
the repository (rule, module, style pack, validator, test or documentation) and keep
the user's actual result outside Git.

Do not remove existing repository font assets. Deliver requested artifacts in the
chat. When the user explicitly asks to change this repository, report the real
commit/push and verification status.
