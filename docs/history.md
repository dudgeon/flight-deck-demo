# History

How Flight Deck got to where it is, from the first import on 20 November 2026
to now. Written so the production team, and any contributor or agent joining
later, can see what was tried, in what order and why. Times are UTC.
Decision numbers (D-nn) are in [product/decisions.md](product/decisions.md);
their current status is in [product/decision-index.md](product/decision-index.md).

## The starting point

Geoff, the product owner, wanted to prototype an agent workspace for product
managers: a "product partner" where unstructured work with context files and
generated artifacts alternates with templated, structured flows (D-04). A
team at his work will productionize [Omnigent](https://github.com/omnigent-ai/omnigent),
an open-source meta-harness, so the prototype is a fork of it rather than a
new app, close enough that what is learned transfers (D-01).

The work computer sets hard limits (D-02): no Claude API (so Claude Code is
driven as a terminal program on the user's own login), no bypassing Claude
Code's permissions, no open internet and no package installs, so every
dependency is vendored. It is an Apple silicon Mac that cannot clone
repositories outside the company's GitHub namespace, so the repository
arrives as a ZIP (D-100). Development happens on Geoff's Mac mini at home and
in cloud agent sessions; the public repository is `dudgeon/omnigent-slim`.

## 20 November: a slim, offline fork

- **Import and strip.** Upstream Omnigent was imported at `068c6a9a053b`, then
  the mobile and desktop shells, tests, docs, CI and deploy trees were removed.
- **Lock it down.** The offline guard, Claude Code as the only harness, the
  Library page and the artifact bridge. Hatchling and editables were vendored
  so editable installs work with no index. Loopback-only CSP, Claude Code's
  non-essential traffic switched off, `ui_open_file` pre-allowed in
  Omnigent's own launch settings (a workspace allow list made Claude Code
  re-ask for folder trust, which a web session cannot answer).
- **Stay close to upstream.** An `UPSTREAM` pin and
  `scripts/sync_upstream.sh`; the first sync brought the web UI to
  `bd08c5e61850`.
- **Docs and skills.** A step-by-step README from ZIP to first session, the
  customizing guide, the skill-writer reference (`docs/skill-writers/`) and
  bundled skills in `skills/`, linked into every session.
- **Defaults and brand.** Auto permission mode restored as the default, with
  Opus 5.5 at medium effort (D-03); the Product Aviator logo replaced
  upstream's, then moved to the sidebar's top left, and the new-session
  heading went.
- **Dock launcher.** `scripts/make_dock_app.sh` builds a local app that starts
  the server and opens the UI (D-103).
- **Canvas tools.** Claude can read, click and edit the artifact in the
  viewer; with a session open in several tabs, one tab is active (D-101).

## Night of 20 to 21 November: the product workspace

Geoff described the long-term shape (two template classes: chat widgets and
canvas workflows; a real example of PRD to requirements catalog to
per-requirement dependency mapping) and asked for questions before building.
Decided one card at a time: one template system for chat and canvas (D-05),
not overfitting to the PRD (D-06), one dataset that stages extend (D-07),
demos first (D-08), skills carry the know-how (D-09).

- **PR 1** (merged 13:16): the view kit (`pa`, data plus small JSON specs,
  D-10), the first two workflow scenarios, the Session panel (D-13 to D-16),
  direct actions for state changes (D-11, D-12), participants with one
  global roster and markdown screenplays (D-17 to D-22).

## 21 November, morning: a decision walkthrough

The first decision walkthrough put seventeen questions to Geoff, each with
its context and visuals. His answers became D-23 to D-34 and the backfilled
D-100 to D-106: Aviator may call participants itself, `@name` addressing,
layout direction A, context per project, the four next kinds of work, how he
wants to be asked (cards, never blind, D-32, D-33), PRs merged by an agent
with Geoff reviewing only designs and test summaries (D-28), ignore the
production build and document intent (D-29), other PMs will write scenarios
inside the app (D-30), the work-Mac ZIP install (D-100).

- **PR 2** (13:50): the collaborative markdown editor, with CriticMarkup
  suggestions in the file, sidecar comment threads and `pa review` for agents
  (D-26, D-104).
- **PR 3** (13:48): participants' `@mentions`, whole-conversation access and
  calling without asking (D-23 to D-25), plus the four kinds of work as
  previews: decision review, problem discovery, delivery status and intent
  shaping with its notional framework (D-31, D-33, D-34). The product notes
  (`docs/product/`) started here.
- **PR 4** (13:56): one design language from `design/tokens.json` for the app,
  the view kit, templates and every artifact (D-36 to D-38). The fork was named
  **Flight Deck**, with Product Aviator kept as the UI's name (D-35).

## 21 November, midday: the Hangar is designed, colors locked

- **PR 5** (14:32): the Hangar, builder mode, designed with a clickable mockup
  and all seven decisions locked (D-39 to D-47). Geoff's one change: the
  in-flight link must be a near-invisible wrench (D-41, D-51).
- **PR 6** (14:40): the first live run (delivery status, about ninety seconds).
  It worked, and showed that a participant only knows what their file says,
  which made per-scenario casts necessary.
- **PR 7** (14:43): `docs/product/roadmap.md`, a where-things-stand page.
- **PR 8** (14:52): the second walkthrough locked the colors: navy frame,
  magenta for the person's own marks, amber for needs-you and red only for
  failures (D-48 to D-50).

## 21 November, afternoon: building the Hangar and the chat views

- **PR 9** (14:58): Hangar slice 1, the read-only look-around mode on its own
  route (D-52).
- **PR 10** (14:59): asks in the chat, work in the canvas (D-53), the intent
  framework kept (D-54), and the canvas greying while the chat waits (D-55).
  Its numbers collided with PR 9's and were renumbered before merging; that
  is where the numbering rule in `CLAUDE.md` comes from.
- **PR 11** (15:11): Hangar slice 2, the person builder with drafts, checks,
  publish and history (D-56 to D-59).
- **PR 12** (15:45): a fix for a phantom Inbox badge.
- **PR 13** (15:59): editing people in place with an Aviator pop-over (D-63 to
  D-66), after Geoff found leaving the Hangar for a flying session "clunky,
  opaque, mysterious". Also the split of scenarios out of workflow folders
  (D-42, D-67).
- **PR 14** (16:10): Hangar slice 3, scenario and workflow builders (D-71 to
  D-73). All three slices of D-45 were now built.
- **PR 15** (17:16): pictures for people and agents, and configuration that
  travels with the repo (D-74, D-75).
- **PR 16** (17:18): participants message the user through the Inbox (D-68 to
  D-70).

## 21 November, evening: demos, the Library and modes

- **PRs 18 and 20** (18:49, 18:54): the modes, runs, projects and intent graph
  exploration, with eleven questions and a survey of what upstream
  Omnigent already has (`docs/product/modes-and-projects.md`).
- **PR 17** (open): fly a scenario as a demo, with canned and live turns
  (D-76 to D-81).
- **PR 19** (open, stacked on 17): the Library redesign, featured skills on top
  and demos below, all generated from their own files (D-82 to D-88).
- **PR 21** (merged): Geoff's answers to the modes walkthrough, D-89 to D-99.
  The headline: the main Aviator session acts as a project director, and
  workflows run in their own threads. A second walkthrough holds four
  remaining questions.
- **This documentation pass**: the decision index, this history, the
  architecture overview, a refreshed roadmap and a root `CLAUDE.md` for
  contributors' agents.

## Still waiting

- The one-step setup script for a browser-downloaded ZIP (D-100).
- Live runs of decision review and problem discovery.
- Progressive complexity (D-54) and the remaining modes questions.
- Whether to rename the repository (D-35), and D-24 for production.

## How the work is run

Each piece of work is a thread with its own agent session, started by a
coordinating agent that talks to Geoff. Threads open pull requests; one
thread reviews and merges them; Geoff looks at designs and test summaries
only (D-28). Decisions are put to him as walkthroughs and decision cards with
real visuals (D-32, D-33, D-105), and each locked answer is logged the same
day. Several threads write to `docs/product/decisions.md` at once, which is
why decision numbers are claimed against open pull requests as well as
`main`.
