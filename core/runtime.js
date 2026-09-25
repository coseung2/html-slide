/* One state owner. CSS owns the complete final frame; JS only replays meaning. */
(() => {
  'use strict';
  const root = document.documentElement;
  const stage = document.querySelector('[data-stage]');
  const slides = [...document.querySelectorAll('[data-slide]')];
  if (!stage || !slides.length || window.__deckEngine) return;
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');
  const plan = JSON.parse(document.getElementById('deck-plan').textContent);
  const params = new URLSearchParams(location.search);
  let staticMode = params.get('mode') === 'static' || (params.get('mode') !== 'live' && document.body.dataset.mode === 'static');
  let index = 0, phase = 0, previousFocus = null;
  const jobs = new Map();
  let renderedIndex = -1;
  const isLive = () => !reduce.matches && !staticMode;
  const max = (i = index) => Number(slides[i].dataset.steps || 0);
  const format = n => new Intl.NumberFormat('en-US', {maximumFractionDigits: 4}).format(n);
  const chrome = document.createElement('nav');
  chrome.className = 'deck-shell'; chrome.setAttribute('aria-label', '발표 조작');
  chrome.innerHTML = '<button class="deck-shell__arrow" data-deck-prev aria-label="이전 단계">&#8249;</button><span class="deck-shell__counter" data-deck-counter></span><button class="deck-shell__arrow" data-deck-next aria-label="다음 단계">&#8250;</button><span class="deck-shell__phase" data-deck-phase></span><button data-deck-static title="S" aria-pressed="false">정적</button><button data-deck-overview title="O">전체 보기</button><button class="deck-shell__fullscreen" data-deck-full title="F">전체 화면</button>';
  const progress = document.createElement('div'); progress.className = 'deck-shell-progress';
  progress.innerHTML = '<div class="deck-shell-progress__value" data-deck-progress></div>'; progress.setAttribute('aria-hidden','true');
  const status = document.createElement('div'); status.className = 'deck-shell-sr'; status.setAttribute('role','status'); status.setAttribute('aria-live','polite');
  const overview = document.createElement('dialog'); overview.className = 'deck-shell-overview';
  overview.setAttribute('aria-label','슬라이드 전체 보기');
  overview.innerHTML = '<h2>슬라이드 전체 보기</h2><div class="deck-shell-overview__list"></div><div class="deck-sources"></div><button class="deck-shell-overview__close">닫기</button>';
  document.body.append(chrome,progress,status,overview);
  const prev = chrome.querySelector('[data-deck-prev]'), next = chrome.querySelector('[data-deck-next]');
  const staticBtn = chrome.querySelector('[data-deck-static]');
  function fit() {
    const k = Math.min(innerWidth/1920, innerHeight/1080);
    stage.style.transform = `translate(${(innerWidth-1920*k)/2}px,${(innerHeight-1080*k)/2}px) scale(${k})`;
  }
  function cancelJobs() { jobs.forEach(request => cancelAnimationFrame(request)); jobs.clear(); }
  function count(el, target) {
    const start = performance.now();
    function frame(now) {
      const t = Math.min(1,(now-start)/500); el.textContent = format(target*(1-Math.pow(1-t,3)));
      if (t < 1) jobs.set(el,requestAnimationFrame(frame)); else jobs.delete(el);
    }
    jobs.set(el,requestAnimationFrame(frame));
  }
  const segment = text => {
    try { return [...new Intl.Segmenter(document.documentElement.lang || 'en',{granularity:'grapheme'}).segment(text)].map(x=>x.segment); }
    catch (_) { return Array.from(text); }
  };
  const primarySelectors={
    'statement':'.statement','quote':'blockquote','comparison-text':'.comparison-copy',
    'metric':'.metric-value','score':'.score-value','image':'img','logo':'img',
    'ranking':'.ranking','bullet-list':'.module-list','timeline':'.module-timeline',
    'process':'.process','bar-chart':'.bar-chart','line-chart':'.line-chart'
  };
  function patternPrimary(block) {
    const selector=primarySelectors[block.dataset.module];
    return (selector && block.querySelector(selector)) || block;
  }
  function splitSource(primary) {
    if(primary.dataset.patternText==null)primary.dataset.patternText=primary.textContent;
    return primary.dataset.patternText;
  }
  function restoreSplit(primary) {
    if(primary.dataset.patternText==null)return;
    primary.textContent=primary.dataset.patternText;delete primary.dataset.patternReady;
  }
  function settleSplit(block,primary,delay) {
    const start=performance.now();
    function frame(now) {
      if(now-start<delay){jobs.set(block,requestAnimationFrame(frame));return;}
      restoreSplit(primary);jobs.delete(block);
    }
    jobs.set(block,requestAnimationFrame(frame));
  }
  function wrapWords(primary) {
    if (primary.dataset.patternReady) return;
    const parts=splitSource(primary).split(/(\s+)/);let n=0;primary.replaceChildren();
    parts.forEach(part=>{
      if(!part)return;
      if(/^\s+$/.test(part)){primary.append(document.createTextNode(part));return;}
      const span=document.createElement('span');span.className='motion-word';span.style.setProperty('--i',n++);span.textContent=part;primary.append(span);
    });
    primary.dataset.patternReady='word';
  }
  function wrapChars(primary) {
    if (primary.dataset.patternReady) return;
    const chars=segment(splitSource(primary));primary.replaceChildren();
    chars.forEach((ch,i)=>{const span=document.createElement('span');span.className='motion-char';span.style.setProperty('--i',i);span.textContent=ch;primary.append(span);});
    primary.dataset.patternReady='char';
  }
  function addParticles(block) {
    if(block.querySelector('.motion-particles'))return;
    const layer=document.createElement('span');layer.className='motion-particles';layer.setAttribute('aria-hidden','true');
    for(let i=0;i<18;i++){
      const dot=document.createElement('span');dot.className='motion-particle';dot.style.setProperty('--i',i);
      const angle=(i*137.5)*Math.PI/180, radius=90+(i%6)*34;
      dot.style.setProperty('--dx',`${Math.cos(angle)*radius}px`);dot.style.setProperty('--dy',`${Math.sin(angle)*radius}px`);layer.append(dot);
    }
    block.append(layer);
  }
  function addTextPath(block, primary) {
    if(block.querySelector('.motion-text-path'))return;
    const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.classList.add('motion-text-path');svg.setAttribute('viewBox','0 0 1000 260');svg.setAttribute('aria-hidden','true');
    const path=document.createElementNS(ns,'path'),id=`motion-path-${block.id}`;path.setAttribute('id',id);path.setAttribute('d','M60 190 C260 30 730 20 940 170');svg.append(path);
    const text=document.createElementNS(ns,'text'),tp=document.createElementNS(ns,'textPath');tp.setAttribute('href',`#${id}`);tp.setAttribute('startOffset','5%');tp.textContent=primary.textContent.trim();text.append(tp);svg.append(text);block.append(svg);
  }
  function preparePatterns() {
    document.querySelectorAll('[data-pattern]').forEach(block=>{
      const primary=patternPrimary(block);primary.setAttribute('data-pattern-primary','');
      const pattern=block.dataset.pattern;
      if(['line-split','highlight-sweep','strike-through'].includes(pattern)) primary.dataset.motionText=primary.textContent;
      if(pattern==='word-by-word')wrapWords(primary);
      else if(pattern==='typewriter-code')wrapChars(primary);
      else if(pattern==='scramble-decode' && primary.dataset.finalText==null)primary.dataset.finalText=primary.textContent;
      else if(pattern==='particle-warp')addParticles(block);
      else if(pattern==='text-path')addTextPath(block,primary);
    });
  }
  const scrambleGlyphs=segment('░▒▓#%&0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ가나다라마바사아자차카타파하');
  function restoreScramble(block){
    const primary=patternPrimary(block);if(primary.dataset.finalText!=null)primary.textContent=primary.dataset.finalText;
  }
  function seedScramble(block){
    const primary=patternPrimary(block),final=primary.dataset.finalText;if(final==null)return;
    primary.textContent=segment(final).map((ch,i)=>/\s/.test(ch)?ch:scrambleGlyphs[(i*7+3)%scrambleGlyphs.length]).join('');
  }
  function runScramble(block){
    const primary=patternPrimary(block),final=primary.dataset.finalText;if(final==null)return;
    const chars=segment(final),start=performance.now(),duration=680;
    function frame(now){
      const t=Math.min(1,(now-start)/duration),fixed=Math.floor(chars.length*Math.pow(t,.72));
      primary.textContent=chars.map((ch,i)=>/\s/.test(ch)||i<fixed?ch:scrambleGlyphs[(i*13+Math.floor(now/42))%scrambleGlyphs.length]).join('');
      if(t<1)jobs.set(block,requestAnimationFrame(frame));else{primary.textContent=final;jobs.delete(block);}
    }
    jobs.set(block,requestAnimationFrame(frame));
  }
  function numericElements(block){return [...block.querySelectorAll('[data-number]')];}
  function setNumbersStart(block){numericElements(block).forEach(el=>el.textContent='0');}
  function restoreNumbers(block){numericElements(block).forEach(el=>el.textContent=format(Number(el.dataset.number)));}
  function runPatternCount(block){numericElements(block).forEach(el=>{el.textContent='0';count(el,Number(el.dataset.number));});}
  function state() { return {slide:index,phase,steps:isLive()?max():0,slideCount:slides.length,reducedMotion:reduce.matches,staticMode:!isLive()}; }
  function render(animate = false) {
    const entered=index!==renderedIndex;
    cancelJobs(); root.classList.toggle('deck-live',isLive());
    slides.forEach((slide,i) => {
      const active = i===index; slide.classList.toggle('deck-entering',active&&entered); slide.classList.toggle('is-active',active); slide.inert = !active;
      slide.setAttribute('aria-hidden',String(!active));
      [...slide.classList].filter(c=>c.startsWith('deck-step-')).forEach(c=>slide.classList.remove(c));
      if (active) slide.classList.add('deck-step-'+phase);
      slide.querySelectorAll('[data-motion]').forEach(block=>{
        const first=Number(block.dataset.startStep),last=Number(block.dataset.endStep);
        const done=!isLive() || phase>=last;
        const was=block.dataset.motionState,nextState=done?'done':'pending';
        block.dataset.motionRun=(isLive()&&active&&!entered&&was==='pending'&&nextState==='done')?'1':'0';
        block.dataset.motionState=nextState;
        block.querySelectorAll('[data-sequence-item]').forEach((item,j)=>{
          item.dataset.sequenceState=(!isLive() || phase>=first+j)?'done':'pending';
        });
        const pattern=block.dataset.pattern;
        if(pattern==='word-by-word'||pattern==='typewriter-code'){
          const primary=patternPrimary(block);
          if(!isLive())restoreSplit(primary);
          else if(!done){
            pattern==='word-by-word'?wrapWords(primary):wrapChars(primary);
          } else if(active&&animate&&was==='pending'){
            const count=primary.querySelectorAll(pattern==='word-by-word'?'.motion-word':'.motion-char').length;
            const delay=pattern==='word-by-word'?Math.min(1600,640+Math.max(0,count-1)*65):Math.min(1400,180+Math.max(0,count-1)*22);
            settleSplit(block,primary,delay);
          } else restoreSplit(primary);
        }
        if(pattern==='scramble-decode'){
          if(!isLive())restoreScramble(block);
          else if(!done)seedScramble(block);
          else if(active&&animate&&was==='pending')runScramble(block);
          else restoreScramble(block);
        }
        if(pattern==='number-counter'){
          if(!isLive())restoreNumbers(block);
          else if(!done)setNumbersStart(block);
          else if(active&&animate&&was==='pending')runPatternCount(block);
          else restoreNumbers(block);
        } else if(block.dataset.motion==='number-count') {
          numericElements(block).forEach(el=>{
            const n=Number(el.dataset.number);el.textContent=format(done?n:0);
            if(active&&done&&isLive()&&animate&&was==='pending')count(el,n);
          });
        }
      });
    });
    document.body.dataset.theme=slides[index].dataset.theme;
    chrome.querySelector('[data-deck-counter]').textContent=`${String(index+1).padStart(2,'0')} / ${String(slides.length).padStart(2,'0')}`;
    chrome.querySelector('[data-deck-phase]').textContent=isLive()?`${phase} / ${max()}`:'STATIC';
    staticBtn.setAttribute('aria-pressed',String(!isLive())); staticBtn.disabled=reduce.matches;
    prev.disabled=index===0 && (!isLive() || phase===0);
    next.disabled=index===slides.length-1 && (!isLive() || phase===max());
    const units=slides.map(s=>isLive()?1+Number(s.dataset.steps):1);
    const total=units.reduce((a,b)=>a+b,0)-1;
    const completed=units.slice(0,index).reduce((a,b)=>a+b,0)+(isLive()?phase:0);
    progress.firstElementChild.style.transform=`scaleX(${total>0?completed/total:1})`;
    status.textContent=`${index+1} / ${slides.length}. ${slides[index].dataset.title}. ${isLive()?phase+' / '+max():'정적 화면'}`;
    renderedIndex=index;
    try { history.replaceState(null,'',`#${index+1}${isLive()&&phase?'.'+phase:''}`); } catch (_) {}
    window.dispatchEvent(new CustomEvent('deck:state',{detail:state()}));
  }
  function goto(n,p=0) {
    if (!Number.isInteger(n) || n<0 || n>=slides.length || !Number.isFinite(Number(p))) return null;
    index=n; phase=isLive()?Math.min(max(n),Math.max(0,Math.trunc(Number(p)))):0; render(); return state();
  }
  function forward() {
    if (isLive() && phase<max()) {phase++;render(true);}
    else if (index<slides.length-1) goto(index+1);
  }
  function back() {
    if (isLive() && phase>0) {phase--;render();}
    else if (index>0) goto(index-1,isLive()?max(index-1):0);
  }
  function setStatic(value) {staticMode=Boolean(value);phase=0;render();}
  function openOverview() {
    previousFocus=document.activeElement;
    const list=overview.querySelector('.deck-shell-overview__list'); list.replaceChildren();
    slides.forEach((s,i)=>{
      const b=document.createElement('button');b.type='button';b.textContent=`${String(i+1).padStart(2,'0')}  ${s.dataset.title}`;
      if (i===index) b.setAttribute('aria-current','true');
      b.addEventListener('click',()=>{goto(i);closeOverview();});list.append(b);
    });
    const sources=overview.querySelector('.deck-sources');sources.replaceChildren();
    const seen=new Set();
    plan.slides.forEach(s=>(s.sources||[]).forEach(source=>{
      if(seen.has(source.url))return;seen.add(source.url);
      const a=document.createElement('a');a.href=source.url;a.textContent=source.label;a.target='_blank';a.rel='noopener noreferrer';sources.append(a);
    }));
    overview.showModal();list.querySelector('[aria-current]')?.focus();
  }
  function closeOverview() {overview.close();previousFocus?.focus();}
  async function fullscreen() {
    try {if(document.fullscreenElement)await document.exitFullscreen();else await root.requestFullscreen();}
    catch(_){status.textContent='이 환경에서는 전체 화면을 사용할 수 없습니다.';}
  }
  prev.addEventListener('click',back);next.addEventListener('click',forward);
  staticBtn.addEventListener('click',()=>setStatic(!staticMode));
  chrome.querySelector('[data-deck-overview]').addEventListener('click',openOverview);
  chrome.querySelector('[data-deck-full]').addEventListener('click',fullscreen);
  overview.querySelector('.deck-shell-overview__close').addEventListener('click',closeOverview);
  overview.addEventListener('cancel',e=>{e.preventDefault();closeOverview();});
  stage.addEventListener('click',e=>{
    if(e.target.closest('a,button,input,select,textarea,[contenteditable]')||getSelection()?.toString())return;
    const r=stage.getBoundingClientRect();e.clientX<r.left+r.width/2?back():forward();
  });
  addEventListener('keydown',e=>{
    if(e.defaultPrevented||e.altKey||e.ctrlKey||e.metaKey||overview.open||e.target.closest?.('input,textarea,select,[contenteditable]'))return;
    if([' ','Enter'].includes(e.key)&&e.target.closest?.('a,button'))return;
    const k=e.key.toLowerCase();
    if(['ArrowRight','ArrowDown',' ','Enter','PageDown'].includes(e.key)){e.preventDefault();forward();}
    else if(['ArrowLeft','ArrowUp','PageUp','Backspace'].includes(e.key)){e.preventDefault();back();}
    else if(k==='s'&&!reduce.matches){e.preventDefault();setStatic(!staticMode);}
    else if(k==='o'){e.preventDefault();openOverview();}
    else if(k==='f'){e.preventDefault();fullscreen();}
    else if(k==='home'){e.preventDefault();goto(0);}
    else if(k==='end'){e.preventDefault();goto(slides.length-1);}
  });
  function applyHash() {
    const m=location.hash.match(/^#(\d+)(?:\.(\d+))?$/);
    return m?goto(Math.max(0,Math.min(slides.length-1,Number(m[1])-1)),Number(m[2]||0)):null;
  }
  addEventListener('hashchange',applyHash);addEventListener('resize',fit);
  let printState=null;
  addEventListener('beforeprint',()=>{printState={staticMode,index,phase};setStatic(true);});
  addEventListener('afterprint',()=>{if(printState){staticMode=printState.staticMode;index=printState.index;phase=printState.phase;printState=null;render();}});
  reduce.addEventListener('change',()=>{phase=0;render();});
  document.fonts?.ready.then(fit);
  window.__deckGoto=goto;window.__deckNext=forward;window.__deckPrev=back;window.__deckState=state;
  window.__deckShell={setStatic,isStatic:()=>!isLive(),openOverview,closeOverview,update:render};
  window.__deckEngine={version:1,plan,fit};
  // Preserve the public adapter shape used by legacy exporters and test harnesses.
  window.deck={stage,slides,goto,next:forward,prev:back,state,render,measure:fit,reflow:fit,start:()=>0,phases:i=>isLive()?max(i):0,
    get slide(){return index;},get phase(){return phase;},get reduce(){return reduce.matches;}};
  preparePatterns();root.classList.add('deck-ready');fit();if(!applyHash())render();
})();
