# Remotion video pipeline

## Goal

The video pipeline reuses the same validated `core/deck.schema.json` source used by
HTML decks. It does not ask an AI to invent a second video-only content document.
`tools/compose_video.py` first runs the normal deck planner, then compiles the resolved
layout slots, art-direction tokens, self-contained raster media and semantic motion
phases into a deterministic Remotion storyboard.

## Boundary

```
deck.json
   ├─ compose_deck.py  -> HTML / PDF / PPTX
   └─ compose_video.py -> storyboard.json -> video/ Remotion runtime -> MP4
```

The deck spec remains the content source of truth. The storyboard is an execution
artifact and should not be committed for a user job.

## Storyboard contract

The generated storyboard preserves:

- the planner-selected layout and exact slot-to-block assignment;
- selected palette and dataviz CSS variables;
- typography pack identity;
- validated content blocks;
- image/logo media as reviewed base64 raster data;
- every semantic motion target, reason and presenter phase;
- an optional Remotion motion-pattern choice attached to the semantic motion;
- deterministic scene start frames and durations.

Do not expose internal production metadata such as `communicationGoal`, layout IDs or
module IDs as visible video copy. They are available for routing and QA only.

## Timing contract

- Default stage: 1920x1080.
- Default frame rate: 30 fps.
- Semantic cues start near scene entry: default lead is 0.6 seconds.
- Each scene retains a base reading duration plus additional time for declared phases.
- Default phase spacing is 1.2 seconds.
- Motion cues are generated only from validated slide `motion` declarations.
- A cue always retains its original target and reason.
- The optional `pattern` field changes the Remotion expression, not the semantic meaning of the motion module.
- No blanket per-element animation is introduced by the compiler.
- A scene without semantic motion renders immediately as a complete readable scene.

Defaults can be overridden without changing the deck spec:

```sh
python tools/compose_video.py deck.json --out dist/storyboard.json \
  --fps 30 --base-seconds 4 --step-seconds 1.2 --lead-seconds 0.6 \
  --transition-seconds 0.35
```

Use `--asset-root` when media paths should resolve somewhere other than the deck
specification directory.

## Native renderer scope

The Remotion runtime is layout-aware. It currently maps the repository's maintained
modules rather than reducing everything to generic cards:

- statement, quote and comparison text;
- metric with `number-count`;
- ranking, timeline, process and bullet list with `sequence-step`;
- bar and line charts with `chart-grow`;
- score with `score-reveal`;
- image and logo with target-bound `focus`;
- planner layouts including hero, comparison, split, stat grid, ranking board,
  timeline/process and image focus.

`focus` is applied only to its declared block. Scene entry opacity is structural
transition behavior, not semantic emphasis.

### Remotion motion-pattern pool

The video renderer maintains 19 explicit patterns in `video/motion-patterns.json`:
`kinetic-type`, `flat-shape`, `info-motion`, `ui-motion`, `card-stack-3d`,
`particle-warp`, `glitch`, `liquid-morph`, `isometric-build`, `paper-cut`,
`type-mask`, `environment-type`, `occlusion`, `scramble-decode`, `variable-font`,
`swiss-grid`, `extruded-type`, `street-collage`, and `path-drawing`.

Choose a pattern only after selecting the semantic target and writing the reason.
The pattern is an expression layer; it must not become the reason a target is
animated. A deck can therefore remain valid HTML even when the Remotion renderer
uses a richer visual expression.

Example motion declaration:

```json
{
  "module": "focus",
  "target": "headline",
  "reason": "핵심 문장을 한 번만 강하게 주목시킨다",
  "pattern": "kinetic-type"
}
```

The Remotion wrapper always resolves to the accepted final content frame. Patterns
that add temporary particles, occluders, grids, paper layers or RGB displacement
must disappear after the cue rather than leaving the information obscured.

The video entrypoint loads the repository-maintained Pretendard WOFF2 through CSS so Korean text does not depend on fonts installed on the runner. Remotion waits for CSS fonts before rendering. The HTML renderer remains the reference for exact browser layout fidelity. When a new
HTML content or motion module is added, add or explicitly reject its video renderer
instead of silently falling back to unrelated motion.

## Canonical render command

Install the isolated runtime once:

```sh
cd video
npm install
cd ..
```

Then use one repository-level command:

```sh
python tools/render_video.py deck.json --out dist/video.mp4
```

The renderer performs these phases in order:

1. compile the validated deck into a deterministic storyboard;
2. validate contiguous scene timing, slot assignment and cue bounds;
3. run the Remotion TypeScript typecheck;
4. run `remotion browser ensure`;
5. render H.264 with planar 8-bit 4:2:0 output;
6. render representative PNGs at scene/transition/cue boundaries;
7. inspect the MP4 with Remotion's bundled `ffprobe`;
8. verify codec, dimensions, fps, duration and sampled-frame dimensions;
9. write `video.qa.json` beside the MP4.

Use `--keep-work` when the storyboard and sampled PNGs must remain available for
human review. Use `--skip-frame-qa` only for an intentional fast render; encoded
video validation still runs.

The composition accepts the raw storyboard as its props object. The packages in
`video/package.json` keep `remotion` and `@remotion/*` aligned to the same
pinned version.

## GitHub Actions

`.github/workflows/video-check.yml` is the cheap contract gate. It runs on video
pipeline changes, installs the pinned runtime, runs modular and video unit tests,
typechecks the Remotion source, compiles the maintained showcase storyboard and
validates that storyboard. It deliberately does not encode a full MP4 on every push.

`.github/workflows/render-video.yml` is the full render path. Run **Render Remotion
video** manually and provide a repository-relative JSON spec path, artifact base name
and concurrency. The workflow validates the request, runs `render_video.py` and
uploads MP4, QA JSON, storyboard and sampled PNGs as a short-lived Actions artifact.

`workflow_dispatch` is intentionally not an excuse to commit user-specific job
inputs. Normal user deck specs, downloaded media, videos and QA captures remain
outside Git. The manual workflow is appropriate for maintained fixtures or inputs
that the user explicitly intends to make public in the repository.

## Verification boundary

Automated checks now cover:

- storyboard timing, target binding, cue bounds and slot coverage;
- self-contained media passed by the deck compiler;
- TypeScript type correctness;
- existence and dimensions of representative PNG frames;
- encoded H.264 codec, planar 8-bit 4:2:0 format (`yuv420p` or FFmpeg's full-range `yuvj420p` name), expected dimensions, fps and duration.

The sampled PNGs still require visual inspection for safe area, clipping, overlap,
text fit, image quality and whether the semantic emphasis is actually perceptible.
Do not claim visual acceptance solely from a green encoded-output report.

Framework changes should run:

```sh
python -m unittest discover -s tests -p 'test_modular.py'
python -m unittest tests.test_video_pipeline
cd video && npm run typecheck && cd ..
python tools/compose_video.py examples/modular-showcase.json --out dist/video-ci/storyboard.json
python tools/verify_video.py dist/video-ci/storyboard.json
```

Generated storyboards, frames, videos and QA captures are task artifacts and stay
outside Git.
