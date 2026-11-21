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
- From the modes and projects work (see
  [modes-and-projects.md](modes-and-projects.md)), put to Geoff with drawings
  at https://claude.ai/artifact/YQcb4HDRGMnn6YW82uFNZd:
  - M-12: how the director session shows a mode for the high-level
    interactions (left open by D-89).
  - M-13: where a thread opens when the person steps into it.
  - M-14: what a thread reports back to the director.
  - M-8, sent back by Geoff to be rethought as a graph, not a tree: how a
    project's connections show.
- The intent graph's level of detail is deliberately held (D-98).
