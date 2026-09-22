#!/usr/bin/env python3
"""Validate a modular HTML deck, then export identical PNG frames to PDF and PPTX."""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from verify_modular import verify, launch_options


def export(source: Path, out: Path) -> dict:
    from playwright.sync_api import sync_playwright
    source=source.resolve();out=out.resolve()
    if not source.is_file() or source.suffix.lower() not in ('.html','.htm'):
        raise ValueError('expected an existing HTML file')
    if not shutil.which('node'):
        raise ValueError('Node.js and pptxgenjs are required; run npm install')
    helper=Path(__file__).with_name('frames_to_pptx.cjs')
    subprocess.run(['node',str(helper),'--check'],check=True,capture_output=True,text=True)
    raw=source.read_text(encoding='utf-8')
    out.mkdir(parents=True,exist_ok=True)
    report=verify(source,out/'qa')
    if report['errors']:raise ValueError('QA failed; export stopped. See qa/report.json')
    frames=out/'frames';frames.mkdir(exist_ok=True)
    records=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(**launch_options())
        try:
            ctx=browser.new_context(viewport={'width':1920,'height':1080},device_scale_factor=1,reduced_motion='reduce')
            page=ctx.new_page();page.set_content(raw,wait_until='load');page.evaluate('document.fonts.ready')
            if not page.evaluate('Boolean(window.__deckEngine)'):
                raise ValueError('not a modular deck; use tools/export_deck.py for legacy decks')
            page.evaluate("__deckShell.setStatic(true);document.documentElement.classList.add('deck-capture')")
            plan=page.locator('#deck-plan').text_content()
            plan=json.loads(plan) if plan else {}
            for i in range(report['slides']):
                page.evaluate('i=>__deckGoto(i)',i);page.wait_for_timeout(30)
                frame=frames/f'slide-{i+1:03}.png';page.screenshot(path=str(frame),animations='disabled')
                title=page.locator('[data-slide].is-active').get_attribute('data-title')
                records.append({'index':i+1,'title':title,'frame':str(frame),'sources':plan.get('slides',[{}]*report['slides'])[i].get('sources',[])})
            ctx.close()
            images=''.join('<section><img src="data:image/png;base64,'+base64.b64encode(Path(x['frame']).read_bytes()).decode()+'"></section>' for x in records)
            printable='<!doctype html><style>@page{size:13.33333333in 7.5in;margin:0}html,body{margin:0;padding:0}section{width:13.33333333in;height:7.5in;break-after:page}section:last-child{break-after:auto}img{display:block;width:100%;height:100%}</style>'+images
            page=browser.new_page();page.set_content(printable,wait_until='load')
            page.pdf(path=str(out/f'{source.stem}.pdf'),print_background=True,prefer_css_page_size=True)
        finally:browser.close()
    manifest={'source':source.name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'stage':[1920,1080],'slides':records,'slide_count':len(records),'editable':False,'qa':'qa/report.json'}
    temp=out/'manifest.json';temp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    subprocess.run(['node',str(helper),str(temp),str(out/f'{source.stem}.pptx')],check=True)
    return manifest


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('html',type=Path);ap.add_argument('--out',type=Path,default=Path('dist/export'))
    a=ap.parse_args()
    try:
        result=export(a.html,a.out);print(f"EXPORT PASS: {result['slide_count']} slides -> {a.out}");return 0
    except (ValueError,OSError,subprocess.CalledProcessError,ImportError) as exc:
        print(f'EXPORT FAIL: {exc}',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
