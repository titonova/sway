"""Cloudflare R2 (S3-compatible) storage adapter for Sway.

Automatically uploads rendered media to Cloudflare R2 and returns public CDN URLs.
Requires R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_PUBLIC_URL.
"""
from __future__ import annotations
import mimetypes
import os
from pathlib import Path
from src.config import SwayError

def is_r2_configured() -> bool:
    return bool(
        os.environ.get('R2_ACCOUNT_ID') and
        os.environ.get('R2_ACCESS_KEY_ID') and
        os.environ.get('R2_SECRET_ACCESS_KEY') and
        os.environ.get('R2_BUCKET_NAME') and
        os.environ.get('R2_PUBLIC_URL')
    )

def get_r2_client():
    account_id = os.environ.get('R2_ACCOUNT_ID')
    access_key = os.environ.get('R2_ACCESS_KEY_ID')
    secret_key = os.environ.get('R2_SECRET_ACCESS_KEY')
    if not (account_id and access_key and secret_key):
        raise SwayError(
            'Cloudflare R2 is not fully configured in environment. '
            'Required: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY'
        )
    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        raise SwayError('boto3 is required for R2 upload. Install with `pip install boto3`')

    endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
    return boto3.client(
        's3',
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version='s3v4'),
        region_name='auto'
    )

def upload_to_r2(local_file: Path | str, remote_key: str | None = None) -> str:
    path = Path(local_file)
    if not path.is_file():
        raise SwayError(f'Local file not found for upload: {path}')

    bucket = os.environ.get('R2_BUCKET_NAME')
    if not bucket:
        raise SwayError('Missing R2_BUCKET_NAME in environment/.env')

    public_base = os.environ.get('R2_PUBLIC_URL', '').rstrip('/')
    if not public_base:
        raise SwayError('Missing R2_PUBLIC_URL in environment/.env (e.g. https://assets.example.com or https://pub-xxx.r2.dev)')

    if not remote_key:
        remote_key = f"social/{path.name}"

    mime_type, _ = mimetypes.guess_type(str(path))
    content_type = mime_type or 'application/octet-stream'

    client = get_r2_client()
    try:
        client.upload_file(
            str(path),
            bucket,
            remote_key,
            ExtraArgs={'ContentType': content_type}
        )
    except Exception as exc:
        raise SwayError(f'Cloudflare R2 upload failed: {exc}')

    return f"{public_base}/{remote_key}"
