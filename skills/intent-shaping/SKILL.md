---
name: intent-shaping
description: Take an idea from a sentence to something a team could commit to, step by step, against a framework that says how deep and how broad the thinking must be. Use when the user has an idea, hunch, opportunity or problem and wants to shape it, elaborate it, define the intent, write an intent or opportunity brief, pressure-test it, or asks "is this ready to take to the team".
---

# Intent shaping

You help the user turn an idea into an intent by asking for one thing at a
time, the thing the idea is weakest on. A framework file says what "deep
enough" and "broad enough" mean; you hold the idea against it honestly. You
do not write the user's intent for them, and you never call an area deeper
than what exists to support it. Views are drawn with the view kit; other
people are called with the `participants` skill.

## Setup (once per session)

```bash
PA="python3 <this skill's folder>/../view-kit/scripts/pa.py"
```

`SKILL_DIR` means this skill's folder. Paths are relative to the workspace.

## The framework

Read `frameworks/intent.md`, or the file the user names. It has:

- `## Depth`: numbered levels, each with what it is enough for.
- `## Breadth`: areas. Each has "Required from: N" and one line per depth
  saying what must exist for the area to be at that depth.
- `## Rules`: follow them.

Use its level and area names word for word. If there is no framework file,
say so and ask whether to use the notional one from the product's
`workspace/frameworks/intent.md`. Do not improvise a framework silently.

**An idea's depth is the lowest depth among the areas required at the target
level** (areas marked not needed do not count).

## 1. Capture the idea and the target

Ask how far to go today with the form, unless the user said:

```bash
$PA render SKILL_DIR/views/target.json --host chat --out artifacts/<slug>-target.html
```

The answer arrives as "Shaping setup: ..." or "Choose the target depth
yourself ...". Then create the dataset with one `area` record per breadth
area in the framework:

```bash
$PA init data/<slug>-intent.json --title "<the idea, as the user said it>" --meta framework="<framework name>" --meta depth="0" --meta target="3 · Shaped"
$PA flow data/<slug>-intent.json --scenario SKILL_DIR
$PA add data/<slug>-intent.json --json '[{"id":"AR-1","type":"area","title":"Customer","required_from":1,"depth":1,"depth_name":"Spark","status":"ready","by":"you","statement":"...","next":"<the framework line for depth 2>","question":"..."}]'
$PA render SKILL_DIR/views/map.json --data data/<slug>-intent.json --out artifacts/<slug>-intent.html
```

Place what the user has already said into the areas, in their words, and
score each area strictly. A solution with no problem behind it leaves Problem
empty: say so, kindly and plainly. If they named files to read first, read
them and place what they contain, with `basis` pointing to where.

Area statuses: `queued` (not required until a deeper level), `needs-you`
(you have asked the user its question), `working` (you or a participant are
on it), `ready` (below target, nobody on it), `reviewed` (at or beyond the
target), `parked` (the user said it is not needed).

## 2. The loop: one area at a time

Repeat until the idea reaches the target:

1. Find the shallowest area required at the current target. Ties: framework
   order.
2. Write its `next` (the framework's line for the next level, word for word)
   and one `question` that would get it there. Set it `needs-you` and ask the
   question in the chat. To show it as a card:
   `$PA render SKILL_DIR/views/area.json --host chat --data data/<slug>-intent.json --record <id> --out artifacts/<slug>-area-<id>.html`
3. When the answer comes, update `statement` in the user's words, add to
   `basis`, and re-score. Move `depth` only when what the line asks for now
   exists. If the answer is confident but does not contain it, say what is
   still missing and leave the depth.
4. Record anything assumed or missing as `gap` records under the area, with
   who could close it, `status` `open`. Set it `closed` when it is answered.
5. Update the dataset's depth (`$PA set data/<slug>-intent.json --meta depth="2 · Framed"`)
   and the workflow step (`$PA flow ... --step <n>`: 1 capture, 2 frame,
   3 shape, 4 test, 5 committable, matching the depth being worked toward).
   Tell the user in one line when the idea crosses a level.

Where an area is about what other people know (risks, dependencies, cost,
evidence), and the user allowed it, call the participant who would know
rather than asking the user to guess. Say you are doing it. Their answer goes
in `statement` and `basis` with `by` set to them. A participant being asked
is not the same as a participant having agreed: score accordingly.

Do several areas in parallel only when they wait on different people.

## 3. What the user can do in the view

| Message | What you do |
|---|---|
| "Let us take <area> one level deeper." (`deepen`) | Step 2 of the loop for that area, even if it is not the shallowest. |
| "On <area>: ..." (`answer`) | Step 3 of the loop with that answer. |
| "Ask whoever would know about <area> what we are missing." (`ask-someone`) | Pick the participant whose `call_for` fits and call them. If nobody fits, say who would be needed. |
| "<area> is not needed for this idea. Why: ..." (`skip`) | Set `status=parked` and `skip_note`. It no longer holds the idea back. Mention it in the brief. |
| "Check the depth of <area> against the framework, strictly." (`challenge`) | Re-read each line up to the claimed depth and say, line by line, what meets it. Lower the depth if something does not, and say why. |
| "Raise the target for ... by one level and show me what that takes." (`go-deeper`) | Update `target`, re-mark areas (`queued` areas may now be required), and list what each needs. |
| "Write the intent brief from ... at its current depth." (`brief`) | Step 4. |
| "Save these edits ..." with `AR-4 statement` (`save-edits`) | Apply with `$PA set`, then re-score that area as in step 3 of the loop. |

## 4. Write the intent brief

Write `artifacts/<slug>-intent-brief.md`: the depth reached and the
framework used; one short section per area in the user's words; what is
deliberately out; open gaps with who could close each; and "what it would
take to reach" the next level. State the depth honestly at the top: a brief
at "Shaped" must not read like a commitment. Open it, render
`views/summary.json` to `artifacts/<slug>-intent-summary.html`, and when the
target is reached set `$PA flow ... --done`.

The natural next kinds of work are decision review (for the open gaps that
are choices) and, once committed, delivery status.

## Preview without an agent

`$PA preview SKILL_DIR --out artifacts/intent-shaping-preview.html`
