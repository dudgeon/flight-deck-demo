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
