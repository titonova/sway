"""Add/list/remove entries in the organization's central asset catalog (catalog.jsonl)."""
import argparse, json, hashlib
from src.config import configured_path,within,SwayError
from src.io import emit,main
from src.io import atomic_json

CATALOG='catalog.jsonl'

def entries(root):
    file=root/CATALOG
    if not file.exists():return []
    try:
        return [json.loads(line) for line in file.read_text(encoding='utf-8').splitlines() if line.strip()]
    except (ValueError, OSError) as e:raise SwayError('Invalid asset catalog: '+str(e))

def store(root,items):
    # Atomic JSONL replacement, no bulk image decoding.
    import os,tempfile
    fd,temp=tempfile.mkstemp(prefix='.catalog.',dir=root)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as out:
            for item in items:out.write(json.dumps(item,ensure_ascii=False)+'\n')
            out.flush();os.fsync(out.fileno())
        os.replace(temp,root/CATALOG)
    finally:
        if os.path.exists(temp):os.unlink(temp)

def run():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['list','add','remove'])
    p.add_argument('--organization','--org',required=True)
    p.add_argument('--path',help='Relative media path within the asset root')
    p.add_argument('--caption',help='Human/agent-authored truthful description (100–1000 characters for photographs)')
    p.add_argument('--tags',default='',help='Comma-separated tags')
    p.add_argument('--brand',default=None)
    p.add_argument('--type',default=None)
    p.add_argument('--license',default=None)
    p.add_argument('--approved',action='store_true',help='Human-confirmed rights/consent flag')
    a=p.parse_args();root=configured_path(a.organization,'assets_path');items=entries(root)
    if a.action=='list':emit({'ok':True,'assets':items});return
    if not a.path:raise SwayError('--path is required')
    if a.action=='remove':
        remaining=[it for it in items if it['path']!=a.path]
        store(root,remaining);emit({'ok':True,'removed':len(items)-len(remaining)});return
    file=within(root,a.path)
    if not file.is_file():raise SwayError('Asset is not a file')
    if not a.caption:raise SwayError('Caption required; agent must visually inspect or use verified description')
    if len(a.caption)>2000:raise SwayError('Caption over 2000 chars')
    obj={'id':hashlib.sha256(a.path.encode()).hexdigest()[:16],'path':a.path,'type':a.type or file.suffix[1:].lower(),
         'caption':a.caption,'tags':[x.strip() for x in a.tags.split(',') if x.strip()],
         'brand':a.brand,'license':a.license,'approved':bool(a.approved)}
    items=[it for it in items if it['path']!=a.path]+[obj]
    store(root,items);emit({'ok':True,'asset':obj})
if __name__=='__main__':main(run)
