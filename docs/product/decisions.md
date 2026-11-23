# Decision log

Format: **D-number · date · who decided.** The decision. *Why.* Entries are
never edited after the fact; a later entry may replace an earlier one and says
so. "Geoff" is the product owner. "Claude" marks a choice made by the agent
while building, which Geoff later accepted as a group (D-27).

Where each decision stands now (built, replaced, pending, open) is in
[decision-index.md](decision-index.md), with a one-line reason for every
entry. Entries are grouped by topic, so numbers are not always in order.
D-60 to D-62 were never assigned. To add a decision, follow "Decisions" in
the repository's `CLAUDE.md`: claim the next number after the highest one on
`main` *and* in open pull requests, and say in the pull request which numbers
it uses.

## Foundations

**D-01 · 2026-11-20 · Geoff.** Product Aviator is a cut-down fork of Omnigent,
not a new app. *A team at work will productionize Omnigent, so staying close
to its interfaces keeps the demo transferable. Its UI paradigms are not
binding.*

**D-02 · 2026-11-20 · Geoff.** It drives Claude Code as a terminal program, no
Claude API, runs offline, never bypasses Claude Code permissions, and all
dependencies are vendored. *Constraints of the work computer.*

**D-03 · 2026-11-20 · Geoff.** Session defaults: Auto permission mode, Opus,
medium effort.

**D-04 · 2026-11-20 · Geoff.** The product is a "product partner" for product
managers: unstructured work with context files and generated artifacts,
alternating with templated structured flows.

**D-107 · 2026-11-21 · Geoff.** The setup script (D-100) clears the macOS
download flag (quarantine) itself, from its own folder only, after explaining
it and waiting for the person to press Return. A `curl` download, which never
gets the flag, stays in the README as the other way. Setup always writes a
report, on the Desktop, to send back when it stops. *A browser ZIP is the
main way onto the work Mac. Clearing the flag on files the person chose to
download is the Terminal version of macOS's own "Open Anyway", and sending
people to IT for it would stall every install. This replaces the earlier
advice in the README to ask IT.*

**D-111 · 2026-11-21 · Geoff asked, Claude chose.** The app lives in one
fixed folder, `~/flight-deck` (Geoff chose the name). Setup copies a download
into it, and a newer download updates it without overwriting anything the
person made or changed: their own files are untouched, their edits to shipped
workspace files win (the new version is saved under `updates/`), files they
deleted stay deleted, and app code outside `workspace/` is always replaced
(their copy saved). A manifest of the last install's file hashes tells the
cases apart. `sh ~/flight-deck/setup.sh` finds the newest download in
~/Downloads by itself, so nobody navigates folders in Terminal, and the
Workspace and Hangar projects follow the app when it moves out of a download
folder. *Geoff asked that a re-download keep the files he added rather than
overwrite them, and said navigating in the command line is hard. One fixed
folder in the home folder, outside iCloud and OneDrive sync, gives updates a
place to find, and comparing against what was shipped is the only way to
tell his edits from ours.*

## Structured work

**D-05 · 2026-11-20 · Geoff.** One template system serves both the chat
(inline widgets) and the canvas (workflow views). Arbitrary HTML in the canvas
must keep working.

**D-06 · 2026-11-20 · Geoff.** Do not overfit to the PRD example. The system
is for iterating on kinds of use case; the PRD flow is one of them.

**D-07 · 2026-11-20 · Geoff.** Stages extend one dataset rather than handing
files to each other. Records progress and lock at their own pace.

**D-08 · 2026-11-20 · Geoff.** Demos first, real use later. Every workflow
also has a standalone preview that runs without an agent.

**D-09 · 2026-11-20 · Geoff.** Skills carry the know-how: how to build a view
inside the frame, how to generate a demo use case.

**D-10 · 2026-11-21 · Claude.** Views are data plus a small JSON spec drawn by
one kit (`pa` and `pa-kit`), with five layouts. *An agent that hand-writes
HTML per view is slow and inconsistent; a spec is quick to write and every
view looks and behaves alike.*

**D-11 · 2026-11-21 · Geoff.** Canvas buttons may act without pressing Send
for state changes only (start, approve, lock). Content edits still wait for
Send. *Pressing Send after every approval is friction; letting a page send
arbitrary text unreviewed is a risk.*

**D-12 · 2026-11-21 · Claude.** The app, not the page, writes the message a
direct action sends, and accepts only record ids, state fields and status
words. *So a view cannot use the channel to say anything else.*

## The Session panel

**D-13 · 2026-11-21 · Claude.** Outputs are the files in `artifacts/`, context
is the files in `context/`. Both are listed in a Session panel.

**D-14 · 2026-11-21 · Geoff.** Layout direction A (the Session panel docks
beside the chat when the canvas is closed and is a popover otherwise) is the
one to refine. The other directions felt cluttered.

**D-15 · 2026-11-21 · Geoff.** Context is set per project and inherited by
every session in it.

**D-16 · 2026-11-21 · Geoff.** The Session panel shows cards for a running
workflow: its steps, the current step and progress, in the manner of Cowork.

## Participants

**D-17 · 2026-11-21 · Geoff.** Other agents, platforms and people take part in
the conversation and are attributed: their turns, inline widgets, canvas
views and document comments.

**D-18 · 2026-11-21 · Geoff.** Build both forms, scripted first: scripted
previews, then live participants, from the same participant files.

**D-19 · 2026-11-21 · Geoff.** A live participant is a background session with
a persona, not a sub-agent. *A sub-agent's context cannot be inspected; a
session can be opened and read.*

**D-20 · 2026-11-21 · Geoff.** There is one global roster. A demo or session
says who in it is eligible. The agent needs this catalog and must know how to
call from it.

**D-21 · 2026-11-21 · Geoff.** Scripts are markdown that a person can edit,
not JSON.

**D-22 · 2026-11-21 · Claude.** A person played by an agent is always labelled
a stand-in, in the roster, in every turn and in views.

**D-23 · 2026-11-21 · Geoff.** Aviator may call a participant in on its own
judgment, and says so when it does.

**D-24 · 2026-11-21 · Geoff.** A called participant sees the whole
conversation. *For the demos. To be revisited for production.*

**D-25 · 2026-11-21 · Geoff.** `@name` in the main chat addresses a
participant: they answer, Aviator still sees everything. A message with no
`@`, or with `@aviator`, goes to Aviator.

**D-26 · 2026-11-21 · Geoff.** Participants only ever suggest changes to a
document; they never edit it directly. (Built in the collaborative editor.)

**D-68 · 2026-11-21 · Geoff.** Participant messages land in the Inbox only
when they are meant for the user: a participant reaching out on their own, a
follow-up after a call, or an invitation to join a session of theirs. Replies
during a call stay in the chat, where the host relays them. *Just as we send
messages to others, they send them to us, and demos will pull the user into
other people's sessions, not only bring others into ours.*

**D-69 · 2026-11-21 · Geoff.** Both scripted and live, scripted first: a
script (or Aviator, following one) drops a participant's message at a set
point with `pa tell`; a live participant posts the same way when its brief
says to.

**D-70 · 2026-11-21 · Geoff.** No inline reply in the Inbox. A participant's
card only offers Open conversation (Join conversation for an invitation) and
Done; the user always replies in context.

## How we work

**D-27 · 2026-11-21 · Geoff.** The choices the agent made without asking, up
to this date, stand.

**D-28 · 2026-11-21 · Geoff.** Geoff reviews designs and summaries of test
results, never code. An agent on his development machine reviews and merges
pull requests.

**D-29 · 2026-11-21 · Geoff.** Ignore the production build. The local demo is
the product for now. Feature intent and decisions are documented as we go so
the production team can reconstruct the reasoning.

**D-30 · 2026-11-21 · Geoff.** Other product managers will write scenarios
too. Scenario building should happen inside Aviator, with guided workflows and
canvas elements that help someone package a runnable demo, reusing personas
and their skills or creating new ones.

**D-31 · 2026-11-21 · Geoff.** The next kinds of work to build, after
document-to-requirements and dependency mapping: problem discovery (data,
interviews and call transcripts to problems worth solving), intent shaping
(progressively elaborating an idea, using notional company frameworks for
depth and breadth that are still to be defined), decision review (a walk
through open decisions, like the one that produced this log) and delivery
status update (plan execution, dependencies, alternatives, updated
projections).

**D-32 · 2026-11-21 · Geoff.** Questions to Geoff, when there is more than
one, are asked as decision cards, one at a time, never as a list in prose.

