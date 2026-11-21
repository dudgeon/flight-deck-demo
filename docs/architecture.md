# Architecture overview

How Flight Deck (the fork) and Product Aviator (its user interface) are put
together, area by area. Each section says what the piece is for, how it works,
where the code is, and which decisions shaped it. Decision numbers (D-nn) are
in [product/decisions.md](product/decisions.md); where each one stands is in
[product/decision-index.md](product/decision-index.md). For how we got here,
read [history.md](history.md). For the status of each workstream, read
[product/roadmap.md](product/roadmap.md).

## The whole thing in one picture

```
Browser (Product Aviator web UI, built and committed)
  │  http://127.0.0.1:6767
  ▼
Omnigent server (Python, FastAPI)  ── slim routes: /v1/slim/library, /v1/slim/hangar, /v1/slim/inbox/…
  │  sessions, projects, inbox, canvas bridge (upstream)
  ▼
Host  ──►  tmux  ──►  `claude` (Claude Code CLI, the user's own login)
                         │ runs in workspace/  (or a demo or Hangar folder)
                         │ reads skills/ (bundled as a plugin dir)
                         ▼
                 files: data/, artifacts/, context/, participants/, scenarios/, progress/
```

Everything the product knows lives in **files** in the repo or the workspace.
There is no database of our own: the server reads the files on each request,
and the agent changes them with the `pa` command. Upstream Omnigent's own
store holds only sessions, projects and the Inbox.

## The fork and its rules

