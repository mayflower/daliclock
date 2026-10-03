"""Exported owner endpoints and rounded coordinates, not a WFF interpreter."""
from pathlib import Path
import sys
import tempfile
from datetime import datetime, timedelta
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from daliclock.geometry import load_glyphs, sample_glyphs
from daliclock.wff import emit_digit, coordinate_for_digit, number
from generate_watchface import generate, time_digits


class ExportTest(unittest.TestCase):
    def test_preview_time_mapping_for_full_day(self):
        # This verifies discrete mapping against datetime, not WFF execution.
        start = datetime(2026, 1, 1)
        for seconds in range(86400):
            t = start + timedelta(seconds=seconds)
            for is_24 in (False, True):
                expected = t.strftime('%H%M%S' if is_24 else '%I%M%S')
                expected = tuple(map(int, expected))
                if not is_24 and expected[0] == 0:
                    expected = (None, *expected[1:])
                self.assertEqual(time_digits(t.hour, t.minute, t.second, is_24), expected)

    def test_scene_dependencies_and_native_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = generate(Path(directory))
        declarations = root.find('UserConfigurations')
        self.assertEqual({c.get('id'): c.get('defaultValue') for c in declarations},
                         {'show_seconds': 'TRUE', 'show_date': 'FALSE', 'color_theme': 'white'})
        ambient = root.find(".//Group[@name='ambient']")
        self.assertIsNone(ambient.find('.//Animation'))
        self.assertIsNone(ambient.find('.//BooleanConfiguration'))
        ambient_text = ET.tostring(ambient, encoding='unicode')
        self.assertNotIn('SECOND', ambient_text)
        self.assertNotIn('REFERENCE.active', ambient_text)
        self.assertNotIn('REFERENCE.seconds', ambient_text)
        for name in ('active_time', 'ambient_time'):
            main = root.find(f".//Group[@name='{name}']")
            for transform in main.findall('.//Transform'):
                self.assertNotIn('[SECOND', transform.get('value'))
                self.assertNotIn('[MILLISECOND', transform.get('value'))
        names = [ref.get('name') for ref in root.findall('.//Reference')]
        self.assertEqual(len(names), len(set(names)))
        for selection in root.findall('.//Scene//BooleanConfiguration'):
            self.assertIsNone(selection.find('.//BooleanConfiguration'))
            self.assertEqual({o.get('id') for o in selection}, {'TRUE', 'FALSE'})
        for name, initial, target in [('active', '255', '0'), ('ambient', '0', '255')]:
            group = root.find(f".//Group[@name='{name}']")
            self.assertEqual(group.get('alpha', '255'), initial)
            variant = group.find('Variant')
            self.assertEqual(variant.attrib, {'mode': 'AMBIENT', 'target': 'alpha',
                                             'value': target, 'duration': '0'})
            self.assertFalse(any(t.get('target') == 'alpha' for t in group.findall('Transform')))

    def test_shared_exported_endpoints_follow_one_owner(self):
        glyphs = load_glyphs(ROOT / 'assets/glyphs/daliclock.json')
        for scale, animated in ((.9, True), (.48, True), (.9, False)):
            geometry = sample_glyphs(glyphs, scale)
            parent = ET.Element('Group')
            part, tables, owners = emit_digit(parent, geometry, '[MINUTE_UNITS_DIGIT]',
                                             (0, 0), '#FFFFFFFF', animated, 'test')
            lines = part.findall('Line')
            refs = {ref.get('name'): (i, ref) for i, line in enumerate(lines) for ref in line.findall('Reference')}
            self.assertEqual(len(refs), len(part.findall('.//Reference')))
            for i, (a, b) in enumerate(geometry.edges):
                line = lines[i]
                self.assertGreater(float(line.find('Stroke').get('thickness')), 0)
                widths = [number(geometry.points[str(d)][a][2] + geometry.points[str(d)][b][2])
                          for d in range(10)]
                stroke = line.find('Stroke')
                self.assertEqual(stroke.get('thickness'), widths[0])
                width_transform = stroke.find('Transform')
                if len(set(widths)) > 1:
                    self.assertEqual(width_transform.get('value'),
                                     coordinate_for_digit('[MINUTE_UNITS_DIGIT]', widths))
                    self.assertEqual(width_transform.find('Animation') is not None, animated)
                for source, target in ((9, 0), (5, 0), (8, 1)):
                    for u in (0, .25, .5, .75, 1):
                        actual = (1-u)*float(widths[source]) + u*float(widths[target])
                        expected = sum((1-u)*geometry.points[str(source)][node][2]
                                       + u*geometry.points[str(target)][node][2] for node in (a, b))
                        self.assertLessEqual(abs(actual - expected), .000051)
                transforms = {t.get('target'): t for t in line.findall('Transform')}
                for node, axis, attr in ((a, 0, 'startX'), (a, 1, 'startY'), (b, 0, 'endX'), (b, 1, 'endY')):
                    values = tables[node, axis]
                    self.assertEqual(line.get(attr), values[0])
                    if len(set(values)) == 1:
                        self.assertNotIn(attr, transforms)
                        continue
                    owner_index, owner_attr, name = owners[node, axis]
                    t = transforms[attr]
                    if owner_index == i and owner_attr == attr:
                        self.assertEqual(t.find('Animation') is not None, animated)
                    else:
                        expected_reference = f'[REFERENCE.{name}]'
                        if not animated:
                            expected_reference = f'({expected_reference} + 0 * ([MINUTE_UNITS_DIGIT]))'
                        self.assertEqual(t.get('value'), expected_reference)
                        self.assertIsNone(t.find('Animation'))
                        self.assertLessEqual(owner_index, i)
                        self.assertEqual(refs[name][0], owner_index)
                        self.assertEqual(refs[name][1].get('source'), owner_attr)
                        self.assertEqual(refs[name][1].get('defaultValue'), values[0])
                    # Numeric samples use the actual serialized owner table.
                    for source, target in ((9, 0), (5, 0), (8, 1), (2, 3)):
                        for u in (0, .25, .5, .75, 1):
                            actual = (1-u)*float(values[source]) + u*float(values[target])
                            expected = ((1-u)*geometry.points[str(source)][node][axis]
                                        + u*geometry.points[str(target)][node][axis])
                            self.assertLessEqual(abs(actual - expected), .000051)


if __name__ == '__main__':
    unittest.main()
