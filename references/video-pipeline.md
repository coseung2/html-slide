# Remotion video pipeline

## Goal

The video pipeline reuses the same validated `core/deck.schema.json` content source used by
HTML decks. It does not ask an AI to invent a second video-specific content document.
`tools/compose_video.py` first runs the normal deck planner, then compiles deterministic
scene timing and semantic motion cues into a Remotion storyboard.

## Boundary

```
deck.json
   ├─ compose_deck.py  -> HTML / PDF / PPTX
   └─ compose_video.py -> storyboard.json -> video/ Remotion runtime -> MP4
```

The deck spec remains the content source of truth. The storyboard is an execution
artifact and should not be committed for a user job.

## Timing contract

- Default stage: 1920x1080.
- Default frame rate: 30 fps.
- Each scene gets a base reading hold plus additional time for declared semantic steps.
- Motion cues are generated only from validated slide `motion` declarations.
- A cue always retains its original target and reason.
- No blanket per-element animation is introduced by the compiler.
- A scene without semantic motion still renders as a complete readable scene.

Defaults can be overridden from the CLI without changing the deck spec:

```sh
python tools/compose_video.py deck.json --out dist/storyboard.json \
  --fps 30 --base-seconds 4 --step-seconds 1.2 --transition-seconds 0.35
```

## Render

```sh
cd video
npm install
npx remotion render src/index.ts DeckVideo ../dist/video.mp4 \
  --props=../dist/storyboard.json
```

The packages in `video/package.json` are pinned to the same Remotion version. Remotion
requires aligned exact versions for `remotion` and `@remotion/*`.

## Current renderer scope

The first runtime intentionally proves the pipeline contract before visual parity work.
It renders slide titles, summaries, content blocks, scene timing and target-bound emphasis.
Content-specific native video renderers can be added incrementally behind the same
storyboard contract. The HTML renderer remains the reference for complete slide-layout
fidelity.

Do not solve missing native video renderers by applying generic motion to every block.
Extend the renderer by semantic module or scene intent instead.

## QA direction

A finished video job should eventually run three checks:

1. storyboard validation: duration, target binding, no meaningless cue;
2. sampled-frame visual QA: safe area, clipping, overlap, asset resolution;
3. encoded-output QA: expected duration, frame size, audio/video stream presence.

Generated frames, videos and storyboard files are task artifacts and stay outside Git.
