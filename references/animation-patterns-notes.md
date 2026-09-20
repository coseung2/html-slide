# animationpatterns.art — catalog notes (public documentation)
# Source: https://animationpatterns.art/animations
# Vendored rationale: pattern vocabulary (reveal/highlight/morph/count-up/stagger categories) behind motion/patterns/ grouping.

CSS & SVG Motion Library

# Animation Patterns

Production-minded CSS and SVG motion patterns rebuilt from first principles. Each detail page pairs a live stage with notes on structure, timing, accessibility, and reduced-motion fallbacks.Live demos, implementation notes, and reduced-motion fallbacks for production CSS and SVG motion.

* Live stagesReal UI contexts instead of static thumbnails
* Copy-ready recipesMarkup, CSS, motion notes, and source tabs
* Reduced-motion awareFallback behavior called out per pattern

65Patterns

9Featured

3Formats

## Pattern Library

65patterns organized into 5focused collections for feedback, loading, controls, layout, and visual effects. Search by behavior or tag when you already know the motion you need.

65patternsin All

[### Grid Row Accordion Expand

An accordion that animates content height without measuring it — the outer wrapper is display: grid, and a CSS transition between grid-template-rows: 0fr and 1fr handles natural panel height. Three product contexts each tune the rhythm: an FAQ Stack (single-open help-centre disclosure), a Checkout Stepper (sequential summary rows), and a Filter Dock (multi-open sidebar groups with a count badge).

accordionexpand-collapsegrid-template-rows0fr-1frauto-height](/animations/grid-row-accordion-expand/)[CSSFeatured

### Shared Element Layout Transition

Progressively-enhanced gallery → detail morph using the View Transition API where supported, with a same-document FLIP fallback that keeps the same hero, title, and metadata anchors moving regardless of browser support. Three rhythms: balanced default, gentle settle, and a sharper power-curve.

view-transitionsshared-elementflip-fallbacklayout-transitionview-transition-nameprogressive-enhancementprefers-reduced-motion](/animations/shared-element-layout-transition/)[X axis · linked · X axis · linked ·X axis · linked · X axis · linked ·

Y axis · linked · Y axis · linked ·Y axis · linked · Y axis · linked ·

CSS

### Axis-aware Scroll-linked Marquee Ticker

Scroll-linked marquee ticker that documents axis ownership (X vs. Y), duplicate-track accessibility (aria-hidden on the dupe), and a static reduced-motion state. Three variants: horizontal news, vertical stats, and a paired axis-cross layout.

marqueetickerscroll-linkedduplicate-trackaxis-awarearia-hiddenprefers-reduced-motion](/animations/axis-aware-scroll-linked-marquee-ticker/)[CSS

### Fixed Background Parallax Baseline

Foreground scrolls past a fixed background image via background-attachment: fixed. Three motion shapes — Linear (steady), Eased (calmer editorial pace), and Steps (snap card-to-card) — each with explicit mobile + reduced-motion fallbacks since iOS Safari ignores fixed-attachment.

parallaxbackground-attachmentfixed-backgroundduplicated-stackios-fallbackprefers-reduced-motion](/animations/fixed-background-parallax-baseline/)[CSS

### Practical Scroll Snapping Caveats

Horizontal scroll-snap rail covering the production caveats — mandatory vs. proximity, scroll-padding for sticky controls, focus framing within the snap zone, and a Padding Trap variant where a tall outlier card breaks alignment until scroll-padding is right.

scroll-snapscroll-snap-typescroll-paddingmandatoryproximityfocus-framekeyboard-a11y](/animations/practical-scroll-snapping-caveats/)[All

New

Saved

CSS

### Segmented Control Radio Tab Group

Segmented control built on real with an accent pill that slides under the checked option via translateX driven by a CSS custom property. Three layouts: horizontal day/week/month, vertical filters, and a compact two-segment pill.

segmented-controlradio-grouptranslateXpill-slidecss-custom-propertiesaria-checkedkeyboard-a11y](/animations/segmented-control-radio-tab-group/)[type a line,pause a beat,type the next.

CSS

### Multiline Typewriter Line-Step Sizing

Three CSS techniques for line-by-line text reveal — a max-height stack, a clip-path top-edge wipe, and a clip-path left-edge draw. Each row appears as a complete line-step, never a partial clip; the technique determines whether rows pop in vertically, wipe down, or draw left-to-right.

multilineline-stepmax-heightclip-pathstaggerno-layout-shiftprefers-reduced-motion](/animations/multiline-typewriter-line-step-sizing/)[GlitchGlitchGlitchGlitch

CSS

### Glitch Text Clip-path Slice Bands

Readable text stays still; two aria-hidden RGB-shifted decoys ride animated clip-path inset bands so the glitch fires without sacrificing legibility. Three cadences: a short edge flicker, an ambient scanline drift, and an aggressive dropout stutter.

glitchclip-pathrgb-splitmix-blend-modetext-effectaria-hiddenprefers-reduced-motion](/animations/glitch-text-clip-path-slice-bands/)[Reveal

CSS

### Clip-path Reveal Transition

A layout stable reveal transition that keeps the element box fixed while clip-path shapes expose content. Three expression methods separate inset wipes, circle-origin reveals, and polygon shutters before mapping them to product surfaces.

clip-pathrevealtransitioninsetcirclepolygonprefers-reduced-motion](/animations/clip-path-reveal-transition/)[Aurora

CSSFeatured

### Aurora Gradient Sweep

Layered radial-gradient blobs drift behind readable foreground content via transform + opacity, no gradient-stop interpolation. Three palettes — cool polar, warm sunset, and an ambient quiet header for low-motion contexts.

auroraradial-gradientbackground-layerblurambient-motionprefers-reduced-motion](/animations/aurora-gradient-sweep/)[Cube

CSSFeatured

### Animated 3D Cube Perspective Walkthrough

Six-face CSS 3D cube that separates scene perspective from per-face transform-order so the rotate → translateZ relationship stays inspectable. Three teaching variants: a balanced centred scene, a wide-origin camera bias, and a slow face-assembly view.

css-3dperspectivepreserve-3dtranslateZtransform-orderperspective-originprefers-reduced-motion](/animations/animated-3d-cube-perspective-walkthrough/)[68%

CSSFeatured

### Semantic Pie/Donut Chart Markup Strategy

Conic-gradient donut chart paired with a real

/1. legend so screen readers + copy-paste users see the data without color or motion. Three layouts: side-legend stat card, stacked overlay, and a centered KPI tile.

   donut-chartconic-gradientol-legendfigcaptiondata-vizdecorative-svgaria-hidden](/animations/semantic-pie-donut-chart-markup-strategy/)[ActivityToday

CSS

### Fixed Grid Cell Overlay Pulse

A fixed CSS grid keeps every cell in its original track while an absolutely positioned overlay pulse highlights one active cell. Three expression methods separate outline ring, inner glow, and shadow halo treatments before mapping them to product contexts.

fixed-gridoverlay-pulsecss-gridactive-cellno-layout-shiftz-indexprefers-reduced-motion](/animations/fixed-grid-cell-overlay-pulse/)[Front

Back

CSSFeatured

### Flip Card Front/Back Face Handling

Two faces share one plane via backface-visibility: hidden + a single rotateY/X transform, with :hover/:focus-within driving the flip. Three variants: a Y-axis profile card, an X-axis product tile, and a Quiet Swap opacity-crossfade fallback for reduced motion.

flip-cardbackface-visibilitypreserve-3drotateYrotateXfocus-withinprefers-reduced-motion](/animations/flip-card-front-back-face-handling/)[CSSFeatured

### Gradient Text Sweep

A narrow highlight band sweeps across live headline text via background-clip + an explicit two-axis background-size, with a static fallback color for engines without clip support. Three variants: a wide launch headline, a tight command label, and a slower editorial kicker.

gradient-textbackground-clipbackground-sizebackground-positionsupports-fallbacktext-shadowprefers-reduced-motion](/animations/gradient-text-sweep/)[CSSFeatured

### Starlight Shimmer Text

A clipped gradient glint sweeps across live text while a separate decorative sparkle layer adds star-like dots. Three cadences: a dramatic midnight pass, an orbit-sync twin-glint ping, and an ambient continu