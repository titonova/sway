"""Shared validated configuration and path handling for Sway.

All paths in YAML resolve relative to config.yaml, never the shell cwd.
Tools only access configured external roots and their children.
"""
from __future__ import annotations
import os
import re
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent

def load_env_file(path: Path | None = None) -> None:
    target = path or (ROOT / '.env')
    if target.is_file():
        for line in target.read_text(encoding='utf-8', errors='replace').splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            k = k.strip()
            v = v.strip().strip('\'"')
            if k and k not in os.environ:
                os.environ[k] = v

load_env_file()
CONFIG_PATH = Path(os.environ.get('SWAY_CONFIG', str(ROOT / 'config.yaml'))).expanduser().resolve()
SLUG = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}$')

class SwayError(Exception):
    pass

def load_config() -> dict:
    if not CONFIG_PATH.is_file():
        raise SwayError(f'Missing Sway config: {CONFIG_PATH}')
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('organizations'), dict):
        raise SwayError('Expected config.yaml version: 1 and an organizations mapping')
    return data

def safe_slug(value: str, what: str='identifier') -> str:
    if not isinstance(value, str) or not SLUG.fullmatch(value):
        raise SwayError(f'Invalid {what}: only letters, numbers, _ and - are allowed')
    return value

def organization(name: str) -> dict:
    safe_slug(name, 'organization')
    cfg = load_config()['organizations'].get(name)
    if not isinstance(cfg, dict):
        raise SwayError(f'Unknown organization: {name}. Check config.yaml')
    return cfg

def brand(name: str, brand_id: str) -> dict:
    cfg=organization(name)
    safe_slug(brand_id,'brand')
    brands=cfg.get('brands') or {}
    if brand_id not in brands:
        raise SwayError(f'Unknown brand {brand_id!r} for organization {name!r}')
    return brands[brand_id] or {}

def resolve_brand(name: str, brand_id: str | None = None) -> str:
    cfg = organization(name)
    brands = cfg.get('brands') or {}
    if not brands:
        raise SwayError(f'No brands configured for organization {name!r}')
    if brand_id:
        brand(name, brand_id)
        return brand_id
    if len(brands) == 1:
        return next(iter(brands.keys()))
    if name in brands:
        return name
    available = ', '.join(repr(k) for k in brands.keys())
    raise SwayError(f'--brand is required for {name!r}. Available brands: {available}')

def configured_path(name: str, key: str, *, create: bool=False) -> Path:
    cfg=organization(name)
    raw=cfg.get(key)
    if not raw and key=='posts_path':
        raw=load_config().get('settings',{}).get('default_posts_path','~/.sway/posts/{organization}')
    if not isinstance(raw,str) or not raw.strip():
        raise SwayError(f'{key} is not configured for {name}')
    raw=raw.replace('{organization}',name)
    p=Path(os.path.expandvars(raw)).expanduser()
    if not p.is_absolute():
        p=CONFIG_PATH.parent/p
    elif os.name == 'nt' and not p.drive and raw.startswith(('/', '\\')):
        stripped = raw.lstrip('/\\')
        candidate_rel = (CONFIG_PATH.parent / stripped).resolve()
        candidate_home = (Path.home() / stripped).resolve()
        if candidate_rel.is_dir():
            p = candidate_rel
        elif candidate_home.is_dir():
            p = candidate_home
    p=p.resolve()
    if create:
        p.mkdir(parents=True,exist_ok=True)
    elif not p.is_dir():
        stripped = raw.lstrip('/\\')
        home_candidate = (Path.home() / stripped).resolve()
        sibling_candidate = (CONFIG_PATH.parent.parent / stripped).resolve()
        if home_candidate.is_dir():
            return home_candidate
        if sibling_candidate.is_dir():
            return sibling_candidate
        raise SwayError(f'Configured {key} directory does not exist: {p}')
    return p

def within(root: Path, subpath: str|Path, *, must_exist=True) -> Path:
    p=Path(subpath)
    if p.is_absolute():
        raise SwayError('Only relative paths inside the configured root are accepted')
    result=(root/p).resolve()
    if not result.is_relative_to(root.resolve()):
        raise SwayError('Path traversal outside the configured root is forbidden')
    if must_exist and not result.exists():
        raise SwayError(f'File not found: {result}')
    return result

def auth_headers(secret_var: str | None) -> dict:
    if not secret_var:
        return {}
    token=os.environ.get(secret_var,'')
    if not token:
        raise SwayError(f'Missing credential environment variable: {secret_var}')
    return {'Authorization':f'Bearer {token}'}

def is_document_accessible(org_name: str, rel_path: str | Path) -> bool:
    from src.documents import is_document_accessible as _ida
    return _ida(org_name, rel_path)

def resolve_document_path(org_name: str, doc_id: str | Path) -> Path:
    from src.documents import resolve_document_path as _rdp
    return _rdp(org_name, doc_id)

