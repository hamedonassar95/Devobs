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
            try:
                page = await browser.new_page()

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
                            'id': 123, 'run_number': 4, 'workflow_id': 374991651,
                            'path': '.github/workflows/ci.yml', 'event': 'push', 'head_branch': 'main',
                            'head_sha': 'a' * 40, 'status': 'completed', 'conclusion': 'success',
                            'updated_at': '2026-11-16T01:02:03Z',
                            'repository': {'full_name': 'hamedonassar95/Devobs', 'private': False},
                            'head_repository': {'full_name': 'hamedonassar95/Devobs', 'private': False}}]}
                    await route.fulfill(status=200, body=json.dumps(value), headers={
                        'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'X-GitHub-Api-Version, Accept',
                        'Access-Control-Allow-Methods': 'GET, OPTIONS'})

                await page.route('**/assets/public-ci/api.mjs', delay_module)
                await page.route('https://api.github.com/**', public_api)
                await page.goto(f'http://127.0.0.1:{server.server_port}/assets/public-ci/', wait_until='commit')
                button = page.get_by_role('button', name='فحص GitHub الآن', exact=True)
                await expect(button).to_be_visible()
                assert await button.is_disabled(), 'Activation must stay disabled until its module is ready'
                assert not requests, 'Bootstrap must not fetch public API data'
                gate.set()
                await expect(button).to_be_enabled()
                await button.click()
                await expect(button).to_be_enabled(timeout=10000)
                assert len(requests) == 2, 'First enabled activation must dispatch exactly two fixed reads'
                assert await page.locator('#ci-outcome').inner_text() == 'نجحت فحوص CI لهذا التشغيل'
                print('PASS delayed module: disabled before readiness, enabled after binding; first activation works; zero live API calls')
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
