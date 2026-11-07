"""Verified Buffer GraphQL API adapter; media must be hosted at public HTTPS URLs.
Docs: https://developers.buffer.com/guides/your-first-post.html
https://developers.buffer.com/examples/create-image-post.html
"""
import requests
from src.config import SwayError
ENDPOINT='https://api.buffer.com'
CREATE='''mutation CreateSwayPost($input: CreatePostInput!) {
  createPost(input: $input) {
    ... on PostActionSuccess { post { id status dueAt } }
    ... on MutationError { message }
  }
}'''
GET='''query GetSwayPost($input: PostInput!) { post(input: $input) { id status dueAt channelId sentAt externalLink } }'''
METRICS='''query GetSwayMetrics($input: PostInput!) { post(input: $input) { id status metrics { type name value unit } metricsUpdatedAt } }'''

def request(key,query,variables):
    if not key:raise SwayError('Missing Buffer API key')
    r=requests.post(ENDPOINT,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},
                    json={'query':query,'variables':variables},timeout=40)
    try:r.raise_for_status()
    except requests.HTTPError as e:raise SwayError('Buffer HTTP error: '+str(e))
    try:result=r.json()
    except ValueError:raise SwayError('Buffer returned invalid JSON')
    if result.get('errors'):raise SwayError('Buffer GraphQL error: '+str([x.get('message') for x in result['errors']]))
    return result.get('data') or {}

def publish(key,channel_id,text,mode='addToQueue',due_at=None,media_urls=None,channel=None):
    if mode not in ('addToQueue','customScheduled','shareNow'):
        raise SwayError('Unsupported Buffer scheduling mode')
    inp={'text':text,'channelId':channel_id,'schedulingType':'automatic','mode':mode}
    if mode=='customScheduled':
        if not due_at:raise SwayError('Exact scheduled time required')
        inp['dueAt']=due_at
    if channel and 'instagram' in str(channel).lower():
        inp['metadata']={'instagram':{'type':'post','shouldShareToFeed':True}}
    attachments=[]
    for url in media_urls or []:
        if not url.startswith('https://'):raise SwayError('Buffer requires public HTTPS URLs for all media')
        attachments.append({'video':{'url':url}} if url.lower().split('?')[0].endswith('.mp4') else {'image':{'url':url}})
    if attachments:inp['assets']=attachments
    data=request(key,CREATE,{'input':inp}).get('createPost') or {}
    if not data.get('post'):raise SwayError('Buffer rejected publication: '+str(data.get('message','No post returned')))
    return data['post']

def status(key,id):
    item=request(key,GET,{'input':{'id':id}}).get('post')
    if not item:raise SwayError('Buffer post not found')
    return item

def metrics(key,id):
    item=request(key,METRICS,{'input':{'id':id}}).get('post')
    if not item:raise SwayError('Buffer post not found')
    return item
