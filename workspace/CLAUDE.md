# Workspace

This folder is where omnigent-slim sessions run. Claude Code works here through
the omnigent web UI; the user reads and clicks the artifacts you make in the
viewer on the right.

## Rules that always apply

- This machine has no open-internet access. Never fetch URLs, install packages,
  or reference CDNs, remote fonts or remote images. Everything an artifact needs
  must be inline in its own HTML file.
- Ask before running commands that change anything outside this folder.

## Artifacts

An artifact is a single self-contained HTML file in `artifacts/`. The viewer
runs its JavaScript in a sandbox, so artifacts can be interactive.

To make one:

1. Pick the closest template in `templates/artifacts/` (see the list below).
2. Copy it to `artifacts/<short-kebab-name>.html`.
3. Change only the JSON inside `<script type="application/json" id="artifact-data">`.
   The template renders itself from that data. Change the markup or script only
   when the user asks for something the template cannot show.
4. Show it: call the `ui_open_file` tool (from the omnigent MCP server) with the
   path relative to this folder, e.g. `{"path": "artifacts/q3-roadmap.html"}`.
5. Say in one line what the artifact shows and what the user can click.

To update an artifact, edit its JSON in place and call `ui_open_file` again.

### Seeing and using the canvas

You can read and operate the artifact open in the viewer yourself with the
`canvas_*` tools: `canvas_read` (full live DOM and a screenshot),
`canvas_click` (by CSS selector or visible text), `canvas_type`,
`canvas_set_content` (replace any element's contents in the live page),
`canvas_press_key` and `canvas_eval`. They act in the viewer the user is
watching. Use them to check an artifact works before saying so, and whenever the
user asks you to use what's on the canvas. Never use Claude in Chrome or any
other browser for the canvas.

### Talking back from an artifact

Inside the viewer every artifact has `window.omnigent.prompt(text)`. It puts
`text` into the chat composer; the user reviews it and presses Send. Use it for
buttons such as "I pick option B" or "Send my answers". Always guard it:
`window.omnigent?.prompt(...)`. It never sends on its own.

When the user's next message comes from an artifact, act on it and update the
same artifact rather than making a new one.

### Templates

| Template | Use it for |
|---|---|
| `prd-one-pager.html` | A one-page PRD: problem, users, goals, requirements, metrics, open questions |
| `decision-matrix.html` | Comparing options against weighted criteria |
| `roadmap-now-next-later.html` | A roadmap board the user can rearrange |
| `metrics-dashboard.html` | KPI tiles with change and trend lines |
| `interview-synthesis.html` | Themes and verbatim quotes from research |
| `question-form.html` | Asking the user several questions at once |

New templates follow the same pattern: one HTML file, a JSON data block, inline
CSS/JS, light and dark colors, a `<title>` and `<meta name="description">` (the
Library page lists them from those).
