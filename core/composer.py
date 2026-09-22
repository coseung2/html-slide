"""Compile a validated deck into a self-contained, deterministic HTML artifact."""
from __future__ import annotations
import copy
import json
import re
from pathlib import Path
from .registry import Registry, ContractError
from .validation import validate_deck
from .renderers import esc, render_block

STYLE_FAMILIES={'typography':'typography','palette':'palettes','dataviz':'dataviz'}


def assign_slots(layout: dict, blocks: list[dict]) -> dict[str,list[dict]] | None:
    """Small constrained search, not greedy filling: honor every required slot."""
    slots=layout['slots']; assigned={name:[] for name in slots}
    def place(i):
        if i==len(blocks): return all(len(assigned[n])>=s.get('min',0) for n,s in slots.items())
        b=blocks[i]
        candidates=[b['slot']] if 'slot' in b else list(slots)
        for name in candidates:
            if name not in slots: continue
            rule=slots[name]
            if b['module'] not in rule['accepts'] or len(assigned[name])>=rule['max']: continue
            assigned[name].append(b)
            if place(i+1): return True
            assigned[name].pop()
        return False
    return assigned if place(0) else None


def _deck_density(spec: dict) -> str:
    explicit=spec.get('style',{}).get('signals',{}).get('density')
    if explicit: return explicit
    values=[s.get('density','medium') for s in spec.get('slides',[])]
    if not values: return 'medium'
    score=sum({'low':0,'medium':1,'high':2}[x] for x in values)/len(values)
    return 'low' if score < .5 else 'high' if score > 1.5 else 'medium'


def resolve_styles(spec: dict, registry: Registry) -> dict:
    style=spec.get('style',{}); signals=style.get('signals',{})
    context={
        'theme':spec['theme'],'language':spec.get('language','ko'),'topic':spec.get('topic',''),
        'domain':signals.get('domain',''),'audience':signals.get('audience',''),
        'tone':signals.get('tone',[]),'density':_deck_density(spec),
    }
    selected={}
    for key,family in STYLE_FAMILIES.items():
        requested=style.get(key,'auto')
        if requested!='auto':
            registry.get(family,requested)
            selected[key]={'id':requested,'mode':'explicit','score':None,
                           'reasons':['explicit style override'],'alternatives':[]}
            continue
        ranked=registry.style_search(family,**context)
        winner=ranked[0]
        selected[key]={**winner,'mode':'auto','alternatives':ranked[1:4]}
    return selected


def plan_deck(spec: dict, registry: Registry | None = None) -> dict:
    registry=registry or Registry()
    validate_deck(spec,registry)
    plan={'schemaVersion':1,'title':spec['title'],'theme':spec['theme'],
          'styles':resolve_styles(spec,registry),'slides':[],'warnings':[]}
    recent=[]
    for source in spec['slides']:
        slide=copy.deepcopy(source); theme=slide.get('theme',spec['theme'])
        explicit=slide.get('layout','auto')!='auto'
        candidates=([{'id':slide['layout'],'score':None,'reasons':['explicit layout']}] if explicit else
          registry.search(intent=slide['intent'],topic=spec.get('topic',''),density=slide.get('density','medium'),theme=theme,recent=recent))
        chosen=None; rejected=[]
        for candidate in candidates:
            layout=registry.get('layouts',candidate['id'])
            slots=assign_slots(layout,slide['blocks'])
            if slots is not None:
                chosen=candidate; break
            rejected.append({'id':candidate['id'],'reason':'slot type/capacity/required-slot mismatch'})
        if chosen is None:
            raise ContractError(f"{slide['id']}: no compatible layout; split the slide or choose matching slots. Rejected: "+', '.join(r['id'] for r in rejected))
        if recent[-2:]==[chosen['id'],chosen['id']]:
            plan['warnings'].append(f"{slide['id']}: layout {chosen['id']} repeats three times; review visual rhythm")
        slide['layout']=chosen['id']; slide['theme']=theme
        slide['slots']={k:[b['id'] for b in v] for k,v in slots.items()}
        slide['selection']={**chosen,'rejected':rejected}
        phase=0
        for effect in slide.get('motion',[]):
            effect['startStep']=phase+1
            target=next(b for b in slide['blocks'] if b['id']==effect['target'])
            phase+=len(target['data']['items']) if effect['module']=='sequence-step' else 1
            effect['endStep']=phase
        slide['steps']=phase
        plan['slides'].append(slide); recent.append(slide['layout'])
    return plan