- **Upstream.** A cut-down copy of [Omnigent](https://github.com/omnigent-ai/omnigent),
  pinned in `UPSTREAM` and synced with `scripts/sync_upstream.sh`. Slim
  changes to upstream files carry an `omnigent-slim:` comment. Mobile and
  desktop shells, CI, deploy and upstream docs were removed (README, "What
  was removed"). D-01.
- **Claude Code only, as a terminal.** Each session is the real `claude` CLI in
  a tmux terminal (`omnigent/harnesses/claude_native/`). No Claude API key.
  D-02.
- **Permissions.** `omnigent/slim_policy.py` rewrites every launch: bypass and
  don't-ask modes are refused, Auto is the default, Opus 5.5 at medium effort
  unless overridden by `OMNIGENT_SLIM_CLAUDE_*` variables. Only `ui_open_file`
  is pre-approved. D-02, D-03.
- **Offline.** `omnigent/_offline_guard.py` blocks outbound sockets from the
  Python process; the CSP allows loopback only; `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`
  quiets Claude Code's extras. Artifacts must be self-contained HTML.
- **Vendored.** `vendor/python/` (a CPython build), `vendor/wheels/` (every
  Python dependency), `vendor/bin/tmux`, and the built web UI in
  `omnigent/server/static/web-ui/`. Rebuild with `vendor/scripts/build_vendor.sh`.
- **Bootstrap.** `start.sh` unpacks Python into `.runtime/`, installs the
  wheels with no index, starts the server (port 6767, or the next free one),
  then `omnigent/slim_bootstrap.py` creates the **Workspace** project (sessions
  run in `workspace/`) and the **Hangar** project (D-59). Data lives in
  `~/.omnigent-slim`. `stop.sh` stops it.
- **Skills.** `omnigent/slim_skills.py` links every folder in `skills/` into
  the skill bundle each Claude Code session gets (`--plugin-dir`). A skill
  appears as `/claude:<name>`. Workspace-built workflows live in
  `workspace/.claude/skills/` and take over a shipped id (D-72).

## The workspace and the four kinds of work

**Workspace.** `workspace/` is the folder sessions run in. Its `CLAUDE.md`
tells every session the always-on rules: no internet, views come from the
view kit, how participants work, asks in chat and work in the canvas.

| Folder | Holds |
|---|---|
| `context/` | Documents to work from, picked per session in the Session panel; per project (D-13, D-15) |
| `data/` | Datasets: JSON records with status, lock and stale marks (D-07) |
| `artifacts/` | What the agent makes: HTML artifacts and rendered views |
| `participants/` | The roster, one markdown file per person or agent, plus `avatars/` |
| `scenarios/<id>/` | Demo stories: `scenario.json`, `fixtures/`, `script.md` (D-42, D-67) |
| `progress/` | Workflow progress for the Session panel's workflow card (`pa flow`) |
| `frameworks/` | Swappable company frameworks, today `intent.md` (D-34) |
| `templates/` | Artifact templates and the Library's starters |
| `.hangar/` | Drafts and kept versions from the Hangar (gitignored, D-56) |

**The view kit** (`skills/view-kit/`) is the engine of structured work (D-05,
D-10). A view is a small JSON spec (table with hierarchy, board, card,
summary, form) over a dataset. `scripts/pa.py` (standard library only)
creates and edits datasets (`pa init|get|add|set`), draws a spec as one
self-contained HTML file (`pa render`, `--host chat` for the conversation),
redraws every view when records change (`pa refresh`), checks a package
(`pa check`) and builds an agent-free demo (`pa preview`, the player is
`kit/harness.html`). `kit/pa-kit.js` and `kit/pa-kit.css` are the runtime.
Buttons in a view put text in the composer; buttons marked `"direct": true`
send a state change at once, as a message the app writes from ids and status
words only (D-11, D-12; `web/src/lib/artifactBridge.ts`).

**A workflow** ("a kind of work") is a skill folder: `SKILL.md` (the agent's
instructions), `workflow.json` (steps, record shapes, who may be called),
`schemas/` and `views/`. **A scenario** is one story that runs a workflow:
cast, invented data and a markdown screenplay (`script.md`, grammar in
`skills/view-kit/references/script.md`). Many scenarios per workflow (D-42).

**The four kinds of work** (D-31), each a workflow with a first scenario:

| Workflow | What it is for | End product |
|---|---|---|
| `problem-discovery` | Turn raw material into problems in the users' words, with evidence for and against | A problem brief, no solutions |
| `intent-shaping` | Walk an idea to committable depth against `frameworks/intent.md` (5 depths, 7 areas) | An intent brief stating its depth |
| `decision-review` | Put waiting decisions to the PM the way Geoff wants (D-33): context, options, consequences, recommendation | A decision log |
| `delivery-status` | Check milestones and dependencies with owners, carry slips through, list alternatives | A status update whose first line is the truth |

They chain into one invented story (discovery finds held payments, shaping
shapes a release date, decisions settle it, delivery tracks it) and each also
stands alone. The earlier workflows `document-review`, `prd-to-requirements`
and `requirements-to-dependencies` (the PRD example from the start) are built
the same way. `scenario-builder` and `build-person` are the builder skills.

**Views in the chat** (D-53). Questions, pick-ones, single cards and
summaries are drawn in the conversation from a fenced `view` block and fold to
"Answered" once the person replies; catalogs, boards and documents open in the
canvas. While a chat view waits, the canvas greys (D-55). Code:
`web/src/lib/chatView.ts`, `web/src/components/chat/ChatViewBlock.tsx`.

**The Session panel** (D-13, D-14, D-16). Cards for cost, the running
workflow, Outputs, Context and People and agents. It docks beside the chat
when the canvas is closed and is a popover otherwise.
`web/src/shell/SessionOverview.tsx`.

**The canvas** is upstream's right-hand viewer. Slim adds the `canvas_*` tools
so Claude can read and operate the artifact inside the sandboxed frame in the
person's own tab, with one active tab per session (D-101;
`omnigent/server/routes/sessions/routes_browser.py`,
`web/src/lib/canvasFrameRuntime.ts`).

## Participants and the roster

Other agents and people take part in the conversation as themselves (D-17).

- **The roster.** One global folder, `workspace/participants/`, one markdown
  file per participant: frontmatter (`name`, `kind` agent or person, `role`,
  `initials`, `stand_in`, `backing` session or script, `call_for`, optional
  `skills` and `avatar`) and a body that is either a brief or a `## Script`.
  `_template.md` and `README.md` explain the format. Scenarios name who in it
  is eligible (D-20). `pa who` lists and shows; `pa who --check` validates.
- **Two backings** (D-18). A *script-backed* participant answers from their
  file. A *session-backed* one is a background Claude Code session started with
  their brief, never a sub-agent, so it can be opened and read (D-19).
  Sessions are created as child sessions through Omnigent's `sys_session_*`
  tools; the `participants` skill has the exact steps.
- **In the chat.** Aviator relays a participant's words verbatim in a
  `participant` fenced block, which the app draws as their own turn with a mark
  (square for agents, round for people, dashed "stand-in" for a person played
  by an agent, D-22) and a link to their session. `@name` addresses them
  (D-25); Aviator may call someone in on its own and says so (D-23); a called
  participant sees the whole conversation, for demos only (D-24).
  `web/src/lib/participantTurn.ts`, `web/src/components/chat/ParticipantTurn.tsx`.
- **The Inbox** (D-68 to D-70). `pa tell` posts a participant's message, or an
  invitation into their own session, as an ordinary agent-posted Inbox item
  with a `participant` media block (`POST /v1/slim/inbox/participant-messages`,
  `omnigent/server/routes/slim_participant_inbox.py`). The card offers Open (or
  Join) conversation and Done; replies always happen in context. A People tab
  lists only these.

## The collaborative editor and CriticMarkup

A person and agents work on one markdown document the way people do in a
shared doc (D-26, D-104).

- A review layer on upstream's TipTap markdown editor
  (`web/src/shell/review/`, hooked into `MarkdownRichTextViewer.tsx`).
- **Suggestions are stored in the `.md` itself as CriticMarkup**
  (`{++added++}`, `{--removed--}`, `{~~old~>new~~}`), each followed by a
  `{>>@author time<<}` note, so they survive any tool that reads the file.
- **Comment threads** live in a sidecar, `<doc>.md.review.json`, attributed to
  the person, Aviator or a participant. `@name` in a comment asks Aviator to
  get that participant's reply into the thread.
- Edits that arrive on disk while the file is open are tinted until marked
  seen. The Review panel accepts, rejects and replies.
- Agents use the same files through `pa review`
  (`skills/view-kit/scripts/docreview.py`) and the `document-collaboration`
  skill. Participants only suggest; the main agent edits directly for "make a
  change" and suggests for "propose changes".
- Known gaps: no simultaneous typing (no CRDT; the editor offers "Keep mine /
  Load latest" on a clash), and a comment loses its anchor when its text is
  deleted.

## Design tokens

One design language for the app, the view kit, the preview player, the
artifact templates and every artifact (D-37, D-38).

- `design/tokens.json` is the only source: a `base` block (fonts, corners,
  sizes) and a `light` and `dark` value for each color token. Names become CSS
  variables with a `--pa-` prefix; the names and their meanings are the
  contract, the values are replaceable.
- `python3 design/build_tokens.py` writes them into the app
  (`web/src/designTokens.generated.css`, `themePalettes.generated.css`), the
  view kit's `pa-kit.css`, `harness.html` and each template (between
  `pa-tokens:begin` and `pa-tokens:end`). `--check` fails if anything is out of
  date.
- The canvas injects the current tokens and light or dark mode into every
  artifact frame, so artifacts made before a change follow it.
- Meanings (D-48 to D-50): navy for the frame and the one primary action;
  green done, blue ready for review, amber needs you (`--pa-attn`), red only
  for failures (`--pa-fail`), indigo the agent working, and one hue reserved
  for the person's own marks (`--pa-you`, magenta today). The Hangar has its
  own teal family (`build`, `hangar-*`).
- Rules for agents are in `skills/product-aviator-design/`, which wins over the
  vendored `skills/frontend-design/` (D-36).

## The Hangar

Builder mode, where people, workflows, views, scenarios and skills are
defined, clearly separate from flying (D-39, D-40). Spec:
[product/hangar.md](product/hangar.md).

- **Route and frame.** `/hangar`, a full-screen route outside the flying shell
  (D-52): teal band, paper sidebar with a dashed edge, drafting grid. The way
  in is a dashed switch at the foot of the sidebar; things met while flying
  carry a hover-only wrench (D-41, D-51; `web/src/hangar/HangarWrench.tsx`).
- **Catalog.** `GET /v1/slim/hangar` (`omnigent/server/routes/slim_hangar.py`)
  reads the files on every request and runs the same checks as `pa check`.
  Shelves: People and agents, Workflows, Views, Scenarios, Skills, Starters,
  Frameworks, Drafts, History.
- **People.** A person's page is their editor (D-63): name, role, kind, how
  they answer, call-for line, brief, skills (D-66), picture (D-74) and tick
  boxes for where they can be called (D-65). It autosaves to a draft in
  `workspace/.hangar/drafts/people/<id>.md`.
- **Scenarios and workflows.** Edited the same way, with the whole folder as
  the draft (`.hangar/drafts/scenarios/<id>/`, `workflows/<id>/`, D-71). A
  shipped workflow is only ever edited as a copy (D-72). A scenario draft plays
  on its own page (D-73).
- **Aviator pop-over.** A real session in the Hangar project working on the
  open draft, pinnable as a column, with "Try them" (people) or "Play it"
  (scenarios) (D-64; `web/src/hangar/AviatorPopover.tsx`).
- **The gate.** Publish is disabled until every check passes, and a scenario
  must play through (D-44). Every publish keeps the replaced version in
  `.hangar/history/`; Restore is itself a publish (D-46, D-57). A used-by
  guard blocks removing anything still referenced.
- **CLI.** The same moves are `pa draft`, `pa publish`, `pa history` and
  `pa uses`.
- **Configuration travels with the repo** (D-75): people, pictures, scenarios,
  workspace workflows, starters and skills are committed; drafts, history and
  sessions are not. A test fails if `.gitignore` would drop any of them.
- **Fly this demos** (pending in PR 17, D-76 to D-81). "◆ Fly this" on a
  scenario page builds `workspace/demos/<id>/` and a "◆ Demo · <title>"
  project, and opens a session with the opening line ready. Each turn of the
  screenplay is canned or `[live]`; the demo's agent steps through with
  `pa demo next`. Flying again offers Reset to the start or Keep going.

## The Library

The page a session starts from (`/library`; `web/src/pages/LibraryPage.tsx`,
`omnigent/server/routes/slim_library.py`).

- **On `main` today:** artifact templates and canned sessions (prompts with
  fill-in fields, `workspace/templates/sessions/`). "Open in composer" opens a
  new Workspace session with the prompt filled in.
- **Redesign, pending in PR 19 (D-82 to D-88):** the top half is four to six
  featured product skills, each card generated from the `library` block of its
  `workflow.json` (steps, a short form, Start). The lower half is scenarios and
  demos, one card per published scenario, with Fly, a Live turns switch and an
  In flight strip. Canned sessions are retired; artifact templates move to the
  Hangar.

## Modes, runs and projects

A design, not yet built. Spec and open questions:
[product/modes-and-projects.md](product/modes-and-projects.md).

- **Vocabulary.** A *workflow* is a kind of work; a *run* is one workflow on
  one subject, with a state and a where-we-left-off note, and outlives its
  session; a *mode* is what a session shows while a run has the floor; a
  *project* is the goal runs serve; the *intent graph* relates goals.
- **Geoff's answers** (D-89 to D-99): Aviator acts as a project
  director and modes run in threads; a mode shows as a strip on the message
  box and a rail beside its turns; side questions stay outside the rail; pause,
  finish and stop are distinct; one mode at a time; any record can have a
  thread; in-flight work shows on the project page; a project is one
  in-market goal inside a lasting area; the graph's detail waits until needed.
- **What it builds on.** `pa flow` progress files, direct actions, views in the
  chat, amber for needs-you, and upstream's project board, session families,
  child sessions and side chats. Project meaning goes in our own file beside
  upstream's project, so the fork stays compatible.

## Setup on the work Mac

The target is an Apple silicon Mac with Claude Code installed and signed in,
no open internet, no package installs, and no cloning outside the company's
GitHub namespace.

1. Download the repository as a ZIP of `main` in the browser and unzip it
   in Downloads (D-100), or use the one-line `curl` download in the README.
   Setup copies it into `~/flight-deck` and runs it from there (D-111);
   `sh ~/flight-deck/setup.sh` later updates from a newer download without
   overwriting the person's files (`scripts/install_sync.py`, a manifest of
   what was shipped).
