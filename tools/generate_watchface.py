#!/usr/bin/env python3
"""Generate the resource-only watchface from the shared digit graph."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import cairosvg
from melt.geometry import load_glyphs, sample_glyphs
from melt.preview import lines_svg
from melt.wff import element as add, emit_digit

ROOT = Path(__file__).resolve().parents[1]
HOUR = '([IS_24_HOUR_MODE] ? [HOUR_0_23] : [HOUR_1_12])'
TIME = [f'floor({HOUR} / 10)', f'({HOUR} % 10)', '[MINUTE_TENS_DIGIT]', '[MINUTE_UNITS_DIGIT]']
COLOR = '[CONFIGURATION.color_theme.0]'


def time_digits(hour, minute, second, is_24_hour):
    """Discrete preview targets; native WFF uses the system sources above."""
    display_hour = hour if is_24_hour else (hour % 12 or 12)
    return (display_hour // 10 if is_24_hour or display_hour >= 10 else None,
            display_hour % 10, minute // 10, minute % 10, second // 10, second % 10)


def group(parent, name, x=0, y=0, width=450, height=450, **attrs):
    return add(parent, 'Group', name=name, x=x, y=y, width=width, height=height, **attrs)


def text(parent, name, x, y, width, size, template, expressions, color=COLOR):
    part = add(parent, 'PartText', name=name, x=x, y=y, width=width, height=30)
    body = add(part, 'Text', align='CENTER')
    font = add(body, 'Font', family='SYNC_TO_DEVICE', size=size, color=color)
    fmt = add(font, 'Template')
    fmt.text = template
    for expression in expressions:
        add(fmt, 'Parameter', expression=expression)
    return part


def clock(parent, geometry, cfg, animated, namespace, color):
    main = group(parent, namespace, cfg['x'], cfg['y'] if animated else cfg['quiet_y'], 388, 160)
    if animated:
        add(main, 'Transform', target='y', value=f'([CONFIGURATION.show_seconds] == "TRUE" ? {cfg["y"]} : {cfg["quiet_y"]})')
    reader = add(main, 'ScreenReader', stringId='time_accessibility')
    for expression in [HOUR, '[MINUTE]', '([IS_24_HOUR_MODE] ? "" : [AMPM_STRING])']:
        add(reader, 'Parameter', expression=expression)
    for i, expression in enumerate(TIME):
        if animated:
            part, _, _ = emit_digit(main, geometry, expression, (cfg['positions'][i], 0), color,
                                   True, f'{namespace}_d{i}', max_digit=(2, 9, 5, 9)[i])
        else:
            part = group(main, f'{namespace}_d{i}', cfg['positions'][i], 0,
                         int(geometry.box[0]), int(geometry.box[1]))
            condition = add(part, 'Condition')
            expressions = add(condition, 'Expressions')
            for digit in range((2, 9, 5, 9)[i] + 1):
                add(expressions, 'Expression', name=f'd{digit}').text = f'({expression}) == {digit}'
                branch = add(condition, 'Compare', expression=f'd{digit}')
                image = add(branch, 'PartImage', x=0, y=0,
                            width=int(geometry.box[0]), height=int(geometry.box[1]))
                add(image, 'Image', resource=f'ambient_{digit}')
        if i == 0:
            add(part, 'Transform', target='alpha', value='([IS_24_HOUR_MODE] || [HOUR_1_12] >= 10 ? 255 : 0)')
    colon = add(main, 'PartDraw', name=f'{namespace}_colon', x=187, y=0, width=14, height=144)
    for y in (53, 84):
        dot = add(colon, 'Ellipse', x=3, y=y, width=8, height=8)
        add(dot, 'Fill', color=color)
    return main


def generate(output):
    cfg = json.loads((ROOT / 'config/melt.json').read_text())
    glyphs = load_glyphs(ROOT / 'assets/glyphs/melt.json')
    main = sample_glyphs(glyphs, cfg['main']['scale'], cfg['tolerance'])
    seconds = sample_glyphs(glyphs, cfg['seconds']['scale'], cfg['tolerance'])
    ambient = sample_glyphs(glyphs, cfg['main']['scale'], cfg['tolerance'])
    # Always-on has no morph: cache the exact exported geometry, not an active
    # frame, and let native time conditions choose the current static digit.
    (output / 'drawable').mkdir(parents=True, exist_ok=True)
    for digit in range(10):
        w, h = ambient.box
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w * 2}" height="{h * 2}" '
               f'viewBox="0 0 {w} {h}">' + lines_svg(ambient, ambient.points[str(digit)],
               '#' + cfg['ambient']['color'][3:]) + '</svg>')
        cairosvg.svg2png(bytestring=svg.encode(), write_to=str(output / f'drawable/ambient_{digit}.png'))
    root = ET.Element('WatchFace', width='450', height='450', clipShape='CIRCLE')
    configs = add(root, 'UserConfigurations')
    for name, default in [('show_seconds', 'TRUE'), ('show_date', 'FALSE')]:
        add(configs, 'BooleanConfiguration', id=name, displayName=f'{name}_label', screenReaderText=f'{name}_label', defaultValue=default)
    colors = add(configs, 'ColorConfiguration', id='color_theme', displayName='color_theme_label', screenReaderText='color_theme_label', defaultValue='white')
    for name, color in [('white', '#FFFFFFFF'), ('green', '#FF66FF66'), ('amber', '#FFFFBF40')]:
        add(colors, 'ColorOption', id=name, displayName=f'{name}_label', screenReaderText=f'{name}_label', colors=color)
    scene = add(root, 'Scene', backgroundColor='#FF000000')
    active = group(scene, 'active')
    add(active, 'Variant', mode='AMBIENT', target='alpha', value=0, duration=0)
    clock(active, main, cfg['main'], True, 'active_time', COLOR)
    ampm = text(active, 'ampm', 185, 270, 80, 16, '%s', ['[AMPM_STRING]'])
    add(ampm, 'Transform', target='alpha', value='([IS_24_HOUR_MODE] ? 0 : 255)')
    selection = add(active, 'BooleanConfiguration', id='show_seconds')
    yes = add(selection, 'BooleanOption', id='TRUE')
    sec = group(yes, 'seconds', cfg['seconds']['x'], cfg['seconds']['y'], 100, 77)
    for i, expression in enumerate(['[SECOND_TENS_DIGIT]', '[SECOND_UNITS_DIGIT]']):
        emit_digit(sec, seconds, expression, (cfg['seconds']['positions'][i], 0), COLOR, True, f'seconds_d{i}', max_digit=(5, 9)[i])
    group(add(selection, 'BooleanOption', id='FALSE'), 'seconds_off')
    selection = add(active, 'BooleanConfiguration', id='show_date')
    date = group(add(selection, 'BooleanOption', id='TRUE'), 'date')
    text(date, 'date_text', 75, 83, 300, 20, '%s %d %s', ['[DAY_OF_WEEK_S]', '[DAY]', '[MONTH_S]'])
    group(add(selection, 'BooleanOption', id='FALSE'), 'date_off')
    quiet = group(scene, 'ambient', alpha=0)
    add(quiet, 'Variant', mode='AMBIENT', target='alpha', value=255, duration=0)
    clock(quiet, ambient, cfg['main'], False, 'ambient_time', cfg['ambient']['color'])
    (output / 'raw').mkdir(parents=True, exist_ok=True)
    ET.indent(root)
    ET.ElementTree(root).write(output / 'raw/watchface.xml', encoding='utf-8', xml_declaration=True)
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="450" height="450"><rect width="450" height="450" fill="black"/>']
    preview_digits = time_digits(9, 8, 10, True)
    for i, d in enumerate(preview_digits[:4]):
        parts.append(f'<g transform="translate({cfg["main"]["x"] + cfg["main"]["positions"][i]},130)">{lines_svg(main, main.points[str(d)])}</g>')
    for y in (187, 218):
        parts.append(f'<circle cx="225" cy="{y}" r="4" fill="white"/>')
    for i, d in enumerate(preview_digits[4:]):
        parts.append(f'<g transform="translate({175 + cfg["seconds"]["positions"][i]},300)">{lines_svg(seconds, seconds.points[str(d)])}</g>')
    parts.append('</svg>')
    (output / 'drawable').mkdir(exist_ok=True)
    cairosvg.svg2png(bytestring=''.join(parts).encode(), write_to=str(output / 'drawable/preview.png'))
    print(f'WFF: {len(root.findall(".//Line"))} lines, {len(root.findall(".//Animation"))} animated coordinates, {len(root.findall(".//Reference"))} references')
    return root


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'watchface/build/generated/melt/res')
    generate(parser.parse_args().output)
