---
name: scenario-builder
description: Create or change a workflow (a kind of work, with its dataset shape and views) or a scenario (one scripted demo of a workflow, with invented data and a click-through script) for the product workspace, as Hangar drafts checked and previewed with `pa`. Use when the user wants to prototype a new workflow or template, add a stage to an existing one, or produce a standalone demo of how an agent and a person would work through a task together.
---

# Scenario builder

A scenario is one kind of work a person does with the agent, packaged so it
can be shown three ways from the same files: as a standalone click-through
with invented data, live in Omnigent with a real agent, and later against real
systems. `prd-to-requirements` and `requirements-to-dependencies`, next to
this skill, are the reference examples. Read one before you start.

```bash
PA="python3 <this skill's folder>/../view-kit/scripts/pa.py"
```

## Workflows and scenarios (D-42)

A **workflow** is the kind of work; a **scenario** is one scripted run of it
with invented data. They live apart, so one workflow can have several demos:

```
skills/<workflow>/                 (shipped)  or  .claude/skills/<workflow>/ (built in the workspace)
  SKILL.md            what the agent does, step by step, and what it does for each button
  workflow.json       the manifest: workflow (its id), title, summary, inputs, dataset, views,
                      steps, progress, participants (who may be called), work products
  schemas/records.json  the record types the workflow reads and adds
  views/*.json        view specs (see the view-kit skill)
  references/         briefs for sub-agents, if it uses them

scenarios/<scenario>/              (in the workspace)
  scenario.json       scenario (its id), title, summary, workflow (the id it runs),
                      participants (the cast), fixtures, script, opening (the first line)
  fixtures/           an invented dataset in its finished state, plus documents the work produces
  script.md           the screenplay: canned turns, and live ones marked [live]
  context/            invented documents the story starts from (a PRD, a platform map)
  cast/<person>.md    what each person in the cast knows in this story
```

A scenario you build, a demo you fly. "Fly this" in the Hangar makes a
"◆ Demo · <title>" project with its own folder: `context/` is copied in, the
dataset starts from the fixture, each cast member's file gets their
`cast/<id>.md` notes, and a session opens with the `opening` line ready to
send. The agent there plays the script with `pa demo next`. Keep `title`,
`summary`, the cast and the `workflow` id tidy: the Library lists demos from
them. Workflow skills never copy anything out of `scenarios/` themselves.

The first scenario of a workflow usually shares its id. Paths in `fixtures`
and `script` are relative to the scenario folder.

## Build in the Hangar: drafts, never the live folder

Others fly what is live, so you never edit `scenarios/` or `.claude/skills/`
directly. Work on a draft, check it, and publish when the user says so (the
Publish button in the Hangar, or `pa publish`). Publishing keeps the version it
replaces, under History.

```bash
$PA draft scenario <id>                                     # a draft of a live scenario
$PA draft scenario --name "Fraud rules review" --duplicate document-review
$PA draft scenario --name "Card freeze demo" --workflow document-review   # a blank one
$PA draft workflow --name "Policy review" --duplicate document-review     # a new workflow from a copy
$PA draft workflow --name "Vendor check"                    # a blank workflow that passes the checks (D-169)
$PA draft workflow document-review                          # change one (a shipped one becomes a workspace copy)
$PA draft scenario <id> --set title="..." --set participants=risk-review,mara-okafor \
  --file script.md=/tmp/script.md                           # change fields and whole files
$PA draft scenario <id>                                     # checks, and what changes
$PA publish scenario <id> --summary "one line"              # only with the user's go-ahead
```

The draft is a folder under `.hangar/drafts/scenarios/<id>/` (or
`workflows/<id>/`); you may also edit files there directly. A scenario only
publishes when `pa check` passes and its script plays through. A workflow
can't be removed while a scenario runs it (unless a shipped one of the same id
takes over again). In the app, the Hangar page for the draft is the editor and
you may be the Aviator in its pop-over: keep changes small and say what you
changed.

**Asked in a flying chat?** If this conversation did not start in the Hangar
(its first message does not say you are editing something in the Hangar),
don't build in the chat (D-168). Start the draft, then give the person its page
and stop: `[Open it in the Hangar](/hangar/drafts/scenario/<id>)` (or
`/hangar/drafts/workflow/<id>`), and say you'll be in the Ask Aviator
pop-over there. Use the id `pa` printed. Skills that are not workflows use
build-skill.

