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

## Open

- Whether views should also appear inside the chat, and in what form. Geoff
  asked for the options to be laid out and mocked before deciding.
