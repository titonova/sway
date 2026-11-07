"""Read one or more documents by their relative IDs from list_docs."""
import argparse
from src.documents import resolve_document_path
from src.io import emit, main
from .list_docs import EXTS

def run():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--organization', '--org', required=True)
    p.add_argument('ids', nargs='+', help='Document IDs relative to configured documents root')
    p.add_argument('--max-chars', type=int, default=80000)
    args = p.parse_args()
    result = []
    for name in args.ids:
        file = resolve_document_path(args.organization, name)
        value = file.read_text(encoding='utf-8')
        result.append({'id': name, 'content': value[:args.max_chars], 'truncated': len(value) > args.max_chars})
    emit({'ok': True, 'organization': args.organization, 'documents': result})

if __name__ == '__main__':
    main(run)
