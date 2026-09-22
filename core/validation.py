"""Fail closed on invalid data, incompatible layouts, and unsafe asset paths."""
from __future__ import annotations
import json
import math
from pathlib import Path
from urllib.parse import urlparse
from .registry import ContractError, identifier

# jsonschema is the only build-time dependency; rendering needs no network.
def validate_schema(value, schema: dict, where: str) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise ContractError('Install the build dependency: pip install -r requirements-modular.txt') from exc
    Draft202012Validator.check_schema(schema)
    errors=sorted(Draft202012Validator(schema).iter_errors(value),key=lambda e:str(list(e.path)))
    if errors:
        e=errors[0]; path='.'.join(map(str,e.absolute_path))
        raise ContractError(f'{where}{"."+path if path else ""}: {e.message}')

def finite(value, where='number') -> float:
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ContractError(f'{where}: a finite number is required')
    return value

def safe_url(value: str) -> str:
    u=urlparse(value)
    if u.scheme not in ('https','http') or not u.netloc or u.username or u.password:
        raise ContractError('source links must be HTTP(S) URLs without credentials')
    if any(ord(c)<32 for c in value): raise ContractError('control character in source URL')
    return value

def load_spec(path: str | Path) -> dict:
    path=Path(path)
    try: return json.loads(path.read_text(encoding='utf-8'),parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
    except (OSError,ValueError) as exc: raise ContractError(f'{path}: invalid JSON: {exc}') from exc

def validate_deck(spec: dict, registry) -> None:
    schema=json.loads((registry.root/'core/deck.schema.json').read_text(encoding='utf-8'))
    validate_schema(spec,schema,'deck')
    registry.get('themes',spec['theme'])
    style=spec.get('style',{})
    for key,family in (('typography','typography'),('palette','palettes'),('dataviz','dataviz')):
        value=style.get(key,'auto')
        if value!='auto': registry.get(family,value)
    slide_ids=set()
    for slide in spec['slides']:
        sid=identifier(slide['id'],'slide.id')
        if sid in slide_ids: raise ContractError(f'duplicate slide id: {sid}')
        slide_ids.add(sid)
        seen=set()
        for block in slide['blocks']:
            bid=identifier(block['id'],sid+'.block.id')
            if bid in seen: raise ContractError(f'{sid}: duplicate block id: {bid}')
            seen.add(bid)
            module=registry.block(block['module'])
            validate_schema(block['data'],module['schema'],f'{sid}.{bid}')
            # jsonschema considers IEEE infinity a number; charts must not.
            def walk(v):
                if isinstance(v,float): finite(v,f'{sid}.{bid}')
                elif isinstance(v,dict):
                    for x in v.values(): walk(x)
                elif isinstance(v,list):
                    for x in v: walk(x)
            walk(block['data'])
        for source in slide.get('sources',[]): safe_url(source['url'])
        if 'theme' in slide: registry.get('themes',slide['theme'])
        for effect in slide.get('motion',[]):
            motion=registry.get('motion',effect['module'])
            if effect['target'] not in seen: raise ContractError(f'{sid}: motion target does not exist')
            target=next(b for b in slide['blocks'] if b['id']==effect['target'])
            if target['module'] not in motion.get('supports',[]):
                raise ContractError(f"{sid}: {effect['module']} does not support {target['module']}")
            if slide['intent'] not in motion.get('intents',[]):
                raise ContractError(f"{sid}: {effect['module']} is incompatible with intent {slide['intent']}")
        targets=[m['target'] for m in slide.get('motion',[])]
        if len(targets)!=len(set(targets)): raise ContractError(f'{sid}: one motion per target only')
