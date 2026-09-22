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

def identifier(value: Any, where: str) -> str:
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ContractError(f'{where}: expected a lowercase kebab-case identifier')
    return value

class Registry:
    def __init__(self, root: str | Path | None = None):
        self.root = Path(root or Path(__file__).resolve().parents[1]).resolve()
        self.entries: dict[tuple[str,str],dict[str,Any]] = {}
        for family in (*FAMILIES, 'themes'):
            folder = self.root / ('themes' if family == 'themes' else f'modules/{family}')
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
        for family in (*FAMILIES, 'themes'):
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

    def list(self, family: str | None = None) -> list[dict]:
        return [copy.deepcopy(v) for (f,_),v in self.entries.items() if family is None or f == family]

    def get(self, family: str, mid: str) -> dict:
        try: return copy.deepcopy(self.entries[(family,mid)])
        except (KeyError,TypeError) as exc:
            raise ContractError(f'unknown {family} module: {mid!r}') from exc

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

    def catalog(self) -> dict:
        return {'schemaVersion':1,'modules':[{k:v for k,v in item.items() if not k.startswith('_')}
                  for item in self.list()]}
