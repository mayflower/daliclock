"""Shared cubic graph, common tessellation, and linear digit interpolation.

The subdivision bound compares a cubic to its parametrized chord. The two
interior difference control points bound the error by 3/4 of their maximum
norm. Taking the worst of all ten digits also bounds every linear morph.
"""

from collections import defaultdict
from dataclasses import dataclass
import json
import math
from pathlib import Path

# Dense round strokes overlap: partial coverage keeps their outer edge soft.
STROKE_ALPHA = 96
# Larger radius changes introduced visible bumps at constant-width line caps.
MAX_RADIUS_CHANGE = 1.5

Point = tuple[float, float, float]  # x, y, radius


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
    points: dict[str, dict[str, Point]]
    edges: list[tuple[str, str]]
    parameters: dict[str, list[float]]
    sample_ids: dict[str, list[str]]
    error_bound: float


def load_glyphs(path):
    data = json.loads(Path(path).read_text())
    glyphs = GlyphSet(tuple(data['box']), data['nodes'],
                      data['curves'], data['smooth_joins'])
    validate_glyphs(glyphs)
    return glyphs


def validate_glyphs(g):
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
                if len(p) != 3 or p[2] <= 0 or not all(math.isfinite(x) for x in p):
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


def sample_glyphs(glyphs, layout_scale=1.0, tolerance=0.35, *, simplify=True):
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
                            points, list(edges), parameters, sample_ids, worst)
    for digit in points:
        validate_geometry(points[digit], result.edges, result.box)
    return simplify_glyphs(result, tolerance) if simplify else result


def simplify_glyphs(sampled, tolerance):
    """Collapse degree-two chains using one correspondence for all digits.

    Junctions and endpoints survive. Cumulative worst-digit arc length supplies
    a shared parameter: the position/radius error then also bounds linear
    intermediate forms by convexity. Limit radius variation separately because
    WFF draws a constant-width capsule, not a tapered stroke.
    """
    neighbors = defaultdict(list)
    for a, b in sampled.edges:
        neighbors[a].append(b)
        neighbors[b].append(a)
    visited, edges = set(), []
    worst = 0.0
    # Starting at every node also covers a graph consisting only of a cycle.
    starts = sorted(neighbors, key=lambda n: len(neighbors[n]) == 2)
    for start in starts:
        for following in neighbors[start]:
            if frozenset((start, following)) in visited:
                continue
            chain = [start, following]
            visited.add(frozenset((start, following)))
            previous, node = start, following
            while len(neighbors[node]) == 2 and node != start:
                other = next(n for n in neighbors[node] if n != previous)
                visited.add(frozenset((node, other)))
                chain.append(other)
                previous, node = node, other
            distance = [0.0]
            for a, b in zip(chain, chain[1:]):
                distance.append(distance[-1] + max(
                    math.dist(p[a], p[b]) for p in sampled.points.values()))

            def reduce(lo, hi):
                nonlocal worst
                if hi == lo + 1:
                    edges.append((chain[lo], chain[hi]))
                    return
                length = distance[hi] - distance[lo]
                error, split_at = -1.0, (lo + hi) // 2
                for i in range(lo + 1, hi):
                    u = (distance[i] - distance[lo]) / length if length else 0
                    deviation = 0.0
                    for points in sampled.points.values():
                        actual = points[chain[i]]
                        expected = mix(points[chain[lo]], points[chain[hi]], u)
                        deviation = max(deviation, math.dist(actual[:2], expected[:2])
                                        + abs(actual[2] - expected[2]))
                    if deviation > error:
                        error, split_at = deviation, i
                radius_change = max(
                    max(p[n][2] for n in chain[lo:hi + 1])
                    - min(p[n][2] for n in chain[lo:hi + 1])
                    for p in sampled.points.values())
                if (error + sampled.error_bound <= tolerance
                        and radius_change <= MAX_RADIUS_CHANGE
                        and chain[lo] != chain[hi]):
                    edges.append((chain[lo], chain[hi]))
                    worst = max(worst, error)
                else:
                    if error + sampled.error_bound <= tolerance:
                        split_at = (lo + hi) // 2
                    reduce(lo, split_at)
                    reduce(split_at, hi)

            reduce(0, len(chain) - 1)
    retained = {n for edge in edges for n in edge}
    points = {d: {n: p[n] for n in p if n in retained}
              for d, p in sampled.points.items()}
    parameters, sample_ids = {}, {}
    for curve, ids in sampled.sample_ids.items():
        kept = [(n, t) for n, t in zip(ids, sampled.parameters[curve]) if n in retained]
        sample_ids[curve] = [n for n, t in kept]
        parameters[curve] = [t for n, t in kept]
    result = SampledGlyphSet(sampled.box, points, edges, parameters, sample_ids,
                             sampled.error_bound + worst)
    for p in points.values():
        validate_geometry(p, edges, result.box)
    return result


def interpolate(sampled, source_digit, target_digit, progress):
    if not 0 <= progress <= 1:
        raise ValueError('Progress must be between zero and one')
    a, b = sampled.points[str(source_digit)], sampled.points[str(target_digit)]
    return {node: mix(a[node], b[node], progress) for node in a}


def validate_geometry(points, edges, box):
    for p in points.values():
        if p[2] <= 0 or not math.isfinite(p[2]):
            raise ValueError('Invalid radius')
        if any(not math.isfinite(v) or v < p[2] or v > limit - p[2]
               for v, limit in zip(p[:2], box)):
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
