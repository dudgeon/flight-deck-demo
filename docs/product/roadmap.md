# Where things stand

A snapshot of every workstream in Flight Deck (the fork) and Product Aviator
(its user interface): what is done, what is only partly done, what comes next,
what is still to be decided, and where to read more. Written for the
production team and for whoever picks the work up next.

Snapshot taken 2026-11-21, after pull requests 1 to 5 were merged. Decision
numbers (D-nn) refer to [decisions.md](decisions.md); feature intent is in
[features.md](features.md). When a workstream moves, update its section here
in the same pull request.

| Workstream | State |
|---|---|
| [Hangar (builder mode)](#hangar-builder-mode) | Designed and decided; slice 1 of 3 being built |
| [Design language and tokens](#design-language-and-tokens) | Built; three colors and two other questions waiting on Geoff |
| [Collaborative markdown editor](#collaborative-markdown-editor) | Built; two known gaps |
| [Participants and personas](#participants-and-personas) | Built, scripted and live; some gaps |
| [The four kinds of work](#the-four-kinds-of-work) | Built as previews; one run live so far |
| [Work-Mac setup from a ZIP](#work-mac-setup-from-a-zip) | In progress, not merged |
| [Canvas tools across several tabs](#canvas-tools-across-several-tabs) | Done |
| [Dock launcher](#dock-launcher) | Done |
| [Branding](#branding) | Done; one naming question open |

---

## Hangar (builder mode)

The Hangar is a second mode of the app where people, workflows, views,
scenarios and skills are defined, clearly distinct from "flying" (using the
app). Building is a guided workflow on a draft copy, with a strict publish
gate and a way back.

- **Done.** Design, clickable mockup and all seven decisions locked by Geoff
  (D-39 to D-47). The in-flight "Open in Hangar" link must be a tiny wrench
  icon, shown only on hover or focus, so it never shows up in demo recordings
  (D-41).
- **In progress.** Slice 1, the look-around Hangar: sidebar switch, the
  Hangar frame and its own teal color token, a read-only catalog endpoint,
  shelves and inspect pages, and the hover-only wrench links (D-45).
- **Next.**
  - Slice 2, the person builder: drafts, checks, trial, publish, dated
    history snapshots, used-by guard, and the optional `skills` line in
    participant files (D-46, D-47).
  - Slice 3, scenario and workflow builders, including the split of each
    scenario into its own folder (proposed `workspace/scenarios/<name>/`)
    and moving the seven existing demos there (D-42). This touches `pa check`,
    `pa preview` and the Session panel's workflow card.
  - New `pa` commands: `draft`, `publish`, `history`, `uses`. Builder skills:
    `build-person`, `build-workflow`, `build-scenario`, `build-skill`.
- **Open.** Nothing for slices 1 and 2. Left for later by design: sharing a
  workflow or scenario with another PM as one file, and a second person's
  approval before publishing (a production feature, D-44).
- **Read.** [hangar.md](hangar.md) (the spec); D-39 to D-47; mockup at
  https://claude.ai/artifact/9M4JGs5WuxigJz1jiJ9QVr.

## Design language and tokens

One set of design tokens for the app, the chat widgets and canvas views (the
view kit), the preview player and the artifact templates, so the product
looks like one product and a change is made once (D-37, D-38).

- **Done (PR 4).** `design/tokens.json` is the only source;
  `design/build_tokens.py` writes it into the app, `pa-kit.css`,
  `harness.html` and every template (`--check` finds anything out of date).
  The canvas injects the current tokens and light or dark mode into every
  artifact, old ones included. The `product-aviator-design` skill holds the
  rules and the vendored `frontend-design` skill gives general guidance
  (D-36). The collab editor's author colors and the app's status colors use
  the tokens.
- **Partial.** The colors shipped are the *recommended* answers, not yet
  confirmed. Upstream Omnigent's Settings → Appearance palettes still exist
  and override the default palette in one browser.
- **Next.** Apply Geoff's answers when they come in. That is a token edit, a
  rebuild of the generated files, and a web UI rebuild; no component changes.
- **Open.** In the "Design Decisions Two" walkthrough
  (https://claude.ai/artifact/QNjXRLU3GYPA26N2qsH42y), none answered yet:
  1. Where navy lives: navy sidebar (recommended, shipped), navy accents, or
     a navy header band.
  2. Color for the person's own marks: magenta (recommended, shipped) or rust.
  3. Color for "needs you": amber (recommended, shipped, red kept for
     failures) or red.
  4. Where agent-drawn views appear: questions and single cards in the chat
     with big views in the canvas (recommended), canvas only (today),
     anything in the chat with an expand button, or snapshots in the chat.
     Building the recommended option is moderate work in the chat renderer.
  5. The intent framework draft: keep it as drafted (recommended), fewer
     depths, or fewer areas.
- **Read.** D-35 to D-38; features.md "Design language and tokens";
  `skills/product-aviator-design/`; docs/customizing.md "One look
  everywhere"; first proposal at
  https://claude.ai/artifact/7YzXdsPux416J5qdkVuAea.

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
- **Read.** D-26; features.md "Collaborative markdown editor";
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
- **Done (this PR).** Participants reach the user through the Inbox (D-68 to
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
  production (D-24). The Hangar's person builder (slice 2) becomes the way
  to add someone.
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
  - Only delivery status has been run live with an agent (once, 21 Nov,
    about 90 seconds). It worked, and showed that a participant only knows
    what their file says, so a convincing live demo needs each scenario to
    give its cast that scenario's facts (the D-42 scenario folders). Until
    then Cards Platform's script carries a load-test answer. Decision
    review, problem discovery and intent shaping have not been run live.
  - The intent framework is a notional draft written by us. Geoff will
    correct it after seeing it run (walkthrough question 5 above).
- **Next.** Run the other three live in the app and fix what breaks,
  starting with decision review (it reuses the most). Then let Geoff react to intent
  shaping live, and swap in the real company framework when there is one.
- **Open.** The framework's shape (question 5 in the design walkthrough).
- **Read.** D-31, D-33, D-34; features.md, one section per kind of work;
  `skills/decision-review/`, `skills/problem-discovery/`,
  `skills/delivery-status/`, `skills/intent-shaping/`;
  `workspace/frameworks/`.

## Work-Mac setup from a ZIP

The work Mac cannot clone repositories outside the company, so the app
arrives as a ZIP of `main`, downloaded in a browser, and has to be set up by
someone who is not technical.

- **Done.** Everything is vendored (Python, wheels, tmux, the built web UI).
  `start.sh` detects a quarantined copy and says so. The README walks through
  a download with `curl`, which avoids quarantine.
- **In progress.** A one-step setup script for a browser-downloaded ZIP,
  approved by Geoff: plain-language steps, and failures that say what broke
  and what to send back. Not yet in a pull request.
- **Next.** Merge it to `main` (Geoff downloads the `main` ZIP), then Geoff
  tests it on the work Mac.
- **Open.** How the quarantine flag is cleared on a browser download. The
  README tells people to ask IT rather than bypass it; the setup script must
  not bypass it either.
- **Read.** README "Quick start"; D-02.

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
- **Read.** `docs/skill-writers/artifacts.md`;
  `omnigent/server/routes/sessions/routes_browser.py`.

## Dock launcher

- **Done.** `scripts/make_dock_app.sh` builds `~/Applications/Product
  Aviator.app` locally from `scripts/dock/app-icon.png`. Clicking it starts
  the server if needed and opens the UI in a Chrome app window, or the
  default browser. `--add-to-dock` pins it. Built on the machine, so nothing
  is downloaded or quarantined. Run it again after moving the folder.
- **Next / open.** None.
- **Read.** README "Step 2".

## Branding

- **Done.** The fork is named Flight Deck (D-35); the UI is Product Aviator,
  with its emblem and name at the top left of the sidebar, the same emblem
  as the Dock icon, and no logo on the new-session screen. The navy look
  comes from the design tokens.
- **Open.** Whether to rename the repository `dudgeon/omnigent-slim`.
  Folders, commands and code identifiers keep `omnigent-slim` until Geoff
  says otherwise (D-35).
- **Read.** D-35; README.

---

## Also still open

- Ignore the production build for now; the local demo is the product (D-29).
- Views inside the chat: see question 4 under design language.
