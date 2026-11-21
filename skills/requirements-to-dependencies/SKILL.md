---
name: requirements-to-dependencies
description: For each requirement in a requirements dataset, find the platform capabilities it depends on and the options that could meet it, shown as a board of explorations the user starts, answers and reviews. Use when the user asks to map dependencies, explore what the platform offers for their requirements, or presses "Map dependencies" in a requirements catalog.
---

# Requirements to dependencies

One exploration per requirement. Each exploration is a sub-agent that reads the
requirement and the platform map, then records the dependencies it found and
the capabilities that could meet each one. You are the orchestrator: you set up
the board, start explorations when the user asks, and act on what the board
sends. You never write HTML for this. You change data with `pa` and the board
redraws itself.

## Setup (once per session)

```bash
PA="python3 <this skill's folder>/../view-kit/scripts/pa.py"
```

`SKILL_DIR` means this skill's folder. Paths are relative to the session's
workspace folder.

## 1. Find the inputs

- **The dataset.** Use the one the user named, else the one requirements
  dataset in `data/`. If there is none, ask for it, or offer to make one with
  the PRD to requirements workflow. A demo flown from the Hangar already has
  its dataset in `data/`. For a clean run on a dataset that was explored
  before: `$PA set data/<x>.json --where type=requirement explore_status=queued`.
- **The platform map.** What the platform offers, in the user's own files.
  Look in `context/` (a flown demo has its invented map there; never copy
  one out of `scenarios/` yourself). If there is nothing to
  read, say so and ask where the capability documentation is. Do not invent
  capabilities.

## 2. Set up the board

```bash
$PA set data/<slug>.json --where type=requirement --where explore_status= explore_status=queued --no-stale
$PA render SKILL_DIR/views/board.json --data data/<slug>.json --out artifacts/<slug>-dependencies.html
```

Open the board with `ui_open_file`. Say in one or two lines that nothing has
started and that they can start one tile or all of them. Then wait. Do not
start explorations until asked.

This stage keeps its own status in `explore_status`, so it never disturbs the
`status` the requirements already carry from the catalog.


## Show where the work is

The Session panel shows this workflow's steps and how far along it is. Tell it
as you go. Once the board is set up:

```bash
$PA flow data/<slug>.json --scenario SKILL_DIR
```

Then `$PA flow data/<slug>.json --step <number> --note "<what is happening, a few words>"`
when you move to another step, and `--done` when the workflow is finished.
The steps: 1 set up the board, 2 explore each requirement, 3 the user's review, 4 summary. The count of items done updates itself.

## 3. Start explorations

For each requirement you are asked to start:

1. `$PA set data/<slug>.json <id> explore_status=working --no-stale` (the board may already show it as `requested`, meaning the user pressed Start)
2. Launch one sub-agent with the Agent tool, in the background, model
   `sonnet`. Its prompt is `references/explorer.md` with the four values at
   the top filled in. Launch up to five at a time. When one finishes, start
   the next queued one.

The explorer writes its own findings with `pa` and sets the final status, so
the board fills in while they run. When a sub-agent returns, check that its
requirement is no longer `working`. If it still is, set
`explore_status=failed` and `explore_note` to one line on what went wrong.

Tell the user about progress only when something needs them: an exploration
that asks a question, or the whole batch finishing. Then give counts, not a
list.

## 4. Act on what the board sends

The board puts text in the chat box and the user presses Send.

| Message from the board | What you do |
|---|---|
| "Canvas action on data/<slug>.json:" then lines like `- R-07 explore_status = requested` | These arrive without the user pressing Send, and only ever carry state. For each `explore_status = requested` line, do step 3 for that requirement. Apply any other line with `$PA set` exactly as written (an approval is `explore_status = reviewed`). Do not reply unless something fails. |
| "Start exploring dependencies for R-07 ..." (`explore`) | The same request in words, from a host without direct actions. Step 3 for that requirement. |
| "Start exploring dependencies for every queued requirement ..." (`explore-all`) | Step 3 for all with `explore_status=queued`. |
| "Save these edits ..." (`save-edits`) | Apply each line with `$PA set`. This is how approvals (`approve`), a chosen capability (`selected_option`) and edited fields arrive. Confirm in one line. |
| "Explore R-07 ... again. My note: ..." (`return`) | Set `explore_status=working`, then start a new explorer with the note added to its prompt. It replaces that requirement's dependencies rather than adding duplicates. |
| "My answer on R-06 ...: <answer>" (`answer`) | Clear `explore_question` with `explore_question=null`, set `explore_status=working` and start an explorer with the answer added to its prompt. |
| "Summarize the dependency mapping ..." (`summarize`) | Render `views/summary.json` to `artifacts/<slug>-dependency-summary.html`, open it, and say in three or four lines what it means for the document: which requirements are cheap, which are expensive, and which may need to move. |

Never set `reviewed` yourself. That is the user's call.

To show one requirement for review inside your answer, render the review card:
`$PA render SKILL_DIR/views/review-card.json --host chat --data data/<slug>.json --record <id> --out artifacts/<slug>-review-<id>.html`

## When requirements change later

If a requirement's content changes after it was explored, `pa` marks the
dependencies and options derived from it as stale, and the board shows that.
Offer to explore those again. Do not do it unasked.

## Without Omnigent

If `printenv OMNIGENT` prints nothing, do the same steps and tell the user to
open the HTML files in a browser. The buttons then show what they would send.
