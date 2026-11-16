"""Optional real-browser regression: a slow module must not lose first activation.

Run after staging with Python Playwright and Chromium available. No GitHub API
request leaves the browser: both API routes are served controlled fixture data.
"""
import asyncio
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
from threading import Thread
from playwright.async_api import async_playwright, expect

ROOT = Path(__file__).resolve().parents[2]


async def verify():
    handler = partial(SimpleHTTPRequestHandler, directory=str(ROOT / '_site'))
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(executable_path=shutil.which('chromium'), headless=True,
                                                       args=['--no-sandbox'])
            gate = asyncio.Event()
            requests = []
            mode = 'success'
            try:
                page = await browser.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))

                async def delay_module(route):
                    await gate.wait()
                    await route.continue_()

                async def public_api(route):
                    if route.request.method == 'OPTIONS':
                        await route.fulfill(status=204, headers={
                            'Access-Control-Allow-Origin': '*',
                            'Access-Control-Allow-Headers': 'X-GitHub-Api-Version, Accept',
                            'Access-Control-Allow-Methods': 'GET, OPTIONS'})
                        return
                    if route.request.method == 'GET':
                        requests.append(route.request.url)
                    prefix = 'https://api.github.com/repos/hamedonassar95/Devobs'
                    assert route.request.url in [prefix + '/branches/main', prefix + '/actions/workflows/ci.yml/runs?branch=main&event=push&per_page=1']
                    value = {'name': 'main', 'commit': {'sha': 'a' * 40}}
                    if '/actions/workflows/' in route.request.url:
                        value = {'total_count': 1, 'workflow_runs': [{
                            'id': 123, 'run_number': 4, 'run_attempt': 1, 'workflow_id': 374991651,
                            'path': '.github/workflows/ci.yml', 'event': 'push', 'head_branch': 'main',
                            'head_sha': 'a' * 40, 'status': 'completed', 'conclusion': 'success',
                            'created_at': '2026-11-16T01:00:00Z', 'updated_at': '2026-11-16T01:02:03Z',
                            'repository': {'full_name': 'hamedonassar95/Devobs', 'private': False},
                            'head_repository': {'full_name': 'hamedonassar95/Devobs', 'private': False}}]}
                        if mode == 'stale':
                            value['workflow_runs'][0]['head_sha'] = 'b' * 40
                        if mode == 'running':
                            value['workflow_runs'][0].update(status='in_progress', conclusion=None)
                        if mode == 'missing_attempt':
                            del value['workflow_runs'][0]['run_attempt']
                    await route.fulfill(status=500 if mode == 'error' else 200, body=json.dumps(value), headers={
                        'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'X-GitHub-Api-Version, Accept',
                        'Access-Control-Allow-Methods': 'GET, OPTIONS'})

                await page.route('**/assets/public-ci/api.mjs', delay_module)
                await page.route('https://api.github.com/**', public_api)
                await page.goto(f'http://127.0.0.1:{server.server_port}/assets/public-ci/', wait_until='commit')
                button = page.get_by_role('button', name='فحص GitHub الآن', exact=True)
                download_button = page.get_by_role('button', name='تنزيل حدث CI محليًا', exact=True)
                await expect(button).to_be_visible()
                await expect(download_button).to_be_visible()
                assert await download_button.is_disabled(), 'No export before a successful public read'
                assert await button.is_disabled(), 'Activation must stay disabled until its module is ready'
                assert not requests, 'Bootstrap must not fetch public API data'
                gate.set()
                await expect(button).to_be_enabled()
                await button.click()
                await expect(button).to_be_enabled(timeout=10000)
                assert len(requests) == 2, 'First enabled activation must dispatch exactly two fixed reads'
                assert await page.locator('#ci-outcome').inner_text() == 'نجحت فحوص CI لهذا التشغيل'
                await expect(download_button).to_be_enabled()
                async with page.expect_download() as pending:
                    await download_button.click()
                download = await pending.value
                assert download.suggested_filename == 'devobs-public-ci.cloudevents.jsonl'
                event = json.loads(Path(await download.path()).read_text())
                assert event['id'] == 'github-ci-123-attempt-1'
                assert event['data'] == {'workflow': 'CI', 'job': 'workflow-summary-run-123-attempt-1',
                                         'conclusion': 'success', 'commit_sha': 'a' * 40}
                assert event['time'] == '2026-11-16T01:00:00.000Z'
                assert len(requests) == 2, 'Download must not perform another API read'
                for mode in ['stale', 'running', 'missing_attempt', 'error']:
                    await button.click()
                    await expect(button).to_be_enabled(timeout=10000)
                    await expect(download_button).to_be_disabled()
                assert await page.locator('#ci-evidence').is_hidden(), 'Failure must clear previous evidence'
                assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                assert not errors, errors
                # Trusted validation accepts older HTML; current modules must keep
                # its original reader working even without optional export controls.
                async def legacy_page(route):
                    html = (ROOT / '_site/assets/public-ci/index.html').read_text()
                    html = '\n'.join(line for line in html.splitlines()
                                     if 'id="download-public-ci"' not in line and 'id="ci-download-note"' not in line)
                    await route.fulfill(body=html, content_type='text/html')
                await page.route('**/assets/public-ci/', legacy_page)
                mode = 'success'
                previous = len(requests)
                await page.reload()
                await expect(button).to_be_enabled()
                assert len(requests) == previous
                await button.click()
                await expect(button).to_be_enabled(timeout=10000)
                assert len(requests) == previous + 2
                assert await page.locator('#ci-outcome').inner_text() == 'نجحت فحوص CI لهذا التشغيل'
                assert not errors, errors
                print('PASS bootstrap/export: first activation, exact local file, zero extra reads, stale/running/missing-attempt/error clearing; zero live API calls')
                print('PASS older HTML/current modules: original public reader remains usable without export controls')
            finally:
                gate.set()
                await asyncio.sleep(0.05)
                await browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


if __name__ == '__main__':
    asyncio.run(verify())
