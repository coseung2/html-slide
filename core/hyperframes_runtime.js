/* HyperFrames adapter: reuse the accepted HTML/CSS frame, replace wall-clock motion with seek-safe WAAPI. */
(() => {
  'use strict';
  const source = document.getElementById('hf-video-timing');
  if (!source || window.__htmlSlideHyperframes) return;
  const timing = JSON.parse(source.textContent);
  const fps = Number(timing.fps || 30);
  const root = document.documentElement;
  const ease = 'cubic-bezier(.16,1,.3,1)';
  const cut = 'cubic-bezier(.76,0,.24,1)';
  const linear = 'linear';
  const fmt = n => new Intl.NumberFormat('en-US', {maximumFractionDigits: 4}).format(n);
  const primarySelectors = {
    'statement':'.statement','quote':'blockquote','comparison-text':'.comparison-copy',
    'metric':'.metric-value','score':'.score-value','image':'img','logo':'img',
    'ranking':'.ranking','bullet-list':'.module-list','timeline':'.module-timeline',
    'process':'.process','bar-chart':'.bar-chart','line-chart':'.line-chart'
  };
  const patternSpecs = {
    'kinetic-type':{scope:'primary',props:['transform','opacity','filter'],duration:680},
    'flat-shape':{scope:'primary',props:['transform','opacity'],duration:700},
    'info-motion':{scope:'primary',props:['transform','opacity','filter'],duration:620},
    'ui-motion':{scope:'block',props:['clipPath','transform','filter'],duration:820,easing:cut},
    'card-stack-3d':{scope:'block',props:['transform','opacity','boxShadow'],duration:900},
    'particle-warp':{scope:'primary',props:['transform','filter'],duration:720},
    'liquid-morph':{scope:'primary',props:['transform'],duration:780},
    'isometric-build':{scope:'block',props:['transform'],duration:980},
    'paper-cut':{scope:'primary',props:['transform'],duration:700},
    'type-mask':{scope:'primary',props:['clipPath','transform'],duration:780,easing:cut},
    'environment-type':{scope:'block',props:['transform'],duration:1050},
    'variable-font':{scope:'primary',props:['fontVariationSettings','fontWeight','letterSpacing','transform'],duration:850},
    'swiss-grid':{scope:'primary',props:['transform'],duration:720},
    'extruded-type':{scope:'primary',props:['transform','textShadow'],duration:760},
    'street-collage':{scope:'block',props:['transform'],duration:720},
    'path-drawing':{scope:'primary',props:[],duration:1},
    'line-split':{scope:'primary',props:['color'],duration:1,easing:linear},
    'highlight-sweep':{scope:'primary',props:['opacity'],duration:180},
    'strike-through':{scope:'primary',props:['opacity'],duration:180,delay:320},
    'number-counter':{scope:'number',props:['transform'],duration:620},
    'text-path':{scope:'primary',props:['transform'],duration:760},
    'oversized-crop-type':{scope:'primary',props:['transform'],duration:880}
  };

  function primary(block) {
    const selector = primarySelectors[block.dataset.module];
    return (selector && block.querySelector(selector)) || block;
  }
  function ms(frame) { return frame * 1000 / fps; }
  function css(el, props, pseudo = null) {
    const style = getComputedStyle(el, pseudo);
    const result = {};
    for (const prop of props) result[prop] = style[prop];
    return result;
  }
  function animation(el, keyframes, options, pseudo = null) {
    const settings = {fill:'both', ...options};
    if (pseudo) settings.pseudoElement = pseudo;
    try {
      const item = el.animate(keyframes, settings);
      item.pause();
      return item;
    } catch (error) {
      (window.__htmlSlideHyperframesWarnings ||= []).push(String(error));
      return null;
    }
  }
  function pair(el, from, to, at, duration, easing = ease, pseudo = null) {
    if (!el || !duration) return null;
    if (JSON.stringify(from) === JSON.stringify(to)) return null;
    return animation(el, [from, to], {delay:at,duration:Math.max(1,duration),easing}, pseudo);
  }
  function withDone(block, fn) {
    const oldState = block.dataset.motionState;
    const oldRun = block.dataset.motionRun;
    const items = [...block.querySelectorAll('[data-sequence-item]')];
    const itemStates = items.map(item => item.dataset.sequenceState);
    block.dataset.motionRun = '0';
    block.dataset.motionState = 'done';
    items.forEach(item => item.dataset.sequenceState = 'done');
    void block.offsetWidth;
    const value = fn();
    block.dataset.motionState = oldState || 'pending';
    block.dataset.motionRun = oldRun || '0';
    items.forEach((item, i) => item.dataset.sequenceState = itemStates[i] || 'pending');
    void block.offsetWidth;
    return value;
  }
  function transition(block, el, props, at, duration, easing = ease, delay = 0, pseudo = null) {
    if (!el || !props.length) return;
    const from = css(el, props, pseudo);
    const to = withDone(block, () => css(el, props, pseudo));
    pair(el, from, to, at + delay, duration, easing, pseudo);
  }
  function explicit(el, frames, at, duration, easing = ease, pseudo = null) {
    animation(el, frames, {delay:at,duration:Math.max(1,duration),easing}, pseudo);
  }
  function setFinal(block) {
    block.dataset.motionState = 'done';
    block.dataset.motionRun = '0';
    block.querySelectorAll('[data-sequence-item]').forEach(item => item.dataset.sequenceState = 'done');
  }
  function sceneCueMs(scene, cue) { return ms(scene.startFrame + cue.atFrame); }
  function groupCues(scene) {
    const map = new Map();
    for (const cue of scene.cues || []) {
      const key = cue.target + '\u0000' + cue.module;
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(cue);
    }
    for (const cues of map.values()) cues.sort((a,b) => a.step - b.step);
    return map;
  }
  function patternAt(scene, cues) {
    const cue = cues[cues.length - 1];
    return sceneCueMs(scene, cue);
  }

  function semantic(block, module, scene, cues) {
    if (module === 'sequence-step') {
      const items = [...block.querySelectorAll('[data-sequence-item]')];
      cues.forEach((cue, i) => {
        const item = items[i];
        if (!item) return;
        const from = css(item, ['opacity']);
        const old = item.dataset.sequenceState;
        item.dataset.sequenceState = 'done'; void item.offsetWidth;
        const to = css(item, ['opacity']);
        item.dataset.sequenceState = old || 'pending'; void item.offsetWidth;
        pair(item, from, to, sceneCueMs(scene, cue), 220, 'ease');
      });
      return;
    }
    const at = sceneCueMs(scene, cues[0]);
    if (module === 'chart-grow') {
      block.querySelectorAll('.bar-fill').forEach(el => transition(block, el, ['transform'], at, 420, 'ease'));
      block.querySelectorAll('.chart-line').forEach(el => transition(block, el, ['strokeDashoffset'], at, 500, 'ease'));
    } else if (module === 'score-reveal') {
      const el = block.querySelector('.score-value');
      transition(block, el, ['opacity','transform'], at, 280, 'ease');
    } else if (module === 'focus') {
      const ring = block.querySelector('.focus-ring');
      transition(block, ring, ['opacity'], at, 1, linear);
    }
  }

  function patternBase(block, pattern, at) {
    const spec = patternSpecs[pattern];
    if (!spec) return;
    if (spec.scope === 'number') {
      block.querySelectorAll('[data-number]').forEach(el => {
        transition(block, el, spec.props, at, spec.duration, spec.easing || ease, spec.delay || 0);
      });
      return;
    }
    const el = spec.scope === 'block' ? block : primary(block);
    transition(block, el, spec.props, at, spec.duration, spec.easing || ease, spec.delay || 0);
  }

  function opacityTransition(block, el, at, duration, delay = 0) {
    transition(block, el, ['opacity'], at, duration, ease, delay);
  }
  function filterTransition(block, el, at, duration, delay = 0) {
    transition(block, el, ['filter'], at, duration, ease, delay);
  }

  function transientPattern(block, pattern, at, sceneStart) {
    const p = primary(block);
    if (pattern === 'flat-shape') {
      const a0 = css(block,['opacity','transform'],'::before');
      const a1 = {...a0, opacity:'0', transform:'matrix(0.25, 0, 0, 0.25, 210, -100)'};
      explicit(block,[a0,a1],at,720,ease,'::before');
      const b0 = css(block,['opacity','transform'],'::after');
      const b1 = {...b0, opacity:'0', transform:'matrix(0.286788, 0.200752, -0.200752, 0.286788, -240, 120)'};
      explicit(block,[b0,b1],at,760,ease,'::after');
    } else if (pattern === 'particle-warp') {
      opacityTransition(block,p,at,260,280);
      filterTransition(block,p,at,620);
      block.querySelectorAll('.motion-particle').forEach((dot,i) => {
        const start = css(dot,['opacity','transform']);
        const mid = {opacity:'.8',transform:'matrix(1, 0, 0, 1, 0, 0)'};
        const end = {opacity:'0',transform:'matrix(0.15, 0, 0, 0.15, 0, 0)'};
        explicit(dot,[{...start,offset:0},{...mid,offset:.72},{...end,offset:1}],at+i*14,760,ease);
      });
    } else if (pattern === 'glitch') {
      const end = withDone(block,()=>css(p,['opacity','transform','textShadow','clipPath','filter']));
      explicit(p,[
        {opacity:'.35',transform:'translate(-10px,3px)',textShadow:'9px 0 #f05,-9px 0 #0df',offset:0},
        {transform:'translate(8px,-3px)',textShadow:'-12px 0 #f05,12px 0 #0df',offset:.18},
        {transform:'translate(-5px,2px)',clipPath:'inset(12% 0 52% 0)',offset:.34},
        {transform:'translate(4px,0)',clipPath:'inset(58% 0 8% 0)',textShadow:'7px 0 #f05,-7px 0 #0df',offset:.52},
        {clipPath:'inset(0)',transform:'translate(-2px,0)',offset:.72},
        {...end,offset:1}
      ],at,620,'steps(2,end)');
    } else if (pattern === 'liquid-morph') {
      opacityTransition(block,p,at,220,300);
      const start=css(block,['opacity','transform','borderRadius'],'::before');
      explicit(block,[
        {...start,offset:0},
        {opacity:'.55',transform:'scale(1.08) rotate(3deg)',borderRadius:'60% 40% 34% 66% / 38% 61% 39% 62%',offset:.55},
        {opacity:'0',transform:'scale(1.2)',borderRadius:'50%',offset:1}
      ],at,900,ease,'::before');
    } else if (pattern === 'isometric-build') {
      opacityTransition(block,block,at,220);
    } else if (pattern === 'paper-cut') {
      ['::before','::after'].forEach(pseudo => {
        const from=css(block,['opacity','transform'],pseudo);
        const to=withDone(block,()=>css(block,['opacity','transform'],pseudo));
        pair(block,{transform:from.transform},{transform:to.transform},at,760,ease,pseudo);
        pair(block,{opacity:from.opacity},{opacity:to.opacity},at+460,300,ease,pseudo);
      });
      opacityTransition(block,p,at,180,260);
    } else if (pattern === 'environment-type') {
      opacityTransition(block,block,at,220);
      filterTransition(block,block,at,620);
    } else if (pattern === 'occlusion') {
      opacityTransition(block,p,at,160,380);
      explicit(block,[
        {opacity:'0',transform:'translateX(-115%) skewX(-7deg)',offset:0},
        {opacity:'1',transform:'translateX(-115%) skewX(-7deg)',offset:.001},
        {opacity:'1',transform:'translateX(-6%) skewX(-7deg)',offset:.45},
        {opacity:'1',transform:'translateX(115%) skewX(-7deg)',offset:1}
      ],at,820,cut,'::after');
    } else if (pattern === 'scramble-decode') {
      scrambleSurface(block,p,at,680);
      explicit(p,[
        {transform:'translateX(-7px) skewX(-5deg)',filter:'blur(1.2px)',offset:0},
        {transform:'translateX(4px) skewX(3deg)',filter:'blur(.8px)',offset:.45},
        {transform:'none',filter:'none',letterSpacing:'inherit',opacity:'1',offset:1}
      ],at,720,ease);
    } else if (pattern === 'variable-font') {
      opacityTransition(block,p,at,180);
    } else if (pattern === 'swiss-grid') {
      opacityTransition(block,p,at,180,250);
      explicit(block,[
        {opacity:'0',transform:'scaleY(0)',transformOrigin:'top',offset:0},
        {opacity:'1',transform:'scaleY(0)',transformOrigin:'top',offset:.001},
        {opacity:'1',transform:'scaleY(1)',offset:.68},
        {opacity:'0',transform:'scaleY(1)',offset:1}
      ],at,680,cut,'::before');
      explicit(block,[
        {opacity:'0',transform:'scaleX(0)',transformOrigin:'left',offset:0},
        {opacity:'1',transform:'scaleX(0)',transformOrigin:'left',offset:.001},
        {opacity:'1',transform:'scaleX(1)',offset:.68},
        {opacity:'0',transform:'scaleX(1)',offset:1}
      ],at+110,680,cut,'::after');
    } else if (pattern === 'extruded-type') {
      opacityTransition(block,p,at,180);
    } else if (pattern === 'street-collage') {
      const a0=css(block,['opacity','transform'],'::before');
      const b0=css(block,['opacity','transform'],'::after');
      explicit(block,[a0,{opacity:'0',transform:'translateX(140%) rotate(-2deg)'}],at,700,ease,'::before');
      explicit(block,[b0,{opacity:'0',transform:'translateX(-150%) rotate(1deg)'}],at,760,ease,'::after');
    } else if (pattern === 'path-drawing') {
      opacityTransition(block,p,at,180,280);
      explicit(block,[
        {opacity:'0',clipPath:'polygon(0 0,0 0,0 0,0 0)',offset:0},
        {opacity:'1',clipPath:'polygon(0 0,0 0,0 0,0 0)',offset:.001},
        {opacity:'1',clipPath:'polygon(0 0,100% 0,100% 0,0 0)',offset:.35},
        {opacity:'1',clipPath:'polygon(0 0,100% 0,100% 100%,0 100%)',offset:.7},
        {opacity:'0',clipPath:'polygon(0 0,100% 0,100% 100%,0 100%)',offset:1}
      ],at,850,cut,'::after');
    } else if (pattern === 'word-by-word') {
      splitSurface(block,p,'word',at);
    } else if (pattern === 'line-split') {
      const before=css(p,['opacity','transform'],'::before');
      const after=css(p,['opacity','transform'],'::after');
      explicit(p,[{...before,offset:0},{opacity:'1',transform:'none',offset:.65},{opacity:'0',transform:'none',offset:1}],at,620,ease,'::before');
      explicit(p,[{...after,offset:0},{opacity:'1',transform:'none',offset:.65},{opacity:'0',transform:'none',offset:1}],at,620,ease,'::after');
    } else if (pattern === 'highlight-sweep') {
      explicit(p,[
        {opacity:'0',transform:'scaleX(0)',offset:0},
        {opacity:'.9',transform:'scaleX(0)',offset:.001},
        {opacity:'.9',transform:'scaleX(1)',offset:.62},
        {opacity:'0',transform:'scaleX(1)',offset:1}
      ],at,820,cut,'::after');
    } else if (pattern === 'strike-through') {
      explicit(p,[
        {opacity:'0',transform:'scaleX(0)',offset:0},
        {opacity:'1',transform:'scaleX(0)',offset:.001},
        {opacity:'1',transform:'scaleX(1)',offset:.62},
        {opacity:'0',transform:'scaleX(1)',offset:1}
      ],at,720,cut,'::after');
    } else if (pattern === 'typewriter-code') {
      splitSurface(block,p,'char',at);
      const pre=Math.max(1,at-sceneStart);
      const blink=[];
      const steps=Math.max(2,Math.ceil(pre/350));
      for(let i=0;i<=steps;i++) blink.push({opacity:i%2===0?'1':'0',offset:i/steps});
      explicit(p,blink,sceneStart,pre,'steps(1,end)','::after');
      explicit(p,[
        {opacity:'1',offset:0},{opacity:'0',offset:.1},{opacity:'1',offset:.2},{opacity:'0',offset:.3},
        {opacity:'1',offset:.4},{opacity:'0',offset:.5},{opacity:'1',offset:.6},{opacity:'0',offset:.7},{opacity:'0',offset:1}
      ],at,1250,'steps(1,end)','::after');
    } else if (pattern === 'number-counter') {
      block.querySelectorAll('[data-number]').forEach(el => {
        opacityTransition(block,el,at,150);
        filterTransition(block,el,at,380);
        numberSurface(el,at,500);
      });
    } else if (pattern === 'text-path') {
      opacityTransition(block,p,at,180,300);
      const layer=block.querySelector('.motion-text-path');
      const path=block.querySelector('.motion-text-path path');
      if(layer) explicit(layer,[
        {opacity:'.75',transform:'translateY(18px)',offset:0},
        {opacity:'.55',transform:'none',offset:.72},
        {opacity:'0',transform:'none',offset:1}
      ],at,900,ease);
      if(path) explicit(path,[{strokeDashoffset:'1400'},{strokeDashoffset:'0'}],at,720,cut);
    } else if (pattern === 'oversized-crop-type') {
      opacityTransition(block,p,at,180,160);
      filterTransition(block,p,at,450);
    }
  }

  function splitSurface(block,p,kind,at) {
    const selector=kind==='word'?'.motion-word':'.motion-char';
    const sourceText=p.dataset.patternText || p.textContent;
    const originals=[...p.querySelectorAll(selector)];
    if(!originals.length)return;
    const overlay=document.createElement('span');
    overlay.className='hf-motion-overlay';
    originals.forEach(node=>overlay.append(node.cloneNode(true)));
    p.replaceChildren();
    const final=document.createElement('span');
    final.className='hf-final-text';
    final.textContent=sourceText;
    p.append(final,overlay);
    const duration=kind==='word'?560:52;
    const stagger=kind==='word'?65:22;
    [...overlay.querySelectorAll(selector)].forEach((el,i)=>{
      const from=css(el,kind==='word'?['opacity','transform','filter']:['opacity']);
      const props=kind==='word'?['opacity','transform','filter']:['opacity'];
      const to=withDone(block,()=>css(el,props));
      pair(el,from,to,at+i*stagger,duration,ease);
    });
    const total=kind==='word'
      ? Math.min(1600,640+Math.max(0,originals.length-1)*65)
      : Math.min(1400,180+Math.max(0,originals.length-1)*22);
    explicit(final,[{opacity:'0',offset:0},{opacity:'0',offset:.82},{opacity:'1',offset:1}],at,total,linear);
    explicit(overlay,[{opacity:'1',offset:0},{opacity:'1',offset:.9},{opacity:'0',offset:1}],at,total,linear);
  }

  const scrambleGlyphs=Array.from('░▒▓#%&0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ가나다라마바사아자차카타파하');
  function scrambleSurface(block,p,at,duration) {
    const finalText=p.dataset.finalText || p.textContent;
    const chars=Array.from(finalText);
    const samples=Math.max(8,Math.round(duration*fps/1000)+1);
    const values=[];
    for(let frame=0;frame<samples;frame++){
      const t=frame/(samples-1);
      const fixed=Math.floor(chars.length*Math.pow(t,.72));
      values.push(chars.map((ch,i)=>/\s/.test(ch)||i<fixed?ch:scrambleGlyphs[(i*13+frame)%scrambleGlyphs.length]).join(''));
    }
    valueSurface(p,values,at,duration);
  }

  function numberSurface(el,at,duration) {
    if(el.dataset.hfNumberReady)return;
    el.dataset.hfNumberReady='1';
    const target=Number(el.dataset.number);
    if(!Number.isFinite(target))return;
    const samples=Math.max(4,Math.round(duration*fps/1000)+1);
    const values=[];
    for(let frame=0;frame<samples;frame++){
      const t=frame/(samples-1);
      values.push(fmt(target*(1-Math.pow(1-t,3))));
    }
    values[values.length-1]=fmt(target);
    valueSurface(el,values,at,duration);
  }

  function valueSurface(host,values,at,duration) {
    if(host.dataset.hfValueReady)return;
    host.dataset.hfValueReady='1';
    const finalText=values[values.length-1];
    host.classList.add('hf-value-host');
    host.replaceChildren();
    const spacer=document.createElement('span');
    spacer.className='hf-value-spacer';
    spacer.textContent=finalText;
    host.append(spacer);
    const count=values.length;
    values.forEach((value,i)=>{
      const frame=document.createElement('span');
      frame.className='hf-value-frame';
      frame.textContent=value;
      host.append(frame);
      const a=i/count,b=(i+1)/count,eps=Math.min(.001,1/(count*20));
      let keys;
      if(i===0) keys=[
        {opacity:'1',offset:0},{opacity:'1',offset:Math.max(0,b-eps)},{opacity:'0',offset:b},{opacity:'0',offset:1}
      ];
      else if(i===count-1) keys=[
        {opacity:'0',offset:0},{opacity:'0',offset:Math.max(0,a-eps)},{opacity:'1',offset:a},{opacity:'1',offset:1}
      ];
      else keys=[
        {opacity:'0',offset:0},{opacity:'0',offset:Math.max(0,a-eps)},{opacity:'1',offset:a},
        {opacity:'1',offset:Math.max(a,b-eps)},{opacity:'0',offset:b},{opacity:'0',offset:1}
      ];
      explicit(frame,keys,at,duration,'steps(1,end)');
    });
  }

  function ensureSemanticNumber(block,module,at) {
    if(module==='number-count'){
      block.querySelectorAll('[data-number]').forEach(el=>numberSurface(el,at,500));
    }
  }

  root.classList.add('deck-capture');
  const animationsBefore = document.getAnimations().length;
  for (const scene of timing.scenes) {
    const slide=document.querySelector('[data-slide="'+CSS.escape(scene.id)+'"]');
    if(!slide)continue;
    const sceneStart=ms(scene.startFrame);
    if(scene.transitionFrames){
      explicit(slide,[{opacity:'0'},{opacity:'1'}],sceneStart,ms(scene.transitionFrames),ease);
    }
    const groups=groupCues(scene);
    for(const cues of groups.values()){
      const cue=cues[0];
      const block=document.getElementById('s-'+scene.id+'--'+cue.target);
      if(!block)continue;
      semantic(block,cue.module,scene,cues);
      const at=patternAt(scene,cues);
      const pattern=cues.find(item=>item.pattern)?.pattern;
      if(pattern){
        patternBase(block,pattern,at);
        transientPattern(block,pattern,at,sceneStart);
      }
      ensureSemanticNumber(block,cue.module,sceneCueMs(scene,cues[0]));
      setFinal(block);
      block.style.setProperty('--hf-start',(at/1000)+'s');
    }
  }

  root.classList.remove('deck-ready');
  document.querySelectorAll('[data-slide]').forEach(slide=>{
    slide.classList.remove('is-active','deck-entering');
    slide.inert=false;
    slide.removeAttribute('aria-hidden');
  });
  const stage=document.querySelector('[data-stage]');
  if(stage)stage.style.transform='none';
  window.__htmlSlideHyperframes={
    version:1,
    timing,
    waapiAnimations:document.getAnimations().length-animationsBefore,
    warnings:window.__htmlSlideHyperframesWarnings||[]
  };
})();
