"""Machine-readable responses and crash-safe metadata writes."""
from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
from .config import SwayError

def emit(data):
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
        except Exception:
            pass
    try:
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    except (UnicodeEncodeError, OSError):
        print(json.dumps(data, ensure_ascii=True, indent=2, default=str))

def main(fn):
    try:
        fn()
    except (SwayError, ValueError, FileNotFoundError, RuntimeError) as e:
        emit({'ok':False,'error':str(e)})
        sys.exit(1)
    except Exception as e:
        # Last-resort structured failure: prevent giant tracebacks and accidental token exposure.
        emit({'ok':False,'error_type':type(e).__name__, 'error':str(e)[:1200]})
        sys.exit(1)

def read_json(path:Path, fallback=None):
    if not path.exists():
        if fallback is not None:
            return fallback
        raise SwayError(f'JSON file missing: {path}')
    try: return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,json.JSONDecodeError) as e: raise SwayError(f'Invalid JSON at {path}: {e}')

def atomic_json(path:Path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.', suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(data,f,indent=2,ensure_ascii=False)
            f.write('\n');f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
