#!/usr/bin/env python3
"""Render Play listing artwork from Daliclock's actual sampled digit geometry."""
import io
import json
from pathlib import Path

import cairosvg
from PIL import Image

from daliclock.geometry import load_glyphs, sample_glyphs
from daliclock.preview import lines_svg

ROOT = Path(__file__).resolve().parents[1]


def main():
    cfg = json.loads((ROOT / 'config/daliclock.json').read_text())
    glyphs = load_glyphs(ROOT / 'assets/glyphs/daliclock.json')
    parts = ['<circle cx="225" cy="225" r="225" fill="black"/>']
    for name, digits in [('main', '0941'), ('seconds', '30')]:
        layout = cfg[name]
        sampled = sample_glyphs(glyphs, layout['scale'], cfg['tolerance'])
        for position, digit in zip(layout['positions'], digits):
            parts.append(f'<g transform="translate({layout["x"] + position},{layout["y"]})">'
                         + lines_svg(sampled, sampled.points[digit], '#FFBF40') + '</g>')
    for y in (57, 88):
        parts.append(f'<circle cx="{cfg["main"]["x"] + 194}" cy="{cfg["main"]["y"] + y}" r="4" fill="#FFBF40"/>')
    face = ''.join(parts)
    icon = f'<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 450 450">{face}</svg>'
    feature = ('<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="500">'
               '<rect width="1024" height="500" fill="#352710"/>'
               '<text x="64" y="276" font-family="serif" font-size="80" fill="#FFBF40">Daliclock</text>'
               f'<g transform="translate(544,50) scale(0.888888889)">{face}</g></svg>')
    output = ROOT / 'build/store'
    output.mkdir(parents=True, exist_ok=True)
    for name, svg, mode in [('icon', icon, 'RGBA'), ('feature-graphic', feature, 'RGB')]:
        (output / f'{name}.svg').write_text(svg)
        rendered = cairosvg.svg2png(bytestring=svg.encode())
        Image.open(io.BytesIO(rendered)).convert(mode).save(output / f'{name}.png')
        print(output / f'{name}.png')


if __name__ == '__main__':
    main()
