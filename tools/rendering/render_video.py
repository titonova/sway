"""Render deterministic browser animation frames into MP4 using Chromium and FFmpeg.

HTML animation contract: optional `window.swayFrame(seconds)` function sets state;
otherwise seek and pause document.getAnimations() at the specified time.
"""
import argparse, shutil, subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright
from src.posts import get,ensure_version
from src.config import SwayError
from src.browser import launch,create_page
from src.io import emit,main

def find_ffmpeg_executable() -> str | None:
    import os
    configured = os.environ.get('SWAY_FFMPEG_EXECUTABLE')
    if configured and Path(configured).is_file():
        return configured
    found = shutil.which('ffmpeg')
    if found:
        return found
    local_app = os.environ.get('LOCALAPPDATA', '')
    home = Path.home()
    candidates = [
        *Path(local_app).glob('ms-playwright/ffmpeg-*/ffmpeg*.exe'),
        *Path(home).glob('.cache/ms-playwright/ffmpeg-*/ffmpeg*'),
        *Path(home).glob('Library/Caches/ms-playwright/ffmpeg-*/ffmpeg*'),
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    return None

def render(html,output,duration,fps,width,height,audio=None,asset_root=None):
    ffmpeg_exe = find_ffmpeg_executable()
    if not ffmpeg_exe: raise SwayError('FFmpeg missing. Install ffmpeg to create MP4')
    if fps<1 or fps>60 or duration<=0 or duration>120:raise SwayError('FPS range 1..60; duration max 120 seconds')
    if width%2 or height%2:raise SwayError('H264 dimensions must be even')
    out=output/(html.stem+'.mp4');output.mkdir(parents=True,exist_ok=True)
    cmd=[ffmpeg_exe,'-hide_banner','-loglevel','error','-y','-f','image2pipe','-vcodec','png','-framerate',str(fps),'-i','pipe:0']
    if audio:
        if not audio.is_file():raise SwayError('Audio file not found')
        cmd.extend(['-i',str(audio),'-shortest'])
    cmd.extend(['-c:v','libx264','-preset','veryfast','-pix_fmt','yuv420p','-movflags','+faststart'])
    if audio:cmd.extend(['-c:a','aac','-b:a','160k'])
    cmd.append(str(out))
    count=round(duration*fps)
    previews=[]
    with sync_playwright() as p:
        browser=launch(p)
        try:
            page,context=create_page(browser,html,width,height,asset_root)
            proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                for n in range(count):
                    seconds=n/fps
                    page.evaluate('''(s) => {
                      if (typeof window.swayFrame === 'function') window.swayFrame(s);
                      else { document.getAnimations().forEach(a => { a.pause(); a.currentTime=s*1000; }); }
                    }''', seconds)
                    frame=page.screenshot(type='png',animations='allow')
                    proc.stdin.write(frame)
                    if n in {0,count//2,count-1}:
                        preview=output/(html.stem+f'_preview_{n:04d}.png');preview.write_bytes(frame)
                        previews.append(str(preview))
                proc.stdin.close()
                error=proc.stderr.read().decode(errors='replace');rc=proc.wait()
                if rc:raise SwayError('ffmpeg failed: '+error[-1500:])
            except Exception:
                proc.kill();proc.wait()
                out.unlink(missing_ok=True)
                raise
            finally:context.close()
        finally:browser.close()
    return {'video':str(out),'duration_seconds':duration,'fps':fps,'preview_frames':previews}

def run():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--organization','--org',required=True)
    p.add_argument('--post',required=True);p.add_argument('--version');p.add_argument('--html',default='video.html')
    p.add_argument('--duration',type=float,default=4);p.add_argument('--fps',type=int,default=15)
    p.add_argument('--width',type=int,default=1080);p.add_argument('--height',type=int,default=1920)
    p.add_argument('--audio',help='Relative path inside the post version source directory')
    a=p.parse_args();path,state=get(a.organization,a.post);v=ensure_version(path,a.version or state['current_version'])
    file=v/'source'/a.html
    if not file.is_file() or not file.resolve().is_relative_to((v/'source').resolve()):raise SwayError('Video HTML missing inside source directory')
    audio=None
    if a.audio:
        audio=(v/'source'/a.audio).resolve()
        if not audio.is_relative_to((v/'source').resolve()):raise SwayError('Audio must be inside source directory')
    from src.config import configured_path
    result=render(file,v/'output',a.duration,a.fps,a.width,a.height,audio,configured_path(a.organization,'assets_path'))
    emit({'ok':True,'render':result,'next_step':'Visually review preview frames AND the actual MP4, including pacing, text, audio and transitions.'})
if __name__=='__main__':main(run)
