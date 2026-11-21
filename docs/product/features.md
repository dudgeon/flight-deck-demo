# Features: what each is for

For each feature: the intent, how it behaves, and where it lives. Decision
numbers refer to `decisions.md`.

## Views from data (the view kit)

**Intent.** Structured work is many similar items that a person reviews one by
one. The agent should spend its effort on the items, not on drawing them, and
every such view should look and behave the same (D-05, D-10).

**Behaviour.** Items are records in a JSON dataset in `data/`. A view is a
small JSON spec (table with hierarchy, board, card, summary or form). The `pa`
command draws a spec over a dataset as one self-contained HTML file, and
redraws every view of a dataset when its records change. Each record has its
own status, can be locked, and is marked stale when what it was derived from
changes (D-07). The same spec draws in the canvas and, as a widget, in a
preview's chat.

**Where.** `skills/view-kit/` (`scripts/pa.py`, `kit/pa-kit.js`,
`kit/pa-kit.css`, `references/spec.md`).

## Acting from a view

**Intent.** Reviewing twenty items should not mean pressing Send twenty times,
but a page must not be able to speak for the user (D-11, D-12).

**Behaviour.** A button that only changes state (approve, start, lock) is sent
to the agent at once, as a message the app itself writes. Anything with words
in it (an edit, a note, an answer) lands in the message box for the user to
send.

**Where.** `web/src/lib/artifactBridge.ts`, actions with `"direct": true` in
view specs.

## Scenarios and previews

**Intent.** A kind of work should be packaged once and shown two ways: live,
with an agent doing it, and as a click-through that needs no agent, for
showing people and for designing before building (D-06, D-08, D-09).

**Behaviour.** A workflow is a skill folder: instructions for the live agent,
the record shapes and view specs. A scenario is its own folder in
`workspace/scenarios/<id>/` with invented fixture data, the cast and a
markdown screenplay (D-21, D-42, D-67); many scenarios can run one workflow. `pa preview` turns it into one HTML file that plays the screenplay
over the fixtures with the real views. `pa check` validates the package.

**Where.** Workflows in `skills/<id>/` (for example `skills/document-review/`),
scenarios in `workspace/scenarios/<id>/`; how to make one in `skills/scenario-builder/`; the
screenplay format in `skills/view-kit/references/script.md`; the player in
`skills/view-kit/kit/harness.html`.

## The Session panel

**Intent.** One place that answers: what is this session working from, what
has it made, where is the work up to, and who else can be brought in (D-13 to
D-16).

