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
Since D-42 the story lives in `workspace/scenarios/<id>/`, with `context/`
documents and `cast/` notes beside the fixtures (D-79); flying it is below.

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

## Flying a scenario as a demo

**Intent.** "Scenario you build, demo you fly" (D-76). A demo should feel like
the real product, because it is the real product: a real session in a project
of its own, with the story's documents, data and people in place. The
screenplay keeps it on rails where that matters, and hands over to a real
agent on the turns that should show real reasoning (D-77). Demos are what the
Library lists for people who want to see a kind of work, so launching one is
one click and the same everywhere (D-78).

**Behaviour.** "Fly this" on a scenario's Hangar page calls
`POST /v1/slim/scenarios/{id}/fly`. That makes `workspace/demos/<id>/`
(`pa.fly_demo`): the scenario's `context/` documents, a `data/` file started
from the fixture with the records the script reveals held back, the roster
with each cast member's `cast/<id>.md` notes appended under "In this story", a
copy of a workflow built in the workspace, a `CLAUDE.md` that tells the agent
how to run the demo, and `.demo/` with a snapshot of the scenario and a
cursor. It creates or reuses the project "◆ Demo · <title>" (settings copied
from the Workspace project, folder set to the demo's) and opens a new session
there with the opening line in the composer. After each message the agent runs
`pa demo next`, which prints the next turn: canned lines to say or pass on word
for word (participant blocks included), the commands for documents, comments
and views, and LIVE turns to answer for real; data changes are done for it. If
the demo exists already, the button offers "Reset to the start" or "Keep
going" (D-81).

**Where.** `skills/view-kit/scripts/pa.py` (demos section, `pa demo
next|status|fly`); `omnigent/server/routes/slim_hangar.py` (`fly_scenario`,
the route); `web/src/hangar/FlyButton.tsx` and `useFlyScenario` /
`demoSessionLink` in `web/src/hangar/hangarApi.ts`, which the Library reuses;
the `[live]` direction in `skills/view-kit/references/script.md`.

## Runs and the "In flight" section

**Intent.** A person should be able to walk away from a workflow in the
middle and find it again without remembering which session it was in (D-93,
D-96). The unit they come back to is the **run**: one workflow working on one
subject, for example intent shaping on "Teen allowances". A run outlives its
session, so the place to find runs is the project, not a session. This is the
first built piece of [modes and projects](modes-and-projects.md), and it was
built so it stays true when modes move into threads (D-89): a thread will be
one more session a run can name.

**Behaviour.**

- A run has a state: working, needs you, waiting (on someone else), paused,
  finished or stopped. Paused and stopped are the person's word and nothing
  else overrides them. Needs-you comes from the records (any with status
  `needs-you`) or from the agent saying the run cannot move without an answer.
- **Pause** is said in plain language or (later) pressed. The agent records it
  at once with a where-we-left-off note of one or two sentences: what is
  settled, what is next, any question left unanswered. A pause without a note
  is refused, because the note is the whole point. It does not ask to confirm.
- **Stop** is for abandoning the work. It is the only one that confirms.
  Nothing is deleted and a stopped run can be resumed.
- **Resume** clears the note and carries on. Doing work on a paused run also
  resumes it; a stopped run needs an explicit resume.
- The project page shows **In flight** above the sessions board: a card per
  run with the workflow, subject, step, state, the note, and one button.
  Paused runs say Resume, a run that needs the person says Answer, the rest
  say Open. Runs that need the person are first and outlined in amber (D-50).
  Finished and stopped runs sit behind a "Show n finished or stopped" link.
  A project that has never had a run shows no section at all.
- Resume opens the run's session with "Resume intent shaping on ..." waiting
  in the message box for the person to send. If the session is gone, it opens
  a new session in the project with the same message, which names the run's
  dataset so the agent picks up the same run.
- The sidebar shows an amber count beside a project when any of its runs
  needs the person. Paused runs are not counted: the person chose to leave
  them.
- The Session panel's workflow card shows Paused or Stopped and the note.

**Choices made while building (not product decisions; change freely).**

- The app cannot read the conversation (no model API at work), so only the
  agent can recognise "pause this". The rule for when to pause, resume and
  stop is in the workspace's `CLAUDE.md` and the view kit skill, so every
  workflow follows it without each skill repeating it.
- Runs are the `progress/*.json` files `pa flow` already wrote, with a few
  more fields. No table. Files written before runs had a state still read.
- The Workspace and Hangar projects share one folder. A run that names a
  session is listed in that session's project; a run that names none is
  listed in the default project only.
- The Resume message goes to the message box, not straight to the agent, to
  match how every other button outside the chat behaves (D-11 keeps direct
  sends for state changes made inside a view).

**Not built yet.** The strip on the message box with a Pause button (D-90),
the rail beside mode turns (D-91), threads (D-89). Those wait on the second
walkthrough.

**Where.** `skills/view-kit/scripts/pa.py` (`flow --pause/--resume/--stop/
--state/--session`, `runs`); the rule in `workspace/CLAUDE.md` and
`skills/view-kit/SKILL.md` ("Runs"); `omnigent/server/routes/slim_runs.py`
(`GET /v1/slim/runs?project=`); `web/src/projectHome/ProjectInFlight.tsx`,
`projectRuns.ts`, `ProjectRunsBadge.tsx`; `web/src/lib/pendingPrompt.ts`;
tests in `tests/test_slim_runs.py` and `web/src/projectHome/projectRuns.test.ts`.

## Aviator as director: threads, briefs, reports and the run card

**Intent.** The main Aviator session should feel like the lead of a project,
not like one long transcript (D-89). A workflow's working (every question,
every record, every file read) fills a conversation's context and crowds out
everything else. So each workflow runs in a **thread**: a session of its own
that the director starts, briefs and keeps track of. The person stays with
the director for the whole picture and steps into a thread to do that work.
This is the third slice of [modes and projects](modes-and-projects.md).

