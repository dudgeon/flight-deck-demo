# Modes, runs, projects and the intent graph

Status: **design exploration, nothing built, nine decisions open.** Raised by
Geoff on 2026-11-21. The walkthrough with drawings of each option, where he
records his answers, is https://claude.ai/artifact/HRgpJURjcqasGSCmd3894d
(answers in its database, collection `answers`). When an answer is locked
there, it becomes a numbered entry in [decisions.md](decisions.md) and the
matching "Open" line below is removed. The open questions are labelled M-1 to
M-9 here so they cannot collide with decision numbers being added by other
work.

## What was asked

> Hero skills (like intent shaping) implicitly put the flight deck into their
> given "mode": the sequence of tasks will show, sometimes artifacts will
> show. Responses from the agent in that mode should be attributed to that
> mode. A user can always back out of a mode ("pause intent shaping, let me
> come back to that later"). A project should also show which in-flight
> workflows/modes there are and allow a user to come back to them. We need to
> address what a project is and what granularity of intent it relates to. I
> think most projects are a given in-market goal, like a feature or
> enhancement to ship. They will need some connectivity to parent or sibling
> features. We will likely need some representation of the graph of various
> intents. This does not need to be user facing.

## Vocabulary

Five words, deliberately different things.

| Word | What it is | Exists today |
|---|---|---|
| **Workflow** | A kind of work, built in the Hangar (`skills/<id>/workflow.json`). | Yes |
| **Run** | One workflow started on one subject. It has a step, a state, its dataset and a where-we-left-off note. It outlives the session it started in. | Half. The dataset's `flow` block and the `progress/` file hold the steps and current step; there is no state, no note and no link to a project. |
| **Mode** | What a session is in while a run has the floor. It is what the person sees: a strip, a rail, the steps. | No. The Session panel's workflow card (D-16) is the only sign. |
| **Project** | The goal the runs serve. | Only as a folder with sessions (Workspace, Hangar, one per flown demo, D-59 and D-76). |
| **Intent graph** | How goals relate to each other, kept behind the scenes. | No |

"Hero" describes how a skill is presented in the Library. Whether something
makes a mode depends on it being a workflow, not on being featured (proposed;
see "Smaller calls").

## Why this needs designing

- **A mode is invisible most of the time.** The workflow card is in the
  Session panel, which is a popover whenever the canvas is open (D-14).
- **A mode is not a participant.** A participant is *who* is speaking; a mode
  is *what work* a turn belongs to. Aviator is still Aviator in a mode, and
  Risk Review can speak inside one. Attribution to the mode must sit beside
  participant attribution (D-17), not replace it.
- **The app cannot understand "pause".** With no Claude API (D-02), only the
  agent can interpret the sentence. The agent must record the pause somewhere
  the app reads, the way `pa flow` writes the progress file today.
- **Runs outlive sessions.** A paused intent shaping must be resumable next
  week, possibly in a new session. That works only if the state is in files
  (D-07 already puts it there) plus a short note written at the moment of
  pausing.
- **Discovery happens before a feature exists.** If a project is a feature to
  ship, problem discovery (which studies a problem space and yields several
  problems) needs a home that is not a feature.
- **The four kinds of work already chain** (discovery, shaping, decisions,
  delivery; see features.md). Nothing records that chain. It lives in the
  invented fixtures.

## Proposed shape (the recommended options, for orientation)

None of this is decided. It is written down so the production team can see
the reasoning behind whichever answers are locked.

**Modes.** A one-line strip on the message box names the mode and step and
carries Pause. A thin rail runs beside every turn made in the mode, with a
marker in the transcript where it starts, pauses and resumes. Side questions
are answered outside the rail and do not end the mode. One mode has the floor
at a time; starting a second pauses the first and offers to return.

**Leaving.** Three endings that must not be confused: pause (come back),
finish (the work product is written) and stop (not worth pursuing; data
kept). Pause is said in plain language or pressed; the agent records it and
writes a "where we left off" note (done, pending question, who has not
answered). An unanswered view in the chat freezes as "Paused" instead of
"Answered" (extends D-53). Only stop asks for confirmation.

**Runs and resuming.** Run states: working, needs you (amber, D-50), paused,
waiting on someone, finished, stopped. The project page leads with an "In
flight" section, one card per run with Resume. Resume reopens the original
session if it still exists; otherwise a new session starts from the note and
the dataset.

**Projects.** A project is one in-market goal: a feature or enhancement that
ships and then ends. It belongs to one **area**, a lasting problem space
where problem discovery and shared context live. A problem marked "worth
solving" in an area can start a goal project that carries the problem brief.
The project page shows a "part of" trail and a Related card (parent,
siblings with their state, what this goal needs). Area context is inherited
by its goals and labelled with where it came from (extends D-15).

**Intent graph.** A node per area and goal with `part-of`, `came-from` and
`needs` links, and each run attached to its goal. The graph points at
datasets and does not copy their records. Stored as one small file per
project and assembled on demand, so it works from a ZIP (as with the Hangar,
D-52) and can later be replaced by a service.

## What it would touch, if the recommended options are chosen

| Area | Change |
|---|---|
| `pa flow` (`skills/view-kit/scripts/pa.py`) | New states and `--pause`, `--resume`, `--stop` with `--note`; the progress file gains `state`, `note`, `session`, `project`, `parent_run`. |
| Workflow skills | One shared rule (in `view-kit/SKILL.md` and `workspace/CLAUDE.md`): how to recognise pause, finish, stop and a side question, and what to write. |
| Chat (`web/src/components/chat/`) | The mode rail and start/pause/resume markers; "Paused" state on `ChatViewBlock`. |
| Composer | The mode strip, with Pause as a direct action (D-11, D-12: a state change, so allowed). |
| Project home (`web/src/projectHome/`) | "In flight" section above the sessions board; trail and Related card. |
| Projects | A folder per project (as demos have under `workspace/demos/`), with a small manifest naming its goal, level, parent and links. |
| Server | A read-only endpoint listing runs per project, modelled on `slim_library.py`. |
| Hangar | Workflow pages show how the mode looks; no new shelf. |

## Open decisions

Each is put to Geoff in the walkthrough with drawings of every option.
"Recommended" is the agent's recommendation, not a decision.

- **M-1 · How a mode shows.** A strip on the message box (recommended), a
  band under the header, or only the Session panel card as today. *Must stay
  clearly lighter than the Hangar's frame change (D-40).*
- **M-2 · Marking replies as the mode's.** A rail beside the mode's turns
  with start, pause and resume markers (recommended), a label on every reply,
  or the mode speaking as its own character. *Has to coexist with participant
  marks.*
- **M-3 · Side questions during a mode.** Answered outside the rail while the
  mode stays on (recommended), everything counts as the mode until paused, or
  the agent asks each time.
- **M-4 · Leaving a mode.** Say it or press it, three endings, a
  where-we-left-off note, only stop confirms (recommended); say it only, with
  no button or note; or confirm every exit.
- **M-5 · A second mode in the same session.** One at a time with a way back
  (recommended), nested inside each other, or several at once.
- **M-6 · Finding what is in flight.** An "In flight" section on the project
  page plus a needs-you count in the sidebar (recommended), runs listed in
  the sidebar, or only by asking Aviator.
- **M-7 · What a project is.** A goal that ships, inside an area that lasts
  (recommended); projects at any level, nested freely; or flat folders as
  today. *Geoff's stated lean is the in-market goal; the area level is the
  proposed answer to where discovery lives.*
- **M-8 · Showing a project's relatives.** A "part of" trail and a Related
  card, with area context inherited (recommended); a tree in the sidebar; or
  nothing on screen, with Aviator speaking up when a relative matters.
- **M-9 · How detailed the intent graph is.** Areas and goals pointing at
  datasets (recommended); down to every requirement and decision; or only a
  parent line per project for now.

### Smaller calls the agent will make unless Geoff objects

Listed on the walkthrough's "Smaller calls" tab.

- Every workflow makes a mode, not only the ones featured in the Library.
- A mode has no color of its own; the rail and strip use the existing
  "agent at work" token and the workflow's name.
- Starting a mode never asks first; the start marker carries a quiet Undo.
- Resume returns to the same session when it exists, else a new one; Resume
  also offers "in a new session".
- A run belongs to one project; work that spans goals is a run in the area.
- Demo projects (D-76) stay as they are, and runs show in them the same way.

### Not yet explored

- What an area page looks like, and whether "area" is the right word for
  Geoff's company.
- A project's own life cycle (idea, shaped, specified, in delivery, in
  market) and whether the project page shows it. The intent framework's depth
  (D-34, D-54) is a candidate for the early part.
- How a change upstream reaches the person: a sibling slipping, a parent
  intent being reworded. The Inbox (D-68) is the likely place.
- How much of the parent chain an agent is given when a run starts. This is
  the agent half of progressive disclosure (the open item from D-54).
- Whether a record in one goal's dataset may point at another goal (the seam
  left by M-9's recommended option).
- More than one person on a project, and who may pause or stop a run.
- How projects and the graph map onto what upstream Omnigent has (projects,
  saved workflows, tasks), so the production team can keep the interfaces.
