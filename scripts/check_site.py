"""Project-specific HTML checks and local HTTP smoke test; standard library only."""
from functools import partial
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import re
import threading
import tempfile
from urllib.request import urlopen

if __package__:
    from .stage_site import FREE_DEMO_CLIENT_FILES, copy_public_content
else:
    from stage_site import FREE_DEMO_CLIENT_FILES, copy_public_content

ROOT = Path(os.environ.get("SITE_ROOT", Path(__file__).resolve().parents[1])).resolve()


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.doctype = False
        self.title = []
        self.in_title = False

    def handle_decl(self, decl):
        self.doctype |= decl.lower() == 'doctype html'

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag == 'title':
            self.in_title = True

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data)


def validate(source):
    page = Page()
    page.feed(source)
    page.close()
    errors = []
    if re.search(r'^(?:<{7}|={7}|>{7})(?:\s|$)', source, re.MULTILINE):
        errors.append('Unresolved merge conflict marker')
    if not page.doctype:
        errors.append('Missing HTML5 doctype')
    for tag in ('html', 'head', 'body', 'title', 'main', 'h1'):
        if sum(name == tag for name, _ in page.tags) != 1:
            errors.append(f'Expected exactly one {tag} element')
    if not ''.join(page.title).strip():
        errors.append('Page title is empty')
    for tag, attrs in page.tags:
        if tag == 'html' and (attrs.get('lang') != 'ar' or attrs.get('dir') != 'rtl'):
            errors.append('Root must use lang="ar" and dir="rtl"')
    metas = [attrs for tag, attrs in page.tags if tag == 'meta']
    if not any((attrs.get('charset') or '').lower() == 'utf-8' for attrs in metas):
        errors.append('Missing UTF-8 charset')
    if not any(attrs.get('name') == 'viewport' and 'width=device-width' in (attrs.get('content') or '').replace(' ', '') for attrs in metas):
        errors.append('Missing responsive viewport')
    ids = [attrs['id'] for _, attrs in page.tags if attrs.get('id')]
    if len(ids) != len(set(ids)):
        errors.append('Duplicate element IDs')
    for _, attrs in page.tags:
        for target in (attrs.get('aria-labelledby') or '').split():
            if target not in ids:
                errors.append(f'Missing aria-labelledby target: {target}')
    return errors


def validate_free_demo(source):
    errors = validate(source)
    page = Page()
    page.feed(source)
    html = [attrs for tag, attrs in page.tags if tag == 'html']
    if not html or html[0].get('data-mode') != 'free-demo':
        errors.append('Free demo profile marker missing')
    expected_csp = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'none'"
    policies = [attrs.get('content') for tag, attrs in page.tags if tag == 'meta'
                and attrs.get('http-equiv', '').lower() == 'content-security-policy']
    if policies != [expected_csp]:
        errors.append('Free demo requires its self-only CSP')
    scripts = [attrs for tag, attrs in page.tags if tag == 'script']
    if scripts != [{'type': 'module', 'src': './dashboard.js'}]:
        errors.append('Free demo requires its relative browser entrypoint')
    for _, attrs in page.tags:
        if (attrs.get('type') == 'password' or attrs.get('id', '').startswith('google-')
                or any(key.startswith('on') for key in attrs)):
            errors.append('Free demo must not contain credentials or cloud controls')
        if any(attrs.get(key, '').startswith(('http:', 'https:', '//', 'javascript:')) for key in ('href', 'src')):
            errors.append('Free demo must use local relative resources')
    return errors


def smoke_test(root):
    handler = partial(SimpleHTTPRequestHandler, directory=str(root))
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        expected = (root / 'index.html').read_bytes()
        paths = ['/', '/index.html']
        demo = root / 'assets/free-devobs'
        if demo.exists():
            paths += ['/assets/free-devobs/' + name for name in ('index.html', 'snapshot.json', *FREE_DEMO_CLIENT_FILES)]
        for path in paths:
            expected = (root / path.lstrip('/')).read_bytes() if path != '/' else expected
            with urlopen(f'http://127.0.0.1:{server.server_port}{path}', timeout=5) as response:
                suffix = Path(path).suffix
                valid_types = {'application/javascript', 'text/javascript'} if suffix in ('.js', '.mjs') else {
                    'text/css' if suffix == '.css' else 'application/json' if suffix == '.json' else 'text/html'}
                if response.status != 200 or response.headers.get_content_type() not in valid_types or response.read() != expected:
                    raise RuntimeError(f'HTTP smoke test failed: {path}')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def main():
    errors = validate((ROOT / 'index.html').read_text(encoding='utf-8'))
    demo = ROOT / 'assets/free-devobs/index.html'
    if demo.exists():
        errors += validate_free_demo(demo.read_text(encoding='utf-8'))
    if errors:
        raise SystemExit('\n'.join(errors))
    if demo.exists() and (ROOT / 'scripts/ai_intelligence/dashboard_assets').exists():
        # A source checkout has no generated client files under assets/. Project
        # the same reviewed public tree without executing candidate code or
        # inventing a release SHA/manifest for this temporary quality check.
        with tempfile.TemporaryDirectory(prefix='devobs-site-check-') as directory:
            staged = Path(directory)
            copy_public_content(ROOT, staged)
            smoke_test(staged)
    else:
        smoke_test(ROOT)
    print('Page contract and HTTP smoke checks passed.')


if __name__ == '__main__':
    main()
