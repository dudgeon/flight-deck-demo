# Decision index

Every decision number, what it decided in one line, who decided, where it
stands now, and why. The full wording is in [decisions.md](decisions.md),
which is never edited after the fact; this index is the part that changes.
Update the status here whenever a decision is built, refined or replaced.

Audit of 2026-11-21 (evening): D-01 to D-75, D-89 to D-107 and D-111 to
D-114 are on `main`. D-60, D-61 and D-62 were never assigned (parallel threads
claimed blocks and skipped them); they stay unused so no reference can point
at the wrong thing. Claimed by open pull requests: D-76 to D-81 (PR 17),
D-82 to D-88 (PR 19), and D-108 to D-110 (PR 25, avatars, held). D-100 to D-106 record decisions Geoff made earlier that
were never logged (see "Backfilled" in decisions.md). D-116 onward is next;
check open pull requests first, as `CLAUDE.md` says. No number is used twice.

**Status words.** *Built*: in the code on `main`. *Active*: a rule or
direction in force, nothing to build. *Refined by* / *replaced by*: a later
entry changes it; read both. *Pending*: claimed in an open pull request, not
on `main` yet. *Open*: decided in direction, with a named question left.

**Why.** Taken from the entry where it has one. Where the entry gives no
reason, the reason is reconstructed from the walkthroughs, pull requests and
feature notes of the time and marked *(reconstructed)*.

## Foundations

| D | Decision | Who | Status | Why |
|---|---|---|---|---|
| D-01 | A cut-down fork of Omnigent, not a new app | Geoff | Active | A work team will productionize Omnigent; staying close keeps the demo transferable. |
| D-02 | Claude Code as a terminal, no API, offline, no permission bypass, everything vendored | Geoff | Built (`_offline_guard.py`, `slim_policy.py`, `vendor/`) | The work Mac's constraints. |
| D-03 | Defaults: Auto permissions, Opus 5.5, medium effort | Geoff | Built | *(reconstructed)* Auto keeps demos flowing without prompts while staying inside Claude Code's own safety checks; Bypass and Don't ask stay removed (D-02). |
| D-04 | A "product partner" for PMs: unstructured work plus templated flows | Geoff | Active | *(reconstructed)* His vision of PM work: context files and generated artifacts alternating with structured, repeatable flows. |
| D-107 | Setup clears the download flag on its own folder after asking; curl stays as the other way | Geoff | Built (`setup.sh`) | A browser ZIP is the main way in; this is what "Open Anyway" does, and IT for every install would stall it. |
| D-111 | App lives in `~/flight-deck`; updates from a newer ZIP never overwrite the person's files or edits | Geoff asked, Claude chose | Built (`setup.sh`, `scripts/install_sync.py`) | A re-download must keep his files, and Terminal navigation is hard: one fixed folder plus a manifest of what was shipped. |

## Structured work

| D | Decision | Who | Status | Why |
|---|---|---|---|---|
| D-05 | One template system for chat widgets and canvas views; plain HTML keeps working | Geoff | Built (view kit); refined by D-53 | *(reconstructed)* One view runs in chat, canvas and a standalone demo, so it is built once. |
| D-06 | Do not overfit to the PRD example | Geoff | Active | *(reconstructed)* The system is for iterating on many kinds of work; the four kinds of work (D-31) test that. |
| D-07 | Stages extend one dataset; records progress and lock at their own pace | Geoff | Built (`pa` datasets) | *(reconstructed)* Twenty requirements move at twenty speeds; handing files between stages loses per-item state. |
| D-08 | Demos first, real use later; every workflow has an agent-free preview | Geoff | Built (`pa preview`); extended by D-77 | *(reconstructed)* The near-term use is showing and designing; the same files later run live. |
| D-09 | Skills carry the know-how | Geoff | Active | *(reconstructed)* Skills are the only thing every session, including on the work Mac, reliably reads. |
| D-10 | Views are data plus a small JSON spec drawn by one kit | Claude | Built (`skills/view-kit/`) | Hand-written HTML per view is slow and inconsistent. |
| D-11 | Canvas buttons may act without Send, for state changes only | Geoff | Built | Pressing Send after every approval is friction; arbitrary unreviewed text is a risk. |
| D-12 | The app writes a direct action's message; only ids, state fields, status words | Claude | Built (`artifactBridge.ts`) | So a view cannot use the channel to say anything else. |

## The Session panel

| D | Decision | Who | Status | Why |
|---|---|---|---|---|
| D-13 | Outputs are `artifacts/`, context is `context/`, both in a Session panel | Claude | Built | *(reconstructed)* One place answers what the session works from and what it made. |
| D-14 | Layout direction A: panel docks beside chat, popover when the canvas is open | Geoff | Built | The other directions felt cluttered. |
| D-15 | Context is per project, inherited by its sessions | Geoff | Built for the Workspace project | *(reconstructed)* A PM's documents belong to the work, not to one conversation. Extended in the modes design (M-8, open). |
| D-16 | A workflow card: steps, current step, progress | Geoff | Built (`pa flow`, `progress/`) | *(reconstructed)* He asked for it on the designs, in the manner of Cowork. |

