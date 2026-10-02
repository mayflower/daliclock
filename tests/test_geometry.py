import copy
import io
import json
import math
from pathlib import Path
import sys
import unittest

import cairosvg
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from melt.geometry import (bezier, interpolate, load_glyphs, mix, sample_glyphs,
                           validate_geometry, validate_glyphs)
from melt.preview import TRANSITIONS, digit_svg, lines_svg


class GeometryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.glyphs = load_glyphs(ROOT / 'assets/glyphs/melt.json')
        cls.sampled = sample_glyphs(cls.glyphs, .9, .35)

    def test_original_xdaliclock_silhouettes(self):
        # Compare rendered exported strokes to the independently stored upstream
        # vector outlines. This catches real font changes, including serif loss.
        sampled = sample_glyphs(self.glyphs)
        for digit in range(10):
            original = Image.open(io.BytesIO(cairosvg.svg2png(
                url=str(ROOT / f'assets/glyphs/xdaliclock/{digit}.svg')))).getchannel('A')
            rendered = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=digit_svg(
                sampled, sampled.points[str(digit)], (400, 640)).encode()))).convert('L')
            original = original.point(lambda v: 255 if v >= 128 else 0)
            rendered = rendered.point(lambda v: 255 if v >= 128 else 0)
            intersection = sum(ImageChops.darker(original, rendered).histogram()[128:])
            union = sum(ImageChops.lighter(original, rendered).histogram()[128:])
            self.assertGreaterEqual(intersection / union, .98, digit)

    def test_all_pairs_and_parametric_correspondence(self):
        g, s = self.glyphs, self.sampled
        self.assertLessEqual(s.error_bound, .35)
        for a in range(10):
            for b in range(10):
                for step in range(21):
                    u = step / 20
                    points = interpolate(s, a, b, u)
                    validate_geometry(points, s.edges, s.box)
                    for curve in g.curves:
                        cubic = [mix(p, q, u) for p, q in zip(g.cubic(curve, a), g.cubic(curve, b))]
                        for node, t in zip(s.sample_ids[curve['id']], s.parameters[curve['id']]):
                            expected = tuple(x * .9 for x in bezier(cubic, t))
                            self.assertLess(math.dist(points[node], expected), 1e-10)
        for d in range(10):
            self.assertEqual(interpolate(s, d, d, .5), s.points[str(d)])

    def test_broken_join_and_swapped_ids_are_detected(self):
        broken = copy.deepcopy(self.glyphs)
        broken.curves[1]['start'] = 'missing'
        with self.assertRaises(ValueError):
            validate_glyphs(broken)
        broken = copy.deepcopy(self.glyphs)
        broken.curves[1]['controls']['0'][0][2] = -1
        with self.assertRaises(ValueError):
            validate_glyphs(broken)
        points = dict(self.sampled.points['0'])
        ids = self.sampled.sample_ids['upper_0']
        points[ids[0]], points[ids[-1]] = points[ids[-1]], points[ids[0]]
        with self.assertRaises(AssertionError):
            for node, t in zip(ids, self.sampled.parameters['upper_0']):
                expected = tuple(x * .9 for x in bezier(self.glyphs.cubic(self.glyphs.curves[0], 0), t))
                self.assertLess(math.dist(points[node], expected), 1e-10)

    def test_chords_stay_within_parametric_error_bound(self):
        for curve in self.glyphs.curves:
            params = self.sampled.parameters[curve['id']]
            for digit in range(10):
                c = self.glyphs.cubic(curve, digit)
                for lo, hi in zip(params, params[1:]):
                    for u in (.25, .5, .75):
                        error = math.dist(bezier(c, lo + (hi - lo) * u),
                                          mix(bezier(c, lo), bezier(c, hi), u)) * .9
                        self.assertLessEqual(error, self.sampled.error_bound + 1e-10)

    def test_rasterized_strokes_remain_connected(self):
        # Eight-connected foreground at half intensity, without dilation. Test
        # main/seconds/ambient strokes at the emulator and a 384px display size.
        for scale in (.9, .48):
            s = sample_glyphs(self.glyphs, scale, .35)
            for display in (384, 454):
                size = tuple(round(v * display / 450) for v in s.box)
                for a, b in TRANSITIONS:
                    for u in (0, .25, .5, .75, 1):
                        svg = digit_svg(s, interpolate(s, a, b, u), size)
                        im = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert('L')
                        foreground = {(x, y) for y in range(im.height) for x in range(im.width)
                                      if im.getpixel((x, y)) >= 128}
                        self.assertTrue(foreground)
                        remaining = set(foreground)
                        todo = [remaining.pop()]
                        while todo:
                            x, y = todo.pop()
                            for dx in (-1, 0, 1):
                                for dy in (-1, 0, 1):
                                    n = (x + dx, y + dy)
                                    if n in remaining:
                                        remaining.remove(n)
                                        todo.append(n)
                        if remaining:
                            out = ROOT / 'build/test-failures'
                            out.mkdir(parents=True, exist_ok=True)
                            im.save(out / f'{a}-{b}-{u}-{scale}-{display}.png')
                        self.assertFalse(remaining, (a, b, u, scale, display))

    def test_ambient_weighted_pixel_activation(self):
        # WO-P7 uses linearly weighted RGB intensity, not a count of lit pixels.
        # Sum each position's brightest digit: this bounds every HH:MM, including
        # 12-hour times with the leading position hidden. This is geometry-level
        # raster evidence, not a substitute for native ambient rendering tests.
        cfg = json.loads((ROOT / 'config/melt.json').read_text())
        s = sample_glyphs(self.glyphs, cfg['main']['scale'], cfg['tolerance'])
        argb = cfg['ambient']['color'].removeprefix('#')
        self.assertEqual(argb[:2], 'FF')
        color = '#' + argb[2:]
        for display in (384, 454):
            def intensity(content):
                svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{display}" '
                       f'height="{display}" viewBox="0 0 450 450">'
                       '<rect width="450" height="450" fill="black"/>' + content + '</svg>')
                im = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert('RGB')
                return sum(sum(channel * count for channel, count in enumerate(im.getchannel(c).histogram()))
                           for c in 'RGB') / (3 * 255)

            total = 0
            for offset in cfg['main']['positions']:
                x, y = cfg['main']['x'] + offset, cfg['main']['quiet_y']
                total += max(intensity(f'<g transform="translate({x},{y})">'
                                       + lines_svg(s, s.points[str(d)], color) + '</g>')
                             for d in range(10))
            total += intensity(''.join(f'<circle cx="225" cy="{cfg["main"]["quiet_y"] + y}" '
                                       f'r="4" fill="{color}"/>' for y in (57, 88)))
            # Use the smaller circular screen area, a conservative denominator.
            activation = total / (math.pi * (display / 2) ** 2)
            self.assertLessEqual(activation, .15, (display, activation))


if __name__ == '__main__':
    unittest.main()
