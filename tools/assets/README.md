# Assets

`catalog.py` maintains `catalog.jsonl` inside the organization's configured external asset root. The catalog is made of records with stable id, relative path, true caption/description, tags, brand scope, license and approval flag. The root README should describe directories and rights constraints. Asset files remain intact; `remove` deletes only the catalog record. No AI vision API is called by the catalog script: **the coding agent must visually inspect and truthfully describe assets before cataloging them**, and never assume usage rights.

```bash
python -m tools.assets.catalog list --org northstar
python -m tools.assets.catalog add --org northstar --path logos/mark.svg --caption 'Northstar primary brand mark.' --type svg --tags brand,logo --approved
python -m tools.assets.search --org northstar --query 'logo brand'
python -m tools.assets.search --org northstar --full-catalog
```

Use keyword search first; inspect shortlist visually. If no matching result, repeat with `--full-catalog` and inspect promising matches. If no genuinely suitable real photograph exists, do **not** fabricate or replace it with an unrelated near-match. Compose with an explicit placeholder, mark non-publishable, request the precise missing asset, and rerender after it arrives. Icons should come from a verified, properly licensed icon library or supplied SVG; do not hallucinate icon identifiers or paid licenses. Future vector embeddings may index this same metadata.
