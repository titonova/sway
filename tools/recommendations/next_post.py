"""Fetch optional organization-defined deterministic next-post spec; never invent a recommendation."""
import argparse, json, requests
from src.config import organization,resolve_brand,auth_headers,SwayError
from src.io import emit,main
from src.posts import get,save,create

def run():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--organization','--org',required=True)
    p.add_argument('--brand',help='Optional if organization has a default or sole brand')
    p.add_argument('--request-json',help='Optional extra request fields as JSON')
    p.add_argument('--save-to-post',help='Optional local post ID to attach recommendation')
    p.add_argument('--create-post',action='store_true',help='Create a new post container and save recommendation into it')
    a=p.parse_args()
    brand_id=resolve_brand(a.organization,a.brand)
    engine=organization(a.organization).get('recommendation_engine') or {}
    if not engine.get('enabled'):
        emit({'ok':True,'configured':False,'recommendation':None,'message':'No engine; use organization strategy or ask the user for a concept.'});return
    url=engine.get('next_post_url')
    if not isinstance(url,str) or not url.startswith('https://'):raise SwayError('Valid HTTPS next_post_url required')
    data={'brand':brand_id,'schema_version':1}
    if a.request_json:
        other=json.loads(a.request_json)
        if not isinstance(other,dict):raise SwayError('--request-json must be JSON object')
        data.update(other)
    response=requests.post(url,json=data,headers=auth_headers(engine.get('token_env')),timeout=30)
    response.raise_for_status();result=response.json()
    if not isinstance(result,dict):raise SwayError('Engine returned non-object JSON')
    if a.create_post:
        path,state=create(a.organization,brand_id)
        state['recommendation']=result;save(path,state)
        v=path/'versions'/'v001'
        emit({'ok':True,'configured':True,'created_post':True,'post_id':state['post_id'],
              'path':str(path),'version_dir':str(v),'source_dir':str(v/'source'),
              'output_dir':str(v/'output'),'caption_path':str(v/'caption.md'),
              'recommendation':result})
        return
    if a.save_to_post:
        path,state=get(a.organization,a.save_to_post)
        if state['brand']!=brand_id:raise SwayError('Post brand does not match recommendation')
        state['recommendation']=result;save(path,state)
    emit({'ok':True,'configured':True,'request':data,'recommendation':result})
if __name__=='__main__':main(run)