**D-33 · 2026-11-21 · Geoff.** He is never to be asked to decide blind. Each
decision put to him carries its context, the real options with what each
leads to, the actual visuals where there are any, and a recommendation with
its reason. The decision-review kind of work is built to the same standard
for any PM: question, context, options with consequences, recommendation,
who raised it.

**D-34 · 2026-11-21 · Geoff.** The intent-shaping framework is drafted by us
as a notional one and kept swappable: a markdown file in
`workspace/frameworks/` that the skill reads, so the real company framework
can replace it later without changing the skill. He will correct the draft
from a preview.

**D-115 · 2026-11-21 · Geoff asked, Claude chose.** Every page used to put a
decision to Geoff (walkthroughs, design rounds, proposals, mockups) is kept in
the repository as an offline HTML copy in `docs/decision-artifacts/`, with
the answers he recorded on it, listed in `artifacts.json` and an index. The
`docs-refresh` contributor skill (`.claude/skills/docs-refresh/`) keeps the
copies and the docs current; its script makes each copy load nothing from the
network and shows the recorded answers read-only. *Geoff: the copies are "for
historic record and as examples we can refer to in the future; the html
versions will let others see the artifacts without needing access to my
Claude account." A skill, rather than a one-off, because walkthroughs keep
being made and the docs pass needs repeating.*

**D-159 · 2026-11-22 · Geoff asked, Claude chose.** Every complex decision
put to a person, by any agent, skill or persona in Flight Deck and by
contributors asking Geoff, is a decision brief made with one bundled skill,
`decision-brief`. The agent writes only the brief's content as a JSON file;
a fixed template (`skills/decision-brief/template/brief.html`) draws the
page, with the context, a visual stage that redraws for the option being
looked at, options with what each gives up, one recommendation and its
reason, "Something else" on every decision, a note box and saved answers.
The same page saves answers to the page on claude.ai, puts them in the chat
box in Flight Deck (the person presses Send) and offers Copy anywhere else.
`brief.py` checks the rules (never blind, exactly one recommendation, no
colors or network loads), imports answers, locks them, writes each to the
initiative's decisions register and writes a decision note linking the
research and the archived copy. Other skills point to the skill instead of
drawing their own. Its first brief puts the open details (layout, how
answers come back at work, where the record goes, when to make a brief:
DB-1 to DB-4) to Geoff, and it is built to its recommendations meanwhile.
*Geoff: "a consistent layout/experience we can iterate on, and without
wasting tokens reinventing the wheel." The 22 archived walkthroughs each
rebuilt the same parts with their own styles and saved answers in two
different shapes; duo-v2's best page held its decisions as data.*

**D-160 · 2026-11-22 · Geoff.** A brief is one scrolling page with the
briefing and picture beside "Your call", stacked on a phone (DB-1). A
narrated version (a voice and an animated stage) may come later as another
way to view the same brief, but it is not part of the core. *Geoff: "We may
later add the narrations; they're useful but not a core feature set."*

**D-161 · 2026-11-22 · Geoff.** Answers leave from a Send button in the
brief itself and reach the agent directly (DB-2, refines D-159): in Flight
Deck through a new bridge call, `omnigent.answer`, whose message the app
writes from checked ids with each note quoted as the person's words; on
claude.ai as a comment sent to Claude, with picks still saved to the page as
they are made. The composer remains the fallback on older builds. *Geoff
picked the direct send as a hybrid: "send button in the brief; keeps user
focused in the brief (no toggling back to chat)."*

**D-162 · 2026-11-22 · Geoff.** Briefs live exclusively within their project:
`projects/<key>/decisions/` holds each brief's data, page and decision note
together (DB-3). The decision also gets one line in the project's decisions
register, which is in the same project, so other skills don't ask again.
*Geoff: "briefs are just a decision artifact, so put them in the project
decisions folder." The register line is Claude's reading; it stays inside
the project.*

**D-163 · 2026-11-22 · Geoff.** When to make a brief is the agent's
judgment: generally when the decision requires context, is more than one
question, and/or has a visual side that isn't well suited to chat (DB-4,
replacing the proposed fixed rule). A single quick choice stays a question
card. *Geoff's own wording; a fixed rubric would misfire.*

## Name and design language

**D-35 · 2026-11-21 · Geoff.** The fork of the Omnigent meta-harness is named
**Flight Deck**. Product Aviator stays the name of the user interface. The
repository, folders and code identifiers keep `omnigent-slim` unless Geoff
says otherwise. *He liked the name when it came up for the design direction.*

**D-114 · 2026-11-21 · Geoff.** The GitHub repository is renamed from
`dudgeon/omnigent-slim` to `dudgeon/flight-deck-demo`. This refines D-35 for
the repository only: local folders (the Mac mini checkout, `~/flight-deck` on
the work Mac), the `~/.omnigent-slim` data folder, commands and code
identifiers keep their names. The download ZIP and its folder are now
`flight-deck-demo-main`; `setup.sh` finds downloads under either name.
*Geoff wanted the repository to carry the product's name. Renaming a local
checkout would break its Python environment and Dock launcher, which hold the
folder's path, and would separate the folder from its Claude Code session
history, so the folders stay put; GitHub redirects the old name.*

**D-36 · 2026-11-21 · Geoff.** Anthropic's `frontend-design` skill is
vendored into `skills/` (Apache 2.0, unchanged), so every session has it,
including on the work Mac, which cannot download skills. *He asked for the
Anthropic visual design skill to freshen the look.*

**D-37 · 2026-11-21 · Geoff.** One design language for the whole product: the
app, its components, chat widgets and canvas templates all read the same
design tokens, so a later change to a token reaches all of them. The widget
and template builders (view kit, scenario builder, artifact templates) are
steered to use only those tokens. *Today's four separate color systems (pink
app, navy and rust views, blue templates, orange previews) look like four
products.*

**D-38 · 2026-11-21 · Claude.** How D-37 is built: `design/tokens.json` is the
single source; `design/build_tokens.py` writes it into the app, the view kit,
the preview player and each template; the canvas viewer injects the current
tokens and the app's light or dark mode into every artifact frame, so old
artifacts follow too. The view kit's `--pa-` token names are kept as the
public contract. A `product-aviator-design` skill holds the rules and wins
over `frontend-design` where they disagree. Small all-caps mono labels are
dropped in favor of sentence case, following `frontend-design`. *Built ahead of
the color choices because it is the same whichever colors are picked.*

## The Hangar (builder mode)

Design and mockup: https://claude.ai/artifact/9M4JGs5WuxigJz1jiJ9QVr. Spec:
`hangar.md`.

**D-39 · 2026-11-21 · Geoff.** The app has two modes. "Flying" is using
Product Aviator as an end user. The "Hangar" is where the people, workflows,
views, scenarios and skills that others fly are defined. *Those are the names
in the UI: "Open in Hangar", "Back to flying".*

**D-40 · 2026-11-21 · Geoff.** In the Hangar the whole frame changes, not
only a band: paper sidebar with a dashed edge, drafting grid behind the work,
a band across the top naming the mode, Hangar shelves in the sidebar in place
of sessions, and a color of its own that is none of navy, magenta, amber or
red. *It must be obvious at a glance, and in a screenshot, which mode this
is.*

**D-41 · 2026-11-21 · Geoff.** The way in is a quiet switch at the foot of
the sidebar. Things met while flying (a participant, the workflow card, a
Library card) may also link to themselves in the Hangar, but that link must
be extremely subtle: a small wrench icon button at most, no words, shown on
hover or focus. *It must not distract in screen recordings of demos.*

**D-42 · 2026-11-21 · Geoff.** A scenario is its own small folder (cast,
invented data, screenplay) that names the workflow or workflows it runs.
A workflow keeps its instructions, record shapes and views. Many scenarios
per workflow; the seven existing demos become each workflow's first scenario.
*Many PMs will tell stories with a few kinds of work, and editing a story
must not be able to break the kind of work.*

**D-43 · 2026-11-21 · Geoff.** Building or changing anything is a guided
session with Aviator, with a form beside the chat that is the file. Building
is itself a workflow, so its constraints come before the mistake. Wording
(a brief, a screenplay line) may still be edited in place.

**D-44 · 2026-11-21 · Geoff.** Publish is strict: disabled until every check
passes, and a scenario must also play through to the end on its own.
Built-in things can only be duplicated. *A second person's approval is what
the production version should add; there is nobody to ask on one laptop.*

**D-45 · 2026-11-21 · Geoff.** Build order: the look-around Hangar first
(mode switch, frame, shelves, inspect pages, read-only), then the person
builder with drafts, checks, trial, publish and history, then scenario and
workflow building.

