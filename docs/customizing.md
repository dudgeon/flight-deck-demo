# Customizing omnigent-slim

What you can change, where it lives, and whether it needs a rebuild. Most of it
is plain files you can edit on the offline Mac; changes to the web UI's own code
need a Mac with internet to rebuild.

| You want to change | Edit | Takes effect | Rebuild? |
|---|---|---|---|
| Canned sessions | `workspace/templates/sessions/*.md` | Next Library page load | No |
| Artifact templates and their look | `workspace/templates/artifacts/*.html` | Next artifact Claude makes | No |
| How Claude works in the workspace | `workspace/CLAUDE.md`, `workspace/.claude/skills/` | Next session | No |
| Skills every session gets, in any folder | `skills/<name>/SKILL.md` (see [skills/README.md](../skills/README.md)) | Next session | No |
| What every session knows about the canvas | `slim_canvas_instruction()` in `omnigent/runtime/prompt.py` | After `./stop.sh && ./start.sh` | No |
| Colors and theme of the app | Settings → Appearance in the web UI | Immediately | No |
| The app's own layout, pages or styles | `web/src/` | After rebuilding the web UI | Yes, on a Mac with internet |
| Python dependencies | `pyproject.toml`, `uv.lock` | After re-vendoring | Yes, on a Mac with internet |

## Canned sessions (pre-written demo scripts)

A canned session is one Markdown file in `workspace/templates/sessions/`. The
file name (without `.md`) is its id.

```markdown
---
title: Compare options with a decision matrix
description: Score options against weighted criteria and recommend one.
template: decision-matrix
---
Help me decide: {{decision: the question we're deciding}}

The options are: {{options: comma-separated}}

Propose 4-6 criteria with weights, score each option, build a decision matrix
artifact from the decision-matrix template and open it in the viewer.
```

- **Front matter** (between the `---` lines) is optional:
  - `title`: the card's heading (default: the file name).
  - `description`: one line under the title.
  - `template`: the file name of an artifact template, without `.html`. It's
    shown on the card; mention the template in the prompt too, because the prompt
    is what Claude reads.
- **Body**: the prompt. `{{name}}` or `{{name: hint}}` becomes a text box on the
  card; the hint is its placeholder. The same name used twice fills both places.
- **What happens**: **Open in composer** opens a new session in the Workspace
  project with the prompt filled in. The user edits it if they like and presses
  Send. Nothing is sent automatically.
- Cards are sorted by file name. Prefix files with numbers (`01-…`) to set the
  order.

For a scripted multi-step demo, write the first prompt as a canned session and
end it with the next step for Claude to wait on, e.g. "Build the form, open it,
and wait for my answers before drafting anything."

## Artifact templates

A template is one self-contained HTML file in `workspace/templates/artifacts/`.
Copy an existing one to start. The pattern:

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Risk register</title>                        <!-- the Library card title -->
<meta name="description" content="Risks with likelihood, impact and owner.">
<style>
  /* pa-tokens:begin */ /* filled in by design/build_tokens.py; copy it from another template */ /* pa-tokens:end */
  :root { --bg:var(--pa-surface); --fg:var(--pa-ink); --accent:var(--pa-navy); }
  body { background:var(--bg); color:var(--fg); font:15px/1.5 var(--pa-font); }
</style>
</head>
<body>
<script type="application/json" id="artifact-data">
{ "title": "Risks", "risks": [ { "risk": "…", "likelihood": "High", "owner": "…" } ] }
</script>
<main id="app"></main>
<script>
  const data = JSON.parse(document.getElementById("artifact-data").textContent);
  // Render `data` into #app. Escape text before inserting it as HTML.
  // Buttons can hand text back to the chat:
  //   window.omnigent?.prompt("Add a mitigation for: " + data.risks[0].risk);
