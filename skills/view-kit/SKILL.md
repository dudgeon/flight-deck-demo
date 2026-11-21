---
name: view-kit
description: Build and test structured, interactive views for the Omnigent canvas and chat from a dataset and a small JSON spec, using the `pa` command. Use when you need a table, board, detail card, summary or form that stays in step with a JSON dataset, when a workflow skill tells you to run `pa`, or when the user asks for a new view, widget or template for the product workspace.
---

# View kit

A view is a **spec** (a small JSON file saying which layout, which records,
which columns and which actions) drawn over a **dataset** (one JSON file of
records). `pa` turns the two into a single self-contained HTML file and redraws
that file whenever the data changes. The viewer picks up the change by itself.

So the working rule is: **change data, never markup.**

```bash
PA="python3 <this skill's folder>/scripts/pa.py"     # standard library only
```

## The frame you are drawing into

- One HTML file per view. Everything inline. The viewer blocks every network
  request, so no CDN, remote font, remote image or fetch will ever work.
- The file runs in a sandbox with no access to the app, to other files or to
  storage. The only ways out are `window.omnigent.prompt(text)`, which puts
  text in the chat box for the user to send, and `window.omnigent.saveState`.
- The canvas is usually 480 to 900 px wide, and the user can make it narrower.
  A view in chat is at most 720 px. Every layout here already adapts.
- The viewer reloads the file when it changes. The kit keeps the user's open
  card, filters and unsent edits across a reload.
- Views follow the app's light or dark mode. Never set colors, fonts or
  corners by hand: use the `--pa-…` tokens in `references/tokens.md`. The
  viewer injects the current tokens, so a design change reaches every view.
  See the `product-aviator-design` skill.

## Chat or canvas

Asks go in the chat; work goes in the canvas.

