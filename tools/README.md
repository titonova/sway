# Agent-callable Sway tools

Each folder contains documented Python module entry points. Run commands from the `sway/` root as `python -m tools.<folder>.<script>`. All CLI tools emit JSON results and exit nonzero on failures. `src/` contains internal helpers only and is not the agent-facing interface.

| Folder | Responsibility |
|---|---|
| `documents/` | List and retrieve selected external organization documents |
| `assets/` | Maintain/search per-organization asset descriptions; verify real media |
| `recommendations/` | Optional external next-post recommendation and verified publication logging |
| `posts/` | Create and manage posts, only major versioning, human approval and highlight curation |
| `rendering/` | Render HTML/CSS/JS to PNG/carousel or motion-graphics MP4 |
| `publishing/` | Approved queue/schedule, provider-specific APIs and confirmation checks |
| `analytics/` | Collect or import factual per-placement metric snapshots |

Read the category's `README.md` before calling its scripts, or run `python -m tools.<category>.<module> --help`.

**Every tool requiring `--organization` uses an ID from config.yaml.** All organization paths resolve from config.yaml, not from the current working directory. Never treat an engine spec as permission to publish.
