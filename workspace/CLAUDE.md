# Workspace

This folder is where omnigent-slim sessions run. Claude Code works here through
the omnigent web UI; the user reads and clicks the artifacts you make in the
viewer on the right.

## Rules that always apply

- This machine has no open-internet access. Never fetch URLs, install packages,
  or reference CDNs, remote fonts or remote images. Everything an artifact needs
  must be inline in its own HTML file.
- Ask before running commands that change anything outside this folder.

## Context

`context/` holds the documents the user wants you to work from: PRDs, notes,
platform documentation, exports. The user picks which of them a session should
use from the Session panel, and they arrive as file mentions in a message.
Read what you are pointed at. Do not go through the rest of `context/` unless
asked, and never change a file in it.

## Structured work

When the work is many similar items that the user reviews one by one (a
catalog of requirements, a set of explorations, a list of options), do not
hand-write an HTML artifact. Keep the items in a dataset in `data/` and draw
it with the `view-kit` skill, which also redraws the view when the data
changes. Skills such as `prd-to-requirements` and
`requirements-to-dependencies` are built this way, and `scenario-builder`
makes new ones.

## Other people and agents

`participants/` is the roster of other agents and people who can join a
conversation: one file each, with who they are and how they are played. When
the user asks to check in with, call or ask someone ("check in with Mara from
design and the risk agent"), or asks who is available, use the `participants`
skill. It tells you how to look them up, call them in a background session or
from their script, and show what they say under their own name. A message
that mentions a participant with `@` is for them to answer, not you. Never
answer on a participant's behalf.

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
CSS/JS, colors only from the `--pa-…` design tokens (copy the
`pa-tokens:begin`…`pa-tokens:end` block from an existing template, then run
`python3 design/build_tokens.py`; see the `product-aviator-design` skill), a `<title>` and `<meta name="description">` (the
Library page lists them from those).

## Where views go

Questions, single cards and summaries are shown in the chat: render the view
with `--host chat` and put the block the command prints (a ` ```view ` fence
naming the file) in your reply. Catalogs, boards and documents open in the
canvas. Never show the same view in both.
