"""Create/list/show/major-version/curate portable post folders."""
import argparse
from pathlib import Path
from src.config import configured_path,resolve_brand,SwayError
from src.io import emit,main
from src.posts import create,get,major,save,manifest

def run():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['create','list','show','major-version','highlight','unhighlight'])
    p.add_argument('--organization','--org',required=True);p.add_argument('--brand')
    p.add_argument('--post');p.add_argument('--reason',default='major creative change')
    p.add_argument('--note',default='');p.add_argument('--tags',default='')
    a=p.parse_args()
    if a.action=='create':
        brand_id=resolve_brand(a.organization,a.brand)
        path,state=create(a.organization,brand_id,a.post)
        v=path/'versions'/'v001'
        emit({'ok':True,'path':str(path),'post':state,
              'version_dir':str(v),'source_dir':str(v/'source'),
              'output_dir':str(v/'output'),'caption_path':str(v/'caption.md')})
        return
    if a.action=='list':
        root=configured_path(a.organization,'posts_path',create=True)
        items=[]
        for f in sorted(root.glob('*/post.json')):
            try:
                import json
                x=json.loads(f.read_text(encoding='utf-8'))
                items.append({k:x.get(k) for k in ('post_id','brand','status','current_version','updated_at')})
            except Exception:continue
        emit({'ok':True,'posts':items});return
    if not a.post:raise SwayError('--post required')
    if a.action=='major-version':
        path,state=major(a.organization,a.post,a.reason)
        emit({'ok':True,'current_version':state['current_version'],'path':str(path)});return
    path,state=get(a.organization,a.post)
    if a.action in ('highlight','unhighlight'):
        state['highlight']={'enabled':a.action=='highlight',
                            'note':a.note if a.action=='highlight' else '',
                            'tags':[x.strip() for x in a.tags.split(',') if x.strip()] if a.action=='highlight' else []}
        save(path,state)
    if a.action=='show':
        state=dict(state);state['current_files']=manifest(a.organization,a.post)
    emit({'ok':True,'path':str(path),'post':state})
if __name__=='__main__':main(run)
