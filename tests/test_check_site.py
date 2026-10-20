"""Regression checks: CI must reject representative broken pages."""
from pathlib import Path
import re
import unittest
from scripts.check_site import Page, validate

SOURCE = (Path(__file__).resolve().parents[1] / 'index.html').read_text(encoding='utf-8')
EXPECTED_TITLE = 'Devobs | خدمات DevOps والبرمجيات للشركات'
EXPECTED_H1 = 'خدمات البرمجيات وDevOps للشركات'
EXPECTED_SECTION_IDS = ('services', 'start', 'contact')
EXPECTED_PAGE_TEXT = (
    'Devobs',
    EXPECTED_H1,
    'خدمات DevOps والبرمجيات بمساندة الذكاء الاصطناعي للشركات',
    'إنشاء تطبيقات الويب والمواقع الإلكترونية',
    'إنشاء تطبيقات الهواتف المحمولة',
    'إصلاح المواقع والأنظمة وصيانتها',
    'أتمتة DevOps باستخدام GitHub Actions وCI/CD',
    'مراجعة الشيفرة وفرز الحوادث بمساندة الذكاء الاصطناعي',
    'أرسل موجز مشروعك',
    'نراجعه',
    'نقترح نطاق العمل',
    'mohammadnassar813@gmail.com',
    'Devobs — DevOps and AI-assisted services.',
)


class SiteChecks(unittest.TestCase):
    def test_current_page(self):
        self.assertEqual(validate(SOURCE), [])

    def test_devobs_landing_content_contract(self):
        page = Page()
        page.feed(SOURCE)
        page.close()
        title = ''.join(page.title).strip()
        self.assertEqual(title, EXPECTED_TITLE, 'index.html must use the Devobs landing page title')

        ids = {attrs['id'] for _, attrs in page.tags if attrs.get('id')}
        for section_id in EXPECTED_SECTION_IDS:
            with self.subTest(section_id=section_id):
                self.assertIn(section_id, ids, f'index.html must contain the #{section_id} section')

        for expected_text in EXPECTED_PAGE_TEXT:
            with self.subTest(expected_text=expected_text):
                self.assertIn(expected_text, SOURCE, f'index.html is missing required landing page text: {expected_text}')

        email_addresses = re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', SOURCE)
        self.assertEqual(
            set(email_addresses),
            {'mohammadnassar813@gmail.com'},
            'index.html must expose only the approved email',
        )
        self.assertIn('href="mailto:mohammadnassar813@gmail.com"', SOURCE, 'contact email must be a mailto link')
        self.assertNotRegex(SOURCE, r'<(?:script|link|img)\b', 'landing page must not load JavaScript or external assets')
        self.assertNotIn('highest quality', SOURCE.lower(), 'landing page must not claim highest quality')
        self.assertNotIn('best ai for 2027', SOURCE.lower(), 'landing page must not use the prohibited AI claim')

    def test_rejects_broken_pages(self):
        cases = {
            'missing doctype': SOURCE.replace('<!doctype html>', '', 1),
            'empty title': SOURCE[:SOURCE.index('<title>')] + '<title></title>' + SOURCE[SOURCE.index('</title>') + 8:],
            'wrong direction': SOURCE.replace('dir="rtl"', 'dir="ltr"'),
            'missing heading': SOURCE.replace('<h1>', '<div>').replace('</h1>', '</div>'),
            'duplicate ID': SOURCE.replace('id="contact"', 'id="services"'),
            'broken label reference': SOURCE.replace('aria-labelledby="contact-title"', 'aria-labelledby="missing"'),
            'conflict': SOURCE + '\n<<<<<<< HEAD\n',
        }
        for name, source in cases.items():
            with self.subTest(name=name):
                self.assertTrue(validate(source), name)

    def test_comment_cannot_supply_heading(self):
        source = SOURCE.replace(f'<h1>{EXPECTED_H1}</h1>', f'<!-- <h1>{EXPECTED_H1}</h1> -->')
        self.assertIn('Expected exactly one h1 element', validate(source))


if __name__ == '__main__':
    unittest.main()
