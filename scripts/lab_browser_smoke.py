"""Exercise the real attention laboratory; never supplies fake experiment results.

Start `.venv/bin/python -m continuum.lab serve --port 8791`, then run this.
All output goes into a fresh repository-local directory.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['TMPDIR'] = str(ROOT / '.cache/tmp')
from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8791)
    parser.add_argument('--output', type=Path, default=ROOT / 'experiments/v1/browser-smoke')
    parser.add_argument('--channel', default=None, help='For an already installed browser, e.g. chrome')
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT):
        parser.error('output must remain inside the repository')
    output.mkdir(parents=True, exist_ok=False)
    errors, checks = [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, channel=args.channel)
        page = browser.new_page(viewport={'width': 1440, 'height': 1150}, device_scale_factor=1)
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(f'http://127.0.0.1:{args.port}')
        expect(page.locator('#connection-label')).to_have_text('Local simulator connected')
        page.get_by_label('World seed').fill('11')
        page.get_by_label('Horizon · seconds').fill('20')
        page.get_by_label('Observations', exact=True).fill('8')
        page.get_by_label('Inferences', exact=True).fill('8')
        page.get_by_role('button', name='New comparison').click()
        expect(page.locator('#sim-time')).to_have_text('0.0')
        expect(page.locator('#reveal')).to_be_disabled()
        public = page.request.get(f'http://127.0.0.1:{args.port}/api/state').json()
        assert not public.get('truth'), 'truth leaked before completion'
        assert all(p.get('metrics') is None for p in public['policies']), 'hidden scoring leaked'
        checks.append('No truth or scores before completion')
        page.locator('#step').click()
        page.locator('#step').click()
        expect(page.locator('#sim-time')).not_to_have_text('0.0')
        checks.append('Step advances real simulation')
        page.get_by_role('button', name='Inject at next step').click()
        expect(page.locator('#injection-status')).to_have_text('Injection recorded for all four policies.')
        page.get_by_label('Injection', exact=True).select_option('event')
        page.get_by_role('button', name='Inject at next step').click()
        checks.append('Hidden change and public event injection')
        page.get_by_label('Speed', exact=False).select_option('1')
        page.locator('#play').click()
        expect(page.locator('#run-status')).to_have_text('running')
        page.locator('#play').click()
        expect(page.locator('#run-status')).to_have_text('paused')
        paused_time = page.locator('#sim-time').inner_text()
        page.wait_for_timeout(600)
        expect(page.locator('#sim-time')).to_have_text(paused_time)
        checks.append('Pause persists without hidden advancement')
        page.get_by_label('Speed', exact=False).select_option('12')
        page.locator('#play').click()
        expect(page.locator('#run-status')).to_have_text('completed', timeout=60000)
        expect(page.locator('#result-label')).to_have_text('MEASURED')
        expect(page.locator('#reveal')).to_be_enabled()
        page.locator('#reveal').check()
        expect(page.locator('#chart-legend')).to_contain_text('Truth')
        complete = page.request.get(f'http://127.0.0.1:{args.port}/api/state').json()
        assert complete['truth'], 'truth absent after reveal'
        assert all(p.get('metrics') is not None for p in complete['policies'])
        checks.append('Completion unlocks actual truth and scorer outputs')
        page.locator('.timeline-mark').first.click()
        expect(page.locator('#receipt-dialog')).to_be_visible()
        assert 'status' in page.locator('#receipt-json').inner_text()
        page.get_by_role('button', name='Close receipt').click()
        checks.append('Timeline opens actual operation receipt')
        page.locator('.timeline-mark.think').first.click()
        expect(page.locator('#receipt-refs button')).to_have_count(1)
        page.locator('#receipt-refs button').click()
        expect(page.locator('#receipt-title')).to_contain_text('observe')
        page.get_by_role('button', name='Close receipt').click()
        checks.append('Receipt evidence references navigate to recorded source')
        page.screenshot(path=str(output / 'desktop.png'), full_page=True)
        page.set_viewport_size({'width': 390, 'height': 844})
        page.screenshot(path=str(output / 'mobile.png'), full_page=True)
        width = page.evaluate('document.documentElement.scrollWidth')
        assert width <= 390, f'mobile horizontal overflow: {width}'
        assert page.locator('#inject').is_visible(), 'mobile injection inaccessible'
        checks.append('Responsive mobile layout and controls')
        page.locator('#replay').click()
        expect(page.locator('#mode-label')).to_have_text('Deterministic replay')
        expect(page.locator('#sim-time')).to_have_text('0.0')
        expect(page.locator('#reveal')).to_be_disabled()
        checks.append('Replay resets view without live model inference')
        assert not errors, errors
        browser.close()
    (output / 'receipt.json').write_text(json.dumps({'result':'passed','browser':args.channel or 'Chromium','checks':checks,'page_errors':errors,'checked_at_unix':time.time()},indent=2)+'\n')
    print('PASS:', ', '.join(checks))


if __name__ == '__main__':
    main()
