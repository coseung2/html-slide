"""Discover reviewed repository modules; never import executable code from a deck."""
from __future__ import annotations
import copy
import json
import re
from pathlib import Path
from typing import Any

class ContractError(ValueError):
    """A specification or module violates a public engine contract."""

ID = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
FAMILIES = ('layouts', 'content', 'visuals', 'motion')
STYLE_FAMILIES = ('typography', 'palettes', 'dataviz')
ALL_FAMILIES = (*FAMILIES, 'themes', *STYLE_FAMILIES)

def identifier(value: Any, where: str) -> str:
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ContractError(f'{where}: expected a lowercase kebab-case identifier')
    return value

class Registry:
    def __init__(self, root: str | Path | None = None):
        self.root = Path(root or Path(__file__).resolve().parents[1]).resolve()
        self.entries: dict[tuple[str,str],dict[str,Any]] = {}
        for family in ALL_FAMILIES:
            if family == 'themes':
                folder = self.root / 'themes'
            elif family in STYLE_FAMILIES:
                folder = self.root / 'styles' / family
            else:
                folder = self.root / 'modules' / family
            for path in sorted(folder.glob('*/manifest.json')):
                try:
                    item = json.loads(path.read_text(encoding='utf-8'))
                except (ValueError, OSError) as exc:
                    raise ContractError(f'{path}: invalid manifest: {exc}') from exc
                if not isinstance(item, dict):
                    raise ContractError(f'{path}: manifest must be an object')
                mid = identifier(item.get('id'), str(path))
                if item.get('version') != 1 or item.get('type') != family:
                    raise ContractError(f'{path}: expected version=1 and type={family}')
                if mid != path.parent.name or (family,mid) in self.entries:
                    raise ContractError(f'{path}: directory/id mismatch or duplicate module')
                item['_dir'] = path.parent
                self.entries[(family,mid)] = item
        for family in ALL_FAMILIES:
            if not self.list(family):
                raise ContractError(f'registry is missing the {family} family')
        for layout in self.list('layouts'):
            if not isinstance(layout.get('slots'),dict) or not layout['slots']:
                raise ContractError(f"layout {layout['id']} needs named slots")
            template = self.resource(layout, 'template.html')
            for name,slot in layout['slots'].items():
                identifier(name,'slot')
                if '{{slot.'+name+'}}' not in template:
                    raise ContractError(f"{layout['id']}: missing slot {name} in template")
                if not isinstance(slot.get('max'),int) or slot['max'] < slot.get('min',0):
                    raise ContractError(f"{layout['id']}: invalid slot capacity")
        for item in self.list('content')+self.list('visuals'):
            if not isinstance(item.get('schema'),dict):
                raise ContractError(f"{item['id']}: data schema required")
        for item in self.list('motion'):
            if not isinstance(item.get('supports'),list) or not item['supports']:
                raise ContractError(f"{item['id']}: motion supports list required")
            phase_by=item.get('phaseBy')
            if phase_by is not None and (not isinstance(phase_by,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',phase_by)):
                raise ContractError(f"{item['id']}: phaseBy must name a data-list property")
        for item in self.list('typography'):
            css=self.resource(item,'style.css')
            if f'data-typography="{item["id"]}"' not in css:
                raise ContractError(f"{item['id']}: typography CSS selector does not match its id")
            if not item.get('languages') or not item.get('density'):
                raise ContractError(f"{item['id']}: typography languages and density metadata required")
            for token in ('font-body','font-heading','font-number'):
                if f'--{token}:' not in css:
                    raise ContractError(f"{item['id']}: missing typography token --{token}")
        for item in self.list('palettes'):
            css=self.resource(item,'style.css')
            if f'data-palette="{item["id"]}"' not in css:
                raise ContractError(f"{item['id']}: palette CSS selector does not match its id")
            for token in ('paper','ink','muted','accent','surface','line','positive','negative','warning'):
                if f'--{token}:' not in css:
                    raise ContractError(f"{item['id']}: missing palette token --{token}")
        for item in self.list('dataviz'):
            css=self.resource(item,'style.css')
            if f'data-dataviz="{item["id"]}"' not in css:
                raise ContractError(f"{item['id']}: dataviz CSS selector does not match its id")
            for n in range(1,7):
                if f'--viz-{n}:' not in css:
                    raise ContractError(f"{item['id']}: missing dataviz token --viz-{n}")

    def list(self, family: str | None = None) -> list[dict]:
        return [copy.deepcopy(v) for (f,_),v in self.entries.items() if family is None or f == family]

    def get(self, family: str, mid: str) -> dict:
        try: return copy.deepcopy(self.entries[(family,mid)])
        except (KeyError,TypeError) as exc:
            raise ContractError(f'unknown {family} registry entry: {mid!r}') from exc

    def block(self, mid: str) -> dict:
        matches=[v for (f,i),v in self.entries.items() if i==mid and f in ('content','visuals')]
        if len(matches)!=1: raise ContractError(f'unknown or ambiguous content/visual module: {mid!r}')
        return copy.deepcopy(matches[0])

    def resource(self, item: dict, name: str, optional: bool = False) -> str:
        base = Path(item['_dir']).resolve()
        path = (base / name).resolve()
        if not path.is_relative_to(base): raise ContractError('module resource escapes module directory')
        if optional and not path.exists(): return ''
        try: return path.read_text(encoding='utf-8')
        except OSError as exc: raise ContractError(f'missing module resource: {path}') from exc

    def search(self, *, family: str='layouts', intent: str='', topic: str='', density: str='medium',
               theme: str | None=None, recent: list[str] | None=None) -> list[dict]:
        if family in STYLE_FAMILIES:
            raise ContractError(f'use style_search for {family}')
        if theme: self.get('themes',theme)
        terms=set(re.findall(r'[\w-]+',(intent+' '+topic).lower()))
        results=[]
        for item in self.list(family):
            if theme and item.get('themes') and theme not in item['themes']: continue
            score=0; reasons=[]
            if intent in item.get('intents',[]): score+=100; reasons.append('intent match')
            hits=terms.intersection(set(item.get('tags',[])))
            if hits: score+=len(hits)*8; reasons.append('tags: '+', '.join(sorted(hits)))
            if density in item.get('density',['low','medium','high']): score+=10; reasons.append('density match')
            if item['id'] in (recent or [])[-2:]: score-=18; reasons.append('recent-layout penalty')
            results.append({'id':item['id'],'type':family,'score':score,'reasons':reasons})
        return sorted(results,key=lambda x:(-x['score'],x['id']))

    def style_search(self, family: str, *, theme: str, language: str='ko', topic: str='',
                     domain: str='', audience: str='', tone: list[str] | None=None,
                     density: str='medium') -> list[dict]:
        if family not in STYLE_FAMILIES:
            raise ContractError(f'unknown style family: {family}')
        theme_item=self.get('themes',theme)
        domain=domain.lower(); audience=audience.lower(); tone=[x.lower() for x in (tone or [])]
        context=set(re.findall(r'[\w-]+',' '.join([
            topic,domain,audience,' '.join(tone),' '.join(theme_item.get('tags',[]))
        ]).lower()))
        results=[]
        for item in self.list(family):
            languages=item.get('languages',['ko','en'])
            if family=='typography' and language not in languages: continue
            score=0; reasons=[]
            if theme in item.get('themes',[]): score+=30; reasons.append('theme recommendation')
            if domain and domain in item.get('domains',[]): score+=18; reasons.append('domain match')
            if audience and audience in item.get('audiences',[]): score+=16; reasons.append('audience match')
            tone_hits=set(tone).intersection(set(item.get('tones',[])))
            if tone_hits: score+=10*len(tone_hits); reasons.append('tone: '+', '.join(sorted(tone_hits)))
            tag_hits=context.intersection(set(item.get('tags',[])))
            if tag_hits: score+=6*len(tag_hits); reasons.append('tags: '+', '.join(sorted(tag_hits)))
            if density in item.get('density',['low','medium','high']): score+=8; reasons.append('density match')
            if family=='typography' and language in languages: score+=6; reasons.append('language support')
            results.append({'id':item['id'],'type':family,'score':score,'reasons':reasons})
        if not results: raise ContractError(f'no compatible {family} style pack')
        return sorted(results,key=lambda x:(-x['score'],x['id']))

    def catalog(self) -> dict:
        clean=lambda item:{k:v for k,v in item.items() if not k.startswith('_')}
        return {'schemaVersion':1,
                'modules':[clean(item) for family in (*FAMILIES,'themes') for item in self.list(family)],
                'styles':[clean(item) for family in STYLE_FAMILIES for item in self.list(family)]}
