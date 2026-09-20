/* ===========================================================================
   motion/deck-shell.js — standard presenter UI for deck-motion.js.

   Auto-injects: previous/next, slide counter, phase counter, static-final-frame
   toggle, overview, fullscreen, whole-deck progress and stage-half click nav.
   It observes the Deck runtime; it does not own slide state or stage geometry.
   Opt out with data-deck-shell="off" on <html> or <body>.
   =========================================================================== */
(function (global) {
  'use strict';

  const REDUCE = global.matchMedia('(prefers-reduced-motion: reduce)');

  function titleOf(slide, i) {
    const explicit = slide.getAttribute('data-title');
    if (explicit) return explicit.trim();
    const h = slide.querySelector('h1,h2,[role="heading"]');
    if (h && h.textContent.trim()) return h.textContent.trim().replace(/\s+/g, ' ');
    const aria = slide.getAttribute('aria-label');
    return aria ? aria.replace(/^\s*\d+[.)]?\s*/, '').trim() : 'Slide ' + (i + 1);
  }

  function declaredPhases(slide) {
    let max = parseInt(slide.getAttribute('data-step'), 10) || 0;
    slide.querySelectorAll('[data-step]').forEach(el => {
      if (el !== slide) max = Math.max(max, parseInt(el.getAttribute('data-step'), 10) || 0);
    });
    return max;
  }

  function boot(attempt) {
    const deck = global.deck;
    if (!deck) {
      if ((attempt || 0) < 40) setTimeout(() => boot((attempt || 0) + 1), 25);
      return;
    }
    if (document.documentElement.dataset.deckShell === 'off' ||
        document.body.dataset.deckShell === 'off' ||
        document.querySelector('.deck-shell')) return;

    let staticMode = new URLSearchParams(location.search).get('mode') === 'static';
    let previousFocus = null;
    let lastHash = '';

    const nav = document.createElement('nav');
    nav.className = 'deck-shell';
    nav.setAttribute('aria-label', 'Presentation controls');
    nav.innerHTML =
      '<button type="button" class="deck-shell__arrow" data-deck-prev aria-label="Previous step">&#8249;</button>' +
      '<span class="deck-shell__counter" data-deck-counter>01 / 01</span>' +
      '<button type="button" class="deck-shell__arrow" data-deck-next aria-label="Next step">&#8250;</button>' +
      '<span class="deck-shell__phase" data-deck-phase></span>' +
      '<button type="button" data-deck-static aria-pressed="false" title="S">Static</button>' +
      '<button type="button" data-deck-overview title="O">Overview</button>' +
      '<button type="button" class="deck-shell__fullscreen" data-deck-full title="F">Fullscreen</button>';

    const progressTrack = document.createElement('div');
    progressTrack.className = 'deck-shell-progress';
    progressTrack.setAttribute('aria-hidden', 'true');
    progressTrack.innerHTML = '<div class="deck-shell-progress__value" data-deck-progress></div>';

    const status = document.createElement('div');
    status.className = 'deck-shell-sr';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    status.setAttribute('aria-atomic', 'true');

    const overview = document.createElement('dialog');
    overview.className = 'deck-shell-overview';
    overview.setAttribute('aria-labelledby', 'deck-shell-overview-title');
    overview.innerHTML =
      '<h2 id="deck-shell-overview-title">Slide overview</h2>' +
      '<div class="deck-shell-overview__list" data-deck-overview-list></div>' +
      '<button type="button" class="deck-shell-overview__close" data-deck-overview-close>Close</button>';

    document.body.append(nav, progressTrack, status, overview);

    const prev = nav.querySelector('[data-deck-prev]');
    const next = nav.querySelector('[data-deck-next]');
    const counter = nav.querySelector('[data-deck-counter]');
    const phaseCounter = nav.querySelector('[data-deck-phase]');
    const staticBtn = nav.querySelector('[data-deck-static]');
    const progress = progressTrack.querySelector('[data-deck-progress]');
    const overviewList = overview.querySelector('[data-deck-overview-list]');

    function live() { return !REDUCE.matches && !staticMode; }
    function maxAt(i) { return declaredPhases(deck.slides[i]); }

    function goSlide(n) {
      const clamped = Math.max(0, Math.min(deck.slides.length - 1, n));
      deck.goto(clamped, live() ? deck.start(clamped) : 0);
    }
    function forward() {
      if (live()) deck.next();
      else if (deck.slide < deck.slides.length - 1) goSlide(deck.slide + 1);
    }
    function back() {
      if (live()) deck.prev();
      else if (deck.slide > 0) goSlide(deck.slide - 1);
    }
    function setStatic(value) {
      staticMode = Boolean(value);
      document.documentElement.classList.toggle('deck-live', live());
      if (live()) deck.phase = deck.start(deck.slide);
      deck.render();
      update();
    }
    function openOverview() {
      previousFocus = document.activeElement;
      overview.showModal();
      renderOverview();
      overview.querySelector('[aria-current="true"]')?.focus();
    }
    function closeOverview() {
      if (!overview.open) return;
      overview.close();
      if (previousFocus && previousFocus.isConnected) previousFocus.focus();
    }
    async function toggleFull() {
      try {
        if (document.fullscreenElement) await document.exitFullscreen();
        else await document.documentElement.requestFullscreen();
      } catch (_) {
        status.textContent = 'Fullscreen is unavailable in this browser.';
      }
    }

    function renderOverview() {
      overviewList.innerHTML = deck.slides.map((s, i) => {
        const current = i === deck.slide ? ' aria-current="true"' : '';
        return '<button type="button" data-goto="' + i + '"' + current + '>' +
          '<span>' + String(i + 1).padStart(2, '0') + '</span>' +
          titleOf(s, i).replace(/[<>&]/g, ch => ({'<':'&lt;','>':'&gt;','&':'&amp;'}[ch])) +
          '</button>';
      }).join('');
    }

    function update() {
      const n = deck.slides.length;
      const max = maxAt(deck.slide);
      counter.textContent = String(deck.slide + 1).padStart(2, '0') + ' / ' + String(n).padStart(2, '0');
      phaseCounter.textContent = live() ? deck.phase + ' / ' + max : 'STATIC';
      staticBtn.setAttribute('aria-pressed', String(!live()));
      staticBtn.disabled = REDUCE.matches;
      prev.disabled = deck.slide === 0 && (!live() || deck.phase <= deck.start(0));
      next.disabled = deck.slide === n - 1 && (!live() || deck.phase >= max);

      let completed, total;
      if (live()) {
        total = deck.slides.reduce((sum, s) => sum + declaredPhases(s) + 1, 0) - 1;
        completed = deck.slides.slice(0, deck.slide)
          .reduce((sum, s) => sum + declaredPhases(s) + 1, 0) + deck.phase;
      } else {
        total = Math.max(1, n - 1);
        completed = deck.slide;
      }
      progress.style.transform = 'scaleX(' + Math.min(1, Math.max(0, completed / Math.max(1, total))) + ')';

      const title = titleOf(deck.slides[deck.slide], deck.slide);
      status.textContent = (deck.slide + 1) + ' / ' + n + '. ' + title +
        (live() ? '. Phase ' + deck.phase + ' / ' + max : '. Static final frame.');
      const hash = '#' + (deck.slide + 1) + (live() && deck.phase ? '.' + deck.phase : '');
      lastHash = hash;
      try { history.replaceState(null, '', hash); } catch (_) {}
      renderOverview();
    }

    prev.addEventListener('click', back);
    next.addEventListener('click', forward);
    staticBtn.addEventListener('click', () => setStatic(!staticMode));
    nav.querySelector('[data-deck-overview]').addEventListener('click', openOverview);
    nav.querySelector('[data-deck-full]').addEventListener('click', toggleFull);
    overview.querySelector('[data-deck-overview-close]').addEventListener('click', closeOverview);
    overview.addEventListener('cancel', e => { e.preventDefault(); closeOverview(); });
    overview.addEventListener('click', e => {
      const button = e.target.closest('[data-goto]');
      if (!button) return;
      goSlide(Number(button.dataset.goto));
      closeOverview();
    });

    deck.stage.addEventListener('click', e => {
      if (e.target.closest('a,button,input,textarea,select,[contenteditable="true"]') ||
          global.getSelection()?.toString()) return;
      const r = deck.stage.getBoundingClientRect();
      if (e.clientX < r.left + r.width / 2) back();
      else forward();
    });

    addEventListener('deck:state', update);
    REDUCE.addEventListener('change', () => {
      document.documentElement.classList.toggle('deck-live', live());
      deck.phase = live() ? deck.start(deck.slide) : 0;
      deck.render();
      update();
    });

    // Capture-phase interception is deliberate: in static mode Space/Arrows
    // advance slides, not invisible phases handled by the core runtime.
    addEventListener('keydown', e => {
      if (overview.open) return;
      if (e.altKey || e.ctrlKey || e.metaKey ||
          e.target.closest?.('input,textarea,select,[contenteditable="true"]')) return;

      const k = e.key.toLowerCase();
      if (k === 'o') { e.preventDefault(); e.stopImmediatePropagation(); openOverview(); return; }
      if (k === 'f') { e.preventDefault(); e.stopImmediatePropagation(); toggleFull(); return; }
      if (k === 's' && !REDUCE.matches) {
        e.preventDefault(); e.stopImmediatePropagation(); setStatic(!staticMode); return;
      }
      if (e.key === 'Home') {
        e.preventDefault(); e.stopImmediatePropagation(); goSlide(0); return;
      }
      if (e.key === 'End') {
        e.preventDefault(); e.stopImmediatePropagation(); goSlide(deck.slides.length - 1); return;
      }
      if (!live() && ['ArrowRight','ArrowDown',' ','Enter','PageDown'].includes(e.key)) {
        e.preventDefault(); e.stopImmediatePropagation(); forward(); return;
      }
      if (!live() && ['ArrowLeft','ArrowUp','PageUp','Backspace'].includes(e.key)) {
        e.preventDefault(); e.stopImmediatePropagation(); back();
      }
    }, true);

    addEventListener('hashchange', () => {
      if (location.hash === lastHash) return;
      const m = location.hash.match(/^#(\d+)(?:\.(\d+))?$/);
      if (!m) return;
      const n = Math.min(deck.slides.length - 1, Math.max(0, Number(m[1]) - 1));
      const p = Math.max(0, Number(m[2] || 0));
      deck.goto(n, live() ? p : 0);
    });

    document.documentElement.classList.toggle('deck-live', live());
    update();

    global.__deckShell = {
      openOverview,
      closeOverview,
      setStatic,
      update,
      isStatic: () => !live()
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => boot(0));
  } else {
    boot(0);
  }
})(typeof window !== 'undefined' ? window : globalThis);
