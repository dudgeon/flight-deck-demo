# omnigent-slim

A cut-down fork of [Omnigent](https://github.com/omnigent-ai/omnigent), the
open-source meta-harness from Databricks, for prototyping an agent workspace on
a locked-down Mac. It drives **Claude Code as a terminal program**, so it needs
no API key, and it is set up to **run with no internet access** of its own.

What you get:

- **Sessions** with Claude Code from a browser UI. Each session is the real
  `claude` CLI running in a terminal (tmux) on your Mac; the web UI forwards
  your messages and shows Claude's replies, tool approvals and the terminal.
- **Artifacts in a right-hand canvas.** Claude writes self-contained HTML files
  into `workspace/artifacts/` and opens them in the viewer. Their JavaScript
  runs, and a button in an artifact can hand text back to the chat with
  `window.omnigent.prompt("...")`. You review it and press Send.
- **Artifact templates** in `workspace/templates/artifacts/`: PRD one-pager,
  decision matrix, now/next/later roadmap, metrics dashboard, interview
  synthesis and a question form.
- **Canned sessions** in `workspace/templates/sessions/`: prompts with
  fill-in fields, listed on the **Library** page. Picking one opens the
  composer with the prompt filled in; nothing is sent until you press Send.

## Requirements

- A Mac with Apple silicon, macOS 13 or later.
- Claude Code installed and signed in (`claude` on your `PATH`).

Everything else (Python 3.12, every Python package, tmux and the built web UI)
is in this repository.

## Get it

Download it in a way macOS doesn't quarantine, because the bundled tmux and
Python are not notarized and Gatekeeper blocks quarantined copies:

```bash
git clone https://github.com/dudgeon/omnigent-slim.git
```

or, without git:

```bash
curl -fsSLO https://github.com/dudgeon/omnigent-slim/archive/refs/heads/main.zip
unzip -q main.zip && cd omnigent-slim-main
```

A ZIP downloaded through a web browser and opened in Finder is quarantined;
ask your IT team before clearing that flag.

## Run it

```bash
./start.sh
```

The first run unpacks the bundled Python into `.runtime/` and installs the
bundled packages from `vendor/wheels/` without touching the network (about a
minute). Then it starts the server and opens <http://127.0.0.1:6767/library>.

```bash
./stop.sh
```

Data (sessions, settings, logs) lives in `~/.omnigent-slim`, separate from any
other Omnigent install. Delete that folder to start over.

### Settings

`start.sh` reads these from your environment:

| Variable | Default | What it does |
|---|---|---|
| `OMNIGENT_SLIM_WORKSPACE` | `./workspace` | Folder sessions run in |
| `OMNIGENT_SLIM_LIBRARY_DIR` | `$OMNIGENT_SLIM_WORKSPACE/templates` | Where the Library reads templates and canned sessions |
| `OMNIGENT_SLIM_PROJECT` | `Workspace` | Project the Library starts sessions in (created on first start) |
| `OMNIGENT_DATA_DIR` | `~/.omnigent-slim` | Sessions database, logs and settings |

## Customize it

- **Canned sessions:** add a Markdown file to `workspace/templates/sessions/`.
  Front matter sets `title`, `description` and optionally `template` (an artifact
  template's file name without `.html`). The body is the prompt. Write
  `{{name}}` or `{{name: hint}}` where the user should fill something in. The
  Library re-reads the folder on every visit.
- **Artifact templates:** add a self-contained HTML file to
  `workspace/templates/artifacts/`. Give it a `<title>` and a
  `<meta name="description">`, keep CSS and JavaScript inline, and put its
  content in a `<script type="application/json" id="artifact-data">` block so
  Claude only has to edit data. Copy an existing template as a starting point.
- **How Claude works in the workspace:** `workspace/CLAUDE.md` and the
  `artifacts` skill in `workspace/.claude/skills/` tell Claude where templates
  are, how to open artifacts and how artifacts talk back.

## What's locked down

- **No internet from Omnigent.** Every Omnigent process installs an offline
  guard (`omnigent/_offline_guard.py`) that refuses DNS lookups and connections
  to anything but this machine. Telemetry, update checks, model catalog
  lookups and harness installs are off. The web UI sends a Content Security
  Policy that lets the browser load nothing from other hosts, and that policy
  covers artifacts too. Browser speech recognition, which streams audio to a
  cloud service, is disabled. The `claude` CLI is a separate program: it talks
  to Anthropic exactly as it does when you run it yourself, and `start.sh` asks
  it to skip its non-essential traffic (`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`).
- **No permission bypass.** Every Claude Code launch gets an explicit
  `--permission-mode`, limited to Manual, Accept edits or Plan
  (`omnigent/slim_policy.py`). `--dangerously-skip-permissions` and
  `bypassPermissions` are removed, and so are Auto and Don't ask. Tool approvals
  appear in the web UI; the only tool pre-allowed is `ui_open_file`, which
  shows a file in the viewer.
- **Project MCP servers are not auto-approved.** If a workspace has a
  `.mcp.json`, Claude asks in the session's terminal tab.
- **Only Claude Code.** The other harnesses, cloud sandboxes, Databricks and
  model-provider integrations are hidden.

Two things Omnigent still does on your behalf, so a web-driven session doesn't
hang on prompts nobody can see: it marks the session's workspace folder as
trusted in Claude Code's config (the "Do you trust the files in this folder?"
question), and it generates session titles with a one-shot `claude -p` call
that has no tools.

## Rebuild the vendored files

On a Mac with internet access (not the offline machine):

```bash
vendor/scripts/build_vendor.sh   # Python runtime, wheels (from uv.lock), web UI
vendor/scripts/build_tmux.sh     # tmux
```

Then commit the results. `build_vendor.sh` needs `uv`, `node` and `pnpm`.

## What was removed from upstream

The iOS, Android and Electron apps, the test suites, docs, CI workflows,
deployment configs, editor plugins, the Slack integration, the browser
extension, and examples that need other harnesses or cloud services. The
Python package keeps upstream's code for other harnesses (it is tangled into
the session runtime), but none of it is offered or reachable from the UI. See
the git history for each change; the first commit is the unmodified upstream
snapshot.

## License

Apache License 2.0, as upstream. See `LICENSE` and `NOTICE`. This is an
independent fork, not affiliated with or endorsed by Databricks.
