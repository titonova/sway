"""List documents available inside a configured organization's documents root."""
import argparse
from src.documents import get_accessible_documents, SUPPORTED_EXTENSIONS
from src.io import emit, main

EXTS = SUPPORTED_EXTENSIONS

def run():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--organization', '--org', required=True)
    args = p.parse_args()
    docs = get_accessible_documents(args.organization)
    emit({'ok': True, 'organization': args.organization, 'documents': docs})

if __name__ == '__main__':
    main(run)
