#!/usr/bin/env python3
"""Generate the offline line preview and a contact sheet."""
import argparse
from pathlib import Path
import json
from melt.geometry import load_glyphs, sample_glyphs
from melt.preview import overview, player, digit_svg

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/preview')
    args = parser.parse_args()
    config = json.loads((ROOT / 'config/melt.json').read_text())
    sampled = sample_glyphs(load_glyphs(ROOT / 'assets/glyphs/melt.json'),
                            config['main']['scale'], config['tolerance'])
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'index.html').write_text(player(sampled))
    svg = overview(sampled)
    (args.output / 'overview.svg').write_text(svg)
    import cairosvg
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(args.output / 'overview.png'))
    # Original vector artwork beside the same line geometry used by WFF.
    import io
    from PIL import Image, ImageDraw
    sheet = Image.new('RGB', (2000, 700), '#101216')
    labels = ImageDraw.Draw(sheet)
    comparison = sample_glyphs(load_glyphs(ROOT / 'assets/glyphs/melt.json'))
    for digit in range(10):
        original = Image.open(io.BytesIO(cairosvg.svg2png(
            url=str(ROOT / f'assets/glyphs/xdaliclock/{digit}.svg')))).getchannel('A')
        rendered = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=digit_svg(
            comparison, comparison.points[str(digit)], (400, 640)).encode()))).convert('L')
        x, y = (digit % 5) * 400, (digit // 5) * 350
        labels.text((x + 10, y + 10), f'{digit}: original / Melt', fill='white')
        sheet.paste(original.resize((200, 320)), (x, y + 30))
        sheet.paste(rendered.resize((200, 320)), (x + 200, y + 30))
    sheet.save(args.output / 'classic-comparison.png')
    print(f'{args.output}: {len(sampled.edges)} lines, bound {sampled.error_bound:.4f} logical units')


if __name__ == '__main__':
    main()
