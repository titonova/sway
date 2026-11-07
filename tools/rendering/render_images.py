"""Render one or more source/*.html pages to output/*.png using Chromium."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright
from src.config import SwayError
from src.posts import get,ensure_version
from src.browser import launch,create_page
from src.io import emit,main

def render_sources(source:Path,output:Path,width:int,height:int,asset_root=None):
    files=sorted(source.glob('*.html'))
    if not files:raise SwayError('No .html files in '+str(source))
    output.mkdir(parents=True,exist_ok=True)
    artifacts=[]
    with sync_playwright() as p:
        browser=launch(p)
        try:
            for file in files:
                page,context=create_page(browser,file,width,height,asset_root)
                try:
                    result=output/(file.stem+'.png')
                    page.screenshot(path=str(result),full_page=False,animations='disabled')
                    artifacts.append({'source':str(file),'output':str(result),'width':width,'height':height})
                finally:context.close()
        finally:browser.close()
    return artifacts

def run():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--organization','--org',required=True);p.add_argument('--post',required=True)
    p.add_argument('--version');p.add_argument('--width',type=int,default=1080);p.add_argument('--height',type=int,default=1350)
    a=p.parse_args()
    if not (100<=a.width<=4096 and 100<=a.height<=4096):raise SwayError('Dimensions must be within 100..4096')
    path,state=get(a.organization,a.post);v=ensure_version(path,a.version or state['current_version'])
    from src.config import configured_path
    out=render_sources(v/'source',v/'output',a.width,a.height,configured_path(a.organization,'assets_path'))
    emit({'ok':True,'post_id':a.post,'version':v.name,'renders':out,
          'next_step':'Open and visually inspect EVERY rendered PNG; fix defects and rerun before approval (max 3 autonomous revision rounds). Minor corrections stay in this version.'})
if __name__=='__main__':main(run)
