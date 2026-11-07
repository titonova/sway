"""Queue/schedule an explicitly approved post through configured provider; NEVER silently publish.
When configured, Cloudflare R2 automatically hosts final media for Buffer. Status 'queued' is not published.
"""
import argparse,os
from pathlib import Path
from src.config import organization,SwayError
from src.posts import check_approval,get,add_placement
from src.io import emit,main
from .providers import buffer

def run():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--organization','--org',required=True)
    p.add_argument('--post',required=True);p.add_argument('--channel',required=True)
    p.add_argument('--due-at',help='Exact time, MUST match approval; default queue')
    p.add_argument('--media-url',action='append',default=[],help='Optional public HTTPS URL in approved media order; repeat for carousel. Omit to auto-upload to configured Cloudflare R2.')
    p.add_argument('--dry-run',action='store_true')
    a=p.parse_args();path,state=check_approval(a.organization,a.post,a.channel,a.due_at)
    if any(x['channel']==a.channel and x['status'] in ('published','queued','scheduled','unknown') for x in state['placements']):
        raise SwayError('Already submitted to this channel; check status first. Never automatically resubmit.')
    cfg=organization(a.organization).get('publishing') or {}
    if not cfg.get('enabled') and not a.dry_run:raise SwayError('Publishing disabled for this organization')
    provider=cfg.get('provider','buffer')
    if provider!='buffer':raise SwayError('Only Buffer adapter implemented')
    account=(cfg.get('accounts') or {}).get(a.channel) or {}
    if not a.dry_run and not account.get('provider_channel_id'):raise SwayError('Buffer channel ID not configured')
    folder=path/'versions'/state['current_version']
    text=(folder/'caption.md').read_text(encoding='utf-8').strip()
    import re
    text=re.sub(r'\*\*(.*?)\*\*',r'\1',text)
    text=re.sub(r'\*(.*?)\*',r'\1',text)
    from src.posts import manifest
    media=manifest(a.organization,a.post)['rendered_media']
    # Only final deliverables, not video preview frames, count as expected media.
    final_media=[x for x in media if x.endswith(('.png','.jpg','.jpeg','.mp4','.webp')) and '_preview_' not in x]
    from src.storage import is_r2_configured
    r2_configured=is_r2_configured()
    auto_upload=bool(final_media and len(a.media_url)!=len(final_media) and r2_configured)
    if final_media and len(a.media_url)!=len(final_media) and not a.dry_run:
        from src.storage import upload_to_r2
        if r2_configured:
            a.media_url = [upload_to_r2(path / rel, f"social/{a.organization}/{a.post}/{Path(rel).name}") for rel in final_media]
        else:
            raise SwayError(f'Expected {len(final_media)} public media URLs, got {len(a.media_url)}. Buffer cannot read local files. Configure Cloudflare R2 in .env or pass --media-url.')
    plan={'organization':a.organization,'post_id':a.post,'channel':a.channel,'provider':provider,
          'source_media':final_media,'media_urls':a.media_url,'approved_due_at':a.due_at,
          'would_queue':a.due_at is None,'would_schedule':a.due_at is not None,
          'r2_configured':r2_configured,'would_auto_upload_to_r2':auto_upload}
    if a.dry_run:emit({'ok':True,'dry_run':True,'plan':plan,'note':'No API call made.'});return
    secret_var=account.get('token_env') or cfg.get('token_env') or 'BUFFER_API_KEY'
    secret=os.environ.get(secret_var)
    if not secret:raise SwayError('Missing publishing credential environment variable: '+secret_var)
    # Record an uncertain state BEFORE making remote mutation to prevent duplicate attempts after process/network crashes.
    add_placement(a.organization,a.post,a.channel,'unknown',provider=provider)
    try:
        item=buffer.publish(secret,account['provider_channel_id'],text,
             mode='customScheduled' if a.due_at else 'addToQueue',due_at=a.due_at,media_urls=a.media_url,channel=a.channel)
    except Exception as exc:
        # Distinguish possible network timeout from rejection: never blindly retry unknown remote state.
        emit({'ok':False,'submission_state':'unknown','error':str(exc),
              'message':'Check Buffer dashboard before manual resolution; DO NOT blindly submit again.'})
        raise SystemExit(1)
    add_placement(a.organization,a.post,a.channel,'scheduled' if a.due_at else 'queued',
                  provider=provider,provider_post_id=item['id'])
    emit({'ok':True,'submitted':True,'provider_post':item,'plan':plan,
          'warning':'Queued/scheduled, NOT confirmed published. Run publishing.status to verify delivery.'})
if __name__=='__main__':main(run)