## Participants and the Inbox

| D | Decision | Who | Status | Why |
|---|---|---|---|---|
| D-17 | Other agents and people take part, attributed | Geoff | Built | *(reconstructed)* Product work is done with others; their voices must be clearly theirs. |
| D-18 | Both scripted and live, scripted first, same files | Geoff | Built | *(reconstructed)* Scripted previews are reliable for demos; live follows without new files. |
| D-19 | A live participant is a background session, not a sub-agent | Geoff | Built | A sub-agent's context cannot be inspected; a session can be opened and read. |
| D-20 | One global roster; scenarios say who is eligible | Geoff | Built (`workspace/participants/`, `pa who`) | *(reconstructed)* The agent needs one catalog to call from. |
| D-21 | Scripts are editable markdown, not JSON | Geoff | Built (`script.md`) | *(reconstructed)* Other PMs edit them (D-30). |
| D-22 | A person played by an agent is always labelled a stand-in | Claude | Built | *(reconstructed)* Nobody may mistake an agent for a real colleague. |
| D-23 | Aviator may call a participant on its own, and says so | Geoff | Built | *(reconstructed)* That is what a colleague would do; saying so keeps it visible. |
| D-24 | A called participant sees the whole conversation | Geoff | Built; **demo only, revisit for production** | For the demos. |
| D-25 | `@name` addresses a participant; no `@` or `@aviator` goes to Aviator | Geoff | Built | *(reconstructed)* The familiar chat convention; Aviator still sees everything. |
| D-26 | Participants only ever suggest document changes | Geoff | Built (collab editor); see D-104 for the main agent | *(reconstructed)* The person stays the author; others' changes are proposals. |
| D-68 | Participant messages reach the Inbox only when meant for the user | Geoff | Built | Others send messages to us, and demos pull the user into others' sessions. |
| D-69 | Inbox messages: scripted first (`pa tell`), live the same way | Geoff | Built | *(reconstructed)* Same pattern as D-18. |
| D-70 | No inline reply in the Inbox; Open or Join, and Done | Geoff | Built | *(reconstructed)* The user always replies in context, where the conversation is. |

## How we work

| D | Decision | Who | Status | Why |
|---|---|---|---|---|
| D-27 | The agent's unasked choices up to 21 Nov stand | Geoff | Active | *(reconstructed)* He reviewed them as a group in the walkthrough. |
| D-28 | Geoff reviews designs and test summaries, never code; an agent merges PRs | Geoff | Active (see CLAUDE.md) | *(reconstructed)* His time goes to product judgment, not code review. |
| D-29 | Ignore the production build; document intent for the production team | Geoff | Active | *(reconstructed)* The local demo is the product for now; the production team rebuilds from the notes. |
| D-30 | Other PMs write scenarios, inside Aviator | Geoff | Built (the Hangar, D-39 on) | *(reconstructed)* Scenario authoring must not need the repo. |
| D-31 | Next kinds of work: problem discovery, intent shaping, decision review, delivery status | Geoff | Built as previews; delivery status and intent shaping run live | *(reconstructed)* They cover the PM life cycle beyond requirements. |
| D-32 | More than one question: decision cards, one at a time | Geoff | Active; extended by D-105 | *(reconstructed)* A list in prose is hard to answer from a phone. |
| D-33 | Never ask Geoff to decide blind | Geoff | Active; built into decision review | *(reconstructed)* A decision without context, options and visuals is not a decision he can make. |
| D-115 | Decision artifacts are archived in the repo as offline HTML, kept by the `docs-refresh` skill | Geoff asked, Claude chose | Built (`docs/decision-artifacts/`) | A record anyone can open without his claude.ai account, and examples of how to ask. |
| D-34 | Intent framework is notional and swappable (`workspace/frameworks/`) | Geoff | Built | *(reconstructed)* The real company framework can replace it without touching the skill. |

## Name and design language

