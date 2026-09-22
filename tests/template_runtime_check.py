#!/usr/bin/env python3
"""Regression tests for media-heavy template helpers and the shared Deck runtime."""
from pathlib import Path
import json
import shutil
import sys
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from media_qa import MEASURE, mount

STYLE = '''
*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;color:#152034;background:#fbfaf7}
#stage{position:relative;width:1920px;transform-origin:top left}
.slide{position:relative;width:1920px;height:1080px;padding:96px;background:#fbfaf7;word-break:keep-all}
.deck-ready #stage{position:absolute;height:1080px;overflow:hidden}
.deck-ready .slide{position:absolute;inset:0;visibility:hidden;opacity:0}
.deck-ready .slide.is-active{visibility:visible;opacity:1}
h1{font-size:80px;margin:0 0 64px}p{font-size:36px;margin:24px 0}
.panel{width:720px;padding:32px;border:2px solid #304057;margin-bottom:32px}
.sport-focus{width:320px;height:200px;padding:32px}
.sport-focus strong{font-size:80px}.sport-focus p{font-size:24px;margin:12px 0}
.sport-bar-track{margin-top:24px}
[data-media-zone]{width:640px;height:320px}
.caption{margin-top:40px}.aux-controls{display:none}
'''
BODY = '''
<main id="stage" data-stage>
<section class="slide" data-slide="01" data-title="Sample points" data-sports="compare" data-start="0" data-step="1">
<h1 data-copy>Sample points</h1><div data-visual><div class="panel"><p>ALPHA: 15 points</p><div class="sport-bar-track"><i class="sport-bar-fill" style="--value:100%"></i></div></div><div class="panel"><p>BETA: 12 points</p><div class="sport-bar-track"><i class="sport-bar-fill" style="--value:80%"></i></div></div></div>
</section>
<section class="slide" data-slide="02" data-title="Sample record" data-sports="focus" data-start="0" data-step="1">
<h1 data-copy>Sample record</h1><div id="record" class="sport-focus" data-visual><strong>16</strong><p>Sample goals</p><i class="sport-cue" data-hl data-target="#record" data-step="1" aria-hidden="true"></i></div>
</section>
<section class="slide" data-slide="03" data-title="Separate media">
<h1 data-copy>Separate media</h1><figure data-visual style="margin:0"><div data-media-zone><img alt="Synthetic test graphic, not a match photograph" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 640 320'%3E%3Crect width='640' height='320' fill='%23345a85'/%3E%3C/svg%3E"></div><figcaption class="caption"><p>Caption in its own row</p></figcaption></figure>
</section></main>
<dialog id="credits"><p>Source dialog</p><button>Close</button></dialog>
'''

def fixture():
    css = (ROOT / 'templates' / 'sports-broadcast.css').read_text(encoding='utf-8') + '\n' + (ROOT / 'motion' / 'deck-shell.css').read_text(encoding='utf-8')
    js = '\n'.join('<script>'+ (ROOT / 'motion' / n).read_text(encoding='utf-8') + '</script>' for n in ['deck-motion.js','deck-shell.js'])
    return '<!doctype html><html><head><meta charset="utf-8"><style>'+STYLE+css+'</style></head><body>'+BODY+js+'</body></html>'

