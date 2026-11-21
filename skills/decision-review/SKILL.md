---
name: decision-review
description: Gather the open decisions on a piece of work, prepare each with options and a recommendation, and walk the user through them one at a time, recording what they decide. Use when the user asks what is still open, what they need to decide, to walk through open questions or decisions, to prepare for a steering or review meeting, or says "decision review".
---

# Decision review

You find what is waiting on the user, turn each into a decision they can make
in seconds, and record what they decide. You never decide for them. Views are
drawn with the view kit; other people are called with the `participants`
skill.

## Setup (once per session)

```bash
PA="python3 <this skill's folder>/../view-kit/scripts/pa.py"
```

`SKILL_DIR` means this skill's folder. Paths are relative to the workspace.

## 1. Gather what is open

Look where the user points. If they did not say, look in this order:

- datasets in `data/`: records with `status` (or another stage's status)
  `needs-you` or `returned`, and any `question` field that is set;
- documents they named or that this session worked on: contradictions,
  "TBD", open questions sections, review comments;
- this conversation: questions you asked that were never answered.

Pick a slug and start the dataset and the view:

```bash
$PA init data/<slug>-decisions.json --title "<what the decisions are about>" --meta source="<where you looked>"
$PA flow data/<slug>-decisions.json --scenario SKILL_DIR --session <this session's id, from sys_session_get_info>
$PA render SKILL_DIR/views/queue.json --data data/<slug>-decisions.json --out artifacts/<slug>-decisions.html
```

Open `artifacts/<slug>-decisions.html`. Tell the user how many you found and
where, in two lines. If you found more than ten, ask which area to start with.

## 2. Prepare each decision

Add one record per decision. Shapes are in `schemas/records.json`.

```bash
$PA add data/<slug>-decisions.json --json '[
 {"id":"D-1","type":"decision","by":"risk-review","area":"Compliance","impact":"High",
  "source":"Review finding RR-03, PRD section 7.4",
  "title":"Decide whose consent an under-18 allowance needs",
  "context":"...",
  "options":[{"label":"The cardholder only","consequence":"..."},{"label":"Cardholder and card user","consequence":"..."}],
  "recommended":"The cardholder only","reason":"...","status":"ready"}
]'
```

What makes a decision easy to make:

- **The title is the question**, verb first, in the user's words, about twelve
  words. Not a topic.
- **Context is three sentences or fewer**: what is true, what is at stake, who
  is waiting.
- **Two to four options**, each a real choice with one sentence on what
  happens if it is picked. Never pad with an option nobody would choose.
  "Find out more first" is only an option when you can say what would be found
  out and how long it takes.
- **Recommend one** and say why in a sentence or two. If you cannot recommend,
  say what you would need to know.
- **`by` is who raised it**: a participant's id, or `aviator`. `source` is
  where: a file and section, a record id, or "this conversation".

Use `status: working` for a decision you or a participant are still
preparing, and `ready` once it can be decided. If a decision belongs to a
participant's area and you lack what you need, call them (the `participants`
skill) and ask for the options and their recommendation. Set
`$PA flow ... --step 2`, then `--step 3` when the first ones are ready.

Order matters. Put first whatever blocks other people, then by impact.

## 3. Walk the user through them

Say how many are ready and which to start with. The user decides in the
canvas: they open a decision, pick an option and may add a note. Picks collect
as unsent changes and arrive together.

| Message | What you do |
|---|---|
| "Save these edits ..." with lines such as `D-2 choice: "(empty)" -> "Within 3 seconds"` or `D-2 note: ...` (`save-edits`) | Apply each line with `$PA set`. For every decision that now has a `choice`, also set `status=reviewed` and `locked=true`. Then do step 4 for those decisions. Confirm in one line with the count. |
| "I cannot decide D-5 ... yet. What is missing: ..." (`more`) | Set `status=returned` and `return_note`. Find what is missing, or call whoever can. When you have it, add it to `context`, clear `return_note` with `return_note=null` and set `status=ready`. |
| "@risk-review about decision D-1 ...: ..." (`ask`) | A message for that participant: pass it on as the `participants` skill says. |
| "Reopen decision D-6 ... because: ..." (`reopen`) | Set `locked=false`, `status=ready`, `choice=null`, and add the reason to `context`. |
| "For every open decision ... take the recommended option." (`take-recommended`) | For each `ready` decision with no `choice`, set `choice` to its `recommended`, `status=reviewed`, `locked=true`, and `note` to "Took the recommendation". List what you took, one line each. |
| "Write up the decisions ... as a decision log." (`log`) | Step 5. |

To put one decision in front of the user in the chat:
`$PA render SKILL_DIR/views/card.json --host chat --data data/<slug>-decisions.json --record <id> --out artifacts/<slug>-decision-<id>.html`

Never set `choice` yourself except for `take-recommended`.

## 4. After each decision

- If someone else raised it (`by` is a participant), tell them what was
  decided and pass on their reply. If they object, that is a new decision.
- Add what the decision causes as `follow-up` records under it:
  `{"id":"FU-3","type":"follow-up","parent":"D-2","title":"...","owner":"<participant id, aviator or you>","status":"queued"}`.
  Do the ones that are yours and that the user would expect, and set them
  `reviewed`.
- If the decision settles a record elsewhere (a requirement's `question`, a
  review finding), update that record too, and say so.

## 5. Record

When the user asks, or when nothing is open, write
`artifacts/<slug>-decision-log.md`: one entry per decided decision with the
question, what was picked, the user's note, who raised it, the date, and its
follow-ups. Add a short list of what is still open and why. Render
`views/summary.json` to `artifacts/<slug>-decisions-summary.html` and open it.
Set `$PA flow ... --done`.

## Preview without an agent

`$PA preview SKILL_DIR --out artifacts/decision-review-preview.html`
