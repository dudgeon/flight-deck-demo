---
name: document-review
description: Review a document and call in other agents or people for second opinions, with everyone's findings in one attributed list the user accepts or pushes back on. Use when the user asks to review a PRD, plan or other document, wants a second opinion on one, or asks to check in with risk, design or another participant about a document.
---

# Review a document with others

You review a document yourself, then bring in the participants who should have
a view. Everything anyone raises goes into one dataset of findings, each with
who raised it, shown in the canvas with the view kit. Calling people and
showing their turns is done with the `participants` skill; read it first.

## Setup (once per session)

```bash
PA="python3 <this skill's folder>/../view-kit/scripts/pa.py"
```

`SKILL_DIR` means this skill's folder. Paths are relative to the workspace.

## 1. Find the document and read it

Use the file the user named, otherwise look in `context/`. For a demo with no
document: `mkdir -p context && cp SKILL_DIR/fixtures/allowances-prd.md context/`.
Pick a short slug, e.g. `allowances`.

## 2. Your own review

```bash
$PA init data/<slug>-review.json --title "<Document name>" --meta source=<path of the document>
$PA render SKILL_DIR/views/findings.json --data data/<slug>-review.json --out artifacts/<slug>-review.html
```

Add what you found, a few at a time. Shapes are in `schemas/records.json`.

```bash
$PA add data/<slug>-review.json --json '[
 {"id":"F-01","type":"finding","by":"aviator","area":"Clarity","severity":"Medium",
  "section":"3.3 and FAQ","quote":"<the passage, word for word>",
  "title":"...","detail":"...","suggestion":"...","status":"ready"}
]'
```

Use `status: needs-you` with a `question` only when the user alone can settle
it. Open `artifacts/<slug>-review.html` with `ui_open_file`, say in two lines
what you found, and ask what needs asking.


## Show where the work is

The Session panel shows this workflow's steps and how far along it is. Tell it
as you go. Right after `init`:

```bash
$PA flow data/<slug>-review.json --scenario SKILL_DIR
```

Then `$PA flow data/<slug>-review.json --step <number> --note "<what is happening, a few words>"`
when you move to another step, and `--done` when the workflow is finished.
The steps: 1 first read, 2 call in others, 3 their reviews, 4 the user's decisions, 5 wrap up. The count of items done updates itself.

## 3. Decide who else should look

Run `$PA who --scenario SKILL_DIR` for who is eligible for this workflow. If
the user already named people, call them. Otherwise pick the participants
whose `call for` fits the document, say in one line who you are bringing in
and why, and call them. The user can stop you.

## 4. Call them

For each one, follow the `participants` skill. In what you ask them, include:

- the document's path and what to look at;
- that findings go in `data/<slug>-review.json`, with the command to add them:
  `python3 <absolute path of pa.py> add data/<slug>-review.json --json '[...]'`
  and the record shape from step 2, with `by` set to their id and ids that
  start with their initials (for example `RR-01`);
- that a finding only the user can settle gets `status: needs-you` and a
  `question`.

Pass on each reply in a participant block. The findings view redraws itself
when they add records. When a participant asks the user something, stop and
wait for the user; send their answer back to that participant.

## 5. Act on what the view sends

| Message | What you do |
|---|---|
| "Canvas action on data/<slug>-review.json:" then lines like `- F-05 status = reviewed` | Sent without the user pressing Send, state only. Apply each line with `$PA set` exactly as written. Do not reply unless something fails. |
| "I push back on finding F-06 ... raised by mara-okafor. My note: ..." (`push-back`) | Set `status=returned` and `return_note`. If someone else raised it, send them the note and pass on their answer. If you raised it, answer yourself. |
| "About finding F-03 ...: <answer>" (`answer`) | Set `answer`, clear `question` with `question=null`, set `status=ready`. Tell whoever raised it. |
| "Accept every finding that is raised." (`accept-all`) | The same request in words, from a host without direct actions. Set `status=reviewed` where `status=ready`. |
| "Apply the accepted findings ..." (`apply`) | Propose the edits to the document for every finding with `status=reviewed`, as a list of before and after passages. Change the document only when the user says to, and never a file in `context/`: write the revised copy to `artifacts/`. |

Never set `reviewed` yourself. Accepting is the user's call.

## 6. Wrap up

When everyone called has finished, render `views/summary.json` to
`artifacts/<slug>-review-summary.html`, open it, and say in three lines: how
many findings from whom, what is High, and what is waiting on the user.

## Preview without an agent

`$PA preview SKILL_DIR --out artifacts/document-review-preview.html` writes a
scripted click-through with invented data, including the other participants.