**D-46 · 2026-11-21 · Claude.** All Hangar work happens on a draft copy;
nothing changes for anyone until Publish. Every publish keeps the previous
version as a dated snapshot folder, and Restore makes a new version. *Dated
folders work from a ZIP download, where git may not exist.*

**D-47 · 2026-11-21 · Claude.** A participant file may carry an optional
`skills` line naming the skills their session gets, so the Hangar can show
and narrow it. Without it they get every bundled skill, as today.

**D-48 · 2026-11-21 · Geoff.** Navy lives in the app's frame: the sidebar is
navy, and content areas stay light (dark in dark mode). Navy also marks the
one primary action on a card. *A solid frame makes the app recognizable at a
glance and keeps the brand color out of the content, where color has to mean
something.* Options were a navy sidebar, navy accents only, or a navy header
band. Proposal and visuals: https://claude.ai/artifact/7YzXdsPux416J5qdkVuAea.

**D-49 · 2026-11-21 · Geoff.** The person's own marks get one color of their
own, today magenta (`--pa-you`). It is used only for what the person did:
their edits, ticks, notes and things they sent back, and never for status or
decoration. *In a workspace full of agent output, the person must be able to
spot their own hand instantly. Magenta was chosen because it is far from
every status color (green, blue, amber, red) and from the agent and author
hues, so it can't be misread as a state.* Geoff expects a corporate design
system to replace the exact hue later. What must survive is the rule, not
the color: whatever palette comes in, keep one hue reserved for the person,
distinct from all status, agent and author colors, and change only the
`you` values in `design/tokens.json`. Rust was the alternative; it sat too
close to amber and red.

**D-50 · 2026-11-21 · Geoff.** "Needs you" is amber (`--pa-attn`), and red
(`--pa-fail`) is kept only for real failures. *If waiting on the person were
red, red would be everywhere and real failures would stop standing out;
amber reads as "your turn" without alarm.* The alternative was red for both.

**D-51 · 2026-11-21 · Geoff.** The "Open in Hangar" link on things met while
flying (a participant's turn, the Session panel's workflow card, Library cards)
is a small wrench icon with no words, invisible until the pointer is over the
thing or the wrench has keyboard focus. *Refines D-41: it must never show in a
screen recording of a demo.*

**D-52 · 2026-11-21 · Claude.** The Hangar is its own full-screen route
(`/hangar`) outside the flying shell, not a variant of the flying sidebar. Its
catalog is read by the server from the existing files on every request, and
its checks and rendered views come from the view kit's own `pa` code, so the
Hangar can never disagree with `pa check`. *Keeps builder mode separable from
upstream Omnigent's shell and adds no new data store.*

**D-53 · 2026-11-21 · Geoff.** Asks in chat, work in canvas. Questions,
pick-ones, single cards and summaries are drawn inside the conversation and
fold into a record once answered; catalogs, boards and documents open in the
canvas. *He can answer a question without losing the document in the canvas,
the transcript shows what was decided, and there is never a second live copy
of a view.* The options not taken: canvas only (the app before this), anything
in chat with an expand button, and still snapshots in chat.

**D-54 · 2026-11-21 · Geoff.** The intent framework stays as drafted (five
depths, seven areas). His note: it is a lot, and the product will need ways to
add and remove complexity progressively, to focus the person on one task in
depth or several at a high level, and to disclose progressively to both human
and agent. The framework's job was to pressure-test the system, and it did.

**D-55 · 2026-11-21 · Geoff.** The agent must be able to direct the person's
attention. First form, as he suggested: while a view in the chat is waiting
for an answer, the canvas goes grey and returns when pointed at. This is an
exploration to react to, not a settled design.

**D-56 · 2026-11-21 · Claude.** Hangar drafts and the kept versions live in
the workspace under `.hangar/` (`drafts/people/<id>.md`, `history/people/<id>/`),
which is gitignored, and the live roster file is only ever replaced by
`pa publish`. *A draft is a plain copy of the file it will become, so the same
`pa` checks run on it, and nothing half-made can be picked up by a session.*

**D-57 · 2026-11-21 · Claude.** Restoring an old version is a publish: it
turns the old version into a draft and sends it through the same checks and
used-by guard, and the version it replaces is kept too. *An old version may
no longer fit what exists now; "always a way back" must not become a way
around the gate.*

**D-58 · 2026-11-21 · Claude.** For slice 2, "Try them" opens a builder
session that loads the draft with `pa who --dir .hangar/drafts/people` and asks
it the user's question, rather than a separate striped trial strip. *It uses
the real participant turn, so what you try is what people will meet; the
dedicated trial strip from the mockup can come later without changing files.*

**D-59 · 2026-11-21 · Claude.** Builder sessions start in their own "Hangar"
project (created at startup next to Workspace), so building never mixes into
the flying session list. *Matches D-39's two modes without a second app.*

**D-63 · 2026-11-21 · Geoff asked, Claude chose.** In the Hangar, a person's
page *is* their editor. Edit starts a draft and stays on the same page; the
name, role, kind, how they answer, call-for line, brief, skills and where they
are called are form fields that save to the draft as you type (about half a
second after you stop). Nothing goes live until Publish. *Geoff found that
Edit threw him back into flying mode and a new session ("clunky, opaque,
mysterious"); simple values like the brief should just be editable.*
Walkthrough: https://claude.ai/artifact/3w9xwsyNFs5P7zA4sT5dSt

**D-64 · 2026-11-21 · Claude.** Aviator helps from a pop-over at the bottom
right of the Hangar page, which can be pinned as a column, instead of opening
a session in flying mode. It is a real session in the Hangar project working
on the open draft; its id is kept on the draft so reopening the page finds the
same conversation, and its edits show on the page as it works. "Try them"
lives in the same pop-over. This replaces D-58's jump to a builder session.
*Keeps the person in the Hangar while still letting Aviator make several
changes at once.*

**D-65 · 2026-11-21 · Claude.** Where someone can be called is set on their
own page with tick boxes for workflows, scenarios and starters. Publish writes
those changes into each `workflow.json` and `scenario.json` cast and each
starter's participant line. Checks block taking someone out of a scenario
whose script has them speak, and warn when a scenario is ticked but its
workflow is not. *Casting was the hidden step in slice 2 (the skill told you
which file to change); it belongs with the person.*

**D-66 · 2026-11-21 · Claude.** A person can bring skills: the `skills` field
in their roster file, picked from the Skills shelf. The session that plays
them is told to use those skills (a "Skills you bring" section in its opening
message). *Geoff could not see how to give a character skills.*

**D-67 · 2026-11-21 · Claude.** D-42 is built: a workflow's manifest is now
`skills/<id>/workflow.json` (no fixtures or script), and each scenario is
`workspace/scenarios/<id>/` with `scenario.json` (naming its `workflow`, the
cast, fixtures and script), `fixtures/` and `script.md`. The seven demos keep
their ids. `pa` still reads the old one-folder layout. *Lets one workflow have
several scenarios, and lets the scenario builder (slice 3) edit demo data
without touching the workflow.*

**D-71 · 2026-11-21 · Claude.** Scenarios and workflows are built like people
(D-63): the Hangar page is the editor, saving to a draft as you type, with the
Aviator pop-over beside it and Publish as the gate. Their draft is a copy of the
whole folder (`.hangar/drafts/scenarios/<id>/` or `workflows/<id>/`), so the
fields (title, summary, workflow, cast, steps, opening line) and every text file
in the folder (the script, fixtures, `SKILL.md`, `context/` and `cast/` notes)
can be edited in place. A scenario publishes only when `pa check` passes and it
plays through; a workflow can't be removed while a scenario runs it. Publish
keeps the folder it replaces, and History can restore it. *Same pattern as
people, so there is one way to build anything; folder drafts because a scenario
is several files that must change together.*

**D-72 · 2026-11-21 · Claude.** A workflow that ships with the app is never
changed in place. "Edit a copy" drafts it, and publishing puts a workspace copy
in `.claude/skills/<id>/` that takes over its id; removing that copy brings the
shipped one back. A new workflow starts as a duplicate of the nearest one.
*Keeps the shipped workflows as a safe floor while letting a PM change one for
their team; a blank workflow has too many parts to start from nothing.*

**D-73 · 2026-11-21 · Claude.** A scenario draft plays on its own editor page
(the same player a demo uses, drawn from the draft), and the pop-over's second
tab is "Play it" instead of "Try them", asking Aviator to run the draft. A
scenario can carry an opening line (`opening` in `scenario.json`), for the
Library's demos. *Seeing the demo is the real check that a script change
worked.*

**D-74 · 2026-11-21 · Geoff.** People and agents can have a picture. It is
picked on the person's Hangar page from any PNG, JPEG, WebP or GIF file (under
2 MB), copied into the draft, and on Publish into
`workspace/participants/avatars/<id>.<ext>`, named by the `avatar` line of
their roster file. It replaces the initials everywhere they appear: Hangar
cards, participant turns in the chat and the Session panel. *Geoff: "we also
need to be able to select icons/avatars for each participant… when selected
(e.g. from a file in my desktop), they should be added to the repo."*