- **In the chat:** anything the user answers or glances at: a `form`, a single
  record's card (`detail`), a `summary`. Render it with `--host chat`. The
  command prints a fenced block (` ```view ` with `file:` and `title:`); put
  that block in your reply as it is and do not open the file. The app draws
  the view in the conversation. Once the user replies it folds into a
  one-line record, so say in words what you are asking as well.
- **In the canvas:** anything the user works in: a `tree-table`, a `board`, a
  document. Render it without `--host` and open the file.

One view in the chat at a time, and only when you need the user. Never put the
same view in both places. Outside Product Aviator the block shows as plain
text; then name the file and ask the question in words.

## The commands

| Command | Use |
|---|---|
| `$PA init data/x.json --title "Name"` | Start a dataset. `--from file.json` copies records in. `--meta key=value` adds dataset facts. |
| `$PA add data/x.json --json '[{...}]'` | Add records, or replace ones with the same id. Ids are assigned when left out and printed back. |
| `$PA set data/x.json R-01,R-02 field=value` | Change fields. `--where type=requirement --where status=ready` selects by value. `field=null` removes a field. `field=` in `--where` means "not set". `--meta key=value` changes a fact of the dataset itself (what `{dataset.key}` shows), and needs no ids. |
| `$PA get data/x.json [ids] [--where ...] [--fields a,b] [--count-by field]` | Read records, one JSON object per line. Read this instead of the whole file. |
| `$PA render spec.json --data data/x.json --out artifacts/x.html` | Draw a view. It is then redrawn on every `add` and `set`. `--host chat` for the compact form, `--record R-01` for a detail view. |
| `$PA refresh data/x.json` | Redraw every view of a dataset. |
| `$PA flow <data> --scenario <folder> --session <id>`, then `--step <n or name> [--note "..."]`, `--done` | Record which step of a workflow the work is at. The Session panel and the project page draw it as a card with the steps and how many items are done. |
| `$PA flow <data> --pause --note "..."`, `--resume`, `--stop`, `--state needs-you` | Set a run aside with a note on where it was left, pick it up, abandon it, or say it is waiting on the person. See "Runs" below. |
| `$PA runs [--all] [--json]` | List the runs in this workspace: state, step and where each was left. |
| `$PA who [id]` | List the participants in `participants/` (other agents and people), or show one. See the `participants` skill. |
| `$PA check <scenario folder>` | Validate a scenario's specs, schemas and fixtures. |
| `$PA preview <scenario folder> --out demo.html` | Build a standalone click-through of a scenario from its fixtures. |

After `render`, show the file with `ui_open_file`. You do not need to open it
again after later changes.

## Runs: pausing, resuming and stopping

One workflow working on one subject is a **run**. It outlives the session: its
state lives on the dataset and in `progress/`, and the project page lists every
run under "In flight" with a Resume button. Keep that state true, because the
app cannot read the conversation; it only reads what `pa flow` wrote.

- **Start.** Pass `--session <id>` with `--scenario` (the id is `conversation_id`
  from `sys_session_get_info`), so the project page can reopen this session.
- **Pause.** When the person sets the work aside in any words ("pause this",
  "let me come back to that later", "park it", or a press of Pause), run
  `$PA flow <data> --pause --note "<where we left off>"` straight away. The
  note is one or two sentences for someone returning cold: what is settled,
  what is next, and any question left unanswered. Do not confirm first and do
  not finish the step first. Reply in one line with the note and that they can
  resume from the project page or by saying so. Then stop working on it.
- **A side question is not a pause.** Answer it and carry on (the run stays
  where it is).
- **Needs the person.** When the run cannot move until the person answers or
  decides, run `--state needs-you --note "<what you need>"`. Clear it with
  `--state working` when they answer. Records with status `needs-you` set this
  on their own.
- **Resume.** When the person comes back ("resume intent shaping", "where did
  I leave off?", or a message from the Resume button), run `$PA runs` to find
  the run, read its note and its dataset, run `$PA flow <data> --resume`,
  say in one or two lines where things stood, and carry on from there. Never
  start a second dataset for a subject that already has a run.
- **Finish.** `--done`, when the last step's work is complete.
- **Stop.** Only when the person abandons the work ("drop this", "we are not
  doing this"). Ask once to confirm, then `--stop [--note "<why>"]`. Nothing
  is deleted, and `--resume` brings it back.

## Records and state

A record is a flat JSON object with `id`, `type` and `title`. `parent` puts it
under another record. `derived_from` lists the records it was worked out from.

State fields describe the work, not the content: `status`, `locked`, `stale`,
`question`, `return_note`, and any field ending `_status`, `_question`,
`_note`. Rules:

- The statuses are `queued`, `working`, `needs-you`, `ready`, `reviewed`,
  `returned`, `failed` and `draft`. A spec can add more.
- `reviewed` and `locked` belong to the user. Never set them yourself. Never
  rewrite a locked record unless the user asks for that record by id.
- When a record's content changes, `pa` marks everything derived from it as
  `stale`. Rewriting a stale record with `add` clears the mark.
- A later stage of work keeps its own status in its own field, such as
  `explore_status`, named by the spec's `status_field`. That way several
  stages share one dataset without treading on each other.

## Layouts

| Layout | Shows | Typical use |
|---|---|---|
| `tree-table` | Records as rows under collapsible parents, with editable cells | A catalog the user reviews line by line |
| `board` | Records as tiles in one lane per status | Many pieces of work running at once |
| `detail` | One record, in sections | A review card in chat |
| `summary` | Count tiles, bar breakdowns and short lists | Where things stand |
| `form` | Questions with a submit button | A few choices before work starts |

Every layout except `form` opens a detail card for a record, with drill-down
into its children and breadcrumbs back. Full reference with every key:
`references/spec.md`.

## Building a new view

1. Start from the nearest spec in a scenario's `views/` folder. Copy it.
2. Write a small fixture dataset with every status and edge case you care
   about: an empty group, a very long title, a record that needs the user, a
   locked one, a stale one.
3. Render and look at it: `$PA render my.json --data fixture.json --out artifacts/try.html --no-register`,
   then `ui_open_file` and `canvas_read`. Check it at a narrow width and with
   an empty dataset. Press every button: `canvas_eval` with `PA.pending()`
   shows what an edit would send.
4. If the scenario has a `SKILL.md`, every action id in the spec must be named
   there with what the agent does about it. `$PA check` enforces this.

If no layout fits, do not bend one. Either ask for a new layout to be added to
the kit, or write a one-off HTML artifact using the kit's stylesheet
(`kit/pa-kit.css`, inlined) so it still looks like it belongs. Any HTML file
is still a valid artifact.

## How actions reach you

Buttons with only a `set` (approve, lock, edit a cell) collect in a bar at the
bottom of the view as unsent edits. "Send to agent" puts one message in the
chat box: `Save these edits from the "<view>" view to <dataset>:` and one line
per change. Buttons with a `prompt` put that sentence in the chat box. In both
cases the user presses Send. Nothing in a view changes data by itself.

**Direct state changes.** Where the app supports it, a change that touches only
state (`status`, `locked`, any `*_status`) skips the chat box. It reaches you
as a message that starts `Canvas action on <dataset>:` followed by lines of the
form `- <id> <field> = <value>`. The app writes that message itself from
checked values, so it never contains anything but state. Apply the lines with
`$PA set` and stay quiet unless one fails. Mark an action `"direct": true` in
the spec to use this; give it a `prompt` as well for hosts without it.

Before you rewrite records the user may be editing, read their unsent edits
with `canvas_eval` and `PA.pending()` and keep them.
