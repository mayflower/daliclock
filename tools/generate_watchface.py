#!/usr/bin/env python3
"""Generate the resource-only watchface from the shared digit graph."""
import argparse
import base64
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import cairosvg
from daliclock.geometry import load_glyphs, sample_glyphs
from daliclock.preview import lines_svg
from daliclock.wff import element as add, emit_active_digit

ROOT = Path(__file__).resolve().parents[1]
HOUR = '([IS_24_HOUR_MODE] ? [HOUR_0_23] : [HOUR_1_12])'
TIME = [f'floor({HOUR} / 10)', f'({HOUR} % 10)', '[MINUTE_TENS_DIGIT]', '[MINUTE_UNITS_DIGIT]']
COLOR = '[CONFIGURATION.color_theme.0]'
PREVIOUS_SECOND = '(([SECOND] + 59) % 60)'
PREVIOUS_MINUTE = '([SECOND] == 0 ? ([MINUTE] + 59) % 60 : [MINUTE])'
PREVIOUS_HOUR_24 = '([MINUTE] == 0 && [SECOND] == 0 ? ([HOUR_0_23] + 23) % 24 : [HOUR_0_23])'
PREVIOUS_HOUR = f'([IS_24_HOUR_MODE] ? {PREVIOUS_HOUR_24} : (({PREVIOUS_HOUR_24} + 11) % 12) + 1)'
PREVIOUS_TIME = [f'floor({PREVIOUS_HOUR} / 10)', f'({PREVIOUS_HOUR} % 10)',
                 f'floor({PREVIOUS_MINUTE} / 10)', f'({PREVIOUS_MINUTE} % 10)']
NEXT_SECOND = '(([SECOND] + 1) % 60)'
NEXT_MINUTE = '([SECOND] == 59 ? ([MINUTE] + 1) % 60 : [MINUTE])'
NEXT_HOUR_24 = '([MINUTE] == 59 && [SECOND] == 59 ? ([HOUR_0_23] + 1) % 24 : [HOUR_0_23])'
NEXT_HOUR = f'([IS_24_HOUR_MODE] ? {NEXT_HOUR_24} : (({NEXT_HOUR_24} + 11) % 12) + 1)'
NEXT_TIME = [f'floor({NEXT_HOUR} / 10)', f'({NEXT_HOUR} % 10)',
             f'floor({NEXT_MINUTE} / 10)', f'({NEXT_MINUTE} % 10)']
# Active-only decoration in the existing 450-unit layout.
RING_RADIUS, RING_WIDTH, DOT_SIZE = 217, 1.4, 4
RING_IDLE, RING_ACTIVE = '#266C79FF', '#806C79FF'
BACKGROUND = ROOT / 'assets/backgrounds/dali-landscape.png'
BACKGROUND_DIM = 0.25


def background_svg():
    # Fit the supplied artwork inside the ring; keep its colors and composition.
    radius = RING_RADIUS - RING_WIDTH / 2
    image = base64.b64encode(BACKGROUND.read_bytes()).decode('ascii')
    return (f'<defs><clipPath id="background_clip"><circle cx="225" cy="225" r="{radius}"/></clipPath></defs>'
            f'<image xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="data:image/png;base64,{image}" '
            f'x="{225-radius}" y="{225-radius}" width="{2*radius}" height="{2*radius}" '
            'preserveAspectRatio="xMidYMid slice" clip-path="url(#background_clip)"/>'
            f'<circle cx="225" cy="225" r="{radius}" fill="black" opacity="{BACKGROUND_DIM}"/>')


def decoration(parent):
    background = add(parent, 'PartImage', name='landscape', x=0, y=0, width=450, height=450)
    add(background, 'Image', resource='landscape')
    ring = add(parent, 'PartDraw', name='minute_ring', x=0, y=0, width=450, height=450)
    track = add(ring, 'Ellipse', x=225-RING_RADIUS, y=225-RING_RADIUS,
                width=2*RING_RADIUS, height=2*RING_RADIUS)
    add(track, 'Stroke', color=RING_IDLE, thickness=RING_WIDTH)
    arc = add(ring, 'Arc', centerX=225, centerY=225, width=2*RING_RADIUS,
              height=2*RING_RADIUS, startAngle=0, endAngle=0, direction='CLOCKWISE')
    add(arc, 'Stroke', color=RING_ACTIVE, thickness=RING_WIDTH, cap='ROUND')
    add(arc, 'Transform', target='endAngle', value='[MINUTE] * 6')