**Behaviour.**

- **The brief.** The director hands a thread a written brief: the workflow,
  the subject, the dataset, the files to read, the target, who may be
  called, and what to report. It is a file (`briefs/<run>.md`), so the person
  can read exactly what the thread was told. `pa brief` writes it and prints
  the thread's first message, so every brief has the same shape.
- **Reports** (D-118). A thread tells the director milestones, progress,
  blockers and state, one line each, pointing at files. The thread's agent
  decides when and what; the brief tells it never to send everything.
  `pa report` records the line in the run's file (the last twenty are kept).
  For a blocker, a need, or a finish the thread also wakes the director with
  a message (`sys_session_message`, the upstream tool for messaging a session
  you did not start; `sys_session_send` only reaches a session's own
  children, which the first live flight showed). A blocker shows the run as waiting until work moves again.
- **The run card.** The director shows a run as a live card in its chat: the
  workflow and subject, the step, the state, what it needs from the person,
  its last three reports, and a button into the thread ("Answer in the
  thread" when it needs the person). The card says "Starting" until the
  thread has written its first step. It reads the run from disk through the
  server, so it still fills in when an old director session is reopened.
- **Where things stand.** The director answers from the runs' reports and
  notes (`pa runs`), not by reading the threads' histories.
- A thread's run is listed under In flight in its director's project.

**Choices made while building (not product decisions; change freely).**

- **Directing is opt-in for now.** Aviator uses the `director` skill when
  the person asks it to direct the project, or asks for a workflow "in a
  thread" or "in the background". Starting a workflow the plain way still
  runs it in the session, as before. Making threads the default for every
  workflow (D-99) should wait until this has been flown with a live agent on
  the Mac mini: the brief, the reports and the card are tested, but no cloud
  session can run Claude Code inside the app, so the agent's side of the
  conversation is not.
- Until the direct line (D-116) is built, the person answers a thread's
  questions in the thread. The skill tells the director not to relay turns
  back and forth, which would double every wait and refill its context.
- Reports live in the run's file rather than only in messages, so the card,
  the project page and the director all read the same thing and nothing is
  lost if a message is missed.

**Stepping into a thread (D-117).** Opening a thread, from its run card or
from In flight, puts the thread where the chat was. The canvas keeps its
room: Geoff turned down a side tab because it takes space from the canvas,
and because stepping in is a choice to focus. The director does not vanish.
It folds to one line above the thread's chat, and that line does three jobs:

- **Leads back.** The director's name with a back arrow returns to its chat.
- **Says where this thread is.** Its subject, step and state, so the person
  knows what they stepped into without reading the transcript.
- **Shows what else is in flight.** A count of the project's other runs, and
  an amber "needs you" count only when one of them is waiting on the person.
  Opening it lists them, each a link straight into its own thread, so the
  person can move between threads without going back through the director.

The bar appears on any session a director started, even before the thread
has written its first step (it then shows only the way back). It never
appears on the director itself. The list covers the whole project, not only
this director's threads, so it matches In flight on the project page.

**The direct line (D-116, with D-90 to D-92).** The person should be able to
stay with Aviator and still do the work, without Aviator repeating every turn
(which would double each wait and fill its context). So while a thread has
the floor, the director's chat is a direct line to it:

- **The thread's turns show in the director's chat, inside a rail** (D-91),
  in the order things happened, next to Aviator's own turns. The rail is a
  thin line in the "agent at work" color with the work's name where each run
  of turns begins. It says which work a turn belongs to; who is speaking is
  unchanged inside it. A question the thread asks is answered right there,
  and the answer goes to the thread.
- **A strip on the message box says who it is talking to** (D-90): the
  workflow and subject, the step, the state, and Pause. It is always in view.
  The name on it steps into the thread (D-117).
- **What the person types goes straight to the thread.** Aviator is not in
  the path. A message that starts with `@aviator`, or "Talk to Aviator" on
  the strip, goes to Aviator instead, and its answer shows outside the rail
  while the thread carries on (D-92). "Back to the thread" returns.
- **Pause** asks the thread to stop and note where things are; the agent
  writes the note, as with pausing in words (D-93).

Which thread has the floor: of the runs this director started that are in
flight and not set aside, the one that needs the person, else the one touched
most recently. That keeps one obvious destination for a message (D-94). When
a different thread takes the floor, the message box goes back to talking to
it.

Choices made while building, and what is still thin:

- The agent-to-agent messages (the brief, the director's nudges) are kept
  out of the rail using upstream's own marking of messages sent by another
  session. Whether the very first brief is marked that way needs the live
  flight to confirm.
- D-91 also asks for markers where a mode starts, pauses and resumes. Today
  the only marker is the work's name at the start of each run of turns.
- An off-topic question typed without `@aviator` goes to the thread; nothing
  yet guesses that it was meant for Aviator.
- Not flown with a live agent, like the rest of directing.

**Not built yet.** Start, pause and resume markers in the rail (D-91).
Threads on items (D-95).

**Where.** `skills/director/SKILL.md`; `pa brief`, `pa report` and
`pa flow --director/--brief` in `skills/view-kit/scripts/pa.py`;
`web/src/lib/runBlock.ts` (the ` ```run ` fence),
`web/src/components/chat/RunCardBlock.tsx`, `web/src/projectHome/RunParts.tsx`;
`web/src/lib/directLine.ts` (who has the floor, where a message goes, the
merge by time) and `web/src/components/chat/DirectLine.tsx` (the rail and the
strip), wired into `components/chat/Transcript.tsx` and `pages/ChatPage.tsx`
with `omnigent-slim:` comments; `GET /v1/slim/directors/{session}`;
`web/src/components/chat/DirectorBar.tsx` and `web/src/lib/threadContext.ts`
(the folded director, mounted in `pages/ChatPage.tsx`, placed by
`.pa-director-bar` in `index.css`);
`GET /v1/slim/runs/{id}?session=` and `GET /v1/slim/threads/{session}` in
`omnigent/server/routes/slim_runs.py`;
the rule in `workspace/CLAUDE.md` ("Threads").

## Routing to workflows, and what the director remembers

**Intent.** Aviator should reach for the right workflow when an ask fits one,
and stay out of the way when the person is thinking out loud (D-128). Adding
a workflow must never mean editing Aviator (D-120), so every workflow carries
its own routing, and the director reads the catalog at run time. A director
also runs for days, across compactions and new sessions, so what it must not
lose is written down where the person can see and correct it (D-134).

**Behaviour.**

- Each `workflow.json` has a `routing` block: when it fits, when it does
  not, what it needs, its lifecycle stage, the one-line offer, example prompts
  (start, offer, open; the routing evals use them) and its persona (default
  strictness and the rules that never relax). The stages are
  `workspace/frameworks/lifecycle.json`.
- `pa workflows` lists every workflow by stage with that block (`--json` adds
  the examples); `pa check` fails a Library or shipped workflow without one
  (D-136).
- The director skill routes by the ladder: named means start, and so does
  a plain request for exactly one workflow's work, said in one line (D-146);
  a clear fit to a situation or question gets one offer as a "Start it in a thread" / "Not now" question; open work
  is done directly, with no offer in that reply; quick questions, including
  one about a single paragraph, are answered. It holds other threads'
  news while the person is mid-exchange, except failures and blockers
  (D-132), and changes strictness only when the person says so (D-131).
- Director memory: a short charter beside the skill, `director/state.md`
  (rewritten at checkpoints) and `director/memory.md` (`pa remember`), all
  printed by `pa recap`, which `workspace/CLAUDE.md` tells a director to run
  after a compaction (D-135).
- **Director's notes** on the project page show both files, folded, once a
  director has written; the person edits either in place, and a save that
  would overwrite the director's newer text is refused (D-137).

- The **routing suite** measures all of this (D-133, D-143): each task is a
  prompt with what should happen (start, offer, open, answer), run through
  the real app on the model under test; the report says how many passed, on
  the tuning and the held-out sets, and shows every failing reply. Geoff
  compares two runs on a blind page of ten pairs (D-145). A question card
  that only asks what the person means is not an offer (D-147). The ladder is in
  `workspace/CLAUDE.md`, so every Aviator session routes this way (D-144).

**Where.** `evals/routing_suite.py` and `evals/routing/tasks.json`
(`evals/README.md`), `skills/*/workflow.json`, `skills/director/` (`SKILL.md`,
`charter.md`), `skills/view-kit/scripts/pa.py` (`workflows`, `recap`,
`remember`), `omnigent/server/routes/slim_director.py`,
`web/src/projectHome/DirectorNotes.tsx`. Spec:
[director-coordination.md](director-coordination.md).

## Projects with a goal, and their connections

**What it is for.** A project is one in-market goal that ships and then ends,
inside an area that lasts (D-97). So the project page should say what the
goal is before it lists sessions. And projects are not a family tree: a
requirement handed to another team is that team's project. The person needs
to see that where they act on it, and to be able to ask "what does this
project touch" (D-119).

**What it does.**

- **The goal line.** The project page opens with the goal in one line and a
  chip for how the project stands (shaping, in delivery, shipped, slipped,
  paused, stopped).
- **The Connections card**, under the goal, groups links by what they mean:
  Lives in (the area), Came from, Handed to others, Relies on, Others rely
  on this. Each row names the item the link hangs from, the other project,
  its team, and its state. No map is drawn.
- **A chip on the linked item.** In any view of the dataset, a linked record
  carries a chip: the other project, its team, and its state in a few words
  ("Allowance alerts · Cards Platform · slipped 2 wks"). Amber only when the
  other project has slipped, because that is the news the person acts on.
- **Read both ways.** A link is written once, on the item it hangs from.
  From the other project it reads the other way: what one project handed
  over is where the other came from.
- Nothing shows on a project nobody has described or linked.

**How the agent keeps it.** `pa project "<name>" --goal … --area … --team …
--state … --state-note … --data <dataset>` writes what a project is and which
datasets belong to it. `pa link <dataset> <record id> --to "<project>"
--type handed-to|started|relies-on` hangs a link from a record (`--remove`
takes it off). `pa project` alone lists them. A project can be described
without existing in the app, which is how another team's project appears.

**Choices made while building (D-121).** Meaning lives in files of our own,
not in upstream's project table. "Relies on" is shown as its own group next
to the four D-119 named, because a link stored as relies-on has to read
somewhere from the near end.

**Not built yet.** An area page. Starting a goal project from a problem
marked worth solving. Opening the linked item or the other project from a
row. Aviator telling the person when a linked project slips. The intent
graph's detail is held (D-98).

**Where.** `pa project`, `pa link` and the `projects` block of a view's data
in `skills/view-kit/scripts/pa.py`; the chip in `skills/view-kit/kit/`
(`links()` in `pa-kit.js`, `.pa-link` in `pa-kit.css`);
`omnigent/server/routes/slim_projects.py`
(`GET /v1/slim/projects/connections?project=`);
`web/src/projectHome/projectConnections.ts` and `ProjectConnections.tsx`,
mounted in `pages/ProjectHomePage.tsx`. Files: `workspace/projects/*.json`
(not committed, like `data/`).

## Initiatives, artifacts and templates

**What it is for.** Many workflows, run at different times and by different
skills, work on one initiative. Each needs to find what the others made, read
the shared intent and the questions still open, and add its own work without
overwriting anyone's. And when the person or the lifecycle skill asks "what
do we have for this feature", the answer has to come from the files
themselves. Geoff's words: an initiative registry with ids that associates
artifacts back to a shared representation of the intent.

**What it does.**

- **A fixed id for every initiative** (D-138). A project's card gets `id`
  and `key` the first time it is written, so renaming it breaks nothing.
- **A stamp in every artifact** (D-140): which initiative, which template
  and version, which stages, its status, who made it and what from. A drawn
  view counts as a rendition of its dataset. The person's own files are
  listed on the card, never changed.
- **`pa artifacts`** lists everything by initiative, stage or template, read
  from the stamps, and flags a copied file that kept its stamp.
- **Templates in three kinds** (D-139): markdown with sections owned by
  stages, records with schemas and views, and self-contained pages.
  `pa template new` writes one into place, stamped; `pa template check`
  keeps them offline and consistent with the lifecycle stages.
- **The shared intent**: an intent document with a section per concern,
  each owned by a stage, and **registers** for evidence (source required),
  open questions and assumptions, decisions (superseded, never edited) and
  ready checks, drawn as a board.
- **Alternatives and onboarding tracks**: shared templates for choosing a way
  forward (effort and waiting kept apart, a reason for every option turned
  down) and for running each owning team's onboarding steps, with who
  answers at each step and how long it takes.

**How the agent keeps it.** The hero skill contract (D-142) in the
`view-kit` skill, "Initiatives, stamps, templates and registers", and one
rule in `workspace/CLAUDE.md`.

**Not built yet.** The project page and the Hangar do not show it; no hero
workflow stamps its work yet; the lifecycle skill (D-129) is not written.

**Where.** `skills/view-kit/scripts/pa.py` (section "initiatives, artifacts
and templates"); `workspace/templates/initiative-intent/` and
`workspace/templates/initiative-registers/`; `tests/test_slim_initiatives.py`.
Spec: [initiatives-and-templates.md](initiatives-and-templates.md).

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

## PRD to dependencies (an arc in three parts)

**What it is for.** A product manager with a PRD needs to know what the work
depends on and what their options are when a dependency won't be ready, not
just a list of requirements. This arc (D-148) takes them from the document to
a choice, in three parts they can move between in any order, leaving and
coming back (D-149): **Specify** (the requirements catalog, run by
`prd-to-requirements`), **Map** (the platform capabilities each requirement
needs, run by `requirements-to-dependencies`) and **Choose** (for each
dependency that needs a decision, two to four alternatives of Pathfinder's
four kinds, with effort and waiting kept as separate numbers, and the
person's choice written to the initiative's decisions register).

**How it works.** `skills/prd-to-dependencies/` has the arc's SKILL.md and a
`workflow.json` that lists its `parts` and `checkpoints` (the few rules that
always hold, whatever the order). The two older workflows stay as they were,
with `part_of` set, so their scenarios still fly and they still start when
named; only the arc has a Library card, and the parts' demos show on it.
Choose uses the `alternatives` records template (PR 52). Complex choices go to
the decision brief skill when it is installed. `pa workflows` prints each
workflow's tier, parts and checkpoints; `pa check` notes an unknown tier or a
malformed part, never fails on one (D-153).

**The alternatives worksheet (D-152).** Choose opens on a `worksheet` view
(a new view-kit layout). Each choice shows its options as cards; pressing one
*tries* it, and four readouts at the top redraw at once: our effort (summed),
the longest wait (the one that sets the date), teams relied on, and how many
choices trade scope, each against the baseline (the first option). The point
is to feel a trade-off before committing to it: trying is local to the page,
and choosing still asks for a reason and goes to the agent. The plain table
(`compare`) stays as a second view. **Not yet:** a phase lane with projected
dates, which needs dates on options.

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

## The Library

**Intent.** The Library is where work starts, both real work on the person's
own material and demos of how the work goes (D-82). Productive work starts from
the few product skills a PM uses across the lifecycle, so they get the top
half; utility skills stay out of sight (D-83). Demos sit below, so the same
page that starts a PRD review can show someone what one looks like. Nothing is
typed into the Library: a card is only as good as the workflow's or scenario's
own metadata, which keeps one source of truth as skills and scenarios change.

**Behaviour.** "Start with a skill" shows one spotlight card and a grid of the
featured workflows, in lifecycle order. Each card has the title, a summary,
the steps as an unnumbered list (D-84), a short form made from its inputs, and
Start, which opens a new session in the Workspace project with the prompt
filled in; nothing is sent until the person presses Send. A Hangar starter
that names the workflow shows as "Other ways in", and the scenarios that run
it as "See it flown". "Scenarios and demos" shows an "In flight" strip of
demos already flown (Continue offers Reset to the start or Keep going), then a
card per published scenario: kind (Scripted or Mixed), title, summary, the
workflow it shows, the cast, a meter of live turns, about how long it takes,
Fly and, when the script has live turns, a "Live turns" switch (D-85). Fly
uses the same route and button as the Hangar's "Fly this". Templates are not
listed here (D-88).

**Where.** `omnigent/server/routes/slim_library.py` (`GET /v1/slim/library`),
`web/src/pages/LibraryPage.tsx` and `library.css`; the `library` block in
`skills/<id>/workflow.json` (`show`, `order`, `spotlight`, `summary`,
`prompt`); `title`, `summary`, `length_minutes` and optional
`"library": {"show": false, "order": N}` in `scenario.json`; extra starters in
`workspace/templates/sessions/`; `live_turns` in `pa.fly_demo`. How to add
one: `docs/customizing.md`.

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
Every run writes `setup-report.txt` in the app folder and
`flight-deck-setup-report.txt` on the Desktop; a failure names the problem,
the fix, and that file. `tests/setup_sim/simulate_zip_setup.py` rehearses the
whole flow in a Linux container.

**Updates (D-111).** Setup installs into one fixed folder, `~/flight-deck`,
and `sh ~/flight-deck/setup.sh` finds the newest ZIP or unzipped folder in
~/Downloads and updates from it, so the person never navigates folders.
`scripts/install_sync.py` compares each file with the manifest of the last
install: the person's own files, their edits to shipped workspace files and
their deletions all survive, the new versions they didn't take are saved in
`updates/<date>/`, and app code is always the release's. The Workspace and
Hangar projects follow the app out of a download folder
(`omnigent/slim_bootstrap.py`). It also builds and pins the Dock icon.

**Where.** `setup.sh`, `scripts/install_sync.py`, `start.sh`,
`omnigent/slim_bootstrap.py`, `tests/setup_sim/`, `tests/test_slim_install_sync.py`,
README "Quick start" and "Updating to a newer version".

## Usage log

**Intent.** Know how the whole platform is used (which pages, workflows,
skills and tools, what fails, what it costs), mostly while testing, without
any work content leaving the work or reaching the log (D-122 to D-127).

**Behaviour.** Every part of the app writes one JSON line per event to
`logs/usage/<day>.jsonl` in the app folder: page views and clicks from the
web app, sessions, turns and tokens from the server, Hangar actions, each
tool and skill an agent uses, and every `pa` command with its exit code. A
line holds ids, numbers and status words; any text with spaces becomes
`<text N>`. Nothing is shown in flying. `pa usage summary` prints the counts;
`pa usage pack` writes one file to the Desktop to carry elsewhere, optionally
with names hashed; `pa usage eval start` tags an eval trial's lines and keeps
them apart. Off with `OMNIGENT_SLIM_USAGE=0`.

**Where.** `skills/view-kit/scripts/usagelog.py` (the writer, reader and
packs), `pa.py` (`pa log`, `pa usage`, the per-command line),
`omnigent/slim_usage.py` (server feeds), `omnigent/server/routes/slim_usage.py`
(`POST /v1/slim/usage/events`, `GET /v1/slim/usage/summary`),
`web/src/lib/slimUsage.ts` (the web sink), `tests/test_slim_usage.py`. Spec:
[usage-logging.md](usage-logging.md).

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

**Send to repo (D-113).** On a git copy of the app, the Overview's "Not in
the repo yet" list has a Send to repo button and a line for what changed. It
commits just those files to a new `hangar/<date-time>` branch without touching
the folder's own branch, pushes it, and opens a pull request (with `gh`) or
links GitHub's page to open one; the last send is shown under the list. *Why:*
publishing wrote the files but nothing put them in the repo, so edits made on
the Mac mini never reached the ZIP everyone downloads. On the work Mac (a ZIP,
no git) the button does not show; there setup keeps published files across
updates (D-111).

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

**Widgets and views (D-112).** A workflow's page groups what people see into
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
(`GET /v1/slim/hangar`, `POST /v1/slim/hangar/repo/send`, rendered views, templates and scenario players, and the
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
