import copy
import io
import json
import math
from pathlib import Path
import sys
import unittest

import cairosvg
from PIL import Image, ImageChops, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from daliclock.geometry import (bezier, interpolate, load_glyphs, mix, sample_glyphs,
                           validate_geometry, validate_glyphs, simplify_glyphs, SampledGlyphSet)
from daliclock.animation import eased_progress
from daliclock.preview import TRANSITIONS, digit_svg, lines_svg


class GeometryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.glyphs = load_glyphs(ROOT / 'assets/glyphs/daliclock.json')
        cls.sampled = sample_glyphs(cls.glyphs, .9, .35, simplify=False)

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
                    u = eased_progress(step / 20)
                    points = interpolate(s, a, b, u)
                    validate_geometry(points, s.edges, s.box)
                    for curve in g.curves:
                        cubic = [mix(p, q, u) for p, q in zip(g.cubic(curve, a), g.cubic(curve, b))]
                        for node, t in zip(s.sample_ids[curve['id']], s.parameters[curve['id']]):
                            expected = tuple(x * .9 for x in bezier(cubic, t))
                            self.assertLess(math.dist(points[node], expected), 1e-10)
        for d in range(10):
            self.assertEqual(interpolate(s, d, d, .5), s.points[str(d)])

    def test_simplification_preserves_shared_junctions_and_digit_extrema(self):
        # The last digit alone has a corner; an optimizer looking only at zero
        # would erase it. A branch must retain its shared attachment point.
        points = {str(d): {'a': (5., 5., 1.), 'b': (7., 5., 1.),
                           'c': (9., 5., 1.), 'd': (11., 5., 1.),
                           'e': (13., 5., 1.), 'tip': (9., 9., 1.)}
                  for d in range(10)}
        points['9']['d'] = (11., 7., 1.)
        source = SampledGlyphSet((20, 20), points,
                                 [('a', 'b'), ('b', 'c'), ('c', 'd'),
                                  ('d', 'e'), ('c', 'tip')], {}, {}, 0.)
        reduced = simplify_glyphs(source, .35)
        self.assertNotIn('b', reduced.points['0'])
        self.assertIn('d', reduced.points['0'])
        for step in (0, .25, .5, .75, 1):
            actual = interpolate(reduced, 0, 9, step)
            validate_geometry(actual, reduced.edges, reduced.box)
            self.assertEqual(actual['c'], (9., 5., 1.))
            self.assertEqual(actual['d'], (11., 5. + 2 * step, 1.))

    def test_simplification_keeps_closed_contours(self):
        points = {str(d): {'a': (5., 5., 1.), 'b': (9., 5., 1.),
                           'c': (9., 9., 1.), 'd': (5., 9., 1.)}
                  for d in range(10)}
        source = SampledGlyphSet((20, 20), points,
                                 [('a', 'b'), ('b', 'c'), ('c', 'd'), ('d', 'a')],
                                 {}, {}, 0.)
        reduced = simplify_glyphs(source, .35)
        self.assertEqual(reduced.points, points)
        for p in reduced.points.values():
            validate_geometry(p, reduced.edges, reduced.box)

    def test_reduced_morphs_keep_source_coordinates_and_bounds(self):
        reduced = sample_glyphs(self.glyphs, .9, .35)
        self.assertLessEqual(reduced.error_bound, .35)
        for a in range(10):
            for b in range(10):
                for u in (0, .25, .5, .75, 1):
                    actual = interpolate(reduced, a, b, u)
                    source = interpolate(self.sampled, a, b, u)
                    validate_geometry(actual, reduced.edges, reduced.box)
                    self.assertEqual(actual, {n: source[n] for n in actual})

    def test_viscous_easing_stays_within_exact_targets(self):
        self.assertEqual(eased_progress(0), 0)
        self.assertEqual(eased_progress(1), 1)
        self.assertLess(eased_progress(.25), .1)
        self.assertGreater(eased_progress(.75), .9)
        # Overshoot left persistent bulges in the native renderer. Check the
        # actual timing function throughout the transition, not only endpoints.
        previous = 0
        for step in range(1001):
            progress = eased_progress(step / 1000)
            self.assertGreaterEqual(progress, previous)
            self.assertLessEqual(progress, 1)
            previous = progress
        for invalid in (-.001, 1.001, math.nan):
            with self.assertRaises(ValueError):
                interpolate(self.sampled, 1, 2, invalid)

    def test_soft_strokes_preserve_partial_edge_coverage(self):
        sampled = sample_glyphs(self.glyphs, .9, .35)
        for d in (2, 4, 7):
            svg = digit_svg(sampled, sampled.points[str(d)])
            soft = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert('L')
            opaque_svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="90" height="144">'
                          '<rect width="90" height="144" fill="black"/>'
                          + lines_svg(sampled, sampled.points[str(d)], opacity=1) + '</svg>')
            hard = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=opaque_svg.encode()))).convert('L')
            # Inspect the visible boundary, excluding the fully covered interior.
            core = hard.point(lambda v: 255 if v == 255 else 0).filter(ImageFilter.MinFilter(3))
            partial = lambda im: sum(1 for v, c in zip(im.getdata(), core.getdata()) if c == 0 and 0 < v < 250)
            self.assertGreater(partial(soft), partial(hard))

    def test_ring_clears_all_digit_silhouettes(self):
        from generate_watchface import RING_RADIUS, RING_WIDTH
        cfg = json.loads((ROOT / 'config/daliclock.json').read_text())['main']
        for y in (cfg['y'], cfg['quiet_y']):
            for x in cfg['positions']:
                for points in self.sampled.points.values():
                    for px, py, radius in points.values():
                        extent = math.hypot(cfg['x']+x+px-225, y+py-225)+radius
                        self.assertGreater(RING_RADIUS-RING_WIDTH/2-extent, 4)

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
                    for u in [eased_progress(t) for t in (0, .25, .5, .75, 1)]:
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
        cfg = json.loads((ROOT / 'config/daliclock.json').read_text())
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
                                       + lines_svg(s, s.points[str(d)], color, opacity=1) + '</g>')
                             for d in range(10))
            total += intensity(''.join(f'<circle cx="225" cy="{cfg["main"]["quiet_y"] + y}" '
                                       f'r="4" fill="{color}"/>' for y in (57, 88)))
            # Use the smaller circular screen area, a conservative denominator.
            activation = total / (math.pi * (display / 2) ** 2)
            self.assertLessEqual(activation, .15, (display, activation))


if __name__ == '__main__':
    unittest.main()