def decoration_preview(minute, second):
    """Static listing/chooser preview only; native WFF owns the live effects."""
    parts = [background_svg()]
    circumference = 2*math.pi*RING_RADIUS
    for color, dash in ((RING_IDLE, ''), (RING_ACTIVE, f'stroke-dasharray="{circumference*minute/60} {circumference}"')):
        parts.append(f'<circle cx="225" cy="225" r="{RING_RADIUS}" fill="none" stroke="#{color[3:]}" stroke-opacity="{int(color[1:3],16)/255}" stroke-width="{RING_WIDTH}" transform="rotate(-90 225 225)" {dash}/>')
    angle = math.radians(second*6)
    parts.append(f'<circle cx="{225+RING_RADIUS*math.sin(angle)}" cy="{225-RING_RADIUS*math.cos(angle)}" r="{DOT_SIZE/2}" fill="#E8EAFF"/>')
    return ''.join(parts)


def orbit_dot(parent):
    orbit = group(parent, 'seconds_orbit')
    add(orbit, 'Transform', target='angle', value='[SECOND_MILLISECOND] * 6')
    part = add(orbit, 'PartDraw', name='seconds_dot', x=0, y=0, width=450, height=450)
    dot = add(part, 'Ellipse', x=225-DOT_SIZE/2, y=225-RING_RADIUS-DOT_SIZE/2,
              width=DOT_SIZE, height=DOT_SIZE)
    add(dot, 'Fill', color='#FFE8EAFF')


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
    if not animated:
        part = add(main, 'PartText', name='ambient_clock', x=0, y=0, width=391, height=144)
        body = add(part, 'Text', align='START')
        font = add(body, 'BitmapFont', family='ambient_digits', size=144, color=color)
        fmt = add(font, 'Template')
        fmt.text = '%s%d:%02d'
        add(fmt, 'Parameter', expression=f'([IS_24_HOUR_MODE] || [HOUR_1_12] >= 10 ? floor({HOUR} / 10) : " ")')
        add(fmt, 'Parameter', expression=f'({HOUR} % 10)')
        add(fmt, 'Parameter', expression='[MINUTE]')
        return main
    for i, expression in enumerate(TIME):
        emit_active_digit(main, geometry, expression, PREVIOUS_TIME[i], NEXT_TIME[i],
                          (cfg['positions'][i], 0), color, f'{namespace}_d{i}',
                          'active_digits', max_digit=(2, 9, 5, 9)[i],
                          visible='([IS_24_HOUR_MODE] || [HOUR_1_12] >= 10)' if i == 0 else '1 == 1',
                          previous_visible=f'([IS_24_HOUR_MODE] || {PREVIOUS_HOUR} >= 10)' if i == 0 else '1 == 1')
    colon = add(main, 'PartDraw', name=f'{namespace}_colon', x=187, y=0, width=14, height=144)
    for y in (53, 84):
        dot = add(colon, 'Ellipse', x=3, y=y, width=8, height=8)
        add(dot, 'Fill', color=color)
    return main