2. `sh setup.sh` (D-107): checks the Mac and Claude Code, clears the browser's
   quarantine flag from this folder after asking, restores execute bits,
   checks the bundled tmux, runs `start.sh` and confirms the app answers. It
   writes a report (in the folder and on the Desktop) to send back on
   failure. `start.sh` refuses a still-quarantined copy and points to
   `setup.sh`. Rehearsed in the cloud by `tests/setup_sim/simulate_zip_setup.py`.
3. `./start.sh` (setup runs it the first time): first run unpacks the
   vendored Python and installs vendored wheels into `.runtime/` with no network (about a minute), then starts the
   server and opens `http://127.0.0.1:6767/library`.
4. Optional Dock icon: `scripts/make_dock_app.sh --add-to-dock` builds
   `~/Applications/Product Aviator.app` on the machine (D-103).
5. `./stop.sh` stops it; sessions stay in `~/.omnigent-slim`.

## Where to read the code

| Area | Python | Web (`web/src/`) | Skills |
|---|---|---|---|
| Launch rules, offline | `omnigent/slim_policy.py`, `_offline_guard.py` | | |
| Bootstrap, skills | `omnigent/slim_bootstrap.py`, `slim_skills.py` | | `skills/README.md` |
| Library | `server/routes/slim_library.py` | `pages/LibraryPage.tsx` | |
| Runs and In flight | `server/routes/slim_runs.py` | `projectHome/ProjectInFlight.tsx`, `projectHome/projectRuns.ts` | `view-kit` (`pa flow`, `pa runs`) |
| Hangar | `server/routes/slim_hangar.py` | `hangar/` | `build-person`, `scenario-builder` |
| Inbox participants | `server/routes/slim_participant_inbox.py`, `server/inbox_media.py` | `pages/InboxPage.tsx`, `lib/proactiveInbox.ts` | `participants` |
| Views and actions | | `lib/artifactBridge.ts`, `lib/chatView.ts` | `view-kit` |
| Participants in chat | | `lib/participantTurn.ts`, `components/chat/ParticipantTurn.tsx` | `participants` |
| Collab editor | | `shell/review/` | `document-collaboration` |
| Session panel | | `shell/SessionOverview*.tsx` | |
| Design tokens | `design/build_tokens.py` | `designTokens.generated.css` | `product-aviator-design` |
