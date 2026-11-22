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

`scenarios/` holds invented stories for demos. Never copy anything out of it
yourself; a demo is flown from the Hangar into `demos/<id>/`, which has its own
`CLAUDE.md` saying how to run it.

## Structured work

When the work is many similar items that the user reviews one by one (a
catalog of requirements, a set of explorations, a list of options), do not
hand-write an HTML artifact. Keep the items in a dataset in `data/` and draw
it with the `view-kit` skill, which also redraws the view when the data
changes. Skills such as `prd-to-requirements` and
`requirements-to-dependencies` are built this way, and `scenario-builder`
makes new ones.

Everything made for a project (an initiative) carries a stamp saying which
one: start documents with `pa template new … --initiative <key>`, stamp other
files with `pa stamp`, and record evidence, open questions, decisions and
ready checks with `pa register`. Details: "Initiatives, stamps, templates and
registers" in the `view-kit` skill.

## Which workflow, if any

Workflows describe when they fit: `pa workflows` lists them by stage, each
with when it fits, when it does not, what it needs and a one-line offer.
Read it before deciding; never route from memory. Then, top first:

1. **Named.** The user names a workflow or asks to run one: start it.
2. **Asked for.** The user tells you to do the work one workflow does, on
   material they point to ("find the problems worth solving in these
   notes", "walk me through the open decisions", "get risk and design's
   comments on the plan in one place"): that is asking to run it, so start
   it, and say in one line which workflow you started.
3. **Clear fit.** The user describes a situation or asks a question that a
   workflow answers ("what are people struggling with?", "is the date still
   real?"): it matches the workflow's "When", none of its "Not when", and
   what it needs is at hand. Answer what you can, then make its offer once,
   as one `AskUserQuestion` with "Start it" and "Not now", and record it
   with `pa log offer.made workflow=<id>`. Not again for this subject if
   they decline.
4. **Open.** Ideas, options, what-ifs, "what else could we do", a
   half-formed worry: think it through with them in your own voice. Make no
   offer in that reply; offer later only if they then ask for a workflow's
   whole job.
5. **Quick.** A question you can answer in a few lines, including one about
   a single paragraph, sentence or call: answer it, with no offer.

Never start a workflow the user did not ask for. When what a workflow needs
is missing, say what it needs instead of offering it. What it needs is its "Needs" line and no more: when that is "an idea in a sentence", the idea they just wrote is enough.

## Decisions that need the user

When the user has to choose, size the ask to the choice:

- **One quick choice** (seconds to answer, or easy to change later): one
  `AskUserQuestion` card, recommendation first, always with "Something else".
  If it is easy to undo, just do it and say so.
- **A complex decision**: use your judgment, but generally when it needs
  context the user doesn't have in front of them, is more than one question,
  or has a visual side that chat can't show well. Put it to the user as a
  decision brief with the `decision-brief` skill: you write one JSON file
  and its template draws the page, with context, a picture of each option,
  your recommendation and why, their pick and note, and a Send button that
  brings their answers straight back to you. Say in one line why you made a
  brief. The user can always say "brief me on this" or "just ask me".

Every skill and workflow uses the same rule, and none draws its own brief.
A brief is one of the project's decision artifacts and lives in
`projects/<key>/decisions/` with its page and decision note. Record what
the user decided as the brief skill says, and do not ask it again.

## Work in flight

A workflow working on one subject is a run, and the project page lists every
run under "In flight" so the user can leave and come back. That list is only
as true as what you record with the `pa flow` command (see "Runs" in the
`view-kit` skill):

- When the user sets a workflow aside in any words ("pause this", "let me
  come back to that later"), record it at once with `--pause --note "<where
  we left off>"`, say so in one line, and stop working on it. Do not ask
  first.
- When the user asks what is in flight or where they left off, or asks to
  resume, run `pa runs`, read the note and the dataset, mark it `--resume`
  and carry on from there. Do not start the workflow over.
- When the user abandons a workflow, confirm once, then `--stop`.
- A question on the side is not a pause. Answer it and carry on.

### Projects and links

A project is one goal that ships. When the user says what a project is for,
which area it belongs to, or how another team's project stands, record it
with `pa project "<name>" --goal … --area … --team … --state …`. When a
record is handed to another project, started one, or relies on one, hang
the link from that record with `pa link <dataset> <id> --to "<project>"
--type handed-to|started|relies-on`. Write a link once, on the item it is
about; the other project's page reads it the other way.

### Threads

A workflow can run in a thread of its own, with you as the project's
director, so its detail stays out of this conversation. Use the `director`
skill when the user asks you to direct or coordinate the project, asks for
a workflow "in a thread", "in the background" or "on the side", or wants two
pieces of work going at once. If your first message is a brief from a
director (it starts "Read your brief at"), you are the thread: follow the
brief, including what to report and when.

**If you are directing** (you started threads in this conversation, or a
summary of it says you did), then after a compaction, and when you take up
directing in a new session, run `pa recap` before anything else and follow
what it prints. It holds your charter and your notes in `director/`, which
the user can read and edit.

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
