# HyperFrames video pipeline

## Goal

Video output reuses the same validated `core/deck.schema.json` source and the same
HTML renderer used by the presentation deck. There is no second React renderer and no
video-only content document.

The compiler builds the accepted HTML layout first, resolves the same semantic motion
and expression-pattern choices, then packages each slide as an isolated HyperFrames
sub-composition. HyperFrames supplies deterministic seek-by-time capture and encoding.

## Boundary

```
deck.json
   |
   +-- compose_deck.py  -> deck.html -> PDF / PPTX
   |
   +-- render_video.py
          |
          +-- build_deck()                  canonical HTML renderer
          +-- hyperframes_project.py        isolated slide compositions
          +-- core/hyperframes_runtime.js   paused GSAP seek timeline
          +-- hyperframes check/snapshot/render
          +-- ffprobe + sampled-frame QA
          |
          +-- video.mp4
```

The deck JSON remains the content source of truth. HyperFrames project HTML, manifests,
sampled PNGs and QA reports are execution artifacts and do not belong in maintained
repository history for a user job.

## Why slides are isolated

The top-level composition owns scene timing only. Each slide is emitted as
`compositions/<slide-id>.html` and mounted with `data-composition-src`.

This keeps layout ownership identical to the presentation HTML while preventing
different slides from sharing one live DOM during layout validation or capture. It
also avoids seek-order coupling between GSAP targets on different scenes.

The parent composition therefore uses `data-no-timeline`. Each slide fragment owns
its own paused GSAP timeline registered under its composition ID.

## Timing contract

- Stage: 1920x1080.
- Default frame rate: 30 fps.
- Base reading time: 4 seconds per slide.
- Semantic cue lead: 0.6 seconds.
- Presenter-phase spacing: 1.2 seconds.
- Default cue expression duration: 0.8 seconds.
- Scene durations are contiguous.
- A cue is generated only from a validated slide `motion` declaration.
- Every cue retains its semantic module, target and reason.
- `pattern` changes expression, never semantic meaning.
- Slides with no semantic motion remain complete readable frames.

Timing overrides are render options; they do not create a second content spec.

## Motion contract

Choose semantic motion before expression. The canonical pattern catalog is
`core/motion-patterns.json`; deterministic ranking lives in
`core/motion_patterns.py`.

Presentation HTML expresses patterns through `core/motion_patterns.css` and
`core/runtime.js`. HyperFrames uses the same resolved pattern choice but implements
the seek-safe expression in `core/hyperframes_runtime.js`.

A pattern may be marked `hyperframes: "supported"` only after its GSAP path is
implemented and covered by regression tests. HyperFrames motion must be seek-safe:

- timelines are paused;
- capture time, not wall-clock time, owns progress;
- do not use CSS transitions as video timing;
- avoid layout-snapping tween properties such as animated letter spacing;
- do not measure geometry inside timeline callbacks;
- randomness must be deterministic;
- temporary overlays must resolve away from the accepted final frame.

When no visual expression was requested, use `pattern: "auto"` rather than choosing
an attractive effect first.

Inspect candidates with:

```sh
python tools/motion_patterns.py search \
  --intent result --target score --semantic score-reveal \
  --renderer hyperframes --tone sports --intensity high --density low
```

## Canonical render command

Install the isolated video dependencies once. HyperFrames MP4 encoding and the QA probe also require system `ffmpeg`/`ffprobe` on `PATH`:

```sh
cd video
npm install
cd ..
ffmpeg -version
ffprobe -version
```

Then render through the repository entrypoint:

```sh
python tools/render_video.py deck.json --out dist/video.mp4
```

`render_video.py` performs these phases:

1. validate the deck against normal html-slide contracts;
2. build the canonical HTML representation with an embedded authorized WOFF2;
3. split slides into external HyperFrames sub-compositions;
4. validate the generated manifest and cue bounds;
5. copy the pinned browser GSAP runtime into the temporary project;
6. run `hyperframes check` at representative scene/cue checkpoints;
7. render representative PNG snapshots around semantic boundaries;
8. render the full MP4 with HyperFrames workers;
9. inspect the encoded result with `ffprobe`;
10. verify codec, pixel format, dimensions, fps, duration and sampled PNG dimensions;
11. write `*.qa.json` beside the MP4.

Use `--keep-work` when generated composition files and sampled PNGs must remain for
inspection. Use `--skip-frame-qa` only for an intentional fast render; encoded video
validation still runs.

The repository-maintained `assets/fonts/PretendardVariable.woff2` is the default
video font, so Korean metrics do not depend on fonts installed on the runner.

## Render workers

Prefer `--workers N` for HyperFrames rendering. The old `--concurrency` option is
accepted temporarily as a compatibility alias and converted to a bounded worker
count.

Transient `.render/request.json` jobs may specify:

```json
{
  "spec_path": "deck.json",
  "output_name": "pohang-intro-60s",
  "workers": "3"
}
```

The request validator rejects path traversal, absolute paths, non-JSON specs, invalid
artifact names, invalid worker counts and unknown keys.

## GitHub Actions

`.github/workflows/video-check.yml` is the contract gate. It installs the pinned
HyperFrames/GSAP runtime, runs modular and video tests, compiles the maintained
showcase into isolated sub-compositions and runs `hyperframes check` at semantic
checkpoints.

`.github/workflows/render-video.yml` is the full render path. It supports manual
dispatch and disposable `render/**` transport branches. For push-triggered jobs,
the workflow checks out the default branch as trusted renderer code and extracts only
the triggering branch's `.render/` job data.

After a successful push-triggered render, the cleanup job deletes the transport
branch. Rendered MP4, QA JSON, generated project HTML and sampled PNGs are uploaded as
short-lived artifacts and are never committed.

## Verification boundary

Automated checks cover:

- deterministic scene timing and cue bounds;
- HyperFrames composition/runtime contract checks;
- layout and contrast at representative semantic checkpoints;
- sampled PNG existence and dimensions;
- encoded H.264 codec and planar 8-bit 4:2:0 pixel format;
- output dimensions, fps and duration.

Sampled PNGs still require visual inspection for safe area, clipping, text fit,
image quality and whether the intended emphasis is perceptible. A valid codec/duration
report is not visual acceptance.

Framework changes should run:

```sh
python -m unittest discover -s tests -p 'test_modular.py'
python tests/modular_runtime_check.py
python -m unittest tests.test_hyperframes_pipeline tests.test_motion_patterns tests.test_render_request
cd video && npm install && cd ..
python tools/hyperframes_project.py examples/modular-showcase.json \
  --out-dir dist/video-ci \
  --font assets/fonts/PretendardVariable.woff2
cp video/node_modules/gsap/dist/gsap.min.js dist/video-ci/gsap.min.js
video/node_modules/.bin/hyperframes check dist/video-ci --json
```

Generated compositions, manifests, videos, QA reports and sampled frames are task
artifacts and stay outside Git.
