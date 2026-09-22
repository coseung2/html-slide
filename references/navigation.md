# Presentation shell contract

The deck shell is reusable presenter chrome. It is **not slide content** and
must never change the 1920x1080 authored geometry.

It is also **not merely a visual component**. The shell and the Deck state
machine form one presenter contract. A deck that copies the bottom bar but
reimplements navigation with autoplay or slide-only next/prev does not conform.

## Standard modules

Include these after the base motion files:

```html
<link rel="stylesheet" href="motion/deck-shell.css">
<script src="motion/deck-motion.js"></script>
<script src="motion/deck-shell.js"></script>
```

`deck-shell.js` injects the controls automatically. Opt out only for a
deliberately kiosk-style deck with `data-deck-shell="off"` on `<html>` or
`<body>`.

## Required behaviour

- Show current slide as `NN / NN`.
- Keep **whole-deck progress** separate from **phase progress**.
- Previous/next buttons walk phases first in live mode.
- Right-half stage click advances one phase; left-half click reverses one phase.
- A slide may sit idle forever without its phase changing. Slide entry never auto-advances a beat.
- Static mode walks slide-to-slide while every slide displays its accepted
  final frame.
- `O` opens overview; `F` toggles fullscreen; `S` toggles static mode.
- Arrow keys, Space, Enter, PageUp/PageDown remain usable.
- Home/End jump to first/last slide.
- Clicking the left/right half of the stage navigates unless the click started
  on an interactive control or selected text.
- Overview titles come from `data-title`, then `h1/h2`, then `aria-label`.
- Hash state is `#<slide>.<phase>`; a slide-only state is `#<slide>`.
- Reduced motion is always a complete static final frame; the static toggle is
  disabled because the user preference already chose that mode.
- Print and capture hide the shell.

## Geometry boundary

The shell, progress track and overview dialog are siblings of the stage,
positioned against the viewport. Never place presenter controls inside
`[data-stage]`. A runtime control may not consume safe-area space, alter slide
box dimensions, or become a target for a slide emphasis.

## Customisation boundary

Theme colour, labels, border treatment and compact/expanded chrome may change.
The following may not: phase-first next/prev, left/right stage click semantics,
static-final-frame behaviour, hash state, reduced-motion collapse, or the
separation of slide and phase indicators. Do not fork these behaviours per deck.

## Accessibility

Use native buttons and `dialog`; keep keyboard focus visible; return focus to
the control that opened the overview; expose a polite live-region status for
slide/phase changes.

## Source pattern

This shell is normalized from the presenter controls proven in the AI UI/UX
13-slide deck: compact bottom controls, a separate 3px whole-deck progress bar,
overview navigation, static-final-frame mode and fullscreen.
