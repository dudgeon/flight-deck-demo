# Decision log

Format: **D-number · date · who decided.** The decision. *Why.* Entries are
never edited after the fact; a later entry may replace an earlier one and says
so. "Geoff" is the product owner. "Claude" marks a choice made by the agent
while building, which Geoff later accepted as a group (D-27).

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

## Name and design language

**D-35 · 2026-11-21 · Geoff.** The fork of the Omnigent meta-harness is named
**Flight Deck**. Product Aviator stays the name of the user interface. The
repository, folders and code identifiers keep `omnigent-slim` unless Geoff
says otherwise. *He liked the name when it came up for the design direction.*

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

## Open

- Whether views should also appear inside the chat, and in what form. Geoff
  asked for the options to be laid out and mocked before deciding.
