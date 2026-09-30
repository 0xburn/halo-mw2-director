"""Local Chrome smoke check. Start manage.py serve before running this."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json
import argparse
parser=argparse.ArgumentParser();parser.add_argument("--headed",action="store_true");args=parser.parse_args()

ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=not args.headed)
    page = browser.new_page(viewport={'width': 1280, 'height': 720}, accept_downloads=True)
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto('http://127.0.0.1:8765')
    page.wait_for_function('window.sceneDirector !== undefined')
    page.locator('#director-open').click()
    assert page.evaluate('sceneDirector.cast.size') == 7
    page.locator('#red-count').fill('5')
    page.locator('#blue-count').fill('4')
    page.locator('#cast-weapon').select_option('sniper')
    page.locator('#scene-build').click()
    assert page.evaluate('sceneDirector.cast.size') == 9
    page.evaluate('sceneDirector.seek(6)')
    page.screenshot(path=str(ROOT / 'previews/director-mac.png'))
    before = page.evaluate('JSON.stringify(sceneDirector.state.actors)')
    page.evaluate('sceneDirector.seek(12); sceneDirector.seek(6)')
    assert page.evaluate('JSON.stringify(sceneDirector.state.actors)') == before
    page.locator('#scene-play').click()
    page.wait_for_timeout(400)
    assert page.evaluate('sceneDirector.time') > 6
    page.locator('#scene-play').click()
    with page.expect_download(timeout=45000) as download:
        page.locator('#scene-record').click()
    video = download.value
    video.save_as(str(ROOT / 'previews/director-mac.webm'))
    assert (ROOT / 'previews/director-mac.webm').stat().st_size > 10000
    page.locator('#director-close').click()
    page.wait_for_timeout(500)
    page.locator('#play').click()
    page.wait_for_timeout(1500)
    print('Pointer capture:',page.evaluate('document.pointerLockElement !== null'),page.locator('#notice').inner_text(),flush=True)
    page.wait_for_function('document.pointerLockElement !== null',timeout=5000)
    page.keyboard.press('1')
    page.mouse.click(640,360)
    page.wait_for_timeout(200)
    assert page.locator('#ammo').inner_text() == '11'
    page.keyboard.press('2')
    assert page.locator('#ammo').inner_text() == '4'
    page.keyboard.press('3')
    assert page.locator('#ammo').inner_text() == '2'
    page.keyboard.press('v')
    page.keyboard.press('Escape')
    assert not errors, errors
    print(json.dumps({'browser': browser.version, 'actors':9,'recording':str(ROOT/'previews/director-mac.webm'),'errors':errors}))
    browser.close()
