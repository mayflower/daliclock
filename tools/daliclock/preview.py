"""Development-only rendering of the very same short lines exported to WFF."""

import json
from .geometry import interpolate
from .animation import ANIMATION, eased_progress

TRANSITIONS = [(i, (i + 1) % 10) for i in range(10)] + [(5, 0), (2, 0), (8, 1)]


def lines_svg(sampled, points, color='#fff'):
    return ''.join(f'<line x1="{points[a][0]:.4f}" y1="{points[a][1]:.4f}" '
                   f'x2="{points[b][0]:.4f}" y2="{points[b][1]:.4f}" '
                   f'stroke="{color}" stroke-width="{points[a][2] + points[b][2]:.4f}" stroke-linecap="round"/>'
                   for a, b in sampled.edges)


def digit_svg(sampled, points, pixels=None):
    w, h = sampled.box
    pw, ph = pixels or (w, h)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{pw}" height="{ph}" '
            f'viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="black"/>'
            + lines_svg(sampled, points) + '</svg>')


def overview(sampled):
    w, h = sampled.box
    cell_w, cell_h = w + 28, h + 30
    width, height = cell_w * 6, cell_h * (len(TRANSITIONS) + 2)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
             f'viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="#08090b"/>']
    for digit in range(10):
        x, y = (digit % 5) * cell_w + cell_w, (digit // 5) * cell_h
        parts += [f'<g transform="translate({x},{y})">',
                  f'<text x="0" y="16" fill="#9faabd" font-size="12">{digit}</text>',
                  f'<g transform="translate(0,22)">{lines_svg(sampled, sampled.points[str(digit)])}</g></g>']
    for row, (a, b) in enumerate(TRANSITIONS, 2):
        y = row * cell_h
        parts.append(f'<text x="12" y="{y + h / 2}" fill="#9faabd" font-size="16">{a} to {b}</text>')
        for col, u in enumerate((0, .25, .5, .75, 1), 1):
            parts += [f'<g transform="translate({col * cell_w},{y})">',
                      f'<text y="16" fill="#9faabd" font-size="12">{u:g}</text>',
                      '<g transform="translate(0,22)">',
                      lines_svg(sampled, interpolate(sampled, a, b, eased_progress(u))), '</g></g>']
    return ''.join(parts) + '</svg>'


def player(sampled):
    data = json.dumps({'points': sampled.points, 'edges': sampled.edges,
                       'box': sampled.box, 'animation': ANIMATION}, separators=(',', ':'))
    return '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Daliclock · geometry preview</title><style>
body{background:#101216;color:#e5e9ef;font:16px system-ui;max-width:840px;margin:40px auto;padding:20px}
label,button{margin-right:20px}select,button,input{font:inherit;accent-color:#99f2bb}
svg{display:block;background:black;width:240px;height:384px;margin:30px auto;border-radius:12px}
input{width:100%}small{color:#a8b2c0}a{color:#99f2bb}
</style><h1>Daliclock</h1><p>Shared-line geometry preview</p>
<p><small>Development preview, not the Wear OS renderer. Viscous cubic-Bezier 650 ms morphs with a slow start and smooth settling at the exact target.</small></p>
<label>From <select id="from"></select></label><label>To <select id="to"></select></label>
<button id="play">Play</button><label><input id="nodes" type="checkbox" style="width:auto"> Nodes</label>
<svg id="digit" role="img" aria-label="Morph preview"></svg>
<label>Progress <output id="value">0</output><input id="progress" type="range" min="0" max="1" step=".001" value="0"></label>
<p><a href="overview.svg">All digits and intermediate forms</a></p>
<script>const data=DATA;
const from=document.querySelector('#from'),to=document.querySelector('#to'),range=document.querySelector('#progress'),
svg=document.querySelector('#digit'),nodes=document.querySelector('#nodes');
for(let d=0;d<10;d++){from.add(new Option(d,d));to.add(new Option(d,d));}to.value=1;
svg.setAttribute('viewBox',`0 0 ${data.box.join(' ')}`);
let animation=0;
function ease(x){if(x<=0||x>=1)return x;
const [x1,y1,x2,y2]=data.animation.controls;
const b=(t,a,c)=>3*(1-t)*(1-t)*t*a+3*(1-t)*t*t*c+t*t*t;
let lo=0,hi=1;for(let i=0;i<40;i++){const t=(lo+hi)/2;if(b(t,x1,x2)<x)lo=t;else hi=t;}
return b((lo+hi)/2,y1,y2);}
function draw(){const u=ease(Number(range.value)),a=data.points[from.value],b=data.points[to.value],p={};
for(const id in a)p[id]=a[id].map((x,j)=>(1-u)*x+u*b[id][j]);
svg.innerHTML=data.edges.map(([a,b])=>`<line x1="${p[a][0]}" y1="${p[a][1]}" x2="${p[b][0]}" y2="${p[b][1]}" stroke="white" stroke-width="${p[a][2]+p[b][2]}" stroke-linecap="round"/>`).join('');
if(nodes.checked)svg.innerHTML+=Object.values(p).map(([x,y])=>`<circle cx="${x}" cy="${y}" r=".7" fill="#ec5987"/>`).join('');
document.querySelector('#value').value=u.toFixed(3);}
for(const el of [from,to,range,nodes])el.addEventListener('input',()=>{cancelAnimationFrame(animation);draw()});
document.querySelector('#play').onclick=()=>{cancelAnimationFrame(animation);const start=performance.now();
function tick(now){range.value=Math.min(1,(now-start)/(data.animation.duration*1000));draw();if(Number(range.value)<1)animation=requestAnimationFrame(tick);}
animation=requestAnimationFrame(tick);};draw();</script></html>'''.replace('DATA', data)
