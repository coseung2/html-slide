"""Escaped HTML renderers. Local raster media are embedded, not hotlinked."""
from __future__ import annotations
import base64
import html
import mimetypes
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
    elif kind=='image':
        uri=media_data(data['src'],asset_root)
        fit='contain' if module['id']=='logo' else data.get('fit','cover')
        body=f'<img src="{uri}" alt="{esc(data["alt"])}" style="object-fit:{fit}"/>'
    elif kind=='process':
        body='<div class="process">'+''.join(f'<div class="process-node" data-sequence-item><strong>{i+1:02d}</strong><p>{esc(item)}</p></div>' for i,item in enumerate(data['items']))+'</div>'
    else: raise ContractError(f'unsupported renderer: {kind}')
    classes=f'module module-{module["id"]}'
    return f'<article id="{dom_id}" class="{classes}" data-module="{module["id"]}" data-qa-box>{body}</article>'