## Ask before you build

Find out, one question at a time, only what you cannot infer:

1. What does the person start with, and what do they want to end with?
2. What are the units of work? One record per what?
3. Where does the person need to look, decide or correct? Those are the
   states and the buttons.
4. Does any of it run in parallel or take long enough to need a board?

Do not ask about field names, colors or layout. Propose them and show them.
Colors come only from the design tokens (see `product-aviator-design`): a
spec names a status tone such as `ok` or `attn`, never a color.

## Design rules

- **One dataset, extended.** A scenario that follows another adds record types
  and its own `<stage>_status` field to the same dataset. It does not copy
  data into a new file.
- **Every record can move at its own pace.** Do not design a stage that
  requires all records to be finished before the next can start. Use per-record
  state, `locked` for what the person has settled, and `derived_from` so later
  work is marked stale when its source changes.
- **Views are projections.** If two views disagree it is a bug in a spec. The
  truth is the dataset.
- **Chat for the turn, canvas for the work.** Short choices, single reviews
  and summaries can go in chat with `--host chat`. Anything the person comes
  back to goes in the canvas.
- **The person sends.** Buttons put words in the chat box. Write the `prompt`
  of every action as a sentence the person would be content to have said.
- **Invented data must look invented.** Use made-up companies and people.
  Never real customer data, real internal system names or real people.
- **Start from the standard layouts.** A new layout is a change to the kit and
  needs a reason that at least two scenarios share.

## Steps

1. Start drafts from the nearest reference: `pa draft workflow --name ...
   --duplicate <nearest>` for a new kind of work, and `pa draft scenario
   --name ... --duplicate <nearest>` (then `--set workflow=<new id>`) for its
   demo. Both are renamed for you.
2. Write `schemas/records.json`: the record types, required fields and allowed
   values.
3. Write the fixture dataset as the work would look when it is about two
   thirds done: some reviewed, some waiting on the person, some still running,
   one stale, one failed. A demo of a finished job shows nothing.
4. Write the view specs. Render each against the fixture and look at it
   (view-kit skill, "Building a new view").
5. Write `SKILL.md` for the live agent. It must say what to do for every
   action id in the views.
   Give `workflow.json` a `steps` list (three to six short names for the
   stages of the work, as the person would say them) and a `progress` entry
   that says which records count and which statuses mean done. Have `SKILL.md`
   call `$PA flow` at each stage, as the reference scenarios do, so the
   Session panel shows where the work is.
6. Write `script.md`, the screenplay for the preview. It is plain markdown:
   `**You:**` and `**Aviator:**` lines for the chat, and bracketed directions
   such as `[show catalog]`, `[reveal R-01, R-02]` and `[wait]` for everything
   else. The whole vocabulary is in the view-kit skill's
   `references/script.md`. Keep it under about thirty steps.
   Mark a turn `[live]` (under its line) where a flown demo should show a real
   answer, such as a reply to something the user types in their own words.
   Write `cast/<id>.md` for each person in the cast: the facts of the story
   they need to answer a live turn, in a few bullets.
   If other agents or people take part, list their ids under `participants`
   in `workflow.json` (who may be called) and in `scenario.json` (the cast). They must be on the roster (the `participants` skill
   explains how to add one). Then they can speak in the script by name, be
   called and leave. `skills/document-review` is the example.
7. Check and preview:

```bash
$PA draft scenario <name>          # runs every check on the draft
$PA preview .hangar/drafts/scenarios/<name> --out artifacts/<name>-preview.html
```

   Open the preview with `ui_open_file`, click through it yourself with the
   `canvas_*` tools, and fix what reads badly. The preview file is
   self-contained, so the user can send it to someone or open it in a browser.
8. Tell the user what you built in three lines and what you were unsure about,
   and that it goes live when they publish the drafts (workflow first).

## Changing a scenario or workflow

Start a draft (`pa draft scenario <id>` or `pa draft workflow <id>`), change
the spec, schema, fixture or script in the draft folder, run `pa draft` again
to check, and rebuild the preview. If you
rename an action id or a field, search `SKILL.md` and the other scenarios that
list this one under `needs`.

New sessions pick up a newly published workflow. A running session keeps the skills it
started with.
