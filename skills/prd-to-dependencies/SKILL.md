---
name: prd-to-dependencies
description: Take a PRD or requirements document through to what the work depends on and the options for getting it, in three parts the person moves between freely - Specify (a catalog of testable requirements), Map (the platform capabilities each requirement needs) and Choose (alternatives with scope and delivery levers, then a choice). Use when the person wants to go from a PRD to dependencies and options, says "PRD to dependencies", or has mapped dependencies and needs to weigh alternatives.
---

# PRD to dependencies

One arc in three parts (D-148). The person can start at any part, leave and
come back, work on another stage in between, and run the same initiative
through again later (D-149). What matters is that every part gets done, not
the order. You never write HTML. You change data with `pa` and the views
redraw themselves.

| Part | What it makes | How |
|---|---|---|
| **Specify** | A catalog of testable requirements, each traced to a line of the document | The `prd-to-requirements` skill |
| **Map** | For each requirement, the platform capabilities it depends on and the options that could meet it | The `requirements-to-dependencies` skill |
| **Choose** | For each dependency that needs a decision, a few real alternatives compared on scope, effort and waiting, and the person's choice | This skill, below |

## Setup

```bash
PA="python3 <this skill's folder>/../view-kit/scripts/pa.py"
```

`SKILL_DIR` means this skill's folder. Paths are relative to the session's
workspace folder.

## 1. Find where the person is

Look before you ask:

- A requirements dataset in `data/` whose requirements are not all
  `reviewed`: Specify is under way.
- A dataset whose requirements carry `explore_status`: Map is under way or
  done.
- A `data/<slug>-alternatives.json`: Choose is under way.
- Only a document in `context/`: start at Specify.

If the person named a part ("let's look at the options"), go there, even if
an earlier part is unfinished. Say in one line which parts are done and which
are not, and carry on. Never send them back to finish a part first.

If the work belongs to an initiative (`pa artifacts`, or the person named
one), stamp what you make with it and use its registers (D-142).

## 2. Specify and Map

Follow the `prd-to-requirements` skill for Specify and the
`requirements-to-dependencies` skill for Map, step by step, with their views
and their canvas actions. Read their SKILL.md when you start a part. The
catalog's "Map dependencies" button (`map-dependencies`) moves to Map.

Show progress with the step that matches the part:

```bash
$PA flow data/<slug>.json --scenario SKILL_DIR --session <this session's id, from sys_session_get_info>
$PA flow data/<slug>.json --step <2 for Specify, 3 for Map, 4 for Choose> --note "<a few words>"
```

## 3. Choose

Choose starts from the map. A dependency needs a choice when no option meets
it in time, when the options trade scope or cost differently, or when the
person asks.

```bash
$PA template new alternatives --out data/<slug>-alternatives.json --title "<Initiative>: alternatives" [--initiative <key>]
$PA render <the template's folder>/views/worksheet.json --data data/<slug>-alternatives.json --out artifacts/<slug>-alternatives.html
```

`$PA template show alternatives` prints the template's folder. The worksheet
lets the person try an option in each choice and watch the totals move (our
effort, the longest wait, teams relied on, scope traded) against the
baseline before choosing. `views/compare.json` is the same data as a plain
table. Open the view with `ui_open_file`, then add records:

- One `choice` per decision, written as a question ("How do we verify
  identity by March?"), with `about` naming the requirement or dependency id.
- Two to four `option` records under it, never more. Put the baseline (what
  the map found) first: the worksheet measures the others against it. Use the four kinds:
  `capability-swap` (another capability or provider, or building it),
  `scope-trade` (do less, or differently), `resequence` (change the order or
  the phase) and `presets` (a default or ready-made instead of building).
  (The baseline from the map is one of the four at most.)
- `effort` (our own work, person-weeks) and `waiting` (time on other teams,
  weeks) are separate numbers. Put where each number came from in `scope` or
  `relies_on`. Leave a number out rather than guess.
- Every option says what it gives up in `scope`.

Then say in one or two lines how many choices are waiting and what the
person can do in the view (choose, turn down, ask for another option).

When a choice has real trade-offs or several choices depend on each other,
put it to the person with the `decision-brief` skill if it is installed,
handing over the choice, its options and their evidence. Otherwise the view
is enough.

When the person has chosen, write the decision to the initiative's
decisions register, if there is one, and set its id on the choice:

```bash
$PA register <initiative> decision "<choice>: <option chosen>. <reason>" --stage specify
$PA set data/<slug>-alternatives.json <choice id> decision=<register id>
```

A later change of mind is a new decision with `--supersedes`, never an edit.

## 4. Hand over

When every part is done, say so in two or three lines: requirements,
dependencies, and what was chosen. Then offer the next step once: Engage
owners, for onboarding with the teams that were chosen, or Deliver, for
the plan and status. Do not start it unasked.

## Act on what the views send

Specify and Map actions are handled exactly as their skills say:

| Message | Where it is handled |
|---|---|
| `answer`, `return`, `split`, `approve-all`, `save-edits`, canvas actions on the catalog | `prd-to-requirements` |
| `map-dependencies` | Move to Map with the same dataset |
| `explore`, `explore-all`, `answer`, `return`, `summarize`, canvas actions on the board | `requirements-to-dependencies` |

From the alternatives view:

| Message | What you do |
|---|---|
| "I choose option O-2 ... because: ..." (`choose`) | Set the option `status=chosen` with the reason, set the choice `status=chosen` and `selected_option`, turn the others down with a reason each (ask the person if they gave none), and record the decision as above. |
| "Turn down option O-3 ... Reason: ..." (`reject`) | Set `status=rejected` and `reason`. |
| "Find another option for C-1 ..." (`more`) | Add one more option of a kind not yet there, if the choice has fewer than four. If it already has four, say which one you would replace. |

Never choose for the person, and never set an option `chosen` without their
words.

## Without Omnigent

If `printenv OMNIGENT` prints nothing, do the same steps and tell the person
to open the HTML files in a browser. The buttons then show what they would
send.
