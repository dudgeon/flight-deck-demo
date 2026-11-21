# The Hangar: builder mode

Status: designed, decided and built. Decisions D-39 to D-47, D-51, D-52,
D-56 to D-59, D-63 to D-67 and D-71 to D-75 (where each stands:
[decision-index.md](decision-index.md)). All three slices are built: the
look-around Hangar, the person builder (edited in place with the Aviator
pop-over) and the scenario and workflow builders, plus pictures for people.
"Fly this" demos (D-76 to D-81) are in an open pull request. Clickable mockup
and the decision walkthrough: https://claude.ai/artifact/9M4JGs5WuxigJz1jiJ9QVr

## What it is for

Product Aviator is used in two ways. Most people **fly**: they do product work
with the agent and meet colleagues, workflows and views as finished things.
A few people **build**: they define who can be called into a conversation,
what kinds of work exist, what the views look like and what stories the demos
tell. Until now building meant editing files in the repo. The Hangar brings
it into the app, for two reasons:

- Other PMs will write scenarios (D-30) and should not need to learn the
  file formats or the repo.
- Building by hand breaks things: a workflow that names a person who does not
  exist, a screenplay that shows a view that was renamed. Making each build a
  guided workflow puts the constraints before the mistake.

## Three ideas

1. **Everything in the Hangar is already a file.** The roster, workflow
   folders, view specs, screenplays and starters are on disk and have checks.
   The Hangar is a way of seeing and changing them. No database, no new
   format.
2. **Building is itself a workflow.** New person, new workflow, new scenario
   and new skill each run as a guided session: steps, a form in the canvas, a
   check, a trial, a publish. They reuse the step card, the view kit and the
   chat.
3. **Nothing changes for anyone until Publish.** Work happens on a draft
   copy. Publish runs the checks, shows what changes and who is affected,
   keeps the previous version and swaps the files in. Running sessions keep
   what they started with.

## The two modes

| | Flying | Hangar |
|---|---|---|
| Frame | Navy sidebar, plain work area | Paper sidebar with a dashed edge, drafting grid, a band across the top |
| Sidebar lists | Sessions and projects | Shelves: Overview, People and agents, Workflows, Views, Scenarios, Skills, Starters, Frameworks, then Drafts and History |
| Color | Navy frame; magenta, amber, red keep their meanings | One color of its own (teal in the mockup), used for nothing else |
| A person | A colleague with a mark | A file: fields, a brief or script, where they are used |

**Switching.** A quiet dashed "Hangar" item at the foot of the sidebar, above
the user's name. The band and the sidebar foot both carry "Back to flying".
A participant turn, the Session panel's workflow card and a Library card may
link to themselves in the Hangar, but only as a small wrench icon button with
no words, visible on hover or keyboard focus (D-41). Nothing about the Hangar
may draw the eye in a screen recording of a demo.

## The shelves and what an inspect page shows

Every shelf is a grid of cards drawn the way the thing appears to a user,
with a health chip and "used in" counts. Every inspect page has two halves:
how it looks when flying, and what it is made of, with the file path. Whatever
it uses and whatever uses it is a link.

- **People and agents.** The mark, name, role, kind, stand-in label, how they
  answer (live from a brief, or from a script), what they are called for,
  their skills, the workflows that may call them. A sample turn as it appears
  in the chat.
- **Workflows.** Steps as the Session panel shows them, the views rendered
  from sample data, who can be called, how people start it (starters,
  launchers), the record types, its scenarios, its checks.
- **Views.** Every view spec and standalone template, rendered, grouped by
  layout, each with the workflows that use it.
- **Scenarios.** The screenplay as plain text beside the preview player, the
  cast, the sample data, whether it plays through.
- **Skills, Starters, Frameworks.** The file, what it is for, what uses it.

## The nine moves

