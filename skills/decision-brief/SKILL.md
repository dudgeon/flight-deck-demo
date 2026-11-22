---
name: decision-brief
description: Put a complex decision to the person as a decision brief, a page with context, drawn options, tradeoffs and a recommendation where they pick and comment, from one JSON file and a fixed template. Use when a choice has real tradeoffs and is hard to undo, visual, one of several linked decisions or needed research, when any skill's Decide step needs the person, or when asked to "brief me", for a decision walkthrough or to lay out options. Not for one quick choice; ask that with a question card.
---

# Decision brief

A brief puts one or more decisions in front of the person so they never
decide blind: what they need to know, a picture of each option, what each
gives up, your recommendation and why, and a place to pick, write
"Something else" and add a note. Every brief in Flight Deck uses this skill,
so they all look and work the same, and you write only the content.

**You write one JSON file. Never write the page.** `scripts/brief.py` draws
it from `template/brief.html`, which holds the layout, the styles, the
visual components and the answer handling. Changing how briefs look is a
change to the template, once, for every brief.

```bash
BRIEF="python3 <this skill's folder>/scripts/brief.py"   # standard library only
```

## When to make one

Make a brief when there are **two or more real options with tradeoffs** and
at least one of these holds:

- it is hard to undo (scope, dates, commitments, anything another team builds on);
- it is visual (layouts, designs, what something looks like);
- it is one of several linked decisions;
- framing it took research the person has not seen.

Otherwise ask with one question card (`AskUserQuestion`, recommendation
first, with "Something else"), or just do the work if it is easy to undo. The
person can always say "brief me on this" or "just ask me". When you make a
brief on your own judgment, say why in one line.

Other skills don't copy any of this. A skill whose step needs the person to
choose says "put it to the person with the `decision-brief` skill" and hands
over what it found: the question, the options, the evidence. A workflow's
own checklist questions stay in its own views.

## 1. Gather before you write

- Read what the decision rests on: the files, datasets and earlier
  decisions. In a workspace, `pa artifacts --initiative <key>` and the
  initiative's `registers.json`; do not re-ask what a decision there already
  settled.
- Find the real options. Each one is something someone would actually do,
  not a straw man. Three or four is usually right.
- Know what each option costs and gives up, and which you recommend and why.
- Find or make the pictures: screenshots, a wireframe, a flow, a file tree,
  a table of examples. Saved images go next to the brief.

## 2. Write the brief

Start from a skeleton, or copy `examples/decision-briefs.json`, which shows
every field in use:

```bash
$BRIEF new briefs/<slug>.json --title "<the choice, as a name>" --decisions 3 [--initiative <key>] --for "<person>"
```

In a workspace, briefs live in `briefs/` and pages in `artifacts/`. The
fields, in full in `reference/format.md`:

| Field | What it holds |
|---|---|
| `id`, `title`, `for`, `from`, `date` | Names the brief. The title is what is being decided. |
| `initiative` | The initiative's key, so the answers go to its decisions register. |
| `why` | Two or three sentences: what this is and why the person is seeing it. |
| `recommendation` | All your recommendations together, in one paragraph. |
| `read`, `findings` | What you read (with links) and what you found, each in a sentence. |
| `decisions[]` | `id`, `label`, `question`, `context`, `know`, `stage`, `options[]`, `reason`, `depends_on` |
| `options[]` | `id`, `label`, `consequence` (what happens and what it gives up), `cost`, `recommended` (exactly one), `visual` |
| `after` | What happens once they decide. |

A **visual** is `{"html": "...", "caption": "..."}` or `{"image": "file.png"}`.
Put one on the decision (`stage`) or on each option; the page shows the
option the person points at. Build html only from the components in
`reference/components.md` (wireframes, flows, comparisons, file trees,
tables, chips). They follow the design tokens in light and dark; never set a
color or load anything.

Do not write a "Something else" option: the page adds it to every decision.
Write in plain words, sentence case, and keep each consequence to a sentence
or two.

## 3. Check, draw and show it

```bash
$BRIEF check briefs/<slug>.json      # errors stop the render: blind, no recommendation, remote loads, own colors
$BRIEF render briefs/<slug>.json --out artifacts/<slug>.html
```

Then show it where the person is:

- **In Flight Deck:** open it with `ui_open_file`. The person picks, then
  presses **Send answers to Claude**, which puts their answers in the chat
  box; they press Send.
- **On claude.ai** (contributors putting decisions to Geoff): render with
  `--fragment` and publish it as an Artifact with
  `capabilities: {"db": {}, "comments": {"composer_only": true}}`. Picks save
  to the page's `answers` collection as they are made. Give the person the
  direct link.
- **Anywhere else** the page keeps picks in the browser and offers **Copy
  answers** for pasting into the chat.

Tell the person in one or two lines what the brief asks and how many
decisions; don't repeat the brief in the chat.

## 4. Take the answers

Answers come back one of three ways. Write them into the brief, never only
in your head:

```bash
$BRIEF import briefs/<slug>.json --text -     # the text Send or Copy produced, on stdin
$BRIEF import briefs/<slug>.json --db <dir>   # an `answers` collection saved with ArtifactData list (out_dir)
$BRIEF answer briefs/<slug>.json <decision> <option|else> --note "..."   # an answer given in words
```

Record only what the person said or picked; a pick from another agent is
not their answer. "Something else" needs their words in `--note`. If an
answer changes what another decision means, say so before going on.

## 5. Record and write the note

When the person says they are done, or all decisions are answered:

```bash
$BRIEF record briefs/<slug>.json      # locks the answers; with `initiative`, one `pa register … decision` each
$BRIEF note briefs/<slug>.json --out briefs/<slug>.md [--url <artifact link>] [--archive <archived copy>]
$BRIEF render briefs/<slug>.json --out artifacts/<slug>.html   # the page now shows them as decided
```

The note holds each decision, the pick, the person's note, whether it was
the recommendation, the reason, the options considered, and links to the
brief, the archived copy and the research. A recorded answer is never
edited; a later change is a new brief whose decision names `supersedes`.
Reply with the outcome in a line or two and the note's link.

**In this repository** (contributors), the decisions also go in
`docs/product/decisions.md` and the index with numbers claimed the careful
way `CLAUDE.md` describes (the note's "Log entries" are written in that
form), the page is archived with the `docs-refresh` skill, and the note goes
in that archive folder as `note.md`.
