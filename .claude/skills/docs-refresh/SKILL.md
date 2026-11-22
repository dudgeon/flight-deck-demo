---
name: docs-refresh
description: Bring Flight Deck's docs up to date with merged and open pull requests, list what is built but not yet verified, and archive decision artifacts (walkthroughs, design rounds) as offline HTML in docs/decision-artifacts/. Use when asked to update or clean up the docs, audit unverified work, or save a decision artifact to the repo.
---

# Docs refresh

A pass that keeps the written record current, so the production team (D-29)
and the next contributor can rebuild the product from the notes. It has three
parts. Do all three unless you were asked for one:

1. **Docs**: history, roadmap, decision index and the feature notes match
   what is on `main` and in open pull requests.
2. **Not yet verified**: the roadmap lists what is built but not yet seen
   working where it matters.
3. **Decision artifacts**: every page used to put a decision to Geoff has an
   offline copy in `docs/decision-artifacts/`, with his recorded answers.

Then put it all in one pull request, and if anything needs Geoff, ask him
the way `CLAUDE.md` says (one decision card at a time, with "Something
else", context and visuals, D-32, D-33, D-105).

Read `CLAUDE.md` first. The rules there win over this skill.

## 1. Docs

Find what changed since the last pass. `docs/history.md` names the last pull
request it covers.

```sh
git fetch origin main
git log --oneline --merges origin/main | head -40       # merged PRs
gh pr list --state open                                 # or the GitHub tools you have
```

For each pull request since the last pass, read its description (it carries
what changed, why, the decision numbers and test results). Then update, in
this order:

| File | What to change |
|---|---|
| `docs/history.md` | One bullet per merged PR under the right day, with its time (UTC), what it did and why, and its D-numbers. A short "Open" list for open PRs. Refresh "Still waiting". |
| `docs/product/roadmap.md` | The snapshot line (which PRs are merged and open), the summary table, each workstream's Done / Next / Open, and "Also still open". A workstream nobody has written up gets a section. |
| `docs/product/decision-index.md` | The audit paragraph: which numbers are on `main`, which open PRs claim which, and the next free number. Flip the status of rows whose PR merged. Never edit `decisions.md` entries; add new ones. |
| `docs/product/features.md`, `docs/architecture.md`, `README.md` | Only where a merged PR changed what a feature is for or how it is built, and its own PR did not already say so. |

Things a person said that are not in any PR (a direction, a pause, a
constraint) belong in history and the roadmap, and, if Geoff decided
something, in `decisions.md` with a new number claimed the careful way
`CLAUDE.md` describes.

Open PRs often edit `roadmap.md` and `decision-index.md` too. Keep your
edits away from their lines where you can, and say in your PR description
which ones to merge first. When they land, merge `main` into your branch and
resolve the conflicts yourself.

## 2. Not yet verified

`docs/product/roadmap.md` has a "Not yet verified" section. Rebuild it each
pass from what you can check, and date it. Look for:

- **Draft or conflicting pull requests**, and who has to act (only Geoff, or
  GitHub's Ready for review button, takes another thread's draft out of
  draft).
- **Machines running old builds.** On the Mac mini, compare the checkout
  (`~/claude-home/omnigent-slim`) with `origin/main`: `git log -1`,
  `git rev-list --count HEAD..origin/main`. If you cannot reach it, say so.
- **Features only ever run in the cloud** or in a simulation (the work-Mac
  setup, Inbox messages, the kinds of work never run live).
- **Known gaps** a thread reported but nobody fixed.
- **Tools contributors rely on** outside the repo (for example the image
  skill's keys and models), noted briefly.

State each item as a fact with how you know it. Do not guess.

## 3. Decision artifacts

`docs/decision-artifacts/` holds offline copies of the walkthroughs, design
rounds, proposals and mockups that decisions were put to Geoff with. They are
the record behind `decisions.md` and worked examples of how to ask. Anyone can
open them from a clone or a ZIP, with no claude.ai account.

The folder:

- `artifacts.json`: one entry per artifact. Fields: `id` (the end of its
  claude.ai URL, or `local-<name>` for one that only lived in the project
  files), `url`, `slug` (`YYYY-MM-DD-short-name`), `date`, `title`,
  `kind`, `about` (what it asked, one line), `decisions` (what it led to,
  as a pointer), `status`, optional `answers_as_of`, `note`,
  `archived: false`.
- `<slug>/index.html` and its images: the copy. `<slug>/answers.json`: the
  answers recorded on the page, when it had any.
- `README.md` and `index.html`: generated from `artifacts.json`.

`scripts/archive_artifacts.py` (standard library only) does the copying:

```sh
S=.claude/skills/docs-refresh/scripts/archive_artifacts.py
python3 $S add --id <id> --src <fetched folder> [--answers <answers folder>]
python3 $S index      # rebuild README.md and index.html
python3 $S check      # every entry present, nothing loads from the network
```

`add` makes the copy offline-safe: it drops remote font links, points links
to other archived artifacts at their copies, adds a note at the top, and
replaces the page's database with the recorded answers, so locked answers
show and nothing saves. Run `add` again to refresh a copy.

### Finding them

- **Published pages.** In a Claude project, `list_project_artifacts` lists
  them; the Artifact tool's `list` does too. Decision pages are linked from
  `decisions.md`, `roadmap.md`, `hangar.md`, `modes-and-projects.md` and
  project memory. Anything titled as a walkthrough, decisions, round, design,
  proposal or options is in scope. Skip ones already in `artifacts.json`
  unless they changed since (compare the artifact's last update with
  `answers_as_of` or the copy's date).
- **Project files.** Mockups and drafts under the project's shared folder
  (for example `collab-editor/mockup.html`). Prefer the published version
  when both exist; the files are often its source.

### Fetching one

With the Artifact tool, for each artifact:

1. `read` with `path: "index.html"` and an `out_dir` in your scratchpad.
2. `list` with `scope: "files"`, then `read` with `paths` (the images and
   any scripts or views) into the same `out_dir`.
3. If the page saved answers (it calls `window.claude.use("db")`), read its
   `answers` collection with the ArtifactData tool, `action: "list"`, with an
   `out_dir`. Pass the `answers` folder it writes to `--answers`.

A page made with the `decision-brief` skill (D-153) needs no fetching: its
brief's JSON is in the repo or the project files. Import the answers into it
(`brief.py import <brief> --db <answers folder>`), render it as a full page
into a folder, and `add` that folder with `--answers`. Its decision note
(`brief.py note`) goes in the same archive folder as `note.md`.

A Claude Doc (an artifact of type "Docs") has no page to copy. Export it as
HTML (the doc's menu, or the Claude Docs export tool) into a folder as
`index.html`, or mark it `archived: false` with a note.

Without those tools, ask Geoff to save the page from his browser ("Save Page
As", web page complete) into the project files, and archive that.

### Before committing

- Read each new copy yourself before you commit it: it goes into a public
  repository. It must hold no keys, no personal details beyond Geoff's name
  and his own answers, and nothing a viewer wrote that is not about the
  product.
- `check` passes.
- Open a few copies with external requests blocked (Playwright, as in
  `CLAUDE.md`), in light and dark, and confirm the recorded answers show.
- Keep images as published. If a folder passes about 5 MB, say so in the PR.

## Pull request

One PR for the pass. In the description: what changed in the docs, the
"Not yet verified" list as it stands, the artifacts added (titles), the
checks with results (`archive_artifacts.py check`, the browser check), and
any decision numbers (normally none). Screenshots of a copy or two go in the
project's shared files, not the repo.

## Asking Geoff

When the pass finds work only Geoff can unblock (a draft to take out of
draft, a restart, a round he has not answered, a key to top up), tell him in
one short message what needs him, in order, then put the first decision on a
card. Give each card the context, the real options with what happens, the
visuals (attach screenshots or link the archived copy), a recommendation with
its reason, and "Something else". One card at a time.
