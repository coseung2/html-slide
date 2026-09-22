#!/usr/bin/env python3
"""Build, inspect, and validate AI-authored module compositions."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Registry, plan_deck, build_deck
from core.registry import ContractError, identifier, STYLE_FAMILIES
from core.validation import load_spec

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('catalog')
    search=commands.add_parser('search');search.add_argument('--type',default='layouts',choices=['layouts','content','visuals','motion','themes','typography','palette','palettes','dataviz'])
    search.add_argument('--intent',default='');search.add_argument('--topic',default='');search.add_argument('--theme');search.add_argument('--density',default='medium',choices=['low','medium','high'])
    search.add_argument('--language',default='ko',choices=['ko','en']);search.add_argument('--domain',default='');search.add_argument('--audience',default='');search.add_argument('--tone',action='append',default=[])
    init=commands.add_parser('init');init.add_argument('--preset',required=True);init.add_argument('--out',type=Path,required=True)
    for name in ('plan','build'):
        p=commands.add_parser(name);p.add_argument('spec',type=Path);p.add_argument('--out',type=Path);p.add_argument('--theme');p.add_argument('--font',type=Path);p.add_argument('--asset-root',type=Path)
        p.add_argument('--typography');p.add_argument('--palette');p.add_argument('--dataviz')
    args=parser.parse_args(argv)
    try:
        registry=Registry()
        if args.command=='catalog': result=registry.catalog()
        elif args.command=='search':
            family='palettes' if args.type=='palette' else args.type
            if family in STYLE_FAMILIES:
                if not args.theme: raise ContractError('--theme is required when searching style packs')
                result=registry.style_search(family,theme=args.theme,language=args.language,topic=args.topic,domain=args.domain,audience=args.audience,tone=args.tone,density=args.density)
            else: result=registry.search(family=family,intent=args.intent,topic=args.topic,density=args.density,theme=args.theme)
        elif args.command=='init':
            identifier(args.preset,'preset')
            result=load_spec(registry.root/'presets'/f'{args.preset}.json')
            plan_deck(result,registry)
            args.out.parent.mkdir(parents=True,exist_ok=True)
            args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print(f'Created {args.out}');return 0
        else:
            spec=load_spec(args.spec)
            if args.theme: spec['theme']=args.theme
            style=spec.setdefault('style',{})
            for key in ('typography','palette','dataviz'):
                value=getattr(args,key,None)
                if value: style[key]=value
            if args.command=='plan': result=plan_deck(spec,registry)
            else:
                html,result=build_deck(spec,registry,asset_root=args.asset_root or args.spec.parent,font=args.font)
                out=args.out or args.spec.with_suffix('.html')
                if out.resolve()==args.spec.resolve(): raise ContractError('HTML output may not overwrite the source specification')
                if out.suffix.lower() not in ('.html','.htm'): raise ContractError('build output must be an HTML file')
                out.parent.mkdir(parents=True,exist_ok=True);out.write_text(html,encoding='utf-8')
                out.with_suffix('.plan.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                print(f'Built {out}: {len(result["slides"])} slides; {len(result["warnings"])} review warnings')
                for warning in result['warnings']:print('REVIEW:',warning)
                return 0
        text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
        if getattr(args,'out',None):
            args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(text,encoding='utf-8')
        else:print(text,end='')
        return 0
    except (ContractError,OSError,ValueError) as exc:
        print(f'COMPOSE FAIL: {exc}',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
