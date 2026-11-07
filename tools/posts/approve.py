"""Explicit human approval of a specific rendered version and destination set.

Approval happens in conversation: the user sends an approval message to the
agent (e.g. "APPROVE post_x for instagram and linkedin"). The agent records it
by passing that VERBATIM message via --user-message. The agent must never
write, paraphrase or invent this message; only relay exactly what the user said.
"""
import argparse, json,sys
from src.config import SwayError
from src.io import emit,main
from src.posts import approve_record

def run():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--organization','--org',required=True);p.add_argument('--post',required=True)
    p.add_argument('--channels',required=True,help='Comma-separated channel IDs being approved')
    p.add_argument('--due-at',help='ISO-8601 scheduled time. Omit for queued now/next slot')
    p.add_argument('--user-message',help='VERBATIM approval message sent by the user in conversation')
    a=p.parse_args()
    channels=[x.strip() for x in a.channels.split(',') if x.strip()]
    if not channels or len(set(channels))!=len(channels):raise SwayError('Nonempty distinct channels required')
    if not a.user_message:
        raise SwayError('Missing --user-message: ask the user to approve in conversation and relay their exact words. Never write the approval message yourself.')
    if 'APPROVE' not in a.user_message.upper():
        raise SwayError('User message does not contain APPROVE; ask the user to confirm with the word APPROVE plus the post ID')
    if a.post not in a.user_message:
        raise SwayError('User message does not mention this post ID; ask the user to include it, e.g. APPROVE '+a.post)
    state=approve_record(a.organization,a.post,channels,a.due_at,user_message=a.user_message)
    emit({'ok':True,'approval':state['approval']})
if __name__=='__main__':main(run)
