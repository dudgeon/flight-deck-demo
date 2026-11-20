---
name: artifacts
description: Make or update an interactive HTML artifact shown in the omnigent viewer, starting from a template in templates/artifacts. Use whenever the user asks for a PRD, roadmap, decision matrix, dashboard, research synthesis, a form of questions, or anything they should see rather than read in chat.
---

# Artifacts

Follow the "Artifacts" section of this workspace's CLAUDE.md. In short:

1. Choose the closest template in `templates/artifacts/`.
2. Copy it to `artifacts/<short-kebab-name>.html`; edit only its `#artifact-data` JSON.
3. Open it with the `ui_open_file` tool: `{"path": "artifacts/<name>.html"}`.
4. Tell the user in one line what it shows and what they can click.

Keep artifacts offline: no URLs to CDNs, fonts, images or APIs. Interactive
controls hand text back with `window.omnigent?.prompt("...")`, which fills the
chat composer for the user to send.
