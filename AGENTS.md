# Working on Flight Deck (omnigent-slim)

Flight Deck is a cut-down fork of [Omnigent](https://github.com/omnigent-ai/omnigent)
for prototyping an agent workspace for product managers on a locked-down work
Mac. Its user interface is **Product Aviator**. The repository, folders,
commands and code identifiers keep the name `omnigent-slim` (D-35). It drives
Claude Code as a terminal program, runs offline, and is fully vendored.

This file is for contributors' agents, whatever harness they run in.
`CLAUDE.md` is a link to it, so there is one copy to keep current. Read it
whole before changing anything.

## Orient first

Read these in order, and the rest only as needed:

1. `README.md`: what it is, and how a person installs and runs it.
2. `docs/architecture.md`: how every part is built and where its code is.
3. `docs/product/decision-index.md`: every decision and where it stands.
   The full wording is in `docs/product/decisions.md`.
4. `docs/product/roadmap.md`: each workstream's done, next and open items.
5. `docs/history.md`: how it got here, pull request by pull request.

Then the doc for your area: `docs/product/features.md` (intent of each
feature), `docs/product/hangar.md` (builder mode),
`docs/product/modes-and-projects.md` (modes and projects design),
`docs/customizing.md` (templates, styles, where code lives) and
`docs/skill-writers/` (how skills detect and use Omnigent).

Vocabulary used everywhere: **flying** is using the app; the **Hangar** is
builder mode (`/hangar`). A **workflow** is a kind of work (a skill folder
with a `workflow.json`); a **scenario** is one demo story that runs a
workflow (`workspace/scenarios/<id>/`). A **participant** is another agent or
person in the conversation, from the roster in `workspace/participants/`.

## Repository layout

| Path | What it is |
|---|---|
| `omnigent/` | Upstream's Python server, runner and harnesses. Slim pieces: `slim_policy.py` (launch rules), `slim_bootstrap.py` (Workspace and Hangar projects), `slim_skills.py` (bundles `skills/`), `_offline_guard.py`, `server/routes/slim_*.py` (Library, Hangar, Inbox participant messages) |
| `omnigent/server/static/web-ui/` | The **built** web UI, committed |
| `web/src/` | Web UI source (React, Vite). Slim areas: `hangar/`, `shell/review/` (collab editor), `shell/SessionOverview*.tsx`, `lib/artifactBridge.ts`, `lib/chatView.ts`, `lib/participantTurn.ts`, `pages/LibraryPage.tsx`, `pages/InboxPage.tsx` |
| `skills/` | Bundled skills, in every session. `view-kit/scripts/pa.py` is the `pa` command |
| `workspace/` | Where sessions run: `participants/`, `scenarios/`, `context/`, `data/`, `artifacts/`, `frameworks/`, `templates/`, `progress/`; `.hangar/` (drafts, gitignored); its own `CLAUDE.md`, which is for sessions, not contributors |
| `design/` | `tokens.json` (the only source of colors, fonts and corners) and `build_tokens.py` |
| `docs/` | Architecture, history, product notes, customizing, skill-writer reference |
| `tests/` | `test_slim_*.py` pytest suites |
| `vendor/` | Python runtime, wheels, tmux, and `scripts/build_vendor.sh` |
| `scripts/` | `sync_upstream.sh`, `make_dock_app.sh`, build helpers |
| `start.sh`, `stop.sh` | Start and stop everything (macOS, Apple silicon) |
| `UPSTREAM` | The upstream commit this fork is synced to |

## Running the app

- `./start.sh` sets up `.runtime/` on first run (offline, about a minute),
  starts the server and opens `http://127.0.0.1:6767/library`. If 6767 is busy
  it takes the next free port and prints it. `./start.sh --no-open` skips the
  browser. `./stop.sh` stops it. Session data is in `~/.omnigent-slim`.
- `start.sh` is macOS-only. In a Linux container, use a plain venv:
  `pip install -e sdks/python-client -e sdks/ui -e .`, then `omnigent start`.
  On a machine with internet, `uv sync` and `uv run omnigent start` also work.
- Sessions started from the **Workspace** project run in `workspace/`;
  Hangar builds run in the **Hangar** project.

## Tests and checks

Run what your change touches, and put the results in the pull request:
Geoff reads test summaries, not code.

| Check | Command | When |
|---|---|---|
| Python tests | `pytest tests/` | Any server, `pa` or workspace-file change |
| Scenario checks | `python3 skills/view-kit/scripts/pa.py check workspace/scenarios/<id>` (a workflow folder in `skills/<id>` works too) | Any workflow, scenario, view or script change. All seven scenarios must pass |
| Roster check | `cd workspace && python3 ../skills/view-kit/scripts/pa.py who --check` | Any change in `workspace/participants/` |
| Token check | `python3 design/build_tokens.py --check` | Any style or token change; must report nothing out of date |
| Types | `pnpm install --frozen-lockfile`, then `npx tsc -p web/tsconfig.json --noEmit` | Any `web/src/` change |
| Web tests and lint | `pnpm --filter web run test`, `pnpm --filter web run lint` | Any `web/src/` change |
| In the browser | the running app and `pa preview`, with external requests blocked (Playwright) | Any visible change; attach screenshots |

A UI change is not done until you have looked at it in the running app, in
light and dark mode. Screenshots for Geoff go in the project's shared files,
not in the repo.

## Rules that keep it usable on the work Mac

- **Nothing reaches the internet at runtime.** No CDN links, remote fonts or
  images, telemetry, update checks or downloads. Python runs behind
  `omnigent/_offline_guard.py`; never weaken it or reintroduce uvloop.
  Artifacts are single self-contained HTML files.
  The one exception is the Hangar's "Send to repo" (D-113): a `git push` (and
  `gh pr create`) that runs only when a person presses it, on a git copy.
