---
name: scenario-builder
description: Create or change a demo use case for the product workspace (a "scenario"): a skill folder with a dataset shape, views, invented fixture data and a click-through script, checked and previewed with `pa`. Use when the user wants to prototype a new workflow or template, add a stage to an existing one, or produce a standalone demo of how an agent and a person would work through a task together.
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

## What is in a scenario folder

```
skills/<scenario-name>/
  SKILL.md            what the agent does, step by step, and what it does for each button
  scenario.json       the manifest: inputs, dataset, views, work products, what comes next
  schemas/records.json  the record types this scenario reads and adds
  views/*.json        view specs (see the view-kit skill)
  fixtures/           an invented dataset in its finished state, plus any documents
  script.json         the click-through: who says what, which view appears, where it waits
  references/         briefs for sub-agents, if it uses them
```

## Ask before you build

Find out, one question at a time, only what you cannot infer:

1. What does the person start with, and what do they want to end with?
2. What are the units of work? One record per what?
3. Where does the person need to look, decide or correct? Those are the
   states and the buttons.
4. Does any of it run in parallel or take long enough to need a board?

Do not ask about field names, colors or layout. Propose them and show them.

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

1. Copy the nearest reference scenario to `skills/<new-name>/` and rename it in
   `SKILL.md` and `scenario.json`.
2. Write `schemas/records.json`: the record types, required fields and allowed
   values.
3. Write the fixture dataset as the work would look when it is about two
   thirds done: some reviewed, some waiting on the person, some still running,
   one stale, one failed. A demo of a finished job shows nothing.
4. Write the view specs. Render each against the fixture and look at it
   (view-kit skill, "Building a new view").
5. Write `SKILL.md` for the live agent. It must say what to do for every
   action id in the views.
6. Write `script.json`. Step kinds: `pm` and `agent` (chat lines), `task` (the
   progress line), `doc` (open a document), `canvas` and `widget` (show a
   view), `reveal`, `status`, `restore` and `patch` (make data appear or
   change as if the agent did it), `await` with a `hint` (wait for the person
   to try something), `apply` (save their edits). Keep it under twenty steps.
7. Check and preview:

```bash
$PA check skills/<new-name>
$PA preview skills/<new-name> --out artifacts/<new-name>-preview.html
```

   Open the preview with `ui_open_file`, click through it yourself with the
   `canvas_*` tools, and fix what reads badly. The preview file is
   self-contained, so the user can send it to someone or open it in a browser.
8. Tell the user what you built in three lines and what you were unsure about.

## Changing a scenario

Change the spec, schema or fixture, run `check`, rebuild the preview. If you
rename an action id or a field, search `SKILL.md` and the other scenarios that
list this one under `needs`.

New sessions pick up a new skill folder. A running session keeps the skills it
started with.
