"""WFF 4 line exporter; every moving point has exactly one drawn owner."""
from collections import Counter
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
                   width=math.ceil(geometry.box[0]), height=math.ceil(geometry.box[1]))
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
        stroke = element(line, 'Stroke', color=color_expression, thickness=widths[0], cap='ROUND')
        if len(set(widths)) > 1:
            transform = element(stroke, 'Transform', target='thickness',
                                value=coordinate_for_digit(digit_expression, widths))
            if animated:
                element(transform, 'Animation', duration='0.65', interpolation='LINEAR', fps='30', repeat='0')
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
                    element(transform, 'Animation', duration='0.65', interpolation='LINEAR', fps='30', repeat='0')
                reference = f'{namespace}_{node}_{"xy"[axis]}'
                owners[key] = index, attr, reference
                if degree[node] > 1:
                    element(line, 'Reference', name=reference, source=attr, defaultValue=values[0])
    return part, tables, owners
