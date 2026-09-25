# HyperFrames video pipeline

## Goal

Video is a derivative of the same accepted HTML presentation, not a second graphics
implementation. The validated deck JSON is compiled once by the normal html-slide
planner/composer. `tools/compose_video.py` then adds only timing attributes and a
seek-safe adapter to that HTML. HyperFrames captures the resulting DOM frame by frame
and encodes it to video.

```
deck.json
   ↓
build_deck()
   ↓
accepted self-contained HTML
   ├─ presentation / PNG / PDF / PPTX
   └─ timing attributes + seek adapter
          ↓
       HyperFrames
          ↓
          MP4
```

Do not create a video-only content tree, React renderer, or duplicated layout
implementation. `timing.json` is execution metadata only: scene boundaries, target
IDs and semantic cue times. It must not copy blocks, layout markup, design tokens or
user-facing content.

## Requirements

- Python 3.10+
- Node.js 22+
- repository-level `npm install` (pins `hyperframes`)
- FFmpeg / ffprobe
- the repository Pretendard WOFF2 for deterministic Korean video typography

HyperFrames is used as the capture/encode backend. The project remains authored by
html-slide; HyperFrames Studio/templates are not a second design system.

## Timing contract

Defaults:

- stage: 1920×1080
- frame rate: 30 fps
- base scene reading time: 4.0 s
- semantic lead: 0.6 s
- phase spacing: 1.2 s
- structural scene fade: 0.35 s

Each slide becomes one HyperFrames `.clip` with explicit `data-start` and
`data-duration`. The root receives `data-composition-id`, dimensions, duration,
fps and `data-no-timeline`. Timing stays contiguous and every cue retains the
validated motion module, target and reason.

Inspect/build the video HTML without encoding:

```sh
python tools/compose_video.py deck.json \
  --out dist/video/index.html \
  --timing-out dist/video/timing.json
```

## Motion contract

Semantic motion is still chosen before expression. The 27 expression patterns live
in `core/motion-patterns.json`; there are no renderer-specific `html`/`remotion`
support flags.

Interactive presentation motion may use CSS transitions and the presenter runtime,
but those are wall-clock mechanisms. The generated video composition disables CSS
transitions and uses `core/hyperframes_runtime.js` to reproduce the same pending and
accepted final CSS states with finite paused Web Animations API animations. Existing
transient pattern choreography is ported to finite WAAPI keyframes. Number counting
and scramble/decode are converted to deterministic frame-indexed value sequences.

Render-critical video motion must not depend on `Date.now`, `performance.now`,
unregistered `requestAnimationFrame`, timers, unseeded randomness or infinite loops.
The accepted final frame remains the same static HTML content. Word/character effects
must settle to an unsplit final text run so Korean typography and kerning do not drift.

When `pattern: "auto"` is used, `core/motion_patterns.py` resolves the expression
once before HTML is emitted. HyperFrames receives that resolved HTML; it does not make
another design or motion selection.

## Canonical render command

```sh
npm install
python tools/render_video.py deck.json --out dist/video.mp4
```

The renderer performs:

1. validate and plan the deck;
2. build the canonical self-contained HTML with the repository font embedded;
3. compile timing-only metadata and instrument the HTML for HyperFrames;
4. run HyperFrames lint;
5. render H.264 MP4 through HyperFrames;
6. capture representative PNG snapshots around scene and semantic-cue boundaries;
7. inspect the encoded file with system ffprobe;
8. verify codec, yuv420p-compatible pixel format, dimensions, fps and duration;
9. write `video.qa.json`.

Use `--workers 1..24` to override HyperFrames worker auto-selection. Use
`--keep-work` when the generated `index.html`, `timing.json` and sampled PNGs
must remain available for inspection. `--skip-frame-qa` intentionally skips the
snapshot gate but not encoded-output verification.

## GitHub Actions

`.github/workflows/video-check.yml` is the contract/browser gate. It installs the
pinned HyperFrames CLI, runs modular/video tests, builds the maintained showcase
composition, runs HyperFrames lint/check and uploads QA snapshots.

`.github/workflows/render-video.yml` is the full MP4 path. It supports manual
`workflow_dispatch` and disposable `render/**` transport branches. A transient
branch carries job input only under `.render/`; the workflow checks out the default
branch as trusted renderer code and extracts only that data directory from the
triggering commit.

Optional `.render/request.json`:

```json
{
  "spec_path": "deck.json",
  "output_name": "pohang-intro-60s",
  "workers": "auto"
}
```

`workers` is `auto` or an integer from 1 to 24. Successful push-triggered render
branches are deleted by the cleanup job. Failed branches remain for diagnosis and
should be removed after inspection. Rendered MP4, QA JSON, generated HTML/timing and
sampled PNGs are workflow artifacts, never maintained repository history.

## Verification boundary

Automated checks cover:

- timing continuity, target binding and cue bounds;
- canonical HTML composition attributes;
- deterministic adapter rules (no wall-clock render motion);
- HyperFrames lint/runtime/layout checks;
- representative 1920×1080 PNG snapshots;
- H.264 codec, 8-bit 4:2:0 pixel format, dimensions, fps and duration.

Snapshots still require visual inspection for safe area, clipping, overlap, text fit,
image quality and whether semantic emphasis is perceptible. A green codec/duration
report is not visual acceptance.

Framework changes should run:

```sh
python -m unittest discover -s tests -p 'test_modular.py'
python tests/modular_runtime_check.py
python -m unittest tests.test_video_pipeline
python tools/compose_video.py examples/modular-showcase.json \
  --out dist/video-ci/index.html \
  --timing-out dist/video-ci/timing.json
./node_modules/.bin/hyperframes lint dist/video-ci
./node_modules/.bin/hyperframes check dist/video-ci --samples 7 --no-contrast --frame-check --snapshots
python tools/verify_video.py dist/video-ci/timing.json
```

Generated HTML compositions, timing files, frames, videos and QA captures for user
jobs stay outside Git.
