"""Escaped HTML renderers. Local raster media are embedded, not hotlinked."""
from __future__ import annotations
import base64
import html
import mimetypes
import math
import re
from pathlib import Path
from .registry import ContractError
from .validation import finite

def esc(value) -> str: return html.escape(str(value),quote=True)
def fmt(value) -> str:
    finite(value)
    return f'{value:,.4f}'.rstrip('0').rstrip('.') if isinstance(value,float) else f'{value:,}'

def media_data(src: str, root: Path) -> str:
    # Restrict both decoded MIME and local file paths. SVG is deliberately not accepted.
    if src.startswith('data:'):
        m=re.fullmatch(r'data:(image/(?:png|jpeg|webp|gif));base64,([A-Za-z0-9+/=\r\n]+)',src)
        if not m: raise ContractError('only base64 PNG/JPEG/WebP/GIF image data are accepted')
        mime=m[1]
        try: data=base64.b64decode(m[2],validate=True)
        except ValueError as exc: raise ContractError('invalid base64 image') from exc
    else:
        path=(root/src).resolve()
        if not path.is_relative_to(root.resolve()): raise ContractError('asset path escapes asset root')
        if not path.is_file(): raise ContractError(f'missing image asset: {src}')
        if path.stat().st_size>8*1024*1024: raise ContractError('image exceeds 8 MiB')
        data=path.read_bytes(); mime=mimetypes.guess_type(path.name)[0]
    if not data or len(data)>8*1024*1024: raise ContractError('empty or oversized image asset')
    detected=('image/png' if data.startswith(b'\x89PNG\r\n\x1a\n') else
              'image/jpeg' if data.startswith(b'\xff\xd8\xff') else
              'image/gif' if data[:6] in (b'GIF87a',b'GIF89a') else
              'image/webp' if data[:4]==b'RIFF' and data[8:12]==b'WEBP' else None)
    if detected!=mime or detected is None: raise ContractError('image MIME/signature mismatch')
    return f'data:{mime};base64,'+base64.b64encode(data).decode('ascii')

def template_render(registry,module,data):
    template=registry.resource(module,'template.html')
    def replace(m):
        key=m[1]
        if key not in data: raise ContractError(f"{module['id']}: missing template value: {key}")
        if isinstance(data[key],(dict,list)): raise ContractError('template values must be scalars')
        return esc(data[key])
    return re.sub(r'\{\{([a-zA-Z][\w]*)\}\}',replace,template)

