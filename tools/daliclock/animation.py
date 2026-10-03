"""Shared native animation settings and development-preview timing."""
import json
from pathlib import Path

ANIMATION = json.loads((Path(__file__).resolve().parents[2] /
                        'config/daliclock.json').read_text())['animation']


def eased_progress(elapsed):
    """Invert the Bezier time coordinate for the bounded native easing."""
    if not 0 <= elapsed <= 1:
        raise ValueError('Elapsed fraction must be between zero and one')
    if elapsed in (0, 1):
        return elapsed
    x1, y1, x2, y2 = ANIMATION['controls']

    def component(t, a, b):
        return 3 * (1-t)**2 * t * a + 3 * (1-t) * t*t * b + t**3

    lo, hi = 0., 1.
    for _ in range(40):
        t = (lo + hi) / 2
        if component(t, x1, x2) < elapsed:
            lo = t
        else:
            hi = t
    return component((lo + hi) / 2, y1, y2)
