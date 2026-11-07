"""Retrieve curated local highlights, optionally filter brand, format, pillar and tags."""
import argparse
from src.config import configured_path
from src.io import emit,main,read_json

def run():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--organization','--org',required=True);p.add_argument('--brand')
    p.add_argument('--format');p.add_argument('--pillar');p.add_argument('--tag')
    p.add_argument('--limit',type=int,default=15)
    a=p.parse_args();root=configured_path(a.organization,'posts_path',create=True);results=[]
    for f in sorted(root.glob('*/post.json')):
        item=read_json(f)
        if not item.get('highlight',{}).get('enabled'):continue
        if a.brand and item.get('brand')!=a.brand:continue
        if a.tag and a.tag not in item.get('highlight',{}).get('tags',[]):continue
        spec=(item.get('recommendation') or {}).get('spec') or {}
        if a.format and (spec.get('creative') or {}).get('format')!=a.format:continue
        if a.pillar and (spec.get('content') or {}).get('pillar')!=a.pillar:continue
        v=item.get('current_version');file=f.parent/'versions'/v
        results.append({'post_id':item['post_id'],'brand':item.get('brand'),
                       'highlight':item['highlight'],'recommendation':item.get('recommendation'),
                       'version':v,'directory':str(file),
                       'media':[str(p) for p in (file/'output').glob('*') if p.is_file()]})
    emit({'ok':True,'count':len(results),'results':results[:max(1,a.limit)]})
if __name__=='__main__':main(run)
