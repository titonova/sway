# Recommendations

Recommendation engines are **optional and organization-owned**. Sway has a generic JSON-over-HTTPS adapter; it does not hardcode Fladov taxonomies. The organization's own schema/API guide remains authoritative. No engine means the agent uses the current organization strategy or user's instructions.

```bash
python -m tools.recommendations.next_post --org northstar --brand main
python -m tools.recommendations.next_post --org ORG --brand BRAND --request-json '{"schema_version":1}' --save-to-post POST_ID
```

For a configured engine set `recommendation_engine.enabled`, `next_post_url`, `log_post_url`, and `token_env` in `config.yaml`. The token variable must exist in the process environment. It is sent as an HTTPS Bearer token.

`log_post.py` records **verified actual placements only**; optional fields capture publishing provider, provider-assigned ID, native platform ID, post URL, highlight note. If engine sync is configured, pass a payload JSON file conforming *precisely* to that engine's validation schema:

```bash
python -m tools.recommendations.log_post --org ORG --post POST_ID \
  --channel instagram --provider manual --published-at 2026-10-17T12:00:00Z --verified
python -m tools.recommendations.log_post --org ORG --post POST_ID --record-json /path/to/engine-canonical-record.json
python -m tools.recommendations.log_post --org ORG --post POST_ID --highlight --highlight-note 'Great hook'
```

`--verified` is the operator's truthful claim that publication was checked externally. Never use it for a pending draft. External engines may need schema updates before they accept provider-specific identifiers or highlight fields. Sway stores these locally regardless; the generic adapter does **not** send arbitrary unknown fields to an engine.