def render_block(registry, block, asset_root: Path, dom_id: str) -> str:
    module=registry.block(block['module']); data=block['data']; kind=module.get('renderer','template')
    if kind=='template': body=template_render(registry,module,data)
    elif kind=='metric':
        body=f'<p class="module-label">{esc(data["label"])}</p><p class="metric-value"><span data-number="{data["value"]}">{fmt(data["value"])}</span><span class="metric-unit">{esc(data.get("unit",""))}</span></p>'
        if data.get('detail'): body+=f'<p class="module-detail">{esc(data["detail"])}</p>'
    elif kind in ('list','timeline'):
        tag='ol' if kind=='timeline' else 'ul'
        body=f'<{tag} class="module-{kind}">'+''.join(f'<li data-sequence-item><span class="sequence-index">{i+1:02d}</span><span>{esc(item)}</span></li>' for i,item in enumerate(data['items']))+f'</{tag}>'
    elif kind=='ranking':
        body='<table class="ranking"><thead><tr><th scope="col">'+esc(data.get('label','Item'))+'</th><th scope="col">'+esc(data.get('valueLabel','Value'))+'</th></tr></thead><tbody>'
        for i,row in enumerate(data['items']):
            body+=f'<tr data-sequence-item><th scope="row"><span class="rank-index">{i+1:02d}</span>{esc(row["label"])}</th><td>{fmt(row["value"])}</td></tr>'
        body+='</tbody></table>'
    elif kind=='score':
        body=f'<div class="score-teams"><span>{esc(data["home"])}</span><span>{esc(data["away"])}</span></div><div class="score-value"><span>{data["homeScore"]}</span><span aria-hidden="true">:</span><span>{data["awayScore"]}</span></div>'
        if data.get('detail'): body+=f'<p class="module-detail">{esc(data["detail"])}</p>'
    elif kind=='bar-chart':
        vals=[finite(x['value']) for x in data['items']]; maximum=max(vals) or 1
        body='<div class="bar-chart" role="img" aria-label="'+esc(data['label'])+'">'
        for row in data['items']:
            width=100*row['value']/maximum
            body+=f'<div class="bar-row"><span>{esc(row["label"])}</span><div class="bar-track"><div class="bar-fill" style="width:{width:.5f}%"></div></div><strong>{fmt(row["value"])}</strong></div>'
        body+='</div>'
    elif kind=='line-chart':
        values=[finite(x['value']) for x in data['items']]; low=min(0,min(values)); high=max(values)
        span=(high-low) or 1; points=[(160+i*680/(len(values)-1),340-(v-low)/span*280) for i,v in enumerate(values)]
        coords=' '.join(f'{x:.3f},{y:.3f}' for x,y in points)
        zero=340-(0-low)/span*280
        body=f'<svg class="line-chart" viewBox="0 0 1000 440" role="img" aria-label="{esc(data["label"])}"><line class="chart-axis" x1="40" y1="{zero:.3f}" x2="960" y2="{zero:.3f}"/><polyline class="chart-line" points="{coords}"/>'
        for row,(x,y) in zip(data['items'],points):
            body+=f'<circle class="chart-dot" cx="{x:.3f}" cy="{y:.3f}" r="7"/><text x="{x:.3f}" y="{y-22:.3f}" text-anchor="middle">{fmt(row["value"])}</text><text x="{x:.3f}" y="407" text-anchor="middle">{esc(row["label"])}</text>'
        body+='</svg><table class="sr-only"><caption>'+esc(data['label'])+'</caption><tbody>'+''.join(f'<tr><th>{esc(r["label"])}</th><td>{fmt(r["value"])}</td></tr>' for r in data['items'])+'</tbody></table>'
    elif kind=='character-callout':
        uri=media_data(data['src'],asset_root)
        fit=data.get('fit','contain'); align=data.get('align','left')
        role=f'<p class="character-callout__role">{esc(data["role"])}</p>' if data.get('role') else ''
        caption=f'<p class="character-callout__caption">{esc(data["caption"])}</p>' if data.get('caption') else ''
        body=(f'<figure class="character-callout character-callout--{align}">'
              f'<div class="character-callout__portrait"><img src="{uri}" alt="{esc(data["alt"])}" style="object-fit:{fit}"/></div>'
              f'<figcaption class="character-callout__copy"><p class="character-callout__name">{esc(data["name"])}</p>{role}'
              f'<div class="character-callout__speech" data-speech-bubble data-speech-kind="{esc(data["speechKind"])}">'
              f'<span class="character-callout__speech-label">{esc(data["speechLabel"])}</span>'
              f'<p>{esc(data["speech"])}</p></div>{caption}</figcaption></figure>')
    elif kind=='map-route':
        uri=media_data(data['src'],asset_root)
        fit='meet' if data.get('fit','contain')=='contain' else 'slice'
        route_parts=[]; accessible=[]
        for i,row in enumerate(data['routes']):
            sx=finite(row['start']['x'],f'{dom_id}.route[{i}].start.x')*10
            sy=finite(row['start']['y'],f'{dom_id}.route[{i}].start.y')*6
            ex=finite(row['end']['x'],f'{dom_id}.route[{i}].end.x')*10
            ey=finite(row['end']['y'],f'{dom_id}.route[{i}].end.y')*6
            arc=finite(row.get('arcHeight',18),f'{dom_id}.route[{i}].arcHeight')*6
            cy=max(30,min(570,(sy+ey)/2 + (arc if row.get('arcDirection','up')=='down' else -arc)))
            cx=(sx+ex)/2
            path=f'M {sx:.3f} {sy:.3f} Q {cx:.3f} {cy:.3f} {ex:.3f} {ey:.3f}'
            angle=math.degrees(math.atan2(ey-cy,ex-cx))
            tone=row.get('tone','accent')
            def label_at(x,y):
                anchor='end' if x>820 else 'start'
                dx=-18 if anchor=='end' else 18
                yy=y-18 if y>70 else y+36
                return anchor,x+dx,yy
            sa,sxtext,sytext=label_at(sx,sy); ea,extext,eytext=label_at(ex,ey)
            route_label=''
            if row.get('label'):
                ly=max(40,min(560,cy-24))
                route_label=f'<text class="map-route__route-label" x="{cx:.3f}" y="{ly:.3f}" text-anchor="middle">{esc(row["label"])}</text>'
            traveler=''
            if row.get('traveler'):
                tr=row['traveler']; truri=media_data(tr['src'],asset_root)
                trlabel=f'<text class="map-route__traveler-label" x="0" y="-52" text-anchor="middle">{esc(tr["label"])}</text>' if tr.get('label') else ''
                traveler=(f'<g class="map-route__traveler" data-route-traveler transform="translate({ex:.3f} {ey:.3f}) scale(1)">'
                          f'<image href="{truri}" x="-38" y="-38" width="76" height="76" preserveAspectRatio="xMidYMid meet"/>'
                          f'{trlabel}</g>')
            route_parts.append(
                f'<g class="map-route__item map-route__item--{tone}" data-route-item>'
                f'<path class="map-route__path" data-route-path d="{path}" pathLength="1"/>'
                f'<circle class="map-route__marker map-route__marker--start" cx="{sx:.3f}" cy="{sy:.3f}" r="10"/>'
                f'<circle class="map-route__marker map-route__marker--end" cx="{ex:.3f}" cy="{ey:.3f}" r="12"/>'
                f'<path class="map-route__arrow" d="M -18 -12 L 0 0 L -18 12 Z" transform="translate({ex:.3f} {ey:.3f}) rotate({angle:.3f})"/>'
                f'<text class="map-route__place" x="{sxtext:.3f}" y="{sytext:.3f}" text-anchor="{sa}">{esc(row["start"]["label"])}</text>'
                f'<text class="map-route__place" x="{extext:.3f}" y="{eytext:.3f}" text-anchor="{ea}">{esc(row["end"]["label"])}</text>'
                f'{route_label}{traveler}</g>')
            accessible.append(f'<li>{esc(row.get("label","Route"))}: {esc(row["start"]["label"])} to {esc(row["end"]["label"])}</li>')
        body=(f'<div class="map-route"><svg class="map-route__svg" viewBox="0 0 1000 600" role="img" aria-label="{esc(data["alt"])}">'
              f'<image class="map-route__map" href="{uri}" x="0" y="0" width="1000" height="600" preserveAspectRatio="xMidYMid {fit}"/>'
              f'<rect class="map-route__scrim" x="0" y="0" width="1000" height="600"/>'
              f'{"".join(route_parts)}</svg><ol class="sr-only">{"".join(accessible)}</ol></div>')
    elif kind=='image':
        uri=media_data(data['src'],asset_root)
        fit='contain' if module['id']=='logo' else data.get('fit','cover')
        body=f'<img src="{uri}" alt="{esc(data["alt"])}" style="object-fit:{fit}"/>'
    elif kind=='process':
        body='<div class="process">'+''.join(f'<div class="process-node" data-sequence-item><strong>{i+1:02d}</strong><p>{esc(item)}</p></div>' for i,item in enumerate(data['items']))+'</div>'
    else: raise ContractError(f'unsupported renderer: {kind}')
    classes=f'module module-{module["id"]}'
    return f'<article id="{dom_id}" class="{classes}" data-module="{module["id"]}" data-qa-box>{body}</article>'
