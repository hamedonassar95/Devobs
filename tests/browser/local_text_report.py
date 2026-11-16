"""Optional real-browser check for free/local TXT downloads; no external calls.

Run after shared staging with existing Python Playwright and Chromium installed.
Both servers are disposable and bound to loopback; local input is an empty store.
"""
import asyncio
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from threading import Thread
from urllib.parse import urlparse
from playwright.async_api import async_playwright, expect

ROOT = Path(__file__).resolve().parents[2]


async def verify():
    handler = partial(SimpleHTTPRequestHandler, directory=str(ROOT / '_site'))
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix='devobs-report-browser-') as folder:
            process = subprocess.Popen(['node', 'scripts/ai_intelligence/dashboard_server.mjs',
                                        '--store', str(Path(folder) / 'empty.jsonl'), '--port', '0'],
                                       cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                address = process.stdout.readline().strip()
                assert address.startswith('ai-dashboard: http://127.0.0.1:'), address
                local_url = address.removeprefix('ai-dashboard: ')
                free_url = f'http://127.0.0.1:{server.server_port}/assets/free-devobs/'
                async with async_playwright() as p:
                    browser = await p.chromium.launch(executable_path=shutil.which('chromium'), args=['--no-sandbox'])
                    try:
                        for width in [390, 1440]:
                            for url, prefix, label in [(free_url, 'synthetic', 'عينة اصطناعية ثابتة'),
                                                        (local_url, 'local', 'لقطة محلية عند بدء الخادم')]:
                                page = await browser.new_page(viewport={'width': width, 'height': 900})
                                requests, errors = [], []
                                page.on('request', lambda request: requests.append(request.url))
                                page.on('pageerror', lambda error: errors.append(str(error)))
                                await page.goto(url, wait_until='networkidle')
                                button = page.get_by_role('button', name='تنزيل تقرير عربي TXT', exact=True)
                                await expect(button).to_be_enabled()
                                before = len(requests)
                                async with page.expect_download() as pending:
                                    await button.click()
                                download = await pending.value
                                assert download.suggested_filename.startswith(f'devobs-{prefix}-report-')
                                text = Path(await download.path()).read_text(encoding='utf-8')
                                assert label in text and 'وقت إنشاء الملف:' in text and 'الأحداث:' in text
                                assert 'البيانات المرسلة' not in text
                                assert len(requests) == before, 'TXT download must not add network requests'
                                assert all(urlparse(item).hostname == '127.0.0.1' for item in requests)
                                assert not errors, errors
                                assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                                await page.close()
                        page = await browser.new_page()
                        snapshot = json.loads((ROOT / '_site/assets/free-devobs/snapshot.json').read_text())
                        snapshot['summary']['event_count'] = 'invalid'
                        await page.route('**/snapshot.json', lambda route: route.fulfill(json=snapshot))
                        await page.goto(free_url, wait_until='networkidle')
                        await expect(page.get_by_role('button', name='تنزيل تقرير عربي TXT', exact=True)).to_be_disabled()
                        assert 'تعذر' in await page.locator('#local-report-status').inner_text()
                        await page.close()
                        page = await browser.new_page()
                        await page.route('**/snapshot.json', lambda route: route.fulfill(status=500, body='unavailable'))
                        await page.goto(free_url, wait_until='networkidle')
                        await expect(page.get_by_role('button', name='تنزيل تقرير عربي TXT', exact=True)).to_be_disabled()
                        assert 'تعذر' in await page.locator('#status').inner_text()
                        await page.close()
                        page = await browser.new_page()
                        errors = []
                        page.on('pageerror', lambda error: errors.append(str(error)))
                        html = (ROOT / '_site/assets/free-devobs/index.html').read_text()
                        html = '\n'.join(line for line in html.splitlines()
                                         if 'id="local-report-download"' not in line and 'id="local-report-status"' not in line)
                        await page.route('**/assets/free-devobs/', lambda route: route.fulfill(body=html, content_type='text/html'))
                        await page.goto(free_url, wait_until='networkidle')
                        assert await page.locator('.stage-card').count() == 7
                        assert not errors, errors
                        await page.close()
                        print('PASS TXT: free/local actual UTF-8 downloads at390/1440, correct labels, zero extra/external requests/errors/overflow; malformed counts disable export')
                        print('PASS TXT failure/compatibility: failed snapshot cannot export; older HTML/current modules retains seven stages')
                    finally:
                        await browser.close()
            finally:
                process.terminate()
                try:
                    process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate(timeout=5)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


if __name__ == '__main__':
    asyncio.run(verify())
