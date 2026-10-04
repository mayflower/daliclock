"""WFF 4 line exporter; every moving point has exactly one drawn owner."""
from collections import Counter
from .animation import ANIMATION
from .geometry import STROKE_ALPHA
import math
import xml.etree.ElementTree as ET


def element(parent, tag, **attrs):
    return ET.SubElement(parent, tag, {k: str(v) for k, v in attrs.items()})


def number(value):
    return f'{value:.4f}'.rstrip('0').rstrip('.') or '0'


def coordinate_for_digit(expression, values):
    if len(set(values)) == 1:
        return values[0]
    result = values[-1]
    for digit in reversed(range(len(values) - 1)):
        result = f'(({expression}) == {digit} ? {values[digit]} : {result})'
    return result


def emit_digit(parent, geometry, digit_expression, position, color_expression,
               animated, namespace, max_digit=9):
    part = element(parent, 'PartDraw', name=namespace, x=position[0], y=position[1],
                   width=math.ceil(geometry.box[0]), height=math.ceil(geometry.box[1]),
                   tintColor=color_expression)
    degree = Counter(node for edge in geometry.edges for node in edge)
    tables = {(node, axis): [number(geometry.points[str(d)][node][axis]) for d in range(max_digit + 1)]
              for node in geometry.points['0'] for axis in range(2)}
    owners = {}
    for index, (a, b) in enumerate(geometry.edges):
        endpoints = [(a, 0, 'startX'), (a, 1, 'startY'),
                     (b, 0, 'endX'), (b, 1, 'endY')]
        line = element(part, 'Line', **{attr: tables[node, axis][0] for node, axis, attr in endpoints})
        widths = [number(geometry.points[str(d)][a][2] + geometry.points[str(d)][b][2])
                  for d in range(max_digit + 1)]
        stroke = element(line, 'Stroke', color=f'#{STROKE_ALPHA:02X}FFFFFF', thickness=widths[0], cap='ROUND')
        if len(set(widths)) > 1:
            transform = element(stroke, 'Transform', target='thickness',
                                value=coordinate_for_digit(digit_expression, widths))
            if animated:
                element(transform, 'Animation', duration=ANIMATION['duration'], interpolation=ANIMATION['interpolation'],
                        controls=' '.join(map(str, ANIMATION['controls'])), fps=ANIMATION['fps'], repeat='0')
        for node, axis, attr in endpoints:
            values = tables[node, axis]
            if len(set(values)) == 1:
                continue
            key = node, axis
            if key in owners:
                value = f'[REFERENCE.{owners[key][2]}]'
                if not animated:
                    # Wear OS 6 flushes ambient reference notifications before
                    # time notifications. Subscribe to the owner's time source
                    # too, so this consumer reads its updated coordinate in the
                    # same tick. Owners precede consumers in document order.
                    # The coordinate still comes exclusively from the reference.
                    value = f'({value} + 0 * ({digit_expression}))'
                element(line, 'Transform', target=attr, value=value)
            else:
                transform = element(line, 'Transform', target=attr,
                                    value=coordinate_for_digit(digit_expression, values))
                if animated:
                    element(transform, 'Animation', duration=ANIMATION['duration'], interpolation=ANIMATION['interpolation'],
                            controls=' '.join(map(str, ANIMATION['controls'])), fps=ANIMATION['fps'], repeat='0')
                reference = f'{namespace}_{node}_{"xy"[axis]}'
                owners[key] = index, attr, reference
                if degree[node] > 1:
                    element(line, 'Reference', name=reference, source=attr, defaultValue=values[0])
    return part, tables, owners


# Active-only accents; the foreground remains the sole animation owner.
RIM_COLOR, RIM_ALPHA, RIM_WIDTH = '#FF9DCFFF', 150, 2.0
GHOST_COLOR, GHOST_ALPHA, GHOST_MS = '#FFD5DEFF', 24, 180