| D | Decision | Who | Status | Why |
|---|---|---|---|---|
| D-35 | The fork is Flight Deck; the UI is Product Aviator; identifiers keep `omnigent-slim` | Geoff | Active; repository renamed by D-114 | He liked the name. |
| D-114 | Repository renamed `dudgeon/flight-deck-demo`; local folders, data folder and identifiers keep their names | Geoff | Built (README, `setup.sh` accepts both download names) | Repo should carry the product name; renaming checkouts breaks their venv, Dock launcher and session history. |
| D-36 | Vendor Anthropic's `frontend-design` skill | Geoff | Built (`skills/frontend-design/`) | He asked for it; the work Mac cannot download skills. |
| D-37 | One design language from shared tokens | Geoff | Built | Four color systems looked like four products. |
| D-38 | How tokens are built and injected | Claude | Built (`design/`) | The same whichever colors are picked. |
| D-48 | Navy lives in the frame (sidebar) and the one primary action | Geoff | Built | Recognizable frame; color in content must mean something. |
| D-49 | One hue reserved for the person's own marks (magenta today) | Geoff | Built | The person must spot their own hand; keep the rule if the palette changes. |
| D-50 | Amber for needs-you, red only for failures | Geoff | Built | Red everywhere would hide real failures. |
| D-102 | Sidebar brand: emblem plus the name as text; no logo on the new-session screen | Geoff | Built | See decisions.md. |

## The Hangar (builder mode)

| D | Decision | Who | Status | Why |
|---|---|---|---|---|
| D-39 | Two modes: flying and the Hangar | Geoff | Built | Names used in the UI. |
| D-40 | In the Hangar the whole frame changes | Geoff | Built | Obvious at a glance and in a screenshot. |
| D-41 | Way in: sidebar-foot switch, plus subtle in-flight links | Geoff | Built; refined by D-51 | Must not distract in demo recordings. |
| D-42 | Scenarios are their own folders, separate from workflows | Geoff | Built by D-67; extended by D-79 | Editing a story must not break the kind of work. |
| D-43 | Building is guided by Aviator, with a form that is the file | Geoff | Built as refined by D-63 and D-71 | Constraints come before the mistake. |
| D-44 | Strict publish; built-ins only duplicated | Geoff | Built | Nobody else to approve on one laptop. |
| D-45 | Build order: look-around, person builder, scenario and workflow builders | Geoff | Done (all three slices) | *(reconstructed)* Smallest useful step first. |
| D-46 | Work on drafts; every publish keeps a dated snapshot | Claude | Built (`.hangar/`, D-56) | Works from a ZIP without git. |
| D-47 | Optional `skills` line in a participant file | Claude | Built; extended by D-66 | *(reconstructed)* So the Hangar can show and narrow a person's skills. |
| D-51 | The in-flight link is a hover-only wrench, no words | Geoff | Built (`HangarWrench.tsx`) | Never visible in a recording. |
| D-52 | The Hangar is its own route, reading files on each request | Claude | Built (`slim_hangar.py`) | Separable from upstream's shell; no new store. |
| D-56 | Drafts and history live in `workspace/.hangar/`, gitignored | Claude | Built | Same checks run on a draft; nothing half-made goes live. |
| D-57 | Restore is a publish, through the same gate | Claude | Built | A way back must not become a way around the gate. |
| D-58 | "Try them" opens a builder session | Claude | **Replaced by D-64** | It used the real participant turn. |
| D-59 | Builder sessions live in a "Hangar" project | Claude | Built | Keeps building out of the flying list. |
| D-60 to D-62 | Never assigned | | Unused | Numbers skipped by parallel threads. |
| D-63 | A person's Hangar page is their editor, autosaving to a draft | Geoff asked, Claude chose; confirmed by Geoff | Built | Leaving for a flying session was "clunky, opaque, mysterious". |
| D-64 | Aviator in a pinnable pop-over on the Hangar page | Claude; confirmed by Geoff | Built; replaces D-58 | Stay in the Hangar. |
| D-65 | Casting is set on the person's page | Claude; confirmed by Geoff | Built | Casting was the hidden step. |
| D-66 | A person brings skills, told to their session | Claude; confirmed by Geoff | Built | He could not see how to give a character skills. |
| D-67 | D-42 built: `workflow.json` and `workspace/scenarios/<id>/` | Claude | Built | Several scenarios per workflow. |
| D-71 | Scenarios and workflows edit like people, with folder drafts | Claude | Built | One way to build anything. |
| D-72 | Shipped workflows are never changed in place; "Edit a copy" | Claude | Built | Shipped workflows stay a safe floor. |
| D-73 | A scenario draft plays on its page; `opening` line | Claude | Built | Seeing the demo is the real check. |
| D-74 | Pictures for people and agents, committed with the repo | Geoff | Built | He asked for avatars chosen from a file. |
| D-75 | Configuration travels with the repo; a test guards `.gitignore` | Geoff | Built | Personas, skills, workflows and scenarios go to the work Mac. |
| D-112 | A workflow's widgets and views are shown, edited and added in the Hangar | Geoff asked, Claude chose | Done (PR 27) | He asked that widgets tied to a workflow be visible and editable there. |
| D-113 | "Send to repo" on git copies: published config to a new branch, pushed, PR opened | Geoff | Done (PR 29) | Hangar edits only shipped once someone committed them by hand. |

