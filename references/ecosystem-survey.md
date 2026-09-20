# The HTML-slide agent-skill ecosystem

Surveyed 2026-09 by reading the repositories themselves (tree API + each `SKILL.md`), not from blog summaries. Star counts drift fast — treat them as ordering signal only.

## Start with the catalogs, not with repo search

- **`ToseaAI/awesome-html-slide-skills`** — the domain catalog: 23 entries, star-ranked and tiered (S: 1k+, A: 100–1k, B: emerging), refreshed continuously. Its own blurb lists Claude Code / Codex / Cursor / OpenClaw / **Hermes**, so it is agent-agnostic by design. Use it as the map, then verify each entry against its own repository. (CC BY 4.0.)
- `tosea.ai/slide-skills` — the same curation as a browsable gallery.
- **`vercel-labs/skills`** (~32k★) — the `npx skills add <owner>/<repo>` installer several of these use.

## Deck generators

| Repository | ★ | Use it for |
|---|---|---|
| `zarazhangrui/frontend-slides` | 29.3k | "Show, don't tell" — generates style previews and lets the user pick; 16 themes; fixed-size stage (no mobile reflow); screenshot-level overflow/overlap checks. Its `animation-patterns.md` covers CSS entrance effects only — no anchoring rule. |
| `op7418/guizang-ppt-skill` | 26.6k | Magazine-style horizontal decks + presenter mode. **Strongest measured-verification story**: `scripts/validate-swiss-deck.mjs`, `validate-presenter-mode.mjs`, `check-presenter-runtime-sync.mjs` measure DOM/visual overflow, bottom whitespace, nav-safe band, title gap. **AGPL-3.0** — check before shipping inside a product. |
| `alchaincyf/huashu-design` | 19.5k | 20 design philosophies + 5-dimension critique, brand-asset ingestion, MP4/PPTX export. |
| `nicobailon/visual-explainer` | 9.9k | Diagram / diff-review / plan-audit decks, inline SVG, dark-first. |
| `lewislulu/html-ppt-skill` | 8.4k (MIT) | 36 themes, 31 layouts, 20+ animations, real presenter mode. `scripts/render.sh` renders per-slide PNGs via headless Chrome — it renders, it does not assert. |
| `1weiho/open-slide` | 7.6k (MIT) | A framework, not a markdown skill: agents write React, it owns a fixed 1920×1080 canvas, nav, hot reload, present mode. Also ships `.agents/skills/review-animations/`. |
| `zarazhangrui/beautiful-html-templates` | 3.1k | 32 templates, no skill logic — pure visual vocabulary. |
| `kaisersong/slide-creator` | 50★ | Small but ships `scripts/browser_geometry_qa.py` (~1,060 lines): `title_clipped`, `content_clipped`, `text_overflow`, `character_overlap`, contrast, viewport escape, plus a deterministic-layout wait. **Best pure geometry validator surveyed** — a good target to crib from. |
| `archlizheng/frontend-slides-editable` | 362★ | Editable fork: drag/resize, slide reorder, local save, PPTX↔web. |
| `nghiahsgs/skills-slides` | 35★ | `references/anti-slop-checklist.md` — gates AI-looking decks before delivery. |
| `edu-ai-builders/visual-cognition-slides` | 72★ | Cognitive-science framing: every animation answers "what cognitive action does the audience need here?" Good for lesson / booth decks. |
| `anthropics/skills` (official) | — | `pptx` + `frontend-design`. PPTX-native, not HTML-with-motion. |

## Motion / animation craft

- **`emilkowalski/skill`** (38.9k, MIT) — the origin of the rules the others copy. `skills/improve-animations/AUDIT.md` §3 "Physicality & origin": animate `transform`/`opacity` only; never `scale(0)`; popovers/dropdowns/tooltips scale **from their trigger** via `transform-origin` (modals exempt). Also `animate`, `review-animations`, `find-animation-opportunities`, `animation-vocabulary`, `apple-design`, `performance-cheatsheet.md`.
- **`1weiho/open-slide` → `.agents/skills/review-animations/SKILL.md`** — 10 non-negotiable standards, `STANDARDS.md` (~10KB), and escalation triggers. Framework-agnostic, so it applies to a deck: flags `transform-origin: center` on a trigger-anchored popover on sight, blocks UI motion over 300ms, blocks layout-property animation.
- **`iart-ai/web-animation-skills`** (MIT, 9 skills) — `gsap-web` teaches **FLIP** (`Flip.getState()` → mutate → `Flip.from(state, {absolute:true})`) as the layout-transition technique; `60fps-animation` converts layout-property animation to `transform`; `micro-interaction` covers list reorder; plus `page-transition-animation`, `svg-animation`, `lottie-animation`, `glassmorphism`, `accessible-animation`, `ascii-animation`.
- **`iart-ai/motion-design-skills`** (9 skills) — `shot-composition` (grid, focal point, enter/exit placement, 16:9 · 9:16 adaptation), `animation-principles`, `motion-art-direction`, `color-motion`, `motion-background`, `logo-animation`, `beat-sync-editing`, `after-effects`, `remotion-video`.
- `iart-ai/motion-skills` — hub packaging those packs. `remotion-dev/skills` (4.6k) — code-driven MP4 video, not a deck.

## Install patterns seen in the wild

- clone into the agent's skills dir: `git clone <repo> ~/.claude/skills/<name>` (same shape works for `~/.hermes/skills/`)
- package manager: `npx skills add <owner>/<repo>`
- plugin manifest: `.claude-plugin/plugin.json` / `.claude-plugin/marketplace.json`
- **license gate**: guizang is AGPL-3.0, the ToseaAI catalog is CC BY 4.0, most others MIT. Check before shipping inside a product.

## The gap — state it honestly

Grepping all 23 catalog entries: `animation` appears in a handful of blurbs; `overflow`, `overlap`, `position`, `GSAP`, `reveal.js` appear essentially **zero** times. The ecosystem splits the problem — deck generators *measure* geometry; motion skills keep animation on `transform` — and **no surveyed skill states "emphasis must be anchored to its target"**.

So when the complaint is drifting emphasis, a tool recommendation alone is the wrong answer. Name the gap and apply the anchoring rule from the parent `SKILL.md` directly.

## Re-surveying later

The catalog makes this cheap: read `ToseaAI/awesome-html-slide-skills`' README for the current list, then verify candidates against their own repos (tree API + `SKILL.md` frontmatter) before recommending anything. Method: `repository-research` → `references/agent-skill-ecosystem-scouting.md`.
