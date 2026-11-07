"""Check Buffer delivery and record confirmed publication without duplicate posting."""
import argparse,os
from src.config import organization,SwayError
from src.posts import get,add_placement,now
from src.io import emit,main
from .providers import buffer

def run():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--organization','--org',required=True)
    p.add_argument('--post',required=True);p.add_argument('--channel',required=True)
    p.add_argument('--confirmed-published-at',help='Verified real publication time; required for status=sent')
    a=p.parse_args();path,state=get(a.organization,a.post)
    place=next((x for x in state['placements'] if x['channel']==a.channel),None)
    if not place or place.get('provider')!='buffer' or not place.get('provider_post_id'):
        raise SwayError('No Buffer identifier for this placement')
    cfg=organization(a.organization).get('publishing') or {}
    account=(cfg.get('accounts') or {}).get(a.channel) or {}
    env=account.get('token_env') or cfg.get('token_env') or 'BUFFER_API_KEY'
    key=os.environ.get(env)
    if not key:raise SwayError('Missing credential environment variable: '+env)
    result=buffer.status(key,place['provider_post_id'])
    st=(result.get('status') or '').lower()
    if st in ('sent','published'):
        # Buffer provides sentAt as its recorded publication timestamp. Prefer
        # that API-verified value when the operator did not supply one.
        published_at=a.confirmed_published_at or result.get('sentAt')
        if not published_at:
            emit({'ok':True,'provider':result,'local_changed':False,
                  'message':'Buffer reports sent but did not return sentAt. Supply an externally verified publication timestamp.'});return
        state=add_placement(a.organization,a.post,a.channel,'published','buffer',place['provider_post_id'],
                            published_at=published_at)
    elif st in ('error','failed'):
        state=add_placement(a.organization,a.post,a.channel,'failed','buffer',place['provider_post_id'])
    elif st in ('scheduled','buffer','pending'):
        state=add_placement(a.organization,a.post,a.channel,'scheduled','buffer',place['provider_post_id'])
    else:
        emit({'ok':True,'provider':result,'local_changed':False,'message':'Unknown provider status, not marked published'});return
    emit({'ok':True,'provider':result,'placement':next(x for x in state['placements'] if x['channel']==a.channel)})
if __name__=='__main__':main(run)
