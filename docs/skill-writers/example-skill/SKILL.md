---
name: one-pager
description: Turn notes or a rough idea into a one-page brief. In Omnigent, shows it as an artifact in the viewer with buttons to send feedback; elsewhere, writes a Markdown file. Use when the user asks for a one-pager, brief or summary page.
---

# One-pager

## 1. Where am I?

Run `printenv OMNIGENT` once.

- `1`: you're in Omnigent. Do step 2a.
- Empty: you're in a plain terminal. Do step 2b.

## 2a. In Omnigent: make an artifact

1. Look for a template. If the system prompt names a library folder, read
   `<library>/artifacts/prd-one-pager.html`; otherwise use
   `references/one-pager-template.html` from this skill.
2. Copy it to `artifacts/<short-name>.html` in the current folder and fill in
   only its `#artifact-data` JSON.
3. Call the `ui_open_file` tool with `{"path": "artifacts/<short-name>.html"}`.
4. Reply in one line: what it shows and that the "Discuss with Claude" buttons
   put a question in the chat box.

Keep everything inline: no CDNs, fonts, images or URLs. Buttons call
`window.omnigent?.prompt("...")`. You can't see the viewer; ask the user to
check it.

## 2b. Elsewhere: write Markdown

Write `<short-name>.md` with the same sections (problem, users, goals,
non-goals, requirements, metrics, open questions) and reply with its path.
