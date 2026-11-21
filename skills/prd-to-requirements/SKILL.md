---
name: prd-to-requirements
description: Turn a PRD or other requirements document into a structured catalog of testable requirements, shown as an interactive table the user reviews, edits and locks. Use when the user asks to catalog, extract, structure or review the requirements in a document, or says "PRD to requirements".
---

# PRD to requirements

You turn an unstructured document into a dataset of requirements and show it in
the canvas with the view kit. You never write HTML for this. You change data
with the `pa` command and the views redraw themselves.

## Setup (once per session)

`pa` lives in the `view-kit` skill, next to this one:

```bash
PA="python3 <this skill's folder>/../view-kit/scripts/pa.py"
```

Use `python` if `python3` is missing. All paths below are relative to the
session's workspace folder. `SKILL_DIR` means this skill's folder.

## 1. Find the document

Use the file the user named. Otherwise look in `context/` for a PRD. If there
is none and the user wants a demo, copy the invented one:
`mkdir -p context && cp scenarios/prd-to-requirements/fixtures/allowances-prd.md context/`.
Pick a short kebab-case slug for the initiative, e.g. `allowances`.

## 2. Ask how to catalog it (skip if the user already said)

```bash
$PA render SKILL_DIR/views/scope-form.json --host chat --out artifacts/<slug>-scope.html
```

Open it with `ui_open_file` and say one line: "Three quick choices before I
start, in the canvas." Then stop and wait. The answers arrive as a message
that starts with "Catalog setup:". If the user says to use your judgment,
carry on with the defaults.

## 3. Build the dataset

```bash
$PA init data/<slug>.json --title "<Initiative name>" --meta source=<path of the document>
$PA render SKILL_DIR/views/catalog.json --data data/<slug>.json --out artifacts/<slug>-requirements.html
```

Open `artifacts/<slug>-requirements.html` now, while it is empty, so the user
watches it fill. Then add records in batches of one capability at a time:

```bash
$PA add data/<slug>.json --json '[
 {"id":"C-1","type":"capability","title":"Set an allowance"},
 {"id":"R-01","type":"requirement","parent":"C-1","title":"...","statement":"...",
  "kind":"Functional","priority":"Must","source":"PRD section 3.1",
  "acceptance":["..."],"confidence":5,"status":"ready"}
]'
```

The record shapes are in `schemas/records.json`. Rules for good records:

- `title` is one line written as an outcome. `statement` is one or two
  testable sentences. Keep the document's own words where they are clear.
- `source` says where it came from, so the user can check it.
- `confidence` is 1 to 5: how clearly the document states it.
- `status` is `ready` normally. Use `needs-you` plus a `question` when the
  document contradicts itself or leaves out something only the user can
  settle. Ask the question in one or two plain sentences.
- Never set `reviewed` or `locked` yourself. Those are the user's.
- Never edit the dataset file by hand. Use `add` and `set` only.

Every `add` and `set` redraws the open view. You do not need to call
`ui_open_file` again.


## Show where the work is

The Session panel shows this workflow's steps and how far along it is. Tell it
as you go. Right after `init`:

```bash
$PA flow data/<slug>.json --scenario SKILL_DIR
```

Then `$PA flow data/<slug>.json --step <number> --note "<what is happening, a few words>"`
when you move to another step, and `--done` when the workflow is finished.
The steps: 1 read the document, 2 agree how to catalog, 3 build the catalog, 4 the user's review. The count of items done updates itself.

## 4. Report

Two or three lines in chat: how many requirements in how many groups, how many
need the user's answer, and what they can do in the canvas (open a row, change
a priority, approve, lock, send back). For a compact picture in the canvas,
`$PA render SKILL_DIR/views/summary.json --data data/<slug>.json --out artifacts/<slug>-summary.html`.

## 5. Act on what the canvas sends

The view puts text in the chat box and the user presses Send. Handle each:

| Message from the view | What you do |
|---|---|
| "Canvas action on data/<slug>.json:" then lines like `- R-07 status = reviewed` or `- R-02 locked = true` (`approve`, `approve-lock`, `approve-all`, the lock box) | These arrive without the user pressing Send, and only ever carry state. Apply each line with `$PA set data/<slug>.json <id> field=value` exactly as written. Do not reply unless something fails. |
| "Save these edits ..." (`save-edits`) | Apply each line with `$PA set data/<slug>.json <id> field=value`. Booleans and numbers are bare (`locked=true`). Confirm in one line. |
| "Rework requirement R-07 ... My note: ..." (`return`) | Rewrite that record from the document and the note, set `status=ready` and clear `return_note` with `return_note=null`. |
| "About requirement R-03 ...: <answer>" (`answer`) | Update the record with the answer, set `status=ready`, clear `question` with `question=null`. |
| "Split requirement R-06 ..." (`split`) | Rewrite the original as the first part with `set`, then `add` the other parts as new records under the same parent. |
| "Mark every requirement that is ready as reviewed." (`approve-all`) | `$PA set data/<slug>.json --where type=requirement --where status=ready status=reviewed` |
| "Map the platform dependencies ..." (`map-dependencies`) | Hand over to the `requirements-to-dependencies` skill with the same dataset. |

Before you rewrite a record the user may have been editing, read their unsaved
edits from the canvas with `canvas_eval` and `PA.pending()`, and keep them.

Changing a requirement's content marks anything derived from it as stale. That
is intended: it tells the user what to look at again.

## Without Omnigent

If `printenv OMNIGENT` prints nothing, do the same steps and tell the user to
open the HTML file in a browser. The buttons then show what they would send.
