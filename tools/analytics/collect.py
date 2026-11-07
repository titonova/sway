"""Store per-placement timestamped metrics snapshots from Buffer or trusted JSON input.

No inferred zero for unavailable metrics. Storage is organization-local, not in the recommender.
"""
import argparse,json,os
from datetime import datetime,timezone
from pathlib import Path
from src.config import organization,SwayError
from src.posts import get,now
from src.io import emit,main
from tools.publishing.providers import buffer

def run():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--organization','--org',required=True);p.add_argument('--post',required=True)
    p.add_argument('--channel',required=True);p.add_argument('--input-json',help='Trusted exported metrics JSON (alternative to Buffer API)')
    a=p.parse_args();path,state=get(a.organization,a.post)
    placement=next((x for x in state['placements'] if x['channel']==a.channel),None)
    if not placement or placement.get('status')!='published':raise SwayError('Only confirmed published placements can have analytics snapshots')
    if a.input_json:
        data=json.loads(Path(a.input_json).read_text(encoding='utf-8'))
        if not isinstance(data,dict):raise SwayError('Input metrics must be JSON object')
        source='manual_import'
        metrics=data.get('metrics',data)
    else:
        if placement.get('provider')!='buffer' or not placement.get('provider_post_id'):
            raise SwayError('No supported metrics connector for this placement; use --input-json')
        cfg=organization(a.organization).get('publishing') or {}
        account=(cfg.get('accounts') or {}).get(a.channel) or {}
        env=account.get('token_env') or cfg.get('token_env') or 'BUFFER_API_KEY'
        key=os.environ.get(env)
        if not key:raise SwayError('Buffer metrics require personal API key via '+env)
        result=buffer.metrics(key,placement['provider_post_id'])
        metrics=result.get('metrics')
        if metrics is None:raise SwayError('Buffer returned unavailable metrics; do not record as zero')
        source='buffer_api'
    timestamp=datetime.fromisoformat(placement['published_at'].replace('Z','+00:00'))
    age=(datetime.now(timezone.utc)-timestamp).total_seconds()/3600
    snapshot={'post_id':a.post,'channel':a.channel,'provider_post_id':placement.get('provider_post_id'),
              'source':source,'captured_at':now(),'age_hours':round(age,2),'metrics':metrics}
    file=path/'analytics.jsonl'
    with file.open('a',encoding='utf-8') as h:h.write(json.dumps(snapshot,ensure_ascii=False)+'\n')
    emit({'ok':True,'snapshot':snapshot,'storage':str(file),
          'note':'Analytics are observational. Performance-based editorial weight changes belong to the external deterministic engine.'})
if __name__=='__main__':main(run)