</script>
</body>
</html>
```

Rules that keep templates working in the viewer:

- **Everything inline.** No `<script src>`, `<link>` to other hosts, web fonts,
  remote images or `fetch` to the internet: the viewer's security policy blocks
  them, and the work Mac is offline. Use system fonts and inline SVG.
- **One file.** Relative links to other files don't resolve in the viewer.
- **Content in the JSON block.** Claude fills in data instead of rewriting
  markup, which is faster and keeps the design consistent.
- **Colors only from the tokens.** Use the `--pa-…` variables (see below),
  never your own hex values. The token block already carries light and dark,
  and the viewer keeps it in step with the app.
- **Talk back with `window.omnigent?.prompt(text)`.** It puts text in the chat
  box for the user to send. Always use `?.` so the file also works outside
  Omnigent.

### One look everywhere: the design tokens

Every color, font and corner in Product Aviator comes from one file,
`design/tokens.json`. The app, chat widgets and canvas views (the view kit),
the scenario preview player and every artifact template read those values as
`--pa-…` CSS variables, and the canvas viewer injects the current values and
light or dark mode into each artifact as it opens it, so artifacts made before
a change pick it up too.

To change the look:

1. Edit `design/tokens.json` (each token has a light and a dark value).
2. Run `python3 design/build_tokens.py`. It rewrites the generated copies:
   `web/src/designTokens.generated.css`, `web/src/lib/designTokens.generated.ts`,
   the token block in `skills/view-kit/kit/pa-kit.css` and
   `skills/view-kit/kit/harness.html`, and the block between
   `pa-tokens:begin` and `pa-tokens:end` in each template.
   `--check` lists anything out of date.
3. Rebuild the web UI (`pnpm --filter web run build`, delete `*.map`).

Templates still keep their own short names (`--bg`, `--accent` and so on), but
those only point at tokens. The `product-aviator-design` skill tells Claude
what each token means and to use nothing else.

Remember to add new templates to the table in `workspace/CLAUDE.md` so Claude
knows when to use them.

## How Claude learns about the canvas

Three layers, from most general to most specific:

1. **Every session**, in any folder, gets a short paragraph in its system
   prompt: `slim_canvas_instruction()` in `omnigent/runtime/prompt.py`. It
   explains the viewer, `artifacts/`, `ui_open_file`, the templates folder,
   working offline, and `window.omnigent.prompt`. Keep it short and general.
2. **Sessions in the workspace folder** also read `workspace/CLAUDE.md`: the
   template table and house rules. Put project-specific guidance here.
3. **Skills** load when relevant. Drop a skill folder in `skills/` and every
   new session gets it, whatever folder it runs in (see
   [skills/README.md](../skills/README.md); `skills/omnigent-operator` is a
   working example). Skills in `workspace/.claude/skills/`, like the included
   `artifacts` checklist, only apply to sessions in the workspace folder.

To write skills that work in Omnigent and elsewhere, see
[skill-writers/README.md](skill-writers/README.md).

## Theme and colors of the app

The default look comes from the design tokens (above), for everyone. Upstream
Omnigent's **Settings** → **Appearance** palettes are still there and override
it in that one browser only; use them for personal taste, not to change the
product's look.

## Changing the web app itself

The web UI source is in `web/src/` (React + TypeScript + Tailwind). The running
app uses the prebuilt copy in `omnigent/server/static/web-ui/`, so source edits
do nothing until you rebuild. Rebuilding needs Node and the npm packages, so do
it on a Mac with internet:

```bash
corepack enable          # or: npm install -g pnpm
pnpm install
pnpm --filter web run build
find omnigent/server/static/web-ui -name '*.map' -delete
```

Then commit `omnigent/server/static/web-ui/` and copy the repo to the work Mac.

Useful places:

| What | File |
|---|---|
| Design tokens (the one source) | `design/tokens.json`, then `design/build_tokens.py` |
| Global styles | `web/src/index.css` (the Product Aviator chrome block is at the end), `web/src/lib/themePalette.ts` (the default palette points at the tokens) |
| Sidebar (where the Library link is) | `web/src/shell/Sidebar.tsx` |
| Library page | `web/src/pages/LibraryPage.tsx` |
| Viewer for HTML artifacts | `web/src/shell/HtmlCommentViewer.tsx` |
| The `window.omnigent` artifact API | `web/src/lib/artifactBridge.ts` |
| Routes | `web/src/App.tsx` |

Mark edits to upstream files with an `omnigent-slim:` comment so they survive
upstream syncs (see the README).

## Server-side pieces

| What | File |
|---|---|
| Library API (`GET /v1/slim/library`) | `omnigent/server/routes/slim_library.py` |
| Offline guard | `omnigent/_offline_guard.py` |
| Allowed permission modes; default mode, model and effort | `omnigent/slim_policy.py` |
| Workspace project created at start | `omnigent/slim_bootstrap.py` |
| Start and stop | `start.sh`, `stop.sh` |

Python changes take effect after `./stop.sh && ./start.sh` (the package is
installed in editable mode). New Python dependencies must be vendored: add them
to `pyproject.toml`, run `uv lock` and `vendor/scripts/build_vendor.sh` on a Mac
with internet, and commit `vendor/wheels/`.

## Structured workflows (scenarios)

A scenario is a skill folder that also carries a dataset shape, view specs,
invented fixture data and a click-through script (`script.md`, a markdown
screenplay described in `skills/view-kit/references/script.md`). See `skills/scenario-builder`
for how to make one, `skills/view-kit` for the views and the `pa` command, and
`skills/prd-to-requirements` for a worked example. To see one without starting
the app:

```bash
python3 skills/view-kit/scripts/pa.py preview skills/prd-to-requirements --out /tmp/preview.html
open /tmp/preview.html
```

Write previews outside the repository (as above) so they don't get committed.

The look of every view comes from `skills/view-kit/kit/pa-kit.css`, whose token
block is generated: restyle through `design/tokens.json`, not that file.

The Session panel (Outputs, Context, People and agents) is
`web/src/shell/SessionOverviewFiles.tsx`.

### Other participants

`workspace/participants/` is the one roster of agents and people the session's
agent can call into a conversation. Add a file to add someone, or ask the
agent to; `workspace/participants/README.md` is the guide for people and the
`participants` skill is the guide for the agent. A scenario narrows the roster
by listing ids under `participants` in its `scenario.json`. `backing: session` plays them in
a background session from their brief, `backing: script` answers from text in
the file. Their turns are drawn by `web/src/components/chat/ParticipantTurn.tsx`
from a fenced block described in `web/src/lib/participantTurn.ts`.

## Frameworks

`workspace/frameworks/` holds markdown files that say how deep and how broad a
piece of thinking must be. `intent.md` (notional) drives the `intent-shaping`
skill. Edit it or replace it with a real framework, keeping the headings
(`## Depth`, `## Breadth` with "Required from: N" and one line per depth,
`## Rules`). See `workspace/frameworks/README.md`.
