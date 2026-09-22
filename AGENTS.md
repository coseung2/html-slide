# html-slide repository contract

Read `SKILL.md` before authoring or changing a deck. It is the active entrypoint.
Read the executable catalog before adding a new module or selecting a layout.

## Default authoring

Start with communication goals and evidence, then write JSON and inspect the plan.
Treat presets as editable combinations, not mandatory templates. Use `core/`,
`modules/`, `themes/` and the modular CLI for new work. Keep theme appearance,
layout geometry, data rendering, media and meaningful motion independently owned.
Never fabricate missing facts or silently truncate overflowing data.

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

Commit maintained source and finished example HTML. Keep caches, plan reports,
QA screenshots, PDF/PPTX exports, font-file copies and delivery ZIPs out of new
commits. Do not remove existing repository font assets. Deliver actual artifacts
in the chat and report the real commit/push and verification status.
