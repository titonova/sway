"""One post = one portable, versioned directory with a single post.json manifest.
Minor revisions edit files in place. Only intentional major revisions copy a new version.
"""
from __future__ import annotations
import hashlib, json, shutil, uuid
from datetime import datetime, timezone
from pathlib import Path
from .config import configured_path, organization, brand, safe_slug, within, SwayError
from .io import read_json, atomic_json

def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')

def home(org: str, post_id: str, create=False) -> Path:
    safe_slug(post_id,'post ID')
    root=configured_path(org,'posts_path',create=create)
    return within(root,post_id,must_exist=not create)

def get(org: str, post_id: str):
    path=home(org,post_id)
    return path,read_json(path/'post.json')

def save(path:Path, data:dict):
    data['updated_at']=now()
    atomic_json(path/'post.json',data)

def ensure_version(path:Path,v:str):
    safe_slug(v,'version')
    root=path/'versions'
    loc=within(root,v,must_exist=False)
    if not loc.is_dir(): raise SwayError('Post version does not exist: '+v)
    return loc

def create(org: str, brand_id: str, post_id:str|None=None):
    brand(org,brand_id)
    post_id=safe_slug(post_id or 'post_'+uuid.uuid4().hex[:12],'post ID')
    path=home(org,post_id,create=True)
    if (path/'post.json').exists(): raise SwayError('Post ID already exists: '+post_id)
    v=path/'versions'/'v001'
    (v/'source').mkdir(parents=True,exist_ok=True)
    (v/'output').mkdir(parents=True,exist_ok=True)
    (v/'caption.md').write_text('',encoding='utf-8')
    state={'post_id':post_id,'organization':org,'brand':brand_id,'created_at':now(),
           'updated_at':now(),'status':'draft','current_version':'v001','versions':['v001'],
           'recommendation':None,'highlight':{'enabled':False,'note':'','tags':[]},
           'approval':None,'placements':[],'publication_attempts':[]}
    save(path,state)
    return path,state

def major(org,post_id,reason='major creative revision'):
    path,state=get(org,post_id)
    existing=state['current_version']
    next_name=f'v{len(state["versions"])+1:03d}'
    shutil.copytree(ensure_version(path,existing),path/'versions'/next_name)
    state['versions'].append(next_name);state['current_version']=next_name
    state['status']='draft';state['approval']=None
    state.setdefault('revision_notes',[]).append({'from':existing,'to':next_name,'reason':reason,'at':now()})
    save(path,state)
    return path,state

def manifest(org,post_id,version=None):
    path,state=get(org,post_id)
    v=ensure_version(path,version or state['current_version'])
    caption=v/'caption.md'
    files=[]
    for bucket in ('source','output'):
        files.extend(sorted(p for p in (v/bucket).rglob('*') if p.is_file()))
    files.append(caption)
    h=hashlib.sha256()
    for f in files:
        rel=f.relative_to(v).as_posix()
        h.update(rel.encode());h.update(b'\x00');h.update(f.read_bytes());h.update(b'\x00')
    return {'version':v.name,'sha256':h.hexdigest(),
            'files':[str(p.relative_to(path)) for p in files],
            'rendered_media':[str(p.relative_to(path)) for p in files if p.is_relative_to(v/'output')]}

def approve_record(org,post_id,channels,due_at,user_message=None):
    path,state=get(org,post_id)
    fingerprint=manifest(org,post_id)
    if not fingerprint['rendered_media']:
        raise SwayError('Cannot approve without final rendered media')
    if not (path/'versions'/state['current_version']/'caption.md').read_text(encoding='utf-8').strip():
        raise SwayError('Cannot approve without a caption')
    if not user_message or not user_message.strip():
        raise SwayError('Approval requires the verbatim user approval message')
    state['approval']={'version':fingerprint['version'],'sha256':fingerprint['sha256'],
                      'channels':channels,'due_at':due_at,'approved_at':now(),
                      'user_message':user_message}
    state['status']='approved'
    save(path,state)
    return state

def check_approval(org,post_id,channel,due_at):
    path,state=get(org,post_id)
    approval=state.get('approval')
    if not approval:
        raise SwayError('Content has not been explicitly approved')
    if channel not in approval['channels']:
        raise SwayError('This destination was not in the human-approved channel set')
    if due_at!=approval.get('due_at'):
        raise SwayError('Publication time differs from the approved time; obtain new approval')
    if approval['version']!=state['current_version'] or approval['sha256']!=manifest(org,post_id)['sha256']:
        raise SwayError('Approved content was modified; re-approve the final files and caption')
    return path,state

def add_placement(org,post_id,channel,status,provider=None,provider_post_id=None,
                  platform_post_id=None,published_at=None,url=None):
    path,state=get(org,post_id)
    if status not in ('queued','scheduled','published','failed','unknown'):
        raise SwayError('Invalid placement status')
    if status=='published' and not published_at:
        raise SwayError('Published placements need a verified publication timestamp')
    if published_at:
        try:
            parsed=datetime.fromisoformat(published_at.replace('Z','+00:00'))
            if parsed.tzinfo is None: raise ValueError('missing timezone')
            if parsed>datetime.now(timezone.utc): raise ValueError('timestamp lies in future')
        except (ValueError,TypeError): raise SwayError('published_at must be valid non-future timezone-aware ISO-8601 timestamp')
    existing=next((p for p in state['placements'] if p['channel']==channel),None)
    if existing and existing['status']=='published' and status!='published':
        raise SwayError('Cannot downgrade a confirmed publication')
    if existing and existing['status']=='published' and published_at!=existing['published_at']:
        raise SwayError('Conflicting publication timestamp; manual correction required')
    record={k:v for k,v in {'channel':channel,'status':status,'provider':provider,
            'provider_post_id':provider_post_id,'platform_post_id':platform_post_id,
            'published_at':published_at,'url':url,'updated_at':now()}.items() if v is not None}
    if existing:
        existing.update(record)
    else:
        state['placements'].append(record)
    statuses=[x['status'] for x in state['placements']]
    if statuses and all(x=='published' for x in statuses):state['status']='published'
    elif any(x in ('scheduled','queued') for x in statuses):state['status']='scheduled'
    elif any(x=='published' for x in statuses):state['status']='partially_published'
    elif any(x=='failed' for x in statuses):state['status']='publication_failed'
    save(path,state)
    return state
