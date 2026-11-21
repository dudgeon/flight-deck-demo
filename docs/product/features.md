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

**Behaviour.** A scenario is a skill folder: instructions for the live agent,
the record shapes, view specs, invented fixture data and a markdown screenplay
(D-21). `pa preview` turns it into one HTML file that plays the screenplay
over the fixtures with the real views. `pa check` validates the package.

**Where.** `skills/prd-to-requirements/`, `skills/requirements-to-dependencies/`,
`skills/document-review/`; how to make one in `skills/scenario-builder/`; the
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

## The Hangar (builder mode): look-around version built

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
Nothing in the Hangar writes a file yet: drafts, trial and publish are slice 2.

**Where.** Design in `hangar.md`. Server: `omnigent/server/routes/slim_hangar.py`
(`GET /v1/slim/hangar`, plus rendered views, templates and scenario players).
Web: `web/src/hangar/`. Colors: the `build` and `hangar-*` tokens.
