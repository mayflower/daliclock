"""Shared cubic graph, common tessellation, and linear digit interpolation.

The subdivision bound compares a cubic to its parametrized chord. The two
interior difference control points bound the error by 3/4 of their maximum
norm. Taking the worst of all ten digits also bounds every linear morph.
"""

from dataclasses import dataclass
import json
import math
from pathlib import Path

Point = tuple[float, float]


def mix(a, b, u):
    return tuple((1 - u) * x + u * y for x, y in zip(a, b))


def bezier(c, s):
    a = [mix(c[i], c[i + 1], s) for i in range(3)]
    b = [mix(a[i], a[i + 1], s) for i in range(2)]
    return mix(*b, s)


def split(c):
    a, b, d = [mix(c[i], c[i + 1], 0.5) for i in range(3)]
    e, f = mix(a, b, 0.5), mix(b, d, 0.5)
    m = mix(e, f, 0.5)
    return (c[0], a, e, m), (m, f, d, c[3])


def chord_bound(c):
    return 0.75 * max(math.dist(c[i], mix(c[0], c[3], i / 3)) for i in (1, 2))


@dataclass
class GlyphSet:
    box: tuple[float, float]
    stroke: float
    nodes: dict
    curves: list
    smooth_joins: dict

    def cubic(self, curve, digit):
        digit = str(digit)
        return (self.nodes[curve['start']][digit], *curve['controls'][digit],
                self.nodes[curve['end']][digit])


@dataclass
class SampledGlyphSet:
    box: tuple[float, float]
    stroke: float
    points: dict[str, dict[str, Point]]
    edges: list[tuple[str, str]]
    parameters: dict[str, list[float]]
    sample_ids: dict[str, list[str]]
    error_bound: float


def load_glyphs(path):
    data = json.loads(Path(path).read_text())
    glyphs = GlyphSet(tuple(data['box']), data['stroke'], data['nodes'],
                      data['curves'], data['smooth_joins'])
    validate_glyphs(glyphs)
    return glyphs


def validate_glyphs(g):
    if g.stroke <= 0 or not math.isfinite(g.stroke):
        raise ValueError('Stroke must be positive and finite')
    digits = set(map(str, range(10)))
    ids = [c['id'] for c in g.curves]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate curve ID')
    neighbors = {n: set() for n in g.nodes}
    for node in g.nodes.values():
        if set(node) != digits:
            raise ValueError('Every node needs all ten digits')
    for curve in g.curves:
        a, b = curve['start'], curve['end']
        if a not in neighbors or b not in neighbors or set(curve['controls']) != digits:
            raise ValueError('Incomplete curve or unknown endpoint')
        neighbors[a].add(b)
        neighbors[b].add(a)
        for d in digits:
            for p in g.cubic(curve, d):
                if len(p) != 2 or not all(math.isfinite(x) for x in p):
                    raise ValueError('Nonfinite or malformed control point')
    seen, pending = set(), [next(iter(neighbors))]
    while pending:
        n = pending.pop()
        if n not in seen:
            seen.add(n)
            pending.extend(neighbors[n] - seen)
    if seen != set(neighbors):
        raise ValueError('Disconnected graph')
    curves = {c['id']: c for c in g.curves}
    for d, joins in g.smooth_joins.items():
        for first, second in joins:
            a, b = curves[first], curves[second]
            if a['end'] != b['start']:
                raise ValueError('Broken shared join')
            ca, cb = g.cubic(a, d), g.cubic(b, d)
            if any(abs((ca[3][j] - ca[2][j]) - (cb[1][j] - cb[0][j])) > 1e-8
                   for j in range(2)):
                raise ValueError('Broken smooth tangent')


def sample_glyphs(glyphs, layout_scale=1.0, tolerance=0.35, stroke=None):
    if layout_scale <= 0 or tolerance <= 0:
        raise ValueError('Scale and tolerance must be positive')
    points = {str(d): {} for d in range(10)}
    edges, parameters, sample_ids = [], {}, {}
    worst = 0.0
    for curve in glyphs.curves:
        params = [0.0]

        def subdivide(cubics, lo, hi):
            nonlocal worst
            bound = max(map(chord_bound, cubics)) * layout_scale
            if bound <= tolerance:
                params.append(hi)
                worst = max(worst, bound)
                return
            if hi - lo < 2 ** -16:
                raise ValueError('Cannot meet tessellation tolerance')
            halves = [split(c) for c in cubics]
            mid = (lo + hi) / 2
            subdivide([h[0] for h in halves], lo, mid)
            subdivide([h[1] for h in halves], mid, hi)

        subdivide([glyphs.cubic(curve, d) for d in range(10)], 0.0, 1.0)
        ids = [curve['start']] + [f"{curve['id']}_s{i}" for i in range(1, len(params) - 1)] + [curve['end']]
        parameters[curve['id']] = params
        sample_ids[curve['id']] = ids
        edges.extend(zip(ids, ids[1:]))
        for digit in points:
            for node, s in zip(ids, params):
                p = tuple(x * layout_scale for x in bezier(glyphs.cubic(curve, digit), s))
                if node in points[digit] and math.dist(p, points[digit][node]) > 1e-9:
                    raise ValueError('Inconsistent shared coordinate')
                points[digit][node] = p
    result = SampledGlyphSet(tuple(x * layout_scale for x in glyphs.box),
                            (glyphs.stroke if stroke is None else stroke) * layout_scale,
                            points, list(edges), parameters, sample_ids, worst)
    for digit in points:
        validate_geometry(points[digit], result.edges, result.box, result.stroke)
    return result


def interpolate(sampled, source_digit, target_digit, progress):
    if not 0 <= progress <= 1:
        raise ValueError('Progress must be between zero and one')
    a, b = sampled.points[str(source_digit)], sampled.points[str(target_digit)]
    return {node: mix(a[node], b[node], progress) for node in a}


def validate_geometry(points, edges, box, stroke):
    if not math.isfinite(stroke) or stroke <= 0:
        raise ValueError('Invalid stroke')
    for p in points.values():
        if any(not math.isfinite(v) or v < stroke / 2 or v > limit - stroke / 2
               for v, limit in zip(p, box)):
            raise ValueError(f'Point outside padded box: {p}')
    used = {node for edge in edges for node in edge}
    if used != set(points):
        raise ValueError('Edges and point IDs do not match')
    neighbors = {node: set() for node in points}
    for a, b in edges:
        neighbors[a].add(b)
        neighbors[b].add(a)
    visited, todo = set(), [next(iter(points))]
    while todo:
        node = todo.pop()
        if node not in visited:
            visited.add(node)
            todo.extend(neighbors[node] - visited)
    if visited != used:
        raise ValueError('Disconnected sampled graph')