def emit_morph_effects(parent, source, current, previous, visible='1 == 1', previous_visible='1 == 1'):
    name = source.get('name')
    attrs = {key: source.get(key) for key in ('x', 'y', 'width', 'height')}
    changed = f'(({current}) != ({previous}))'
    # A short image of the previous target uses the existing build-time font.
    ghost = element(parent, 'PartText', name=f'{name}_ghost', **attrs, alpha=0)
    ghost.set('x', str(int(attrs['x']) + 2))
    ghost.set('y', str(int(attrs['y']) + 1))
    ghost.set('width', str(math.ceil(float(attrs['width']) + 4)))
    element(ghost, 'Transform', target='alpha',
            value=f'({changed} && ({previous_visible}) ? {GHOST_ALPHA} * clamp(1 - [MILLISECOND] / {float(GHOST_MS)}, 0, 1) : 0)')
    text = element(ghost, 'Text', align='START')
    font = element(text, 'BitmapFont', family='ambient_digits', size=attrs['height'], color=GHOST_COLOR)
    template = element(font, 'Template'); template.text = '%d'
    element(template, 'Parameter', expression=previous)
    rim = element(parent, 'PartDraw', name=f'{name}_rim', **attrs, tintColor=RIM_COLOR, alpha=0)
    progress = f'clamp([MILLISECOND] / {ANIMATION["duration"] * 1000}, 0, 1)'
    element(rim, 'Transform', target='alpha',
            value=f'({changed} && ({visible}) ? {RIM_ALPHA} * 4 * {progress} * (1 - {progress}) : 0)')

    def follow(original, target, attribute, reference_name, extra=0):
        transform = original.find(f"Transform[@target='{attribute}']")
        if transform is None:
            target.set(attribute, number(float(original.get(attribute)) + extra))
            return
        reference = original.find(f"Reference[@source='{attribute}']")
        value = transform.get('value')
        if reference is not None:
            value = f'[REFERENCE.{reference.get("name")}]'
        elif not value.startswith('[REFERENCE.'):
            element(original, 'Reference', name=reference_name, source=attribute,
                    defaultValue=original.get(attribute))
            value = f'[REFERENCE.{reference_name}]'
        element(target, 'Transform', target=attribute, value=f'({value}) + {extra}')

    # Sparse highlights overlap through the original round caps. Keeping every
    # fourth segment avoids doubling the full animated draw workload.
    for index, original in enumerate(source.findall('Line')[::4]):
        line = element(rim, 'Line', **original.attrib)
        for attribute in ('startX', 'startY', 'endX', 'endY'):
            follow(original, line, attribute, f'{name}_rim_{index}_{attribute}')
        stroke = original.find('Stroke')
        copy = element(line, 'Stroke', **stroke.attrib)
        follow(stroke, copy, 'thickness', f'{name}_width_{index}', RIM_WIDTH)


def emit_active_digit(parent, geometry, current, previous, following, position, color,
                      namespace, family, max_digit=9, visible='1 == 1',
                      previous_visible='1 == 1'):
    """Enable a digit before its next tick so the native morph has its source.

    The graph paints the current, settled digit during the pre-roll. At the tick
    its native target animation starts normally, then the identical bitmap takes
    over. Keep accents and reference owners inside the same enabled branch.
    """
    duration_ms = ANIMATION['duration'] * 1000
    condition = element(parent, 'Condition')
    name = f'{namespace}_moving'
    expression = element(element(condition, 'Expressions'), 'Expression', name=name)
    expression.text = (f'(([MILLISECOND] < {duration_ms:g} && ({current}) != ({previous})) || '
                       f'([MILLISECOND] >= {duration_ms:g} && ({current}) != ({following})))')
    branch = element(condition, 'Compare', expression=name)
    part, _, _ = emit_digit(branch, geometry, current, position, color, True,
                            namespace, max_digit)
    emit_morph_effects(branch, part, current, previous, visible, previous_visible)
    branch.remove(part)
    branch.append(part)
    element(part, 'Transform', target='alpha', value=f'({visible} ? 255 : 0)')
    stable = element(element(condition, 'Default'), 'PartText',
                     name=f'{namespace}_stable', x=position[0], y=position[1],
                     width=math.ceil(geometry.box[0]), height=math.ceil(geometry.box[1]))
    element(stable, 'Transform', target='alpha', value=f'({visible} ? 255 : 0)')
    text = element(stable, 'Text', align='START')
    font = element(text, 'BitmapFont', family=family,
                   size=math.ceil(geometry.box[1]), color=color)
    template = element(font, 'Template')
    template.text = '%d'
    element(template, 'Parameter', expression=current)
