#!/usr/bin/env python3
"""Browser QA for modular decks: geometry, overlap, media and motion contracts."""
from __future__ import annotations
import argparse
import json
import os
import shutil
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

GEOMETRY = r'''() => {
 const slides=[...document.querySelectorAll('[data-slide]')];
 const slide=slides.find(s=>s.classList.contains('is-active')) || slides[0];
 const base=slide.getBoundingClientRect(), scale=base.width/1920, errors=[];
 const rect=e=>{const r=e.getBoundingClientRect();return {x:(r.left-base.left)/scale,y:(r.top-base.top)/scale,w:r.width/scale,h:r.height/scale}};
 const bad=(kind,el,detail)=>errors.push({kind,element:el.id||el.className?.baseVal||el.className||el.tagName,detail});
 const outside=(r,p,t=2)=>r.x<p.x-t||r.y<p.y-t||r.x+r.w>p.x+p.w+t||r.y+r.h>p.y+p.h+t;
 const safe={x:96,y:54,w:1728,h:972};
 const boxes=[...slide.querySelectorAll('[data-copy],[data-qa-box]')];
 for(const e of boxes){const r=rect(e);if(outside(r,safe))bad('safe-area',e,r);
  if(e.scrollWidth>e.clientWidth+2||e.scrollHeight>e.clientHeight+2)bad('overflow',e,{scroll:[e.scrollWidth,e.scrollHeight],box:[e.clientWidth,e.clientHeight]});}
 for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++){
  const a=boxes[i],b=boxes[j];if(a.contains(b)||b.contains(a))continue;
  const ar=rect(a),br=rect(b),w=Math.min(ar.x+ar.w,br.x+br.w)-Math.max(ar.x,br.x),h=Math.min(ar.y+ar.h,br.y+br.h)-Math.max(ar.y,br.y);
  if(w>2&&h>2)bad('overlap',a,{other:b.id||b.className,w,h});
 }
 const walker=document.createTreeWalker(slide,NodeFilter.SHOW_TEXT);
 while(walker.nextNode()){
  const node=walker.currentNode,el=node.parentElement;if(!node.textContent.trim()||!el||el.closest('.sr-only,[aria-hidden="true"]'))continue;
  const range=document.createRange();range.selectNodeContents(node);const r0=range.getBoundingClientRect();if(!r0.width||!r0.height)continue;
  const r={x:(r0.left-base.left)/scale,y:(r0.top-base.top)/scale,w:r0.width/scale,h:r0.height/scale};
  const box=el.closest('[data-qa-box],[data-copy]');
  if(outside(r,safe))bad('text-safe-area',el,r);
  if(box&&outside(r,rect(box),3))bad('text-overflow',el,{text:node.textContent.slice(0,70),rect:r,container:rect(box)});
 }
 for(const img of slide.querySelectorAll('img'))if(!img.complete||!img.naturalWidth)bad('broken-image',img,img.alt);
 for(const hl of slide.querySelectorAll('[data-hl]')){
  const target=slide.querySelector(hl.dataset.target);if(!target||!target.contains(hl)){bad('unbound-highlight',hl,hl.dataset.target);continue;}
  const a=rect(hl),b=rect(target);const covered=Math.max(0,Math.min(a.x+a.w,b.x+b.w)-Math.max(a.x,b.x))*Math.max(0,Math.min(a.y+a.h,b.y+b.h)-Math.max(a.y,b.y));
  if(covered/(b.w*b.h)<.85)bad('highlight-coverage',hl,covered/(b.w*b.h));
 }
 return {slide:slide.dataset.slide,errors};
}'''


def launch_options():
    path=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH') or os.environ.get('CHROME_PATH') or shutil.which('chromium') or shutil.which('google-chrome')
    return {'executable_path':path} if path else {}