**D-75 · 2026-11-21 · Geoff.** Configuration travels with the repo: people and
their pictures, scenarios, workflows built in the workspace
(`workspace/.claude/skills/`), starters and skills are committed files; a test
fails if `.gitignore` would drop any of them. Drafts and the Hangar's own
history (`workspace/.hangar/`) and user sessions stay local. The Hangar's
overview lists published files not yet committed. *Geoff: "config, like
personas, harness skills, workflows, scenarios should all travel with the repo.
user sessions don't need to but can."*

**D-76 · 2026-11-21 · Geoff.** "Scenario you build, demo you fly." The Hangar
shelf stays "Scenarios": a scenario is the thing you build (story, cast, data,
screenplay). Flying one makes a demo: a project named "◆ Demo · <title>" with
its own folder (`workspace/demos/<id>/`, not committed) and real sessions in
it. Most demos are projects, so their sessions are listed together.

**D-77 · 2026-11-21 · Geoff.** Scripting is set per turn, not per scenario. A
flown demo plays each turn of the screenplay either canned (said word for word,
the default) or live, where a real agent answers. A live turn is marked with
`[live]` or `[live: what the turn is about]` under its Aviator or participant
line; the written line stays as a guide, and "Play it" shows it as live. The
agent in the demo steps through the script with `pa demo next`, which also does
the data changes (revealing records, setting statuses) itself.

**D-78 · 2026-11-21 · Geoff.** A demo is launched with "Fly this" on the
scenario's Hangar page, and from the Library. Both call one route,
`POST /v1/slim/scenarios/{id}/fly`, and the web UI's `FlyButton`. The Library
lists demos from `scenario.json` and `workflow.json` (title, summary, cast,
workflow), so those stay tidy. The Library's own design belongs to the Library
redesign, not to this work.

**D-79 · 2026-11-21 · Geoff.** A scenario folder holds `scenario.json` (with
`opening`, the line the demo starts with), `fixtures/` (the dataset, and
documents the work produces), `script.md`, `context/` (invented documents the
story starts from, such as the Allowances PRD and the platform map, which moved
out of `workspace/context/`) and `cast/<person>.md` (what each person knows in
this story). Flying copies `context/` in, starts the dataset from the fixture
with the records the script reveals held back, and appends each `cast/` note to
that person's roster file in the demo under "In this story".

**D-80 · 2026-11-21 · Geoff.** Workflow skills never copy demo material out of
`scenarios/` themselves. A demo's documents and data are put in place by
flying it; outside a demo the agent asks for what it needs.

**D-81 · 2026-11-21 · Geoff.** Flying a scenario whose demo already exists
offers "Reset to the start" (the folder is made again from the scenario as it
is now) or "Keep going" (a new session in the same folder, the story where it
was). A fresh demo's first session opens with the opening line in the
composer, ready to send.

**D-82 · 2026-11-21 · Geoff.** Keep the Library. It is where real work and
demos start, and nothing on it is typed into it: every card is generated from
the metadata of the workflow or scenario it starts. The old contents (13 canned
sessions, the template list) were temporary and are gone. Design round:
https://claude.ai/artifact/5XhbdjSKp7i2t1ChoxqS6Z.

**D-83 · 2026-11-21 · Geoff.** The top half is the featured product skills,
expected to be four to six (intent shaping, problem discovery and the like).
The many utility skills (person builder, scenario builder) are never shown. A
workflow is featured by `"library": {"show": true, "order": N}` in its
`workflow.json`; `order` puts them in rough product-lifecycle order. One
spotlight card (`"spotlight": true`, else the first), then a grid.

**D-84 · 2026-11-21 · Geoff.** A skill card shows its steps, without a
picture. Steps are as much tasks and outcomes as a sequence, so they are an
unnumbered list. Imagery may come later. The workflow's `inputs` (or the
fields in `library.prompt`) become a short form; Start opens the composer with
the prompt filled in. A Hangar starter that names the workflow is an extra way
in on the same card.

**D-85 · 2026-11-21 · Geoff.** A demo card has Fly and, when the script has
live turns, a "Live turns" switch. Off plays every turn canned, for a demo
that must not vary.

**D-86 · 2026-11-21 · Geoff.** One project per demo. A demo already flown shows
in an "In flight" strip; flying it again offers "Reset to the start" or "Keep
going" (D-81).

**D-87 · 2026-11-21.** A demo card reads `scenario.json`: the title names the
situation and the summary states the tension in at most 25 words;
`length_minutes` is optional. Scripted or Mixed and "N of M turns live" are
worked out from `script.md`. Demos are listed in the order of the skills they
show. The seven shipped scenarios were retitled to match.

**D-88 · 2026-11-21 · Geoff.** Artifact templates leave the Library. They are
managed in the Hangar, and the agent finds them when asked.

**D-170 · 2026-11-23 · Geoff asked, Claude chose.** The Library's top half
shows a workflow the way the Hangar shows it. Each card draws the workflow's
main view from its scenario's sample data (the first work product that is a
view, preferring a part of the arc that has a scenario), labelled "You get",
with its steps as the Hangar's chevrons, its stage tag (Discover, Shape,
Requirements, Engage, Deliver) and who it can call in. Only arcs get a card,
as D-153 says; Review and Decide demos still show below. The lower half becomes
one board, a row per demo (story, workflow, cast, turns and minutes, Fly),
with Fly plain until a row is hovered. A person keeps one author colour across
the Library, and labels are sentence case with no shadows. Refines D-83 to
D-85: steps get a picture after all, now that the Hangar draws views. *Geoff
(2026-11-23): the top half "predates our entire walk through concept and the
entire hangar — so it needs to be reconciled with the hangar", and it may
appear in an explainer video. A board of rows lines up for any number of
demos, where a three-wide grid of seven left one orphan card.*