| Move | The builder | Runs on |
|---|---|---|
| Discover | Uses the sidebar switch or a wrench on a thing | A `/hangar/...` route |
| Browse | Picks a shelf | A read-only endpoint listing the folders and how they refer to each other |
| Inspect | Opens one thing | The files, plus `pa render` over sample data |
| Create | Starts a guided build: from something similar, from a description, or from a session just had | Builder skills, written like `scenario-builder` |
| Edit | Presses Edit; built-ins offer "Duplicate to change" | A drafts folder; the collab editor for wording |
| Check | Nothing: checks run on every change | `pa check`, `pa who --check`, extended across things |
| Try | Plays the preview, or opens a trial session | `pa preview`; a normal session pointed at the draft, with a "Trial" strip |
| Publish | Reads the summary and presses Publish | Copy into place after a snapshot |
| Go back | Opens History and presses Restore | Dated snapshot folders |

## What prevents breaking changes

- **Drafts only.** The live thing is read-only in the Hangar.
- **Pick, do not type.** People, views, record types and layouts are chosen
  from what exists. Ids are generated from names.
- **Fixed shapes.** A person needs a name, kind, way of answering and a
  call-for line; a real person is always a stand-in. A workflow has three to
  six steps and uses the standard layouts.
- **Used-by guard.** Renaming, removing or reshaping something lists what
  depends on it and is blocked until each is updated or replaced.
- **Built-ins are locked.** The kit and reference workflows can only be
  duplicated.
- **Publish gate.** Disabled while a check fails; a scenario must play
  through on its own (D-44).
- **Always a way back.** Every publish keeps the one before it.

## The guided person build (the reference build)

Steps: Who they are, How they answer, Where they can be called, Try them,
Publish. Aviator asks one thing at a time and drafts the brief; the form in
the canvas is the participant file. Kind = Person forces the stand-in label.
The id is derived and checked for uniqueness. "Where" is a pick list of
existing workflows. "Try" asks the draft a real question. Publish shows the
checks, the files that change (the new roster file, each workflow's
`scenario.json`), and who is affected.

**Since D-63:** the build happens on the person's own page rather than in a
flying session. The steps above are still the order Aviator follows when you
ask it in the pop-over, and the build-person skill still works from any
session. Casting (D-65) and skills (D-66) are fields on the page.

## Workflows and scenarios split (D-42)

A workflow folder (`skills/<name>/`) keeps `SKILL.md`, `schemas/`, `views/`
and the manifest. A scenario is its own folder
(`workspace/scenarios/<name>/`, built in D-67) with a manifest naming the workflow or
workflows it runs, the cast (roster ids), invented data and `script.md`. The
seven existing demos move there as each workflow's first scenario. Places
this touches: `pa check` and `pa preview` (they read fixtures and script
relative to one folder today) and the Session panel's workflow card (progress
files are keyed by scenario id).

## New pieces

- Web: a `/hangar` route, a body class that swaps the frame, the second nav
  list and band, one token family for the Hangar color in `design/tokens.json`.
- Server: a read-only endpoint modelled on `slim_library.py`.
- `pa`: `draft`, `publish`, `history`, `uses`.
- Skills: `build-person`, `build-workflow`, `build-scenario`, `build-skill`.
  Built so far: `build-person`, and `scenario-builder` in place of
  `build-scenario`.
- A "Hangar" project so builder sessions stay out of the flying sidebar.

## Build order (D-45)

1. Look-around Hangar: switch, frame, shelves, inspect pages. Read-only. **Built.**
2. Person builder: drafts, checks, trial, publish, history, used-by guard.
   **Built**; editing in place with the Aviator pop-over (D-63 to D-66).
3. Scenario and workflow builders, with the D-42 split. **Built** (D-67, D-71 to D-73).

## Flying a scenario (D-76 to D-81)

The scenario page has "◆ Fly this": a "◆ Demo · <title>" project and a real
session that plays the screenplay, canned turns word for word and `[live]`
turns answered for real. See "Flying a scenario as a demo" in features.md.

## Left for later

Sharing a workflow or scenario with another PM as one file. A second
person's approval before publish (for the production version).