def verify(path: Path, out: Path, viewports=None) -> dict:
    from playwright.sync_api import sync_playwright
    out.mkdir(parents=True,exist_ok=True)
    results=[]; errors=[]; page_errors=[]; network=[]
    raw=path.read_text(encoding='utf-8')
    def load_page(page,suffix=''):
        page.set_content(raw,wait_until='load')
    viewports=viewports or [(1920,1080),(1366,768),(1024,768),(390,844)]
    def require(condition,label,detail=None):
        if not condition: errors.append({'kind':label,'detail':detail})
    with sync_playwright() as pw:
        browser=pw.chromium.launch(**launch_options())
        try:
            for width,height in viewports:
                ctx=browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce')
                page=ctx.new_page();page.on('pageerror',lambda e:page_errors.append(str(e)))
                page.on('request',lambda req:network.append(req.url) if req.url.startswith(('http:','https:')) and not req.url.startswith('http://deck.local/') else None)
                load_page(page);page.evaluate('document.fonts.ready')
                count=page.locator('[data-slide]').count()
                for i in range(count):
                    page.evaluate('i=>__deckGoto(i)',i);page.wait_for_timeout(15)
                    result=page.evaluate(GEOMETRY);result['viewport']=[width,height];results.append(result)
                    errors.extend(result['errors'])
                    if width==1920:page.screenshot(path=str(out/f'slide-{i+1:02d}.png'))
                ctx.close()
            # Live phase walk, reversal, static toggle, deep link, reduced motion.
            ctx=browser.new_context(viewport={'width':1920,'height':1080},reduced_motion='no-preference')
            page=ctx.new_page();page.on('pageerror',lambda e:page_errors.append(str(e)))
            load_page(page);page.evaluate('document.fonts.ready')
            count=page.locator('[data-slide]').count()
            for i in range(count):
                state=page.evaluate('i=>__deckGoto(i,0)',i);maximum=state['steps']
                for step in range(1,maximum+1):
                    page.evaluate('__deckNext()');state=page.evaluate('__deckState()')
                    require(state['slide']==i and state['phase']==step,'phase-forward',state)
                page.wait_for_timeout(540)
                require(page.evaluate("[...document.querySelectorAll('[data-slide].is-active [data-motion]')].every(e=>e.dataset.motionState==='done')"),'final-phase-complete',i)
                for step in range(maximum-1,-1,-1):
                    page.evaluate('__deckPrev()');require(page.evaluate('__deckState().phase')==step,'phase-reverse',i)
            page.evaluate('__deckShell.setStatic(true);__deckGoto(0)')
            page.keyboard.press('ArrowRight');require(page.evaluate('__deckState().slide')==min(1,count-1),'static-navigation')
            page.keyboard.press('s');require(page.evaluate('__deckState().staticMode') is False,'static-toggle')
            page.keyboard.press('o');require(page.locator('dialog').evaluate('(el)=>el.open'),'overview-open')
            page.keyboard.press('Escape');require(not page.locator('dialog').evaluate('(el)=>el.open'),'overview-close')
            page.evaluate("history.replaceState(null,'','#2');dispatchEvent(new HashChangeEvent('hashchange'))")
            require(page.evaluate('__deckState().slide')==min(1,count-1),'hash-navigation')
            page.emulate_media(reduced_motion='reduce');page.wait_for_timeout(80);require(page.evaluate("!document.documentElement.classList.contains('deck-live')"),'reduced-motion')
            # Print events must restore the pre-print state after showing final text.
            page.emulate_media(reduced_motion='no-preference');page.wait_for_timeout(80);page.evaluate('__deckShell.setStatic(false);__deckGoto(0)')
            before=page.evaluate('__deckState()');page.evaluate("dispatchEvent(new Event('beforeprint'))")
            require(page.evaluate('__deckState().staticMode'),'print-final')
            page.evaluate("dispatchEvent(new Event('afterprint'))");require(page.evaluate('__deckState()')==before,'print-state-restore')
            ctx.close()
            # JavaScript-disabled DOM must contain every complete final value.
            ctx=browser.new_context(viewport={'width':1920,'height':1080},java_script_enabled=False)
            page=ctx.new_page();load_page(page);page.evaluate('document.fonts.ready')
            require(page.locator('[data-slide]').count()==count,'no-js-slide-count')
            for i in range(count):
                page.evaluate('i=>document.querySelectorAll("[data-slide]").forEach((s,n)=>s.classList.toggle("is-active",i===n))',i)
                result=page.evaluate(GEOMETRY);result['viewport']='no-js';results.append(result);errors.extend(result['errors'])
            require(page.evaluate("[...document.querySelectorAll('[data-number]')].every(e=>Number(e.textContent.replaceAll(',',''))===Number(e.dataset.number))"),'no-js-final-numbers')
            ctx.close()
        finally:browser.close()
    errors.extend({'kind':'page-error','detail':e}for e in page_errors)
    errors.extend({'kind':'external-request','detail':e}for e in network)
    report={'source':str(path),'slides':count,'geometryFrames':len(results),'viewports':[list(v)for v in viewports],'errors':errors,'results':results,'notes':['Rendered with set_content to support managed Chromium URL restrictions. Initial URL query/deep-link loading is not covered by this harness.']}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('html',type=Path);p.add_argument('--out',type=Path,default=Path('dist/modular-qa'))
    a=p.parse_args(argv)
    try:
        report=verify(a.html,a.out)
        print(json.dumps({k:v for k,v in report.items()if k!='results'},ensure_ascii=False,indent=2))
        return 2 if report['errors']else 0
    except Exception as exc:print(f'MODULAR QA FAIL: {exc}',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