**D-112 · 2026-11-21 · Geoff asked, Claude chose.** A workflow's widgets and
views are shown and edited in the Hangar. The workflow page splits them into
"Widgets · in the chat" and "Views · in the canvas"; a view's page and the
workflow page have Edit buttons that open the workflow's draft at that widget.
In the draft each one opens beside its drawing from the draft (over the
scenario's sample data), with its header lines, form questions and buttons as
fields and the whole spec as JSON; only valid JSON is saved. "Add a widget or
view" starts from a blank form, a blank summary or a copy of one already
there, adds it to `workflow.json` `views` (now editable through `pa`), and
writes a line in `SKILL.md` telling the agent how to draw it, with
`--host chat` for a widget. Where a view shows is read from the scenario's
script first, then from how `SKILL.md` renders it, then from its layout.
*Geoff: "Widgets that relate to given workflows should be visible and editable
in the hangar." Placing by `SKILL.md` makes the label match what the agent will
really do, and editing inside the workflow draft keeps the publish gate,
history and "travels with the repo" (D-75) for free.*

**D-113 · 2026-11-21 · Geoff.** On a git copy of the app (the Mac mini), the
Hangar's Overview has "Send to repo": it commits the published configuration
(the D-75 folders) to a new `hangar/<date-time>` branch, pushes it, and opens a
pull request with `gh` when it is installed, or links GitHub's page to open
one. The commit is built in a throwaway index from HEAD, so the folder's
branch and working tree are untouched; pulling main after the merge brings the
same files back. It runs only when pressed, and the same changes are not sent
twice. A ZIP copy (the work Mac) has no git and shows no button: there, what
matters is that published files survive updates, which setup does (D-111).
*Geoff: "I'm less concerned about the work Mac changes making their way to
GitHub for now; primary concern is them surviving updates. Later, we may
likely re-commit the repo to a company repo, treating this as a fork." The
button pushes to whatever remote the copy came from, so it keeps working in a
company fork. This is the one place the app reaches the network on purpose,
and only on a person's press.*

Geoff confirmed the person-editing choices on 21 Nov (combined walkthrough
https://claude.ai/artifact/7gbkDmURSuwhWGWVzyBtU6): the page as the editor with
autosave (D-63), the pinnable Aviator pop-over with "Try them" (D-64), casting
from the person's page (D-65) and skills passed to the session (D-66).

**D-167 · 2026-11-22 · Geoff asked, Claude chose.** Skills that are not
workflows (the kits and moves every session gets) are built in the Hangar the
same way as workflows: the skill's page has Edit (or "Edit a copy" for one that
ships with the app), Duplicate and Remove, and the Skills shelf has "New
skill". The draft opens as the editor, with the description and the
instructions of `SKILL.md` as fields, every other text file in the folder, the
checks (the name is the folder's id, a one-line description under 1024
characters, some instructions, no workflow manifest), Aviator in the pop-over
with a "Try it" tab, and Publish into `workspace/.claude/skills/<id>/`, where a
copy of a shipped skill takes over its id as D-72 does for workflows. Retiring
one is blocked while a person lists it in their skills. `pa draft|publish|history
skill` and a bundled `build-skill` skill do the same from a session. *Geoff:
"editing people and skills still pops the user out of the Hangar". There was no
way to change a skill in the Hangar at all, so the only route was a flying
chat. Reusing the folder-draft machinery keeps one way to build anything.*

**D-168 · 2026-11-22 · Claude.** Hangar chats never open in flying mode. The
flying sidebar no longer lists the "Hangar" project or its sessions (refining
D-59, which put them there to keep them out of the flying list); a Hangar
session opened in flying mode anyway (an old link) goes back to its draft's
page; and the building skills, asked in a flying chat, start the draft and hand
over a link to its Hangar page instead of building in the chat. The last two
"Continue with Aviator" and "Try them" links that started flying sessions are
gone. *Those were the back doors that kept dropping Geoff out of the Hangar
after editing itself had moved into the page (D-63).*

**D-169 · 2026-11-22 · Geoff asked, Claude chose.** A new workflow can start
blank, refining D-72's "starts as a duplicate". "New workflow" on the Workflows
shelf makes a draft with three steps (Gather, Work through, Wrap up), one record
type (`item`, with a title, detail and status), one list view and a `SKILL.md`
to rewrite, which passes every check once it has a summary. Duplicating the
nearest one still works. *Geoff asked to finish the build, and a PM making a
new kind of work should not have to find one to copy and then strip it.*

## Modes, runs and projects

Geoff's answers of 2026-11-21 to the walkthrough at
https://claude.ai/artifact/HRgpJURjcqasGSCmd3894d (questions M-1 to M-11 in
[modes-and-projects.md](modes-and-projects.md)). Numbers start at D-89 because
D-76 to D-88 are taken by work in open pull requests.

**D-89 · 2026-11-21 · Geoff.** The main Aviator session acts as a project
director, and modes are powered by threads. Deep work that benefits from its
own context window (a workflow such as intent shaping) runs in a sub-session
that runs the skill; the director coordinates with it by agent-to-agent
messages. The person can stay in the director session and click into a thread
only when needed. The approach is dynamic: the director decides when work
earns a thread. A main session should feel like a Claude Code project. *His
words: "for context reasons, the main session should act like a project
director/orchestrator, with threads used to isolate context for a given
workflow." He chose this over all three drawn options (in place with threads
for branches, every mode in its own session, everything in one chat).* Still
open, and his to decide: how the director session shows a mode for the
high-level interactions (M-12).

**D-90 · 2026-11-21 · Geoff.** A mode shows as a one-line strip on the message
box: the workflow, the step, and Pause. Not a band under the header, and not
only the Session panel card. *Always in view whether the canvas or the panel
is open, and clearly lighter than the Hangar's frame change (D-40).*

**D-91 · 2026-11-21 · Geoff.** Replies that belong to a mode are marked by a
thin rail beside them, with a marker in the transcript where the mode starts,
pauses and resumes. Participants keep their own names inside the rail. *Who
is speaking stays separate from what work a turn belongs to.*

**D-92 · 2026-11-21 · Geoff.** A side question during a mode is answered
outside the rail and the mode stays on. It does not end or pause the mode.

**D-93 · 2026-11-21 · Geoff.** Leaving a mode: say it in plain language or
press Pause. There are three endings, kept distinct: pause (come back), finish
(the work product is written) and stop (not worth pursuing; what exists is
kept). On pause the agent writes a "where we left off" note and a Resume
control, and an unanswered question is frozen as Paused. Only stop asks for
confirmation.

**D-94 · 2026-11-21 · Geoff.** One mode has the floor at a time. Starting a
second pauses the first and remembers it, and the agent offers to return when
the second ends. *Chosen when modes were drawn inside one chat. Under D-89
several threads can be in flight at once; what this fixes is that the
person's message always has one obvious destination.*

**D-95 · 2026-11-21 · Geoff.** Any item (a decision, a risk, a requirement)
can have its own thread, attached to the record, opened from its row, with a
count on the row. Aviator may start one when a discussion of one item runs
long, and says so. *Keeps each item's reasoning with the item.*

**D-96 · 2026-11-21 · Geoff.** In-flight work is found on the project page: an
"In flight" section with a card per run (step, state, where it left off,
Resume), sessions below, and a count of runs that need the person in the
sidebar. Built on upstream's project board.

**D-97 · 2026-11-21 · Geoff.** A project is one in-market goal that ships and
then ends. It sits inside an area, a lasting problem space where problem
discovery and shared context live; a problem marked worth solving starts a
goal project. *His caveat, recorded as a constraint on what follows: this may
need to become more graph-like and less hierarchical. "If project A has 20
requirements, and implementing one of them is delegated to a different team,
that would become project B for them." So the area is a home, not the only
kind of link, and a record must be able to point at another project.*

**D-98 · 2026-11-21 · Geoff.** The level of detail of the intent graph is not
decided yet, on purpose: "too early for me to decide; hold decision until it
blocks something." Nothing is built for a graph beyond what D-97 needs (a
project names its goal and its area). *The likely first thing to force it is
his own example in D-97, a requirement handed to another team's project.*

**D-99 · 2026-11-21 · Claude, accepted by Geoff.** The smaller calls listed
in the walkthrough stand: every workflow makes a mode, not only the ones
featured in the Library; a mode has no color of its own (it uses the "agent
at work" token); starting a mode never asks first; a run belongs to one
project; threads reuse upstream's side chats and child sessions; demo
projects (D-76) stay as they are. "Resume returns to the same session" is
carried over as "Resume returns to the run's own thread".

**D-116 · 2026-11-21 · Geoff.** The director shows a mode through a direct
line to its thread. The thread's questions appear in the director's chat
inside the rail (D-91), and while the thread has the floor the person's
messages go straight to it; the strip (D-90) says who they are talking to.
Aviator is not in the path. `@aviator`, or a question off the topic, is
answered by Aviator outside the rail (D-92). *It is the only option where the
person truly stays with the director and still does the work, it keeps D-90
to D-92 as chosen, and it avoids a second agent's wait on every turn. This
answers M-12, the part D-89 left open.*

**D-117 · 2026-11-21 · Geoff.** Stepping into a thread puts it in place of
the chat: the thread takes the chat column, the director folds to a bar on
top that shows what else is in flight and leads back, and the canvas stays
where it is. Not a tab in the side area. *Geoff: a thread in the side pane
steals space from the canvas, and a person who steps into a thread is
choosing to focus. He asked how upstream handles it: upstream opens a child
session as a tab in the Workspace panel, the same area as the canvas, with a
maximise link to the child's own session page, which has a trail back to its
parent. So upstream's tab has exactly the cost he named, and its full page is
most of this option already; what is new is the folded director bar. Answers
M-13.*

**D-118 · 2026-11-21 · Geoff.** A thread reports to the director in short
lines, not transcripts: milestones, progress, blockers, and state such as
completion. The workflow's agent uses its own judgment about when and what to
send, and must not send everything. Each line points at the files rather
than repeating them. *Geoff: "the workflow agents should have discretion on
when and what to send to the director, but they should not send everything."
The director needs the state of each piece of work to coordinate; copying
the working would undo the context isolation that threads exist for (D-89).
Answers M-14.*

**D-119 · 2026-11-21 · Geoff.** A project's connections show in two places:
a chip on the linked item, naming the other project and its state, and one
Connections card on the project page that gathers them, grouped by what the
link means (lives in, came from, handed to others, others rely on this). No
map. A link is typed, hangs from a specific thing (a requirement, a
problem), reads the other way from the far end, and is stored as one line
with the item it hangs from. *This follows his caveat on D-97 that projects
are more graph-like than a family tree: a requirement handed to another team
is that team's project. The chip puts the news where the person acts on it,
and the card answers "what does this project touch" without drawing a tree
that is not there. It does not build the intent graph, whose detail stays
held (D-98). Answers M-8.*

**D-120 · 2026-11-21 · Geoff asked, Claude chose.** Aviator's routing is
modular: adding a hero or workflow skill never means editing Aviator. Geoff:
"I don't want to have to update Aviator every time we add a new hero/workflow
skill." Each workflow carries its own routing (when it fits, near misses,
what it needs, its lifecycle stage, an offer line, eval examples) and its
persona in its `workflow.json`; Aviator reads the catalog at run time with
`pa workflows` and names no workflow; lifecycle stages are a data file;
`pa check` fails a Library workflow without routing. *Workflows are built in
the Hangar by people who should not have to touch the director, and the
production team will add more; a hard-coded list would drift the first time
one is added. See [director-coordination.md](director-coordination.md).*