def main():
    results=[]
    def check(name, condition):
        results.append({'name':name,'pass':bool(condition)})
        if not condition: print('FAIL:',name)
    with sync_playwright() as p:
        executable=shutil.which('chromium') or shutil.which('google-chrome')
        browser=p.chromium.launch(**({'executable_path':executable} if executable else {}))
        page=browser.new_page(viewport={'width':1920,'height':1080})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        req=mount(page,fixture())
        check('shared shell present exactly once',page.locator('.deck-shell').count()==1)
        check('phase zero is live',page.evaluate('__deckState().phase')==0 and not page.evaluate('__deckShell.isStatic()'))
        idle=page.evaluate('__deckState()');page.wait_for_timeout(900)
        check('idle never autoplays a phase',idle==page.evaluate('__deckState()'))
        check('phase indicator starts at zero',page.locator('[data-deck-phase]').inner_text().strip()=='0 / 1')
        stage=page.locator('[data-stage]').bounding_box()
        page.mouse.click(stage['x']+stage['width']*.75,stage['y']+stage['height']*.5)
        check('right-half click advances one phase',page.evaluate('__deckState().slide')==0 and page.evaluate('__deckState().phase')==1)
        check('phase indicator tracks click',page.locator('[data-deck-phase]').inner_text().strip()=='1 / 1')
        page.mouse.click(stage['x']+stage['width']*.25,stage['y']+stage['height']*.5)
        check('left-half click reverses one phase',page.evaluate('__deckState().slide')==0 and page.evaluate('__deckState().phase')==0)
        page.locator('[data-deck-next]').focus();page.keyboard.press('Enter')
        check('button Enter advances once',page.evaluate('__deckState().slide')==0 and page.evaluate('__deckState().phase')==1)
        page.keyboard.press('ArrowRight')
        check('arrow works after control focus',page.evaluate('__deckState().slide')==1 and page.evaluate('__deckState().phase')==0)
        page.keyboard.press('s')
        check('static shows final focus',page.evaluate('__deckShell.isStatic()') and page.locator('.is-active .sport-cue').evaluate("e=>getComputedStyle(e).opacity==='1'"))
        page.keyboard.press('ArrowRight');check('static skips hidden phases',page.evaluate('__deckState().slide')==2)
        page.keyboard.press('s');page.keyboard.press('o')
        check('overview opens',page.locator('.deck-shell-overview').evaluate('(d)=>d.open'))
        old=page.evaluate('__deckState()');page.keyboard.press('ArrowLeft')
        check('overview blocks global navigation',old==page.evaluate('__deckState()'))
        page.locator('[data-goto="0"]').focus();page.keyboard.press('Enter')
        check('overview Enter selects without extra advance',page.evaluate('__deckState().slide')==0 and page.evaluate('__deckState().phase')==0)
        page.evaluate("document.querySelector('#credits').showModal()")
        old=page.evaluate('__deckState()');page.keyboard.press('ArrowRight');page.keyboard.press('s')
        check('non-shell modal isolates navigation and S',old==page.evaluate('__deckState()') and not page.evaluate('__deckShell.isStatic()'))
        page.evaluate("document.querySelector('#credits').close()")
        page.emulate_media(reduced_motion='reduce');page.wait_for_timeout(50)
        check('reduced-motion change updates core and shell',page.evaluate('__deckState().reducedMotion') and page.evaluate('__deckShell.isStatic()'))
        check('reduced-motion final bars',page.locator('.is-active .sport-bar-fill').first.evaluate("e=>getComputedStyle(e).transform==='matrix(1, 0, 0, 1, 0, 0)'"))
        page.emulate_media(reduced_motion='no-preference');page.wait_for_timeout(50)
        check('motion preference can be restored',not page.evaluate('__deckState().reducedMotion') and page.evaluate('__deckState().steps')==1)
        page.evaluate('__deckGoto(0,1)');page.keyboard.press('ArrowLeft')
        check('Back reverses the beat',page.evaluate('__deckState().phase')==0)
        check('invalid slide does not corrupt state',page.evaluate('__deckGoto(NaN)===null && __deckState().slide===0'))
        deep=browser.new_page();deep.evaluate("location.hash='#2.1'");mount(deep,fixture())
        check('initial deep link honored',deep.evaluate('__deckState().slide')==1 and deep.evaluate('__deckState().phase')==1)
        deep.evaluate("location.hash='#3'");deep.wait_for_timeout(50)
        check('subsequent hash change honored',deep.evaluate('__deckState().slide')==2)
        page.emulate_media(reduced_motion='reduce')
        for vw,vh in [(1920,1080),(1280,720),(1024,768),(390,844),(844,390)]:
            page.set_viewport_size({'width':vw,'height':vh})
            for i in range(3):
                page.evaluate('(i)=>__deckGoto(i)',i);page.wait_for_timeout(30)
                findings=page.evaluate(MEASURE)['errors']
                check(f'geometry {vw}x{vh} slide {i+1}',not findings)
        bad=browser.new_page(viewport={'width':1920,'height':1080})
        bad.set_content('''<style>body{margin:0}#stage{width:1920px;height:1080px;position:relative}.slide{position:absolute;inset:0}.x{position:absolute;left:120px;top:120px;width:400px;height:150px}.x img{width:400px;height:150px}.y{position:absolute;left:120px;top:120px;font:36px Arial}.bad{position:absolute;left:1900px;top:300px;font:36px Arial}</style><div data-stage id="stage"><section data-slide class="slide is-active"><div class="x"><img alt="bad" src="data:image/png;base64,bad"></div><p class="y">COVERED TEXT</p><p class="bad">OUT OF STAGE</p><i data-hl data-target="#missing"></i></section></div>''')
        codes={e['kind'] for e in bad.evaluate(MEASURE)['errors']}
        check('negative fixture detects four defect classes',{'broken-image','image-text-overlap','safe-inset','unbound-highlight'}<=codes)
        check('no external dependencies',not req)
        check('no runtime errors',not errors)
        browser.close()
    print(json.dumps({'passed':sum(r['pass'] for r in results),'total':len(results),'checks':results},indent=2))
    return 0 if all(r['pass'] for r in results) else 1
if __name__=='__main__':raise SystemExit(main())
