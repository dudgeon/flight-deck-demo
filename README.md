# omnigent-slim

A cut-down fork of [Omnigent](https://github.com/omnigent-ai/omnigent), the
open-source meta-harness from Databricks, for prototyping an agent workspace on
a locked-down Mac.

- It drives **Claude Code as a terminal program** (your own `claude` login), so
  it needs no API key.
- It **never reaches the internet itself**: Python, every package, tmux and the
  built web UI are in this repository.
- It **never bypasses Claude Code's permissions**.
- Claude can put **artifacts** (interactive HTML pages) on a **canvas**, the
  viewer panel on the right of each session.
- **Templates** and **canned sessions** (prompts with fill-in fields) are plain
  files you can edit.

It stays close to upstream Omnigent on purpose, so prototypes carry over to
apps built on Omnigent; see [Staying close to upstream](#staying-close-to-upstream-omnigent).

**Other docs:** [Customizing](docs/customizing.md) ·
[Writing skills for Omnigent](docs/skill-writers/README.md) ·
[Server API](omnigent/server/API.md)

---

## Quick start: from download to your first session

Every step is a command or a click. Run commands in **Terminal**.

### Step 0. Check what you need

```bash
uname -m
```

It must print `arm64` (an Apple silicon Mac). Intel Macs are not supported.

```bash
claude --version
```

It must print a version. If it says `command not found`, install Claude Code
first. Then run `claude` once on its own, sign in, and quit it with `/exit`.

### Step 1. Download the ZIP from Terminal

Download with `curl`, not with a web browser. macOS marks files downloaded by a
browser as *quarantined*, and then refuses to run the bundled tmux and Python.
`curl` doesn't add that mark.

```bash
cd ~
curl -fL -o omnigent-slim.zip https://github.com/dudgeon/omnigent-slim/archive/refs/heads/main.zip
unzip -q omnigent-slim.zip
cd omnigent-slim-main
```

The folder is `~/omnigent-slim-main`. (`git clone` works too and also avoids
quarantine.)

If you can only download through a browser, `./start.sh` will tell you the copy
is quarantined. Ask your IT team how they want you to clear the flag; don't
bypass it on your own.

### Step 2. Start it

```bash
./start.sh
```

The first run takes about a minute: it unpacks the bundled Python into
`.runtime/` and installs the bundled packages, with no network. Later starts take
a few seconds. When it prints `omnigent-slim is running: http://127.0.0.1:6767/library`,
your browser opens the **Library** page.

**Optional: a Dock icon.** `scripts/make_dock_app.sh --add-to-dock` builds
`~/Applications/Product Aviator.app` and pins it to the Dock. Clicking it starts
the server if it isn't running and opens the UI in its own Chrome app window (or
your default browser without Chrome). It's built locally, so there's nothing to
download or un-quarantine. Leave off `--add-to-dock` to drag it there yourself,
and run the script again if you move this folder.

### Step 3. Run a canned session

1. On the **Library** page, find **Interview me about requirements**.
2. In its **topic** box, type something like `a CSV export button on the reports page`.
3. Click **Open in composer**. A new-session screen opens with the prompt
   filled in, in the **Workspace** project.
4. Press **Enter** (or the arrow button) to send it.
5. Sessions start in Auto mode, so Claude runs most steps itself. When it
   does ask permission, an approval card appears in the chat; click **Allow**.
6. In about half a minute a question form opens in the viewer on the right.
7. Answer a few questions and click **Put my answers in the chat**. Your
   answers appear in the chat box. Press **Enter** to send them.

### Step 4. Ask for anything on the canvas

1. In the left sidebar, hover over **Workspace** under *Projects* and click the
   speech-bubble icon that appears (**New session in Workspace**). Starting from
   the project keeps files in the workspace folder; the top **New session**
   button starts in your home folder instead.
2. Type: `make a canvas with a working calculator in it` and press **Enter**.
3. Allow the file write. The calculator opens on the right, ready to click.

Words like *canvas*, *artifact*, *dashboard*, *form*, *page* or *prototype* all
tell Claude to put the result in the viewer.

### Step 5. Stop it

```bash
./stop.sh
```

Your sessions are kept in `~/.omnigent-slim` for next time.

---

## How it works

| Piece | What it is | Where |
|---|---|---|
| Server and web UI | Omnigent's server, serving the browser UI on `127.0.0.1` | `omnigent/`, built UI in `omnigent/server/static/web-ui/` |
| Sessions | Each is the real `claude` CLI in a tmux terminal on your Mac. The UI forwards your messages and shows replies and approvals. The terminal icon (top right) shows the live terminal | `omnigent/harnesses/claude_native/` |
| Workspace project | Created on first start; its sessions run in `workspace/` | `workspace/` |
| Viewer ("canvas") | Right-hand panel that shows workspace files and runs HTML artifacts | upstream web UI |
| Artifacts | Self-contained HTML files in `workspace/artifacts/`, opened with the `ui_open_file` tool | `workspace/artifacts/` |
| Templates | Artifacts to copy and fill in | `workspace/templates/artifacts/` |
| Canned sessions | Prompts with `{{fields}}`, listed on the Library page | `workspace/templates/sessions/` |
| Canvas instructions | Text added to every session's system prompt so Claude knows about the viewer | `slim_canvas_instruction()` in `omnigent/runtime/prompt.py` |

Included templates: PRD one-pager, decision matrix, now/next/later roadmap,
metrics dashboard, interview synthesis, question form. Included canned
sessions: draft a PRD, compare options, build a roadmap, weekly metrics review,
synthesize interviews, interview me about requirements.

To add your own templates, canned sessions, skills or styles, see
**[docs/customizing.md](docs/customizing.md)**.

## Settings

`start.sh` reads these from your environment, for example
`OMNIGENT_SLIM_WORKSPACE=~/my-project ./start.sh`:

| Variable | Default | What it does |
|---|---|---|
| `OMNIGENT_SLIM_WORKSPACE` | `./workspace` | Folder the Workspace project's sessions run in |
| `OMNIGENT_SLIM_LIBRARY_DIR` | `$OMNIGENT_SLIM_WORKSPACE/templates` | Where templates and canned sessions are read from |
| `OMNIGENT_SLIM_PROJECT` | `Workspace` | Project the Library starts sessions in (created on first start) |
| `OMNIGENT_DATA_DIR` | `~/.omnigent-slim` | Sessions database, logs and settings |

The project is only created once. To point an existing project at another
folder, hover over it in the sidebar, click **⋯**, then **Project settings**.

## Troubleshooting

| You see | Do this |
|---|---|
| `macOS has quarantined this copy` | Download again with `curl` (Step 1) |
| `Claude Code ('claude') is not on your PATH` | Install Claude Code, run `claude` once to sign in |
| `this build needs an Apple silicon Mac` | Use an Apple silicon Mac |
| A session says *Waiting for you in the agent's terminal* | Click the terminal icon (top right of the session) and answer Claude's question there, e.g. whether to trust a folder or a project MCP server |
| The page doesn't load | Run `./stop.sh` then `./start.sh`. It prints the address; another app may hold port 6767, so it may use a different port |
| Claude wrote a file but nothing opened | Ask "open it in the viewer"; or click the file in the viewer's file tree (left icon in the viewer header) |
| Start over completely | `./stop.sh`, then delete `~/.omnigent-slim` and `.runtime/` |

Logs are in `~/.omnigent-slim/logs/`.

## What's locked down

- **No internet from Omnigent.** Every Omnigent process installs an offline
  guard (`omnigent/_offline_guard.py`) that refuses DNS lookups and connections
  to anything but this machine. Telemetry, update checks, model catalog
  lookups and harness installs are off. The web UI sends a Content Security
  Policy that lets the browser load nothing from other hosts, and that policy
  covers artifacts too. Browser speech recognition (a cloud service) and the
  desktop app's embedded browser tools are removed. The `claude` CLI is a
  separate program: it talks to Anthropic exactly as it does when you run it
  yourself, and omnigent-slim asks it to skip its non-essential traffic
  (`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`).
- **No permission bypass.** Every Claude Code launch gets an explicit
  `--permission-mode`, limited to Auto (the default), Manual, Accept edits or
  Plan (`omnigent/slim_policy.py`). `--dangerously-skip-permissions`,
  `bypassPermissions` and Don't ask are removed. New sessions default to
  Opus 5.5 at medium effort; set `OMNIGENT_SLIM_CLAUDE_MODEL`,
  `OMNIGENT_SLIM_CLAUDE_EFFORT` or `OMNIGENT_SLIM_CLAUDE_PERMISSION_MODE`
  before `./start.sh` to change that. Tool approvals appear in
  the web UI. The only pre-allowed tool is `ui_open_file` (shows a file in the
  viewer); Claude may also read, but not change, the templates folder.
- **Project MCP servers are not auto-approved.** If a workspace has a
  `.mcp.json`, Claude asks in the session's terminal.
- **Only Claude Code.** Other harnesses, cloud sandboxes, Databricks and
  model-provider integrations are hidden.

Two things Omnigent still does so a browser-driven session doesn't hang on a
prompt nobody can see: it marks the session's folder as trusted in Claude
Code's config (the "Do you trust the files in this folder?" question), and it
names sessions with a one-shot `claude -p` call that has no tools.

## Staying close to upstream Omnigent

omnigent-slim is meant to stay forward compatible with Omnigent, so work done
here carries over to apps built on it:

- Sessions, projects, agents, the Claude Code terminal harness, its MCP bridge
  and hooks, and the REST API are upstream's, unchanged.
- Artifacts are ordinary workspace files opened with Omnigent's own
  `ui_open_file` tool. Canned sessions open the composer through Omnigent's own
  `/?project=…&prompt=…` link.
- Edits to upstream files are small and marked with `omnigent-slim:` comments;
  `git grep -n "omnigent-slim:"` lists them. New behavior lives in new files:
  `omnigent/_offline_guard.py`, `omnigent/slim_policy.py`,
  `omnigent/slim_bootstrap.py`, `omnigent/server/routes/slim_library.py`,
  `web/src/lib/artifactBridge.ts` and `web/src/pages/LibraryPage.tsx`.
- `UPSTREAM` records the upstream commit this tree matches.
  `scripts/sync_upstream.sh` brings newer upstream changes in on a branch (run
  it on a machine with internet, then rebuild the web UI and test).

The Library page is part of the web UI, not an Omnigent extension: version 1 of
Omnigent's extension API (`sdks/web-extension`) can't read server data or open
the composer with a prompt, so an extension would need more core changes, not
fewer. If the extension API gains those two abilities, the Library can move
into one.

## Rebuilding the vendored files

Only needed when dependencies or the web UI change. On a Mac with internet
access (not the offline machine):

```bash
vendor/scripts/build_vendor.sh   # Python runtime, wheels (from uv.lock), web UI
vendor/scripts/build_tmux.sh     # tmux
```

Then commit the results. `build_vendor.sh` needs `uv`, `node` and `pnpm`.

## What was removed from upstream

The iOS, Android and Electron apps, the test suites, docs, CI workflows,
deployment configs, editor plugins, the Slack integration, and examples that
need other harnesses or cloud services. The Python package keeps upstream's code
for other harnesses (it is tangled into the session runtime), but none of it is
offered or reachable from the UI. The first commit is the unmodified upstream
snapshot; the history after it shows every change.

## License

Apache License 2.0, as upstream. See `LICENSE` and `NOTICE`. This is an
independent fork, not affiliated with or endorsed by Databricks.