**D-121 · 2026-11-21 · Claude.** What a project is lives in a small file of
our own, `projects/<slug>.json` in the workspace: its name, goal, area, team,
state and a few words on the state. A link is one line on the record it
hangs from (`"links": [{"type", "project"}]`), a dataset names the project it
belongs to, and three types are stored: `handed-to`, `started` and
`relies-on`. The far end is never stored; it is read from the same line. A
project file may describe a project that is not in this app, such as another
team's. `pa project` and `pa link` write them. *Upstream's project table is
left alone so the production team can follow upstream; one line per link is
what D-119 asked for and cannot fall out of step with itself; and files
assembled on request work from a ZIP and are easy to replace with a service
when the intent graph is designed (D-98). Another team's project has to be
describable, because that is exactly Geoff's example in D-97.*

Geoff's answers to the Aviator coordination walkthrough
(https://claude.ai/artifact/La4Qa5THk5JhwQBQGcVY7d, questions AV-1 to AV-7 in
[director-coordination.md](director-coordination.md)), locked 2026-11-21.

**D-128 · 2026-11-21 · Geoff.** Aviator routes to workflows by a ladder:
start one when the person names it or presses Start in the Library; when a
request clearly fits one and there is material to work on, offer it once, in
one line with a button, and carry on openly if declined; otherwise work
openly and offer once later, when one idea firms up; answer quick questions
directly. Never start a workflow silently. *An offer costs one line; a false
start imposes a method on someone thinking out loud and costs a thread. It
also gives the routing evals four clear outcomes to grade.*

**D-129 · 2026-11-21 · Geoff.** "I'm working on a new feature" invokes a
feature lifecycle skill. It is not a hero skill (not featured in the Library;
it is part of how Aviator directs). It first looks for an existing project
that fits and uses it; if the work is truly new, it creates the project and,
where it is related to existing ones, links them (D-119, D-121). It then
gathers what exists by linking files, shows the stages (from a data file,
D-120) with each stage's workflows and state, and offers the next stage.
Stages can be skipped, entered at any point or repeated; each runs in its own
thread. Geoff: "Should be paired with a project retrieval function... if a
project actually exists that is relevant, find and use, or associate (with
cross links) if the thing is truly new but related." *It makes the project the
spine routing works from, and avoids a new project every time someone
mentions a feature that already has one.*

