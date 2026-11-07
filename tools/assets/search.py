"""Keyword-ranked asset discovery with optional full-catalog fallback."""
import argparse,re
from src.config import configured_path
from src.io import emit,main
from .catalog import entries

def run():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--organization','--org',required=True)
    p.add_argument('--query',default='')
    p.add_argument('--brand')
    p.add_argument('--limit',type=int,default=12)
    p.add_argument('--full-catalog',action='store_true')
    a=p.parse_args()
    if not a.full_catalog and not a.query.strip():
        a.full_catalog = True
    root=configured_path(a.organization,'assets_path')
    candidates=[x for x in entries(root) if not a.brand or not x.get('brand') or x['brand']==a.brand]
    terms=set(re.findall(r'[a-z0-9]{2,}',a.query.lower()))
    scored=[]
    for item in candidates:
        text=' '.join([str(item.get('caption','')),str(item.get('type','')),' '.join(item.get('tags',[]))]).lower()
        score=sum(2 if t in item.get('tags',[]) else 1 for t in terms if t in text)
        if a.full_catalog or score:scored.append((score,item))
    scored.sort(key=lambda x:(-x[0],x[1]['path']))
    emit({'ok':True,'query':a.query,'results':[dict(x,score=score) for score,x in scored[:max(1,min(a.limit,200))]],
          'total_catalog_entries':len(candidates),'mode':'full_catalog' if a.full_catalog else 'keyword'})
if __name__=='__main__':main(run)
