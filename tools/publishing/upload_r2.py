"""Upload local asset/render to Cloudflare R2 and print public HTTPS URL."""
import argparse
from pathlib import Path
from src.io import emit, main
from src.storage import upload_to_r2

def run():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--file', required=True, help='Path to local file to upload')
    p.add_argument('--key', help='Optional remote key/path inside bucket')
    a = p.parse_args()
    url = upload_to_r2(a.file, a.key)
    emit({'ok': True, 'file': str(a.file), 'url': url})

if __name__ == '__main__':
    main(run)
