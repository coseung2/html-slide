#!/usr/bin/env python3
"""Offline geometry QA for self-contained media-heavy HTML decks.
Checks the authored 1920x1080 stage, text clipping, image/text collisions,
media frames, broken images and presenter chrome. This supplements slide_lint;
it does not validate source facts, media rights, subject identity or focal crops.
"""
from __future__ import annotations
import argparse, json, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

MEASURE = r'''() => {
 const slide=document.querySelector('[data-slide].is-active')||document.querySelector('[data-slide]');
 const stage=document.querySelector('[data-stage]');
 if(!slide||!stage)return {errors:[{kind:'missing-stage-or-slide'}],texts:0,images:0};
 const sr=stage.getBoundingClientRect(),k=sr.width/1920,errors=[],texts=[];
 const box=r=>({x:(r.left-sr.left)/k,y:(r.top-sr.top)/k,w:r.width/k,h:r.height/k});
 const visible=e=>{let a=e;while(a&&a!==document.body){const c=getComputedStyle(a);if(c.display==='none'||c.visibility==='hidden'||Number(c.opacity)===0)return false;a=a.parentElement;}return true;};
 const intersects=(a,b)=>Math.max(0,Math.min(a.right,b.right)-Math.max(a.left,b.left))*Math.max(0,Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top));
 const selector=e=>e.id?'#'+e.id:e.tagName.toLowerCase()+'.'+[...e.classList].join('.');
 const walker=document.createTreeWalker(slide,NodeFilter.SHOW_TEXT);
 while(walker.nextNode()){
   const n=walker.currentNode,e=n.parentElement;if(!n.textContent.trim()||!visible(e)||e.closest('script,style,[aria-hidden="true"]'))continue;
   const range=document.createRange();range.selectNodeContents(n);
   for(const r of range.getClientRects()){
    if(r.width<.1||r.height<.1)continue;
    const b=box(r),text=n.textContent.trim().slice(0,72);texts.push({e,r,text});
    if(!e.closest('[data-bleed]')&&(b.x<95||b.y<53||b.x+b.w>1825||b.y+b.h>1027))errors.push({kind:'safe-inset',text,box:b});
    let a=e;while(a&&a!==stage){const c=getComputedStyle(a),ar=a.getBoundingClientRect();
      if(/hidden|clip|auto|scroll/.test(c.overflowX+' '+c.overflowY)&&
       (r.left<ar.left-k||r.right>ar.right+k||r.top<ar.top-k||r.bottom>ar.bottom+k)){
       errors.push({kind:'text-clipped',text,by:selector(a),box:b});break;
      }a=a.parentElement;
    }
   }
 }
 const imgs=[...slide.querySelectorAll('img')].filter(visible);
 for(const img of imgs){const r=img.getBoundingClientRect(),b=box(r);
  if(!img.complete||!img.naturalWidth)errors.push({kind:'broken-image',alt:img.alt});
  if(b.x<95||b.y<53||b.x+b.w>1825||b.y+b.h>1027)errors.push({kind:'image-outside-safe',alt:img.alt,box:b});
  const zone=img.closest('[data-media-zone]');if(zone){const z=zone.getBoundingClientRect();if(r.left<z.left-k||r.top<z.top-k||r.right>z.right+k||r.bottom>z.bottom+k)errors.push({kind:'media-outside-frame',alt:img.alt});}
  for(const t of texts){if(t.e.closest('[data-media-overlay]'))continue;
   if(intersects(r,t.r)>4*k*k)errors.push({kind:'image-text-overlap',image:img.alt,text:t.text});
  }
 }
 for(const hl of slide.querySelectorAll('[data-hl]')){let target;try{target=slide.querySelector(hl.dataset.target);}catch(_){}
  if(!target||!target.contains(hl)){errors.push({kind:'unbound-highlight',target:hl.dataset.target});continue;}
  const a=hl.getBoundingClientRect(),b=target.getBoundingClientRect();
  if(Math.max(Math.abs(a.left-b.left),Math.abs(a.top-b.top),Math.abs(a.right-b.right),Math.abs(a.bottom-b.bottom))/k>4)errors.push({kind:'highlight-mismatch',target:hl.dataset.target});
 }
 for(const chrome of document.querySelectorAll('.deck-shell,.aux-controls')){if(!visible(chrome))continue;const r=chrome.getBoundingClientRect();
  if(r.left<-.5||r.right>innerWidth+.5||r.top<-.5||r.bottom>innerHeight+.5)errors.push({kind:'chrome-outside-viewport'});
  for(const t of texts)if(intersects(r,t.r)>4*k*k)errors.push({kind:'chrome-covers-text',text:t.text});
 }
 for(let i=0;i<texts.length;i++)for(let j=i+1;j<texts.length;j++){
  const a=texts[i],b=texts[j];if(a.e===b.e||a.e.contains(b.e)||b.e.contains(a.e))continue;
  if(intersects(a.r,b.r)>8*k*k)errors.push({kind:'text-text-overlap',a:a.text,b:b.text});
 }
 const boxes=[...slide.querySelectorAll('[data-copy],[data-visual]')].map(e=>({selector:selector(e),box:box(e.getBoundingClientRect())}));
 return{errors,texts:texts.length,images:imgs.length,boxes};
}'''

