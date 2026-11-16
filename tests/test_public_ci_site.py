"""Exercise the trusted checker against real staged public-CI candidates."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from scripts.stage_site import copy_public_content

ROOT = Path(__file__).resolve().parents[1]


class PublicCiSiteTests(unittest.TestCase):
    def check_candidate(self, mutate=None):
        with tempfile.TemporaryDirectory() as directory:
            staged = Path(directory)
            copy_public_content(ROOT, staged)
            if mutate:
                mutate(staged)
            return subprocess.run([sys.executable, str(ROOT / 'scripts/check_site.py')],
                                  cwd=ROOT, env={**os.environ, 'SITE_ROOT': directory},
                                  capture_output=True, text=True, timeout=15)

    def test_complete_public_ci_candidate_is_deliverable(self):
        result = self.check_candidate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_each_client_file_and_shared_stylesheet_are_required(self):
        for path in ['assets/public-ci/index.html', 'assets/public-ci/api.mjs',
                     'assets/public-ci/app.mjs', 'assets/free-devobs/dashboard.css']:
            with self.subTest(path=path):
                result = self.check_candidate(lambda root: (root / path).unlink())
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Public CI assets missing', result.stderr)

    def test_advertised_page_cannot_be_silently_omitted(self):
        def remove_page(root):
            shutil.rmtree(root / 'assets/public-ci')
            index = root / 'index.html'
            index.write_text(index.read_text().replace('</main>', '<a href="assets/public-ci/">Public CI</a></main>'))
        result = self.check_candidate(remove_page)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Public CI assets missing', result.stderr)

    def test_extra_api_origin_inline_code_and_credentials_fail_closed(self):
        for before, after in [('connect-src https://api.github.com', 'connect-src https://api.github.com https://other.example.invalid'),
                              ('src="./app.mjs"', 'src="https://other.example.invalid/app.mjs"'),
                              ('</main>', '<input type="password"></main>'),
                              ('<button id=', '<button onclick="doSomething()" id=')]:
            with self.subTest(after=after):
                def broken(root):
                    page = root / 'assets/public-ci/index.html'
                    page.write_text(page.read_text().replace(before, after))
                result = self.check_candidate(broken)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Public CI profile', result.stderr)

    def test_older_profile_with_no_public_ci_page_or_link_remains_valid(self):
        def older(root):
            shutil.rmtree(root / 'assets/public-ci')
            for path in ['index.html', 'assets/free-devobs/index.html']:
                page = root / path
                page.write_text('\n'.join(line for line in page.read_text().splitlines() if 'public-ci/' not in line))
        result = self.check_candidate(older)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
