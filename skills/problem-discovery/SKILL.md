---
name: problem-discovery
description: Read raw material (interview notes, call transcripts, support tickets, survey answers, usage data) and find the problems people actually have, with the evidence for and against each, so the user can choose which are worth solving. Use when the user asks to find problems, pain points, themes or opportunities in research or data, to synthesize interviews into problems, asks "what should we solve", or says "problem discovery".
---

# Problem discovery

You read what the user gives you, and only that, and turn it into a short list
of problems stated in the words of the people who have them. You show the
evidence for each, look on purpose for evidence against, and say what the
sources cannot tell us. The user decides which problems are worth solving.
Views are drawn with the view kit; other people are called with the
`participants` skill.

## Setup (once per session)

```bash
PA="python3 <this skill's folder>/../view-kit/scripts/pa.py"
```

`SKILL_DIR` means this skill's folder. Paths are relative to the workspace.

## 1. Agree what you are looking for

Render the setup form and open it, unless the user already said what matters:

```bash
$PA render SKILL_DIR/views/focus.json --out artifacts/<slug>-focus.html
```

The answer arrives as "Discovery setup: ..." or "Use your judgment ...". If
the user wrote what they already believe, treat it as a hypothesis to test,
and say at the end whether the sources support it.

## 2. Read the sources

```bash
$PA init data/<slug>-problems.json --title "<what the discovery is about>" --meta source="<the folder or files>"
$PA flow data/<slug>-problems.json --scenario SKILL_DIR
$PA add data/<slug>-problems.json --json '[{"id":"S-1","type":"source","kind":"Interview","title":"Interview: mobile dog groomer","who":"Sole trader, 3 weeks in","size":"38 minutes","path":"context/interviews/01-groomer.md","status":"queued"}]'
$PA render SKILL_DIR/views/sources.json --data data/<slug>-problems.json --out artifacts/<slug>-sources.html
```

Add every file as a `source` before reading any, so the user sees the whole
pile. Read each one in full; set it `working`, then `reviewed` with a
one-sentence `takeaway`. Describe people by segment, never by name. For a
table of data, say in `size` how many rows or accounts it covers.

If a file cannot be read, keep it in the list and say so. Never fill a gap
from general knowledge: the list of sources is the whole world for this work.

## 3. Find candidate problems

`$PA flow ... --step 2`. Render the board and open it:

```bash
$PA render SKILL_DIR/views/problems.json --data data/<slug>-problems.json --out artifacts/<slug>-problems.html
```

Add `problem` records (shape in `schemas/records.json`). What makes a good
one:

- **The title is the problem as the person would say it**, first person,
  with no solution in it. "I cannot tell which invoices have been paid", not
  "Invoice reconciliation" and not "Needs invoice matching".
- **One problem per record.** If two quotes describe different situations,
  they are two problems. If two candidates would be fixed by the user
  understanding one thing, merge them.
- **`evidence` is word for word**, each with the source id and where in it
  (a time, a line, a row count). A number from data is evidence too: quote
  the figure and what it counts.
- **`today`** says what they do now and what it costs them. A problem with no
  workaround and no cost is a wish.
- **`spread`** (1 to 5) is how many independent sources show it. Three quotes
  from one interview is 1. **`pain`** (1 to 5) comes from the evidence, not
  from how it sounds.
- **`by`** is who found it: `aviator`, or the participant's id.

Honour the bar the user chose in step 1. Below the bar, mention the instance
in your summary instead of adding a record.

## 4. Weigh the evidence

`$PA flow ... --step 3`. For each candidate, while it is `working`:

- Search the sources for **evidence against**: someone in the same situation
  who was not bothered, data that shows no effect, a low count. Record it in
  `against`. Finding none after looking is a result: say you looked.
- If data can size the problem, add `measure` with the number and its source.
- Write `unknown`: the most important thing the sources do not tell us. This
  is usually what the user should find out next.
- If a participant on the roster knows the area, call them: a researcher to
  check you have not missed or understated something, a data owner to size
  it. Say that you are doing so.

Then set the problem `ready`.

## 5. The user chooses

`$PA flow ... --step 4`. Tell the user how many candidates there are, which
stands out and why, in three lines. They sort them on the board.

| Message or action | What you do |
|---|---|
| `pursue` (direct, or "Problem P-1 ... is worth solving.") | The status is already `reviewed`. Reply in one line. If its `unknown` would change what gets built, say so once. |
| "Park problem P-5 ... Why: ..." (`park`) | Set `status=parked` and `park_note`. |
| "I am not convinced by problem P-4 ... What would convince me: ..." (`more`) | Set `status=returned` and `return_note`. Look for exactly that in the sources. If it is there, add it and set `ready`. If it is not, say so plainly, and say what new source would answer it. Do not stretch weak evidence. |
| "Argue against problem P-1 ... as hard as the sources allow." (`challenge`) | Make the strongest honest case that this is not a problem worth solving, from the sources only: alternative explanations, who is missing from the sample, what the numbers do not show. Add anything new to `against`. Leave the status alone. |
| `reconsider` (direct, or "Reconsider problem ...") | The status is already `ready`. Clear `park_note` with `park_note=null`. |
| "Also read these and update the problems ...: ..." (`add-sources`) | Add the files as sources, read them, and update evidence, `spread` and `against` on existing problems before adding new ones. Say what changed. |
| "Open context/... beside this." (`open-source`) | Open that file in the canvas. |
| "Write the problem brief ..." (`brief`) | Step 6. |
| "Save these edits ..." (`save-edits`) | Apply each line with `$PA set`. |

Never mark a problem worth solving yourself.

## 6. Write the problem brief

`$PA flow ... --step 5`. Write `artifacts/<slug>-problem-brief.md`. For each
problem marked worth solving: the problem in their words, who has it and
when, what they do today, the three strongest quotes with sources, the
evidence against, the size if known, and what we still do not know. Then one
short section on what was parked and why, and one on whether the sources
supported what the user believed at the start. No solutions.

Render `views/summary.json` to `artifacts/<slug>-problems-summary.html`, open
it, and set `$PA flow ... --done`. If the user wants to go on, intent shaping
is the next kind of work.

## Preview without an agent

`$PA preview SKILL_DIR --out artifacts/problem-discovery-preview.html`
