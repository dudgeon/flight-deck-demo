# Flight Deck

**Flight Deck** is a cut-down fork of
[Omnigent](https://github.com/omnigent-ai/omnigent), the open-source
meta-harness from Databricks, for prototyping an agent workspace on a
locked-down Mac. Its user interface is branded **Product Aviator**. The
repository is `dudgeon/flight-deck-demo` (renamed from `omnigent-slim`, D-114);
code identifiers, commands and the `~/.omnigent-slim` data folder keep the
name `omnigent-slim`.

- It drives **Claude Code as a terminal program** (your own `claude` login), so
  it needs no API key.
- It **never reaches the internet itself**: Python, every package, tmux and the
  built web UI are in this repository.
- It **never bypasses Claude Code's permissions**.
- Claude can put **artifacts** (interactive HTML pages) on a **canvas**, the
  viewer panel on the right of each session.
- The **Library** starts real work with a featured product skill, or flies a
  demo of a scenario. Its cards are generated from each workflow's and
  scenario's own files, which you can edit.

It stays close to upstream Omnigent on purpose, so prototypes carry over to
apps built on Omnigent; see [Staying close to upstream](#staying-close-to-upstream-omnigent).

**Other docs:** [Where things stand (roadmap)](docs/product/roadmap.md) ·
[Decisions and feature intent](docs/product/README.md) ·
[Customizing](docs/customizing.md) ·
[Writing skills for Omnigent](docs/skill-writers/README.md) ·
[Server API](omnigent/server/API.md)

---

## Quick start: from download to your first session

You don't need to be technical for this. You'll click a link, double-click a
file, and type two short lines into Terminal.

### Step 0. What you need

- A Mac with Apple silicon (M1 or newer) and macOS 13 or newer.
- **Claude Code**, installed and signed in. To check, open Terminal, type
  `claude` and press Return. If it starts, type `/exit` to leave it. If it says
  `command not found`, install Claude Code first.
- About 1 GB of free disk space.

The setup script checks all of this for you and tells you plainly if anything
is missing.

### Step 1. Download and unzip

1. Click this link: **https://github.com/dudgeon/flight-deck-demo/archive/refs/heads/main.zip**
   Your browser saves `flight-deck-demo-main.zip` (about 75 MB) to **Downloads**.
2. In Finder, open **Downloads** and double-click the ZIP. You get a folder
   called **flight-deck-demo-main**. (Safari may unzip it for you.)

Leave it in Downloads. Setup copies the app to its own folder, `~/flight-deck`
(the **flight-deck** folder in your home folder), and runs it from there.

### Step 2. Run the setup

1. Open **Terminal**: press Command-Space, type `Terminal`, press Return.
2. Copy this line, paste it into Terminal and press Return:

   ```bash
   sh ~/Downloads/flight-deck-demo-main/setup.sh
   ```

   (If it says *No such file*, the folder has another name, such as
   `flight-deck-demo-main 2`. Type `sh ` with a space, drag the **setup.sh** file
   from that folder onto the Terminal window, and press Return.)

The setup checks your Mac, then says that macOS has flagged the download as
coming from the internet. Every browser download gets that flag, and macOS
won't run the bundled Python and tmux while it's there. Press **Return** to
let setup remove it from the download only; it's the same thing as macOS's own
*Open Anyway* button. (If your company says not to, press Control-C instead
and use the Terminal download below, which never adds the flag.)

Setup then copies the app into `~/flight-deck`, adds a **Product Aviator**
icon to your Dock, and starts it. The first run takes about a minute. When you
see **Flight Deck is running**, your browser opens the **Library** page at
`http://127.0.0.1:6767/library`. You can delete the download afterwards.

**If it stops with a red ✗,** it says what went wrong and what to do. It also
saves a report on your Desktop, `flight-deck-setup-report.txt`. If the fix
doesn't work, send that file back. It lists the checks and errors, and has no
passwords or keys in it. You can run setup again as often as you like.

**Next time,** click **Product Aviator** in the Dock, or type
`sh ~/flight-deck/setup.sh` in Terminal.

### Updating to a newer version

1. Download the ZIP again from the same link. You don't need to unzip it.
2. In Terminal, type this and press Return:

   ```bash
   sh ~/flight-deck/setup.sh
   ```

(Installed before the repository was renamed on 21 November? Run the new
download's own setup once instead: `sh ~/Downloads/flight-deck-demo-main/setup.sh`.
An older `~/flight-deck/setup.sh` only looks for downloads named
`omnigent-slim-main`. After that, the line above works again.)

Setup finds the newest download in **Downloads**, stops the app, updates
`~/flight-deck` and starts it again. **It never overwrites your work:**

- Files you added (notes, data, artifacts, people, scenarios, drafts) are left
  alone.
- Files you changed that the new version also changes keep your version. The
  new version is saved in `~/flight-deck/updates/<date>/new-versions/` so you
  can compare.
- Files you deleted stay deleted.
- Your sessions, kept in `~/.omnigent-slim`, are never touched.

Setup lists all of this as it runs and in its report. (The app's own code,
outside the `workspace` folder, is always replaced with the new version; if
you changed any of it, your copy is saved under `updates/<date>/replaced/`.)

**Another way to download: one line in Terminal.** Paste this into Terminal
yourself and press Return. It downloads the ZIP to Downloads, unzips it and
runs the setup, for a first install or an update:

```bash
cd ~/Downloads && curl -fL -o flight-deck-demo-main.zip https://github.com/dudgeon/flight-deck-demo/archive/refs/heads/main.zip && unzip -qo flight-deck-demo-main.zip && sh flight-deck-demo-main/setup.sh
```

A download made this way never gets the macOS flag. `git clone` works too, on
a machine that allows it; run `sh setup.sh --here` in the clone to run it in
place instead of copying it to `~/flight-deck`.

**The Dock icon.** Setup builds `~/Applications/Product Aviator.app` and pins
it to the Dock the first time (D-103). Clicking it starts the server if it
isn't running and opens the UI in its own Chrome app window (or your default
browser without Chrome). It's built on your Mac, so there's nothing to download
or un-quarantine. To rebuild it by hand: `~/flight-deck/scripts/make_dock_app.sh`.

### Step 3. Start work, or fly a demo

1. On the **Library** page, the top half is the featured product skills. In
   **Intent shaping**, type an idea such as `show people the release date when a
   payment is held` and click **Start**. A new-session screen opens with the
   prompt filled in, in the **Workspace** project. Press **Enter** to send it.
2. Or, in **Scenarios and demos** lower down, click **Fly** on **Steering
   prep**. A project named **◆ Demo · Steering prep** opens with the story's
   documents and people in place and its opening line in the composer. Press
   **Enter** and the demo plays, one turn per message.
3. Sessions start in Auto mode, so Claude runs most steps itself. When it
   does ask permission, an approval card appears in the chat; click **Allow**.

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
sh ~/flight-deck/stop.sh
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
| Library | Featured skills (from the `library` block in each `workflow.json`) and demos (from each `scenario.json`) | `skills/`, `workspace/scenarios/` |
| Extra starters | Prompts with `{{fields}}`, shown as another way into a skill | `workspace/templates/sessions/` |
| Canvas instructions | Text added to every session's system prompt so Claude knows about the viewer | `slim_canvas_instruction()` in `omnigent/runtime/prompt.py` |

Included templates (managed in the Hangar): PRD one-pager, decision matrix,
now/next/later roadmap, metrics dashboard, interview synthesis, question form.
Featured skills on the Library, in product-lifecycle order: problem discovery,
intent shaping, document review, PRD to requirements, decision review and
delivery status. Each has a demo scenario. Each workflow is a skill in
`skills/` with a click-through preview; other agents and people they can call
in are in `workspace/participants/`.

To add your own templates, Library entries, skills or styles, see
**[docs/customizing.md](docs/customizing.md)**.

## Settings

`start.sh` reads these from your environment, for example
`OMNIGENT_SLIM_WORKSPACE=~/my-project ./start.sh`:

| Variable | Default | What it does |
|---|---|---|
| `OMNIGENT_SLIM_WORKSPACE` | `./workspace` | Folder the Workspace project's sessions run in |
| `OMNIGENT_SLIM_LIBRARY_DIR` | `$OMNIGENT_SLIM_WORKSPACE/templates` | Where templates and extra starters are read from |
| `OMNIGENT_SLIM_PROJECT` | `Workspace` | Project the Library starts sessions in (created on first start) |
| `OMNIGENT_DATA_DIR` | `~/.omnigent-slim` | Sessions database, logs and settings |

The project is only created once. To point an existing project at another
folder, hover over it in the sidebar, click **⋯**, then **Project settings**.

## Troubleshooting

| You see | Do this |
|---|---|
| `macOS has flagged this copy as downloaded from the internet` | Run setup (Step 2) |
| Setup stops with a red ✗ | Do what it says. If that doesn't fix it, send `flight-deck-setup-report.txt` from your Desktop |
| `Claude Code ('claude') is not on your PATH` | Install Claude Code, run `claude` once to sign in |
| `this build needs an Apple silicon Mac` | Use an Apple silicon Mac |
| A session says *Waiting for you in the agent's terminal* | Click the terminal icon (top right of the session) and answer Claude's question there, e.g. whether to trust a folder or a project MCP server |
| The page doesn't load | Run `sh ~/flight-deck/stop.sh` then `sh ~/flight-deck/setup.sh`. It prints the address; another app may hold port 6767, so it may use a different port |
| Claude wrote a file but nothing opened | Ask "open it in the viewer"; or click the file in the viewer's file tree (left icon in the viewer header) |
| Start over completely | `sh ~/flight-deck/stop.sh`, then delete `~/.omnigent-slim` and `~/flight-deck/.runtime/` |
| An update didn't take a change you expected | You had changed that file, so setup kept yours. The new version is in `~/flight-deck/updates/` |

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
  viewer); Claude may also read, but not change, the templates folder. The
  `canvas_*` tools (read the canvas's DOM and a screenshot, click, type, set an
  element's contents, run JavaScript in it) are not pre-allowed; they act only
  inside the viewer's sandboxed frame in your browser tab
  (see `docs/skill-writers/artifacts.md`).
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
  `ui_open_file` tool. Library Start buttons open the composer through Omnigent's own
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
