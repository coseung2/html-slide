/* ===========================================================================
   motion/deck-motion.js — stage fitting, step phases, FLIP.

   Nothing here computes the position of an emphasis. Highlights are DOM
   children of their targets, so they follow for free; this file only handles
   what CSS cannot: the stage scale, the step state machine, and FLIP.

   The `.deck-live` contract
   -------------------------
   The accepted frame must never depend on this file. Without it — file missing,
   JS off, prefers-reduced-motion — the browser renders the complete frame from
   plain CSS, because every phase rule in motion.css is gated on `.deck-live`.
   When it does run, it adds `.deck-live` to <html> and the slide opens on its
   `data-start` phase so the presenter can build the frame up.
   =========================================================================== */
(function (global) {
  'use strict';

  const STAGE_W = 1920, STAGE_H = 1080;
  const LIVE = 'deck-live';

  /* ---------------------------------------------------------------- stage --
     Letterbox with min(): one scale for both axes. Separate x/y scales turn
     circles into ellipses and make every traced radius a lie. */
  function fit(stage) {
    const k = Math.min(innerWidth / STAGE_W, innerHeight / STAGE_H);
    stage.style.transform =
      `translate(${(innerWidth - STAGE_W * k) / 2}px, ` +
      `${(innerHeight - STAGE_H * k) / 2}px) scale(${k})`;
    return k;
  }

  /* ----------------------------------------------------------------- FLIP --
     First, Last, Invert, Play. Call it around any DOM change that moves an
     element; the element is never animated through layout properties. */
  function flip(el, mutate, opts) {
    const o = opts || {};
    const first = el.getBoundingClientRect();
    mutate();                                        // Last (DOM update)
    const last = el.getBoundingClientRect();
    const dx = first.left - last.left;
    const dy = first.top - last.top;
    const sx = last.width ? first.width / last.width : 1;
    const sy = last.height ? first.height / last.height : 1;
    if (!dx && !dy && sx === 1 && sy === 1) return null;
    const anim = el.animate([
      // Invert: the element visually returns to where it was. Translate before
      // scale — scaling first would move the element's own origin.
      { transform: `translate(${dx}px, ${dy}px) scale(${sx}, ${sy})` },
      { transform: 'none' }
    ], {
      duration: o.duration || 320,
      easing: 'cubic-bezier(0.77, 0, 0.175, 1)',
      fill: 'both'
    });
    anim.finished.then(() => { el.style.willChange = ''; }).catch(() => {});
    return { dx: dx, dy: dy, sx: sx, sy: sy };
  }

  /* ------------------------------------------------------------- typewriter --
     Split a `[data-type]` element into per-음절 spans. Doing this by hand in the
     markup is where it goes wrong: it is 40 wrapper elements nobody reviews,
     and the readable string has to survive the split for screen readers and
     static capture.

     So the text is read from the element's own textContent, split on code
     points (Array.from, so an emoji or a rare glyph is not cut in half), and
     written back as spans. The element keeps its complete text in the
     accessibility tree via aria-label. */
  function typeSplit() {
    document.querySelectorAll('[data-type]').forEach(el => {
      if (el.dataset.typed) return;                 // idempotent across reflows
      const text = el.textContent;
      el.textContent = '';
      el.setAttribute('aria-label', text);          // the sentence, whole
      Array.from(text).forEach((ch, i) => {          // code points, not code units
        const s = document.createElement('span');
        s.textContent = ch;
        s.style.setProperty('--i', i);
        el.appendChild(s);
      });
      el.classList.add('pat-type', 'is-typing');
      el.dataset.typed = '1';
    });
  }

  /* ---------------------------------------------------------------- steps --
     Reversibility is a state machine, not a rewind: back walks down to the
     slide's own start phase, then to the previous slide. A resize re-fits and
     re-measures, so a bound emphasis is never left on a stale box. */
  function Deck(root) {
    this.root = root;
    this.stage = root.querySelector('[data-stage]') || root;
    this.slides = Array.prototype.slice.call(root.querySelectorAll('[data-slide]'));
    const reduce = matchMedia('(prefers-reduced-motion: reduce)');
    this.reduce = reduce.matches;
    reduce.addEventListener('change', e => {
      this.reduce = e.matches;
      const staticMode = global.__deckShell?.isStatic() || false;
      document.documentElement.classList.toggle(LIVE, !this.reduce && !staticMode);
      this.phase = this.start(this.slide);
      this.render();
    });
    // `deck-ready` gates the interactive single-slide viewport. Without JS the
    // base CSS leaves complete slides in document order for print/capture/fallback.
    document.documentElement.classList.add('deck-ready');
    this.slide = 0;
    this.prevSlide = null;          // no transition on the first render
    this.phase = this.start(0);
    if (!this.reduce) document.documentElement.classList.add(LIVE);
    addEventListener('resize', () => this.reflow());
    if (document.fonts) document.fonts.ready.then(() => this.reflow());
    this.reflow();
    this.render();
  }

  /* Re-fit the stage. A method on the prototype: the constructor calls it while
     `this` already owns the stage, and nothing about it depends on a closure —
     which is exactly the crash the background fix patched over. */
  Deck.prototype.measure = function () { return fit(this.stage); };

  /* Phases a slide declares — read from the DOM, never from a config table, so
     the markup cannot drift away from the behaviour. */
  Deck.prototype.phases = function (i) {
    const s = this.slides[i];
    if (!s || this.reduce) return 0;
    let max = parseInt(s.getAttribute('data-step'), 10) || 0;
    s.querySelectorAll('[data-step]').forEach(el => {
      if (el !== s) max = Math.max(max, parseInt(el.getAttribute('data-step'), 10) || 0);
    });
    return max;
  };

  Deck.prototype.start = function (i) {
    const s = this.slides[i];
    if (!s || this.reduce) return 0;
    const n = parseInt(s.getAttribute('data-start'), 10);
    return Number.isFinite(n) ? Math.min(Math.max(n, 0), this.phases(i)) : 0;
  };

  Deck.prototype.render = function () {
    const from = this.prevSlide;                       // the scene we came from
    const dir = (from === null || from === undefined || from === this.slide)
      ? 0 : Math.sign(this.slide - from);
    const incoming = this.slides[this.slide];
    // The accepted plain-CSS frame is the finished state. Hidden slides therefore
    // sit on that finished frame unless we pre-position them. Suppress transitions
    // while an incoming slide is moved to its declared start phase; otherwise its
    // first visible beat is a reverse animation from final -> start.
    const preparing = Boolean(incoming && (from === null || from === undefined || from !== this.slide));
    if (preparing) incoming.classList.add('deck-prep');

    this.slides.forEach((s, n) => {
      const active = n === this.slide;
      // Only the scene we just left is "leaving". A transition is a pair, not a
      // pile: any other slide is simply off-stage.
      const leaving = !active && n === from;

      // Preserve the leaving slide's current phase through its exit. Every other
      // hidden slide is parked at data-start so the next activation is already in
      // the correct presenter state before it becomes visible.
      if (!leaving) {
        [...s.classList].filter(c => c.startsWith('deck-step-')).forEach(
          c => s.classList.remove(c));
        const parked = active ? this.phase : this.start(n);
        const max = Math.max(this.phases(n), 1);
        for (let p = 0; p <= max; p++) {
          s.classList.toggle('deck-step-' + p, parked === p);
        }
      }

      s.classList.toggle('is-active', active);
      s.classList.toggle('is-leaving', leaving);
      s.inert = !active;
      s.setAttribute('aria-hidden', String(!active));
    });

    // Flush the prepared start frame with transitions disabled, then release the
    // guard. Removing the guard changes no visual property, so no entry animation
    // is generated and the first presenter click remains the first real beat.
    if (preparing) {
      incoming.getBoundingClientRect();
      incoming.classList.remove('deck-prep');
    }
    this.prevSlide = this.slide;

    if (!this.stage) return;
    // Direction decides which side each scene enters and exits from, so a wipe
    // means the same thing every time it plays.
    if (dir) this.stage.classList.toggle('is-back', dir < 0);

    // The cut curtain is a transition, not a state: it flashes between the two
    // scenes and clears, so it is never on screen when nobody is moving.
    if (dir && this.stage.hasAttribute('data-transition')) {
      this.stage.classList.add('is-cutting');
      clearTimeout(this._cut);
      const ms = parseFloat(
        getComputedStyle(this.stage).getPropertyValue('--d-trans')) || 560;
      this._cut = setTimeout(() => this.stage.classList.remove('is-cutting'), ms / 2);
    }

    // Presentation chrome is an optional observer. The core runtime owns state;
    // shells, remotes and test harnesses subscribe instead of duplicating it.
    global.dispatchEvent(new CustomEvent('deck:state', { detail: this.state() }));
  };

  Deck.prototype.next = function () {
    if (this.phase < this.phases(this.slide)) { this.phase++; this.render(); return; }
    if (this.slide < this.slides.length - 1) {
      this.slide++;
      this.phase = this.start(this.slide);
      this.render();
    }
  };

  Deck.prototype.prev = function () {
    if (this.phase > this.start(this.slide)) { this.phase--; this.render(); return; }
    if (this.slide > 0) {
      this.slide--;
      this.phase = this.start(this.slide);
      this.render();
    }
  };

  /* A resize can change text metrics; re-fit and let the slide re-measure
     anything it positions from geometry (FLIP anchors, SVG paths). */
  Deck.prototype.reflow = function () {
    this.measure();
    this.slides.forEach(s => s.dispatchEvent(new CustomEvent('deck:reflow')));
  };

  Deck.prototype.state = function () {
    return {
      slide: this.slide,
      phase: this.phase,
      steps: this.phases(this.slide),
      slideCount: this.slides.length,
      reducedMotion: this.reduce
    };
  };

  Deck.prototype.goto = function (n, p) {
    if (!Number.isInteger(n) || n < 0 || n >= this.slides.length) return null;
    this.slide = n;
    const max = this.phases(n);
    const requested = Number(p);
    this.phase = Number.isFinite(requested)
      ? Math.max(0, Math.min(max, requested))
      : this.start(n);
    this.render();
    return this.state();
  };

  /* ----------------------------------------------------------------- boot --
     The linter drives the deck through `__deckGoto` and measures each slide
     under prefers-reduced-motion, where this file adds no phase state at all:
     it sees the complete frame. */
  function boot() {
    typeSplit();
    const deck = new Deck(document.body);
    global.deck = deck;
    global.__deckGoto = (n, p) => deck.goto(n, p);
    global.__deckNext = () => deck.next();
    global.__deckPrev = () => deck.prev();
    global.__deckState = () => deck.state();
    global.deckFlip = flip;

    addEventListener('keydown', e => {
      // A focused button owns Enter/Space; dialogs and editors own their keys.
      // Arrow navigation still works after clicking a presenter control.
      if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey ||
          document.querySelector('dialog[open]') ||
          e.target.closest?.('input,textarea,select,[contenteditable="true"]') ||
          (['Enter', ' '].includes(e.key) && e.target.closest?.('a,button'))) return;
      if (['ArrowRight', 'ArrowDown', ' ', 'Enter', 'PageDown'].indexOf(e.key) >= 0) {
        e.preventDefault(); deck.next();
      }
      if (['ArrowLeft', 'ArrowUp', 'PageUp'].indexOf(e.key) >= 0) {
        e.preventDefault(); deck.prev();
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})(typeof window !== 'undefined' ? window : globalThis);
