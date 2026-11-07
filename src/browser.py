"""Browser renderer for trusted local HTML, with local media inlined as data URIs.

Some coding-harness environments forbid navigation even to file:// or localhost.
set_content works there. We inline local assets before set_content, while blocking
external requests for repeatability and to avoid fetching unapproved stock media.
"""
from __future__ import annotations
import base64,mimetypes,os,re,shutil,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
from src.config import SwayError

URL_RE=re.compile(r'(?i)\b(?P<attr>src|href|poster)\s*=\s*(?P<quote>[\'\"])(?P<path>[^\'\"]+)(?P=quote)')
CSS_RE=re.compile(r'url\(\s*(?P<quote>[\'\"]?)(?P<path>[^\)\'\"]+)(?P=quote)\s*\)',re.IGNORECASE)

def find_browser_executable() -> str | None:
    configured = os.environ.get('SWAY_CHROMIUM_EXECUTABLE')
    if configured and Path(configured).is_file():
        return configured

    for name in ('chromium', 'google-chrome', 'chrome', 'msedge', 'edge', 'chromium-browser'):
        found = shutil.which(name)
        if found and Path(found).is_file():
            return found

    candidates: list[Path] = []
    if sys.platform == 'win32':
        prog = os.environ.get('PROGRAMFILES', r'C:\Program Files')
        prog_x86 = os.environ.get('PROGRAMFILES(X86)', r'C:\Program Files (x86)')
        local_app = os.environ.get('LOCALAPPDATA', '')
        candidates = [
            Path(prog) / r'Google\Chrome\Application\chrome.exe',
            Path(prog_x86) / r'Google\Chrome\Application\chrome.exe',
            Path(local_app) / r'Google\Chrome\Application\chrome.exe',
            Path(prog_x86) / r'Microsoft\Edge\Application\msedge.exe',
            Path(prog) / r'Microsoft\Edge\Application\msedge.exe',
        ]
    elif sys.platform == 'darwin':
        candidates = [
            Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
            Path('/Applications/Chromium.app/Contents/MacOS/Chromium'),
            Path('/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'),
        ]
    else:
        candidates = [
            Path('/usr/bin/google-chrome'),
            Path('/usr/bin/chromium'),
            Path('/usr/bin/chromium-browser'),
            Path('/snap/bin/chromium'),
        ]

    for p in candidates:
        if p.is_file():
            return str(p)
    return None

def launch(playwright):
    exe = find_browser_executable()
    args = [
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-extensions',
        '--disable-background-networking',
    ]
    options = {'headless': True, 'args': args}
    if exe:
        options['executable_path'] = exe
    try:
        return playwright.chromium.launch(**options)
    except Exception as exc:
        if exe:
            try:
                return playwright.chromium.launch(headless=True, args=args)
            except Exception:
                pass
        raise SwayError('Chromium unavailable. Install browser with `python -m playwright install chromium` or set SWAY_CHROMIUM_EXECUTABLE. ' + str(exc))

def inline_local_assets(document:Path, roots=()) -> str:
    html=document.read_text(encoding='utf-8')
    roots=[document.parent.resolve(),*(p.resolve() for p in roots)]
    def resource(path:str):
        # Fragment URLs, media data URIs, and destination anchors aren't resources to inline.
        if path.startswith(('data:','#','about:','mailto:','tel:')):
            return path
        if path.startswith(('http://','https://','//')):
            return path # browser explicitly blocks external requests
        file=(document.parent/path).resolve()
        if not file.is_file():
            stripped = path.lstrip('/\\')
            unprefixed = stripped[7:] if stripped.startswith(('assets/', 'assets\\')) else stripped
            for r in roots:
                for cand_name in (stripped, unprefixed):
                    cand = (r / cand_name).resolve()
                    if cand.is_file() and cand.is_relative_to(r):
                        file = cand
                        break
                if file.is_file():
                    break
        if not any(file.is_relative_to(root) for root in roots):
            raise SwayError(f'Render references file outside source/asset roots: {path}')
        if not file.is_file():
            raise SwayError(f'Referenced local asset missing: {path}')
        # Never accidentally inline multi-GB video sources; animation tool targets HTML frames.
        if file.stat().st_size>35_000_000:
            raise SwayError(f'Local asset too large to inline (>35MB): {path}')
        mime=mimetypes.guess_type(str(file))[0] or 'application/octet-stream'
        return 'data:'+mime+';base64,'+base64.b64encode(file.read_bytes()).decode('ascii')
    def replace_attr(m):
        original=m.group('path')
        # Hyperlinks are not asset loads; only href to CSS files is inlined.
        if m.group('attr').lower()=='href' and not original.lower().split('?',1)[0].endswith('.css'):
            return m.group(0)
        return m.group('attr')+'='+m.group('quote')+resource(original)+m.group('quote')
    html=URL_RE.sub(replace_attr,html)
    def replace_css(m):
        return 'url("'+resource(m.group('path').strip())+'")'
    return CSS_RE.sub(replace_css,html)

def create_page(browser, html:Path, width:int, height:int, asset_root:Path|None=None):
    context=browser.new_context(viewport={'width':width,'height':height},device_scale_factor=1,java_script_enabled=True)
    page=context.new_page()
    def guard(route):
        if route.request.url.startswith(('data:','about:')):route.continue_()
        else:route.abort()
    page.route('**/*',guard)
    source=inline_local_assets(html,roots=[asset_root] if asset_root else [])
    page.set_content(source,wait_until='load',timeout=30000)
    page.evaluate('document.fonts.ready')
    page.wait_for_timeout(40)
    return page,context
