"""Document access control, path validation, and discovery for Sway organizations.

Implements configurable document access rules via config.yaml:
- document_access.allow: glob patterns / exact paths of accessible documents
- document_access.deny: glob patterns / exact paths of forbidden documents (overrides allow)
- Prevention of path traversal, absolute paths, and symlink escapes outside documents_path
- Cross-platform path normalization (consistent across Windows and Unix)
"""
from __future__ import annotations
import os
import re
from pathlib import Path
from src.config import organization, configured_path, SwayError

SUPPORTED_EXTENSIONS = {'.md', '.txt', '.json', '.yaml', '.yml', '.csv'}

def glob_to_regex(pat: str) -> re.Pattern:
    """Compile a standard glob pattern (supporting *, ?, **) into a regex pattern.
    
    Supports:
    - '*' matches characters within a single path segment (does not cross '/').
    - '?' matches a single character within a single path segment.
    - '**' matches zero or more path segments across '/'.
    - Exact paths or directory prefixes without wildcards.
    """
    pat = pat.replace('\\', '/').strip()
    if pat.startswith('./'):
        pat = pat[2:]
    pat = pat.lstrip('/')
    
    if pat.endswith('/'):
        pat = pat + '**'
    elif not any(c in pat for c in '*?'):
        escaped = re.escape(pat)
        return re.compile(f'^(?:{escaped}|{escaped}/.*)$')
    
    res = []
    i = 0
    n = len(pat)
    while i < n:
        if pat[i:i+3] == '/**':
            if i + 3 == n:
                res.append('/.*')
                i += 3
            elif pat[i+3:i+4] == '/':
                res.append('(?:/.*)?/')
                i += 4
            else:
                res.append('/.*')
                i += 3
        elif pat[i:i+3] == '**/':
            res.append('(?:.*/)?')
            i += 3
        elif pat[i:i+2] == '**':
            res.append('.*')
            i += 2
        elif pat[i] == '*':
            res.append('[^/]*')
            i += 1
        elif pat[i] == '?':
            res.append('[^/]')
            i += 1
        else:
            res.append(re.escape(pat[i]))
            i += 1
    return re.compile('^' + ''.join(res) + '$')

def normalize_doc_rel_path(subpath: str | Path) -> str:
    """Normalize a relative subpath to a clean POSIX path without leading slashes."""
    s = Path(subpath).as_posix() if isinstance(subpath, Path) else str(subpath).replace('\\', '/')
    s = s.strip()
    if s.startswith('./'):
        s = s[2:]
    return s.lstrip('/')

def get_document_access_rules(org_name: str) -> tuple[list[re.Pattern] | None, list[re.Pattern]]:
    """Retrieve compiled (allow_regexes, deny_regexes) for an organization.
    
    If allow is not configured (or None), returns (None, deny_regexes).
    """
    cfg = organization(org_name)
    access = cfg.get('document_access')
    if not isinstance(access, dict):
        return None, []
    
    allow_raw = access.get('allow')
    deny_raw = access.get('deny') or []
    
    if isinstance(allow_raw, str):
        allow_raw = [allow_raw]
    if isinstance(deny_raw, str):
        deny_raw = [deny_raw]
        
    allow_patterns = None
    if allow_raw is not None:
        allow_patterns = [glob_to_regex(p) for p in allow_raw if isinstance(p, str) and p.strip()]
        
    deny_patterns = [glob_to_regex(p) for p in deny_raw if isinstance(p, str) and p.strip()]
    return allow_patterns, deny_patterns

def is_document_accessible(org_name: str, rel_path: str | Path) -> bool:
    """Check if a relative document path is accessible under an organization's document_access rules.
    
    Rules:
    - deny always overrides allow.
    - If allow is provided, only matching files are accessible.
    - If allow is None, all files are allowed by default for backward compatibility.
    """
    clean_path = normalize_doc_rel_path(rel_path)
    if not clean_path:
        return False
        
    allow_patterns, deny_patterns = get_document_access_rules(org_name)
    
    # 1. Deny overrides allow
    for dp in deny_patterns:
        if dp.match(clean_path):
            return False
            
    # 2. Allow list check
    if allow_patterns is not None:
        return any(ap.match(clean_path) for ap in allow_patterns)
        
    # 3. Default allow when allow list is not specified
    return True

def resolve_document_path(org_name: str, doc_id: str | Path) -> Path:
    """Safely validate and resolve a document ID relative to the organization's documents_path.
    
    Enforces:
    - No absolute paths
    - No path traversal escaping the document root
    - No symlink escapes outside the document root
    - Organization document_access policy (checked on both requested ID and resolved target)
    - File existence and supported extension
    """
    root = configured_path(org_name, 'documents_path')
    p = Path(doc_id)
    raw_str = str(doc_id).strip()
    
    if p.is_absolute() or raw_str.startswith(('/', '\\')):
        raise SwayError('Only relative paths inside the configured root are accepted')
        
    root_resolved = root.resolve()
    resolved = (root / p).resolve()
    
    # Path traversal and symlink escape check
    if not resolved.is_relative_to(root_resolved):
        raise SwayError('Path traversal outside the configured root is forbidden')
        
    # Check policy on normalized requested path and on resolved target relative path
    norm_id = normalize_doc_rel_path(doc_id)
    target_rel = resolved.relative_to(root_resolved).as_posix()
    
    if not is_document_accessible(org_name, norm_id) or not is_document_accessible(org_name, target_rel):
        raise SwayError(f'Document access denied by policy: {doc_id}')
        
    if not resolved.is_file():
        raise SwayError(f'File not found: {resolved}')
        
    if resolved.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise SwayError(f'Not a supported text document: {doc_id}')
        
    return resolved

def get_accessible_documents(org_name: str) -> list[dict]:
    """Discover all accessible documents in an organization's documents_path.
    
    Filters out:
    - Files not matching document_access allow rules
    - Files matching document_access deny rules
    - Files escaping root via symlinks
    - Hidden files (names starting with '.')
    - Unsupported extensions
    """
    root = configured_path(org_name, 'documents_path')
    root_resolved = root.resolve()
    docs = []
    
    for q in sorted(root.rglob('*')):
        if not q.is_file() or q.suffix.lower() not in SUPPORTED_EXTENSIONS or q.name.startswith('.'):
            continue
        try:
            target = q.resolve()
        except OSError:
            continue
        if not target.is_relative_to(root_resolved):
            continue
            
        rel_posix = q.relative_to(root).as_posix()
        target_posix = target.relative_to(root_resolved).as_posix()
        
        if is_document_accessible(org_name, rel_posix) and is_document_accessible(org_name, target_posix):
            docs.append({
                'id': rel_posix,
                'title': q.stem.replace('_', ' ').replace('-', ' '),
                'bytes': q.stat().st_size
            })
            
    return docs
