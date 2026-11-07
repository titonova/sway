# Publishing providers

`buffer.py` is the initial GraphQL driver. It exposes `publish(key, channel_id, text, mode, due_at, media_urls)`, `status(key, provider_id)` and `metrics(key, provider_id)`. It checks GraphQL `errors` and typed `MutationError` results and returns actual API data. The Buffer API examples were verified against `https://developers.buffer.com/` in October 2026; validate the live contract before connecting actual accounts.

External service capabilities and commercial limitations vary by channel and account; do not assume Buffer Free supports every desired network or non-Short YouTube uploads. Media hosting and extra network-specific configuration must be validated with the real accounts. For a new provider, implement equivalent interface functions and explicitly map statuses; do not silently replace an unsupported provider with a fake success.
