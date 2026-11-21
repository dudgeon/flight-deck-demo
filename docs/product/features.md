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