**Behaviour.** Cards for cost, the running workflow (steps, current step, how
many items are done), Outputs (files in `artifacts/`), Context (files in
`context/`, shared by the project's sessions, tick to mention them) and People
and agents (the roster, narrowed to a running workflow's participants). It
docks beside the chat when there is room and the canvas is closed, and opens
from the header otherwise.

**Where.** `web/src/shell/SessionOverview.tsx`,
`web/src/shell/SessionOverviewFiles.tsx`; `pa flow` writes the workflow card's
data to `progress/`.

## Participants

**Intent.** Product work is done with other people and other systems. Their
voices should appear in the same conversation, clearly theirs, whether they
are a scripted demo character, an agent with a persona, or later a real
agent on another platform or a real person (D-17 to D-26).

**Behaviour.** The roster is one markdown file per participant in
`participants/`. The user asks Aviator to check in with someone, or addresses
them with `@`; Aviator may also call someone in itself, and says so. A
participant backed by a session runs as a background session with their brief
and can read the whole conversation; one backed by a script answers from
their file. What they say is shown as their own turn with a mark (square for
agents, round for people, dashed with a "stand-in" tag for a person played by
an agent) and a link to their session. What they add to a dataset carries
their id and shows in views.

**Where.** `workspace/participants/` (and its README), `skills/participants/`,
`web/src/lib/participantTurn.ts`, `web/src/components/chat/ParticipantTurn.tsx`,
`pa who`.

**Messages and invitations in the Inbox.** *Intent:* just as the user sends
messages to others, others send messages to the user, and demos pull the user
into other people's sessions, not only others into the user's (D-68 to D-70).
*Behaviour:* `pa tell <id> --session S --says TEXT` (or `--entry` for a
script entry, `--invite` for an invitation into the participant's own
session) puts a card in the Inbox. The card shows the participant's mark and
name, a stand-in or agent tag, their role and the session it is about, and
counts toward the sidebar badge. It offers Open conversation (Join conversation
for an invitation) and Done; there is no reply box, so the user always answers
in context. A People tab lists only these. Under the hood it is an ordinary
agent-posted Inbox item (`/v1/inbox/items`) with a `participant` media block,
posted through `POST /v1/slim/inbox/participant-messages`, so nothing new is
stored. *Where:* `omnigent/server/routes/slim_participant_inbox.py`,
`omnigent/server/inbox_media.py`, `participantMessageOf` in
`web/src/lib/proactiveInbox.ts`, the participant card in
`web/src/pages/InboxPage.tsx`, `skills/participants/SKILL.md` step 7.

## Decision review (a kind of work)

**What it is for.** A PM's work stalls on questions nobody has put to them
cleanly. Decision review gathers what is waiting on the person (from reviews,
dependency maps, documents, the conversation), turns each into a decision that
can be made in seconds, and records the outcome with who raised it and why.
It is deliberately modelled on how the product owner himself wants to be
asked: never blind, one at a time, with context, real options, consequences
and a recommendation (D-33).

**What it does.** Skill `skills/decision-review`. One dataset of `decision`
records (question, context, two to four options with consequences,
recommended option and reason, who raised it, impact, source) and `follow-up`
records under them. Three views: the queue in the canvas, a single-decision
card for the chat, and a summary. The person picks in the view; picks collect
as unsent edits and are sent together. Only the person sets a pick, except
through the explicit "Take the recommendations" button. After a decision the
agent tells whoever raised it and adds follow-ups. "I need more first" sends a
decision back with what is missing. The end product is a decision log in
markdown.

**New building block.** The `choices` section in view details (pick one of
several, recommended one marked). It is generic: any record with a list of
options can use it.

**Why it is the first of the four.** It reuses the most (one list, cards,
participants, the workflow card) and it proves the kit is not shaped around
requirements documents.

## Problem discovery (a kind of work)

**What it is for.** Before there is anything to specify, a PM has a pile of
raw material and a hunch. Problem discovery turns the pile into a short list
of problems in the words of the people who have them, and makes the strength
of each one visible, so the choice of what to solve is the PM's and is made
on evidence. It is built to resist the usual failure of synthesis by an
agent: confident themes with nothing underneath. Every problem carries its
quotes with sources, the evidence against it (looked for on purpose), a size
where data allows, and the most important thing the sources cannot tell us.

**What it does.** Skill `skills/problem-discovery`. A setup form (whose
problems count, how much evidence makes a candidate, what the PM already
believes, which is then tested rather than assumed). A `source` record per
file, shown as a list so the PM sees exactly what was read and that nothing
else was used. `problem` records on a board with lanes Candidate, Being
weighed, Needs evidence, Worth solving, Not now. Actions: Worth solving
(direct), Not now, Needs more evidence, Argue against it, Add sources, Write
the problem brief. Participants are used the way a PM would use colleagues: a
researcher to catch what was missed, a data owner to size a problem. The
agent never marks a problem worth solving itself. The end product is a
problem brief with no solutions in it.

**Roster addition.** `support-insights`, a script-backed agent that answers
questions about support contact volumes.

**Deliberately a different subject** (new business accounts, not the
allowances feature) so the demos do not all lean on one invented product.

## Delivery status update (a kind of work)

**What it is for.** Status reporting is where a PM's time goes and where
plans quietly rot: last week's date gets repeated as this week's fact. This
kind of work makes the agent do what a careful PM does: ask each owner this
week, check what can be checked, carry a slip through to the final date, look
for ways to get the time back, and write an update whose first line is the
truth. The four things the product owner named (D-31) map to its steps:
executing the plan (checking milestones), monitoring dependencies, exploring
alternatives, and updated projections.

**What it does.** Skill `skills/delivery-status`. `milestone` records (plan
date, date now expected, slip, confidence, what changed, and always how it is
known), `dependency` records under them, and `alternative` records under a
milestone that has moved (effect on the date, cost, who must agree). One plan
view in the canvas, a single-milestone card for the chat with the ways to
recover, and a summary. Owners on the roster are called without asking
first, because that is what a status check is. "Accept the new date" is
always one of the alternatives, with its real cost, so doing nothing is a
visible choice. The agent never chooses an alternative, and a recovered date
stays "at risk" until whoever must agree has agreed. The end product is a
status update in markdown, shaped for the audience.

**Kit additions that came from it.** Dataset facts can change after creation
(`pa set --meta`, and `[fact ...]` in preview scripts), so a header can show
a projected date that moves. The `who` mark understands `you`. Short values
such as dates no longer wrap in narrow columns. A summary list about one
field skips records that lack it.

**Continuity between demos.** The invented plan delivers the top problem from
the problem-discovery demo (held payments with no release date), so the two
can be shown as one story, but neither depends on the other.

**Live run, 21 Nov.** Delivery status was run end to end with a real agent
from a plan typed into the chat: it built the plan view, called the owners,
and wrote the update in about a minute and a half (about a dollar). The
owners' stand-ins had nothing to say about status, and the agent reported
exactly that ("no owner has confirmed it") instead of inventing dates, which
is the behaviour the skill asks for. It also showed a gap in the demo, not
the product: participants only know what their file says, so a convincing
live demo needs each scenario to give its cast the facts of that scenario.
That is what the scenario folder split (D-42) is for. Until then Cards
Platform's script carries a load-test answer.

## Intent shaping (a kind of work) and frameworks

**What it is for.** Most ideas arrive as a solution in one sentence. Intent
shaping walks an idea toward something a team could commit to, without the
agent writing the PM's intent for them. The agent's job is to hold the idea
against a framework honestly, ask for the one thing it is weakest on, and
refuse to call anything deeper than what exists to support it. The failure it
is built to prevent is a fluent, complete-looking brief with nothing under
it.

**Frameworks are files (D-34).** `workspace/frameworks/intent.md` is a
notional framework: five depths (Spark, Framed, Shaped, Tested, Committable)
and seven breadth areas (Customer, Problem, Outcome, Scope, Risks,
Dependencies, Cost), each with one line per depth saying what must exist, and
a "required from" depth. An idea is as deep as its shallowest required area.
The file is markdown and meant to be replaced by a company's real framework
with the same headings. The skill reads it; no code knows its contents.

**What it does.** Skill `skills/intent-shaping`. One `area` record per
breadth area (depth, what we can say now, what the next level asks for, the
one question that would get there, what it rests on) and `gap` records under
them. An intent map in the canvas, a card for the shallowest area in the
chat, a target form, a summary. The loop is one area at a time, shallowest
first. Where an area is about what others know (risks, dependencies, cost),
the agent calls whoever would know instead of asking the PM to guess. The PM
can mark an area not needed, with a reason, and can ask for a strict re-check
of any depth. The end product is an intent brief that states its depth at the
top.

**The four kinds of work as one story.** The invented material chains:
discovery finds the held-payment problem, intent shaping shapes the idea of
showing a release date, decision review settles open questions, delivery
status tracks it. Each demo also stands alone.

## Collaborative markdown editor

**Intent.** A person and agents should be able to work on the same document
the way people do in a shared doc: see what the agent changed, propose
changes instead of making them, discuss in comments, and know who said what
(D-26). Participants only ever suggest; the main agent edits directly when
asked to make a change and suggests when asked to propose one.

**Behaviour.** A review layer on upstream's TipTap markdown editor. A
Suggesting mode turns typing and deleting into suggestions, stored in the
`.md` itself as CriticMarkup with the author and time, so they survive any
tool that reads the file. Comment threads, attributed to the person, Aviator
or a participant, live in a sidecar `<doc>.md.review.json`. An `@name` in a
comment asks Aviator to get that participant's reply into the thread. Edits
that land on disk while the file is open are tinted until marked seen. The
Review panel lists suggestions and threads to accept, reject or answer.
Agents read and write the same files with `pa review`. Known gaps: no
simultaneous typing (the editor reloads from disk and asks "Keep mine / Load
latest" on a clash), and a comment loses its anchor when its text is deleted.

**Where.** `web/src/shell/review/`, the hook in upstream's
`MarkdownRichTextViewer.tsx`; `skills/view-kit/scripts/docreview.py`
(`pa review`); `skills/document-collaboration/`.

## The Library and canned sessions

**Intent.** A demo, or a PM new to the tool, should start from a good prompt
rather than a blank box, and those prompts should be plain files anyone can
edit.

**Behaviour.** The Library page lists artifact templates and canned
sessions (prompts with fill-in fields). "Open in composer" opens a new
session in the Workspace project with the prompt filled in; nothing is sent
until the person presses Send. Each kind of work has a canned session that
starts it.

**Where.** `workspace/templates/`, `web/src/pages/LibraryPage.tsx`,
`omnigent/server/routes/slim_library.py`. How to add one:
`docs/customizing.md`.

## Canvas tools

**Intent.** Claude should be able to check and operate what it put on the
canvas (read the page, click, type) without an outside browser, which the
work Mac does not allow, and without widening what is pre-approved.

**Behaviour.** The `canvas_*` tools act inside the sandboxed artifact frame
in the person's own browser tab. When the session is open in several tabs,
one tab is the active canvas; the others dim and offer "Use this tab". The
tabs are deliberately not mirrored, and a call that moves to another tab
tells Claude to read the page again.

**Where.** `omnigent/runner/tool_dispatch.py`,
`omnigent/server/routes/sessions/routes_browser.py`,
`web/src/lib/canvasFrameRuntime.ts`; for skill writers,
`docs/skill-writers/artifacts.md`.

## Setup from a ZIP

**Intent.** Someone who is not technical gets the app running on a locked-down
work Mac from a browser download, with one command, and when it can't finish
they get a plain explanation and a file to send back (D-100, D-107).

**Behaviour.** `sh setup.sh` in the unzipped folder checks the Mac (macOS 13+,
Apple silicon, not under Rosetta, disk space), that the folder is complete,
and that Claude Code is installed (it finds it in the usual places when
Terminal's PATH misses it). It clears the browser's quarantine flag from its
own folder after asking, restores execute bits an unzip dropped, checks the
bundled tmux runs, then runs `start.sh` and confirms the app answers on port
6767 (or says which port it took). It never downloads or installs anything.
Every run writes `setup-report.txt` in the folder and
`flight-deck-setup-report.txt` on the Desktop; a failure names the problem,
the fix, and that file. `tests/setup_sim/simulate_zip_setup.sh` rehearses the
whole flow in a Linux container.

**Where.** `setup.sh`, `start.sh`, `tests/setup_sim/`, README "Quick start".

## Dock launcher

**Intent.** On the work Mac, starting the demo should be one click, not a
Terminal command.

**Behaviour.** `scripts/make_dock_app.sh` builds a small Product Aviator app
on the machine (so nothing is downloaded or quarantined). It starts the
server if needed and opens the UI in a Chrome app window or the default
browser; `--add-to-dock` pins it.

**Where.** `scripts/make_dock_app.sh`, `scripts/dock/`.

## Design language and tokens

**What it is for.** Product Aviator should look like one product, and a
decision about its look should be made once. Before this, the app, the canvas
views, the artifact templates and the scenario previews each had their own
colors, so every change meant editing many files by hand, and artifacts made
earlier kept the old look forever.

**What it does.** Every color, font and corner comes from
`design/tokens.json`. `design/build_tokens.py` writes those values into the
app (the default palette and the navy sidebar read them), the view kit that
draws chat widgets and canvas views, the preview player, and each artifact
template. When the canvas shows any HTML artifact, it adds the current tokens
and the app's light or dark mode, so artifacts made before a change follow it.
The `product-aviator-design` skill tells Claude what each token means and to
use nothing else; the view kit, scenario builder and artifact skills point to
it. Statuses follow one meaning everywhere: green done, blue ready for review,
amber needs you, red failed, indigo the agent working, and one color reserved
for what the person did.

**For the production team.** The tokens file is plain JSON with a light and a
dark value per token, so it can feed any styling system. The contract that
matters is the set of token names and what each means (in the skill), not the
values. When a corporate palette replaces ours, swap the values but keep the
meanings, in particular one hue reserved for the person's own marks and red
only for failures (decisions D-48 to D-50).

## The Hangar (builder mode)

**Intent.** Defining people, workflows, views and scenarios should happen in
the app, by product managers, without being able to break what others use.
The app therefore has two modes that cannot be mistaken for each other:
flying (using it) and the Hangar (defining what others fly). Building is
itself a guided workflow, drafts are the only thing ever edited, and Publish
is a strict gate with a way back (D-39 to D-47, D-51, D-52).

**What exists now (slice 1, read-only).** A dashed "Hangar" switch at the foot
of the flying sidebar opens `/hangar`: a teal band, a paper sidebar with a
dashed edge and a drafting grid. Shelves for people and agents, workflows,
views, scenarios, skills, starters and frameworks show each thing the way a
user meets it, with a health chip from `pa check`. Inspect pages show how it
looks when flying (a real participant turn, views and templates drawn over
sample data, the scenario player) beside what it is made of, with every "uses"
and "used in" as a link. A hover-only wrench on participant turns, the
workflow card and Library cards jumps to the same thing in the Hangar (D-51).

**Person builder (slice 2).** People and agents are the first thing you can
build. "New person or agent", Edit, Duplicate and Remove each start a draft
(a copy under `workspace/.hangar/`, D-56). Publish stays disabled while a
check fails, asks for one line on what changed, and keeps the replaced
version. Removing someone is blocked while any workflow, scenario or starter
still uses them. History lists every kept version with its note and a diff,
and Restore goes back through the same gate (D-57). The same moves exist for
agents and scripts as `pa draft`, `pa publish`, `pa history` and `pa uses`.

**Editing in place (D-63 to D-66).** Edit no longer leaves the Hangar. The
person's page turns into a form: who they are, the brief (the text the
session playing them is told), the skills they bring, and tick boxes for the
workflows, scenarios and starters they can be called in. Every change saves
to the draft as you type; beside the form are the turn as people will see it,
the checks, a diff and the cast changes. A fixed bar at the bottom holds the
note, Publish and Discard. "Ask Aviator" opens a pop-over (pin it to make it a
column) with a real Aviator session on this draft, and a "Try them" tab that
asks the draft a real question. *Why:* Geoff found leaving for a new flying
session to change a role or a brief clunky and opaque, and could not see how
to give someone skills or put them in a workflow. Direct edits handle the
simple changes; Aviator is there for rewrites, without leaving the page.

**Pictures and the repo (D-74, D-75).** The person editor has a Picture field:
choose a file and it is copied into the draft, then into
`workspace/participants/avatars/` on Publish, and shown instead of the
initials in the Hangar, on participant turns and in the Session panel. The
Overview lists published files that are not committed yet, because everything
built in the Hangar is meant to travel with the repo. *Why:* Geoff wants
recognisable faces for the cast, and wants the cast, workflows and scenarios
to move with the repo to the work machine.

**Scenario and workflow builders (slice 3, D-71 to D-73).** Every scenario
and workflow page has Edit, Duplicate and Remove (for a shipped workflow, "Edit
a copy"), and the Scenarios shelf has "New scenario". The draft opens as an
editor: title, summary, the workflow it runs and the opening line (scenarios)
or the steps (workflows), tick boxes for the cast or for who may be called, the
script or the instructions (`SKILL.md`) as a big text box, and every other text
file in the folder, with a box to add one such as `context/brief.md` or
`cast/mara-okafor.md`. Beside it are the checks and the files that change, each
with a diff; a scenario draft also plays below, as a demo. Publish needs every
check to pass and the script to play through, keeps the version it replaces,
and History restores one. A shipped workflow publishes as a workspace copy
that takes over its id. The same moves are `pa draft|publish|history
scenario|workflow`, which the scenario-builder skill now uses. *Why:* so a PM
can make a new demo, or adjust a kind of work for their team, without editing
files or breaking what others fly, in the same way they edit a person.

**Widgets and views (D-114).** A workflow's page groups what people see into
"Widgets · in the chat" (forms, single-record cards, summaries the agent puts
in the conversation) and "Views · in the canvas", each drawn over the
scenario's sample data. "Edit widgets and views" on the workflow, or "Edit" on
one view's page, opens the workflow draft at that widget: its small line,
heading, form questions, button labels and what each button says in the chat
are fields, the whole spec is a JSON box, and the drawing beside it follows
every save. "Add a widget or view" starts from a blank form, a blank summary or
a copy, and writes the `SKILL.md` line that tells the agent when and how to
show it. Publishing goes through the usual checks and lands in the workflow's
workspace copy, so it travels with the repo. *Why:* the widgets are most of
what a person sees of a workflow, and Geoff wants to shape them where he
shapes everything else, without hand-editing files.

**Where.** Design in `hangar.md`. Server: `omnigent/server/routes/slim_hangar.py`
(`GET /v1/slim/hangar`, rendered views, templates and scenario players, and the
draft, publish, history and restore routes for people, scenarios and
workflows, and `GET /v1/slim/hangar/drafts/workflow/<id>/views/<view>` for a
draft's widget). Widget editor: `web/src/hangar/WidgetsCard.tsx`. Folder drafts: the "workflows and scenarios" builder section of
`skills/view-kit/scripts/pa.py`. Web: `FolderEditor.tsx` beside the person
editor. Builder skill: `skills/build-person/`.
Web: `web/src/hangar/`. Colors: the `build` and `hangar-*` tokens.

## Views in the chat (asks in chat, work in canvas)

**What it is for.** Before this, every view opened in the canvas, so a quick
question took over the canvas and hid the document being read, and scrolling
back did not show what had been answered. Now anything the person answers or
glances at (a form, a single card, a summary) is drawn in the conversation,
and anything they work in (a catalog, a board, a document) stays in the
canvas (D-53).

**What it does.** The agent renders the view with `pa render --host chat`,
which prints a fenced block (language `view`, with `file:` and `title:`). The
agent puts that block in its reply. The app draws the file there in a
sandboxed frame with the same bridge a canvas view has, sized to its content,
and redraws it when the file changes. Buttons in it put text in the message
box, or act directly where the action is a plain state change, exactly as in
the canvas. When the person has replied, the view folds to one line marked
"Answered" with Show and "Open in canvas"; shown again it is read-only. Only
`.html` files inside the workspace are accepted.

**The attention cue (D-55).** While a view in the chat is live and the agent
is waiting, the canvas turns grey and dims, and comes back as soon as the
pointer or keyboard is in it. The intent is that it is always obvious which
side of the screen wants the person. It is a first form to react to.

**Where the code is.** `web/src/lib/chatView.ts`,
`web/src/components/chat/ChatViewBlock.tsx`, the hook in `ChatCodeBlockPre`
(`message.tsx`), one rule in `index.css`; `pa render --host chat` in
`skills/view-kit/scripts/pa.py`; the rule for agents in
`skills/view-kit/SKILL.md` and `workspace/CLAUDE.md`.

**Tested live, 21 Nov.** Intent shaping with a real agent: the target form
appeared in the chat, pressing its button filled the message box, sending
folded it to "Answered", the intent map opened in the canvas, and the next
question appeared as a card in the chat with the canvas greyed.

**Not done.** Participants cannot yet put a view inside their own turn. The
preview player has its own older way of showing chat widgets and does not
fold them.
