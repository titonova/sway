"""Log confirmed placements locally; optionally sync an engine-specific payload to its API.

No fabricated publish confirmation: caller must supply externally verified evidence.
"""
import argparse, json,requests
from src.config import organization,auth_headers,SwayError
from src.io import emit,main
from src.posts import get,save,add_placement,now

def run():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--organization','--org',required=True)
    p.add_argument('--post',required=True);p.add_argument('--channel',help='Destination account ID')
    p.add_argument('--published-at',help='Actual verified ISO-8601 timestamp')
    p.add_argument('--provider',help='Provider such as buffer or manual')
    p.add_argument('--provider-post-id');p.add_argument('--platform-post-id');p.add_argument('--url')
    p.add_argument('--verified',action='store_true',help='Assert publication independently verified (manual or API)')
    p.add_argument('--highlight',action='store_true');p.add_argument('--highlight-note')
    p.add_argument('--record-json',help='Engine-specific canonical payload file (optional)')
    a=p.parse_args();path,state=get(a.organization,a.post)
    if a.channel:
        if not a.verified or not a.published_at:raise SwayError('Manual log requires --verified AND a real --published-at timestamp')
        state=add_placement(a.organization,a.post,a.channel,'published',a.provider or 'manual',
                            a.provider_post_id,a.platform_post_id,a.published_at,a.url)
    if a.highlight or a.highlight_note:
        state['highlight']['enabled']=True
        if a.highlight_note:state['highlight']['note']=a.highlight_note
        save(path,state)
    confirmed=[x for x in state['placements'] if x['status']=='published']
    if not confirmed:raise SwayError('No confirmed published placements; do not log drafts or approvals')
    engine=organization(a.organization).get('recommendation_engine') or {}
    if engine.get('enabled'):
        if not a.record_json:
            emit({'ok':True,'local':True,'engine_synced':False,'confirmed_placements':confirmed,
                  'message':'Engine configured; supply canonical engine-specific --record-json to sync. Never invent its taxonomy.'});return
        url=engine.get('log_post_url')
        if not isinstance(url,str) or not url.startswith('https://'):raise SwayError('Valid HTTPS log_post_url required')
        payload=json.loads(open(a.record_json,encoding='utf-8').read())
        resp=requests.post(url,json=payload,headers=auth_headers(engine.get('token_env')),timeout=30)
        resp.raise_for_status()
        emit({'ok':True,'local':True,'engine_synced':True,'engine_result':resp.json()});return
    emit({'ok':True,'local':True,'engine_synced':False,'confirmed_placements':confirmed,
          'highlight':state['highlight'],'message':'No external recommendation engine configured.'})
if __name__=='__main__':main(run)
