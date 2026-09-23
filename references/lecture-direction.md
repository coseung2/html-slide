# Lecture deck direction

Use this reference when the presentation purpose is a **lecture, workshop, tutorial,
lesson, training session or live technical explanation**.

This is an art-direction and teaching-rhythm reference, not a fixed page template.
Do not copy the example content. Reuse the visual grammar while rebuilding the deck
around the user's actual subject, evidence and teaching sequence.

## Core teaching rhythm

A strong lecture deck alternates between four jobs:

1. **Name the idea** — a short title or typography-led key concept.
2. **Show the thing** — screenshot, interface state, photo, chart, code, document,
   concrete diagram or other evidence.
3. **Compare the change** — before/after, A/B, local/remote, input/output, cause/result,
   expected/actual, or another meaningful contrast.
4. **Close the loop** — implication, action, practice criterion or recap.

Do not turn every slide into title + subtitle + cards. The audience should feel the
lecture moving through scenes, not paging through a document.

## Planning fields

Before composing a lecture slide, decide:

- **learning point**: the one thing the audience should understand after this slide;
- **evidence object**: the concrete object or state that can prove/show it;
- **scene family**: typography, evidence, comparison, process, state change, practice,
  recap or another justified family;
- **presenter beat**: what changes when the presenter advances;
- **anchor state**: when a recurring object is used, what specifically changed from the
  previous appearance.

When the same app, document, chart, object or example can carry several ideas, keep it
as the narrative anchor instead of replacing it with unrelated cards.

## Scene families

### 1. Typography-led concept

Use a large word, address, equation, filename, command, contrast sign or short phrase
when the literal text **is the visual evidence**.

Good uses:
- index.html
- localhost : 3000
- 저장 ≠ 배포
- 입력 → 처리 → 출력

Rules:
- make the key text materially larger than ordinary titles;
- keep supporting copy minimal;
- use whitespace, alignment, scale and one accent before adding boxes;
- do not repeat the same sentence as a subtitle.

Typography scenes are punctuation, not filler. A lecture can use several, but they
should appear where a concept deserves a visual reset.

### 2. Recurring object / anchored example

Keep the same interface, device, document, code sample or diagram recognizable while
its state changes.

Typical progression:
initial → inspected → failed → fixed → verified

The object should stay large enough to read. Do not shrink it into a thumbnail merely
to make room for explanatory prose.

### 3. Direct comparison

Prefer direct spatial comparison over prose when the lesson is about a difference.

Examples:
- file URL / localhost / public URL;
- before / after;
- expected / actual;
- browser A / browser B;
- local state / persisted state.

Use the same visual grammar on both sides so the difference is attributable to the
content, not to unrelated decoration.

### 4. Process / path

Use a path when the lesson is about movement, dependency or sequence.

Examples:
edit → run → test → deploy
input → API → database → response

Make the direction visually obvious. Motion, when used, should travel along the real
path or resolve the real states.

### 5. Evidence scene

If the audience can benefit from a real screenshot, photo, chart, document excerpt,
terminal result or measured number, let that evidence dominate the frame.

Do not replace available evidence with a text card that merely names the evidence.

### 6. Practice / acceptance scene

End a concept block with something the learner can verify:

- a small test matrix;
- a checklist tied to visible states;
- a reproduction path;
- a success/failure comparison;
- a task with an observable acceptance criterion.

### 7. Recap

Use a recap to compress the learned model, not to repeat every slide title. Prefer
three to five memorable nouns, verbs, states or relationships.

## Visual grammar

The maintained reference is **examples/lecture-format-reference.html**.

Use its principles, not its literal copy:

- warm neutral paper, dark ink, one strong accent;
- 1920x1080 fixed stage and generous safe area;
- short titles, usually one line;
- editorial whitespace instead of dashboard-style card density;
- giant typography for concepts that can carry the frame;
- thin rules, rails and direct alignment before container boxes;
- real or intentionally synthetic evidence centered in the hierarchy;
- recurring objects kept visually recognizable;
- layout variation driven by teaching purpose.

Avoid:
- decorative English labels when Korean wording works;
- long narration sentences used as titles;
- a pill/card for every noun;
- five consecutive slides with the same title-left / cards-right skeleton;
- tiny screenshots beside large explanatory paragraphs;
- arbitrary animation on every element.

## Lecture-specific acceptance heuristics

These are review heuristics, not schema constants:

- one primary learning point per slide;
- title should normally fit one projected line; rewrite before shrinking;
- no more than two consecutive generic copy-only slides;
- no more than two consecutive uses of the same composition unless the repetition is
  itself pedagogically meaningful;
- after one or two abstract/conceptual slides, return to concrete evidence, a state,
  a comparison or a practice check;
- typography-led slides should have a reason: naming, contrast, transition or recap;
- if a real interface/photo/document exists and matters to the lesson, use it.

## Technical lecture pattern

For development and vibe-coding lectures, prefer **same artifact, different context**.

For example, when teaching file/local/deploy:

1. show the same page opened as a file;
2. show the same page through a local server;
3. show the same page at a public deployment URL;
4. compare what changed: address, runtime, reachability, environment and update path.

Use real address shapes and screenshots where useful. Explain localhost, ports,
domains and deployment as concrete execution contexts, not as abstract product names.

## Suggested lecture arc

This is a flexible sequence, not a mandatory template:

hook → key term → concrete example → comparison → mechanism → failure/state change → practice → recap

A longer lecture may repeat the middle cycle several times. Keep the visual rhythm
varied while preserving one coherent art direction.
