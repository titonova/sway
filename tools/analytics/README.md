# Analytics snapshots

Analytics remain separate from the next-post generation path and are kept **by confirmed placement**, not merged as fictitious per-creative averages. `collect.py` either reads Buffer's per-post metrics using a personal Buffer API key or imports a trusted metrics JSON export. It appends `analytics.jsonl` to the local post directory and stores source, timestamp, provider ID, channel, hours since actual publication, and only available metrics. Missing is not zero.

```bash
python -m tools.analytics.collect --org ORG --post POST_ID --channel instagram
python -m tools.analytics.collect --org ORG --post POST_ID --channel instagram --input-json /path/to/trusted_metrics.json
```

Take snapshots around 24 hours, 7 days and 30 days when a scheduler/provider permits. Data collection in v1 is manual/command-driven; adding daily scheduling is a distinct deployment step. **Do not** have Sway's creative LLM directly change deterministic recommendation weights. Any automatic weight adjustment after credible sample size belongs to the organization's external engine with bounded, auditable policy.
