# Visual quality gate

The modular compiler validates geometry and runtime behavior, but those checks alone
cannot prevent a deck from becoming a sequence of generic cards and prose. The
visual-quality gate adds deterministic **composition diagnostics** before rendering.

## Authoring mode

Legacy specs omit `quality` and stay in `advisory` mode. New AI-authored decks
should use:

```json
{
  "quality": {"profile": "strict"}
}
```

In advisory mode the planner reports issues in `plan.quality` and mirrors them into
`plan.warnings`. In strict mode the same issues are build-blocking contract errors.

Thresholds can be tuned per deck only when the communication goal warrants it. Do not
loosen a threshold merely to make a weak composition compile.

## What the gate measures

- **Concrete visual coverage**: image, metric, ranking, score and chart modules count
  as concrete evidence. Statement, quote, bullet, comparison-text, process and
  timeline modules are useful structure, but they do not by themselves prove or
  demonstrate a claim.
- **Evidence-required intent**: comparison, before/after, ranking, distribution, KPI,
  scene and evidence slides must contain a concrete visual/data-bearing module.
- **Generic-only run**: consecutive slides made only from copy/structural modules are
  capped so a deck cannot devolve into repeated text cards.
- **Layout repetition**: both whole-deck layout share and consecutive reuse are
  measured. Layout variety must follow communication needs; it is not decorative
  randomness.
- **Motion grammar repetition**: when a deck declares enough motion to establish a
  pattern, one motion module may not dominate beyond the configured share.
- **Explicit-layout accountability**: an explicit `layout` needs `layout_reason`.
  Otherwise the author can bypass deterministic layout search without explaining why.
- **Narrative anchor coverage**: decks that declare recurring or progressive
  continuity must name an anchor and reuse it across enough slides.

The report is embedded in the plan:

```json
{
  "quality": {
    "profile": "strict",
    "passed": true,
    "metrics": {
      "concreteVisualRatio": 0.6,
      "maxLayoutShare": 0.3,
      "maxConsecutiveLayout": 2,
      "maxGenericOnlyRun": 2,
      "maxMotionShare": 0.5,
      "anchorCoverage": 0.7
    },
    "issues": []
  }
}
```

## Visual continuity

When one concrete object can carry the explanation across several slides, declare it
at deck level and reference it from the relevant slides:

```json
{
  "narrative": {
    "continuity": "progressive",
    "anchor": "quiz-app"
  },
  "slides": [
    {
      "id": "prompt",
      "anchor_ref": "quiz-app",
      "communication_goal": "Show the first generated quiz UI",
      "intent": "scene"
    },
    {
      "id": "state",
      "anchor_ref": "quiz-app",
      "communication_goal": "Show which state still lives only in the browser",
      "intent": "evidence"
    }
  ]
}
```

An anchor is not a decorative motif. It is a recurring subject whose state,
annotation, crop, data or relationship changes while the audience follows the same
object.

Use `continuity: "independent"` when the deck genuinely consists of unrelated
evidence scenes.

## Explicit layouts

Prefer layout search. If an exact layout is necessary, include the reason:

```json
{
  "layout": "split-right",
  "layout_reason": "The UI screenshot must remain large while the failure conditions stay readable."
}
```

The planner still records ranked alternatives even for an explicit layout so the
choice remains inspectable.

## Review discipline

A passing quality gate is a floor, not visual acceptance. After planning:

1. inspect every selected/rejected layout and the quality metrics;
2. replace generic copy with concrete screenshots, data, diagrams or generated
   interface scenes where the claim can be shown;
3. keep a recurring subject when the explanation is progressive;
4. choose motion from the relationship being explained;
5. run browser QA and inspect the screenshots.

The gate is intentionally deterministic. It cannot decide whether a particular
image is persuasive, whether a diagram is semantically correct, or whether the art
direction feels appropriate. Those still require visual review.
