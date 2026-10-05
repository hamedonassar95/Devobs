"""Regression checks: CI must reject representative broken pages."""
from pathlib import Path
import unittest
from scripts.check_site import validate

SOURCE = (Path(__file__).resolve().parents[1] / 'index.html').read_text(encoding='utf-8')


class SiteChecks(unittest.TestCase):
    def test_current_page(self):
        self.assertEqual(validate(SOURCE), [])

    def test_rejects_broken_pages(self):
        cases = {
            'missing doctype': SOURCE.replace('<!DOCTYPE html>', ''),
            'empty title': SOURCE[:SOURCE.index('<title>')] + '<title></title>' + SOURCE[SOURCE.index('</title>') + 8:],
            'wrong direction': SOURCE.replace('dir="rtl"', 'dir="ltr"'),
            'missing heading': SOURCE.replace('<h1>', '<div>').replace('</h1>', '</div>'),
            'duplicate ID': SOURCE.replace('id="about"', 'id="services"'),
            'broken label reference': SOURCE.replace('aria-labelledby="about"', 'aria-labelledby="missing"'),
            'conflict': SOURCE + '\n<<<<<<< HEAD\n',
        }
        for name, source in cases.items():
            with self.subTest(name=name):
                self.assertTrue(validate(source), name)

    def test_comment_cannot_supply_heading(self):
        source = SOURCE.replace('<h1>الدلة موبايل</h1>', '<!-- <h1>الدلة موبايل</h1> -->')
        self.assertIn('Expected exactly one h1 element', validate(source))


if __name__ == '__main__':
    unittest.main()
