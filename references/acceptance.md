# Acceptance constants

This file is the single human-readable acceptance baseline. Code and other
references should point here instead of inventing alternate test sizes.

## Stage

- Authored stage: **1920 x 1080**
- Scale: one uniform `min(viewportWidth/1920, viewportHeight/1080)`
- Safe inset: **5%** on every side for meaningful content

## Required verification viewports

Run geometry/binding checks at exactly these baseline sizes unless a deck has
an additional explicit delivery target:

1. **1920 x 1080** — authored 16:9
2. **1280 x 720** — common 16:9 presentation output
3. **1024 x 768** — 4:3 projector stress case

The stage must letterbox; it must not reflow between these viewports.

## Motion properties

- Default safe properties: **transform, opacity**
- Conditional: **filter, clip-path**, only when the effect is explanatory,
  does not change target geometry, and the final static frame remains complete
- Forbidden for animation: **top, left, right, bottom, width, height, margin,
  padding, inset**
- `transition: all` is forbidden because it silently opts layout properties
  into animation

## Timing

- Press feedback: 100-160ms
- Small UI state: 150-250ms
- Emphasis: 200-300ms
- State change: 300-450ms
- Scene transition: 400-700ms
- Enter/respond: ease-out
- Moving on screen: ease-in-out
- Never use ease-in for UI response

These constants are normative for the shipped linter/runtime.
