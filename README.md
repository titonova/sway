# Sway

**Sway** is a reusable social-content planning, creative production, review and publication agent workspace. Open this folder in a capable coding harness (e.g. Codex, Claude Code, ZCode) and ask the agent to create a post. The coding harness provides the LLM, file editing, tool execution and visual reasoning; Sway provides the specialist operating instructions (`AGENTS.md`) and executable CLI tools.

Sway is **organization-agnostic**: it contains no brand facts, graphics or publishing credentials. Each organization supplies its own external `documents_path`, `assets_path` and optional `posts_path`, configured in `config.yaml`. The agent works strictly inside the configured document-access rules and never fabricates product facts, photography or engine responses.

## Quick start

1. Clone and configure:

   ```bash
   git clone https://github.com/titonova/sway.git
   cd sway
   cp config.example.yaml config.yaml   # then edit paths, brands, channels
   ```

   `config.yaml` is gitignored — keep your real organization configuration local. Point `documents_path` / `assets_path` at folders **outside** this repo; posts are saved under the configured `posts_path` (default `~/.sway/posts/{organization}`).

2. Install prerequisites:

   ```bash
   python -m venv .venv
   source .venv/bin/activate            # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   python -m playwright install chromium
   ```

   Install **FFmpeg** for MP4 rendering. Python 3.11+ recommended. Set `SWAY_CHROMIUM_EXECUTABLE` to use a system Chromium instead of Playwright's. Credentials (Buffer API key, R2 keys, engine token) are read from environment variables — never from files the agent can read into context.

3. Sanity-check the tools:

   ```bash
   python -m tools.documents.list_docs --org myorg
   python -m tools.posts.manage list --org myorg
   ```

4. Open the `sway/` directory in your coding harness. Give it `AGENTS.md` as its instructions if the harness doesn't load that automatically. Then just ask in natural language: **“Create an educational Instagram post for myorg.”** The agent reads allowed docs, produces HTML/CSS, renders real PNG/MP4 media, visually inspects its own output, and presents it for your approval.

## How approval works

Publication requires an explicit human decision. Approval happens **in conversation**: you send a message containing `APPROVE` and the post ID (e.g. `APPROVE post_abc123 for instagram`), and the agent records your **verbatim** message through `tools.posts.approve --user-message`. The agent may relay your words but never write, paraphrase or fabricate an approval.

`tools.publishing.publish` independently checks the approved content hash, approved channels and approved time before contacting the provider. Editing an approved file invalidates the approval, even without a new version number.

## Basic commands

From the project root:

```bash
python -m tools.posts.manage create --org myorg --brand main
python -m tools.posts.manage list --org myorg
python -m tools.posts.manage show --org myorg --post YOUR_POST_ID
python -m tools.rendering.render_images --org myorg --post YOUR_POST_ID
python -m tools.rendering.render_video --org myorg --post YOUR_POST_ID
python -m tools.posts.manage major-version --org myorg --post YOUR_POST_ID --reason 'Alternate concept'
python -m tools.posts.manage highlight --org myorg --post YOUR_POST_ID --note 'Excellent typography' --tags editorial,typography
python -m tools.recommendations.next_post --org myorg --brand main   # requires a configured engine
python -m tools.publishing.publish --org myorg --post YOUR_POST_ID --channel instagram
python -m tools.publishing.status --org myorg --post YOUR_POST_ID --channel instagram
python -m tools.analytics.collect --org myorg --post YOUR_POST_ID
```

For argument details see `tools/README.md` and each tool folder's README.

## Directory conventions

- `AGENTS.md`: complete agent operating instructions — workflow, QA, evidence rules, approval and publication truth.
- `src/`: reusable internal Python library (not directly exposed as agent tools).
- `tools/`: standalone CLI entry points, each in a documented capability folder.
- `config.yaml` (local only): per-organization paths, document-access rules (`allow`/`deny` globs), optional recommendation engine and publishing accounts. See [`config.example.yaml`](config.example.yaml).
- Every output post is a self-contained `post_id/` directory under the configured `posts_path`: `post.json`, `versions/v001/source/`, `versions/v001/output/`, `versions/v001/caption.md`. Minor self-revisions overwrite the current version; materially different creative directions create a new major version.

Relative configured paths resolve from `config.yaml`, not the terminal's current directory. Set `SWAY_CONFIG=/absolute/path/to/config.yaml` to use an alternative configuration.

## Capability status and limits

| Feature | In this release | Conditions |
|---|---|---|
| Local document listing/reading | Yes | Text/Markdown/JSON/YAML/CSV files with configurable allow/deny glob access policy |
| Asset catalog and keyword/full-catalog search | Yes | Catalog descriptions must be true; rights/consent tracked by user/agent |
| Optional recommendation engine | Yes, HTTP adapter | Organization supplies a live compatible API and authentication; Sway imposes no fixed schema |
| Create posts and major-version-only history | Yes | Filesystem metadata in `post.json` |
| HTML/CSS carousel and image renderer | Yes | Chromium/Playwright installed; final images must be visually inspected by the agent |
| HTML/JS animation to MP4 + preview frames | Yes | Chromium + FFmpeg required; finite-frame rendering may be slow at high resolution |
| Conversational approval + publication guard | Yes | Verbatim user approval message recorded; approved hash, channels and timing enforced |
| Buffer GraphQL publishing adapter | Implemented, untested against a live account | API key and valid channel IDs required. With Cloudflare R2 configured, rendered media is uploaded automatically and public URLs passed to Buffer; otherwise user-provided media URLs are required. |
| Provider status check | Implemented, untested against a live account | Record *actual verified publication time*; queued does not mean published |
| Highlights and filtered retrieval | Yes, local | Optional external synchronization remains organization-specific |
| Per-placement analytics | JSON imports and Buffer post metrics adapter | Provider metrics availability varies; no fake values, no weight-adjustment LLM |
| Automatic unattended scheduling and notifications | Not bundled | A scheduler can launch the chosen coding harness; v1 is interactive |
| Google Drive/remote docs | Not bundled | Use a local synced/exported folder or implement an adapter later |

## Safety

Never put credentials in source code, `config.yaml` or organization documents; use environment secrets and don't let the agent print them. No public publication without an explicit, recorded human approval of the exact final media, caption, destination list and timing. Never log approval as publication. Use genuine photos and permissioned materials only — no fabricated customers, photos, screenshots, traction numbers or invented engine responses.

## Tests

```bash
python -m unittest discover -s tests -v
```

Tests use temporary demonstration directories, check command invocation, render images and videos (when system prerequisites exist), and verify that unapproved publication is rejected. They do not hit the network.
