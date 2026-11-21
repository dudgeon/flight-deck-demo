# Artifacts and the viewer

## Show something in the viewer

1. Write one self-contained HTML file inside the session workspace, by
   convention `artifacts/<short-kebab-name>.html`.
2. Call the `ui_open_file` tool (MCP server `omnigent`, full name
   `mcp__omnigent__ui_open_file`) with the path **relative to the workspace**:

   ```json
   {"path": "artifacts/q3-roadmap.html"}
   ```

3. Tell the user in one line what it shows and what they can click.

Rules for the path: forward slashes, no leading `/`, no `~`, no `..`, no URLs.
The tool returns once the request is sent; it does not prove the file opened.
Missing files show an error in the viewer.

`ui_open_file` opens any workspace file, not only HTML: Markdown, code, images,
CSV and notebooks render too.

## Update it

Edit the file, then call `ui_open_file` again with the same path. The viewer
reloads.

## What the viewer runs

- HTML renders in a sandboxed frame with JavaScript on. It cannot read the
  Omnigent page, cookies or other files.
- omnigent-slim sends a Content Security Policy that blocks every other host:
  no CDN scripts, web fonts, remote images or API calls. Inline all CSS and
  JavaScript; use inline SVG for charts and icons.
- Relative links to other files don't resolve. One file per artifact.
- Follow the system's light/dark preference with
  `@media (prefers-color-scheme: dark)`.

## Talking back to the session

In the viewer, every artifact has:

```js
window.omnigent?.prompt("I pick option B");
```

It puts the text into the session's chat box. The user reviews it and presses
Send; nothing is sent automatically. Use it for buttons and forms ("Send my
answers", "Use these weights"). Always use `?.` so the file still works when
opened outside Omnigent.

When the next message comes from an artifact, update that artifact rather than
making a new one.

## Comments on artifacts

Users can select text in a rendered HTML artifact and leave a comment. Read
them with `list_comments`; after acting on one, mark it with `update_comment`
(see interfaces.md).

## Templates (omnigent-slim)

The library folder (`workspace/templates/` by default) holds:

- `artifacts/*.html`: templates. Each keeps its content in
  `<script type="application/json" id="artifact-data">` and renders itself from
  it, so a skill only has to copy the file and edit that JSON.
- `sessions/*.md`: canned sessions (prompts) listed on the Library page.

A template needs a `<title>` and `<meta name="description">`; the Library page
lists it by those. See the repository README for the full format.

## Checking an artifact works

Claude can't see or click the viewer, and omnigent-slim has no browser tool. To
check an artifact: read the code carefully, run any pure logic with a quick
script (e.g. `node -e`), then ask the user to try it.