## Views in the chat

| D | Decision | Who | Status | Why |
|---|---|---|---|---|
| D-53 | Asks in chat, work in canvas | Geoff | Built | Answer without losing the document; the transcript shows what was decided. |
| D-54 | Intent framework stays as drafted; progressive complexity is next | Geoff | Active; **progressive complexity open** | It pressure-tested the system. |
| D-55 | The agent directs attention: canvas greys while chat waits | Geoff | Built as an exploration | *(reconstructed)* Always obvious which side wants the person. |

## Demos and the Library (pending)

| D | Decision | Who | Status |
|---|---|---|---|
| D-76 | Scenario you build, demo you fly; one "◆ Demo" project per demo | Geoff | Pending, PR 17 |
| D-77 | Canned or live is set per turn (`[live]`); `pa demo next` | Geoff | Pending, PR 17 |
| D-78 | One fly route and `FlyButton`, from the Hangar and the Library | Geoff | Pending, PR 17 |
| D-79 | Scenario folder adds `context/`, `cast/`, `opening` | Geoff | Pending, PR 17 |
| D-80 | Workflow skills never copy demo material themselves | Geoff | Pending, PR 17 |
| D-81 | Flying again: Reset to the start or Keep going | Geoff | Pending, PR 17 |
| D-82 | Keep the Library; every card generated from metadata | Geoff | Pending, PR 19 |
| D-83 | Top half: four to six featured skills (`library` block) | Geoff | Pending, PR 19 |
| D-84 | Skill card: unnumbered steps, a short form, Start | Geoff | Pending, PR 19 |
| D-85 | Demo card: Fly and a Live turns switch | Geoff | Pending, PR 19 |
| D-86 | One project per demo; an In flight strip | Geoff | Pending, PR 19 |
| D-87 | Demo card text comes from `scenario.json` | Not recorded in the entry | Pending, PR 19 |
| D-88 | Artifact templates leave the Library | Geoff | Pending, PR 19 |

When pull requests 17 and 19 merge, change these rows to their real status
and add a reason to each.

## Modes, runs and projects

Geoff's answers to the first modes walkthrough (pull request 21). These are
decided but nothing is built yet.

| D | Decision | Who | Status |
|---|---|---|---|
| D-89 | Aviator is a project director; modes run in threads with agent-to-agent messages | Geoff | Decided, not built |
| D-90 | A mode shows as a strip on the message box | Geoff | Decided, not built |
| D-91 | A mode's replies are marked by a rail with start, pause and resume markers | Geoff | Decided, not built |
| D-92 | Side questions are answered outside the rail; the mode stays on | Geoff | Decided, not built |
| D-93 | Leaving: pause, finish and stop are distinct; a where-we-left-off note; only stop confirms | Geoff | Partly built: pause, resume and stop with the note; the Pause button waits on D-90 |
| D-94 | One mode has the floor at a time, with a way back | Geoff | Decided, not built |
| D-95 | Any record can have its own thread | Geoff | Decided, not built |
| D-96 | In-flight work shows in an "In flight" section on the project page | Geoff | Built |
| D-97 | A project is one in-market goal inside a lasting area | Geoff | Decided, not built |
| D-98 | The intent graph's detail is held until it blocks something | Geoff | Decided, not built |
| D-99 | The smaller calls stand (every workflow makes a mode, no mode color, and so on) | Claude, accepted by Geoff | Decided, not built |
| D-116 | The director shows a mode through a direct line to its thread; Aviator is not in the path | Geoff | Decided, not built |
| D-117 | Stepping into a thread puts it in place of the chat, the director folded to a bar, the canvas kept | Geoff | Decided, not built |
| D-118 | A thread reports milestones, progress, blockers and state, at its own discretion, never everything | Geoff | Decided, not built |


## Backfilled (decided earlier, logged on 21 Nov)

| D | Decision | Who | Status |
|---|---|---|---|
| D-100 | The work Mac gets the repo as a ZIP and runs one setup script that fails helpfully | Geoff | Built (`setup.sh`); refined by D-107 |
| D-101 | One active canvas tab per session, not mirrored | Geoff | Built |
| D-102 | Sidebar brand: emblem plus name as text | Geoff | Built |
| D-103 | Dock icon A, pinned to the Dock | Geoff | Built |
| D-104 | The main agent edits directly for "make a change", suggests for "propose changes" | Geoff | Built |
| D-105 | Every question card includes "Something else" | Geoff | Active |
| D-106 | Views redraw by rewriting the file; reviewed and locked are the person's | Geoff | Built |

## Open questions not yet numbered

- One modes question is still unanswered (M-8 in
  [modes-and-projects.md](modes-and-projects.md)): how a project's
  connections show. It takes the next free number when Geoff answers.
- Progressive complexity (D-54).
- D-24 for production.
