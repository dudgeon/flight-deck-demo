---
name: delivery-status
description: Check a delivery plan against what is actually happening, project a new date when something moves, explore ways to recover, and write the status update. Use when the user asks for a status update, delivery update, where a launch or project stands, whether a date still holds, what is at risk, to check on dependencies, or to prepare for a steering or status meeting.
---

# Delivery status update

You find out where a plan really stands, by asking the people who own each
part and checking what you can check yourself. You never repeat last week's
date as this week's fact. When something moves you say what it does to the
final date, look for ways to recover, and let the user choose. Views are
drawn with the view kit; owners are reached with the `participants` skill.

## Setup (once per session)

```bash
PA="python3 <this skill's folder>/../view-kit/scripts/pa.py"
```

`SKILL_DIR` means this skill's folder. Paths are relative to the workspace.

## 1. Load the plan

If `data/<slug>-delivery.json` exists, this is a later update: keep it, and
go to step 2. Otherwise build it from the plan the user points to:

```bash
$PA init data/<slug>-delivery.json --title "<what is being delivered>" --meta planned="24 Mar" --meta projected="24 Mar" --meta as_of="<today, as 'Thursday 5 Mar'>" --meta source="<the plan>"
$PA flow data/<slug>-delivery.json --scenario SKILL_DIR
$PA add data/<slug>-delivery.json --json '[{"id":"M-1","type":"milestone","title":"...","owner":"cards-platform","planned":"13 Mar","projected":"13 Mar","status":"on-track","critical":true}]'
$PA render SKILL_DIR/views/plan.json --data data/<slug>-delivery.json --out artifacts/<slug>-delivery.html
```

- A **milestone** is an outcome that is either true or not ("Platform passes
  the load test"), with one owner and a plan date. Five to twelve is right.
  If the plan is a task list, group it.
- A **dependency** (`parent` = the milestone) is something the milestone
  waits for from someone else.
- `owner` is a participant id where one fits, `you` for the user, `aviator`
  for what you can check yourself, otherwise a team name in plain text.
- `critical: true` when a slip here moves the final date.

If there is no plan at all, say so and offer to build one with the user
first. Do not invent dates.

## 2. Check each open milestone

`$PA flow ... --step 2`. Set every milestone that is not `done` to `working`,
then for each:

- **Owned by a participant:** call them and ask one specific question that
  names the milestone and its date. Calling owners for a status check is
  expected: say you are doing it, do not ask first.
- **Owned by the user:** ask them, all in one message.
- **Checkable by you** (a file, a dataset, a build note): check it.
- **Nobody you can reach:** leave the last known date, set `confidence` to 2
  or lower, and write in `basis` that it is unconfirmed and since when.

Record the result on the milestone: `status`, `projected`, `slip`,
`confidence`, and always `basis` (who said it and when, or what you checked).
When something moved, write `change` in one sentence. Clear last time's
`change` with `change=null` where nothing moved this time.

Statuses: `on-track` (expected on the plan date), `at-risk` (may slip, or
holds only if something uncertain happens), `late` (will miss the plan
date), `done`.

## 3. Project the date

`$PA flow ... --step 3`. Carry every slip forward through what depends on it,
down to the final milestone, and update the dataset's own
`projected` (`$PA set data/<slug>-delivery.json --meta projected="2 Apr"`). Say how you got
there in `basis`. A projection is one date with a confidence, not a range
that hides the answer. If the date did not move, say so in one line and go to
step 5.

## 4. Explore ways to recover

`$PA flow ... --step 4`. For each `late` or `at-risk` milestone marked
`critical`, look for two or three real alternatives and add them as
`alternative` records under it: `title` (an action), `effect` (the date it
gives, and how much it recovers), `cost` (what is given up or risked),
`needs` (who has to agree), `fit` 1 to 5. Ask the owners what is possible;
do not make up capacity. Always include "Accept the new date" with its real
cost, so doing nothing is a visible choice.

Put the choice in front of the user:

```bash
$PA render SKILL_DIR/views/milestone.json --host chat --data data/<slug>-delivery.json --record <id> --out artifacts/<slug>-milestone-<id>.html
```

| Message | What you do |
|---|---|
| "Save these edits ..." with `M-4 selected_option` (`save-edits`) | Apply it. Then re-project: update the milestone and everything after it. If the option needs someone's agreement, get it (call them) before you treat the date as recovered; until then the milestone is `at-risk`, not `on-track`. |
| "Explore ways to recover the date on milestone ..." (`recover`) | This step, for that milestone. |
| "I accept the projected date for milestone ... Make it the plan." (`accept`) | Set `planned` to `projected`, clear `slip`, set `on-track`, and note the old date in `note`. Update the dataset's `planned` if it was the final milestone. |
| "Check milestone ... with its owner and update the date." (`check`) | Step 2 for that milestone. |
| "Check every open milestone ..." (`refresh`) | Steps 2 and 3 again. Update `as_of`. |
| "Write the status update from ... for: ..." (`write`) | Step 5, for that audience. |

Never choose an alternative for the user.

## 5. Write the update

`$PA flow ... --step 5`. Write `artifacts/<slug>-status-<date>.md` and open
it. Shape it for the audience the user named; for a steering group:

1. **In one line:** the date, whether it moved, and why.
2. **What changed** since the last update. Only what changed.
3. **Where each milestone stands:** a table of plan date, date now, status.
4. **What you are watching:** things that hold only if something uncertain
   happens, and when you will check.
5. **What is needed from the reader:** a decision, or "nothing".
6. **How you know:** one line on sources.

No adjectives about progress. If something is late, the first line says so.
Render `views/summary.json` to `artifacts/<slug>-delivery-summary.html`, and
set `$PA flow ... --done`. If you said you would check something later, and
the host lets you schedule it, do; otherwise tell the user when to ask you.

## Preview without an agent

`$PA preview SKILL_DIR --out artifacts/delivery-status-preview.html`