**D-130 · 2026-11-21 · Geoff.** A workflow's persona has rules that never
relax (honesty and the person's agency) and a style whose strictness is a
setting: light touch, guide or by the book. The default is guide: a missing
piece becomes a gap with who could close it, the score stays true, and the
work moves on. *Guide is the only level that is both honest and never blocks
the person; the evals decide whether any workflow needs another default.*

**D-131 · 2026-11-21 · Geoff.** The person changes strictness for a run in
words ("be tough on this one", "go easier"); the change is said in one line,
shown on the mode strip (D-90) and recorded in the run. The Hangar sets each
workflow's default. The agent may suggest a change but never makes one
silently. *The person stays in control and the change is visible; a brief
can say how strictly it was shaped.*

**D-132 · 2026-11-21 · Geoff.** While the person is in an exchange with one
thread, news from other threads is held until the exchange pauses, then given
as one line and the run card. Failures and blockers that affect the person
come through at once. *It protects the focus that stepping into a mode is for
(D-94, D-117) and keeps red for failures (D-50).*

**D-133 · 2026-11-21 · Geoff asked, Claude chose.** Aviator is tested in
three suites (routing, personas, coordination including long-haul stories
with a forced compaction) through the real app on the Mac mini, with a fresh
workspace per trial, code graders, a Claude judge per rubric line, and Geoff
choosing the better of ten blind transcript pairs per round. Geoff: "Use a
light model, Sonnet or Haiku; I need to preserve usage for further dev."
Claude's reading: the simulated person and the judge run on Haiku; Aviator
and its threads run on Sonnet in routine eval rounds; an Opus run is made
only when Geoff asks, to check that a tuned prompt holds on the model he
flies (Opus, the session default). *Usage on the Mac mini is shared with
development. Sonnet still behaves enough like the flown model for routing and
coordination to be meaningful, which Haiku may not; the judge's agreement with
Geoff's blind choices shows whether Haiku is good enough to grade.*

**D-134 · 2026-11-21 · Geoff.** The director remembers across sessions and
compactions in three layers: a short charter in the director session's
startup instructions (it survives compaction), the director skill reloaded
after a compaction or in a new session, and state in files written as the
work goes (`state.md`, `memory.md`) added back as one recap. What it holds and
remembers shows on the project page as "Director's notes", readable and
editable. *A memory the person cannot see cannot be trusted, and a wrong one
does damage for weeks; editing in place is the quickest fix.*

Choices made while building D-120 and D-128 to D-134:

**D-135 · 2026-11-21 · Claude.** The director's charter
(`skills/director/charter.md`) reaches a director through a short paragraph in
`workspace/CLAUDE.md` that tells a session that has been directing to run
`pa recap` after a compaction or in a new session; `pa recap` prints the
charter, `director/state.md`, `director/memory.md` and the runs. This refines
D-134, which put the charter in the director session's startup instructions.
*The app has no server-side record of which session is directing, so the
bridge cannot pick the right session; Claude Code re-reads the root
`CLAUDE.md` after every compaction, so the pointer survives without any change
to upstream's bridge. If the evals show directors skipping the recap, the
bridge route is the next step.*

**D-136 · 2026-11-21 · Claude.** `pa check` fails a workflow shown in the
Library (`library.show`) or shipped in `skills/` that has no routing `when`,
`stage` or examples, and checks the shape of any routing block. A Hangar
workflow without one still passes, and `pa workflows` lists it as "start only
when named". The lifecycle stages are `workspace/frameworks/lifecycle.json`;
document review sits on Specify beside PRD to requirements. Strictness levels
are defined once, in `pa.py`, and printed by `pa workflows`. A clear-fit offer
is one `AskUserQuestion` with "Start it in a thread" and "Not now". *Shipped
workflows must stay routable even when hidden from the Library
(requirements-to-dependencies), while a half-built Hangar workflow should not
be blocked; a question card is the one-press answer Claude Code already
draws.*

**D-137 · 2026-11-21 · Claude.** Director's notes live in
`workspace/director/` (one director per workspace, gitignored like runs). The
files start as headings only; what to write and when is in the skill, so the
person reads the project, not instructions. A save from the project page
names the version it edited and is refused if the director rewrote the file
meanwhile, with the newest text shown. The section appears only once a
director has written something, folded. *The notes are for checking and
correcting, not for every visit, and nobody's words should be lost to a
silent overwrite.*

**D-143 · 2026-11-22 · Claude.** The routing suite (D-133) is
`evals/routing_suite.py`. Its tasks are every workflow's `routing.examples`
plus `evals/routing/tasks.json` (near misses, quick answers, open work,
cross-workflow offers, lifecycle prompts that wait for their skill), split
60/40 by a hash of each id. A trial copies the Workspace project's folder
without its data, runs and drafts, opens a new session in that project with
the model under test passed as Claude Code's `--model`, sends the prompt and
waits for one turn; a question card ends it, and a thread it starts is
stopped at once. Trials run one at a time. Grading reads the usage log, the
copy's files and the card first, and asks a Haiku judge only when they are
silent. *Through the app so the result is what Geoff would see; a fresh copy
so trials cannot help each other; one at a time because the eval tag is one
file per machine; threads stopped because only their existence is graded and
their work would cost usage Geoff wants kept.*

**D-144 · 2026-11-22 · Claude.** The routing ladder is in
`workspace/CLAUDE.md` ("Which workflow, if any"), so every Aviator session
follows it, not only one that has loaded the director skill. A clear-fit
offer is recorded with `pa log offer.made workflow=<id>`, in the workspace
instructions and the director skill. *D-128 says Aviator routes this way;
most sessions never load the director skill; a logged offer is graded by
code instead of a judge's reading.*

**D-145 · 2026-11-22 · Claude.** Each tuning round's blind comparison is a
page made by `routing_suite.py pairs`: ten prompts, the ones where two runs
differ most first, each run's reply and what it did side by side in shuffled
order, with "Left", "Right" or "Same". Answers are copied back as JSON; the
key stays in the run folder. *D-133 asks Geoff to rank ten blind pairs per
round; the page names neither run, works offline, and his answers can be
checked against the judge.*

**D-146 · 2026-11-22 · Claude.** The ladder (D-128) gains a rung and two
limits, from the first baseline (35 of 42 on Sonnet). "Asked for": when the
person tells Aviator to do the work one workflow does, on material they point
to ("find the problems worth solving in these notes"), that is asking to run
it, so it starts, and Aviator says which workflow it started. A clear-fit
offer is for a situation described or a question asked. Open work ("what else
could we do") and questions about one paragraph get no offer in that reply.
The routing suite can give a task fixture files, so an offer task has what its
workflow needs. *The baseline started too rarely on plain requests (an
imperative is consent, and an offer then is a wasted turn) and offered on
open asks 3 of 3 times; two offer tasks failed only because the empty trial
workspace lacked the workflow's material, which is Aviator behaving
correctly.*

**D-147 · 2026-11-22 · Claude.** Second tuning round, from tune1 (5 of 7
fixed; two open tasks and two offers still failing). A question card counts
as an offer only when one of its answers starts something ("Start it",
"Run", "Yes") or names a workflow; any other card is a clarifying question,
and the judge reads its words with the reply. `report --regrade` grades saved
trials again with the current grader. What a workflow needs is its `Needs`
line and no more, so an idea in a sentence is enough for intent shaping,
whose `When` now covers "is this a real thing?". The delivery-status offer
task gets its scenario's milestone plan. *On the Mac mini every failing open
trial was Aviator asking "which calls?" or "which paragraph?" on a card,
which is the right behaviour graded wrong; the offer regressions were
Aviator demanding evidence for an idea, and saying what a date check needs
when the trial had no plan.*

## Usage logging

Spec: [usage-logging.md](usage-logging.md). Open questions UL-1 to UL-3 are
there; the build follows each one's recommendation until Geoff answers.

**D-122 · 2026-11-21 · Geoff asked, Claude chose.** Flight Deck keeps one
usage log: local files, one JSON line per event, one file per day, in
`logs/usage/` in the app folder. Every part of the platform writes to it
through one standard-library module (`skills/view-kit/scripts/usagelog.py`)
shared by the server and `pa`. It is on by default, and
`OMNIGENT_SLIM_USAGE=0` turns it off. `logs/` is gitignored and setup's
updates skip it. *Geoff wants to understand how the whole platform is used,
mostly while testing, with no remote storage available. Plain files work
offline, from a ZIP, with no service, and can be aggregated or sent anywhere
later. One writer means one set of rules, whoever writes. Skipping the folder
in updates (D-111) is what lets the log outlive every update.*

**D-123 · 2026-11-21 · Claude.** The log is fed from what upstream already
instruments, not from new instrumentation: upstream's telemetry `emit()` is
teed into it (before upstream's own opt-out, which stays off), the web app's
upstream analytics events reach it through a host sink of ours, and the
runner's existing `PostToolUse` observer adds one line per tool call. A line
uses upstream's telemetry field names, and `pa usage pack --shape upstream`
writes upstream's gateway records. *The production team will run upstream
Omnigent, whose telemetry already has an event set and a wire format;
matching them means our logs and theirs can be read by the same pipeline, and
when upstream adds an event we get it free. The web app was already
instrumented for a host sink that upstream never installs standalone.*

**D-124 · 2026-11-21 · Claude.** What a line may hold is enforced by the
writer, not left to each caller: numbers, yes or no, and short strings with no
spaces (ids, status words, file names). Anything else becomes `<text N>`,
keeping only its length. Paths are made relative to the app or home folder.
A fingerprint level hashes names too, except a fixed vocabulary. `pa usage
check` re-reads every line by the same rules, and a pack leaves out any line
that fails. *Work data must not leak through a log, and a rule each caller
has to remember will be forgotten once. "Ids and words, never sentences" is
the rule the app already uses for direct actions (D-11, D-12), and it keeps
the log useful for counting while making content structurally impossible.*

**D-125 · 2026-11-21 · Claude.** Event names are `area.action` in lower case,
from a fixed set of sources (`server`, `web`, `pa`, `skill`, `tool`, `eval`).
Every `pa` command logs itself (`pa.<command>` with its ids, exit code and
time), every change through a slim route logs itself (Hangar actions by name,
others as `api.slim_write`), and reads are not logged. Skills write their own
events with `pa log` only for moments `pa` cannot see. *Skills already do
their work through `pa`, so logging `pa` covers every workflow without
touching a skill; logging reads would bury the signal under the app's
polling.*

**D-126 · 2026-11-21 · Claude.** An eval trial is tagged (`pa usage eval
start <suite> <task> <trial>`, or `OMNIGENT_SLIM_EVAL`), and its lines go to
`logs/usage/eval/<suite>/`, left out of summaries unless asked for. The
routing suite's code graders read a trial's lines: the skill loaded, whether a
thread was briefed, whether a run started, failed turns. *The testing plan
(AV-6) grades routing by what the agent did; the log records exactly that, so
graders need not parse transcripts. Keeping trials apart keeps real use
readable and lets eval output be deleted on its own.*

**D-127 · 2026-11-21 · Claude.** Until there is a server, a log leaves a
machine only as a pack a person makes and carries: `pa usage pack` writes one
dated, compressed file to the Desktop, re-checking every line, optionally
fingerprinted. A future remote exporter implements the same interface
(`Exporter.send(batch)`) in upstream's gateway shape, and must be switched on
by a person; the offline guard is unchanged until then. *Nothing reaches the
internet at runtime (CLAUDE.md); a file a person moves is the only way out
that keeps that true, and an exporter interface fixed now means the server
can come later without changing the log.*

**D-157 · 2026-11-21 · Geoff.** Usage logs stay out of the repo's git
history for now ("not yet"). Each machine keeps its own `logs/usage/`
(gitignored), and a pack is carried by hand when wanted. Answers UL-1. *Git
history is permanent; there is no need yet to put test logs in it.*

**D-158 · 2026-11-22 · Claude.** UL-2 and UL-3 are settled loosely, without
asking, and either can change whenever it matters. Packs keep names as
written by default; `pa usage pack --fingerprint` is there for a pack that
leaves the work Mac. The numbers are read with `pa usage summary` for now;
a Usage page in the Hangar gets built only when someone wants it. *Geoff
asked not to be held up by low-stakes choices. Both are one flag or one page
away from changing, so nothing is locked in.*

## Initiatives, artifacts and templates

Spec: [initiatives-and-templates.md](initiatives-and-templates.md). Geoff
asked on 2026-11-21 for a template data model and an initiative registry with
ids that tie artifacts back to a shared representation of the intent, run by
the project setup skill and extended by the hero skills. The two questions this raised (IN-1, IN-3)
were settled as build choices, D-155 and D-156; these are the choices made
while building.

**D-138 · 2026-11-21 · Claude.** An initiative is identified by `id`, `ini_`
followed by a bare 32-character UUID, and `key`, the slug its card file is
named by; both are set on the first write and never change, while the name
can. Artifacts are identified the same way with `art_`. Commands find an
initiative by id, key or name. *Names were the only key, so renaming a
project broke every link and dataset that named it; upstream's project id is
a bare UUID, so production can keep ours as they are, and the prefix lets an
agent tell the two kinds apart in a sentence.*

**D-139 · 2026-11-21 · Claude.** A template is a folder with a
`template.json` of one of three kinds: `markdown` (a `template.md` and a list
of sections, each with an id, heading, owner stage and guide, plus optional
frontmatter fields), `records` (schemas and view-kit views) or `page` (one
self-contained HTML file). Each has an id, a whole-number version, stages and
an `out` pattern. Templates live in the workspace's `templates/` and in a
workflow's own `templates/`; the older artifact pages are read as `page`
templates. A workflow's work product may name its template, and `pa check`
fails if it does not exist. *Geoff named two kinds; the existing artifact
pages are the third, and leaving them out would split the Library from the
model. One manifest means one check and one Hangar shelf later.*

**D-140 · 2026-11-21 · Claude.** An artifact says which initiative it belongs
to in a stamp inside the file (markdown frontmatter, a JSON `artifact` block,
an HTML `pa-artifact` script), with its template, stages, status, maker and
the artifacts it was made from. The registry is assembled by reading the
files (`pa artifacts`). Views drawn from a dataset are renditions of it. The
person's `context/` files, and files that cannot hold a stamp, are listed on
the initiative's card instead and never written into. *A stamp travels with
the file and cannot fall out of step with a central list (the D-121
reasoning); the person's documents are linked, never changed (D-129). This
was IN-2 in the design and is a build choice, not a product one.*

**D-141 · 2026-11-21 · Claude.** An artifact may be loose, with no
initiative, and be adopted later. An artifact's stage is a list of tags,
never a gate, and an initiative's stage state is read from its runs and
artifacts, never stored. *The lifecycle research thread found discovery and
delivery running at once and work looping back; a hero skill used on its own
must still be able to record what it made.*

**D-142 · 2026-11-21 · Claude.** The hero skill contract: find the initiative
first (never create one; the lifecycle skill does), read what exists, start
documents from templates and stamp everything, put evidence, questions,
decisions and ready checks in the registers, write only the intent
document's sections its stage owns and suggest changes to the rest, and
extend only in its own records and templates. Decisions in the registers are
superseded, never edited, and `pa set` refuses to edit one. *Skills from
different authors, including ones built in the Hangar, extend one shared
model; without a contract the first two to touch the same initiative would
overwrite each other.*


**D-155 · 2026-11-22 · Claude.** An initiative is a project with a goal: one
record, the card that `pa project` writes, with no separate layer above it.
Settles IN-1 without asking. Easy to change: if one initiative ever has to
span several projects, add a `parent` key to the card. *Geoff asked not to be
asked low-stakes questions (2026-11-22); this reuses D-97 and adds nothing
for a PM to learn.*

**D-156 · 2026-11-22 · Claude.** The shared representation of an
initiative's intent is its intent document (judgment, sections owned by
stages) plus four registers (evidence, open questions, decisions, ready
checks). Settles IN-3 without asking. Easy to change: both are templates,
so their sections or record types can change without touching a command.
*It is what the lifecycle research found missing (evidence still attached
from research to intent), and Geoff asked for loose calls over questions.*

## Hero skills and the lifecycle

Spec: [lifecycle-research.md](lifecycle-research.md) and
[skill-taxonomy.md](skill-taxonomy.md). Geoff answered HS-1 to HS-5 on the
walkthrough on 22 November (archived in
[decision-artifacts](../decision-artifacts/2026-11-21-hero-skills-and-lifecycle/)).

**D-148 · 2026-11-22 · Geoff.** The hero-skill set is five arcs, two moves
and one companion. Arcs: problem discovery, intent shaping, PRD to
dependencies, Engage owners and Deliver. Moves, offered on any artifact:
Review and Decide. Companion: the feature lifecycle skill (D-129). PRD to
dependencies is the multi-stage arc: Specify (the catalog), Map (the board)
and Choose (analysis of alternatives with scope and delivery levers, then a
phased roadmap), and the person moves between them freely. The delivery arc
is called **Deliver**, not delivery status: status updates are one part of
it, with the rest of delivery work beside them. Engage owners runs each
chosen team's onboarding, with the agent's reach set per step by who answers
(self-serve, another agent, a person). *It splits skills by the person's goal
and by the agent's stance, the two lines the research supports, and merges
only steps that share both; Geoff: "PRD to dependencies will be complex and
multi stage, including the analysis of alternatives", and delivery is more
than statusing.*

**D-149 · 2026-11-22 · Geoff.** Each skill has a suggested path plus a few
checkpoints that always hold, never a fixed sequence. Completing every
component matters more than the order: the person can flip between a
skill's components, leave and come back, work on another lifecycle phase in
between, and run the same initiative through every phase again in repeated
loops. *Fix the ritual, free the content; Geoff: "completion of all
components matters more to me than enforcing a sequence".*

**D-150 · 2026-11-22 · Geoff asked, Claude chose.** Discover and Learn are
one stage, Discover: post-launch feedback is a source for problem discovery,
not a stage of its own. The stage list aligns with the arcs of D-148, one tag
per arc: Discover, Shape, Specify, Engage, Deliver. Specify covers PRD to
dependencies' three parts (Specify, Map, Choose); Decide leaves the list and
becomes a move. Stages stay tags, never gates (D-141), and Deliver loops back
to Discover. Refines the stage list in `lifecycle.json`. *Geoff: "Discover and
learn should be the same thing ... the answer here needs to align to the
answer to decision 1". The one job Learn named, checking shipped outcomes
against the intent's success measures, is kept as a post-launch focus of
problem discovery so it is not lost.*

**D-151 · 2026-11-22 · Geoff.** Evidence, open questions, decisions and
ready checks live on the initiative, shared by every skill: the four
registers built as `pa register` (D-141, D-142). Skill datasets keep their
own records and link to these by id. *One place for the why: a decision made
while shaping must be visible to the dependency board.*

**D-152 · 2026-11-22 · Geoff.** The first widgets and templates to build are
the five shared ones (evidence chip, open-question card, decision record,
ready checklist, initiative header) and the analysis-of-alternatives
worksheet, then the per-skill additions. The Decide move and the worksheet's
commit step use the reusable decision brief skill being built in its own
thread, so every complex decision has one layout. The template redesign
stays parked; this sets the order, not the look. *They show the shared
registers every skill uses, and Geoff finds the alternatives worksheet the
most interesting piece; one brief layout avoids each skill reinventing it.*

**D-153 · 2026-11-22 · Geoff.** A workflow may say what kind of skill it is
with one optional `tier` field in `workflow.json`: companion, arc, move or
kit, as defined in [skill-taxonomy.md](skill-taxonomy.md). The app reads it
to place the skill (arcs in the Library, moves as launchers on artifacts,
companion and kit out of sight). It is kept loose: a workflow without it
counts as an arc, an unknown value is a warning in `pa check`, never a
failure, and nothing else is typed by it. Answers HS-6. *Geoff: "as long as
the terms are defined somewhere; but don't make things brittle with over
typing". Without the field the app guesses, and a move built in the Hangar
would show as a Library card.*

## Backfilled

Decisions Geoff made on 20 and 21 November that were acted on but never
logged. Recorded on 21 November from the walkthroughs and threads where he
made them, with the date he made them.

**D-100 · 2026-11-21 · Geoff.** The work Mac gets Flight Deck as a ZIP of the
whole repository downloaded from GitHub, unzipped, and set up by running one
script. The script must fail in ways that say what broke and what to send
back. A `curl` command is fine only if a person runs it, with instructions a
non-technical PM can follow. *The work Mac blocks cloning repositories outside
the company's own namespace, and the people setting it up are not
engineers.* Not built yet: `start.sh` detects a quarantined copy, but the
one-step setup script is still to come.

**D-101 · 2026-11-21 · Geoff.** When a session is open in several browser
tabs, one tab is the active canvas and the others offer "Use this tab". The
canvas is not mirrored between tabs. *One active tab is enough for a demo, and
mirroring the page's state would be a lot of machinery for no visible gain.*

**D-102 · 2026-11-21 · Geoff.** The sidebar shows the Product Aviator emblem
with the name as text beside it, at the top left. The new-session screen has
no logo and no heading. *The full logo would be acceptable, but its spacing
and alignment were poor at sidebar size.*

**D-103 · 2026-11-21 · Geoff.** The Dock launcher uses icon A (the current
emblem), and it is pinned to the Dock (`scripts/make_dock_app.sh
--add-to-dock`). *One click to start the demo on the work Mac.*

**D-104 · 2026-11-21 · Geoff.** In a document, the main agent's behaviour
depends on how it is asked: "make a change" edits directly (the edit is
highlighted until seen), "propose changes" makes tracked suggestions. Every
other agent only suggests (D-26). *The person stays in control of what lands,
without making every small fix a suggestion to accept.*

**D-105 · 2026-11-21 · Geoff.** Every question card put to him includes a
"Something else" option. Extends D-32. *The real answer is often not one of
the options offered.*

**D-106 · 2026-11-21 · Geoff.** Two choices the agent made overnight stand
(confirming them under D-27): a view is redrawn by rewriting its HTML file,
and the reviewed and locked states of a record belong to the person, never
set by the agent. *Rewriting the file is what makes old artifacts and the
canvas reload work; reviewed and locked are the person's judgment.*

## Open

- Progressive complexity (from D-54): how a workflow shows less at first and
  more on demand, to the person and to the agent. Not designed yet.
- The intent graph's level of detail is deliberately held (D-98).
