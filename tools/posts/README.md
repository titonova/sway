# Posts, major revisions and approvals

Sway uses **one folder per creative**, stored at the org's `posts_path` (default `~/.sway/posts/{organization}`). Each post contains `post.json` metadata and `versions/v001/` with `source/`, `output/` and `caption.md`. The agent may write HTML and caption files directly into the active version. **Minor edits and autonomous self-corrections simply overwrite the working files. Only important redesigns/alternative directions warrant `major-version`, which clones a new version.** Old sources/media remain usable references.

```bash
python -m tools.posts.manage create --org northstar --brand main
python -m tools.posts.manage list --org northstar
python -m tools.posts.manage show --org northstar --post POST_ID
python -m tools.posts.manage major-version --org northstar --post POST_ID --reason 'New concept'
python -m tools.posts.manage highlight --org northstar --post POST_ID --note 'Great visual hierarchy' --tags design,editorial
python -m tools.posts.highlights --org northstar --tag editorial
```

Human approval is separate from creation and not automatic:

```bash
python -m tools.posts.approve --org ORG --post POST_ID --channels instagram,facebook
python -m tools.posts.approve --org ORG --post POST_ID --channels instagram --due-at 2026-10-19T12:00:00Z
```

`approve` requires a **real interactive TTY** and typing `APPROVE POST_ID`. The human must review the exact files/caption/accounts/timing first. It saves a SHA-256 fingerprint of all the current version's source, output and caption. Editing any of these invalidates the approval even within the same version. Do not automate the interactive acknowledgement or disable execution permissions. `publish` also checks destination and due time. The agent should seek the user's explicit confirmation before requesting interactive approval.

The local `post.json` status records queued, scheduled and published **per destination** and preserves provider/native IDs. A provider queue ID does NOT mean verified publication. Highlights live locally independent of recommendation engine; retrieve curated examples with `tools.posts.highlights` (filter by brand, tag, format and pillar when structured metadata exists).