- **Everything is vendored.** Nothing is installed at work. A new Python or
  npm dependency must be vendored: rebuild with `vendor/scripts/build_vendor.sh`
  and commit `vendor/wheels/`. Prefer the standard library (`pa.py` uses
  nothing else).
- **Never bypass Claude Code permissions.** All launches go through
  `omnigent/slim_policy.py`. Don't add `--dangerously-skip-permissions`,
  `bypassPermissions` or `dontAsk` (Auto is allowed and the default), and
  don't pre-approve tools beyond `ui_open_file` (allowed in
  `omnigent/harnesses/claude_native/bridge.py`; a project
  `.claude/settings.json` allow list makes Claude Code re-ask for folder trust,
  which a web-driven session cannot answer).
- **The built web UI is committed** in `omnigent/server/static/web-ui/`. After
  changing `web/src/`, run `pnpm --filter web run build`, delete `*.map`, and
  commit the output. When it conflicts in a merge, don't hand-merge it: delete
  the folder, rebuild from the merged source, delete `*.map`, commit.
- **Stay close to upstream.** Mark slim-specific changes to upstream files
  with a short `omnigent-slim:` comment so they're easy to find when pulling
  from upstream (`scripts/sync_upstream.sh`). Keep our own data in our own
  files beside upstream's (a project's meaning goes in a file, not in
  upstream's project table) so the production team can follow upstream.
- **Configuration travels with the repo** (D-75). People and their pictures,
  scenarios, workspace workflows (`workspace/.claude/skills/`), starters and
  skills are committed. Drafts (`workspace/.hangar/`), flown demos
  (`workspace/demos/`) and sessions are not. A test fails if `.gitignore` would
  drop configuration.

## Design tokens

- **Style only with the tokens.** Colors, fonts and corners come from
  `design/tokens.json` as `--pa-…` CSS variables, in the app, the view kit,
  templates and artifacts alike. Never write a literal color, font stack or
  radius. Meanings and rules: `skills/product-aviator-design/`, which wins over
  the vendored `frontend-design` where they disagree.
- After editing `tokens.json`, run `python3 design/build_tokens.py`, then
  `--check`, then rebuild the web UI.
- Keep the meanings (D-48 to D-50): navy is the frame and the one primary
  action; green done, blue ready for review, **amber needs you**, **red only
  for failures**, indigo the agent working, and one hue (`--pa-you`, magenta
  today) reserved for what the person did, never for status. The Hangar's teal
  is used for nothing else. Sentence case, no small all-caps labels.
