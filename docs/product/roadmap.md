# Where things stand

A snapshot of every workstream in Flight Deck (the fork) and Product Aviator
(its user interface): what is done, what is only partly done, what comes next,
what is still to be decided, and where to read more. Written for the
production team and for whoever picks the work up next.

Snapshot refreshed 2026-11-21 evening, after pull requests 1 to 16, 18, 20
and 21 were merged; 17 and 19 are open. Where each decision stands is in
[decision-index.md](decision-index.md); the story so far is in
[../history.md](../history.md). Decision
numbers (D-nn) refer to [decisions.md](decisions.md); feature intent is in
[features.md](features.md). When a workstream moves, update its section here
in the same pull request.

| Workstream | State |
|---|---|
| [Hangar (builder mode)](#hangar-builder-mode) | Built: all three slices, pictures, config in the repo |
| [Demos and the Library](#demos-and-the-library) | In open PRs 17 and 19 |
| [Design language and tokens](#design-language-and-tokens) | Built; colors locked |
| [Views in the chat](#views-in-the-chat) | Built |
| [Collaborative markdown editor](#collaborative-markdown-editor) | Built; two known gaps |
| [Participants and personas](#participants-and-personas) | Built, scripted and live, with Inbox messages; some gaps |
| [The four kinds of work](#the-four-kinds-of-work) | Built as previews; two run live so far |
| [Work-Mac setup from a ZIP](#work-mac-setup-from-a-zip) | Setup script not built yet |
| [Canvas tools across several tabs](#canvas-tools-across-several-tabs) | Done |
| [Dock launcher](#dock-launcher) | Done |
| [Branding](#branding) | Done; one naming question open |
| [Modes, projects and the intent graph](#modes-projects-and-the-intent-graph) | D-89 to D-99 decided; four questions open; nothing built |

---|---|
| [Hangar (builder mode)](#hangar-builder-mode) | Designed and decided; slice 1 of 3 being built |
| [Design language and tokens](#design-language-and-tokens) | Built; three colors and two other questions waiting on Geoff |
| [Collaborative markdown editor](#collaborative-markdown-editor) | Built; two known gaps |
| [Participants and personas](#participants-and-personas) | Built, scripted and live; some gaps |
| [The four kinds of work](#the-four-kinds-of-work) | Built as previews; one run live so far |
| [Work-Mac setup from a ZIP](#work-mac-setup-from-a-zip) | In progress, not merged |
| [Canvas tools across several tabs](#canvas-tools-across-several-tabs) | Done |
| [Dock launcher](#dock-launcher) | Done |
| [Branding](#branding) | Done; one naming question open |
| [Modes, projects and the intent graph](#modes-projects-and-the-intent-graph) | Partly decided (D-89 to D-99); four decisions open; nothing built |

---

## Hangar (builder mode)

The Hangar is a second mode of the app where people, workflows, views,
scenarios and skills are defined, clearly distinct from "flying" (using the
app). Building happens on a draft copy, with a strict publish gate and a way
back.

- **Done.** Design and all decisions (D-39 to D-47, D-51, D-52). Slice 1, the
  read-only look-around (PR 9). Slice 2, the person builder with drafts,
  checks, publish, history and the used-by guard (PR 11, D-56 to D-59).
  Editing people in place with the Aviator pop-over, casting and skills from
  the person's page (PR 13, D-63 to D-66). The scenario folder split (D-42,
  D-67). Slice 3, scenario and workflow builders (PR 14, D-71 to D-73).
  Pictures for people and agents, and configuration that travels with the
  repo (PR 15, D-74, D-75). `pa draft|publish|history|uses`.
- **In an open PR.** "◆ Fly this" on a scenario page (PR 17, see below).
- **Next.** Builder skills for workflows and skills (`build-workflow`,
  `build-skill`) beyond `build-person` and `scenario-builder`.
- **Open.** Left for later by design: sharing a workflow or scenario with
  another PM as one file, and a second person's approval before publishing (a
  production feature, D-44).
- **Read.** [hangar.md](hangar.md); features.md "The Hangar"; mockup at
  https://claude.ai/artifact/9M4JGs5WuxigJz1jiJ9QVr.

## Demos and the Library

A scenario you build becomes a demo you fly, and the Library is where real
work and demos start.

- **In open PRs.** PR 17: flying a scenario makes a "◆ Demo · <title>" project
  with its own folder; each screenplay turn is canned or live; Reset to the
  start or Keep going (D-76 to D-81). PR 19, stacked on 17: the Library shows
  four to six featured skills generated from `workflow.json`, then a card per
  scenario with Fly and a Live turns switch; canned sessions retired and
  templates moved to the Hangar (D-82 to D-88).
- **Next.** Merge 17, then 19. Then run each demo end to end on the work Mac.
- **Open.** D-87 does not record who decided it.
- **Read.** The two pull requests; design round at
  https://claude.ai/artifact/5XhbdjSKp7i2t1ChoxqS6Z.

## Design language and tokens

One set of design tokens for the app, the chat widgets and canvas views (the
view kit), the preview player and the artifact templates, so the product
looks like one product and a change is made once (D-37, D-38).

- **Done.** `design/tokens.json` is the only source; `design/build_tokens.py`
  writes it everywhere (`--check` finds anything out of date). The canvas
  injects the tokens and light or dark mode into every artifact. Colors
  locked by Geoff (PR 8): navy frame (D-48), magenta reserved for the person
  (D-49), amber for needs-you and red only for failures (D-50).
- **Partial.** Upstream Omnigent's Settings → Appearance palettes still exist
  and override the default palette in one browser.
- **Next.** None scheduled. When a corporate palette arrives, change the
  values and keep the meanings.
- **Open.** None.
- **Read.** D-35 to D-38, D-48 to D-50; [../architecture.md](../architecture.md)
  "Design tokens"; `skills/product-aviator-design/`.

## Views in the chat

- **Done (PR 10).** Questions, pick-ones, single cards and summaries are drawn
  in the conversation and fold to "Answered"; catalogs, boards and documents
  stay in the canvas (D-53). The canvas greys while a chat view waits, as an
  exploration (D-55). Tested live with intent shaping.
- **Not done.** Participants cannot put a view in their own turn; the preview
  player does not fold its chat widgets.
- **Open.** Progressive complexity (D-54).
- **Read.** features.md "Views in the chat".

## Collaborative markdown editor

A person and agents work in the same markdown document: agents' edits are
highlighted, changes can be tracked as suggestions, comments are threaded,
everything is attributed, and `@name` in a comment asks that participant to
reply.

- **Done (PR 2).** A review layer on upstream's TipTap editor
  (`web/src/shell/review/`). Suggestions are stored in the `.md` itself as
  CriticMarkup with the author; comment threads live in a sidecar
  `<doc>.md.review.json`; direct edits that arrive on disk are tinted until
  marked seen; a Review panel to accept, reject and reply. Agents use the
  same files through `pa review` and the `document-collaboration` skill.
  Participants only ever suggest (D-26); the main agent edits directly when
  asked to "make a change" and suggests when asked to "propose changes".
  An `@mention` was tested live: a stand-in replied in the thread in about a
  minute.
- **Known gaps.**
  - No simultaneous typing. There is no shared live document (no CRDT): the
    editor reloads from disk and offers "Keep mine / Load latest" when the
    agent and the person both changed the file.
  - A comment loses its anchor when the text it points at is deleted. The
    thread stays in the sidecar but no longer marks a place in the document.
- **Next.** Nothing scheduled. If either gap blocks a demo, fix the anchor
  first (keep the thread at the nearest surviving text and mark it
  "text removed"); live co-typing would need a CRDT and a server change and
  should wait for the production design.
- **Open.** None.
- **Read.** D-26, D-104; features.md "Collaborative markdown editor";
  `skills/document-collaboration/`; upstream's feature map
  `feature-map/markdown-editor.md` (in the upstream repository).

## Participants and personas

Other agents and people take part in the conversation, attributed as
themselves: a scripted demo character, an agent with a persona running in its
own background session, and later real agents and people.

- **Done (PRs 1 and 3).** One global roster in `workspace/participants/`
  (one markdown file each, with a README and a template); scenarios name who
  is eligible. `pa who` and `pa who --check`. The `participants` skill tells
  Aviator how to find and call someone; a live participant is a background
  session it can open and read (D-19), never a sub-agent. Attributed turns
  in the chat with the stand-in label (D-22), `@name` in the main chat
  (D-25), the whole conversation shared with them (D-24, for demos), calling
  in on Aviator's own judgment with a note saying so (D-23). People and
  agents card in the Session panel. Two live participants called in parallel
  replied in about a minute each.
- **Done (PR 16).** Participants reach the user through the Inbox (D-68 to
  D-70): `pa tell` puts a participant's message, or their invitation into a
  session of their own, in the Inbox under their name and mark, with a People
  tab. Cards open the conversation; there is no reply from the Inbox.
- **Partial.**
  - No shipped scenario uses `pa tell` yet; a demo where Risk Review pulls the
    user into its session is the obvious first one.
  - A live participant cannot place a comment on a document anchor through
    the app's own comments (the app has no tool to create one), so their
    findings carry the quoted text and section instead. Comments through the
    collab editor's `pa review` do work.
  - A live turn is a single named block, not the foldable call block the
    previews show.
- **Next.** Revisit "a participant sees the whole conversation" for
  production (D-24). The Hangar's person builder (built) is now the way to
  add someone.
- **Open.** D-24 is explicitly a demo-only choice.
- **Read.** D-17 to D-26, D-68 to D-70; features.md "Participants";
  `workspace/participants/README.md`; `skills/participants/`.

## The four kinds of work

Decision review, problem discovery, delivery status update and intent
shaping (D-31). Each is a skill folder with record shapes, views, invented
data and a screenplay, and runs as a click-through preview with no agent.
Their invented material chains into one story, and each also stands alone.

- **Done.** All four built with previews, canned sessions on the Library page
  and `pa check` passing. Decision review is modelled on how Geoff wants
  decisions put to him (D-33). The intent framework is a swappable markdown
  file, `workspace/frameworks/intent.md` (D-34).
- **Partial.**
  - Delivery status (about 90 seconds) and intent shaping (views in the chat)
    have been run live with an agent. It worked, and showed that a participant only knows
    what their file says, so a convincing live demo needs each scenario to
    give its cast that scenario's facts; the scenario folders (D-67) and
    `cast/` notes (D-79, PR 17) provide that. Decision review and problem
    discovery have not been run live.
  - The intent framework is a notional draft; Geoff kept it as drafted
    (D-54) and wants progressive complexity next.
- **Next.** Run the other three live in the app and fix what breaks,
  starting with decision review (it reuses the most). Then let Geoff react to intent
  shaping live, and swap in the real company framework when there is one.
- **Open.** Progressive complexity (D-54).
- **Read.** D-31, D-33, D-34; features.md, one section per kind of work;
  `skills/decision-review/`, `skills/problem-discovery/`,
  `skills/delivery-status/`, `skills/intent-shaping/`;
  `workspace/frameworks/`.

## Work-Mac setup from a ZIP

The work Mac cannot clone repositories outside the company, so the app
arrives as a ZIP of `main` and has to be set up by someone who is not
technical (D-100).

- **Done.** Everything is vendored (Python, wheels, tmux, the built web UI).
  `sh setup.sh` takes a browser-downloaded ZIP to a running app: it checks
  the Mac and Claude Code, clears the download flag from its own folder after
  asking (D-107), restores execute bits, starts the app on port 6767 and
  writes a report to send back if it stops. The README walks through it in
  plain steps, with a one-line `curl` download as the other way.
  It installs into `~/flight-deck`, and `sh ~/flight-deck/setup.sh` updates
  from a newer download without overwriting the person's files or edits
  (D-111). `tests/setup_sim/simulate_zip_setup.py` rehearses it in a Linux
  container: install, update with the person's edits, moving out of
  Downloads, and four failures.
- **Next.** Geoff's first real install on the work Mac.
- **Open.** Whether the work Mac's management locks the download flag or
  blocks the bundled binaries; setup detects both and says so, but only the
  real machine will tell.
- **Read.** README "Quick start"; D-02, D-100, D-107, D-111; `setup.sh`, `scripts/install_sync.py`; [../architecture.md](../architecture.md)
  "Setup on the work Mac".

## Canvas tools across several tabs

Claude can read, click, type in and run script inside the artifact open in
the canvas (`canvas_*` tools), inside the sandboxed frame in the person's own
browser tab, with nothing pre-approved.

- **Done.** When a session is open in several tabs, the server keeps one
  active canvas per session; the others dim and offer "Use this tab", and a
  call that moves to another tab carries a note telling Claude to read the
  page again. The tabs are not mirrored: each keeps its own copy of the
  page's state, by design.
- **Next / open.** None.
- **Read.** D-101; `docs/skill-writers/artifacts.md`;
  `omnigent/server/routes/sessions/routes_browser.py`.

## Dock launcher

- **Done.** `scripts/make_dock_app.sh` builds `~/Applications/Product
  Aviator.app` locally from `scripts/dock/app-icon.png`. Clicking it starts
  the server if needed and opens the UI in a Chrome app window, or the
  default browser. `--add-to-dock` pins it. Built on the machine, so nothing
  is downloaded or quarantined. Run it again after moving the folder.
- **Next / open.** None.
- **Read.** D-103; README "Step 2".

## Branding

- **Done.** The fork is named Flight Deck (D-35); the UI is Product Aviator,
  with its emblem and name at the top left of the sidebar, the same emblem
  as the Dock icon, and no logo on the new-session screen. The navy look
  comes from the design tokens.
- **Open.** Whether to rename the repository `dudgeon/omnigent-slim`.
  Folders, commands and code identifiers keep `omnigent-slim` until Geoff
  says otherwise (D-35).
- **Read.** D-35, D-102; README.

## Modes, projects and the intent graph

Starting a workflow such as intent shaping puts the session into that
workflow's mode, visibly; replies made in the mode are marked as its own; the
person can pause in plain language and come back later from the project; and
a project means something (a goal to ship) and knows its relatives.

- **Done.** Two design walkthroughs with drawings (2026-11-21). Geoff answered
  the first: D-89 to D-99. The headline is D-89: Aviator is a project
  director and modes run in threads. Nothing is built.
- **Exists already and would be reused.** The workflow card and `pa flow`
  progress files (D-16), direct actions for state changes (D-11), views in
  the chat (D-53), amber for needs-you (D-50), a project per flown demo
  (D-76). From upstream: the project board, child sessions and their tabs,
  agent-to-agent messages, side chats.
- **Next.** Two slices need no further decision and can be built now: run
  state with pause and resume in `pa flow`, and the "In flight" section on
  the project page. The rest waits on the second walkthrough. Build order is
  in modes-and-projects.md.
- **Open.** Four decisions (M-12 how the director shows a mode, M-13 where a
  thread opens, M-14 what a thread reports, M-8 a project's connections). The
  intent graph's detail is deliberately held (D-98). When answered, they take
  D-107 onward.
- **Read.** [modes-and-projects.md](modes-and-projects.md); D-89 to D-99;
  walkthroughs at https://claude.ai/artifact/HRgpJURjcqasGSCmd3894d and
  https://claude.ai/artifact/YQcb4HDRGMnn6YW82uFNZd.

---

## Also still open

- Ignore the production build for now; the local demo is the product (D-29).
- Progressive complexity (D-54).
- Whether to rename the repository (D-35).