def generate(output):
    cfg = json.loads((ROOT / 'config/daliclock.json').read_text())
    glyphs = load_glyphs(ROOT / 'assets/glyphs/daliclock.json')
    main = sample_glyphs(glyphs, cfg['main']['scale'], cfg['tolerance'])
    seconds = sample_glyphs(glyphs, cfg['seconds']['scale'], cfg['tolerance'])
    ambient = sample_glyphs(glyphs, cfg['main']['scale'], cfg['tolerance'])
    # Always-on has no morph. Render the exact geometry into a bitmap font so
    # a single time field invalidates all digits and the colon on each update.
    # Separate PartImages can lose unchanged content in the Wear OS 6 renderer.
    (output / 'drawable').mkdir(parents=True, exist_ok=True)
    background = ('<svg xmlns="http://www.w3.org/2000/svg" width="900" height="900" viewBox="0 0 450 450">'
                  + background_svg() + '</svg>')
    cairosvg.svg2png(bytestring=background.encode(), write_to=str(output / 'drawable/landscape.png'))
    for digit in range(10):
        w, h = ambient.box
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w * 2}" height="{h * 2}" '
               f'viewBox="0 0 {w} {h}">' + lines_svg(ambient, ambient.points[str(digit)],
               '#FFFFFF', opacity=1) + '</svg>')
        cairosvg.svg2png(bytestring=svg.encode(), write_to=str(output / f'drawable/ambient_{digit}.png'))
    root = ET.Element('WatchFace', width='450', height='450', clipShape='CIRCLE')
    fonts = add(root, 'BitmapFonts')
    # Stable active digits use the exact soft strokes of their morph graph.
    for family, geometry in [('active_digits', main), ('seconds_digits', seconds)]:
        font = add(fonts, 'BitmapFont', name=family)
        w, h = map(math.ceil, geometry.box)
        for digit in range(10):
            resource = f'{family}_{digit}'
            svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w * 2}" height="{h * 2}" '
                   f'viewBox="0 0 {w} {h}">'
                   + lines_svg(geometry, geometry.points[str(digit)]) + '</svg>')
            cairosvg.svg2png(bytestring=svg.encode(), write_to=str(output / f'drawable/{resource}.png'))
            add(font, 'Character', name=str(digit), resource=resource, width=w, height=h, marginRight=0)
    font = add(fonts, 'BitmapFont', name='ambient_digits')
    for digit in range(10):
        add(font, 'Character', name=str(digit), resource=f'ambient_{digit}',
            width=93, height=144, marginRight=3)
    for char, name, width, content in [
            (':', 'colon', 19, '<circle cx="8" cy="57" r="4" fill="white"/><circle cx="8" cy="88" r="4" fill="white"/>'),
            (' ', 'space', 93, '')]:
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width * 2}" height="288" '
               f'viewBox="0 0 {width} 144">{content}</svg>')
        cairosvg.svg2png(bytestring=svg.encode(), write_to=str(output / f'drawable/ambient_{name}.png'))
        add(font, 'Character', name=char, resource=f'ambient_{name}', width=width, height=144)
    configs = add(root, 'UserConfigurations')
    for name, default in [('show_seconds', 'TRUE'), ('show_date', 'FALSE')]:
        add(configs, 'BooleanConfiguration', id=name, displayName=f'{name}_label', screenReaderText=f'{name}_label', defaultValue=default)
    colors = add(configs, 'ColorConfiguration', id='color_theme', displayName='color_theme_label', screenReaderText='color_theme_label', defaultValue='white')
    for name, color in [('white', '#FFFFFFFF'), ('green', '#FF66FF66'), ('amber', '#FFFFBF40')]:
        add(colors, 'ColorOption', id=name, displayName=f'{name}_label', screenReaderText=f'{name}_label', colors=color)
    scene = add(root, 'Scene', backgroundColor='#FF000000')
    active = group(scene, 'active')
    add(active, 'Variant', mode='AMBIENT', target='alpha', value=0, duration=0)
    decoration(active)
    clock(active, main, cfg['main'], True, 'active_time', COLOR)
    ampm = text(active, 'ampm', 185, 270, 80, 16, '%s', ['[AMPM_STRING]'])
    add(ampm, 'Transform', target='alpha', value='([IS_24_HOUR_MODE] ? 0 : 255)')
    selection = add(active, 'BooleanConfiguration', id='show_seconds')
    yes = group(add(selection, 'BooleanOption', id='TRUE'), 'seconds_enabled')
    orbit_dot(yes)
    sec = group(yes, 'seconds', cfg['seconds']['x'], cfg['seconds']['y'], 100, 77)
    for i, expression in enumerate(['[SECOND_TENS_DIGIT]', '[SECOND_UNITS_DIGIT]']):
        previous = f'floor({PREVIOUS_SECOND} / 10)' if i == 0 else f'({PREVIOUS_SECOND} % 10)'
        following = f'floor({NEXT_SECOND} / 10)' if i == 0 else f'({NEXT_SECOND} % 10)'
        emit_active_digit(sec, seconds, expression, previous, following,
                          (cfg['seconds']['positions'][i], 0), COLOR,
                          f'seconds_d{i}', 'seconds_digits', max_digit=(5, 9)[i])
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
    parts.append(decoration_preview(8, 10))
    preview_digits = time_digits(9, 8, 10, True)
    for i, d in enumerate(preview_digits[:4]):
        parts.append(f'<g transform="translate({cfg["main"]["x"] + cfg["main"]["positions"][i]},130)">{lines_svg(main, main.points[str(d)])}</g>')
    for y in (187, 218):
        parts.append(f'<circle cx="225" cy="{y}" r="4" fill="white"/>')
    for i, d in enumerate(preview_digits[4:]):
        parts.append(f'<g transform="translate({cfg["seconds"]["x"] + cfg["seconds"]["positions"][i]},{cfg["seconds"]["y"]})">{lines_svg(seconds, seconds.points[str(d)])}</g>')
    parts.append('</svg>')
    (output / 'drawable').mkdir(exist_ok=True)
    cairosvg.svg2png(bytestring=''.join(parts).encode(), write_to=str(output / 'drawable/preview.png'))
    print(f'WFF: {len(root.findall(".//Line"))} lines, {len(root.findall(".//Animation"))} animated coordinates, {len(root.findall(".//Reference"))} references')
    return root


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'watchface/build/generated/daliclock/res')
    generate(parser.parse_args().output)