- In flying mode, links into the Hangar are a hover-only wrench with no words
  (D-51). Nothing about the Hangar may show in a demo recording.

## Decisions and feature intent

The production team will rebuild this product from our notes (D-29), so
writing down intent is part of every change.

- **When the product owner decides something,** add an entry to
  `docs/product/decisions.md` in its topic section and a row in
  `docs/product/decision-index.md`. Format:
  `**D-NN · YYYY-MM-DD · Who.** The decision. *Why.*` "Who" is Geoff, Claude
  (a choice made while building), or "Geoff asked, Claude chose". Always give
  the why.
- **Claim the next D-number carefully.** Several threads add decisions at
  once, and numbers have collided before (PRs 9 and 10). Before writing one:
  1. `git fetch origin main`, then find the highest number on `main`:
     `git show origin/main:docs/product/decisions.md | grep -o 'D-[0-9]*' | sort -t- -k2 -n | tail -1`.
  2. Check open pull requests for numbers they claim (`gh pr list --state open`,
     then each one's diff of `decisions.md`), and the "Pending" rows of
     `decision-index.md`.
  3. Take the next free number after both, and list the numbers you use in
     the pull request description.
  4. Before merging, check again. If another pull request merged the same
     numbers first, renumber yours and every reference to them
     (`features.md`, `roadmap.md`, `hangar.md`, the index).
  Never reuse a skipped number (D-60 to D-62 stay unused).
- **Never rewrite an old entry.** Add a new one that refines or replaces it,
  and update both rows in the index. Status lives in the index, not the log.
- **Questions not yet decided** get labels of their own (for example M-1 in
  `modes-and-projects.md`), never D-numbers.
- **When you add or change a feature,** update its section in
  `docs/product/features.md` with what it is for, not only what it does, and
  move its workstream in `docs/product/roadmap.md`, in the same pull request.
- **Asking Geoff.** One question at a time as a decision card, never a list in
  prose (D-32); always with a "Something else" option (D-105); never blind:
  context, real options with consequences, the actual visuals, and a
  recommendation with its reason (D-33).

## Pull requests

- Work on a branch and open a pull request against `main`. Don't mark it as a
  draft: drafts stall the merge queue.
- **Agents review and merge.** A review-and-merge agent merges pull requests.
  Geoff reviews only designs and test-result summaries, never code (D-28). So
  the description must carry: what changed and why, the decision numbers it
  adds, the checks you ran with their results, and screenshots of anything
  visible.
- Rebase on `main` before asking for a merge. If your branch is stacked on
  another pull request, say so at the top of the description.
- The cloud proxy cannot delete branches; leave that to GitHub's button or the
  Mac mini.

## Skills

- **Bundled skills** live in `skills/<name>/SKILL.md` and are linked into
  every session by `omnigent/slim_skills.py`, appearing as `/claude:<name>`
  (see `skills/README.md`). The main ones: `view-kit` (datasets, views, `pa`),
  `participants`, `document-collaboration`, `scenario-builder`,
  `build-person`, `product-aviator-design`, `frontend-design` (vendored,
  Apache 2.0, unchanged), `omnigent-operator` (an example for skill writers),
  and the workflows `problem-discovery`, `intent-shaping`, `decision-review`,
  `delivery-status`, `document-review`, `prd-to-requirements` and
  `requirements-to-dependencies`.
- **Workflows built in the Hangar** publish to `workspace/.claude/skills/<id>/`
  and take over a shipped workflow's id (D-72). Shipped workflows in `skills/`
  change only as a deliberate repo change.
- **Writing a skill** that uses Omnigent's viewer, sessions or tools: see
  `docs/skill-writers/`.

## Things not to do

- Don't add network calls, CDN assets or unvendored dependencies.
- Don't hand-edit generated files: the token blocks between
  `pa-tokens:begin` and `pa-tokens:end`, `web/src/*.generated.css`, or the
  built web UI.
- Don't write live roster, scenario or workflow files from code other than
  `pa publish` and the Hangar's publish routes; drafts go in `.hangar/`.
- Don't rename the repository, folders or identifiers to Flight Deck until
  Geoff says so (D-35).
