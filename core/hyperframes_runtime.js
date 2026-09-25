/* Deterministic HyperFrames motion runtime. HyperFrames owns the playhead; GSAP only describes state. */
(() => {
  'use strict';
  window.__mountHtmlSlideHyperframes = (rootId, planInput) => {
  const gsap = window.gsap;
  const stage = document.getElementById(rootId);
  if (!gsap || !stage) return;

  const plan = typeof planInput === 'string'
    ? JSON.parse(document.getElementById(planInput)?.textContent || '{}')
    : planInput;
  if (!plan || !Array.isArray(plan.scenes)) return;
  const tl = gsap.timeline({paused:true});
  const ease = 'power3.out';
  const cut = 'power2.inOut';
  const clamp = value => Math.max(0, Math.min(1, value));
  const format = value => new Intl.NumberFormat('en-US',{maximumFractionDigits:4}).format(value);
  const primarySelectors = {
    'statement':'.statement','quote':'blockquote','comparison-text':'.comparison-copy',
    'metric':'.metric-value','score':'.score-value','image':'img','logo':'img',
    'ranking':'.ranking','bullet-list':'.module-list','timeline':'.module-timeline',
    'process':'.process','bar-chart':'.bar-chart','line-chart':'.line-chart'
  };

  const primary = block => {
    const selector = primarySelectors[block.dataset.module];
    return (selector && block.querySelector(selector)) || block;
  };
  const segment = text => {
    try {
      return [...new Intl.Segmenter(document.documentElement.lang || 'en',{granularity:'grapheme'}).segment(text)].map(x=>x.segment);
    } catch (_) {
      return Array.from(text);
    }
  };
  const rememberText = el => {
    if (el.dataset.hfSourceText == null) el.dataset.hfSourceText = el.textContent;
    return el.dataset.hfSourceText;
  };
  const wrapWords = el => {
    if (el.dataset.hfPrepared === 'words') return [...el.querySelectorAll('.hf-word')];
    const parts = rememberText(el).split(/(\s+)/);
    el.replaceChildren();
    let index = 0;
    parts.forEach(part => {
      if (!part) return;
      if (/^\s+$/.test(part)) {
        el.append(document.createTextNode(part));
        return;
      }
      const span = document.createElement('span');
      span.className = 'hf-word';
      span.textContent = part;
      span.style.display = 'inline-block';
      span.dataset.hfIndex = String(index++);
      el.append(span);
    });
    el.dataset.hfPrepared = 'words';
    return [...el.querySelectorAll('.hf-word')];
  };
  const wrapChars = el => {
    if (el.dataset.hfPrepared === 'chars') return [...el.querySelectorAll('.hf-char')];
    const chars = segment(rememberText(el));
    el.replaceChildren();
    chars.forEach((char,index) => {
      const span = document.createElement('span');
      span.className = 'hf-char';
      span.textContent = char;
      span.dataset.hfIndex = String(index);
      el.append(span);
    });
    el.dataset.hfPrepared = 'chars';
    return [...el.querySelectorAll('.hf-char')];
  };
  const overlay = block => {
    let layer = block.querySelector(':scope > .hf-pattern-overlay');
    if (!layer) {
      layer = document.createElement('span');
      layer.className = 'hf-pattern-overlay';
      layer.setAttribute('aria-hidden','true');
      Object.assign(layer.style,{position:'absolute',inset:'0',zIndex:'6',pointerEvents:'none',overflow:'hidden'});
      block.append(layer);
    }
    return layer;
  };
  const shape = (layer, className) => {
    const node = document.createElement('span');
    node.className = className;
    node.style.position = 'absolute';
    layer.append(node);
    return node;
  };
  const pulseFrames = (timeline,target,at,duration,vars) => {
    const half = Math.max(.08,duration*.48);
    timeline.to(target,{...vars,duration:half,ease:cut},at);
    const settled = Object.fromEntries(
      Object.keys(vars).map(key=>[key,key==='opacity'?0:key==='scale'?1:0])
    );
    timeline.to(target,{duration:Math.max(.08,duration-half),ease:cut,...settled},at+half);
  };
  const setPending = (timeline,target,at,vars) => timeline.set(target,vars,at);
  const tweenFinal = (timeline,target,at,duration,vars={}) =>
    timeline.to(target,{duration,ease,...vars},at);

  function semantic(scene,cue,block,at,duration) {
    const module = cue.module;
    if (module === 'number-count' || module === 'score-reveal') {
      const nodes = [...block.querySelectorAll('[data-number]')];
      nodes.forEach((node,index) => {
        const target = Number(node.dataset.number || 0);
        const state = {value:0};
        tl.set(node,{opacity: module === 'score-reveal' ? .08 : 1,y: module === 'score-reveal' ? 12 : 0},scene.start);
        tl.to(state,{
          value:target,duration,ease,
          onUpdate:()=>{node.textContent=format(state.value);}
        },at);
        if (module === 'score-reveal') tl.to(node,{opacity:1,y:0,duration,ease},at);
      });
      return;
    }
    if (module === 'sequence-step') {
      const items = [...block.querySelectorAll('[data-sequence-item]')];
      const item = items[Math.max(0, Number(cue.itemIndex || 0))];
      if (item) {
        tl.set(item,{opacity:.18,y:10},scene.start);
        tl.to(item,{opacity:1,y:0,duration:Math.min(duration,.42),ease},at);
      }
      return;
    }
    if (module === 'chart-grow') {
      const bars = [...block.querySelectorAll('.bar-fill')];
      bars.forEach(bar => {
        tl.set(bar,{scaleX:.001,transformOrigin:'left center'},scene.start);
        tl.to(bar,{scaleX:1,duration:Math.min(duration,.55),ease},at);
      });
      const line = block.querySelector('.chart-line');
      if (line) {
        tl.set(line,{strokeDasharray:2200,strokeDashoffset:2200},scene.start);
        tl.to(line,{strokeDashoffset:0,duration:Math.min(duration,.65),ease},at);
      }
      return;
    }
    if (module === 'focus' && !cue.pattern) {
      const ring = block.querySelector('.focus-ring');
      if (ring) {
        tl.set(ring,{opacity:0},scene.start);
        tl.to(ring,{opacity:1,duration:Math.min(.18,duration*.3),ease:'power1.out'},at);
        tl.to(ring,{opacity:0,duration:Math.min(.3,duration*.4),ease:'power1.in'},at+duration*.58);
      }
      tl.fromTo(block,{scale:.985},{scale:1,duration,ease,immediateRender:false},at);
    }
  }

  const scrambleGlyphs = segment('░▒▓#%&0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ가나다라마바사아자차카타파하');
  function pattern(scene,cue,block,at,duration) {
    const id = cue.pattern;
    if (!id) return;
    const p = primary(block);
    const layer = overlay(block);
    const accent = 'var(--accent)';
    const ink = 'var(--ink)';
    const surface = 'var(--surface)';

    if (id === 'kinetic-type') {
      setPending(tl,p,scene.start,{opacity:.08,y:'0.45em',scale:1.28,skewX:-4,filter:'blur(2px)'});
      tweenFinal(tl,p,at,duration,{opacity:1,y:0,scale:1,skewX:0,filter:'blur(0px)'});
    } else if (id === 'info-motion') {
      setPending(tl,p,scene.start,{opacity:.2,y:22,scale:.985,filter:'saturate(.55)'});
      tweenFinal(tl,p,at,duration,{opacity:1,y:0,scale:1,filter:'saturate(1)'});
    } else if (id === 'ui-motion') {
      setPending(tl,block,scene.start,{opacity:.3,x:54,scale:.96,clipPath:'inset(6% 12%)',filter:'brightness(.72)'});
      tweenFinal(tl,block,at,duration,{opacity:1,x:0,scale:1,clipPath:'inset(0% 0%)',filter:'brightness(1)'});
      const dot = shape(layer,'hf-ui-dot');
      Object.assign(dot.style,{right:'24px',top:'24px',width:'14px',height:'14px',borderRadius:'50%',background:accent,boxShadow:`-24px 0 0 ${accent}88,-48px 0 0 ${accent}44`});
      pulseFrames(tl,dot,at,duration,{opacity:.9,scale:1.15});
    } else if (id === 'card-stack-3d') {
      setPending(tl,block,scene.start,{opacity:.22,transformPerspective:1200,rotationY:-13,rotationX:6,x:28,y:24,scale:.9});
      tweenFinal(tl,block,at,duration,{opacity:1,rotationY:0,rotationX:0,x:0,y:0,scale:1});
      [3,2,1].forEach(depth=>{
        const card=shape(layer,'hf-stack-card');
        Object.assign(card.style,{inset:`${12+depth*12}px`,borderRadius:'24px',border:`2px solid ${accent}55`,background:surface});
        tl.set(card,{opacity:.12,x:-26*depth,y:20*depth},scene.start);
        tl.to(card,{opacity:0,x:0,y:0,duration,ease},at);
      });
    } else if (id === 'flat-shape') {
      setPending(tl,p,scene.start,{opacity:.18,scale:.94});
      tweenFinal(tl,p,at,duration,{opacity:1,scale:1});
      [0,1,2].forEach(index=>{
        const node=shape(layer,'hf-flat-shape');
        const size=90+index*34;
        Object.assign(node.style,{width:`${size}px`,height:`${size}px`,borderRadius:index===1?'18px':'50%',background:index===2?ink:accent,left:`${8+index*31}%`,top:`${12+(index%2)*54}%`});
        const fromX=index%2?100:-100;
        tl.set(node,{opacity:.26,x:fromX,y:45,rotation:0},scene.start);
        tl.to(node,{opacity:0,x:0,y:0,rotation:(index+1)*55,duration,ease},at);
      });
    } else if (id === 'particle-warp') {
      setPending(tl,p,scene.start,{opacity:.12,scale:.94,filter:'blur(4px)'});
      tweenFinal(tl,p,at,duration,{opacity:1,scale:1,filter:'blur(0px)'});
      for(let index=0;index<18;index++){
        const node=shape(layer,'hf-particle');
        const angle=(Math.PI*2*index)/18, radius=190+(index%4)*20;
        Object.assign(node.style,{left:'50%',top:'50%',width:`${9+(index%4)*3}px`,height:`${9+(index%4)*3}px`,borderRadius:'50%',background:index%3===0?ink:accent});
        tl.set(node,{opacity:.72,x:Math.cos(angle)*radius,y:Math.sin(angle)*radius,scale:.65},scene.start);
        tl.to(node,{opacity:0,x:0,y:0,scale:.15,duration:duration*.9,ease},at+index*.012);
      }
    } else if (id === 'glitch') {
      setPending(tl,p,scene.start,{opacity:.18,x:-8,filter:'contrast(1.3)'});
      tl.to(p,{opacity:1,x:9,y:-3,textShadow:`9px 0 #f05,-9px 0 #0df`,duration:duration*.2,ease:'steps(2)'},at);
      tl.to(p,{x:-6,y:2,textShadow:`-12px 0 #f05,12px 0 #0df`,duration:duration*.22,ease:'steps(2)'},at+duration*.2);
      tl.to(p,{x:4,y:0,textShadow:`7px 0 #f05,-7px 0 #0df`,duration:duration*.24,ease:'steps(2)'},at+duration*.42);
      tl.to(p,{x:0,y:0,textShadow:'none',filter:'none',duration:duration*.34,ease:'steps(2)'},at+duration*.66);
    } else if (id === 'liquid-morph') {
      setPending(tl,p,scene.start,{opacity:.15,scale:.92});
      tweenFinal(tl,p,at,duration,{opacity:1,scale:1});
      [0,1,2].forEach(index=>{
        const blob=shape(layer,'hf-liquid');
        Object.assign(blob.style,{width:`${240+index*90}px`,height:`${170+index*70}px`,left:`${8+index*23}%`,top:`${12+(index%2)*40}%`,borderRadius:'42% 58% 63% 37%',background:accent});
        tl.set(blob,{opacity:.18,scale:.55,rotation:-8+(index*4)},scene.start);
        tl.to(blob,{opacity:0,scale:1.2,rotation:8+(index*4),borderRadius:'60% 40% 34% 66%',duration,ease},at);
      });
    } else if (id === 'isometric-build') {
      setPending(tl,block,scene.start,{opacity:.18,transformPerspective:1300,rotationX:54,rotationZ:-29,y:52,scale:.78,transformOrigin:'50% 80%'});
      tweenFinal(tl,block,at,duration,{opacity:1,rotationX:0,rotationZ:0,y:0,scale:1});
    } else if (id === 'paper-cut') {
      setPending(tl,p,scene.start,{opacity:.2,y:20});
      tweenFinal(tl,p,at,duration,{opacity:1,y:0});
      [3,2,1].forEach(depth=>{
        const card=shape(layer,'hf-paper');
        Object.assign(card.style,{inset:`${12+depth*12}px`,borderRadius:'8px',border:'1px solid currentColor',background:depth===2?accent:surface});
        tl.set(card,{opacity:.18,x:(depth-2)*38,y:(2-depth)*24,rotation:(depth-2)*3},scene.start);
        tl.to(card,{opacity:0,x:0,y:0,rotation:0,duration,ease},at);
      });
    } else if (id === 'type-mask') {
      setPending(tl,p,scene.start,{clipPath:'inset(0 100% 0 0)',x:-24});
      tweenFinal(tl,p,at,duration,{clipPath:'inset(0 0% 0 0)',x:0});
    } else if (id === 'environment-type') {
      setPending(tl,block,scene.start,{opacity:.16,transformPerspective:1500,rotationY:18,x:-68,y:18,z:-120,scale:.92,filter:'blur(2px)',transformOrigin:'18% 50%'});
      tweenFinal(tl,block,at,duration,{opacity:1,rotationY:0,x:0,y:0,z:0,scale:1,filter:'blur(0px)'});
    } else if (id === 'occlusion') {
      setPending(tl,p,scene.start,{opacity:.16,scale:1.06});
      tweenFinal(tl,p,at,duration,{opacity:1,scale:1});
      const bar=shape(layer,'hf-occlusion');
      Object.assign(bar.style,{top:'-8%',bottom:'-8%',width:'38%',background:accent});
      tl.set(bar,{opacity:1,xPercent:-120,skewX:-12},scene.start);
      tl.to(bar,{xPercent:310,duration,ease:cut},at);
      tl.to(bar,{opacity:0,duration:.01},at+duration-.01);
    } else if (id === 'scramble-decode') {
      const source=rememberText(p);
      const state={progress:0};
      setPending(tl,p,scene.start,{opacity:.55,filter:'blur(.55px)',x:-4});
      tl.to(state,{progress:1,duration,ease,onUpdate:()=>{
        const chars=segment(source), keep=Math.floor(chars.length*clamp(state.progress));
        p.textContent=chars.map((char,index)=>/\s/.test(char)||index<keep?char:scrambleGlyphs[(index*13+3)%scrambleGlyphs.length]).join('');
      },onComplete:()=>{p.textContent=source;}},at);
      tl.to(p,{opacity:1,filter:'blur(0px)',x:0,duration,ease},at);
    } else if (id === 'variable-font') {
      setPending(tl,p,scene.start,{opacity:.2,scaleX:.9,fontWeight:320,fontVariationSettings:'"wght" 320, "wdth" 78'});
      tweenFinal(tl,p,at,duration,{opacity:1,scaleX:1,fontWeight:800,fontVariationSettings:'"wght" 800, "wdth" 100'});
    } else if (id === 'swiss-grid') {
      setPending(tl,p,scene.start,{opacity:.15,x:26,y:22});
      tweenFinal(tl,p,at,duration,{opacity:1,x:0,y:0});
      const grid=shape(layer,'hf-grid');
      Object.assign(grid.style,{inset:'0',backgroundImage:`linear-gradient(to right,${accent} 1px,transparent 1px),linear-gradient(to bottom,${accent} 1px,transparent 1px)`,backgroundSize:'12.5% 100%,100% 25%'});
      pulseFrames(tl,grid,at,duration,{opacity:.22});
    } else if (id === 'extruded-type') {
      setPending(tl,p,scene.start,{opacity:.28,x:-18,y:-18,textShadow:`5px 5px 0 ${accent},10px 10px 0 ${accent}88,15px 15px 0 ${accent}44`});
      tweenFinal(tl,p,at,duration,{opacity:1,x:0,y:0,textShadow:'0px 0px 0 transparent'});
    } else if (id === 'street-collage') {
      setPending(tl,block,scene.start,{rotation:-2.5,scale:.96});
      tweenFinal(tl,block,at,duration,{rotation:0,scale:1});
      [-1,0,1].forEach(index=>{
        const strip=shape(layer,'hf-strip');
        Object.assign(strip.style,{width:`${48+index*7}%`,height:'34px',left:`${18+index*15}%`,top:`${18+(index+1)*25}%`,background:index===0?accent:ink});
        tl.set(strip,{opacity:.24,x:index*90,rotation:index*5-2},scene.start);
        tl.to(strip,{opacity:0,x:-index*120,duration,ease},at);
      });
    } else if (id === 'path-drawing') {
      setPending(tl,p,scene.start,{opacity:.18});
      tweenFinal(tl,p,at,duration,{opacity:1});
      const ns='http://www.w3.org/2000/svg';
      const svg=document.createElementNS(ns,'svg');
      svg.setAttribute('viewBox','0 0 1000 600');
      Object.assign(svg.style,{position:'absolute',inset:'0',width:'100%',height:'100%'});
      const rect=document.createElementNS(ns,'rect');
      rect.setAttribute('x','12');rect.setAttribute('y','12');rect.setAttribute('width','976');rect.setAttribute('height','576');rect.setAttribute('rx','34');
      rect.setAttribute('fill','none');rect.setAttribute('stroke',accent);rect.setAttribute('stroke-width','8');rect.setAttribute('pathLength','1');
      svg.append(rect);layer.append(svg);
      tl.set(rect,{strokeDasharray:1,strokeDashoffset:1,opacity:.9},scene.start);
      tl.to(rect,{strokeDashoffset:0,duration:duration*.72,ease:cut},at);
      tl.to(rect,{opacity:0,duration:duration*.28,ease:'power1.in'},at+duration*.72);
    } else if (id === 'word-by-word') {
      const words=wrapWords(p);
      tl.set(words,{opacity:0,y:'0.7em',rotation:2,filter:'blur(2px)'},scene.start);
      tl.to(words,{opacity:1,y:0,rotation:0,filter:'blur(0px)',duration:Math.min(.56,duration),stagger:Math.min(.065,duration/Math.max(1,words.length+2)),ease},at);
    } else if (id === 'line-split') {
      const layerA=shape(layer,'hf-line-top'), layerB=shape(layer,'hf-line-bottom');
      [layerA,layerB].forEach(node=>{node.innerHTML=p.innerHTML;Object.assign(node.style,{inset:'0',color:'inherit'});});
      layerA.style.clipPath='inset(0 0 50% 0)';layerB.style.clipPath='inset(50% 0 0 0)';
      tl.set(p,{opacity:0},scene.start);
      tl.set(layerA,{opacity:1,x:'-.32em'},scene.start);tl.set(layerB,{opacity:1,x:'.32em'},scene.start);
      tl.to([layerA,layerB],{x:0,duration:duration*.65,ease},at);
      tl.to([layerA,layerB],{opacity:0,duration:duration*.35,ease:'power1.in'},at+duration*.65);
      tl.set(p,{opacity:1},at+duration);
    } else if (id === 'highlight-sweep') {
      setPending(tl,p,scene.start,{opacity:.4});
      tweenFinal(tl,p,at,duration*.3,{opacity:1});
      const bar=shape(layer,'hf-highlight');
      Object.assign(bar.style,{left:'-2%',right:'-2%',top:'16%',bottom:'8%',background:accent,transformOrigin:'left center'});
      tl.set(bar,{opacity:.3,scaleX:0},scene.start);
      tl.to(bar,{scaleX:1,duration:duration*.62,ease:cut},at);
      tl.to(bar,{opacity:0,duration:duration*.38,ease:'power1.in'},at+duration*.62);
    } else if (id === 'strike-through') {
      setPending(tl,p,scene.start,{opacity:.42});
      tweenFinal(tl,p,at+duration*.35,duration*.25,{opacity:1});
      const bar=shape(layer,'hf-strike');
      Object.assign(bar.style,{left:'-1%',right:'-1%',top:'52%',height:'8px',background:accent,transformOrigin:'left center'});
      tl.set(bar,{opacity:1,scaleX:0},scene.start);
      tl.to(bar,{scaleX:1,duration:duration*.62,ease:cut},at);
      tl.to(bar,{opacity:0,duration:duration*.38,ease:'power1.in'},at+duration*.62);
    } else if (id === 'typewriter-code') {
      const chars=wrapChars(p);
      tl.set(chars,{opacity:0},scene.start);
      tl.to(chars,{opacity:1,duration:Math.min(.052,duration/4),stagger:Math.min(.022,duration/Math.max(1,chars.length+1)),ease:'none'},at);
      const cursor=shape(layer,'hf-cursor');
      cursor.textContent='_';Object.assign(cursor.style,{position:'relative',display:'inline',color:accent,font:'inherit'});
      pulseFrames(tl,cursor,at,duration,{opacity:1});
    } else if (id === 'number-counter') {
      setPending(tl,p,scene.start,{opacity:.18,y:34,scale:.96});
      tweenFinal(tl,p,at,duration,{opacity:1,y:0,scale:1});
    } else if (id === 'text-path') {
      setPending(tl,p,scene.start,{opacity:.25});
      tweenFinal(tl,p,at,duration,{opacity:1});
      const ns='http://www.w3.org/2000/svg';
      const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 1000 600');
      Object.assign(svg.style,{position:'absolute',inset:'0',width:'100%',height:'100%'});
      const path=document.createElementNS(ns,'path'),pathId=`hf-path-${block.id}`;
      path.setAttribute('id',pathId);path.setAttribute('d','M70 420 C260 80 740 80 930 420');path.setAttribute('fill','none');
      const text=document.createElementNS(ns,'text');text.setAttribute('fill',accent);text.setAttribute('font-size','42');text.setAttribute('font-weight','800');
      const tp=document.createElementNS(ns,'textPath');tp.setAttribute('href',`#${pathId}`);tp.textContent=rememberText(p).slice(0,96);
      text.append(tp);svg.append(path,text);layer.append(svg);
      tl.set(text,{opacity:0},scene.start);tl.set(tp,{attr:{startOffset:'20%'}},scene.start);
      tl.to(text,{opacity:.8,duration:duration*.25,ease:'power1.out'},at);
      tl.to(tp,{attr:{startOffset:'5%'},duration,ease},at);
      tl.to(text,{opacity:0,duration:duration*.25,ease:'power1.in'},at+duration*.75);
    } else if (id === 'oversized-crop-type') {
      setPending(tl,p,scene.start,{opacity:.18,scale:1.72,y:18,transformOrigin:'50% 55%'});
      tweenFinal(tl,p,at,duration,{opacity:1,scale:1,y:0});
    }
  }

  plan.scenes.forEach(scene => {
    scene.cues.forEach(cue => {
      const block = document.getElementById(`s-${scene.id}--${cue.target}`);
      if (!block) return;
      const at = scene.start + cue.at;
      const duration = cue.duration;
      semantic(scene,cue,block,at,duration);
      pattern(scene,cue,block,at,duration);
    });
  });

  window.__timelines = window.__timelines || {};
  window.__timelines[stage.dataset.compositionId] = tl;
  tl.seek(0);
  return tl;
  };
})();
