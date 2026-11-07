# Documents

Use these tools to discover and read **external** organization documents. They only read supported local text formats (`.md`, `.txt`, `.json`, `.yaml`, `.yml`, `.csv`), including relevant subfolders, and reject paths that escape the configured documents root.

```bash
python -m tools.documents.list_docs --org northstar
python -m tools.documents.read_docs --org northstar overview.md
python -m tools.documents.read_docs --org northstar overview.md other.md --max-chars 60000
```

Document IDs are relative to `documents_path`. To use Google Drive, first sync/export the needed documents to a local directory or implement a retrieval adapter; no hosted connector is magically available from an arbitrary Python environment. Retrieve stable identity + current brand strategy first, then detailed knowledge as needed.

## Configurable Document Access (`document_access`)

Each organization in `config.yaml` can define an optional `document_access` policy with `allow` and `deny` pattern lists:

```yaml
organizations:
  northstar:
    documents_path: ~/Documents/sway-demo/docs
    document_access:
      allow:
        - "*.md"               # Top-level markdown files
        - "strategy/**"        # Everything inside strategy/ recursively
        - "reports/q?.txt"     # Reports with single-character wildcards
      deny:
        - "strategy/secret.md" # Deny specific confidential file
        - "internal/*"         # Deny all direct files in internal/
```

### Access Rules and Precedence

- **Default / Backward Compatibility:** If `document_access` is omitted, or `allow` is not specified, all files under `documents_path` are accessible by default.
- **Allow List:** When `allow` is provided, only files matching at least one pattern in `allow` are accessible.
- **Deny Precedence:** `deny` **always overrides** `allow`. Any file matching a `deny` pattern is blocked even if it matches an `allow` pattern.
- **Standard Glob Wildcards:**
  - `*`: Matches zero or more characters within a single directory segment (does not cross `/`).
  - `?`: Matches exactly one character within a single directory segment.
  - `**`: Matches zero or more directory segments recursively.
  - `exact/path.md`: Matches exact relative file path.
  - `folder/` or `folder/**`: Matches all files within that directory.
- **Consistent Matching:** Slashes and paths are normalized consistently across Windows (`\`) and Unix (`/`).
- **Path Traversal & Security:** Path traversal attempts (such as `../`), absolute paths, and symlinks escaping the document root are strictly rejected with an error. Redundant relative traversal (`dir/../denied.md`) cannot bypass deny rules.
- **Discovery and Reading Enforcement:** Blocked files are excluded from `list_docs` output, and direct requests to read blocked files via `read_docs` fail with `Document access denied by policy`.
