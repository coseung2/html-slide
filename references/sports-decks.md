# Sports decks: media safety and selective emphasis

Use this supplement for standings, scoreboards, match reports, player statistics
and fixture previews. The base stage, typography, target binding and export
contracts in `SKILL.md` still apply. `sports.css` is opt-in; do not apply a global
`img { object-fit: contain !important }` patch to an entire existing deck.

## Review the actual assets, not just the URLs

Before layout work, inspect the pixels of every distinct embedded asset. A club
wallpaper or a two-crest placeholder is not a match photograph, even when its
`alt`, caption or source URL says "actual match photo". A data URI proves the
file is embedded, not that it depicts the stated fixture. Keep these distinctions
in the source record: verified match photo, reference/action image, crest,
club graphic, unavailable. Never quietly substitute a different match or player.

Inspect transparent assets against a solid contrasting background. Stray fragments
from another crest at the bottom of a sprite can survive successful loading.
Crop the verified crest region; do not remove disconnected legitimate details
(such as lettering or a football) by blindly retaining the largest alpha component.
Keep the original asset and record the crop. Do not invent missing official logos.

## Separate media and information zones

Create explicit neighboring grid/flex slots for an image, a scorebug, names and
statistics. A crest belongs in its own sized slot, not an absolutely positioned
portrait overlay that can cover the last paragraph. Preserve the full cutout or
crest with `contain`; use `cover` only for a deliberately reviewed photo crop.

```html
<figure class="match-layout" data-visual>
  <div data-media-zone>
    <img src="data:image/webp;base64,..." alt="Describe the verified image"
         data-image-kind="cutout">
  </div>
  <figcaption class="scorebug">ALPHA 3 — 0 BETA</figcaption>
</figure>
```

The parent must allocate a finite height to each row. `overflow: hidden` is a
frame boundary, not evidence that the content fits. Do not move a photo behind
important text and call the collision fixed. If an intentional image caption
overlay is necessary, mark just that reviewed caption with `data-media-overlay`.
The exception does not excuse subject occlusion or low contrast.

## Motion budget: one meaningful group beat

Include `motion/sports.css` after the base stylesheet. Leave ordinary tables,
fixtures, badges and result lists static. Select comparison or focus on the
specific scene, normally no more than one or two advances. Do not animate every
row independently or add looping glows, fake live indicators and number counters
that briefly display fabricated match scores.

### Shared-scale comparison

```html
<section data-slide="03" data-sports="compare" data-start="0" data-step="1">
  <p>ALPHA: 15 points</p>
  <div class="sport-bar-track">
    <i class="sport-bar-fill" style="--value:100%" aria-hidden="true"></i>
  </div>
  <p>BETA: 12 points</p>
  <div class="sport-bar-track">
    <i class="sport-bar-fill" style="--value:80%" aria-hidden="true"></i>
  </div>
</section>
```

Use the same denominator, declare the compared metric and keep every value and
label readable before the bars reveal. The 420 ms transform-only transition is
one group beat. Back reverses it. Static, no-JS, reduced-motion and print show the
final bars immediately.

### Target-bound record emphasis

```html
<section data-slide="04" data-sports="focus" data-start="0" data-step="1">
  <div id="record" class="sport-focus">
    <strong>16</strong><p>Goals</p>
    <i class="sport-cue" data-hl data-target="#record"
       data-step="1" aria-hidden="true"></i>
  </div>
</section>
```

The emphasis is a child of its real target. It changes opacity over 240 ms and
remains as a visible final-state outline. Do not absolutely position an unrelated
rectangle over a value using page coordinates.

## Presenter shell and saving

Use the existing `deck-motion.js` + `deck-shell.js` + `deck-shell.css`, not a second
navigation state machine. Preserve Static (`S`), Overview (`O`), Fullscreen (`F`),
slide/phase counters and the bottom progress bar. Put source/credit shortcuts on
another key (for example `C`) so they do not steal `S`. Keep additional controls
outside the authored stage and check them in a short landscape viewport.

An HTML save operation must retain the runtime scripts and inline assets. Remove
only generated presenter chrome, transient active/phase/capture classes and
`inert`/`aria-hidden` from slide roots. Reopening the saved file must create exactly
one working shell. Do not remove the first `<script>` indiscriminately: that can
silently delete navigation instead of a temporary embedding helper.

## Data boundaries

Layout repair is not current-season fact verification. Preserve supplied figures
unless research/correction is requested; record any scoped summary or derivation.
A top-six table cannot itself establish what happened to seventh place. A sum of
the provided ten scorelines may be labeled as a derived total, but not as an
independently verified league statistic. Official-looking URLs do not replace
reading and verifying the underlying report. Avoid "LIVE PHOTO" on a fallback.

## Additional regression gate

Run the normal linter and accepted-frame export workflow. For a **self-contained**
HTML, also run:

```sh
python tools/sports_qa.py deck.html --out out/sports-qa
python tests/sports_check.py
```

`sports_qa.py` uses Playwright/Chromium and blocks network requests. It measures all
slides at 1920×1080, 1280×720, 1024×768, 390×844 and 844×390, writes `geometry.json`
and first-viewport screenshots, and fails on detected clipping, image/text or
text/text collisions, missing images, unbound emphasis, chrome collisions,
external requests and layout drift. It supplements, not replaces, `slide_lint.py`.
Do not feed it an unbundled deck with external CSS/JS and interpret the missing
navigation error as a slide defect; bundle the authored resources first.

Review every screenshot at useful resolution. Pixel/alpha accuracy, which player
is visible, foreground subject cropping, contrast on a complex image, factual
accuracy and image permissions still require separate review. A zero geometry
count does not certify those properties. Test actual motion, reverse, static,
reduced-motion changes, modal keyboard isolation and save/reopen as well.
