#!/usr/bin/env python3
"""Generate the offline line preview and a contact sheet."""
import argparse
from pathlib import Path
import json
from melt.geometry import load_glyphs, sample_glyphs
from melt.preview import overview, player

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
    print(f'{args.output}: {len(sampled.edges)} lines, bound {sampled.error_bound:.4f} logical units')


if __name__ == '__main__':
    main()
