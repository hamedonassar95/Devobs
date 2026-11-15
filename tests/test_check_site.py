"""Regression checks: CI must reject representative broken pages."""
from pathlib import Path
import re
import os
import subprocess
import sys
import tempfile
import unittest
from scripts.check_site import Page, validate, validate_free_demo
from scripts.stage_site import copy_public_content

SOURCE = (Path(__file__).resolve().parents[1] / 'index.html').read_text(encoding='utf-8')
EXPECTED_TITLE = 'Devobs | خدمات DevOps والبرمجيات للشركات | Software & DevOps Services'
EXPECTED_H1 = 'خدمات البرمجيات وDevOps للشركات'
EXPECTED_SECTION_IDS = ('services', 'start', 'contact')
EXPECTED_PAGE_TEXT = (
    'Devobs',
    EXPECTED_H1,
    'Software and DevOps services for businesses',
    'خدمات DevOps والبرمجيات بمساندة الذكاء الاصطناعي للشركات حول العالم',
    'AI-assisted DevOps and software services for businesses worldwide.',
    'إنشاء تطبيقات الويب والمواقع الإلكترونية',
    'Build web applications and websites',
    'إنشاء تطبيقات الهواتف المحمولة',
    'Build mobile applications',
    'إصلاح المواقع والأنظمة وصيانتها',
    'Repair and maintain websites and systems',
    'أتمتة DevOps باستخدام GitHub Actions وCI/CD',
    'DevOps automation with GitHub Actions and CI/CD',
    'مراجعة الشيفرة وفرز الحوادث بمساندة الذكاء الاصطناعي',
    'AI-assisted code review and incident triage',
    'عروض الخدمات',
    'Service offers',
    'تطوير موقع أو تطبيق',
    'Website &amp; mobile app development',
    'إصلاح وصيانة المواقع والأنظمة',
    'Website &amp; systems repair and maintenance',
    'تحسين DevOps ومراجعة هندسية',
    'DevOps &amp; AI-assisted engineering',
    'مخرجات مقترحة',
    'Proposed deliverables',
    'لا ترسل كلمات مرور أو مفاتيح',
    'Do not send passwords or keys',
    'أرسل موجز مشروعك',
    'Send us your project brief',
    'نراجعه',
    'We review it to understand your needs',
    'نقترح نطاق العمل',
    'We propose a suitable scope of work',
    'حول العالم',
    'worldwide',
    'hamedonassar95@outlook.sa',
    '+962 79 808 1818',
    'Devobs — خدمات DevOps والذكاء الاصطناعي.',
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

        self.assertEqual(
            SOURCE.count('class="offer-card"'),
            3,
            'index.html must present exactly three scoped service offers',
        )
        self.assertEqual(
            SOURCE.count('class="offer-link"'),
            3,
            'each service offer must link to the existing project brief steps',
        )

        email_addresses = re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', SOURCE)
        self.assertEqual(
            set(email_addresses),
            {'hamedonassar95@outlook.sa'},
            'index.html must expose only the owner-provided email',
        )
        self.assertIn('href="mailto:hamedonassar95@outlook.sa"', SOURCE, 'contact email must be a mailto link')
        self.assertIn('href="tel:+962798081818"', SOURCE, 'contact phone must use a tel link')
        self.assertIn('lang="en"', SOURCE, 'landing page must include English content')
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
        source = re.sub(
            r'<h1>.*?</h1>',
            f'<!-- <h1>{EXPECTED_H1}</h1> -->',
            SOURCE,
            count=1,
            flags=re.DOTALL,
        )
        self.assertIn('Expected exactly one h1 element', validate(source))


if __name__ == '__main__':
    unittest.main()


class FreeDemoContractTests(unittest.TestCase):
    def test_static_profile_is_valid_but_local_profile_cannot_replace_it(self):
        root = Path(__file__).resolve().parents[1]
        free = (root / 'assets/free-devobs/index.html').read_text()
        local = (root / 'scripts/ai_intelligence/dashboard_assets/index.html').read_text()
        self.assertEqual(validate_free_demo(free), [])
        self.assertTrue(validate_free_demo(local))

    def test_missing_csp_absolute_script_and_credentials_are_rejected(self):
        root = Path(__file__).resolve().parents[1]
        free = (root / 'assets/free-devobs/index.html').read_text()
        for broken in [free.replace('Content-Security-Policy', 'x-disabled'),
                       free.replace('src="./dashboard.js"', 'src="/dashboard.js"'),
                       free.replace('</main>', '<input type="password"></main>')]:
            self.assertTrue(validate_free_demo(broken))


class SourceFreeDemoSmokeTests(unittest.TestCase):
    def report_candidate(self, keep_link):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            staged = Path(directory)
            copy_public_content(root, staged)
            (staged / 'assets/free-devobs/integration-acceptance.json').unlink()
            if not keep_link:
                html = staged / 'assets/free-devobs/index.html'
                html.write_text('\n'.join(line for line in html.read_text().splitlines()
                                           if 'integration-acceptance.json' not in line))
            return subprocess.run([sys.executable, str(root / 'scripts/check_site.py')],
                                  cwd=root, env={**os.environ, 'SITE_ROOT': directory},
                                  capture_output=True, text=True, timeout=15)

    def test_report_download_link_requires_its_file(self):
        result = self.report_candidate(keep_link=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Free demo integration report is missing', result.stderr)

    def test_older_free_profile_without_report_link_or_file_still_passes(self):
        result = self.report_candidate(keep_link=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_source_checkout_can_be_checked_without_generated_browser_files(self):
        root = Path(__file__).resolve().parents[1]
        generated = root / 'assets/free-devobs/dashboard.js'
        self.assertFalse(generated.exists())
        env = dict(os.environ)
        env.pop('SITE_ROOT', None)
        result = subprocess.run([sys.executable, str(root / 'scripts/check_site.py')],
                                cwd=root, env=env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Page contract and HTTP smoke checks passed.', result.stdout)
        self.assertFalse(generated.exists())
