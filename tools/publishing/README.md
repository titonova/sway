# Publishing and confirmation

`publish.py` queues or schedules **previously human-approved** content only. The post's exact source/media/caption SHA-256, approved account, and due time are checked on every call. It refuses duplicate submitted/scheduled/published placement attempts, and records uncertain external requests to prevent automatic duplicate retries.

```bash
python -m tools.publishing.publish --org ORG --post POST_ID --channel instagram --dry-run
python -m tools.publishing.publish --org ORG --post POST_ID --channel instagram
python -m tools.publishing.publish --org ORG --post POST_ID --channel instagram --media-url https://public.example/slide_01.png
python -m tools.publishing.status --org ORG --post POST_ID --channel instagram --confirmed-published-at 2026-10-17T12:00:00Z
```

**Buffer** adapter uses documented GraphQL API (`https://api.buffer.com`) and needs `publishing.enabled`, `provider: buffer`, channel's `provider_channel_id` and `BUFFER_API_KEY` or a configured `token_env`. It supports `addToQueue` by default, or `customScheduled` when `--due-at` was part of approval. Buffer needs publicly accessible HTTPS media URLs and cannot upload local files itself. Sway automatically uploads final media to Cloudflare R2 when all of `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, and `R2_PUBLIC_URL` are configured. The normal command is therefore `publish` with no `--media-url`; pass public URLs only to override R2 or when R2 is unavailable. Sway refuses to silently publish text-only when final local media exists.

A queued/scheduled post is NOT a confirmed publication. `status.py` checks Buffer's real status; when sent, it requires an actual verified publication timestamp before marking local placement `published`. If remote acceptance is uncertain due to timeouts, inspect Buffer dashboard before retrying; do not create duplicates. Native platform IDs are optional when Buffer lacks them. Unconfigured destinations need manual human export/handoff, verified publication and `recommendations.log_post`.

Provider interface is intentionally small: `publish`, `status`, optionally `metrics`, with adapter-specific account capabilities. Future drivers can be added to `providers/` without changing Sway creative workflow. No live Buffer account has been tested with this delivery.