def json_script(value) -> str:
    return json.dumps(value,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026').replace('\u2028','\\u2028').replace('\u2029','\\u2029')


def build_deck(spec: dict, registry: Registry | None = None, *, asset_root: str | Path = '.', font: str | Path | None = None) -> tuple[str,dict]:
    registry=registry or Registry(); plan=plan_deck(spec,registry)
    asset_root=Path(asset_root).resolve()
    css=[(registry.root/'core/stage.css').read_text(encoding='utf-8'),(registry.root/'core/shell.css').read_text(encoding='utf-8')]
    used=set(); used_themes={spec['theme']}; slides=[]
    for slide in plan['slides']:
        layout=registry.get('layouts',slide['layout'])
        used.add(('layouts',slide['layout'])); used_themes.add(slide['theme'])
        fragments={}
        for block in slide['blocks']:
            module=registry.block(block['module']); used.add((module['type'],module['id']))
            dom_id=f"s-{slide['id']}--{block['id']}"
            fragment=render_block(registry,block,asset_root,dom_id)
            effect=next((m for m in slide.get('motion',[]) if m['target']==block['id']),None)
            if effect:
                used.add(('motion',effect['module']))
                attributes=f' data-motion="{effect["module"]}" data-start-step="{effect["startStep"]}" data-end-step="{effect["endStep"]}" data-step="{effect["endStep"]}"'
                fragment=fragment.replace('<article ', '<article'+attributes+' ',1)
                if effect['module']=='focus':
                    ring=f'<span class="focus-ring" data-hl data-target="#{dom_id}" data-step="{effect["endStep"]}" aria-hidden="true"></span>'
                    fragment=fragment.replace('</article>',ring+'</article>')
            fragments[block['id']]=fragment
        copy=f'<h2>{esc(slide["title"])}</h2>'
        if slide.get('summary'): copy+=f'<p>{esc(slide["summary"])}</p>'
        replacements={'copy':copy}
        for name,ids in slide['slots'].items(): replacements['slot.'+name]=''.join(fragments[bid] for bid in ids)
        template=registry.resource(layout,'template.html')
        def substitute(m):
            if m[1] not in replacements: raise ContractError(f"{layout['id']}: unresolved placeholder {m[1]}")
            return replacements[m[1]]
        scene=re.sub(r'\{\{([\w.-]+)\}\}',substitute,template)
        slides.append(f'<section data-slide="{slide["id"]}" data-title="{esc(slide["title"])}" data-start="0" data-steps="{slide["steps"]}" data-theme="{slide["theme"]}" class="layout-{slide["layout"]}" aria-label="{esc(slide["title"])}"><div class="scene">{scene}</div></section>')
    for family,mid in sorted(used):
        entry=registry.get(family,mid)
        css.append(registry.resource(entry,'styles.css',optional=True))
    for theme_id in sorted(used_themes):
        css.append(registry.resource(registry.get('themes',theme_id),'theme.css'))
    for key,family in STYLE_FAMILIES.items():
        entry=registry.get(family,plan['styles'][key]['id'])
        css.append(registry.resource(entry,'style.css'))
    if font is not None:
        import base64
        path=Path(font)
        if path.suffix.lower()!='.woff2' or path.read_bytes()[:4]!=b'wOF2': raise ContractError('font must be a valid WOFF2 font file')
        data=base64.b64encode(path.read_bytes()).decode('ascii')
        css.insert(0,"@font-face{font-family:'HTMLSlide Embedded';src:url(data:font/woff2;base64,"+data+") format('woff2');font-weight:100 900;font-display:block}body{--font-custom:'HTMLSlide Embedded'}")
    else:
        plan['warnings'].append('Font not embedded: system-font metrics vary. Use --font and re-run browser QA for final projection.')
    runtime=(registry.root/'core/runtime.js').read_text(encoding='utf-8')
    if '</script' in runtime.lower(): raise ContractError('unsafe script closing sequence in runtime')
    # Keep selection provenance, but avoid duplicating embedded media and content data.
    public_plan={**plan,'slides':[{k:v for k,v in slide.items() if k not in ('blocks','motion')} for slide in plan['slides']]}
    lang=spec.get('language','ko'); mode=spec.get('mode','live')
    typography=plan['styles']['typography']['id']; palette=plan['styles']['palette']['id']; dataviz=plan['styles']['dataviz']['id']
    html=f'''<!doctype html>
<html lang="{lang}" data-engine="html-slide-modular-v1">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(spec['title'])}</title>
<style>{''.join(css)}</style></head>
<body data-theme="{spec['theme']}" data-typography="{typography}" data-palette="{palette}" data-dataviz="{dataviz}" data-mode="{mode}"><main data-stage aria-label="{esc(spec['title'])}">{''.join(slides)}</main>
<script type="application/json" id="deck-plan">{json_script(public_plan)}</script>
<script>{runtime}</script></body></html>'''
    return html,plan