def mount(page, source: str) -> list[str]:
    """Load authorized local HTML without file navigation or remote requests."""
    requests=[]
    def route(r):
        requests.append(r.request.url)
        r.abort()
    page.route('**/*',route)
    page.set_content(source,wait_until='load')
    page.evaluate('() => document.fonts.ready')
    return requests

def audit(path: Path, out: Path, viewports: list[tuple[int,int]], screenshots=True):
    out.mkdir(parents=True,exist_ok=True);source=path.read_text(encoding='utf-8')
    report={'file':path.name,'viewports':viewports,'samples':[],'errors':[],'externalRequests':[]}
    executable=shutil.which('chromium') or shutil.which('google-chrome')
    with sync_playwright() as p:
        browser=p.chromium.launch(**({'executable_path':executable} if executable else {}))
        for vw,vh in viewports:
            page=browser.new_page(viewport={'width':vw,'height':vh},device_scale_factor=1,reduced_motion='reduce')
            console=[];page.on('pageerror',lambda e:console.append(str(e)))
            requests=mount(page,source)
            n=page.locator('[data-slide]').count()
            if not n:
                report['errors'].append({'kind':'missing-stage-or-slide'});page.close();continue
            if n>1 and not page.evaluate("typeof window.__deckGoto === 'function'"):
                report['errors'].append({'kind':'missing-navigation-hook'});page.close();continue
            for i in range(n):
                page.evaluate('(i)=>window.__deckGoto?.(i)',i)
                page.wait_for_timeout(40)
                data=page.evaluate(MEASURE);sample={'viewport':[vw,vh],'slide':i+1,**data}
                report['samples'].append(sample)
                report['errors'] += [{'viewport':[vw,vh],'slide':i+1,**e} for e in data['errors']]
                if screenshots and (vw,vh)==viewports[0]:
                    page.evaluate("document.documentElement.classList.add('deck-capture')")
                    page.screenshot(path=str(out/f'slide-{i+1:02}.png'))
                    page.evaluate("document.documentElement.classList.remove('deck-capture')")
            report['externalRequests']+=requests
            report['errors'] += [{'kind':'runtime-error','message':e} for e in console]
            page.close()
        browser.close()
    report['errors'] += [{'kind':'external-request','url':url} for url in sorted(set(report['externalRequests']))]
    baselines={s['slide']:s.get('boxes',[]) for s in report['samples'] if tuple(s['viewport'])==viewports[0]}
    for s in report['samples']:
        for a,b in zip(baselines.get(s['slide'],[]),s.get('boxes',[])):
            drift=max(abs(a['box'][k]-b['box'][k]) for k in ['x','y','w','h'])
            if drift>1:report['errors'].append({'kind':'layout-drift','slide':s['slide'],'viewport':s['viewport'],'pixels':drift})
    report['errorCount']=len(report['errors']);report['slideCount']=max((s['slide'] for s in report['samples']),default=0)
    (out/'geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file',type=Path);parser.add_argument('--out',type=Path,default=Path('out/media-qa'))
    args=parser.parse_args()
    r=audit(args.file,args.out,[(1920,1080),(1280,720),(1024,768),(390,844),(844,390)])
    print(json.dumps({'slides':r['slideCount'],'samples':len(r['samples']),'errors':r['errorCount'],'findings':r['errors'][:30]},ensure_ascii=False,indent=2))
    return 1 if r['errors'] else 0
if __name__=='__main__':raise SystemExit(main())
