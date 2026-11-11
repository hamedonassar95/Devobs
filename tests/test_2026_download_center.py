"""Checks for the 2026 static Devobs download-center design."""
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

PAGE = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")


class Reader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class DownloadsTests(unittest.TestCase):
    def test_two_native_cards_are_not_misrepresented_as_releases(self):
        html = Reader()
        html.feed(PAGE)
        cards = [a for t, a in html.tags if t == "article" and "download-card" in a.get("class", "")]
        self.assertEqual(len(cards), 3)
        unavailable = [
            a for t, a in html.tags
            if t == "span" and a.get("aria-disabled") == "true"
        ]
        self.assertEqual(len(unavailable), 2)
        self.assertIn("لا يوجد APK معتمد", PAGE)
        self.assertIn("لا يوجد مثبت معتمد", PAGE)

    def test_no_native_binary_links_or_automatic_file_downloads(self):
        html = Reader()
        html.feed(PAGE)
        hrefs = [a["href"] for _, a in html.tags if "href" in a]
        self.assertNotIn("", hrefs)
        for href in hrefs:
            self.assertNotRegex(href.lower(), r"\.(?:apk|aab|exe|msi|msix)(?:[?#]|$)")
            self.assertNotRegex(href.lower(), r"^(?:javascript|data|file):")
        self.assertIn("https://github.com/hamedonassar95/Devobs/releases", hrefs)
        self.assertFalse(any(t == "script" for t, _ in html.tags))

    def test_public_site_does_not_claim_live_telemetry(self):
        self.assertIn("DESIGN PREVIEW", PAGE)
        self.assertIn("وليس تقريرًا عن CI", PAGE)
        self.assertIn("لا تتضمن لوحة تشغيل حية", PAGE)
        self.assertEqual(len(re.findall(r"<main\b", PAGE)), 1)


if __name__ == "__main__":
    unittest.main()
