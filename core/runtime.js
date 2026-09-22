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
  function placeRoute(item, atEnd) {
    const path=item.querySelector('[data-route-path]'), traveler=item.querySelector('[data-route-traveler]');
    if(!path||!traveler)return;
    const length=path.getTotalLength(), point=path.getPointAtLength(atEnd?length:0);
    traveler.setAttribute('transform','translate('+point.x+' '+point.y+') scale(1)');
  }
  function animateRoute(item) {
    const path=item.querySelector('[data-route-path]'), traveler=item.querySelector('[data-route-traveler]');
    if(!path)return;
    const length=path.getTotalLength(), start=performance.now(), duration=900;
    path.style.strokeDashoffset='1';
    if(traveler)placeRoute(item,false);
    function frame(now) {
      const raw=Math.min(1,(now-start)/duration), t=1-Math.pow(1-raw,3);
      path.style.strokeDashoffset=String(1-t);
      if(traveler){
        const point=path.getPointAtLength(length*t), lift=1+.14*Math.sin(Math.PI*t);
        traveler.setAttribute('transform','translate('+point.x+' '+point.y+') scale('+lift+')');
      }
      if(raw<1)jobs.set(item,requestAnimationFrame(frame));
      else{jobs.delete(item);path.style.strokeDashoffset='';placeRoute(item,true);}
    }
    jobs.set(item,requestAnimationFrame(frame));
  }
  function state() { return {slide:index,phase,steps:isLive()?max():0,slideCount:slides.length,reducedMotion:reduce.matches,staticMode:!isLive()}; }
  function render(animate = false) {
    cancelJobs(); root.classList.toggle('deck-live',isLive());
    slides.forEach((slide,i) => {
      const active = i===index; slide.classList.toggle('is-active',active); slide.inert = !active;
      slide.setAttribute('aria-hidden',String(!active));
      [...slide.classList].filter(c=>c.startsWith('deck-step-')).forEach(c=>slide.classList.remove(c));
      if (active) slide.classList.add('deck-step-'+phase);
      slide.querySelectorAll('[data-motion]').forEach(block=>{
        const first=Number(block.dataset.startStep),last=Number(block.dataset.endStep);
        const done=!isLive() || phase>=last;
        const was=block.dataset.motionState;
        block.dataset.motionState=done?'done':'pending';
        block.querySelectorAll('[data-sequence-item]').forEach((item,j)=>{
          item.dataset.sequenceState=(!isLive() || phase>=first+j)?'done':'pending';
        });
        if(block.dataset.motion==='route-travel'){
          block.querySelectorAll('[data-route-item]').forEach((item,j)=>{
            const routeDone=!isLive() || phase>=first+j, routeWas=item.dataset.routeState;
            item.dataset.routeState=routeDone?'done':'pending';
            const path=item.querySelector('[data-route-path]');if(path)path.style.strokeDashoffset='';
            if(active&&routeDone&&isLive()&&animate&&routeWas==='pending'){placeRoute(item,false);animateRoute(item);}
            else placeRoute(item,routeDone);
          });
          block.querySelectorAll('[data-map-event]').forEach(item=>{
            const after=Math.max(0,Number(item.dataset.eventAfterRoute||0));
            const eventDone=!isLive() || after===0 || phase>=first+after-1;
            item.dataset.eventState=eventDone?'done':'pending';
          });
        }
        (block.dataset.motion==='number-count' ? block.querySelectorAll('[data-number]') : []).forEach(el=>{
          const n=Number(el.dataset.number); el.textContent=format(done?n:0);
          if (block.dataset.motion==='number-count' && active && done && isLive() && animate && was==='pending') count(el,n);
        });
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
  root.classList.add('deck-ready');fit();if(!applyHash())render();
})();
